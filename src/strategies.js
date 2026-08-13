const seatGroup = seat => (seat === 'A' || seat === 'F') ? 0 : (seat === 'B' || seat === 'E') ? 1 : 2;
const side = seat => ['A','B','C'].includes(seat) ? 0 : 1;
const zoneBackToFront = row => Math.floor((30 - row) / 5);

export const STRATEGIES = {
  random_front: {
    id: 'random_front', name: 'Random · front door', accessRecommended: 'bridge', prepCohorts: 1,
    cohort: () => 0,
    rank: (p, randomKey) => randomKey,
    door: () => 'front'
  },
  split_half_two_door: {
    id: 'split_half_two_door', name: 'Rows 1–15 front · 16–30 rear', accessRecommended: 'bus', prepCohorts: 2, preserveSeatDoor: true,
    cohort: p => p.row <= 15 ? 0 : 1,
    rank: (p, randomKey) => (p.row <= 15 ? 0 : 1) * 1000 + randomKey,
    door: p => p.row <= 15 ? 'front' : 'rear'
  },
  wilma: {
    id: 'wilma', name: 'A/F → B/E → C/D', accessRecommended: 'bridge', prepCohorts: 3,
    cohort: p => seatGroup(p.seat),
    rank: (p, randomKey) => seatGroup(p.seat) * 1000 + randomKey,
    door: () => 'front'
  },
  back_to_front_zones: {
    id: 'back_to_front_zones', name: 'Back-to-front · 5-row zones', accessRecommended: 'bridge', prepCohorts: 6,
    cohort: p => zoneBackToFront(p.row),
    rank: (p, randomKey) => zoneBackToFront(p.row) * 1000 + randomKey,
    door: () => 'front'
  },
  wilma_zones: {
    id: 'wilma_zones', name: 'Outside-in + back-to-front zones', accessRecommended: 'bridge', prepCohorts: 18,
    cohort: p => seatGroup(p.seat) * 6 + zoneBackToFront(p.row),
    rank: (p, randomKey) => (seatGroup(p.seat) * 6 + zoneBackToFront(p.row)) * 1000 + randomKey,
    door: () => 'front'
  },
  steffen_companion: {
    id: 'steffen_companion', name: 'Steffen-style · companion compatible', accessRecommended: 'bridge', prepCohorts: 12,
    cohort: p => seatGroup(p.seat) * 4 + side(p.seat) * 2 + (p.row % 2),
    rank: (p) => {
      const sg = seatGroup(p.seat), sd = side(p.seat), parity = p.row % 2;
      const descendingRow = 31 - p.row;
      return (sg * 4 + sd * 2 + parity) * 1000 + descendingRow;
    },
    door: () => 'front'
  },
  split_wilma_two_door: {
    id: 'split_wilma_two_door', name: 'Split doors + A/F → B/E → C/D', accessRecommended: 'bus', prepCohorts: 6, preserveSeatDoor: true,
    cohort: p => (p.row <= 15 ? 0 : 1) * 3 + seatGroup(p.seat),
    rank: (p, randomKey) => ((p.row <= 15 ? 0 : 1) * 3 + seatGroup(p.seat)) * 1000 + randomKey,
    door: p => p.row <= 15 ? 'front' : 'rear'
  }
};

export function strategyComplexity(strategy) {
  // Structural complexity only: monotonic with the number of distinct cohorts.
  // This is not a measured human-factors coefficient.
  return strategy.prepCohorts <= 1 ? 0 : Math.log2(strategy.prepCohorts) / Math.log2(18);
}

export function applyCompanionCompatibility(passengers, strategy, rng) {
  for (const p of passengers) {
    p.rawCohort = strategy.cohort(p);
    p.randomKey = rng.next();
    p.rawRank = strategy.rank(p, p.randomKey);
    p.assignedDoor = strategy.door(p);
  }
  const families = new Map();
  for (const p of passengers) if (p.familyId) {
    if (!families.has(p.familyId)) families.set(p.familyId, []);
    families.get(p.familyId).push(p);
  }
  for (const members of families.values()) {
    // Companions stay together. They take the earliest cohort/rank represented in the family.
    const cohort = Math.min(...members.map(p => p.rawCohort));
    const rank = Math.min(...members.map(p => p.rawRank));
    // A family cannot be split between aircraft doors. Use the door serving the majority of seats;
    // ties use the leader's door. This may reduce ideal strategy conformance, intentionally.
    const front = members.filter(p => p.assignedDoor === 'front').length;
    const rear = members.length - front;
    const commonDoor = front === rear ? members[0].assignedDoor : front > rear ? 'front' : 'rear';
    for (let k = 0; k < members.length; k++) {
      members[k].prepCohort = cohort;
      members[k].boardingRank = rank + k * 0.001;
      // For two-door half-cabin methods, preserve the seat-based door assignment.
      // Otherwise a family spanning the midpoint would create opposing aisle traffic.
      // The family stays in one preparation cohort but separates only at the aircraft-door branch.
      if (!strategy.preserveSeatDoor) members[k].assignedDoor = commonDoor;
      members[k].companionOverride = members[k].rawCohort !== cohort || (!strategy.preserveSeatDoor && strategy.door(members[k]) !== commonDoor);
    }
  }
  for (const p of passengers) if (!p.familyId) {
    p.prepCohort = p.rawCohort;
    p.boardingRank = p.rawRank;
    p.companionOverride = false;
  }
  return passengers;
}
