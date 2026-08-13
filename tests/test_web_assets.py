from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class WebAssetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")
        cls.javascript = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    def test_interface_has_controls_and_all_three_model_parts(self):
        for element_id in (
            "scenario-form",
            "seed",
            "strategy",
            "access-mode",
            "service-model",
            "run-flight",
            "compare-strategies",
            "part-1",
            "part-2",
            "part-3",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn("T=0", self.html)
        self.assertIn("Preparation", self.html)
        self.assertIn("Embarkation", self.html)

    def test_required_metrics_charts_and_distributions_have_mount_points(self):
        for element_id in (
            "metric-total",
            "metric-preparation",
            "metric-embarkation",
            "metric-cabin",
            "t0-population",
            "preparation-chart",
            "embarkation-chart",
            "frustration-chart",
            "burden-histogram",
            "peak-histogram",
            "monte-carlo-table",
            "provenance-table",
        ):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_uncertainty_and_unsuccessful_run_counts_are_visible_contracts(self):
        self.assertIn("P10–P90", self.html)
        self.assertIn("95% mean interval", self.html)
        self.assertIn("Timed out", self.html)
        self.assertIn("Invalid", self.html)
        self.assertIn("valid_runs", self.javascript)
        self.assertIn("timed_out_runs", self.javascript)
        self.assertIn("invalid_runs", self.javascript)

    def test_all_provenance_badge_categories_are_styled(self):
        for category in ("calibrated", "literature", "user", "operational", "provisional"):
            self.assertIn(f'.provenance-badge[data-category="{category}"]', self.css)

    def test_ui_does_not_duplicate_simulation_rules_or_randomness(self):
        forbidden = ("Math.random", "sigmoid", "weibull", "customServiceSeconds", "rowService")
        for token in forbidden:
            self.assertNotIn(token, self.javascript)

    def test_accessibility_responsiveness_and_reduced_motion_are_present(self):
        self.assertIn("aria-live", self.html)
        self.assertIn("aria-label", self.html)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("@media", self.css)

    def test_p90_trajectory_has_a_distinct_dashed_style(self):
        self.assertIn('"is-p90"', self.javascript)
        self.assertIn(".chart-path.is-p90", self.css)


if __name__ == "__main__":
    unittest.main()
