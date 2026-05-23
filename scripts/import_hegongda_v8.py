"""Import 26合工大超越卷（数学一）第八套."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MT, V = "26合工大超越", "卷八"

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
    {"no":1,"d":"中等","kp":["定积分定义"],"q":r"$1.$ $\int_0^\pi \sin x dx=$ $(A)$ $\lim_{n\to\infty} \frac{1}{n}(\sin\frac{\pi}{n}+\cdots+\sin\frac{n\pi}{n})$ $(B)$ $\lim_{n\to\infty} \frac{1}{n}(\sin\frac{\pi}{2n}+\cdots+\sin\frac{(2n-1)\pi}{2n})$ $(C)$ $\lim_{n\to\infty} \frac{\pi}{n}(\sin\frac{\pi}{2n}+\cdots+\sin\frac{(n-1)\pi}{2n})$ $(D)$ $\lim_{n\to\infty} \frac{\pi}{2n}(\sin\frac{\pi}{n}+\cdots+\sin\frac{(n-1)\pi}{n})$","o":{"A":"A","B":"B","C":"C","D":"D"},"c":"B"},
    {"no":2,"d":"中等","kp":["定积分"],"q":r"$2.$ 设 $y=y(x)$ 由 $2\cos y + xe^{-y}=1,y\in[0,\pi]$ 确定，则 $\int_{-1}^\pi y(x)dx=$ $(A)$ $\frac{\pi}{2}$ $(B)$ $0$ $(C)$ $e^{\frac{\pi}{2}}$ $(D)$ $\frac{\pi}{2}e^{\frac{\pi}{2}}$","o":{"A":r"$\frac{\pi}{2}$","B":"0","C":r"$e^{\frac{\pi}{2}}$","D":r"$\frac{\pi}{2}e^{\frac{\pi}{2}}$"},"c":"A"},
    {"no":3,"d":"中等","kp":["多元函数极值"],"q":r"$3.$ 已知 $f(x,y)$ 在 $(0,0)$ 邻域内连续，$\lim_{(x,y)\to(0,0)} \frac{f(x,y)-xy}{\sqrt{x^2+y^2}} = 1$，则 $(0,0)$ 是 $f(x,y)$ 的 $(A)$ 极小值点 $(B)$ 极大值点 $(C)$ 不是极值点 $(D)$ 不确定","o":{"A":"极小值点","B":"极大值点","C":"不是极值点","D":"不确定"},"c":"C"},
    {"no":4,"d":"中等","kp":["级数敛散性"],"q":r"$4.$ 设 $x_0>0,x_{n+1}=\sqrt{\frac{2x_n^2}{3+x_n^2}}$，则 $\sum_{n=1}^\infty (-1)^n (x_n - \ln(1+x_n))$ $(A)$ 条件收敛 $(B)$ 绝对收敛 $(C)$ 发散 $(D)$ 无法判断","o":{"A":"条件收敛","B":"绝对收敛","C":"发散","D":"无法判断"},"c":"B"},
    {"no":5,"d":"中等","kp":["初等变换"],"q":r"$5.$ 将 $A$ 第1行与第2行互换得 $B$，再将 $B$ 第2行乘 $-3$ 加到第3行得 $C$，且 $P^{-1}A=C$，则 $P=$ $(A)$ $\begin{pmatrix} 0&1&0\\1&0&3\\0&0&1 \end{pmatrix}$ $(B)$ $\begin{pmatrix} 0&1&0\\1&0&0\\0&-3&1 \end{pmatrix}$ $(C)$ $\begin{pmatrix} 1&0&0\\0&1&0\\0&3&1 \end{pmatrix}$ $(D)$ $\begin{pmatrix} 0&1&0\\1&0&0\\0&3&1 \end{pmatrix}$","o":{"A":"A","B":"B","C":"C","D":"D"},"c":"D"},
    {"no":6,"d":"中等","kp":["矩阵秩"],"q":r"$6.$ 设 $A,B$ 分别为 $m\times n$ 与 $n\times m$ 矩阵，$r(A)=r(B)=m$，则正确个数为① $BA$ 的行向量组与 $B$ 的行向量组等价；② $A^{\mathrm{T}}B^{\mathrm{T}}$ 的行向量组与 $B^{\mathrm{T}}$ 的行向量组等价；③ $BA$ 的列向量组与 $A$ 的列向量组有相同线性相关性；④ $BA$ 的行向量组与 $A$ 的行向量组等价。$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4","o":{"A":"1","B":"2","C":"3","D":"4"},"c":"C"},
    {"no":7,"d":"中等","kp":["二次型正定"],"q":r"$7.$ $A$ 为3阶可逆对称矩阵，二次型：① $x^{\mathrm{T}}Ax$；② $x^{\mathrm{T}}A^{\mathrm{T}}Ax$；③ $x^{\mathrm{T}}A^2x$；④ $x^{\mathrm{T}}A^{-1}A^*x$，其中正定的是 $(A)$ ①③ $(B)$ ①②④ $(C)$ ②③ $(D)$ ②③④","o":{"A":"①③","B":"①②④","C":"②③","D":"②③④"},"c":"C"},
    {"no":8,"d":"中等","kp":["概率不等式"],"q":r"$8.$ 若 $A$ 与 $B$ 同时发生时 $C$ 发生；若 $A$ 与 $B$ 都不发生时 $C$ 也不发生，正确个数为① $P(A\cup B\cup C) > P(A\cup B)$；② $P(C-A) \le P(B-A)$；③ $P(C) \le P(A)+P(B)-1$；④ $P(C)=P(AB)$。$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4","o":{"A":"1","B":"2","C":"3","D":"4"},"c":"B"},
    {"no":9,"d":"中等","kp":["抽样分布"],"q":r"$9.$ $X\sim N(0,1),X_1,X_2$ 为样本，① $X_1^2+X_2^2 \sim E(\frac{1}{2})$；② $\frac{X_1+X_2}{|X_1-X_2|} \sim t(1)$；③ $\frac{1}{2}+\frac{X_1^2}{2X_2^2} \sim F(2,1)$。正确个数为 $(A)$ 0 $(B)$ 1 $(C)$ 2 $(D)$ 3","o":{"A":"0","B":"1","C":"2","D":"3"},"c":"A"},
    {"no":10,"d":"中等","kp":["概率计算"],"q":r"$10.$ $X,Y$ 同分布，$X$ 密度 $f(x)$ 满足 $f(1-x)=f(1+x)$，若 $P(X\ge 2,Y\ge 0)=p(0<p<\frac{1}{2})$，则 $P(X<2,Y<0)=$ $(A)$ $1-p$ $(B)$ $1-\frac{p}{2}$ $(C)$ $1-2p$ $(D)$ $p$","o":{"A":r"$1-p$","B":r"$1-\frac{p}{2}$","C":r"$1-2p$","D":r"$p$"},"c":"C"},
]

FB = [
    {"no":11,"d":"中等","kp":["渐近线"],"q":r"$11.$ $y=y(x)$ 是 $y'+(x^2+1)y=x^2+\sin^4 x$ 的一个解，则曲线有一条水平渐近线 $y=\underline{\qquad\qquad}$","a":r"$1$"},
    {"no":12,"d":"中等","kp":["极限"],"q":r"$12.$ $z=f(x,y)$ 有连续偏导，$f(x,x^2)=1,f_x'(1,1)=2$，则 $\lim_{x\to 0} [f(\cos x,\sqrt{1+x^2})]^{\frac{1}{\ln(1+x^2)}} = \underline{\qquad\qquad}$","a":r"$e^{\frac{1}{2}}$"},
    {"no":13,"d":"中等","kp":["曲面积分"],"q":r"$13.$ $\Sigma: x^2+y^2+z^2=1$ 取外侧，$f(u)$ 连续，则 $\iint_{\Sigma} [f(x^2\sin(x^4y))+2] dy dz + [f(x\arctan(y^2z))+2y] dz dx + z^2 dx dy = \underline{\qquad\qquad}$","a":r"$0$"},
    {"no":14,"d":"中等","kp":["高阶导数"],"q":r"$14.$ $f(x)=\frac{\sin x^{2024}}{1-x^2}$，则 $f^{(2026)}(0)=\underline{\qquad\qquad}$","a":r"$0$"},
    {"no":15,"d":"中等","kp":["特征值","伴随矩阵"],"q":r"$15.$ $A$ 为2阶方阵，$\alpha_1,\alpha_2$ 是属于特征值 $0,3$ 的特征向量，$A^*$ 为伴随矩阵，则 $A^*x=\alpha_1$ 的通解为 $\underline{\qquad\qquad}$","a":r"$x=k\alpha_2 + \frac{1}{3}\alpha_1$，$k\in\mathbf{R}$"},
    {"no":16,"d":"中等","kp":["数字特征"],"q":r"$16.$ $X$ 分布函数 $F(x)$ 满足 $F(0)=0.3,F(1)=0.8,F(2)=0.9,F(3)=1$，则 $E(X^2)=\underline{\qquad\qquad}$","a":r"$2.5$"},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["二重积分"],"q":r"$17.$ (本题满分10分) $D: x^2+y^2\le 1$，计算 $I=\iint_D \frac{\arctan\frac{1+x^2}{1+y^2}}{1+e^{-y}} dxdy$。","a":r"$\frac{\pi}{4}\ln 2$"},
    {"no":18,"d":"较难","s":12,"kp":["积分不等式"],"q":r"$18.$ (本题满分12分) $f(x)$ 在 $[0,+\infty)$ 上二阶可导，$f''(x)>0$，$F(x)=\frac{1}{x}\int_0^x f(t)dt$。证明：任意 $a,b>0$，$F(b)-F(a) \ge F(\frac{a+b}{2})-F(a)$。","a":r"证明略"},
    {"no":19,"d":"较难","s":12,"kp":["偏微分方程"],"q":r"$19.$ (本题满分12分) (I) $z=f(x,y)$ 有一阶连续偏导，$y\frac{\partial f}{\partial x}=x\frac{\partial f}{\partial y}$。证明：令 $x=r\cos\theta,y=r\sin\theta$，则 $z=g(r)$。(II) $f(x,y)$ 有连续偏导，$f(0,0)=f(1,1)$。证明：在 $0\le x\le 1,0\le y\le 1$ 至少存在一点 $(\xi,\zeta)$ 满足 $\frac{\partial f}{\partial x} + nx^{n-1}\frac{\partial f}{\partial y}=0$。","a":r"证明略"},
    {"no":20,"d":"较难","s":12,"kp":["零点问题"],"q":r"$20.$ (本题满分12分) $f(x)$ 在 $[0,+\infty)$ 上二阶可导，$f(0)>0,f'(0)<0,f''(x)\ge k>0$，讨论 $f(x)$ 在 $(0,+\infty)$ 内有几个零点。","a":r"有且仅有一个零点"},
    {"no":21,"d":"较难","s":12,"kp":["特征值","矩阵幂"],"q":r"$21.$ (本题满分12分) $A=E-\alpha\alpha^{\mathrm{T}}+\beta\beta^{\mathrm{T}}$，$\|\alpha+\beta\|=\|\alpha-\beta\|$。(I) 证明 $\alpha,\beta$ 正交；(II) 若 $\alpha=(1,-1)^{\mathrm{T}},A(1,0)^{\mathrm{T}}=(1,2)^{\mathrm{T}}$，求 $A$ 特征值和特征向量；(III) $\gamma=(1,-3)^{\mathrm{T}}$，求 $A^{2026}\gamma$。","a":r"(I) 证明略\n(II) $\lambda_1=1,\lambda_2=3$，特征向量 $(1,0)^{\mathrm{T}},(1,-2)^{\mathrm{T}}$\n(III) $A^{2026}\gamma = (1,-3\cdot 3^{2026})^{\mathrm{T}}$"},
    {"no":22,"d":"较难","s":12,"kp":["数理统计"],"q":r"$22.$ (本题满分12分) $(X_1,X_2)$ 来自 $X\sim U[0,1]$。(I) 证明 $(X_1,X_2)$ 服从 $[0,1]^2$ 上均匀分布；(II) 求 $P(\overline{X}\le\frac{1}{4})$ 和 $P(S^2\le\frac{1}{8})$；(III) $\overline{X}$ 与 $S^2$ 是否独立？","a":r"(I) 证明略\n(II) $P(\overline{X}\le\frac{1}{4})=\frac{1}{32},P(S^2\le\frac{1}{8})=\frac{1}{2}$\n(III) 不独立"},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v8","solution_steps":[],"volume":V})
    for q in FB: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v8","solution_steps":[],"options":{},"volume":V})
    for q in FR: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v8","solution_steps":[],"options":{},"volume":V})
    for q in all_q:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all_q)})")

if __name__ == "__main__": main()
