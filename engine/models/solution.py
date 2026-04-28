"""
Solution data model.

Represents a single solution to an equation, including its exact symbolic
form, decimal approximation, and verification status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sympy import latex as sympy_latex, simplify, Float


@dataclass
class Solution:
    """
    A single solution to an equation.

    Attributes:
        variable_name: The name of the variable (e.g., 'x', 'y').
        exact_value: The exact symbolic value as a SymPy expression.
        exact_latex: LaTeX representation of the exact value.
        decimal_value: Decimal approximation as a string, or None if not real.
        is_numerical: Whether this solution was obtained numerically.
        is_verified: Whether the solution has been verified by substitution.
        verification_error: Numerical error from verification, if computed.
        sympy_repr: String representation of the SymPy expression.
    """

    variable_name: str
    exact_value: object  # SymPy expression
    exact_latex: str = ""
    decimal_value: Optional[str] = None
    is_numerical: bool = False
    is_verified: bool = False
    verification_error: Optional[float] = None
    sympy_repr: str = ""

    def __post_init__(self):
        """Compute derived fields after initialization."""
        if not self.exact_latex:
            try:
                self.exact_latex = sympy_latex(simplify(self.exact_value))
            except Exception:
                self.exact_latex = str(self.exact_value)

        if not self.sympy_repr:
            self.sympy_repr = str(self.exact_value)

        if self.decimal_value is None:
            self.decimal_value = self._compute_decimal()

    def _compute_decimal(self) -> Optional[str]:
        """Attempt to compute a decimal approximation."""
        try:
            val = self.exact_value.evalf()
            if val.is_real:
                f = float(val)
                return str(round(f, 10))
            return None
        except Exception:
            return None

    @property
    def decimal_float(self) -> Optional[float]:
        """Return the decimal value as a float, or None."""
        if self.decimal_value is not None:
            try:
                return float(self.decimal_value)
            except (ValueError, TypeError):
                return None
        return None

    def mark_verified(self, error: float = 0.0):
        """Mark this solution as verified with an optional error value."""
        self.is_verified = True
        self.verification_error = error

    def to_dict(self) -> dict:
        """Serialize to a dictionary for JSON response."""
        result = {
            "variable": self.variable_name,
            "exact": self.exact_latex,
            "sympy": self.sympy_repr,
        }
        if self.decimal_value is not None:
            result["decimal"] = self.decimal_value
        if self.is_numerical:
            result["numerical"] = True
        if self.is_verified:
            result["verified"] = True
        if self.verification_error is not None:
            result["verification_error"] = self.verification_error
        return result

    def __repr__(self) -> str:
        verified_mark = "✓" if self.is_verified else "?"
        return (
            f"Solution({self.variable_name} = {self.exact_latex} "
            f"[{self.decimal_value}] {verified_mark})"
        )
