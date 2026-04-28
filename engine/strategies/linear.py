"""
Linear equation solving strategy.

Solves equations of the form ax + b = c by:
1. Collecting like terms
2. Isolating the variable
3. Computing the solution
"""

from __future__ import annotations

from sympy import collect, expand, solve, simplify, Symbol

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class LinearStrategy(BaseStrategy):
    """
    Strategy for solving linear equations (degree 1).

    Generates steps showing:
    - Rearrangement to standard form
    - Collection of like terms
    - Isolation of the variable
    - Final solution
    """

    @property
    def name(self) -> str:
        return "Linear Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.LINEAR

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.LINEAR

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.LINEAR)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in linear equation")
            return result

        # Step: Standard form
        expr = expand(equation.lhs - equation.rhs)
        result.add_step(Step(
            title="Rearrange to Standard Form",
            description="Move all terms to the left side: LHS - RHS = 0",
            equation=fmt.standard_form(expr),
            category="rearrange",
        ))

        # Step: Collect like terms
        collected = collect(expr, var)
        if collected != expr:
            result.add_step(Step(
                title="Collect Like Terms",
                description=f"Group all terms containing {fmt.variable(var)} together",
                equation=fmt.standard_form(collected),
                category="simplify",
            ))

        # Step: Isolate variable
        # Express as ax + b = 0, then x = -b/a
        try:
            poly_coeff = expr.coeff(var, 1)
            const_term = expr.subs(var, 0)

            if poly_coeff != 0:
                result.add_step(Step(
                    title="Isolate the Variable",
                    description=f"Move constant terms to the right side and divide by the coefficient of {fmt.variable(var)}",
                    equation=f"{fmt.variable(var)} = {fmt.expr(-const_term / poly_coeff)}",
                    category="isolate",
                ))
        except Exception:
            logger.debug("Could not generate isolation step", exc_info=True)

        # Solve
        try:
            solutions = solve(equation.sympy_eq, var)
        except Exception as e:
            logger.error("SymPy solve failed: %s", e)
            result.mark_failed(f"Could not solve: {e}")
            return result

        # Format solutions
        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )
            result.add_solution(solution)

        if not result.solutions:
            result.add_step(Step(
                title="No Solution",
                description="This linear equation has no solution",
                category="result",
            ))
        elif len(result.solutions) == 1:
            result.add_step(Step(
                title="Solution",
                description=f"The linear equation has one solution",
                equation=fmt.assignment(var, result.solutions[0].exact_value),
                category="result",
                is_highlight=True,
            ))
        else:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title="Solutions",
                description=f"Found {len(result.solutions)} solution(s)",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))

        return result
