import unittest

from boarding_sim.comparison import PUBLIC_STRATEGY_IDS, run_comparison


class ComparisonTests(unittest.TestCase):
    def test_three_strategies_share_one_manifest_and_start_after_preparation(self):
        comparison = run_comparison({"aircraft": {"loadFactor": 0.1}}, 6100)

        self.assertEqual(list(comparison["strategies"]), list(PUBLIC_STRATEGY_IDS))
        fingerprints = {
            result["manifest_fingerprint"]
            for result in comparison["strategies"].values()
        }
        self.assertEqual(fingerprints, {comparison["manifest_fingerprint"]})

        for result in comparison["strategies"].values():
            preparation = result["phases"]["part2_preparation"]
            aircraft = result["phases"]["part3_embarkation"]["aircraft"]
            self.assertEqual(preparation["readiness"]["overall"], 1.0)
            self.assertGreaterEqual(
                aircraft["first_entry_time_seconds"],
                preparation["duration_seconds"],
            )

    def test_preparation_timeout_never_starts_boarding_or_declares_a_winner(self):
        comparison = run_comparison(
            {
                "aircraft": {"loadFactor": 0.1},
                "preparation": {"maxPreparationSeconds": 1},
            },
            6101,
        )

        self.assertIsNone(comparison["winner"])
        for result in comparison["strategies"].values():
            self.assertEqual(result["status"], "timed_out")
            embarkation = result["phases"]["part3_embarkation"]
            self.assertEqual(embarkation["status"], "not_started")
            self.assertEqual(embarkation["access"]["events"], [])
            self.assertEqual(embarkation["aircraft"]["events"], [])
            self.assertIsNone(
                result["metrics"]["timings_seconds"]["total_t0_to_last_seat"]
            )

    def test_family_separation_shock_occurs_only_for_strict_steffen(self):
        comparison = run_comparison({}, seed=20260841)

        for strategy_id in ("random_front", "back_to_front_zones"):
            events = comparison["strategies"][strategy_id]["phases"][
                "part2_preparation"
            ]["events"]
            self.assertFalse(
                any(event["type"] == "companion_separation_shock" for event in events)
            )

        strict = comparison["strategies"]["strict_steffen"]
        events = strict["phases"]["part2_preparation"]["events"]
        self.assertEqual(
            sum(
                event["type"] == "companion_separation_shock" for event in events
            ),
            strict["metrics"]["companion_overrides"],
        )


if __name__ == "__main__":
    unittest.main()
