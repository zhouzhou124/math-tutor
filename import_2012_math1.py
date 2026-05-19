"""Import 2012 Math I exam questions into the database."""
import sys, os, json, re

sys.path.insert(0, os.path.dirname(__file__))
from database.question_db import QuestionDB

db = QuestionDB()

# ── 选择题 ──
choices_q = [
    {
        "number": 1,
        "question": r"曲线 $y = \frac{x^2 + x}{x^2 - 1}$ 的渐近线的条数为",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "D",
        "standard_answer": "D",
    },
    {
        "number": 2,
        "question": r"设函数 $f(x) = (e^x - 1)(e^{2x} - 2)\cdots(e^{nx} - n)$，其中 $n$ 为正整数，则 $f'(0) =$",
        "options": {"A": r"$(-1)^{n-1}(n-1)!$", "B": r"$(-1)^n(n-1)!$", "C": r"$(-1)^{n-1}n!$", "D": r"$(-1)^n n!$"},
        "correct_option": "A",
        "standard_answer": "A",
    },
    {
        "number": 3,
        "question": r"如果函数 $f(x,y)$ 在点 $(0,0)$ 处连续，那么下列命题正确的是",
        "options": {
            "A": r"若极限 $\lim_{(x,y)\to(0,0)} \frac{f(x,y)}{|x|+|y|}$ 存在，则 $f(x,y)$ 在点 $(0,0)$ 处可微",
            "B": r"若极限 $\lim_{(x,y)\to(0,0)} \frac{f(x,y)}{x^2+y^2}$ 存在，则 $f(x,y)$ 在点 $(0,0)$ 处可微",
            "C": r"若 $f(x,y)$ 在点 $(0,0)$ 处可微，则极限 $\lim_{(x,y)\to(0,0)} \frac{f(x,y)}{|x|+|y|}$ 存在",
            "D": r"若 $f(x,y)$ 在点 $(0,0)$ 处可微，则极限 $\lim_{(x,y)\to(0,0)} \frac{f(x,y)}{x^2+y^2}$ 存在"
        },
        "correct_option": "B",
        "standard_answer": "B",
    },
    {
        "number": 4,
        "question": r"设 $I_k = \int_0^{k\pi} e^{x^2} \sin x dx$ ($k=1,2,3$)，则有",
        "options": {"A": r"$I_1 < I_2 < I_3$", "B": r"$I_3 < I_2 < I_1$", "C": r"$I_2 < I_3 < I_1$", "D": r"$I_2 < I_1 < I_3$"},
        "correct_option": "D",
        "standard_answer": "D",
    },
    {
        "number": 5,
        "question": r"设 $\alpha_1 = \begin{pmatrix} 0 \\ 0 \\ c_1 \end{pmatrix}$，$\alpha_2 = \begin{pmatrix} 0 \\ 1 \\ c_2 \end{pmatrix}$，$\alpha_3 = \begin{pmatrix} 1 \\ -1 \\ c_3 \end{pmatrix}$，$\alpha_4 = \begin{pmatrix} -1 \\ 1 \\ c_4 \end{pmatrix}$，其中 $c_1,c_2,c_3,c_4$ 为任意常数，则下列向量组线性相关的为",
        "options": {"A": r"$\alpha_1,\alpha_2,\alpha_3$", "B": r"$\alpha_1,\alpha_2,\alpha_4$", "C": r"$\alpha_1,\alpha_3,\alpha_4$", "D": r"$\alpha_2,\alpha_3,\alpha_4$"},
        "correct_option": "C",
        "standard_answer": "C",
    },
    {
        "number": 6,
        "question": r"设 $A$ 为 3 阶矩阵，$P$ 为 3 阶可逆矩阵，且 $P^{-1}AP = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2 \end{pmatrix}$。若 $P = (\alpha_1,\alpha_2,\alpha_3)$，$Q = (\alpha_1 + \alpha_2,\alpha_2,\alpha_3)$，则 $Q^{-1}AQ =$",
        "options": {
            "A": r"$\begin{pmatrix} 1 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 1 \end{pmatrix}$",
            "B": r"$\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2 \end{pmatrix}$",
            "C": r"$\begin{pmatrix} 2 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2 \end{pmatrix}$",
            "D": r"$\begin{pmatrix} 2 & 0 & 0 \\ 0 & 2 & 0 \\ 0 & 0 & 1 \end{pmatrix}$"
        },
        "correct_option": "A",
        "standard_answer": "A",
    },
    {
        "number": 7,
        "question": r"设随机变量 $X$ 与 $Y$ 相互独立，且分别服从参数为 1 与参数为 4 的指数分布，则 $P\{X<Y\} =$",
        "options": {"A": r"$\frac{1}{5}$", "B": r"$\frac{1}{3}$", "C": r"$\frac{2}{3}$", "D": r"$\frac{4}{5}$"},
        "correct_option": "A",
        "standard_answer": "A",
    },
    {
        "number": 8,
        "question": r"将长度为 $1\,\text{m}$ 的木棒随机地截成两段，则两段长度的相关系数为",
        "options": {"A": "1", "B": r"$\frac{1}{2}$", "C": r"$-\frac{1}{2}$", "D": "$-1$"},
        "correct_option": "D",
        "standard_answer": "D",
    },
]

# ── 填空题 ──
fill_q = [
    {
        "number": 9,
        "question": r"若函数 $f(x)$ 满足方程 $f''(x) + f'(x) - 2f(x) = 0$ 及 $f''(x) + f(x) = 2e^x$，则 $f(x) =$ ______",
        "standard_answer": r"$e^x - e^{-2x}$",
    },
    {
        "number": 10,
        "question": r"$\int_0^2 x\sqrt{2x - x^2} dx =$ ______",
        "standard_answer": r"$\frac{\pi}{2}$",
    },
    {
        "number": 11,
        "question": r"$\operatorname{grad}\left( xy + \frac{z}{y} \right)\bigg|_{(2,1,1)} =$ ______",
        "standard_answer": r"$(1,1,-1)$",
    },
    {
        "number": 12,
        "question": r"设 $\Sigma = \{(x,y,z) \mid x+y+z=1, x\ge 0, y\ge 0, z\ge 0\}$，则 $\iint_\Sigma y^2 dS =$ ______",
        "standard_answer": r"$\frac{\sqrt{3}}{12}$",
    },
    {
        "number": 13,
        "question": r"设 $\alpha$ 为3维单位向量，$E$ 为3阶单位矩阵，则矩阵 $E - \alpha\alpha^{\mathrm{T}}$ 的秩为 ______",
        "standard_answer": "2",
    },
    {
        "number": 14,
        "question": r"设 $A,B,C$ 是随机事件，$A$ 与 $C$ 互不相容，$P(AB) = \frac{1}{2}$，$P(C) = \frac{1}{3}$，则 $P(AB \mid \overline{C}) =$ ______",
        "standard_answer": r"$\frac{3}{4}$",
    },
]

# ── 解答题 ──
solution_q = [
    {
        "number": 15,
        "question": r"证明：$x \ln\frac{1+x}{1-x} + \cos x \ge 1 + \frac{x^2}{2}$，$-1 < x < 1$。",
        "standard_answer": r"证明略。构造函数 $f(x) = x\ln\frac{1+x}{1-x} + \cos x - 1 - \frac{x^2}{2}$，求导后利用泰勒展开可证。",
        "score": 10,
    },
    {
        "number": 16,
        "question": r"求函数 $f(x,y) = x e^{-\frac{x^2+y^2}{2}}$ 的极值。",
        "standard_answer": r"极大值 $f(1,0) = e^{-\frac{1}{2}}$，极小值 $f(-1,0) = -e^{-\frac{1}{2}}$",
        "score": 10,
    },
    {
        "number": 17,
        "question": r"求幂级数 $\sum_{n=0}^\infty \frac{4n^2 + 4n + 3}{2n+1} x^{2n}$ 的收敛域及和函数。",
        "standard_answer": r"收敛域为 $(-1,1)$，和函数 $S(x) = \frac{1}{1-x^2} + \frac{1}{2}\ln\frac{1+x}{1-x}$",
        "score": 10,
    },
    {
        "number": 18,
        "question": r"已知曲线 $L: \begin{cases} x = f(t) \\ y = \cos t \end{cases}$ ($0 \le t < \frac{\pi}{2}$)，其中函数 $f(t)$ 具有连续导数，且 $f(0)=0$，$f'(t)>0$ ($0<t<\frac{\pi}{2}$)。若曲线 $L$ 的切线与 $x$ 轴的交点到切点的距离恒为1，求函数 $f(t)$ 的表达式，并求以曲线 $L$ 及 $x$ 轴和 $y$ 轴为边界的区域的面积。",
        "standard_answer": r"$f(t) = \ln(\sec t + \tan t)$，面积 $S = \frac{\pi}{2} - 1$",
        "score": 10,
    },
    {
        "number": 19,
        "question": r"已知 $L$ 是第一象限中从点 $(0,0)$ 沿圆周 $x^2+y^2=2x$ 到点 $(2,0)$，再沿圆周 $x^2+y^2=4$ 到点 $(0,2)$ 的曲线段，计算曲线积分 $I = \int_L 3x^2y dx + (x^3 + x - 2y) dy$。",
        "standard_answer": r"$\frac{4}{3}$",
        "score": 10,
    },
    {
        "number": 20,
        "question": r"设 $A = \begin{pmatrix} 1 & a & 0 & 0 \\ 0 & 1 & a & 0 \\ 0 & 0 & 1 & a \\ a & 0 & 0 & 1 \end{pmatrix}$，$\beta = \begin{pmatrix} 1 \\ -1 \\ 0 \\ 0 \end{pmatrix}$。(I) 计算行列式 $|A|$；(II) 当实数 $a$ 为何值时，方程组 $Ax = \beta$ 有无穷多解，并求其通解。",
        "standard_answer": r"(I) $|A| = 1 - a^4$。(II) 当 $a = -1$ 时有无穷多解，通解为 $x = \begin{pmatrix} 0 \\ -1 \\ 0 \\ 0 \end{pmatrix} + k\begin{pmatrix} 1 \\ -1 \\ 1 \\ -1 \end{pmatrix}$",
        "score": 11,
    },
    {
        "number": 21,
        "question": r"已知 $A = \begin{pmatrix} 1 & 0 & 1 \\ 0 & 1 & 1 \\ -1 & 0 & a \\ 0 & a & -1 \end{pmatrix}$，二次型 $f(x_1,x_2,x_3) = x^{\mathrm{T}}(A^{\mathrm{T}}A)x$ 的秩为2。(I) 求实数 $a$ 的值；(II) 求正交变换 $x = Qy$ 将二次型 $f$ 化为标准形。",
        "standard_answer": r"(I) $a = 1$。(II) $Q = \begin{pmatrix} \frac{1}{\sqrt{2}} & \frac{1}{\sqrt{2}} & 0 \\ 0 & 0 & 1 \\ \frac{1}{\sqrt{2}} & -\frac{1}{\sqrt{2}} & 0 \end{pmatrix}$，标准形为 $3y_1^2 + 2y_2^2$",
        "score": 11,
    },
    {
        "number": 22,
        "question": r"设二维离散型随机变量 $(X,Y)$ 的概率分布为：$P(X=0,Y=0)=\frac{1}{4}$，$P(X=0,Y=2)=\frac{1}{4}$，$P(X=1,Y=1)=\frac{1}{3}$，$P(X=2,Y=0)=\frac{1}{12}$，$P(X=2,Y=2)=\frac{1}{12}$。(I) 求 $P\{X = 2Y\}$；(II) 求 $\operatorname{Cov}(X-Y, Y)$。",
        "standard_answer": r"(I) $P\{X=2Y\} = \frac{1}{4}$。(II) $\operatorname{Cov}(X-Y,Y) = -\frac{1}{6}$",
        "score": 11,
    },
    {
        "number": 23,
        "question": r"设随机变量 $X$ 与 $Y$ 相互独立且分别服从正态分布 $N(\mu,\sigma^2)$ 与 $N(\mu,2\sigma^2)$，其中 $\sigma$ 是未知参数且 $\sigma > 0$。记 $Z = X - Y$。(I) 求 $Z$ 的概率密度 $f(z;\sigma^2)$；(II) 设 $Z_1,\dots,Z_n$ 为来自总体 $Z$ 的简单随机样本，求 $\sigma^2$ 的最大似然估计量；(III) 证明估计量为 $\sigma^2$ 的无偏估计量。",
        "standard_answer": r"(I) $f(z;\sigma^2) = \frac{1}{\sqrt{6\pi}\sigma} e^{-\frac{z^2}{6\sigma^2}}$。(II) $\hat{\sigma}^2 = \frac{1}{3n} \sum_{i=1}^n Z_i^2$。(III) 证明略。",
        "score": 11,
    },
]

# ── 导入 ──
all_questions = []

# 选择题
for q in choices_q:
    all_questions.append({
        "year": 2012,
        "category": "数学一",
        "question_type": "选择题",
        "question": q["question"],
        "options": q["options"],
        "correct_option": q["correct_option"],
        "standard_answer": q["standard_answer"],
        "knowledge_points": [],
        "difficulty": "中等",
        "score": 4,
        "source": "manual_import_2012",
    })

# 填空题
for q in fill_q:
    all_questions.append({
        "year": 2012,
        "category": "数学一",
        "question_type": "填空题",
        "question": q["question"],
        "standard_answer": q["standard_answer"],
        "knowledge_points": [],
        "difficulty": "中等",
        "score": 4,
        "source": "manual_import_2012",
    })

# 解答题
for q in solution_q:
    all_questions.append({
        "year": 2012,
        "category": "数学一",
        "question_type": "解答题",
        "question": q["question"],
        "standard_answer": q["standard_answer"],
        "knowledge_points": [],
        "difficulty": "中等",
        "score": q.get("score", 10),
        "source": "manual_import_2012",
    })

# 导入
print(f"准备导入 {len(all_questions)} 道题...")
success_count = 0
skip_count = 0

for q in all_questions:
    result = db.insert(q)
    if result["success"]:
        success_count += 1
        print(f"  OK {result['question_id']}")
    else:
        skip_count += 1
        print(f"  SKIP #{q.get('number', '?')}: {result.get('warnings', ['unknown'])[0]}")

print(f"\n导入完成: 成功 {success_count} 道, 跳过 {skip_count} 道")
