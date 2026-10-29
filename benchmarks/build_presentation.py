"""Build presentation assets from actual accepted example artifacts."""
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).parents[1]
NS="http://www.w3.org/2000/svg"


def cover():
    ET.register_namespace("",NS)
    root=ET.Element(f"{{{NS}}}svg",{"viewBox":"0 0 1280 640","width":"1280","height":"640","role":"img","aria-label":"An authored source diagram and its verified portrait edit with an explicit branch"})
    def element(tag,**attrs):
        return ET.SubElement(root,f"{{{NS}}}{tag}",{k.replace("_","-"):str(v) for k,v in attrs.items()})
    def text(value,x,y,size=16,fill="#50625b",weight=400):
        element("text",x=x,y=y,font_size=size,fill=fill,font_weight=weight,font_family="Arial, sans-serif").text=value
    element("rect",width=1280,height=640,rx=22,fill="#f3f6f2")
    element("rect",x=1,y=1,width=1278,height=638,rx=21,fill="none",stroke="#dce4db")
    text("Constraint recovery",40,61,32,"#19382c",600)
    text("Structural edits to scientific SVGs",40,92,17)
    text("LOCAL RESEARCH PROTOTYPE",982,57,12,"#668073",600)
    for x,heading,sub,file,prefix in [
        (36,"01  /  SOURCE","Four stages, three directed relationships","00-original.preview.svg","source-"),
        (652,"02  /  ACCEPTED EDIT","Portrait layout and an explicit branch","04-edited.preview.svg","edited-")]:
        element("rect",x=x,y=124,width=592,height=444,rx=15,fill="#fff",stroke="#dce4db")
        text(heading,x+24,158,13,"#28684d",600)
        text(sub,x+24,185,16,"#293f35")
        nested=ET.parse(ROOT/"docs/demo/sequence"/file).getroot()
        ids={e.get("id"):prefix+e.get("id") for e in nested.iter() if e.get("id")}
        for e in nested.iter():
            for key,value in list(e.attrib.items()):
                if key=="id":
                    e.set(key,ids[value])
                else:
                    for old,new in ids.items():
                        value=value.replace("url(#"+old+")","url(#"+new+")")
                    e.set(key,value)
        nested.attrib.update({"x":str(x+24),"y":"206","width":"544","height":"336","preserveAspectRatio":"xMidYMid meet"})
        root.append(nested)
    for value,x in [("SVG",48),("→",104),("Reviewed relationships",144),("→",340),("Constrained edit",380),("→",530),("Independent checks",570)]:
        text(value,x,610,13,"#19382c" if value=="SVG" else "#50625b",600 if value=="SVG" else 400)
    text("Authored example · accepted graph, not inferred intent",903,610,11)
    (ROOT/"docs/assets/readme-cover.svg").write_text(ET.tostring(root,encoding="unicode")+"\n")


def evidence():
    folder=ROOT/"docs/demo/sequence"
    saved=json.loads((folder/"sequence.json").read_text())
    original=(folder/"00-original.svg").read_bytes()
    entries=[{"step":0,"nodes":4,"edges":3,"font":16,"canvas":[1200,900],"file":"00-original.svg", "sha256":hashlib.sha256(original).hexdigest(),"accepted":True}]
    width,height,font=1200,900,16
    for r in saved["records"]:
        request=r["request"]
        width,height,font=request.get("width",width),request.get("height",height),request.get("font_size",font)
        step=r["step"]
        entries.append({"step":step,"nodes":5 if step>=4 else 4,"edges":4 if step>=4 else 3,"font":font,
                        "canvas":[width,height],"file":f"{min(step,6):02d}-edited.svg","sha256":r.get("output_sha256"),
                        "accepted":bool(r.get("accepted")),"request":request,"seconds":r.get("seconds"),
                        "certificate":r.get("conflict_witness")})
    (folder/"evidence.js").write_text("window.SEQUENCE_EVIDENCE = "+json.dumps(entries,indent=2)+";\n")


if __name__=="__main__":
    cover();evidence()
