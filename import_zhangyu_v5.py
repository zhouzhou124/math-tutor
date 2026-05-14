"""Import Zhang Yu Volume 5."""
import json
from pathlib import Path

SIMUL_DIR = Path('storage/questions/simulations')
INDEX_PATH = Path('storage/questions/_index.json')
vol = "卷五"

Q = [
    {"no":1,"qtype":"选择题","diff":"中等","kps":["极限"],"score":5,
     "q":"$1.$ 设 $f(\\frac{1}{x}) = x + \\sqrt{1 + x^2}$ ($x \\neq 0$)，则 $x = 0$ 是 $f(x)$ 的 "
         "$(A)$ 连续点 $(B)$ 跳跃间断点 $(C)$ 可去间断点 $(D)$ 第二类间断点",
     "opts":{"A":"连续点","B":"跳跃间断点","C":"可去间断点","D":"第二类间断点"},"ans":"C"},
    {"no":2,"qtype":"选择题","diff":"中等","kps":["多元函数微分学"],"score":5,
     "q":"$2.$ 设 $f(x,y) = x^2 + y^2(1 + x^3)$，则 "
         "$(A)$ 点 $(0,0)$ 是唯一极小值点也是最大值点 $(B)$ 点 $(0,0)$ 是唯一极大值点也是最小值点 "
         "$(C)$ 点 $(0,0)$ 是唯一极值点但不是最大值点 $(D)$ 点 $(0,0)$ 是唯一极小值点但不是最大值点",
     "opts":{"A":"极小且最大","B":"极大且最小","C":"极值非最大","D":"极小非最大"},"ans":"D"},
    {"no":3,"qtype":"选择题","diff":"中等","kps":["极限"],"score":5,
     "q":"$3.$ 若 $\\{x_n\\}, \\{y_n\\}$ 满足 $\\lim_{n\\to\\infty} x_n y_n = \\infty$，则：$\\textcircled{1}$ $\\lim x_n=\\infty$ 或 $\\lim y_n=\\infty$；$\\textcircled{2}$ 都趋于无穷；$\\textcircled{3}$ 一个是无穷大另一个是无界量；$\\textcircled{4}$ 当 $x_n$ 是非零无穷小时 $\\lim y_n=\\infty$。正确个数为 "
         "$(A)$ $1$ $(B)$ $2$ $(C)$ $3$ $(D)$ $4$",
     "opts":{"A":"1","B":"2","C":"3","D":"4"},"ans":"A"},
    {"no":4,"qtype":"选择题","diff":"较难","kps":["无穷级数"],"score":5,
     "q":"$4.$ 设 $\\{a_n\\},\\{b_n\\}$ 满足 $0\\le a_{n+1}\\le a_n+b_n$，则 $\\{a_n\\}$ 收敛是 $\\sum b_n$ 收敛的 "
         "$(A)$ 充分非必要 $(B)$ 必要非充分 $(C)$ 充要 $(D)$ 既不充分也不必要",
     "opts":{"A":"充分非必要","B":"必要非充分","C":"充要","D":"既不充分也不必要"},"ans":"B"},
    {"no":5,"qtype":"选择题","diff":"中等","kps":["二次型"],"score":5,
     "q":"$5.$ 设二次型 $f=4x_1^2+x_2^2+ax_3^2+2x_1x_2-4x_1x_3+2x_2x_3$ 与 $g=2y_1^2+by_2^2$ 合同，则 "
         "$(A)$ $a=3,b>0$ $(B)$ $a=3,b<0$ $(C)$ $a=4,b>0$ $(D)$ $a=4,b<0$",
     "opts":{"A":"$a=3,b>0$","B":"$a=3,b<0$","C":"$a=4,b>0$","D":"$a=4,b<0$"},"ans":"A"},
    {"no":6,"qtype":"选择题","diff":"较难","kps":["线性方程组"],"score":5,
     "q":"$6.$ 设 $A,B$ 为 $n$ 阶矩阵且 $A^2-A=3E$，则与 $\\binom{A}{B}x=0$ 不一定同解的是 "
         "$(A)$ $\\binom{A-B}{A+AB}x=0$ $(B)$ $\\binom{A+B}{A+AB-B}x=0$ "
         "$(C)$ $\\binom{A-B}{2A+B}x=0$ $(D)$ $\\binom{A+B}{BA+B^2}x=0$",
     "opts":{"A":"A","B":"B","C":"C","D":"D"},"ans":"D"},
    {"no":7,"qtype":"选择题","diff":"较难","kps":["矩阵"],"score":5,
     "q":"$7.$ 设 $A=\\begin{pmatrix}1&0&a\\\\b&2&0\\\\0&c&3\\end{pmatrix}$，$abc=-6$，则 $A^*$ 有非零特征值 "
         "$(A)$ $-8$ $(B)$ $8$ $(C)$ $-11$ $(D)$ $11$",
     "opts":{"A":"$-8$","B":"$8$","C":"$-11$","D":"$11$"},"ans":"C"},
    {"no":8,"qtype":"选择题","diff":"中等","kps":["随机变量及其分布"],"score":5,
     "q":"$8.$ 设 $X,Y$ 独立且与 $X+Y$ 同分布，则一定可以成立的是 "
         "$(A)$ 均匀分布 $(B)$ 泊松分布 $(C)$ 指数分布 $(D)$ 二项分布",
     "opts":{"A":"均匀分布","B":"泊松分布","C":"指数分布","D":"二项分布"},"ans":"B"},
    {"no":9,"qtype":"选择题","diff":"中等","kps":["随机变量的数字特征"],"score":5,
     "q":"$9.$ 设 $X_1,\\dots,X_n$ 来自 $X\\sim B(1,\\frac{1}{5})$，若 $E[(\\overline{X}-\\frac{1}{5})^2]<0.01$，则 $n$ 最小为 "
         "$(A)$ $17$ $(B)$ $18$ $(C)$ $19$ $(D)$ $20$",
     "opts":{"A":"17","B":"18","C":"19","D":"20"},"ans":"B"},
    {"no":10,"qtype":"选择题","diff":"较难","kps":["随机事件与概率"],"score":5,
     "q":"$10.$ 已知 $0<P(A)<1$ 且 $P(B+C\\mid A)=P(B\\mid A)+P(C\\mid A)$，则正确结论个数为 "
         "$(A)$ $1$ $(B)$ $2$ $(C)$ $3$ $(D)$ $4$",
     "opts":{"A":"1","B":"2","C":"3","D":"4"},"ans":"A"},

    {"no":11,"qtype":"填空题","diff":"基础","kps":["极限"],"score":5,
     "q":"$11.$ $\\lim_{x\\to0}\\frac{\\sqrt{1+2x}-\\sqrt[3]{1+3x}}{\\ln(1+x^2)} =$ ______","ans":"$\\frac{1}{2}$"},
    {"no":12,"qtype":"填空题","diff":"中等","kps":["常微分方程"],"score":5,
     "q":"$12.$ 微分方程 $y'=\\frac{1}{xy(1+xy^2)}$ 满足 $y(1)=0$ 的解为 ______","ans":"$y^2=2\\ln\\frac{x+1}{x}-1$"},
    {"no":13,"qtype":"填空题","diff":"中等","kps":["向量与空间解析几何"],"score":5,
     "q":"$13.$ 设 $F=|x|\\cos y\\bm{i}-y\\sin z\\bm{j}+z\\bm{k}$，则 $\\operatorname{rot}F(1,1,0)=$ ______","ans":"$(0,0,0)$"},
    {"no":14,"qtype":"填空题","diff":"中等","kps":["极限"],"score":5,
     "q":"$14.$ $\\lim_{n\\to\\infty}\\sum_{i=1}^n\\frac{1}{\\sqrt{in}} =$ ______","ans":"$2$"},
    {"no":15,"qtype":"填空题","diff":"中等","kps":["矩阵"],"score":5,
     "q":"$15.$ 设 $A=\\begin{pmatrix}1&1\\\\0&1\\end{pmatrix},B=\\begin{pmatrix}-1&1\\\\0&-1\\end{pmatrix}$，则 $A^9-B^9=$ ______","ans":"$\\begin{pmatrix}18&0\\\\0&18\\end{pmatrix}$"},
    {"no":16,"qtype":"填空题","diff":"较难","kps":["随机变量及其分布"],"score":5,
     "q":"$16.$ 设 $X\\sim N(0,\\sigma^2)$，使 $P\\{\\frac{1}{e^2}<X<e\\}$ 最大的 $\\sigma^2=$ ______","ans":"$2$"},

    {"no":17,"qtype":"解答题","diff":"中等","kps":["重积分"],"score":10,
     "q":"$17.$ (10分) 设 $f$ 在 $D=\\{x^2+y^2\\le1\\}$ 上连续，$f=e^{x^2+y^2}-\\iint_D\\frac{(2x^2+1)f}{x^2+y^2+1}dxdy$，求 $\\iint_D f dxdy$。","ans":"$\\frac{\\pi}{3}(e-1)$"},
    {"no":18,"qtype":"解答题","diff":"中等","kps":["常微分方程"],"score":12,
     "q":"$18.$ (12分) $y=y(x)$ 满足 $(xy-1)dx+x^2dy=0,x>0,y(1)=0$。(1) 求 $y(x)$；(2) 求拐点和渐近线。","ans":"(1) $y=\\frac{1}{x}(1-e^{x-1})$; (2) 拐点$x=1$,渐近线$x=0,y=0$"},
    {"no":19,"qtype":"解答题","diff":"中等","kps":["中值定理"],"score":12,
     "q":"$19.$ (12分) $f$ 在 $[a,b]$ 可导，$c\\in(a,b)$。证：(1) $\\exists\\xi\\in(a,c),f(c)-f(a)=f'(\\xi)(c-a)$；(2) $\\exists\\eta\\in(a,b),f(b)-f(a)=f'(\\eta)(b-a)$ 且 $\\eta>\\xi$。","ans":"证明略"},
    {"no":20,"qtype":"解答题","diff":"较难","kps":["曲线积分与曲面积分"],"score":12,
     "q":"$20.$ (12分) 锥面 $\\Sigma$ 顶点为原点，准线 $\\Gamma:\\{z=y^2,x=1\\}(|y|\\le1)$。(1) 求 $\\Sigma$ 方程；(2) 计算 $I=\\iint_{\\Sigma}2x^2dydz+xydzdx+(z+1)dxdy$，取上侧。","ans":"(1) $z=y^2/x^2$; (2) $4/3$"},
    {"no":21,"qtype":"解答题","diff":"中等","kps":["向量组与线性空间"],"score":12,
     "q":"$21.$ (12分) $\\alpha_1=(1,0,1)^T,\\alpha_2=(0,1,1)^T,\\alpha_3=(1,1,0)^T$。(1) 正交单位化为 $\\gamma_1,\\gamma_2,\\gamma_3$；(2) 若 $(\\alpha_1,\\alpha_2,\\alpha_3)=(\\gamma_1,\\gamma_2,\\gamma_3)C$，求 $C$。","ans":"见解析"},
    {"no":22,"qtype":"解答题","diff":"较难","kps":["参数估计"],"score":12,
     "q":"$22.$ (12分) $X$ 密度 $f(x;b)=ae^{-2(x-b)},x\\ge b$。$X_1,\\dots,X_n$ 样本。(1) 求 $a$；(2) 求矩估计和MLE；(3) MLE是否无偏？","ans":"(1) $a=2$; (2) $\\hat{b}_M=\\overline{X}-1/2,\\hat{b}_L=X_{(1)}$; (3) 不是"},
]

for q in Q:
    qid = f"26宇哥八套卷-{vol}-{q['no']:03d}"
    item = {"question_id":qid,"year":2026,"category":"26宇哥八套卷","volume":vol,
            "question_type":q["qtype"],"question_no":q["no"],"score":q["score"],
            "difficulty":q["diff"],"knowledge_points":q["kps"],"tags":q["kps"],
            "question":q["q"],"source":"import_v5"}
    if q["qtype"]=="选择题":
        item["options"]=q["opts"]; item["correct_option"]=q["ans"]; item["standard_answer"]=q["ans"]
    else:
        item["standard_answer"]=q["ans"]
    json.dump(item, open(SIMUL_DIR/f"{qid}.json",'w',encoding='utf-8'), ensure_ascii=False, indent=2)

# Rebuild
idx = {"categories":{},"knowledge_index":{},"difficulty_index":{},"metadata":{"total_questions":0}}
for d in [Path('storage/questions/exams'), SIMUL_DIR]:
    if not d.exists(): continue
    for fp in sorted(d.glob("*.json")):
        q = json.load(open(fp, encoding='utf-8'))
        qid = q.get("question_id", fp.stem)
        cat = q.get("category",""); sub = q.get("volume","") or str(q.get("year",""))
        qt = q.get("question_type",""); diff = q.get("difficulty","")
        kps = q.get("knowledge_points",[]) or q.get("tags",[])
        cd = idx["categories"].setdefault(cat,{})
        sd = cd.setdefault(sub,{})
        tl = sd.setdefault(qt,[])
        if qid not in tl: tl.append(qid)
        for kp in kps:
            kl = idx["knowledge_index"].setdefault(kp,[])
            if qid not in kl: kl.append(qid)
        if diff:
            dl = idx["difficulty_index"].setdefault(diff,[])
            if qid not in dl: dl.append(qid)

t = sum(len(ids) for cd in idx["categories"].values() for sd in cd.values() for ids in sd.values() if isinstance(ids,list))
idx["metadata"]["total_questions"] = t
json.dump(idx, open(INDEX_PATH,'w',encoding='utf-8'), ensure_ascii=False, indent=2)
print(f"Volume 5: 22 imported. Total: {t}")
