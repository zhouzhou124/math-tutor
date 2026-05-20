"""Import 26宇哥八套卷 卷八 into the question bank."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SIMUL_DIR = os.path.join(ROOT, "storage", "questions", "simulations")

CATEGORY = "26宇哥八套卷"
VOLUME = "卷八"

QUESTIONS = [
    # ===== 选择题 (1-10, 5分×10=50) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-001",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "较难", "score": 5,
        "question": r"设 $a,b$ 为常数，$\int_0^1 \frac{\ln x}{x^a \left( \tan \frac{\pi}{2} x \right)^b} dx$ 收敛，则" + "\n"
                     r"A. $a+b>1$ 且 $b>-2$  B. $a+b<1$ 且 $b>-2$  C. $a+b>1$ 且 $b<-2$  D. $a+b<1$ 且 $b<-2$",
        "options": {"A": r"$a+b>1$ 且 $b>-2$", "B": r"$a+b<1$ 且 $b>-2$", "C": r"$a+b>1$ 且 $b<-2$", "D": r"$a+b<1$ 且 $b<-2$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["反常积分"],
        "tags": ["反常积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-002",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设 $f(x)$ 在 $(0,+\infty)$ 内可导，对于以下结论：" + "\n"
                     r"① 若 $\lim_{x\to+\infty} f(x)$ 存在，$\lim_{x\to+\infty} f'(x)$ 存在，则 $\lim_{x\to+\infty} f'(x)=0$；" + "\n"
                     r"② 若 $\lim_{x\to+\infty} [f(x)+f'(x)]$ 存在，则 $\lim_{x\to+\infty} f'(x)=0$。" + "\n"
                     r"正确的说法是" + "\n"
                     r"A. ①正确，②错误  B. ①错误，②正确  C. ①与②均正确  D. ①与②均错误",
        "options": {"A": "①正确，②错误", "B": "①错误，②正确", "C": "①与②均正确", "D": "①与②均错误"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["极限与连续", "导数与微分"],
        "tags": ["极限与连续", "导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-003",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"当 $|x|<1$ 时，$\sum_{n=1}^\infty \left( 1 + \frac{1}{2!} + \frac{1}{3!} + \cdots + \frac{1}{n!} \right) x^n =$" + "\n"
                     r"A. $\frac{e^x - e^{-x}}{1+x}$  B. $\frac{e^x - e^{-x}}{1-x}$  C. $\frac{e^x - 1}{1+x}$  D. $\frac{e^x - 1}{1-x}$",
        "options": {"A": r"$\frac{e^x - e^{-x}}{1+x}$", "B": r"$\frac{e^x - e^{-x}}{1-x}$", "C": r"$\frac{e^x - 1}{1+x}$", "D": r"$\frac{e^x - 1}{1-x}$"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["无穷级数"],
        "tags": ["无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-004",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设有直线 $L: \begin{cases} x+3y+2z+1=0 \\ 2x-y-10z+3=0 \end{cases}$ 及平面 $\pi: 4x-2y+z-2=0$，则直线 $L$" + "\n"
                     r"A. 平行于 $\pi$  B. 在 $\pi$ 上  C. 垂直于 $\pi$  D. 与 $\pi$ 斜交",
        "options": {"A": r"平行于 $\pi$", "B": r"在 $\pi$ 上", "C": r"垂直于 $\pi$", "D": r"与 $\pi$ 斜交"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["空间解析几何"],
        "tags": ["空间解析几何"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-005",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设 $n$ 阶行列式 $D_n = \begin{vmatrix} 2 & 1 & 0 & \cdots & 0 \\ 1 & 2 & 1 & \cdots & 0 \\ 0 & 1 & 2 & \cdots & 0 \\ \vdots & \vdots & \vdots & \ddots & \vdots \\ 0 & 0 & 0 & \cdots & 2 \end{vmatrix}$，则" + "\n"
                     r"A. $D_1,D_2,\dots,D_n$ 为等比数列  B. $D_1,D_2,\dots,D_n$ 为等差数列" + "\n"
                     r"C. $D_n$ 为范德蒙德行列式  D. $D_n = n$",
        "options": {"A": r"$D_1,D_2,\dots,D_n$ 为等比数列", "B": r"$D_1,D_2,\dots,D_n$ 为等差数列",
                     "C": r"$D_n$ 为范德蒙德行列式", "D": r"$D_n = n$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["行列式"],
        "tags": ["行列式"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-006",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"已知 $A$ 为3阶方阵，$1,1,2$ 是 $A$ 的3个特征值，$\alpha_1,\alpha_2,\alpha_3$ 为这3个特征值对应的特征向量，则" + "\n"
                     r"A. $\alpha_1,\alpha_2,\alpha_3$ 必为矩阵 $2E-A$ 的特征向量" + "\n"
                     r"B. $\alpha_1-\alpha_2$ 必为矩阵 $2E-A$ 的特征向量" + "\n"
                     r"C. $\alpha_1+\alpha_3$ 必为矩阵 $2E-A$ 的特征向量" + "\n"
                     r"D. $\alpha_1,\alpha_2$ 不是矩阵 $2E-A$ 的特征向量，$\alpha_3$ 必为矩阵 $2E-A$ 的特征向量",
        "options": {"A": r"$\alpha_1,\alpha_2,\alpha_3$ 必为矩阵 $2E-A$ 的特征向量",
                     "B": r"$\alpha_1-\alpha_2$ 必为矩阵 $2E-A$ 的特征向量",
                     "C": r"$\alpha_1+\alpha_3$ 必为矩阵 $2E-A$ 的特征向量",
                     "D": r"$\alpha_1,\alpha_2$ 不是矩阵 $2E-A$ 的特征向量，$\alpha_3$ 必为矩阵 $2E-A$ 的特征向量"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["特征值与特征向量"],
        "tags": ["特征值与特征向量"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-007",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "较难", "score": 5,
        "question": r"设 $\alpha_1,\alpha_2,\dots,\alpha_n$ 是 $n$ 个 $n$ 维的线性无关向量，$\alpha_{n+1} = k_1\alpha_1 + k_2\alpha_2 + \cdots + k_n\alpha_n$，其中 $k_1,k_2,\dots,k_n$ 全不为0，则下列结论" + "\n"
                     r"① $\alpha_2,\alpha_3,\dots,\alpha_{n+1}$ 线性相关；" + "\n"
                     r"② $\alpha_1,\alpha_3,\dots,\alpha_{n+1}$ 线性相关；" + "\n"
                     r"③ $\alpha_1,\alpha_2,\alpha_4,\dots,\alpha_{n+1}$ 线性相关。" + "\n"
                     r"正确的个数为" + "\n"
                     r"A. 0  B. 1  C. 2  D. 3",
        "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["向量组与线性空间"],
        "tags": ["向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-008",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设袋中红球数与黑球数之比为 $r$，且无其他颜色的球，现有放回地抽取 $n$ 次，每次取一球，共取出 $k$ 个红球，则 $r$ 的最大似然估计值为" + "\n"
                     r"A. $\frac{n}{k}$  B. $\frac{n-k}{k}$  C. $\frac{k}{n}$  D. $\frac{k}{n-k}$",
        "options": {"A": r"$\frac{n}{k}$", "B": r"$\frac{n-k}{k}$", "C": r"$\frac{k}{n}$", "D": r"$\frac{k}{n-k}$"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["参数估计"],
        "tags": ["参数估计"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-009",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设随机变量 $X \sim N(0,1)$，则与 $Y = \begin{cases} X, & |X|\le 1 \\ -X, & |X|>1 \end{cases}$ 同分布的是" + "\n"
                     r"A. $X$  B. $2X$  C. $\frac{X+Y}{2}$  D. $X+Y$",
        "options": {"A": r"$X$", "B": r"$2X$", "C": r"$\frac{X+Y}{2}$", "D": r"$X+Y$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-010",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "选择题", "difficulty": "中等", "score": 5,
        "question": r"设有5个盒子，100个球，每个球等可能地放入任一盒子中，根据中心极限定理，指定的某一个盒子中不超过22个球的概率近似为" + "\n"
                     r"A. $1-\Phi(1)$  B. $\Phi(1)$  C. $1-\Phi(0.5)$  D. $\Phi(0.5)$",
        "options": {"A": r"$1-\Phi(1)$", "B": r"$\Phi(1)$", "C": r"$1-\Phi(0.5)$", "D": r"$\Phi(0.5)$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["大数定律与中心极限定理"],
        "tags": ["大数定律与中心极限定理"],
        "solution_steps": [],
    },
    # ===== 填空题 (11-16, 5分×6=30) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-011",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"设 $f(x) = \frac{x+|x|}{2}$，则 $\lim_{x\to 0} [f(1-x)f(1+x)]^{\frac{1}{x^2}} =$ ______",
        "standard_answer": r"$e^{-1}$",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-012",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"函数 $u(x,y,z) = xy^2 + z^3 - xyz$ 在点 $P(1,1,1)$ 处沿任意方向的方向导数中，最大值为 ______",
        "standard_answer": r"$\sqrt{6}$",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-013",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"若 $(2ax^3y^3 - 3y^2 + 5)dx + (3x^4y^2 - 2bxy - 4)dy$ 是某函数 $u(x,y)$ 的全微分，则 $u(x,y) =$ ______",
        "standard_answer": r"$\frac{1}{2}ax^4y^3 - 3xy^2 + 5x + \frac{3}{2}x^4y^2 - bxy^2 - 4y + C$",
        "knowledge_points": ["曲线积分"],
        "tags": ["曲线积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-014",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "较难", "score": 5,
        "question": r"设 $\Sigma$ 是曲线 $x = e^y (0\le y\le a)$ 绕 $x$ 轴旋转而成的旋转曲面，取后侧，则 $I = \iint_{\Sigma} 2(1-x^2) dy dz + 8xy dz dx - 4xz dx dy =$ ______",
        "standard_answer": r"$4\pi(e^{2a} - 1)$",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-015",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "较难", "score": 5,
        "question": r"设 $A$ 为 $n(n\ge 2)$ 阶方阵，$A^*$ 为 $A$ 的伴随矩阵，若对任一 $n$ 维列向量 $\alpha$，均有 $A^*\alpha = 0$，则齐次线性方程组 $Ax=0$ 的基础解系所含解向量的个数 $k$ 必定满足 ______",
        "standard_answer": r"$k \ge 2$",
        "knowledge_points": ["线性方程组", "矩阵运算"],
        "tags": ["线性方程组", "矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-016",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "填空题", "difficulty": "中等", "score": 5,
        "question": r"设 $X_1,X_2$ 为来自总体 $N(0,1)$ 的简单随机样本，记 $\hat{\sigma} = a|X_1-X_2| (a>0)$，若 $D(\hat{\sigma}) = 1$，则 $a =$ ______",
        "standard_answer": r"$\frac{\sqrt{\pi}}{2}$",
        "knowledge_points": ["参数估计", "数字特征"],
        "tags": ["参数估计", "数字特征"],
        "solution_steps": [],
    },
    # ===== 解答题 (17-22, 共70分) =====
    {
        "question_id": f"{CATEGORY}-{VOLUME}-017",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "难题", "score": 10,
        "question": r"设 $u(x,y) = f(x) + g(y)$ 具有二阶连续偏导数，且满足" + "\n"
                     r"$\left[1 + \left(\frac{\partial u}{\partial y}\right)^2\right] \frac{\partial^2 u}{\partial x^2} - 2 \frac{\partial u}{\partial x} \frac{\partial u}{\partial y} \frac{\partial^2 u}{\partial x \partial y} + \left[1 + \left(\frac{\partial u}{\partial x}\right)^2\right] \frac{\partial^2 u}{\partial y^2} = 0$，" + "\n"
                     r"又已知 $f''(x) \neq 0$，求 $u = u(x,y)$ 的表达式。",
        "standard_answer": r"$u(x,y) = \pm \frac{x^2}{2} + C_1x + C_2y + C_3$",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-018",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设空间曲线 $\Gamma: \begin{cases} |x|+|y|=1 \\ z = \arctan(x+y) \end{cases}$，从 $z$ 轴正向往 $z$ 轴负向看，$\Gamma$ 的方向为逆时针，计算 $I = \oint_{\Gamma} (x^2 - y) dx + (2x + y^2) dy + z^2 dz$。",
        "standard_answer": "0",
        "knowledge_points": ["曲线积分"],
        "tags": ["曲线积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-019",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "证明题", "difficulty": "较难", "score": 12,
        "question": r"设函数 $f(x)$ 在 $x=x_0$ 的某邻域 $U$ 内存在连续的二阶导数。" + "\n"
                     r"(1) 设当 $h>0$，$x_0-h\in U$，$x_0+h\in U$，恒有 $f(x_0) < \frac{1}{2}[f(x_0+h) + f(x_0-h)]$，证明 $f''(x_0) \ge 0$；" + "\n"
                     r"(2) 如果 $f''(x_0) > 0$，证明必存在 $h>0$，$x_0-h\in U$，$x_0+h\in U$，使(*)式成立。",
        "standard_answer": "证明略",
        "knowledge_points": ["导数与微分", "中值定理"],
        "tags": ["导数与微分", "中值定理"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-020",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设 $a_n = \int_0^1 x^n \sqrt{1-x^2} dx$，$b_n = \int_0^{\frac{\pi}{2}} \sin^n t dt$，$n=0,1,2,\dots$，计算 $\sum_{n=0}^\infty \frac{b_n}{(2n+1)a_n} x^{2n}$。",
        "standard_answer": r"$\frac{1}{1-x^2}$",
        "knowledge_points": ["无穷级数", "定积分"],
        "tags": ["无穷级数", "定积分"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-021",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设 $A$ 为3阶矩阵，$\lambda_1,\lambda_2,\lambda_3$ 是 $A$ 的3个不同的特征值，其对应的特征向量为 $\xi_1,\xi_2,\xi_3$，$a = \xi_1 + \xi_2 + \xi_3$，$P = (a, Aa, A^2a)$。" + "\n"
                     r"(1) 证明 $P$ 可逆；" + "\n"
                     r"(2) 若 $(A^3 - A)a = 0$，求 $|A-3E|$。",
        "standard_answer": r"(1) 证明略" + "\n"
                           r"(2) $|A-3E| = 0$",
        "knowledge_points": ["特征值与特征向量", "矩阵运算"],
        "tags": ["特征值与特征向量", "矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": f"{CATEGORY}-{VOLUME}-022",
        "year": 2026, "category": CATEGORY, "math_type": CATEGORY, "volume": VOLUME,
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设某营运车辆的使用寿命 $X$（天）服从参数为 $\frac{1}{1000}$ 的指数分布，车辆的使用成本为300元/天，司机的报酬为400元/天，并约定按照 $m$ 天支付报酬，车辆每天正常运营可获得1000元收益，求该营运车辆的期望利润最大时 $m$ 的值（$m$ 为整数）。（$\ln 2$ 取 0.693，$\ln 7$ 取 1.946）",
        "standard_answer": r"$m = 7$",
        "knowledge_points": ["随机变量及其分布", "数字特征"],
        "tags": ["随机变量及其分布", "数字特征"],
        "solution_steps": [],
    },
]

os.makedirs(SIMUL_DIR, exist_ok=True)

for q in QUESTIONS:
    path = os.path.join(SIMUL_DIR, f"{q['question_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(q, f, ensure_ascii=False, indent=2)
    print(f"Created {q['question_id']}.json  ({q['question_type']})")

print(f"\nDone. Created {len(QUESTIONS)} question files in simulations/")
