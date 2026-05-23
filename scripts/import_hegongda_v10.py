"""Import 26合工大超越卷（数学一）第十套."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id
from database.question_schema import set_raw_question, set_raw_answer

MT, V = "26合工大超越", "卷十"

def fix_cases(s):
    """Only upgrade $...$ to $$...$$ around cases when Chinese text is inside."""
    if not isinstance(s, str) or r'\begin{cases}' not in s: return s
    i = 0
    while True:
        cs = s.find(r'\begin{cases}', i)
        if cs < 0: break
        ce = s.find(r'\end{cases}', cs) + len(r'\end{cases}')
        # Check if Chinese characters exist inside the cases block
        inner = s[cs:ce]
        has_chinese = any('一' <= ch <= '鿿' or '　' <= ch <= '〿' for ch in inner)
        if not has_chinese:
            i = ce
            continue
        # Find enclosing $ delimiters and upgrade to $$
        j = cs - 1
        while j >= 0 and s[j] != '$': j -= 1
        if j >= 0 and not (j > 0 and s[j-1] == '$'): s = s[:j] + '$' + s[j:]; ce += 1
        k = ce
        while k < len(s) and s[k] != '$': k += 1
        if k < len(s) and not (k+1 < len(s) and s[k+1] == '$'): s = s[:k] + '$' + s[k:]
        i = ce + 1
    return s

MC = [
    {"no":1,"d":"中等","kp":["反常积分"],"q":'$1.$ 已知反常积分 $\\int_1^{+\\infty} \\frac{\\ln(2x^2-1) \\arctan(x-1)}{(x-1)^p} dx$ 收敛，则 $(A)$ $1<p<2$ $(B)$ $2<p<3$ $(C)$ $1<p<3$ $(D)$ $2<p<4$',"o":{"A":'$1<p<2$',"B":'$2<p<3$',"C":'$1<p<3$',"D":'$2<p<4$'},"c":"A"},
    {"no":2,"d":"中等","kp":["极值"],"q":'$2.$ 设函数 $f(x),g(x)$ 在 $[a,b]$ 上连续，$f(x)\\neq g(x)$ 且 $g(x)\\neq 0$，如果 $x_0\\in(a,b)$ 为 $\\frac{f(x)}{g(x)}$ 的极大值点，则 $x_0$ 为 $\\frac{f(x)+g(x)}{f(x)-g(x)}$ 的 $(A)$ 极小值点 $(B)$ 极大值点 $(C)$ 无法判断 $(D)$ 非极值点',"o":{"A":"极小值点","B":"极大值点","C":"无法判断","D":"非极值点"},"c":"A"},
    {"no":3,"d":"中等","kp":["偏导数"],"q":'$3.$ 已知函数 $f(x,y)=\\begin{cases} x^2y, & xy\\neq0 \\\\ x, & y=0 \\\\ y, & x=0 \\end{cases}$，则 $f(x,y)$ 在点 $(0,0)$ 处 $(A)$ 偏导数 $f_x\'(x,y)$ 连续，$f_y\'\'(0,0)$ 存在 $(B)$ 偏导数 $f_x\'(x,y)$ 连续，$f_y\'\'(0,0)$ 不存在 $(C)$ 偏导数 $f_x\'(x,y)$ 不连续，$f_y\'\'(0,0)$ 存在 $(D)$ 偏导数 $f_x\'(x,y)$ 不连续，$f_y\'\'(0,0)$ 不存在',"o":{"A":'偏导数 $f_x\'(x,y)$ 连续，$f_y\'\'(0,0)$ 存在',"B":'偏导数 $f_x\'(x,y)$ 连续，$f_y\'\'(0,0)$ 不存在',"C":'偏导数 $f_x\'(x,y)$ 不连续，$f_y\'\'(0,0)$ 存在',"D":'偏导数 $f_x\'(x,y)$ 不连续，$f_y\'\'(0,0)$ 不存在'},"c":"C"},
    {"no":4,"d":"中等","kp":["曲线积分"],"q":'$4.$ 设函数 $f(t)=\\int_L (x\\ln(x^2+y^2+1))dx + (y\\ln(x^2+y^2+1))dy$，其中 $L$ 为有向曲线 $2x^2+y^2=2y$ 按照逆时针方向从点 $(0,0)$ 到点 $(\\frac{\\sqrt{2}}{2},t)$，则 $(A)$ $t=0$ 是极小值点，且 $(0,0)$ 是 $f(t)$ 拐点 $(B)$ $t=0$ 是极大值点，且 $(0,0)$ 是 $f(t)$ 拐点 $(C)$ $t=0$ 是极小值点，但 $(0,0)$ 不是 $f(t)$ 拐点 $(D)$ $t=0$ 是极大值点，但 $(0,0)$ 不是 $f(t)$ 拐点',"o":{"A":'$t=0$ 是极小值点，且 $(0,0)$ 是 $f(t)$ 拐点',"B":'$t=0$ 是极大值点，且 $(0,0)$ 是 $f(t)$ 拐点',"C":'$t=0$ 是极小值点，但 $(0,0)$ 不是 $f(t)$ 拐点',"D":'$t=0$ 是极大值点，但 $(0,0)$ 不是 $f(t)$ 拐点'},"c":"B"},
    {"no":5,"d":"中等","kp":["矩阵合同"],"q":'$5.$ 设矩阵 $A=\\begin{pmatrix} a & 0 & -1 \\\\ 0 & 2 & 0 \\\\ -1 & 0 & a \\end{pmatrix}$ 与矩阵 $B=\\begin{pmatrix} 0 & 0 & -1 \\\\ b & -1 & 0 \\\\ -1 & 0 & 2 \\end{pmatrix}$ 合同，则 $(A)$ $a<1,b=0$ $(B)$ $a<-1,b=0$ $(C)$ $a>-1,b=0$ $(D)$ $a>1,b=0$',"o":{"A":'$a<1,b=0$',"B":'$a<-1,b=0$',"C":'$a>-1,b=0$',"D":'$a>1,b=0$'},"c":"B"},
    {"no":6,"d":"中等","kp":["行列式","线性相关"],"q":'$6.$ 若 $n$ 阶方阵 $A$ 的行列式 $|A|=0$，则下列说法正确的是 $(A)$ $|A|$ 的某行（列）的元素为 0 $(B)$ $|A|$ 的某两行（列）的元素对应成比例 $(C)$ $A$ 的某行（列）向量可由其余行（列）向量组线性表示 $(D)$ $A$ 的任意一行（列）向量可由其余行（列）向量组线性表示',"o":{"A":'$|A|$ 的某行（列）的元素为 0',"B":'$|A|$ 的某两行（列）的元素对应成比例',"C":'$A$ 的某行（列）向量可由其余行（列）向量组线性表示',"D":'$A$ 的任意一行（列）向量可由其余行（列）向量组线性表示'},"c":"C"},
    {"no":7,"d":"较难","kp":["二次型"],"q":'$7.$ 设 $n$ 元二次型 $f(x_1,x_2,\\dots,x_n)=(\\sum_{i=1}^n x_i^2 + a_1 x_1)^2 + (\\sum_{i=1}^n x_i^2 + a_2 x_2)^2 + \\cdots + (\\sum_{i=1}^n x_i^2 + a_n x_n)^2$，其中 $a_i\\neq0 (i=1,2,\\dots,n)$，若二次型正定，则 $(A)$ $1+\\sum_{i=1}^n \\frac{1}{a_i}=0$ $(B)$ $1+\\sum_{i=1}^n \\frac{1}{a_i}\\neq0$ $(C)$ $1+\\sum_{i=1}^n a_i=0$ $(D)$ $1+\\sum_{i=1}^n a_i\\neq0$',"o":{"A":'$1+\\sum_{i=1}^n \\frac{1}{a_i}=0$',"B":'$1+\\sum_{i=1}^n \\frac{1}{a_i}\\neq0$',"C":'$1+\\sum_{i=1}^n a_i=0$',"D":'$1+\\sum_{i=1}^n a_i\\neq0$'},"c":"B"},
    {"no":8,"d":"中等","kp":["条件概率"],"q":'$8.$ 已知 $P(A)=\\frac{3}{5}$，$P(B)=\\frac{4}{5}$，记 $p=P(B|A)\\cdot P(B|\\overline{A})$，则 $p$ 的最大值与最小值的差为 $(A)$ $\\frac{1}{3}$ $(B)$ $\\frac{1}{4}$ $(C)$ $\\frac{1}{5}$ $(D)$ $\\frac{1}{6}$',"o":{"A":'$\\frac{1}{3}$',"B":'$\\frac{1}{4}$',"C":'$\\frac{1}{5}$',"D":'$\\frac{1}{6}$'},"c":"C"},
    {"no":9,"d":"较难","kp":["多维随机变量"],"q":'$9.$ 设二维随机变量 $(X,Y)\\sim N(0,0.4,16,-\\frac{1}{2})$，有下列 4 个命题：① $2X-Y\\sim N(0,48)$；② $\\frac{(2X+Y)^2}{16}\\sim\\chi^2(1)$；③ $\\frac{\\sqrt{3}(2X+Y)}{|2X-Y|}\\sim t(1)$；④ $\\frac{3(2X+Y)^2}{(2X-Y)^2}\\sim F(1,1)$。正确的个数是 $(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4',"o":{"A":"1","B":"2","C":"3","D":"4"},"c":"B"},
    {"no":10,"d":"较难","kp":["假设检验"],"q":'$10.$ 设 $\\overline{X}$ 为来自总体 $X\\sim N(\\mu,\\sigma^2)$ 的一个简单随机样本的样本均值，若已知在置信水平 $1-\\alpha$ 下，$\\mu$ 的置信区间的长度为 2，则在显著性水平 $\\alpha$ 下，对于假设检验问题 $H_0:\\mu=1,H_1:\\mu\\neq1$，要使得检验结果接受 $H_0$，则应有 $(A)$ $\\overline{X}\\in(-1,1)$ $(B)$ $\\overline{X}\\in(-1,3)$ $(C)$ $\\overline{X}\\in(-2,0)$ $(D)$ $\\overline{X}\\in(0,2)$',"o":{"A":'$\\overline{X}\\in(-1,1)$',"B":'$\\overline{X}\\in(-1,3)$',"C":'$\\overline{X}\\in(-2,0)$',"D":'$\\overline{X}\\in(0,2)$'},"c":"D"},
]

FB = [
    {"no":11,"d":"中等","kp":["微分方程","拐点"],"q":'$11.$ 设函数 $f(x)$ 满足 $f\'(x)-f(x)=e^x$，$f(0)=1$，则曲线 $y=f(x)$ 的拐点为 $\\underline{\\qquad\\qquad}$',"a":'$(0,1)$'},
    {"no":12,"d":"中等","kp":["切线","定积分"],"q":'$12.$ 曲线 $f(x)=x^2(0\\le x\\le 6)$ 的切线与 $x=1,x=3$ 和 $x$ 轴所围面积取得最大值为 $\\underline{\\qquad\\qquad}$',"a":'$\\frac{8}{3}$'},
    {"no":13,"d":"中等","kp":["多元函数极值"],"q":'$13.$ $f(x,y)=\\frac{1}{x^2}e^{x-y}$ 的极值点个数为 $\\underline{\\qquad\\qquad}$',"a":'$0$'},
    {"no":14,"d":"中等","kp":["二重积分"],"q":'$14.$ $\\int_{-1}^0 dy \\int_{-y}^1 (x^2y^3+x-1)dx + \\int_0^1 dy \\int_{1-y}^1 (x^2y^3+x-1)dx = \\underline{\\qquad\\qquad}$',"a":'$-\\frac{1}{3}$'},
    {"no":15,"d":"中等","kp":["矩阵","线性方程组"],"q":'$15.$ 设矩阵 $A=\\begin{pmatrix} 1 & a+1 & a \\\\ 1 & a+1 & 1 \\\\ a & 0 & 1 \\end{pmatrix}$ 不可逆，$B=(0\\ 1\\ b)$，已知 $Ax=0$ 的解均是 $Bx=0$ 的解，则 $(a,b)=\\underline{\\qquad\\qquad}$',"a":'$(1,1)$'},
    {"no":16,"d":"中等","kp":["数字特征"],"q":'$16.$ 已知连续型随机变量 $X$ 的分布函数为 $F(x)$，记 $EX=\\mu$，$DX=\\sigma^2$，$Y$ 的分布函数为 $F_Y(y)=0.4F(2y)+0.6F(y)$，则 $DY=\\underline{\\qquad\\qquad}$',"a":'$1.64\\sigma^2$'},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["数列极限","中值定理"],"q":'$17.$ (本题满分10分) 设函数 $f(x)$ 在 $[0,+\\infty)$ 上有二阶导数，$f\'(0)=1$，当 $x>0$ 时有 $0<f(x)<x$，设 $x_1>0,x_{n+1}=f(x_n),n=1,2,\\dots$。(I) 证明：数列 $\\{x_n\\}$ 收敛，并求极限；(II) 求极限 $\\lim_{n\\to\\infty} (\\frac{1}{x_n}-\\frac{1}{x_{n+1}})$。',"a":'(I) $\\lim_{n\\to\\infty}x_n=0$ (II) $\\lim_{n\\to\\infty}(\\frac{1}{x_n}-\\frac{1}{x_{n+1}})=1$'},
    {"no":18,"d":"较难","s":12,"kp":["积分中值定理"],"q":'$18.$ (本题满分12分) 设函数 $f(x)$ 在 $[a,b]$ 上连续，$g(x)$ 在 $[a,b]$ 上连续且不变号。(I) 证明：存在 $\\xi\\in[a,b]$，使得 $\\int_a^b f(x)g(x)dx = f(\\xi)\\cdot\\int_a^b g(x)dx$。(II) $f(x)$ 为 $[0,\\frac{\\pi}{2}]$ 上连续，证明：$\\lim_{n\\to\\infty} \\int_0^{\\frac{\\pi}{2}} f(x)|\\cos(nx)|dx = \\frac{2}{\\pi}\\int_0^{\\frac{\\pi}{2}} f(x)dx$。',"a":"证明略"},
    {"no":19,"d":"较难","s":12,"kp":["空间解析几何","曲面积分"],"q":'$19.$ (本题满分12分) 设 $l_1:\\frac{x-2}{1}=\\frac{y-3}{2}=\\frac{z-2}{2}$ 与 $l_2:\\frac{x-1}{1}=\\frac{y-1}{1}=\\frac{z}{0}$，(I) 求 $l_1,l_2$ 的交点和夹角。(II) 设 $\\Sigma$ 为 $l_1$ 绕 $l_2$ 旋转一周所得曲面，求 $\\Sigma$ 的方程。(III) 取 $\\Sigma_1$ 为 $\\Sigma$ 被平面 $x+y=2$ 和 $x+y=4$ 截下且位于第一卦限的有界部分，物体占有 $\\Sigma_1$ 的区域，其密度函数为 $\\rho(x,y,z)=z$，求物体的质量 $M$。',"a":'(I) 交点为 $(1,1,0)$，夹角为 $\\frac{\\pi}{4}$ (II) $\\Sigma: (x-1)^2+(y-1)^2+(z-0)^2=2$ (III) $M=\\frac{8}{3}\\pi$'},
    {"no":20,"d":"较难","s":12,"kp":["幂级数","微分方程"],"q":'$20.$ (本题满分12分) 已知幂级数 $\\sum_{n=0}^\\infty a_n x^n$ 在其收敛域内的和函数 $S(x)$ 满足微分方程 $xS\'(x)+S(x)=xe^{-x^2}$，(I) 求幂级数的系数 $a_n$，(II) 求幂级数的收敛域，(III) 求 $S(x)$。',"a":'(I) $a_n=\\frac{(-1)^n}{n!}$ (II) 收敛域为 $(-\\infty,+\\infty)$ (III) $S(x)=e^{-x^2}$'},
    {"no":21,"d":"较难","s":12,"kp":["特征值","二次型"],"q":'$21.$ (本题满分12分) 设 $A=\\begin{pmatrix} 1 & 0 & 0 \\\\ 0 & a & -1 \\\\ 0 & -1 & a \\end{pmatrix}$ 为正定矩阵，且 $A$ 有二重特征值。(I) 求 $a$ 的值；(II) 求正交矩阵 $P$，令 $x=Py$，将二次型 $f=x^{\\mathrm{T}}(A-3A^{-1})x$ 化为标准形；(III) 求可逆矩阵 $Q$，使得 $A^*=Q^{\\mathrm{T}}Q$。',"a":'(I) $a=2$ (II) $P=\\begin{pmatrix} 1 & 0 & 0 \\\\ 0 & \\frac{1}{\\sqrt{2}} & \\frac{1}{\\sqrt{2}} \\\\ 0 & \\frac{1}{\\sqrt{2}} & -\\frac{1}{\\sqrt{2}} \\end{pmatrix}$，标准形为 $y_1^2+2y_2^2+2y_3^2$ (III) $Q=\\begin{pmatrix} 1 & 0 & 0 \\\\ 0 & \\sqrt{2} & 0 \\\\ 0 & 0 & \\sqrt{2} \\end{pmatrix}$'},
    {"no":22,"d":"较难","s":12,"kp":["条件分布"],"q":'$22.$ (本题满分12分) 设随机变量 $X$ 的密度函数 $f_X(x)=\\begin{cases} ax^2e^{-x}, & x>0 \\\\ 0, & \\text{其他} \\end{cases}$，在 $X=x (x>0)$ 条件下，随机变量 $Y\\sim U(0,x)$。(I) 求常数 $a$，以及 $(X,Y)$ 的联合分布函数 $F(x,y)$，(II) 求 $Y$ 的密度函数 $f_Y(y)$，(III) 求 $Z=X-Y$ 的密度函数 $f_Z(z)$。',"a":'(I) $a=1$，$F(x,y)=\\begin{cases} 1-e^{-x}-\\frac{y}{x}(1-e^{-x}), & 0<y<x \\\\ 0, & \\text{其他} \\end{cases}$ (II) $f_Y(y)=e^{-y}$，$y>0$ (III) $f_Z(z)=e^{-z}$，$z>0$'},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v10","solution_steps":[],"volume":V})
    for q in FB: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v10","solution_steps":[],"options":{},"volume":V})
    for q in FR: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v10","solution_steps":[],"options":{},"volume":V})
    for q in all_q:
        set_raw_question(q, q["question"])
        set_raw_answer(q, q["standard_answer"])
    for q in all_q:
        try:
            r = db.insert(q)
            if r.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")
    print(f"Done: {ok} imported, {fail} failed (total {len(all_q)})")

if __name__ == "__main__": main()
