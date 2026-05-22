"""Import 26合工大超越卷（数学一）第五套 into the question bank."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MT, V = "26合工大超越", "卷五"

MC = [
    {"no":1,"d":"中等","kp":["极限","可导性"],"q":'$1.$ 设 $f(a)=0$，则"极限 $\lim_{h\to 0} \frac{f(a+\sin h)}{1-\cos h}$ 存在"是"函数 $f(x)$ 在 $x=a$ 处可导"的 $(A)$ 充分非必要条件 $(B)$ 必要非充分条件 $(C)$ 充要条件 $(D)$ 既非充分也非必要条件',"o":{"A":"充分非必要条件","B":"必要非充分条件","C":"充要条件","D":"既非充分也非必要条件"},"c":"D"},
    {"no":2,"d":"中等","kp":["定积分比较"],"q":r"$2.$ 设 $a>1$，$I_1=\int_0^a \sin^2 x dx$，$I_2=\int_0^1 \sin x^2 dx$，$I_3=\int_0^1 \tan^2 x dx$，$I_4=\int_0^1 \tan^2 x dx$，则 $(A)$ $I_1\ge I_2, I_3\ge I_4$ $(B)$ $I_1\ge I_2, I_3\le I_4$ $(C)$ $I_1\le I_2, I_3\ge I_4$ $(D)$ $I_1\le I_2, I_3\le I_4$","o":{"A":r"$I_1\ge I_2, I_3\ge I_4$","B":r"$I_1\ge I_2, I_3\le I_4$","C":r"$I_1\le I_2, I_3\ge I_4$","D":r"$I_1\le I_2, I_3\le I_4$"},"c":"D"},
    {"no":3,"d":"中等","kp":["多元函数可微性"],"q":r"$3.$ 二元函数 $f(x,y)=\begin{cases} \frac{x|y|+y|x|}{\sqrt{x^2+y^2}}, & (x,y)\neq(0,0) \\ 0, & (x,y)=(0,0) \end{cases}$ 在点 $(0,0)$ 处 $(A)$ 极限存在但不连续 $(B)$ 连续但偏导不存在 $(C)$ 偏导存在但不可微 $(D)$ 可微","o":{"A":"极限存在但不连续","B":"连续但偏导不存在","C":"偏导存在但不可微","D":"可微"},"c":"C"},
    {"no":4,"d":"中等","kp":["曲线积分"],"q":r"$4.$ 设平面曲线 $L$ 为星形线 $x^{\frac{2}{3}}+y^{\frac{2}{3}}=1$，取顺时针方向，则 $I=\oint_L \frac{x dy - y dx}{4x^2+y^2}=$ $(A)$ $0$ $(B)$ $-\pi$ $(C)$ $-2\pi$ $(D)$ $\pi$","o":{"A":"0","B":r"$-\pi$","C":r"$-2\pi$","D":r"$\pi$"},"c":"B"},
    {"no":5,"d":"中等","kp":["二次型","标准形"],"q":r"$5.$ 设 $A$ 为3阶实对称矩阵，若 $|A+E|=|A-2E|=-4$，$|A-E|=0$，二次型 $f(x)=x^{\mathrm{T}}Ax$ 在正交变换下的标准形为 $(A)$ $-y_1^2+2y_2^2+y_3^2$ $(B)$ $5y_1^2+2y_2^2+y_3^2$ $(C)$ $y_1^2+y_2^2-2y_3^2$ $(D)$ $y_1^2+y_2^2+2y_3^2$","o":{"A":r"$-y_1^2+2y_2^2+y_3^2$","B":r"$5y_1^2+2y_2^2+y_3^2$","C":r"$y_1^2+y_2^2-2y_3^2$","D":r"$y_1^2+y_2^2+2y_3^2$"},"c":"D"},
    {"no":6,"d":"中等","kp":["代数余子式"],"q":r"$6.$ 设 $A=\begin{pmatrix} 1 & 2 & -1 & 0 \\ 0 & 2 & 1 & -1 \\ 0 & 0 & 4 & -2 \\ 0 & 0 & 0 & 2 \end{pmatrix}$，$A_{ij}$ 为 $|A|$ 中元素 $a_{ij}$ 的代数余子式，则 $\sum_{i=1}^4\sum_{j=1}^4 A_{ij}=$ $(A)$ $4$ $(B)$ $16$ $(C)$ $32$ $(D)$ $64$","o":{"A":"4","B":"16","C":"32","D":"64"},"c":"C"},
    {"no":7,"d":"中等","kp":["矩阵","伴随矩阵"],"q":r"$7.$ 已知 $A$ 为3阶可逆矩阵，将 $A$ 的第二行的 $-2$ 倍加到第一行得矩阵 $B$，$B^*$ 为 $B$ 的伴随矩阵，则 $\operatorname{tr}(B^*A)=$ $(A)$ $|A|$ $(B)$ $2|A|$ $(C)$ $3|A|$ $(D)$ $4|A|$","o":{"A":r"$|A|$","B":r"$2|A|$","C":r"$3|A|$","D":r"$4|A|$"},"c":"C"},
    {"no":8,"d":"中等","kp":["随机变量","数字特征"],"q":r"$8.$ 设随机变量 $X$ 的密度函数为 $f(x)=a e^{\frac{x(2-x)}{2}}$($-\infty<x<+\infty$)，则 $E(X^2 e^x)=$ $(A)$ $4$ $(B)$ $6$ $(C)$ $8$ $(D)$ $10$","o":{"A":"4","B":"6","C":"8","D":"10"},"c":"B"},
    {"no":9,"d":"较难","kp":["多维随机变量"],"q":r"$9.$ 设二维随机变量 $(X,Y)$ 的概率密度 $f(x,y)=\begin{cases} A x e^{-y}, & 0<x<y<+\infty \\ 0, & \text{其他} \end{cases}$。记 $M=\max(X,Y),N=\min(X,Y)$，则 $P(M<2,N<1)=$ $(A)$ $1-\frac{1}{e}$ $(B)$ $1-\frac{1}{e}-\frac{1}{e^2}$ $(C)$ $1-\frac{2}{e^2}$ $(D)$ $1-\frac{2}{e}-\frac{1}{2e^2}$","o":{"A":r"$1-\frac{1}{e}$","B":r"$1-\frac{1}{e}-\frac{1}{e^2}$","C":r"$1-\frac{2}{e^2}$","D":r"$1-\frac{2}{e}-\frac{1}{2e^2}$"},"c":"C"},
    {"no":10,"d":"较难","kp":["极大似然估计"],"q":r"$10.$ 设 $(X,Y)\sim N(0,2\sigma^2,\sigma^2;\frac{1}{2})$，$\sigma^2$ 未知，$(x_1,y_1),\dots,(x_n,y_n)$ 是简单随机样本。则 $P(X+Y\le 1)$ 的极大似然估计值为 $(A)$ $\Phi(\sqrt{\frac{n}{\sum (x_i+y_i)^2}})$ $(B)$ $1-\Phi(\sqrt{\frac{n}{\sum (x_i+y_i-2)^2}})$ $(C)$ $\Phi(\sqrt{\frac{n}{\sum (x_i+y_i-2)^2}})$ $(D)$ $1-\Phi(\sqrt{\frac{3n}{\sum (x_i+y_i-2)^2}})$","o":{"A":r"$\Phi(\sqrt{\frac{n}{\sum (x_i+y_i)^2}})$","B":r"$1-\Phi(\sqrt{\frac{n}{\sum (x_i+y_i-2)^2}})$","C":r"$\Phi(\sqrt{\frac{n}{\sum (x_i+y_i-2)^2}})$","D":r"$1-\Phi(\sqrt{\frac{3n}{\sum (x_i+y_i-2)^2}})$"},"c":"C"},
]

FB = [
    {"no":11,"d":"中等","kp":["二重积分极限"],"q":r"$11.$ $\lim_{t\to 0^+} \int_0^t dx \int_x^t (e^{x+y}-e^x-e^y+1) dy = \underline{\qquad\qquad}$","a":r"$\frac{1}{2}$"},
    {"no":12,"d":"中等","kp":["偏导数"],"q":r"$12.$ 设 $z(x,y)=\int_0^1 (x^2+y^2-t)|f(t)| dt$，$0\le x\le 1,0\le y\le 1$，$f(t)$ 连续且 $f(\frac{1}{2})=\frac{1}{2}$，则 $z''_x(\frac{1}{2},\frac{1}{2})=\underline{\qquad\qquad}$","a":r"$2$"},
    {"no":13,"d":"中等","kp":["级数求和"],"q":r"$13.$ 设 $a_n=\int_0^1 \frac{dx}{(1+x^2)^n}$，则 $\sum_{n=1}^\infty (\frac{a_{n+1}}{2n-1}-\frac{a_n}{2n})$ 的和为 $\underline{\qquad\qquad}$","a":r"$0$"},
    {"no":14,"d":"中等","kp":["隐函数求导"],"q":r"$14.$ 设 $y=y(x)$ 由 $x^2-\int_1^{x+y} e^{-(t-y)^2} dt = 0$ 确定，则 $y''(0)=\underline{\qquad\qquad}$","a":r"$2$"},
    {"no":15,"d":"中等","kp":["线性方程组"],"q":r"$15.$ 已知方程组 $\begin{cases} kx_1 - x_3 + x_4 = 1 \\ kx_2 + x_3 - x_4 = -1 \\ -x_1 + x_2 + kx_3 = 1 \\ x_1 - x_2 + kx_4 = -1 \end{cases}$ 无解，$k\neq 0$，则 $k=\underline{\qquad\qquad}$","a":r"$-2$"},
    {"no":16,"d":"中等","kp":["条件概率"],"q":r"$16.$ 某人向一目标独立重复射击4次，每次命中概率均为0.8。已知目标被击中，则第三次射击恰好第二次命中的概率是 $\underline{\qquad\qquad}$","a":r"$\frac{6}{25}$"},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["参数方程求导","极限"],"q":r"$17.$ (本题满分10分) 设 $y=f(x)$ 由 $\begin{cases} x = t^2 + 2t - 3 \\ t^2 - y - \sin y = 1 \end{cases}$($t\ge 0$) 确定，求 $\lim_{x\to 0^+} \frac{4f(x)\sin x - x^2}{x^3}$。","a":r"$-\frac{1}{2}$"},
    {"no":18,"d":"较难","s":12,"kp":["定积分证明"],"q":r"$18.$ (本题满分12分) (I) 设 $f(x),g(x)$ 在 $[0,a]$ 上连续，且 $f(x)=f(a-x)$，$g(x)+g(a-x)=k$。证明 $\int_0^a f(x)g(x)dx = \frac{k}{2}\int_0^a f(x)dx$。(II) 计算 $\int_0^{\frac{\pi}{2}} \sin^4 4x \cdot \ln(1+\tan x) dx$。","a":r"(I) 证明略\n(II) $\frac{\pi}{16}\ln 2$"},
    {"no":19,"d":"较难","s":12,"kp":["偏微分方程"],"q":r"$19.$ (本题满分12分) 设 $f(t)$ 二阶可导，$u = f(\sqrt{x^2+y^2+z^2})$ 满足 $u_{xx}''+u_{yy}''+u_{zz}''=0$，若 $f(1)=0,f'(1)=1$，求 $f(t)$。","a":r"$f(t) = \ln t$"},
    {"no":20,"d":"较难","s":12,"kp":["曲面积分"],"q":r"$20.$ (本题满分12分) 设 $\Sigma$ 为 $x^2+y^2+z^2=2$($z\ge 0$)上侧，$f(x,y)$ 满足 $f(x,y) = x^2+y^2 + x\iint_{\Sigma} xy^2 dy dz + x^2 y dz dx - [(x+3y)^2 - z^2 + z f(x,y)] dx dy$，求 $f(x,y)$。","a":r"$f(x,y) = x^2 + y^2 - \frac{2}{3}\pi$"},
    {"no":21,"d":"较难","s":12,"kp":["特征值","二次型"],"q":r"$21.$ (本题满分12分) $A = \begin{pmatrix} 1 & 0 & a \\ 0 & 1-a & -2 \\ -1 & 0 & 2 \end{pmatrix}$ 特征值为实数。(I) 若 $A$ 可对角化，求 $a$ 范围。(II) 当 $a<0$ 且 $A$ 不可对角化时，判断二次型 $f=x^{\mathrm{T}}Ax$ 的正定性。","a":r"(I) $a \neq 1$\n(II) $f$ 为不定二次型"},
    {"no":22,"d":"较难","s":12,"kp":["多维随机变量"],"q":r"$22.$ (本题满分12分) 三个编号1,2,3的盒子，三只球随机放入。$X$ 为所有非空盒子的最小号码。(I) 求 $X$ 分布律；(II) 若 $X=i$ 时 $Y\sim U[0,i]$，$Z=Y/X$，证明 $Z\sim U[0,1]$。","a":r"(I) $P(X=1)=\frac{1}{9},P(X=2)=\frac{2}{9},P(X=3)=\frac{6}{9}$\n(II) 证明略"},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":q["q"],"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v5","solution_steps":[],"volume":V})
    for q in FB:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":q["q"],"standard_answer":q["a"],"source":"import_hegongda_v5","solution_steps":[],"options":{},"volume":V})
    for q in FR:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":q["q"],"standard_answer":q["a"],"source":"import_hegongda_v5","solution_steps":[],"options":{},"volume":V})
    for q in all_q:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all_q)})")

if __name__ == "__main__": main()
