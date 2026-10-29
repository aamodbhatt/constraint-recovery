// Recheck the bytes actually distributed in the public demo, independently of
// regenerated artifacts. Byte equality with a new export is not required: local
// font/browser geometry can differ while the saved edit still verifies.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {isDeepStrictEqual}=require('node:util');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function check(ok,message){if(!ok)throw Error(message);}
(async()=>{
  const browser=await chromium.launch({headless:true}),temp=await fs.mkdtemp(path.join(os.tmpdir(),'published-svg-check-'));
  const measured=new Map(),records=[],annotationDigests=new Map();
  async function geometry(file){
    const source=await fs.readFile(file,'utf8'),digest=sha(source);
    if(!measured.has(digest)){
      const output=path.join(temp,digest+'.json');
      await fs.writeFile(output,JSON.stringify(await measureSvg(browser,source,{styleDetails:true,maxPrimitives:500})));
      measured.set(digest,output);
    }
    return measured.get(digest);
  }
  try{
    const selection=JSON.parse(await fs.readFile(path.join(root,'data/native-pilot-selection.json'),'utf8'));
    const saved=JSON.parse(await fs.readFile(path.join(root,'results/native-pilot.json'),'utf8'));
    const exports=path.join(root,'docs/demo/native-pilot/exports');
    for(const entry of selection.cases){
      const outcome=saved.records.find(r=>r.id===entry.id);
      if(!outcome.sequence_complete)continue;
      const modes=entry.id==='distill-rnn-read'?['channel','visibility']:['channel'];
      const source=path.join(root,'data/native-pilot/original',entry.id+'.svg');
      const annotation=path.join(root,'data/native-pilot/annotations',entry.id+'.agent.json');
      const requests=JSON.parse(await fs.readFile(path.join(root,'data/native-pilot/requests',entry.id+'.json'),'utf8'));
      check(sha(await fs.readFile(source))===entry.source_sha256,'Published source differs from frozen input');
      check(sha(await fs.readFile(annotation))===outcome.annotation_sha256,'Annotation file changed since the saved evaluation');
      for(const mode of modes){
        let current=source,manifest=annotation;
        for(let step=1;step<=requests.steps.length;step++){
          const stem=path.join(exports,entry.id+(mode==='visibility'?'-visibility':'')+'-step-'+step);
          const candidate=stem+'.svg',stored=JSON.parse(await fs.readFile(stem+'.report.json','utf8'));
          check(stored.passed&&stored.input_sha256===sha(await fs.readFile(current))&&stored.output_sha256===sha(await fs.readFile(candidate)),'Published report/source/output binding mismatch: '+stem);
          const state=JSON.parse(await fs.readFile(stem+'.compound.json','utf8'));
          check(state.source_sha256===stored.output_sha256&&state.annotation.source_sha256===entry.source_sha256,'Published derived state was rebound incorrectly');
          check(state.history.length===step&&state.history.at(-1).output_sha256===stored.output_sha256,'Published history is incomplete');
          const moves=path.join(temp,'moves.json');await fs.writeFile(moves,JSON.stringify(requests.steps[step-1]));
          const report=path.join(temp,'checked.json');
          const result=spawnSync(python,['-m','constraint_recovery.compound','verify','--source',current,'--measurements',await geometry(current),
            '--manifest',manifest,'--moves',moves,'--candidate',candidate,'--after',await geometry(candidate),'--routing',mode,
            '--report',report,'--state',path.join(temp,'state.json')],
            {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
          check(result.status===0,'Published SVG failed fresh checks: '+path.basename(candidate)+' '+result.stderr);
          const checked=JSON.parse(await fs.readFile(report,'utf8'));
          check(isDeepStrictEqual(state,JSON.parse(await fs.readFile(path.join(temp,'state.json'),'utf8'))),
            'Published derived state differs from independently reconstructed history/annotation: '+path.basename(candidate));
          if(!annotationDigests.has(entry.id))annotationDigests.set(entry.id,checked.annotation_sha256);
          check(checked.annotation_sha256===annotationDigests.get(entry.id)&&checked.accepted_review.status==='agent-reviewed','Original agent annotation provenance changed');
          for(const key of ['moved_primitives','rerouted_connectors','carried_connectors'])check(checked[key]===stored[key],'Published edit-count evidence changed');
          if(mode==='channel')check(checked.parallel_shaft_checks.every(g=>g.contact_pairs===0),'A published channel separation observation did not survive fresh measurement');
          if(mode==='visibility')check(checked.parallel_shaft_checks.some(g=>g.shared_segment_pairs>0),'Published visibility control lost its shared-segment diagnostic');
          records.push({file:path.relative(root,candidate),source_sha256:stored.input_sha256,output_sha256:stored.output_sha256,
            source_state_binding:true,full_derived_state_reconstructed:true,original_annotation_preserved:true,fresh_style_pose_attachment_checks:true,
            parallel_contacts:checked.parallel_shaft_checks.map(g=>g.contact_pairs)});
          current=candidate;manifest=stem+'.compound.json';
        }
      }
    }
    check(records.length===8,'Published export denominator changed');
    const report={passed:true,browser:browser.version(),published_svg_exports:records.length,unique_browser_measurements:measured.size,
      scope:'Fresh local browser checks of the eight public demo SVG bytes and their bound histories under the original agent-reviewed assumptions. Does not establish author intent, human review, pixel identity, stroke/head collision bounds or complete-figure topology.',records};
    await fs.writeFile(path.join(root,'artifacts/published-examples-check.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }finally{await browser.close();await fs.rm(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e.message);process.exit(1);});
