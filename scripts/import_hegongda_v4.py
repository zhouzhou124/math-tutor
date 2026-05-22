"""Import 26合工大超越卷（数学一）第四套 into the question bank."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MATH_TYPE = "26合工大超越"
VOLUME = "卷四"

MC = [
    {"no":1,"difficulty":"中等","knowledge_points":["反常积分"],
     "question":r"$1.$ 已知 $I_1 = \int_{0}^{\frac{\pi}{2}} \frac{\tan x}{\sqrt{x - 2x}} dx$，$I_2 = \int_{0}^{+\infty} \frac{\ln x}{\sqrt{x^3 + x}} dx$，则 "
                r"$(A)$ $I_1$ 收敛，$I_2$ 收敛 $(B)$ $I_1$ 收敛，$I_2$ 发散 $(C)$ $I_1$ 发散，$I_2$ 收敛 $(D)$ $I_1$ 发散，$I_2$ 发散",
     "options":{"A":r"$I_1$ 收敛，$I_2$ 收敛","B":r"$I_1$ 收敛，$I_2$ 发散","C":r"$I_1$ 发散，$I_2$ 收敛","D":r"$I_1$ 发散，$I_2$ 发散"},"correct_option":"C"},
    {"no":2,"difficulty":"中等","knowledge_points":["间断点"],
     "question":r"$2.$ 函数 $f(x) = \frac{x^2 - x}{\sin x |x^2 - 1|}$ 在 $(-\frac{\pi}{2}, \frac{\pi}{2})$ 内的第一类间断点个数为 "
                r"$(A)$ 0 $(B)$ 1 $(C)$ 2 $(D)$ 3",
     "options":{"A":"0","B":"1","C":"2","D":"3"},"correct_option":"B"},
    {"no":3,"difficulty":"中等","knowledge_points":["隐函数求导"],
     "question":r"$3.$ 设 $z = z(x,y)$ 由方程 $xy + \ln z + yz^2 = 0$ 所确定，则 $\left.\frac{\partial^2 z}{\partial x \partial y}\right|_{(1,0)} =$ "
                r"$(A)$ $-1$ $(B)$ $0$ $(C)$ $1$ $(D)$ $2$",
     "options":{"A":r"$-1$","B":r"$0$","C":r"$1$","D":r"$2$"},"correct_option":"A"},
    {"no":4,"difficulty":"中等","knowledge_points":["曲面积分"],
     "question":r"$4.$ 设 $\Sigma$ 为球面 $z = \sqrt{1 - x^2 - y^2}$ 被柱面 $x^2 + y^2 = x$ 所截下的部分，取下侧，则将对坐标曲面积分 $\iint_{\Sigma} \frac{xy dy dz + yz dx dy}{x^2 + y^2 + z^2}$ 化为对面积的曲面积分为 "
                r"$(A)$ $\iint_{\Sigma} (x^2 y + yz^2) dS$ $(B)$ $-\iint_{\Sigma} (x^2 y + yz^2) dS$ $(C)$ $\iint_{\Sigma} (x^2 y + yz^2) dA$ $(D)$ $-\iint_{\Sigma} (x^2 y + yz^2) dA$",
     "options":{"A":r"$\iint_{\Sigma} (x^2 y + yz^2) dS$","B":r"$-\iint_{\Sigma} (x^2 y + yz^2) dS$","C":r"$\iint_{\Sigma} (x^2 y + yz^2) dA$","D":r"$-\iint_{\Sigma} (x^2 y + yz^2) dA$"},"correct_option":"B"},
    {"no":5,"difficulty":"中等","knowledge_points":["矩阵", "特征值"],
     "question":r"$5.$ $P = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & 1 \\ 0 & 1 & 0 \end{pmatrix}$，$P^{\mathrm{T}} A P^{2026} = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2 \end{pmatrix}$，$n$ 为正整数，则 $A^{2n} =$ "
                r"$(A)$ $\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 2^n \end{pmatrix}$ $(B)$ $\begin{pmatrix} 1 & 0 & 0 \\ 0 & 2^n & 0 \\ 0 & 0 & 2^n \end{pmatrix}$ $(C)$ $\begin{pmatrix} 1 & 0 & 0 \\ 0 & 2^n & 0 \\ 0 & 0 & 1 \end{pmatrix}$ $(D)$ $\begin{pmatrix} 2^n & 0 & 0 \\ 0 & 2^n & 0 \\ 0 & 0 & 1 \end{pmatrix}$",
     "options":{"A":r"$\begin{pmatrix}1&0&0\\0&1&0\\0&0&2^n\end{pmatrix}$","B":r"$\begin{pmatrix}1&0&0\\0&2^n&0\\0&0&2^n\end{pmatrix}$","C":r"$\begin{pmatrix}1&0&0\\0&2^n&0\\0&0&1\end{pmatrix}$","D":r"$\begin{pmatrix}2^n&0&0\\0&2^n&0\\0&0&1\end{pmatrix}$"},"correct_option":"A"},
    {"no":6,"difficulty":"中等","knowledge_points":["矩阵", "向量组"],
     "question":r"$6.$ 设 $A,B$ 分别为 $m\times n$，$n\times s$ 矩阵，且 $r(B)=n$，则 "
                r"$(A)$ $AB$ 的行向量组与 $A$ 的行向量组等价 $(B)$ $AB$ 的列向量组与 $A$ 的列向量组等价 $(C)$ $AB$ 的行向量组与 $B$ 的行向量组等价 $(D)$ $AB$ 的列向量组与 $B$ 的列向量组等价",
     "options":{"A":r"$AB$ 的行向量组与 $A$ 的行向量组等价","B":r"$AB$ 的列向量组与 $A$ 的列向量组等价","C":r"$AB$ 的行向量组与 $B$ 的行向量组等价","D":r"$AB$ 的列向量组与 $B$ 的列向量组等价"},"correct_option":"B"},
    {"no":7,"difficulty":"中等","knowledge_points":["特征值", "对角化"],
     "question":r'$7.$ 设 $A$ 为3阶矩阵，$\lambda_1=\lambda_2=a$，$\lambda_3=b$（$a\neq b$）是关于 $A$ 的特征值，则"$A$ 可对角化"是"$(A-aE)(A-bE)=0$"的 '
                r'$(A)$ 充分必要条件 $(B)$ 充分非必要条件 $(C)$ 必要非充分条件 $(D)$ 非充分非必要条件',
     "options":{"A":"充分必要条件","B":"充分非必要条件","C":"必要非充分条件","D":"非充分非必要条件"},"correct_option":"A"},
    {"no":8,"difficulty":"中等","knowledge_points":["随机变量", "分布函数"],
     "question":r"$8.$ 设 $X \sim f(x) = \begin{cases} \frac{3}{2}x^2, & -1<x<1 \\ 0, & \text{其他} \end{cases}$，$Y = \begin{cases} -1, & X<0 \\ 0, & 0\le X<\frac{1}{2} \\ 1, & X\ge\frac{1}{2} \end{cases}$，$F(x,y)$ 为 $(X,Y)$ 的分布函数，则 $F(\frac{1}{4},\frac{1}{2})=$ "
                r"$(A)$ $\frac{65}{128}$ $(B)$ $\frac{64}{128}$ $(C)$ $\frac{1}{64}$ $(D)$ $\frac{5}{64}$",
     "options":{"A":r"$\frac{65}{128}$","B":r"$\frac{64}{128}$","C":r"$\frac{1}{64}$","D":r"$\frac{5}{64}$"},"correct_option":"A"},
    {"no":9,"difficulty":"中等","knowledge_points":["指数分布", "数字特征"],
     "question":r"$9.$ 设 $X$ 与 $Y$ 相互独立，$X\sim E(\lambda_1)$，$Y\sim E(\lambda_2)$（$\lambda_1>0,\lambda_2>0$），$Z=\min\{X,Y\}$ 且 $P(Z\le 1)=1-e^{-2}$，则 $EZ^2=$ "
                r"$(A)$ $\frac{1}{4}$ $(B)$ $\frac{3}{4}$ $(C)$ $\frac{1}{2}$ $(D)$ $\frac{3}{2}$",
     "options":{"A":r"$\frac{1}{4}$","B":r"$\frac{3}{4}$","C":r"$\frac{1}{2}$","D":r"$\frac{3}{2}$"},"correct_option":"C"},
    {"no":10,"difficulty":"较难","knowledge_points":["抽样分布"],
     "question":r"$10.$ 设 $X_1,X_2,X_3,X_4,X_5$ 为来自总体 $X\sim N(0,\sigma^2)$ 的简单随机样本，$\overline{X}=\frac{1}{5}\sum_{i=1}^5 X_i$，$S^2=\frac{1}{4}\sum_{i=1}^5 (X_i-\overline{X})^2$，则下列结论中正确的个数有 "
                r"① $\sqrt{\frac{3}{2}} \frac{X_1+X_2}{|X_3+X_4+X_5|} \sim t(1)$；② $\frac{5}{6} \frac{\overline{X}^2}{\sigma^2} \sim \chi^2(5)$；③ $\frac{1}{\sigma^2}[(X_1-2X_2)^2+(2X_3+X_4)^2] \sim \chi^2(2)$；④ $\frac{(X_1-2X_2)^2}{(2X_3+X_4)^2} \sim F(1,1)$。"
                r"$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4",
     "options":{"A":"1","B":"2","C":"3","D":"4"},"correct_option":"A"},
]

FB = [
    {"no":11,"difficulty":"中等","knowledge_points":["曲率"],
     "question":r"$11.$ 曲线 $xy=1$ 在点 $(1,1)$ 处的曲率圆方程为 $\underline{\qquad\qquad}$",
     "standard_answer":r"$(x-2)^2+(y-2)^2=2$"},
    {"no":12,"difficulty":"中等","knowledge_points":["傅里叶级数"],
     "question":r"$12.$ 设 $f(x)$ 是周期为4的偶函数，且 $f(x)=\begin{cases} x, & 0\le x<1 \\ 2-x, & 1\le x<2 \end{cases}$，$a_n,b_n$ 为 $f(x)$ 的傅里叶级数的系数，则 $(a_2,b_2)=$ $\underline{\qquad\qquad}$",
     "standard_answer":r"$(0,0)$"},
    {"no":13,"difficulty":"中等","knowledge_points":["偏导数"],
     "question":r"$13.$ 设 $f(x,y)$ 具有二阶连续偏导数，且 $\frac{\partial^2 f}{\partial x^2}+\frac{\partial^2 f}{\partial y^2}=2$，令 $u=ax+by$，$v=ax-by$，若 $\frac{\partial^2 f}{\partial u^2}+\frac{\partial^2 f}{\partial v^2}=4$，$\frac{\partial^2 f}{\partial u\partial v}=0$，则 $a^2+b^2=$ $\underline{\qquad\qquad}$",
     "standard_answer":r"$1$"},
    {"no":14,"difficulty":"中等","knowledge_points":["微分方程"],
     "question":r"$14.$ 方程 $x\frac{dy}{dx}+y=\frac{1}{1+(xy)^2}$ 的通解为 $\underline{\qquad\qquad}$",
     "standard_answer":r"$xy = \arctan(xy) + C$"},
    {"no":15,"difficulty":"较难","knowledge_points":["线性方程组"],
     "question":r"$15.$ 设 $A$ 为3阶矩阵，非齐次线性方程组 $Ax=(2,1,0)^{\mathrm{T}}$ 的通解为 $k_1\xi_1+k_2\xi_2+\eta^*$，其中 $\xi_1=(2,1,0)^{\mathrm{T}},\xi_2=(1,0,1)^{\mathrm{T}},\eta^*=(-1,2,1)^{\mathrm{T}}$，记矩阵 $B=(\xi_1,\xi_2,\eta^*)$，$\beta=(1,2,3)^{\mathrm{T}}$，则 (Ⅰ) $Bx=\beta$ 的解为 $\underline{\qquad\qquad}$，(Ⅱ) $\beta^{\mathrm{T}}A\beta=$ $\underline{\qquad\qquad}$",
     "standard_answer":r"(Ⅰ) $x = \begin{pmatrix} 1 \\ 1 \\ 1 \end{pmatrix} + k\begin{pmatrix} -1 \\ 0 \\ 1 \end{pmatrix}$；(Ⅱ) $0$"},
    {"no":16,"difficulty":"中等","knowledge_points":["条件概率"],
     "question":r"$16.$ 设二维随机变量 $(X,Y)$ 的概率密度为 $f(x,y)=\begin{cases} k(1-xy), & |x|\le 1, 0\le y\le 1 \\ 0, & \text{其他} \end{cases}$，则 $P\{Y<\frac{1}{2} \mid X=\frac{1}{4}\}=$ $\underline{\qquad\qquad}$",
     "standard_answer":r"$\frac{3}{4}$"},
]

FR = [
    {"no":17,"difficulty":"中等","score":12,"knowledge_points":["二重积分"],
     "question":r"$17.$ (本题满分12分) 设 $D=\{(x,y)\mid 0\le x\le 1,0\le y\le 1\}$，$f(x,y)=\begin{cases} \frac{(y+1)e^x}{(1+x)^2}, & y<x \\ x^2+y^2, & y\ge x \end{cases}$，计算 $\iint_D f(x,y) dxdy$。",
     "standard_answer":r"$e - 1 + \frac{2}{3}$"},
    {"no":18,"difficulty":"较难","score":12,"knowledge_points":["定积分", "级数"],
     "question":r"$18.$ (本题满分12分) 设 $a_n=\int_0^{\frac{\pi}{2}} \frac{1}{(1+\sin x)^n} dx$（$n\ge 1$）。\n$(I)$ 求 $\lim_{n\to\infty} a_n$；\n$(II)$ 证明 $\lim_{n\to\infty} [a_1-a_2+a_3-\cdots+(-1)^{n-1}a_n]$ 存在。",
     "standard_answer":r"(I) $\lim_{n\to\infty} a_n = 0$\n(II) 证明略"},
    {"no":19,"difficulty":"较难","score":12,"knowledge_points":["曲线积分"],
     "question":r"$19.$ (本题满分12分) 设 $\Gamma$ 为曲线 $\begin{cases} z=\sqrt{1-x^2-y^2} \\ x^2+y^2=z \end{cases}$，从 $z$ 轴正向任意向看为逆时针方向，计算 $\oint_{\Gamma} (2y-z)dx + (x-2)dy + (x-2y)dz$。",
     "standard_answer":r"$-\pi$"},
    {"no":20,"difficulty":"较难","score":12,"knowledge_points":["中值定理", "积分不等式"],
     "question":r"$20.$ (本题满分12分) 设 $f(x)$ 是 $[0,1]$ 上恒正连续函数，且在 $(0,1)$ 内二阶可导，$f(0)=0$。\n$(I)$ 证明存在 $\xi\in(0,1)$，有 $\int_0^1 f^3(x)dx = f'(\xi)(\int_0^1 f(x)dx)^2$；\n$(II)$ 证明存在 $\eta\in(0,1)$，有 $\eta f''(\eta)+2f'(\eta)=6\int_0^1 xf(x)dx$。",
     "standard_answer":r"证明略"},
    {"no":21,"difficulty":"较难","score":12,"knowledge_points":["向量组", "线性方程组"],
     "question":r"$21.$ (本题满分12分) 设实数 $a\neq 0$，向量组 $\alpha_1=(a,0,1)^{\mathrm{T}},\alpha_2=(0,-a,0)^{\mathrm{T}},\alpha_3=(1,0,a)^{\mathrm{T}}$。已知 $\beta=(1,1,-1)^{\mathrm{T}}$ 不能由 $\alpha_1,\alpha_2,\alpha_3$ 线性表示，$\gamma$ 满足 $\gamma=k_1\alpha_1+k_2\alpha_2+k_3\alpha_3$ 且 $\beta^{\mathrm{T}}\alpha_i=\gamma^{\mathrm{T}}\alpha_i(i=1,2,3)$。\n$(I)$ 求 $a$ 的值；$(II)$ 证明 $\beta-\gamma$ 为 $A^{\mathrm{T}}x=0$ 的解；$(III)$ 求 $\gamma$。",
     "standard_answer":r"(I) $a = -1$\n(II) 证明略\n(III) $\gamma = (1,-1,1)^{\mathrm{T}}$"},
    {"no":22,"difficulty":"较难","score":12,"knowledge_points":["多维随机变量", "变量变换"],
     "question":r"$22.$ (本题满分12分) 设二维随机变量 $(X,Y)$ 概率密度函数为 $f(x,y)=\begin{cases} \frac{2}{\pi}e^{-\sqrt{x^2+y^2}}, & x>0,y>0 \\ 0, & \text{其他} \end{cases}$。令 $\begin{cases} U=\sqrt{X^2+Y^2} \\ V=\arctan\frac{Y}{X} \end{cases}$。\n$(I)$ 求 $P(U\le 1, V\le \frac{\pi}{4})$；$(II)$ 分别求 $(U,V)$ 的分布函数和密度函数；$(III)$ 求 $U$ 和 $V$ 的边缘密度，判断是否独立。",
     "standard_answer":r"(I) $\frac{1}{2}(1-e^{-1})$\n(II) $F_{U,V}(u,v) = \frac{2v}{\pi}(1-e^{-u})$，$f_{U,V}(u,v) = \frac{2}{\pi}ue^{-u}(u>0,0<v<\frac{\pi}{2})$\n(III) $f_U(u)=2ue^{-u}$，$f_V(v)=\frac{2}{\pi}$，独立"},
]


def main():
    db = QuestionDB()
    ok = fail = 0
    all = []
    for q in MC:
        all.append({"question_id":make_question_id(2026,MATH_TYPE,q["no"],VOLUME),"year":2026,"category":MATH_TYPE,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["difficulty"],"knowledge_points":q["knowledge_points"],"tags":q["knowledge_points"],"question":q["question"],"options":q["options"],"correct_option":q["correct_option"],"standard_answer":q["correct_option"],"source":"import_hegongda_v4","solution_steps":[],"volume":VOLUME})
    for q in FB:
        all.append({"question_id":make_question_id(2026,MATH_TYPE,q["no"],VOLUME),"year":2026,"category":MATH_TYPE,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["difficulty"],"knowledge_points":q["knowledge_points"],"tags":q["knowledge_points"],"question":q["question"],"standard_answer":q["standard_answer"],"source":"import_hegongda_v4","solution_steps":[],"options":{},"volume":VOLUME})
    for q in FR:
        all.append({"question_id":make_question_id(2026,MATH_TYPE,q["no"],VOLUME),"year":2026,"category":MATH_TYPE,"question_type":"解答题","question_no":q["no"],"score":q["score"],"difficulty":q["difficulty"],"knowledge_points":q["knowledge_points"],"tags":q["knowledge_points"],"question":q["question"],"standard_answer":q["standard_answer"],"source":"import_hegongda_v4","solution_steps":[],"options":{},"volume":VOLUME})
    for q in all:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all)})")

if __name__ == "__main__": main()
