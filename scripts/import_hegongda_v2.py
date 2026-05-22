"""Import 26合工大超越卷（数学一）第二套 into the question bank."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MATH_TYPE = "26合工大超越"
VOLUME = "卷二"

# ── 选择题 (1-9) ──
MC = [
    {
        "no": 1, "difficulty": "中等",
        "knowledge_points": ["连续函数", "数列极限"],
        "question": r"$1.$ 设函数 $f(x)$ 在闭区间 $[-1,1]$ 上连续，数列 $\{a_n\}$ 满足 $a_n \in (-1,1)$，$n\in\mathbf{N}$。则 "
                   r"$(A)$ 若数列 $\{f(a_n)\}$ 收敛，则数列 $\{a_n\}$ 收敛 "
                   r"$(B)$ 若数列 $\{f(a_n)\}$ 发散，则数列 $\{a_n\}$ 可能收敛 "
                   r"$(C)$ 若数列 $\{a_n\}$ 单调，则数列 $\{f(a_n)\}$ 收敛 "
                   r"$(D)$ 若数列 $\{f(a_n)\}$ 单调，则数列 $\{a_n\}$ 收敛",
        "options": {"A": r"若 $\{f(a_n)\}$ 收敛，则 $\{a_n\}$ 收敛", "B": r"若 $\{f(a_n)\}$ 发散，则 $\{a_n\}$ 可能收敛", "C": r"若 $\{a_n\}$ 单调，则 $\{f(a_n)\}$ 收敛", "D": r"若 $\{f(a_n)\}$ 单调，则 $\{a_n\}$ 收敛"},
        "correct_option": "B",
    },
    {
        "no": 2, "difficulty": "中等",
        "knowledge_points": ["隐函数", "渐近线"],
        "question": r"$2.$ 已知连续函数 $y=y(x)$ 由方程 $\frac{1}{2}x + \frac{\sqrt{3}}{2}y = \arctan(\frac{\sqrt{3}}{2}x - \frac{1}{2}y)$ 确定，则下列说法中正确的个数为 "
                   r"① $y(x)$ 为奇函数；② $y(x)$ 的零点个数是3；③ 曲线 $y=y(x)$ 有两条斜渐近线。"
                   r"$(A)$ 0 $(B)$ 1 $(C)$ 2 $(D)$ 3",
        "options": {"A": r"0", "B": r"1", "C": r"2", "D": r"3"},
        "correct_option": "C",
    },
    {
        "no": 3, "difficulty": "中等",
        "knowledge_points": ["多元函数微分学"],
        "question": r"$3.$ 设 $z = (x^2 + y^2)e^{-xy}$，$g(x,y) = \frac{\partial^2 z}{\partial x^2} - \frac{\partial^2 z}{\partial y^2}$，区域 $D = \{(x,y) \mid 0<x<1, 0<y<1-x\}$，在 $D$ 内取两点 $(x_1,y_1),(x_2,y_2)$，则 $g(x_1,y_1) \le g(x_2,y_2)$ 的一个充分条件为 "
                   r"$(A)$ $x_1 < x_2, y_1 < y_2$ $(B)$ $x_1 < x_2, y_1 > y_2$ $(C)$ $x_1 > x_2, y_1 < y_2$ $(D)$ $x_1 > x_2, y_1 > y_2$",
        "options": {"A": r"$x_1 < x_2, y_1 < y_2$", "B": r"$x_1 < x_2, y_1 > y_2$", "C": r"$x_1 > x_2, y_1 < y_2$", "D": r"$x_1 > x_2, y_1 > y_2$"},
        "correct_option": "D",
    },
    {
        "no": 4, "difficulty": "中等",
        "knowledge_points": ["无穷级数"],
        "question": r"$4.$ 已知级数 $\sum_{n=1}^\infty \frac{(-1)^n \ln n}{n^k}$，$k>0$，下列说法正确的是 "
                   r"$(A)$ 当 $k>0$ 时，级数绝对收敛 "
                   r"$(B)$ 当 $k>0$ 时，级数条件收敛 "
                   r"$(C)$ 当 $0<k\le 1$ 时，级数发散，当 $k>1$ 时，级数绝对收敛 "
                   r"$(D)$ 当 $0<k\le 1$ 时，级数条件收敛，当 $k>1$ 时，级数绝对收敛",
        "options": {"A": r"$k>0$ 绝对收敛", "B": r"$k>0$ 条件收敛", "C": r"$0<k\le1$ 发散，$k>1$ 绝对收敛", "D": r"$0<k\le1$ 条件收敛，$k>1$ 绝对收敛"},
        "correct_option": "D",
    },
    {
        "no": 5, "difficulty": "中等",
        "knowledge_points": ["向量组", "线性表示"],
        "question": r"$5.$ 设 $\alpha_1 = \begin{pmatrix} 1 \\ 0 \\ 1 \end{pmatrix}$，$\alpha_2 = \begin{pmatrix} 1 \\ 2 \\ 1 \end{pmatrix}$，$\alpha_3 = \begin{pmatrix} -1 \\ 1 \\ a \end{pmatrix}$，$\alpha_4 = \begin{pmatrix} 1 \\ b \\ 1 \end{pmatrix}$。若 $\alpha_4$ 可由 $\alpha_1,\alpha_2,\alpha_3$ 表示，但是 $\alpha_1$ 不可由 $\alpha_2,\alpha_3,\alpha_4$ 表示，则 "
                   r"$(A)$ $a \neq 1$ 且 $b \neq 2$ $(B)$ $a \neq 1$ 且 $b = 2$ $(C)$ $a = 1$ 且 $b \neq 2$ $(D)$ $a = 1$ 且 $b = 2$",
        "options": {"A": r"$a \neq 1$ 且 $b \neq 2$", "B": r"$a \neq 1$ 且 $b = 2$", "C": r"$a = 1$ 且 $b \neq 2$", "D": r"$a = 1$ 且 $b = 2$"},
        "correct_option": "B",
    },
    {
        "no": 6, "difficulty": "较难",
        "knowledge_points": ["矩阵", "代数余子式"],
        "question": r"$6.$ 设 $A = (a_{ij})$ 为三阶非零矩阵，$A_{ij}$ 为 $|A|$ 中 $a_{ij}$ 的代数余子式，满足 $a_{ij} = -A_{ij}$，$1\le i\le 3, 1\le j\le 3$，$\alpha,\beta$ 为任意3维列向量，$E$ 为三阶单位矩阵，下列结论："
                   r"① $\alpha^{\mathrm{T}} A^{\mathrm{T}} A \alpha = \|\alpha\|^2$；"
                   r"② $[A\alpha, A\beta] = [\alpha, \beta]$；"
                   r"③ 齐次线性方程组 $(A+E)x=0$ 有非零解；"
                   r"④ $\operatorname{tr}(A^2) = [\operatorname{tr}(A)]^2$。"
                   r"正确的选项是 $(A)$ ①③ $(B)$ ②④ $(C)$ ①②③ $(D)$ ①②③④",
        "options": {"A": r"①③", "B": r"②④", "C": r"①②③", "D": r"①②③④"},
        "correct_option": "A",
    },
    {
        "no": 7, "difficulty": "中等",
        "knowledge_points": ["矩阵", "秩"],
        "question": r"$7.$ 设 $A,B$ 为三阶非零矩阵，$r(A)+r(B) \le 3$，则下列说法正确的是 "
                   r"$(A)$ $\begin{pmatrix} A \\ B \end{pmatrix}x = 0$ 与 $Ax=0$ 有公共非零解 "
                   r"$(B)$ $\begin{pmatrix} A \\ B \end{pmatrix}x = 0$ 与 $Bx=0$ 没有公共非零解 "
                   r"$(C)$ $\begin{pmatrix} B \\ BA \end{pmatrix}x = 0$ 与 $Bx=0$ 同解 "
                   r"$(D)$ $\begin{pmatrix} A \\ BA \end{pmatrix}x = 0$ 与 $Ax=0$ 同解",
        "options": {"A": r"$\begin{pmatrix}A\\B\end{pmatrix}x=0$ 与 $Ax=0$ 有公共非零解", "B": r"没有公共非零解", "C": r"$\begin{pmatrix}B\\BA\end{pmatrix}x=0$ 与 $Bx=0$ 同解", "D": r"$\begin{pmatrix}A\\BA\end{pmatrix}x=0$ 与 $Ax=0$ 同解"},
        "correct_option": "D",
    },
    {
        "no": 8, "difficulty": "中等",
        "knowledge_points": ["概率", "条件概率"],
        "question": r"$8.$ 设随机事件 $A,B$ 满足 $P(B)=0.3$，$P(A-B)=0.4$，$P(\overline{A} \mid \overline{B}) + P(A \mid B) = 1$，则 $P(\overline{A} \cup B) =$ "
                   r"$(A)$ $\frac{2}{7}$ $(B)$ $\frac{3}{7}$ $(C)$ $\frac{3}{5}$ $(D)$ $\frac{4}{5}$",
        "options": {"A": r"$\frac{2}{7}$", "B": r"$\frac{3}{7}$", "C": r"$\frac{3}{5}$", "D": r"$\frac{4}{5}$"},
        "correct_option": "C",
    },
    {
        "no": 9, "difficulty": "中等",
        "knowledge_points": ["随机变量", "数字特征"],
        "question": r"$9.$ 设随机变量 $X$ 的密度函数 $f(x) = \begin{cases} a(x+b)e^{-x}, & x>0 \\ 0, & x\le 0 \end{cases}$ 在点 $x=1$ 处取得最大值，其中 $a,b$ 均为常数，则 $P(X \ge EX) =$ "
                   r"$(A)$ $\frac{2}{e}$ $(B)$ $\frac{3}{e}$ $(C)$ $\frac{2}{e^2}$ $(D)$ $\frac{3}{e^2}$",
        "options": {"A": r"$\frac{2}{e}$", "B": r"$\frac{3}{e}$", "C": r"$\frac{2}{e^2}$", "D": r"$\frac{3}{e^2}$"},
        "correct_option": "A",
    },
]

# ── 填空题 (10-15) ──
FB = [
    {
        "no": 10, "difficulty": "中等",
        "knowledge_points": ["极限", "定积分"],
        "question": r"$10.$ $\lim_{n\to\infty} \int_0^1 \frac{\sqrt{1 + n \arctan x}}{1+x^2} dx = \underline{\qquad\qquad}$",
        "standard_answer": r"$\frac{\pi}{2}$",
    },
    {
        "no": 11, "difficulty": "中等",
        "knowledge_points": ["反常积分"],
        "question": r"$11.$ $\int_0^{+\infty} \frac{1}{\sqrt{x(x+2)^3}} dx = \underline{\qquad\qquad}$",
        "standard_answer": r"$\frac{\pi}{2}$",
    },
    {
        "no": 12, "difficulty": "中等",
        "knowledge_points": ["曲线积分"],
        "question": r"$12.$ 设 $L$ 是曲线 $x^2 + 2xy + 2y^2 = 1$ 位于第一象限的部分，则 $\int_L \frac{x^2 - 4y^2}{\sqrt{2 + 2xy + y^2}} ds = \underline{\qquad\qquad}$",
        "standard_answer": r"$0$",
    },
    {
        "no": 13, "difficulty": "中等",
        "knowledge_points": ["二重积分"],
        "question": r"$13.$ 二次积分 $\int_0^1 dy \int_0^{\sqrt{y}} x^2 y dx + \int_1^{\sqrt{2}} dy \int_0^{\sqrt{2-y^2}} x^2 y dx = \underline{\qquad\qquad}$",
        "standard_answer": r"$\frac{3}{20}$",
    },
    {
        "no": 14, "difficulty": "中等",
        "knowledge_points": ["二次型"],
        "question": r"$14.$ 二次型 $f(x_1,x_2,x_3) = 2a x_1 x_2 + 4x_1 x_3 - 4x_2 x_3$ 的正惯性指数为2，则 $a$ 的取值范围为 $\underline{\qquad\qquad}$",
        "standard_answer": r"$a > 2$",
    },
    {
        "no": 15, "difficulty": "中等",
        "knowledge_points": ["数字特征", "相关系数"],
        "question": r"$15.$ 设随机变量 $X_1$ 与 $X_2$ 相互独立，$X_1 \sim \begin{pmatrix} -1 & 1 \\ \frac{1}{2} & \frac{1}{2} \end{pmatrix}$，$X_2 \sim N(0,1)$，$Z = X_1 X_2^2$，则 $X_1$ 与 $Z$ 的相关系数 $\rho_{X_1,Z} = \underline{\qquad\qquad}$",
        "standard_answer": r"$0$",
    },
]

# ── 解答题 (16-21) ──
FR = [
    {
        "no": 16, "difficulty": "基础", "score": 10,
        "knowledge_points": ["不定积分"],
        "question": r"$16.$ (本题满分10分) 计算 $\int \frac{e^x}{(e^x+3)^2} dx$。",
        "standard_answer": r"$-\frac{1}{e^x+3} + C$",
    },
    {
        "no": 17, "difficulty": "中等", "score": 12,
        "knowledge_points": ["多元函数极值"],
        "question": r"$17.$ (本题满分12分) 求函数 $f(x,y) = x^3 + y^3 - 3x - 3y + 3xy$ 的极值。",
        "standard_answer": r"极小值 $f(1,1) = -4$，极大值 $f(-1,-1) = 4$，鞍点 $(0,0)$",
    },
    {
        "no": 18, "difficulty": "较难", "score": 12,
        "knowledge_points": ["曲面积分"],
        "question": r"$18.$ (本题满分12分) 设 $\Sigma$ 为曲面 $z = 1 - 4x^2 - 4y^2$（$0\le x\le 1$），取上侧，计算对坐标的曲面积分 "
                   r"$\iint_{\Sigma} \frac{xy^2z dy dz - x^2yz dz dx + (x^2 - y^2)\ln(x^2+y^2+z^2)}{x^2+y^2+z^2} dx dy$。",
        "standard_answer": r"$0$",
    },
    {
        "no": 19, "difficulty": "较难", "score": 12,
        "knowledge_points": ["中值定理", "导数应用"],
        "question": r"$19.$ (本题满分12分) 设函数 $f(x)$ 在 $(-\infty,+\infty)$ 上二阶可导，\n$(I)$ 证明 $f''(x) \ge 0$ 的充要条件是对任意的 $h,x\in(-\infty,+\infty)$ 都有 $f(x+h) - 2f(x) + f(x-h) \ge 0$。\n$(II)$ 若 $(x_0,f(x_0))$ 是曲线 $y=f(x)$ 的拐点，证明 $f''(x_0)=0$。",
        "standard_answer": r"证明略",
    },
    {
        "no": 20, "difficulty": "较难", "score": 12,
        "knowledge_points": ["二次型", "特征值", "正交变换"],
        "question": r"$20.$ (本题满分12分) 已知二次型 $f(x_1,x_2,x_3) = 2x_1^2 + 2x_2^2 + a x_3^2 - 2x_1x_2 + 2x_1x_3 - 2x_2x_3$，其矩阵为 $A$。$\alpha = \begin{pmatrix} 1 \\ b \\ 1 \end{pmatrix}$ 是矩阵 $A$ 对应特征值 $\lambda$ 的一个特征向量（$b<0$）。\n$(I)$ 求 $a,b,\lambda$；\n$(II)$ 求正交变换 $x = Qy$，将二次型化为标准型；\n$(III)$ 求 $f$ 在 $x^{\mathrm{T}}x=1$ 条件下的最小值。",
        "standard_answer": r"(I) $a=2$，$b=-1$，$\lambda=0$\n(II) $Q = \begin{pmatrix} \frac{1}{\sqrt{2}} & \frac{1}{\sqrt{6}} & \frac{1}{\sqrt{3}} \\ \frac{1}{\sqrt{2}} & -\frac{1}{\sqrt{6}} & -\frac{1}{\sqrt{3}} \\ 0 & \frac{2}{\sqrt{6}} & -\frac{1}{\sqrt{3}} \end{pmatrix}$，标准型为 $3y_1^2 + 3y_2^2$\n(III) 最小值为 $0$",
    },
    {
        "no": 21, "difficulty": "中等", "score": 12,
        "knowledge_points": ["多维随机变量", "条件分布"],
        "question": r"$21.$ (本题满分12分) 设二维随机变量 $(X,Y)$ 的联合概率密度为 $f(x,y) = \begin{cases} Axy, & 0<y<x<1 \\ 0, & \text{其他} \end{cases}$。\n$(I)$ 求常数 $A$；\n$(II)$ 在 $0<X<\frac{1}{2}$ 的条件下，求 $Y$ 的条件密度函数。",
        "standard_answer": r"(I) $A = 8$\n(II) $f_{Y|X}(y|x) = \frac{2y}{x^2}$，$0<y<x$",
    },
]


def main():
    db = QuestionDB()
    ok = fail = 0

    all_questions = []

    for q in MC:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026,
            "category": MATH_TYPE,
            "question_type": "选择题", "question_no": q["no"],
            "score": 5, "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "options": q["options"],
            "correct_option": q["correct_option"],
            "standard_answer": q["correct_option"],
            "source": "import_hegongda_v2",
            "solution_steps": [],
            "volume": VOLUME,
        })

    for q in FB:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026,
            "category": MATH_TYPE,
            "question_type": "填空题", "question_no": q["no"],
            "score": 5, "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "standard_answer": q["standard_answer"],
            "source": "import_hegongda_v2",
            "solution_steps": [],
            "options": {},
            "volume": VOLUME,
        })

    for q in FR:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026,
            "category": MATH_TYPE,
            "question_type": "解答题", "question_no": q["no"],
            "score": q["score"], "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "standard_answer": q["standard_answer"],
            "source": "import_hegongda_v2",
            "solution_steps": [],
            "options": {},
            "volume": VOLUME,
        })

    for q in all_questions:
        try:
            result = db.insert(q)
            if result.get("success"):
                ok += 1
                print(f"  OK: {q['question_id']}")
            else:
                fail += 1
                print(f"  FAIL: {q['question_id']} — {result.get('warnings', result)}")
        except Exception as e:
            fail += 1
            print(f"  ERROR: {e}")

    print(f"\nDone: {ok} imported, {fail} failed (total {len(all_questions)})")


if __name__ == "__main__":
    main()
