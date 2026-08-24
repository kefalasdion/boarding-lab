"""Every passenger must reach their marked slot; no run may stall at the gate."""

import unittest

from boarding_sim.comparison import PUBLIC_STRATEGY_IDS, run_comparison
from boarding_sim.metrics import companion_separations
from boarding_sim.population import generate_manifest
from boarding_sim.prng import RNG
from boarding_sim.strategies import strategy_by_id
from boarding_sim.population import assign_strategy
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario

# Seeds that stalled before gate steering existed: a passenger whose slot sat behind
# already-staged passengers had no route to it and preparation ran to its timeout.
PREVIOUSLY_STALLING_SEEDS = (20260814, 20260825, 20260839, 20260842, 20260899, 20260908)

PATCH = {"preparation": {"replaySampleSeconds": 6}}


class GateReachabilityTests(unittest.TestCase):
    def test_previously_stalling_seeds_now_complete(self):
        for seed in PREVIOUSLY_STALLING_SEEDS:
            with self.subTest(seed=seed):
                comparison = run_comparison(PATCH, seed)
                for strategy_id in PUBLIC_STRATEGY_IDS:
                    result = comparison["strategies"][strategy_id]
                    self.assertEqual(
                        result["status"],
                        "valid",
                        f"{strategy_id} did not finish at seed {seed}",
                    )
                    self.assertEqual(result["metrics"]["seated_count"], 180)

    def test_every_passenger_is_correctly_staged_before_boarding(self):
        comparison = run_comparison(PATCH, 20260814)
        for strategy_id in PUBLIC_STRATEGY_IDS:
            readiness = comparison["strategies"][strategy_id]["phases"][
                "part2_preparation"
            ]["readiness"]
            self.assertEqual(readiness["overall"], 1.0, strategy_id)


class CompanionSeparationTests(unittest.TestCase):
    """A method that keeps companions together must report zero separations."""

    def _passengers(self, strategy_id, seed=20260888):
        scenario = normalize_scenario()
        calibration = load_behaviour_calibration()
        manifest = generate_manifest(scenario, RNG(seed).fork(1), calibration)
        return assign_strategy(manifest, strategy_by_id(strategy_id), RNG(seed).fork(1))

    def test_companion_preserving_methods_separate_nobody(self):
        for strategy_id in ("random_front", "back_to_front_zones", "wilma"):
            with self.subTest(strategy=strategy_id):
                self.assertEqual(companion_separations(self._passengers(strategy_id)), 0)

    def test_strict_steffen_separates_every_companion(self):
        passengers = self._passengers("strict_steffen")
        family_passengers = sum(1 for p in passengers if p.family_id)
        self.assertEqual(companion_separations(passengers), family_passengers)

    def test_separations_are_distinct_from_policy_overrides(self):
        """Back-to-front moves people between zones without splitting anyone up."""
        passengers = self._passengers("back_to_front_zones")
        overrides = sum(p.companion_override for p in passengers)
        self.assertGreater(overrides, 0)
        self.assertEqual(companion_separations(passengers), 0)


if __name__ == "__main__":
    unittest.main()
