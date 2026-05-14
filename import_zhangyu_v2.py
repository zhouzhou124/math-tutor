"""Import Zhang Yu 8-exam-set Volume 2."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import QuestionDB

db = QuestionDB()
vol, cat = "卷二", "26宇哥八套卷"

Q = [
    # === CHOICE (1-10) ===
    {"no":1,"qtype":"选择题","diff":"中等","kps":["极限","数列"],"score":5,
     "q":"$1.$ 设函数 $f(x)$ 在 $(0, +\\infty)$ 上有界且可导，$f'(x)$ 单调增加，则 "
         "$(A)$ $\\{f(n)\\}$ 收敛，$\\{nf'(n)\\}$ 收敛 "
         "$(B)$ $\\{f(n)\\}$ 收敛，$\\{nf'(n)\\}$ 发散 "
         "$(C)$ $\\{f(n)\\}$ 发散，$\\{nf'(n)\\}$ 收敛 "
         "$(D)$ $\\{f(n)\\}$ 发散，$\\{nf'(n)\\}$ 发散",
     "opts":{"A":"$\\{f(n)\\}$ 收敛，$\\{nf'(n)\\}$ 收敛","B":"$\\{f(n)\\}$ 收敛，$\\{nf'(n)\\}$ 发散","C":"$\\{f(n)\\}$ 发散，$\\{nf'(n)\\}$ 收敛","D":"$\\{f(n)\\}$ 发散，$\\{nf'(n)\\}$ 发散"},"ans":"A"},
    {"no":2,"qtype":"选择题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$2.$ 设可微函数 $f(x,y)$ 在点 $(0,0)$ 处的最小方向导数为 $a$，$a \\neq 0$ 且 $a \\neq -1$，$b,c$ 是满足 $b^2 + c^2$ 为正常数的任意实数，则 $\\operatorname{grad} f(0,0)$ 与 $(b,c)$ 内积的最大值为 "
         "$(A)$ $a\\sqrt{b^2 + c^2}$ $(B)$ $-a\\sqrt{b^2 + c^2}$ $(C)$ $\\sqrt{a|(b^2 + c^2)|}$ $(D)$ $-\\sqrt{a|(b^2 + c^2)|}$",
     "opts":{"A":"$a\\sqrt{b^2 + c^2}$","B":"$-a\\sqrt{b^2 + c^2}$","C":"$\\sqrt{a|(b^2 + c^2)|}$","D":"$-\\sqrt{a|(b^2 + c^2)|}$"},"ans":"B"},
    {"no":3,"qtype":"选择题","diff":"基础","kps":["无穷级数"],"score":5,
     "q":"$3.$ $\\sum_{n=2}^{\\infty} \\left[ \\frac{1}{n!} + \\frac{1}{(n-2)!} \\right] =$ "
         "$(A)$ $e-1$ $(B)$ $e$ $(C)$ $2(e-1)$ $(D)$ $2e$",
     "opts":{"A":"$e-1$","B":"$e$","C":"$2(e-1)$","D":"$2e$"},"ans":"C"},
    {"no":4,"qtype":"选择题","diff":"中等","kps":["一元函数微分学"],"score":5,
     "q":"$4.$ 设 $f(x)$ 在 $[0,1]$ 上可导，当 $0 \\le x \\le 1$ 时，$f'(x) + f^2(x) \\ge 0$，$f(0) > 0$，则 "
         "$(A)$ $\\int_0^1 f(x) dx \\le \\ln \\frac{f(1)}{f(0)}$ $(B)$ $\\int_0^1 f(x) dx \\ge \\ln \\frac{f(0)}{f(1)}$ "
         "$(C)$ $\\int_0^1 f(x) dx \\le \\ln f(1)$ $(D)$ $\\int_0^1 f(x) dx \\ge \\ln f(0)$",
     "opts":{"A":"$\\int_0^1 f(x) dx \\le \\ln \\frac{f(1)}{f(0)}$","B":"$\\int_0^1 f(x) dx \\ge \\ln \\frac{f(0)}{f(1)}$","C":"$\\int_0^1 f(x) dx \\le \\ln f(1)$","D":"$\\int_0^1 f(x) dx \\ge \\ln f(0)$"},"ans":"A"},
    {"no":5,"qtype":"选择题","diff":"较难","kps":["矩阵"],"score":5,
     "q":"$5.$ 设 $A$ 为 $n$ 阶实矩阵，则 "
         "$(A)$ $\\begin{pmatrix} A & O \\\\ E & A^T A \\end{pmatrix} x = 0$ 只有零解 "
         "$(B)$ $\\begin{pmatrix} O & A \\\\ A^T A & AA^T A \\end{pmatrix} x = 0$ 只有零解 "
         "$(C)$ $\\begin{pmatrix} A & A^T A \\\\ O & A^T A \\end{pmatrix} x = 0$ 与 $\\begin{pmatrix} A^T A & A \\\\ O & A \\end{pmatrix} x = 0$ 同解 "
         "$(D)$ $\\begin{pmatrix} AA^T A & A^T A \\\\ O & A \\end{pmatrix} x = 0$ 与 $\\begin{pmatrix} A^T A^2 & A \\\\ O & A^T A \\end{pmatrix} x = 0$ 同解",
     "opts":{"A":"只有零解","B":"只有零解","C":"同解","D":"同解"},"ans":"C"},
    {"no":6,"qtype":"选择题","diff":"较难","kps":["二次型"],"score":5,
     "q":"$6.$ 已知二次型 $f(x_1,x_2,x_3) = 4x_1^2 + x_2^2 + a x_3^2 + 2x_1x_2 - 4x_1x_3 + 2x_2x_3$ 可经可逆线性变换但不可经正交变换化为 $g(y_1,y_2,y_3) = b y_1^2 + 6 y_2^2$，则 $a+b$ 的取值范围为 "
         "$(A)$ $(4, +\\infty)$ $(B)$ $(7, +\\infty)$ $(C)$ $[4, +\\infty)$ $(D)$ $(4,7) \\cup (7,+\\infty)$",
     "opts":{"A":"$(4, +\\infty)$","B":"$(7, +\\infty)$","C":"$[4, +\\infty)$","D":"$(4,7) \\cup (7,+\\infty)$"},"ans":"D"},
    {"no":7,"qtype":"选择题","diff":"较难","kps":["矩阵"],"score":5,
     "q":"$7.$ 下列矩阵中，与 $\\begin{pmatrix} 1 & 0 & 0 \\\\ 0 & 2 & 1 \\\\ 0 & 0 & 2 \\end{pmatrix}$ 不相似的是 "
         "$(A)$ $\\begin{pmatrix} 2 & 0 & -1 \\\\ 0 & 1 & 0 \\\\ 0 & 0 & 2 \\end{pmatrix}$ $(B)$ $\\begin{pmatrix} 2 & 0 & 0 \\\\ -1 & 2 & 1 \\\\ 0 & 0 & 1 \\end{pmatrix}$ "
         "$(C)$ $\\begin{pmatrix} 2 & 1 & 0 \\\\ 0 & 1 & 1 \\\\ 0 & 0 & 2 \\end{pmatrix}$ $(D)$ $\\begin{pmatrix} 2 & -1 & 0 \\\\ 1 & 2 & 0 \\\\ 0 & 0 & 1 \\end{pmatrix}$",
     "opts":{"A":"相似","B":"相似","C":"相似","D":"不相似"},"ans":"D"},
    {"no":8,"qtype":"选择题","diff":"基础","kps":["随机变量的数字特征"],"score":5,
     "q":"$8.$ 设10个球中有3个红球，7个白球，现从10个球中无放回地抽取3个球，记取到白球的个数为 $X$，则 $E(X) =$ "
         "$(A)$ $\\frac{7}{10}$ $(B)$ $\\frac{21}{10}$ $(C)$ $\\frac{7}{5}$ $(D)$ $\\frac{21}{5}$",
     "opts":{"A":"$\\frac{7}{10}$","B":"$\\frac{21}{10}$","C":"$\\frac{7}{5}$","D":"$\\frac{21}{5}$"},"ans":"B"},
    {"no":9,"qtype":"选择题","diff":"中等","kps":["随机变量及其分布"],"score":5,
     "q":"$9.$ 设随机变量 $X$ 服从参数为 $\\mu, \\sigma^2$ 的正态分布，其概率密度为 $f(x)$，则 $\\int_{-\\infty}^{+\\infty} f(x) \\ln f(x) dx$ "
         "$(A)$ 与 $\\mu$ 有关，与 $\\sigma$ 无关 $(B)$ 与 $\\mu$ 有关，与 $\\sigma$ 有关 "
         "$(C)$ 与 $\\mu$ 无关，与 $\\sigma$ 有关 $(D)$ 与 $\\mu$ 无关，与 $\\sigma$ 无关",
     "opts":{"A":"与 $\\mu$ 有关，与 $\\sigma$ 无关","B":"有关","C":"与 $\\mu$ 无关，与 $\\sigma$ 有关","D":"无关"},"ans":"C"},
    {"no":10,"qtype":"选择题","diff":"中等","kps":["参数估计"],"score":5,
     "q":"$10.$ 设总体 $X$ 服从参数为1的指数分布，$X_1,X_2,\\dots,X_n$ 为来自总体 $X$ 的简单随机样本，记 $\\nu_n(1)$ 为 $n$ 个观测值中不大于1的个数，则 $\\frac{\\nu_n(1)}{n}$ 的方差为 "
         "$(A)$ $\\frac{e-1}{ne^2}$ $(B)$ $\\frac{e-1}{ne}$ $(C)$ $\\frac{e(e-1)}{n}$ $(D)$ $\\frac{e-1}{n}$",
     "opts":{"A":"$\\frac{e-1}{ne^2}$","B":"$\\frac{e-1}{ne}$","C":"$\\frac{e(e-1)}{n}$","D":"$\\frac{e-1}{n}$"},"ans":"A"},

    # === FILL-IN (11-16) ===
    {"no":11,"qtype":"填空题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$11.$ 设 $f(x,y)$ 具有二阶连续偏导数，$z = x f(2x, \\frac{y^2}{x})$，则 $\\frac{\\partial^2 z}{\\partial x \\partial y} =$ ______","ans":"$2y f_{12} - \\frac{2y}{x} f_{22}$"},
    {"no":12,"qtype":"填空题","diff":"较难","kps":["重积分"],"score":5,
     "q":"$12.$ 设平面曲线 $z^2 = 2x$ 绕 $x$ 轴旋转一周所得空间曲面 $\\Sigma$ 与平面 $x=1, x=2$ 围成的空间区域为 $\\Omega$，则 $I = \\iiint_{\\Omega} \\frac{1}{x^2 + y^2 + z^2} dv =$ ______","ans":"$2\\pi \\ln 2$"},
    {"no":13,"qtype":"填空题","diff":"中等","kps":["曲线积分与曲面积分"],"score":5,
     "q":"$13.$ 设 $L$ 为圆周 $x^2 + y^2 = 1$，则 $\\oint_L (x^3 + y^2) ds =$ ______","ans":"$\\pi$"},
    {"no":14,"qtype":"填空题","diff":"较难","kps":["曲线积分与曲面积分"],"score":5,
     "q":"$14.$ 设 $I = \\oint_L (2x - \\frac{x^3}{3}) dy + (y + \\frac{1}{6} y^3) dx$，其中 $L$ 为平面上的简单闭曲线，方向为逆时针，若 $I$ 达到最大值，则 $L$ 的表达式为 ______","ans":"$x^2 + y^2 = 1$"},
    {"no":15,"qtype":"填空题","diff":"较难","kps":["向量组与线性空间"],"score":5,
     "q":"$15.$ 设向量组 $\\alpha_1 = \\begin{pmatrix} 1 \\\\ 0 \\\\ -1 \\end{pmatrix}$，$\\alpha_2 = \\begin{pmatrix} a \\\\ 1 \\\\ 1 \\end{pmatrix}$，$\\alpha_3 = \\begin{pmatrix} 2 \\\\ 1 \\\\ 1 \\end{pmatrix}$ 不可由向量组 $\\beta_1 = \\begin{pmatrix} 1 \\\\ 1 \\\\ 2 \\end{pmatrix}$，$\\beta_2 = \\begin{pmatrix} 2 \\\\ 3 \\\\ 7 \\end{pmatrix}$，$\\beta_3 = \\begin{pmatrix} a \\\\ 0 \\\\ -a \\end{pmatrix}$ 线性表示，则 $a$ 的取值范围为 ______","ans":"$a \\neq -2, a \\neq 2$"},
    {"no":16,"qtype":"填空题","diff":"中等","kps":["随机变量及其分布"],"score":5,
     "q":"$16.$ 设随机变量 $X$ 的概率密度为 $f(x) = \\begin{cases} \\frac{x}{2}, & 0 < x < 2 \\\\ 0, & \\text{其他} \\end{cases}$，$F_X(x)$ 是 $X$ 的分布函数，若 $Y = -\\ln[1 - F_X(X)]$，则 $P\\{Y > \\frac{1}{2}\\} =$ ______","ans":"$e^{-\\frac{1}{2}}$"},

    # === SOLUTION (17-22) ===
    {"no":17,"qtype":"解答题","diff":"中等","kps":["定积分"],"score":10,
     "q":"$17.$ (本题满分10分) 求 $f(x) = \\int_0^1 |\\ln|x - t|| dt$（$0 \\le x \\le 1$）的最大值。","ans":"$x = \\frac{1}{2}$ 时最大，最大值为 $\\ln 2$"},
    {"no":18,"qtype":"解答题","diff":"中等","kps":["多元函数微分学"],"score":12,
     "q":"$18.$ (本题满分12分) 设 $f(x,y)$ 满足 $f_x'(x,y) = y(1 + x)e^{x-y}$，$f(1,y) = ye^{1-y}$。求 (1) $f(x,y)$ 的表达式；(2) $f(x,y)$ 的极值。","ans":"(1) $f(x,y) = xy e^{x-y}$; (2) 极大值 $f(-1,-1) = e^{-2}$"},
    {"no":19,"qtype":"解答题","diff":"中等","kps":["中值定理"],"score":12,
     "q":"$19.$ (本题满分12分) 设 $f(x)$ 在 $(a,b)$ 内有定义，且任给 $(a,b)$ 内的 $x_1 < x_2 < x_3$，有 $f(x_2) \\le \\lambda f(x_1) + (1-\\lambda)f(x_3)$，其中 $\\lambda = \\frac{x_3 - x_2}{x_3 - x_1}$。证明：(1) 不等式；(2) $f(x)$ 在 $(a,b)$ 内连续。","ans":"证明略"},
    {"no":20,"qtype":"解答题","diff":"较难","kps":["曲线积分与曲面积分"],"score":12,
     "q":"$20.$ (本题满分12分) 设 $\\Sigma$ 为曲面 $x = y^2 + z^2$（$x \\le 1$）的后侧，计算曲面积分 $I = \\iint_{\\Sigma} (x-1) dy dz + (y-1)^3 dz dx + (z-1)^3 dx dy$。","ans":"$\\frac{\\pi}{2}$"},
    {"no":21,"qtype":"解答题","diff":"较难","kps":["矩阵"],"score":12,
     "q":"$21.$ (本题满分12分) 设 $A = \\begin{pmatrix} 1 & 1 & 0 \\\\ 0 & 1 & 1 \\\\ 1 & 0 & 1 \\end{pmatrix}$，$A^T A = B^2$，其中 $B$ 为正定矩阵。(1) 求 $B$；(2) 证明存在正交矩阵 $C$ 使得 $A = CB$，并求出 $C$。","ans":"$B = \\begin{pmatrix} \\sqrt{2} & \\frac{\\sqrt{2}}{2} & \\frac{\\sqrt{2}}{2} \\\\ \\frac{\\sqrt{2}}{2} & \\sqrt{2} & \\frac{\\sqrt{2}}{2} \\\\ \\frac{\\sqrt{2}}{2} & \\frac{\\sqrt{2}}{2} & \\sqrt{2} \\end{pmatrix}$"},
    {"no":22,"qtype":"解答题","diff":"较难","kps":["参数估计"],"score":12,
     "q":"$22.$ (本题满分12分) 设 $X$ 服从参数为 $\\frac{2}{\\theta}$ 的指数分布，在 $X = x (x > 0)$ 的条件下，$Y$ 服从条件概率密度 $f_{Y|X}(y|x) = \\frac{1}{\\theta} e^{-\\frac{y-x}{\\theta}}, 0 < x < y$。$(X_1,Y_1),\\dots,(X_n,Y_n)$ 是简单随机样本。(1) 求 $\\theta$ 的最大似然估计量；(2) 计算 $D(\\hat{\\theta})$。","ans":"(1) $\\hat{\\theta} = \\frac{2}{n} \\sum_{i=1}^n (Y_i - X_i)$; (2) $D(\\hat{\\theta}) = \\frac{4\\theta^2}{n}$"},
]

total = 0
for q in Q:
    qid = f"2026-宇哥-{vol}-{q['no']:03d}"
    if db.get(qid):
        print(f"  Skip: {qid}")
        continue

    item = {
        "question_id": qid, "year": 2026, "category": cat, "volume": vol,
        "question_type": q["qtype"], "question_no": q["no"],
        "score": q["score"], "difficulty": q["diff"],
        "knowledge_points": q["kps"], "tags": q["kps"],
        "question": q["q"], "source": "import_zhangyu_v2",
    }
    if q["qtype"] == "选择题":
        item["options"] = q["opts"]
        item["correct_option"] = q["ans"]
        item["standard_answer"] = q["ans"]
    else:
        item["standard_answer"] = q["ans"]

    r = db.insert(item)
    if r["success"]:
        total += 1
        print(f"  OK: {r['question_id']} ({q['qtype']} #{q['no']})")
    else:
        print(f"  FAIL: #{q['no']} — {r.get('warnings',[])}")

print(f"\nImported: {total}, DB now: {db.stats()['total']}")
