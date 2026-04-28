"""
SolveResult data model.

The top-level result object produced by the solving pipeline.
Contains all solutions, steps, metadata, and any errors encountered.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from engine.models.equation import Equation, EquationType
from engine.models.solution import Solution
from engine.models.step import Step


@dataclass
class SolveResult:
    """
    Complete result of solving an equation or system.

    Attributes:
        success: Whether solving completed without errors.
        equations: List of parsed Equation objects.
        solutions: List of Solution objects found.
        steps: Ordered list of Step objects forming the walkthrough.
        equation_type: The classified type of the equation(s).
        primary_variable: The main variable that was solved for.
        is_system: Whether this was a system of equations.
        is_numerical: Whether solutions were obtained numerically.
        error_message: Error message if solving failed, None otherwise.
        warnings: Non-fatal warnings encountered during solving.
        processing_time_ms: Time taken to solve, in milliseconds.
    """

    success: bool = True
    equations: List[Equation] = field(default_factory=list)
    solutions: List[Solution] = field(default_factory=list)
    steps: List[Step] = field(default_factory=list)
    equation_type: Optional[EquationType] = None
    primary_variable: Optional[str] = None
    is_system: bool = False
    is_numerical: bool = False
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    processing_time_ms: float = 0.0
    graph_data: Optional[dict] = None

    def add_step(self, step: Step):
        """Append a step and auto-assign its number."""
        step = step.with_number(len(self.steps) + 1)
        self.steps.append(step)

    def add_warning(self, warning: str):
        """Record a non-fatal warning."""
        self.warnings.append(warning)

    def add_solution(self, solution: Solution):
        """Append a solution to the result."""
        self.solutions.append(solution)

    def mark_failed(self, error: str):
        """Mark the result as failed with an error message."""
        self.success = False
        self.error_message = error

    @property
    def has_solutions(self) -> bool:
        """Whether any solutions were found."""
        return len(self.solutions) > 0

    @property
    def num_solutions(self) -> int:
        """Number of solutions found."""
        return len(self.solutions)

    @property
    def variable_names(self) -> List[str]:
        """List of all variable names across equations."""
        names = set()
        for eq in self.equations:
            names.update(eq.variable_names)
        return sorted(names)

    def to_dict(self) -> dict:
        """Serialize to a dictionary for JSON response."""
        result = {
            "success": self.success,
            "solutions": [s.to_dict() for s in self.solutions],
            "steps": [s.to_dict() for s in self.steps],
            "is_system": self.is_system,
            "is_numerical": self.is_numerical,
        }

        if self.equation_type:
            result["equation_type"] = self.equation_type.value
            result["equation_type_display"] = self.equation_type.display_name

        if self.primary_variable:
            result["variable"] = self.primary_variable

        if self.error_message:
            result["error"] = self.error_message

        if self.warnings:
            result["warnings"] = self.warnings

        if self.processing_time_ms > 0:
            result["processing_time_ms"] = round(self.processing_time_ms, 2)

        if self.graph_data:
            result["graph_data"] = self.graph_data

        return result

    def __repr__(self) -> str:
        status = "OK" if self.success else f"FAIL: {self.error_message}"
        return (
            f"SolveResult({status}, "
            f"solutions={len(self.solutions)}, "
            f"steps={len(self.steps)}, "
            f"type={self.equation_type})"
        )
