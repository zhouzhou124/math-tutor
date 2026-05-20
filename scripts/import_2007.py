"""Import 2007 数一 exam questions into the question bank."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS_DIR = os.path.join(ROOT, "storage", "questions", "exams")

QUESTIONS = [
    # ===== 选择题 (1-10) =====
    {
        "question_id": "2007-数一-001",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"当 $x\to 0^+$ 时，与 $\sqrt{x}$ 等价的无穷小量是" + "\n"
                     r"A. $1 - e^{\frac{1}{x}}$  B. $\ln\frac{1+x}{1-\sqrt{x}}$  C. $\sqrt{1+\sqrt{x}} - 1$  D. $1 - \cos\sqrt{x}$",
        "options": {"A": r"$1 - e^{\frac{1}{x}}$", "B": r"$\ln\frac{1+x}{1-\sqrt{x}}$", "C": r"$\sqrt{1+\sqrt{x}} - 1$", "D": r"$1 - \cos\sqrt{x}$"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-002",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"曲线 $y = \frac{1}{x} + \ln(1+e^x)$ 渐近线的条数为" + "\n"
                     r"A. 0  B. 1  C. 2  D. 3",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["极限与连续", "导数与微分"],
        "tags": ["极限与连续", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-003",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"如图，连续函数 $y=f(x)$ 在区间 $[-3,-2]$、$[2,3]$ 上的图形分别是直径为1的上、下半圆周，在区间 $[-2,0]$、$[0,2]$ 上的图形分别是直径为2的下、上半圆周。设 $F(x) = \int_0^x f(t) dt$，则下列结论正确的是" + "\n"
                     r"A. $F(3) = -\frac{3}{4}F(-2)$  B. $F(3) = \frac{5}{4}F(2)$  C. $F(-3) = \frac{3}{4}F(2)$  D. $F(-3) = -\frac{5}{4}F(-2)$",
        "options": {"A": r"$F(3) = -\frac{3}{4}F(-2)$", "B": r"$F(3) = \frac{5}{4}F(2)$", "C": r"$F(-3) = \frac{3}{4}F(2)$", "D": r"$F(-3) = -\frac{5}{4}F(-2)$"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["定积分", "定积分应用"],
        "tags": ["定积分", "定积分应用"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-004",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设函数 $f(x)$ 在 $x=0$ 处连续，下列命题错误的是" + "\n"
                     r"A. 若 $\lim_{x\to 0} \frac{f(x)}{x}$ 存在，则 $f(0)=0$" + "\n"
                     r"B. 若 $\lim_{x\to 0} \frac{f(x)+f(-x)}{x}$ 存在，则 $f(0)=0$" + "\n"
                     r"C. 若 $\lim_{x\to 0} \frac{f(x)}{x}$ 存在，则 $f'(0)$ 存在" + "\n"
                     r"D. 若 $\lim_{x\to 0} \frac{f(x)-f(-x)}{x}$ 存在，则 $f'(0)$ 存在",
        "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["极限与连续", "导数与微分"],
        "tags": ["极限与连续", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-005",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设函数 $f(x)$ 在 $(0,+\infty)$ 上具有二阶导数，且 $f''(x)>0$，令 $u_n = f(n)$（$n=1,2,\dots$），则下列结论正确的是" + "\n"
                     r"A. 若 $u_1 > u_2$，则 $\{u_n\}$ 必收敛  B. 若 $u_1 > u_2$，则 $\{u_n\}$ 必发散" + "\n"
                     r"C. 若 $u_1 < u_2$，则 $\{u_n\}$ 必收敛  D. 若 $u_1 < u_2$，则 $\{u_n\}$ 必发散",
        "options": {"A": r"若 $u_1 > u_2$，则 $\{u_n\}$ 必收敛", "B": r"若 $u_1 > u_2$，则 $\{u_n\}$ 必发散",
                     "C": r"若 $u_1 < u_2$，则 $\{u_n\}$ 必收敛", "D": r"若 $u_1 < u_2$，则 $\{u_n\}$ 必发散"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["导数与微分", "极限与连续"],
        "tags": ["导数与微分", "极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-006",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设曲线 $L: f(x,y)=1$（$f(x,y)$ 具有一阶连续偏导数），过第II象限内的点 $M$ 和第IV象限内的点 $N$，$\Gamma$ 为 $L$ 上从点 $M$ 到点 $N$ 的一段弧，则下列积分小于零的是" + "\n"
                     r"A. $\int_{\Gamma} f(x,y) dx$  B. $\int_{\Gamma} f(x,y) dy$  C. $\int_{\Gamma} f(x,y) ds$  D. $\int_{\Gamma} f_x'(x,y) dx + f_y'(x,y) dy$",
        "options": {"A": r"$\int_{\Gamma} f(x,y) dx$", "B": r"$\int_{\Gamma} f(x,y) dy$", "C": r"$\int_{\Gamma} f(x,y) ds$", "D": r"$\int_{\Gamma} f_x'(x,y) dx + f_y'(x,y) dy$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["曲线积分"],
        "tags": ["曲线积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-007",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设向量组 $\alpha_1,\alpha_2,\alpha_3$ 线性无关，则下列向量组线性相关的是" + "\n"
                     r"A. $\alpha_1-\alpha_2, \alpha_2-\alpha_3, \alpha_3-\alpha_1$  B. $\alpha_1+\alpha_2, \alpha_2+\alpha_3, \alpha_3+\alpha_1$" + "\n"
                     r"C. $\alpha_1-2\alpha_2, \alpha_2-2\alpha_3, \alpha_3-2\alpha_1$  D. $\alpha_1+2\alpha_2, \alpha_2+2\alpha_3, \alpha_3+2\alpha_1$",
        "options": {"A": r"$\alpha_1-\alpha_2, \alpha_2-\alpha_3, \alpha_3-\alpha_1$", "B": r"$\alpha_1+\alpha_2, \alpha_2+\alpha_3, \alpha_3+\alpha_1$",
                     "C": r"$\alpha_1-2\alpha_2, \alpha_2-2\alpha_3, \alpha_3-2\alpha_1$", "D": r"$\alpha_1+2\alpha_2, \alpha_2+2\alpha_3, \alpha_3+2\alpha_1$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["向量组与线性空间"],
        "tags": ["向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-008",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设矩阵 $A = \begin{pmatrix} 2 & -1 & -1 \\ -1 & 2 & -1 \\ -1 & -1 & 2 \end{pmatrix}$，$B = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{pmatrix}$，则 $A$ 与 $B$" + "\n"
                     r"A. 合同，且相似  B. 合同，但不相似  C. 不合同，但相似  D. 既不合同，也不相似",
        "options": {"A": "合同，且相似", "B": "合同，但不相似", "C": "不合同，但相似", "D": "既不合同，也不相似"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["特征值与特征向量", "二次型"],
        "tags": ["特征值与特征向量", "二次型"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-009",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"某人向同一目标独立重复射击，每次射击命中目标的概率为 $p(0<p<1)$，则此人第4次射击恰好第2次命中目标的概率为" + "\n"
                     r"A. $3p(1-p)^2$  B. $6p(1-p)^2$  C. $3p^2(1-p)^2$  D. $6p^2(1-p)^2$",
        "options": {"A": r"$3p(1-p)^2$", "B": r"$6p(1-p)^2$", "C": r"$3p^2(1-p)^2$", "D": r"$6p^2(1-p)^2$"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-010",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $(X,Y)$ 服从二维正态分布，且 $X$ 与 $Y$ 不相关，$f_X(x)$、$f_Y(y)$ 分别表示 $X,Y$ 的概率密度，则在 $Y=y$ 的条件下，$X$ 的条件概率密度 $f_{X|Y}(x|y)$ 为" + "\n"
                     r"A. $f_X(x)$  B. $f_Y(y)$  C. $f_X(x)f_Y(y)$  D. $\frac{f_X(x)}{f_Y(y)}$",
        "options": {"A": r"$f_X(x)$", "B": r"$f_Y(y)$", "C": r"$f_X(x)f_Y(y)$", "D": r"$\frac{f_X(x)}{f_Y(y)}$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["随机变量及其分布", "多维随机变量"],
        "tags": ["随机变量及其分布", "多维随机变量"],
        "solution_steps": [],
    },
    # ===== 填空题 (11-16) =====
    {
        "question_id": "2007-数一-011",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"$\int_1^2 \frac{1}{x^3} e^{\frac{1}{x}} dx =$ ______",
        "standard_answer": r"$\frac{3}{2}e^{\frac{1}{2}} - \frac{1}{2}e$",
        "knowledge_points": ["定积分"],
        "tags": ["定积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-012",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设 $f(u,v)$ 为二元可微函数，$z = f(x^y, x^z)$，则 $\frac{\partial z}{\partial x} =$ ______",
        "standard_answer": r"$f_1 \cdot y x^{y-1} + f_2 \cdot z x^{z-1}$",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-013",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"二阶常系数非齐次线性微分方程 $y'' - 4y' + 3y = 2e^{2x}$ 的通解为 $y =$ ______",
        "standard_answer": r"$y = C_1 e^x + C_2 e^{3x} - 2e^{2x}$",
        "knowledge_points": ["微分方程"],
        "tags": ["微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-014",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设曲面 $\Sigma: |x| + |y| + |z| = 1$，则 $\iint_{\Sigma} (x + |y|) dS =$ ______",
        "standard_answer": r"$\frac{4}{3}\sqrt{3}$",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-015",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设矩阵 $A = \begin{pmatrix} 0 & 1 & 0 \\ 0 & 0 & 1 \\ 0 & 0 & 0 \end{pmatrix}$，则 $A^3$ 的秩为 ______",
        "standard_answer": "0",
        "knowledge_points": ["矩阵运算"],
        "tags": ["矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-016",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"在区间 $(0,1)$ 中随机地取两个数，则这两个数之差的绝对值小于 $\frac{1}{2}$ 的概率为 ______",
        "standard_answer": r"$\frac{3}{4}$",
        "knowledge_points": ["随机事件与概率"],
        "tags": ["随机事件与概率"],
        "solution_steps": [],
    },
    # ===== 解答题 (17-24) =====
    {
        "question_id": "2007-数一-017",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 11,
        "question": r"求函数 $f(x,y) = x^2 + 2y^2 - x^2y^2$ 在区域 $D = \{(x,y) \mid x^2+y^2 \le 4, y \ge 0\}$ 上的最大值和最小值。",
        "standard_answer": r"最大值 $4$，最小值 $-8$",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-018",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 10,
        "question": r"计算曲面积分 $I = \iint_{\Sigma} xz dy dz + 2yz dz dx + 3xy dx dy$，其中 $\Sigma$ 为曲面 $z = 1 - x^2 - \frac{y^2}{4}$（$0 \le z \le 1$）的上侧。",
        "standard_answer": r"$\frac{3\pi}{4}$",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-019",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "证明题", "difficulty": "较难", "score": 11,
        "question": r"设函数 $f(x),g(x)$ 在 $[a,b]$ 上连续，在 $(a,b)$ 内具有二阶导数且存在相等的最大值，$f(a)=g(a)$，$f(b)=g(b)$，证明：存在 $\xi \in (a,b)$，使得 $f''(\xi) = g''(\xi)$。",
        "standard_answer": "证明略",
        "knowledge_points": ["中值定理"],
        "tags": ["中值定理"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-020",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 10,
        "question": r"设幂级数 $\sum_{n=0}^\infty a_n x^n$ 在 $(-\infty,+\infty)$ 内收敛，其和函数 $y(x)$ 满足 $y'' - 2xy' - 4y = 0$，$y(0)=0$，$y'(0)=1$。" + "\n"
                     r"(I) 证明 $a_{n+2} = \frac{2}{n+1} a_n$，$n=1,2,\dots$；" + "\n"
                     r"(II) 求 $y(x)$ 的表达式。",
        "standard_answer": r"(I) 证明略" + "\n"
                           r"(II) $y(x) = x e^{x^2}$",
        "knowledge_points": ["无穷级数", "微分方程"],
        "tags": ["无穷级数", "微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-021",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 11,
        "question": r"设线性方程组" + "\n"
                     r"$\begin{cases} x_1 + x_2 + x_3 = 0 \\ x_1 + 2x_2 + a x_3 = 0 \\ x_1 + 4x_2 + a^2 x_3 = 0 \end{cases}$" + "\n"
                     r"与方程 $x_1 + 2x_2 + x_3 = a-1$ 有公共解，求 $a$ 的值及所有公共解。",
        "standard_answer": r"当 $a=1$ 时，公共解为 $k(1,-2,1)^{\mathrm{T}}$；当 $a=2$ 时，公共解为 $(0,-1,1)^{\mathrm{T}}$",
        "knowledge_points": ["线性方程组"],
        "tags": ["线性方程组"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-022",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 11,
        "question": r"设3阶实对称矩阵 $A$ 的特征值 $\lambda_1 = 1$，$\lambda_2 = 2$，$\lambda_3 = -2$，且 $\alpha_1 = (1,-1,1)^{\mathrm{T}}$ 是 $A$ 的属于 $\lambda_1$ 的一个特征向量。记 $B = A^5 - 4A^3 + E$，其中 $E$ 为3阶单位矩阵。" + "\n"
                     r"(I) 验证 $\alpha_1$ 是矩阵 $B$ 的特征向量，并求 $B$ 的全部特征值与特征向量；" + "\n"
                     r"(II) 求矩阵 $B$。",
        "standard_answer": r"(I) $B$ 的特征值为 $-2$（对应特征向量 $k(1,-1,1)^{\mathrm{T}}$），$1$（对应特征向量 $k\alpha_2$），$1$（对应特征向量 $k\alpha_3$）" + "\n"
                           r"(II) $B = E$（3阶单位矩阵）",
        "knowledge_points": ["特征值与特征向量"],
        "tags": ["特征值与特征向量"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-023",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 11,
        "question": r"设二维随机变量 $(X,Y)$ 的概率密度为 $f(x,y) = \begin{cases} 2-x-y, & 0<x<1,0<y<1 \\ 0, & \text{其他} \end{cases}$。" + "\n"
                     r"(I) 求 $P\{X > 2Y\}$；" + "\n"
                     r"(II) 求 $Z = X + Y$ 的概率密度 $f_Z(z)$。",
        "standard_answer": r"(I) $P\{X > 2Y\} = \frac{1}{4}$" + "\n"
                           r"(II) $f_Z(z) = \begin{cases} z(2-z), & 0<z<1 \\ (2-z)^2, & 1<z<2 \\ 0, & \text{其他} \end{cases}$",
        "knowledge_points": ["多维随机变量", "随机变量及其分布"],
        "tags": ["多维随机变量", "随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": "2007-数一-024",
        "year": 2007, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 11,
        "question": r"设总体 $X$ 的概率密度为 $f(x;\theta) = \begin{cases} \frac{1}{2\theta}, & 0<x<\theta \\ \frac{1}{2(1-\theta)}, & \theta \le x < 1 \\ 0, & \text{其他} \end{cases}$，其中参数 $\theta(0<\theta<1)$ 未知，$X_1,X_2,\dots,X_n$ 是来自总体 $X$ 的简单随机样本，$\overline{X}$ 是样本均值。" + "\n"
                     r"(I) 求参数 $\theta$ 的矩估计量 $\hat{\theta}$；" + "\n"
                     r"(II) 判断 $4\overline{X}^2$ 是否为 $\theta^2$ 的无偏估计量，并说明理由。",
        "standard_answer": r"(I) $\hat{\theta} = \frac{1}{2} \overline{X} + \frac{1}{2}$" + "\n"
                           r"(II) $4\overline{X}^2$ 不是 $\theta^2$ 的无偏估计量",
        "knowledge_points": ["参数估计"],
        "tags": ["参数估计"],
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
