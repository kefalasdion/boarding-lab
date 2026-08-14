from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parent.parent


class WebAssetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.css = "\n".join(
            (ROOT / "web" / name).read_text(encoding="utf-8")
            for name in ("styles.css", "race.css", "expert.css")
            if (ROOT / "web" / name).exists()
        )
        cls.javascript = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((ROOT / "web" / "js").glob("*.js"))
        )

    def test_public_race_and_playback_mount_points_exist(self):
        for element_id in (
            "race-canvas",
            "master-clock",
            "play-toggle",
            "replay-button",
            "timeline-scrubber",
            "playback-speed",
            "frustration-legend",
            "passenger-inspector",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        for strategy_id in ("random", "back-to-front", "strict-steffen"):
            self.assertIn(f'id="lane-{strategy_id}-live"', self.html)

    def test_results_evidence_scenario_and_expert_contracts_exist(self):
        for element_id in (
            "result-headline",
            "timing-table",
            "heatmap",
            "evidence-disclosure",
            "scenario-controls",
            "expert-workspace",
            "sources",
            "copy-summary",
            "download-image",
            "heatmap-strategy",
            "heatmap-metric",
        ):
            self.assertIn(f'id="{element_id}"', self.html)

    def test_document_has_one_h1_and_meaningful_fallback_table(self):
        self.assertEqual(len(re.findall(r"<h1(?:\s|>)", self.html)), 1)
        self.assertIn('id="race-live-table"', self.html)
        for label in (
            "Preparation finished",
            "Boarding started",
            "Boarding finished",
            "During preparation",
            "During embarkation",
            "Total burden",
        ):
            self.assertIn(label, self.html)
        self.assertIn('aria-hidden="true"', self.html)
        self.assertIn('aria-live="polite"', self.html)

    def test_scientific_language_and_inspiration_credit_are_explicit(self):
        self.assertIn("model-predicted", self.html)
        self.assertIn("provisional", self.html)
        self.assertIn("Adam Jacobs", self.html)
        self.assertIn("boarding-only clock", self.html)
        self.assertIn("By Dennis Kefalas", self.html)
        self.assertNotIn("caused by", self.html.lower())

    def test_browser_code_only_displays_authoritative_model_outputs(self):
        for token in ("Math.random", "sigmoid", "weibull", "customServiceSeconds", "rowService"):
            self.assertNotIn(token, self.javascript)
        self.assertIn("preparation_frustration_burden_f_minutes", self.javascript)
        self.assertIn("embarkation_frustration_burden_f_minutes", self.javascript)
        self.assertIn("total_frustration_burden_f_minutes", self.javascript)

    def test_visual_system_is_accessible_and_responsive(self):
        for token in (
            "--warm-neutral",
            "--navy",
            "--action-blue",
            "--frustration-calm",
            "--frustration-critical",
        ):
            self.assertIn(token, self.css)
        self.assertIn(":focus-visible", self.css)
        self.assertIn("min-height: 44px", self.css)
        self.assertIn("max-width: 780px", self.css)
        self.assertIn("prefers-reduced-motion", self.css)
        self.assertIn("forced-colors", self.css)
        self.assertIn("@media print", self.css)

    def test_obsolete_root_entry_point_is_removed(self):
        self.assertFalse((ROOT / "index.html").exists())


if __name__ == "__main__":
    unittest.main()
