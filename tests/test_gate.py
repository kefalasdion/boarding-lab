import copy
import unittest

from boarding_sim.gate import build_gate_plan
from boarding_sim.population import assign_strategy, generate_manifest
from boarding_sim.preparation import simulate_preparation
from boarding_sim.prng import RNG
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


class GateLayoutTests(unittest.TestCase):
    def setUp(self):
        self.scenario = normalize_scenario()
        self.calibration = load_behaviour_calibration()
        self.manifest = generate_manifest(
            self.scenario, RNG(20260813), self.calibration
        )

    def passengers_for(self, strategy_id):
        return assign_strategy(
            copy.deepcopy(self.manifest),
            strategy_by_id(strategy_id),
            RNG(77),
        )

    def plan(self, strategy_id, seed=123):
        strategy = strategy_by_id(strategy_id)
        return build_gate_plan(
            self.passengers_for(strategy_id), self.scenario, strategy, RNG(seed)
        )

    def test_start_and_queue_positions_are_unique_and_bounded(self):
        plan = self.plan("random_front")
        self.assertEqual(len(plan.start_positions), 180)
        self.assertEqual(len(set(plan.start_positions.values())), 180)
        self.assertEqual(len(set(plan.queue_slots.values())), 180)
        for point in (*plan.start_positions.values(), *plan.queue_slots.values()):
            self.assertGreaterEqual(point.x_m, 0)
            self.assertLessEqual(point.x_m, plan.layout.width_m)
            self.assertGreaterEqual(point.y_m, 0)
            self.assertLessEqual(point.y_m, plan.layout.height_m)

    def test_each_public_queue_follows_authoritative_boarding_rank(self):
        for strategy_id in (
            "random_front",
            "back_to_front_zones",
            "strict_steffen",
        ):
            with self.subTest(strategy=strategy_id):
                plan = self.plan(strategy_id)
                passengers = self.passengers_for(strategy_id)
                ordered_ids = [
                    slot.passenger_id
                    for slot in sorted(plan.slots, key=lambda slot: slot.slot_index)
                ]
                expected_ids = [
                    passenger.id
                    for passenger in sorted(
                        passengers,
                        key=lambda passenger: (
                            passenger.boarding_rank,
                            passenger.id,
                        ),
                    )
                ]
                self.assertEqual(ordered_ids, expected_ids)

    def test_back_to_front_queue_keeps_six_visible_zone_bands(self):
        plan = self.plan("back_to_front_zones")
        band_centres = {}
        for slot in plan.slots:
            band_centres.setdefault(slot.cohort, []).append(slot.point.y_m)
        self.assertEqual(set(band_centres), set(range(6)))
        means = [
            sum(band_centres[cohort]) / len(band_centres[cohort])
            for cohort in range(6)
        ]
        self.assertEqual(len({round(value, 3) for value in means}), 6)

    def test_gate_plan_is_byte_stable_for_the_same_seed(self):
        self.assertEqual(
            self.plan("strict_steffen", seed=5150),
            self.plan("strict_steffen", seed=5150),
        )

    def test_complete_preparation_replay_has_no_overlaps_or_teleportation(self):
        scenario = normalize_scenario(
            {
                "boarding": {"strategy": "strict_steffen"},
                "preparation": {
                    "policy": {
                        "mode": "complete_preparation",
                        "readinessTarget": 1.0,
                        "firstCohortTarget": 1.0,
                    }
                },
            }
        )
        strategy = strategy_by_id("strict_steffen")
        passengers = assign_strategy(
            copy.deepcopy(self.manifest), strategy, RNG(77)
        )
        plan = build_gate_plan(passengers, scenario, strategy, RNG(123))
        result = simulate_preparation(
            passengers,
            scenario,
            strategy,
            RNG(456),
            self.calibration,
            gate_plan=plan,
        )
        self.assertFalse(result.timed_out)
        self.assertEqual(result.readiness.overall, 1.0)
        self.assertTrue(result.gate_replay.frames)
        previous = None
        passenger_by_id = {passenger.id: passenger for passenger in passengers}
        for frame in result.gate_replay.frames:
            points = {
                state.passenger_id: (state.x_m, state.y_m)
                for state in frame.passengers
            }
            self.assertEqual(len(points), len(set(points.values())))
            if previous is not None:
                elapsed = frame.time_seconds - previous.time_seconds
                previous_points = {
                    state.passenger_id: (state.x_m, state.y_m)
                    for state in previous.passengers
                }
                for passenger_id, point in points.items():
                    prior = previous_points[passenger_id]
                    distance = ((point[0] - prior[0]) ** 2 + (point[1] - prior[1]) ** 2) ** 0.5
                    maximum = passenger_by_id[passenger_id].walking_speed_mps * elapsed
                    self.assertLessEqual(
                        distance,
                        maximum + scenario["preparation"]["queueLaneSpacingM"],
                    )
            previous = frame
        final = {
            state.passenger_id: (state.x_m, state.y_m)
            for state in result.gate_replay.frames[-1].passengers
        }
        expected = {
            passenger_id: (point.x_m, point.y_m)
            for passenger_id, point in plan.queue_slots.items()
        }
        self.assertEqual(final, expected)


if __name__ == "__main__":
    unittest.main()
