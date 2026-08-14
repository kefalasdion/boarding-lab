import json
import threading
import unittest
import urllib.error
import urllib.request

from boarding_sim.server import make_server


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = make_server("127.0.0.1", 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def request_json(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if payload is not None else "GET",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            self.assertEqual(response.headers.get_content_type(), "application/json")
            return response.status, json.load(response)

    def test_config_endpoint_exposes_scenario_strategies_and_provenance(self):
        status, payload = self.request_json("/api/config")
        self.assertEqual(status, 200)
        self.assertEqual(payload["defaultScenario"]["preparation"]["policy"]["mode"], "strict_preparation")
        self.assertEqual(len(payload["strategies"]), 8)
        self.assertTrue(payload["parameterProvenance"])
        self.assertFalse(payload["modelStatus"]["frustration_validated"])

    def test_run_endpoint_returns_real_typed_result(self):
        status, payload = self.request_json(
            "/api/run", {"scenario": {}, "seed": 8200}
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["seed"], 8200)
        self.assertEqual(payload["status"], "valid")
        self.assertEqual(payload["metrics"]["seated_count"], 180)

    def test_monte_carlo_endpoint_surfaces_all_run_counts(self):
        status, payload = self.request_json(
            "/api/monte-carlo",
            {"scenario": {}, "runs": 2, "baseSeed": 8300},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["requested_runs"], 2)
        self.assertEqual(
            payload["valid_runs"] + payload["timed_out_runs"] + payload["invalid_runs"],
            2,
        )

    def test_compare_endpoint_returns_the_public_three_lane_race(self):
        status, payload = self.request_json(
            "/api/compare",
            {"scenario": {"aircraft": {"loadFactor": 0.1}}, "seed": 8350},
        )
        self.assertEqual(status, 200)
        self.assertEqual(
            payload["strategy_order"],
            ["random_front", "back_to_front_zones", "strict_steffen"],
        )
        self.assertIn(payload["winner"], payload["strategies"])
        self.assertNotIn("parameter_provenance", payload["strategies"]["random_front"])
        self.assertIn("state_codebook", payload["strategies"]["random_front"]["replay"])
        self.assertLess(len(json.dumps(payload, separators=(",", ":"))), 6_000_000)

    def test_validation_errors_are_structured_http_400_responses(self):
        request = urllib.request.Request(
            self.base_url + "/api/run",
            data=json.dumps({"scenario": {"boarding": {"warp": 9}}, "seed": 1}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(caught.exception.code, 400)
        with caught.exception as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["error"], "validation_error")
        self.assertEqual(payload["issues"][0]["path"], "boarding.warp")

    def test_simulation_timeout_is_a_successful_modeled_response(self):
        status, payload = self.request_json(
            "/api/run",
            {"scenario": {"boarding": {"maxBoardingSeconds": 1}}, "seed": 8400},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "timed_out")

    def test_static_path_traversal_is_not_served(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base_url + "/%2e%2e/MODEL_SPEC.md", timeout=10)
        self.assertIn(caught.exception.code, {403, 404})
        caught.exception.close()

    def test_root_serves_the_browser_application(self):
        with urllib.request.urlopen(self.base_url + "/", timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "text/html")
            body = response.read().decode("utf-8")
        self.assertIn("Boarding Lab", body)
        self.assertIn('id="scenario-form"', body)

    def test_public_methodology_documents_are_readable(self):
        for path, expected in (
            ("/SOURCES.md", "Research sources"),
            ("/VALIDATION_PLAN.md", "Validation Plan"),
            ("/RESULT_SCHEMA.md", "Public Result Schema"),
        ):
            with urllib.request.urlopen(self.base_url + path, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(expected, response.read().decode("utf-8"))

    def test_default_artifact_has_public_cache_headers_and_etag(self):
        request = urllib.request.Request(self.base_url + "/data/default-comparison.json")
        with urllib.request.urlopen(request, timeout=10) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers["Cache-Control"], "public, max-age=3600")
            self.assertTrue(response.headers["ETag"])
            self.assertEqual(response.headers.get_content_type(), "application/json")
            self.assertGreater(len(response.read()), 1_000_000)

        conditional = urllib.request.Request(
            self.base_url + "/data/default-comparison.json",
            headers={"If-None-Match": response.headers["ETag"]},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(conditional, timeout=10)
        self.assertEqual(caught.exception.code, 304)
        caught.exception.close()

    def test_public_comparison_run_cap_is_structured_validation(self):
        request = urllib.request.Request(
            self.base_url + "/api/compare-monte-carlo",
            data=json.dumps({"scenario": {}, "runs": 201, "baseSeed": 1}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        self.assertEqual(caught.exception.code, 400)
        with caught.exception as response:
            payload = json.load(response)
        self.assertEqual(payload["issues"][0]["path"], "runs")

    def test_malformed_json_and_unknown_api_routes_are_rejected(self):
        malformed = urllib.request.Request(
            self.base_url + "/api/run",
            data=b"{not-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(malformed, timeout=10)
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base_url + "/api/unknown", timeout=10)
        self.assertEqual(caught.exception.code, 404)
        caught.exception.close()

    def test_security_headers_cover_html_and_json(self):
        for path in ("/", "/api/config"):
            with urllib.request.urlopen(self.base_url + path, timeout=10) as response:
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                self.assertEqual(response.headers["Referrer-Policy"], "no-referrer")
                self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])


if __name__ == "__main__":
    unittest.main()
