"""
Rational equation solving strategy.

Solves equations containing fractions where the variable appears in
the denominator by:
1. Finding the least common denominator (LCD)
2. Multiplying both sides by the LCD to clear fractions
3. Solving the resulting polynomial equation
4. Checking for extraneous solutions (denominator = 0)
"""

from __future__ import annotations

from sympy import (
    simplify, solve, expand, lcm, fraction, Add,
    S, Symbol, Eq, cancel, factor,
)

from config import ENABLE_FRACTION_CLEARING
from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class RationalStrategy(BaseStrategy):
    """
    Strategy for solving rational equations (fractions with variable in denominator).

    Generates steps showing:
    - LCD identification
    - Fraction clearing by LCD multiplication
    - Solving the simplified equation
    - Extraneous solution checking
    """

    @property
    def name(self) -> str:
        return "Rational Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.RATIONAL

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.RATIONAL

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.RATIONAL)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in rational equation")
            return result

        # Original equation
        result.add_step(Step(
            title="Original Equation",
            description="Rational equation with variable in denominator",
            equation=fmt.equation(equation.lhs, equation.rhs),
            category="identify",
        ))

        # Find LCD and clear fractions
        cleared_eq = equation.sympy_eq
        if ENABLE_FRACTION_CLEARING:
            cleared_eq, frac_steps = self._clear_fractions(equation, var, fmt)
            result.steps.extend(frac_steps)

        # Identify restricted values (zeros of denominator)
        restricted = self._find_restricted_values(equation, var, fmt)
        if restricted:
            result.steps.extend(restricted)

        # Solve the cleared equation
        try:
            solutions = solve(cleared_eq, var)
        except Exception as e:
            logger.error("Rational solve failed: %s", e)
            result.mark_failed(f"Could not solve rational equation: {e}")
            return result

        # Format and check for extraneous solutions
        valid_solutions = []
        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )

            # Check if this solution makes any denominator zero
            if self._is_extraneous(sol, equation, var):
                result.add_step(Step(
                    title="Reject Extraneous Solution",
                    description=f"{fmt.variable(var)} = {solution.exact_latex} makes a denominator equal to zero",
                    equation=f"{fmt.variable(var)} \\neq {solution.exact_latex}",
                    category="domain_check",
                ))
            else:
                valid_solutions.append(solution)

        result.solutions = valid_solutions

        # Solution step
        if result.solutions:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Valid Solution{'s' if len(result.solutions) > 1 else ''}",
                description="Solutions that do not make any denominator zero",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
        else:
            result.add_step(Step(
                title="No Valid Solution",
                description="All solutions were extraneous (made a denominator zero)",
                category="result",
            ))

        return result

    def _clear_fractions(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> tuple:
        """
        Clear fractions by finding and multiplying by the LCD.

        Returns:
            Tuple of (cleared_Eq, list_of_Steps)
        """
        steps = []

        # Collect all denominators
        denoms = self._collect_denominators(equation)
        if not denoms:
            return equation.sympy_eq, steps

        # Compute LCD
        lcd_val = denoms[0]
        for d in denoms[1:]:
            lcd_val = lcm(lcd_val, d)
        lcd_val = factor(simplify(lcd_val))

        if lcd_val == 1:
            return equation.sympy_eq, steps

        steps.append(Step(
            title="Find the LCD",
            description="Identify the least common denominator of all fractions",
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

        # Compute the cleared equation
        new_lhs = expand(cancel(equation.lhs * lcd_val))
        new_rhs = expand(cancel(equation.rhs * lcd_val))
        cleared_eq = Eq(new_lhs, new_rhs)

        # Step: Show simplified result
        steps.append(Step(
            title="After Clearing Fractions",
            description="All fractions have been eliminated",
            equation=fmt.equation(new_lhs, new_rhs),
            category="fraction",
        ))

        return cleared_eq, steps

    def _collect_denominators(self, equation: Equation) -> list:
        """Collect all unique denominators from the equation."""
        denoms = []
        for side in (equation.lhs, equation.rhs):
            for term in Add.make_args(side):
                numer, denom = fraction(term)
                if denom != 1 and denom not in denoms:
                    denoms.append(denom)
        return denoms

    def _find_restricted_values(self, equation: Equation, var: Symbol, fmt: LatexFormatter) -> list:
        """
        Find values of the variable that make any denominator zero.

        Returns a list of Steps describing the restrictions.
        """
        steps = []

        # Find all denominators that contain the variable
        restricted_values = set()
        for side in (equation.lhs, equation.rhs):
            for term in Add.make_args(side):
                _, denom = fraction(term)
                if var in denom.free_symbols:
                    try:
                        zeros = solve(denom, var)
                        for z in zeros:
                            restricted_values.add(simplify(z))
                    except Exception:
                        pass

        if restricted_values:
            restrictions = ", ".join(
                [f"{fmt.variable(var)} \\neq {fmt.expr(v)}" for v in restricted_values]
            )
            steps.append(Step(
                title="Domain Restrictions",
                description="The variable cannot take values that make any denominator zero",
                equation=restrictions,
                category="domain",
            ))

        return steps

    def _is_extraneous(self, sol, equation: Equation, var: Symbol) -> bool:
        """Check if a solution is extraneous (makes a denominator zero)."""
        try:
            for side in (equation.lhs, equation.rhs):
                for term in Add.make_args(side):
                    _, denom = fraction(term)
                    if var in denom.free_symbols:
                        evaluated = simplify(denom.subs(var, sol))
                        if evaluated == 0 or (evaluated.is_number and abs(float(evaluated)) < 1e-10):
                            return True
        except Exception:
            pass
        return False
