"""Deterministic passenger boarding simulation package."""

from .comparison import run_comparison, run_comparison_monte_carlo
from .engine import run_flight
from .monte_carlo import run_monte_carlo

__all__ = [
    "run_comparison",
    "run_comparison_monte_carlo",
    "run_flight",
    "run_monte_carlo",
]
__version__ = "1.1.0"
