// Scripted authored records exercise adjudication; no human agreement claim.
const fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..'),python=process.env.PYTHON||'python3';
function check(ok,message){if(!ok)throw Error(message);}
(async()=>{const browser=await chromium.launch({headless:true});try{
  const source=path.join(root,'examples/compound.svg'),geometry=path.join(root,'artifacts/comparison-geometry.json');
  await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
  await fs.writeFile(geometry,JSON.stringify(await measureSvg(browser,await fs.readFile(source,'utf8'))));
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const generate=variant=>{
    const output=path.join(root,'artifacts/comparison-'+variant+'.json');
    const r=spawnSync(python,['-m','constraint_recovery','compare-annotations',path.join(root,'examples/compound.annotation.agent.json'),
      path.join(root,'examples/annotation-comparison',variant+'.agent.json'),'--source',source,'--measurements',geometry,'--output',output,'--html'],
      {cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8',timeout:30000});
    check(r.status===0,r.stderr||r.stdout);return output.replace(/\.json$/,'.html');
  };
  await page.goto(pathToFileURL(generate('split')).href);
  check(await page.locator('.left-highlight').count()===3&&await page.locator('.right-highlight').count()===2,'Split grouping overlay is wrong');
  check((await page.locator('#roles').textContent())==='80.0%','Joint role comparison wrong');
  await page.locator('#focus-view').click();
  const a=await page.locator('#left-canvas').getAttribute('viewBox'),b=await page.locator('#right-canvas').getAttribute('viewBox');
  check(a===b&&a!=='0 0 760 440','Focus must use the same selected region on both sides');
  await page.locator('#full-view').click();
  check(await page.locator('#left-canvas').getAttribute('viewBox')==='0 0 760 440','Full diagram reset failed');
  await page.locator('tr[data-match="encoder"]').click();
  check(await page.locator('.left-highlight').count()===4&&await page.locator('.right-highlight').count()===4,'Matched object selection failed');
  await page.getByRole('button',{name:'right: variant_decoder',exact:true}).click();
  check(await page.locator('.left-highlight').count()===0&&await page.locator('.right-highlight').count()===1,'Unmatched object disappeared');
  await page.locator('tr[data-match="decoder"]').click();
  await page.screenshot({path:path.join(root,'artifacts/annotation-comparison-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
  check(mobile.content<=mobile.viewport,'Comparison mobile overflow');
  await page.screenshot({path:path.join(root,'artifacts/annotation-comparison-mobile.png'),fullPage:true});
  await page.goto(pathToFileURL(generate('partial')).href);
  check((await page.locator('#coverage').textContent())==='7 / 10','Partial comparison hid abstention');
  check((await page.locator('#ari').textContent())==='1.000','Conditional grouping score changed');
  check((await page.locator('#positive-overlap').textContent())==='Not scorable','Unscorable relations were treated as correct/incorrect');
  check((await page.locator('#domain').textContent()).includes('3 primitives'),'Excluded-domain count missing');
  check(!errors.length,errors.join(';'));
  const report={passed:true,scripted_authored_fixture:true,independent_human_annotations:0,part_highlights:true,
    common_focus_crop:true,unmatched_objects_retained:true,partial_coverage_visible:true,unscorable_relations_not_promoted:true,mobile,errors};
  await fs.writeFile(path.join(root,'artifacts/annotation-comparison-check.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
}finally{await browser.close();}})().catch(e=>{console.error(e.message);process.exit(1);});
