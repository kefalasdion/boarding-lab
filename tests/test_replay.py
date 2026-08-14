import unittest

from boarding_sim.engine import run_flight
from boarding_sim.serialization import canonical_json_bytes, to_primitive


class ReplayTests(unittest.TestCase):
    def test_replay_is_continuous_and_traces_every_passenger(self):
        result = to_primitive(run_flight({}, 5100))
        replay = result["replay"]
        self.assertEqual(replay["starts_at_seconds"], 0)
        self.assertEqual(
            replay["ends_at_seconds"],
            result["metrics"]["timings_seconds"]["total_t0_to_last_seat"],
        )
        passenger_ids = {passenger["id"] for passenger in result["passengers"]}
        self.assertEqual(
            set(map(int, replay["passenger_tracks"])), passenger_ids
        )
        self.assertLess(len(canonical_json_bytes(replay)), 2_500_000)

    def test_replay_frames_carry_live_index_and_accumulated_burden(self):
        replay = to_primitive(run_flight({}, 5102))["replay"]
        frames = replay["frustration_frames"]
        self.assertTrue(frames)
        for time_seconds, mean_frustration, mean_burden, passengers in frames:
            self.assertGreaterEqual(time_seconds, 0)
            self.assertGreaterEqual(mean_frustration, 0)
            self.assertLessEqual(mean_frustration, 1)
            self.assertGreaterEqual(mean_burden, 0)
            self.assertEqual(len(passengers), 180)
            self.assertTrue(all(len(state) == 4 for state in passengers))

    def test_replay_includes_aircraft_movement_and_seating_events(self):
        replay = to_primitive(run_flight({}, 5103))["replay"]
        event_codes = {event[1] for event in replay["aircraft_events"]}
        self.assertIn(replay["event_codebook"]["aircraft_entered"], event_codes)
        self.assertIn(replay["event_codebook"]["aisle_moved"], event_codes)
        self.assertIn(replay["event_codebook"]["seated"], event_codes)


if __name__ == "__main__":
    unittest.main()
