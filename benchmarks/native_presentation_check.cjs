const fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
function check(ok,message){if(!ok)throw Error(message);}
(async()=>{const browser=await chromium.launch({headless:true});try{
  const page=await browser.newPage({viewport:{width:1600,height:1040}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(root,'docs/demo/native-pilot/index.html')).href);
  for(let i=0;i<5;i++){
    await page.locator('#case-'+i).click();
    await page.locator('#source').evaluate(img=>img.decode());await page.locator('#result').evaluate(img=>img.decode());
    const accepted=![1,3].includes(i);
    check(await page.locator('#download').isVisible()===accepted,'Incorrect download state: '+i);
    if(accepted){await page.locator('#step2').click();await page.locator('#result').evaluate(img=>img.decode());check((await page.locator('#result').getAttribute('src')).includes('step-2'),'Second edit not shown');}
    else check(await page.locator('#result').getAttribute('src')===await page.locator('#source').getAttribute('src'),'Declined edit replaced source');
  }
  await page.locator('#case-2').click();await page.locator('#view-result').click();
  check(await page.locator('#source-card').isHidden()&&await page.locator('#result-card').isVisible(),'Enlarge-result control failed');
  await page.screenshot({path:path.join(root,'artifacts/native-pilot-focused.png'),fullPage:true});
  await page.locator('#view-source').click();check(await page.locator('#result-card').isHidden(),'Enlarge-source control failed');
  await page.locator('#view-compare').click();check(await page.locator('#source-card').isVisible()&&await page.locator('#result-card').isVisible(),'Compare control failed');
  await page.screenshot({path:path.join(root,'artifacts/native-pilot-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const mobile=await page.evaluate(()=>({viewport:innerWidth,content:document.documentElement.scrollWidth}));
  check(mobile.content<=mobile.viewport,'Native pilot mobile overflow');
  await page.screenshot({path:path.join(root,'artifacts/native-pilot-mobile.png'),fullPage:true});
  // Independent-review views begin with no model/agent roles or relations.
  const entries=JSON.parse(await fs.readFile(path.join(root,'data/native-pilot-selection.json'),'utf8')).cases;
  await page.setViewportSize({width:1440,height:1000});
  for(const entry of entries){
    await page.goto(pathToFileURL(path.join(root,'docs/demo/native-pilot/review',entry.id+'.html')).href);
    check(await page.locator('#objects').evaluate(e=>e.children.length)===0,'Review view prefilled object suggestions');
    check(await page.locator('#relations').evaluate(e=>e.children.length)===0,'Review view prefilled relations');
    check(await page.locator('#role').inputValue()==='','Review view preselected a role');
  }
  // Resume must expose and retain advanced connector assumptions, rather than
  // silently dropping them when a reviewer downloads an existing record.
  await page.goto(pathToFileURL(path.join(root,'docs/demo/native-pilot/review/distill-rnn-basic.html')).href);
  const file=path.join(root,'data/native-pilot/annotations/distill-rnn-basic.agent.json');
  const annotation=JSON.parse(await fs.readFile(file,'utf8'));
  await page.locator('#resume').setInputFiles(file);
  await page.getByText('Forward shaft:',{exact:false}).first().waitFor();
  const downloadPromise=page.waitForEvent('download');await page.locator('#download').click();
  const downloaded=JSON.parse(await fs.readFile(await(await downloadPromise).path(),'utf8'));
  check(JSON.stringify(downloaded.objects)===JSON.stringify(annotation.objects),'Resume dropped explicit connector geometry');
  check(downloaded.review.status==='agent-reviewed','Resume promoted agent annotations to human review');
  check(!errors.length,errors.join(';'));
  const report={passed:true,all_five_comparisons:true,refused_request_retains_source:true,focus_controls:true,mobile,
    unlabelled_review_views:5,connector_geometry_exposed_and_retained:true,no_review_promotion:true,errors};
  await fs.writeFile(path.join(root,'artifacts/native-presentation-check.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
}finally{await browser.close();}})().catch(e=>{console.error(e.message);process.exit(1);});
