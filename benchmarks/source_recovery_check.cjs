// Authored fixture for offline CI; no public external artwork or network fetch.
const fs=require('node:fs/promises'),path=require('node:path');
const {chromium}=require('playwright');
const {runCase}=require('./run_source_recovery.cjs');
(async()=>{const root=path.resolve(__dirname,'..'),browser=await chromium.launch({headless:true});try{
  const result=await runCase(browser,path.join(root,'examples/source-reference.svg'),path.join(root,'artifacts/source-recovery-fixture'));
  if(!result.scored||!result.pixel_check.passed||Object.keys(result.checks).length!==3||
    Object.values(result.scores.methods).some(m=>m.correct_endpoints!==2))throw Error('Blinded recovery workflow regressed');
  const report={passed:true,scope:'Authored workflow fixture, not external accuracy',...result};
  await fs.writeFile(path.join(root,'artifacts/source-recovery-check.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close();}})().catch(e=>{console.error(e.message);process.exit(1);});
