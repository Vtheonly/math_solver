"""
Logarithmic equation solving strategy.

Solves equations containing logarithmic functions by:
1. Applying logarithm properties (product, quotient, power rules)
2. Combining logarithmic terms
3. Converting to exponential form
4. Solving and checking domain restrictions
"""

from __future__ import annotations

from sympy import (
    simplify, solve, solveset, S, Symbol, log, exp,
    expand_log, expand, Eq,
)

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class LogarithmicStrategy(BaseStrategy):
    """
    Strategy for solving logarithmic equations.

    Generates steps showing:
    - Logarithm expansion/combination
    - Conversion to exponential form
    - Domain restrictions (arguments must be positive)
    """

    @property
    def name(self) -> str:
        return "Logarithmic Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.LOGARITHMIC

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.LOGARITHMIC

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.LOGARITHMIC)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in logarithmic equation")
            return result

        # Original equation
        result.add_step(Step(
            title="Original Equation",
            description="Logarithmic equation to solve",
            equation=fmt.equation(equation.lhs, equation.rhs),
            category="identify",
        ))

        # Step: Domain restriction
        result.add_step(Step(
            title="Domain Restriction",
            description="All logarithm arguments must be positive. "
                       "Solutions that make any argument ≤ 0 are extraneous and must be rejected.",
            category="domain",
        ))

        # Try expanding logarithms
        expr = equation.lhs - equation.rhs
        expanded = expand_log(expr, force=True)
        if expanded != expr:
            result.add_step(Step(
                title="Expand Logarithms",
                description="Apply logarithm expansion rules: log(ab) = log(a) + log(b), log(a/b) = log(a) - log(b)",
                equation=fmt.equation(expanded, S.Zero),
                category="simplify",
            ))

        # Try combining logarithms on each side
        combined_lhs = self._combine_logs(equation.lhs, var, fmt, result, side="left")
        combined_rhs = self._combine_logs(equation.rhs, var, fmt, result, side="right")

        # If we have log(something) = constant or log(something) = log(something_else)
        conversion_step = self._try_exponential_conversion(
            equation, var, fmt
        )
        if conversion_step:
            result.add_step(conversion_step)

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
            logger.error("Logarithmic solve failed: %s", e)
            result.mark_failed(f"Could not solve logarithmic equation: {e}")
            return result

        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )
            result.add_solution(solution)

        # Check for extraneous solutions
        self._check_extraneous(result, equation, var, fmt)

        # Solution step
        if result.solutions:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Solution{'s' if len(result.solutions) > 1 else ''}",
                description="Valid solutions (within domain)",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Valid Solution",
                description="No solutions exist within the domain of the logarithmic function",
                category="result",
            ))

        return result

    def _combine_logs(self, expr, var, fmt, result, side: str) -> object:
        """Try to combine logarithmic terms on one side."""
        from sympy import collect
        # Check if expression has multiple log terms
        log_terms = list(expr.find(log))
        if len(log_terms) > 1:
            result.add_step(Step(
                title=f"Combine Logarithms ({side.title()} Side)",
                description="Apply: log(a) + log(b) = log(ab) or log(a) - log(b) = log(a/b)",
                category="simplify",
            ))
        return expr

    def _try_exponential_conversion(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> Step | None:
        """
        Try to identify a pattern where we can convert to exponential form.

        Patterns handled:
        - log(expr) = constant → expr = e^constant or 10^constant
        - log(expr1) = log(expr2) → expr1 = expr2
        """
        from sympy import Integer

        lhs, rhs = equation.lhs, equation.rhs

        # Pattern: log(a) = log(b) → a = b
        if lhs.has(log) and rhs.has(log):
            lhs_logs = list(lhs.find(log))
            rhs_logs = list(rhs.find(log))
            if len(lhs_logs) == 1 and len(rhs_logs) == 1:
                inner_lhs = lhs_logs[0].args[0]
                inner_rhs = rhs_logs[0].args[0]
                return Step(
                    title="One-to-One Property of Logarithms",
                    description="If log(a) = log(b), then a = b (for the same base)",
                    equation=fmt.equation(inner_lhs, inner_rhs),
                    category="transform",
                )

        # Pattern: log(a) = c → a = base^c
        if lhs.func == log and not rhs.has(log):
            inner = lhs.args[0]
            base = lhs.args[1] if len(lhs.args) > 1 else "e"
            return Step(
                title="Convert to Exponential Form",
                description=f"Rewrite the logarithmic equation in exponential form",
                equation=f"{fmt.expr(inner)} = {fmt.expr(exp(rhs))}" if base == "e"
                         else f"{fmt.expr(inner)} = {fmt.expr(base)}^{{{fmt.expr(rhs)}}}",
                category="transform",
            )

        if rhs.func == log and not lhs.has(log):
            inner = rhs.args[0]
            return Step(
                title="Convert to Exponential Form",
                description="Rewrite the logarithmic equation in exponential form",
                equation=f"{fmt.expr(inner)} = {fmt.expr(exp(lhs))}",
                category="transform",
            )

        return None

    def _check_extraneous(self, result: StrategyResult, equation: Equation, var: Symbol, fmt: LatexFormatter):
        """Check for extraneous solutions (those violating domain restrictions)."""
        valid = []
        for sol in result.solutions:
            try:
                val = sol.exact_value
                # Check that all log arguments are positive at this solution
                all_positive = True
                for side in (equation.lhs, equation.rhs):
                    for log_expr in side.find(log):
                        arg = log_expr.args[0]
                        evaluated = simplify(arg.subs(var, val))
                        if not evaluated.is_positive:
                            all_positive = False
                            break
                    if not all_positive:
                        break

                if all_positive:
                    valid.append(sol)
                else:
                    result.add_step(Step(
                        title=f"Reject Extraneous Solution",
                        description=f"{fmt.variable(var)} = {sol.exact_latex} makes a logarithm argument non-positive",
                        category="domain_check",
                    ))
            except Exception:
                # If we can't check, keep the solution
                valid.append(sol)

        if len(valid) != len(result.solutions):
            result.solutions = valid
