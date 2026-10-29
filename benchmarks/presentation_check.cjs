// Portable smoke/visual checks for the public authored sequence workspace.
const fs=require('node:fs/promises'),path=require('node:path');
const {pathToFileURL}=require('node:url');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..');
function check(value,message){if(!value)throw Error(message);}
(async()=>{
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:1440,height:1040}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(pathToFileURL(path.join(root,'docs/demo/sequence/index.html')).href);
    await page.getByRole('button',{name:'Step 4: Add a branch',exact:true}).click();
    await page.locator('#figure').evaluate(img=>img.decode());
    await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
    await page.screenshot({path:path.join(root,'artifacts/presentation-desktop.png'),fullPage:true,animations:'disabled'});
    await page.getByRole('button',{name:'Actual size',exact:true}).click();
    check(await page.locator('#viewport').evaluate(e=>e.classList.contains('actual')),'Actual-size control failed');
    await page.getByRole('button',{name:'Fit',exact:true}).click();
    check(!await page.locator('#viewport').evaluate(e=>e.classList.contains('actual')),'Fit control failed');
    await page.getByRole('button',{name:'Step 7: Rejected request',exact:true}).click();
    check(await page.locator('#proof').isVisible(),'Rejection proof missing');
    check((await page.locator('#figure').getAttribute('src')).startsWith('06-'),'Rejected request replaced accepted SVG');
    await page.screenshot({path:path.join(root,'artifacts/presentation-rejected.png'),fullPage:true,animations:'disabled'});
    await page.setViewportSize({width:390,height:844});
    await page.getByRole('button',{name:'Step 3: Portrait',exact:true}).click();
    await page.locator('#figure').evaluate(img=>img.decode());
    const mobile=await page.evaluate(()=>({width:innerWidth,content:document.documentElement.scrollWidth}));
    check(mobile.content<=mobile.width+1,'Mobile workspace overflows viewport');
    await page.screenshot({path:path.join(root,'artifacts/presentation-mobile.png'),fullPage:true,animations:'disabled'});
    check(!errors.length,errors.join(';'));
    const report={passed:true,steps_checked:[3,4,7],mobile,fit_controls:true,rejected_request_retains_accepted_svg:true,errors};
    await fs.writeFile(path.join(root,'artifacts/presentation-check.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report));
  }finally{await browser.close();}
})().catch(e=>{console.error(e.message);process.exit(1);});
