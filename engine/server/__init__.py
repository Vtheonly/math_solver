"""
HTTP server for the equation solving engine.

Provides a simple HTTP server that serves the UI and
handles solve requests via a JSON API.
"""

from engine.server.http_server import MathSolverServer

__all__ = ["MathSolverServer"]
