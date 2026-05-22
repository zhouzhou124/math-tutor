"""Import 26合工大超越卷（数学一）第一套 into the question bank."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.question_db import QuestionDB, make_question_id

MATH_TYPE = "26合工大超越"

def import_volume(volume: str):
    """Import one volume of 合工大超越 questions."""
    import json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database.question_db import QuestionDB, make_question_id

    db = QuestionDB()
    results = {"ok": 0, "fail": 0}

# ── 选择题 ──
MC_QUESTIONS = [
    {
        "no": 1, "difficulty": "中等",
        "knowledge_points": ["极限", "函数"],
        "question": r"$1.$ 函数 $y = (1 + e^x)^{\frac{1}{x}}$ 的值域为 "
                   r"$(A)$ $(1, +\infty)$ $(B)$ $(0, +\infty)$ $(C)$ $(0,1) \cup (e, +\infty)$ $(D)$ $(0,1) \cup (1, +\infty)$",
        "options": {"A": r"$(1, +\infty)$", "B": r"$(0, +\infty)$", "C": r"$(0,1) \cup (e, +\infty)$", "D": r"$(0,1) \cup (1, +\infty)$"},
        "correct_option": "D",
    },
    {
        "no": 2, "difficulty": "中等",
        "knowledge_points": ["定积分", "积分不等式"],
        "question": r"$2.$ 已知 $I_1 = \int_0^{\frac{\pi}{2}} \frac{\sin x}{1+x^2} dx$，$I_2 = \int_0^{\frac{\pi}{2}} \frac{\cos x}{1+x^2} dx$，$J_1 = \int_0^1 e^x \sqrt{1-x} dx$，$J_2 = \int_0^1 e^x \frac{x}{2\sqrt{1-x}} dx$，则 "
                   r"$(A)$ $I_1 > I_2, J_1 > J_2$ $(B)$ $I_1 > I_2, J_1 < J_2$ $(C)$ $I_1 < I_2, J_1 > J_2$ $(D)$ $I_1 < I_2, J_1 < J_2$",
        "options": {"A": r"$I_1 > I_2, J_1 > J_2$", "B": r"$I_1 > I_2, J_1 < J_2$", "C": r"$I_1 < I_2, J_1 > J_2$", "D": r"$I_1 < I_2, J_1 < J_2$"},
        "correct_option": "C",
    },
    {
        "no": 3, "difficulty": "中等",
        "knowledge_points": ["多元函数微分学"],
        "question": r"$3.$ 已知函数 $f(x,y)$ 在点 $(0,0)$ 处连续，且 $\lim_{(x,y)\to(0,0)} \frac{f(x,y)}{\ln(1+|x|+|y|)} = 0$，则 $f(x,y)$ 在点 $(0,0)$ 处 "
                   r"$(A)$ 偏导数不存在，也不可微 $(B)$ 偏导数存在，但不可微 $(C)$ 偏导数存在，且可微",
        "options": {"A": r"偏导数不存在，也不可微", "B": r"偏导数存在，但不可微", "C": r"偏导数存在，且可微"},
        "correct_option": "C",
    },
    {
        "no": 4, "difficulty": "较难",
        "knowledge_points": ["曲线积分"],
        "question": r"$4.$ 设 $L$ 为从点 $(-1,0)$ 到点 $(1,0)$ 的上半圆周 $y = \sqrt{1-x^2}$，则 $\int_L \frac{(e^{-2y} + x^2 y) dx - 2(e^{-2y} + xy^2) dy}{x^2 + y^2} =$ "
                   r"$(A)$ $\frac{3}{8}\pi - e + e^{-1}$ $(B)$ $-\frac{3}{8}\pi - e + e^{-1}$ $(C)$ $e - e^{-1} + \frac{3}{8}\pi$ $(D)$ $e - e^{-1} - \frac{3}{8}\pi$",
        "options": {"A": r"$\frac{3}{8}\pi - e + e^{-1}$", "B": r"$-\frac{3}{8}\pi - e + e^{-1}$", "C": r"$e - e^{-1} + \frac{3}{8}\pi$", "D": r"$e - e^{-1} - \frac{3}{8}\pi$"},
        "correct_option": "B",
    },
    {
        "no": 5, "difficulty": "中等",
        "knowledge_points": ["矩阵", "秩"],
        "question": r"$5.$ 设 $A,E$ 为 $n$ 阶矩阵，$B$ 为 $n\times m$ 矩阵，$C$ 为 $m\times n$ 矩阵，$M = \begin{pmatrix} A & AB \\ CA & O \end{pmatrix}$，$N = \begin{pmatrix} E & B \\ A & O \end{pmatrix}$。其中 $r(M)=r(N)$，若 $r(C)=n$，则 "
                   r"$(A)$ $r(A)=n$ $(B)$ $r(A)=m$ $(C)$ $r(B)=n$ $(D)$ $r(B)=m$",
        "options": {"A": r"$r(A)=n$", "B": r"$r(A)=m$", "C": r"$r(B)=n$", "D": r"$r(B)=m$"},
        "correct_option": "A",
    },
    {
        "no": 6, "difficulty": "中等",
        "knowledge_points": ["向量组", "线性表示"],
        "question": r"$6.$ 设 $\alpha_1 = \begin{pmatrix} 1 \\ 2 \\ -1 \end{pmatrix}$，$\alpha_2 = \begin{pmatrix} 1 \\ 0 \\ 1 \end{pmatrix}$，$\alpha_3 = \begin{pmatrix} -1 \\ a \\ 3 \end{pmatrix}$，$\beta = \begin{pmatrix} 3 \\ 2 \\ b \end{pmatrix}$，$a,b$ 为实数。已知 $\beta$ 可由 $\alpha_1,\alpha_2,\alpha_3$ 线性表示，但不能由 $\alpha_1,\alpha_2$ 表示，则 "
                   r"$(A)$ $a \neq -4, b$ 为任意实数 $(B)$ $a = 4, b = 1$ $(C)$ $a \neq -4$ 且 $b \neq 1$ $(D)$ $a = 4, b$ 为任意实数",
        "options": {"A": r"$a \neq -4, b$ 为任意实数", "B": r"$a = 4, b = 1$", "C": r"$a \neq -4$ 且 $b \neq 1$", "D": r"$a = 4, b$ 为任意实数"},
        "correct_option": "B",
    },
    {
        "no": 7, "difficulty": "中等",
        "knowledge_points": ["矩阵", "行列式"],
        "question": r"$7.$ 设 $A$ 为 $2\times 3$ 矩阵，若 $|AA^{\mathrm{T}}| = 2$，$|A^{\mathrm{T}}A - 2E| = 0$，则 $|A^{\mathrm{T}}A + 2E| =$ "
                   r"$(A)$ $-12$ $(B)$ $12$ $(C)$ $-24$ $(D)$ $24$",
        "options": {"A": r"$-12$", "B": r"$12$", "C": r"$-24$", "D": r"$24$"},
        "correct_option": "B",
    },
    {
        "no": 8, "difficulty": "中等",
        "knowledge_points": ["数字特征", "相关系数"],
        "question": r"$8.$ 设总体 $X$ 的期望和方差分别为 $EX = \mu$ 和 $DX = \sigma^2$，$X_1,X_2,X_3$ 是总体 $X$ 的简单随机样本，记 $\overline{X} = \frac{1}{3}\sum_{i=1}^3 X_i$，则 $X_1 - \overline{X}$ 和 $X_2 - \overline{X}$ 的相关系数等于 "
                   r"$(A)$ $\frac{1}{2}$ $(B)$ $-\frac{1}{2}$ $(C)$ $0$ $(D)$ $1$",
        "options": {"A": r"$\frac{1}{2}$", "B": r"$-\frac{1}{2}$", "C": r"$0$", "D": r"$1$"},
        "correct_option": "B",
    },
    {
        "no": 9, "difficulty": "中等",
        "knowledge_points": ["数理统计", "F分布"],
        "question": r"$9.$ 设随机变量 $F \sim F(1,1)$，则 $P\{F \le 3\} =$ "
                   r"$(A)$ $\frac{1}{2}$ $(B)$ $\frac{2}{3}$ $(C)$ $\Phi(1)$ $(D)$ $\Phi(2)$",
        "options": {"A": r"$\frac{1}{2}$", "B": r"$\frac{2}{3}$", "C": r"$\Phi(1)$", "D": r"$\Phi(2)$"},
        "correct_option": "B",
    },
    {
        "no": 10, "difficulty": "较难",
        "knowledge_points": ["数理统计", "抽样分布"],
        "question": r"$10.$ 设 $(X_1,\dots,X_n)$ 和 $(Y_1,\dots,Y_n)$ 为来自总体 $X \sim N(\mu,\sigma^2)$ 的两个独立样本，样本均值分别为 $\overline{X},\overline{Y}$，样本方差分别为 $S_X^2,S_Y^2$，记 $W = S_X^2 + S_Y^2$。对任意 $0<\alpha<1$，以下正确的是 "
                   r"$(A)$ $P\{\chi_{1-\frac{\alpha}{2}}^2(2n) < \frac{(n-1)W}{\sigma^2} < \chi_{\frac{\alpha}{2}}^2(2n)\} = 1-\alpha$ "
                   r"$(B)$ $P\{\chi_{1-\frac{\alpha}{2}}^2(2n-2) < \frac{(n-1)W}{\sigma^2} < \chi_{\frac{\alpha}{2}}^2(2n-2)\} = 1-\alpha$ "
                   r"$(C)$ $P\{-t_{\frac{\alpha}{2}}(2n) < \frac{\sqrt{n}(\overline{X}-\overline{Y})}{W} < t_{\frac{\alpha}{2}}(2n)\} = 1-\alpha$ "
                   r"$(D)$ $P\{-t_{\frac{\alpha}{2}}(2n-2) < \frac{\sqrt{n}(\overline{X}-\overline{Y})}{W} < t_{\frac{\alpha}{2}}(2n-2)\} = \alpha$",
        "options": {"A": r"$\chi_{1-\frac{\alpha}{2}}^2(2n)$", "B": r"$\chi_{1-\frac{\alpha}{2}}^2(2n-2)$", "C": r"$t_{\frac{\alpha}{2}}(2n)$", "D": r"$t_{\frac{\alpha}{2}}(2n-2)$"},
        "correct_option": "B",
    },
]

# ── 填空题 ──
FB_QUESTIONS = [
    {
        "no": 11, "difficulty": "中等",
        "knowledge_points": ["极限"],
        "question": r"$11.$ $\lim_{x\to +\infty} \left( \frac{\pi}{2} - \arctan x \right)^{\frac{1}{\ln x}} = \underline{\qquad\qquad}$",
        "standard_answer": r"$e^{-1}$",
    },
    {
        "no": 12, "difficulty": "中等",
        "knowledge_points": ["定积分", "函数方程"],
        "question": r"$12.$ 设 $f(x)$ 是 $(-\infty,+\infty)$ 上的非负连续函数，且 $f(x) \cdot \int_0^x f(x-t) dt = x \cos^4 x$，则 $f(x)$ 在 $[0,\pi]$ 上的平均值为 $\underline{\qquad\qquad}$",
        "standard_answer": r"$\frac{3}{8}$",
    },
    {
        "no": 13, "difficulty": "中等",
        "knowledge_points": ["空间解析几何", "切平面"],
        "question": r"$13.$ 曲面 $\Sigma: x^2 + y^2 + 2z^2 = 1$ 上某点的切平面与曲线 $\Gamma: \begin{cases} x^2 + y^2 + z^2 = 3 \\ x + y - z = 1 \end{cases}$ 在点 $(1,1,1)$ 处的法平面平行，则该点的坐标为 $\underline{\qquad\qquad}$",
        "standard_answer": r"$\left( \pm \frac{1}{2}, \pm \frac{1}{2}, \pm \frac{1}{2} \right)$",
    },
    {
        "no": 14, "difficulty": "中等",
        "knowledge_points": ["幂级数", "收敛域"],
        "question": r"$14.$ 幂级数 $\sum_{n=1}^\infty \frac{(n!)^2}{(2n)!} x^n$ 的收敛域为 $\underline{\qquad\qquad}$",
        "standard_answer": r"$(-4,4)$",
    },
    {
        "no": 15, "difficulty": "中等",
        "knowledge_points": ["线性方程组"],
        "question": r"$15.$ 设 $A = \begin{pmatrix} 1 & -1 & 1 \\ a & 1 & 2 \\ 1 & b & 1 \end{pmatrix}$，$B = \begin{pmatrix} 1 & 1 \\ 1 & 2 \\ 1 & b \end{pmatrix}$。已知 $Ax=0$ 与 $B^{\mathrm{T}}x=0$ 同解，则 $a+b = \underline{\qquad\qquad}$",
        "standard_answer": r"$2$",
    },
    {
        "no": 16, "difficulty": "中等",
        "knowledge_points": ["概率", "条件概率"],
        "question": r"$16.$ 已知随机事件 $A,B,C$ 恰好有一个不发生的概率为 $\frac{1}{3}$，且 $A,B$ 互斥，$P(A)=P(B)=\frac{2}{5}$，则 $P(C \mid A \cup B) = \underline{\qquad\qquad}$",
        "standard_answer": r"$\frac{2}{5}$",
    },
]

# ── 解答题 ──
FR_QUESTIONS = [
    {
        "no": 17, "difficulty": "中等", "score": 10,
        "knowledge_points": ["积分方程", "旋转体体积"],
        "question": r"$17.$ (本题满分10分) 设函数 $f(x)$ 在 $(0,+\infty)$ 内连续，且 $f(1)=3$。对任意的 $x,y \in (0,+\infty)$，恒有等式 $\int_0^{xy} f(t) dt = y^2 \int_0^x f(t) dt + x^2 \int_0^y f(t) dt$ 成立。\n$(I)$ 求函数 $f(x)$。\n$(II)$ 求曲线 $y=f(x)$ 和直线 $x=1, x=e$ 及 $x$ 轴围成的图形绕直线 $x=1$ 旋转一周形成的旋转体的体积。",
        "standard_answer": r"(I) $f(x) = 3x$\n(II) $V = 2\pi e^2 - 2\pi e$",
    },
    {
        "no": 18, "difficulty": "中等", "score": 12,
        "knowledge_points": ["全微分", "多元函数极值"],
        "question": r"$18.$ (本题满分12分) 函数 $f(x,y)$ 的全微分 $df(x,y) = 3(x-y)^2 dx - 3(x^2 - 2xy + 2y^2 - 2) dy$，且 $f(0,0)=0$。\n$(I)$ 求 $f(x,y)$。\n$(II)$ 求 $f(x,y)$ 在闭区域 $D = \{(x,y) \mid x\ge 0, y\ge 0, x+y\le 3\}$ 上的最值。",
        "standard_answer": r"(I) $f(x,y) = x^3 - 3x^2y + 3xy^2 - 2y^3 + 6y$\n(II) 最大值 $f(0,3)=18$，最小值 $f(0,0)=0$",
    },
    {
        "no": 19, "difficulty": "较难", "score": 12,
        "knowledge_points": ["曲面积分", "旋转曲面"],
        "question": r"$19.$ (本题满分12分) 设 $\Sigma$ 为曲线 $\begin{cases} x = \sqrt{2}\cos t \\ y = \sin t \\ z = \cos^2 t \end{cases}$，$0\le t\le \frac{\pi}{2}$ 绕 $z$ 轴旋转一周所得的曲面，计算对面积的曲面积分 $\iint_{\Sigma} \frac{xy^3 + \sqrt{5+4z}}{1+x^2+y^2} dS$。",
        "standard_answer": r"$\frac{4\sqrt{5}\pi}{3}$",
    },
    {
        "no": 20, "difficulty": "较难", "score": 12,
        "knowledge_points": ["中值定理", "微分方程"],
        "question": r"$20.$ (本题满分12分) 设 $f(x)$ 是 $[-a,a]$ 上二阶可导的奇函数，且 $\int_0^a f(x) dx = \frac{1}{2} a^2 f(a)$。\n$(I)$ 证明存在 $\xi \in (0,a)$，有 $f'(\xi) = f(a)$。\n$(II)$ 证明对任意的实数 $\lambda$，存在 $\eta \in (-a,a)$，有 $f''(\eta) - \lambda f'(\eta) + \lambda f(a) = 0$。",
        "standard_answer": r"证明略",
    },
    {
        "no": 21, "difficulty": "较难", "score": 12,
        "knowledge_points": ["向量组", "相似对角化"],
        "question": r"$21.$ (本题满分12分) 设向量组 (i) $\alpha_1 = (a,0,1)^{\mathrm{T}}$，$\alpha_2 = (0,-a,0)^{\mathrm{T}}$，$\alpha_3 = (1,0,a)^{\mathrm{T}}$，(ii) $\beta_1 = (a,0,1)^{\mathrm{T}}$，$\beta_2 = (a,1,1)^{\mathrm{T}}$，$\beta_3 = (a^2,0,a)^{\mathrm{T}}$（$a \neq 0$）。\n$(I)$ 若向量组 (i) 与 (ii) 等价，求 $a$ 的值；\n$(II)$ 记 $A = (\alpha_1,\alpha_2,\alpha_3)$，$B = (\beta_1,\beta_2,\beta_3)$，当 $a$ 为何值时，存在可逆矩阵 $P$，使得 $P^{-1}AP = B$？并求 $P$。",
        "standard_answer": r"(I) $a = \pm 1$\n(II) 当 $a=1$ 时，$P = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$；当 $a=-1$ 时，$P = \begin{pmatrix} 1 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$",
    },
    {
        "no": 22, "difficulty": "较难", "score": 12,
        "knowledge_points": ["多维随机变量", "条件分布"],
        "question": r"$22.$ (本题满分12分) 设随机变量 $X$ 的分布律为 $\begin{pmatrix} 1 & 2 \\ \frac{1}{4} & \frac{3}{4} \end{pmatrix}$，随机变量 $Y \sim U[-\pi,\pi]$，且 $X$ 和 $Y$ 相互独立，令 $Z = X \cos\left(\frac{\pi}{4}+Y\right)$。\n$(I)$ 在随机变量 $X=1$ 的条件下，求随机变量 $Z$ 的条件概率密度 $f_{Z|X}(z \mid 1)$；\n$(II)$ 求随机变量 $Z$ 的概率密度 $f_Z(z)$；\n$(III)$ 判断随机变量 $X$ 和 $Z$ 是否不相关，是否独立，并说明理由。",
        "standard_answer": r"(I) $f_{Z|X}(z \mid 1) = \frac{1}{\pi\sqrt{1-z^2}}$，$|z|<1$\n(II) $f_Z(z) = \frac{3}{4\pi\sqrt{1-z^2}} + \frac{1}{4\pi\sqrt{4-z^2}}$，$|z|<2$\n(III) $X$ 与 $Z$ 不相关，但不独立",
    },
]


def main():
    db = QuestionDB()
    results = {"ok": 0, "skip": 0, "fail": 0}

    all_questions = []
    for q in MC_QUESTIONS:
        qid = make_question_id(0, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid,
            "year": 2026,
            "category": MATH_TYPE,
            "question_type": "选择题",
            "question_no": q["no"],
            "score": 5,
            "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "options": q["options"],
            "correct_option": q["correct_option"],
            "standard_answer": q["correct_option"],
            "source": "import_hegongda",
            "solution_steps": [],
            "volume": VOLUME,
        })

    for q in FB_QUESTIONS:
        qid = make_question_id(0, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid,
            "year": 2026,
            "category": MATH_TYPE,
            "question_type": "填空题",
            "question_no": q["no"],
            "score": 5,
            "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "standard_answer": q["standard_answer"],
            "source": "import_hegongda",
            "solution_steps": [],
            "options": {},
            "volume": VOLUME,
        })

    for q in FR_QUESTIONS:
        qid = make_question_id(0, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid,
            "year": 2026,
            "category": MATH_TYPE,
            "question_type": "解答题",
            "question_no": q["no"],
            "score": q["score"],
            "difficulty": q["difficulty"],
            "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"],
            "question": q["question"],
            "standard_answer": q["standard_answer"],
            "source": "import_hegongda",
            "solution_steps": [],
            "options": {},
            "volume": VOLUME,
        })

    for q in all_questions:
        qid = q["question_id"]
        try:
            result = db.insert(q)
            if result.get("success"):
                results["ok"] += 1
                print(f"  OK: {qid}")
            else:
                results["fail"] += 1
                print(f"  FAIL: {qid} — {result}")
        except Exception as e:
            results["fail"] += 1
            print(f"  ERROR: {qid} — {e}")

    print(f"\nDone: {results['ok']} imported, {results['fail']} failed")


if __name__ == "__main__":
    main()
