// Split the running accumulated frustration burden into the two phases the
// race compares: forming the line, and boarding the aircraft.
//
// Both figures are means over every passenger, so the two lanes stay
// comparable at any clock position and neither can be inflated by averaging
// over a handful of stragglers. The split is an exact time attribution taken
// from the simulation's own preparation checkpoint; it is not a claim about
// which phase caused the feeling.

/**
 * @param time current clock position in seconds from T=0
 * @param runningBurden serialized mean accumulated burden at that moment
 * @param preparationEndsAt this strategy's strict-readiness timestamp
 * @param preparationCheckpoint authoritative mean burden at that timestamp
 * @returns {{preparation: number|null, boarding: number|null}} in F-minutes
 */
export function phaseBurden({
  time,
  runningBurden,
  preparationEndsAt,
  preparationCheckpoint,
}) {
  if (!Number.isFinite(runningBurden)) return {preparation: null, boarding: null};
  if (!Number.isFinite(preparationCheckpoint) || time <= preparationEndsAt) {
    return {preparation: runningBurden, boarding: 0};
  }
  return {
    preparation: preparationCheckpoint,
    boarding: Math.max(0, runningBurden - preparationCheckpoint),
  };
}
