"""
Fraction handler for the equation solving engine.

Standalone module for clearing fractions from equations by
finding the LCD and multiplying both sides. Can be used as
a pipeline preprocessor or by individual strategies.
"""

from __future__ import annotations

from typing import List, Tuple

from sympy import (
    simplify, expand, lcm, fraction, Add, Eq, Symbol, cancel, factor
)

from engine.models.equation import Equation
from engine.models.step import Step
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class FractionHandler:
    """
    Handles fraction clearing in equations.

    Finds the least common denominator (LCD) of all fractional
    terms and multiplies both sides by it, producing a simpler
    equation without denominators.

    This is used as a preprocessing step in the pipeline and
    can also be called directly by strategies.
    """

    @staticmethod
    def has_fractions(equation: Equation) -> bool:
        """Check if an equation contains fractional expressions."""
        for side in (equation.lhs, equation.rhs):
            for term in Add.make_args(side):
                _, denom = fraction(term)
                if denom != 1:
                    return True
        return False

    @staticmethod
    def clear_fractions(
        equation: Equation,
    ) -> Tuple[Eq, List[Step]]:
        """
        Clear all fractions from an equation.

        Finds the LCD of every denominator in the equation,
        then multiplies both sides by it and simplifies.

        Args:
            equation: The Equation object to clear fractions from.

        Returns:
            Tuple of (cleared_SymPy_Eq, list_of_Steps).
            If no fractions are found, returns the original equation
            and an empty step list.
        """
        fmt = LatexFormatter()
        steps = []

        if not FractionHandler.has_fractions(equation):
            logger.debug("No fractions to clear in equation")
            return equation.sympy_eq, steps

        # Collect all denominators
        denoms = FractionHandler._collect_denominators(equation)
        logger.debug("Found %d denominators: %s", len(denoms), denoms)

        if not denoms:
            return equation.sympy_eq, steps

        # Compute LCD
        lcd_val = FractionHandler._compute_lcd(denoms)
        logger.debug("LCD = %s", lcd_val)

        if lcd_val == 1:
            return equation.sympy_eq, steps

        steps.append(Step(
            title="Find the LCD (Least Common Denominator)",
            description=f"Identify the least common denominator of all fractions",
            equation=f"\\text{{LCD}} = {fmt.expr(lcd_val, simplify_expr=False)}",
            category="fraction",
        ))

        # Step: Multiply both sides
        steps.append(Step(
            title="Multiply Both Sides by LCD",
            description="Multiply every term by the LCD to eliminate all fractions",
            equation=fmt.lcd_multiply(equation.lhs, equation.rhs, lcd_val),
            category="fraction",
        ))

        # Compute cleared equation
        new_lhs = expand(cancel(equation.lhs * lcd_val))
        new_rhs = expand(cancel(equation.rhs * lcd_val))
        cleared_eq = Eq(new_lhs, new_rhs)

        # Step: Show result
        steps.append(Step(
            title="After Clearing Fractions",
            description="All fractions have been eliminated",
            equation=fmt.equation(new_lhs, new_rhs),
            category="fraction",
        ))

        return cleared_eq, steps

    @staticmethod
    def clear_system_fractions(
        equations: List[Equation],
    ) -> Tuple[List[Eq], List[Step]]:
        """
        Clear fractions from each equation in a system.

        Args:
            equations: List of Equation objects.

        Returns:
            Tuple of (list_of_cleared_Eq, list_of_Steps).
        """
        all_steps = []
        cleared_eqs = []

        for i, eq in enumerate(equations, 1):
            if FractionHandler.has_fractions(eq):
                cleared, steps = FractionHandler.clear_fractions(eq)
                for step in steps:
                    step.title = f"Eq {i}: {step.title}"
                all_steps.extend(steps)
                cleared_eqs.append(cleared)
            else:
                cleared_eqs.append(eq.sympy_eq)

        return cleared_eqs, all_steps

    @staticmethod
    def _collect_denominators(equation: Equation) -> List[object]:
        """Collect all unique non-trivial denominators from an equation."""
        denoms = []
        for side in (equation.lhs, equation.rhs):
            for term in Add.make_args(side):
                _, denom = fraction(term)
                if denom != 1 and denom not in denoms:
                    denoms.append(denom)
        return denoms

    @staticmethod
    def _compute_lcd(denominators: List[object]) -> object:
        """Compute the least common denominator from a list of denominators."""
        if not denominators:
            return 1

        lcd_val = denominators[0]
        for d in denominators[1:]:
            try:
                lcd_val = lcm(lcd_val, d)
            except Exception:
                # Fallback: multiply denominators
                lcd_val = lcd_val * d
        return factor(simplify(lcd_val))
