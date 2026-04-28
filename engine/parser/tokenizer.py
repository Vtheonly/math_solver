"""
Tokenizer for the equation solving engine.

Preprocesses raw input strings into clean, normalized forms
suitable for SymPy parsing. Handles common input patterns,
operator conversions, and structural normalization.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from engine.utils.logger import get_logger

logger = get_logger(__name__)


class Tokenizer:
    """
    Preprocesses and normalizes equation input strings.

    Handles:
    - Caret to power conversion (^  → **)
    - Natural log mapping (ln → log)
    - Implicit multiplication hints
    - Whitespace normalization
    - Multiple equation splitting
    - Absolute value notation normalization
    """

    # Pattern for splitting multiple equations
    SEPARATOR_PATTERN = re.compile(r"[\n,;]+")

    @staticmethod
    def split_equations(raw_input: str) -> List[str]:
        """
        Split a raw input string into individual equation strings.

        Supports newlines, commas, and semicolons as separators.

        Args:
            raw_input: The raw user input.

        Returns:
            List of stripped, non-empty equation strings.
        """
        parts = Tokenizer.SEPARATOR_PATTERN.split(raw_input)
        equations = [p.strip() for p in parts if p.strip()]
        logger.debug("Split input into %d equation(s): %s", len(equations), equations)
        return equations

    @staticmethod
    def normalize(raw_input: str) -> str:
        """
        Normalize a single equation string for SymPy parsing.

        Performs the following transformations:
        1. Strip whitespace
        2. Convert ^ to ** (power notation)
        3. Convert ln( to log( (natural log)
        4. Normalize absolute value notation |expr| → Abs(expr)
        5. Normalize spaces around operators

        Args:
            raw_input: A single equation string.

        Returns:
            The normalized equation string.
        """
        text = raw_input.strip()
        logger.debug("Tokenizing: '%s'", text)

        # Step 1: Convert caret to power
        text = Tokenizer._convert_caret_to_power(text)

        # Step 2: Convert natural log
        text = Tokenizer._convert_natural_log(text)

        # Step 3: Normalize absolute value
        text = Tokenizer._normalize_absolute_value(text)

        # Step 4: Normalize spacing
        text = Tokenizer._normalize_spacing(text)

        logger.debug("Normalized to: '%s'", text)
        return text

    @staticmethod
    def _convert_caret_to_power(text: str) -> str:
        """Convert ^ operator to ** for SymPy."""
        result = text.replace("^", "**")
        if "^" in text:
            logger.debug("Converted ^ to **: '%s' → '%s'", text, result)
        return result

    @staticmethod
    def _convert_natural_log(text: str) -> str:
        """Convert ln() to log() for SymPy (SymPy uses log for natural log)."""
        result = re.sub(r'\bln\s*\(', 'log(', text)
        return result

    @staticmethod
    def _normalize_absolute_value(text: str) -> str:
        """
        Convert |expr| notation to Abs(expr).

        Handles both simple and nested absolute value expressions.
        This is a heuristic approach — complex nested cases may need
        the user to use Abs() directly.
        """
        # Match |...| patterns, being careful with nested pipes
        # Simple approach: find matching pipe pairs
        result = []
        i = 0
        pipe_positions = []

        while i < len(text):
            if text[i] == '|':
                pipe_positions.append(i)
            i += 1

        # If we have an even number of pipes, pair them up
        if len(pipe_positions) >= 2 and len(pipe_positions) % 2 == 0:
            # Replace from right to left to preserve positions
            paired = [(pipe_positions[j], pipe_positions[j + 1])
                      for j in range(0, len(pipe_positions), 2)]

            # Build result string
            result = list(text)
            for open_pos, close_pos in reversed(paired):
                inner = text[open_pos + 1:close_pos].strip()
                replacement = f"Abs({inner})"
                for k in range(open_pos, close_pos + 1):
                    result[k] = ''
                result[open_pos] = replacement

            return ''.join(result)

        return text

    @staticmethod
    def _normalize_spacing(text: str) -> str:
        """Normalize whitespace without changing semantics."""
        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def validate_equation_string(text: str) -> Tuple[bool, str]:
        """
        Validate that a string looks like a valid equation.

        Args:
            text: The equation string to validate.

        Returns:
            Tuple of (is_valid, error_message). If valid, error_message is empty.
        """
        if not text or not text.strip():
            return False, "Empty input"

        text = text.strip()

        # Check for graphing or matrix exceptions
        if "=" not in text:
            raw_lower = text.lower()
            if raw_lower.startswith(("plot", "graph", "draw")):
                pass
            elif "circle" in raw_lower or "sine wave" in raw_lower or "animation" in raw_lower:
                pass
            elif "[" in text and "]" in text:
                pass
            elif bool(re.search(r'[a-zA-Z]', text)):
                pass
            else:
                return False, "Input must contain an '=' sign to be an equation"

        # Must not have multiple equals signs (unless it's a==b which we don't handle)
        equals_count = text.count("=")
        if equals_count > 1:
            # Check for == which might be a comparison
            if "==" in text:
                return False, "Use single '=' for equations, not '==' for comparisons"
            # Multiple = could be a chained equation like a=b=c, split on first
            logger.warning("Multiple '=' signs found, splitting on first one")

        # Must have at least one alphabetic character (variable or function)
        if not re.search(r'[a-zA-Z]', text):
            # Could be purely numeric, which is fine but trivial
            logger.info("No alphabetic characters found in equation")

        return True, ""

    @staticmethod
    def split_on_equals(text: str) -> Tuple[str, str]:
        """
        Split an equation string on the first equals sign.

        Args:
            text: Equation string like "x^2 + 1 = 5"

        Returns:
            Tuple of (lhs_string, rhs_string)

        Raises:
            ValueError: If no equals sign is found.
        """
        if "=" not in text:
            raw_lower = text.lower()
            if raw_lower.startswith(("plot", "graph", "draw")):
                import re
                pattern = re.compile(r'^(plot|graph|draw)\s+', re.IGNORECASE)
                stripped_cmd = pattern.sub('', text)
                return stripped_cmd, "0"
            return text, "0"

        parts = text.split("=", 1)
        lhs = parts[0].strip()
        rhs = parts[1].strip()

        if not lhs and not rhs:
            raise ValueError("Both sides of equation are empty")

        if not lhs:
            rhs_expr = rhs
            # Could be like "= 5" which means "0 = 5"
            logger.warning("Empty LHS, treating as 0 = %s", rhs)
            lhs = "0"

        if not rhs:
            # Like "x + 1 =" which means "x + 1 = 0"
            logger.warning("Empty RHS, treating as %s = 0", lhs)
            rhs = "0"

        return lhs, rhs
