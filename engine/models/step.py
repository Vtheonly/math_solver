"""
Step data model.

Represents a single step in the step-by-step solution walkthrough,
including a title, description, and optional LaTeX equation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Step:
    """
    A single step in the solution walkthrough.

    Attributes:
        title: Short label for this step (e.g., "Factor the Quadratic").
        description: Longer explanation of what is happening in this step.
        equation: LaTeX equation string to display, or None if no equation.
        step_number: Sequential step number (assigned by the pipeline).
        category: Category tag for grouping (e.g., "parse", "classify", "solve").
        is_highlight: Whether this step should be visually highlighted.
    """

    title: str
    description: str
    equation: Optional[str] = None
    step_number: int = 0
    category: str = "general"
    is_highlight: bool = False

    def to_dict(self) -> dict:
        """Serialize to a dictionary for JSON response."""
        return {
            "title": self.title,
            "description": self.description,
            "equation": self.equation,
            "step_number": self.step_number,
            "category": self.category,
            "is_highlight": self.is_highlight,
        }

    def with_number(self, number: int) -> "Step":
        """Return a copy of this step with an assigned number."""
        return Step(
            title=self.title,
            description=self.description,
            equation=self.equation,
            step_number=number,
            category=self.category,
            is_highlight=self.is_highlight,
        )

    def __repr__(self) -> str:
        eq_preview = f" | {self.equation[:40]}..." if self.equation and len(self.equation) > 40 else f" | {self.equation}" if self.equation else ""
        return f"Step({self.step_number}: {self.title}{eq_preview})"
