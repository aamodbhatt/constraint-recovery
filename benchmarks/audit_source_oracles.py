"""Non-rendering feasibility probes for external source-declared graph references.

This reads authoring metadata, not pixels or predictions. It does not establish
human review, SVG edit support, geometric grounding or recovery accuracy.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import ssl
from urllib.parse import unquote
import urllib.request
import zlib
from defusedxml import ElementTree as ET

LIMIT=8_000_000


def parse_xml(text):
    if len(text.encode('utf-8'))>LIMIT:
        raise ValueError('XML reference exceeds the eight-MB budget')
    # Legacy SVG exports contain an external SVG DTD declaration. This is a
    # non-rendering parser: entities/external entity references remain forbidden,
    # and neither the DTD nor URLs in the source are fetched or executed.
    return ET.fromstring(text,forbid_entities=True,forbid_external=True)


def graph_reference(source,include_cells=False):
    root=parse_xml(source)
    if root.tag!='{http://www.w3.org/2000/svg}svg':
        raise ValueError('Expected an SVG source')
    embedded=root.get('content')
    if not embedded:
        raise ValueError('No embedded authoring graph; do not infer a reference')
    document=parse_xml(unquote(embedded))
    if document.tag!='mxfile':
        raise ValueError('Expected an embedded mxfile')
    pages=[];decoded_total=0;cell_total=0
    source_pages=document.findall('diagram')
    if len(source_pages)>32:raise ValueError('Authoring reference exceeds the 32-page budget')
    for page in source_pages:
        model=page.find('mxGraphModel')
        if model is None:
            compressed=base64.b64decode(''.join((page.text or '').split()),validate=True)
            decoder=zlib.decompressobj(-15)
            decoded=decoder.decompress(compressed,LIMIT+1)
            if len(decoded)>LIMIT or decoder.unconsumed_tail or decoder.unused_data or not decoder.eof:
                raise ValueError('Oversized, truncated or trailing compressed graph')
            decoded_total+=len(decoded)
            if decoded_total>LIMIT:raise ValueError('Combined authoring pages exceed the decoded budget')
            model=parse_xml(unquote(decoded.decode('utf-8')))
        else:
            decoded_total+=len(ET.tostring(model,encoding='utf-8'))
            if decoded_total>LIMIT:raise ValueError('Combined authoring pages exceed the decoded budget')
        if model.tag!='mxGraphModel' or model.find('root') is None:
            raise ValueError('Missing mxGraphModel/root')
        cell_total+=len(model.find('root'))
        if cell_total>5000:raise ValueError('Authoring reference exceeds the 5000-cell budget')
        cells={};labels={}
        for item in model.find('root'):
            if item.tag=='mxCell':
                cell=item;identifier=cell.get('id')
            elif item.tag in {'object','UserObject'} and len(item.findall('mxCell'))==1:
                cell=item.find('mxCell');identifier=item.get('id') or cell.get('id')
            else:
                raise ValueError('Unsupported authoring cell wrapper')
            if not identifier or identifier in cells:
                raise ValueError('Missing or duplicate authoring cell ID')
            cells[identifier]=cell
            labels[identifier]=item.get('label',cell.get('value',''))
        vertices={key for key,cell in cells.items() if cell.get('vertex')=='1'}
        edges=[]
        for key,cell in cells.items():
            if cell.get('edge')!='1':continue
            if cell.get('vertex')=='1':raise ValueError('A cell cannot be both an edge and vertex')
            style={}
            for token in cell.get('style','').split(';'):
                if '=' in token:
                    name,value=token.split('=',1);style[name]=value
            source_id,target_id=cell.get('source'),cell.get('target')
            edges.append(dict(id=key,source=source_id,target=target_id,
                both_endpoints_are_declared_vertices=source_id in vertices and target_id in vertices,
                start_arrow=style.get('startArrow'),end_arrow=style.get('endArrow')))
        record=dict(id=page.get('id'),name=page.get('name'),vertices=len(vertices),edges=len(edges),
            bound_edges=sum(e['both_endpoints_are_declared_vertices'] for e in edges),bindings=edges)
        if include_cells:
            record['cells']=[dict(id=key,attributes=dict(cell.attrib),label_present=bool(labels[key]),
                geometry=dict(cell.find('mxGeometry').attrib) if cell.find('mxGeometry') is not None else None,
                geometry_children=len(cell.find('mxGeometry')) if cell.find('mxGeometry') is not None else 0)
                for key,cell in cells.items()]
        pages.append(record)
    if not pages:raise ValueError('No authoring pages')
    return dict(pages=pages,foreign_objects=len(root.findall('.//{http://www.w3.org/2000/svg}foreignObject')))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selection',type=Path,default=Path('data/source-oracle-feasibility-selection.json'))
    parser.add_argument('--cache',type=Path,default=Path('.cache/label-source-audit'))
    parser.add_argument('--output',type=Path,default=Path('artifacts/source-oracle-feasibility.json'))
    parser.add_argument('--ca-file',type=Path)
    parser.add_argument('--offline',action='store_true')
    args=parser.parse_args();selection=json.loads(args.selection.read_text());records=[]
    args.cache.mkdir(parents=True,exist_ok=True)
    for entry in selection['cases']:
        name=entry['id']+'.svg';file=args.cache/name
        if file.exists():
            with file.open('rb') as cached:raw=cached.read(LIMIT+1)
        elif args.offline:raise ValueError('Missing frozen source cache: '+name)
        else:
            if not entry['source_url'].startswith('https://raw.githubusercontent.com/'):
                raise ValueError('This bounded acquisition probe only fetches pinned raw GitHub sources')
            with urllib.request.urlopen(entry['source_url'],timeout=30,context=ssl.create_default_context(cafile=str(args.ca_file) if args.ca_file else None)) as response:
                raw=response.read(LIMIT+1)
        if len(raw)>LIMIT:raise ValueError('SVG exceeds source budget')
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        if blob!=entry['git_blob']:raise ValueError('Pinned original source Git blob mismatch: '+name)
        if not file.exists():file.write_bytes(raw)
        reference=graph_reference(raw.decode('utf-8'))
        records.append(dict(id=entry['id'],source_url=entry['source_url'],git_blob=blob,
            source_sha256=hashlib.sha256(raw).hexdigest(),foreign_objects=reference['foreign_objects'],
            pages=[{key:value for key,value in page.items() if key!='bindings'} for page in reference['pages']],
            separately_human_reviewed=False))
    report=dict(schema_version=1,kind='external-source-reference-feasibility',selection=str(args.selection),
        selection_policy=selection['selection_policy'],records=records,
        limitations=['Source-declared bindings only, not human reannotation or verified author intent',
            'Source/target ordering is not semantic direction; missing arrow styles require renderer defaults',
            'No geometry-to-cell grounding, label recovery, SVG editing support or accuracy measured',
            'Remove authoring payload and semantic identifiers before any geometry-only recovery; retain oracle separately',
            'These inspected feasibility cases are development data, not an untouched holdout'])
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
