"""Import 2008 数一 exam questions into the question bank."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS_DIR = os.path.join(ROOT, "storage", "questions", "exams")

QUESTIONS = [
    # ===== 选择题 (1-8) =====
    {
        "question_id": "2008-数一-001",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设函数 $f(x) = \int_0^x \ln(2+t) dt$，则 $f'(x)$ 的零点个数为" + "\n"
                     r"A. 0  B. 1  C. 2  D. 3",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["定积分", "导数与微分"],
        "tags": ["定积分", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-002",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"函数 $f(x,y) = \arctan \frac{x}{y}$ 在点 $(0,1)$ 处的梯度等于" + "\n"
                     r"A. $i$  B. $-i$  C. $j$  D. $-j$",
        "options": {"A": r"$i$", "B": r"$-i$", "C": r"$j$", "D": r"$-j$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-003",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"在下列微分方程中，以 $y = C_1 e^x + C_2 \cos 2x + C_3 \sin 2x$（$C_1,C_2,C_3$ 为任意常数）为通解的是" + "\n"
                     r"A. $y''' + y'' - 4y' - 4y = 0$  B. $y''' + y'' + 4y' + 4y = 0$" + "\n"
                     r"C. $y''' - y'' - 4y' + 4y = 0$  D. $y''' - y'' + 4y' - 4y = 0$",
        "options": {
            "A": r"$y''' + y'' - 4y' - 4y = 0$",
            "B": r"$y''' + y'' + 4y' + 4y = 0$",
            "C": r"$y''' - y'' - 4y' + 4y = 0$",
            "D": r"$y''' - y'' + 4y' - 4y = 0$",
        },
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["微分方程"],
        "tags": ["微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-004",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设函数 $f(x)$ 在 $(-\infty,+\infty)$ 内单调有界，$\{x_n\}$ 为数列，下列命题正确的是" + "\n"
                     r"A. 若 $\{x_n\}$ 收敛，则 $\{f(x_n)\}$ 收敛" + "\n"
                     r"B. 若 $\{x_n\}$ 单调，则 $\{f(x_n)\}$ 收敛" + "\n"
                     r"C. 若 $\{f(x_n)\}$ 收敛，则 $\{x_n\}$ 收敛" + "\n"
                     r"D. 若 $\{f(x_n)\}$ 单调，则 $\{x_n\}$ 收敛",
        "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-005",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $A$ 为 $n$ 阶非零矩阵，$E$ 为 $n$ 阶单位矩阵，若 $A^3 = O$，则" + "\n"
                     r"A. $E-A$ 不可逆，$E+A$ 不可逆  B. $E-A$ 不可逆，$E+A$ 可逆" + "\n"
                     r"C. $E-A$ 可逆，$E+A$ 可逆  D. $E-A$ 可逆，$E+A$ 不可逆",
        "options": {"A": r"$E-A$ 不可逆，$E+A$ 不可逆", "B": r"$E-A$ 不可逆，$E+A$ 可逆",
                     "C": r"$E-A$ 可逆，$E+A$ 可逆", "D": r"$E-A$ 可逆，$E+A$ 不可逆"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["矩阵运算"],
        "tags": ["矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-006",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $A$ 为3阶实对称矩阵，如果二次曲面方程 $(x,y,z)A \begin{pmatrix} x \\ y \\ z \end{pmatrix} = 1$ 在正交变换下的标准方程的图形如图所示（双叶双曲面），则 $A$ 的正特征值的个数为" + "\n"
                     r"A. 0  B. 1  C. 2  D. 3",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["特征值与特征向量", "二次型"],
        "tags": ["特征值与特征向量", "二次型"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-007",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $X,Y$ 独立同分布，且 $X$ 的分布函数为 $F(x)$，则 $Z = \max\{X,Y\}$ 的分布函数为" + "\n"
                     r"A. $F^2(x)$  B. $F(x)F(y)$  C. $1 - [1-F(x)]^2$  D. $[1-F(x)][1-F(y)]$",
        "options": {"A": r"$F^2(x)$", "B": r"$F(x)F(y)$", "C": r"$1 - [1-F(x)]^2$", "D": r"$[1-F(x)][1-F(y)]$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-008",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $X \sim N(0,1)$，$Y \sim N(1,4)$，且相关系数 $\rho_{XY} = 1$，则" + "\n"
                     r"A. $P\{Y = -2X-1\} = 1$  B. $P\{Y = 2X-1\} = 1$" + "\n"
                     r"C. $P\{Y = -2X+1\} = 1$  D. $P\{Y = 2X+1\} = 1$",
        "options": {"A": r"$P\{Y = -2X-1\} = 1$", "B": r"$P\{Y = 2X-1\} = 1$",
                     "C": r"$P\{Y = -2X+1\} = 1$", "D": r"$P\{Y = 2X+1\} = 1$"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["数字特征", "随机变量及其分布"],
        "tags": ["数字特征", "随机变量及其分布"],
        "solution_steps": [],
    },
    # ===== 填空题 (9-14) =====
    {
        "question_id": "2008-数一-009",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"微分方程 $xy' + y = 0$ 满足条件 $y(1)=1$ 的解是 $y =$ ______",
        "standard_answer": r"$\frac{1}{x}$",
        "knowledge_points": ["微分方程"],
        "tags": ["微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-010",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"曲线 $\sin(xy) + \ln(y-x) = x$ 在点 $(0,1)$ 处的切线方程是 ______",
        "standard_answer": r"$y = x + 1$",
        "knowledge_points": ["导数与微分", "多元函数微分"],
        "tags": ["导数与微分", "多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-011",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "较难", "score": 4,
        "question": r"已知幂级数 $\sum_{n=0}^\infty a_n (x+2)^n$ 在 $x=0$ 处收敛，在 $x=-4$ 处发散，则幂级数 $\sum_{n=0}^\infty a_n (x-3)^n$ 的收敛域为 ______",
        "standard_answer": r"$(1,5]$",
        "knowledge_points": ["无穷级数"],
        "tags": ["无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-012",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设曲面 $\Sigma$ 是 $z = \sqrt{4 - x^2 - y^2}$ 的上侧，则 $\iint_{\Sigma} xy dy dz + x dz dx + x^2 dx dy =$ ______",
        "standard_answer": "0",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-013",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设 $A$ 为2阶矩阵，$\alpha_1,\alpha_2$ 为线性无关的2维列向量，$A\alpha_1 = 0$，$A\alpha_2 = 2\alpha_1 + \alpha_2$，则 $A$ 的非零特征值为 ______",
        "standard_answer": "1",
        "knowledge_points": ["特征值与特征向量", "向量组与线性空间"],
        "tags": ["特征值与特征向量", "向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-014",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $X$ 服从参数为1的泊松分布，则 $P\{X = E(X^2)\} =$ ______",
        "standard_answer": r"$e^{-1}$",
        "knowledge_points": ["随机变量及其分布", "数字特征"],
        "tags": ["随机变量及其分布", "数字特征"],
        "solution_steps": [],
    },
    # ===== 解答题 (15-23) =====
    {
        "question_id": "2008-数一-015",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 9,
        "question": r"求极限 $\lim_{x\to 0} \frac{\sin x - \sin(\sin x)}{x^4} \sin x$。",
        "standard_answer": r"$\frac{1}{6}$",
        "knowledge_points": ["极限与连续", "导数与微分"],
        "tags": ["极限与连续", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-016",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 9,
        "question": r"计算曲线积分 $\int_L \sin 2x dx + 2(x^2-1)y dy$，其中 $L$ 是曲线 $y = \sin x$ 上从点 $(0,0)$ 到点 $(\pi,0)$ 的一段。",
        "standard_answer": "0",
        "knowledge_points": ["曲线积分"],
        "tags": ["曲线积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-017",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 11,
        "question": r"已知曲线 $C: \begin{cases} x^2 + y^2 - 2z^2 = 0 \\ x + y + 3z = 5 \end{cases}$，求曲线 $C$ 上距离 $xOy$ 面最远的点和最近的点。",
        "standard_answer": r"最远点为 $(-2, -2, 3)$，最近点为 $(1, 1, 1)$",
        "knowledge_points": ["多元函数微分", "空间解析几何"],
        "tags": ["多元函数微分", "空间解析几何"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-018",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "证明题", "difficulty": "中等", "score": 10,
        "question": r"设 $f(x)$ 是连续函数，" + "\n"
                     r"(I) 利用定义证明函数 $F(x) = \int_0^x f(t) dt$ 可导，且 $F'(x) = f(x)$；" + "\n"
                     r"(II) 当 $f(x)$ 是以2为周期的周期函数时，证明 $G(x) = 2\int_0^x f(t) dt - x \int_0^2 f(t) dt$ 也是以2为周期的周期函数。",
        "standard_answer": "证明略",
        "knowledge_points": ["定积分", "导数与微分"],
        "tags": ["定积分", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-019",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 11,
        "question": r"将函数 $f(x) = 1 - x^2$（$0 \le x \le \pi$）展开成余弦级数，并求 $\sum_{n=1}^\infty \frac{(-1)^{n-1}}{n^2}$ 的和。",
        "standard_answer": r"$f(x) = \frac{2}{\pi} \sum_{n=1}^\infty \frac{1-(-1)^n}{n^2} \cos nx$，$\sum_{n=1}^\infty \frac{(-1)^{n-1}}{n^2} = \frac{\pi^2}{12}$",
        "knowledge_points": ["无穷级数"],
        "tags": ["无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-020",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "证明题", "difficulty": "中等", "score": 10,
        "question": r"设 $\alpha,\beta$ 为3维列向量，矩阵 $A = \alpha \alpha^{\mathrm{T}} + \beta \beta^{\mathrm{T}}$，其中 $\alpha^{\mathrm{T}},\beta^{\mathrm{T}}$ 分别是 $\alpha,\beta$ 的转置。证明：" + "\n"
                     r"(I) 秩 $r(A) \le 2$；" + "\n"
                     r"(II) 若 $\alpha,\beta$ 线性相关，则秩 $r(A) < 2$。",
        "standard_answer": "证明略",
        "knowledge_points": ["矩阵运算", "向量组与线性空间"],
        "tags": ["矩阵运算", "向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-021",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "难题", "score": 12,
        "question": r"设 $n$ 元线性方程组 $Ax = b$，其中" + "\n"
                     r"$A = \begin{pmatrix} 2a & 1 & & & \\ a^2 & 2a & 1 & & \\ & \ddots & \ddots & \ddots & \\ & & a^2 & 2a & 1 \\ & & & a^2 & 2a \end{pmatrix}$，$x = \begin{pmatrix} x_1 \\ x_2 \\ \vdots \\ x_n \end{pmatrix}$，$b = \begin{pmatrix} 1 \\ 0 \\ \vdots \\ 0 \end{pmatrix}$。" + "\n"
                     r"(I) 证明行列式 $|A| = (n+1)a^n$；" + "\n"
                     r"(II) 当 $a$ 为何值时，该方程组有唯一解，并求 $x_1$；" + "\n"
                     r"(III) 当 $a$ 为何值时，该方程组有无穷多解，并求通解。",
        "standard_answer": r"(I) 证明略" + "\n"
                           r"(II) 当 $a \neq 0$ 时，有唯一解，$x_1 = \frac{1}{(n+1)a^n}$" + "\n"
                           r"(III) 当 $a = 0$ 时，有无穷多解，通解为 $x = (1,0,\dots,0)^{\mathrm{T}} + k(0,\dots,0,1)^{\mathrm{T}}$，$k \in \mathbf{R}$",
        "knowledge_points": ["行列式", "线性方程组"],
        "tags": ["行列式", "线性方程组"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-022",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 11,
        "question": r"设随机变量 $X$ 与 $Y$ 相互独立，$X$ 的概率分布为 $P\{X=i\} = \frac{1}{3} (i=-1,0,1)$，$Y$ 的概率密度为 $f_Y(y) = \begin{cases} 1, & 0 \le y < 1 \\ 0, & \text{其他} \end{cases}$。记 $Z = X + Y$。" + "\n"
                     r"(I) 求 $P\{Z \le \frac{1}{2} \mid X = 0\}$；" + "\n"
                     r"(II) 求 $Z$ 的概率密度 $f_Z(z)$。",
        "standard_answer": r"(I) $P\{Z \le \frac{1}{2} \mid X = 0\} = \frac{1}{2}$" + "\n"
                           r"(II) $f_Z(z) = \begin{cases} \frac{1}{3}, & -1 \le z < 0 \\ \frac{2}{3}, & 0 \le z < 1 \\ \frac{1}{3}, & 1 \le z < 2 \\ 0, & \text{其他} \end{cases}$",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": "2008-数一-023",
        "year": 2008, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 11,
        "question": r"设 $X_1,X_2,\dots,X_n$ 是总体 $N(\mu,\sigma^2)$ 的简单随机样本，记 $\overline{X} = \frac{1}{n}\sum_{i=1}^n X_i$，$S^2 = \frac{1}{n-1}\sum_{i=1}^n (X_i - \overline{X})^2$，$T = \overline{X}^2 - \frac{1}{n}S^2$。" + "\n"
                     r"(I) 证明 $T$ 是 $\mu^2$ 的无偏估计量；" + "\n"
                     r"(II) 当 $\mu = 0$，$\sigma = 1$ 时，求 $D(T)$。",
        "standard_answer": r"(I) 证明略" + "\n"
                           r"(II) $D(T) = \frac{2}{n}$",
        "knowledge_points": ["参数估计", "数字特征"],
        "tags": ["参数估计", "数字特征"],
        "solution_steps": [],
    },
]

os.makedirs(EXAMS_DIR, exist_ok=True)

for q in QUESTIONS:
    path = os.path.join(EXAMS_DIR, f"{q['question_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
    print(f"Created {q['question_id']}.json  ({q['question_type']})")

print(f"\nDone. Created {len(QUESTIONS)} question files.")
