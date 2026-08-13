"""Deterministic passenger boarding simulation package."""

from .engine import run_flight
from .monte_carlo import run_monte_carlo

__all__ = ["run_flight", "run_monte_carlo"]
__version__ = "1.0.0"
