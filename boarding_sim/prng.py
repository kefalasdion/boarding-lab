"""Fixed seeded pseudo-random number generator used by the simulation."""

from __future__ import annotations

import math
from collections.abc import MutableSequence
from typing import TypeVar

T = TypeVar("T")
_MASK_32 = 0xFFFFFFFF


class RNG:
    """Mulberry32 with deterministic distribution helpers.

    The implementation mirrors the V2 JavaScript reference's 32-bit arithmetic.
    """

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        self.state = (seed & _MASK_32) or 1
        self._spare: float | None = None

    def next(self) -> float:
        self.state = (self.state + 0x6D2B79F5) & _MASK_32
        value = self.state
        value = ((value ^ (value >> 15)) * (value | 1)) & _MASK_32
        value ^= (value + (((value ^ (value >> 7)) * (value | 61)) & _MASK_32)) & _MASK_32
        return ((value ^ (value >> 14)) & _MASK_32) / 4294967296.0

    def normal(self, mean: float = 0.0, sd: float = 1.0) -> float:
        if self._spare is not None:
            z = self._spare
            self._spare = None
            return mean + sd * z
        u = max(1e-12, self.next())
        v = max(1e-12, self.next())
        magnitude = math.sqrt(-2.0 * math.log(u))
        z0 = magnitude * math.cos(2.0 * math.pi * v)
        self._spare = magnitude * math.sin(2.0 * math.pi * v)
        return mean + sd * z0

    def exponential(self, mean: float) -> float:
        return -math.log(max(1e-12, 1.0 - self.next())) * mean

    def weibull(self, shape: float, scale: float) -> float:
        return scale * (-math.log(max(1e-12, 1.0 - self.next()))) ** (1.0 / shape)

    def triangular(self, minimum: float, mode: float, maximum: float) -> float:
        u = self.next()
        c = (mode - minimum) / (maximum - minimum)
        if u < c:
            return minimum + math.sqrt(u * (maximum - minimum) * (mode - minimum))
        return maximum - math.sqrt((1.0 - u) * (maximum - minimum) * (maximum - mode))

    def integer(self, minimum: int, maximum_inclusive: int) -> int:
        return minimum + int(self.next() * (maximum_inclusive - minimum + 1))

    def boolean(self, probability: float = 0.5) -> bool:
        return self.next() < probability

    def shuffle(self, values: MutableSequence[T]) -> MutableSequence[T]:
        for index in range(len(values) - 1, 0, -1):
            swap_index = int(self.next() * (index + 1))
            values[index], values[swap_index] = values[swap_index], values[index]
        return values

    def fork(self, offset: int) -> "RNG":
        return RNG((self.state + 0x9E3779B9 + offset) & _MASK_32)
