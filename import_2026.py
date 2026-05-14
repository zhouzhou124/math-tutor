"""Import 2026 Math I exam questions into the question bank."""
import re, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import QuestionDB, QuestionImporter

# Raw LaTeX content for 2026 Math I questions
RAW_QUESTIONS = {
    "选择题": [
        {
            "no": 1, "difficulty": "中等",
            "knowledge_points": ["多元函数微分学"],
            "question": r"$1.$ 设 $z = z(x,y)$ 由方程 $x - az = e^{y + az}$（$a$ 是非零常数）确定，则 "
                       r"$(A)$ $\frac{\partial z}{\partial x} - \frac{\partial z}{\partial y} = \frac{1}{a}$ "
                       r"$(B)$ $\frac{\partial z}{\partial x} + \frac{\partial z}{\partial y} = \frac{1}{a}$ "
                       r"$(C)$ $\frac{\partial z}{\partial x} - \frac{\partial z}{\partial y} = -\frac{1}{a}$ "
                       r"$(D)$ $\frac{\partial z}{\partial x} + \frac{\partial z}{\partial y} = -\frac{1}{a}$",
            "options": {
                "A": r"$\frac{\partial z}{\partial x} - \frac{\partial z}{\partial y} = \frac{1}{a}$",
                "B": r"$\frac{\partial z}{\partial x} + \frac{\partial z}{\partial y} = \frac{1}{a}$",
                "C": r"$\frac{\partial z}{\partial x} - \frac{\partial z}{\partial y} = -\frac{1}{a}$",
                "D": r"$\frac{\partial z}{\partial x} + \frac{\partial z}{\partial y} = -\frac{1}{a}$",
            },
            "correct_option": "D",
        },
        {
            "no": 2, "difficulty": "中等",
            "knowledge_points": ["无穷级数"],
            "question": r"$2.$ 幂级数 $\sum_{n=1}^{\infty} \left(\frac{3 + (-1)^n}{4}\right)^n x^{2n}$ 的收敛域是 "
                       r"$(A)$ $[-2,2]$ $(B)$ $[-1,1]$ $(C)$ $(-2,2)$ $(D)$ $(-1,1)$",
            "options": {"A": r"$[-2,2]$", "B": r"$[-1,1]$", "C": r"$(-2,2)$", "D": r"$(-1,1)$"},
            "correct_option": "C",
        },
        {
            "no": 3, "difficulty": "中等",
            "knowledge_points": ["一元函数微分学"],
            "question": r"$3.$ 设函数 $f(x)$ 在区间 $[-1,1]$ 上有定义，则 "
                       r"$(A)$ 当 $f(x)$ 在 $(-1,0)$ 单调递减，在 $(0,1)$ 单调递增，$f(0)$ 是极小值 "
                       r"$(B)$ 当 $f(0)$ 是极小值时，$f(x)$ 在 $(-1,0)$ 单调递减，在 $(0,1)$ 单调递增 "
                       r"$(C)$ 当 $f(x)$ 的图形在 $[-1,1]$ 是凹的时，$\frac{f(x)-f(1)}{x-1}$ 在 $[-1,1]$ 单调递增 "
                       r"$(D)$ $\frac{f(x)-f(1)}{x-1}$ 在 $[-1,1]$ 单调递增时，$f(x)$ 的图形在 $[-1,1]$ 是凸的",
            "options": {
                "A": r"当 $f(x)$ 在 $(-1,0)$ 单调递减，在 $(0,1)$ 单调递增，$f(0)$ 是极小值",
                "B": r"当 $f(0)$ 是极小值时，$f(x)$ 在 $(-1,0)$ 单调递减，在 $(0,1)$ 单调递增",
                "C": r"当 $f(x)$ 的图形在 $[-1,1]$ 是凹的时，$\frac{f(x)-f(1)}{x-1}$ 在 $[-1,1]$ 单调递增",
                "D": r"$\frac{f(x)-f(1)}{x-1}$ 在 $[-1,1]$ 单调递增时，$f(x)$ 的图形在 $[-1,1]$ 是凸的",
            },
            "correct_option": "C",
        },
        {
            "no": 4, "difficulty": "较难",
            "knowledge_points": ["重积分"],
            "question": r"$4.$ 设 $z = \sqrt{4 - x^2 - y^2}$ 与 $z = \sqrt{x^2 + y^2}$ 两个曲面相交的有界闭区域为 $\Omega$，$f(u)$ 为连续函数，则 $\iiint_\Omega f(x^2 + y^2 + z^2) dv$ 可以表示为 "
                       r"$(A)$ $\int_0^{2\pi} d\theta \int_0^{\sqrt{4-r^2}} dr \int_r^{\sqrt{4-r^2}} f(r^2 + z^2) r dz$ "
                       r"$(B)$ $\int_0^{2\pi} d\theta \int_0^{\sqrt{2}} dr \int_r^{\sqrt{4-r^2}} f(r^2 + z^2) r dz$ "
                       r"$(C)$ $\int_0^{2\pi} d\theta \int_0^{\frac{\pi}{4}} d\varphi \int_0^2 f(r^2) r^2 \sin\varphi dr$ "
                       r"$(D)$ $\int_0^{2\pi} d\theta \int_0^{\frac{\pi}{4}} d\varphi \int_0^{\sqrt{2}} f(r^2) r^2 \sin\varphi dr$",
            "options": {
                "A": r"$\int_0^{2\pi} d\theta \int_0^{\sqrt{4-r^2}} dr \int_r^{\sqrt{4-r^2}} f(r^2 + z^2) r dz$",
                "B": r"$\int_0^{2\pi} d\theta \int_0^{\sqrt{2}} dr \int_r^{\sqrt{4-r^2}} f(r^2 + z^2) r dz$",
                "C": r"$\int_0^{2\pi} d\theta \int_0^{\frac{\pi}{4}} d\varphi \int_0^2 f(r^2) r^2 \sin\varphi dr$",
                "D": r"$\int_0^{2\pi} d\theta \int_0^{\frac{\pi}{4}} d\varphi \int_0^{\sqrt{2}} f(r^2) r^2 \sin\varphi dr$",
            },
            "correct_option": "B",
        },
        {
            "no": 5, "difficulty": "中等",
            "knowledge_points": ["矩阵"],
            "question": r"$5.$ 单位矩阵经过若干次互换两行得到的矩阵成为置换矩阵，设 $A$ 为 $n$ 阶置换矩阵，$A^*$ 为 $A$ 的伴随矩阵，则 "
                       r"$(A)$ $A^*$ 为置换矩阵 $(B)$ $A^{-1}$ 为置换矩阵 $(C)$ $A^{-1} = A^*$ $(D)$ $A^{-1} = -A^*$",
            "options": {
                "A": r"$A^*$ 为置换矩阵", "B": r"$A^{-1}$ 为置换矩阵",
                "C": r"$A^{-1} = A^*$", "D": r"$A^{-1} = -A^*$",
            },
            "correct_option": "B",
        },
        {
            "no": 6, "difficulty": "中等",
            "knowledge_points": ["线性方程组"],
            "question": r"$6.$ 设 $A,B$ 为 $n$ 阶矩阵，$\beta$ 是 $n$ 维列向量，若 $A$ 的列向量组可由 $B$ 的列向量组表示，则 "
                       r"$(A)$ 当 $Ax = \beta$ 有解时，$Bx = \beta$ 有解 "
                       r"$(B)$ 当 $A^{\mathrm{T}}x = \beta$ 有解时，$B^{\mathrm{T}}x = \beta$ 有解 "
                       r"$(C)$ 当 $Bx = \beta$ 有解时，$Ax = \beta$ 有解 "
                       r"$(D)$ 当 $B^{\mathrm{T}}x = \beta$ 有解时，$A^{\mathrm{T}}x = \beta$ 有解",
            "options": {
                "A": r"当 $Ax = \beta$ 有解时，$Bx = \beta$ 有解",
                "B": r"当 $A^{\mathrm{T}}x = \beta$ 有解时，$B^{\mathrm{T}}x = \beta$ 有解",
                "C": r"当 $Bx = \beta$ 有解时，$Ax = \beta$ 有解",
                "D": r"当 $B^{\mathrm{T}}x = \beta$ 有解时，$A^{\mathrm{T}}x = \beta$ 有解",
            },
            "correct_option": "D",
        },
        {
            "no": 7, "difficulty": "较难",
            "knowledge_points": ["二次型"],
            "question": r"$7.$ 设二次型 $f(x_1,x_2,x_3) = a(x_1^2 + x_2^2 + x_3^2) + 4x_1x_2 + 4x_1x_3 + 4x_2x_3$，若方程 $f(x_1,x_2,x_3) = -1$ 表示的曲面为圆柱面，则 "
                       r"$(A)$ $a = -4$，且规范型为 $-y_1^2 - y_2^2 - y_3^2$ "
                       r"$(B)$ $a = -4$，且正交变换下标准型为 $-6y_1^2 - 6y_2^2$ "
                       r"$(C)$ $a = 2$，且规范型为 $-y_1^2 - y_2^2 - y_3^2$ "
                       r"$(D)$ $a = 2$，且正交变换下标准型为 $-6y_1^2 - 6y_2^2$",
            "options": {
                "A": r"$a = -4$，且规范型为 $-y_1^2 - y_2^2 - y_3^2$",
                "B": r"$a = -4$，且正交变换下标准型为 $-6y_1^2 - 6y_2^2$",
                "C": r"$a = 2$，且规范型为 $-y_1^2 - y_2^2 - y_3^2$",
                "D": r"$a = 2$，且正交变换下标准型为 $-6y_1^2 - 6y_2^2$",
            },
            "correct_option": "B",
        },
        {
            "no": 8, "difficulty": "中等",
            "knowledge_points": ["随机变量的数字特征"],
            "question": r"$8.$ 设随机变量 $X \sim N(1,1)$，$f(t) = E[(X + t)^2]$，则 $f(t)$ 的最小值点与最小值为 "
                       r"$(A)$ $1,2$ $(B)$ $1,4$ $(C)$ $-1,2$ $(D)$ $-1,4$",
            "options": {"A": r"$1,2$", "B": r"$1,4$", "C": r"$-1,2$", "D": r"$-1,4$"},
            "correct_option": "C",
        },
        {
            "no": 9, "difficulty": "中等",
            "knowledge_points": ["随机变量的数字特征"],
            "question": r"$9.$ 设连续型随机变量 $X$ 的分布函数为 $F(x)$，随机变量 $Y$ 的分布函数为 $F(ay+b)$，$X$ 的数学期望为 $\mu$，方差为 $\sigma^2 (\sigma>0)$。若 $Y$ 的数学期望与方差分别为 $0$ 和 $1$，则 "
                       r"$(A)$ $a = \sigma, b = \mu$ $(B)$ $a = \sigma, b = -\mu$ "
                       r"$(C)$ $a = \frac{1}{\sigma}, b = \mu$ $(D)$ $a = \frac{1}{\sigma}, b = -\mu$",
            "options": {
                "A": r"$a = \sigma, b = \mu$", "B": r"$a = \sigma, b = -\mu$",
                "C": r"$a = \frac{1}{\sigma}, b = \mu$", "D": r"$a = \frac{1}{\sigma}, b = -\mu$",
            },
            "correct_option": "D",
        },
        {
            "no": 10, "difficulty": "较难",
            "knowledge_points": ["随机变量及其分布"],
            "question": r"$10.$ 设随机变量 $X$ 的概率分布为 $P(X=k) = \frac{1}{2^{k+1}} + \frac{1}{3^k} (k=1,2,\dots)$，则对于任意的正整数 $m,n$ 有 "
                       r"$(A)$ $P\{X > m+n \mid X > m\} = P\{X > m\}$ "
                       r"$(B)$ $P\{X > m+n \mid X > m\} = P\{X > n\}$ "
                       r"$(C)$ $P\{X > m+n \mid X > m\} > P\{X > m\}$ "
                       r"$(D)$ $P\{X > m+n \mid X > m\} < P\{X > n\}$",
            "options": {
                "A": r"$P\{X > m+n \mid X > m\} = P\{X > m\}$",
                "B": r"$P\{X > m+n \mid X > m\} = P\{X > n\}$",
                "C": r"$P\{X > m+n \mid X > m\} > P\{X > m\}$",
                "D": r"$P\{X > m+n \mid X > m\} < P\{X > n\}$",
            },
            "correct_option": "D",
        },
    ],
    "填空题": [
        {
            "no": 11, "difficulty": "中等",
            "knowledge_points": ["向量与空间解析几何"],
            "question": r"$11.$ 设向量 $v_1 = (0, x, z)$，$v_2 = (y, 0, 1)$，记 $F = v_1 + v_2$，则 $\operatorname{div} F = \_\_\_\_\_\_$",
            "standard_answer": r"x + 1",
        },
        {
            "no": 12, "difficulty": "基础",
            "knowledge_points": ["极限"],
            "question": r"$12.$ 极限 $\lim_{x \to 0} \frac{1}{x} \ln(1+x) \cdot \frac{x}{\sin x} = \_\_\_\_\_\_$",
            "standard_answer": r"1",
        },
        {
            "no": 13, "difficulty": "中等",
            "knowledge_points": ["一元函数微分学"],
            "question": r"$13.$ 设函数 $y = y(x)$ 由参数方程 $\begin{cases} x = 2\sin^2 t \\ y = t + \cos t \end{cases}$ 在 $(0,\frac{\pi}{2})$ 确定，则 $\left.\frac{d^2y}{dx^2}\right|_{t=\frac{\pi}{4}} = \_\_\_\_\_\_$",
            "standard_answer": r"\frac{\sqrt{2}}{4}",
        },
        {
            "no": 14, "difficulty": "中等",
            "knowledge_points": ["定积分"],
            "question": r"$14.$ $\int_1^{+\infty} \frac{\ln(x+1)}{x^2} dx = \_\_\_\_\_\_$",
            "standard_answer": r"\ln 2",
        },
        {
            "no": 15, "difficulty": "较难",
            "knowledge_points": ["矩阵的特征值与特征向量"],
            "question": r"$15.$ 设矩阵 $A = \begin{pmatrix} 1 & 0 & 0 \\ 2 & a & 2 \\ 0 & 2 & a \end{pmatrix}$，$B = \begin{pmatrix} a & -1 & -1 \\ -1 & 2 & -1 \\ -1 & -1 & a \end{pmatrix}$，$m(X)$ 是 3 阶矩阵 $X$ 对实的特征值的最大值，且 $m(A) = m(B)$，则 $a$ 的取值范围是 \_\_\_\_\_\_",
            "standard_answer": r"[-2,2]",
        },
        {
            "no": 16, "difficulty": "中等",
            "knowledge_points": ["随机变量的数字特征"],
            "question": r"$16.$ 设随机变量 $X$ 服从参数为 1 的泊松分布，$Y$ 服从参数为 3 的泊松分布，且 $X$ 与 $Y-X$ 相互独立，则 $E(XY) = \_\_\_\_\_\_$",
            "standard_answer": r"4",
        },
    ],
    "解答题": [
        {
            "no": 17, "difficulty": "中等", "score": 10,
            "knowledge_points": ["多元函数微分学"],
            "question": r"$17.$ (本题满分10分) 求函数 $f(x,y) = (2x^2 - y^2)e^x$ 的极值。",
            "standard_answer": r"极大值 f(0,0) = 0，极小值 f(1,\pm 2) = -2e",
        },
        {
            "no": 18, "difficulty": "较难", "score": 12,
            "knowledge_points": ["常微分方程"],
            "question": r"$18.$ (本题满分12分) 设 $f(u)$ 在 $(0,+\infty)$ 内具有3阶连续导数，且存在可微函数 $F(x,y)$ 使 $dF(x,y) = \frac{f(xy)}{x^2 y} dx + \frac{f''(xy)}{xy^2} dy$ ($xy>0$)。(1) 证明：$\frac{f'(u)}{u} - \frac{f(u)}{u} = c$，$c$ 为常数；(2) 设 $f(1) = 1$，$f'(1) = -1$，$f''(1) = 0$，求 $f(u)$ 的表达式。",
            "standard_answer": r"(1) 证明略 (2) f(u) = \ln u - \frac{1}{u} + 1",
        },
        {
            "no": 19, "difficulty": "较难", "score": 12,
            "knowledge_points": ["曲线积分与曲面积分"],
            "question": r"$19.$ (本题满分12分) 设有向曲线 $L$ 为椭圆 $x^2 + 3y^2 = 1$ 上沿逆时针方向从点 $A\left(-\frac{1}{2}, -\frac{1}{2}\right)$ 到点 $B\left(\frac{1}{2}, \frac{1}{2}\right)$ 的部分，计算曲线积分 $I = \int_L (e^{x^2} \sin x - 2xy) dx + (6x - x^2 - y \cos^4 y) dy$。",
            "standard_answer": r"0",
        },
        {
            "no": 20, "difficulty": "较难", "score": 12,
            "knowledge_points": ["中值定理"],
            "question": r"$20.$ (本题满分12分) 设可导函数 $f(x)$ 严格单调递增且满足 $\int_{-1}^1 f(x) dx = 0$，记 $a = \int_0^1 f(x) dx$。(1) 证明 $a > 0$；(2) 令 $F(x) = a(1-x^2) + \int_1^x f(t) dt$，证明：存在 $\xi \in (-1,1)$ 使 $F''(\xi) = 0$。",
            "standard_answer": r"证明略",
        },
        {
            "no": 21, "difficulty": "较难", "score": 12,
            "knowledge_points": ["向量组与线性空间"],
            "question": r"$21.$ (本题满分12分) 已知向量组 $\alpha_1 = \begin{pmatrix} 1 \\ 0 \\ -1 \\ -1 \end{pmatrix}$，$\alpha_2 = \begin{pmatrix} 1 \\ -1 \\ 0 \\ -2 \end{pmatrix}$，$\alpha_3 = \begin{pmatrix} 0 \\ -1 \\ 1 \\ -1 \end{pmatrix}$，$\alpha_4 = \begin{pmatrix} 0 \\ 1 \\ -1 \\ 1 \end{pmatrix}$，记 $A = (\alpha_1,\alpha_2,\alpha_3,\alpha_4)$，$G = (\alpha_1,\alpha_2)$。(1) 证明：$\alpha_1,\alpha_2$ 是极大线性无关组。(2) 求矩阵 $H$ 使得 $A = GH$，并求 $A^{10}$。",
            "standard_answer": r"A^{10} = A",
        },
        {
            "no": 22, "difficulty": "较难", "score": 12,
            "knowledge_points": ["参数估计"],
            "question": r"$22.$ (本题满分12分) 假设某种元件寿命服从指数分布，其均值 $\theta$ 是未知参数，为估计 $\theta$，取 $n$ 个这种元件同时做寿命实验，试验直到出现 $k(1 \le k \le n)$ 个元件失效时停止。(1) 若 $k=1$，(i) 求 $T$ 的概率密度；(ii) 确定 $a$ 使 $\hat{\theta} = aT$ 是 $\theta$ 的无偏估计；(2) 求 $\theta$ 的最大似然估计值。",
            "standard_answer": r"(1)(i) f_T(t) = \frac{n}{\theta} e^{-\frac{nt}{\theta}}, t>0; (ii) a = \frac{1}{n}, D(\hat{\theta}) = \frac{\theta^2}{n^2}; (2) \hat{\theta} = \frac{1}{k}[\sum_{i=1}^k t_i + (n-k)t_k]",
        },
    ],
}


def import_all():
    """Import all 2026 Math I questions."""
    db = QuestionDB()
    importer = QuestionImporter(db)
    stats = db.stats()
    print(f"Current DB: {stats['total']} questions")

    total_imported = 0
    total_skipped = 0

    for qtype, questions in RAW_QUESTIONS.items():
        for q in questions:
            # Build question dict
            item = {
                "year": 2026,
                "category": "数学一",
                "question_type": qtype,
                "question_no": q["no"],
                "score": q.get("score", 5 if qtype == "选择题" else 5 if qtype == "填空题" else 10),
                "difficulty": q["difficulty"],
                "knowledge_points": q["knowledge_points"],
                "tags": q["knowledge_points"],
                "question": q["question"],
                "source": "import_2026",
            }

            if qtype == "选择题":
                item["options"] = q["options"]
                item["correct_option"] = q["correct_option"]
                item["standard_answer"] = q["correct_option"]
            else:
                item["standard_answer"] = q.get("standard_answer", "")

            # Check for duplicates
            existing = db.search(keyword=f"2026-数一-{q['no']:03d}", limit=1)
            if existing and any(r.get("question_id", "").startswith("2026") for r in existing):
                print(f"  Skip: 2026-数一-{q['no']:03d} (already exists)")
                total_skipped += 1
                continue

            result = db.insert(item)
            if result["success"]:
                print(f"  OK: {result['question_id']} ({qtype} #{q['no']})")
                total_imported += 1
            else:
                print(f"  FAIL: {qtype} #{q['no']} — {result.get('warnings', [])}")

    stats = db.stats()
    print(f"\nDone. Imported: {total_imported}, Skipped: {total_skipped}")
    print(f"DB now has {stats['total']} questions")


if __name__ == "__main__":
    import_all()
