"""
LaTeX formatting utilities.

Provides consistent LaTeX rendering for SymPy expressions and
custom formatting for steps, solutions, and verification output.
"""

from __future__ import annotations

from typing import Optional

from sympy import latex as sympy_latex, simplify, Symbol, Expr, Eq, Add, Mul


class LatexFormatter:
    """
    Centralized LaTeX formatting for the solving engine.

    All LaTeX output should go through this class to ensure
    consistent rendering and escaping.
    """

    @staticmethod
    def expr(expr: Expr, simplify_expr: bool = True) -> str:
        """Format a SymPy expression as LaTeX.
        Set simplify_expr to False to preserve the exact structure (like factored forms).
        """
        if not simplify_expr:
            return sympy_latex(expr)
            
        try:
            return sympy_latex(simplify(expr))
        except Exception:
            return sympy_latex(expr)

    @staticmethod
    def equation(lhs: Expr, rhs: Expr) -> str:
        """Format an equation (lhs = rhs) as LaTeX."""
        return f"{sympy_latex(lhs)} = {sympy_latex(rhs)}"

    @staticmethod
    def sympy_eq(eq: Eq) -> str:
        """Format a SymPy Eq object as LaTeX."""
        return f"{sympy_latex(eq.lhs)} = {sympy_latex(eq.rhs)}"

    @staticmethod
    def variable(var: Symbol) -> str:
        """Format a variable symbol as LaTeX."""
        return sympy_latex(var)

    @staticmethod
    def assignment(var: Symbol, value: Expr) -> str:
        """Format a variable assignment (var = value) as LaTeX."""
        return f"{sympy_latex(var)} = {sympy_latex(simplify(value))}"

    @staticmethod
    def assignment_str(var_name: str, value_latex: str) -> str:
        """Format a variable assignment using pre-rendered LaTeX strings."""
        return f"{var_name} = {value_latex}"

    @staticmethod
    def standard_form(expr: Expr) -> str:
        """Format an expression in standard form (= 0) as LaTeX."""
        return f"{sympy_latex(expr)} = 0"

    @staticmethod
    def discriminant(disc: Expr) -> str:
        """Format a discriminant value as LaTeX."""
        return f"\\Delta = {sympy_latex(simplify(disc))}"

    @staticmethod
    def quadratic_formula(var: Symbol, a: Expr, b: Expr, disc: Expr) -> str:
        """
        Format the quadratic formula application as LaTeX.

        Shows: var = (-b ± √Δ) / (2a)
        """
        var_latex = sympy_latex(var)
        b_neg = sympy_latex(simplify(-b))
        disc_latex = sympy_latex(simplify(disc))
        denom = sympy_latex(simplify(2 * a))
        return f"{var_latex} = \\dfrac{{{b_neg} \\pm \\sqrt{{{disc_latex}}}}}{{{denom}}}"

    @staticmethod
    def verify_substitution(var: Symbol, value: Expr, lhs_result: Expr, rhs_result: Expr, passed: bool) -> str:
        """Format a verification step as LaTeX."""
        var_l = sympy_latex(var)
        val_l = sympy_latex(simplify(value))
        lhs_l = sympy_latex(lhs_result)
        rhs_l = sympy_latex(rhs_result)
        mark = "\\checkmark" if passed else "\\times"
        return f"{lhs_l} = {rhs_l} \\quad {mark}"

    @staticmethod
    def back_substitution(var: Symbol, expr: Expr, sub_var: Symbol, sub_val: Expr, result: Expr) -> str:
        """
        Format a back-substitution step as LaTeX.

        Shows: var = expr |_{sub_var = sub_val} = result
        """
        var_l = sympy_latex(var)
        expr_l = sympy_latex(simplify(expr))
        sub_var_l = sympy_latex(sub_var)
        sub_val_l = sympy_latex(simplify(sub_val))
        result_l = sympy_latex(simplify(result))
        return f"{var_l} = {expr_l} \\Big|_{{{sub_var_l}={sub_val_l}}} = {result_l}"

    @staticmethod
    def coefficients(coeffs: dict) -> str:
        """Format coefficient labels as LaTeX."""
        parts = [f"{k} = {sympy_latex(simplify(v))}" for k, v in coeffs.items()]
        return "\\quad ".join(parts)

    @staticmethod
    def lcd_multiply(lhs: Expr, rhs: Expr, lcd: Expr) -> str:
        """Format the LCD multiplication step as LaTeX."""
        def wrap(expr: Expr) -> str:
            l = sympy_latex(expr)
            # If expression is additive, wrap it in parens to avoid ambiguous multiplication
            if isinstance(expr, Add) or (isinstance(expr, Mul) and any(isinstance(a, Add) for a in expr.args)):
                return f"\\left({l}\\right)"
            return l

        return f"{wrap(lhs)} \\cdot {wrap(lcd)} = {wrap(rhs)} \\cdot {wrap(lcd)}"
