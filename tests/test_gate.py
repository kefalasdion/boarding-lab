import copy
import unittest

from boarding_sim.gate import build_gate_plan
from boarding_sim.population import assign_strategy, generate_manifest
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


if __name__ == "__main__":
    unittest.main()
