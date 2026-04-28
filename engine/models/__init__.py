"""
Core data models for the equation solving engine.

Defines the fundamental data structures used throughout the pipeline:
- Equation: parsed representation of a mathematical equation
- Solution: a single solution with exact, decimal, and verification status
- Step: a single step in the solution walkthrough
- SolveResult: the complete result of solving an equation or system
"""

from engine.models.equation import Equation
from engine.models.solution import Solution
from engine.models.step import Step
from engine.models.solve_result import SolveResult

__all__ = [
    "Equation",
    "Solution",
    "Step",
    "SolveResult",
]
