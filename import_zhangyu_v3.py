"""Import Zhang Yu 8-exam-set Volume 3."""
import json
from pathlib import Path

SIMUL_DIR = Path('storage/questions/simulations')
INDEX_PATH = Path('storage/questions/_index.json')
vol = "卷三"

Q = [
    {"no":1,"qtype":"选择题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$1.$ 设 $f(x,y) = \\begin{cases} (y - e^{-\\frac{1}{x^2}})(y - 3e^{-\\frac{1}{x^2}}), & x \\neq 0, \\\\ y^2, & x = 0, \\end{cases}$ 则点 $(0,0)$ "
         "$(A)$ 是 $f(x,x)$ 的极小值点，也是 $f(x,y)$ 的极小值点 "
         "$(B)$ 是 $f(x,x)$ 的极小值点，不是 $f(x,y)$ 的极小值点 "
         "$(C)$ 不是 $f(x,x)$ 的极小值点，是 $f(x,y)$ 的极小值点 "
         "$(D)$ 不是 $f(x,x)$ 的极小值点，也不是 $f(x,y)$ 的极小值点",
     "opts":{"A":"都是极小值点","B":"是$f(x,x)$不是$f(x,y)$","C":"不是$f(x,x)$是$f(x,y)$","D":"都不是"},"ans":"B"},
    {"no":2,"qtype":"选择题","diff":"中等","kps":["定积分"],"score":5,
     "q":"$2.$ 设函数 $f(x)$ 具有二阶导数，$f'(x) > 0, f''(x) < 0$，记 $I_1 = \\int_{-\\pi}^{\\pi} f(x) \\sin x dx, I_2 = \\int_{-\\pi}^{\\pi} f(x) \\cos x dx$，则 "
         "$(A)$ $I_1 > 0, I_2 < 0$ $(B)$ $I_1 < 0, I_2 > 0$ $(C)$ $I_1 < 0, I_2 < 0$ $(D)$ $I_1 > 0, I_2 > 0$",
     "opts":{"A":"$I_1>0,I_2<0$","B":"$I_1<0,I_2>0$","C":"都小于0","D":"都大于0"},"ans":"D"},
    {"no":3,"qtype":"选择题","diff":"较难","kps":["常微分方程"],"score":5,
     "q":"$3.$ 已知 $y'(x) + \\frac{a}{x} y(x) = \\frac{\\sin x}{x^a} (x > 0)$ 的解均有界，且 $\\lim_{x \\to 0^+} y(x) = 0$，则 $a$ 的取值范围是 "
         "$(A)$ $(0,1)$ $(B)$ $(0,1]$ $(C)$ $[1,2)$ $(D)$ $(1,2]$",
     "opts":{"A":"$(0,1)$","B":"$(0,1]$","C":"$[1,2)$","D":"$(1,2]$"},"ans":"D"},
    {"no":4,"qtype":"选择题","diff":"中等","kps":["无穷级数"],"score":5,
     "q":"$4.$ 设 $p$ 为常数，若级数 $\\sum_{n=1}^\\infty \\frac{(\\sqrt{n+1} - \\sqrt{n})^p}{n}$ 与 $\\sum_{n=1}^\\infty [\\frac{1}{n^p} - \\frac{1}{(n+1)^p}]$ 均收敛，则 "
         "$(A)$ $-2 < p \\le -1$ $(B)$ $-1 \\le p < 0$ $(C)$ $-1 < p \\le 0$ $(D)$ $p > 0$",
     "opts":{"A":"$-2<p\\le-1$","B":"$-1\\le p<0$","C":"$-1<p\\le0$","D":"$p>0$"},"ans":"A"},
    {"no":5,"qtype":"选择题","diff":"中等","kps":["矩阵"],"score":5,
     "q":"$5.$ 设 $A = \\begin{pmatrix} a_{11} & a_{12} & a_{13} \\\\ a_{21} & a_{22} & a_{23} \\\\ a_{31} & a_{32} & a_{33} \\end{pmatrix}$，$B = \\begin{pmatrix} a_{21} & a_{22} & a_{23} \\\\ a_{11} & a_{12} & a_{13} \\\\ a_{31}+a_{11} & a_{32}+a_{12} & a_{33}+a_{13} \\end{pmatrix}$，$P_1 = \\begin{pmatrix} 0 & 1 & 0 \\\\ 1 & 0 & 0 \\\\ 0 & 0 & 1 \\end{pmatrix}$，$P_2 = \\begin{pmatrix} 1 & 0 & 1 \\\\ 0 & 1 & 0 \\\\ 0 & 0 & 1 \\end{pmatrix}$，则 "
         "$(A)$ $A P_1^9 P_2^T = B$ $(B)$ $A P_2^T P_1^9 = B$ $(C)$ $P_1^9 P_2^T A = B$ $(D)$ $P_2^T P_1^9 A = B$",
     "opts":{"A":"$AP_1^9P_2^T=B$","B":"$AP_2^TP_1^9=B$","C":"$P_1^9P_2^TA=B$","D":"$P_2^TP_1^9A=B$"},"ans":"B"},
    {"no":6,"qtype":"选择题","diff":"较难","kps":["线性方程组"],"score":5,
     "q":"$6.$ 设 3 阶矩阵 $A,B$ 满足 $r(BA) < r(AB)$，对于以下结论：$\\textcircled{1} ABx = 0$ 与 $BAx = 0$ 有非零公共解；$\\textcircled{2} ABAx = 0$ 与 $BABx = 0$ 有非零公共解。正确的说法是 "
         "$(A)$ $\\textcircled{1}$正确，$\\textcircled{2}$正确 $(B)$ $\\textcircled{1}$正确，$\\textcircled{2}$错误 $(C)$ $\\textcircled{1}$错误，$\\textcircled{2}$正确 $(D)$ $\\textcircled{1}$错误，$\\textcircled{2}$错误",
     "opts":{"A":"均正确","B":"1正确2错误","C":"1错误2正确","D":"均错误"},"ans":"A"},
    {"no":7,"qtype":"选择题","diff":"中等","kps":["二次型"],"score":5,
     "q":"$7.$ 设 $A$ 为 $n$ 阶方阵，有下列结论：$\\textcircled{1}$ 若 $A$ 的全部顺序主子式为正，则 $A$ 正定；$\\textcircled{2}$ 若 $A$ 相似于对角矩阵 $\\Lambda$，则 $A$ 与 $\\Lambda$ 合同；$\\textcircled{3}$ 若 $A$ 与正定矩阵合同，则 $A$ 为正定矩阵。则正确结论的个数为 "
         "$(A)$ $0$ $(B)$ $1$ $(C)$ $2$ $(D)$ $3$",
     "opts":{"A":"$0$","B":"$1$","C":"$2$","D":"$3$"},"ans":"B"},
    {"no":8,"qtype":"选择题","diff":"较难","kps":["随机变量的数字特征"],"score":5,
     "q":"$8.$ 设 $X_1,X_2,\\dots,X_{10}$ 是来自标准正态总体 $X$ 的简单随机样本，$Y = \\frac{9}{10}(X_{10} - \\frac{1}{9}\\sum_{i=1}^9 X_i)^2$，则 $D(Y) =$ "
         "$(A)$ $2$ $(B)$ $1$ $(C)$ $\\frac{1}{100}$ $(D)$ $\\frac{81}{100}$",
     "opts":{"A":"$2$","B":"$1$","C":"$1/100$","D":"$81/100$"},"ans":"A"},
    {"no":9,"qtype":"选择题","diff":"中等","kps":["随机变量及其分布"],"score":5,
     "q":"$9.$ 设随机变量 $X$ 的概率分布为 $P(X=1)=a, P(X=2)=1-a$。在给定 $X=i$ 的条件下，$Y \\sim U(0,i)(i=1,2)$，且当 $0 \\le y < 1$ 时，$F_Y(y)=\\frac{2}{3}y$，则 $a=$ "
         "$(A)$ $\\frac{1}{3}$ $(B)$ $\\frac{2}{3}$ $(C)$ $\\frac{1}{2}$ $(D)$ $\\frac{1}{4}$",
     "opts":{"A":"$1/3$","B":"$2/3$","C":"$1/2$","D":"$1/4$"},"ans":"B"},
    {"no":10,"qtype":"选择题","diff":"较难","kps":["参数估计"],"score":5,
     "q":"$10.$ 设 $(X_1,Y_1),\\dots,(X_n,Y_n)$ 来自总体 $(X,Y) \\sim f(x,y) = \\frac{1}{2\\theta^2} e^{-\\frac{2x+y}{2\\theta}}, x>0,y>0$。记 $\\overline{X} = \\frac{1}{n}\\sum X_i$，$\\overline{Y} = \\frac{1}{n}\\sum Y_j$，则 $\\hat{\\theta}$ 与 $D(\\hat{\\theta})$ 分别为 "
         "$(A)$ $\\overline{X}+\\frac{\\overline{Y}}{2}, \\frac{\\theta^2}{4n}$ $(B)$ $\\frac{\\overline{X}}{2}+\\frac{\\overline{Y}}{4}, \\frac{\\theta^2}{2n}$ $(C)$ $\\overline{X}+\\frac{\\overline{Y}}{2}, \\frac{\\theta^2}{2n}$ $(D)$ $\\frac{\\overline{X}}{2}+\\frac{\\overline{Y}}{4}, \\frac{\\theta^2}{4n}$",
     "opts":{"A":"$\\bar{X}+\\bar{Y}/2,\\theta^2/4n$","B":"$\\bar{X}/2+\\bar{Y}/4,\\theta^2/2n$","C":"$\\bar{X}+\\bar{Y}/2,\\theta^2/2n$","D":"$\\bar{X}/2+\\bar{Y}/4,\\theta^2/4n$"},"ans":"D"},

    {"no":11,"qtype":"填空题","diff":"中等","kps":["一元函数微分学"],"score":5,
     "q":"$11.$ 若 $\\begin{cases} x = \\ln |t|, \\\\ y = e^{-t^2}, \\end{cases}$ 则 $\\left.\\frac{d^2y}{dx^2}\\right|_{t=\\sqrt{2}} =$ ______","ans":"$8e^{-2}(2\\ln 2 - 1)$"},
    {"no":12,"qtype":"填空题","diff":"中等","kps":["常微分方程"],"score":5,
     "q":"$12.$ 微分方程 $dy = \\cos(y-x)dx$ 满足 $y(0) = \\frac{\\pi}{2}$ 的解为 ______","ans":"$y = \\frac{\\pi}{2}$"},
    {"no":13,"qtype":"填空题","diff":"较难","kps":["重积分"],"score":5,
     "q":"$13.$ 设 $\\Omega$ 是由上半球面 $z = \\sqrt{4 - x^2 - y^2}$ 与曲面 $x^2 + y^2 = 3z$ 所围成的空间有界闭区域，则 $\\Omega$ 的形心竖坐标 $\\bar{z} =$ ______","ans":"$\\frac{5}{6}$"},
    {"no":14,"qtype":"填空题","diff":"较难","kps":["曲线积分与曲面积分"],"score":5,
     "q":"$14.$ 设 $\\Sigma = \\{(x,y,z) \\mid x^2 + y^2 + z^2 = 1, x \\ge 0, y \\ge 0\\}$，指向右侧，则 $\\iint_{\\Sigma} xyz dz dy =$ ______","ans":"$\\frac{1}{12}$"},
    {"no":15,"qtype":"填空题","diff":"较难","kps":["矩阵"],"score":5,
     "q":"$15.$ 设 $A = \\begin{pmatrix} a & 2 & 0 \\\\ 0 & 4 & 0 \\\\ 0 & 1 & 1 \\end{pmatrix}$ 与 $B = \\begin{pmatrix} 2 & b & c \\\\ c & 2 & b \\\\ b & c & 2 \\end{pmatrix}$ 相似，则实向量 $(a,b,c) =$ ______","ans":"$(2,2,2)$"},
    {"no":16,"qtype":"填空题","diff":"基础","kps":["随机变量及其分布"],"score":5,
     "q":"$16.$ 设有 40 个盒子，100 个球，每个球等可能地放入任一盒子中，则指定某一个盒子中最有可能出现的球的个数为 ______","ans":"$2$"},

    {"no":17,"qtype":"解答题","diff":"中等","kps":["一元函数微分学"],"score":10,
     "q":"$17.$ (本题满分10分) 求曲线 $y = x^3(e^x + e^{-x} - 2)$ 的全部渐近线。","ans":"水平渐近线 $y=0$"},
    {"no":18,"qtype":"解答题","diff":"中等","kps":["多元函数微分学"],"score":12,
     "q":"$18.$ (本题满分12分) 求函数 $f(x,y) = x^2(2x^2 - 4y - \\frac{1}{7}x^5) + y^2$ 的极值。","ans":"极小值 $f(0,0)=0$"},
    {"no":19,"qtype":"解答题","diff":"较难","kps":["中值定理"],"score":12,
     "q":"$19.$ (本题满分12分) 设 $f(x)$ 在 $[0,1]$ 上二阶可导，$|f''(x)| \\le M, x \\in [0,1], M>0, f(0)=f(1)=0$。证明：(1) $|f'(x)| \\le \\frac{M}{2}$；(2) 若 $f(\\frac{1}{2})=0$，则 $|f'(x)| < \\frac{M}{2}$。","ans":"证明略"},
    {"no":20,"qtype":"解答题","diff":"较难","kps":["曲线积分与曲面积分"],"score":12,
     "q":"$20.$ (本题满分12分) 设 $f(x)$ 具有一阶连续导数，且对右半平面内任意分段光滑简单闭曲线 $L$，均有 $\\oint_L \\frac{f(x)y^2 dy - y^3 dx}{2x^2 + y^6} = 0$。(1) 求 $f(x)$；(2) 计算 $L_0$ 上的积分。","ans":"(1) $f(x)=\\frac{1}{x}$; (2) $0$"},
    {"no":21,"qtype":"解答题","diff":"较难","kps":["二次型"],"score":12,
     "q":"$21.$ (本题满分12分) 设 $f(x) = (\\alpha^T x)^2 + k(\\beta^T x)^2$ 的二次型矩阵的迹为 3，$\\alpha=(\\frac{1}{\\sqrt{2}},0,-\\frac{1}{\\sqrt{2}})^T$，$\\beta=(\\frac{1}{\\sqrt{3}},\\frac{1}{\\sqrt{3}},\\frac{1}{\\sqrt{3}})^T$。(1) 求 $k$ 和正交矩阵 $Q$；(2) 求 $P$ 使 $f(x)=(Px)^T Px$。","ans":"(1) $k=3$; (2) 见解析"},
    {"no":22,"qtype":"解答题","diff":"较难","kps":["随机变量的数字特征"],"score":12,
     "q":"$22.$ (本题满分12分) 设 $X \\sim U(0,1)$，当 $X=x$ 时 $Y \\sim B(2,x)$，求 (1) $P\\{Y=k\\mid X=x\\}$；(2) $\\rho_{XY}$。","ans":"(1) $\\binom{2}{k}x^k(1-x)^{2-k}$; (2) $\\rho_{XY}=\\frac{\\sqrt{6}}{3}$"},
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
        "question": q["q"], "source": "import_v3",
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
index = {"categories":{"metadata":{"total_questions":0}},"knowledge_index":{},"difficulty_index":{},"metadata":{"total_questions":0}}
EXAM_DIR = Path('storage/questions/exams')
for d in [EXAM_DIR, SIMUL_DIR]:
    if not d.exists(): continue
    for f in sorted(d.glob("*.json")):
        with open(f, 'r', encoding='utf-8') as fp:
            q = json.load(fp)
        qid = q.get("question_id", f.stem)
        cat = q.get("category", "")
        qtype = q.get("question_type", "")
        vol2 = q.get("volume", "") or str(q.get("year", ""))
        diff = q.get("difficulty", "")
        kps = q.get("knowledge_points", []) or q.get("tags", [])

        cd = index["categories"].setdefault(cat, {"metadata":{"total_questions":0}})
        sd = cd.setdefault(vol2, {"metadata":{"total_questions":0}})
        tl = sd.setdefault(qtype, [])
        if qid not in tl: tl.append(qid)

        for kp in kps:
            kl = index["knowledge_index"].setdefault(kp, [])
            if qid not in kl: kl.append(qid)

        if diff:
            dl = index["difficulty_index"].setdefault(diff, [])
            if qid not in dl: dl.append(qid)

total_q = 0
for cat_name, cat_data in index["categories"].items():
    if cat_name == "metadata": continue
    for sub_key, sub_data in cat_data.items():
        if sub_key == "metadata": continue
        for type_key, ids in sub_data.items():
            if isinstance(ids, list): total_q += len(ids)
index["metadata"]["total_questions"] = total_q

with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f"\nVolume 3: {total} imported, Total: {total_q}")
