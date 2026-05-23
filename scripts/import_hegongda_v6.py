"""Import 26合工大超越卷（数学一）第六套 into the question bank."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MT, V = "26合工大超越", "卷六"

def fix_cases(s):
    """Ensure \\begin{cases} is inside $$...$$ not $...$"""
    if not isinstance(s, str) or r'\begin{cases}' not in s:
        return s
    i = 0
    while True:
        cs = s.find(r'\begin{cases}', i)
        if cs < 0: break
        # Fix opening $
        j = cs - 1
        while j >= 0 and s[j] != '$': j -= 1
        if j >= 0 and not (j > 0 and s[j-1] == '$'):
            s = s[:j] + '$' + s[j:]
            cs += 1
        # Fix closing $
        ce = s.find(r'\end{cases}', cs) + len(r'\end{cases}')
        k = ce
        while k < len(s) and s[k] != '$': k += 1
        if k < len(s) and not (k+1 < len(s) and s[k+1] == '$'):
            s = s[:k] + '$' + s[k:]
        i = cs + 1
    return s

MC = [
    {"no":1,"d":"中等","kp":["导数概念"],"q":r"$1.$ 设函数 $f(x)$ 在点 $x_0$ 处可导，则下列命题正确的个数为① $|f'(x)|$ 在 $x_0$ 处一定可导；② $f(|x|)$ 在 $x_0$ 处一定可导；③ $f(x)-x_0$ 在 $x_0$ 处一定可导；④ $\cos|f(x)|$ 在 $x_0$ 处一定可导。$(A)$ 0 $(B)$ 1 $(C)$ 2 $(D)$ 3","o":{"A":"0","B":"1","C":"2","D":"3"},"c":"B"},
    {"no":2,"d":"中等","kp":["间断点"],"q":r"$2.$ 下列函数中，点 $x=0$ 是可去间断点的数是① $f(x)=\frac{\ln|x|}{\cot x}$；② $f(x)=\frac{d(\int_{-1}^x g(t)dt)}{dx},g(t)=\begin{cases} 1, & t\neq 0 \\ 0, & t=0 \end{cases}$；③ $f(x)=\lim_{n\to\infty}[\frac{1}{n}\ln(1+ne^{nx})+\frac{\sin x+e^{nx}}{1+e^{2nx}}]$。$(A)$ ①② $(B)$ ②③ $(C)$ ①③ $(D)$ ①②③","o":{"A":"①②","B":"②③","C":"①③","D":"①②③"},"c":"C"},
    {"no":3,"d":"中等","kp":["多元函数极值"],"q":r"$3.$ 设 $f(x,y)$ 具有二阶连续偏导数，且 $\lim_{(x,y)\to(0,0)}\frac{f(x,y)-x+y}{\sqrt{x^2+y^2}}=0$，则 $(A)$ $(0,0)$ 是 $z=f(xy,x^2+y^2)$ 的极小值点 $(B)$ $(0,0)$ 是极大值点 $(C)$ $(0,0)$ 不是极值点 $(D)$ 无法判断","o":{"A":"极小值点","B":"极大值点","C":"不是极值点","D":"无法判断"},"c":"C"},
    {"no":4,"d":"中等","kp":["级数敛散性"],"q":r"$4.$ 关于级数的敛散性，下列说法正确的是 $(A)$ $\sum |u_nv_n|$ 收敛 $\Leftrightarrow$ $\sum u_n^2,\sum v_n^2$ 均收敛 $(B)$ $\sum (u_n+v_n)^2$ 收敛 $\Leftrightarrow$ $\sum u_n^2,\sum v_n^2$ 均收敛 $(C)$ $\sum (|u_n|+|v_n|)$ 发散 $\Leftrightarrow$ $\sum |u_n|$ 发散或 $\sum |v_n|$ 发散 $(D)$ $\sum u_nv_n$ 发散 $\Leftrightarrow$ $\sum u_n,\sum v_n$ 均发散","o":{"A":"A","B":"B","C":"C","D":"D"},"c":"B"},
    {"no":5,"d":"中等","kp":["正交矩阵"],"q":r"$5.$ 已知 $A,B$ 均为 $n$ 阶正交矩阵，且 $|A|+|B|=0$，则 $(A)$ $n$ 为偶数时 $(A-B)x=0$ 仅有零解 $(B)$ $n$ 为偶数时有非零解 $(C)$ $n$ 为奇数时仅有零解 $(D)$ $n$ 为奇数时有非零解","o":{"A":"n偶数仅有零解","B":"n偶数有非零解","C":"n奇数仅有零解","D":"n奇数有非零解"},"c":"D"},
    {"no":6,"d":"中等","kp":["二次型","特征值"],"q":r"$6.$ 设二次型 $f=x^{\mathrm{T}}Ax$，$A^{\mathrm{T}}=A$，$A$ 有3个互异特征值 $\lambda_1,\lambda_2,\lambda_3$，对应特征向量 $\xi_1,\xi_2,\xi_3$，若 $\|x\|=1,x^{\mathrm{T}}\xi_3=0$，则 $f$ 的最小值为 $(A)$ $\min\{\lambda_1,\lambda_2\}$ $(B)$ $\min\{\lambda_1,\lambda_3\}$ $(C)$ $\min\{\lambda_2,\lambda_3\}$ $(D)$ $\min\{\lambda_1,\lambda_2,\lambda_3\}$","o":{"A":r"$\min\{\lambda_1,\lambda_2\}$","B":r"$\min\{\lambda_1,\lambda_3\}$","C":r"$\min\{\lambda_2,\lambda_3\}$","D":r"$\min\{\lambda_1,\lambda_2,\lambda_3\}$"},"c":"A"},
    {"no":7,"d":"中等","kp":["向量空间","基"],"q":r"$7.$ 设 $\alpha_1=(1,1,0)^{\mathrm{T}},\alpha_2=(1,0,1)^{\mathrm{T}},\alpha_3=(0,1,1)^{\mathrm{T}}$ 与 $\beta_1=(1,-2,1)^{\mathrm{T}},\beta_2=(-1,-2,1)^{\mathrm{T}},\beta_3=(1,-1,2)^{\mathrm{T}}$ 是 $\mathbf{R}^3$ 的两组基，$\gamma$ 在两组基下有相同坐标，则 $\gamma$ 为 $(A)$ $(3,0,-1)^{\mathrm{T}}$ $(B)$ $(1,0,-3)^{\mathrm{T}}$ $(C)$ $(1,-3,0)^{\mathrm{T}}$ $(D)$ $(3,-1,0)^{\mathrm{T}}$","o":{"A":r"$(3,0,-1)^T$","B":r"$(1,0,-3)^T$","C":r"$(1,-3,0)^T$","D":r"$(3,-1,0)^T$"},"c":"C"},
    {"no":8,"d":"中等","kp":["概率","独立性"],"q":r"$8.$ 以下4个结论：① 设 $0<P(A)<1,P(B|A)+P(B|\bar{A})=1$，则 $\bar{A}$ 与 $B$ 独立；② 设 $A,B$ 独立，$P(C)=0$，则 $\bar{A},\bar{B},C$ 必独立；③ 若 $A,B$ 互不相容，$P(C)>0$，则 $P(\bar{A}\bar{B}|C)=1$；④ 若 $A,B,C$ 独立，则 $A$ 和 $B-C$ 独立。正确的个数为 $(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4","o":{"A":"1","B":"2","C":"3","D":"4"},"c":"B"},
    {"no":9,"d":"中等","kp":["中心极限定理"],"q":r"$9.$ 盒中装有 $2^n$ 张卡片，其中 $C_n$ 张标以号码 $i(i=0,1,\dots,n)$，现有放回抽取100张，$\Phi(x)$ 为标准正态分布函数，$n=16$ 时，号码数之和 $X>850$ 的近似值为 $(A)$ $\Phi(\frac{5}{2})$ $(B)$ $1-\Phi(\frac{5}{2})$ $(C)$ $\Phi(\frac{1}{8})$ $(D)$ $1-\Phi(\frac{1}{8})$","o":{"A":r"$\Phi(\frac{5}{2})$","B":r"$1-\Phi(\frac{5}{2})$","C":r"$\Phi(\frac{1}{8})$","D":r"$1-\Phi(\frac{1}{8})$"},"c":"B"},
    {"no":10,"d":"较难","kp":["参数估计"],"q":r"$10.$ 设 $(X_1,Y_1),\dots,(X_n,Y_n)$ 来自 $N(\theta,\sigma_1^2,\sigma_2^2;0)$，$\sigma_1^2,\sigma_2^2>0$ 已知，$\theta$ 未知，$\hat{\theta}=a\bar{X}+b\bar{Y}$，$E\hat{\theta}=\theta$ 时 $D\hat{\theta}$ 的最小值为 $(A)$ $\frac{\sigma_1^2}{n(\sigma_1^2+\sigma_2^2)}$ $(B)$ $\frac{\sigma_2^2}{n(\sigma_1^2+\sigma_2^2)}$ $(C)$ $\frac{\sigma_1^2\sigma_2^2}{n(\sigma_1^2+\sigma_2^2)}$ $(D)$ $\frac{\sigma_1^2\sigma_2^2}{\sigma_1^2+\sigma_2^2}$","o":{"A":r"$\frac{\sigma_1^2}{n(\sigma_1^2+\sigma_2^2)}$","B":r"$\frac{\sigma_2^2}{n(\sigma_1^2+\sigma_2^2)}$","C":r"$\frac{\sigma_1^2\sigma_2^2}{n(\sigma_1^2+\sigma_2^2)}$","D":r"$\frac{\sigma_1^2\sigma_2^2}{\sigma_1^2+\sigma_2^2}$"},"c":"C"},
]

FB = [
    {"no":11,"d":"中等","kp":["定积分"],"q":r"$11.$ 设 $f(x)$ 在 $[1,+\infty)$ 内连续，且 $2xf(x^2)=f(x)+\frac{1}{x}$，则 $\int_1^4 f(x)dx = \underline{\qquad\qquad}$","a":r"$\ln 2$"},
    {"no":12,"d":"中等","kp":["全微分"],"q":r"$12.$ 设 $f(x,y)$ 在 $(0,0)$ 处可微，$df|_{(0,0)}=-dx+dy$，若 $g(x,y)=f(x^2+y,x+y^2)-f(x,y)$，则 $dg|_{(0,0)}=\underline{\qquad\qquad}$","a":r"$dx-dy$"},
    {"no":13,"d":"中等","kp":["二重积分"],"q":r"$13.$ $I=\int_{-1}^0 dx\int_{-1}^x [\cos(y^2)+x^2\sin(x+y)]dy + \int_0^1 dx\int_x^1 [\cos(y^2)+x^2\sin(x+y)]dy = \underline{\qquad\qquad}$","a":r"$0$"},
    {"no":14,"d":"中等","kp":["微分方程"],"q":r"$14.$ 设 $f(x)$ 为偶函数，且 $f'(x)=\int_0^x f(t-x)dt = 2\sin x$，则 $f(x)=\underline{\qquad\qquad}$","a":r"$\cos x + C$"},
    {"no":15,"d":"中等","kp":["矩阵方程"],"q":r"$15.$ 设 $A=\begin{pmatrix} 2 & 1 & -2 \\ 0 & 0 & 2 \\ 0 & 0 & 2 \end{pmatrix}$，$A^{-1}$ 为 $A$ 的逆矩阵，满足 $AB=A^{-1}(B+E)+E$ 的方阵 $B=\underline{\qquad\qquad}$","a":r"$B = \begin{pmatrix} 1 & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & 0 \end{pmatrix}$"},
    {"no":16,"d":"中等","kp":["数字特征"],"q":r"$16.$ 设 $X$ 概率密度 $f(x)=\begin{cases} 2x, & 0<x<1 \\ 0, & \text{其他} \end{cases}$。对 $X$ 独立重复观测直到第3个小于 $\frac{1}{2}$ 的观测值出现时停止，$Y$ 为观测次数，则 $EY=\underline{\qquad\qquad}$","a":r"$15$"},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["积分方程"],"q":r"$17.$ (本题满分10分) 设连续函数 $f(x)$ 满足 $f(x)=\sin x+\frac{1}{2}\int_x^\pi f(y)f(y-x)dy$，求 $I=\int_0^\pi f(x)dx$。","a":r"$I=2$"},
    {"no":18,"d":"较难","s":12,"kp":["数列极限","级数"],"q":r"$18.$ (本题满分12分) 设 $\{a_n\}$ 满足 $a_1>0$，$a_n=\arctan(a_n+\tan a_{n+1})(n=1,2,\dots)$，证明：(I) $\lim a_n$ 存在；(II) $\sum a_n$ 收敛；(III) $\sum \frac{a_{n+1}}{a_n^2}$ 收敛。","a":r"证明略"},
    {"no":19,"d":"较难","s":12,"kp":["曲面积分"],"q":r"$19.$ (本题满分12分) 设 $\Sigma$ 是球心在原点半径为 $t$ 的球面取外侧，$f(u)$ 可导且 $f(0)=1$，$I(t)=\iint_{\Sigma} xf(y)dy dz + yf(z)dz dx + zf(x)dx dy$，求 $\lim_{t\to 0^+} \frac{I(t)}{\pi t^3}$。","a":r"$4$"},
    {"no":20,"d":"较难","s":12,"kp":["中值定理"],"q":r"$20.$ (本题满分12分) 设 $f(x)$ 在 $[0,+\infty)$ 上非负可导，$f(0)=2,f(1)=0$，$\lim_{x\to+\infty} f'(x)=1$。(I) 证明存在 $c\in(0,+\infty)$ 有 $f(c)=2$；(II) 证明存在 $\xi\in(0,+\infty)$ 有 $f'(\xi)+f^2(\xi)=4$。","a":r"证明略"},
    {"no":21,"d":"较难","s":12,"kp":["矩阵相似"],"q":r"$21.$ (本题满分12分) 设 $A$ 与 $B=\begin{pmatrix} 1 & -2 & 0 \\ 0 & 5 & a \\ 0 & 2 & b \end{pmatrix}$ 相似，$\alpha_1=(2,1,0)^{\mathrm{T}},\alpha_2=(-3,0,1)^{\mathrm{T}}$ 是 $(A-E)x=0$ 的两个线性无关解，$\alpha_3=(-1,-1,1)^{\mathrm{T}}$ 是 $Ax=(-5,-5,5)^{\mathrm{T}}$ 的一个解。(I) 求 $A$；(II) 求 $a,b$；(III) 求可逆 $P$ 使 $P^{-1}BP=A$。","a":r"(I) $A=\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 5 \end{pmatrix}$\n(II) $a=0,b=1$\n(III) $P=\begin{pmatrix} 1 & 2 & -1 \\ 0 & 1 & -1 \\ 0 & 0 & 1 \end{pmatrix}$"},
    {"no":22,"d":"较难","s":12,"kp":["随机变量函数分布"],"q":r"$22.$ (本题满分12分) 设 $X$ 概率密度 $f_X(x)=\begin{cases} \frac{1}{\sqrt{2\pi}}e^{-\frac{x^2}{2}}, & x\le 0 \\ e^{-2x}, & x>0 \end{cases}$。$Z=g(X)=\begin{cases} X, & X<0 \\ X^2, & 0\le X\le 1 \\ X, & X>1 \end{cases}$。(I) 求 $Z$ 的概率密度；(II) 求 $EZ$。","a":r"(I) $f_Z(z)=\begin{cases} \frac{1}{\sqrt{2\pi}}e^{-\frac{z^2}{2}}, & z<0 \\ \frac{1}{2\sqrt{z}}\frac{1}{\sqrt{2\pi}}e^{-\frac{z}{2}}+\frac{1}{2\sqrt{z}}e^{-2\sqrt{z}}, & 0<z<1 \\ e^{-2z}, & z>1 \end{cases}$\n(II) $EZ=\frac{1}{\sqrt{2\pi}}+\frac{1}{4}+\frac{1}{2e^2}$"},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v6","solution_steps":[],"volume":V})
    for q in FB:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v6","solution_steps":[],"options":{},"volume":V})
    for q in FR:
        all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v6","solution_steps":[],"options":{},"volume":V})
    for q in all_q:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all_q)})")

if __name__ == "__main__": main()
