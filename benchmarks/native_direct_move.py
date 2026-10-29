"""Direct source-edit control: move reviewed node parts, leave arrows untouched.

Shares only the affine leaf writer with the editor. It does not recover objects,
place nodes, reroute connectors or call the edit planner. Outputs are unverified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from constraint_recovery.annotation import validate_annotation
from constraint_recovery.compound import translate_leaf
from constraint_recovery.model import DiagramError
from constraint_recovery.static_svg import parse_static,elements
from constraint_recovery.svg import NS


def main():
    parser=argparse.ArgumentParser()
    for flag in ['source','before','annotation','moves','output']:
        parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--carry-edges',action='store_true',help='Also translate connectors whose two accepted endpoint objects move identically')
    args=parser.parse_args()
    try:
        source=args.source.read_bytes().decode('utf-8');root=parse_static(source)
        measured=json.loads(args.before.read_text());annotation=json.loads(args.annotation.read_text());moves=json.loads(args.moves.read_text())
        validate_annotation(annotation,hashlib.sha256(source.encode()).hexdigest(),measured)
        mapped=elements(root);parts={p['location']:p for p in measured['primitives']}
        objects={o['id']:o for o in annotation['objects']}
        for key,delta in moves.items():
            if key not in objects or objects[key]['role']!='node' or objects[key]['status']!='confirmed':
                raise DiagramError('Direct control requires an explicitly confirmed node')
            for location in objects[key]['parts']:
                translate_leaf(mapped[location],parts[location],delta)
        if args.carry_edges:
            for relation in annotation['relations']:
                if relation['kind']!='directed_edge' or relation['status']!='confirmed' or not relation.get('connector'):
                    continue
                a,b=relation['objects'];delta=moves.get(a,[0,0])
                if delta==[0,0] or delta!=moves.get(b,[0,0]):
                    continue
                for location in objects[relation['connector']]['parts']:
                    translate_leaf(mapped[location],parts[location],delta)
        ET.register_namespace('',NS)
        args.output.write_text(ET.tostring(root,encoding='unicode')+'\n')
        return 0
    except (DiagramError,ValueError,KeyError,OSError,TypeError) as error:
        print(str(error))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
