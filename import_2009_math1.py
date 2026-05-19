"""Import 2009 Math I exam questions."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database.question_db import QuestionDB

db = QuestionDB()

questions = [
    (1, "选择题", r"当 $x\to 0$ 时，$f(x) = x - \sin ax$ 与 $g(x) = x^2 \ln(1-bx)$ 是等价无穷小量，则",
     {"A": r"$a=1, b=-\frac{1}{6}$", "B": r"$a=1, b=\frac{1}{6}$", "C": r"$a=-1, b=-\frac{1}{6}$", "D": r"$a=-1, b=\frac{1}{6}$"}, "A", 4),
    (2, "选择题", r"如图，正方形 $\{(x,y) \mid |x|\le 1, |y|\le 1\}$ 被其对角线划分为四个区域 $D_k (k=1,2,3,4)$，$I_k = \iint_{D_k} y\cos x dxdy$，则 $\max_{1\le k\le 4} |I_k| =$",
     {"A": r"$I_1$", "B": r"$I_2$", "C": r"$I_3$", "D": r"$I_4$"}, "B", 4),
    (3, "选择题", r"设函数 $y=f(x)$ 在区间 $[-1,3]$ 上的图形如图所示，则函数 $F(x) = \int_0^x f(t) dt$ 的图形为（图略）",
     {"A": "(图略)", "B": "(图略)", "C": "(图略)", "D": "(图略)"}, "D", 4),
    (4, "选择题", r"设有两个数列 $\{a_n\}, \{b_n\}$，若 $\lim_{n\to\infty} a_n = 0$，则",
     {"A": r"当 $\sum_{n=1}^\infty b_n$ 收敛时，$\sum_{n=1}^\infty a_n b_n$ 收敛",
      "B": r"当 $\sum_{n=1}^\infty b_n$ 发散时，$\sum_{n=1}^\infty a_n b_n$ 发散",
      "C": r"当 $\sum_{n=1}^\infty |b_n|$ 收敛时，$\sum_{n=1}^\infty a_n^2 b_n^2$ 收敛",
      "D": r"当 $\sum_{n=1}^\infty |b_n|$ 发散时，$\sum_{n=1}^\infty a_n^2 b_n^2$ 发散"}, "C", 4),
    (5, "选择题", r"设 $\alpha_1,\alpha_2,\alpha_3$ 是3维向量空间 $\mathbf{R}^3$ 的一组基，则由基 $\alpha_1, \frac{1}{2}\alpha_2, \frac{1}{3}\alpha_3$ 到基 $\alpha_1+\alpha_2, \alpha_2+\alpha_3, \alpha_3+\alpha_1$ 的过渡矩阵为",
     {"A": r"$\begin{pmatrix} 1 & 0 & 1 \\ 2 & 2 & 0 \\ 0 & 3 & 3 \end{pmatrix}$",
      "B": r"$\begin{pmatrix} 1 & 2 & 0 \\ 0 & 2 & 3 \\ 1 & 0 & 3 \end{pmatrix}$",
      "C": r"$\begin{pmatrix} \frac{1}{2} & -\frac{1}{4} & -\frac{1}{6} \\ -\frac{1}{2} & \frac{1}{4} & \frac{1}{6} \\ \frac{1}{2} & -\frac{1}{4} & \frac{1}{6} \end{pmatrix}$",
      "D": r"$\begin{pmatrix} \frac{1}{2} & -\frac{1}{2} & \frac{1}{2} \\ \frac{1}{4} & \frac{1}{4} & -\frac{1}{4} \\ -\frac{1}{6} & \frac{1}{6} & \frac{1}{6} \end{pmatrix}$"}, "C", 4),
    (6, "选择题", r"设 $A,B$ 均为2阶矩阵，$A^*, B^*$ 分别为 $A,B$ 的伴随矩阵，若 $|A|=2, |B|=3$，则分块矩阵 $\begin{pmatrix} O & A \\ B & O \end{pmatrix}$ 的伴随矩阵为",
     {"A": r"$\begin{pmatrix} O & 3B^* \\ 2A^* & O \end{pmatrix}$",
      "B": r"$\begin{pmatrix} O & 2B^* \\ 3A^* & O \end{pmatrix}$",
      "C": r"$\begin{pmatrix} O & 3A^* \\ 2B^* & O \end{pmatrix}$",
      "D": r"$\begin{pmatrix} O & 2A^* \\ 3B^* & O \end{pmatrix}$"}, "B", 4),
    (7, "选择题", r"设随机变量 $X$ 的分布函数为 $F(x) = 0.3\Phi(x) + 0.7\Phi\left(\frac{x-1}{2}\right)$，其中 $\Phi(x)$ 为标准正态分布的分布函数，则 $E(X) =$",
     {"A": "0", "B": "0.3", "C": "0.7", "D": "1"}, "C", 4),
    (8, "选择题", r"设随机变量 $X$ 与 $Y$ 相互独立，且 $X$ 服从标准正态分布 $N(0,1)$，$Y$ 的概率分布为 $P\{Y=0\} = P\{Y=1\} = \frac{1}{2}$。记 $F_Z(z)$ 为随机变量 $Z = XY$ 的分布函数，则函数 $F_Z(z)$ 的间断点个数为",
     {"A": "0", "B": "1", "C": "2", "D": "3"}, "B", 4),

    (9, "填空题", r"设函数 $f(u,v)$ 具有二阶连续偏导数，$z = f(x,xy)$，则 $\frac{\partial^2 z}{\partial x \partial y} =$ ______", None, r"$f_{12} + xy f_{22}$", 4),
    (10, "填空题", r"若二阶常系数线性齐次微分方程 $y'' + ay' + by = 0$ 的通解为 $y = (C_1 + C_2x)e^x$，则非齐次方程 $y'' + ay' + by = x$ 满足条件 $y(0)=2, y'(0)=0$ 的解为 $y =$ ______", None, r"$y = 2e^x - x - 2$", 4),
    (11, "填空题", r"已知曲线 $L: y = x^2 (0 \le x \le \sqrt{2})$，则 $\int_L x ds =$ ______", None, r"$\frac{1}{3}(5\sqrt{5} - 1)$", 4),
    (12, "填空题", r"设 $\Omega = \{(x,y,z) \mid x^2 + y^2 + z^2 \le 1\}$，则 $\iiint_\Omega z^2 dx dy dz =$ ______", None, r"$\frac{4\pi}{15}$", 4),
    (13, "填空题", r"若3维列向量 $\alpha, \beta$ 满足 $\alpha^{\mathrm{T}} \beta = 2$，其中 $\alpha^{\mathrm{T}}$ 为 $\alpha$ 的转置，则矩阵 $\beta \alpha^{\mathrm{T}}$ 的非零特征值为 ______", None, "2", 4),
    (14, "填空题", r"设 $X_1, X_2, \dots, X_m$ 为来自二项分布总体 $B(n,p)$ 的简单随机样本，$\overline{X}$ 和 $S^2$ 分别为样本均值和样本方差，若 $\overline{X} + kS^2$ 为 $np^2$ 的无偏估计量，则 $k =$ ______", None, "-1", 4),

    (15, "解答题", r"求二元函数 $f(x,y) = x^2(2 + y^2) + y \ln y$ 的极值。", None, r"极小值 $f(0,\frac{1}{e}) = -\frac{1}{e}$，无极大值", 9),
    (16, "解答题", r"设 $a_n$ 为曲线 $y = x^n$ 与 $y = x^{n+1} (n=1,2,\dots)$ 所围成区域的面积，记 $S_1 = \sum_{n=1}^\infty a_n$，$S_2 = \sum_{n=1}^\infty a_{2n-1}$，求 $S_1$ 与 $S_2$ 的值。", None, r"$S_1 = \frac{1}{2}$，$S_2 = \frac{1}{2}$", 9),
    (17, "解答题", r"椭球面 $S_1$ 是椭圆 $\frac{x^2}{4} + \frac{y^2}{3} = 1$ 绕 $x$ 轴旋转而成，圆锥面 $S_2$ 是由过点 $(4,0)$ 且与椭圆 $\frac{x^2}{4} + \frac{y^2}{3} = 1$ 相切的直线绕 $x$ 轴旋转而成。(I) 求 $S_1$ 及 $S_2$ 的方程；(II) 求 $S_1$ 与 $S_2$ 之间的立体的体积。", None, r"(I) $S_1: \frac{x^2}{4} + \frac{y^2+z^2}{3} = 1$，$S_2: x = \frac{4}{3}(y^2+z^2) + 4$；(II) $V = 4\pi$", 11),
    (18, "解答题", r"(I) 证明拉格朗日中值定理；(II) 证明：若函数 $f(x)$ 在 $x=0$ 处连续，在 $(0,\delta)(\delta>0)$ 内可导，且 $\lim_{x\to 0^+} f'(x) = A$，则 $f'_+(0)$ 存在，且 $f'_+(0) = A$。", None, r"证明略。", 11),
    (19, "解答题", r"计算曲面积分 $I = \iint_{\Sigma} \frac{x dy dz + y dz dx + z dx dy}{(x^2 + y^2 + z^2)^{\frac{3}{2}}}$，其中 $\Sigma$ 是曲面 $2x^2 + 2y^2 + z^2 = 4$ 的外侧。", None, "0", 10),
    (20, "解答题", r"设 $A = \begin{pmatrix} 1 & -1 & -1 \\ -1 & 1 & 1 \\ 0 & -4 & -2 \end{pmatrix}$，$\xi_1 = \begin{pmatrix} -1 \\ 1 \\ -2 \end{pmatrix}$。(I) 求满足 $A\xi_2 = \xi_1$，$A^2\xi_3 = \xi_1$ 的所有向量 $\xi_2, \xi_3$；(II) 证明 $\xi_1, \xi_2, \xi_3$ 线性无关。",
     None, r"(I) $\xi_2 = \begin{pmatrix} 1 \\ 0 \\ 1 \end{pmatrix} + k_1\begin{pmatrix} 1 \\ 1 \\ 0 \end{pmatrix}$，$\xi_3$ 略；(II) 证明略", 11),
    (21, "解答题", r"设二次型 $f(x_1,x_2,x_3) = a x_1^2 + a x_2^2 + (a-1)x_3^2 + 2x_1x_3 - 2x_2x_3$。(I) 求二次型 $f$ 的矩阵的所有特征值；(II) 若二次型 $f$ 的规范形为 $y_1^2 + y_2^2$，求 $a$ 的值。",
     None, r"(I) $\lambda_1 = a-1$, $\lambda_2 = a-1$, $\lambda_3 = a+1$；(II) $a = 0$", 11),
    (22, "解答题", r"袋中有1个红球、2个黑球与3个白球。现有放回地从袋中取两次，每次取一个球。以 $X,Y,Z$ 分别表示两次取球所取得的红球、黑球与白球的个数。(I) 求 $P\{X=1 \mid Z=0\}$；(II) 求二维随机变量 $(X,Y)$ 的概率分布。",
     None, r"(I) $P\{X=1 \mid Z=0\} = \frac{8}{15}$；(II) 分布略", 11),
    (23, "解答题", r"设总体 $X$ 的概率密度为 $f(x) = \begin{cases} \lambda^2 x e^{-\lambda x}, & x>0 \\ 0, & \text{其他} \end{cases}$，$\lambda>0$ 未知，$X_1,\dots,X_n$ 为样本。(I) 求 $\lambda$ 的矩估计量；(II) 求 $\lambda$ 的最大似然估计量。",
     None, r"(I) $\hat{\lambda} = \frac{2}{\overline{X}}$；(II) $\hat{\lambda} = \frac{2n}{\sum_{i=1}^n X_i}$", 11),
]

print(f"Importing {len(questions)} questions...")
ok = skip = 0
for num, qt, qtext, opts, ans, score in questions:
    q = {"year": 2009, "category": "数学一", "question_type": qt, "question": qtext,
         "standard_answer": ans, "knowledge_points": [], "difficulty": "中等",
         "score": score, "source": "manual_import_2009"}
    if opts:
        q["options"] = opts
        q["correct_option"] = ans
    r = db.insert(q)
    if r["success"]:
        print(f"  OK {r['question_id']}")
        ok += 1
    else:
        print(f"  SKIP #{num}: {r.get('warnings', ['?'])[0][:80]}")
        skip += 1

print(f"\nDone: {ok} imported, {skip} skipped")
