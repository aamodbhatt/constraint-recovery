// Browser-backed transaction. Candidate artifacts remain private until checked.
const fs=require('node:fs/promises'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {chromium}=require(require.resolve('playwright',{paths:[process.cwd(),__dirname]}));
const {measureSvg}=require('./browser_geometry.cjs');
let raw='';process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>raw+=chunk);
process.stdin.on('end',async()=>{
  let browser,temp;
  try{
    const request=JSON.parse(raw);
    temp=await fs.mkdtemp(path.join(os.tmpdir(),'constraint-compound-'));
    const input=path.join(temp,'input.svg'),before=path.join(temp,'before.json'),candidate=path.join(temp,'candidate.svg');
    const source=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true}).decode(await fs.readFile(request.input));
    await fs.writeFile(input,source);
    browser=await chromium.launch({headless:true});
    await fs.writeFile(before,JSON.stringify(await measureSvg(browser,source,{styleDetails:true,maxPrimitives:500})));
    const report=path.join(temp,'report.json'),state=path.join(temp,'state.json'),after=path.join(temp,'after.json');
    function worker(action,extra=[]){
      const result=spawnSync(request.python,['-m','constraint_recovery.compound',action,'--source',input,'--measurements',before,
        '--manifest',request.manifest,'--moves',request.moves,'--candidate',candidate,'--report',report,'--routing',request.routing||'channel',...extra],
        {encoding:'utf8',env:process.env,timeout:30000,maxBuffer:2000000});
      if(result.status!==0)throw Error(result.stderr||result.error?.message||'Compound worker failed');
    }
    worker('prepare');
    const output=await fs.readFile(candidate,'utf8');
    await fs.writeFile(after,JSON.stringify(await measureSvg(browser,output,{styleDetails:true,maxPrimitives:500})));
    worker('verify',['--after',after,'--state',state]);
    await fs.mkdir(path.dirname(request.output),{recursive:true});
    const stem=request.output.replace(/\.[^.\/\\]*$/,'');
    const artifacts=[[report,stem+'.report.json'],[state,stem+'.compound.json'],[after,stem+'.measurements.json'],[candidate,request.output]];
    const staging=await fs.mkdtemp(path.join(path.dirname(request.output),'.compound-export-'));
    try{
      for(let i=0;i<artifacts.length;i++)await fs.copyFile(artifacts[i][0],path.join(staging,String(i)));
      for(let i=0;i<artifacts.length;i++)await fs.rename(path.join(staging,String(i)),artifacts[i][1]);
    }finally{await fs.rm(staging,{recursive:true,force:true});}
    console.log(await fs.readFile(report,'utf8'));
  }catch(error){console.error(error.message);process.exitCode=2;}
  finally{if(browser)await browser.close();if(temp)await fs.rm(temp,{recursive:true,force:true});}
});
