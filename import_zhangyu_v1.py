"""Import Zhang Yu 8-exam-set Volume 1 questions."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import QuestionDB, QuestionImporter

QUESTIONS = {
    "选择题": [
        {"no":1,"difficulty":"中等","score":5,"knowledge_points":["极限","无穷小量比较"],
         "question":r"$1.$ 当 $x \to 0$ 时，以下无穷小量阶数最高的是 "
            r"$(A)$ $\int_0^{\sin x} [(1+t)^t - 1] dt$ "
            r"$(B)$ $\int_0^{\sin^2 x} (1+t)^t dt$ "
            r"$(C)$ $\int_0^{\sin x} [e^{-(1+t)^t}] dt$ "
            r"$(D)$ $\int_0^{\sin^2 x} (te^t - t) dt$",
         "options":{"A":r"$\int_0^{\sin x} [(1+t)^t - 1] dt$","B":r"$\int_0^{\sin^2 x} (1+t)^t dt$","C":r"$\int_0^{\sin x} [e^{-(1+t)^t}] dt$","D":r"$\int_0^{\sin^2 x} (te^t - t) dt$"},"correct_option":"A"},
        {"no":2,"difficulty":"中等","score":5,"knowledge_points":["重积分"],
         "question":r"$2.$ 设 $I_i = \iint_{D_i} e^{-(x^2+y^2)} d\sigma$，$i=1,2,3$，其中 $D_1 = \{(x,y) \mid x^2+y^2 \le R^2\}$，$D_2 = \{(x,y) \mid x^2+y^2 \ge 2R^2\}$，$D_3 = \{(x,y) \mid |x| \le R, |y| \le R\}$，$R>0$，则 "
            r"$(A)$ $I_1 < I_2 < I_3$ $(B)$ $I_2 < I_3 < I_1$ $(C)$ $I_1 < I_3 < I_2$ $(D)$ $I_3 < I_2 < I_1$",
         "options":{"A":r"$I_1 < I_2 < I_3$","B":r"$I_2 < I_3 < I_1$","C":r"$I_1 < I_3 < I_2$","D":r"$I_3 < I_2 < I_1$"},"correct_option":"B"},
        {"no":3,"difficulty":"中等","score":5,"knowledge_points":["无穷级数"],
         "question":r"$3.$ 设级数 $\sum_{n=1}^\infty \frac{1}{n\sqrt{n}}$，② $\sum_{n=2}^\infty \frac{1}{n\sqrt{\ln n}}$，则 "
            r"$(A)$ ①收敛，②发散 $(B)$ ①发散，②收敛 $(C)$ ①②均收敛 $(D)$ ①②均发散",
         "options":{"A":r"①收敛，②发散","B":r"①发散，②收敛","C":r"①②均收敛","D":r"①②均发散"},"correct_option":"A"},
        {"no":4,"difficulty":"中等","score":5,"knowledge_points":["一元函数微分学"],
         "question":r"$4.$ 设 $f(x)$ 在 $(0,+\infty)$ 内可导，以下结论：① 若 $\lim_{x\to+\infty} f(x)$ 存在，则 $\lim_{x\to+\infty} f'(x)$ 存在；② 若 $\lim_{x\to+\infty} f'(x)$ 存在，则 $\lim_{x\to+\infty} f(x)$ 存在；③ 若 $\lim_{x\to+\infty} f'(x) = a \neq 0$，则 $f(x)$ 在 $x\to+\infty$ 时无界；④ 若 $\lim_{x\to+\infty} f'(x) = 0$，则 $f(x)$ 在 $x\to+\infty$ 时有界。正确的个数为 "
            r"$(A)$ $1$ $(B)$ $2$ $(C)$ $3$ $(D)$ $4$",
         "options":{"A":r"$1$","B":r"$2$","C":r"$3$","D":r"$4$"},"correct_option":"B"},
        {"no":5,"difficulty":"中等","score":5,"knowledge_points":["矩阵"],
         "question":r"$5.$ 设 $A = \begin{pmatrix} a & 1 & 1 \\ 1 & a & a \\ 1 & 1 & a \end{pmatrix}$ 可经初等列变换化成 $B = \begin{pmatrix} a & 1 & 1 \\ 1 & a & 1 \\ 1 & 1 & a \end{pmatrix}$，则 $a$ 的取值范围为 "
            r"$(A)$ $\{a \mid a \in \mathbf{R}, a \neq -2\}$ $(B)$ $\{a \mid a \in \mathbf{R}, a \neq -2, a \neq -1\}$ $(C)$ $\{a \mid a \in \mathbf{R}, a \neq 1, a \neq -1\}$ $(D)$ $\{a \mid a \in \mathbf{R}, a \neq -1\}$",
         "options":{"A":r"$\{a \mid a \in \mathbf{R}, a \neq -2\}$","B":r"$\{a \mid a \in \mathbf{R}, a \neq -2, a \neq -1\}$","C":r"$\{a \mid a \in \mathbf{R}, a \neq 1, a \neq -1\}$","D":r"$\{a \mid a \in \mathbf{R}, a \neq -1\}$"},"correct_option":"D"},
        {"no":6,"difficulty":"中等","score":5,"knowledge_points":["二次型"],
         "question":r"$6.$ 设二次型 $f(x_1,x_2,x_3)$ 在正交变换 $x = Py$ 下的标准形为 $y_1^2 + y_2^2 - 2y_3^2$，其中 $P = (e_1, e_2, e_3)$。若 $Q = (-e_3, e_2, e_1)$，则 $f(x_1,x_2,x_3)$ 在正交变换 $x = Qy$ 下的标准形为 "
            r"$(A)$ $2y_1^2 - y_2^2 + y_3^2$ $(B)$ $2y_1^2 + y_2^2 - y_3^2$ $(C)$ $-2y_1^2 + y_2^2 + y_3^2$ $(D)$ $-2y_1^2 - y_2^2 + y_3^2$",
         "options":{"A":r"$2y_1^2 - y_2^2 + y_3^2$","B":r"$2y_1^2 + y_2^2 - y_3^2$","C":r"$-2y_1^2 + y_2^2 + y_3^2$","D":r"$-2y_1^2 - y_2^2 + y_3^2$"},"correct_option":"C"},
        {"no":7,"difficulty":"较难","score":5,"knowledge_points":["矩阵"],
         "question": "$7.$ 设 $A$ 为 $n$ 阶矩阵，$r(A) = r$，$E_r$ 为 $r$ 阶单位矩阵，则 $A^2 = A$ 是存在列满秩矩阵 $C_{n\times r}$，使得 $A = CB$，$BC = E_r$ 的 "
            r"$(A)$ 充分非必要条件 $(B)$ 必要非充分条件 $(C)$ 充分必要条件 $(D)$ 既非充分又非必要条件",
         "options":{"A":r"充分非必要条件","B":r"必要非充分条件","C":r"充分必要条件","D":r"既非充分又非必要条件"},"correct_option":"B"},
        {"no":8,"difficulty":"中等","score":5,"knowledge_points":["随机变量及其分布"],
         "question":r"$8.$ 设 $X,Y$ 分别服从参数为 $n,m$ 的泊松分布，且 $n > m$，$F_X(x), F_Y(y)$ 分别是 $X,Y$ 的分布函数，$-\infty < z < +\infty$，则 "
            r"$(A)$ $P\{X \ge Y\} = 1$ $(B)$ $P\{X \le Y\} = 1$ $(C)$ $F_X(z) \ge F_Y(z)$ $(D)$ $F_X(z) \le F_Y(z)$",
         "options":{"A":r"$P\{X \ge Y\} = 1$","B":r"$P\{X \le Y\} = 1$","C":r"$F_X(z) \ge F_Y(z)$","D":r"$F_X(z) \le F_Y(z)$"},"correct_option":"C"},
        {"no":9,"difficulty":"较难","score":5,"knowledge_points":["随机变量的数字特征"],
         "question":r"$9.$ 设 $X_1,X_2,\dots,X_n (n \ge 2)$ 为来自正态总体 $X$ 的简单随机样本，$E(X) = \mu$，$D(X) = \sigma^2$，$\sigma > 0$，记 $Y = \frac{1}{n} \sum_{i=1}^n |X_i - \mu|$，则 $D(Y) =$ "
            r"$(A)$ $\frac{\sigma^2}{n} (1 - \frac{2}{\pi})$ $(B)$ $\frac{\sigma^2}{n} (1 - \frac{\pi}{2})$ $(C)$ $\frac{\sigma^2}{n^2} (1 - \frac{2}{\pi})$ $(D)$ $\frac{\sigma^2}{n^2} (1 - \pi)$",
         "options":{"A":r"$\frac{\sigma^2}{n} (1 - \frac{2}{\pi})$","B":r"$\frac{\sigma^2}{n} (1 - \frac{\pi}{2})$","C":r"$\frac{\sigma^2}{n^2} (1 - \frac{2}{\pi})$","D":r"$\frac{\sigma^2}{n^2} (1 - \pi)$"},"correct_option":"A"},
        {"no":10,"difficulty":"较难","score":5,"knowledge_points":["假设检验"],
         "question":r"$10.$ 设总体 $X \sim N(\mu,1)$，$H_0: \mu = 0$，$H_1: \mu = 1$。来自总体 $X$ 的样本容量为9的简单随机样本均值为 $\overline{X}$，设拒绝域为 $W = \{\overline{X} \ge 0.55\}$，则不犯第二类错误的概率为 "
            r"$(A)$ $1 - \Phi(1.35)$ $(B)$ $\Phi(1.35)$ $(C)$ $\Phi(1.65)$ $(D)$ $1 - \Phi(1.65)$",
         "options":{"A":r"$1 - \Phi(1.35)$","B":r"$\Phi(1.35)$","C":r"$\Phi(1.65)$","D":r"$1 - \Phi(1.65)$"},"correct_option":"B"},
    ],
    "填空题": [
        {"no":11,"difficulty":"中等","score":5,"knowledge_points":["极限"],
         "question":r"$11.$ $\lim_{x\to 0} \frac{|x|^{x+2}}{\sqrt{1+x^2}-1} = \_\_\_\_\_\_$","standard_answer":r"2"},
        {"no":12,"difficulty":"中等","score":5,"knowledge_points":["多元函数微分学"],
         "question":r"$12.$ $z = \arcsin y^x$ 在点 $(-1,2)$ 处的全微分为 $dz = \_\_\_\_\_\_$","standard_answer":r"-2\ln 2 \cdot dx - \frac{1}{2} dy"},
        {"no":13,"difficulty":"中等","score":5,"knowledge_points":["一元函数微分学"],
         "question":r"$13.$ 设 $e^{ax} \ge 1 + x$ 对任意实数 $x$ 均成立，则 $a$ 的取值范围为 $\_\_\_\_\_\_$","standard_answer":r"[1, +\infty)"},
        {"no":14,"difficulty":"较难","score":5,"knowledge_points":["曲线积分与曲面积分"],
         "question":r"$14.$ 已知 $\Omega = \{(x,y,z) \mid y^2 + z^2 \le 1, 0 \le x \le 1\}$，$\Sigma$ 为 $\Omega$ 的边界面且取外侧，则 $\iint_{\Sigma} (y^3 + z \sin x) dx dy + z dx dy = \_\_\_\_\_\_$","standard_answer":r"\pi"},
        {"no":15,"difficulty":"较难","score":5,"knowledge_points":["线性方程组"],
         "question":r"$15.$ 设四元齐次线性方程组（I）$\begin{cases} 2x_1 + 3x_2 - x_3 = 0 \\ x_1 + 2x_2 + x_3 - x_4 = 0 \end{cases}$，且四元齐次线性方程组（II）的一个基础解系为 $\xi_1 = (2,-1,k+2,1)^{\mathrm{T}}$，$\xi_2 = (-1,2,4,k+8)^{\mathrm{T}}$，若方程组（I）与（II）没有非零公共解，则 $k$ 的取值范围为 $\_\_\_\_\_\_$","standard_answer":r"k \neq -2 且 k \neq -6"},
        {"no":16,"difficulty":"中等","score":5,"knowledge_points":["随机变量的数字特征"],
         "question":r"$16.$ 设随机变量 $X \sim B(2,\frac{1}{2})$，则 $E(e^{2X}) = \_\_\_\_\_\_$","standard_answer":r"\frac{1}{2}(1 + e^4)"},
    ],
    "解答题": [
        {"no":17,"difficulty":"中等","score":10,"knowledge_points":["重积分"],
         "question":r"$17.$ (本题满分10分) 计算 $\int_0^1 dx \int_1^x (e^{-y^2} + e^y \sin y) dy$。","standard_answer":r"e^{-1} - \frac{1}{2}e^{-2} - \frac{1}{2} + \sin 1 - 1"},
        {"no":18,"difficulty":"中等","score":12,"knowledge_points":["常微分方程"],
         "question":r"$18.$ (本题满分12分) 设 $y = y(x)$ 满足 $x^2 y' + (x^2 - 3)y^2 = 0$ 且 $y(1) = 1$。(1) 求 $y = y(x)$ 的表达式；(2) 计算 $\int_0^3 y^2(x) dx$。",
         "standard_answer":r"(1) y = \frac{3}{3 - x + x e^{3 - \frac{3}{x}}}; (2) 1"},
        {"no":19,"difficulty":"中等","score":12,"knowledge_points":["定积分"],
         "question":r"$19.$ (本题满分12分) 设 $f(x)$ 为连续函数，$T > 0$，证明：$f(x)$ 以 $T$ 为周期的充分必要条件是任给常数 $a$，$\int_a^{a+T} f(x) dx$ 为常数。","standard_answer":r"证明略"},
        {"no":20,"difficulty":"较难","score":12,"knowledge_points":["曲线积分与曲面积分"],
         "question":r"$20.$ (本题满分12分) 设 $\Gamma$ 为曲线 $\begin{cases} x^2 + y^2 + z^2 = a^2 \\ y = x \tan\theta \end{cases}$，其中 $a > 0$，$-\frac{\pi}{2} < \theta < \frac{\pi}{2}$ 且 $\theta \neq 0$，从 $x$ 轴的正向看去，$\Gamma$ 的方向为顺时针方向。求当 $\theta$ 为何值时，$I = \oint_{\Gamma} (y-z) dx + (z-x) dy + (x-y) dz$ 最大？并求出最大值。",
         "standard_answer":r"\theta = \frac{\pi}{4} 时 I 最大，最大值为 \sqrt{2}\pi a^2"},
        {"no":21,"difficulty":"较难","score":12,"knowledge_points":["矩阵"],
         "question":r"$21.$ (本题满分12分) 设矩阵 $A = \begin{pmatrix} -1 & 0 & 1 \\ 1 & 2 & 0 \\ a & 0 & 3 \end{pmatrix}$ 与 $B = \begin{pmatrix} 1 & b & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2 \end{pmatrix}$ 相似，且 $Ax = x + (b, -b, 2b)^{\mathrm{T}}$ 的一个解为 $(0, -1, 1)^{\mathrm{T}}$，求 (1) $a, b$ 的值；(2) $A^{100}$。",
         "standard_answer":r"(1) a = 3, b = 2; (2) A^{100} = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 3^{100} & 0 \\ 0 & 0 & 2^{100} \end{pmatrix}"},
        {"no":22,"difficulty":"较难","score":12,"knowledge_points":["参数估计"],
         "question":r"$22.$ (本题满分12分) 设一组两台机器同时启动开始制作产品，其独立工作时间 $T_1, T_2$ 均服从参数为1的指数分布，$X$ 表示两台机器较早出现故障的时间，且收益 $Y = \begin{cases} X-1, & X > 1 \\ 0, & X \le 1 \end{cases}$。(1) 求 $P\{Y > 0\}$；(2) 若有 $N$ 组机器承接制作产品的任务，收益大于0的组数记为 $M$，记 $N \sim P(2e^2)$，在 $N = n (n \ge 1)$ 的条件下，$M \sim B(n, P\{Y > 0\})$，求 $M$ 的概率分布。",
         "standard_answer":r"(1) P\{Y > 0\} = e^{-2}; (2) M \sim P(2), P\{M = m\} = \frac{2^m}{m!} e^{-2}, m = 0,1,2,\dots"},
    ],
}


def import_all():
    db = QuestionDB()
    importer = QuestionImporter(db)
    stats = db.stats()
    print(f"Current DB: {stats['total']} questions")

    total_imported = 0
    total_skipped = 0
    category = "26宇哥八套卷"
    volume = "卷一"

    for qtype, questions in QUESTIONS.items():
        for q in questions:
            qid = f"2026-宇哥-{volume}-{q['no']:03d}"

            existing = db.get(qid)
            if existing:
                print(f"  Skip: {qid} (exists)")
                total_skipped += 1
                continue

            item = {
                "question_id": qid,
                "year": 2026,
                "category": category,
                "volume": volume,
                "question_type": qtype,
                "question_no": q["no"],
                "score": q.get("score", 5),
                "difficulty": q["difficulty"],
                "knowledge_points": q["knowledge_points"],
                "tags": q["knowledge_points"],
                "question": q["question"],
                "source": "import_zhangyu_v1",
            }

            if qtype == "选择题":
                item["options"] = q["options"]
                item["correct_option"] = q["correct_option"]
                item["standard_answer"] = q["correct_option"]
            else:
                item["standard_answer"] = q.get("standard_answer", "")

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
