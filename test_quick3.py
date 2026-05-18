import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from latex_engine.trace import RewriteTrace, RewriteStep

trace = RewriteTrace(
    steps=[
        RewriteStep(
            rule="simplify",
            before="x^2 + 2x + 1",
            after="(x+1)^2",
        ),
        RewriteStep(
            rule="expand",
            before="(x+1)^2",
            after="x^2 + 2x + 1",
        ),
    ],
    final_expr="(x+1)^2",
)

latex = trace.to_latex()
print("RewriteTrace.to_latex():", repr(latex))

from rendering.structured_latex_renderer import LatexRenderer
renderer = LatexRenderer()
nodes = renderer.render_proof_trace(trace)
print("render_proof_trace:", len(nodes), "nodes")
for i, n in enumerate(nodes):
    print(f"  node[{i}]: type={n.type}, content={getattr(n, 'content', '')[:60]}")

from rendering.unified_renderer import UnifiedRenderer
ur = UnifiedRenderer()
tree = ur.render(trace)
print("UnifiedRenderer.render(trace):", type(tree).__name__)

print("RewriteTrace pipeline test done!")
