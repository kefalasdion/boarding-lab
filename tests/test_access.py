import unittest

from boarding_sim.access import simulate_access
from boarding_sim.population import generate_population
from boarding_sim.preparation import simulate_preparation
from boarding_sim.prng import RNG
from boarding_sim.serialization import canonical_json_bytes
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


class AccessEngineTests(unittest.TestCase):
    def setUp(self):
        self.calibration = load_behaviour_calibration()

    def prepared_case(self, patch, seed):
        scenario = normalize_scenario(patch)
        strategy = strategy_by_id(scenario["boarding"]["strategy"])
        root = RNG(seed)
        passengers = generate_population(
            scenario, strategy, root.fork(1), self.calibration
        )
        preparation = simulate_preparation(
            passengers, scenario, strategy, root.fork(2), self.calibration
        )
        result = simulate_access(
            passengers,
            scenario,
            root.fork(3),
            self.calibration,
            preparation.time_seconds,
        )
        return scenario, passengers, preparation, result

    def test_bridge_models_scan_walk_and_door_headway(self):
        scenario, passengers, preparation, result = self.prepared_case(
            {"access": {"mode": "bridge"}}, 700
        )
        self.assertEqual(result.mode, "bridge")
        self.assertEqual(len(result.arrivals), len(passengers))
        self.assertTrue(all(arrival.door == "front" for arrival in result.arrivals))
        arrival_times = sorted(arrival.ready_time for arrival in result.arrivals)
        minimum = scenario["access"]["bridgeMinimumHeadwaySeconds"]
        self.assertTrue(all(b - a >= minimum - 1e-9 for a, b in zip(arrival_times, arrival_times[1:])))
        event_types = {event.type for event in result.events}
        self.assertIn("boarding_control_complete", event_types)
        self.assertIn("bridge_walk_complete", event_types)
        self.assertIn("aircraft_door_arrival", event_types)
        self.assertEqual(result.history[-1].access_arrived_count, len(passengers))
        self.assertGreater(result.transfer_end_seconds, preparation.time_seconds)

    def test_bus_models_capacity_loading_travel_and_two_unloading_streams(self):
        patch = {
            "access": {"mode": "bus"},
            "boarding": {"strategy": "split_half_two_door"},
        }
        _, passengers, _, result = self.prepared_case(patch, 701)
        self.assertEqual(result.mode, "bus")
        self.assertEqual(len(result.arrivals), len(passengers))
        self.assertEqual({arrival.door for arrival in result.arrivals}, {"front", "rear"})
        by_id = {passenger.id: passenger for passenger in passengers}
        self.assertTrue(
            all(arrival.door == by_id[arrival.passenger_id].assigned_door for arrival in result.arrivals)
        )
        self.assertEqual(len(result.buses), 2)
        self.assertTrue(all(bus["passengerCount"] <= 90 for bus in result.buses))
        event_types = {event.type for event in result.events}
        self.assertTrue({"bus_loaded", "bus_departed", "bus_arrived", "bus_unloaded"} <= event_types)
        self.assertEqual(result.history[-1].access_arrived_count, len(passengers))

    def test_access_output_is_deterministic(self):
        first = self.prepared_case({"access": {"mode": "bridge"}}, 808)[-1]
        second = self.prepared_case({"access": {"mode": "bridge"}}, 808)[-1]
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_bus_travel_is_a_seeded_distribution_not_a_constant_penalty(self):
        patch = {
            "access": {"mode": "bus"},
            "boarding": {"strategy": "split_half_two_door"},
        }
        first = self.prepared_case(patch, 901)[-1]
        second = self.prepared_case(patch, 902)[-1]
        first_travel = [bus["arriveAt"] - bus["departAt"] for bus in first.buses]
        second_travel = [bus["arriveAt"] - bus["departAt"] for bus in second.buses]
        self.assertNotEqual(first_travel, second_travel)
        self.assertTrue(all(value >= 30 for value in first_travel + second_travel))


if __name__ == "__main__":
    unittest.main()
