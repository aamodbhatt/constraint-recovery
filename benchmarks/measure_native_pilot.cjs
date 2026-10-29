// Acquisition audit of the fixed, attributed native-SVG development selection.
const fs=require('node:fs/promises'),path=require('node:path'),crypto=require('node:crypto');
const {spawnSync}=require('node:child_process');
const {chromium}=require('playwright');
const {measureSvg}=require('./measure_svg.cjs');
const root=path.resolve(__dirname,'..');
async function main(){
  const selection=JSON.parse(await fs.readFile(path.join(root,'data/native-pilot-selection.json'),'utf8'));
  const folder=path.join(root,'.cache/native-pilot/geometry'),renders=path.join(root,'.cache/native-pilot/renders');
  await fs.mkdir(folder,{recursive:true});await fs.mkdir(renders,{recursive:true});
  const browser=await chromium.launch({headless:true}),records=[];
  try{
    for(const entry of selection.cases){
      const file=path.join(root,'data/native-pilot/original',entry.id+'.svg'),raw=await fs.readFile(file),source=raw.toString('utf8');
      const sha=crypto.createHash('sha256').update(raw).digest('hex');
      const blob=crypto.createHash('sha1').update(Buffer.concat([Buffer.from('blob '+raw.length+'\0'),raw])).digest('hex');
      if(sha!==entry.source_sha256||blob!==entry.git_blob)throw Error('Frozen source mismatch: '+entry.id);
      const guard=spawnSync(process.env.PYTHON||'python3',['-c',
        'import sys; from constraint_recovery.static_svg import parse_static; from constraint_recovery.model import DiagramError; '+
        '\ntry: parse_static(open(sys.argv[1]).read())\nexcept DiagramError as e: print(str(e)); sys.exit(2)',file],
        {cwd:root,encoding:'utf8',env:{...process.env,PYTHONPATH:path.join(root,'src')}});
      if(![0,2].includes(guard.status))throw Error(guard.stderr||'Static worker failed');
      const record={id:entry.id,source_sha256:sha,original_git_blob_verified:true,license:entry.license,
        static_edit_guard:{passed:guard.status===0,reason:guard.stdout.trim()||null}};
      try{
        const measured=await measureSvg(browser,source,{styleDetails:true,includeText:true,maxPrimitives:500});
        await fs.writeFile(path.join(folder,entry.id+'.json'),JSON.stringify(measured,null,2)+'\n');
        record.geometry={measured:true,canvas:measured.canvas,primitives:measured.primitives.length,
          unmeasured:measured.primitives.filter(p=>!p.viewbox_bounds).length,
          primitives_with_effects:measured.primitives.filter(p=>p.has_unbounded_effects).length,
          marked_arrows:measured.primitives.filter(p=>p.computed_all['marker-end']!=='none').length,
          blocked_secondary_references:measured.blocked_references.length};
        const context=await browser.newContext({javaScriptEnabled:false,offline:true});
        try{
          const page=await context.newPage({viewport:{width:1200,height:900}});
          const height=Math.ceil(1100*measured.canvas[1]/measured.canvas[0]);
          await page.setContent('<html><body style="margin:0;padding:30px;background:#fff"><img style="display:block;width:1100px;height:'+height+'px" src="data:image/svg+xml;base64,'+raw.toString('base64')+'"></body></html>');
          await page.locator('img').evaluate(e=>e.decode());
          await page.screenshot({path:path.join(renders,entry.id+'.png'),fullPage:true});
        }finally{await context.close();}
      }catch(error){record.geometry={measured:false,reason:error.message};}
      records.push(record);
    }
    const report={schema_version:1,selection:'data/native-pilot-selection.json',browser:browser.version(),figures:records.length,
      sources_measured:records.filter(r=>r.geometry.measured).length,static_guard_passes:records.filter(r=>r.static_edit_guard.passed).length,
      scope:'Read-only acquisition audit of five author-published SVGs. No annotations, editing success, recovery accuracy or independent human review established.',records};
    await fs.mkdir(path.join(root,'artifacts'),{recursive:true});
    await fs.writeFile(path.join(root,'artifacts/native-pilot-acquisition.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify(report,null,2));
  }finally{await browser.close();}
}
if(require.main===module)main().catch(e=>{console.error(e.message);process.exit(1);});
module.exports={main};
