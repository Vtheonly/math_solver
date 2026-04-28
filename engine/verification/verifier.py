"""
Solution verifier for the equation solving engine.

Substitutes solutions back into the original equation to confirm
they are valid. Generates verification steps showing the
substitution and the check result.
"""

from __future__ import annotations

from typing import List

from sympy import simplify, Eq, Symbol, Abs

from config import VERIFICATION_TOLERANCE, MAX_VERIFIED_SOLUTIONS
from engine.models.equation import Equation
from engine.models.solution import Solution
from engine.models.step import Step
from engine.utils.latex_formatter import LatexFormatter
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class Verifier:
    """
    Verifies solutions by substitution into the original equation.

    Supports both single-equation and system verification.
    Generates clear step-by-step verification output.
    """

    @staticmethod
    def verify_solution(
        equation: Equation,
        solution: Solution,
        index: int = 0,
        total: int = 1,
    ) -> Step | None:
        """
        Verify a single solution against an equation.

        Args:
            equation: The original equation (with fractions, etc.).
            solution: The solution to verify.
            index: Solution index (0-based) for labeling.
            total: Total number of solutions for labeling.

        Returns:
            A Step object showing the verification, or None if verification fails.
        """
        fmt = LatexFormatter()
        var = equation.primary_variable

        if var is None or str(var) != solution.variable_name:
            logger.debug(
                "Variable mismatch: equation has '%s', solution has '%s'",
                var,
                solution.variable_name,
            )
            # Try to find the matching variable
            for v in equation.variables:
                if str(v) == solution.variable_name:
                    var = v
                    break
            if var is None:
                return None

        try:
            val = solution.exact_value
            lhs_val = simplify(equation.lhs.subs(var, val))
            rhs_val = simplify(equation.rhs.subs(var, val))

            diff = simplify(lhs_val - rhs_val)
            is_valid = Verifier._check_validity(diff)

            label = "Verify Solution" if total == 1 else f"Verify Solution {index + 1}"
            mark = "\\checkmark" if is_valid else "\\times"

            solution.mark_verified(
                error=abs(complex(diff.evalf())) if not is_valid else 0.0
            )

            return Step(
                title=f"{mark} {label}",
                description=f"Substitute {fmt.variable(var)} = {solution.exact_latex} "
                           f"into the original equation",
                equation=fmt.verify_substitution(var, val, lhs_val, rhs_val, is_valid),
                category="verify",
            )

        except Exception as e:
            logger.debug(
                "Verification failed for %s = %s: %s",
                solution.variable_name,
                solution.exact_latex,
                e,
            )
            return None

    @staticmethod
    def verify_all(
        equation: Equation,
        solutions: List[Solution],
    ) -> List[Step]:
        """
        Verify all solutions against an equation.

        Verifies up to MAX_VERIFIED_SOLUTIONS solutions.

        Args:
            equation: The original equation.
            solutions: List of solutions to verify.

        Returns:
            List of verification Step objects.
        """
        steps = []
        count = min(len(solutions), MAX_VERIFIED_SOLUTIONS)

        for i in range(count):
            step = Verifier.verify_solution(
                equation=equation,
                solution=solutions[i],
                index=i,
                total=len(solutions),
            )
            if step:
                steps.append(step)

        return steps

    @staticmethod
    def verify_system_solution(
        equations: List[Equation],
        solutions: List[Solution],
    ) -> List[Step]:
        """
        Verify solutions against all equations in a system.

        Args:
            equations: List of equations in the system.
            solutions: List of solutions (one per variable).

        Returns:
            List of verification Step objects.
        """
        steps = []
        fmt = LatexFormatter()

        # Build substitution dict from solutions
        from sympy import symbols
        sub_dict = {}
        for sol in solutions:
            sub_dict[symbols(sol.variable_name)] = sol.exact_value

        for i, eq in enumerate(equations, 1):
            try:
                lhs_val = simplify(eq.lhs.subs(sub_dict))
                rhs_val = simplify(eq.rhs.subs(sub_dict))
                diff = simplify(lhs_val - rhs_val)
                is_valid = Verifier._check_validity(diff)

                mark = "\\checkmark" if is_valid else "\\times"
                sub_desc = ", ".join(
                    [f"{fmt.variable(symbols(s.variable_name))} = {s.exact_latex}"
                     for s in solutions]
                )

                steps.append(Step(
                    title=f"{mark} Verify in Equation {i}",
                    description=f"Substitute {sub_desc}",
                    equation=f"{fmt.expr(lhs_val)} = {fmt.expr(rhs_val)} \\quad {mark}",
                    category="verify",
                ))

            except Exception as e:
                logger.debug("System verification failed for eq %d: %s", i, e)

        return steps

    @staticmethod
    def _check_validity(diff) -> bool:
        """
        Check if a difference expression is effectively zero.

        Handles both exact symbolic zero and numerical near-zero.
        """
        if diff == 0:
            return True

        try:
            numerical = complex(diff.evalf())
            return abs(numerical) < VERIFICATION_TOLERANCE
        except Exception:
            pass

        try:
            simplified = simplify(diff)
            return simplified == 0
        except Exception:
            return False
