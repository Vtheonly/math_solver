"""
Exponential equation solving strategy.

Solves equations containing exponential functions by:
1. Recognizing same-base patterns (a^x = a^c → x = c)
2. Taking logarithms of both sides
3. Applying exponential/logarithmic identities
"""

from __future__ import annotations

from sympy import (
    simplify, solve, solveset, S, Symbol, log, exp,
    Eq, expand, Pow,
)

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class ExponentialStrategy(BaseStrategy):
    """
    Strategy for solving exponential equations.

    Generates steps showing:
    - Same-base recognition
    - Logarithm application
    - Conversion and solution
    """

    @property
    def name(self) -> str:
        return "Exponential Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.EXPONENTIAL

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.EXPONENTIAL

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.EXPONENTIAL)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in exponential equation")
            return result

        # Original equation
        result.add_step(Step(
            title="Original Equation",
            description="Exponential equation to solve",
            equation=fmt.equation(equation.lhs, equation.rhs),
            category="identify",
        ))

        # Try same-base approach
        same_base_step = self._try_same_base(equation, var, fmt)
        if same_base_step:
            result.add_step(same_base_step)

        # Apply logarithms
        log_step = self._apply_logarithm(equation, var, fmt)
        if log_step:
            result.add_step(log_step)

        # Solve
        try:
            solutions = solve(equation.sympy_eq, var)

            if not solutions:
                sol_set = solveset(equation.sympy_eq, var, domain=S.Reals)
                if sol_set != S.EmptySet:
                    try:
                        solutions = list(sol_set)
                    except Exception:
                        solutions = []
        except Exception as e:
            logger.error("Exponential solve failed: %s", e)
            result.mark_failed(f"Could not solve exponential equation: {e}")
            return result

        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )
            result.add_solution(solution)

        # Solution step
        if result.solutions:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Solution{'s' if len(result.solutions) > 1 else ''}",
                description="Solution(s) to the exponential equation",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Solution",
                description="No real solutions found for this exponential equation",
                category="result",
            ))

        return result

    def _try_same_base(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> Step | None:
        """
        Try to recognize the same-base pattern.

        If both sides are powers of the same base, we can equate the exponents:
        a^f(x) = a^g(x) → f(x) = g(x)
        """
        lhs, rhs = equation.lhs, equation.rhs

        # Check if both sides are Pow with the same base
        if lhs.is_Pow and rhs.is_Pow:
            if lhs.base == rhs.base and lhs.base != var:
                return Step(
                    title="Same-Base Property",
                    description=f"If a^m = a^n, then m = n (for a > 0, a ≠ 1). "
                               f"Both sides have the same base {fmt.expr(lhs.base)}.",
                    equation=f"{fmt.expr(lhs.exp)} = {fmt.expr(rhs.exp)}",
                    category="transform",
                )

        # Check if one side is a constant that is a power of the base on the other side
        if lhs.is_Pow and rhs.is_number:
            try:
                base = lhs.base
                # Try to express rhs as base^something
                from sympy import ln
                log_result = simplify(log(rhs) / log(base))
                if log_result.is_rational:
                    return Step(
                        title="Express with Same Base",
                        description=f"Rewrite {fmt.expr(rhs)} as {fmt.expr(base)}^{{{fmt.expr(log_result)}}}",
                        equation=f"{fmt.expr(lhs)} = {fmt.expr(base)}^{{{fmt.expr(log_result)}}}",
                        category="transform",
                    )
            except Exception:
                pass

        if rhs.is_Pow and lhs.is_number:
            try:
                base = rhs.base
                from sympy import ln
                log_result = simplify(log(lhs) / log(base))
                if log_result.is_rational:
                    return Step(
                        title="Express with Same Base",
                        description=f"Rewrite {fmt.expr(lhs)} as {fmt.expr(base)}^{{{fmt.expr(log_result)}}}",
                        category="transform",
                    )
            except Exception:
                pass

        return None

    def _apply_logarithm(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> Step | None:
        """
        Show the step of applying logarithm to both sides.

        This is the general approach for exponential equations.
        """
        from sympy import Pow

        lhs, rhs = equation.lhs, equation.rhs

        # If one side has exp or Pow with variable in exponent
        has_exp_var = False
        for side in (lhs, rhs):
            for sub in side.find(Pow):
                if var in sub.exp.free_symbols:
                    has_exp_var = True
                    break
            if side.has(exp):
                for sub in side.find(exp):
                    if var in sub.args[0].free_symbols:
                        has_exp_var = True
                        break

        if has_exp_var:
            return Step(
                title="Take Logarithm of Both Sides",
                description="Apply ln (natural log) to both sides to bring the variable out of the exponent. "
                           "This uses: ln(a^b) = b·ln(a)",
                category="transform",
            )

        return None
