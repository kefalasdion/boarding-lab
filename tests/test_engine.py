import math
import unittest

from boarding_sim.engine import run_flight
from boarding_sim.serialization import canonical_json_bytes, to_primitive
from boarding_sim.validation import ScenarioValidationError


def numeric_values(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from numeric_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from numeric_values(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield value


class FlightEngineTests(unittest.TestCase):
    def test_every_run_requires_an_explicit_seed(self):
        with self.assertRaises(ScenarioValidationError):
            run_flight({}, None)

    def test_result_preserves_three_conceptual_parts_and_t0_boundary(self):
        result = to_primitive(run_flight({}, 20260813))
        self.assertEqual(set(result["phases"]), {"part1_t0_state", "part2_preparation", "part3_embarkation"})
        self.assertEqual(result["phases"]["part1_t0_state"]["time_seconds"], 0)
        initial_load_mean = sum(
            passenger["initial_stress_load"] for passenger in result["passengers"]
        ) / len(result["passengers"])
        self.assertAlmostEqual(
            result["phases"]["part1_t0_state"]["latent_stress_load"]["mean"],
            initial_load_mean,
        )
        all_events = (
            result["phases"]["part2_preparation"]["events"]
            + result["phases"]["part3_embarkation"]["access"]["events"]
            + result["phases"]["part3_embarkation"]["aircraft"]["events"]
        )
        self.assertTrue(all(event["time_seconds"] >= 0 for event in all_events))
        self.assertNotIn("airport_arrival", canonical_json_bytes(result).decode("utf-8"))
        self.assertNotIn("security", canonical_json_bytes(result).decode("utf-8"))

    def test_complete_result_is_byte_deterministic(self):
        first = run_flight({"flightContext": {"delayMinutes": 65}}, 4401)
        second = run_flight({"flightContext": {"delayMinutes": 65}}, 4401)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_metrics_use_explicit_phase_definitions_and_passenger_distributions(self):
        result = to_primitive(run_flight({}, 4402))
        metrics = result["metrics"]
        timings = metrics["timings_seconds"]
        self.assertAlmostEqual(
            timings["total_t0_to_last_seat"],
            timings["preparation"] + timings["embarkation"],
        )
        self.assertGreaterEqual(timings["embarkation"], timings["cabin_boarding"])
        for key in (
            "initial_frustration",
            "frustration_burden_f_minutes",
            "peak_frustration",
            "time_above_threshold_minutes",
        ):
            self.assertEqual(metrics["passenger_experience"][key]["count"], 180)
        self.assertEqual(result["status"], "valid")
        self.assertEqual(metrics["seated_count"], 180)

    def test_phase_burdens_partition_total_burden_exactly(self):
        result = run_flight({}, 5101)
        for passenger in result.passengers:
            self.assertAlmostEqual(
                passenger.preparation_frustration_burden
                + passenger.embarkation_frustration_burden,
                passenger.frustration_burden,
                places=10,
            )
        experience = result.metrics["passenger_experience"]
        self.assertEqual(
            experience["frustration_burden_f_minutes"],
            experience["total_frustration_burden_f_minutes"],
        )

    def test_frustration_status_is_provisional_not_validated(self):
        result = to_primitive(run_flight({}, 4403))
        status = result["model_status"]
        self.assertFalse(status["frustration_validated"])
        self.assertFalse(status["operational_claims_allowed"])
        self.assertIn("Layer 4", status["warning"])

    def test_timeout_keeps_counts_and_uses_null_for_unobserved_last_seat(self):
        result = to_primitive(
            run_flight({"boarding": {"maxBoardingSeconds": 1}}, 4404)
        )
        self.assertEqual(result["status"], "timed_out")
        self.assertLess(result["metrics"]["seated_count"], 180)
        self.assertIsNone(result["metrics"]["timings_seconds"]["total_t0_to_last_seat"])
        self.assertIsNone(result["metrics"]["timings_seconds"]["embarkation"])

    def test_public_result_contains_only_finite_numbers(self):
        result = to_primitive(run_flight({}, 4405))
        self.assertTrue(all(math.isfinite(value) for value in numeric_values(result)))
        canonical_json_bytes(result)


if __name__ == "__main__":
    unittest.main()
