"""
Verification subsystem for the equation solving engine.

Verifies solutions by substituting them back into the original
equation and checking that both sides are equal.
"""

from engine.verification.verifier import Verifier

__all__ = ["Verifier"]
