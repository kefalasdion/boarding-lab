import { runFlight, runMonteCarlo } from './simulation.js';
import { STRATEGIES } from './strategies.js';
import { fmtSeconds } from './stats.js';

const $ = id => document.getElementById(id);
const stratEl = $('strategy');
for (const s of Object.values(STRATEGIES)) {
  const o=document.createElement('option'); o.value=s.id; o.textContent=s.name; stratEl.appendChild(o);
}

function patchFromUI() {
  return {
    flightContext:{delayMinutes:+$('delay').value,priorDelayUpdates:+$('updates').value,priorGateWaitMinutes:+$('gatewait').value},
    population:{familyPassengerShare:+$('families').value/100,handLuggageShare:+$('bags').value/100},
    preparation:{readinessTarget:+$('readiness').value/100},
    access:{mode:$('access').value},
    boarding:{strategy:$('strategy').value,serviceModel:$('service').value}
  };
}

function renderPopulation(r) {
  const el=$('population'); el.innerHTML='';
  for (const p of r.passengers) {
    const d=document.createElement('span'); d.className='pax';
    d.style.setProperty('--f',p.initialFrustration);
    d.title=`${p.row}${p.seat} · initial F ${p.initialFrustration.toFixed(2)} · tolerance ${p.toleranceThreshold.toFixed(2)}${p.familyId?` · family ${p.familyId}`:''}`;
    if(p.familyId)d.classList.add('family'); el.appendChild(d);
  }
}

function renderHistory(r) {
  const svg=$('chart'), w=720,h=230,pad=38;
  const hist=r.history; const maxT=Math.max(...hist.map(x=>x.t),1);
  const path=k=>hist.map((x,i)=>`${i?'L':'M'}${(pad+(w-pad-12)*x.t/maxT).toFixed(1)},${(h-pad-(h-2*pad)*x[k]).toFixed(1)}`).join(' ');
  $('meanPath').setAttribute('d',path('meanF')); $('p90Path').setAttribute('d',path('p90F'));
  $('prepMarker').setAttribute('x1',pad+(w-pad-12)*r.metrics.prepSeconds/maxT); $('prepMarker').setAttribute('x2',pad+(w-pad-12)*r.metrics.prepSeconds/maxT);
  $('prepLabel').setAttribute('x',Math.min(w-100,pad+(w-pad-12)*r.metrics.prepSeconds/maxT+5));
}

function renderMetrics(r) {
  const m=r.metrics;
  $('mInit').textContent=m.initialFrustration.mean.toFixed(2);
  $('mPrep').textContent=fmtSeconds(m.prepSeconds);
  $('mEmbark').textContent=fmtSeconds(m.embarkationSeconds);
  $('mCabin').textContent=fmtSeconds(m.cabinBoardingSeconds||0);
  $('mTotal').textContent=fmtSeconds(m.totalSeconds);
  $('mBurden').textContent=m.frustrationBurden.mean.toFixed(2)+' F·min';
  $('mPeak').textContent=(100*m.sharePeakAbove075).toFixed(0)+'%';
  $('mCorrections').textContent=String(m.corrections);
  $('status').textContent=m.timedOut?'Timed out':'180 / 180 seated';
  $('status').className='badge '+(m.timedOut?'bad':'good');
  $('detail').innerHTML=`<b>${r.strategy.name}</b> · ${r.scenario.access.mode} · ${r.scenario.boarding.serviceModel.replaceAll('_',' ')}<br>Preparation readiness ${Math.round(m.readiness.overall*100)}%; companion overrides ${m.companionOverrides}; max aisle occupancy ${r.aircraft.debug.maxAisleOccupancy}/${r.aircraft.debug.aisleCells} cells.`;
}

function renderOne(r){renderMetrics(r);renderPopulation(r);renderHistory(r)}

function runOne(){ $('run').disabled=true; setTimeout(()=>{const r=runFlight(patchFromUI(),+$('seed').value);renderOne(r);$('run').disabled=false},0); }

function compare(){
  $('compare').disabled=true; $('comparison').innerHTML='<div class="muted">Running deterministic Monte Carlo batches…</div>';
  setTimeout(()=>{
    const rows=[]; let seed=70000;
    for(const s of Object.values(STRATEGIES)){
      const mode=s.accessRecommended;
      const mc=runMonteCarlo({...patchFromUI(),access:{...patchFromUI().access,mode},boarding:{...patchFromUI().boarding,strategy:s.id}},30,seed); seed+=1000;
      rows.push({name:s.name,mode,total:mc.total.mean,prep:mc.prep.mean,cabin:mc.cabinBoarding.mean,burden:mc.burden.mean,valid:mc.validRuns});
    }
    rows.sort((a,b)=>a.total-b.total);
    $('comparison').innerHTML=`<table><thead><tr><th>Strategy</th><th>Access</th><th>Prep</th><th>Cabin</th><th>T=0 → seated</th><th>F burden</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${x.name}</td><td>${x.mode}</td><td>${fmtSeconds(x.prep)}</td><td>${fmtSeconds(x.cabin)}</td><td><b>${fmtSeconds(x.total)}</b></td><td>${x.burden.toFixed(2)}</td></tr>`).join('')}</tbody></table><div class="muted small">30 runs per strategy. Behaviour coefficients remain provisional; do not use this ranking operationally before calibration.</div>`;
    $('compare').disabled=false;
  },0);
}

for(const id of ['delay','updates','gatewait','families','bags','readiness']) $(id).addEventListener('input',()=>{
  $('delayv').textContent=$('delay').value+'m'; $('updatesv').textContent=$('updates').value; $('gatewaitv').textContent=$('gatewait').value+'m'; $('familiesv').textContent=$('families').value+'%'; $('bagsv').textContent=$('bags').value+'%'; $('readinessv').textContent=$('readiness').value+'%';
});
$('strategy').addEventListener('change',()=>{const s=STRATEGIES[$('strategy').value];$('access').value=s.accessRecommended;});
$('run').addEventListener('click',runOne); $('compare').addEventListener('click',compare);
runOne();
