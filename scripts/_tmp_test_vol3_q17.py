import json
from services.grading_adapter import build_standard_solution_view

with open("storage/questions/simulations4/26李擂八套卷-卷三-017.json", encoding="utf-8") as f:
    q = json.load(f)

solution = {
    "success": True,
    "standard_answer": q["standard_answer"],
    "total_score": q["score"],
    "steps": q["solution_steps"],
}
view = build_standard_solution_view(solution, "解答题", {})
for i, s in enumerate(view.get("sections") or [], 1):
    c = " ".join(str(b.get("content", "")) for b in s.get("blocks") or [])
    print(i, repr(c[:150]))
