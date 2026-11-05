'use strict';
const REPO='https://github.com/PrototypeVersions/UnpricedZ';
const S={research:null,controls:null,live:null,market:null,status:null,risk:null,risk_research:null,risk_controls:null,risk_status:null,route:'risk',riskEvidence:'live',presentation:null,reader:null,resources:{},riskTask:'variance',riskSort:'ewma',riskSearch:'',period:'confirmation',portfolio:'live',forecastModel:'logistic',search:'',control:'0'};
const COLORS={logistic:'#116D68',raw_logistic:'#587A65',boosted:'#365F99',momentum:'#A34D38',base_rate:'#5F6B74',coin_flip:'#886318'};
const NAMES={logistic:'Regularized logistic',raw_logistic:'Before calibration',boosted:'Boosted challenger',momentum:'Momentum baseline',base_rate:'Historical base rate',coin_flip:'Constant 50%'};
const ROUTES={risk:'Overview',outlook:'Forecasts',record:'Results',experiments:'Research',methods:'Methods',about:'About',overview:'Direction overview',forecasts:'Direction forecasts',research:'Direction research',controls:'Direction controls',portfolio:'$1,000 experiment',method:'Direction methods'};
const $=s=>document.querySelector(s);
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=(v,n=2)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n});
const pct=(v,n=1)=>v==null||!Number.isFinite(v)?'—':`${num(v*100,n)}%`;
const signed=(v,n=4)=>v==null?'—':`${v>0?'+':''}${num(v,n)}`;
const spct=(v,n=1)=>v==null?'—':`${v>0?'+':''}${pct(v,n)}`;
const money=v=>v==null?'—':Number(v).toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
const date=x=>x?new Date(`${String(x).slice(0,10)}T12:00:00Z`).toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric',timeZone:'UTC'}):'Awaiting data';
const timestamp=x=>x?new Date(x).toLocaleString('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/New_York',timeZoneName:'short'}):'Not yet published';
const badge=(text,type='')=>`<span class="badge ${type}">${esc(text)}</span>`;
const empty=(title,description,link='')=>`<div class="empty"><span class="empty-icon">○</span><h3>${esc(title)}</h3><p>${esc(description)}</p>${link}</div>`;
const panel=(title,subtitle,body,foot='',right='')=>`<section class="panel"><div class="panel-head"><div><h2>${title}</h2>${subtitle?`<p>${subtitle}</p>`:''}</div>${right}</div>${body}${foot?`<div class="panel-foot">${foot}</div>`:''}</section>`;
const stat=(label,value,note='',color='')=>`<article class="stat"><div class="label">${label}</div><strong class="${color}">${value}</strong><small>${note}</small></article>`;
const header=(eyebrow,title,description)=>`<div class="page-header"><div><span class="eyebrow">${eyebrow}</span><h1>${title}</h1><p>${description}</p></div><div class="date-badge">LATEST MARKET SESSION<strong>${date(RiskUI.isRisk(S.route)?S.risk?.latest?.sessionDate:S.live?.latest?.sessionDate||S.market?.asOf)}</strong></div></div>`;
const links=(items)=>`<div class="link-list">${items.map(([text,url])=>`<a href="${esc(url)}" target="_blank" rel="noopener">${text} ↗</a>`).join('')}</div>`;
function openDetail(html){$('#detail-content').innerHTML=html;GuideUI.localize($('#detail-content'));$('#detail').showModal();}
function metric(id,summary){return summary?.models?.find(m=>m.id===id);}
function intervalText(v,n=4){return v?.low==null?'More forecast dates needed':`${signed(v.low,n)} to ${signed(v.high,n)}`;}
function verdict(v){if(!v||v.low==null)return 'Insufficient evidence';return v.low>0?'Positive estimate · confirmation required':v.high<0?'Baseline currently stronger':'No clear improvement';}
function selectedSummary(){return S.period==='all'?S.research?.summary:S.research?.periods?.[S.period];}
function legend(series){return `<div class="legend">${series.map(s=>`<span><i style="background:${s.color}"></i>${esc(s.label)}</span>`).join('')}</div>`;}
function lineChart(rows,series,{height=228,zero=false,format=v=>num(v,3),label='Historical observations'}={}){
  if(!rows?.length)return empty('Evidence is still accumulating','The chart appears when the corresponding observations are available.');
  const W=typeof window!=='undefined'&&window.innerWidth<640?390:700,H=height,p={l:58,r:12,t:14,b:29},iw=W-p.l-p.r,ih=H-p.t-p.b;
  const values=series.flatMap(s=>rows.map(r=>r[s.key]).filter(v=>v!=null&&Number.isFinite(v)));
  if(!values.length)return empty('No values in this period','Select another period.');
  let min=Math.min(...values),max=Math.max(...values);if(zero){min=Math.min(min,0);max=Math.max(max,0);}
  const spread=Math.max(max-min,Math.abs(max)*.08,.0001);min-=spread*.10;max+=spread*.10;
  const x=i=>p.l+(rows.length>1?i/(rows.length-1):.5)*iw,y=v=>p.t+(max-v)/(max-min)*ih;
  let content='';
  for(let i=0;i<4;i++){const v=min+(max-min)*i/3,yy=y(v);content+=`<line class="gridline" x1="${p.l}" y1="${yy}" x2="${W-p.r}" y2="${yy}"/><text x="${p.l-9}" y="${yy+3}" text-anchor="end">${esc(format(v))}</text>`;}
  if(zero&&min<0&&max>0)content+=`<line class="zero" x1="${p.l}" y1="${y(0)}" x2="${W-p.r}" y2="${y(0)}"/>`;
  series.forEach(s=>{let path='',started=false;const step=Math.max(1,Math.floor(rows.length/700));rows.forEach((r,i)=>{if(i%step&&i!==rows.length-1)return;const v=r[s.key];if(v==null||!Number.isFinite(v)){started=false;return;}path+=`${started?'L':'M'}${x(i).toFixed(2)},${y(v).toFixed(2)} `;started=true;});content+=`<path d="${path}" fill="none" stroke="${s.color}" stroke-width="1.8" vector-effect="non-scaling-stroke"/>`;});
  for(const [i,anchor] of [[0,'start'],[Math.floor((rows.length-1)/2),'middle'],[rows.length-1,'end']])content+=`<text x="${x(i)}" y="${H-5}" text-anchor="${anchor}">${esc(String(rows[i].date).slice(0,7))}</text>`;
  return `<svg class="chart" role="img" aria-label="${esc(label)}" viewBox="0 0 ${W} ${H}"><title>${esc(label)}</title>${content}</svg>`;
}
function advantageChart(summary){
  const sums={logistic:0,boosted:0,momentum:0};
  const rows=(summary?.daily||[]).map((r,i)=>{const out={date:r.date};for(const k in sums){sums[k]+=r[k]||0;out[k]=sums[k]/(i+1);}return out;});
  const series=['logistic','boosted','momentum'].map(k=>({key:k,label:NAMES[k],color:COLORS[k]}));
  return `<div class="panel-body">${legend(series)}<div class="chart-wrap">${lineChart(rows,series,{zero:true,format:v=>signed(v,3),label:'Cumulative mean Brier improvement over the historical base-rate forecast; positive is better'})}</div></div>`;
}
function sectors(){
  const rows=[...(S.market?.sectors||[])].sort((a,b)=>b.relative20d-a.relative20d);
  if(!rows.length)return empty('Market data pending','The first successful data cycle will populate measured sector conditions.');
  const max=Math.max(...rows.map(r=>Math.abs(r.relative20d)),.01);
  return `<div class="panel-body">${rows.map(r=>`<div class="sector-row"><span class="symbol" title="${esc(r.name)}">${esc(r.ticker)}</span><div class="bar-track"><i class="bar-fill" style="width:${Math.abs(r.relative20d)/max*50}%;left:${r.relative20d>=0?50:50-Math.abs(r.relative20d)/max*50}%;background:${r.relative20d>=0?'var(--lime)':'var(--coral)'}"></i></div><span class="value ${r.relative20d>=0?'lime':'coral'}">${spct(r.relative20d)}</span></div>`).join('')}</div>`;
}
const RISK_NAMES={ewma:'EWMA',har_daily:'HAR · daily data',garch11:'GARCH(1,1)',base_rate:'Event frequency',volatility_only:'Volatility-only logistic'};
function riskDecomposition(summary){
  const rows=Object.entries(summary?.groups||{}).flatMap(([group,s])=>s.models.filter(m=>m.task==='variance'&&m.decomposition).map(m=>({group,...m.decomposition,model:m.model})));
  if(!rows.length)return '';
  return `<details class="risk-details"><summary>Inspect variance loss concentration</summary><p class="small-note">Date-level medians and the worst ceil(1% × dates) date losses. Excluding 2020 is a diagnostic; the all-date mean above remains the primary result.</p><div class="table-scroll"><table class="data-table"><thead><tr><th>Group / model</th><th>Median QLIKE</th><th>Worst 1% share</th><th>Mean excluding 2020</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.group)} · ${esc(RISK_NAMES[r.model])}</td><td class="num">${num(r.medianDateQLIKE,4)}</td><td class="num">${pct(r.worstDateShare)}<small>${r.worstDateCount} dates</small></td><td class="num">${num(r.excluding2020MeanQLIKE,4)}</td></tr>`).join('')}</tbody></table></div></details>`;
}
function overview(){
  const historical=S.research?.periods?.confirmation,primary=metric('logistic',historical),live=S.live;
  const nulls=S.controls?.groups?.find(g=>g.strength===0);
  return `${header('OBSERVE / TEST / VERIFY','A market research laboratory.','Forecasts are hypotheses. Their record is the evidence.')}
  <section class="hero"><div><span class="badge lime">UNPRICED · RESEARCH EDITION 02</span><h2>Test ideas.<br><span>Keep the evidence.</span></h2><p>Explore sector forecasts, measure uncertainty, and compare each model with a simpler explanation. Every live forecast is recorded before its outcome.</p><a class="text-link" href="#research">Explore the research <span>↗</span></a></div><div class="hero-right"><span class="eyebrow">PRESPECIFIED 2025 CONFIRMATION / LOGISTIC</span><div class="big-stat ${primary?.improvement?.mean>0?'lime':''}">${primary?signed(primary.improvement.mean,4):'PENDING'}</div><p>Brier improvement over the historical base rate.<br><strong>${primary?verdict(primary.improvement):'The first historical evaluation is being prepared.'}</strong></p><p class="small-note">${primary?`95% date-block interval: ${intervalText(primary.improvement)}. Positive values favor the model.`:'No historical result is displayed as live performance.'}</p></div></section>
  <div class="stat-grid">${stat('Historical forecast dates',S.research?num(S.research.summary.dates,0):'—','Chronological tests since 2016')}${stat('Live forecast dates',num(live?.forecastDates||0,0),`${num(live?.summary?.dates||0,0)} dates with resolved outcomes`,'lime')}${stat('Null-control detections',nulls?`${nulls.detections} / ${nulls.runs}`:'—','Synthetic markets with no directional signal')}${stat('Market volatility',pct(S.market?.annualizedVol),'SPY · trailing 20 sessions · annualized')}</div>
  <div class="grid-two">${panel('Does complexity add value?','Historical 2025 confirmation · cumulative average',advantageChart(historical),'Above zero: lower Brier loss than the base-rate forecast. This is historical evidence.',`<a href="#research">Inspect all periods ↗</a>`)}${panel('The sector landscape','20-session performance relative to SPY',sectors(),'Measured price behavior; not a forecast.',badge('9 legacy sectors'))}</div>
  <div class="evidence-note"><strong>Evidence has boundaries.</strong> Research uses provider-adjusted historical data. Live results begin only with this version’s first publication. No model is automatically promoted because it wins a short comparison.</div>
  <div class="callout-grid"><a href="#forecasts"><span class="eyebrow">01 / FORWARD</span><span class="arrow">↗</span><h3>What are the models expecting?</h3><p>Five-session relative returns, probability estimates, and risk.</p></a><a href="#controls"><span class="eyebrow">02 / FALSIFICATION</span><span class="arrow">↗</span><h3>Can the lab distinguish noise?</h3><p>Inspect every null and planted-signal experiment.</p></a><a href="#method"><span class="eyebrow">03 / REPRODUCIBILITY</span><span class="arrow">↗</span><h3>Open the notebook.</h3><p>Targets, data boundaries, limitations, and archived inputs.</p></a></div>`;
}
function range(f){const lo=Math.max(0,Math.min(100,50+f.lower80*500)),hi=Math.max(0,Math.min(100,50+f.upper80*500)),point=Math.max(0,Math.min(100,50+f.expectedExcess*500));return `<div class="range" title="Empirical 80% residual band: ${spct(f.lower80,2)} to ${spct(f.upper80,2)}"><i class="center"></i><i class="band" style="left:${lo}%;width:${Math.max(hi-lo,1)}%"></i><i class="point" style="left:${point}%"></i></div><small>${spct(f.lower80,1)} to ${spct(f.upper80,1)}</small>`;}
function forecasts(){
  const snap=S.live?.latest;
  let body=header('FROZEN BEFORE OUTCOMES','The next five sessions.','Relative-performance probabilities and risk estimates for nine sector ETFs.');
  if(!snap)return body+panel('Prospective forecast record','Awaiting a valid publication window',empty('No live forecast has been published yet','A new snapshot can be issued only after a completed market session and before its target entry open. Missed windows remain missed.',links([['Check pipeline',`${REPO}/actions`]])));
  const key=`p_${S.forecastModel}`;
  const rows=snap.forecasts.filter(f=>`${f.ticker} ${f.name}`.toLowerCase().includes(S.search.toLowerCase())).sort((a,b)=>b[key]-a[key]);
  body+=`<div class="stat-grid">${stat('Information through',date(snap.sessionDate),'Official market close')}${stat('Reference entry',date(snap.entryDate),'Next session opening price')}${stat('Reference exit',date(snap.exitDate),'Fifth session closing price')}${stat('Publication',new Date(snap.publishedAt).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:'America/New_York'}),'Eastern time · actual issue time','lime')}</div>
  <div class="toolbar"><div class="field"><label for="model-select">Probability model</label><select id="model-select">${['logistic','raw_logistic','boosted','momentum','base_rate','coin_flip'].map(m=>`<option value="${m}" ${m===S.forecastModel?'selected':''}>${NAMES[m]}</option>`).join('')}</select></div><input id="search" class="search" type="search" value="${esc(S.search)}" placeholder="Find a sector or ticker" aria-label="Find a sector or ticker"></div>
  ${panel('Sector forecasts','Select a row to inspect component models and input values',`<div class="table-scroll"><table class="data-table"><thead><tr><th>Sector / ETF</th><th>P(outperform SPY)</th><th>Expected excess</th><th>80% residual band</th><th>Expected volatility</th><th></th></tr></thead><tbody>${rows.length?rows.map(f=>`<tr class="clickable" data-ticker="${esc(f.ticker)}" tabindex="0" role="button" aria-label="Inspect ${esc(f.name)} forecast"><td><span class="ticker">${esc(f.ticker)}</span><small>${esc(f.name)}</small></td><td><div class="probability"><span>${pct(f[key])}</span><div class="prob-track"><span style="width:${f[key]*100}%"></span></div></div></td><td class="num ${f.expectedExcess>=0?'lime':'coral'}">${spct(f.expectedExcess,2)}</td><td>${range(f)}</td><td class="num">${pct(Math.sqrt(252*f.harVariance))}<small>Annualized · daily variance proxy</small></td><td class="muted">↗</td></tr>`).join(''):'<tr><td colspan="6">No sectors match this search.</td></tr>'}</tbody></table></div>`,'Probability refers to beating SPY, not making a positive return. Bands are empirical residual ranges; conditional coverage is not guaranteed.',badge('LIVE SHADOW','lime'))}
  <div class="evidence-note"><strong>These are experimental forecasts.</strong> A higher displayed probability is not proof of a reliable opportunity. The models retain separate scores, and the paper policy uses only its predeclared rules.</div>`;
  return body;
}
function forecastDetail(ticker){const snap=S.live.latest,f=snap.forecasts.find(x=>x.ticker===ticker),features=snap.features.find(x=>x.ticker===ticker);openDetail(`<span class="eyebrow">${esc(f.name)} / FIVE SESSIONS</span><h2>${esc(ticker)} · forecast record</h2><p>Published ${timestamp(snap.publishedAt)}. Target ${date(snap.entryDate)} open through ${date(snap.exitDate)} close.</p><div class="stat-grid">${stat('P(outperform)',pct(f.p_logistic),'Calibrated logistic','lime')}${stat('Expected excess',spct(f.expectedExcess,2),'Ridge regression')}${stat('Expected volatility',pct(Math.sqrt(252*f.harVariance)),'Annualized proxy')}</div><dl class="key-values">${Object.entries(NAMES).map(([k,n])=>`<div><dt>${n}</dt><dd>${pct(f[`p_${k}`],2)}</dd></div>`).join('')}<div><dt>80% residual range</dt><dd>${spct(f.lower80,2)} to ${spct(f.upper80,2)}</dd></div><div><dt>Fitting dates</dt><dd>${esc(snap.model.training.fitStart)} to ${esc(snap.model.training.fitEnd)}</dd></div><div><dt>Calibration dates</dt><dd>${esc(snap.model.training.calibrationStart)} to ${esc(snap.model.training.calibrationEnd)}</dd></div></dl><details><summary class="small-note">Exact feature values</summary><dl class="key-values">${Object.entries(features).filter(([k])=>k!=='ticker').map(([k,v])=>`<div><dt>${esc(k)}</dt><dd><code>${num(v,6)}</code></dd></div>`).join('')}</dl></details>${links([['Immutable snapshot',`${REPO}/blob/main/records/forecasts/${snap.sessionDate}.json`],['Input vintage',`${REPO}/blob/main/${snap.inputVintage.path}`]])}`);}
function modelTable(summary){return `<div class="table-scroll"><table class="data-table"><thead><tr><th>Model</th><th>Brier ↓</th><th>Log loss ↓</th><th>Gain vs base rate ↑</th><th>95% date-block interval</th></tr></thead><tbody>${(summary?.models||[]).map(m=>`<tr><td><span class="model-name"><i class="model-dot" style="background:${COLORS[m.id]}"></i>${esc(m.name)}</span></td><td class="num">${num(m.brier,4)}</td><td class="num">${num(m.logLoss,4)}</td><td class="num ${m.improvement?.mean>0?'lime':m.improvement?.mean<0?'coral':''}">${signed(m.improvement?.mean,4)}</td><td class="num">${m.id==='base_rate'?'Reference':intervalText(m.improvement)}</td></tr>`).join('')}</tbody></table></div>`;}
function calibration(summary){const m=metric('logistic',summary);if(!m?.calibration?.length)return empty('Calibration pending','Resolved observations are needed to compare forecast probabilities with outcome frequencies.');const rows=m.calibration;return `<div class="panel-body"><div class="table-scroll"><table class="data-table"><thead><tr><th>Probability group</th><th>Mean forecast</th><th>Observed</th><th>Rows</th></tr></thead><tbody>${rows.map(b=>`<tr><td>${pct(b.low,0)}–${pct(b.high,0)}</td><td class="num">${pct(b.predicted)}</td><td class="num">${pct(b.observed)}</td><td class="num">${num(b.count,0)}</td></tr>`).join('')}</tbody></table></div></div>`;}
function research(){
  let body=header('HISTORICAL / PROSPECTIVE','Make the comparison fair.','The same target, the same dates, and an explicit baseline for every model.');
  body+=`<div class="toolbar"><div class="tabs" aria-label="Evaluation period">${[['confirmation','2025 confirmation'],['development','2016–24 development'],['recent','2026 recent'],['all','All historical'],['live','Live record']].map(([id,t])=>`<button data-period="${id}" class="${S.period===id?'selected':''}">${t}</button>`).join('')}</div>${badge(S.period==='live'?'PROSPECTIVE':'HISTORICAL',S.period==='live'?'lime':'blue')}</div>`;
  const summary=S.period==='live'?S.live?.summary:selectedSummary();
  if(!summary?.dates)return body+panel('Evaluation record','A result is shown only when it exists',empty(S.period==='live'?'Live outcomes have not matured yet':'Historical evaluation is pending',S.period==='live'?'The first five-session outcomes will become available after the stated exit date. A prediction count is not a count of independent experiments.':'The pipeline is running its chronological tests. Results will appear here after successful completion.',links([['Pipeline runs',`${REPO}/actions`]])));
  body+=`<div class="stat-grid">${stat('Forecast dates',num(summary.dates,0),`${date(summary.start)} – ${date(summary.end)}`,'lime')}${stat('Sector observations',num(summary.observations,0),'Rows share dates and market conditions')}${stat('Rank correlation',num(summary.rankIC?.mean,3),'Secondary diagnostic · expected vs realized')}${stat('80% band coverage',pct(summary.intervalCoverage80),'Observed coverage · not a guarantee')}</div>`;
  body+=panel('Probability quality','Lower Brier and log loss are better. Positive gain favors the candidate.',modelTable(summary),'All candidates are compared on the same complete observations. No ensemble reweights itself from a few days of outcomes.');
  body+=`<div style="margin-top:22px">${panel('Advantage over the base rate','Cumulative mean of paired, date-level Brier differences',advantageChart(summary),'The line summarizes observed performance; its movement is not a confidence interval.')}</div>`;
  body+=`<div class="grid-equal" style="margin-top:22px">${panel('Do probabilities match frequencies?','Calibrated logistic · pooled probability bins',calibration(summary),'These bins contain correlated observations. Interpret alongside date-level uncertainty.')}${panel('A separate question: can we forecast risk?','Five-session daily-sampled variance proxy',`<div class="panel-body">${(summary.risk||[]).map(r=>`<dl class="key-values"><div><dt>${esc(r.name)}</dt><dd>QLIKE ${num(r.qlike,4)}</dd></div></dl>`).join('')}<div class="evidence-note"><strong>${verdict(summary.risk?.[1]?.improvement)}</strong><br>Mean QLIKE improvement: ${signed(summary.risk?.[1]?.improvement?.mean,4)}.<br>95% interval: ${intervalText(summary.risk?.[1]?.improvement)}.</div><p class="small-note">Volatility skill does not imply return-direction skill. EWMA is the reference; the challenger is a HAR-style regression on daily squared returns.</p></div>`,'Risk and return forecasts are evaluated independently.')}</div>`;
  if(S.period!=='live')body+=`<div class="evidence-note"><strong>Historical evidence.</strong> Data were downloaded today and may include provider revisions. The confirmation year was fixed before the initial run; after its first inspection it is no longer an untouched test for future redesigns.</div>${links([['Full research JSON','data/research.json'],['Prediction archive',`${REPO}/blob/main/${S.research.predictionsArchive.path}`],['Fold boundaries',`${REPO}/blob/main/${S.research.archivePath}`]])}`;
  return body;
}
function controls(){
  let body=header('FALSIFICATION / DETECTION','First, test the laboratory.','Can the pipeline resist false discoveries and recover a relationship we deliberately planted?');
  const c=S.controls;if(!c)return body+panel('Synthetic controls','Production pipeline · fixed seeds',empty('Controls are running','The full feature, fitting, calibration, and evaluation pipeline is exercised on synthetic markets. Results are published whether detection is strong or weak.',links([['Inspect the run',`${REPO}/actions`]])));
  body+=`<div class="mini-grid">${c.groups.map((g,i)=>`<article class="control-card"><span class="eyebrow">EXPERIMENT 0${i+1}</span><h3>${esc(g.name)}</h3><div class="rate">${g.detections}<small> / ${g.runs} detections</small></div><p>${i===0?'A detection here is a false positive under this generator.':'A detection requires the 95% date-block interval to be entirely above zero.'}</p><div class="bar-track"><span class="bar-fill" style="left:0;width:${g.detectionRate*100}%;background:${i===0?'var(--coral)':'var(--lime)'}"></span></div><p class="small-note">Rate interval: ${pct(g.rateInterval95[0],0)}–${pct(g.rateInterval95[1],0)}<br>Mean Brier gain over 50%: ${signed(g.meanImprovement,4)}</p></article>`).join('')}</div>`;
  body+=`<div class="evidence-note"><strong>A diagnostic, not a certificate.</strong> ${c.groups[0].runs} seeds cannot tightly establish a 5% false-positive rate. Weak detection is retained in the record. A risk model can succeed in the directional-null market because volatility still changes predictably.</div>
  <div class="toolbar"><h2 style="font-size:16px;font-weight:450">Every run stays visible.</h2><label class="field">Experiment <select id="control-select">${c.groups.map(g=>`<option value="${g.strength}" ${String(g.strength)===S.control?'selected':''}>${esc(g.name)}</option>`).join('')}</select></label></div>
  ${panel('Seed-level results','Regularized, calibrated logistic · production model',`<div class="table-scroll"><table class="data-table"><thead><tr><th>Seed</th><th>Forecast dates</th><th>Brier</th><th>Gain vs constant 50%</th><th>95% interval</th><th>Detection</th></tr></thead><tbody>${c.runs.filter(r=>String(r.strength)===S.control).map(r=>`<tr><td class="num">${r.seed}</td><td class="num">${r.dates}</td><td class="num">${num(r.brier,4)}</td><td class="num">${signed(r.improvement.mean,4)}</td><td class="num">${intervalText(r.improvement)}</td><td>${badge(r.positiveDetection?'Detected':'Not detected',r.positiveDetection?'gold':'')}</td></tr>`).join('')}</tbody></table></div>`,'No results are discarded because they contradict the desired conclusion.')}
  ${links([['All model results','data/controls.json'],['Generator and protocol',`${REPO}/blob/main/unpriced/controls.py`]])}`;
  return body;
}
function portfolio(){
  let body=header('PAPER PORTFOLIO / PREDECLARED POLICY','$1,000 trading experiment.','The continuing sector-direction strategy. Five-session holds, modeled costs, and cash when no entries qualify.');
  body+=GuideUI.portfolioIntro();
  body+=`<div class="toolbar"><div class="tabs"><button data-portfolio="live" class="${S.portfolio==='live'?'selected':''}">Prospective plans</button><button data-portfolio="historical" class="${S.portfolio==='historical'?'selected':''}">Historical simulation</button></div>${badge('PAPER · NO BROKER FILLS','gold')}</div>`;
  const live=S.portfolio==='live',p=live?S.live?.portfolio:S.research?.portfolio;
  if(!p)return body+panel('Paper record','No invented activity',empty('No paper record yet','The first completed pipeline creates the reference-return experiment. It remains distinct from actual execution.'));
  const equity=live?p.settledEquity:p.equity,bench=live?p.settledBenchmark:p.benchmark;
  body+=`<div class="stat-grid">${stat(live?'Settled equity':'Simulated final equity',money(equity),'Starts at $1,000','lime')}${stat('Reference SPY',money(bench),'Identical holding windows')}${stat('Return',spct(equity/1000-1,2),live?'Settled cohorts only':'After modeled costs')}${stat('Cost assumption','10 bps','Each side of each position')}</div>
  ${panel('Capital through the experiment',live?'Only settled cohorts change this chart':'Historical, non-overlapping five-session cohorts',`<div class="panel-body">${legend([{label:'Paper policy',color:COLORS.logistic},{label:'SPY · matched windows',color:COLORS.base_rate}])}${lineChart(p.curve,[{key:'equity',label:'Policy',color:COLORS.logistic},{key:'benchmark',label:'SPY',color:COLORS.base_rate}],{format:v=>`$${num(v,0)}`,label:'Reference portfolio and SPY equity across identical holding windows'})}</div>`,'The comparator is not continuous buy-and-hold SPY. Both exclude overnight exposure between cohorts; cash earns zero.')}`;
  if(live){body+=`<div style="margin-top:22px">${panel('Frozen prospective plans','Allocations are recorded before the intended entry open',p.plans?.length?`<div class="table-scroll"><table class="data-table"><thead><tr><th>Signal</th><th>Entry → exit</th><th>Allocations</th><th>Cash</th><th>Status</th></tr></thead><tbody>${[...p.plans].reverse().map(x=>`<tr><td class="num">${x.signalDate}</td><td class="num">${x.entryDate} → ${x.exitDate}</td><td>${x.allocations.length?x.allocations.map(a=>`${a.ticker} ${pct(a.weight,0)}`).join(' · '):'No qualifying entries'}</td><td class="num">${pct(x.cashWeight,0)}</td><td>${badge(x.status,x.status==='resolved'?'lime':'gold')}</td></tr>`).join('')}</tbody></table></div>`:empty('No allocation plan yet','A plan is created with an eligible live forecast. It can hold entirely cash.'),'Unresolved plans are not represented as zero-return trades.')}</div>`;}
  else body+=`<div class="split-title"><h2>Historical positions</h2><span class="eyebrow">${p.positionCount} TOTAL</span></div>${panel('Most recent positions','Fixed exits; thresholds were not optimized',p.trades?.length?`<div class="table-scroll"><table class="data-table"><thead><tr><th>ETF</th><th>Signal date</th><th>Entry</th><th>Exit</th><th>Weight</th><th>Reference return</th></tr></thead><tbody>${p.trades.slice(-30).reverse().map(t=>`<tr><td class="ticker">${t.ticker}</td><td class="num">${t.signalDate}</td><td class="num">${t.entryDate}</td><td class="num">${t.exitDate}</td><td class="num">${pct(t.weight,0)}</td><td class="num">${spct(t.return,2)}</td></tr>`).join('')}</tbody></table></div>`:empty('The policy remained in cash','No historical candidates met the predeclared rules.'),'Opening prices are adjusted research references, not verified executable fills.')}`;
  return body+GuideUI.portfolioDetails({showDecision:live});
}
function method(){return `${header('OPEN METHODS / KNOWN LIMITS','The lab notebook.','Enough detail to understand the experiment—and reproduce its results.')}
  <div class="method-grid">
  <article class="method-card"><span class="number">01 / THE QUESTION</span><h2>A precise target.</h2><p>For each of nine legacy US sector ETFs, predict its return relative to SPY from the next trading session’s opening price through the fifth session’s closing price. A relative winner can still lose money.</p><p>A separate model forecasts the average squared daily log-return legs over that same window, displayed as annualized volatility. This is a daily-sampled proxy, not high-frequency realized variance.</p></article>
  <article class="method-card"><span class="number">02 / INFORMATION BOUNDARIES</span><h2>Only information available then.</h2><p>Models fit on a rolling five-year development window. The last 126 eligible forecast dates are reserved for calibration. Training outcomes must finish before calibration begins; calibration outcomes must finish by the fitting cutoff.</p><p>Models remain frozen within each calendar quarter. Live publication occurs after the close and before the target entry open. A late run cannot invent a forecast after entry.</p></article>
  <article class="method-card"><span class="number">03 / COMPARISON</span><h2>Give the baseline a fair chance.</h2><p>Constant 50%, historical base rate, and momentum forecasts sit beside uncalibrated logistic, calibrated logistic, and a fixed-complexity boosted challenger. There is no class balancing and no random early-stopping holdout.</p><p>Brier and log loss assess probabilities. Paired daily losses are compared using a 20-session block bootstrap. Rank correlation and calibration bins are secondary diagnostics. No automatic ensemble weighting or promotion.</p></article>
  <article class="method-card"><span class="number">04 / FALSIFICATION</span><h2>Run worlds with known structure.</h2><p>Synthetic markets retain shared factors and changing volatility. The directional-null world has symmetric conditional relative log returns. Positive controls introduce a lagged-momentum effect that the production features can observe.</p><p>Every seed is preserved, including false positives and missed signals. Small simulation batches provide diagnostics, not guarantees.</p></article>
  <article class="method-card"><span class="number">05 / DATA REALISM</span><h2>Archive the input, name the limits.</h2><p>The initial adapter uses Yahoo Finance through yfinance. Historical adjusted prices may have been revised. This is retrospective research, not a reconstructed archive of what the provider published years ago.</p><p>Training vintages, daily inputs, feature values, model artifacts, code revisions, and resolved outcomes are archived. Both return endpoints use the same data vintage. The nine selected ETFs are not the entire stock market or all modern sectors.</p></article>
  <article class="method-card"><span class="number">06 / WHAT COMES NEXT</span><h2>Changes must earn their place.</h2><p>The first specification fixes 2016–2024 as development and 2025 as confirmation. After inspection, that confirmation period cannot be called untouched for a redesigned model. New specifications need fresh evidence and separate records.</p><p>Event and economic-network models are future experiments. They are not implied by the present forecasts. Data availability, provenance, and incremental value come before complexity.</p></article>
  </div>${links([['Full methodology',`${REPO}/blob/main/docs/METHODOLOGY.md`],['Research protocol',`${REPO}/blob/main/docs/PROTOCOL.md`],['Upgrade experiments',`${REPO}/blob/main/docs/RESEARCH_PROGRAM.md`],['Two-lab strategy',`${REPO}/blob/main/docs/MULTI_LAB_STRATEGY.md`],['Cross-review brief',`${REPO}/blob/main/docs/CROSS_REVIEW_BRIEF.md`],['Operations & scheduled reviews',`${REPO}/blob/main/docs/OPERATIONS.md`],['Integrity tests',`${REPO}/blob/main/tests/test_integrity.py`]])}
  <div class="evidence-note"><strong>Two independent experiments.</strong> The original UNPRICED V1 remains at its existing repository and address. Research edition 02 has its own methodology, predictions, and performance record. Neither inherits the other’s results.</div>`;}
function showAudit(){const r=S.research,s=S.live?.latest;openDetail(`<span class="eyebrow">DATA / REPRODUCIBILITY</span><h2>Follow the evidence.</h2><dl class="key-values"><div><dt>Experiment</dt><dd>research-2.0.0</dd></div><div><dt>Pipeline status</dt><dd>${esc(S.status?.status||'awaiting first run')}</dd></div><div><dt>Last successful cycle</dt><dd>${timestamp(S.status?.lastSuccessfulAt)}</dd></div><div><dt>Latest live publication</dt><dd>${timestamp(s?.publishedAt)}</dd></div><div><dt>Live input hash</dt><dd><code>${esc(s?.inputVintage?.csvSha256||'Pending')}</code></dd></div><div><dt>Research input range</dt><dd>${r?`${r.inputVintage.start} → ${r.inputVintage.end}`:'Pending'}</dd></div><div><dt>Research source revision</dt><dd><code>${esc(r?.provenance?.codeCommit||'Pending')}</code></dd></div><div><dt>Research input hash</dt><dd><code>${esc(r?.inputVintage?.csvSha256||'Pending')}</code></dd></div></dl>${S.status?.error?`<div class="evidence-note error"><strong>Last cycle error</strong><br>${esc(S.status.error)}</div>`:''}${links([['Repository',REPO],['Workflow history',`${REPO}/actions`],...(r?[['Archived research input',`${REPO}/blob/main/${r.inputVintage.path}`],['Research report','data/research.json']]:[]),...(s?[['Latest forecast',`${REPO}/blob/main/records/forecasts/${s.sessionDate}.json`]]:[])])}<p>Files carry content hashes and source revisions. The research adapter can revise historical prices; archived vintages preserve exactly the data used by this experiment.</p>`);}
function bind(){
  document.querySelectorAll('[data-risk-evidence]').forEach(b=>b.addEventListener('click',()=>{S.riskEvidence=b.dataset.riskEvidence;load();}));
  document.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>{S.period=b.dataset.period;render();}));
  document.querySelectorAll('[data-portfolio]').forEach(b=>b.addEventListener('click',()=>{S.portfolio=b.dataset.portfolio;load();}));
  $('#model-select')?.addEventListener('change',e=>{S.forecastModel=e.target.value;render();});
  $('#control-select')?.addEventListener('change',e=>{S.control=e.target.value;render();});
  $('#search')?.addEventListener('input',e=>{const pos=e.target.selectionStart;S.search=e.target.value;render();$('#search').focus();try{$('#search').setSelectionRange(pos,pos);}catch{}});
  document.querySelectorAll('[data-ticker]').forEach(row=>{row.addEventListener('click',()=>forecastDetail(row.dataset.ticker));row.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();forecastDetail(row.dataset.ticker);}});});
}
// Each view requests only the records it needs. Static research is cached until
// a manual refresh; live data is rechecked every five minutes while visible.
function routeFromHash() {
  const hash=location.hash.slice(1);
  return hash==='main'?S.route:ROUTES[hash]?hash:'risk';
}
function dependencies(route=S.route) {
  if(RiskUI.isRisk(route)) {
    const keys=['risk','risk_status','presentation'];
    if(route==='experiments')keys.push('risk_research','risk_controls');
    if(['about','methods'].includes(route))keys.push('reader');
    if(route==='record'&&S.riskEvidence==='historical')keys.push('risk_research');
    return keys;
  }
  const views={overview:['research','controls','live','market'],forecasts:['live'],research:['research','live'],controls:['controls'],portfolio:['live','reader',...(S.portfolio==='historical'?['research']:[])],method:[]};
  return ['status',...(views[route]||[])];
}
function validateResource(key,value) {
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Invalid JSON record');
  if(key==='risk'&&(!Array.isArray(value.history)||!Number.isFinite(value.forecastDates)||(value.latest&&!Array.isArray(value.latest.forecasts))))throw Error('Invalid forecast record');
  if(key==='reader'&&(!value.builtAt||!value.hub))throw Error('Invalid reader context');
  if(key==='presentation'&&(!Array.isArray(value.history)||!Array.isArray(value.calendar?.sessions)))throw Error('Invalid presentation record');
  if((key==='risk_status'||key==='status')&&typeof value.status!=='string')throw Error('Invalid operational status');
  return value;
}
const requests=new Map();
async function fetchResource(key,force=false) {
  if(requests.has(key))return requests.get(key);
  const state=S.resources[key]||(S.resources[key]={});
  const historical=['research','controls','risk_research','risk_controls'].includes(key);
  if(!force&&S[key]&&state.loadedAt&&!state.error&&(historical||Date.now()-Date.parse(state.loadedAt)<300000))return;
  const request=(async()=>{
    const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),20000);
    try {
      const response=await fetch(`data/${key}.json`,{cache:'no-cache',signal:abort.signal});
      if(!response.ok)throw Error(`HTTP ${response.status}`);
      S[key]=validateResource(key,await response.json());
      state.loadedAt=new Date().toISOString();state.error=null;
    } catch(error) {state.error=String(error.message||error);}
    finally {clearTimeout(timer);requests.delete(key);}
  })();
  requests.set(key,request);
  return request;
}
function render(){
  S.route=routeFromHash();
  document.querySelectorAll('[data-route]').forEach(a=>{a.classList.toggle('active',a.dataset.route===S.route);if(a.dataset.route===S.route)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  $('#crumb').textContent=ROUTES[S.route];
  const riskRoute=RiskUI.isRisk(S.route);
  const currentStatus=riskRoute?S.risk_status:S.status;
  const views={risk:RiskUI.home,outlook:RiskUI.forecasts,record:RiskUI.results,experiments:RiskUI.experiments,about:GuideUI.about,methods:GuideUI.methods,overview,forecasts,research,controls,portfolio,method};
  const failures=dependencies().filter(k=>S.resources[k]?.error);
  const f=riskRoute?RiskUI.freshness(S.risk?.latest,RiskUI.presentation()):null;
  let warning='';
  if(failures.length)warning+=`<div class="evidence-note error" role="alert"><strong>Some records could not be refreshed.</strong> Last fetched data is retained where available. Affected: ${esc(failures.join(', '))}. Use Refresh to retry.</div>`;
  if(currentStatus?.status==='error')warning+=`<div class="evidence-note error"><strong>The last pipeline run needs attention.</strong> ${esc(currentStatus.error)} <a href="${REPO}/actions">Inspect runs ↗</a></div>`;
  if(riskRoute&&f.kind==='warn'&&S.risk?.latest)warning+=`<div class="evidence-note"><strong>${esc(f.label)}.</strong> Displaying the issue from ${timestamp(S.risk.latest.issuedAt)}. Check Data & status for details.</div>`;
  const legacy=riskRoute?'':`<div class="study-banner"><strong>Continuing direction study · research-2.0.0</strong><a href="#risk">Back to Risk Lab →</a>${RiskUI.directionLinks()}</div>`;
  let body,viewError=false;
  try {body=views[S.route]();} catch(error) {viewError=true;body=empty('This view could not be displayed','The public data remains available in the on-site documents and records. Try Refresh.',links([['Public records',`${REPO}/tree/main/site/data`]]));warning+=`<p class="evidence-note error">View error: ${esc(error.message)}</p>`;}
  $('#main').innerHTML=`<div class="fade-in">${warning}${legacy}${body}</div>`;
  const unhealthy=viewError||failures.length||currentStatus?.status==='error';
  $('#health').className=`health ${unhealthy?'bad':currentStatus?.status!=='healthy'?'':riskRoute&&f.kind!=='good'?'warn':'good'}`;
  $('#health').textContent=viewError?'View needs attention':failures.length?'Refresh needs attention':currentStatus?.status==='error'?'Pipeline needs attention':!currentStatus?'Status unavailable':riskRoute?f.label:`Direction pipeline: ${currentStatus.status}`;
  $('#updated').textContent=currentStatus?.lastSuccessfulAt?`Last successful cycle ${timestamp(currentStatus.lastSuccessfulAt)}`:'No successful cycle loaded';
  document.title=`${ROUTES[S.route]} · UNPRICED`;
  GuideUI.localize();bind();RiskUI.bind();
}
async function load({force=false}={}){
  S.route=routeFromHash();render();
  await Promise.allSettled(dependencies().map(k=>fetchResource(k,force)));
  render();
}
$('#close-dialog').addEventListener('click',()=>$('#detail').close());
$('#detail-content').addEventListener('click',e=>{if(e.target.closest('a[href^="#"]'))$('#detail').close();});
$('#detail').addEventListener('click',e=>{if(e.target===$('#detail')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#audit').addEventListener('click',()=>RiskUI.isRisk(S.route)?RiskUI.audit():showAudit());
$('#refresh').addEventListener('click',()=>load({force:true}));
window.addEventListener('hashchange',()=>{if(location.hash==='#main'){$('#main').focus();return;}load();window.scrollTo({top:0,behavior:'instant'});});
document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
setInterval(()=>{if(!document.hidden)load();},300000);
load();
