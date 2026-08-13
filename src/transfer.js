import { clamp } from './stats.js';
import { evolvePassenger } from './frustration.js';

function sortedForBoarding(passengers) {
  return [...passengers].sort((a,b) => a.boardingRank - b.boardingRank || a.id - b.id);
}

function serviceTimeline(queue, startTime, rng, meanSeconds) {
  let t = startTime; const out = [];
  for (const p of queue) {
    // Gamma-like positive service time from two exponentials, lower variance than one exponential.
    const svc = (rng.exponential(meanSeconds / 2) + rng.exponential(meanSeconds / 2));
    t += Math.max(.35, svc);
    out.push({ passenger: p, completed: t });
  }
  return out;
}

function evolvePiecewise(p, seconds, stress, recovery, behaviour) {
  if (seconds <= 0) return;
  evolvePassenger(p, seconds, stress, recovery, behaviour);
}

export function simulateBridgeTransfer(passengers, scenario, rng, behaviour, phaseStartSeconds) {
  const cfg = scenario.access, b = behaviour.transferPerMinute;
  const q = sortedForBoarding(passengers);
  const scan = serviceTimeline(q, phaseStartSeconds, rng, cfg.gateScanMeanSeconds);
  let lastDoorTime = phaseStartSeconds;
  const arrivals = [];
  for (let i = 0; i < scan.length; i++) {
    const {passenger:p, completed:scanDone} = scan[i];
    const walk = cfg.bridgeLengthM / Math.max(.5, Math.min(cfg.bridgeWalkSpeedMps, p.walkingSpeedMps + .3));
    let ready = scanDone + walk;
    // Preserve the measured aircraft-door mean spacing as a baseline constraint.
    ready = Math.max(ready, lastDoorTime + cfg.bridgeMinimumHeadwaySeconds);
    const waitBeforeScan = Math.max(0, scanDone - phaseStartSeconds - cfg.gateScanMeanSeconds);
    evolvePiecewise(p, waitBeforeScan, b.bridgeWaiting * p.waitSensitivity, 0, behaviour);
    evolvePiecewise(p, walk, 0, b.bridgeWalkingRecovery, behaviour);
    lastDoorTime = ready;
    arrivals.push({ passenger:p, door:'front', readyTime:ready });
  }
  return { arrivals, transferEndSeconds:lastDoorTime, mode:'bridge' };
}

export function simulateBusTransfer(passengers, scenario, rng, behaviour, phaseStartSeconds) {
  const cfg = scenario.access, b = behaviour.transferPerMinute;
  const q = sortedForBoarding(passengers);
  const busCount = Math.max(1, cfg.busCount);
  const buses = Array.from({length:busCount}, (_,id)=>({id, passengers:[], readyAt:phaseStartSeconds, departAt:null, arriveAt:null}));
  // Assign by earliest available bus with capacity. Loading occurs in parallel across bus doors.
  for (const p of q) {
    const eligible = buses.filter(x => x.passengers.length < cfg.busCapacity);
    const bus = eligible.sort((a,busB)=>a.readyAt-busB.readyAt || a.id-busB.id)[0];
    if (!bus) throw new Error('Bus capacity is insufficient for passenger count.');
    const svc = Math.max(.35, rng.exponential(cfg.busBoardMeanSeconds));
    const start = Math.max(phaseStartSeconds, bus.readyAt);
    const done = start + svc;
    bus.passengers.push({p, loadedAt:done}); bus.readyAt = done;
  }
  for (const bus of buses) {
    if (!bus.passengers.length) continue;
    bus.departAt = bus.readyAt;
    bus.arriveAt = bus.departAt + Math.max(30, rng.normal(cfg.busTravelMeanSeconds, cfg.busTravelSdSeconds));
  }

  const arrivals=[];
  for (const bus of buses) {
    if (!bus.passengers.length) continue;
    const doorStreams = {front:[], rear:[]};
    for (const rec of bus.passengers) doorStreams[rec.p.assignedDoor || 'front'].push(rec);
    for (const door of ['front','rear']) {
      let t = bus.arriveAt;
      for (const rec of doorStreams[door]) {
        const p = rec.p;
        t += Math.max(.25, rng.exponential(cfg.busUnloadMeanSeconds));
        const gateWait = Math.max(0, rec.loadedAt - phaseStartSeconds - cfg.busBoardMeanSeconds);
        const busWait = Math.max(0, bus.departAt - rec.loadedAt);
        const travel = Math.max(0, bus.arriveAt - bus.departAt);
        const unload = Math.max(0, t - bus.arriveAt);
        evolvePiecewise(p, gateWait, b.busWaiting * p.waitSensitivity, 0, behaviour);
        evolvePiecewise(p, busWait, b.busWaiting * p.waitSensitivity + b.busCrowding * p.crowdSensitivity, 0, behaviour);
        evolvePiecewise(p, travel, b.busCrowding * .35 * p.crowdSensitivity, b.busMovingRecovery, behaviour);
        evolvePiecewise(p, unload, 0, b.unloadingRecovery, behaviour);
        arrivals.push({passenger:p, door, readyTime:t});
      }
    }
  }
  arrivals.sort((a,b)=>a.readyTime-b.readyTime || a.passenger.boardingRank-b.passenger.boardingRank);
  return { arrivals, transferEndSeconds:Math.max(...arrivals.map(x=>x.readyTime)), mode:'bus', buses };
}

export function simulateTransfer(passengers, scenario, rng, behaviour, phaseStartSeconds) {
  return scenario.access.mode === 'bus'
    ? simulateBusTransfer(passengers, scenario, rng, behaviour, phaseStartSeconds)
    : simulateBridgeTransfer(passengers, scenario, rng, behaviour, phaseStartSeconds);
}
