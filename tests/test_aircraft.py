import unittest

from boarding_sim.access import simulate_access
from boarding_sim.aircraft import (
    custom_service_seconds,
    resolve_conflict,
    simulate_aircraft,
)
from boarding_sim.population import generate_population
from boarding_sim.preparation import simulate_preparation
from boarding_sim.prng import RNG
from boarding_sim.serialization import canonical_json_bytes
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


class AircraftCellularAutomatonTests(unittest.TestCase):
    def setUp(self):
        self.calibration = load_behaviour_calibration()

    def run_case(self, patch=None, seed=500):
        scenario = normalize_scenario(patch)
        strategy = strategy_by_id(scenario["boarding"]["strategy"])
        root = RNG(seed)
        passengers = generate_population(
            scenario, strategy, root.fork(1), self.calibration
        )
        preparation = simulate_preparation(
            passengers, scenario, strategy, root.fork(2), self.calibration
        )
        access = simulate_access(
            passengers,
            scenario,
            root.fork(3),
            self.calibration,
            preparation.time_seconds,
        )
        aircraft = simulate_aircraft(
            passengers,
            access,
            scenario,
            root.fork(4),
            self.calibration,
            preparation.time_seconds,
        )
        return scenario, passengers, access, aircraft

    def test_custom_rule_transitions_exactly_at_each_threshold(self):
        config = normalize_scenario()["boarding"]
        self.assertEqual(custom_service_seconds(0.59, config), 15)
        self.assertEqual(custom_service_seconds(0.60, config), 20)
        self.assertEqual(custom_service_seconds(0.699999, config), 20)
        self.assertEqual(custom_service_seconds(0.70, config), 25)
        self.assertEqual(custom_service_seconds(0.80, config), 30)
        self.assertEqual(custom_service_seconds(0.90, config), 35)

    def test_baseline_seats_every_passenger_once_without_occupancy_violations(self):
        _, passengers, _, result = self.run_case(seed=88)
        self.assertFalse(result.timed_out)
        self.assertEqual(result.seated_count, 180)
        self.assertEqual(sum(passenger.seated for passenger in passengers), 180)
        self.assertEqual(len({(p.row, p.seat) for p in passengers if p.seated}), 180)
        self.assertEqual(result.diagnostics["occupiedSeatCount"], 180)
        self.assertEqual(result.diagnostics["occupancyViolations"], 0)
        self.assertEqual(result.diagnostics["simultaneousAisleSeatViolations"], 0)
        self.assertGreaterEqual(result.diagnostics["minimumServiceRemaining"], 0)
        self.assertLessEqual(
            result.diagnostics["maxAisleOccupancy"], result.diagnostics["aisleCells"]
        )
        seated_events = [event for event in result.events if event.type == "seated"]
        self.assertEqual(len({event.passenger_id for event in seated_events}), 180)

    def test_movement_audit_has_no_teleportation_or_backwards_movement(self):
        _, _, _, result = self.run_case(seed=91)
        self.assertTrue(result.movement_audit)
        for event in result.movement_audit:
            self.assertEqual(abs(event.to_cell - event.from_cell), 1)
            direction = 1 if event.door == "front" else -1
            self.assertEqual(event.to_cell - event.from_cell, direction)
            if direction == 1:
                self.assertLessEqual(event.to_cell, event.target_cell)
            else:
                self.assertGreaterEqual(event.to_cell, event.target_cell)

    def test_split_strategy_enters_through_both_independent_doors(self):
        patch = {
            "access": {"mode": "bus"},
            "boarding": {"strategy": "split_half_two_door"},
        }
        _, passengers, _, result = self.run_case(patch, seed=92)
        entries = [event for event in result.events if event.type == "aircraft_entered"]
        self.assertEqual({event.details["door"] for event in entries}, {"front", "rear"})
        by_id = {passenger.id: passenger for passenger in passengers}
        self.assertTrue(
            all(event.details["door"] == by_id[event.passenger_id].assigned_door for event in entries)
        )
        self.assertEqual(result.seated_count, 180)

    def test_service_models_are_complete_alternatives(self):
        field = self.run_case(
            {"boarding": {"serviceModel": "field_calibrated"}}, seed=93
        )[-1]
        custom = self.run_case(
            {"boarding": {"serviceModel": "user_occupancy_rule"}}, seed=93
        )[-1]
        field_starts = [event for event in field.events if event.type == "row_service_started"]
        custom_starts = [event for event in custom.events if event.type == "row_service_started"]
        self.assertTrue(any(event.details["baggageSeconds"] > 0 for event in field_starts))
        self.assertTrue(
            all(event.details["baggageSeconds"] == 0 and event.details["seatShuffleSeconds"] == 0 for event in custom_starts)
        )
        self.assertTrue(
            all(event.details["durationSeconds"] in {15, 20, 25, 30, 35} for event in custom_starts)
        )
        self.assertNotEqual(field.cabin_boarding_seconds, custom.cabin_boarding_seconds)

    def test_aircraft_output_is_deterministic(self):
        first = self.run_case(seed=303)[-1]
        second = self.run_case(seed=303)[-1]
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

    def test_conflict_resolution_uses_only_seeded_rng(self):
        contenders = [3, 8, 11, 14]
        self.assertEqual(
            resolve_conflict(contenders, RNG(999)),
            resolve_conflict(contenders, RNG(999)),
        )
        self.assertIn(resolve_conflict(contenders, RNG(10)), contenders)

    def test_boarding_timeout_is_reported_without_fabricated_completion(self):
        _, _, _, result = self.run_case(
            {"boarding": {"maxBoardingSeconds": 1}}, seed=94
        )
        self.assertTrue(result.timed_out)
        self.assertLess(result.seated_count, 180)
        self.assertIsNone(result.last_seat_time)


if __name__ == "__main__":
    unittest.main()
