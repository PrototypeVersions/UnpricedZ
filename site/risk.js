'use strict';
// Presentation only. Forecasts, losses and intervals are read from published records.
const RiskUI = (() => {
  const varianceModels = ['ewma', 'har_daily', 'garch11'];
  const drawdownModels = ['base_rate', 'volatility_only'];
  const names = {ewma:'EWMA', har_daily:'HAR', garch11:'GARCH', base_rate:'Historical frequency', volatility_only:'Volatility model'};
  const colors = {ewma:'#116D68', har_daily:'#73528A', garch11:'#A75B28', base_rate:'#506C87', volatility_only:'#116D68'};
  const valid = v => typeof v === 'number' && Number.isFinite(v);
  const annual = v => valid(v) && v >= 0 ? Math.sqrt(252 * v) : null;
  const span = values => { const xs = values.filter(valid); return xs.length ? [Math.min(...xs), Math.max(...xs)] : null; };
  const rangeText = values => { const r = span(values); return r ? r[0] === r[1] ? pct(r[0]) : `${pct(r[0])}–${pct(r[1])}` : 'Unavailable'; };
  const isRisk = route => ['risk','outlook','record','experiments','about'].includes(route);
  const title = (eyebrow, heading, copy) => `<div class="intro"><span class="eyebrow">${eyebrow}</span><h1>${heading}</h1><p>${copy}</p></div>`;
  const section = (heading, copy, content, link='') => `<section class="section"><div class="section-heading"><div><h2>${heading}</h2>${copy?`<p>${copy}</p>`:''}</div>${link}</div>${content}</section>`;
  const table = (head, rows, label) => `<div class="table-scroll" role="region" tabindex="0" aria-label="${esc(label)}"><table class="data-table"><thead><tr>${head.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
  const missing = key => S.resources?.[key]?.error ? empty('This record could not be loaded','Use Refresh to try again. Saved records remain available from the repository.',links([['Public data',`${REPO}/tree/main/site/data`]])) : empty('Loading this record','The page will update when the published data arrives.');
  const snapshot = () => S.risk?.latest;
  function presentation() {
    const p=S.presentation;
    return p && p.forecastId===snapshot()?.forecastId && p.riskUpdatedAt===S.risk?.updatedAt ? p : null;
  }
  function freshness(snap, context, now=Date.now()) {
    if(!snap) return {kind:'warn',label:'No forecast published'};
    const cal=context?.calendar;
    if(!cal?.sessions?.length || now<Date.parse(cal.validFrom) || now>=Date.parse(cal.validUntil)) return {kind:'warn',label:'Freshness not verified'};
    if(Date.parse(snap.issuedAt)>now || Date.parse(snap.informationCutoff)>now) return {kind:'warn',label:'Forecast timestamp is in the future'};
    const completed=cal.sessions.filter(d=>Date.parse(d.close)<=now);
    const last=completed[completed.length-1];
    if(!last) return {kind:'warn',label:'Freshness not verified'};
    if(snap.sessionDate>=last.date) return {kind:'good',label:'Latest completed session'};
    const next=cal.sessions.find(d=>d.date>last.date);
    // Publication can occur after close and before the next NYSE open. A weekend
    // or holiday is not a missed session; a passed entry open is a missed window.
    if(!next) return {kind:'warn',label:'Freshness not verified'};
    return now<Date.parse(next.open) ? {kind:'pending',label:'Next issue pending'} : {kind:'warn',label:'Newer forecast overdue'};
  }
  function period(snap=snapshot()) {
    return snap ? `${date(snap.entryDate)} open → ${date(snap.exitDate)} close` : 'Next open through the fifth session’s close';
  }
  function nextOutcome() {
    return [...(S.risk?.history||[])].filter(h=>!h.resolved).sort((a,b)=>a.exitClose.localeCompare(b.exitClose))[0];
  }
  function recordCopy() {
    const r=S.risk;
    if(!r) return 'The live record is loading.';
    if(!r.forecastDates) return 'The live record begins with the first valid publication.';
    const next=nextOutcome();
    if(!r.resolvedDates) return `${num(r.forecastDates,0)} forecast dates recorded. The first window ends ${timestamp(next?.exitClose)}; scoring follows a successful data cycle.`;
    return `${num(r.resolvedDates,0)} of ${num(r.forecastDates,0)} forecast dates resolved. Overlapping windows share market moves, so these are not independent trials.`;
  }
  function modelValues(row, task) {
    const models=task==='variance'?varianceModels:drawdownModels;
    return `<dl class="model-values">${models.map(m=>`<div><dt><i style="background:${colors[m]}"></i>${names[m]}</dt><dd>${pct(task==='variance'?annual(row[task]?.[m]):row[task]?.[m])}${!valid(row[task]?.[m])?'<span class="sr-only"> · model abstained</span>':''}</dd></div>`).join('')}</dl>`;
  }
  function outlookCards(row) {
    return `<div class="outlook-pair"><article class="forecast-card"><p class="eyebrow">${esc(row.ticker)} · Expected volatility</p><strong class="forecast-range">${rangeText(varianceModels.map(m=>annual(row.variance?.[m])))}</strong><p class="small-note">Annualized scale · range across available models</p>${modelValues(row,'variance')}</article><article class="forecast-card"><p class="eyebrow">${esc(row.ticker)} · Chance of a drawdown &gt;3%</p><strong class="forecast-range">${rangeText(drawdownModels.map(m=>row.drawdown?.[m]))}</strong><p class="small-note">Entry price and daily closes · two different estimates</p>${modelValues(row,'drawdown')}</article></div>`;
  }
  function changes() {
    const p=presentation(), current=snapshot();
    const previous=p?.history?.filter(h=>h.sessionDate<current.sessionDate).at(-1);
    if(!previous) return `<p class="muted">A comparison appears when two archived issues are available. <a href="#outlook">Explore the current forecasts →</a></p>`;
    const rows=current.forecasts.map(row=>{
      const old=previous.forecasts.find(f=>f.ticker===row.ticker);
      const before=annual(old?.variance?.ewma), after=annual(row.variance?.ewma);
      return {row,before,after,change:valid(before)&&valid(after)?after-before:null};
    }).filter(r=>valid(r.change)).sort((a,b)=>Math.abs(b.change)-Math.abs(a.change)).slice(0,3);
    if(!rows.length) return '<p class="muted">No paired EWMA estimates are available for the last two issues.</p>';
    return `<p class="small-note">Largest moves in EWMA volatility since the ${date(previous.sessionDate)} information cutoff. Each issue predicts a different five-session window.</p><div class="change-grid">${rows.map(({row,before,after,change})=>`<button class="change-card" data-risk-ticker="${esc(row.ticker)}"><span>${esc(row.ticker)} <span class="muted">${esc(row.name)}</span></span><strong>${change>0?'+':''}${num(change*100,1)} <small>percentage points</small></strong><span class="small-note">${pct(before)} → ${pct(after)} annualized</span></button>`).join('')}</div>`;
  }
  function home() {
    const snap=snapshot(), spy=snap?.forecasts?.find(r=>r.ticker==='SPY');
    return `${title('UNPRICED Z / MARKET & SECTOR RISK','Forecasts, put to the test.','Explore market forecasts, compare models, and follow how predictions perform.')}<p class="focus-line">Current focus: <strong>how much markets may move, and how far they may fall.</strong> <a href="#about">Why risk?</a></p>
      ${section('The current outlook',snap?`SPY · S&P 500 ETF · ${period()}`:'Market and sector forecasts',spy?`${outlookCards(spy)}<div class="section-foot"><span>Model disagreement is visible; these ranges are not confidence intervals.</span><a class="button primary" href="#outlook">Explore all 10 assets →</a></div>`:missing('risk'))}
      ${section('What changed','',changes())}
      ${section('The record','',`<div class="record-strip"><div><h3>${S.risk?.resolvedDates?'The live evidence is accumulating.':'Too early to judge.'}</h3><p>${recordCopy()}</p></div><a class="button" href="#record">See the record →</a></div>`)}
      ${section('Inside the research','Every idea has to face a fair comparison.',`<div class="research-grid"><a class="research-card" href="#experiments"><span class="eyebrow">Historical tests</span><h3>Can models beat simple baselines?</h3><p>Compare variance and drawdown forecasts on past markets.</p><span class="text-link">Explore the evidence →</span></a><a class="research-card" href="#experiments"><span class="eyebrow">Controlled experiments</span><h3>Can they learn known patterns?</h3><p>Inspect model results in synthetic markets, including missed signals.</p><span class="text-link">Inspect the diagnostics →</span></a><a class="research-card" href="#about"><span class="eyebrow">Open methods</span><h3>What does a forecast mean?</h3><p>See the targets, learning schedule, and limits of this lab.</p><span class="text-link">How it works →</span></a></div>`)}${labLinks()}`;
  }
  function dots(row, max) {
    return `<div class="model-dots" aria-hidden="true">${varianceModels.map(m=>{const v=annual(row.variance?.[m]);return valid(v)?`<i style="left:${100*v/max}%;background:${colors[m]}"></i>`:'';}).join('')}</div>`;
  }
  function forecastTable() {
    const snap=snapshot(); if(!snap) return missing('risk');
    const task=S.riskTask, models=task==='variance'?varianceModels:drawdownModels;
    const query=(S.riskSearch||'').trim().toLowerCase();
    const rows=snap.forecasts.filter(r=>`${r.ticker} ${r.name}`.toLowerCase().includes(query));
    const sort=S.riskSort;
    rows.sort((a,b)=>sort==='ticker'?a.ticker.localeCompare(b.ticker):((b[task]?.[sort]??-Infinity)-(a[task]?.[sort]??-Infinity))||a.ticker.localeCompare(b.ticker));
    if(!rows.length)return empty('No matching assets','Try a ticker such as SPY or a sector name.');
    const max=Math.max(.1,...snap.forecasts.flatMap(r=>varianceModels.map(m=>annual(r.variance?.[m]))).filter(valid))*1.08;
    return table(['Asset',...models.map(m=>`<span class="model-key" style="--key:${colors[m]}">${names[m]}</span>`),...(task==='variance'?['Model spread']:[])],rows.map(r=>`<tr><th scope="row"><button class="asset-button" data-risk-ticker="${esc(r.ticker)}">${esc(r.ticker)} <span aria-hidden="true">↗</span><small>${esc(r.name)}</small></button></th>${models.map(m=>`<td class="num">${valid(r[task]?.[m])?pct(task==='variance'?annual(r.variance[m]):r.drawdown[m]):`<span title="${esc(r.abstentions?.[m]||'No valid estimate')}">—<span class="sr-only"> Model abstained</span></span>`}</td>`).join('')}${task==='variance'?`<td class="spread-cell">${dots(r,max)}</td>`:''}</tr>`),task==='variance'?'Annualized volatility by asset and model':'Probability of a drawdown greater than 3%');
  }
  function forecasts() {
    const snap=snapshot();
    return `${title('FORECASTS / FIVE TRADING SESSIONS','The current outlook.','Compare each model’s view of the market and nine sectors. Select an asset to follow its record.')}
      ${snap?`<p class="window-line">${period()}<br><span class="small-note">Information through ${timestamp(snap.informationCutoff)} · issued ${timestamp(snap.issuedAt)}</span></p>`:''}
      <div class="controls forecast-controls"><div class="segmented" role="group" aria-label="Forecast target"><button data-risk-task="variance" aria-pressed="${S.riskTask==='variance'}">Volatility</button><button data-risk-task="drawdown" aria-pressed="${S.riskTask==='drawdown'}">Drawdown</button></div><label class="search-label">Find an asset<input id="risk-search" type="search" placeholder="Ticker or sector" value="${esc(S.riskSearch)}"></label><label>Sort by<select id="risk-sort">${['ticker',...(S.riskTask==='variance'?varianceModels:drawdownModels)].map(m=>`<option value="${m}"${S.riskSort===m?' selected':''}>${m==='ticker'?'Asset A–Z':names[m]+' · highest first'}</option>`).join('')}</select></label></div>
      <p class="small-note">${S.riskTask==='variance'?'Five-session variance, displayed as annualized volatility: √(252 × variance). Dots share one scale and show model disagreement, not a confidence band.':'Probability of a drop greater than 3% from a running peak, using the entry open and five daily closes. A drawdown can occur even when the final return is positive.'} — means the model abstained.</p>
      <div id="risk-table" class="panel">${forecastTable()}</div>
      <details class="detail-block"><summary>What do the models use?</summary><p>EWMA gives recent squared returns more weight. HAR relates variance to recent daily, weekly and monthly averages. GARCH models how volatility changes over time. For drawdowns, historical event frequency is compared with a logistic model that uses volatility alone.</p><p>No model is selected as a winner and no combined forecast is calculated.</p></details>${macroContext(snap?.macroContext)}`;
  }
  function macroContext(macro) {
    if(!macro)return '';
    const f=macro.features||{};
    return `<details class="detail-block"><summary>Economic context <span class="muted">· ${esc(macro.status)}</span></summary><p>Dated FRED observations provide background. They are not inputs to the current risk models.</p>${macro.status==='available'||macro.status==='incomplete'?`<dl class="context-grid"><div><dt>10-year Treasury yield</dt><dd>${num(f.rate10,2)}%</dd></div><div><dt>10-year / 2-year spread</dt><dd>${num(f.slope,2)} pp</dd></div><div><dt>Credit spread</dt><dd>${num(f.credit,2)} pp</dd></div><div><dt>12-month inflation</dt><dd>${num(f.inflation12,1)}%</dd></div><div><dt>Unemployment</dt><dd>${num(f.unemployment,1)}%</dd></div></dl>`:`<p>${esc(macro.reason||'The context feed is unavailable. Price-based risk forecasts can still run.')}</p>`}${macro.inputVintage?.path?links([['Dated input archive',`${REPO}/blob/main/${macro.inputVintage.path}`]]):''}</details>`;
  }
  function outcomeText(row) { return valid(row?.drawdownSeverity)?`${pct(row.drawdownSeverity)} peak-to-trough`:'Pending'; }
  function detail(ticker) {
    const snap=snapshot(), row=snap?.forecasts.find(r=>r.ticker===ticker); if(!row)return;
    const p=presentation();
    const rows=(p?.history||[]).map(h=>({h,f:h.forecasts.find(r=>r.ticker===ticker),outcome:h.outcomes?.find(r=>r.ticker===ticker)})).filter(r=>r.f);
    const history=rows.length?table(['Information cutoff','EWMA / HAR / GARCH','Realized volatility','Drawdown forecast¹','Realized drawdown'],[...rows].reverse().map(({h,f,outcome})=>`<tr><th scope="row"><a href="${REPO}/blob/main/${esc(h.path)}">${date(h.sessionDate)}</a><small>${date(h.entryDate)} → ${date(h.exitDate)}</small></th><td class="num">${varianceModels.map(m=>pct(annual(f.variance[m]))).join(' / ')}</td><td class="num">${outcome?pct(annual(outcome.realizedVariance)):'Pending'}</td><td class="num">${drawdownModels.map(m=>pct(f.drawdown[m])).join(' / ')}</td><td>${outcomeText(outcome)}</td></tr>`),'Recent forecast issues and actual outcomes'):'<p class="muted">The expanded history is temporarily unavailable. The frozen records remain linked below.</p>';
    const actual=rows.filter(r=>valid(r.outcome?.realizedVariance)).map(({h,f,outcome})=>({date:h.sessionDate,...Object.fromEntries(varianceModels.map(m=>[m,annual(f.variance[m])])),actual:annual(outcome.realizedVariance)}));
    const chart=actual.length>=2?`<h3>Forecasts and realized volatility</h3><div class="chart-wrap">${legend([...varianceModels.map(m=>({label:names[m],color:colors[m]})),{label:'Realized',color:'#213044'}])}${lineChart(actual,[...varianceModels.map(m=>({key:m,color:colors[m]})),{key:'actual',color:'#213044'}],{format:v=>pct(v),label:'Annualized forecast and realized volatility for resolved dates'})}</div>`:'';
    const abstentions=Object.entries(row.abstentions||{});
    openDetail(`<span class="eyebrow">${esc(ticker)} / FIVE-SESSION FORECAST</span><h2>${esc(row.name)}</h2><p>${period()}</p>${outlookCards(row)}${abstentions.length?`<div class="evidence-note">${abstentions.map(([m,reason])=>`<p><strong>${esc(names[m]||m)} abstained:</strong> ${esc(reason)}</p>`).join('')}</div>`:''}<p class="small-note">The displayed range is the spread between model estimates, not an uncertainty interval.</p>${chart}<h3>Recent issues & outcomes</h3><p class="small-note">Up to 60 recent issues. ¹ Historical frequency / volatility model. Outcomes appear only after their full window closes and a resolution is recorded.</p>${history}${links([['All frozen issues',`${REPO}/tree/main/risk_records/risk-1.0.0/forecasts`],['Current forecast JSON',`${REPO}/blob/main/risk_records/risk-1.0.0/forecasts/${snap.sessionDate}.json`]])}`);
  }
  function scorecards(summary) {
    if(!Object.keys(summary?.groups||{}).length)return empty('No resolved outcomes yet',recordCopy());
    return ['variance','drawdown'].map(task=>section(task==='variance'?'Variance forecasts':'Drawdown probabilities',task==='variance'?'QLIKE loss · lower is better. Scored on raw variance, not displayed volatility.':'Brier loss · lower is better. Measures the probabilities assigned to drawdowns greater than 3%.',`<div class="score-grid">${Object.entries(summary.groups).map(([group,g])=>`<article class="panel"><div class="panel-head"><h3>${group==='SPY'?'SPY · the market':'Nine sectors'}</h3></div>${table(['Model','Mean loss','Scored / expected','Dates'],g.models.filter(m=>m.task===task).map(m=>`<tr><th scope="row">${names[m.model]}</th><td class="num">${num(m.loss,4)}</td><td class="num">${num(m.scoredRows,0)} / ${num(g.expectedRows,0)}</td><td class="num">${num(m.dates,0)}</td></tr>`),`${group} ${task} scores`)}<div class="panel-body comparison-list">${g.comparisons.filter(c=>c.task===task).map(c=>`<p><strong>${names[c.candidate]} vs ${names[c.baseline]}</strong><br>Improvement ${signed(c.gain?.mean,4)} <span class="small-note">· 95% interval ${intervalText(c.gain)}</span><br><span class="small-note">${num(c.pairedRows,0)} paired observations · ${num(c.gain?.dates,0)} dates</span></p>`).join('')}</div></article>`).join('')}</div>`)).join('')+`<p class="small-note">Positive improvement means lower loss than the baseline. Intervals use blocks of dates to account for dependence; they are descriptive, not adjusted for model selection. Sector comparisons weight each date equally.</p>${riskDecomposition(summary)}${calibrationTable(summary)}`;
  }
  function calibrationTable(summary) {
    // Avoid making a handful of live observations look like a reliability study.
    if(S.riskEvidence==='live'&&(S.risk?.resolvedDates||0)<60)return '<p class="small-note">Calibration tables will appear after 60 resolved forecast dates. This display threshold is not a claim of statistical power.</p>';
    const rows=Object.entries(summary?.groups||{}).flatMap(([group,g])=>g.models.filter(m=>m.task==='drawdown').flatMap(m=>(m.calibration||[]).map(b=>({group,model:m.model,...b}))));
    return rows.length?`<details class="detail-block"><summary>Are the drawdown probabilities calibrated?</summary><p>Compare average forecast probability with observed event frequency in each bin. Counts include correlated assets and overlapping windows.</p>${table(['Group / model','Probability bin','Mean forecast','Observed rate','Rows'],rows.map(r=>`<tr><th scope="row">${esc(r.group)} · ${names[r.model]}</th><td>${pct(r.low,0)}–${pct(r.low+.1,0)}</td><td>${pct(r.predicted)}</td><td>${pct(r.observed)}</td><td>${num(r.rows,0)}</td></tr>`),'Drawdown calibration bins')}</details>`:'';
  }
  function results() {
    const live=S.riskEvidence==='live', data=live?S.risk:S.risk_research;
    return `${title('RESULTS / SEPARATE RECORDS','What does the evidence say?','Follow forecasts made before their outcomes, or inspect the historical development tests.')}<div class="segmented" role="group" aria-label="Evidence source"><button data-risk-evidence="live" aria-pressed="${live}">Live record</button><button data-risk-evidence="historical" aria-pressed="${!live}">Historical tests</button></div><div class="evidence-note"><strong>${live?'Prospective · risk-1.0.0':'Historical development · risk-1.0.0'}</strong><p>${live?recordCopy():'2019–2024 walk-forward forecasts. These results have already been inspected and are not an untouched test for future redesigns.'}</p></div>${data?scorecards(data.summary):missing(live?'risk':'risk_research')}${live?ledger():links([['Original historical report','data/risk_research.json']])}`;
  }
  function ledger() {
    const history=S.risk?.history||[];
    return section('Forecast ledger','Every issue keeps its dates and original file.',history.length?table(['Issued','Forecast window','Outcome','Frozen file'],[...history].reverse().slice(0,60).map(h=>`<tr><td>${timestamp(h.issuedAt)}</td><td>${timestamp(h.entryOpen)} → ${timestamp(h.exitClose)}</td><td>${h.resolved?'Resolved':'Pending'}</td><td><a href="${REPO}/blob/main/${esc(h.path)}">${esc(h.sessionDate)} ↗</a></td></tr>`),'Recent frozen forecasts'):'<p class="muted">No live issue has been published yet.</p>');
  }
  function synthetic() {
    const runs=S.risk_controls?.runs;if(!runs)return missing('risk_controls');
    return `<p>Known simulated processes let us check what the learners recover. The oracle knows the generating process; it is not a fitted model or a real-market result.</p>${table(['World / seed','EWMA QLIKE','HAR QLIKE','GARCH QLIKE','Oracle QLIKE'],runs.map(r=>`<tr><th scope="row">${esc(r.scenario)}<small>Seed ${r.seed}</small></th>${varianceModels.map(m=>`<td class="num">${num(r.summary.groups.SPY.models.find(x=>x.model===m)?.loss,4)}</td>`).join('')}<td class="num">${num(r.oracleQLIKE,4)}</td></tr>`),'Learners and oracle in synthetic worlds')}<details class="detail-block"><summary>Inspect every synthetic run</summary>${runs.map(r=>`<details><summary>${esc(r.scenario)} · seed ${r.seed}</summary>${scorecards(r.summary)}</details>`).join('')}</details><p class="small-note">Lower QLIKE is better. These few seeds diagnose behavior; they do not establish real-market forecasting skill.</p>`;
  }
  function experiments() {
    return `${title('RESEARCH / IDEAS UNDER TEST','Find out what holds up.','Simple baselines, stronger models, and a record that keeps the unsuccessful ideas too.')}
      ${section('On historical markets','2019–2024 · development evidence',`<div class="record-strip"><div><h3>A useful starting point, not a live verdict.</h3><p>GARCH had lower variance loss than EWMA in the recorded historical comparison. The volatility-based drawdown model did not clearly beat event frequency.</p></div><button class="button" id="historical-results">Compare the scores →</button></div>`)}
      ${section('In controlled worlds','Synthetic evidence',synthetic())}
      ${section('What did not work','Registered macro study',`<div class="record-strip"><div><h3>More economic inputs did not improve the recorded variance result.</h3><p>The registered macro models produced substantially larger losses than EWMA. A small share of extreme dates accounts for much of the loss; the original all-date result still stands.</p></div></div><details class="detail-block"><summary>Read the result and its decomposition</summary><p>The recorded macro attempt is preserved exactly. Inspect mean and median QLIKE, the share of loss from the worst 1% of dates, and the result excluding 2020 for every variance model. Excluding a difficult period is a diagnostic, not a replacement score.</p>${links([['Registered program result','data/program.json'],['All-model variance decomposition',`${REPO}/blob/main/docs/MACRO_VARIANCE_DECOMPOSITION.md`],['Risk research review',`${REPO}/blob/main/docs/RISK_FIRST_REVIEW_2026-11-04.md`]])}</details>`)}
      ${section('The continuing direction study','A separate question, with its own record.',`<p>The original research-2.0.0 study still forecasts which sectors will outperform SPY. Its live record and paper portfolio continue under their existing rules.</p>${directionLinks()}`)}`;
  }
  function directionLinks() {
    return `<nav class="study-nav" aria-label="Continuing direction study"><a href="#overview">Direction overview</a><a href="#forecasts">Direction forecasts</a><a href="#research">Historical research</a><a href="#controls">Synthetic controls</a><a href="#portfolio">Paper portfolio</a><a href="#method">Direction methods</a></nav>`;
  }
  function labLinks() {
    return `<div class="lab-network"><p><strong>One project, different questions.</strong> Z studies risk. X ranks stocks. Hub keeps an independent record.</p><div><a href="https://prototypeversions.github.io/UnpricedX/">Stock Lab ↗</a><a href="https://prototypeversions.github.io/UnpricedHub/">Independent scorekeeper ↗</a><a href="#overview">Z’s direction study →</a></div></div>`;
  }
  function about() {
    return `${title('ABOUT / THE FORECASTING LAB','A focused piece of a bigger question.','UNPRICED asks which market forecasts deserve confidence. This lab concentrates on risk.')}
      <div class="prose"><h2>Why focus on risk?</h2><p>Forecasting includes more than predicting whether prices will rise. It also means estimating how much they may move and the chance of a large fall. Z studies those questions; X studies which stocks may perform better than others. Risk forecasts alone are not a complete investment strategy.</p></div>${labLinks()}
      <div class="method-grid"><article class="method-card"><span class="eyebrow">The targets</span><h2>Five sessions, two questions.</h2><p>For SPY and nine sector ETFs, predict the average squared log-return legs from the next open through the fifth session’s close. The site displays this variance as annualized volatility.</p><p>Separately, predict the probability of a drawdown greater than 3%, measured from a running peak using the entry open and five daily closes. Intraday lows are not included.</p></article>
      <article class="method-card"><span class="eyebrow">The learning schedule</span><h2>New observations each day.</h2><p>Daily prices update forecasts and the EWMA and GARCH volatility states. Model parameters are fitted monthly and held fixed within that month. Matured outcomes update the scorecards.</p><p>That is learning from new data, not a guarantee of improvement. No automatic model promotion or ensemble is applied.</p></article>
      <article class="method-card"><span class="eyebrow">The test</span><h2>Compare like with like.</h2><p>Variance models compete against EWMA using QLIKE. Drawdown probabilities compete against historical event frequency using Brier loss. Each keeps its own record.</p><p>Historical tests, synthetic diagnostics, and live results stay separate. Shared dates and overlapping windows limit how much independent evidence there is.</p></article>
      <article class="method-card"><span class="eyebrow">The boundaries</span><h2>Freeze the forecast first.</h2><p>Publication must finish before the forecast’s entry open. Missing inputs can make a model abstain. Late forecasts are not backfilled.</p><p>Provider-adjusted historical prices may be revised. Inputs, fits, forecasts, and outcomes are archived so the record can be inspected.</p></article></div>
      <details class="detail-block"><summary>Training and evaluation details</summary><p>Fits use a trailing five-year window. Supervised models require at least 504 training dates and reserve 126 eligible dates for calibration, with overlapping target windows purged at the split. These are chronological splits.</p><p>Comparisons use a 20-session block bootstrap with 1,500 resamples. Reported 95% intervals are descriptive and do not adjust for all model searches. Inspected historical periods cannot be reused as fresh confirmation.</p>${links([['Risk protocol',`${REPO}/blob/main/docs/RISK_PROTOCOL.md`],['Registered specification',`${REPO}/blob/main/risk_lab/registry.json`]])}</details>
      <h2>The continuing direction study</h2><p>research-2.0.0 remains a separate, running experiment. Its quarterly fits and paper portfolio are specific to that study.</p>${directionLinks()}`;
  }
  function audit() {
    const snap=snapshot(), p=presentation(), f=freshness(snap,p);
    const errors=Object.entries(S.resources||{}).filter(([,v])=>v.error);
    openDetail(`<h2>Data & publication status</h2><dl class="key-values"><div><dt>Risk pipeline</dt><dd>${esc(S.risk_status?.status||'Unavailable')}<small>Last success ${timestamp(S.risk_status?.lastSuccessfulAt)}</small></dd></div><div><dt>Forecast freshness</dt><dd>${esc(f.label)}<small>Checked against NYSE sessions and the next entry open</small></dd></div><div><dt>Browser last fetched risk data</dt><dd>${timestamp(S.resources?.risk?.loadedAt)}</dd></div><div><dt>Information cutoff</dt><dd>${timestamp(snap?.informationCutoff)}</dd></div><div><dt>Issued</dt><dd>${timestamp(snap?.issuedAt)}</dd></div><div><dt>Target entry / exit</dt><dd>${timestamp(snap?.entryOpen)}<small>${timestamp(snap?.exitClose)}</small></dd></div><div><dt>Forecast payload SHA-256</dt><dd><code>${esc(snap?.payloadSha256||'Unavailable')}</code></dd></div><div><dt>Independent receipt</dt><dd><a href="https://prototypeversions.github.io/UnpricedHub/">Check UnpricedHub ↗</a><small>This page does not verify a Hub receipt.</small></dd></div></dl>${errors.length?`<p class="evidence-note error">Fetch errors: ${esc(errors.map(([k])=>k).join(', '))}. Last fetched data is retained where available.</p>`:''}${S.risk_status?.error?`<p class="evidence-note error">${esc(S.risk_status.error)}</p>`:''}${links([['Workflow history',`${REPO}/actions`],['Risk status JSON','data/risk_status.json'],['Risk forecast JSON','data/risk.json'],['Registered protocol',`${REPO}/blob/main/docs/RISK_PROTOCOL.md`]])}`);
  }
  function bind() {
    document.querySelectorAll('[data-risk-ticker]').forEach(b=>b.addEventListener('click',()=>detail(b.dataset.riskTicker)));
    document.querySelectorAll('[data-risk-task]').forEach(b=>b.addEventListener('click',()=>{S.riskTask=b.dataset.riskTask;S.riskSort=S.riskTask==='variance'?'ewma':'volatility_only';render();}));
    $('#risk-sort')?.addEventListener('change',e=>{S.riskSort=e.target.value;render();});
    $('#risk-search')?.addEventListener('input',e=>{S.riskSearch=e.target.value;$('#risk-table').innerHTML=forecastTable();document.querySelectorAll('#risk-table [data-risk-ticker]').forEach(b=>b.addEventListener('click',()=>detail(b.dataset.riskTicker)));});
    $('#historical-results')?.addEventListener('click',()=>{S.riskEvidence='historical';location.hash='record';});
  }
  return {home,forecasts,results,experiments,about,bind,audit,detail,directionLinks,presentation,freshness,isRisk,valid,annual,span,scorecards};
})();
