import json
import math
import unittest

from boarding_sim.prng import RNG
from boarding_sim.provenance import (
    load_parameter_registry,
    validate_registry_coverage,
)
from boarding_sim.serialization import canonical_json_bytes
from boarding_sim.validation import (
    ScenarioValidationError,
    load_behaviour_calibration,
    load_default_scenario,
    normalize_scenario,
)


class PRNGTests(unittest.TestCase):
    def test_mulberry32_sequence_is_fixed(self):
        rng = RNG(42)
        self.assertEqual(
            [rng.next(), rng.next(), rng.next()],
            [0.6011037519201636, 0.44829055899754167, 0.8524657934904099],
        )

    def test_forked_stream_is_repeatable(self):
        self.assertEqual(
            [RNG(99).fork(7).normal() for _ in range(3)],
            [RNG(99).fork(7).normal() for _ in range(3)],
        )

    def test_shuffle_is_seeded_and_does_not_use_global_randomness(self):
        first = RNG(12).shuffle(list(range(12)))
        second = RNG(12).shuffle(list(range(12)))
        self.assertEqual(first, second)
        self.assertNotEqual(first, list(range(12)))


class ValidationTests(unittest.TestCase):
    def test_patch_is_merged_into_a_complete_scenario(self):
        scenario = normalize_scenario({"flightContext": {"delayMinutes": 45}})
        self.assertEqual(scenario["flightContext"]["delayMinutes"], 45)
        self.assertEqual(scenario["aircraft"]["rows"], 30)
        self.assertEqual(scenario["preparation"]["policy"]["mode"], "strict_preparation")

    def test_unknown_scenario_keys_are_rejected_with_stable_paths(self):
        with self.assertRaises(ScenarioValidationError) as caught:
            normalize_scenario({"boarding": {"magicSpeedMultiplier": 2}})
        self.assertEqual(caught.exception.issues[0].path, "boarding.magicSpeedMultiplier")
        self.assertEqual(caught.exception.issues[0].code, "unknown_parameter")

    def test_unsupported_readiness_policy_is_rejected(self):
        with self.assertRaises(ScenarioValidationError) as caught:
            normalize_scenario({"preparation": {"policy": {"mode": "rolling_preparation"}}})
        self.assertEqual(caught.exception.issues[0].code, "unsupported_policy")

    def test_two_door_strategy_requires_two_stream_access(self):
        with self.assertRaises(ScenarioValidationError) as caught:
            normalize_scenario({"boarding": {"strategy": "split_half_two_door"}})
        self.assertTrue(any(issue.code == "incompatible_access" for issue in caught.exception.issues))

    def test_insufficient_single_trip_bus_capacity_is_rejected(self):
        with self.assertRaises(ScenarioValidationError) as caught:
            normalize_scenario({"access": {"mode": "bus", "busCount": 1, "busCapacity": 90}})
        self.assertTrue(any(issue.code == "insufficient_capacity" for issue in caught.exception.issues))

    def test_invalid_primitive_types_return_structured_issues(self):
        with self.assertRaises(ScenarioValidationError) as caught:
            normalize_scenario(
                {
                    "aircraft": {"rows": "thirty"},
                    "access": {"busCount": "two"},
                }
            )
        paths = {issue.path for issue in caught.exception.issues}
        self.assertIn("aircraft", paths)
        self.assertIn("access.busCount", paths)


class ProvenanceAndSerializationTests(unittest.TestCase):
    def test_registry_covers_every_configurable_leaf(self):
        issues = validate_registry_coverage(
            load_default_scenario(),
            load_behaviour_calibration(),
            load_parameter_registry(),
        )
        self.assertEqual(issues, [])

    def test_registry_has_only_supported_display_categories(self):
        categories = {entry["category"] for entry in load_parameter_registry()}
        self.assertLessEqual(
            categories,
            {"calibrated", "literature", "user", "operational", "provisional"},
        )

    def test_registry_values_cannot_drift_from_configuration(self):
        registry = load_parameter_registry()
        registry[0]["value"] = "drifted"
        issues = validate_registry_coverage(
            load_default_scenario(), load_behaviour_calibration(), registry
        )
        self.assertTrue(any("does not match configuration" in issue for issue in issues))

    def test_canonical_json_is_byte_equivalent(self):
        a = {"z": [3.5, 1], "a": {"b": True}}
        b = {"a": {"b": True}, "z": [3.5, 1]}
        self.assertEqual(canonical_json_bytes(a), canonical_json_bytes(b))
        self.assertEqual(canonical_json_bytes(a), b'{"a":{"b":true},"z":[3.5,1]}')

    def test_canonical_json_rejects_non_finite_numbers(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json_bytes({"value": value})


if __name__ == "__main__":
    unittest.main()
