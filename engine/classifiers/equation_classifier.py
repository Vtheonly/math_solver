"""
Equation classifier for the equation solving engine.

Analyzes parsed Equation objects to determine their type,
which then drives strategy selection in the solving pipeline.
The classifier uses a rule-based approach with explicit priority
ordering to handle equations that could match multiple types.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sympy import (
    Abs, Poly, degree, sin, cos, tan, cot, sec, csc,
    log, exp, Rational, Symbol, Eq, expand,
)

from engine.models.equation import Equation, EquationType
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class ClassificationRule:
    """
    A single classification rule.

    Each rule has a name, a check function, and an equation type.
    Rules are evaluated in priority order; the first matching rule wins.
    """

    def __init__(self, name: str, check_fn, eq_type: EquationType, priority: int = 0):
        self.name = name
        self.check_fn = check_fn
        self.eq_type = eq_type
        self.priority = priority

    def check(self, equation: Equation) -> bool:
        """Evaluate this rule against an equation."""
        try:
            return self.check_fn(equation)
        except Exception as e:
            logger.debug("Rule '%s' check failed: %s", self.name, e)
            return False


class EquationClassifier:
    """
    Classifies equations into types using a priority-based rule system.

    The classification pipeline:
    1. Check for system (multiple equations)
    2. Check for absolute value
    3. Check for trigonometric functions
    4. Check for logarithmic/exponential functions
    5. Check for rational (fractional) expressions
    6. Determine polynomial degree (linear, quadratic, cubic, etc.)
    7. Default to GENERAL

    Rules are evaluated in priority order. Higher priority values
    are checked first. The first matching rule determines the type.
    """

    def __init__(self):
        """Initialize the classifier with built-in rules."""
        self.rules: List[ClassificationRule] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register the standard classification rules."""
        # System detection (highest priority — handled externally)
        self.add_rule(ClassificationRule(
            name="system",
            check_fn=self._check_system,
            eq_type=EquationType.SYSTEM,
            priority=100,
        ))

        # Absolute value
        self.add_rule(ClassificationRule(
            name="absolute_value",
            check_fn=self._check_absolute_value,
            eq_type=EquationType.ABSOLUTE_VALUE,
            priority=90,
        ))

        # Trigonometric
        self.add_rule(ClassificationRule(
            name="trigonometric",
            check_fn=self._check_trigonometric,
            eq_type=EquationType.TRIGONOMETRIC,
            priority=80,
        ))

        # Logarithmic
        self.add_rule(ClassificationRule(
            name="logarithmic",
            check_fn=self._check_logarithmic,
            eq_type=EquationType.LOGARITHMIC,
            priority=70,
        ))

        # Exponential
        self.add_rule(ClassificationRule(
            name="exponential",
            check_fn=self._check_exponential,
            eq_type=EquationType.EXPONENTIAL,
            priority=65,
        ))

        # Rational (fractions with variable in denominator)
        self.add_rule(ClassificationRule(
            name="rational",
            check_fn=self._check_rational,
            eq_type=EquationType.RATIONAL,
            priority=60,
        ))

        # Linear (degree 1)
        self.add_rule(ClassificationRule(
            name="linear",
            check_fn=lambda eq: self._check_polynomial_degree(eq, 1),
            eq_type=EquationType.LINEAR,
            priority=50,
        ))

        # Quadratic (degree 2)
        self.add_rule(ClassificationRule(
            name="quadratic",
            check_fn=lambda eq: self._check_polynomial_degree(eq, 2),
            eq_type=EquationType.QUADRATIC,
            priority=40,
        ))

        # Cubic (degree 3)
        self.add_rule(ClassificationRule(
            name="cubic",
            check_fn=lambda eq: self._check_polynomial_degree(eq, 3),
            eq_type=EquationType.CUBIC,
            priority=30,
        ))

        # Higher-degree polynomial
        self.add_rule(ClassificationRule(
            name="polynomial",
            check_fn=self._check_polynomial,
            eq_type=EquationType.POLYNOMIAL,
            priority=20,
        ))

    def add_rule(self, rule: ClassificationRule):
        """Add a classification rule, maintaining priority order."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug("Registered classification rule: %s (priority %d)", rule.name, rule.priority)

    def classify(self, equation: Equation) -> Equation:
        """
        Classify an equation and return it with its type set.

        Args:
            equation: An Equation object (type may be UNKNOWN).

        Returns:
            The same Equation with equation_type updated.
        """
        logger.info("Classifying equation: %s", equation)

        for rule in self.rules:
            if rule.check(equation):
                logger.info(
                    "Classification rule '%s' matched → %s",
                    rule.name,
                    rule.eq_type.value,
                )
                classified = equation.with_type(rule.eq_type)

                # Also compute degree for polynomials
                if rule.eq_type in (
                    EquationType.LINEAR,
                    EquationType.QUADRATIC,
                    EquationType.CUBIC,
                    EquationType.POLYNOMIAL,
                ):
                    classified.degree = self._compute_degree(equation)

                return classified

        logger.info("No classification rule matched, defaulting to GENERAL")
        return equation.with_type(EquationType.GENERAL)

    def classify_system(self, equations: List[Equation]) -> List[Equation]:
        """
        Classify each equation in a system.

        Args:
            equations: List of Equation objects.

        Returns:
            List of classified Equation objects.
        """
        return [self.classify(eq) for eq in equations]

    # ── Rule check methods ─────────────────────────────────────────────────

    @staticmethod
    def _check_system(equation: Equation) -> bool:
        """Check if this is part of a system of equations."""
        return equation.is_system and equation.num_variables > 1

    @staticmethod
    def _check_absolute_value(equation: Equation) -> bool:
        """Check if the equation contains absolute value expressions."""
        return equation.has_abs or equation.expression.has(Abs)

    @staticmethod
    def _check_trigonometric(equation: Equation) -> bool:
        """Check if the equation contains trigonometric functions."""
        expr = equation.expression
        return expr.has(sin, cos, tan, cot, sec, csc)

    @staticmethod
    def _check_logarithmic(equation: Equation) -> bool:
        """Check if the equation contains logarithmic functions."""
        expr = equation.expression
        return expr.has(log) and not expr.has(exp)

    @staticmethod
    def _check_exponential(equation: Equation) -> bool:
        """
        Check if the equation contains exponential expressions.

        Catches both exp(x) and Pow(base, variable) like 2^x.
        """
        from sympy import Pow
        expr = equation.expression
        if expr.has(exp):
            return True
        # Check for a^x patterns (Pow with variable in exponent)
        if equation.primary_variable:
            var = equation.primary_variable
            for sub in expr.find(Pow):
                if var in sub.exp.free_symbols:
                    return True
            # Also check both sides of the equation directly
            for side in (equation.lhs, equation.rhs):
                for sub in side.find(Pow):
                    if var in sub.exp.free_symbols:
                        return True
        return False

    @staticmethod
    def _check_rational(equation: Equation) -> bool:
        """
        Check if the equation is a rational equation.

        A rational equation has a variable in the denominator.
        Simple polynomial equations are NOT classified as rational
        even though they technically have denominator 1.
        """
        if not equation.primary_variable:
            return False

        var = equation.primary_variable
        expr = equation.expression

        try:
            numer, denom = expr.as_numer_denom()
            # Variable appears in denominator
            if var in denom.free_symbols:
                return True
        except Exception:
            pass

        return False

    @staticmethod
    def _check_polynomial_degree(equation: Equation, target_degree: int) -> bool:
        """Check if the equation is a polynomial of a specific degree."""
        deg = EquationClassifier._compute_degree(equation)
        return deg == target_degree

    @staticmethod
    def _check_polynomial(equation: Equation) -> bool:
        """Check if the equation is a polynomial of degree >= 4."""
        deg = EquationClassifier._compute_degree(equation)
        return deg is not None and deg >= 4

    @staticmethod
    def _compute_degree(equation: Equation) -> Optional[int]:
        """
        Compute the polynomial degree of the equation.

        Returns None if the equation is not a polynomial in the primary variable.
        """
        if not equation.primary_variable:
            return None

        var = equation.primary_variable
        expr = expand(equation.expression)

        try:
            p = Poly(expr, var)
            return p.degree()
        except Exception:
            return None
