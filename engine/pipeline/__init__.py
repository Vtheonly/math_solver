"""
Pipeline subsystem for the equation solving engine.

Orchestrates the full solving pipeline from raw input to
verified result, coordinating all subsystems.
"""

from engine.pipeline.solver_pipeline import SolverPipeline

__all__ = ["SolverPipeline"]
