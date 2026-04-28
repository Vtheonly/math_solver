"""
Step builder for the equation solving engine.

Provides factory methods for creating common Step objects,
ensuring consistent formatting and descriptions across
all strategies.
"""

from __future__ import annotations

from typing import Optional

from sympy import Eq, Expr, Symbol, expand, simplify

from engine.models.equation import Equation, EquationType
from engine.models.step import Step
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class StepBuilder:
    """
    Factory for creating common Step objects.

    Centralizes step creation so all strategies produce
    consistently formatted and described steps.
    """

    fmt = LatexFormatter()

    @staticmethod
    def original_equation(equation: Equation) -> Step:
        """Create a step showing the original equation."""
        return Step(
            title="Original Equation",
            description="Starting equation as entered",
            equation=LatexFormatter.sympy_eq(equation.sympy_eq),
            category="identify",
        )

    @staticmethod
    def equation_type(equation: Equation) -> Step:
        """Create a step identifying the equation type."""
        return Step(
            title="Equation Type",
            description=f"This is a **{equation.equation_type.display_name}** equation"
                        + (f" in {LatexFormatter.variable(equation.primary_variable)}"
                           if equation.primary_variable else ""),
            category="classify",
        )

    @staticmethod
    def standard_form(equation: Equation) -> Step:
        """Create a step showing the equation in standard form (= 0)."""
        expr = expand(equation.lhs - equation.rhs)
        return Step(
            title="Rearrange to Standard Form",
            description="Move all terms to the left side",
            equation=LatexFormatter.standard_form(expr),
            category="rearrange",
        )

    @staticmethod
    def solved_for(var: Symbol, solutions: list, is_numerical: bool = False) -> Step:
        """Create a step showing the final solution(s)."""
        if not solutions:
            return Step(
                title="No Solution",
                description="No solutions were found",
                category="result",
            )

        if len(solutions) == 1:
            sol = solutions[0]
            return Step(
                title="Solution" + (" (Numerical)" if is_numerical else ""),
                description="The solution to the equation",
                equation=LatexFormatter.assignment(var, sol.exact_value),
                category="result",
                is_highlight=True,
            )

        sol_latex = ", \\quad ".join(
            [LatexFormatter.assignment(var, s.exact_value) for s in solutions]
        )
        return Step(
            title=f"Solutions ({len(solutions)})" + (" (Numerical)" if is_numerical else ""),
            description=f"Found {len(solutions)} solution(s)",
            equation=sol_latex,
            category="result",
            is_highlight=True,
        )

    @staticmethod
    def system_overview(equations: list, variables: list) -> Step:
        """Create a step showing the system overview."""
        var_list = ", ".join([LatexFormatter.variable(v) for v in variables])
        return Step(
            title="System Overview",
            description=f"{len(equations)} equation(s), {len(variables)} variable(s): {var_list}",
            category="overview",
        )

    @staticmethod
    def no_solution(reason: str = "") -> Step:
        """Create a step indicating no solution."""
        desc = reason or "No solutions were found for this equation"
        return Step(
            title="No Solution",
            description=desc,
            category="result",
        )

    @staticmethod
    def periodicity_note(trig_type: str = "trigonometric") -> Step:
        """Create a step noting periodicity for trig equations."""
        return Step(
            title="Note on Periodicity",
            description="Trigonometric equations have infinitely many solutions due to periodicity. "
                       "The solutions shown are principal values. Add 2πn (sin/cos) or πn (tan) "
                       "for the general solution, where n ∈ ℤ.",
            category="note",
        )

    @staticmethod
    def domain_restriction(variable: Symbol, restricted_values: list) -> Step:
        """Create a step showing domain restrictions."""
        restrictions = ", ".join(
            [f"{LatexFormatter.variable(variable)} \\neq {LatexFormatter.expr(v)}"
             for v in restricted_values]
        )
        return Step(
            title="Domain Restrictions",
            description="The variable cannot take values that make any denominator zero or any logarithm argument non-positive",
            equation=restrictions,
            category="domain",
        )
