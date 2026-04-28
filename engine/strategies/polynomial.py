"""
Polynomial equation solving strategy.

Solves higher-degree polynomial equations (degree >= 4) by:
1. Attempting factorization
2. Finding rational roots
3. Using SymPy's general polynomial solver
"""

from __future__ import annotations

from sympy import (
    Poly, factor, expand, simplify, solve, solveset,
    S, Symbol, factor_list, roots,
)

from config import ENABLE_FACTORIZATION_STEPS
from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class PolynomialStrategy(BaseStrategy):
    """
    Strategy for solving polynomial equations of degree >= 4.

    Attempts factorization first, then falls back to SymPy's
    general polynomial solver. Generates steps showing the
    factoring process and root identification.
    """

    @property
    def name(self) -> str:
        return "Polynomial Equation Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.POLYNOMIAL

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.POLYNOMIAL

    def solve(self, equation: Equation) -> StrategyResult:
        result = StrategyResult(equation_type=EquationType.POLYNOMIAL)
        var = equation.primary_variable
        fmt = LatexFormatter()

        if var is None:
            result.mark_failed("No variable found in polynomial equation")
            return result

        # Standard form
        expr = expand(equation.lhs - equation.rhs)
        deg = equation.degree or self._compute_degree(expr, var)

        result.add_step(Step(
            title="Rearrange to Standard Form",
            description=f"This is a degree-{deg} polynomial equation",
            equation=fmt.standard_form(expr),
            category="rearrange",
        ))

        # Try factorization
        factored = factor(expr)
        if ENABLE_FACTORIZATION_STEPS and factored != expr:
            result.add_step(Step(
                title="Factor the Polynomial",
                description="Factor the expression to identify roots",
                equation=f"{fmt.expr(factored)} = 0",
                category="factor",
            ))

            # Show factor list for deeper insight
            try:
                flist = factor_list(expr)
                if flist and len(flist) > 1:
                    factors = flist[1]
                    if factors:
                        factor_descriptions = []
                        for f, mult in factors:
                            f_simplified = simplify(f)
                            factor_descriptions.append(
                                f"({fmt.expr(f_simplified)})"
                                + (f"^{mult}" if mult > 1 else "")
                            )
                        result.add_step(Step(
                            title="Factor Breakdown",
                            description="Individual polynomial factors and their multiplicities",
                            equation=" \\cdot ".join(factor_descriptions) + " = 0",
                            category="factor",
                        ))
            except Exception:
                logger.debug("Could not generate factor list", exc_info=True)

        # Try to find rational roots for additional insight
        try:
            rts = roots(expr, var)
            if rts:
                rational_roots = {k: v for k, v in rts.items() if k.is_rational}
                if rational_roots:
                    root_strs = []
                    for root_val, mult in rational_roots.items():
                        root_strs.append(f"{fmt.expr(root_val)}" + (f" (mult. {mult})" if mult > 1 else ""))
                    result.add_step(Step(
                        title="Rational Roots Found",
                        description="These rational roots were identified by the rational root theorem",
                        equation=", \\quad ".join(root_strs),
                        category="insight",
                    ))
        except Exception:
            logger.debug("Could not find rational roots", exc_info=True)

        # Solve using SymPy
        try:
            solutions = solve(equation.sympy_eq, var)

            if not solutions:
                # Try solveset as backup
                sol_set = solveset(equation.sympy_eq, var, domain=S.Reals)
                if sol_set != S.EmptySet:
                    try:
                        solutions = list(sol_set)
                    except Exception:
                        solutions = []
        except Exception as e:
            logger.error("SymPy solve failed for polynomial: %s", e)
            result.mark_failed(f"Could not solve polynomial: {e}")
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

    def _compute_degree(self, expr, var) -> int | None:
        """Compute the polynomial degree."""
        try:
            return Poly(expr, var).degree()
        except Exception:
            return None

    def _add_solution_step(self, result: StrategyResult, var: Symbol, fmt: LatexFormatter):
        """Add the final solution step."""
        if not result.solutions:
            result.add_step(Step(
                title="No Real Solutions",
                description="This polynomial has no real roots",
                category="result",
            ))
        else:
            sol_latex = ", \\quad ".join(
                [fmt.assignment(var, s.exact_value) for s in result.solutions]
            )
            result.add_step(Step(
                title=f"Solutions ({len(result.solutions)} found)",
                description="Roots of the polynomial equation",
                equation=sol_latex,
                category="result",
                is_highlight=True,
            ))
