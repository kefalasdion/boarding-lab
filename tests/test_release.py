import unittest

from boarding_sim.population import generate_population
from boarding_sim.prng import RNG
from boarding_sim.release import (
    release_events,
    release_schedule,
    strategy_release_mode,
)
from boarding_sim.strategies import strategy_by_id
from boarding_sim.validation import load_behaviour_calibration, normalize_scenario


def _population(strategy_id):
    scenario = normalize_scenario()
    calibration = load_behaviour_calibration()
    strategy = strategy_by_id(strategy_id)
    passengers = generate_population(scenario, strategy, RNG(4242), calibration)
    return passengers, strategy, calibration


class ReleaseModeTests(unittest.TestCase):
    def test_single_cohort_strategies_use_one_general_call(self):
        self.assertEqual(strategy_release_mode(strategy_by_id("random_front")), "general")

    def test_multi_cohort_strategies_default_to_zone_calls(self):
        self.assertEqual(
            strategy_release_mode(strategy_by_id("back_to_front_zones")), "cohort"
        )
        self.assertEqual(strategy_release_mode(strategy_by_id("wilma")), "cohort")

    def test_strict_steffen_is_called_passenger_by_passenger(self):
        self.assertEqual(
            strategy_release_mode(strategy_by_id("strict_steffen")), "individual"
        )


class ReleaseScheduleTests(unittest.TestCase):
    def test_random_releases_every_passenger_at_zero(self):
        passengers, strategy, calibration = _population("random_front")
        schedule = release_schedule(passengers, strategy, calibration)
        self.assertEqual(set(schedule.values()), {0.0})
        self.assertEqual(len(schedule), len(passengers))

    def test_back_to_front_releases_zones_twenty_seconds_apart_rear_first(self):
        passengers, strategy, calibration = _population("back_to_front_zones")
        schedule = release_schedule(passengers, strategy, calibration)
        by_cohort = {}
        for passenger in passengers:
            by_cohort.setdefault(passenger.prep_cohort, set()).add(schedule[passenger.id])
        for cohort, times in by_cohort.items():
            self.assertEqual(len(times), 1, f"cohort {cohort} must share one release time")
        ordered = [by_cohort[cohort].pop() for cohort in sorted(by_cohort)]
        self.assertEqual(ordered, [0.0, 20.0, 40.0, 60.0, 80.0, 100.0])

    def test_back_to_front_calls_the_rear_of_the_cabin_first(self):
        """Solo passengers follow their own zone; the rear five rows go first.

        Family members can be pulled forward into an earlier cohort by the
        existing companion rule, so this checks passengers travelling alone.
        """
        passengers, strategy, calibration = _population("back_to_front_zones")
        schedule = release_schedule(passengers, strategy, calibration)
        solo = [passenger for passenger in passengers if not passenger.family_id]
        self.assertTrue(solo, "the population must contain passengers travelling alone")
        for passenger in solo:
            expected = ((30 - passenger.row) // 5) * 20.0
            self.assertEqual(schedule[passenger.id], expected)
        first_called = {passenger.row for passenger in solo if schedule[passenger.id] == 0.0}
        self.assertTrue(min(first_called) >= 26, "the first zone called must be the rear")

    def test_strict_steffen_releases_one_passenger_every_four_seconds(self):
        passengers, strategy, calibration = _population("strict_steffen")
        schedule = release_schedule(passengers, strategy, calibration)
        times = sorted(schedule.values())
        self.assertEqual(len(set(times)), len(passengers))
        self.assertEqual(times[0], 0.0)
        self.assertEqual(times[-1], 716.0)
        self.assertEqual(times, [index * 4.0 for index in range(len(passengers))])

    def test_release_times_follow_exact_boarding_order(self):
        passengers, strategy, calibration = _population("strict_steffen")
        schedule = release_schedule(passengers, strategy, calibration)
        for passenger in passengers:
            self.assertEqual(schedule[passenger.id], passenger.boarding_rank * 4.0)


class ReleaseEventTests(unittest.TestCase):
    def test_random_emits_exactly_one_general_call(self):
        passengers, strategy, calibration = _population("random_front")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].type, "preparation_general_call")
        self.assertEqual(events[0].time_seconds, 0.0)
        self.assertIsNone(events[0].passenger_id)
        self.assertEqual(events[0].details["passenger_count"], len(passengers))

    def test_back_to_front_emits_one_call_per_zone(self):
        passengers, strategy, calibration = _population("back_to_front_zones")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual([event.type for event in events], ["preparation_zone_called"] * 6)
        self.assertEqual(
            [event.time_seconds for event in events], [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]
        )
        self.assertEqual(
            sum(event.details["passenger_count"] for event in events), len(passengers)
        )
        self.assertTrue(all(event.passenger_id is None for event in events))

    def test_strict_steffen_emits_one_call_per_passenger_in_order(self):
        passengers, strategy, calibration = _population("strict_steffen")
        events = release_events(
            passengers, strategy, release_schedule(passengers, strategy, calibration)
        )
        self.assertEqual(len(events), len(passengers))
        self.assertTrue(
            all(event.type == "preparation_passenger_called" for event in events)
        )
        times = [event.time_seconds for event in events]
        self.assertEqual(times, sorted(times))
        self.assertEqual(times[-1], 716.0)
        self.assertTrue(all(event.passenger_id is not None for event in events))


if __name__ == "__main__":
    unittest.main()
