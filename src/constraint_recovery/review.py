"""Portable local endpoint review UI, rendered from safe normalized geometry."""
from copy import deepcopy
import json
import xml.etree.ElementTree as ET
from .model import Diagram,Node
from .svg import NS,render_svg


def render_review(observations):
    nodes=[Node(**deepcopy(n)) for n in observations["nodes"]]
    for n in nodes:
        n.fill,n.stroke="#eef3fb","#30445f"
    svg=ET.fromstring(render_svg(Diagram(observations["width"],observations["height"],nodes,[])))
    for i,element in enumerate(svg.iter()):
        if element.get("id"):
            if element.tag==f"{{{NS}}}rect":
                element.set("data-node",element.get("id"))
            element.set("id",f"cr-review-svg-{i}")
    marker=svg.find(f"{{{NS}}}defs/{{{NS}}}marker").get("id")
    for i,edge in enumerate(observations["connectors"]):
        line=ET.Element(f"{{{NS}}}polyline",{"points":" ".join(f"{x},{y}" for x,y in edge["points"]),
              "fill":"none","stroke":"#617591","stroke-width":"2","marker-end":f"url(#{marker})","data-edge":edge["id"]})
        svg.insert(1+i,line)
        for role in ["source","target"]:
            x,y=edge[role]["point"]
            svg.append(ET.Element(f"{{{NS}}}circle",{"cx":str(x),"cy":str(y),"r":"4","fill":"#c15b28","data-endpoint":edge["id"]+":"+role}))
    svg.set("width","100%")
    svg.set("height","100%")
    payload=json.dumps(observations).replace("<","\\u003c")
    return '''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Review recovered attachments</title>
<style>
*{box-sizing:border-box}body{margin:0;font:15px system-ui;background:#f4f6fa;color:#172c47}main{max-width:1480px;margin:auto;padding:32px}small{color:#586b83;letter-spacing:.06em}h1{font-size:30px;margin:12px 0}p{line-height:1.6;max-width:900px}.workspace{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(330px,1fr);gap:24px;margin-top:28px}.canvas,.panel{background:white;border:1px solid #dbe3ee;border-radius:12px;padding:24px}.canvas{height:650px;position:sticky;top:24px}.canvas svg{width:100%;height:100%}.canvas text,.canvas circle{pointer-events:none}.canvas rect{cursor:pointer;transition:fill .1s}.canvas rect.selected{fill:#cde9dd;stroke:#207451;stroke-width:3}.canvas polyline.active{stroke:#c15b28;stroke-width:3}.edge{padding:16px 0;border-bottom:1px solid #e5eaf2}.edge h2{font-size:16px;margin:0 0 12px}label{display:block;margin:12px 0 4px;font-weight:600}select{display:block;width:100%;padding:10px;border:1px solid #b9c7da;background:white;border-radius:6px;color:#172c47}.reason{font-size:12px;color:#586b83;margin:5px 0 12px;overflow-wrap:anywhere}button{padding:12px 18px;border:0;border-radius:6px;background:#244e7d;color:white;font:600 14px system-ui;cursor:pointer}button:disabled{opacity:.45;cursor:default}#status{font-weight:600;margin:16px 0}.note{color:#586b83;font-size:13px}.controls{position:sticky;bottom:0;background:white;padding-top:12px}.commands{white-space:pre-wrap;font-size:12px;line-height:1.6;background:#f4f6fa;padding:14px;overflow-wrap:anywhere}@media(max-width:850px){.workspace{grid-template-columns:1fr}.canvas{position:static;height:420px}}
</style><main><small>LOCAL ATTACHMENT REVIEW · NO API CALLS</small><h1>Which nodes do these arrows connect?</h1>
<p>Inspect each source and target. Focus a selector, then click a node in the diagram or choose it from the list. Orange dots mark observed endpoints. Distances are geometric clues; they do not establish intent.</p>
<div class="workspace"><section class="canvas" aria-label="Normalized diagram preview">'''+ET.tostring(svg,encoding="unicode")+'''</section>
<section class="panel"><div id="rows"></div><div class="controls"><div id="status" role="status"></div><button id="download" disabled>Download attachment choices</button><p class="note">This normalized preview simplifies styling. The downloaded file is bound to this exact source SVG. Choices remain local.</p></div>
<pre class="commands">Apply choices with:
constraint-recovery recover INPUT.svg --attachments attachment-overrides.json --output recovered.json

For broader static SVGs, also pass --source-preserving.</pre></section></div>
<p class="note">A review records user-supplied relationships, not independent ground truth. Model scores, when present in the companion JSON, are uncalibrated.</p></main>
<script type="application/json" id="observations">'''+payload+'''</script><script>
const data=JSON.parse(document.getElementById('observations').textContent);
const selects=new Map();let focused=null;
const rows=document.getElementById('rows');
function key(edge,role){return JSON.stringify([edge,role]);}
function refresh(){let missing=0,invalid=0;
 for(const edge of data.connectors){const a=selects.get(key(edge.id,'source')).value,b=selects.get(key(edge.id,'target')).value;if(!a)missing++;if(!b)missing++;if(a&&a===b)invalid++;}
 document.getElementById('status').textContent=missing?`${missing} endpoint choice${missing===1?'':'s'} remaining`:invalid?`${invalid} arrow${invalid===1?'':'s'} connects a node to itself; review again`:'All arrow endpoints selected';
 document.getElementById('download').disabled=missing>0||invalid>0;
 for(const rect of document.querySelectorAll('.canvas rect'))rect.classList.toggle('selected',focused&&rect.dataset.node===focused.value);
 for(const line of document.querySelectorAll('.canvas polyline'))line.classList.toggle('active',focused&&line.dataset.edge===focused.dataset.edge);
}
for(const edge of data.connectors){const row=document.createElement('div');row.className='edge';const title=document.createElement('h2');title.textContent=edge.id;row.append(title);
 for(const role of ['source','target']){const label=document.createElement('label');label.textContent=role==='source'?'Source node':'Target node';const select=document.createElement('select');select.dataset.edge=edge.id;select.setAttribute('aria-label',edge.id+' '+role);const blank=document.createElement('option');blank.value='';blank.textContent='Choose a node';select.append(blank);
 for(const candidate of edge[role].candidates){const n=data.nodes.find(n=>n.id===candidate.node_id);const option=document.createElement('option');option.value=n.id;option.textContent=`${n.id}${n.label?' · '+n.label:''} · ${candidate.boundary_distance.toFixed(1)} units`;select.append(option);}
 select.value=edge[role].selected||'';select.addEventListener('focus',()=>{focused=select;refresh();});select.addEventListener('change',refresh);label.append(select);row.append(label);const reason=document.createElement('div');reason.className='reason';reason.textContent=edge[role].reason;row.append(reason);selects.set(key(edge.id,role),select);if(!focused&&!select.value)focused=select;
 }rows.append(row);}
for(const rect of document.querySelectorAll('.canvas rect')){rect.addEventListener('click',()=>{if(focused){focused.value=rect.dataset.node;refresh();}});}
document.getElementById('download').addEventListener('click',()=>{const decisions=Object.fromEntries(data.connectors.map(e=>[e.id,{source:selects.get(key(e.id,'source')).value,target:selects.get(key(e.id,'target')).value}]));const output={schema_version:1,kind:'attachment-overrides',source_sha256:data.source_sha256,decisions};const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)+'\\n'],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='attachment-overrides.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
refresh();
</script>'''
