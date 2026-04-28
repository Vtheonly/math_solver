"""
Quadratic equation solving strategy.

Solves equations of the form ax² + bx + c = 0 by:
1. Attempting factorization first
2. If unfactorable, applying the quadratic formula
3. Computing discriminant and classifying root nature
"""

from __future__ import annotations

from sympy import (
    Poly, factor, expand, simplify, solve, sqrt, Symbol,
)

from config import (
    ENABLE_FACTORIZATION_STEPS,
    ENABLE_COEFFICIENT_IDENTIFICATION,
    ENABLE_DISCRIMINANT_STEPS,
)
from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class QuadraticStrategy(BaseStrategy):
    """
    Strategy for solving quadratic equations (degree 2).

    Generates detailed steps showing either:
    - Factorization method (if the quadratic factors nicely), or
    - Quadratic formula method (discriminant, coefficients, formula)
    """

    @property
    def name(self) -> str:
        return "Quadratic Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.QUADRATIC

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.QUADRATIC

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.QUADRATIC)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in quadratic equation")
            return result

        # Standard form
        expr = expand(equation.lhs - equation.rhs)
        result.add_step(Step(
            title="Rearrange to Standard Form",
            description="Move all terms to the left side",
            equation=fmt.standard_form(expr),
            category="rearrange",
        ))

        # Try factorization first
        factored = factor(expr)
        use_factoring = (
            ENABLE_FACTORIZATION_STEPS
            and factored != expr
            and _is_factored_form(factored)
        )

        if use_factoring:
            result.add_step(Step(
                title="Factor the Quadratic",
                description="Factor the expression into a product of linear factors",
                equation=f"{fmt.expr(factored)} = 0",
                category="factor",
            ))
            result.add_step(Step(
                title="Apply Zero Product Property",
                description="If a product equals zero, at least one factor must be zero",
                category="factor",
            ))
        else:
            # Quadratic formula path
            if ENABLE_COEFFICIENT_IDENTIFICATION:
                coeff_steps = self._generate_coefficient_steps(expr, var, fmt)
                result.steps.extend(coeff_steps)

            if ENABLE_DISCRIMINANT_STEPS:
                disc_steps = self._generate_discriminant_steps(expr, var, fmt)
                result.steps.extend(disc_steps)

            # Quadratic formula application
            formula_step = self._generate_formula_step(expr, var, fmt)
            if formula_step:
                result.add_step(formula_step)

        # Solve
        try:
            solutions = solve(equation.sympy_eq, var)
        except Exception as e:
            logger.error("SymPy solve failed: %s", e)
            result.mark_failed(f"Could not solve: {e}")
            return result

        for sol in solutions:
            sol_simplified = simplify(sol)
            solution = Solution(
                variable_name=str(var),
                exact_value=sol_simplified,
            )
            result.add_solution(solution)

        # Solution step
        self._add_solution_step(result, var, fmt)

        return result

    def _generate_coefficient_steps(self, expr, var, fmt) -> list:
        """Generate steps identifying the coefficients a, b, c."""
        steps = []
        try:
            p = Poly(expr, var)
            coeffs = p.all_coeffs()
            if len(coeffs) == 3:
                a_c, b_c, c_c = coeffs
                steps.append(Step(
                    title="Identify Coefficients",
                    description=f"Written in the form a{fmt.variable(var)}² + b{fmt.variable(var)} + c = 0",
                    equation=fmt.coefficients({"a": a_c, "b": b_c, "c": c_c}),
                    category="identify",
                ))
        except Exception:
            logger.debug("Could not identify coefficients", exc_info=True)
        return steps

    def _generate_discriminant_steps(self, expr, var, fmt) -> list:
        """Generate discriminant calculation steps."""
        steps = []
        try:
            p = Poly(expr, var)
            coeffs = p.all_coeffs()
            if len(coeffs) == 3:
                a_c, b_c, c_c = coeffs
                disc = simplify(b_c ** 2 - 4 * a_c * c_c)

                steps.append(Step(
                    title="Calculate Discriminant",
                    description="The discriminant Δ = b² - 4ac determines the nature of the roots",
                    equation=fmt.discriminant(disc),
                    category="discriminant",
                ))

                # Nature of roots
                disc_val = disc.evalf()
                if disc_val > 0:
                    nature = "two distinct real roots"
                elif disc_val == 0:
                    nature = "one repeated real root"
                else:
                    nature = "two complex conjugate roots"

                steps.append(Step(
                    title="Nature of Roots",
                    description=f"Based on the discriminant, this equation has {nature}",
                    category="discriminant",
                ))
        except Exception:
            logger.debug("Could not generate discriminant steps", exc_info=True)
        return steps

    def _generate_formula_step(self, expr, var, fmt) -> Step | None:
        """Generate the quadratic formula application step."""
        try:
            p = Poly(expr, var)
            coeffs = p.all_coeffs()
            if len(coeffs) == 3:
                a_c, b_c, c_c = coeffs
                disc = simplify(b_c ** 2 - 4 * a_c * c_c)
                return Step(
                    title="Apply Quadratic Formula",
                    description="Use the quadratic formula to find the roots",
                    equation=fmt.quadratic_formula(var, a_c, b_c, disc),
                    category="formula",
                )
        except Exception:
            logger.debug("Could not generate formula step", exc_info=True)
        return None

    def _add_solution_step(self, result: StrategyResult, var: Symbol, fmt: LatexFormatter):
        """Add the final solution step."""
        if not result.solutions:
            result.add_step(Step(
                title="No Real Solution",
                description="The discriminant is negative; no real solutions exist",
                category="result",
            ))
        elif len(result.solutions) == 1:
            result.add_step(Step(
                title="Solution",
                description="One root found (discriminant = 0, repeated root)",
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
                description=f"Two roots found",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))


def _is_factored_form(expr) -> bool:
    """Check if an expression is in factored form (a product of terms)."""
    from sympy import Mul
    return expr.is_Mul or (expr.func == Mul)
