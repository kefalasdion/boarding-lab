import { clamp, logistic } from './stats.js';
import { initialStressLoad, frustrationFromLoad } from './frustration.js';
import { applyCompanionCompatibility } from './strategies.js';

const SEATS = ['A','B','C','D','E','F'];

function buildFamilyAssignments(n, targetPassengerShare, rng) {
  const ids = Array(n).fill(0); let nextFamily = 1, assigned = 0;
  const target = Math.round(n * targetPassengerShare);
  const indices = rng.shuffle([...Array(n).keys()]);
  let cursor = 0;
  while (assigned < target && cursor < n) {
    const remaining = target - assigned;
    const size = Math.min(remaining, rng.next() < .22 ? 4 : rng.next() < .55 ? 3 : 2);
    for (let k = 0; k < size && cursor < n; k++, cursor++) ids[indices[cursor]] = nextFamily;
    assigned += size; nextFamily++;
  }
  return ids;
}

export function generatePopulation(scenario, strategy, rng, behaviour) {
  const n = scenario.aircraft.rows * scenario.aircraft.seatsPerRow;
  const familyIds = buildFamilyAssignments(n, scenario.population.familyPassengerShare, rng.fork(31));
  const passengers = [];
  for (let i = 0; i < n; i++) {
    const row = Math.floor(i / 6) + 1, seat = SEATS[i % 6];
    // Four shared latent factors create correlated traits instead of independent random draws.
    const selfReg = rng.normal();
    const stressReact = rng.normal();
    const social = rng.normal();
    const mobility = rng.normal();
    const familyId = familyIds[i];
    const toleranceThreshold = clamp(.55 + .13 * selfReg - .07 * stressReact + rng.normal(0,.05), .16, .92);
    const delaySensitivity = clamp(.50 - .12 * selfReg + .16 * stressReact + rng.normal(0,.06), .05, .98);
    const uncertaintySensitivity = clamp(.48 - .10 * selfReg + .15 * stressReact + rng.normal(0,.07), .05, .98);
    const waitSensitivity = clamp(.48 - .10 * selfReg + .12 * stressReact + rng.normal(0,.07), .05, .98);
    const crowdSensitivity = clamp(.44 + .16 * stressReact + rng.normal(0,.07), .05, .98);
    const socialSusceptibility = clamp(.46 + .18 * social + rng.normal(0,.07), .03, .98);
    const compliance = clamp(.83 + .09 * selfReg - .08 * stressReact + rng.normal(0,.06), .25, .99);
    const informationTrust = clamp(.88 - .055 * scenario.flightContext.priorDelayUpdates - .0015 * scenario.flightContext.delayMinutes + rng.normal(0,.06), .12, .98);
    const fatigue = clamp(.19 + .07 * stressReact + .0015 * scenario.flightContext.priorAirportDwellMinutes + (familyId ? .04 : 0) + rng.normal(0,.05), .02, .95);
    const connectionPressure = rng.bool(scenario.flightContext.connectionPressureShare) ? clamp(.55 + rng.normal(0,.16), .15, 1) : clamp(.08 + rng.normal(0,.05), 0, .25);
    const urgency = clamp(.20 + .45 * connectionPressure + .15 * delaySensitivity + rng.normal(0,.07), .02, .98);
    const walkingSpeedMps = clamp(.80 + .10 * mobility - .08 * fatigue + rng.normal(0,.06), .45, 1.15);
    const hasBag = rng.bool(scenario.population.handLuggageShare);
    const bagCount = !hasBag ? 0 : rng.bool(scenario.population.twoBagShareAmongBagPassengers) ? 2 : 1;
    const p = {
      id: i, row, seat, familyId,
      toleranceThreshold, delaySensitivity, uncertaintySensitivity, waitSensitivity,
      crowdSensitivity, socialSusceptibility, compliance, informationTrust,
      fatigue, connectionPressure, urgency, walkingSpeedMps, bagCount,
      stressLoad: 0, frustration: 0, frustrationBurden: 0, peakFrustration: 0,
      prepState: 'waiting', prepCorrect: false, correctionCount: 0, seated: false
    };
    p.stressLoad = initialStressLoad(p, scenario, behaviour);
    p.frustration = frustrationFromLoad(p, behaviour);
    p.peakFrustration = p.frustration;
    passengers.push(p);
  }
  applyCompanionCompatibility(passengers, strategy, rng.fork(71));
  return passengers;
}
