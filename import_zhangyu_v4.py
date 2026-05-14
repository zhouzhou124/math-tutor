"""Import Zhang Yu 8-exam-set Volume 4."""
import json
from pathlib import Path

SIMUL_DIR = Path('storage/questions/simulations')
INDEX_PATH = Path('storage/questions/_index.json')
vol = "卷四"

Q = [
    {"no":1,"qtype":"选择题","diff":"中等","kps":["极限"],"score":5,
     "q":"$1.$ 设函数 $f(x)$ 在 $x=0$ 的某邻域内有定义，且 $\\lim_{x\\to 0} \\frac{x - f(x)}{\\ln(1+x)} = 1$，则以下叙述：\\textcircled{1} $f(0)=0$；\\textcircled{2} $\\lim_{x\\to 0} f(x) = f(0)$；\\textcircled{3} $\\lim_{x\\to 0} \\frac{f(x)}{x} = 1$；\\textcircled{4} 当 $x\\to 0$ 时，$f(x)$ 是 $x$ 的高阶无穷小。正确叙述的个数为 "
         "$(A)$ $1$ $(B)$ $2$ $(C)$ $3$ $(D)$ $4$",
     "opts":{"A":"1","B":"2","C":"3","D":"4"},"ans":"C"},
    {"no":2,"qtype":"选择题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$2.$ 函数 $f(x,y) = x^2 + y^2$ 在约束条件 $(x-1)^3 = y^2$ 下 "
         "$(A)$ 有最大值，无最小值 $(B)$ 无最大值，有最小值 $(C)$ 有最大值，有最小值 $(D)$ 无最大值，无最小值",
     "opts":{"A":"有最大值无最小值","B":"无最大值有最小值","C":"都有","D":"都无"},"ans":"B"},
    {"no":3,"qtype":"选择题","diff":"中等","kps":["定积分"],"score":5,
     "q":"$3.$ 设 $f(x)$ 在 $[0,1]$ 上可积，则 $\\lim_{n\\to\\infty} \\sum_{i=0}^{n-1} \\ln[1 + \\frac{1}{n} f(\\frac{i}{n})] =$ "
         "$(A)$ $\\int_0^1 \\ln[1 + \\frac{f(x)}{n}] dx$ $(B)$ $\\int_0^1 \\ln[1 + f(x)] dx$ "
         "$(C)$ $\\int_0^1 f(x) dx$ $(D)$ $\\int_0^1 f^2(x) dx$",
     "opts":{"A":"积分A","B":"积分B","C":"$\\int_0^1 f(x)dx$","D":"$\\int_0^1 f^2(x)dx$"},"ans":"C"},
    {"no":4,"qtype":"选择题","diff":"较难","kps":["无穷级数"],"score":5,
     "q":"$4.$ 若级数 $\\sum_{n=1}^\\infty |u_n v_n|$ 发散，则 "
         "$(A)$ $\\sum n|u_n|$ 收敛且 $\\sum \\frac{|v_n|}{n}$ 收敛 "
         "$(B)$ $\\sum n|u_n|$ 发散且 $\\sum \\frac{|v_n|}{n}$ 收敛 "
         "$(C)$ $\\sum n|u_n|$ 收敛或 $\\sum \\frac{v_n}{n}$ 发散 "
         "$(D)$ $\\sum n|u_n|$ 发散或 $\\sum \\frac{v_n}{n}$ 发散",
     "opts":{"A":"都收敛","B":"一发一收","C":"收敛或发散","D":"发散或发散"},"ans":"D"},
    {"no":5,"qtype":"选择题","diff":"中等","kps":["矩阵"],"score":5,
     "q":"$5.$ 以下矩阵乘积的结果为 $\\begin{pmatrix} 1 & -1 & 2 \\\\ 2 & 1 & 3 \\\\ 3 & 1 & 4 \\end{pmatrix}$ 的是 "
         "$(A)$ $\\begin{pmatrix} 1 & 0 & 0 \\\\ 2 & 1 & 0 \\\\ 3 & 4 & 2 \\end{pmatrix} \\begin{pmatrix} 1 & -1 & 2 \\\\ 0 & 3 & -1 \\\\ 0 & 0 & -\\frac{2}{3} \\end{pmatrix}$ "
         "$(B)$ $\\begin{pmatrix} 1 & 0 & 0 \\\\ 2 & -1 & 0 \\\\ 3 & 4 & 1 \\end{pmatrix} \\begin{pmatrix} 1 & -1 & 2 \\\\ 0 & -3 & -1 \\\\ 0 & 0 & -\\frac{2}{3} \\end{pmatrix}$ "
         "$(C)$ LDU分解形式1 $(D)$ LDU分解形式2",
     "opts":{"A":"选项A","B":"选项B","C":"选项C","D":"选项D"},"ans":"D"},
    {"no":6,"qtype":"选择题","diff":"中等","kps":["二次型"],"score":5,
     "q":"$6.$ 设二次型 $f(x_1,x_2,x_3) = a x_1 x_2 + x_1 x_3 - x_2 x_3$ 的正惯性指数为2，负惯性指数为1，则以下结论可能成立的是 "
         "$(A)$ $a = -1$ $(B)$ $a = 1$ $(C)$ $a \\ge 0$ $(D)$ $a < 0$",
     "opts":{"A":"$a=-1$","B":"$a=1$","C":"$a\\ge0$","D":"$a<0$"},"ans":"B"},
    {"no":7,"qtype":"选择题","diff":"较难","kps":["线性方程组"],"score":5,
     "q":"$7.$ 在空间直角坐标系中，三张平面 $\\pi_1: ax + y - z = 1$，$\\pi_2: x + y + bz = a$，$\\pi_3: x + ay - z = 1$ 的位置关系如图所示，则 "
         "$(A)$ $a = -2, b = 2$ $(B)$ $a \\neq -2, b = 2$ $(C)$ $a = 1, b = -1$ $(D)$ $a = 1, b \\neq -1$",
     "opts":{"A":"$a=-2,b=2$","B":"$a\\neq-2,b=2$","C":"$a=1,b=-1$","D":"$a=1,b\\neq-1$"},"ans":"A"},
    {"no":8,"qtype":"选择题","diff":"较难","kps":["大数定律与中心极限定理"],"score":5,
     "q":"$8.$ 设 $F_n(x) = \\frac{\\nu_n(x)}{n}$，其中 $\\nu_n(x)$ 表示 $n$ 个观测值中不大于 $x$ 的个数。$F(x)$ 是分布函数，则：\\textcircled{1} $E[F_n(x)] = F(x)$；\\textcircled{2} $F_n(x) \\xrightarrow{P} F(x)$；\\textcircled{3} $F_n(x)$ 是一个分布函数；\\textcircled{4} $F_n(x)$ 是一个统计量。正确个数为 "
         "$(A)$ $1$ $(B)$ $2$ $(C)$ $3$ $(D)$ $4$",
     "opts":{"A":"1","B":"2","C":"3","D":"4"},"ans":"C"},
    {"no":9,"qtype":"选择题","diff":"较难","kps":["参数估计"],"score":5,
     "q":"$9.$ 设 $X_1,\\dots,X_n$ 是来自总体 $X$ 的样本，$P\\{X=k\\} = -\\frac{\\theta^k}{k\\ln(1-\\theta)}$，$k=1,2,\\dots$，$0<\\theta<1$，$\\mu_m = \\frac{1}{n}\\sum X_i^m$，则 $\\theta$ 的矩估计量为 "
         "$(A)$ $1+\\frac{\\mu_1}{\\mu_2}$ $(B)$ $1-\\frac{\\mu_1}{\\mu_2}$ $(C)$ $1+\\frac{\\mu_2}{\\mu_3}$ $(D)$ $1-\\frac{\\mu_2}{\\mu_3}$",
     "opts":{"A":"$1+\\mu_1/\\mu_2$","B":"$1-\\mu_1/\\mu_2$","C":"$1+\\mu_2/\\mu_3$","D":"$1-\\mu_2/\\mu_3$"},"ans":"B"},
    {"no":10,"qtype":"选择题","diff":"中等","kps":["随机变量的数字特征"],"score":5,
     "q":"$10.$ 设 $X,Y$ 独立同分布于 $N(0,\\sigma^2)$，$X_1,\\dots,X_9$ 与 $Y_1,\\dots,Y_{11}$ 是样本，$S_X^2$ 与 $S_Y^2$ 为样本方差，$S_1^2 = \\frac{1}{2}(S_X^2 + S_Y^2)$，$S_2^2 = \\frac{1}{9}(4S_X^2 + 5S_Y^2)$，则方差最小的是 "
         "$(A)$ $S_X^2$ $(B)$ $S_Y^2$ $(C)$ $S_1^2$ $(D)$ $S_2^2$",
     "opts":{"A":"$S_X^2$","B":"$S_Y^2$","C":"$S_1^2$","D":"$S_2^2$"},"ans":"B"},

    {"no":11,"qtype":"填空题","diff":"中等","kps":["极限"],"score":5,
     "q":"$11.$ $\\lim_{x\\to 0} (\\frac{\\arctan x}{x})^{\\tan^2 x} =$ ______","ans":"$e^{-\\frac{1}{3}}$"},
    {"no":12,"qtype":"填空题","diff":"中等","kps":["常微分方程"],"score":5,
     "q":"$12.$ 设 $y = y(x)$ 满足 $xy' = \\sqrt{1 - x^2}$，$y(1)=0$，则 $\\int_0^1 y(x) dx =$ ______","ans":"$\\frac{\\pi}{4} - \\frac{1}{2}$"},
    {"no":13,"qtype":"填空题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$13.$ $z = \\ln(e^{-y} + \\frac{y^2}{x})$ 在点 $(1,1)$ 处沿 $l = (1,0)$ 的方向导数为 ______","ans":"$-\\frac{1}{2}$"},
    {"no":14,"qtype":"填空题","diff":"较难","kps":["曲线积分与曲面积分"],"score":5,
     "q":"$14.$ 设 $\\Sigma$ 为曲面 $x^2 + \\frac{y^2}{4} + \\frac{z^2}{4} = 1$ 的外侧，则 $\\iint_{\\Sigma} x dy dz + z^2 dx dy =$ ______","ans":"$0$"},
    {"no":15,"qtype":"填空题","diff":"较难","kps":["线性方程组"],"score":5,
     "q":"$15.$ 设 $a_1=(4,1,2)^T,a_2=(1,1,-1)^T,a_3=(-2,0,4)^T,a_4=(7,2,-3)^T$，$A=(a_1,a_2,a_3,a_4)$，则 $Ax = a_2 + 3a_4$ 的通解为 ______","ans":"$x = k_1(1,-2,1,0)^T + k_2(0,-1,0,1)^T$"},
    {"no":16,"qtype":"填空题","diff":"中等","kps":["随机事件与概率"],"score":5,
     "q":"$16.$ 已知 $A$ 发生且 $B$ 不发生的概率为 $\\frac{1}{2}$，在 $A$ 发生或 $B$ 不发生的条件下 $B$ 发生的概率为 $\\frac{1}{4}$，若 $P(A)=\\frac{7}{10}$，则 $P(B)=$ ______","ans":"$\\frac{3}{5}$"},

    {"no":17,"qtype":"解答题","diff":"中等","kps":["一元函数积分学"],"score":10,
     "q":"$17.$ (本题满分10分) 设 $f'(e^x) = \\sin x$，求 $f(x)$ 的表达式。","ans":"$f(x) = \\arcsin(\\ln x) + C$"},
    {"no":18,"qtype":"解答题","diff":"中等","kps":["常微分方程"],"score":12,
     "q":"$18.$ (本题满分12分) 设 $y = y(x)$ 满足 $[(1+x)y - 1]dx + x(1+x)dy = 0$，$y(1) = \\ln 2$。(1) 求 $y(x)$ 及定义域；(2) 记 $f(x) = \\int_{-1}^x y(|t|) dt$，求 $f'(0)$。","ans":"(1) $y=\\frac{\\ln(1+x)}{x},x>-1,x\\neq0$; (2) $0$"},
    {"no":19,"qtype":"解答题","diff":"中等","kps":["中值定理"],"score":12,
     "q":"$19.$ (本题满分12分) 设 $f(x)$ 在 $[0,1]$ 上连续，$g(x)$ 在 $[0,1]$ 上可积且非负。证明：存在 $\\xi\\in(0,1)$ 使 $\\int_0^1 f(x)g(x)dx = f(\\xi)\\int_0^1 g(x)dx$。","ans":"证明略"},
    {"no":20,"qtype":"解答题","diff":"较难","kps":["曲线积分与曲面积分"],"score":12,
     "q":"$20.$ (本题满分12分) 设 $\\Gamma$ 为球面 $x^2+y^2+z^2=m^2$ 与平面 $x+z=m(m>0)$ 的交线，计算 $I = \\oint_{\\Gamma} xz(1+yz-xy)ds$。","ans":"$0$"},
    {"no":21,"qtype":"解答题","diff":"较难","kps":["矩阵"],"score":12,
     "q":"$21.$ (本题满分12分) 设 $A=\\begin{pmatrix}1&-2&3\\\\0&1&-1\\\\1&2&0\\end{pmatrix}$，$\\beta=(-4,1,-3)^T$，$B=\\begin{pmatrix}-2&1&3\\\\1&0&-1\\\\2&1&0\\end{pmatrix}$，$(A,\\beta)=BC$。(1) 求 $Ax=\\beta$ 的解及 $C$；(2) 求满足 $(A,\\beta)Y=E$ 的所有 $Y$。","ans":"(1) $x=(-2,1,0)^T+k(-5,-1,1)^T$"},
    {"no":22,"qtype":"解答题","diff":"较难","kps":["随机变量及其分布"],"score":12,
     "q":"$22.$ (本题满分12分) 设 $t(\\ge0)$ 时刻已进入某商场的顾客人数 $N$ 服从参数为 $\\frac{t}{2}$ 的泊松分布，$T$ 为第1个顾客到来时刻。(1) 求 $T$ 的概率密度；(2) 当 $T_1,T_2,\\dots$ 独立同分布于 $T$ 时，$\\frac{1}{n}\\sum T_i^2$ 依概率收敛于 $a$，求 $a$。","ans":"(1) $f_T(t)=\\frac{1}{2}e^{-t/2},t>0$; (2) $a=8$"},
]

total = 0
for q in Q:
    qid = f"26宇哥八套卷-{vol}-{q['no']:03d}"
    item = {
        "question_id": qid, "year": 2026,
        "category": "26宇哥八套卷", "volume": vol,
        "question_type": q["qtype"], "question_no": q["no"],
        "score": q["score"], "difficulty": q["diff"],
        "knowledge_points": q["kps"], "tags": q["kps"],
        "question": q["q"], "source": "import_v4",
    }
    if q["qtype"] == "选择题":
        item["options"] = q["opts"]
        item["correct_option"] = q["ans"]
        item["standard_answer"] = q["ans"]
    else:
        item["standard_answer"] = q["ans"]

    path = SIMUL_DIR / f"{qid}.json"
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(item, f, ensure_ascii=False, indent=2)
    total += 1
    print(f"  OK: {qid}")

# Rebuild index
index = {"categories":{},"knowledge_index":{},"difficulty_index":{},"metadata":{"total_questions":0}}
for d in [Path('storage/questions/exams'), SIMUL_DIR]:
    if not d.exists(): continue
    for f in sorted(d.glob("*.json")):
        with open(f, 'r', encoding='utf-8') as fp:
            q = json.load(fp)
        qid = q.get("question_id", f.stem)
        cat = q.get("category", "")
        qtype = q.get("question_type", "")
        sub = q.get("volume", "") or str(q.get("year", ""))
        diff = q.get("difficulty", "")
        kps = q.get("knowledge_points", []) or q.get("tags", [])

        cd = index["categories"].setdefault(cat, {})
        sd = cd.setdefault(sub, {})
        tl = sd.setdefault(qtype, [])
        if qid not in tl: tl.append(qid)
        for kp in kps:
            kl = index["knowledge_index"].setdefault(kp, [])
            if qid not in kl: kl.append(qid)
        if diff:
            dl = index["difficulty_index"].setdefault(diff, [])
            if qid not in dl: dl.append(qid)

total_q = sum(
    len(ids) for cat_data in index["categories"].values()
    for sub_data in cat_data.values()
    for ids in sub_data.values() if isinstance(ids, list)
)
index["metadata"]["total_questions"] = total_q

with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\nVolume 4: {total} imported, Total: {total_q}")
