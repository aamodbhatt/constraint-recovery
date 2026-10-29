// Same native source, accepted relationships and requests; vary routing only.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function run(args){
  const result=spawnSync(python,args,{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:90000});
  if(result.status!==0)throw Error(result.stderr||result.stdout||String(result.error));
}
(async()=>{
  const id='distill-rnn-read',source=path.join(root,'data/native-pilot/original',id+'.svg');
  const annotation=path.join(root,'data/native-pilot/annotations',id+'.agent.json');
  const requestFile=path.join(root,'data/native-pilot/requests',id+'.json'),requests=JSON.parse(await fs.readFile(requestFile,'utf8'));
  const folder=path.join(root,'artifacts/parallel-routing');await fs.mkdir(folder,{recursive:true});
  const modes={};
  for(const mode of ['visibility','channel']){
    let current=source,state=annotation;const steps=[];
    for(let i=0;i<requests.steps.length;i++){
      const moves=path.join(folder,mode+'-'+(i+1)+'.moves.json'),output=path.join(folder,mode+'-'+(i+1)+'.svg');
      await fs.writeFile(moves,JSON.stringify(requests.steps[i])+'\n');
      run(['-m','constraint_recovery','edit-compound',current,i?'--constraints':'--annotation',state,'--moves',moves,'--routing',mode,'--output',output]);
      const checks=JSON.parse(await fs.readFile(output.replace(/\.svg$/,'.report.json'),'utf8'));
      if(!checks.passed||checks.rerouted_connectors!==7||checks.parallel_shaft_checks.length!==1)throw Error('Incomplete parallel-routing check');
      const quality=checks.parallel_shaft_checks[0];
      if(mode==='channel'&&quality.contact_pairs!==0)throw Error('Ordered candidate has external shaft contacts');
      if(mode==='visibility'&&quality.shared_segment_pairs<1)throw Error('Visibility control no longer exercises the shared-segment failure');
      steps.push({step:i+1,input_sha256:checks.input_sha256,output_sha256:checks.output_sha256,moved_primitives:checks.moved_primitives,
        rerouted_connectors:checks.rerouted_connectors,shaft_contacts:quality});
      current=output;state=output.replace(/\.svg$/,'.compound.json');
    }
    modes[mode]={accepted_steps:steps.length,steps};
  }
  // Challenge the checker with a visibility output while reporting a channel
  // preference. Contact evidence must come from the actual exported segments.
  const browser=await chromium.launch({headless:true});
  try{
    const before=path.join(folder,'before.json');
    await fs.writeFile(before,JSON.stringify(await measureSvg(browser,await fs.readFile(source,'utf8'),{styleDetails:true,maxPrimitives:500})));
    const checked=path.join(folder,'independent-check.json');
    run(['-m','constraint_recovery.compound','verify','--source',source,'--measurements',before,'--manifest',annotation,
      '--moves',path.join(folder,'visibility-1.moves.json'),'--candidate',path.join(folder,'visibility-1.svg'),
      '--after',path.join(folder,'visibility-1.measurements.json'),'--routing','channel','--report',checked,'--state',path.join(folder,'independent-state.json')]);
    const observed=JSON.parse(await fs.readFile(checked,'utf8')).parallel_shaft_checks[0];
    if(JSON.stringify(observed)!==JSON.stringify(modes.visibility.steps[0].shaft_contacts))throw Error('Checker trusted the routing label instead of serialized geometry');
  }finally{await browser.close();}
  const report={schema_version:1,figure:id,source_sha256:sha(await fs.readFile(source)),annotation_file_sha256:sha(await fs.readFile(annotation)),
    request_file_sha256:sha(await fs.readFile(requestFile)),review_status:'agent-reviewed',independent_human_annotations:0,modes,
    checker_uses_serialized_geometry_not_routing_label:true,
    scope:'Paired development diagnostic on one native figure and two frozen moves. Classical channel-order constraints, not a new routing algorithm or learned advantage. Checks shaft centerlines outside accepted endpoint envelopes; excludes stroke/head extents, unchanged edges and intended topology inside those envelopes.'};
  await fs.writeFile(path.join(folder,'report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report,null,2));
})().catch(e=>{console.error(e.message);process.exit(1);});
