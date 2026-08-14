import copy
import math
import unittest

from boarding_sim.frustration import evolve_passenger, frustration_from_load
from boarding_sim.population import assign_strategy, generate_manifest, generate_population
from boarding_sim.prng import RNG
from boarding_sim.strategies import STRATEGIES, strategy_by_id, strict_steffen_key
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


def correlation(xs, ys):
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - x_mean) ** 2 for x in xs) * sum((y - y_mean) ** 2 for y in ys)
    )
    return numerator / denominator


def stable_passenger(passenger):
    return (
        passenger.id,
        passenger.row,
        passenger.seat,
        passenger.family_id,
        passenger.tolerance_threshold,
        passenger.walking_speed_mps,
        passenger.bag_count,
        passenger.initial_stress_load,
        passenger.initial_frustration,
    )


class PopulationTests(unittest.TestCase):
    def setUp(self):
        self.scenario = normalize_scenario()
        self.calibration = load_behaviour_calibration()

    def population(self, strategy_id="random_front", seed=9):
        return generate_population(
            self.scenario,
            strategy_by_id(strategy_id),
            RNG(seed),
            self.calibration,
        )

    def test_population_has_180_individuals_and_unique_seats(self):
        passengers = self.population()
        self.assertEqual(len(passengers), 180)
        self.assertEqual(len({p.id for p in passengers}), 180)
        self.assertEqual(len({(p.row, p.seat) for p in passengers}), 180)

    def test_public_strategies_use_identical_manifest(self):
        manifest = generate_manifest(self.scenario, RNG(20260813), self.calibration)
        populations = [
            assign_strategy(
                copy.deepcopy(manifest),
                strategy_by_id(strategy_id),
                RNG(77),
            )
            for strategy_id in (
                "random_front",
                "back_to_front_zones",
                "strict_steffen",
            )
        ]
        expected = [stable_passenger(passenger) for passenger in populations[0]]
        for population in populations[1:]:
            self.assertEqual(
                [stable_passenger(passenger) for passenger in population], expected
            )

    def test_strict_steffen_is_exact_and_may_separate_companions(self):
        passengers = assign_strategy(
            copy.deepcopy(
                generate_manifest(self.scenario, RNG(44), self.calibration)
            ),
            strategy_by_id("strict_steffen"),
            RNG(91),
        )
        ordered = sorted(passengers, key=lambda passenger: passenger.boarding_rank)
        keys = [strict_steffen_key(passenger) for passenger in ordered]
        self.assertEqual(keys, sorted(keys))
        self.assertTrue(any(passenger.companion_override for passenger in passengers))

    def test_initial_frustration_is_derived_from_load_and_tolerance(self):
        for passenger in self.population():
            self.assertEqual(passenger.initial_frustration, passenger.frustration)
            self.assertAlmostEqual(
                passenger.frustration,
                frustration_from_load(passenger, self.calibration),
            )

    def test_shared_latent_factors_create_correlated_sensitivities(self):
        passengers = self.population(seed=221)
        value = correlation(
            [p.delay_sensitivity for p in passengers],
            [p.uncertainty_sensitivity for p in passengers],
        )
        self.assertGreater(value, 0.25)

    def test_traits_and_state_stay_in_documented_bounds(self):
        for passenger in self.population():
            self.assertGreaterEqual(passenger.tolerance_threshold, 0.16)
            self.assertLessEqual(passenger.tolerance_threshold, 0.92)
            self.assertGreaterEqual(passenger.walking_speed_mps, 0.45)
            self.assertLessEqual(passenger.walking_speed_mps, 1.15)
            self.assertIn(passenger.bag_count, (0, 1, 2))

    def test_families_remain_individual_and_boarding_contiguous(self):
        passengers = self.population("wilma_zones", seed=31)
        ordered = sorted(passengers, key=lambda p: (p.boarding_rank, p.id))
        positions = {p.id: index for index, p in enumerate(ordered)}
        family_ids = sorted({p.family_id for p in passengers if p.family_id})
        self.assertTrue(family_ids)
        for family_id in family_ids:
            members = [p for p in passengers if p.family_id == family_id]
            self.assertGreaterEqual(len(members), 2)
            self.assertEqual(len({p.id for p in members}), len(members))
            self.assertEqual(len({p.prep_cohort for p in members}), 1)
            member_positions = sorted(positions[p.id] for p in members)
            self.assertEqual(member_positions, list(range(member_positions[0], member_positions[0] + len(members))))

    def test_two_door_family_policy_preserves_seat_based_flow(self):
        passengers = self.population("split_half_two_door", seed=55)
        self.assertTrue(all(p.assigned_door == ("front" if p.row <= 15 else "rear") for p in passengers))
        self.assertEqual({p.assigned_door for p in passengers}, {"front", "rear"})

    def test_all_strategy_assignments_are_valid(self):
        for strategy_id in STRATEGIES:
            with self.subTest(strategy=strategy_id):
                passengers = self.population(strategy_id, seed=81)
                self.assertTrue(all(p.assigned_door in {"front", "rear"} for p in passengers))
                self.assertTrue(all(isinstance(p.prep_cohort, int) and p.prep_cohort >= 0 for p in passengers))


class FrustrationStateTests(unittest.TestCase):
    def setUp(self):
        scenario = normalize_scenario()
        self.calibration = load_behaviour_calibration()
        self.passengers = generate_population(
            scenario, strategy_by_id("random_front"), RNG(100), self.calibration
        )

    def test_tolerance_does_not_multiply_stress_growth(self):
        low, high = self.passengers[:2]
        low.stress_load = high.stress_load = 0.4
        low.tolerance_threshold = 0.2
        high.tolerance_threshold = 0.9
        evolve_passenger(low, 60, 0.2, 0.0, self.calibration, 0.75)
        evolve_passenger(high, 60, 0.2, 0.0, self.calibration, 0.75)
        self.assertAlmostEqual(low.stress_load, 0.6)
        self.assertAlmostEqual(high.stress_load, 0.6)
        self.assertNotEqual(low.frustration, high.frustration)

    def test_burden_peak_and_time_above_threshold_are_tracked(self):
        passenger = self.passengers[0]
        passenger.stress_load = 1.2
        passenger.tolerance_threshold = 0.2
        passenger.frustration = frustration_from_load(passenger, self.calibration)
        before_burden = passenger.frustration_burden
        evolve_passenger(passenger, 30, 0.0, 0.0, self.calibration, 0.75)
        self.assertGreater(passenger.frustration_burden, before_burden)
        self.assertEqual(passenger.time_above_threshold_seconds, 30)
        self.assertGreaterEqual(passenger.peak_frustration, passenger.frustration)


if __name__ == "__main__":
    unittest.main()
