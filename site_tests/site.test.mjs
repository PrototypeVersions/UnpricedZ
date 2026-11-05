import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';

const html=fs.readFileSync('site/index.html','utf8');
const scripts=['site/risk.js','site/app.js'].map(p=>fs.readFileSync(p,'utf8'));
const read=key=>JSON.parse(fs.readFileSync(`site/data/${key}.json`,'utf8'));
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function lab(hash='') {
  const {window,document}=parseHTML(html);
  window.innerWidth=1100;window.scrollTo=()=>{};
  const location={hash};const calls=[],failed=new Set();
  document.querySelector('dialog').showModal=function(){this.setAttribute('open','');};
  document.querySelector('dialog').close=function(){this.removeAttribute('open');};
  const context=vm.createContext({document,window,location,console,setTimeout,clearTimeout,setInterval:()=>0,AbortController,
    fetch:async url=>{const key=url.match(/data\/(\w+)\.json/)[1];calls.push(key);if(failed.has(key))throw Error('Network unavailable');return {ok:true,json:async()=>read(key)};}});
  for(const s of scripts)vm.runInContext(s,context);
  const run=code=>vm.runInContext(code,context);
  await tick();await run('load()');
  const route=async hash=>{location.hash=hash;await run('load()');};
  return {window,document,run,route,calls,failed,context};
}

test('landing page uses only the small live resources and explains its focus',async()=>{
  const l=await lab();
  assert.deepEqual([...new Set(l.calls)].sort(),['presentation','risk','risk_status']);
  assert.match(l.document.querySelector('h1').textContent,/Forecasts, put to the test/);
  assert.match(l.document.querySelector('main').textContent,/how much markets may move/);
  assert.equal(l.document.querySelectorAll('.forecast-card').length,2);
  assert.match(l.document.querySelector('main').textContent,/not confidence intervals/);
  assert.equal(l.document.querySelector('[aria-current="page"]').getAttribute('href'),'#risk');
});

test('refresh failure retains forecasts, displays a warning and recovers',async()=>{
  const l=await lab(), id=l.run('S.risk.latest.forecastId');
  l.failed.add('risk');await l.run('load({force:true})');
  assert.equal(l.run('S.risk.latest.forecastId'),id);
  assert.match(l.document.querySelector('#health').textContent,/Refresh needs attention/);
  assert.match(l.document.querySelector('[role="alert"]').textContent,/could not be refreshed/);
  l.failed.clear();await l.run('load({force:true})');
  assert.equal(l.document.querySelector('[role="alert"]'),null);
  assert.doesNotMatch(l.document.querySelector('#health').textContent,/Refresh needs attention/);
});

test('forecast controls filter assets, switch targets, and open original estimates',async()=>{
  const l=await lab('#outlook');
  const search=l.document.querySelector('#risk-search');search.value='SPY';search.dispatchEvent(new l.window.Event('input'));
  assert.equal(l.document.querySelectorAll('#risk-table tbody tr').length,1);
  l.document.querySelector('#risk-table [data-risk-ticker]').click();
  assert.ok(l.document.querySelector('dialog').hasAttribute('open'));
  assert.match(l.document.querySelector('#detail-content').textContent,/Recent issues & outcomes/);
  l.document.querySelector('[data-risk-task="drawdown"]').click();
  assert.match(l.document.querySelector('#risk-table').textContent,/Historical frequency/);
  assert.doesNotMatch(l.document.querySelector('#risk-table').textContent,/GARCH/);
});

test('live and historical results remain distinct; QLIKE and Brier use separate sections',async()=>{
  const l=await lab('#record');
  assert.match(l.document.querySelector('main').textContent,/Prospective/);
  assert.ok(!l.calls.includes('risk_research'));
  l.document.querySelector('[data-risk-evidence="historical"]').click();await tick();await l.run('load()');
  assert.match(l.document.querySelector('main').textContent,/Historical development/);
  const sections=[...l.document.querySelectorAll('.section')];
  const variance=sections.find(s=>s.querySelector('h2')?.textContent==='Variance forecasts');
  const drawdown=sections.find(s=>s.querySelector('h2')?.textContent==='Drawdown probabilities');
  assert.match(variance.textContent,/QLIKE/);assert.doesNotMatch(variance.textContent,/Brier/);
  assert.match(drawdown.textContent,/Brier/);assert.doesNotMatch(drawdown.textContent,/QLIKE/);
});

test('all routes including the original direction deep links render without errors',async()=>{
  const l=await lab();
  for(const route of ['outlook','record','experiments','about','overview','forecasts','research','controls','portfolio','method']){
    await l.route('#'+route);
    assert.doesNotMatch(l.document.querySelector('main').textContent,/View error:|could not be displayed/,route);
    assert.ok(l.document.querySelector('main h1'),route);
  }
  await l.route('#about');assert.match(l.document.querySelector('main').textContent,/fitted monthly/);
  await l.route('#method');assert.match(l.document.querySelector('main').textContent,/calendar quarter/);
});

test('missing estimates stay missing, zero stays zero, and only units are converted',async()=>{
  const l=await lab();
  assert.equal(l.run('RiskUI.annual(null)'),null);
  assert.equal(l.run('RiskUI.annual(-1)'),null);
  assert.equal(l.run('RiskUI.annual(0)'),0);
  assert.equal(l.run('RiskUI.annual(1/252)'),1);
  assert.equal(l.run('pct(null)'),'—');assert.equal(l.run('pct(NaN)'),'—');assert.equal(l.run('pct(0)'),'0.0%');
});

test('freshness follows exchange sessions, next-open deadline, and calendar expiry',async()=>{
  const l=await lab();
  l.context.fixture={calendar:{validFrom:'2026-11-23T00:00:00Z',validUntil:'2026-12-02T00:00:00Z',sessions:[
    {date:'2026-11-25',open:'2026-11-25T14:30:00Z',close:'2026-11-25T21:00:00Z'},
    {date:'2026-11-27',open:'2026-11-27T14:30:00Z',close:'2026-11-27T18:00:00Z'},
    {date:'2026-11-30',open:'2026-11-30T14:30:00Z',close:'2026-11-30T21:00:00Z'}]}};
  l.context.snap={sessionDate:'2026-11-25',issuedAt:'2026-11-25T23:00:00Z',informationCutoff:'2026-11-25T21:00:00Z'};
  const at=date=>l.run(`RiskUI.freshness(snap,fixture,Date.parse('${date}'))`);
  assert.equal(at('2026-11-26T18:00:00Z').kind,'good');
  assert.equal(at('2026-11-27T18:01:00Z').kind,'pending');
  assert.equal(at('2026-11-29T18:00:00Z').kind,'pending');
  assert.equal(at('2026-11-30T14:30:00Z').label,'Newer forecast overdue');
  assert.equal(at('2026-12-03T14:30:00Z').label,'Freshness not verified');
});

test('a partially updated deployment does not mix histories from different reports',async()=>{
  const l=await lab();
  assert.ok(l.run('RiskUI.presentation()'));
  l.run("S.presentation.riskUpdatedAt='older report'");
  assert.equal(l.run('RiskUI.presentation()'),null);
  l.run('render()');
  assert.match(l.document.querySelector('#health').textContent,/Freshness not verified/);
});

test('synthetic evidence shows fitted models as well as the oracle',async()=>{
  const l=await lab('#experiments');
  const table=l.document.querySelector('[aria-label="Learners and oracle in synthetic worlds"]');
  assert.ok(table);
  for(const model of ['EWMA','HAR','GARCH','Oracle'])assert.match(table.textContent,new RegExp(model));
  assert.equal(table.querySelectorAll('tbody tr').length,read('risk_controls').runs.length);
});
