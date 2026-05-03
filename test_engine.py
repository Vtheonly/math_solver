import os, sys
sys.path.insert(0, os.path.abspath('.'))
from engine.pipeline.solver_pipeline import SolverPipeline

try:
    print("Testing simplifier:")
    p = SolverPipeline()
    res1 = p.solve("2x + 3x", mode="simplifier")
    print(res1.to_dict())
    
    print("\nTesting plotter:")
    res2 = p.solve("y = x^2 + 2x + 1", mode="plotter")
    print("Plotter success:", "error" not in str(res2.to_dict()))
    if "error" in str(res2.to_dict()):
        print(res2.to_dict())
except Exception as e:
    import traceback
    traceback.print_exc()
