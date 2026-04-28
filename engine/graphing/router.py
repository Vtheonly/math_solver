"""
Determines if an input should be rendered as a graph.
"""
from __future__ import annotations

import re
from typing import Tuple, List, Optional
import sympy as sp

from engine.models.equation import Equation
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class GraphRouter:
    """
    Evaluates parsed input to decide if it should be graphed.
    """

    @staticmethod
    def should_graph(raw_input: str, equations: List[Equation]) -> bool:
        """
        Determine if the user intent is purely graphical, or if the expression
        is best represented as a graph.
        """
        raw_lower = raw_input.lower().strip()
        
        # Explicit graphing command
        if raw_lower.startswith(("plot", "graph", "draw")):
            return True
            
        # Specific visualization keywords
        if "circle" in raw_lower or "sine wave" in raw_lower or "animation" in raw_lower:
            return True

        if not equations:
            return False

        eq = equations[0]
        
        # Free expressions usually indicate a plot when there are 1-2 variables
        # E.g. "x^2" (parsed as x^2 = 0 maybe, depends on parser)
        # We check if it's explicitly y = f(x)
        if len(equations) == 1:
            vars_str = [str(v) for v in eq.variables]
            if len(vars_str) == 2 and ("y" in vars_str or "z" in vars_str):
                # We graph things like y = x^2, z = x^2 + y^2
                if str(eq.lhs) in ("y", "z") or str(eq.rhs) in ("y", "z"):
                    return True
            
            # Simple expression with 1 variable often wanted plotted if no '=' was originally provided
            if "=" not in raw_input and len(vars_str) in (1, 2):
                return True
                
        return False
