import { DEFAULT_SCENARIO, PROVISIONAL_BEHAVIOUR } from './config.js';
import { RNG } from './prng.js';
import { STRATEGIES } from './strategies.js';
import { generatePopulation } from './population.js';
import { simulatePreparation } from './preparation.js';
import { simulateTransfer } from './transfer.js';
import { simulateAircraftCA } from './aircraft-ca.js';
import { mean, quantile, summarize } from './stats.js';

export function deepMerge(base, patch) {
  if (!patch) return structuredClone(base);
  const out = structuredClone(base);
  const merge = (a,b) => { for (const [k,v] of Object.entries(b)) { if (v && typeof v === 'object' && !Array.isArray(v) && a[k] && typeof a[k] === 'object') merge(a[k],v); else a[k]=v; } };
  merge(out, patch); return out;
}

function metrics(passengers, scenario, prep, transfer, aircraft) {
  const initialFs = passengers.map(p => p.initialFrustration);
  const burdens = passengers.map(p => p.frustrationBurden);
  const peaks = passengers.map(p => p.peakFrustration);
  const prepEnd = prep.timeSeconds;
  const transferSeconds = transfer.transferEndSeconds - prepEnd;
  const totalSeconds = aircraft.lastSeatTime ?? (transfer.transferEndSeconds + scenario.boarding.maxBoardingSeconds);
  return {
    initialFrustration: summarize(initialFs),
    prepSeconds: prep.timeSeconds,
    transferSeconds,
    cabinBoardingSeconds: aircraft.cabinBoardingSeconds,
    embarkationSeconds: totalSeconds - prepEnd,
    totalSeconds,
    frustrationBurden: summarize(burdens),
    peakFrustration: summarize(peaks),
    sharePeakAbove075: peaks.filter(x=>x>.75).length / passengers.length,
    corrections: prep.corrections,
    companionOverrides: passengers.filter(p=>p.companionOverride).length,
    readiness: prep.readiness,
    seatedCount: aircraft.seatedCount,
    timedOut: prep.timedOut || aircraft.timedOut
  };
}

export function runFlight(patch = {}, seedOverride = null) {
  const scenario = deepMerge(DEFAULT_SCENARIO, patch);
  const strategy = STRATEGIES[scenario.boarding.strategy];
  if (!strategy) throw new Error(`Unknown strategy ${scenario.boarding.strategy}`);
  const seed = seedOverride ?? scenario.seed;
  const rng = new RNG(seed);
  const passengers = generatePopulation(scenario, strategy, rng.fork(1), PROVISIONAL_BEHAVIOUR);
  for (const p of passengers) p.initialFrustration = p.frustration;
  const prep = simulatePreparation(passengers, scenario, strategy, rng.fork(2), PROVISIONAL_BEHAVIOUR);
  const transfer = simulateTransfer(passengers, scenario, rng.fork(3), PROVISIONAL_BEHAVIOUR, prep.timeSeconds);
  const aircraft = simulateAircraftCA(passengers, transfer.arrivals, scenario, rng.fork(4), PROVISIONAL_BEHAVIOUR);
  const combinedHistory = [...prep.history, ...aircraft.history.filter(h=>h.t>prep.timeSeconds)];
  return { scenario, strategy, passengers, prep, transfer, aircraft, history:combinedHistory, metrics:metrics(passengers,scenario,prep,transfer,aircraft) };
}

export function runMonteCarlo(patch = {}, runs = 100, baseSeed = 10000) {
  const results=[];
  for (let i=0;i<runs;i++) results.push(runFlight(patch, baseSeed+i));
  const valid=results.filter(r=>!r.metrics.timedOut);
  const grab = f => valid.map(f);
  return {
    runs, validRuns:valid.length,
    prep:summarize(grab(r=>r.metrics.prepSeconds)),
    transfer:summarize(grab(r=>r.metrics.transferSeconds)),
    cabinBoarding:summarize(grab(r=>r.metrics.cabinBoardingSeconds ?? 0)),
    total:summarize(grab(r=>r.metrics.totalSeconds)),
    burden:summarize(grab(r=>r.metrics.frustrationBurden.mean)),
    peak:summarize(grab(r=>r.metrics.peakFrustration.mean)),
    sharePeakAbove075:mean(grab(r=>r.metrics.sharePeakAbove075)),
    corrections:summarize(grab(r=>r.metrics.corrections)),
    results
  };
}
