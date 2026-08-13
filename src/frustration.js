import { clamp, logistic } from './stats.js';

export function frustrationFromLoad(passenger, behaviour) {
  return logistic((passenger.stressLoad - passenger.toleranceThreshold) / behaviour.frustrationSlope);
}

export function evolvePassenger(passenger, dtSeconds, loadRatePerMinute, recoveryRatePerMinute, behaviour) {
  const dtMin = dtSeconds / 60;
  passenger.stressLoad = clamp(passenger.stressLoad + dtMin * (loadRatePerMinute - recoveryRatePerMinute), 0, 2);
  passenger.frustration = frustrationFromLoad(passenger, behaviour);
  passenger.frustrationBurden += passenger.frustration * dtMin;
  passenger.peakFrustration = Math.max(passenger.peakFrustration, passenger.frustration);
}

export function initialStressLoad(passenger, scenario, behaviour) {
  const h = scenario.flightContext, c = behaviour.initial;
  const delayTerm = c.delay * passenger.delaySensitivity * Math.log1p(h.delayMinutes / 15);
  const gateWaitTerm = c.priorGateWait * passenger.waitSensitivity * Math.log1p(h.priorGateWaitMinutes / 30);
  const dwellTerm = c.airportDwell * passenger.fatigue * Math.log1p(h.priorAirportDwellMinutes / 60);
  const uncertaintyTerm = c.uncertainty * passenger.uncertaintySensitivity * (1 - passenger.informationTrust);
  const fatigueTerm = c.fatigue * passenger.fatigue;
  const connectionTerm = c.connection * passenger.connectionPressure;
  const infoTerm = c.unreliableInformation * (1 - passenger.informationTrust) * Math.min(1, h.priorDelayUpdates / 3);
  return clamp(delayTerm + gateWaitTerm + dwellTerm + uncertaintyTerm + fatigueTerm + connectionTerm + infoTerm, 0, 1.5);
}
