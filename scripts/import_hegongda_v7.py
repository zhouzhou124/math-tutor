"""Import 26合工大超越卷（数学一）第七套."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MT, V = "26合工大超越", "卷七"

def fix_cases(s):
    if not isinstance(s, str) or r'\begin{cases}' not in s: return s
    i = 0
    while True:
        cs = s.find(r'\begin{cases}', i)
        if cs < 0: break
        j = cs - 1
        while j >= 0 and s[j] != '$': j -= 1
        if j >= 0 and not (j > 0 and s[j-1] == '$'): s = s[:j] + '$' + s[j:]; cs += 1
        ce = s.find(r'\end{cases}', cs) + len(r'\end{cases}')
        k = ce
        while k < len(s) and s[k] != '$': k += 1
        if k < len(s) and not (k+1 < len(s) and s[k+1] == '$'): s = s[:k] + '$' + s[k:]
        i = cs + 1
    return s

MC = [
    {"no":1,"d":"中等","kp":["连续与可导"],"q":r"$1.$ 设 $f(x)$ 在 $[-1,1]$ 上有定义，在 $[-1,0)\cup(0,1]$ 内连续，$F(x)=\int_{-1}^x f(t)dt$。则 $(A)$ 若 $x=0$ 是 $f(x)$ 的可去间断点，则 $F(x)$ 在 $x=0$ 连续但不可导 $(B)$ 若可去间断点，则 $F(x)$ 在 $x=0$ 可导且 $F'(0)=f(0)$ $(C)$ 若跳跃间断点，则 $f(x)$ 在 $[-1,1]$ 上不存在原函数 $(D)$ 若 $f(x)$ 无界，则不存在原函数","o":{"A":"A","B":"B","C":"C","D":"D"},"c":"B"},
    {"no":2,"d":"中等","kp":["方程根"],"q":r"$2.$ 方程 $\int_0^x \frac{2\ln(1+t)}{t} dt - \int_{\cos x}^{\frac{\pi}{2}} e^{-a^2} dt = 0$（$a>0$）在 $(0,\frac{\pi}{2})$ 内的个数为 $(A)$ 0 $(B)$ 1 $(C)$ 2 $(D)$ 与 $a$ 有关","o":{"A":"0","B":"1","C":"2","D":"与a有关"},"c":"B"},
    {"no":3,"d":"中等","kp":["多元函数极值"],"q":r"$3.$ 若点 $(-1,0)$ 是 $f(x,y)=(ax+b+y^2)e^{-x}$ 的极小值点，则 $(A)$ $a<0$ $(B)$ $a>0$ $(C)$ $a\le 0$ $(D)$ $a\ge 0$","o":{"A":r"$a<0$","B":r"$a>0$","C":r"$a\le 0$","D":r"$a\ge 0$"},"c":"A"},
    {"no":4,"d":"中等","kp":["傅里叶级数"],"q":r"$4.$ 设 $f(x)=e^x$ 在 $[-1,1]$ 上展开成傅里叶级数 $\frac{a_0}{2}+\sum_{n=1}^\infty (a_n\cos n\pi x+b_n\sin n\pi x)$，则 $(A)$ $\sum a_n,\sum b_n$ 均绝对收敛 $(B)$ 均条件收敛 $(C)$ $\sum a_n$ 绝对收敛，$\sum b_n$ 条件收敛 $(D)$ $\sum a_n$ 条件收敛，$\sum b_n$ 绝对收敛","o":{"A":"均绝对收敛","B":"均条件收敛","C":r"$\sum a_n$绝对，$\sum b_n$条件","D":r"$\sum a_n$条件，$\sum b_n$绝对"},"c":"C"},
    {"no":5,"d":"中等","kp":["向量组等价"],"q":r"$5.$ 设 $\alpha_1,\dots,\alpha_s$ 与 $\beta_1,\dots,\beta_s$ 为等价向量组，$A=(\alpha_1,\dots,\alpha_s),B=(\beta_1,\dots,\beta_s)$，则 $(A)$ 有相同相关性 $(B)$ $A$ 与 $B$ 的行向量组等价 $(C)$ $A^{\mathrm{T}}x=0$ 与 $B^{\mathrm{T}}x=0$ 同解 $(D)$ 不同解但有非零公共解","o":{"A":"相同相关性","B":"行向量组等价","C":"同解","D":"不同解有公共解"},"c":"C"},
    {"no":6,"d":"中等","kp":["伴随矩阵"],"q":'$6.$ 设 $A,B$ 为三阶非零矩阵，$AB=O$，$A^*$ 为 $A$ 的伴随矩阵，则"$A^*\\neq O$"是"$A^*$ 与 $B$ 等价"的 $(A)$ 充要条件 $(B)$ 充分非必要 $(C)$ 必要非充分 $(D)$ 非充分非必要',"o":{"A":"充要","B":"充分非必要","C":"必要非充分","D":"非充分非必要"},"c":"A"},
    {"no":7,"d":"中等","kp":["相似合同"],"q":r"$7.$ $A=\begin{pmatrix} 1 & -1 \\ -1 & 3 \end{pmatrix}$，与 $A$ 相似且合同的是 $(A)$ $\begin{pmatrix} 1 & 0 \\ 0 & 2 \end{pmatrix}$ $(B)$ $\begin{pmatrix} 2 & 0 \\ 0 & 1 \end{pmatrix}$ $(C)$ $\begin{pmatrix} 1 & 0 \\ 0 & -2 \end{pmatrix}$ $(D)$ $\begin{pmatrix} -1 & 0 \\ 0 & 2 \end{pmatrix}$","o":{"A":r"$\begin{pmatrix}1&0\\0&2\end{pmatrix}$","B":r"$\begin{pmatrix}2&0\\0&1\end{pmatrix}$","C":r"$\begin{pmatrix}1&0\\0&-2\end{pmatrix}$","D":r"$\begin{pmatrix}-1&0\\0&2\end{pmatrix}$"},"c":"A"},
    {"no":8,"d":"中等","kp":["随机变量函数"],"q":r"$8.$ 设 $X$ 概率密度 $f(x)=\begin{cases} kx, & 0<x<1 \\ 1-\frac{1}{x^2}, & 1\le x<2 \\ 0, & \text{其他} \end{cases}$，$F(x)$ 为分布函数，则 $P(X+F(X)\le \frac{5}{8})=$ $(A)$ $\frac{1}{2}$ $(B)$ $\frac{1}{4}$ $(C)$ $\frac{1}{8}$ $(D)$ $\frac{1}{16}$","o":{"A":r"$\frac{1}{2}$","B":r"$\frac{1}{4}$","C":r"$\frac{1}{8}$","D":r"$\frac{1}{16}$"},"c":"C"},
    {"no":9,"d":"中等","kp":["数字特征"],"q":r"$9.$ 已知 $DX,DY$ 均存在，正确个数为① $E^2(XY)\le E(X^2)E(Y^2)$；② $\operatorname{Cov}^2(X,Y) > \operatorname{Cov}(X,X)\operatorname{Cov}(Y,Y)$；③ $E(|X|) \ge \sqrt{E(X^2)}$；④ $DX > E(X-a)^2$。$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4","o":{"A":"1","B":"2","C":"3","D":"4"},"c":"A"},
    {"no":10,"d":"中等","kp":["随机变量类型"],"q":r"$10.$ $X\sim N(0,1),Y\sim B(1,\frac{1}{2})$ 独立，$Z_1=X+Y,Z_2=X\cdot Y$，则 $(A)$ $Z_1,Z_2$ 均非连续型 $(B)$ $Z_1$ 非连续 $Z_2$ 连续 $(C)$ $Z_1$ 连续 $Z_2$ 非连续 $(D)$ 均连续","o":{"A":"均非连续","B":r"$Z_1$非连续$Z_2$连续","C":r"$Z_1$连续$Z_2$非连续","D":"均连续"},"c":"C"},
]

FB = [
    {"no":11,"d":"中等","kp":["极限求导"],"q":r"$11.$ $f(x)=\lim_{n\to\infty} \frac{x^2}{n}(\cos\frac{x}{n}+\cos\frac{2x}{n}+\cdots+\cos\frac{nx}{n})$，则 $f^{(2026)}(0)=\underline{\qquad\qquad}$","a":r"$0$"},
    {"no":12,"d":"中等","kp":["法向量"],"q":r"$12.$ 设可微函数 $f(x,y)=2x-y-1+o(\sqrt{(x-1)^2+y^2})$，曲面 $z=f(e^{xy},x^2+y^2-1)$ 上点 $(1,0,1)$ 处指向上侧的单位法向量 $n^o=\underline{\qquad\qquad}$","a":r"$(0,0,1)$"},
    {"no":13,"d":"中等","kp":["二重积分极限"],"q":r"$13.$ $f(a,b)=\iint_D e^{\max\{b^2,a^2\}} d\sigma$，$D=\{(x,y)\mid 0\le x\le a,0\le y\le b\}$，$g(a,b)$ 是 $\frac{x}{a}+\frac{y}{b}=1$ 与坐标轴所围面积，则 $\lim_{a\to0,b\to0}\frac{f(a,b)}{g(a,b)}=\underline{\qquad\qquad}$","a":r"$1$"},
    {"no":14,"d":"中等","kp":["微分方程"],"q":r"$14.$ $f'(x)=\frac{1}{x}f(x)+\int_1^x f(t)dt$，$f(1)=1$，则 $\int_1^x f(x)dx=\underline{\qquad\qquad}$","a":r"$\frac{1}{2}x^2 - \frac{1}{2}$"},
    {"no":15,"d":"较难","kp":["矩阵","行列式"],"q":r"$15.$ 设 $A$ 可逆，$B=E-kaa^{\mathrm{T}}$ 为正交矩阵（$k>0$），$a$ 为单位列向量，$C$ 满足 $A^2-AB+CA=0$，则 $|A+C|=\underline{\qquad\qquad}$","a":r"$0$"},
    {"no":16,"d":"中等","kp":["切比雪夫不等式"],"q":r"$16.$ $X\sim N(0,\sigma^2)$，$(X_1,\dots,X_9)$ 为样本，$\overline{X}$ 为样本均值，$S^2$ 为样本方差，则 $P\{-\sigma^2 < 9\overline{X}^2 + S^2 < 5\sigma^2\} \ge \underline{\qquad\qquad}$","a":r"$\frac{9}{10}$"},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["全微分方程"],"q":r"$17.$ (本题满分10分) $f(t)$ 二阶连续可导，$t\to0^+$ 时 $f(t)$ 与 $t^2$ 同阶无穷小，$D=\{(x,y)\mid x>0,y>0\}$ 内 $du=[\frac{1}{x}(f(xy)+e^{xy})]dx + \frac{1}{y}f'(xy)dy$。(I) 求 $f(t)$；(II) 求 $f(t)$ 在 $[0,2]$ 上的平均值。","a":r"(I) $f(t)=t^2$\n(II) $\frac{4}{3}$"},
    {"no":18,"d":"中等","s":12,"kp":["多元函数极值"],"q":r"$18.$ (本题满分12分) $df=(3x^2-3a)dx+(3y^2-6y)dy$（$a>0$），$f(0,0)=0$。若 $f$ 有极大值16，求 $a$。","a":r"$a=4$"},
    {"no":19,"d":"中等","s":12,"kp":["二重积分"],"q":r"$19.$ (本题满分12分) $I=\iint_D (x+\sin y) dxdy$，$D=\{(x,y)\mid x^2+y^2\le \min(1,2x)\}$。","a":r"$\frac{1}{2}$"},
    {"no":20,"d":"较难","s":12,"kp":["积分不等式"],"q":r"$20.$ (本题满分12分) (I) 证明柯西-施瓦茨不等式 $\left(\int_a^b fg dx\right)^2 \le \int_a^b f^2 dx \int_a^b g^2 dx$。(II) 是否存在 $[0,1]$ 上连续正函数 $f(x)$ 使 $\int_0^1 f=1,\int_0^1 xf=a,\int_0^1 x^2f=a^2$？说明理由。","a":r"(I) 证明略\n(II) 不存在"},
    {"no":21,"d":"较难","s":12,"kp":["二次型","正交变换"],"q":r"$21.$ (本题满分12分) $A=(a_1,a_2,a_3)$ 为3阶对称矩阵，$(a_1+a_2-a_3, a_1-a_2, a_1+a_3)=\begin{pmatrix} 2 & -1 & -1 \\ 2 & 1 & 0 \\ -2 & 0 & -1 \end{pmatrix}$。(I) 求正交变换 $x=Qy$ 化 $x^{\mathrm{T}}(A+A^{-1})x$ 为标准形；(II) 是否存在可逆 $C$ 使 $A+2E=C^{\mathrm{T}}C$？","a":r"(I) $Q=\begin{pmatrix} \frac{1}{\sqrt{2}} & \frac{1}{\sqrt{3}} & \frac{1}{\sqrt{6}} \\ 0 & -\frac{1}{\sqrt{3}} & \frac{2}{\sqrt{6}} \\ -\frac{1}{\sqrt{2}} & \frac{1}{\sqrt{3}} & -\frac{1}{\sqrt{6}} \end{pmatrix}$，标准形 $2y_1^2+y_2^2+y_3^2$\n(II) 存在，$C=\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 1 \end{pmatrix}$"},
    {"no":22,"d":"较难","s":12,"kp":["参数估计"],"q":r"$22.$ (本题满分12分) 元件寿命 $T$ 的分布函数 $F(t)$ 满足 $\frac{F'(t)}{1-F(t)}=\frac{t^2}{\theta}$，$t\ge0,F(0)=0$，$\theta>0$ 未知。$n$ 个样本 $T_1,\dots,T_n$。(I) 求 $F(t)$；(II) 求 $\theta$ 的极大似然估计 $\hat{\theta}$ 及 $E\hat{\theta}$。","a":r"(I) $F(t)=1-e^{-\frac{t^3}{3\theta}}$\n(II) $\hat{\theta}=\frac{1}{3n}\sum_{i=1}^n T_i^3$，$E\hat{\theta}=\theta$"},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v7","solution_steps":[],"volume":V})
    for q in FB: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v7","solution_steps":[],"options":{},"volume":V})
    for q in FR: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v7","solution_steps":[],"options":{},"volume":V})
    for q in all_q:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all_q)})")

if __name__ == "__main__": main()
