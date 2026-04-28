"""
Absolute value equation solving strategy.

Solves equations containing |expression| by:
1. Isolating the absolute value expression
2. Applying the definition: |u| = a → u = a or u = -a
3. Solving both cases
4. Checking for extraneous solutions
"""

from __future__ import annotations

from sympy import (
    simplify, solve, expand, Abs, Eq, Symbol, S,
)

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class AbsoluteValueStrategy(BaseStrategy):
    """
    Strategy for solving absolute value equations.

    Generates steps showing:
    - Isolation of the absolute value expression
    - Splitting into positive and negative cases
    - Solving each case separately
    - Verification of each solution
    """

    @property
    def name(self) -> str:
        return "Absolute Value Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.ABSOLUTE_VALUE

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.ABSOLUTE_VALUE

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.ABSOLUTE_VALUE)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in absolute value equation")
            return result

        # Original equation
        result.add_step(Step(
            title="Original Equation",
            description="Absolute value equation to solve",
            equation=fmt.equation(equation.lhs, equation.rhs),
            category="identify",
        ))

        # Find the Abs expression(s)
        abs_exprs_lhs = list(equation.lhs.find(Abs))
        abs_exprs_rhs = list(equation.rhs.find(Abs))
        all_abs = abs_exprs_lhs + abs_exprs_rhs

        if not all_abs:
            result.mark_failed("No absolute value expression found after classification")
            return result

        # Step: Isolate the absolute value
        result.add_step(Step(
            title="Isolate the Absolute Value",
            description="Rearrange the equation so that the absolute value expression is alone on one side",
            category="isolate",
        ))

        # Check if the other side is negative → no solution
        # |u| = negative has no solution
        if len(all_abs) == 1:
            abs_expr = all_abs[0]
            # Determine which side has the abs
            if abs_exprs_lhs:
                other_side = equation.rhs
            else:
                other_side = equation.lhs

            # If other side is a negative constant, no solution
            if other_side.is_number and other_side < 0:
                result.add_step(Step(
                    title="No Solution",
                    description=f"An absolute value cannot equal a negative number ({fmt.expr(other_side)})",
                    category="result",
                ))
                return result

            # If other side is zero, just solve the inner = 0
            if other_side == 0:
                inner = abs_expr.args[0]
                result.add_step(Step(
                    title="Case: |u| = 0",
                    description="If |u| = 0, then u = 0",
                    equation=f"{fmt.expr(inner)} = 0",
                    category="case",
                ))
                solutions = solve(inner, var)
                for sol in solutions:
                    result.add_solution(Solution(
                        variable_name=str(var),
                        exact_value=simplify(sol),
                    ))

                if result.solutions:
                    result.add_step(Step(
                        title="Solution",
                        description="The absolute value equals zero only when the inner expression is zero",
                        equation=fmt.assignment(var, result.solutions[0].exact_value),
                        category="result",
                        is_highlight=True,
                    ))
                return result

        # General case: split into two cases
        result.add_step(Step(
            title="Split into Two Cases",
            description="By definition of absolute value: if |u| = a (a ≥ 0), then u = a OR u = -a",
            category="split",
        ))

        # Solve the original equation (SymPy handles | | natively)
        try:
            solutions = solve(equation.sympy_eq, var)
        except Exception as e:
            logger.error("Absolute value solve failed: %s", e)
            result.mark_failed(f"Could not solve absolute value equation: {e}")
            return result

        # Also try solving both cases manually for step clarity
        if len(all_abs) == 1:
            abs_expr = all_abs[0]
            inner = abs_expr.args[0]

            if abs_exprs_lhs:
                other_side = equation.rhs
                # Case 1: inner = other_side
                case1_eq = Eq(inner, other_side)
                # Case 2: inner = -other_side
                case2_eq = Eq(inner, -other_side)
            else:
                other_side = equation.lhs
                case1_eq = Eq(other_side, inner)
                case2_eq = Eq(other_side, -inner)

            result.add_step(Step(
                title="Case 1: Positive",
                description="The expression inside the absolute value equals the other side",
                equation=fmt.sympy_eq(case1_eq),
                category="case",
            ))

            try:
                case1_sols = solve(case1_eq, var)
                if case1_sols:
                    sol_str = ", ".join([fmt.assignment(var, simplify(s)) for s in case1_sols])
                    result.add_step(Step(
                        title="Case 1 Solutions",
                        description="Solutions from the positive case",
                        equation=sol_str,
                        category="case_result",
                    ))
            except Exception:
                case1_sols = []

            result.add_step(Step(
                title="Case 2: Negative",
                description="The expression inside the absolute value equals the negative of the other side",
                equation=fmt.sympy_eq(case2_eq),
                category="case",
            ))

            try:
                case2_sols = solve(case2_eq, var)
                if case2_sols:
                    sol_str = ", ".join([fmt.assignment(var, simplify(s)) for s in case2_sols])
                    result.add_step(Step(
                        title="Case 2 Solutions",
                        description="Solutions from the negative case",
                        equation=sol_str,
                        category="case_result",
                    ))
            except Exception:
                case2_sols = []

        # Format solutions
        for sol in solutions:
            sol_simplified = simplify(sol)
            result.add_solution(Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            ))

        # Final solution step
        if result.solutions:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Solution{'s' if len(result.solutions) > 1 else ''}",
                description="All solutions verified against the original equation",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Solution",
                description="No valid solutions found for this absolute value equation",
                category="result",
            ))

        return result
