"""Comprehensive 4-type AI grading rendering test"""
import sys, json
sys.path.insert(0, '.')
from latex_utils import validate_and_repair
from database import QuestionDB

db = QuestionDB()
bs = chr(92)
passed = 0; failed = 0; fixed = 0

def test_render(name, qtype, solution, expect_ok=True):
    global passed, failed, fixed
    model, errors, repairs = validate_and_repair(solution)
    ok = model is not None and not errors
    if ok == expect_ok: passed += 1; tag = "OK"
    else: failed += 1; tag = "FAIL"
    if repairs: fixed += len(repairs)
    detail = f" [{len(repairs)} repairs]" if repairs else ""
    if not ok and expect_ok:
        for e in errors[:2]: detail += f" ERR:{str(e)[:80]}"
    print(f"  {tag}: {name}{detail}")
    return model

print("="*60)
print("4-TYPE AI GRADING RENDERING TEST")
print("="*60)

# 1. Multiple Choice (Engine A)
print("\n=== 1. 选择题 ===")
q = db.search(question_type='选择题', limit=1)[0]
print(f"Q: {q.get('question_id')}")
test_render("极限参数", "选择题", {
    "steps": [{"label": "标准解法", "blocks": [
        {"type": "text", "content": "泰勒展开 arctan x = x - x^3/3 + O(x^5)"},
        {"type": "latex", "content": bs + "lim_{x" + bs + "to 0}" + bs + "frac{x-" + bs + "arctan x}{x^k} = " + bs + "lim_{x" + bs + "to 0}" + bs + "frac{x^3/3}{x^k} = c", "display": "block"},
        {"type": "text", "content": "极限为非零常数需 k=3，此时 c=1/3，选(C)"},
    ]}],
    "final_answer": {"type": "text", "content": "(C) k=3, c=1/3"},
})

# 2. Fill-in-blank (Engine A)
print("\n=== 2. 填空题 ===")
q = db.search(question_type='填空题', limit=1)[0]
print(f"Q: {q.get('question_id')}")
test_render("隐函数求导", "填空题", {
    "steps": [{"label": "标准解法", "blocks": [
        {"type": "text", "content": "方程 y-x = e^{x(1-y)} 两边对 x 求导"},
        {"type": "latex", "content": "y' - 1 = e^{x(1-y)}[(1-y) - xy']", "display": "block"},
        {"type": "text", "content": "x=0 时 y=1，代入得 y'(0)=1。极限即 f'(0)=1"},
    ]}],
    "final_answer": {"type": "latex", "content": "1"},
})

# 3. Free Response (Engine B/C)
print("\n=== 3. 解答题 ===")
q = db.search(question_type='解答题', limit=1)[0]
print(f"Q: {q.get('question_id')}")
test_render("积分换序", "解答题", {
    "steps": [
        {"label": "步骤1：交换积分次序", "blocks": [
            {"type": "text", "content": "积分区域：0<=x<=1, 1<=t<=x 改写为 0<=t<=1, t<=x<=1"},
            {"type": "latex", "content": "I = " + bs + "int_0^1 " + bs + "frac{dx}{" + bs + "sqrt{x}} " + bs + "int_1^x " + bs + "frac{" + bs + "ln(t+1)}{t} dt = " + bs + "int_0^1 " + bs + "frac{" + bs + "ln(t+1)}{t} dt " + bs + "int_t^1 " + bs + "frac{dx}{" + bs + "sqrt{x}}", "display": "block"},
        ], "operation": "transform"},
        {"label": "步骤2：计算", "blocks": [
            {"type": "text", "content": "内层积分"},
            {"type": "latex", "content": bs + "int_t^1 x^{-1/2} dx = [2" + bs + "sqrt{x}]_t^1 = 2(1-" + bs + "sqrt{t})", "display": "block"},
        ], "operation": "evaluate"},
        {"label": "步骤3：换元", "blocks": [
            {"type": "text", "content": "令 u = sqrt(t)，代入化简"},
            {"type": "latex", "content": "I = 4" + bs + "int_0^1 " + bs + "ln(u^2+1)(1-u) du = 2" + bs + "ln^2 2 - " + bs + "frac{" + bs + "pi^2}{6}", "display": "block"},
        ], "operation": "substitute"},
    ],
    "final_answer": {"type": "latex", "content": "2" + bs + "ln^2 2 - " + bs + "frac{" + bs + "pi^2}{6}"},
})
test_render("矩阵秩", "解答题", {
    "steps": [
        {"label": "步骤1", "blocks": [
            {"type": "text", "content": "写成分块矩阵形式"},
            {"type": "latex", "content": "A(" + bs + "alpha_1," + bs + "alpha_2," + bs + "alpha_3) = (" + bs + "alpha_2," + bs + "alpha_3,0)", "display": "block"},
        ], "operation": "transform"},
        {"label": "步骤2", "blocks": [
            {"type": "latex", "content": "(" + bs + "alpha_2," + bs + "alpha_3,0) = (" + bs + "alpha_1," + bs + "alpha_2," + bs + "alpha_3) " + bs + "begin{pmatrix} 0&0&0 " + bs + bs + " 1&0&0 " + bs + bs + " 0&1&0 " + bs + "end{pmatrix}", "display": "block"},
        ], "operation": "simplify"},
        {"label": "步骤3", "blocks": [
            {"type": "text", "content": "M有两行非零且线性无关，r(M)=2。由相似不变性 r(A)=2"},
        ], "operation": "conclude"},
    ],
    "final_answer": {"type": "text", "content": "r(A)=2"},
})

# 4. Proof
print("\n=== 4. 证明题 ===")
q = db.search(question_type='证明题', limit=1)[0]
print(f"Q: {q.get('question_id')}")
test_render("中值定理", "证明题", {
    "steps": [
        {"label": "(1) 存在 xi in (0,1) 使 f'(xi)=1", "blocks": [
            {"type": "text", "content": "f为奇函数：f(-x)=-f(x)。f(1)=1 => f(-1)=-1。"},
            {"type": "text", "content": "在[-1,1]上应用拉格朗日中值定理"},
            {"type": "latex", "content": "f'(" + bs + "xi) = " + bs + "frac{f(1)-f(-1)}{1-(-1)} = 1", "display": "block"},
            {"type": "text", "content": "xi in (-1,1)，进一步可证 xi in (0,1)。"},
        ], "operation": "apply_theorem"},
        {"label": "(2) 存在 eta 使 f''(eta)+f'(eta)=1", "blocks": [
            {"type": "text", "content": "由(1)知存在 xi 使 f'(xi)=1。f'为偶函数，存在另一点 c 使 f'(c)=1。"},
            {"type": "text", "content": "令 h(x)=e^x(f'(x)-1)，h(xi)=h(c)=0。Rolle定理 => 存在 eta 使 h'(eta)=0。"},
            {"type": "text", "content": "h'(x)=e^x(f''(x)+f'(x)-1)=0 => f''(eta)+f'(eta)=1。"},
        ], "operation": "apply_theorem"},
    ],
    "final_answer": {"type": "text", "content": "证明完成"},
})

# 5. Production edge cases
print("\n=== 5. Production Edge Cases ===")
test_render("$ in latex", {"steps":[{"label":"s1","blocks":[{"type":"latex","content":"$"+bs+"frac{x}{y}$","display":"block"}]}]})
test_render("Chinese in latex", {"steps":[{"label":"s1","blocks":[{"type":"latex","content":"将方程代入","display":"block"}]}]})
test_render("bare begin", {"steps":[{"label":"s1","blocks":[{"type":"latex","content":"begin{pmatrix} a&b "+bs+bs+" c&d end{pmatrix}","display":"block"}]}]})
test_render("frac in text", {"steps":[{"label":"s1","blocks":[{"type":"text","content":"计算 "+bs+"frac{1}{2}"}]}]}, expect_ok=False)
test_render("empty blocks", {"steps":[{"label":"s1","blocks":[]}]}, expect_ok=False)
test_render("unknown type", {"steps":[{"label":"s1","blocks":[{"content":"hello","type":"bad"}]}]})

print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed, {fixed} auto-repairs")
