"""
Solving strategies for the equation solving engine.

Implements the Strategy pattern — each equation type has its own
strategy that knows how to solve it and generate detailed steps.
"""

from engine.strategies.base import BaseStrategy, StrategyResult
from engine.strategies.linear import LinearStrategy
from engine.strategies.quadratic import QuadraticStrategy
from engine.strategies.polynomial import PolynomialStrategy
from engine.strategies.trigonometric import TrigonometricStrategy
from engine.strategies.logarithmic import LogarithmicStrategy
from engine.strategies.exponential import ExponentialStrategy
from engine.strategies.rational import RationalStrategy
from engine.strategies.absolute_value import AbsoluteValueStrategy
from engine.strategies.system import SystemStrategy
from engine.strategies.numerical import NumericalStrategy
from engine.strategies.factory import StrategyFactory

__all__ = [
    "BaseStrategy",
    "StrategyResult",
    "LinearStrategy",
    "QuadraticStrategy",
    "PolynomialStrategy",
    "TrigonometricStrategy",
    "LogarithmicStrategy",
    "ExponentialStrategy",
    "RationalStrategy",
    "AbsoluteValueStrategy",
    "SystemStrategy",
    "NumericalStrategy",
    "StrategyFactory",
]
