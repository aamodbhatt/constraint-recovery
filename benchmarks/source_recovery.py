"""Prepare blinded artwork and ground/score source references outside recovery."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as XML
from benchmarks.audit_source_oracles import graph_reference,parse_xml
from constraint_recovery.geometric_recovery import validate_observations,TAGS

NS='http://www.w3.org/2000/svg'
DTD=re.compile(r'''<!DOCTYPE\s+svg\s+PUBLIC\s+["']-//W3C//DTD SVG 1\.1//EN["']\s+["']https?://www\.w3\.org/Graphics/SVG/1\.1/DTD/svg11\.dtd["']\s*>''',re.I)


def local(name):return name.rsplit('}',1)[-1]
def sha(raw):return hashlib.sha256(raw.encode() if isinstance(raw,str) else raw).hexdigest()


def normalize(source):
    normalized,count=DTD.subn('',source)
    if re.search(r'<!DOCTYPE|<\?(?!xml(?:\s|\?>))',normalized,re.I):
        raise ValueError('Only the known legacy SVG DTD declaration can be removed')
    root=parse_xml(normalized)
    if root.tag!='{'+NS+'}svg':raise ValueError('Expected SVG')
    return normalized,count


def blind_source(source):
    normalized,dtds=normalize(source);root=parse_xml(normalized);removed={}
    def note(name):removed[name]=removed.get(name,0)+1
    def prune(parent):
        for child in list(parent):
            if local(child.tag) in {'metadata','title','desc','script'}:
                note('element:'+local(child.tag));parent.remove(child)
            else:prune(child)
    prune(root)
    if any(local(e.tag)=='style' for e in root.iter()):
        raise ValueError('Blinding does not rewrite stylesheet selectors; source unsupported')
    identifiers={};classes={}
    for e in root.iter():
        if e.get('id'):
            if e.get('id') in identifiers:raise ValueError('Duplicate visual SVG ID')
            identifiers[e.get('id')]='b'+str(len(identifiers))
        for name in e.get('class','').split():
            if name not in classes:classes[name]='c'+str(len(classes))
    def fragment(name):
        if name not in identifiers:raise ValueError('Unknown functional SVG fragment reference')
        return identifiers[name]
    for e in root.iter():
        for key,value in list(e.attrib.items()):
            name=local(key)
            if name in {'content','resource','role','source','target'} or name.startswith(('data-','aria-','on')):
                del e.attrib[key];note('attribute:'+name);continue
            if name=='id':value=identifiers[value]
            elif name=='class':value=' '.join(classes[token] for token in value.split())
            elif name=='href' and value.startswith('#'):value='#'+fragment(value[1:])
            elif name=='href' and local(e.tag)=='a':
                del e.attrib[key];note('external-link');continue
            value=re.sub(r'''url\(\s*["']?#([^\s)"']+)["']?\s*\)''',lambda m:'url(#'+fragment(m.group(1))+')',value)
            e.set(key,value)
    XML.register_namespace('',NS)
    XML.register_namespace('xlink','http://www.w3.org/1999/xlink')
    blinded=XML.tostring(root,encoding='unicode')
    return dict(normalized=normalized,blinded=blinded,known_dtds_removed=dtds,redactions=removed)


def make_observations(blinded,measured):
    digest=sha(blinded)
    if measured.get('source_sha256')!=digest:raise ValueError('Blind measurements do not match artwork')
    observations=[];locations={}
    def painted(value,opacity):
        if value in {'none','transparent','rgba(0, 0, 0, 0)'}:return False
        return float(opacity)>0
    for p in measured['primitives']:
        if p['tag'] not in TAGS or not p['visible_by_display_visibility_opacity'] or p.get('viewbox_bounds') is None:continue
        identifier='p-'+sha(digest+'\0'+p['location'])[:12]
        if identifier in locations.values():raise ValueError('Opaque primitive identifier collision')
        locations[p['location']]=identifier
        path=p.get('path_geometry')
        closed=p['tag'] in {'rect','circle','ellipse','polygon'} or bool(path and math.dist(path['start'],path['end'])<=1e-6)
        style=p.get('computed_all',{})
        observations.append(dict(id=identifier,tag=p['tag'],bounds=p['viewbox_bounds'],closed=closed,
            filled=p['tag']!='line' and painted(p['computed']['fill'],style.get('fill-opacity','1')),
            stroked=painted(p['computed']['stroke'],style.get('stroke-opacity','1')) and float(re.sub(r'px$','',p['computed']['stroke_width']))>0,
            path=path))
    data=dict(schema_version=1,kind='blind-primitive-geometry',canvas=measured['canvas'],primitives=sorted(observations,key=lambda p:p['id']))
    validate_observations(data)
    return data,locations


def ground_reference(source,blinded,measured,locations):
    """A restricted exporter trace, not nearest-node matching or predictions."""
    reference=graph_reference(source,include_cells=True)
    if len(reference['pages'])!=1:raise ValueError('Grounding requires one authoring page')
    page=reference['pages'][0];root=parse_xml(blinded)
    groups=[e for e in root if local(e.tag)=='g']
    if len(groups)!=1 or any(local(e.tag) not in {'defs','g','switch'} for e in root):
        raise ValueError('Unsupported root export structure')
    group=groups[0];elements={}
    def walk(e,location):
        elements[id(e)]=location
        for i,child in enumerate(e):walk(child,location+'/'+local(child.tag)+'['+str(i)+']')
    walk(root,'svg')
    by_location={p['location']:p for p in measured['primitives']}
    children=list(group);cursor=0;nodes={};edges=[];translations=[]
    cells=page['cells'];vertex_ids={c['id'] for c in cells if c['attributes'].get('vertex')=='1'}
    edge_ids={c['id'] for c in cells if c['attributes'].get('edge')=='1'}
    def consume(tag):
        nonlocal cursor
        if cursor>=len(children) or local(children[cursor].tag)!=tag:
            raise ValueError('Unsupported exporter paint order: expected '+tag)
        e=children[cursor];cursor+=1;location=elements[id(e)]
        if tag!='g' and (location not in locations or location not in by_location):
            raise ValueError('Paint primitive is invisible or unmeasured')
        return e,by_location.get(location),locations.get(location)
    for cell in cells:
        attributes=cell['attributes'];is_node=attributes.get('vertex')=='1';is_edge=attributes.get('edge')=='1'
        if not (is_node or is_edge):continue
        if attributes.get('parent') in vertex_ids|edge_ids:raise ValueError('Nested objects need separate grounding')
        style={};flags=[]
        for token in attributes.get('style','').split(';'):
            if '=' in token:
                key,value=token.split('=',1);style[key]=value
            elif token:flags.append(token)
        if style.get('rotation','0')!='0' or style.get('flipH','0')!='0' or style.get('flipV','0')!='0':
            raise ValueError('Rotated/reflected source cells need separate grounding')
        if is_node:
            if any(flag!='rhombus' for flag in flags) or style.get('shape','rectangle') not in {'rectangle','rhombus'}:
                raise ValueError('Unsupported declared vertex shape')
            rhombus='rhombus' in flags or style.get('shape')=='rhombus'
            element,primitive,identifier=consume('path' if rhombus else 'rect')
            if rhombus:
                if not primitive.get('path_geometry') or math.dist(primitive['path_geometry']['start'],primitive['path_geometry']['end'])>1e-6:
                    raise ValueError('Declared rhombus is not a closed path')
                # This narrow exporter contract accepts only its four-sided
                # linear rhombus, not any artwork with the same bounding box.
                if not re.fullmatch(r'\s*M\s*[-+\d.eE ,]+(?:L\s*[-+\d.eE ,]+){3}\s*Z\s*',element.get('d','')):
                    raise ValueError('Unsupported rhombus drawing commands')
            geometry=cell['geometry']
            if not geometry or geometry.get('relative','0')!='0' or cell['geometry_children']:
                raise ValueError('Relative/offset vertex geometry needs separate grounding')
            x,y,width,height=[float(geometry.get(k,'0')) for k in ['x','y','width','height']]
            if not all(math.isfinite(v) for v in [x,y,width,height]) or min(width,height)<=0:raise ValueError('Invalid source vertex geometry')
            bounds=primitive['viewbox_bounds']
            if abs(bounds[2]-bounds[0]-width)>.2 or abs(bounds[3]-bounds[1]-height)>.2:
                raise ValueError('Source/paint vertex dimensions disagree')
            translations.append([bounds[0]-x,bounds[1]-y]);nodes[cell['id']]=identifier
        else:
            if style.get('endArrow')!='block' or style.get('startArrow','none')!='none':
                raise ValueError('Explicit single block end-head required for grounding')
            _,shaft,identifier=consume('path');_,head,_=consume('path')
            path=shaft.get('path_geometry');head_path=head.get('path_geometry')
            if not path or not head_path or math.dist(path['start'],path['end'])<=2 or math.dist(head_path['start'],head_path['end'])>1e-6:
                raise ValueError('Exporter shaft/head geometry does not match the declared form')
            from constraint_recovery.geometric_recovery import boundary_distance
            if boundary_distance(path['end'],head['viewbox_bounds'])>.3 or boundary_distance(path['start'],head['viewbox_bounds'])<=1:
                raise ValueError('Head is not at the declared terminal end of the shaft')
            edges.append(dict(shaft=identifier,source_cell=attributes.get('source'),target_cell=attributes.get('target')))
        if cell['label_present']:
            label,_,_=consume('g')
            if not any(local(e.tag) in {'text','foreignObject'} for e in label.iter()):raise ValueError('Missing exporter label')
    if cursor!=len(children):raise ValueError('Unaccounted painted export elements; no partial grounding claimed')
    if translations and any(abs(a-b)>.2 for delta in translations for a,b in zip(delta,translations[0])):
        raise ValueError('Source/paint vertex positions do not share one translation')
    for edge in edges:
        edge['source']=nodes.get(edge.pop('source_cell'));edge['target']=nodes.get(edge.pop('target_cell'))
    return dict(schema_version=1,kind='source-binding-reference',source_sha256=sha(source),observation_source_sha256=sha(blinded),
        declared_vertices=page['vertices'],declared_edges=page['edges'],nodes=list(nodes.values()),edges=edges,
        grounding='Restricted flat exporter paint-order trace plus all-vertex envelope/translation checks; no prediction used')


def score_predictions(predictions,reference,observation_raw):
    if predictions.get('observation_sha256')!=sha(observation_raw):raise ValueError('Prediction/input binding mismatch')
    if reference.get('observation_sha256')!=sha(observation_raw):raise ValueError('Reference/input binding mismatch')
    observations=validate_observations(json.loads(observation_raw));ids={p['id'] for p in observations['primitives']}
    if len(set(reference['nodes']))!=len(reference['nodes']) or not set(reference['nodes'])<=ids:
        raise ValueError('Invalid grounded vertex identifiers')
    shafts=[e['shaft'] for e in reference['edges']]
    if len(set(shafts))!=len(shafts) or not set(shafts)<=ids:raise ValueError('Invalid grounded shaft identifiers')
    if any(e[k] is not None and e[k] not in reference['nodes'] for e in reference['edges'] for k in ['source','target']):
        raise ValueError('Invalid grounded endpoint')
    if any(len(set(predictions[k]))!=len(predictions[k]) or not set(predictions[k])<=ids for k in ['node_candidates','shaft_candidates']):
        raise ValueError('Invalid prediction candidate identifiers')
    scored=[e for e in reference['edges'] if e['source'] is not None and e['target'] is not None]
    metrics={}
    for method,edges in predictions['methods'].items():
        if len({e['shaft'] for e in edges})!=len(edges) or {e['shaft'] for e in edges}!=set(predictions['shaft_candidates']):
            raise ValueError('Prediction shaft inventory mismatch')
        for e in edges:
            if any(e[k]['node'] is not None and e[k]['node'] not in predictions['node_candidates'] for k in ['source','target']):
                raise ValueError('Prediction points outside its candidate set')
        by_shaft={e['shaft']:e for e in edges};correct=0;both=0;answered=0
        for truth in scored:
            guess=by_shaft.get(truth['shaft']);hits=[]
            for end in ['source','target']:
                value=guess[end]['node'] if guess else None;answered+=value is not None
                hit=value==truth[end];correct+=hit;hits.append(hit)
            both+=all(hits)
        metrics[method]=dict(reference_endpoints=2*len(scored),answered_endpoints=answered,correct_endpoints=correct,
            endpoint_accuracy=correct/(2*len(scored)) if scored else None,both_end_correct_edges=both,
            both_end_accuracy=both/len(scored) if scored else None)
    def coverage(predicted,expected):
        matched=len(set(predicted)&set(expected))
        return dict(predicted=len(predicted),reference=len(expected),matched=matched,
            recall=matched/len(expected) if expected else None,precision=matched/len(predicted) if predicted else None)
    return dict(reference_vertices=reference['declared_vertices'],grounded_vertices=len(reference['nodes']),
        reference_edges=reference['declared_edges'],grounded_edges=len(reference['edges']),fully_bound_reference_edges=len(scored),
        node_candidates=coverage(predictions['node_candidates'],reference['nodes']),shaft_candidates=coverage(predictions['shaft_candidates'],shafts),methods=metrics)


def poison_source(source):
    """Deliberately alter one hidden binding, leaving visible artwork intact."""
    root=parse_xml(normalize(source)[0]);reference=graph_reference(source,include_cells=True)
    if len(reference['pages'])!=1:raise ValueError('One page required for mutation probe')
    page=reference['pages'][0];vertices=[c['id'] for c in page['cells'] if c['attributes'].get('vertex')=='1']
    edge=next((c for c in page['cells'] if c['attributes'].get('edge')=='1' and c['attributes'].get('target') in vertices),None)
    if not edge or len(vertices)<2:raise ValueError('Mutation probe needs a bound edge and two vertices')
    alternative=next(key for key in vertices if key!=edge['attributes']['target'])
    document=XML.Element('mxfile');diagram=XML.SubElement(document,'diagram',name=page['name'] or 'page')
    model=XML.SubElement(diagram,'mxGraphModel');cells=XML.SubElement(model,'root')
    for original in page['cells']:
        attributes=dict(original['attributes']);attributes['id']=original['id']
        if original is edge:attributes['target']=alternative
        cell=XML.SubElement(cells,'mxCell',attributes)
        if original['geometry'] is not None:XML.SubElement(cell,'mxGeometry',original['geometry'])
    root.set('content',XML.tostring(document,encoding='unicode'))
    return XML.tostring(root,encoding='unicode')


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    prep=sub.add_parser('prepare');prep.add_argument('--source',type=Path,required=True);prep.add_argument('--folder',type=Path,required=True)
    observation=sub.add_parser('observe');observation.add_argument('--folder',type=Path,required=True)
    ground=sub.add_parser('ground');ground.add_argument('--source',type=Path,required=True);ground.add_argument('--folder',type=Path,required=True)
    score=sub.add_parser('score');score.add_argument('--folder',type=Path,required=True)
    check=sub.add_parser('scorer-check');check.add_argument('--folder',type=Path,required=True)
    mutation=sub.add_parser('poison');mutation.add_argument('--source',type=Path,required=True);mutation.add_argument('--output',type=Path,required=True)
    pixels=sub.add_parser('pixels');pixels.add_argument('--folder',type=Path,required=True)
    args=parser.parse_args();folder=getattr(args,'folder',None)
    if args.command=='prepare':
        if args.source.resolve() in {(folder/'normalized.svg').resolve(),(folder/'blinded.svg').resolve()}:
            parser.error('Preparation cannot overwrite the original source')
        source=args.source.read_text();result=blind_source(source);folder.mkdir(parents=True,exist_ok=True)
        result['source_sha256']=sha(source)
        for key in ['normalized','blinded']:(folder/(key+'.svg')).write_text(result.pop(key))
        (folder/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
    elif args.command=='observe':
        data,locations=make_observations((folder/'blinded.svg').read_text(),json.loads((folder/'geometry.json').read_text()))
        (folder/'observations.json').write_text(json.dumps(data,indent=2)+'\n')
        (folder/'private-locations.json').write_text(json.dumps(locations,indent=2)+'\n')
    elif args.command=='ground':
        source=args.source.read_text();blinded=(folder/'blinded.svg').read_text();measured=json.loads((folder/'geometry.json').read_text())
        if json.loads((folder/'preparation.json').read_text())['source_sha256']!=sha(source):raise ValueError('Original source changed after preparation')
        observations,locations=make_observations(blinded,measured)
        if observations!=json.loads((folder/'observations.json').read_text()) or locations!=json.loads((folder/'private-locations.json').read_text()):
            raise ValueError('Private geometry correspondence changed')
        reference=ground_reference(source,blinded,measured,locations)
        reference['observation_sha256']=sha((folder/'observations.json').read_bytes())
        (folder/'reference.json').write_text(json.dumps(reference,indent=2)+'\n')
    elif args.command in {'score','scorer-check'}:
        raw=(folder/'observations.json').read_bytes();predictions=json.loads((folder/'predictions.json').read_text())
        reference=json.loads((folder/'reference.json').read_text())
        if args.command=='score':
            (folder/'scores.json').write_text(json.dumps(score_predictions(predictions,reference,raw),indent=2)+'\n')
        else:
            truth=next(e for e in reference['edges'] if e['source'] in predictions['node_candidates'] and e['target'] in predictions['node_candidates'] and e['shaft'] in predictions['shaft_candidates'])
            wrong=next(n for n in predictions['node_candidates'] if n!=truth['source'])
            before=json.loads(json.dumps(predictions));after=json.loads(json.dumps(predictions))
            for method in before['methods']:
                a=next(e for e in before['methods'][method] if e['shaft']==truth['shaft'])
                b=next(e for e in after['methods'][method] if e['shaft']==truth['shaft'])
                a['source']['node']=truth['source'];a['target']['node']=truth['target']
                b['source']['node']=wrong;b['target']['node']=truth['target']
            good=score_predictions(before,reference,raw);bad=score_predictions(after,reference,raw)
            if any(good['methods'][name]['correct_endpoints']-bad['methods'][name]['correct_endpoints']!=1 or good['methods'][name]['both_end_correct_edges']-bad['methods'][name]['both_end_correct_edges']!=1 for name in good['methods']):
                raise ValueError('Scorer did not detect the deliberately incorrect endpoint')
            (folder/'scorer-check.json').write_text(json.dumps(dict(passed=True,
                scope='One diagnostic edge set correct then deliberately incorrect; these modified predictions are not benchmark performance.'))+'\n')
    elif args.command=='poison':
        if args.source.resolve()==args.output.resolve():parser.error('Mutation cannot overwrite original source')
        args.output.write_text(poison_source(args.source.read_text()))
    else:
        import base64,io
        from PIL import Image,ImageChops
        records=[json.loads((folder/name).read_text()) for name in ['normalized-geometry.json','geometry.json']]
        images=[]
        for record in records:
            snapshot=record['snapshot'];raw=base64.b64decode(snapshot['data'],validate=True)
            if snapshot['source_sha256']!=record['source_sha256'] or snapshot['sha256']!=sha(raw):raise ValueError('Snapshot binding mismatch')
            images.append(Image.open(io.BytesIO(raw)).convert('RGBA'))
        if images[0].size!=images[1].size:raise ValueError('Blinding changed image dimensions')
        changed=sum(pixel!=(0,0,0,0) for pixel in ImageChops.difference(*images).getdata())
        result=dict(passed=changed==0,pixel_dimensions=list(images[0].size),changed_rgba_pixels=changed,
            scope='Exact full-viewport pixels in this browser with scripts disabled and secondary requests blocked, not cross-browser identity.')
        (folder/'pixel-check.json').write_text(json.dumps(result,indent=2)+'\n')
        if changed:raise ValueError('Blinding changed rendered pixels')


if __name__=='__main__':
    try:main()
    except ValueError as error:
        import sys
        print('source-reference: '+str(error),file=sys.stderr);raise SystemExit(2)
