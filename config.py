"""
Engine configuration constants.

Centralizes all configurable parameters for the solving engine,
including variable definitions, parsing rules, and numerical settings.
"""

from __future__ import annotations

from sympy import symbols, E, pi, I as SympyI

# ── Symbol definitions ────────────────────────────────────────────────────────

SUPPORTED_VARIABLES = list(symbols("x y z a b c t n u v w"))
VARIABLE_PRIORITY = ["x", "y", "z", "a", "b", "c", "t", "n", "u", "v", "w"]

# Constant symbols that should NOT be treated as variables
CONSTANT_NAMES = {"e", "E", "i", "I", "pi"}

# Mapping from string to SymPy symbol for parsing
SYMBOL_DICT = {str(s): s for s in SUPPORTED_VARIABLES}

# Constants available during parsing
CONSTANT_DICT = {
    "e": E,
    "E": E,
    "pi": pi,
    "i": SympyI,
    "I": SympyI,
}

# Combined local dict for parse_expr
PARSE_LOCAL_DICT = {**SYMBOL_DICT, **CONSTANT_DICT}

# ── Numerical solver settings ─────────────────────────────────────────────────

NUMERICAL_STARTING_POINTS = [-100, -50, -10, -5, -1, 0, 0.5, 1, 5, 10, 50, 100]
NUMERICAL_TOLERANCE = 1e-12
NUMERICAL_MAX_SOLUTIONS = 20
DUPLICATE_THRESHOLD = 1e-6

# ── Verification settings ─────────────────────────────────────────────────────

VERIFICATION_TOLERANCE = 1e-8
MAX_VERIFIED_SOLUTIONS = 3

# ── System solver settings ────────────────────────────────────────────────────

SYSTEM_MAX_EQUATIONS = 10
SYSTEM_SEPARATOR_PATTERN = r"[\n,;]+"

# ── Decimal formatting ────────────────────────────────────────────────────────

DECIMAL_PRECISION = 10
DECIMAL_DISPLAY_PRECISION = 6

# ── Server settings ───────────────────────────────────────────────────────────

DEFAULT_HOST = ""
DEFAULT_PORT = 8000

# ── Pipeline settings ─────────────────────────────────────────────────────────

ENABLE_FRACTION_CLEARING = True
ENABLE_FACTORIZATION_STEPS = True
ENABLE_COEFFICIENT_IDENTIFICATION = True
ENABLE_DISCRIMINANT_STEPS = True
ENABLE_BACK_SUBSTITUTION_STEPS = True
ENABLE_VERIFICATION_STEPS = True
