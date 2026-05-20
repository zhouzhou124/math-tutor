"""Import 26宇哥八套卷 卷七 into the question bank."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS_DIR = os.path.join(ROOT, "storage", "questions", "exams")

CATEGORY = "26宇哥八套卷"
VOLUME = "卷七"

QUESTIONS = [
    # ===== 选择题 (1-10, 5分×10=50) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-001",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设 $f(x) = |\ln|x||$，则" + "\n"
                     r"A. $x=1$ 不是 $f(x)$ 的极值点  B. $(1,0)$ 不是 $y=f(x)$ 的拐点" + "\n"
                     r"C. $x=-1$ 不是 $f(x)$ 的驻点  D. $x=0$ 不是 $y=f(x)$ 的渐近线",
        "options": {"A": r"$x=1$ 不是 $f(x)$ 的极值点", "B": r"$(1,0)$ 不是 $y=f(x)$ 的拐点",
                     "C": r"$x=-1$ 不是 $f(x)$ 的驻点", "D": r"$x=0$ 不是 $y=f(x)$ 的渐近线"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["导数与微分"],
        "tags": ["导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-002",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设 $f(x)$ 在 $(0,+\infty)$ 内可导，$a$ 为常数。对于以下结论：" + "\n"
                     r"① 若 $\lim_{x\to+\infty} f'(x) = a$，则 $\lim_{x\to+\infty} \frac{f(x)}{x} = a$；" + "\n"
                     r"② 若 $\lim_{x\to+\infty} \frac{f(x)}{x} = a$，则 $\lim_{x\to+\infty} f'(x) = a$。" + "\n"
                     r"下列说法中正确的是" + "\n"
                     r"A. ①正确，②错误  B. ①错误，②正确  C. ①与②均正确  D. ①与②均错误",
        "options": {"A": "①正确，②错误", "B": "①错误，②正确", "C": "①与②均正确", "D": "①与②均错误"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["极限与连续", "导数与微分"],
        "tags": ["极限与连续", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-003",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "较难", "score": 5,
        "question": r"已知级数 $\sum_{n=1}^\infty u_n(x)$ 的部分和为 $S_n(x) = \begin{cases} n, & 0 < x < \frac{1}{n} \\ 0, & \text{其他} \end{cases}$，记 $a = \int_0^1 \sum_{n=1}^\infty u_n(x) dx$，$b = \sum_{n=1}^\infty \int_0^1 u_n(x) dx$，则" + "\n"
                     r"A. $a < b < 1$  B. $a < b = 1$  C. $0 = b < a$  D. $a = b = 0$",
        "options": {"A": r"$a < b < 1$", "B": r"$a < b = 1$", "C": r"$0 = b < a$", "D": r"$a = b = 0$"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["无穷级数", "定积分"],
        "tags": ["无穷级数", "定积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-004",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"$I_1 = \int_0^{2\pi} \frac{\sin x}{x} dx$，$I_2 = \int_0^{2\pi} \frac{\sin x}{2\pi - x} dx$，$I_3 = \int_0^{2\pi} \frac{\sin x}{x(2\pi - x)} dx$，则" + "\n"
                     r"A. $I_3 < I_1 < I_2$  B. $I_3 < I_2 < I_1$  C. $I_2 < I_3 < I_1$  D. $I_1 < I_2 < I_3$",
        "options": {"A": r"$I_3 < I_1 < I_2$", "B": r"$I_3 < I_2 < I_1$", "C": r"$I_2 < I_3 < I_1$", "D": r"$I_1 < I_2 < I_3$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["定积分"],
        "tags": ["定积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-005",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设 $A$ 是 $n$ 阶矩阵，$x$ 是任意的 $n$ 维列向量，$B$ 是任意的 $n$ 阶方阵，则下列说法中错误的是" + "\n"
                     r"A. $AB = 0$，必有 $A = 0$  B. $B^{\mathrm{T}}AB = 0$，必有 $A = 0$" + "\n"
                     r"C. $Ax = 0$，必有 $A = 0$  D. $x^{\mathrm{T}}Ax = 0$，必有 $A = 0$",
        "options": {"A": r"$AB = 0$，必有 $A = 0$", "B": r"$B^{\mathrm{T}}AB = 0$，必有 $A = 0$",
                     "C": r"$Ax = 0$，必有 $A = 0$", "D": r"$x^{\mathrm{T}}Ax = 0$，必有 $A = 0$"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["矩阵运算"],
        "tags": ["矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-006",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"$n$ 维向量组 $\alpha_1,\alpha_2,\dots,\alpha_r$（$3\le r\le n$）线性相关的充分必要条件是" + "\n"
                     r"A. 对于任意一组不全为零的数 $k_1,k_2,\dots,k_r$，都有 $k_1\alpha_1 + \cdots + k_r\alpha_r = 0$" + "\n"
                     r"B. $\alpha_1,\alpha_2,\dots,\alpha_r$ 中任意两个向量都线性相关" + "\n"
                     r"C. $\alpha_1,\alpha_2,\dots,\alpha_r$ 中任何一个向量都能由其余向量线性表示" + "\n"
                     r"D. $\alpha_1,\alpha_2,\dots,\alpha_r$ 中至少有一个向量能由其余向量线性表示",
        "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["向量组与线性空间"],
        "tags": ["向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-007",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"若 $A, A^*$, $B$ 都是 $n(n>2)$ 阶非零矩阵，且 $A^*$ 是 $A$ 的伴随矩阵，$AB = O$，则 $r(B) =$" + "\n"
                     r"A. 1  B. $n-1$  C. $n$  D. $n-1$ 或 $n$",
        "options": {"A": "1", "B": r"$n-1$", "C": r"$n$", "D": r"$n-1$ 或 $n$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["矩阵运算"],
        "tags": ["矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-008",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设存在非零常数 $a$ 使得 $P\{aX + Y = 0\} = 1$，则随机变量 $X$ 与 $Y$ 的相关系数 $\rho$ 满足" + "\n"
                     r"A. $\rho = \frac{a}{|a|}$  B. $\rho = -\frac{a}{|a|}$  C. $-1 < \rho < 1$  D. $|\rho| = |a|$",
        "options": {"A": r"$\rho = \frac{a}{|a|}$", "B": r"$\rho = -\frac{a}{|a|}$", "C": r"$-1 < \rho < 1$", "D": r"$|\rho| = |a|$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["数字特征"],
        "tags": ["数字特征"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-009",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设生产每件产品的时间服从指数分布，且平均时间为 10 分钟，生产各件产品的时间相互独立，由中心极限定理，在 15 小时至 20 小时之间生产 100 件产品的概率约为" + "\n"
                     r"A. $\Phi(2) - \Phi(1)$  B. $2\Phi(1) - \Phi(2)$  C. $\Phi(1) + \Phi(2) - 1$  D. $2[\Phi(1) - \Phi(-2)]$",
        "options": {"A": r"$\Phi(2) - \Phi(1)$", "B": r"$2\Phi(1) - \Phi(2)$", "C": r"$\Phi(1) + \Phi(2) - 1$", "D": r"$2[\Phi(1) - \Phi(-2)]$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["大数定律与中心极限定理"],
        "tags": ["大数定律与中心极限定理"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-010",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"在数集 $\Omega = \{0,1,2,\dots,N\}$ 中有放回地抽取 $n$ 次，得 $X_1,X_2,\dots,X_n$，则 $N$ 的最大似然估计量是" + "\n"
                     r"A. $\max\{X_1,X_2,\dots,X_n\}$  B. $\min\{X_1,X_2,\dots,X_n\}$  C. $\frac{1}{n}\sum_{i=1}^n X_i$  D. $n$",
        "options": {"A": r"$\max\{X_1,X_2,\dots,X_n\}$", "B": r"$\min\{X_1,X_2,\dots,X_n\}$", "C": r"$\frac{1}{n}\sum_{i=1}^n X_i$", "D": r"$n$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["参数估计"],
        "tags": ["参数估计"],
        "solution_steps": [],
    },
    # ===== 填空题 (11-16, 5分×6=30) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-011",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"$\lim_{n\to\infty} \left[ \frac{1}{2} + \frac{1}{6} + \cdots + \frac{1}{n(n+1)} \right]^n =$ ______",
        "standard_answer": r"$e^{-1}$",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-012",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"过原点的曲线 $y = y(x)$ 满足 $\frac{dy}{dx} = (x+y)^2$，则 $\lim_{x\to 0^+} [y(x)]^x =$ ______",
        "standard_answer": "1",
        "knowledge_points": ["微分方程", "极限与连续"],
        "tags": ["微分方程", "极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-013",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "较难", "score": 5,
        "question": r"设 $f(x)$ 在 $[0,1]$ 上连续，$\int_0^1 2x^2 f(x) dx \ge \int_0^1 f^2(x) dx + \frac{1}{5}$，则 $f(x) =$ ______",
        "standard_answer": r"$x^2$",
        "knowledge_points": ["定积分"],
        "tags": ["定积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-014",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"设 $l$ 是从点 $(1,1,1)$ 到点 $(4,4,4)$ 的直线段，则 $\int_l \frac{x dx + y dy + z dz}{\sqrt{x^2 + y^2 + z^2 - x - y + 2z}} =$ ______",
        "standard_answer": r"$4\ln 2$",
        "knowledge_points": ["曲线积分"],
        "tags": ["曲线积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-015",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "较难", "score": 5,
        "question": r"已知 3 阶矩阵 $A,B$ 相似，$\lambda_1 = 1,\lambda_2 = 2$ 为 $A$ 的两个特征值，行列式 $|B| = 2$，则行列式 $\begin{vmatrix} (A+E)^{-1} & O \\ O & (2B)^* \end{vmatrix} =$ ______",
        "standard_answer": r"$-\frac{1}{16}$",
        "knowledge_points": ["特征值与特征向量", "矩阵运算", "行列式"],
        "tags": ["特征值与特征向量", "矩阵运算", "行列式"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-016",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"设随机变量 $X$ 的分布函数为 $F(x) = k\left(\frac{\pi}{2} + \arctan x\right)$，$x\in\mathbf{R}$，$Y = \min\{1,|X|\}$，则 $E(Y) =$ ______",
        "standard_answer": r"$\frac{2}{\pi}\ln(1+\sqrt{2})$",
        "knowledge_points": ["随机变量及其分布", "数字特征"],
        "tags": ["随机变量及其分布", "数字特征"],
        "solution_steps": [],
    },
    # ===== 解答题 (17-22, 共70分) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-017",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "中等", "score": 10,
        "question": r"设函数 $y(x)$ 具有二阶导数，曲线 $l: y=y(x)$ 与直线 $y=x$ 相切于原点，且曲线 $l$ 在点 $(x,y)$ 处切线的倾角 $\theta$ 关于 $x$ 的变化率与曲线 $l$ 在该点的切线斜率相等。求 $y(x)$ 的表达式。",
        "standard_answer": r"$y(x) = \ln(1+x)$",
        "knowledge_points": ["导数与微分", "微分方程"],
        "tags": ["导数与微分", "微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-018",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "中等", "score": 12,
        "question": r"设 $u = u(x,y)$ 具有二阶连续偏导数，且满足 $\frac{\partial^2 u}{\partial x \partial y} = x^2 y$，$u(x,0) = -x^2 + 2$，$u(1,y) = \cos y$。求" + "\n"
                     r"(1) $u = u(x,y)$ 的表达式；" + "\n"
                     r"(2) $u(x,y) - \cos y$ 的极值。",
        "standard_answer": r"(1) $u(x,y) = -x^2 + 2 + \cos y + \frac{1}{2}x^2 y^2 - \frac{1}{2}y^2$" + "\n"
                           r"(2) 极小值 $u(1,0) - \cos 0 = -1$",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-019",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设数列 $\{x_n\}$ 满足 $x_{n+1} = \frac{a + x_n}{1 + x_n}$，$0<a<1$，$x_1 \ge 0$。" + "\n"
                     r"(1) 证明 $\sum_{n=1}^\infty (x_{n+1} - x_n)$ 绝对收敛；" + "\n"
                     r"(2) 求 $\lim_{n\to\infty} \sum_{i=1}^n (x_{i+1} - x_i)$。",
        "standard_answer": r"(1) 证明略" + "\n"
                           r"(2) $\lim_{n\to\infty} \sum_{i=1}^n (x_{i+1} - x_i) = 1 - a$",
        "knowledge_points": ["极限与连续", "无穷级数"],
        "tags": ["极限与连续", "无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-020",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设曲面 $\Sigma$ 为 $z^2 = x^2 + y^2 - 1$ 介于 $z=0$ 与 $z=1$ 之间的部分，取外侧，$f(x)$ 为连续函数，计算" + "\n"
                     r"$I = \iint_{\Sigma} [y f(xy) - 2x] dy dz + [y^2 - x f(xy)] dz dx + (z-1)^2 dx dy$。",
        "standard_answer": "0",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-021",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设 $A = \begin{pmatrix} 2 & 1 & 0 \\ 1 & 2 & 0 \\ a & 1 & b \end{pmatrix}$ 恰有 2 个不同的特征值且可相似对角化，$a>0$，$(A+E)(E-B)=E$。求" + "\n"
                     r"(1) $a,b$ 的值；" + "\n"
                     r"(2) 可以使 $A,B$ 同时相似对角化的可逆矩阵 $P$。",
        "standard_answer": r"(1) $a=2$，$b=1$" + "\n"
                           r"(2) $P = E$（3阶单位矩阵）",
        "knowledge_points": ["特征值与特征向量", "矩阵运算"],
        "tags": ["特征值与特征向量", "矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-022",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设某商品每天的供应量 $X$ 的概率密度为 $f(x) = \begin{cases} xe^{-x}, & x\ge 0 \\ 0, & x<0 \end{cases}$。若每天的供应量相互独立，求" + "\n"
                     r"(1) 3天总供应量的概率密度；" + "\n"
                     r"(2) 连续3天中最大供应量的概率密度。",
        "standard_answer": r"(1) $f_{S_3}(s) = \frac{1}{2} s^2 e^{-s}$，$s \ge 0$" + "\n"
                           r"(2) $f_{M_3}(m) = 3m e^{-m}(1 - e^{-m})^2$，$m \ge 0$",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
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
