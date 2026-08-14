import { mean, quantile } from './stats.js';
import { evolvePassenger } from './frustration.js';

const LEFT = ['A','B','C'];
const RIGHT = ['D','E','F'];

function targetCell(p, cfg) {
  return (p.row - 1) * cfg.aisleCellsPerRow + (cfg.aisleCellsPerRow - 1);
}

function seatMovementCount(p, occupied) {
  const key = s => occupied.has(`${p.row}${s}`);
  if (p.seat === 'C' || p.seat === 'D') return 1;
  if (p.seat === 'B') return key('C') ? 4 : 1;
  if (p.seat === 'E') return key('D') ? 4 : 1;
  if (p.seat === 'A') {
    const middle = key('B'), aisle = key('C');
    if (middle && aisle) return 9;
    if (middle) return 5;
    if (aisle) return 4;
    return 1;
  }
  if (p.seat === 'F') {
    const middle = key('E'), aisle = key('D');
    if (middle && aisle) return 9;
    if (middle) return 5;
    if (aisle) return 4;
    return 1;
  }
  return 1;
}

export function customSeatRuleSeconds(seatedFraction, cfg) {
  if (seatedFraction < cfg.customLoadThreshold) return cfg.customSeatBaseSeconds;
  const steps = Math.floor((seatedFraction - cfg.customLoadThreshold) / cfg.customIncrementLoadStep + 1e-9) + 1;
  return cfg.customSeatBaseSeconds + steps * cfg.customIncrementSeconds;
}

function rowServiceSeconds(p, occupiedSeats, seatedCount, total, cfg, rng) {
  if (cfg.serviceModel === 'user_occupancy_rule') {
    return customSeatRuleSeconds(seatedCount / total, cfg);
  }
  let baggage = 0;
  for (let k = 0; k < p.bagCount; k++) baggage += rng.weibull(cfg.baggageWeibullShape, cfg.baggageWeibullScaleSeconds);
  const movements = seatMovementCount(p, occupiedSeats);
  const [min, mode, max] = cfg.seatMovementTriangularSeconds;
  let seating = 0;
  for (let k = 0; k < movements; k++) seating += rng.triangular(min, mode, max);
  return baggage + seating;
}

function aggregate(passengers, t, seated) {
  const active = passengers.filter(p => !p.seated);
  const fs = active.length ? active.map(p => p.frustration) : passengers.map(p => p.frustration);
  return { t, phase:'boarding', meanF:mean(fs), p90F:quantile(fs,.9), p95F:quantile(fs,.95), prepared:passengers.length, seated };
}

export function simulateAircraftCA(passengers, arrivals, scenario, rng, behaviour) {
  const cfg = scenario.boarding, b = behaviour.cabinPerMinute;
  const total = passengers.length;
  const aisleCells = scenario.aircraft.rows * cfg.aisleCellsPerRow;
  const dt = cfg.dtSeconds;
  const firstReady = Math.min(...arrivals.map(a => a.readyTime));
  let t = firstReady, firstEntryTime = null, lastSeatTime = null, seatedCount = 0;
  let maxAisleOccupancy = 0, conflictCount = 0;
  const occupiedSeats = new Set();
  const inAisle = new Map(); // passenger id -> {p, cell, state, serviceRemaining, moveCredit}
  const queues = {front:[], rear:[]};
  for (const a of arrivals) queues[a.door].push({...a, entered:false});
  for (const d of ['front','rear']) queues[d].sort((x,y)=>x.readyTime-y.readyTime || x.passenger.boardingRank-y.passenger.boardingRank);
  const history = [aggregate(passengers, t, seatedCount)];
  const events = [];

  for (const p of passengers) { p.seated = false; p.aircraftState = 'not_arrived'; }

  while (seatedCount < total && t - firstReady < cfg.maxBoardingSeconds) {
    // Complete / progress row services. The passenger occupies the aisle cell while servicing.
    for (const rec of inAisle.values()) {
      if (rec.state === 'service') {
        rec.serviceRemaining -= dt;
        evolvePassenger(rec.p, dt, b.rowServiceEffort, 0, behaviour);
        if (rec.serviceRemaining <= 0) {
          rec.p.seated = true; rec.p.aircraftState = 'seated'; seatedCount++;
          occupiedSeats.add(`${rec.p.row}${rec.p.seat}`);
          events.push({type:'seated', t, passengerId:rec.p.id, row:rec.p.row, seat:rec.p.seat});
          inAisle.delete(rec.p.id);
          lastSeatTime = t;
        }
      }
    }

    const occupancy = new Map();
    for (const rec of inAisle.values()) occupancy.set(rec.cell, rec);
    maxAisleOccupancy = Math.max(maxAisleOccupancy, occupancy.size);

    // Start row service for passengers already at their row.
    for (const rec of inAisle.values()) {
      if (rec.state !== 'walking') continue;
      if (rec.cell === targetCell(rec.p, cfg)) {
        rec.state = 'service'; rec.p.aircraftState = 'row_service';
        rec.serviceRemaining = rowServiceSeconds(rec.p, occupiedSeats, seatedCount, total, cfg, rng);
        events.push({type:'service_start', t, passengerId:rec.p.id, duration:rec.serviceRemaining});
      }
    }

    // Snapshot after service starts. Service cells remain occupied and block the aisle.
    const occSnapshot = new Map();
    for (const rec of inAisle.values()) occSnapshot.set(rec.cell, rec);
    const proposals = new Map();
    for (const rec of inAisle.values()) {
      if (rec.state !== 'walking') continue;
      const target = targetCell(rec.p, cfg);
      if (rec.cell === target) continue;
      rec.moveCredit += Math.min(rec.p.walkingSpeedMps, cfg.walkingSpeedMps) * dt / cfg.cellSizeM;
      if (rec.moveCredit < 1) {
        evolvePassenger(rec.p, dt, b.aisleBlocked * .25, 0, behaviour);
        continue;
      }
      const dir = target > rec.cell ? 1 : -1;
      const next = rec.cell + dir;
      if (next < 0 || next >= aisleCells || occSnapshot.has(next)) {
        evolvePassenger(rec.p, dt, b.aisleBlocked * rec.p.waitSensitivity, 0, behaviour);
        continue;
      }
      if (!proposals.has(next)) proposals.set(next, []);
      proposals.get(next).push(rec);
    }

    for (const [cell, contenders] of proposals) {
      let winner = contenders[0];
      if (contenders.length > 1) {
        conflictCount += contenders.length - 1;
        winner = contenders[Math.floor(rng.next() * contenders.length)];
      }
      winner.cell = cell; winner.moveCredit -= 1; winner.p.aircraftState = 'aisle_moving';
      evolvePassenger(winner.p, dt, 0, b.aisleMovingRecovery, behaviour);
      for (const loser of contenders) if (loser !== winner) evolvePassenger(loser.p, dt, b.aisleBlocked * loser.p.waitSensitivity, 0, behaviour);
    }

    // Update passengers waiting at aircraft doors and enter if the door cell is clear.
    const currentOcc = new Map();
    for (const rec of inAisle.values()) currentOcc.set(rec.cell, rec);
    for (const door of ['front','rear']) {
      const queue = queues[door];
      for (const item of queue) {
        if (item.entered || item.readyTime > t) continue;
        item.passenger.aircraftState = 'door_queue';
        evolvePassenger(item.passenger, dt, b.doorQueue * item.passenger.waitSensitivity, 0, behaviour);
      }
      const nextItem = queue.find(x => !x.entered && x.readyTime <= t);
      if (!nextItem) continue;
      const entryCell = door === 'front' ? 0 : aisleCells - 1;
      if (!currentOcc.has(entryCell)) {
        nextItem.entered = true;
        const p = nextItem.passenger;
        p.aircraftState = 'aisle_moving';
        inAisle.set(p.id, {p, cell:entryCell, state:'walking', serviceRemaining:0, moveCredit:0});
        currentOcc.set(entryCell, inAisle.get(p.id));
        if (firstEntryTime === null) firstEntryTime = t;
        events.push({type:'entered', t, passengerId:p.id, door});
      }
    }

    t += dt;
    if (Math.abs((t - firstReady) % 10) < dt / 2) history.push(aggregate(passengers, t, seatedCount));
  }

  return {
    passengers, history, events,
    firstAircraftReadyTime:firstReady,
    firstEntryTime, lastSeatTime,
    cabinBoardingSeconds:firstEntryTime === null || lastSeatTime === null ? null : lastSeatTime - firstEntryTime,
    aircraftPhaseSeconds:lastSeatTime === null ? cfg.maxBoardingSeconds : lastSeatTime - firstReady,
    seatedCount, timedOut:seatedCount < total,
    debug:{aisleCells,maxAisleOccupancy,conflictCount,occupiedSeatCount:occupiedSeats.size}
  };
}
