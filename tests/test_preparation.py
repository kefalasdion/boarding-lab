import unittest

from boarding_sim.population import generate_population
from boarding_sim.preparation import (
    StrictPreparationPolicy,
    readiness_policy_from_config,
    simulate_preparation,
)
from boarding_sim.prng import RNG
from boarding_sim.serialization import canonical_json_bytes
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


class PreparationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.scenario = normalize_scenario()
        self.calibration = load_behaviour_calibration()
        self.strategy = strategy_by_id("wilma")
        self.passengers = generate_population(
            self.scenario, self.strategy, RNG(51), self.calibration
        )

    def test_strict_policy_is_an_explicit_object(self):
        policy = readiness_policy_from_config(self.scenario["preparation"]["policy"])
        self.assertIsInstance(policy, StrictPreparationPolicy)
        state = policy.evaluate(self.passengers)
        self.assertFalse(state.ready)
        self.assertEqual(state.overall, 0)

    def test_strict_policy_requires_overall_and_first_cohort_targets(self):
        policy = StrictPreparationPolicy(readiness_target=0.5, first_cohort_target=1.0)
        first = min(p.prep_cohort for p in self.passengers)
        for passenger in self.passengers[:100]:
            passenger.prep_correct = True
        first_members = [p for p in self.passengers if p.prep_cohort == first]
        first_members[-1].prep_correct = False
        self.assertFalse(policy.evaluate(self.passengers).ready)
        for passenger in first_members:
            passenger.prep_correct = True
        self.assertTrue(policy.evaluate(self.passengers).ready)


class PreparationEngineTests(unittest.TestCase):
    def run_preparation(self, seed=100, patch=None):
        scenario = normalize_scenario(patch)
        strategy = strategy_by_id(scenario["boarding"]["strategy"])
        passengers = generate_population(scenario, strategy, RNG(seed).fork(1), self.calibration)
        result = simulate_preparation(
            passengers, scenario, strategy, RNG(seed).fork(2), self.calibration
        )
        return passengers, result

    def setUp(self):
        self.calibration = load_behaviour_calibration()

    def test_baseline_reaches_strict_readiness_with_progress_history(self):
        passengers, result = self.run_preparation()
        self.assertFalse(result.timed_out)
        self.assertTrue(result.readiness.ready)
        self.assertGreaterEqual(result.readiness.overall, 0.90)
        self.assertGreaterEqual(result.readiness.first_cohort, 0.95)
        self.assertEqual(result.history[0].time_seconds, 0)
        prepared = [sample.prepared_count for sample in result.history]
        self.assertEqual(prepared, sorted(prepared))
        self.assertEqual(sum(p.correction_count for p in passengers), result.corrections)
        self.assertEqual(
            len([event for event in result.events if event.type == "preparation_correction"]),
            result.corrections,
        )

    def test_preparation_is_deterministic(self):
        _, first = self.run_preparation(seed=911)
        _, second = self.run_preparation(seed=911)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_preparation_timeout_is_a_modeled_result(self):
        _, result = self.run_preparation(
            seed=17, patch={"preparation": {"maxPreparationSeconds": 1}}
        )
        self.assertTrue(result.timed_out)
        self.assertFalse(result.readiness.ready)
        self.assertEqual(result.time_seconds, 1)


if __name__ == "__main__":
    unittest.main()
