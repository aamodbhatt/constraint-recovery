// External development fixtures are regression cases, not a held-out benchmark.
const fs=require('node:fs/promises'),path=require('node:path'),os=require('node:os');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const {main:runPilot}=require('./run_native_pilot.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
function check(ok,message){if(!ok)throw Error(message);}
(async()=>{
  const report=await runPilot();
  check(report.figures===5&&report.planned_move_requests===10,'Pilot denominator changed');
  check(report.complete_sequences===3&&report.accepted_move_requests===6&&report.checked_bounds_refusals===3,'Native development behavior regressed');
  check(report.controls.node_only.accepted===0&&report.controls.translate_only.accepted===1,'Direct-control behavior changed');
  check(/protected object|uncertain relation/.test(report.records.find(r=>r.id==='distill-rnn-memory').steps[0].reason),'Unresolved memory interpretation was silently accepted');
  check(/mid-marker/.test(report.records.find(r=>r.id==='distill-graph-tasks').steps[0].reason),'Mid-marker rerouting was silently accepted');
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'native-pilot-check-')),browser=await chromium.launch({headless:true});
  const mutations={};
  try{
    for(const [name,id,location,attribute,value,expected] of [
      ['separate_head_pose','distill-rnn-basic','svg/g[29]/path[1]','transform','translate(1 0)',/rigid\/protected pose|relative pose/],
      ['carried_curve_geometry','distill-standard-networks','svg/g[3]/path[7]','d','M 45 20 L 60 20',/Protected source/],
      ['editor_metadata','distill-standard-networks','svg/namedview[1]','pagecolor','#ff0000',/Protected source/],
    ]){
      const folder=path.join(root,'artifacts/native-pilot',id),candidate=path.join(temp,name+'.svg'),after=path.join(temp,name+'.json');
      const change=spawnSync(python,['-c',
        'import sys,xml.etree.ElementTree as E; from constraint_recovery.static_svg import parse_static,elements; '+
        'r=parse_static(open(sys.argv[1]).read()); e=elements(r)[sys.argv[3]]; e.set(sys.argv[4],sys.argv[5]); '+
        'E.register_namespace("","http://www.w3.org/2000/svg"); open(sys.argv[2],"w").write(E.tostring(r,encoding="unicode"))',
        path.join(folder,'step-1.svg'),candidate,location,attribute,value],
        {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
      check(change.status===0,change.stderr);
      await fs.writeFile(after,JSON.stringify(await measureSvg(browser,await fs.readFile(candidate,'utf8'),{styleDetails:true,maxPrimitives:500})));
      const result=spawnSync(python,['-m','constraint_recovery.compound','verify','--source',path.join(root,'data/native-pilot/original',id+'.svg'),
        '--measurements',path.join(folder,'direct-before.json'),'--manifest',path.join(root,'data/native-pilot/annotations',id+'.agent.json'),
        '--moves',path.join(folder,'step-1.moves.json'),'--candidate',candidate,'--after',after,'--report',path.join(temp,'report.json'),'--state',path.join(temp,'state.json')],
        {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
      check(result.status===2&&expected.test(result.stderr),'Damaged native candidate not rejected correctly: '+name+' '+result.stderr);
      mutations[name]=true;
    }
    await fs.writeFile(path.join(root,'artifacts/native-pilot-check.json'),JSON.stringify({passed:true,damaged_candidates_rejected:mutations,scope:'Frozen external development regressions under agent-reviewed assumptions; not independent recovery accuracy.'},null,2)+'\n');
    console.log(JSON.stringify({passed:true,damaged_candidates_rejected:mutations}));
  }finally{await browser.close();await fs.rm(temp,{recursive:true,force:true});}
})().catch(e=>{console.error(e.message);process.exit(1);});
