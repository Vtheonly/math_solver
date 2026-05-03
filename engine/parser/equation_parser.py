"""
Equation parser for the equation solving engine.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from sympy import Eq, Expr, parse_expr, sympify, Add
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

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


class ParseError(Exception):
    def __init__(self, message: str, raw_input: str = ""):
        self.raw_input = raw_input
        super().__init__(f"Parse error: {message}")


class EquationParser:

    @staticmethod
    def parse(raw_input: str) -> Equation:
        logger.info("Parsing equation: '%s'", raw_input)

        # Step 1: Validate
        is_valid, error = Tokenizer.validate_equation_string(raw_input)
        if not is_valid:
            logger.error("Validation failed: %s", error)
            raise ParseError(error, raw_input)

        is_latex = Tokenizer.is_latex(raw_input)

        # Step 2: Normalize
        if is_latex:
            normalized = Tokenizer.normalize_latex(raw_input)
            logger.debug("Detected LaTeX. Normalized to: '%s'", normalized)
        else:
            normalized = Tokenizer.normalize(raw_input)
            
        normalized = MatrixOperations.preprocess_matrix_syntax(normalized)

        # Step 3: Split on equals
        try:
            lhs_str, rhs_str = Tokenizer.split_on_equals(normalized)
        except ValueError as e:
            raise ParseError(str(e), raw_input)

        logger.debug("LHS string: '%s', RHS string: '%s'", lhs_str, rhs_str)

        # Step 4: Parse with SymPy or latex2sympy
        if is_latex:
            try:
                from latex2sympy2 import latex2sympy
                lhs = latex2sympy(lhs_str) if lhs_str and lhs_str != "0" else sympify(0)
                rhs = latex2sympy(rhs_str) if rhs_str and rhs_str != "0" else sympify(0)
            except ImportError:
                logger.error("latex2sympy2 is not installed!")
                raise ParseError("LaTeX parsing requires the latex2sympy2 package.", raw_input)
            except Exception as e:
                logger.error("Failed to parse LaTeX: %s", e)
                # Fallback to basic sympy parsing if it failed
                try:
                    lhs = parse_expr(lhs_str.replace('\\', ''), local_dict=PARSE_LOCAL_DICT, transformations=TRANSFORMATIONS)
                    rhs = parse_expr(rhs_str.replace('\\', ''), local_dict=PARSE_LOCAL_DICT, transformations=TRANSFORMATIONS)
                except Exception as e2:
                    raise ParseError(f"Cannot parse LaTeX: {e}", raw_input)
        else:
            try:
                lhs = parse_expr(lhs_str, local_dict=PARSE_LOCAL_DICT, transformations=TRANSFORMATIONS)
            except Exception as e:
                logger.error("Failed to parse LHS '%s': %s", lhs_str, e)
                raise ParseError(f"Cannot parse left side '{lhs_str}': {e}", raw_input)

            try:
                rhs = parse_expr(rhs_str, local_dict=PARSE_LOCAL_DICT, transformations=TRANSFORMATIONS)
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
        from sympy import Abs
        return eq.lhs.has(Abs) or eq.rhs.has(Abs)