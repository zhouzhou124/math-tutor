"""Import 2011 Math I exam questions."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database.question_db import QuestionDB

db = QuestionDB()

questions = [
    # ── 选择题 (1-8, 4分) ──
    (1, "选择题", r"曲线 $y = (x-1)(x-2)^2(x-3)^3(x-4)^4$ 的拐点是",
     {"A": r"$(1,0)$", "B": r"$(2,0)$", "C": r"$(3,0)$", "D": r"$(4,0)$"}, "C", 4),
    (2, "选择题", r"设数列 $\{a_n\}$ 单调减少，$\lim_{n\to\infty} a_n = 0$，$S_n = \sum_{k=1}^n a_k$ 无界，则幂级数 $\sum_{n=1}^\infty a_n (x-1)^n$ 的收敛域为",
     {"A": r"$(-1,1]$", "B": r"$[-1,1)$", "C": r"$[0,2)$", "D": r"$(0,2]$"}, "D", 4),
    (3, "选择题", r"设函数 $f(x)$ 具有二阶连续导数，且 $f'(x) > 0$，$f''(0) = 0$，则函数 $z = f(x)\ln f(y)$ 在点 $(0,0)$ 处取得极小值的一个充分条件是",
     {"A": r"$f(0) > 1, f''(0) > 0$", "B": r"$f(0) > 1, f''(0) < 0$", "C": r"$f(0) < 1, f''(0) > 0$", "D": r"$f(0) < 1, f''(0) < 0$"}, "A", 4),
    (4, "选择题", r"设 $I = \int_0^{\frac{\pi}{4}} \ln(\sin x) dx$，$J = \int_0^{\frac{\pi}{4}} \ln(\cot x) dx$，$K = \int_0^{\frac{\pi}{4}} \ln(\cos x) dx$，则 $I,J,K$ 的大小关系为",
     {"A": r"$I < J < K$", "B": r"$I < K < J$", "C": r"$J < I < K$", "D": r"$K < J < I$"}, "B", 4),
    (5, "选择题", r"设 $A$ 为3阶矩阵，将 $A$ 的第2列加到第1列得矩阵 $B$，再交换 $B$ 的第2行与第3行得单位矩阵。记 $P_1 = \begin{pmatrix} 1 & 0 & 0 \\ 1 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$，$P_2 = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & 1 & 0 \end{pmatrix}$，则 $A =$",
     {"A": r"$P_1 P_2$", "B": r"$P_1^{-1} P_2$", "C": r"$P_2 P_1$", "D": r"$P_2 P_1^{-1}$"}, "D", 4),
    (6, "选择题", r"设 $A = (\alpha_1,\alpha_2,\alpha_3,\alpha_4)$ 是4阶矩阵，$A^*$ 为 $A$ 的伴随矩阵。若 $(1,0,1,0)^{\mathrm{T}}$ 是方程组 $Ax = 0$ 的一个基础解系，则 $A^*x = 0$ 的基础解系可为",
     {"A": r"$\alpha_1,\alpha_3$", "B": r"$\alpha_1,\alpha_2$", "C": r"$\alpha_1,\alpha_2,\alpha_3$", "D": r"$\alpha_2,\alpha_3,\alpha_4$"}, "D", 4),
    (7, "选择题", r"设 $F_1(x)$ 与 $F_2(x)$ 为两个分布函数，其相应的概率密度 $f_1(x)$ 与 $f_2(x)$ 是连续函数，则必为概率密度的是",
     {"A": r"$f_1(x)f_2(x)$", "B": r"$2f_2(x)F_1(x)$", "C": r"$f_1(x)F_2(x)$", "D": r"$f_1(x)F_2(x) + f_2(x)F_1(x)$"}, "D", 4),
    (8, "选择题", r"设随机变量 $X$ 与 $Y$ 相互独立，且 $E(X)$ 与 $E(Y)$ 存在，记 $U = \max\{X,Y\}$，$V = \min\{X,Y\}$，则 $E(UV) =$",
     {"A": r"$E(U)E(V)$", "B": r"$E(X)E(Y)$", "C": r"$E(U)E(Y)$", "D": r"$E(X)E(V)$"}, "B", 4),

    # ── 填空题 (9-14, 4分) ──
    (9, "填空题", r"曲线 $y = \int_0^x \tan t dt$（$0 \le x \le \frac{\pi}{4}$）的弧长 $s =$ ______", None, r"$\ln(1+\sqrt{2})$", 4),
    (10, "填空题", r"微分方程 $y' + y = e^{-x} \cos x$ 满足条件 $y(0)=0$ 的解为 $y =$ ______", None, r"$e^{-x}\sin x$", 4),
    (11, "填空题", r"设函数 $F(x,y) = \int_0^{xy} \frac{\sin t}{1+t^2} dt$，则 $\left.\frac{\partial^2 F}{\partial x^2}\right|_{(0,2)} =$ ______", None, "0", 4),
    (12, "填空题", r"设 $L$ 是柱面 $x^2 + y^2 = 1$ 与平面 $z = x + y$ 的交线，从 $z$ 轴正向往 $z$ 轴负向看去为逆时针方向，则曲线积分 $\oint_L xz dx + x dy + \frac{y^2}{2} dz =$ ______", None, "0", 4),
    (13, "填空题", r"若二次曲面的方程 $x^2 + 3y^2 + z^2 + 2a xy + 2xz + 2yz = 4$ 经正交变换化为 $y_1^2 + 4z_1^2 = 4$，则 $a =$ ______", None, "1", 4),
    (14, "填空题", r"设二维随机变量 $(X,Y)$ 服从正态分布 $N(\mu,\mu;\sigma^2,\sigma^2;0)$，则 $E(XY^2) =$ ______", None, r"$\mu^3 + \mu\sigma^2$", 4),

    # ── 解答题 (15-23) ──
    (15, "解答题", r"求极限 $\lim_{x\to 0} \left[ \frac{\ln(1+x)}{x} \right]^{\frac{1}{x-1}}$。", None, r"$e^{\frac{1}{2}}$", 10),
    (16, "解答题", r"设函数 $z = f(xy, yg(x))$，其中函数 $f$ 具有二阶连续偏导数，函数 $g(x)$ 可导，且在 $x=1$ 处取得极值 $g(1)=1$。求 $\left.\frac{\partial^2 z}{\partial x \partial y}\right|_{\substack{x=1\\y=1}}$。", None, r"$f_{11}(1,1) \cdot g'(1) + f_2(1,1)$", 9),
    (17, "解答题", r"求方程 $k \arctan x - x = 0$ 不同实根的个数，其中 $k$ 为参数。", None, r"当 $k \le 1$ 时，只有 $x=0$ 一个实根；当 $k > 1$ 时，有三个不同实根", 10),
    (18, "解答题", r"(I) 证明：对任意的正整数 $n$，都有 $\frac{1}{n+1} < \ln\left(1+\frac{1}{n}\right) < \frac{1}{n}$ 成立；(II) 设 $a_n = 1 + \frac{1}{2} + \cdots + \frac{1}{n} - \ln n$，证明数列 $\{a_n\}$ 收敛。", None, r"证明略。", 10),
    (19, "解答题", r"已知函数 $f(x,y)$ 具有二阶连续偏导数，且 $f(1,y)=0$，$f(x,1)=0$，$\iint_D f(x,y) dxdy = a$，其中 $D = \{(x,y) \mid 0 \le x \le 1, 0 \le y \le 1\}$，计算二重积分 $I = \iint_D xy f_{xy}(x,y) dxdy$。", None, r"$I = a$", 11),
    (20, "解答题", r"设向量组 $\alpha_1 = (1,0,1)^{\mathrm{T}}$，$\alpha_2 = (0,1,1)^{\mathrm{T}}$，$\alpha_3 = (1,3,5)^{\mathrm{T}}$ 不能由向量组 $\beta_1 = (1,1,1)^{\mathrm{T}}$，$\beta_2 = (1,2,3)^{\mathrm{T}}$，$\beta_3 = (3,4,a)^{\mathrm{T}}$ 线性表示。(I) 求 $a$ 的值；(II) 将 $\beta_1,\beta_2,\beta_3$ 用 $\alpha_1,\alpha_2,\alpha_3$ 线性表示。",
     None, r"(I) $a = 1$。(II) $\beta_1 = \alpha_1 + \alpha_2$，$\beta_2 = \alpha_2 + \alpha_3$，$\beta_3 = -\alpha_1 + 2\alpha_2 + \alpha_3$", 11),
    (21, "解答题", r"设 $A$ 为3阶实对称矩阵，$A$ 的秩为2，且 $A \begin{pmatrix} 1 & 1 & 0 \\ 0 & 0 & 1 \\ -1 & 1 & 1 \end{pmatrix} = \begin{pmatrix} -1 & 1 & 0 \\ 0 & 0 & 1 \\ 1 & 1 & 1 \end{pmatrix}$。(I) 求 $A$ 的所有特征值与特征向量；(II) 求矩阵 $A$。",
     None, r"(I) 特征值 $\lambda_1=2$（$k(1,1,0)^{\mathrm{T}}$），$\lambda_2=1$（$k(1,-1,0)^{\mathrm{T}}$），$\lambda_3=0$（$k(0,0,1)^{\mathrm{T}}$）。(II) $A = \begin{pmatrix} 2 & 1 & 0 \\ 1 & 2 & 0 \\ 0 & 0 & 0 \end{pmatrix}$", 11),
    (22, "解答题", r"设随机变量 $X$ 与 $Y$ 的概率分布分别为：$X$ 取值 $0,1$，概率分别为 $\frac{1}{3},\frac{2}{3}$；$Y$ 取值 $-1,0,1$，概率各为 $\frac{1}{3}$。且 $P\{X^2 = Y^2\} = 1$。(I) 求 $(X,Y)$ 的概率分布；(II) 求 $Z = XY$ 的概率分布；(III) 求 $X$ 与 $Y$ 的相关系数 $\rho_{XY}$。",
     None, r"(I) 分布略。(II) $P\{Z=-1\}=\frac{1}{6}$，$P\{Z=0\}=\frac{1}{3}$，$P\{Z=1\}=\frac{1}{2}$。(III) $\rho_{XY} = \frac{\sqrt{6}}{6}$", 11),
    (23, "解答题", r"设 $X_1,\dots,X_n$ 为来自正态总体 $N(\mu_0,\sigma^2)$ 的简单随机样本，$\mu_0$ 已知，$\sigma^2>0$ 未知。(I) 求 $\sigma^2$ 的最大似然估计 $\hat{\sigma}^2$；(II) 计算 $E(\hat{\sigma}^2)$ 和 $D(\hat{\sigma}^2)$。",
     None, r"(I) $\hat{\sigma}^2 = \frac{1}{n} \sum_{i=1}^n (X_i - \mu_0)^2$。(II) $E(\hat{\sigma}^2) = \sigma^2$，$D(\hat{\sigma}^2) = \frac{2\sigma^4}{n}$", 11),
]

print(f"Importing {len(questions)} questions...")
ok = skip = 0
for num, qt, qtext, opts, ans, score in questions:
    q = {
        "year": 2011, "category": "数学一", "question_type": qt,
        "question": qtext, "standard_answer": ans,
        "knowledge_points": [], "difficulty": "中等", "score": score,
        "source": "manual_import_2011",
    }
    if opts:
        q["options"] = opts
        q["correct_option"] = ans
    result = db.insert(q)
    if result["success"]:
        print(f"  OK {result['question_id']}")
        ok += 1
    else:
        print(f"  SKIP #{num}: {result.get('warnings', ['?'])[0][:80]}")
        skip += 1

print(f"\nDone: {ok} imported, {skip} skipped")
