// Optional integration checks: npm ci && npx playwright install chromium.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {pathToFileURL}=require('node:url');
const {spawnSync}=require('node:child_process');
const crypto=require('node:crypto');
const assert=require('node:assert/strict');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..');
function cli(args,expected=0){
  const result=spawnSync(process.env.PYTHON||'python3',['-m','constraint_recovery',...args],{
    cwd:root,env:{...process.env,PYTHONPATH:path.join(root,'src')},encoding:'utf8'});
  assert.equal(result.status,expected,result.stderr||result.stdout);
}
(async()=>{
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'constraint-recovery-browser-'));
  let browser;
  try{
    browser=await chromium.launch({headless:true});
    const page=await browser.newPage({viewport:{width:1400,height:1000}});
    const errors=[],remote=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.route(/^https?:/,route=>{remote.push(route.request().url());return route.abort();});
    const source=path.join(root,'examples/ambiguous.svg');
    const review=path.join(temp,'review.json');
    cli(['review',source,'--output',review]);
    await page.goto(pathToFileURL(path.join(temp,'review.html')).href);
    const button=page.getByRole('button',{name:'Download attachment choices'});
    assert(await button.isDisabled(),'Unresolved choices must block download');
    await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
    await page.screenshot({path:path.join(root,'artifacts/browser-review.png'),fullPage:true});
    await page.getByLabel('ambiguous-result source').focus();
    await page.locator('.canvas rect[data-node="option-a"]').click();
    assert(await button.isEnabled(),'Clicking the node must select it through the text overlay');
    const pending=page.waitForEvent('download');
    await button.click();
    const download=await pending;
    const choices=path.join(temp,'choices.json');
    await download.saveAs(choices);
    const manifest=JSON.parse(await fs.readFile(choices,'utf8'));
    assert.equal(manifest.source_sha256,crypto.createHash('sha256').update(await fs.readFile(source)).digest('hex'));
    assert.deepEqual(manifest.decisions,{'ambiguous-result':{source:'option-a',target:'result'}});
    const edited=path.join(temp,'accepted.svg');
    cli(['edit',source,'--attachments',choices,'--output',edited]);
    assert(JSON.parse(await fs.readFile(path.join(temp,'accepted.report.json'),'utf8')).verification.passed);
    await page.getByLabel('ambiguous-result target').selectOption('option-a');
    assert(await button.isDisabled(),'Self-attachments must block download');

    // Source IDs must not collide with HTML controls; source text stays inert.
    const adversarial=path.join(temp,'adversarial.svg');
    const raw=(await fs.readFile(source,'utf8')).replace('id="option-a"','id="observations"')
      .replace('Option A','&lt;/script&gt;&lt;script&gt;window.BAD=true&lt;/script&gt;');
    await fs.writeFile(adversarial,raw);
    cli(['review',adversarial,'--output',path.join(temp,'adversarial.json')]);
    await page.goto(pathToFileURL(path.join(temp,'adversarial.html')).href);
    assert.equal(await page.evaluate(()=>document.getElementById('observations').tagName),'SCRIPT');
    assert.equal(await page.evaluate(()=>window.BAD),undefined);
    await page.getByLabel('ambiguous-result source').selectOption('observations');
    assert(await page.getByRole('button',{name:'Download attachment choices'}).isEnabled());

    // Browser-measured typography verifies the CSS pixel unit and scale inverse.
    const styled=path.join(temp,'styled.svg');
    const labels=path.join(temp,'labels.json');
    await fs.writeFile(labels,JSON.stringify({model:'Recovered structure across edits'}));
    cli(['edit',path.join(root,'examples/styled-pipeline.svg'),'--source-preserving','--font-size','24',
         '--width','330','--height','650','--flow','vertical','--labels',labels,'--output',styled]);
    await page.goto(pathToFileURL(styled).href);
    const measured=await page.evaluate(async()=>{
      await document.fonts.ready;
      return ['data','model'].map(id=>{
        const node=document.getElementById(id),text=document.getElementById(id+'-label');
        const a=node.getBoundingClientRect(),b=text.getBoundingClientRect(),m=text.getCTM();
        return {id,global_font_size:parseFloat(getComputedStyle(text).fontSize)*Math.hypot(m.a,m.b),
          text_inside_node:b.left>=a.left-.5&&b.right<=a.right+.5&&b.top>=a.top-.5&&b.bottom<=a.bottom+.5};
      });
    });
    assert(measured.every(r=>r.global_font_size>=23.999&&r.text_inside_node),JSON.stringify(measured));
    const geometry=await measureSvg(browser,await fs.readFile(path.join(root,'examples/styled-pipeline.svg'),'utf8'));
    const recovered=geometry.primitives.find(r=>r.source_id==='data').viewbox_bounds;
    assert(recovered.every((v,i)=>Math.abs(v-[54,92,198,176][i])<1e-4),JSON.stringify(recovered));
    const probe=`<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
      <defs><g id="glyph"><rect width="20" height="10"/></g></defs>
      <rect id="guard" x="10" y="10" width="20" height="10"/>
      <g transform="rotate(90 100 100)"><rect id="rotated" x="20" y="30" width="40" height="10"/></g>
      <use id="instance" href="#glyph" x="120" y="140"/>
      <image href="https://example.invalid/pixel.png" width="10" height="10"/>
      <script><![CDATA[document.getElementById('guard').setAttribute('x','999');fetch('https://example.invalid/active');]]></script>
    </svg>`;
    const guarded=await measureSvg(browser,probe);
    assert.equal(guarded.primitives.find(r=>r.source_id==='guard').viewbox_bounds[0],10);
    for(const [id,wanted] of [['rotated',[160,20,170,60]],['instance',[120,140,140,150]]]){
      const actual=guarded.primitives.find(r=>r.source_id===id).viewbox_bounds;
      assert(actual.every((v,i)=>Math.abs(v-wanted[i])<1e-4),JSON.stringify({id,actual}));
    }
    assert.deepEqual(guarded.blocked_references,['https://example.invalid/pixel.png']);
    assert.deepEqual(errors,[]);
    assert.deepEqual(remote,[]);
    const report={passed:true,browser:browser.version(),review_download_roundtrip:true,self_attachment_blocked:true,
      source_id_collision_test:true,inert_source_text_test:true,unexpected_remote_requests:remote,typography:measured,
      browser_geometry:{normalized_transform_test:true,rotation_and_use_test:true,source_scripts_disabled:true,secondary_requests_blocked:true},
      scope:'Authored SVGs and adversarial probes; not an external-figure rendering benchmark'};
    await fs.writeFile(path.join(root,'artifacts/browser-check.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }finally{
    if(browser)await browser.close();
    await fs.rm(temp,{recursive:true,force:true});
  }
})().catch(e=>{console.error(e);process.exit(1);});
