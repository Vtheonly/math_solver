"""
Strategy factory for the equation solving engine.

Selects the appropriate solving strategy based on equation type.
Implements the Factory pattern to decouple the pipeline from
concrete strategy implementations.
"""

from __future__ import annotations

from typing import List, Optional, Type

from engine.models.equation import Equation, EquationType
from engine.strategies.base import BaseStrategy
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
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class StrategyFactory:
    """
    Factory that selects the appropriate solving strategy for a given equation.

    Strategy selection rules:
    1. SYSTEM → SystemStrategy
    2. ABSOLUTE_VALUE → AbsoluteValueStrategy
    3. TRIGONOMETRIC → TrigonometricStrategy
    4. LOGARITHMIC → LogarithmicStrategy
    5. EXPONENTIAL → ExponentialStrategy
    6. RATIONAL → RationalStrategy
    7. LINEAR → LinearStrategy
    8. QUADRATIC → QuadraticStrategy
    9. CUBIC → PolynomialStrategy (handles degree 3)
    10. POLYNOMIAL → PolynomialStrategy
    11. GENERAL / fallback → attempt exact, then NumericalStrategy

    The factory maintains a priority-ordered list of strategies.
    The first strategy that can_handle() the equation is selected.
    """

    # Type-to-strategy mapping
    TYPE_STRATEGY_MAP = {
        EquationType.SYSTEM: SystemStrategy,
        EquationType.ABSOLUTE_VALUE: AbsoluteValueStrategy,
        EquationType.TRIGONOMETRIC: TrigonometricStrategy,
        EquationType.LOGARITHMIC: LogarithmicStrategy,
        EquationType.EXPONENTIAL: ExponentialStrategy,
        EquationType.RATIONAL: RationalStrategy,
        EquationType.LINEAR: LinearStrategy,
        EquationType.QUADRATIC: QuadraticStrategy,
        EquationType.CUBIC: PolynomialStrategy,
        EquationType.POLYNOMIAL: PolynomialStrategy,
    }

    def __init__(self):
        self._strategies: List[BaseStrategy] = []
        self._register_strategies()

    def _register_strategies(self):
        """Register all available strategies in priority order."""
        strategy_classes = [
            SystemStrategy,
            AbsoluteValueStrategy,
            TrigonometricStrategy,
            LogarithmicStrategy,
            ExponentialStrategy,
            RationalStrategy,
            LinearStrategy,
            QuadraticStrategy,
            PolynomialStrategy,
            NumericalStrategy,
        ]

        for cls in strategy_classes:
            instance = cls()
            self._strategies.append(instance)
            logger.debug("Registered strategy: %s", instance.name)

    def get_strategy(self, equation: Equation) -> BaseStrategy:
        """
        Select the best strategy for a given equation.

        Uses the equation type mapping first, then falls back to
        checking can_handle() on each strategy in priority order.

        Args:
            equation: The equation to find a strategy for.

        Returns:
            The selected BaseStrategy instance.

        Raises:
            ValueError: If no strategy can handle the equation (should never happen
                       since NumericalStrategy is a universal fallback).
        """
        # Direct type lookup
        eq_type = equation.equation_type
        if eq_type in self.TYPE_STRATEGY_MAP:
            strategy_cls = self.TYPE_STRATEGY_MAP[eq_type]
            for strategy in self._strategies:
                if isinstance(strategy, strategy_cls):
                    logger.info(
                        "Selected strategy '%s' for type %s",
                        strategy.name,
                        eq_type.value,
                    )
                    return strategy

        # Fallback: check can_handle()
        for strategy in self._strategies:
            if strategy.can_handle(equation):
                logger.info(
                    "Selected strategy '%s' via can_handle() for type %s",
                    strategy.name,
                    eq_type.value,
                )
                return strategy

        # Last resort: numerical
        logger.warning("No strategy matched, falling back to NumericalStrategy")
        for strategy in self._strategies:
            if isinstance(strategy, NumericalStrategy):
                return strategy

        raise ValueError(f"No strategy available for equation type: {eq_type}")

    def get_all_strategies(self) -> List[BaseStrategy]:
        """Return all registered strategies."""
        return list(self._strategies)
