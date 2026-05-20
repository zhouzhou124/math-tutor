"""Import 2006 数一 exam questions into the question bank."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS_DIR = os.path.join(ROOT, "storage", "questions", "exams")

QUESTIONS = [
    # ===== 填空题 (1-6) =====
    {
        "question_id": "2006-数一-001",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"$\lim_{x\to 0} \frac{x\ln(1+x)}{1-\cos x} =$ ______",
        "standard_answer": "2",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-002",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"微分方程 $y' = \frac{y(1-x)}{x}$ 的通解是 $y =$ ______",
        "standard_answer": r"$y = Cxe^{-x}$",
        "knowledge_points": ["微分方程"],
        "tags": ["微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-003",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设 $\Sigma$ 是锥面 $z = \sqrt{x^2+y^2}$（$0\le z\le 1$）的下侧，则 $\iint_{\Sigma} x dy dz + 2y dz dx + 3(z-1) dx dy =$ ______",
        "standard_answer": r"$\pi$",
        "knowledge_points": ["曲面积分"],
        "tags": ["曲面积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-004",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"点 $(2,1,0)$ 到平面 $3x+4y+5z=0$ 的距离 $d =$ ______",
        "standard_answer": r"$\frac{3\sqrt{2}}{5}$",
        "knowledge_points": ["空间解析几何"],
        "tags": ["空间解析几何"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-005",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设矩阵 $A = \begin{pmatrix} 2 & 1 \\ -1 & 2 \end{pmatrix}$，$E$ 为2阶单位矩阵，矩阵 $B$ 满足 $BA = B + 2E$，则 $|B| =$ ______",
        "standard_answer": "2",
        "knowledge_points": ["矩阵运算", "行列式"],
        "tags": ["矩阵运算", "行列式"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-006",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "填空题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $X$ 与 $Y$ 相互独立，且均服从区间 $[0,3]$ 上的均匀分布，则 $P\{\max(X,Y) \le 1\} =$ ______",
        "standard_answer": r"$\frac{1}{9}$",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    # ===== 选择题 (7-14) =====
    {
        "question_id": "2006-数一-007",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设函数 $y=f(x)$ 具有二阶导数，且 $f'(x)>0$，$f''(x)>0$，$\Delta x$ 为自变量 $x$ 在点 $x_0$ 处的增量，$\Delta y$ 与 $dy$ 分别为 $f(x)$ 在点 $x_0$ 处对应的增量与微分，若 $\Delta x>0$，则" + "\n"
                     r"A. $0<dy<\Delta y$  B. $0<\Delta y<dy$  C. $\Delta y<dy<0$  D. $dy<\Delta y<0$",
        "options": {"A": r"$0<dy<\Delta y$", "B": r"$0<\Delta y<dy$", "C": r"$\Delta y<dy<0$", "D": r"$dy<\Delta y<0$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["导数与微分"],
        "tags": ["导数与微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-008",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $f(x,y)$ 为连续函数，则 $\int_0^{\frac{\pi}{4}} d\theta \int_0^1 f(r\cos\theta, r\sin\theta) r dr$ 等于" + "\n"
                     r"A. $\int_0^{\frac{\sqrt{2}}{2}} dx \int_x^{\sqrt{1-x^2}} f(x,y) dy$  B. $\int_0^{\frac{\sqrt{2}}{2}} dx \int_0^{\sqrt{1-x^2}} f(x,y) dy$" + "\n"
                     r"C. $\int_0^{\frac{\sqrt{2}}{2}} dy \int_y^{\sqrt{1-y^2}} f(x,y) dx$  D. $\int_0^{\frac{\sqrt{2}}{2}} dy \int_0^{\sqrt{1-y^2}} f(x,y) dx$",
        "options": {
            "A": r"$\int_0^{\frac{\sqrt{2}}{2}} dx \int_x^{\sqrt{1-x^2}} f(x,y) dy$",
            "B": r"$\int_0^{\frac{\sqrt{2}}{2}} dx \int_0^{\sqrt{1-x^2}} f(x,y) dy$",
            "C": r"$\int_0^{\frac{\sqrt{2}}{2}} dy \int_y^{\sqrt{1-y^2}} f(x,y) dx$",
            "D": r"$\int_0^{\frac{\sqrt{2}}{2}} dy \int_0^{\sqrt{1-y^2}} f(x,y) dx$",
        },
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["二重积分"],
        "tags": ["二重积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-009",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"若级数 $\sum_{n=1}^\infty a_n$ 收敛，则级数" + "\n"
                     r"A. $\sum_{n=1}^\infty |a_n|$ 收敛  B. $\sum_{n=1}^\infty (-1)^n a_n$ 收敛  C. $\sum_{n=1}^\infty a_n a_{n+1}$ 收敛  D. $\sum_{n=1}^\infty \frac{a_n + a_{n+1}}{2}$ 收敛",
        "options": {"A": r"$\sum_{n=1}^\infty |a_n|$ 收敛", "B": r"$\sum_{n=1}^\infty (-1)^n a_n$ 收敛",
                     "C": r"$\sum_{n=1}^\infty a_n a_{n+1}$ 收敛", "D": r"$\sum_{n=1}^\infty \frac{a_n + a_{n+1}}{2}$ 收敛"},
        "correct_option": "D",
        "standard_answer": "D",
        "knowledge_points": ["无穷级数"],
        "tags": ["无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-010",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $f(x,y)$ 与 $\varphi(x,y)$ 均为可微函数，且 $\varphi'_x(x,y) \neq 0$。已知 $(x_0,y_0)$ 是 $f(x,y)$ 在约束条件 $\varphi(x,y)=0$ 下的一个极值点，下列选项正确的是" + "\n"
                     r"A. 若 $f'_x(x_0,y_0)=0$，则 $f'_y(x_0,y_0)=0$  B. 若 $f'_x(x_0,y_0)=0$，则 $f'_y(x_0,y_0)\neq 0$" + "\n"
                     r"C. 若 $f'_x(x_0,y_0)\neq 0$，则 $f'_y(x_0,y_0)=0$  D. 若 $f'_x(x_0,y_0)\neq 0$，则 $f'_y(x_0,y_0)\neq 0$",
        "options": {"A": r"若 $f'_x(x_0,y_0)=0$，则 $f'_y(x_0,y_0)=0$", "B": r"若 $f'_x(x_0,y_0)=0$，则 $f'_y(x_0,y_0)\neq 0$",
                     "C": r"若 $f'_x(x_0,y_0)\neq 0$，则 $f'_y(x_0,y_0)=0$", "D": r"若 $f'_x(x_0,y_0)\neq 0$，则 $f'_y(x_0,y_0)\neq 0$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["多元函数微分"],
        "tags": ["多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-011",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $\alpha_1,\alpha_2,\dots,\alpha_s$ 均为 $n$ 维列向量，$A$ 是 $m\times n$ 矩阵，下列选项正确的是" + "\n"
                     r"A. 若 $\alpha_1,\alpha_2,\dots,\alpha_s$ 线性相关，则 $A\alpha_1,A\alpha_2,\dots,A\alpha_s$ 线性相关" + "\n"
                     r"B. 若 $\alpha_1,\alpha_2,\dots,\alpha_s$ 线性相关，则 $A\alpha_1,A\alpha_2,\dots,A\alpha_s$ 线性无关" + "\n"
                     r"C. 若 $\alpha_1,\alpha_2,\dots,\alpha_s$ 线性无关，则 $A\alpha_1,A\alpha_2,\dots,A\alpha_s$ 线性相关" + "\n"
                     r"D. 若 $\alpha_1,\alpha_2,\dots,\alpha_s$ 线性无关，则 $A\alpha_1,A\alpha_2,\dots,A\alpha_s$ 线性无关",
        "options": {"A": "A", "B": "B", "C": "C", "D": "D"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["向量组与线性空间"],
        "tags": ["向量组与线性空间"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-012",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $A$ 为3阶矩阵，将 $A$ 的第2行加到第1行得 $B$，再将 $B$ 的第1列的 $-1$ 倍加到第2列得 $C$，记 $P = \begin{pmatrix} 1 & 1 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$，则" + "\n"
                     r"A. $C = P^{-1}AP$  B. $C = PAP^{-1}$  C. $C = P^{\mathrm{T}}AP$  D. $C = PAP^{\mathrm{T}}$",
        "options": {"A": r"$C = P^{-1}AP$", "B": r"$C = PAP^{-1}$", "C": r"$C = P^{\mathrm{T}}AP$", "D": r"$C = PAP^{\mathrm{T}}$"},
        "correct_option": "B",
        "standard_answer": "B",
        "knowledge_points": ["矩阵运算"],
        "tags": ["矩阵运算"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-013",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设 $A,B$ 为随机事件，且 $P(B)>0$，$P(A|B)=1$，则必有" + "\n"
                     r"A. $P(A\cup B) > P(A)$  B. $P(A\cup B) > P(B)$  C. $P(A\cup B) = P(A)$  D. $P(A\cup B) = P(B)$",
        "options": {"A": r"$P(A\cup B) > P(A)$", "B": r"$P(A\cup B) > P(B)$", "C": r"$P(A\cup B) = P(A)$", "D": r"$P(A\cup B) = P(B)$"},
        "correct_option": "C",
        "standard_answer": "C",
        "knowledge_points": ["条件概率与独立性", "随机事件与概率"],
        "tags": ["条件概率与独立性", "随机事件与概率"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-014",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "选择题", "difficulty": "中等", "score": 4,
        "question": r"设随机变量 $X$ 服从正态分布 $N(\mu_1,\sigma_1^2)$，$Y$ 服从正态分布 $N(\mu_2,\sigma_2^2)$，且 $P\{|X-\mu_1|<1\} > P\{|Y-\mu_2|<1\}$，则必有" + "\n"
                     r"A. $\sigma_1 < \sigma_2$  B. $\sigma_1 > \sigma_2$  C. $\mu_1 < \mu_2$  D. $\mu_1 > \mu_2$",
        "options": {"A": r"$\sigma_1 < \sigma_2$", "B": r"$\sigma_1 > \sigma_2$", "C": r"$\mu_1 < \mu_2$", "D": r"$\mu_1 > \mu_2$"},
        "correct_option": "A",
        "standard_answer": "A",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    # ===== 解答题 (15-23) =====
    {
        "question_id": "2006-数一-015",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 10,
        "question": r"设区域 $D = \{(x,y) \mid x^2+y^2 \le 1, x \ge 0\}$，计算二重积分 $I = \iint_D \frac{1+xy}{1+x^2+y^2} dxdy$。",
        "standard_answer": r"$I = \frac{\pi}{2} \ln 2$",
        "knowledge_points": ["二重积分"],
        "tags": ["二重积分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-016",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设数列 $\{x_n\}$ 满足 $0<x_1<\pi$，$x_{n+1} = \sin x_n$（$n=1,2,\dots$）。" + "\n"
                     r"(I) 证明 $\lim_{n\to\infty} x_n$ 存在，并求该极限；" + "\n"
                     r"(II) 计算 $\lim_{n\to\infty} \left(\frac{x_{n+1}}{x_n}\right)^{\frac{1}{n}}$。",
        "standard_answer": r"(I) $\lim_{n\to\infty} x_n = 0$" + "\n"
                           r"(II) $\lim_{n\to\infty} \left(\frac{x_{n+1}}{x_n}\right)^{\frac{1}{n}} = 1$",
        "knowledge_points": ["极限与连续"],
        "tags": ["极限与连续"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-017",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 12,
        "question": r"将函数 $f(x) = \frac{x}{2+x-x^2}$ 展开成 $x$ 的幂级数。",
        "standard_answer": r"$f(x) = \sum_{n=0}^\infty \left(\frac{1}{2^{n+1}} - (-1)^n\right) x^{n+1}$，收敛域为 $(-1,1)$",
        "knowledge_points": ["无穷级数"],
        "tags": ["无穷级数"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-018",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 12,
        "question": r"设函数 $f(u)$ 在 $(0,+\infty)$ 内具有二阶导数，且 $z = f(\sqrt{x^2+y^2})$ 满足等式 $\frac{\partial^2 z}{\partial x^2} + \frac{\partial^2 z}{\partial y^2} = 0$。" + "\n"
                     r"(I) 验证 $f''(u) + \frac{f'(u)}{u} = 0$；" + "\n"
                     r"(II) 若 $f(1)=0$，$f'(1)=1$，求函数 $f(u)$ 的表达式。",
        "standard_answer": r"(I) 证明略" + "\n"
                           r"(II) $f(u) = \ln u$",
        "knowledge_points": ["多元函数微分", "微分方程"],
        "tags": ["多元函数微分", "微分方程"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-019",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "证明题", "difficulty": "较难", "score": 12,
        "question": r"设在上半平面 $D = \{(x,y) \mid y>0\}$ 内，函数 $f(x,y)$ 具有连续偏导数，且对任意的 $t>0$ 都有 $f(tx,ty) = t^{-2} f(x,y)$。证明：对 $D$ 内的任意分段光滑的有向简单闭曲线 $L$，都有 $\oint_L y f(x,y) dx - x f(x,y) dy = 0$。",
        "standard_answer": "证明略",
        "knowledge_points": ["曲线积分", "多元函数微分"],
        "tags": ["曲线积分", "多元函数微分"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-020",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 9,
        "question": r"已知非齐次线性方程组" + "\n"
                     r"$\begin{cases} x_1 + x_2 + x_3 + x_4 = -1 \\ 4x_1 + 3x_2 + 5x_3 - x_4 = -1 \\ a x_1 + x_2 + 3x_3 + b x_4 = 1 \end{cases}$" + "\n"
                     r"有3个线性无关的解。" + "\n"
                     r"(I) 证明方程组系数矩阵 $A$ 的秩 $r(A)=2$；" + "\n"
                     r"(II) 求 $a,b$ 的值及方程组的通解。",
        "standard_answer": r"(I) 证明略" + "\n"
                           r"(II) $a=2$，$b=-3$，通解为 $x = \begin{pmatrix} -2 \\ 0 \\ 1 \\ 0 \end{pmatrix} + k_1 \begin{pmatrix} -1 \\ 1 \\ 0 \\ 0 \end{pmatrix} + k_2 \begin{pmatrix} -1 \\ 0 \\ 0 \\ 1 \end{pmatrix}$，$k_1,k_2 \in \mathbf{R}$",
        "knowledge_points": ["线性方程组"],
        "tags": ["线性方程组"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-021",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "较难", "score": 9,
        "question": r"设3阶实对称矩阵 $A$ 的各行元素之和均为3。向量 $\alpha_1 = (-1,2,-1)^{\mathrm{T}}$，$\alpha_2 = (0,-1,1)^{\mathrm{T}}$ 是线性方程组 $Ax=0$ 的两个解。" + "\n"
                     r"(I) 求 $A$ 的特征值与特征向量；" + "\n"
                     r"(II) 求正交矩阵 $Q$ 和对角矩阵 $\Lambda$，使得 $Q^{\mathrm{T}}AQ = \Lambda$。",
        "standard_answer": r"(I) 特征值 $\lambda_1=3$（对应特征向量 $k(1,1,1)^{\mathrm{T}}$），$\lambda_2=\lambda_3=0$（对应特征向量 $k_1(-1,2,-1)^{\mathrm{T}}+k_2(0,-1,1)^{\mathrm{T}}$）" + "\n"
                           r"(II) $Q = \begin{pmatrix} \frac{1}{\sqrt{3}} & -\frac{1}{\sqrt{6}} & \frac{1}{\sqrt{2}} \\ \frac{1}{\sqrt{3}} & \frac{2}{\sqrt{6}} & 0 \\ \frac{1}{\sqrt{3}} & -\frac{1}{\sqrt{6}} & -\frac{1}{\sqrt{2}} \end{pmatrix}$，$\Lambda = \begin{pmatrix} 3 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix}$",
        "knowledge_points": ["特征值与特征向量", "二次型"],
        "tags": ["特征值与特征向量", "二次型"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-022",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 9,
        "question": r"设随机变量 $X$ 的概率密度为 $f_X(x) = \begin{cases} \frac{1}{2}, & -1<x<0 \\ \frac{1}{4}, & 0\le x<2 \\ 0, & \text{其他} \end{cases}$。令 $Y = X^2$，$F(x,y)$ 为二维随机变量 $(X,Y)$ 的分布函数，求：" + "\n"
                     r"(I) $Y$ 的概率密度 $f_Y(y)$；" + "\n"
                     r"(II) $F\left(-\frac{1}{2}, 4\right)$。",
        "standard_answer": r"(I) $f_Y(y) = \begin{cases} \frac{1}{4\sqrt{y}}, & 0<y<1 \\ \frac{1}{8\sqrt{y}}, & 1\le y<4 \\ 0, & \text{其他} \end{cases}$" + "\n"
                           r"(II) $F\left(-\frac{1}{2},4\right) = \frac{1}{4}$",
        "knowledge_points": ["随机变量及其分布"],
        "tags": ["随机变量及其分布"],
        "solution_steps": [],
    },
    {
        "question_id": "2006-数一-023",
        "year": 2006, "category": "数学一", "math_type": "数学一",
        "question_type": "解答题", "difficulty": "中等", "score": 9,
        "question": r"设总体 $X$ 的概率密度为 $f(x;\theta) = \begin{cases} \theta, & 0<x<1 \\ 1-\theta, & 1\le x<2 \\ 0, & \text{其他} \end{cases}$，其中 $\theta$ 是未知参数（$0<\theta<1$）。$X_1,X_2,\dots,X_n$ 为来自总体 $X$ 的简单随机样本，记 $N$ 为样本值 $x_1,x_2,\dots,x_n$ 中小于1的个数。求 $\theta$ 的最大似然估计。",
        "standard_answer": r"$\hat{\theta} = \frac{N}{n}$",
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
