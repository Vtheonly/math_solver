"""
Variable detector for the equation solving engine.

Identifies which variables appear in an equation string or SymPy
expression, applying priority rules and filtering out constants.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set

from sympy import Symbol, symbols, Expr, Eq, Add

from config import VARIABLE_PRIORITY, CONSTANT_NAMES, SUPPORTED_VARIABLES, SYMBOL_DICT
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class VariableDetector:
    """
    Detects and prioritizes variables in equation strings and expressions.

    Uses a priority ordering (x > y > z > a > b > c > t > n > u > v > w)
    to select the primary variable when multiple candidates exist.
    Filters out known constants (e, pi, i/I) and function names.
    """

    # Common mathematical function names that should not be treated as variables
    FUNCTION_NAMES = {
        "sin", "cos", "tan", "cot", "sec", "csc",
        "asin", "acos", "atan", "atan2",
        "sinh", "cosh", "tanh",
        "log", "ln", "exp", "sqrt",
        "Abs", "abs", "sign", "floor", "ceil",
        "factorial", "gamma",
    }

    @staticmethod
    def detect_from_string(text: str) -> List[Symbol]:
        """
        Detect variables from a raw equation string.

        Scans for single-letter identifiers and filters out constants
        and function names. Returns variables in priority order.

        Args:
            text: Raw equation string.

        Returns:
            List of Symbol objects, ordered by priority.
        """
        # Find all single-letter identifiers
        letters = set(re.findall(r'\b([a-zA-Z])\b', text))

        # Remove constants and function names
        letters -= CONSTANT_NAMES
        letters -= VariableDetector.FUNCTION_NAMES

        if not letters:
            logger.debug("No variables detected in string: '%s'", text[:80])
            return []

        # Sort by priority
        sorted_vars = VariableDetector._sort_by_priority(letters)

        logger.debug("Detected variables from string: %s → %s", letters, sorted_vars)
        return sorted_vars

    @staticmethod
    def detect_from_expression(expr: Expr) -> List[Symbol]:
        """
        Detect variables from a SymPy expression.

        Uses SymPy's free_symbols to find all symbols, then
        orders them by the engine's priority.

        Args:
            expr: A SymPy expression.

        Returns:
            List of Symbol objects, ordered by priority.
        """
        free_syms = expr.free_symbols

        if not free_syms:
            return []

        # Filter to only single-character symbols (our supported variables)
        filtered = {s for s in free_syms if str(s) in SYMBOL_DICT}

        if not filtered:
            # If no recognized single-char symbols, use whatever we found
            filtered = free_syms

        sorted_vars = VariableDetector._sort_by_priority_symbols(filtered)
        logger.debug("Detected variables from expression: %s", sorted_vars)
        return sorted_vars

    @staticmethod
    def detect_from_equation(eq: Eq) -> List[Symbol]:
        """
        Detect variables from a SymPy Eq object.

        Combines variables from both sides of the equation.

        Args:
            eq: A SymPy equation.

        Returns:
            List of Symbol objects, ordered by priority.
        """
        lhs_vars = VariableDetector.detect_from_expression(eq.lhs)
        rhs_vars = VariableDetector.detect_from_expression(eq.rhs)

        # Merge preserving priority
        seen = set()
        merged = []
        for v in lhs_vars + rhs_vars:
            if v not in seen:
                seen.add(v)
                merged.append(v)

        return merged

    @staticmethod
    def select_primary(variables: List[Symbol]) -> Optional[Symbol]:
        """
        Select the primary variable from a list of candidates.

        Uses the configured priority ordering. If no priority match,
        returns the first variable.

        Args:
            variables: List of candidate Symbol objects.

        Returns:
            The primary Symbol, or None if the list is empty.
        """
        if not variables:
            return None

        var_names = {str(v) for v in variables}

        for priority_name in VARIABLE_PRIORITY:
            if priority_name in var_names:
                for v in variables:
                    if str(v) == priority_name:
                        logger.debug("Selected primary variable: %s", v)
                        return v

        # Fallback: first variable
        primary = variables[0]
        logger.debug("Selected primary variable (fallback): %s", primary)
        return primary

    @staticmethod
    def _sort_by_priority(letter_set: Set[str]) -> List[Symbol]:
        """Sort a set of letter strings by the configured priority."""
        result = []
        for name in VARIABLE_PRIORITY:
            if name in letter_set:
                result.append(symbols(name))
                letter_set.discard(name)
        # Append any remaining letters alphabetically
        for name in sorted(letter_set):
            result.append(symbols(name))
        return result

    @staticmethod
    def _sort_by_priority_symbols(symbol_set: Set[Symbol]) -> List[Symbol]:
        """Sort a set of Symbol objects by the configured priority."""
        name_map = {str(s): s for s in symbol_set}
        result = []
        for name in VARIABLE_PRIORITY:
            if name in name_map:
                result.append(name_map[name])
                del name_map[name]
        for name in sorted(name_map.keys()):
            result.append(name_map[name])
        return result
