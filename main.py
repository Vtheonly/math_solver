#!/usr/bin/env python3
"""
Equation Solver — Main Entry Point

Starts the HTTP server and serves the equation solving engine.

Usage:
    python main.py                  # Default port 8000
    python main.py --port 3000      # Custom port
    python main.py --log-level INFO # Set log level
"""

import argparse
import logging
import sys
import os

# Ensure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.utils.logger import configure_logging, get_logger
from engine.server.http_server import MathSolverServer


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Equation Solver Engine — HTTP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py
  python main.py --port 3000
  python main.py --log-level INFO
  python main.py --log-file solver.log
        """,
    )
    parser.add_argument(
        "--host",
        default="",
        help="Host to bind to (default: all interfaces)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="DEBUG",
        help="Logging level (default: DEBUG)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Log file path (default: stderr only)",
    )
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Configure logging
    log_level = getattr(logging, args.log_level)
    configure_logging(level=log_level, log_file=args.log_file)

    logger = get_logger("main")
    logger.info("Starting Equation Solver Engine")
    logger.info("Host: %s, Port: %d", args.host or "*", args.port)
    logger.info("Log level: %s", args.log_level)

    # Start the server
    server = MathSolverServer(host=args.host, port=args.port)
    server.start()


if __name__ == "__main__":
    main()
