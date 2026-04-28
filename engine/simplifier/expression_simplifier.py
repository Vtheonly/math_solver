"""
Logic for the Expression Simplifier mode.
"""
import sympy as sp
from typing import List

from engine.models.equation import Equation
from engine.models.solve_result import SolveResult
from engine.models.solution import Solution
from engine.models.step import Step

class ExpressionSimplifier:
    """
    Handles simplifying expressions without trying to solve them like equations.
    """

    @staticmethod
    def simplify(raw_input: str, equations: List[Equation]) -> SolveResult:
        result = SolveResult()
        
        if not equations:
            result.mark_failed("No expression to simplify.")
            return result

        eq = equations[0]
        expr = eq.lhs
        
        if "=" in raw_input:
            expr = eq.lhs - eq.rhs

        result.add_step(Step(
            title="Original Expression",
            description="The starting mathematical expression.",
            equation=sp.latex(expr),
            category="simplify"
        ))

        # Simplify
        try:
            simplified = sp.simplify(expr)
            
            result.add_step(Step(
                title="Simplified Form",
                description="Applying algebraic simplification rules.",
                equation=sp.latex(simplified),
                category="simplify"
            ))
            
            sol = Solution(
                variable_name="Expression",
                exact_value=simplified
            )
            result.add_solution(sol)
        except Exception as e:
            result.mark_failed(f"Simplification failed: {str(e)}")

        return result
