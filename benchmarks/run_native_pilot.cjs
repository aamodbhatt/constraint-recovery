// Fixed requests and direct-edit controls; every selected figure stays visible.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function worker(args){
  const r=spawnSync(python,args,{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:90000,maxBuffer:2000000});
  if(![0,2].includes(r.status))throw Error(r.stderr||String(r.error)||'Worker failed unexpectedly');
  return {accepted:r.status===0,returncode:r.status,reason:r.status===0?null:(r.stderr||r.stdout).trim()};
}
async function main(){
  const selectionFile=path.join(root,'data/native-pilot-selection.json');
  const selectionRaw=await fs.readFile(selectionFile),selection=JSON.parse(selectionRaw);
  const output=path.join(root,'artifacts/native-pilot');await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true}),records=[];
  try{
    for(const entry of selection.cases){
      const id=entry.id,folder=path.join(output,id);await fs.mkdir(folder,{recursive:true});
      const source=path.join(root,'data/native-pilot/original',id+'.svg');
      const annotation=path.join(root,'data/native-pilot/annotations',id+'.agent.json');
      const requestFile=path.join(root,'data/native-pilot/requests',id+'.json');
      const original=await fs.readFile(source,'utf8'),annotationRaw=await fs.readFile(annotation),requestRaw=await fs.readFile(requestFile);
      if(sha(original)!==entry.source_sha256)throw Error('Frozen source mismatch: '+id);
      const requests=JSON.parse(requestRaw),record={id,source_sha256:entry.source_sha256,annotation_sha256:sha(annotationRaw),
        request_sha256:sha(requestRaw),review_status:JSON.parse(annotationRaw).review.status,license:entry.license,steps:[]};
      const labels=JSON.parse(annotationRaw);
      record.annotation_coverage={total_primitives:labels.coverage.total_primitives,
        confirmed_role_primitives:labels.objects.filter(o=>o.status==='confirmed'&&o.role!=='unknown').reduce((n,o)=>n+o.parts.length,0),
        unresolved_primitives:labels.objects.filter(o=>o.status!=='confirmed'||o.role==='unknown').reduce((n,o)=>n+o.parts.length,0)+labels.coverage.unassigned_parts.length,
        confirmed_directed_edges:labels.relations.filter(r=>r.kind==='directed_edge'&&r.status==='confirmed').length,
        unresolved_relations:labels.relations.filter(r=>r.status!=='confirmed').length};
      let current=source,state=annotation,accepted=0;
      for(let i=0;i<requests.steps.length;i++){
        if(i>0&&accepted!==i){record.steps.push({step:i+1,attempted:false,accepted:false,reason:'Previous request declined; no invalid state reused'});continue;}
        const moves=path.join(folder,`step-${i+1}.moves.json`),svg=path.join(folder,`step-${i+1}.svg`);
        await fs.writeFile(moves,JSON.stringify(requests.steps[i])+'\n');
        const result=worker(['-m','constraint_recovery','edit-compound',current,i?'--constraints':'--annotation',state,'--moves',moves,'--output',svg]);
        const step={step:i+1,attempted:true,...result};
        if(result.accepted){
          const report=JSON.parse(await fs.readFile(svg.replace(/\.svg$/,'.report.json'),'utf8'));
          if(!report.passed||report.output_sha256!==sha(await fs.readFile(svg)))throw Error('Accepted report binding failed: '+id);
          step.checks=report;current=svg;state=svg.replace(/\.svg$/,'.compound.json');accepted++;
        }
        record.steps.push(step);
      }
      record.sequence_complete=accepted===requests.steps.length;
      // The impossible probe is scored as a bounds refusal only after a
      // supported edit sequence, not merely because any unsupported input fails.
      const impossibleMoves=path.join(folder,'impossible.moves.json'),impossibleSvg=path.join(folder,'impossible.svg');
      await fs.writeFile(impossibleMoves,JSON.stringify(requests.impossible)+'\n');
      record.impossible=worker(['-m','constraint_recovery','edit-compound',current,accepted?'--constraints':'--annotation',state,'--moves',impossibleMoves,'--output',impossibleSvg]);
      record.impossible.bounds_refusal_checked=record.sequence_complete&&!record.impossible.accepted&&/outside canvas/.test(record.impossible.reason||'');
      if(record.impossible.accepted)throw Error('Impossible request exported an SVG: '+id);
      // Fresh browser acquisition, direct node-only movement, then the same
      // checker against the same accepted objects and requested translations.
      const before=path.join(folder,'direct-before.json'),after=path.join(folder,'direct-after.json');
      await fs.writeFile(before,JSON.stringify(await measureSvg(browser,original,{styleDetails:true,maxPrimitives:500})));
      record.controls={};
      const moves=path.join(folder,'step-1.moves.json');
      for(const [name,flags] of [['node_only',[]],['translate_only',['--carry-edges']]]){
        const direct=path.join(folder,'unverified-'+name+'.svg');
        const control=worker([path.join(root,'benchmarks/native_direct_move.py'),'--source',source,'--before',before,'--annotation',annotation,'--moves',moves,'--output',direct,...flags]);
        if(control.accepted){
          const raw=await fs.readFile(direct,'utf8');
          await fs.writeFile(after,JSON.stringify(await measureSvg(browser,raw,{styleDetails:true,maxPrimitives:500})));
          record.controls[name]={generated:true,...worker(['-m','constraint_recovery.compound','verify','--source',source,'--measurements',before,
            '--manifest',annotation,'--moves',moves,'--candidate',direct,'--after',after,'--report',path.join(folder,name+'-check.json'),'--state',path.join(folder,name+'-state.json')])};
        }else record.controls[name]={generated:false,...control};
      }
      records.push(record);
      console.log(JSON.stringify({id,accepted_steps:accepted,sequence_complete:record.sequence_complete,controls:record.controls}));
    }
    const implementation_files={};
    for(const file of ['src/constraint_recovery/compound.py','src/constraint_recovery/static_svg.py','src/constraint_recovery/annotation.py',
      'src/constraint_recovery/routing.py','src/constraint_recovery/check.py','src/constraint_recovery/channel.py','src/constraint_recovery/edge_check.py','src/constraint_recovery/assets/browser_geometry.cjs',
      'src/constraint_recovery/assets/compound_edit.cjs','benchmarks/native_direct_move.py','benchmarks/run_native_pilot.cjs']){
      implementation_files[file]=sha(await fs.readFile(path.join(root,file)));
    }
    const report={schema_version:1,selection:'data/native-pilot-selection.json',selection_sha256:sha(selectionRaw),browser:browser.version(),implementation_files,
      figures:records.length,authoring_origin_clusters:selection.article_clusters,agent_annotations:records.length,independent_human_annotations:0,
      planned_move_requests:records.reduce((n,r)=>n+r.steps.length,0),
      attempted_move_requests:records.reduce((n,r)=>n+r.steps.filter(s=>s.attempted).length,0),
      accepted_move_requests:records.reduce((n,r)=>n+r.steps.filter(s=>s.accepted).length,0),
      complete_sequences:records.filter(r=>r.sequence_complete).length,
      checked_bounds_refusals:records.filter(r=>r.impossible.bounds_refusal_checked).length,
      controls:Object.fromEntries(['node_only','translate_only'].map(name=>[name,{planned:records.length,generated:records.filter(r=>r.controls[name].generated).length,accepted:records.filter(r=>r.controls[name].accepted).length}])),
      scope:'Conditional editing of fixed author-published SVGs under explicit agent-reviewed assumptions. Development pilot with two authoring origins; not independent recovery accuracy, human intent, pixel identity, learned advantage or a representative sample.',
      records};
    await fs.writeFile(path.join(output,'report.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(Object.fromEntries(Object.entries(report).filter(([k])=>k!=='records')),null,2));
    return report;
  }finally{await browser.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exit(1);});
module.exports={main};
