/** Browser integration checks: real UI, real loopback backend, fictional inputs. */
const { chromium }=require('playwright');
const {spawn}=require('node:child_process');
const {mkdtemp,mkdir,rm}=require('node:fs/promises');
const {tmpdir}=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
 const directory=await mkdtemp(path.join(tmpdir(),'hm023-browser-'));
 const port=8199,base=`http://127.0.0.1:${port}`;
 const server=spawn(process.env.PYTHON||'python',['-m','webapp.app','--port',String(port),'--data-dir',directory],{stdio:['ignore','pipe','pipe']});
 let serverLog='';server.stderr.on('data',c=>serverLog+=c);let browser;
 try{
  for(let i=0;i<80;i++){try{const r=await fetch(base);if(r.ok)break;}catch{}await new Promise(r=>setTimeout(r,250));}
  browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
  page.setDefaultTimeout(30000);const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('favicon'))errors.push(m.text());});
  await page.goto(base);await page.waitForFunction(()=>document.querySelector('#content').children.length>0);
  const kind=await page.evaluate(()=>document.body.dataset.kind);
  const click=name=>page.getByRole('button',{name,exact:true}).click();
  const notice=part=>page.waitForFunction(p=>document.querySelector('#notice').textContent.includes(p),part);
  const isError=async()=>assert.equal(await page.locator('#notice').getAttribute('class'),'notice');
  if(kind==='ml'){
   await click('Inspect dataset');await notice('Dataset inspected');await isError();
   assert.equal(await page.getByText('300',{exact:true}).count()>0,true);
   await page.locator('select[name=model]').selectOption('logistic-regression');
   await click('Train & evaluate');await notice('Experiment saved');await isError();
   await page.getByRole('heading',{name:'Evaluation report',exact:true}).waitFor();
   await click('Experiment history');assert.equal(await page.locator('tbody tr').count(),1);
   await click('Model predictions');
   await page.locator('input[name=file]').setInputFiles({name:'features.csv',mimeType:'text/csv',buffer:Buffer.from('Flow Duration,Packets,Bytes,Destination Port\n2.5,10,1200,443\n4.2,16,1900,80\n')});
   await click('Run local prediction');await notice('Predictions completed');await isError();
   assert.equal(await page.locator('tbody tr').count(),2);
   await click('Experiment studio');
  }else if(kind==='network'){
   await click('Build address plan');await notice('Design saved');await isError();
   await page.getByRole('heading',{name:'Address plan',exact:true}).waitFor();
   assert.equal(await page.locator('tbody tr').count(),6);
   const [download]=await Promise.all([page.waitForEvent('download'),click('Export configuration text')]);assert.equal(download.suggestedFilename(),'configuration-baseline.txt');
   await click('Saved designs');await click('Open');
  }else if(kind==='defense'){
   await click('Analyze policy');await notice('Policy analysis saved');await isError();
   await page.getByRole('heading',{name:'Inter-zone access matrix',exact:true}).waitFor();
   assert.equal(await page.getByText('PASS',{exact:false}).count()>=3,true);
   await click('Analysis history');await click('Open');
  }else if(kind==='assessment'){
   await click('Add fictional example');await notice('Fictional example data added');await isError();
   await click('Edit / retest');await page.locator('select[name=status]').selectOption('resolved');
   await page.locator('textarea[name=retest_note]').fill('Illustrative retest note: parameterized inputs remain data.');
   await click('Save finding');await notice('Finding saved');await isError();
   await click('Reports & exports');await click('Prepare redacted report');await notice('Redacted report prepared');await isError();
   const [download]=await Promise.all([page.waitForEvent('download'),click('Download HTML')]);assert.equal(download.suggestedFilename(),'assessment-report.html');
   await click('Finding register');assert.equal(await page.locator('.report-item').count(),1);
  }else if(kind==='volunteer'){
   await click('Add fictional demo data');await notice('Fictional example data added');await isError();
   await click('Assignments');await page.locator('select[name=volunteer_id]').selectOption({label:'Volunteer Cedar · coordination, logistics'});await click('Assign volunteer');await notice('Record saved');await isError();
   assert.equal(await page.locator('tbody tr').count(),1);
   await click('Resource intents');await click('Mark received');await notice('Resource status updated');await isError();
   await click('Mark distributed');await notice('Resource status updated');await isError();
   await click('Operations overview');
  }else throw Error('Unknown workspace kind: '+kind);
  await mkdir('visuals',{recursive:true});
  await page.screenshot({path:'visuals/desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  assert.equal(overflow,false,'Page must fit the mobile viewport; data tables may scroll within their container.');
  await page.screenshot({path:'visuals/mobile.png',fullPage:true});
  await page.reload();await page.waitForFunction(()=>document.querySelector('#content').children.length>0);
  assert.equal(errors.length,0,'Browser errors: '+errors.join('\n'));
  console.log(`Browser workflow passed: ${kind}; desktop/mobile screenshots captured; persisted state reloaded.`);
 }finally{if(browser)await browser.close();server.kill('SIGTERM');if(server.exitCode===null)await Promise.race([new Promise(r=>server.once('exit',r)),new Promise(r=>setTimeout(r,2000))]);await rm(directory,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
