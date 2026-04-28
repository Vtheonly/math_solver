"""
Trigonometric equation solving strategy.

Solves equations containing trigonometric functions (sin, cos, tan, etc.)
by applying identities and inverse functions, with step-by-step
explanations of the trigonometric transformations.
"""

from __future__ import annotations

from sympy import (
    simplify, solve, solveset, S, Symbol, pi, sin, cos, tan,
    expand_trig, trigsimp, asin, acos, atan,
)

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class TrigonometricStrategy(BaseStrategy):
    """
    Strategy for solving trigonometric equations.

    Generates steps showing:
    - Simplification using trig identities
    - Isolation of the trig function
    - Application of inverse trig functions
    - General solution with periodicity notes
    """

    @property
    def name(self) -> str:
        return "Trigonometric Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.TRIGONOMETRIC

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.TRIGONOMETRIC

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.TRIGONOMETRIC)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in trigonometric equation")
            return result

        # Standard form
        expr = equation.lhs - equation.rhs
        result.add_step(Step(
            title="Original Equation",
            description="Trigonometric equation to solve",
            equation=fmt.equation(equation.lhs, equation.rhs),
            category="identify",
        ))

        # Try to simplify using trig identities
        simplified = trigsimp(expr)
        if simplified != expr:
            result.add_step(Step(
                title="Simplify Using Trigonometric Identities",
                description="Apply trigonometric simplification rules",
                equation=fmt.equation(simplified, S.Zero),
                category="simplify",
            ))

        # Try expanding trig expressions
        expanded = expand_trig(expr)
        if expanded != expr and expanded != simplified:
            result.add_step(Step(
                title="Expand Trigonometric Expression",
                description="Expand using angle addition and double-angle formulas",
                equation=fmt.equation(expanded, S.Zero),
                category="simplify",
            ))

        # Identify the trig function and try to isolate it
        isolation_step = self._try_isolate_trig(equation, var, fmt)
        if isolation_step:
            result.add_step(isolation_step)

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
            logger.error("Trig solve failed: %s", e)
            result.mark_failed(f"Could not solve trigonometric equation: {e}")
            return result

        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )
            result.add_solution(solution)

        # Note about periodicity
        if result.solutions:
            result.add_step(Step(
                title="Note on Periodicity",
                description="Trigonometric equations have infinitely many solutions due to periodicity. "
                           "The solutions shown are the principal values. Add 2πn (for sin/cos) or πn (for tan) "
                           "for the general solution, where n is any integer.",
                category="note",
            ))

            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Principal Solutions ({len(result.solutions)})",
                description="Principal values of the solutions",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Solution",
                description="No solutions found for this trigonometric equation",
                category="result",
            ))

        return result

    def _try_isolate_trig(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> Step | None:
        """
        Try to identify and isolate the trigonometric function.

        Looks for patterns like sin(x) = value, cos(x) = value, etc.
        and generates an isolation step if found.
        """
        from sympy import Function

        expr = equation.lhs - equation.rhs

        # Check for sin(var), cos(var), tan(var) patterns
        for trig_func, name, inverse_name in [
            (sin, "sin", "arcsin"),
            (cos, "cos", "arccos"),
            (tan, "tan", "arctan"),
        ]:
            # Check if the expression contains this trig function applied to var
            trig_terms = expr.find(trig_func(var))
            if trig_terms:
                # Try to isolate
                try:
                    # Solve for trig(var) = value
                    trig_var = trig_func(var)
                    solutions_for_trig = solve(expr, trig_var)
                    if solutions_for_trig:
                        val = solutions_for_trig[0]
                        return Step(
                            title=f"Isolate {name}({fmt.variable(var)})",
                            description=f"Apply {inverse_name} to both sides to solve for {fmt.variable(var)}",
                            equation=f"{name}({fmt.variable(var)}) = {fmt.expr(val)}",
                            category="isolate",
                        )
                except Exception:
                    pass

        return None
