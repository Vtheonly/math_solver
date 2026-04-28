"""
Solver pipeline for the equation solving engine.

Orchestrates the complete solving workflow:
1. Parse raw input → Equation object(s)
2. Classify equation type
3. Select solving strategy
4. Execute strategy
5. Verify solutions
6. Assemble final SolveResult

This is the main entry point for the engine's core logic.
"""

from __future__ import annotations

import time
from typing import List, Optional

from engine.models.equation import Equation, EquationType
from engine.models.solve_result import SolveResult
from engine.models.solution import Solution
from engine.models.step import Step
from engine.parser.equation_parser import EquationParser, ParseError
from engine.classifiers.equation_classifier import EquationClassifier
from engine.strategies.factory import StrategyFactory
from engine.strategies.base import StrategyResult
from engine.strategies.system import SystemStrategy
from engine.strategies.numerical import NumericalStrategy
from engine.fractions.fraction_handler import FractionHandler
from engine.verification.verifier import Verifier
from engine.steps.step_builder import StepBuilder
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class SolverPipeline:
    """
    Main pipeline orchestrator for the equation solving engine.

    Coordinates all subsystems to transform raw input into a
    complete SolveResult with solutions, steps, and verification.

    Usage:
        pipeline = SolverPipeline()
        result = pipeline.solve("x^2 - 5x + 6 = 0")
        print(result.to_dict())
    """

    def __init__(self):
        """Initialize the pipeline with all required components."""
        self.classifier = EquationClassifier()
        self.strategy_factory = StrategyFactory()
        self.system_strategy = SystemStrategy()
        logger.info("SolverPipeline initialized")

    def solve(self, raw_input: str, mode: str = "solver") -> SolveResult:
        """
        Solve an equation or system from raw user input.

        This is the main entry point for the engine.

        Args:
            raw_input: Raw equation string from the user.

        Returns:
            A SolveResult with solutions, steps, and metadata.
        """
        start_time = time.time()
        result = SolveResult()

        logger.info("=" * 60)
        logger.info("SOLVING: '%s'", raw_input)
        logger.info("=" * 60)

        from engine.graphing.router import GraphRouter
        from engine.graphing.generator import GraphGenerator

        # Step 1: Determine if single or system
        from engine.parser.tokenizer import Tokenizer
        from engine.parser.equation_parser import EquationParser
        equation_strings = Tokenizer.split_equations(raw_input)
        is_system = len(equation_strings) > 1

        equations = []
        try:
            if is_system:
                equations = EquationParser.parse_system(raw_input)
            else:
                equations = [EquationParser.parse(raw_input)]
        except Exception as e:
            logger.warning("Parsing failed, but maybe it's an explicit graph command: %s", e)

        if mode == "simplifier":
            logger.info("Routing to Simplifier Mode")
            from engine.simplifier.expression_simplifier import ExpressionSimplifier
            result = ExpressionSimplifier.simplify(raw_input, equations)
            result.processing_time_ms = (time.time() - start_time) * 1000
            return result

        if mode == "plotter" or (mode == "solver" and GraphRouter.should_graph(raw_input, equations)):
            logger.info("Routing to Graphing Mode")
            graph_data = GraphGenerator.generate(raw_input, equations)
            result.graph_data = graph_data
            if "error" in graph_data:
                result.mark_failed(graph_data["error"])
            result.processing_time_ms = (time.time() - start_time) * 1000
            return result

        if is_system:
            result = self._solve_system(equation_strings, raw_input)
        else:
            result = self._solve_single(raw_input)

        # Record timing
        elapsed = (time.time() - start_time) * 1000
        result.processing_time_ms = elapsed

        logger.info(
            "Pipeline complete: %d solutions, %d steps, %.1fms",
            len(result.solutions),
            len(result.steps),
            elapsed,
        )

        return result

    def _solve_single(self, raw_input: str) -> SolveResult:
        """
        Solve a single equation.

        Pipeline:
        1. Parse → Equation
        2. Classify → EquationType
        3. Preprocess (clear fractions)
        4. Select strategy
        5. Execute strategy
        6. Verify solutions
        7. Assemble result
        """
        result = SolveResult()

        # Step 1: Parse
        try:
            equation = EquationParser.parse(raw_input)
        except ParseError as e:
            logger.error("Parse failed: %s", e)
            result.mark_failed(str(e))
            result.add_step(Step(
                title="Parse Error",
                description=str(e),
                category="error",
            ))
            return result

        result.equations = [equation]

        # Add initial steps
        result.add_step(StepBuilder.original_equation(equation))

        # Step 2: Classify
        equation = self.classifier.classify(equation)
        result.equation_type = equation.equation_type
        result.primary_variable = str(equation.primary_variable) if equation.primary_variable else None
        result.add_step(StepBuilder.equation_type(equation))

        # Step 3: Check for fractions and preprocess
        original_equation = equation  # Keep for verification

        if equation.has_fractions and not equation.equation_type == EquationType.RATIONAL:
            # Rational strategy handles its own fraction clearing
            cleared_eq, frac_steps = FractionHandler.clear_fractions(equation)
            for step in frac_steps:
                result.add_step(step)

            # Update equation with cleared version
            equation = Equation(
                raw_input=raw_input,
                sympy_eq=cleared_eq,
                variables=equation.variables,
                primary_variable=equation.primary_variable,
                equation_type=equation.equation_type,
                lhs=cleared_eq.lhs,
                rhs=cleared_eq.rhs,
                has_fractions=False,
                has_abs=equation.has_abs,
                degree=equation.degree,
            )
            result.equations = [equation]

        # Step 4: Select and execute strategy
        strategy = self.strategy_factory.get_strategy(equation)
        strategy_result = strategy.safe_solve(equation)

        # Step 5: Merge strategy results
        if not strategy_result.success:
            # Primary strategy failed, try numerical fallback
            logger.warning("Primary strategy '%s' failed, trying numerical fallback", strategy.name)
            numerical = NumericalStrategy()
            strategy_result = numerical.safe_solve(equation)

            if not strategy_result.success:
                result.mark_failed(strategy_result.error_message or "All solving strategies failed")
                return result

        # Merge steps and solutions
        for step in strategy_result.steps:
            result.add_step(step)

        result.solutions = strategy_result.solutions
        result.is_numerical = strategy_result.is_numerical

        # Step 6: Verify solutions against ORIGINAL equation
        if result.solutions and original_equation.equation_type != EquationType.SYSTEM:
            verify_steps = Verifier.verify_all(original_equation, result.solutions)
            for step in verify_steps:
                result.add_step(step)

        return result

    def _solve_system(self, equation_strings: List[str], raw_input: str) -> SolveResult:
        """
        Solve a system of equations.

        Pipeline:
        1. Parse all equations
        2. Classify each equation
        3. Clear fractions in each
        4. Execute system strategy
        5. Verify solutions
        """
        result = SolveResult(is_system=True)

        # Step 1: Parse all equations
        try:
            equations = EquationParser.parse_system(raw_input)
        except ParseError as e:
            logger.error("System parse failed: %s", e)
            result.mark_failed(str(e))
            return result

        result.equations = equations
        all_vars = []
        seen = set()
        for eq in equations:
            for v in eq.variables:
                if str(v) not in seen:
                    all_vars.append(v)
                    seen.add(str(v))

        if all_vars:
            result.primary_variable = str(all_vars[0])

        # Step 2: Classify
        equations = self.classifier.classify_system(equations)
        result.equation_type = EquationType.SYSTEM
        result.equations = equations

        # Step 3: Add identification steps
        for i, eq in enumerate(equations, 1):
            result.add_step(Step(
                title=f"Equation {i}",
                description=f"Parsed: {eq.equation_type.display_name}",
                equation=_fmt_eq(eq.sympy_eq),
                category="identify",
            ))

        result.add_step(StepBuilder.system_overview(equations, all_vars))

        # Step 4: Execute system strategy
        strategy_result = self.system_strategy.solve_system(equations)

        if not strategy_result.success:
            result.mark_failed(strategy_result.error_message or "System solving failed")
            # Still include any partial steps
            for step in strategy_result.steps:
                result.add_step(step)
            return result

        # Merge
        for step in strategy_result.steps:
            result.add_step(step)

        result.solutions = strategy_result.solutions
        result.is_numerical = strategy_result.is_numerical

        # Step 5: Verify
        if result.solutions:
            verify_steps = Verifier.verify_system_solution(equations, result.solutions)
            for step in verify_steps:
                result.add_step(step)

        return result


def _fmt_eq(eq):
    """Helper to format a SymPy Eq as LaTeX."""
    from engine.utils.latex_formatter import LatexFormatter
    return LatexFormatter.sympy_eq(eq)
