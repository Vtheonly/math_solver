"""
Equation Solving Engine

A modular, extensible engine for solving mathematical equations
with step-by-step solutions. Supports:

- Linear, quadratic, cubic, and higher-degree polynomial equations
- Rational equations (fractions with variable in denominator)
- Trigonometric equations
- Logarithmic and exponential equations
- Absolute value equations
- Systems of equations (multi-variable)
- Numerical fallback for unsolvable cases
- Solution verification by substitution

Architecture:
    Parser → Classifier → Strategy → Verifier → Result

Usage:
    from engine.pipeline import SolverPipeline
    pipeline = SolverPipeline()
    result = pipeline.solve("x^2 - 5x + 6 = 0")
    print(result.to_dict())
"""

from engine.models import Equation, Solution, Step, SolveResult
from engine.pipeline import SolverPipeline
from engine.parser import EquationParser
from engine.classifiers import EquationClassifier
from engine.strategies import StrategyFactory
from engine.verification import Verifier

__version__ = "1.0.0"

__all__ = [
    "Equation",
    "Solution",
    "Step",
    "SolveResult",
    "SolverPipeline",
    "EquationParser",
    "EquationClassifier",
    "StrategyFactory",
    "Verifier",
]
