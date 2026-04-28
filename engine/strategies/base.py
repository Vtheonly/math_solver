"""
Base strategy interface for the equation solving engine.

Defines the abstract interface that all solving strategies must implement,
along with the StrategyResult data class that strategies return.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step
from engine.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyResult:
    """
    Result returned by a solving strategy.

    Attributes:
        success: Whether the strategy successfully solved the equation.
        solutions: List of Solution objects found.
        steps: List of Step objects generated during solving.
        equation_type: The confirmed equation type.
        is_numerical: Whether solutions were obtained numerically.
        error_message: Error message if solving failed.
        warnings: Non-fatal warnings.
        modified_equation: Optionally, a transformed equation after preprocessing
                          (e.g., after clearing fractions) for use in verification.
    """

    success: bool = True
    solutions: List[Solution] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    equation_type: Optional[EquationType] = None
    is_numerical: bool = False
    is_system: bool = False
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    modified_equation: Optional[Equation] = None

    def add_step(self, step: Step):
        """Append a step to the result."""
        self.steps.append(step)

    def add_solution(self, solution: Solution):
        """Append a solution to the result."""
        self.solutions.append(solution)

    def add_warning(self, warning: str):
        """Record a non-fatal warning."""
        self.warnings.append(warning)

    def mark_failed(self, error: str):
        """Mark the result as failed."""
        self.success = False
        self.error_message = error


class BaseStrategy(ABC):
    """
    Abstract base class for all solving strategies.

    Each strategy handles a specific equation type and provides:
    - Solving logic (the actual math)
    - Step generation (walkthrough for the user)
    - Error handling (graceful failure)

    Subclasses must implement:
    - can_handle(equation): Whether this strategy can solve the equation
    - solve(equation): Perform the solving and return StrategyResult
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this strategy."""
        ...

    @property
    @abstractmethod
    def handled_type(self) -> EquationType:
        """The equation type this strategy handles."""
        ...

    @abstractmethod
    def can_handle(self, equation: Equation) -> bool:
        """
        Check if this strategy can handle the given equation.

        Args:
            equation: The equation to check.

        Returns:
            True if this strategy should be used for this equation.
        """
        ...

    @abstractmethod
    def solve(self, equation: Equation) -> StrategyResult:
        """
        Solve the equation and generate steps.

        Args:
            equation: The equation to solve.

        Returns:
            A StrategyResult with solutions and steps.
        """
        ...

    def safe_solve(self, equation: Equation) -> StrategyResult:
        """
        Wrapper around solve() with comprehensive error handling.

        Catches all exceptions and returns a failed StrategyResult
        rather than propagating errors.
        """
        logger.info("Strategy '%s' solving: %s", self.name, equation)
        try:
            result = self.solve(equation)
            logger.info(
                "Strategy '%s' result: %d solutions, %d steps",
                self.name,
                len(result.solutions),
                len(result.steps),
            )
            return result
        except Exception as e:
            logger.exception("Strategy '%s' failed with exception: %s", self.name, e)
            result = StrategyResult(success=False)
            result.mark_failed(f"{self.name} strategy failed: {e}")
            return result
