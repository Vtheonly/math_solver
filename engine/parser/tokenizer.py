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
    """

    # Pattern for splitting multiple equations
    SEPARATOR_PATTERN = re.compile(r"[\n,;]+")

    @staticmethod
    def is_latex(text: str) -> bool:
        """Detect if the input string is likely LaTeX."""
        if "\\" in text:
            return True
        latex_patterns = [
            r"^{", r"_{", r"\frac", r"\sqrt", r"\sin", r"\cos", r"\tan",
            r"\int", r"\sum", r"\left", r"\right"
        ]
        return any(p in text for p in latex_patterns)

    @staticmethod
    def normalize_latex(text: str) -> str:
        """Fix common OCR errors in LaTeX without breaking syntax."""
        # Remove spaces between digits (e.g., "1 0" -> "10")
        text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
        # Collapse multiple spaces into one
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def split_equations(raw_input: str) -> List[str]:
        parts = Tokenizer.SEPARATOR_PATTERN.split(raw_input)
        equations = [p.strip() for p in parts if p.strip()]
        logger.debug("Split input into %d equation(s): %s", len(equations), equations)
        return equations

    @staticmethod
    def normalize(raw_input: str) -> str:
        text = raw_input.strip()
        logger.debug("Tokenizing: '%s'", text)

        # Detect if it's LaTeX. If so, DO NOT convert ^ to ** 
        if "\\" in text or "_{" in text or "^{" in text:
            # Fix spacing errors from OCR (e.g., "1 0" -> "10")
            text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
            text = re.sub(r'\s+', ' ', text)
            logger.debug("Detected LaTeX. Safe normalized to: '%s'", text)
            return text

        # Standard plain-text normalization
        text = Tokenizer._convert_caret_to_power(text)
        text = Tokenizer._convert_natural_log(text)
        text = Tokenizer._normalize_absolute_value(text)
        text = Tokenizer._normalize_spacing(text)

        logger.debug("Normalized to: '%s'", text)
        return text

    @staticmethod
    def _convert_caret_to_power(text: str) -> str:
        result = text.replace("^", "**")
        if "^" in text:
            logger.debug("Converted ^ to **: '%s' → '%s'", text, result)
        return result

    @staticmethod
    def _convert_natural_log(text: str) -> str:
        return re.sub(r'\bln\s*\(', 'log(', text)

    @staticmethod
    def _normalize_absolute_value(text: str) -> str:
        result = []
        i = 0
        pipe_positions = []

        while i < len(text):
            if text[i] == '|':
                pipe_positions.append(i)
            i += 1

        if len(pipe_positions) >= 2 and len(pipe_positions) % 2 == 0:
            paired = [(pipe_positions[j], pipe_positions[j + 1])
                      for j in range(0, len(pipe_positions), 2)]
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
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    @staticmethod
    def validate_equation_string(text: str) -> Tuple[bool, str]:
        if not text or not text.strip():
            return False, "Empty input"

        text = text.strip()
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

        equals_count = text.count("=")
        if equals_count > 1:
            if "==" in text:
                return False, "Use single '=' for equations, not '==' for comparisons"
            logger.warning("Multiple '=' signs found, splitting on first one")

        if not re.search(r'[a-zA-Z]', text):
            logger.info("No alphabetic characters found in equation")

        return True, ""

    @staticmethod
    def split_on_equals(text: str) -> Tuple[str, str]:
        if "=" not in text:
            raw_lower = text.lower()
            if raw_lower.startswith(("plot", "graph", "draw")):
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
            logger.warning("Empty LHS, treating as 0 = %s", rhs)
            lhs = "0"

        if not rhs:
            logger.warning("Empty RHS, treating as %s = 0", lhs)
            rhs = "0"

        return lhs, rhs