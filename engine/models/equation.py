"""
Equation data model.

Represents a parsed mathematical equation with metadata about its structure,
type, and the variables it contains. This is the primary data object that
flows through the solving pipeline.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from sympy import Eq, Expr, Symbol


class EquationType(enum.Enum):
    """Enumeration of all supported equation types."""
    LINEAR = "linear"
    QUADRATIC = "quadratic"
    CUBIC = "cubic"
    POLYNOMIAL = "polynomial"
    RATIONAL = "rational"
    TRIGONOMETRIC = "trigonometric"
    LOGARITHMIC = "logarithmic"
    EXPONENTIAL = "exponential"
    ABSOLUTE_VALUE = "absolute_value"
    SYSTEM = "system"
    GENERAL = "general"
    UNKNOWN = "unknown"

    @property
    def display_name(self) -> str:
        """Human-readable name for the equation type."""
        names = {
            EquationType.LINEAR: "Linear",
            EquationType.QUADRATIC: "Quadratic",
            EquationType.CUBIC: "Cubic",
            EquationType.POLYNOMIAL: "Polynomial",
            EquationType.RATIONAL: "Rational (Fractional)",
            EquationType.TRIGONOMETRIC: "Trigonometric",
            EquationType.LOGARITHMIC: "Logarithmic",
            EquationType.EXPONENTIAL: "Exponential",
            EquationType.ABSOLUTE_VALUE: "Absolute Value",
            EquationType.SYSTEM: "System of Equations",
            EquationType.GENERAL: "General",
            EquationType.UNKNOWN: "Unknown",
        }
        return names.get(self, "Unknown")


@dataclass
class Equation:
    """
    Parsed equation with full metadata.

    Attributes:
        raw_input: The original string input from the user.
        sympy_eq: The SymPy Eq object representing this equation.
        variables: List of Symbol objects that appear in the equation.
        primary_variable: The main variable being solved for.
        equation_type: The classified type of the equation.
        lhs: The left-hand side expression.
        rhs: The right-hand side expression.
        is_system: Whether this is part of a system of equations.
        system_index: Index of this equation within a system (0-based, -1 if not a system).
        has_fractions: Whether the equation contains rational/fractional expressions.
        has_abs: Whether the equation contains absolute value expressions.
        degree: Polynomial degree if applicable, None otherwise.
        latex: LaTeX representation of the full equation.
    """

    raw_input: str
    sympy_eq: Eq
    variables: List[Symbol]
    primary_variable: Optional[Symbol]
    equation_type: EquationType = EquationType.UNKNOWN
    lhs: Expr = field(default=None)
    rhs: Expr = field(default=None)
    is_system: bool = False
    system_index: int = -1
    has_fractions: bool = False
    has_abs: bool = False
    degree: Optional[int] = None
    latex: str = ""

    def __post_init__(self):
        """Derive computed fields after initialization."""
        if self.lhs is None:
            self.lhs = self.sympy_eq.lhs
        if self.rhs is None:
            self.rhs = self.sympy_eq.rhs
        if not self.latex:
            from sympy import latex as sympy_latex
            self.latex = f"{sympy_latex(self.lhs)} = {sympy_latex(self.rhs)}"

    @property
    def expression(self) -> Expr:
        """Return lhs - rhs as a single expression (standard form)."""
        return self.lhs - self.rhs

    @property
    def variable_names(self) -> List[str]:
        """Return string names of all variables."""
        return [str(v) for v in self.variables]

    @property
    def is_single_variable(self) -> bool:
        """True if the equation involves exactly one variable."""
        return len(self.variables) == 1

    @property
    def num_variables(self) -> int:
        """Number of distinct variables in the equation."""
        return len(self.variables)

    def with_type(self, eq_type: EquationType) -> "Equation":
        """Return a copy of this equation with an updated type."""
        return Equation(
            raw_input=self.raw_input,
            sympy_eq=self.sympy_eq,
            variables=self.variables,
            primary_variable=self.primary_variable,
            equation_type=eq_type,
            lhs=self.lhs,
            rhs=self.rhs,
            is_system=self.is_system,
            system_index=self.system_index,
            has_fractions=self.has_fractions,
            has_abs=self.has_abs,
            degree=self.degree,
            latex=self.latex,
        )

    def with_system_info(self, index: int) -> "Equation":
        """Return a copy of this equation with system metadata."""
        return Equation(
            raw_input=self.raw_input,
            sympy_eq=self.sympy_eq,
            variables=self.variables,
            primary_variable=self.primary_variable,
            equation_type=self.equation_type,
            lhs=self.lhs,
            rhs=self.rhs,
            is_system=True,
            system_index=index,
            has_fractions=self.has_fractions,
            has_abs=self.has_abs,
            degree=self.degree,
            latex=self.latex,
        )

    def __repr__(self) -> str:
        return (
            f"Equation(type={self.equation_type.value}, "
            f"vars={self.variable_names}, "
            f"eq={self.latex})"
        )
