// Offline geometry audit of the predeclared cached external development prefix.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const {measureSvg}=require('./measure_svg.cjs');
function option(args,name,fallback){const i=args.indexOf(name);return i===-1?fallback:args[i+1];}
(async()=>{
  const args=process.argv.slice(2),count=Number(option(args,'--rows','20')),offset=Number(option(args,'--offset','0'));
  if(!Number.isInteger(count)||count<1||count>100||!Number.isInteger(offset)||offset<0)throw Error('Invalid predeclared row range');
  const cache=option(args,'--cache-dir','.cache/external'),measurements=option(args,'--measurements','.cache/browser-geometry');
  const output=option(args,'--output','results/browser-geometry-audit.json');
  if(!path.resolve(measurements).includes(path.sep+'.cache'+path.sep))throw Error('Full external measurements must stay in a private .cache directory');
  const rows=new Map();
  for(const name of (await fs.readdir(cache)).sort()){
    if(!/^SciDiagramRevision-test-\d+-\d+\.json$/.test(name))continue;
    const payload=JSON.parse(await fs.readFile(path.join(cache,name),'utf8'));
    for(const item of payload.rows){
      if(item.row_idx>=offset&&item.row_idx<offset+count){
        if(rows.has(item.row_idx)&&rows.get(item.row_idx).row.input_svg!==item.row.input_svg)throw Error('Conflicting cached dataset rows');
        rows.set(item.row_idx,item);
      }
    }
  }
  if(rows.size!==count)throw Error('Offline cache does not cover the complete predeclared range');
  const browser=await chromium.launch({headless:true});
  const records=[];
  try{
    await fs.mkdir(measurements,{recursive:true});
    for(let row=offset;row<offset+count;row++){
      const item=rows.get(row),source=item.row.input_svg;
      const record={row,task_id:item.row.task_id,source_sha256:typeof source==='string'?crypto.createHash('sha256').update(source).digest('hex'):null};
      if(typeof source!=='string'||(item.truncated_cells||[]).includes('input_svg')){
        record.measured=false;record.failure=typeof source==='string'?'Truncated source':'Unavailable source';records.push(record);continue;
      }
      try{
        const measured=await measureSvg(browser,source,{snapshot:args.includes('--snapshot')});
        await fs.writeFile(path.join(measurements,`row-${String(row).padStart(4,'0')}.json`),JSON.stringify(measured,null,2)+'\n');
        const visible=measured.primitives.filter(p=>p.visible_by_display_visibility_opacity&&p.viewbox_bounds);
        const rects=visible.filter(p=>p.tag==='rect');
        const background=rects.filter(p=>p.viewbox_bounds[0]<=.001&&p.viewbox_bounds[1]<=.001&&p.viewbox_bounds[2]>=measured.canvas[0]-.001&&p.viewbox_bounds[3]>=measured.canvas[1]-.001);
        const candidates=rects.filter(p=>!background.includes(p));
        const texts=visible.filter(p=>p.tag==='text');
        const contains=(a,b)=>a[0]<=b[0]+.001&&a[1]<=b[1]+.001&&a[2]>=b[2]-.001&&a[3]>=b[3]-.001;
        const owners=texts.map(t=>candidates.filter(r=>contains(r.viewbox_bounds,t.viewbox_bounds)).length);
        record.measured=true;
        record.observations={primitives:measured.primitives.length,bounded:measured.primitives.filter(p=>p.viewbox_bounds).length,
          visible_bounded:visible.length,text_envelopes:texts.length,canvas_covering_rectangle_envelopes:background.length,
          text_envelopes_with_zero_rect_owners:owners.filter(v=>v===0).length,text_envelopes_with_multiple_rect_owners:owners.filter(v=>v>1).length,
          primitives_with_effects:visible.filter(p=>p.has_unbounded_effects).length,blocked_secondary_references:measured.blocked_references.length};
      }catch(error){record.measured=false;record.failure=error.message;}
      records.push(record);
    }
    const totals={};
    for(const r of records)if(r.observations)for(const [key,value]of Object.entries(r.observations))totals[key]=(totals[key]||0)+value;
    const report={schema_version:1,dataset:'yashengsun/SciDiagramRevision',selection:`Published test rows ${offset}..${offset+count-1}; development prefix, not representative`,
      browser:browser.version(),sources_measured:records.filter(r=>r.measured).length,requested_rows:count,aggregate_observations:totals,
      protocol:'Offline cached source; JavaScript disabled; all secondary non-embedded references blocked. Full geometry stays in private .cache. Only aggregate observations and source hashes committed.',
      limitations:['Read-only geometry, not complete-figure editing support or relation accuracy','Envelope containment is a candidate relation, not author-intent ground truth',
        'Transformed local browser getBBox envelopes exclude stroke, marker, filter and clipping extents','Blocked resources can change appearance; system font fallback is environment-dependent',
        'Mixed upstream arXiv-source licensing; no original SVGs, text or figures redistributed'],records};
    await fs.mkdir(path.dirname(output),{recursive:true});
    await fs.writeFile(output,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({sources_measured:report.sources_measured,requested_rows:count,aggregate_observations:totals},null,2));
  }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exit(1);});
