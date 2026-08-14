import unittest

from boarding_sim.comparison import PUBLIC_STRATEGY_IDS
from boarding_sim.engine import MODEL_VERSION, SCHEMA_VERSION
from boarding_sim.serialization import canonical_json_bytes
from scripts.build_default_comparison import DEFAULT_ARTIFACT_PATH, load_default_artifact


class DefaultArtifactTests(unittest.TestCase):
    def test_default_artifact_is_current_canonical_and_complete(self):
        artifact = load_default_artifact()
        self.assertEqual(artifact["schema_version"], SCHEMA_VERSION)
        self.assertEqual(artifact["model_version"], MODEL_VERSION)
        self.assertEqual(artifact["summary"]["requested_runs"], 100)
        self.assertEqual(
            artifact["representative"]["strategy_order"],
            list(PUBLIC_STRATEGY_IDS),
        )
        self.assertEqual(
            DEFAULT_ARTIFACT_PATH.read_bytes(), canonical_json_bytes(artifact)
        )

    def test_representative_never_fabricates_a_winner(self):
        representative = load_default_artifact()["representative"]
        if not all(
            result["status"] == "valid"
            for result in representative["strategies"].values()
        ):
            self.assertIsNone(representative["winner"])


if __name__ == "__main__":
    unittest.main()
