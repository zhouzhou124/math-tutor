"""Import 2010 Math I exam questions."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from database.question_db import QuestionDB

db = QuestionDB()

questions = [
    (1, "选择题", r"极限 $\lim_{x\to\infty} \left[ \frac{x^2}{(x-a)(x+b)} \right]^x =$",
     {"A": "1", "B": r"$e$", "C": r"$e^{a-b}$", "D": r"$e^{b-a}$"}, "D", 4),
    (2, "选择题", r"设函数 $z = z(x,y)$ 由方程 $F\left(\frac{y}{x}, \frac{z}{x}\right) = 0$ 确定，其中 $F$ 为可微函数，且 $F'_2 \neq 0$，则 $x\frac{\partial z}{\partial x} + y\frac{\partial z}{\partial y} =$",
     {"A": r"$x$", "B": r"$z$", "C": r"$-x$", "D": r"$-z$"}, "B", 4),
    (3, "选择题", r"设 $m,n$ 均是正整数，则反常积分 $\int_0^1 \frac{\sqrt[m]{\ln^2(1-x)}}{\sqrt[n]{x}} dx$ 的收敛性",
     {"A": r"仅与 $m$ 的取值有关", "B": r"仅与 $n$ 的取值有关", "C": r"与 $m,n$ 的取值都有关", "D": r"与 $m,n$ 的取值都无关"}, "D", 4),
    (4, "选择题", r"$\lim_{n\to\infty} \sum_{i=1}^n \sum_{j=1}^n \frac{n}{(n+i)(n^2+j^2)} =$",
     {"A": r"$\int_0^1 dx \int_0^x \frac{1}{(1+x)(1+y^2)} dy$", "B": r"$\int_0^1 dx \int_0^x \frac{1}{(1+x)(1+y)} dy$",
      "C": r"$\int_0^1 dx \int_0^1 \frac{1}{(1+x)(1+y)} dy$", "D": r"$\int_0^1 dx \int_0^1 \frac{1}{(1+x)(1+y^2)} dy$"}, "D", 4),
    (5, "选择题", r"设 $A$ 为 $m\times n$ 矩阵，$B$ 为 $n\times m$ 矩阵，$E$ 为 $m$ 阶单位矩阵，若 $AB = E$，则",
     {"A": r"$r(A)=m$，$r(B)=m$", "B": r"$r(A)=m$，$r(B)=n$", "C": r"$r(A)=n$，$r(B)=m$", "D": r"$r(A)=n$，$r(B)=n$"}, "A", 4),
    (6, "选择题", r"设 $A$ 为4阶实对称矩阵，且 $A^2 + A = O$。若 $A$ 的秩为3，则 $A$ 相似于",
     {"A": r"$\begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & 1 & 0 & 0 \\ 0 & 0 & 1 & 0 \\ 0 & 0 & 0 & 0 \end{pmatrix}$",
      "B": r"$\begin{pmatrix} -1 & 0 & 0 & 0 \\ 0 & -1 & 0 & 0 \\ 0 & 0 & -1 & 0 \\ 0 & 0 & 0 & 0 \end{pmatrix}$",
      "C": r"$\begin{pmatrix} 1 & 0 & 0 & 0 \\ 0 & -1 & 0 & 0 \\ 0 & 0 & -1 & 0 \\ 0 & 0 & 0 & 0 \end{pmatrix}$",
      "D": r"$\begin{pmatrix} -1 & 0 & 0 & 0 \\ 0 & -1 & 0 & 0 \\ 0 & 0 & 0 & 0 \\ 0 & 0 & 0 & 1 \end{pmatrix}$"}, "B", 4),
    (7, "选择题", r"设随机变量 $X$ 的分布函数 $F(x) = \begin{cases} 0, & x<0 \\ \frac{1}{2}, & 0\le x<1 \\ 1-e^{-x}, & x\ge 1 \end{cases}$，则 $P\{X=1\} =$",
     {"A": "0", "B": r"$\frac{1}{2}$", "C": r"$1-e^{-1}$", "D": r"$e^{-1}$"}, "C", 4),
    (8, "选择题", r"设 $f_1(x)$ 为标准正态分布的概率密度，$f_2(x)$ 为 $[-1,3]$ 上均匀分布的概率密度，若 $f(x) = \begin{cases} a f_1(x), & x\le 0 \\ b f_2(x), & x>0 \end{cases}$（$a>0,b>0$）为概率密度，则 $a,b$ 应满足",
     {"A": r"$2a+3b=4$", "B": r"$3a+2b=4$", "C": r"$a+b=1$", "D": r"$a+b=2$"}, "A", 4),

    (9, "填空题", r"设 $\begin{cases} x = e^{-t} \\ y = \int_0^t \ln(1+u^2) du \end{cases}$，则 $\left.\frac{d^2y}{dx^2}\right|_{t=0} =$ ______", None, r"$0$", 4),
    (10, "填空题", r"$\int_0^{\pi^2} \sqrt{x} \cos\sqrt{x} dx =$ ______", None, "2", 4),
    (11, "填空题", r"已知曲线 $L$ 的方程为 $y=1-|x|$（$x\in[-1,1]$），起点是 $(-1,0)$，终点为 $(1,0)$，则曲线积分 $\int_L xy dx + x^2 dy =$ ______", None, r"$\frac{1}{3}$", 4),
    (12, "填空题", r"设 $\Omega = \{(x,y,z) \mid x^2+y^2 \le z \le 1\}$，则 $\Omega$ 的形心竖坐标 $\bar{z} =$ ______", None, r"$\frac{2}{3}$", 4),
    (13, "填空题", r"设 $\alpha_1 = (1,2,-1,0)^{\mathrm{T}}$，$\alpha_2 = (1,1,0,2)^{\mathrm{T}}$，$\alpha_3 = (2,1,1,a)^{\mathrm{T}}$。若由 $\alpha_1,\alpha_2,\alpha_3$ 生成的向量空间的维数为2，则 $a =$ ______", None, "6", 4),
    (14, "填空题", r"设随机变量 $X$ 的概率分布为 $P\{X=k\} = \frac{C}{k!}$，$k=0,1,2,\dots$，则 $E(X^2) =$ ______", None, "2", 4),

    (15, "解答题", r"求微分方程 $y'' - 3y' + 2y = 2xe^x$ 的通解。", None, r"$y = C_1 e^x + C_2 e^{2x} - x^2 e^x - 2x e^x$", 10),
    (16, "解答题", r"求函数 $f(x) = \int_1^{x^2} (x^2 - t) e^{-t^2} dt$ 的单调区间与极值。", None, r"单调递增区间为 $(-\infty,0)$ 和 $(1,+\infty)$，单调递减区间为 $(0,1)$", 10),
    (17, "解答题", r"(I) 比较 $\int_0^1 |\ln t| [\ln(1+t)]^n dt$ 与 $\int_0^1 t^n |\ln t| dt$ 的大小；(II) 求 $\lim_{n\to\infty} u_n$。", None, r"(I) 前者 < 后者；(II) $\lim_{n\to\infty} u_n = 0$", 10),
    (18, "解答题", r"求幂级数 $\sum_{n=1}^\infty \frac{(-1)^{n-1}}{2n-1} x^{2n}$ 的收敛域及和函数。", None, r"收敛域为 $[-1,1]$，和函数 $S(x) = \frac{1}{2}\ln\frac{1+x}{1-x} - x$", 10),
    (19, "解答题", r"设 $P$ 为椭球面 $S: x^2 + y^2 + z^2 - yz = 1$ 上的动点，若 $S$ 在点 $P$ 处的切平面与 $xOy$ 面垂直，求点 $P$ 的轨迹 $C$，并计算曲面积分 $I = \iint_{\Sigma} \frac{(x+\sqrt{3})}{|x-y-z|} dS$，其中 $\Sigma$ 是椭球面 $S$ 位于曲线 $C$ 上方的部分。", None, r"轨迹 $C: 2y - z = 0$，$I = \frac{2\pi}{3}$", 10),
    (20, "解答题", r"设 $A = \begin{pmatrix} \lambda & 1 & 1 \\ 0 & \lambda-1 & 0 \\ 1 & 1 & \lambda \end{pmatrix}$，$b = \begin{pmatrix} a \\ 1 \\ 1 \end{pmatrix}$。已知线性方程组 $Ax = b$ 存在2个不同的解。(I) 求 $\lambda, a$；(II) 求 $Ax = b$ 的通解。", None, r"(I) $\lambda = 1$，$a = -1$；(II) 通解 $x = \begin{pmatrix} -2 \\ 1 \\ 0 \end{pmatrix} + k\begin{pmatrix} -1 \\ 0 \\ 1 \end{pmatrix}$", 11),
]

print(f"Importing {len(questions)} questions...")
ok = skip = 0
for num, qt, qtext, opts, ans, score in questions:
    q = {"year": 2010, "category": "数学一", "question_type": qt, "question": qtext,
         "standard_answer": ans, "knowledge_points": [], "difficulty": "中等",
         "score": score, "source": "manual_import_2010"}
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
