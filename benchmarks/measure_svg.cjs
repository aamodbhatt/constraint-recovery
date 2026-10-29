// Non-editing browser geometry. Original SVGs and full measurements stay local.
const {chromium}=require('playwright');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const crypto=require('node:crypto');
const {pathToFileURL}=require('node:url');

async function measureSvg(browser,source,{includeText=false,maxPrimitives=5000,timeout=15000}={}){
  if(typeof source!=='string'||Buffer.byteLength(source)>8000000)throw Error('SVG must be UTF-8 text of at most eight MB');
  if(!Number.isInteger(maxPrimitives)||maxPrimitives<1||maxPrimitives>10000)throw Error('Invalid primitive budget');
  if(/<!DOCTYPE|<\?(?!xml(?:\s|\?>))/i.test(source))throw Error('Document types and processing instructions are unsupported');
  const temp=await fs.mkdtemp(path.join(os.tmpdir(),'constraint-recovery-measure-'));
  let context,timer;
  const blocked=[];
  try{
    const input=path.join(temp,'source.svg');
    await fs.writeFile(input,source,'utf8');
    const url=pathToFileURL(input).href;
    context=await browser.newContext({javaScriptEnabled:false,offline:true,serviceWorkers:'block',acceptDownloads:false,
      viewport:{width:1280,height:960},deviceScaleFactor:1});
    await context.route('**/*',route=>{
      if(route.request().url()===url)return route.continue();
      if(/^data:image\/(png|jpeg|webp);base64,/i.test(route.request().url()))return route.continue();
      blocked.push(route.request().url().startsWith('file:')?'blocked-local-reference':route.request().url());
      return route.abort();
    });
    const page=await context.newPage();
    const work=(async()=>{
      await page.goto(url,{waitUntil:'domcontentloaded',timeout});
      return page.evaluate(async({includeText,maxPrimitives})=>{
        const root=document.documentElement;
        if(root.localName!=='svg'||root.namespaceURI!=='http://www.w3.org/2000/svg')throw Error('Expected an SVG document');
        if(root.pauseAnimations)root.pauseAnimations();
        for(const animation of document.getAnimations())animation.cancel();
        await document.fonts.ready;
        const vb=root.viewBox.baseVal;
        function matrix(value){
          if(!value||![value.a,value.b,value.c,value.d,value.e,value.f].every(Number.isFinite))throw Error('No finite 2D SVG transform');
          return new DOMMatrix([value.a,value.b,value.c,value.d,value.e,value.f]);
        }
        const screen=matrix(root.getScreenCTM());
        const origin=vb.width&&vb.height?[vb.x,vb.y]:[0,0];
        const normalized=new DOMMatrix().translate(-origin[0],-origin[1]).multiply(screen.inverse());
        const viewport=root.getBoundingClientRect();
        const imageProjection=new DOMMatrix().translate(-viewport.left,-viewport.top).multiply(screen).translate(origin[0],origin[1]);
        const canvas=vb.width&&vb.height?[vb.width,vb.height]:[root.width.baseVal.value,root.height.baseVal.value];
        if(!canvas.every(v=>Number.isFinite(v)&&v>0))throw Error('Invalid browser canvas');
        const tags=new Set(['rect','circle','ellipse','line','polyline','polygon','path','text','image','use']);
        const definitions=new Set(['defs','symbol','marker','pattern','clipPath','mask']);
        const records=[];
        function visit(element,location,inDefs=false){
          inDefs=inDefs||definitions.has(element.localName);
          if(tags.has(element.localName)&&!inDefs){
            if(records.length>=maxPrimitives)throw Error('Primitive budget exceeded; no partial coverage reported');
            const style=getComputedStyle(element);
            let hidden=style.visibility!=='visible';
            let opacity=1;
            let threeD=false;
            let effects=false;
            for(let ancestor=element;ancestor;ancestor=ancestor.parentElement){
              const s=getComputedStyle(ancestor);
              hidden=hidden||s.display==='none';opacity*=Number(s.opacity);
              threeD=threeD||s.perspective!=='none'||(s.transform!=='none'&&!new DOMMatrix(s.transform).is2D);
              effects=effects||s.filter!=='none'||s.clipPath!=='none'||s.maskImage!=='none';
            }
            const record={location,source_id:element.id||null,tag:element.localName,viewbox_bounds:null,
              visible_by_display_visibility_opacity:!hidden&&opacity>0,
              computed:{fill:style.fill,stroke:style.stroke,stroke_width:style.strokeWidth,font_family:style.fontFamily,
                font_size:style.fontSize,font_weight:style.fontWeight,marker_end:style.markerEnd,
                filter:style.filter,clip_path:style.clipPath,mask:style.mask},
              has_unbounded_effects:effects};
            try{
              if(threeD)throw Error('3D CSS transforms/perspective are outside 2D envelope scope');
              const box=element.getBBox(),ctm=matrix(element.getScreenCTM());
              const affine=normalized.multiply(ctm);
              const points=[[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],[box.x+box.width,box.y+box.height]]
                .map(([x,y])=>new DOMPoint(x,y).matrixTransform(affine));
              const values=[Math.min(...points.map(p=>p.x)),Math.min(...points.map(p=>p.y)),
                Math.max(...points.map(p=>p.x)),Math.max(...points.map(p=>p.y))];
              if(!values.every(Number.isFinite))throw Error('Non-finite browser bounds');
              record.viewbox_bounds=values;
              record.matrix=[affine.a,affine.b,affine.c,affine.d,affine.e,affine.f];
              if(element.localName==='text'){
                record.characters=Array.from(element.textContent).length;
                if(includeText)record.text=element.textContent;
              }
            }catch(error){record.geometry_failure=error.message;}
            records.push(record);
          }
          [...element.children].forEach((child,i)=>visit(child,location+'/'+child.localName+'['+i+']',inDefs));
        }
        visit(root,'svg');
        return {canvas,origin,image_size:[viewport.width,viewport.height],
          image_projection:[imageProjection.a,imageProjection.b,imageProjection.c,imageProjection.d,imageProjection.e,imageProjection.f],
          root_css_transform:getComputedStyle(root).transform,primitives:records};
      },{includeText,maxPrimitives});
    })();
    const deadline=new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Browser geometry deadline exceeded')),timeout);});
    const result=await Promise.race([work,deadline]);
    return {schema_version:1,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),browser:browser.version(),
      javascript_enabled:false,network_enabled:false,blocked_references:[...new Set(blocked)],...result,
      limitations:['Read-only browser geometry, not an accepted graph or edit support',
        'Bounds transform browser local getBBox envelopes; strokes, markers, clipping and filter extents are not certified',
        'Remote/local references are blocked; missing resources may change rendered content or font fallback',
        'Animations are paused/cancelled for measurement; this is not an SVG sanitizer or authorization to embed the original']};
  }finally{
    clearTimeout(timer);
    if(context)await context.close();
    await fs.rm(temp,{recursive:true,force:true});
  }
}

module.exports={measureSvg};
if(require.main===module){
  (async()=>{
    const args=process.argv.slice(2),input=args[0],out=args[1];
    if(!input||!out)throw Error('Usage: node benchmarks/measure_svg.cjs INPUT.svg OUTPUT.json [--include-text]');
    if(path.resolve(input)===path.resolve(out))throw Error('Output must differ from input');
    const browser=await chromium.launch({headless:true});
    try{
      const source=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await fs.readFile(input));
      const result=await measureSvg(browser,source,{includeText:args.includes('--include-text')});
      await fs.mkdir(path.dirname(out),{recursive:true});
      await fs.writeFile(out,JSON.stringify(result,null,2)+'\n');
      console.log(JSON.stringify({primitives:result.primitives.length,bounded:result.primitives.filter(p=>p.viewbox_bounds).length,blocked_references:result.blocked_references.length}));
    }finally{await browser.close();}
  })().catch(error=>{console.error(error.message);process.exit(1);});
}
