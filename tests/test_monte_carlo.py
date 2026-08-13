import unittest

from boarding_sim.engine import run_flight
from boarding_sim.monte_carlo import (
    MonteCarloRunRecord,
    aggregate_run_records,
    run_monte_carlo,
)
from boarding_sim.serialization import canonical_json_bytes, to_primitive
from boarding_sim.validation import ScenarioValidationError


class MonteCarloTests(unittest.TestCase):
    def test_batch_is_deterministic_and_uses_sequential_population_seeds(self):
        first = run_monte_carlo({}, runs=3, base_seed=7000)
        second = run_monte_carlo({}, runs=3, base_seed=7000)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        primitive = to_primitive(first)
        self.assertEqual([record["seed"] for record in primitive["run_records"]], [7000, 7001, 7002])
        self.assertEqual(primitive["valid_runs"], 3)
        self.assertEqual(primitive["timed_out_runs"], 0)
        self.assertEqual(primitive["invalid_runs"], 0)

    def test_summaries_include_quantiles_and_mean_confidence_intervals(self):
        result = to_primitive(run_monte_carlo({}, runs=4, base_seed=7100))
        total = result["summaries"]["total_seconds"]
        self.assertLessEqual(total["p10"], total["p50"])
        self.assertLessEqual(total["p50"], total["p90"])
        self.assertLessEqual(total["mean_ci95_low"], total["mean"])
        self.assertGreaterEqual(total["mean_ci95_high"], total["mean"])
        for required in (
            "preparation_seconds",
            "embarkation_seconds",
            "cabin_boarding_seconds",
            "mean_frustration_burden",
            "p90_frustration_burden",
            "mean_peak_frustration",
            "p90_peak_frustration",
            "share_peak_above_threshold",
            "correction_events",
        ):
            self.assertIn(required, result["summaries"])

    def test_timed_out_runs_are_counted_and_excluded_from_summaries(self):
        result = to_primitive(
            run_monte_carlo(
                {"boarding": {"maxBoardingSeconds": 1}},
                runs=3,
                base_seed=7200,
            )
        )
        self.assertEqual(result["valid_runs"], 0)
        self.assertEqual(result["timed_out_runs"], 3)
        self.assertEqual(result["invalid_runs"], 0)
        self.assertTrue(all(value is None for value in result["summaries"].values()))

    def test_aggregator_counts_invalid_records_without_polluting_valid_metrics(self):
        valid = run_flight({}, 7300)
        records = [
            MonteCarloRunRecord(seed=7300, status="valid", metrics=valid.metrics),
            MonteCarloRunRecord(seed=7301, status="timed_out"),
            MonteCarloRunRecord(seed=7302, status="invalid", error_code="synthetic_failure"),
        ]
        result = to_primitive(aggregate_run_records(records, base_seed=7300))
        self.assertEqual(result["requested_runs"], 3)
        self.assertEqual(result["valid_runs"], 1)
        self.assertEqual(result["timed_out_runs"], 1)
        self.assertEqual(result["invalid_runs"], 1)
        self.assertEqual(result["summaries"]["total_seconds"]["count"], 1)

    def test_run_count_and_seed_range_are_validated(self):
        with self.assertRaises(ScenarioValidationError):
            run_monte_carlo({}, runs=0, base_seed=1)
        with self.assertRaises(ScenarioValidationError):
            run_monte_carlo({}, runs=2, base_seed=0xFFFFFFFF)


if __name__ == "__main__":
    unittest.main()
