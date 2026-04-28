"""
Classifier subsystem for the equation solving engine.

Determines the type of an equation (linear, quadratic, trigonometric, etc.)
to select the appropriate solving strategy.
"""

from engine.classifiers.equation_classifier import EquationClassifier

__all__ = ["EquationClassifier"]
