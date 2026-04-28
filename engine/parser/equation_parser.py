"""
Equation parser for the equation solving engine.

Converts raw user input strings into structured Equation objects
by tokenizing, parsing with SymPy, detecting variables, and
assembling the full Equation model.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sympy import Eq, Expr, parse_expr, sympify
from sympy.parsing.sympy_parser import (
    standard_transformations,
    implicit_multiplication_application,
)

from config import PARSE_LOCAL_DICT, ENABLE_FRACTION_CLEARING
from engine.models.equation import Equation, EquationType
from engine.parser.tokenizer import Tokenizer
from engine.parser.variable_detector import VariableDetector
from engine.matrices.operations import MatrixOperations
from engine.utils.logger import get_logger
from engine.utils.latex_formatter import LatexFormatter

logger = get_logger(__name__)

# SymPy parsing transformations
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


class ParseError(Exception):
    """Raised when an equation cannot be parsed."""

    def __init__(self, message: str, raw_input: str = ""):
        self.raw_input = raw_input
        super().__init__(f"Parse error: {message}")


class EquationParser:
    """
    Parses raw equation strings into Equation model objects.

    The parsing pipeline:
    1. Validate input structure
    2. Normalize (caret → power, ln → log, |x| → Abs(x))
    3. Split on equals sign
    4. Parse both sides with SymPy
    5. Detect variables
    6. Assemble Equation object with metadata
    """

    @staticmethod
    def parse(raw_input: str) -> Equation:
        """
        Parse a single equation string into an Equation object.

        Args:
            raw_input: Raw equation string from the user.

        Returns:
            A fully populated Equation object.

        Raises:
            ParseError: If the input cannot be parsed.
        """
        logger.info("Parsing equation: '%s'", raw_input)

        # Step 1: Validate
        is_valid, error = Tokenizer.validate_equation_string(raw_input)
        if not is_valid:
            logger.error("Validation failed: %s", error)
            raise ParseError(error, raw_input)

        # Step 2: Normalize
        normalized = Tokenizer.normalize(raw_input)
        normalized = MatrixOperations.preprocess_matrix_syntax(normalized)

        # Step 3: Split on equals
        try:
            lhs_str, rhs_str = Tokenizer.split_on_equals(normalized)
        except ValueError as e:
            raise ParseError(str(e), raw_input)

        logger.debug("LHS string: '%s', RHS string: '%s'", lhs_str, rhs_str)

        # Step 4: Parse with SymPy
        try:
            lhs = parse_expr(
                lhs_str,
                local_dict=PARSE_LOCAL_DICT,
                transformations=TRANSFORMATIONS,
            )
        except Exception as e:
            logger.error("Failed to parse LHS '%s': %s", lhs_str, e)
            raise ParseError(f"Cannot parse left side '{lhs_str}': {e}", raw_input)

        try:
            rhs = parse_expr(
                rhs_str,
                local_dict=PARSE_LOCAL_DICT,
                transformations=TRANSFORMATIONS,
            )
        except Exception as e:
            logger.error("Failed to parse RHS '%s': %s", rhs_str, e)
            raise ParseError(f"Cannot parse right side '{rhs_str}': {e}", raw_input)

        # Step 5: Build SymPy equation
        sympy_eq = Eq(lhs, rhs)

        # Step 6: Detect variables
        variables = VariableDetector.detect_from_equation(sympy_eq)
        primary = VariableDetector.select_primary(variables)

        # Step 7: Detect structural features
        has_fractions = EquationParser._detect_fractions(sympy_eq)
        has_abs = EquationParser._detect_absolute_value(sympy_eq)

        # Step 8: Build Equation model
        equation = Equation(
            raw_input=raw_input,
            sympy_eq=sympy_eq,
            variables=variables,
            primary_variable=primary,
            lhs=lhs,
            rhs=rhs,
            has_fractions=has_fractions,
            has_abs=has_abs,
            latex=LatexFormatter.sympy_eq(sympy_eq),
        )

        logger.info("Parsed successfully: %s", equation)
        return equation

    @staticmethod
    def parse_system(raw_input: str) -> List[Equation]:
        """
        Parse a multi-equation input into a list of Equation objects.

        Splits the input on newlines, commas, or semicolons,
        then parses each equation individually and assigns
        system metadata.

        Args:
            raw_input: Raw multi-equation string.

        Returns:
            List of Equation objects with system metadata.

        Raises:
            ParseError: If any equation cannot be parsed.
        """
        equation_strings = Tokenizer.split_equations(raw_input)

        if not equation_strings:
            raise ParseError("No equations found in input", raw_input)

        logger.info("Parsing system of %d equation(s)", len(equation_strings))

        equations = []
        for i, eq_str in enumerate(equation_strings):
            try:
                eq = EquationParser.parse(eq_str)
                eq = eq.with_system_info(index=i)
                equations.append(eq)
                logger.info("Parsed equation %d: %s", i + 1, eq)
            except ParseError as e:
                logger.error("Failed to parse equation %d: %s", i + 1, e)
                raise ParseError(f"Equation {i + 1}: {e}", raw_input)

        return equations

    @staticmethod
    def _detect_fractions(eq: Eq) -> bool:
        """
        Detect whether an equation contains rational/fractional expressions.

        Checks if any term has a denominator that isn't 1.
        """
        try:
            for side in (eq.lhs, eq.rhs):
                terms = Add.make_args(side)
                for term in terms:
                    numer, denom = term.as_numer_denom()
                    if denom != 1:
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def _detect_absolute_value(eq: Eq) -> bool:
        """Detect whether an equation contains absolute value expressions."""
        from sympy import Abs
        return eq.lhs.has(Abs) or eq.rhs.has(Abs)
