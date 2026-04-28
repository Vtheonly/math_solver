"""
HTTP server for the equation solving engine.

Serves the static HTML frontend and provides a JSON API
endpoint for solving equations. Uses Python's built-in
http.server module — no external dependencies required.
"""

from __future__ import annotations

import http.server
import json
import os
import traceback
from typing import Optional

from config import DEFAULT_HOST, DEFAULT_PORT
from engine.pipeline.solver_pipeline import SolverPipeline
from engine.utils.logger import get_logger

logger = get_logger(__name__)


class MathSolverHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler for the equation solver.

    Routes:
        GET  /        → Serves index.html
        POST /solve   → Solves an equation and returns JSON
        OPTIONS /solve → CORS preflight
    """

    # Directory where index.html is located
    UI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ui")

    def do_GET(self):
        """Handle GET requests — serve the UI."""
        if self.path == "/" or self.path == "/index.html":
            self._serve_file(os.path.join(self.UI_DIR, "index.html"), "text/html")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests — solve equations."""
        if self.path == "/solve":
            self._handle_solve()
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def _handle_solve(self):
        """Process a solve request."""
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)

            if not body:
                self._send_json({"error": "Empty request body"}, 400)
                return

            data = json.loads(body)
            equation = data.get("equation", "").strip()
            mode = data.get("mode", "solver").strip()

            if not equation:
                self._send_json({"error": "No equation provided"}, 400)
                return

            logger.info("Solve request: '%s' [Mode: %s]", equation, mode)

            # Solve
            pipeline = SolverPipeline()
            result = pipeline.solve(equation, mode=mode)

            # Send response
            self._send_json(result.to_dict())

        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON in request body"}, 400)
        except Exception as e:
            logger.exception("Unhandled error in solve handler")
            self._send_json({"error": f"Internal server error: {str(e)}"}, 500)

    def _serve_file(self, filepath: str, content_type: str):
        """Serve a static file."""
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self._set_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            logger.error("File not found: %s", filepath)

    def _send_json(self, data: dict, status: int = 200):
        """Send a JSON response."""
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self):
        """Set CORS headers for cross-origin requests."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.debug("HTTP: %s", format % args)


class MathSolverServer:
    """
    The equation solver HTTP server.

    Usage:
        server = MathSolverServer(port=8000)
        server.start()
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._server: Optional[http.server.HTTPServer] = None

    def start(self):
        """Start the server (blocking)."""
        self._server = http.server.HTTPServer(
            (self.host, self.port), MathSolverHandler
        )
        logger.info("Server starting at http://localhost:%d", self.port)
        print(f"Equation Solver running at http://localhost:{self.port}")
        print("Press Ctrl+C to stop")
        try:
            self._server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Server shutting down")
            self._server.shutdown()

    def start_async(self):
        """Start the server in a background thread (non-blocking)."""
        import threading
        self._server = http.server.HTTPServer(
            (self.host, self.port), MathSolverHandler
        )
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        logger.info("Server started in background at http://localhost:%d", self.port)
