"""
Matrix Operations for parsing and evaluating matrix expressions.
"""
from __future__ import annotations

import re
from typing import Tuple, List, Optional
import sympy as sp

from engine.utils.logger import get_logger

logger = get_logger(__name__)

class MatrixOperations:
    """
    Handles parsing and transformations for matrix representation.
    """
    
    @staticmethod
    def preprocess_matrix_syntax(raw_input: str) -> str:
        """
        Converts MATLAB/Octave-like matrix syntax [1, 2; 3, 4] 
        or [[1,2],[3,4]] to something sympy can safely parse 
        like Matrix([[1, 2], [3, 4]])
        """
        if not raw_input:
            return raw_input
            
        text = raw_input
        
        # Replace MATLAB style [1, 2; 3, 4] with nested lists
        def replace_semicolon_matrix(match):
            content = match.group(1).strip()
            rows = content.split(';')
            nested_rows = []
            for row in rows:
                # Fallback splitting: support both comma or space separated
                if ',' in row:
                    items = [item.strip() for item in row.split(',')]
                else:
                    items = [item.strip() for item in row.split()]
                nested_rows.append(f"[{', '.join(items)}]")
            return f"Matrix([{', '.join(nested_rows)}])"

        if ';' in text and '[' in text:
            # Matches strings like [1, 2; 3, 4]
            text = re.sub(r'\[([^\[\]]+;[^\[\]]+)\]', replace_semicolon_matrix, text)

        # Replace nested lists [[1, 2], [3, 4]] with Matrix([[1, 2], [3, 4]])
        if '[[' in text and 'Matrix' not in text:
            text = re.sub(r'\[\s*\[', 'Matrix([[', text)
            
        return text

    @staticmethod
    def is_matrix(expr) -> bool:
        """Determines if a sympy expression is a matrix."""
        return isinstance(expr, sp.MatrixBase)
