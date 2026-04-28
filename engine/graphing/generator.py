"""
Generates graph datasets compatible with Plotly.js.
"""
from __future__ import annotations

import numpy as np
import sympy as sp
from typing import Dict, Any, List, Optional, Tuple

from engine.models.equation import Equation
from engine.utils.logger import get_logger

logger = get_logger(__name__)

class GraphGenerator:
    """
    Transforms sympy expressions and geometric specs into Plotly graph payloads.
    """
    
    @staticmethod
    def generate(raw_input: str, equations: List[Equation]) -> Dict[str, Any]:
        logger.info("Generating graph for input: %s", raw_input)
        
        if not equations:
            return {"error": "No equation found to graph"}

        eq = equations[0]
        
        # Decide if it's an explicit equation or just an expression
        expr = eq.lhs
        if "=" in raw_input and "draw" not in raw_input.lower() and "plot" not in raw_input.lower():
            if str(eq.lhs) in ("y", "z"):
                expr = eq.rhs
            elif str(eq.rhs) in ("y", "z"):
                expr = eq.lhs
            else:
                expr = eq.lhs - eq.rhs

        all_vars = sorted([str(v) for v in expr.free_symbols])
        
        # Separate spatial variables from parameters
        spatial_candidates = ['x', 'y', 'z']
        spatial_vars = [v for v in all_vars if v in spatial_candidates]
        params = [v for v in all_vars if v not in spatial_candidates]

        # If no spatial variables found, maybe they used something else?
        # Just pick the first variable as 'x' if possible
        if not spatial_vars and all_vars:
            spatial_vars = [all_vars[0]]
            params = all_vars[1:]

        logger.info("Graphing variables: Spatial=%s, Params=%s", spatial_vars, params)

        if len(spatial_vars) == 1:
            var_x = sp.Symbol(spatial_vars[0])
            if not params:
                return GraphGenerator._plot_2d(expr, var_x)
            else:
                return GraphGenerator._plot_2d_animated(expr, var_x, params[0])
                
        if len(spatial_vars) == 2:
            var_x = sp.Symbol(spatial_vars[0])
            var_y = sp.Symbol(spatial_vars[1])
            if not params:
                return GraphGenerator._plot_3d(expr, var_x, var_y)
            else:
                return GraphGenerator._plot_3d_animated(expr, var_x, var_y, params[0])
                
        return {"error": f"Cannot graph expressions with {len(spatial_vars)} spatial variables."}

    @staticmethod
    def _plot_2d(expr, var_x: sp.Symbol) -> Dict[str, Any]:
        x_vals = np.linspace(-10, 10, 400)
        y_vals = GraphGenerator._evaluate(expr, [var_x], [x_vals])
            
        traces = [{
            "x": x_vals.tolist(),
            "y": y_vals.tolist(),
            "type": "scatter",
            "mode": "lines",
            "name": f"f({var_x})"
        }]

        try:
            roots = sp.solve(expr, var_x)
            real_roots = []
            for r in roots:
                try:
                    if r.is_real or r.is_real is None:
                        val = float(r)
                        if -20 <= val <= 20: 
                            real_roots.append(val)
                except Exception:
                    pass
            
            if real_roots:
                traces.append({
                    "x": real_roots,
                    "y": [0] * len(real_roots),
                    "type": "scatter",
                    "mode": "markers",
                    "marker": {"size": 8, "symbol": "diamond", "color": "red"},
                    "name": "Solutions (Roots)"
                })
        except Exception as e:
            logger.debug("Roots could not be extracted: %s", e)

        return {
            "is_graph": True,
            "type": "2D",
            "traces": traces,
            "layout": {
                "title": f"Graph of {expr}",
                "xaxis": {"title": str(var_x)},
                "yaxis": {"title": f"f({var_x})"}
            }
        }

    @staticmethod
    def _plot_3d(expr, var_x: sp.Symbol, var_y: sp.Symbol) -> Dict[str, Any]:
        x_vals = np.linspace(-10, 10, 50)
        y_vals = np.linspace(-10, 10, 50)
        X, Y = np.meshgrid(x_vals, y_vals)
        Z = GraphGenerator._evaluate(expr, [var_x, var_y], [X, Y])
        
        traces = [{
            "x": x_vals.tolist(),
            "y": y_vals.tolist(),
            "z": Z.tolist(),
            "type": "surface",
            "colorscale": "Viridis",
            "contours": {
                "z": {"show": True, "usecolormap": True, "highlightcolor": "limegreen", "project": {"z": True}}
            }
        }]

        try:
            fx = sp.diff(expr, var_x)
            fy = sp.diff(expr, var_y)
            crit_pts = sp.solve((fx, fy), (var_x, var_y))
            
            crit_x, crit_y, crit_z = [], [], []
            
            if isinstance(crit_pts, dict):
                crit_pts = [(crit_pts.get(var_x), crit_pts.get(var_y))]
            elif isinstance(crit_pts, tuple) and len(crit_pts) == 2 and not isinstance(crit_pts[0], tuple):
                crit_pts = [crit_pts]
            
            if isinstance(crit_pts, list):
                for pt in crit_pts:
                    if isinstance(pt, tuple) and len(pt) == 2:
                        try:
                            px, py = float(pt[0]), float(pt[1])
                            pz = float(expr.subs({var_x: px, var_y: py}))
                            if -20 <= px <= 20 and -20 <= py <= 20:
                                crit_x.append(px)
                                crit_y.append(py)
                                crit_z.append(pz)
                        except Exception:
                            pass
                            
            if crit_x:
                traces.append({
                    "x": crit_x,
                    "y": crit_y,
                    "z": crit_z,
                    "type": "scatter3d",
                    "mode": "markers",
                    "marker": {"size": 6, "color": "red", "symbol": "diamond"},
                    "name": "Critical Points"
                })
        except Exception as e:
            logger.debug("Failed to find 3D critical points: %s", e)
            
        return {
            "is_graph": True,
            "type": "3D",
            "traces": traces,
            "layout": {
                "title": f"3D Surface: {expr}",
                "scene": {
                    "xaxis": {"title": str(var_x)},
                    "yaxis": {"title": str(var_y)},
                    "zaxis": {"title": f"f({var_x}, {var_y})"}
                }
            }
        }

    @staticmethod
    def _plot_2d_animated(expr, var_x: sp.Symbol, param: str) -> Dict[str, Any]:
        p_sym = sp.Symbol(param)
        x_vals = np.linspace(-10, 10, 400)
        
        frames = []
        p_vals = np.linspace(-5, 5, 20)
        
        # Initial trace
        y_initial = GraphGenerator._evaluate(expr.subs(p_sym, p_vals[0]), [var_x], [x_vals])
        
        for p_val in p_vals:
            # Substitute parameter then lambdify
            y_frame = GraphGenerator._evaluate(expr.subs(p_sym, p_val), [var_x], [x_vals])
            frames.append({"data": [{"y": y_frame.tolist()}], "name": f"{p_val:.2f}"})
            
        return {
            "is_graph": True,
            "type": "animation",
            "traces": [{"x": x_vals.tolist(), "y": y_initial.tolist(), "type": "scatter", "mode": "lines"}],
            "frames": frames,
            "layout": {
                "title": f"Animated {expr} with slider for {param}",
                "xaxis": {"title": str(var_x)},
                "yaxis": {"title": "f(...) ", "range": [-10, 10]},
                "updatemenus": [{
                    "type": "buttons",
                    "buttons": [{"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 200}}]}]
                }],
                "sliders": [{
                    "active": 0,
                    "steps": [{"label": f"{p:.2f}", "method": "animate", "args": [[f"{p:.2f}"]]} for p in p_vals]
                }]
            }
        }

    @staticmethod
    def _plot_3d_animated(expr, var_x: sp.Symbol, var_y: sp.Symbol, param: str) -> Dict[str, Any]:
        p_sym = sp.Symbol(param)
        x_vals = np.linspace(-10, 10, 30)
        y_vals = np.linspace(-10, 10, 30)
        X, Y = np.meshgrid(x_vals, y_vals)
        
        frames = []
        p_vals = np.linspace(-5, 5, 10)
        
        Z_initial = GraphGenerator._evaluate(expr.subs(p_sym, p_vals[0]), [var_x, var_y], [X, Y])
        
        for p_val in p_vals:
            Z_frame = GraphGenerator._evaluate(expr.subs(p_sym, p_val), [var_x, var_y], [X, Y])
            frames.append({"data": [{"z": Z_frame.tolist()}], "name": f"{p_val:.2f}"})
            
        return {
            "is_graph": True,
            "type": "animation",
            "traces": [{
                "x": x_vals.tolist(),
                "y": y_vals.tolist(),
                "z": Z_initial.tolist(),
                "type": "surface",
                "colorscale": "Viridis"
            }],
            "frames": frames,
            "layout": {
                "title": f"Animated Surface {expr} with slider for {param}",
                "scene": {
                    "xaxis": {"title": str(var_x)},
                    "yaxis": {"title": str(var_y)},
                    "zaxis": {"title": "f(...)", "range": [-10, 10]}
                },
                "updatemenus": [{
                    "type": "buttons",
                    "buttons": [{"label": "Play", "method": "animate", "args": [None, {"frame": {"duration": 400}}]}]
                }],
                "sliders": [{
                    "active": 0,
                    "steps": [{"label": f"{p:.2f}", "method": "animate", "args": [[f"{p:.2f}"]]} for p in p_vals]
                }]
            }
        }

    @staticmethod
    def _evaluate(expr, vars: List[sp.Symbol], grids: List[np.ndarray]) -> np.ndarray:
        try:
            f = sp.lambdify(vars, expr, modules=["numpy", "math"])
            res = f(*grids)
            if np.isscalar(res):
                res = np.full_like(grids[0], res)
            if np.iscomplexobj(res):
                res = np.real(res)
            return res
        except Exception as e:
            logger.error("Evaluation error: %s", e)
            return np.zeros_like(grids[0])
