import { clamp, logistic, mean, quantile } from './stats.js';
import { evolvePassenger } from './frustration.js';
import { strategyComplexity } from './strategies.js';

function groupMembers(passengers) {
  const m = new Map();
  for (const p of passengers) if (p.familyId) {
    if (!m.has(p.familyId)) m.set(p.familyId, []);
    m.get(p.familyId).push(p);
  }
  return m;
}

function firstCohort(passengers) {
  return Math.min(...passengers.map(p => p.prepCohort));
}

function snapshot(passengers, t, phase = 'preparation') {
  const fs = passengers.map(p => p.frustration);
  const prepared = passengers.filter(p => p.prepCorrect).length;
  return { t, phase, meanF: mean(fs), p90F: quantile(fs,.9), p95F: quantile(fs,.95), prepared, seated: 0 };
}

export function simulatePreparation(passengers, scenario, strategy, rng, behaviour) {
  const cfg = scenario.preparation;
  const b = behaviour.preparationPerMinute;
  const dt = 1.0;
  const complexity = strategyComplexity(strategy);
  const families = groupMembers(passengers);
  const initial = firstCohort(passengers);
  const history = [snapshot(passengers, 0)];
  let t = 0;
  let totalCorrections = 0;

  // Initial position is state-dependent, but all passengers are already in the gate area.
  for (const p of passengers) {
    const standProb = clamp(.06 + .24 * p.urgency + .18 * p.frustration + .08 * p.socialSusceptibility, .02, .65);
    if (rng.bool(standProb)) p.prepState = 'standing';
    p.prepDistanceM = Math.max(2, cfg.averageStartDistanceM * clamp(1 + rng.normal(0,.35), .35, 1.8));
    p.moveRemainingS = 0;
    p.correctRemainingS = 0;
  }

  function readyCondition() {
    const overall = passengers.filter(p => p.prepCorrect).length / passengers.length;
    const first = passengers.filter(p => p.prepCohort === initial);
    const firstReady = first.filter(p => p.prepCorrect).length / Math.max(1, first.length);
    return { overall, firstReady, ready: overall >= cfg.readinessTarget && firstReady >= cfg.firstCohortTarget };
  }

  while (t < cfg.maxPreparationSeconds) {
    const stagedCount = passengers.filter(p => p.prepState === 'staged').length;
    const movingCount = passengers.filter(p => p.prepState === 'moving' || p.prepState === 'correcting').length;
    const standingCount = passengers.filter(p => p.prepState !== 'waiting').length;
    const gateDensity = clamp((stagedCount + movingCount) / Math.max(1, cfg.gateUsableAreaM2 / 1.0), 0, 1.6);
    const socialSignal = standingCount / passengers.length;
    const visibleProgress = stagedCount / passengers.length;
    const stagedMeanF = stagedCount ? mean(passengers.filter(p => p.prepState === 'staged').map(p => p.frustration)) : mean(passengers.map(p => p.frustration));

    for (const p of passengers) {
      if (p.prepState === 'staged') {
        const social = b.socialCoupling * p.socialSusceptibility * (stagedMeanF - p.frustration);
        evolvePassenger(p, dt,
          b.uncertainty * p.uncertaintySensitivity * (1 - visibleProgress) + Math.max(0, social),
          b.visibleProgressRecovery * visibleProgress + Math.max(0, -social), behaviour);
        continue;
      }

      if (p.prepState === 'correcting') {
        p.correctRemainingS -= dt;
        evolvePassenger(p, dt,
          b.instruction * complexity * (1 - p.compliance) + b.correctionShock,
          0, behaviour);
        if (p.correctRemainingS <= 0) {
          p.prepState = 'staged'; p.prepCorrect = true;
        }
        continue;
      }

      if (p.prepState === 'moving') {
        const speed = p.walkingSpeedMps / (1 + 1.8 * gateDensity * gateDensity);
        p.moveRemainingS -= dt * Math.max(.2, speed / Math.max(.2, p.walkingSpeedMps));
        evolvePassenger(p, dt,
          b.crowding * p.crowdSensitivity * gateDensity + b.instruction * complexity * .35,
          b.visibleProgressRecovery * .45, behaviour);
        if (p.moveRemainingS <= 0) {
          // Comprehension is derived from compliance, trust and structural complexity.
          const correctProb = clamp(.985 - .42 * complexity * (1 - p.compliance) - .14 * complexity * (1 - p.informationTrust), .45, .995);
          if (rng.bool(correctProb)) {
            p.prepState = 'staged'; p.prepCorrect = true;
          } else {
            p.prepState = 'correcting'; p.correctionCount++; totalCorrections++;
            p.correctRemainingS = 8 + 18 * complexity + rng.triangular(3,8,18);
          }
        }
        continue;
      }

      // waiting / standing: choice to start preparing is agent-based, not a fixed method delay.
      const family = p.familyId ? families.get(p.familyId) : null;
      const familyActive = family ? family.some(q => ['moving','correcting','staged'].includes(q.prepState)) : false;
      const noProgress = 1 - visibleProgress;
      const loadRate = b.uncertainty * p.uncertaintySensitivity * noProgress
        + b.noProgress * p.waitSensitivity * noProgress
        + b.crowding * p.crowdSensitivity * gateDensity
        + b.instruction * complexity * .25;
      const recovery = p.prepState === 'waiting' ? b.seatedRecovery : 0;
      evolvePassenger(p, dt, loadRate, recovery, behaviour);

      const d = behaviour.decision;
      const utility = d.activationBase
        + d.frustration * p.frustration
        + d.urgency * p.urgency
        + d.social * p.socialSusceptibility * socialSignal
        + d.family * (familyActive ? 1 : 0)
        + d.progress * visibleProgress
        - d.complexityPenalty * complexity * (1 - p.compliance);
      // Convert a per-decision propensity to per-second probability.
      const perSecond = 1 - Math.pow(1 - logistic(utility), dt / 5);
      if (rng.bool(perSecond)) {
        p.prepState = 'moving';
        const familySlowdown = family ? Math.max(...family.map(q => 1 / Math.max(.4, q.walkingSpeedMps))) * p.walkingSpeedMps : 1;
        p.moveRemainingS = (p.prepDistanceM / Math.max(.35, p.walkingSpeedMps)) * familySlowdown;
      } else if (p.prepState === 'waiting' && rng.bool(.05 + .15 * p.frustration)) {
        p.prepState = 'standing';
      }
    }

    t += dt;
    if (t % 10 === 0) history.push(snapshot(passengers, t));
    const rc = readyCondition();
    if (rc.ready) return { timeSeconds: t, passengers, history, corrections: totalCorrections, readiness: rc, complexity, timedOut: false };
  }
  const rc = readyCondition();
  return { timeSeconds: t, passengers, history, corrections: totalCorrections, readiness: rc, complexity, timedOut: true };
}
