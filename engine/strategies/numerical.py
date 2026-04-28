"""
Numerical equation solving strategy.

Fallback strategy when exact (symbolic) solutions cannot be found.
Uses SymPy's nsolve with multiple starting points to find
numerical approximations.
"""

from __future__ import annotations

from sympy import simplify, nsolve, Symbol

from config import (
    NUMERICAL_STARTING_POINTS,
    NUMERICAL_TOLERANCE,
    DUPLICATE_THRESHOLD,
    NUMERICAL_MAX_SOLUTIONS,
)
from engine.models.equation import Equation
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class NumericalStrategy(BaseStrategy):
    """
    Fallback numerical solver using Newton's method (nsolve).

    Tries multiple starting points to find distinct solutions.
    Used when exact symbolic solutions are unavailable.
    """

    @property
    def name(self) -> str:
        return "Numerical Solver (Fallback)"

    @property
    def handled_type(self) -> EquationType:
        from engine.models.equation import EquationType
        return EquationType.GENERAL

    def can_handle(self, equation: Equation) -> bool:
        return True  # Can always attempt numerical solving

    def solve(self, equation: Equation) -> StrategyResult:
        from engine.models.equation import EquationType
        result = StrategyResult(
            equation_type=equation.equation_type or EquationType.GENERAL,
            is_numerical=True,
        )
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found for numerical solving")
            return result

        result.add_step(Step(
            title="Numerical Method",
            description="Exact symbolic solution not available. Using Newton's method (numerical approximation) with multiple starting points.",
            category="numerical",
        ))

        expr = equation.lhs - equation.rhs
        found_decimal_values = []
        solution_count = 0

        for x0 in NUMERICAL_STARTING_POINTS:
            if solution_count >= NUMERICAL_MAX_SOLUTIONS:
                break

            try:
                sol = nsolve(expr, var, x0, tol=NUMERICAL_TOLERANCE, maxsteps=100)
                sol_float = float(sol)

                # Check for duplicates
                is_duplicate = any(
                    abs(sol_float - existing) < DUPLICATE_THRESHOLD
                    for existing in found_decimal_values
                )

                if not is_duplicate:
                    found_decimal_values.append(sol_float)
                    solution = Solution(
                        variable_name=str(var),
                        exact_value=sol,
                        is_numerical=True,
                    )
                    result.add_solution(solution)
                    solution_count += 1
                    logger.debug("Numerical solution found at x0=%s: %s", x0, sol_float)

            except Exception:
                continue

        if result.solutions:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Numerical Solution{'s' if len(result.solutions) > 1 else ''}",
                description=f"Found {len(result.solutions)} solution(s) numerically. These are approximations.",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Solution Found",
                description="Numerical method could not find any solutions from the starting points tried",
                category="result",
            ))

        return result
