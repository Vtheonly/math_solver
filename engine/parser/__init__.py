"""
Parser subsystem for the equation solving engine.

Handles tokenization, variable detection, and equation parsing
from raw user input strings into structured Equation objects.
"""

from engine.parser.tokenizer import Tokenizer
from engine.parser.variable_detector import VariableDetector
from engine.parser.equation_parser import EquationParser

__all__ = [
    "Tokenizer",
    "VariableDetector",
    "EquationParser",
]
