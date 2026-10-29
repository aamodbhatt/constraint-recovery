// End-to-end rigid-edit and rejection checks on an authored rich SVG.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
function cli(args,status=0){const r=spawnSync(python,['-m','constraint_recovery',...args],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:60000});if(r.status!==status)throw Error(r.stderr||r.stdout||String(r.error));return r;}
function check(value,message){if(!value)throw Error(message);}
(async()=>{const temp=await fs.mkdtemp(path.join(os.tmpdir(),'compound-integration-'));try{
  const source=path.join(root,'examples/compound.svg'),annotation=path.join(root,'examples/compound.annotation.agent.json');
  const first=path.join(temp,'first.svg');
  cli(['edit-compound',source,'--annotation',annotation,'--moves',path.join(root,'examples/compound-moves.json'),'--output',first]);
  const firstReport=JSON.parse(await fs.readFile(path.join(temp,'first.report.json'),'utf8'));
  check(firstReport.passed&&firstReport.moved_primitives===3&&firstReport.rerouted_connectors===1,'First compound edit did not pass');
  const nextMoves=path.join(temp,'next.json');await fs.writeFile(nextMoves,JSON.stringify({decoder:[20,-40]}));
  const second=path.join(temp,'second.svg');
  cli(['edit-compound',first,'--constraints',path.join(temp,'first.compound.json'),'--moves',nextMoves,'--output',second]);
  const state=JSON.parse(await fs.readFile(path.join(temp,'second.compound.json'),'utf8'));
  const originalAnnotation=JSON.parse(await fs.readFile(annotation,'utf8'));
  check(state.history.length===2,'Derived edit history was lost');
  check(state.annotation.source_sha256===originalAnnotation.source_sha256,'Original annotation was falsely rebound');
  check(state.source_sha256===crypto.createHash('sha256').update(await fs.readFile(second)).digest('hex'),'Output binding mismatch');
  const badMoves=path.join(temp,'bad.json');await fs.writeFile(badMoves,JSON.stringify({decoder:[-1000,0]}));
  const prior=await fs.readFile(second,'utf8');
  cli(['edit-compound',first,'--constraints',path.join(temp,'first.compound.json'),'--moves',badMoves,'--output',second],2);
  check(await fs.readFile(second,'utf8')===prior,'Rejected edit overwrote the previous output');
  // A CSS rule activated by inserted transform attributes must cause rejection.
  const raw=(await fs.readFile(source,'utf8')).replace('</svg>','<style>[transform]{opacity:.5}</style></svg>');
  const probe=path.join(temp,'style.svg'),probeAnnotation=path.join(temp,'style.annotation.json');
  await fs.writeFile(probe,raw);originalAnnotation.source_sha256=crypto.createHash('sha256').update(raw).digest('hex');
  await fs.writeFile(probeAnnotation,JSON.stringify(originalAnnotation));
  const declined=path.join(temp,'declined.svg');
  const failure=cli(['edit-compound',probe,'--annotation',probeAnnotation,'--moves',path.join(root,'examples/compound-moves.json'),'--output',declined],2);
  check(/styling changed/.test(failure.stderr),'CSS mutation failed for an unexpected reason: '+failure.stderr);
  check(!await fs.stat(declined).then(()=>true,()=>false),'Style failure exported an SVG');
  // Exercise the checker directly with independently measured damaged candidates.
  const browser=await chromium.launch({headless:true});
  const mutationChecks={};
  try{
    const before=path.join(temp,'before.json'),after=path.join(temp,'after.json'),candidate=path.join(temp,'damaged.svg');
    const sourceText=await fs.readFile(source,'utf8'),valid=await fs.readFile(first,'utf8');
    await fs.writeFile(before,JSON.stringify(await measureSvg(browser,sourceText,{styleDetails:true,maxPrimitives:500})));
    const variants=[
      ['text_change',s=>s.replace('structured output','corrupted output'),/Protected source/],
      ['definition_change',s=>s.replace('stop-color="#eaf2e8"','stop-color="#ff0000"'),/Protected source/],
      ['wrong_rigid_pose',s=>s.replace(/(<rect\b[^>]*id="decoder-shape"[^>]*transform=")([^"]+)(")/,
        (_,a,b,c)=>a+'translate(3 0) '+b+c),/rigid\/protected pose|relative pose|styling changed/],
      ['detached_arrow',s=>s.replace(/(<path\b[^>]*id="encoded-decoded"[^>]*d=")([^"]+)(")/,
        (_,a,b,c)=>a+b.replace(/^M\s+[-\d.e+]+/,'M 250')+c),/detached/],
    ];
    for(const [name,damage,expected] of variants){
      const changed=damage(valid);check(changed!==valid,'Mutation did not modify candidate: '+name);
      await fs.writeFile(candidate,changed);
      await fs.writeFile(after,JSON.stringify(await measureSvg(browser,changed,{styleDetails:true,maxPrimitives:500})));
      const r=spawnSync(python,['-m','constraint_recovery.compound','verify','--source',source,'--measurements',before,
        '--manifest',annotation,'--moves',path.join(root,'examples/compound-moves.json'),'--candidate',candidate,
        '--after',after,'--report',path.join(temp,'mutation-report.json'),'--state',path.join(temp,'mutation-state.json')],
        {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
      check(r.status===2&&expected.test(r.stderr),'Mutation was not rejected as expected: '+name+' '+r.stderr);
      mutationChecks[name]=true;
    }
  }finally{await browser.close();}
  // Authored affine variants exercise parent conjugation, including reflection.
  const affineCases={};
  for(const [name,matrix,delta] of [
    ['skew_nonuniform','0.8 .08 .1 .85 0 0',[-50,70]],
    ['reflected','-0.8 .08 .1 .85 650 0',[40,80]],
  ]){
    const variantSource=path.join(temp,name+'.svg'),variantAnnotation=path.join(temp,name+'.annotation.json');
    const generate=spawnSync(python,['-c',
      'import sys,json,hashlib,xml.etree.ElementTree as E; from constraint_recovery.static_svg import parse_static; '+
      'r=parse_static(open(sys.argv[1]).read()); g=E.Element("{http://www.w3.org/2000/svg}g",{"transform":"matrix("+sys.argv[4]+")"}); '+
      'children=list(r); r[:]=[]; g.extend(children); r.append(g); E.register_namespace("","http://www.w3.org/2000/svg"); '+
      's=E.tostring(r,encoding="unicode"); open(sys.argv[2],"w").write(s); a=json.load(open(sys.argv[3])); '+
      'a["source_sha256"]=hashlib.sha256(s.encode()).hexdigest(); '+
      '[(o.update(parts=[p.replace("svg/","svg/g[0]/",1) for p in o["parts"]])) for o in a["objects"]]; '+
      'json.dump(a,open(sys.argv[5],"w"))',source,variantSource,annotation,matrix,variantAnnotation],
      {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
    check(generate.status===0,generate.stderr);
    const variantMoves=path.join(temp,name+'.moves.json');await fs.writeFile(variantMoves,JSON.stringify({decoder:delta}));
    cli(['edit-compound',variantSource,'--annotation',variantAnnotation,'--moves',variantMoves,'--output',path.join(temp,name+'-edited.svg')]);
    affineCases[name]=true;
  }
  await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
  const report={passed:true,first_edit:firstReport,repeated_edit:true,original_annotation_preserved:true,output_binding:true,
    rejected_request_preserves_existing_output:true,css_triggered_style_change_rejected:true,damaged_candidates_rejected:mutationChecks,
    affine_parent_cases:affineCases,
    scope:'Authored agent-reviewed fixture with rotated card, symbol instance and bold text. No external recovery or human annotation claim.'};
  await fs.writeFile(path.join(root,'artifacts/compound-integration.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{await fs.rm(temp,{recursive:true,force:true});}})().catch(e=>{console.error(e.message);process.exit(1);});
