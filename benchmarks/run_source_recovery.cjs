// Recovery receives numeric observations only; reference loading follows a
// persisted prediction hash. This is an input boundary, not an OS sandbox.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {isDeepStrictEqual}=require('node:util');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),executable=process.env.PYTHON||'python3';
const python=executable.includes(path.sep)?path.resolve(root,executable):executable;
const sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
function check(ok,message){if(!ok)throw Error(message);}
function worker(args,optional=false){
  const r=spawnSync(python,['-m','benchmarks.source_recovery',...args],{cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
  if(r.status===2&&optional)return {passed:false,reason:r.stderr.trim()};
  check(r.status===0,r.stderr||String(r.error));return {passed:true};
}
async function json(file){return JSON.parse(await fs.readFile(file,'utf8'));}
async function predict(folder,raw){
  const isolated=path.join(folder,'predictor-input');await fs.mkdir(isolated,{recursive:true});
  await fs.writeFile(path.join(isolated,'observations.json'),raw);
  const r=spawnSync(python,['-m','constraint_recovery.geometric_recovery','observations.json','--output','predictions.json'],
    {cwd:isolated,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
  check(r.status===0,r.stderr||String(r.error));
  const result=await fs.readFile(path.join(isolated,'predictions.json'));
  check(JSON.parse(result).observation_sha256===sha(raw),'Prediction/input binding mismatch');return result;
}
async function runCase(browser,source,folder,adversarial=true){
  await fs.mkdir(folder,{recursive:true});const prepared=worker(['prepare','--source',source,'--folder',folder],true);
  if(!prepared.passed)return {scored:false,stage:'blinding',reason:prepared.reason};
  const normalized=await fs.readFile(path.join(folder,'normalized.svg'),'utf8'),blinded=await fs.readFile(path.join(folder,'blinded.svg'),'utf8');
  const before=await measureSvg(browser,normalized,{snapshot:true,styleDetails:true});
  const after=await measureSvg(browser,blinded,{snapshot:true,styleDetails:true});
  await fs.writeFile(path.join(folder,'normalized-geometry.json'),JSON.stringify(before));
  await fs.writeFile(path.join(folder,'geometry.json'),JSON.stringify(after));
  const pixels=worker(['pixels','--folder',folder],true);
  if(!pixels.passed)return {scored:false,stage:'render-preservation',reason:pixels.reason};
  worker(['observe','--folder',folder]);
  const raw=await fs.readFile(path.join(folder,'observations.json')),prediction=await predict(folder,raw);
  await fs.writeFile(path.join(folder,'predictions.json'),prediction);
  const frozen={observation_sha256:sha(raw),prediction_sha256:sha(prediction)};
  await fs.writeFile(path.join(folder,'prediction-freeze.json'),JSON.stringify(frozen,null,2)+'\n');
  const evidence={source_sha256:sha(await fs.readFile(source)),blinded_svg_sha256:sha(blinded),...frozen,
    preparation:await json(path.join(folder,'preparation.json')),
    prediction_written_before_reference_loaded:true,pixel_check:await json(path.join(folder,'pixel-check.json')),
    blocked_secondary_resources:[...new Set([...before.blocked_references,...after.blocked_references])].length};
  if(evidence.blocked_secondary_resources)return {...evidence,scored:false,stage:'source-resources',reason:'Blocked source assets prevent an intact-artwork recovery claim'};
  const grounded=worker(['ground','--source',source,'--folder',folder],true);
  if(!grounded.passed)return {...evidence,scored:false,stage:'reference-grounding',reason:grounded.reason};
  worker(['score','--folder',folder]);
  const scores=await json(path.join(folder,'scores.json'));
  const checks={};
  if(adversarial&&scores.fully_bound_reference_edges){
    const permuted=JSON.parse(raw);permuted.primitives.reverse();
    const variant=JSON.parse(await predict(path.join(folder,'permutation'),Buffer.from(JSON.stringify(permuted))));
    const original=JSON.parse(prediction);delete original.observation_sha256;delete variant.observation_sha256;
    check(isDeepStrictEqual(original,variant),'Primitive permutation changed recovery');checks.primitive_permutation_invariant=true;
    worker(['scorer-check','--folder',folder]);checks.wrong_endpoint_detected=true;
    const mutatedSource=path.join(folder,'reference-mutant.svg'),mutant=path.join(folder,'metadata-mutation');
    worker(['poison','--source',source,'--output',mutatedSource]);
    worker(['prepare','--source',mutatedSource,'--folder',mutant]);
    check(await fs.readFile(path.join(mutant,'blinded.svg'),'utf8')===blinded,'Hidden binding mutation leaked into the blinded artwork');
    await fs.copyFile(path.join(folder,'geometry.json'),path.join(mutant,'geometry.json'));
    worker(['observe','--folder',mutant]);
    const mutatedRaw=await fs.readFile(path.join(mutant,'observations.json')),mutatedPrediction=await predict(mutant,mutatedRaw);
    check(mutatedRaw.equals(raw)&&mutatedPrediction.equals(prediction),'Hidden binding mutation changed predictions');
    worker(['ground','--source',mutatedSource,'--folder',mutant]);
    const reference=await json(path.join(folder,'reference.json')),changed=await json(path.join(mutant,'reference.json'));
    check(!isDeepStrictEqual(reference.edges,changed.edges),'Reference mutation changed no binding');
    checks.hidden_binding_mutation_preserves_blind_input_and_predictions=true;
  }
  check(sha(await fs.readFile(path.join(folder,'predictions.json')))===frozen.prediction_sha256,'Scoring modified frozen predictions');
  return {...evidence,scored:true,reference_sha256:sha(await fs.readFile(path.join(folder,'reference.json'))),scores,checks};
}
async function main(){
  const selectionRaw=await fs.readFile(path.join(root,'data/source-oracle-feasibility-selection.json'));
  const selection=JSON.parse(selectionRaw),protocol=await fs.readFile(path.join(root,'data/source-recovery-protocol.json'));
  const browser=await chromium.launch({headless:true}),records=[];
  try{for(const entry of selection.cases){
    const source=path.join(root,'.cache/label-source-audit',entry.id+'.svg'),raw=await fs.readFile(source);
    check(crypto.createHash('sha1').update(Buffer.concat([Buffer.from('blob '+raw.length+'\0'),raw])).digest('hex')===entry.git_blob,'Pinned source mismatch');
    const result=await runCase(browser,source,path.join(root,'artifacts/source-recovery',entry.id));
    records.push({id:entry.id,...result});console.log(JSON.stringify({id:entry.id,scored:result.scored,reason:result.reason,scores:result.scores}));
  }
  const implementations={};for(const file of ['benchmarks/run_source_recovery.cjs','benchmarks/source_recovery.py','benchmarks/audit_source_oracles.py','src/constraint_recovery/geometric_recovery.py','src/constraint_recovery/assets/browser_geometry.cjs'])implementations[file]=sha(await fs.readFile(path.join(root,file)));
  const report={schema_version:1,kind:'blinded-source-recovery-development',selection_sha256:sha(selectionRaw),protocol_sha256:sha(protocol),
    browser:browser.version(),device:'CPU',selected_figures:records.length,scored_figures:records.filter(r=>r.scored).length,implementations,
    scope:'Previously inspected two-source development probes, not a holdout. Source-declared bindings, no new human labels. Identical local render pixels do not prove semantic intent. No new editing support or learned advantage.',records};
  await fs.writeFile(path.join(root,'artifacts/source-recovery/report.json'),JSON.stringify(report,null,2)+'\n');
  }finally{await browser.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exit(1);});
module.exports={runCase,worker,sha};
