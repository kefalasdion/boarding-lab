"""Boarding policy definitions, independent of physical boarding engines."""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from .models import Passenger
from .prng import RNG


def _seat_group(seat: str) -> int:
    return 0 if seat in {"A", "F"} else 1 if seat in {"B", "E"} else 2


def _side(seat: str) -> int:
    return 0 if seat in {"A", "B", "C"} else 1


def _zone_back_to_front(row: int) -> int:
    return (30 - row) // 5


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    access_recommended: str
    prep_cohorts: int
    cohort: Callable[[Passenger], int]
    rank: Callable[[Passenger, float], float]
    door: Callable[[Passenger], str]
    preserve_seat_door: bool = False


STRATEGIES: dict[str, Strategy] = {
    "random_front": Strategy(
        "random_front", "Random · front door", "bridge", 1,
        lambda _p: 0, lambda _p, random_key: random_key, lambda _p: "front",
    ),
    "split_half_two_door": Strategy(
        "split_half_two_door", "Rows 1–15 front · 16–30 rear", "bus", 2,
        lambda p: 0 if p.row <= 15 else 1,
        lambda p, random_key: (0 if p.row <= 15 else 1) * 1000 + random_key,
        lambda p: "front" if p.row <= 15 else "rear", True,
    ),
    "wilma": Strategy(
        "wilma", "A/F → B/E → C/D", "bridge", 3,
        lambda p: _seat_group(p.seat),
        lambda p, random_key: _seat_group(p.seat) * 1000 + random_key,
        lambda _p: "front",
    ),
    "back_to_front_zones": Strategy(
        "back_to_front_zones", "Back-to-front · 5-row zones", "bridge", 6,
        lambda p: _zone_back_to_front(p.row),
        lambda p, random_key: _zone_back_to_front(p.row) * 1000 + random_key,
        lambda _p: "front",
    ),
    "wilma_zones": Strategy(
        "wilma_zones", "Outside-in + back-to-front zones", "bridge", 18,
        lambda p: _seat_group(p.seat) * 6 + _zone_back_to_front(p.row),
        lambda p, random_key: (_seat_group(p.seat) * 6 + _zone_back_to_front(p.row)) * 1000 + random_key,
        lambda _p: "front",
    ),
    "steffen_companion": Strategy(
        "steffen_companion", "Steffen-style · companion compatible", "bridge", 12,
        lambda p: _seat_group(p.seat) * 4 + _side(p.seat) * 2 + (p.row % 2),
        lambda p, _random_key: (_seat_group(p.seat) * 4 + _side(p.seat) * 2 + (p.row % 2)) * 1000 + (31 - p.row),
        lambda _p: "front",
    ),
    "split_wilma_two_door": Strategy(
        "split_wilma_two_door", "Split doors + A/F → B/E → C/D", "bus", 6,
        lambda p: (0 if p.row <= 15 else 1) * 3 + _seat_group(p.seat),
        lambda p, random_key: ((0 if p.row <= 15 else 1) * 3 + _seat_group(p.seat)) * 1000 + random_key,
        lambda p: "front" if p.row <= 15 else "rear", True,
    ),
}


def strategy_by_id(strategy_id: str) -> Strategy:
    return STRATEGIES[strategy_id]


def strategy_complexity(strategy: Strategy) -> float:
    if strategy.prep_cohorts <= 1:
        return 0.0
    return math.log2(strategy.prep_cohorts) / math.log2(18)


def strategy_catalog() -> list[dict[str, object]]:
    return [
        {
            "id": strategy.id,
            "name": strategy.name,
            "recommendedAccess": strategy.access_recommended,
            "preparationCohorts": strategy.prep_cohorts,
        }
        for strategy in STRATEGIES.values()
    ]


def apply_companion_compatibility(
    passengers: list[Passenger], strategy: Strategy, rng: RNG
) -> list[Passenger]:
    families: dict[int, list[Passenger]] = {}
    for passenger in passengers:
        passenger.raw_cohort = strategy.cohort(passenger)
        passenger.random_key = rng.next()
        passenger.raw_rank = strategy.rank(passenger, passenger.random_key)
        passenger.assigned_door = strategy.door(passenger)
        passenger.prep_cohort = passenger.raw_cohort
        if passenger.family_id:
            families.setdefault(passenger.family_id, []).append(passenger)

    for members in families.values():
        cohort = min(member.raw_cohort for member in members)
        front_count = sum(member.assigned_door == "front" for member in members)
        rear_count = len(members) - front_count
        common_door = members[0].assigned_door if front_count == rear_count else ("front" if front_count > rear_count else "rear")
        for member in members:
            original_door = member.assigned_door
            member.prep_cohort = cohort
            if not strategy.preserve_seat_door:
                member.assigned_door = common_door
            member.companion_override = member.raw_cohort != cohort or member.assigned_door != original_door

    groups: list[list[Passenger]] = []
    grouped_ids: set[int] = set()
    for family_id in sorted(families):
        members = sorted(families[family_id], key=lambda passenger: (passenger.raw_rank, passenger.id))
        groups.append(members)
        grouped_ids.update(member.id for member in members)
    groups.extend([[passenger] for passenger in passengers if passenger.id not in grouped_ids])
    groups.sort(key=lambda group: (min(member.raw_rank for member in group), min(member.id for member in group)))
    next_rank = 0
    for group in groups:
        for member in group:
            member.boarding_rank = float(next_rank)
            next_rank += 1
    return passengers
