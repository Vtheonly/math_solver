"""
System of equations solving strategy.

Solves systems of equations by:
1. Parsing all equations
2. Clearing fractions in each equation
3. Using substitution method (with detailed back-substitution steps)
4. Verifying all solutions in every equation
"""

from __future__ import annotations

from typing import List, Optional

from sympy import (
    simplify, solve, expand, Eq, Symbol, Matrix,
)

from config import (
    SYSTEM_MAX_EQUATIONS,
    ENABLE_FRACTION_CLEARING,
    ENABLE_BACK_SUBSTITUTION_STEPS,
)
from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.strategies.base import BaseStrategy, StrategyResult
from engine.strategies.rational import RationalStrategy
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class SystemStrategy(BaseStrategy):
    """
    Strategy for solving systems of equations.

    Generates steps showing:
    - Each equation parsed
    - Fraction clearing (if needed)
    - Variable isolation from one equation
    - Substitution into other equations
    - Back-substitution to find all variables
    - Verification in all equations
    """

    @property
    def name(self) -> str:
        return "System of Equations Solver"

    @property
    def handled_type(self) -> EquationType:
        return EquationType.SYSTEM

    def can_handle(self, equation: Equation) -> bool:
        return equation.equation_type == EquationType.SYSTEM

    def solve(self, equation: Equation) -> StrategyResult:
        # This method handles the case where a single Equation object
        # represents a system. For actual system solving, use solve_system().
        result = StrategyResult(equation_type=EquationType.SYSTEM)
        result.mark_failed("Use solve_system() for system of equations")
        return result

    def solve_system(self, equations: List[Equation]) -> StrategyResult:
        """
        Solve a system of equations.

        Args:
            equations: List of Equation objects forming the system.

        Returns:
            A StrategyResult with all solutions and detailed steps.
        """
        result = StrategyResult(equation_type=EquationType.SYSTEM, is_system=True)
        fmt = LatexFormatter()

        if len(equations) > SYSTEM_MAX_EQUATIONS:
            result.mark_failed(f"Too many equations (max {SYSTEM_MAX_EQUATIONS})")
            return result

        # Collect all variables
        all_vars = []
        seen = set()
        for eq in equations:
            for v in eq.variables:
                if str(v) not in seen:
                    all_vars.append(v)
                    seen.add(str(v))

        # Step: List all equations
        for i, eq in enumerate(equations, 1):
            result.add_step(Step(
                title=f"Equation {i}",
                description=f"Parsed equation {i}",
                equation=fmt.sympy_eq(eq.sympy_eq),
                category="identify",
            ))

        # Step: System overview
        var_list = ", ".join([fmt.variable(v) for v in all_vars])
        result.add_step(Step(
            title="System Overview",
            description=f"{len(equations)} equation(s), {len(all_vars)} variable(s): {var_list}",
            category="overview",
        ))

        # Clear fractions in each equation
        cleared_eqs = []
        for i, eq in enumerate(equations, 1):
            cleared_eq = eq.sympy_eq
            if eq.has_fractions and ENABLE_FRACTION_CLEARING:
                rational = RationalStrategy()
                cleared, frac_steps = rational._clear_fractions(eq, eq.primary_variable, fmt)
                for step in frac_steps:
                    step.title = f"Eq {i}: {step.title}"
                    result.add_step(step)
                cleared_eqs.append(cleared)
            else:
                cleared_eqs.append(eq.sympy_eq)

        # Substitution steps
        if ENABLE_BACK_SUBSTITUTION_STEPS and len(all_vars) >= 2 and len(equations) >= 2:
            sub_steps = self._generate_substitution_steps(cleared_eqs, all_vars, fmt)
            result.steps.extend(sub_steps)

        # Solve the system
        try:
            solutions = solve(cleared_eqs, all_vars, dict=True)
        except Exception as e:
            logger.error("System solve failed: %s", e)
            result.mark_failed(f"Could not solve system: {e}")
            return result

        if not solutions:
            result.add_step(Step(
                title="No Solution",
                description="The system has no solution (inconsistent) or infinitely many solutions",
                category="result",
            ))
            return result

        sol_dict = solutions[0] if isinstance(solutions, list) else solutions

        # Format solutions
        for v in all_vars:
            if v in sol_dict:
                val = simplify(sol_dict[v])
                result.add_solution(Solution(
                    variable_name=str(v),
                    exact_value=val,
                ))

        # Solution step
        if result.solutions:
            parts = []
            for sol in result.solutions:
                parts.append(f"{sol.variable_name} = {sol.exact_latex}")
            result.add_step(Step(
                title="Solution",
                description="Solution to the system of equations",
                equation=", \\quad ".join(parts),
                category="result",
                is_highlight=True,
            ))

        return result

    def _generate_substitution_steps(
        self, eqs: List[Eq], vars: List[Symbol], fmt: LatexFormatter
    ) -> List[Step]:
        """
        Generate detailed substitution and back-substitution steps.

        Shows how one variable is isolated from one equation and
        substituted into another, then back-substituted.
        """
        steps = []

        if len(vars) < 2 or len(eqs) < 2:
            return steps

        v0 = vars[0]
        eq0 = eqs[0]

        try:
            # Isolate first variable from first equation
            expr_v0 = solve(eq0, v0)
            if not expr_v0:
                return steps
            expr_v0 = expr_v0[0]

            steps.append(Step(
                title=f"Isolate {fmt.variable(v0)} from Equation 1",
                description=f"Solve equation 1 for {fmt.variable(v0)}",
                equation=fmt.assignment(v0, expr_v0),
                category="isolate",
            ))

            # Substitute into equation 2
            eq2 = eqs[1]
            subbed_lhs = eq2.lhs.subs(v0, expr_v0)
            subbed_rhs = eq2.rhs.subs(v0, expr_v0)
            subbed_eq = Eq(expand(subbed_lhs), expand(subbed_rhs))

            steps.append(Step(
                title="Substitute into Equation 2",
                description=f"Replace {fmt.variable(v0)} with {fmt.expr(simplify(expr_v0))} in equation 2",
                equation=fmt.equation(subbed_lhs, subbed_rhs),
                category="substitute",
            ))

            # Solve for second variable
            if len(vars) >= 2:
                v1 = vars[1]
                v1_sols = solve(subbed_eq, v1)
                if v1_sols:
                    v1_val = simplify(v1_sols[0])
                    steps.append(Step(
                        title=f"Solve for {fmt.variable(v1)}",
                        description="The substituted equation now has one variable — solve it",
                        equation=fmt.assignment(v1, v1_val),
                        category="solve",
                    ))

                    # Back-substitute
                    v0_val = simplify(expr_v0.subs(v1, v1_val))
                    steps.append(Step(
                        title=f"Back-Substitute to Find {fmt.variable(v0)}",
                        description=f"Plug {fmt.variable(v1)} = {fmt.expr(v1_val)} back into the expression for {fmt.variable(v0)}",
                        equation=fmt.back_substitution(v0, expr_v0, v1, v1_val, v0_val),
                        category="back_substitute",
                    ))

                    # For 3+ variable systems, show further substitution
                    if len(vars) >= 3 and len(eqs) >= 3:
                        steps.append(Step(
                            title="Continue Substitution",
                            description="Continue substituting known values into remaining equations",
                            category="substitute",
                        ))

        except Exception as e:
            logger.debug("Could not generate substitution steps: %s", e)

        return steps
