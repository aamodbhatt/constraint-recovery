// End-to-end rigid-edit and rejection checks on an authored rich SVG.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
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
  await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
  const report={passed:true,first_edit:firstReport,repeated_edit:true,original_annotation_preserved:true,output_binding:true,
    rejected_request_preserves_existing_output:true,css_triggered_style_change_rejected:true,
    scope:'Authored agent-reviewed fixture with rotated card, symbol instance and bold text. No external recovery or human annotation claim.'};
  await fs.writeFile(path.join(root,'artifacts/compound-integration.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
}finally{await fs.rm(temp,{recursive:true,force:true});}})().catch(e=>{console.error(e.message);process.exit(1);});
