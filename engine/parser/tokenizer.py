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
        """
        Fix common TAMER OCR errors in LaTeX without breaking syntax.

        The OCR model frequently produces:
        - Spaced-out letters inside \\operatorname{}, \\mathrm{}, \\text{}: "c o s" → "cos"
        - Spaced-out digits: "1 6" → "16"
        - "\\ell n" instead of "\\ln"
        - Stray trailing periods/commas on equations
        - Spaces before/after braces that break parsing
        """
        text = text.strip()

        # ── 1. Fix spaced-out letters inside \operatorname{...}, \mathrm{...}, \text{...} ──
        # e.g. \operatorname{c o s} → \operatorname{cos}
        def _collapse_spaces_in_braces(m):
            cmd = m.group(1)     # e.g. "\\operatorname"
            inner = m.group(2)   # e.g. "c o s"
            collapsed = inner.replace(' ', '')
            return f'{cmd}{{{collapsed}}}'

        text = re.sub(
            r'(\\(?:operatorname|mathrm|text|textit|textbf|mathbf|mathcal|mathbb))\{([^}]*)\}',
            _collapse_spaces_in_braces,
            text,
        )

        # ── 2. Fix spaced-out standalone function names (no \operatorname wrapper) ──
        # e.g. "l o g" → "log", "c o s" → "cos", "s i n" → "sin"
        known_funcs = [
            'sin', 'cos', 'tan', 'cot', 'sec', 'csc',
            'arcsin', 'arccos', 'arctan',
            'sinh', 'cosh', 'tanh', 'coth',
            'log', 'exp', 'det', 'dim', 'ker', 'deg',
            'max', 'min', 'sup', 'inf', 'lim',
            'gcd', 'hom', 'arg',
        ]
        for fn in known_funcs:
            # Build pattern like "l\s+o\s+g" for "log"
            spaced = r'\s+'.join(re.escape(c) for c in fn)
            # Only match when not already preceded by a backslash (avoid double-fixing \log)
            text = re.sub(
                r'(?<!\\)(?<![a-zA-Z])' + spaced + r'(?![a-zA-Z])',
                fn,
                text,
            )

        # ── 3. Fix "\ell n" → "\ln"  (common TAMER misparse) ──
        text = re.sub(r'\\ell\s*n\b', r'\\ln', text)

        # ── 4. Remove spaces between digits: "1 6" → "16", "2 7" → "27" ──
        text = re.sub(r'(?<=\d)\s+(?=\d)', '', text)

        # ── 5. Fix spaces around decimal points: "0 . 2" → "0.2" ──
        text = re.sub(r'(\d)\s*\.\s*(\d)', r'\1.\2', text)

        # ── 6. Remove stray trailing period/comma (not inside braces) ──
        text = re.sub(r'[.,]\s*$', '', text)

        # ── 7. Fix unbalanced braces (OCR often produces extra } at end) ──
        text = Tokenizer._balance_braces(text)

        # ── 8. Fix invalid \cdot right after ^{ (OCR misread of - sign) ──
        text = re.sub(r'\^\{\s*\\cdot\s*', r'^{-', text)

        # ── 9. Collapse multiple spaces into one ──
        text = re.sub(r'\s+', ' ', text)

        logger.debug("Normalized LaTeX: '%s'", text)
        return text.strip()

    @staticmethod
    def _balance_braces(text: str) -> str:
        """Fix unbalanced { } braces from OCR output."""
        opens = text.count('{')
        closes = text.count('}')
        if closes > opens:
            # Remove extra closing braces from the end
            diff = closes - opens
            # Walk backwards and remove the outermost extra '}'
            result = list(text)
            i = len(result) - 1
            while diff > 0 and i >= 0:
                if result[i] == '}':
                    # Check if this brace is truly unmatched
                    # by scanning from here to the end
                    depth = 0
                    for j in range(i, -1, -1):
                        if result[j] == '}':
                            depth += 1
                        elif result[j] == '{':
                            depth -= 1
                    if depth > 0:  # more } than { from start to here
                        result[i] = ''
                        diff -= 1
                i -= 1
            text = ''.join(result)
        elif opens > closes:
            text += '}' * (opens - closes)
        return text

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
    def _find_toplevel_equals(text: str) -> List[int]:
        """Find positions of '=' that are NOT inside {} braces."""
        depth = 0
        positions = []
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth = max(0, depth - 1)
            elif ch == '=' and depth == 0:
                positions.append(i)
        return positions

    @staticmethod
    def validate_equation_string(text: str) -> Tuple[bool, str]:
        if not text or not text.strip():
            return False, "Empty input"

        text = text.strip()

        # Use brace-aware equals detection for LaTeX
        if Tokenizer.is_latex(text):
            toplevel_eq = Tokenizer._find_toplevel_equals(text)
            has_equals = len(toplevel_eq) > 0
        else:
            has_equals = "=" in text

        if not has_equals:
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

        if has_equals:
            if "==" in text:
                return False, "Use single '=' for equations, not '==' for comparisons"
            if Tokenizer.is_latex(text):
                eq_count = len(Tokenizer._find_toplevel_equals(text))
            else:
                eq_count = text.count("=")
            if eq_count > 1:
                logger.warning("Multiple top-level '=' signs found (%d), will use first one", eq_count)

        if not re.search(r'[a-zA-Z]', text):
            logger.info("No alphabetic characters found in equation")

        return True, ""

    @staticmethod
    def split_on_equals(text: str) -> Tuple[str, str]:
        """
        Split on the main '=' sign.

        For LaTeX, this is brace-aware: it only splits on '=' that is
        NOT inside {} braces.  This prevents splitting on subscript
        equals like \\sum_{j = 1}.

        For chained equalities like 'w = expr1 = expr2', only the
        first top-level '=' is used (LHS = 'w', RHS = 'expr1').
        """
        # Check for top-level equals
        if Tokenizer.is_latex(text):
            eq_positions = Tokenizer._find_toplevel_equals(text)
        else:
            eq_positions = [i for i, ch in enumerate(text) if ch == '=']

        if not eq_positions:
            # No equals sign — treat as expression = 0
            raw_lower = text.lower()
            if raw_lower.startswith(("plot", "graph", "draw")):
                pattern = re.compile(r'^(plot|graph|draw)\s+', re.IGNORECASE)
                stripped_cmd = pattern.sub('', text)
                return stripped_cmd, "0"
            return text, "0"

        # Split on the first top-level '='
        pos = eq_positions[0]
        lhs = text[:pos].strip()

        if len(eq_positions) >= 2:
            # Chained equality: "w = expr1 = expr2"
            # Take only up to the second '=' as the RHS
            second_eq = eq_positions[1]
            rhs = text[pos + 1:second_eq].strip()
            logger.info(
                "Chained equality detected (%d '=' signs). "
                "Using first equation only: '%s = %s'",
                len(eq_positions), lhs, rhs,
            )
        else:
            rhs = text[pos + 1:].strip()

        if not lhs and not rhs:
            raise ValueError("Both sides of equation are empty")

        if not lhs:
            logger.warning("Empty LHS, treating as 0 = %s", rhs)
            lhs = "0"

        if not rhs:
            logger.warning("Empty RHS, treating as %s = 0", lhs)
            rhs = "0"

        return lhs, rhs