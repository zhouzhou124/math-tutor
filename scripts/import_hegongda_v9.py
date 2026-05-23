"""Import 26合工大超越卷（数学一）第九套."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id
from database.question_schema import set_raw_question, set_raw_answer

MT, V = "26合工大超越", "卷九"

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
    {"no":1,"d":"中等","kp":["极限"],"q":'$1.$ “对任意的 $\\varepsilon>0$，只有有限个 $x_n\\in[a-\\varepsilon,a+\\varepsilon]$”是“$\\lim_{n\\to\\infty}x_n=a$”的 $(A)$ 充分而非必要条件 $(B)$ 必要而非充分条件 $(C)$ 充分必要条件 $(D)$ 既非充分又非必要条件',"o":{"A":"充分而非必要条件","B":"必要而非充分条件","C":"充分必要条件","D":"既非充分又非必要条件"},"c":"C"},
    {"no":2,"d":"中等","kp":["导数","拐点"],"q":'$2.$ 设函数 $y=y(x)$ 是由方程 $x^3+y^3+xy-1=0$ 确定，则 $(A)$ $x=0$ 是函数 $y=y(x)$ 极大值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点 $(B)$ $x=0$ 是函数 $y=y(x)$ 极小值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点 $(C)$ $x=0$ 不是函数 $y=y(x)$ 极值点，$(0,1)$ 是曲线 $y=y(x)$ 的拐点 $(D)$ $x=0$ 不是函数 $y=y(x)$ 极值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点',"o":{"A":'$x=0$ 是函数 $y=y(x)$ 极大值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点',"B":'$x=0$ 是函数 $y=y(x)$ 极小值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点',"C":'$x=0$ 不是函数 $y=y(x)$ 极值点，$(0,1)$ 是曲线 $y=y(x)$ 的拐点',"D":'$x=0$ 不是函数 $y=y(x)$ 极值点，$(0,1)$ 不是曲线 $y=y(x)$ 的拐点'},"c":"C"},
    {"no":3,"d":"中等","kp":["方向导数","多元函数微分"],"q":'$3.$ 设函数 $f(x,y)$ 在 $(0,0)$ 处可微，且在该点处指向 $P_1(-1,0)$ 及 $P_2(0,-1)$ 的方向导数分别为1和-1，若 $g(x,y)=f(x^2+y,x+y^2)$，则 $dg|_{(0,0)}=$ $(A)$ $-dx-dy$ $(B)$ $-dx+dy$ $(C)$ $dx-dy$ $(D)$ $dx+dy$',"o":{"A":'$-dx-dy$',"B":'$-dx+dy$',"C":'$dx-dy$',"D":'$dx+dy$'},"c":"A"},
    {"no":4,"d":"中等","kp":["曲线积分"],"q":'$4.$ 设一质点在平面上受变力 $F(x,y)=\\frac{(x+y)i+(y-x)j}{x^2+y^2}$ 的作用，从点 $A(-1,0)$ 处沿曲线 $y=1-x^2$ 运动到点 $B(1,0)$ 处，则变力 $F(x,y)$ 对质点所做的功 $W=$ $(A)$ $0$ $(B)$ $\\frac{\\pi}{2}$ $(C)$ $\\frac{\\pi}{3}$ $(D)$ $\\pi$',"o":{"A":"0","B":'$\\frac{\\pi}{2}$',"C":'$\\frac{\\pi}{3}$',"D":'$\\pi$'},"c":"A"},
    {"no":5,"d":"中等","kp":["特征值","行列式"],"q":'$5.$ 设 $A=(a_{ij})$ 为3阶非零矩阵；若存在非零列向量 $\\alpha_i$，满足 $A\\alpha_i=i\\alpha_i$，$(i=1,2,3)$，$A_{ij}$ 为 $|A|$ 的元素 $a_{ij}$ 的代数余子式，则 $A_{11}+A_{22}+A_{33}=$ $(A)$ 6 $(B)$ 11 $(C)$ 12 $(D)$ 36',"o":{"A":"6","B":"11","C":"12","D":"36"},"c":"B"},
    {"no":6,"d":"中等","kp":["线性方程组"],"q":'$6.$ 已知 $A$ 为 $n$ 阶矩阵，$n$ 维列向量 $b$ 与齐次线性方程组 $Ax=0$ 的解向量均正交，则 $(A)$ $b^{\\mathrm{T}}$ 可以由 $A^{\\mathrm{T}}$ 的行向量组线性表示 $(B)$ 方程组 $A^{\\mathrm{T}}x=b$ 有解 $(C)$ 方程组 $Ax=b$ 有解 $(D)$ 以上说法均不正确',"o":{"A":'$b^{\\mathrm{T}}$ 可以由 $A^{\\mathrm{T}}$ 的行向量组线性表示',"B":'方程组 $A^{\\mathrm{T}}x=b$ 有解',"C":'方程组 $Ax=b$ 有解',"D":"以上说法均不正确"},"c":"B"},
    {"no":7,"d":"较难","kp":["二次型","特征值"],"q":'$7.$ 设3阶矩阵 $A=\\alpha a^{\\mathrm{T}}+2\\beta b^{\\mathrm{T}}-3\\gamma y^{\\mathrm{T}}$，其中3维单位列向量 $\\alpha,\\beta,\\gamma$ 两两正交，$E$ 为3阶单位矩阵；若二次型 $f(x_1,x_2,x_3)=x^{\\mathrm{T}}(A^*+kE)x=1$ 在空间直角坐标系下表示单叶双曲面，则 $(A)$ $-2<k<6$ $(B)$ $-2<k<3$ $(C)$ $3<k<6$ $(D)$ $k>6$',"o":{"A":'$-2<k<6$',"B":'$-2<k<3$',"C":'$3<k<6$',"D":'$k>6$'},"c":"A"},
    {"no":8,"d":"中等","kp":["几何概型"],"q":'$8.$ 将一根长为2米的直杆随机截成两段，恰好与另一根长为1米的直杆构成钝角三角形的概率 $(A)$ $\\frac{1}{5}$ $(B)$ $\\frac{1}{4}$ $(C)$ $\\frac{1}{6}$ $(D)$ $\\frac{1}{3}$',"o":{"A":'$\\frac{1}{5}$',"B":'$\\frac{1}{4}$',"C":'$\\frac{1}{6}$',"D":'$\\frac{1}{3}$'},"c":"A"},
    {"no":9,"d":"较难","kp":["多维随机变量"],"q":'$9.$ 设二维连续型随机变量 $(X,Y)$ 的分布函数为 $F(x,y)=\\begin{cases} 0, & x\\le 0 \\text{ 或 } y\\le 0 \\\\ 1-e^{-x}-ye^{-y}, & 0\\le y\\le x \\\\ 1-(1+x)e^{-x}, & 0\\le x\\le y \\end{cases}$，则 $P\\{XY-\\frac{1}{2}X-Y+\\frac{1}{2}\\le 0\\}=$ $(A)$ $\\frac{1}{2}(e^{-\\frac{1}{2}}-e^{-1})$ $(B)$ $e^{-\\frac{1}{2}}-e^{-1}$ $(C)$ $2(e^{-\\frac{1}{2}}-e^{-1})$ $(D)$ $2e^{-\\frac{1}{2}}-e^{-1}$',"o":{"A":'$\\frac{1}{2}(e^{-\\frac{1}{2}}-e^{-1})$',"B":'$e^{-\\frac{1}{2}}-e^{-1}$',"C":'$2(e^{-\\frac{1}{2}}-e^{-1})$',"D":'$2e^{-\\frac{1}{2}}-e^{-1}$'},"c":"A"},
    {"no":10,"d":"较难","kp":["数字特征"],"q":'$10.$ 已知 $X_1,X_2,\\dots,X_n$ 为总体 $X$ 的一个简单随机样本，且 $X\\sim N(0,\\sigma^2)$，记 $\\overline{X}=\\frac{1}{n}\\sum_{i=1}^n X_i$，$S_n^2=\\frac{1}{n}\\sum_{i=1}^n X_i^2-\\overline{X}^2$，则 $E[(X+S_n^2)^2]=$ $(A)$ $\\frac{\\sigma^2}{n}+\\frac{(n^2-1)\\sigma^4}{n^2}$ $(B)$ $\\frac{\\sigma^2+\\sigma^4}{n}$ $(C)$ $\\frac{\\sigma^2}{n}+\\frac{(n^2+1)\\sigma^4}{n^2}$ $(D)$ $\\frac{\\sigma^2}{n-1}+\\frac{n^2\\sigma^4}{n-1}$',"o":{"A":'$\\frac{\\sigma^2}{n}+\\frac{(n^2-1)\\sigma^4}{n^2}$',"B":'$\\frac{\\sigma^2+\\sigma^4}{n}$',"C":'$\\frac{\\sigma^2}{n}+\\frac{(n^2+1)\\sigma^4}{n^2}$',"D":'$\\frac{\\sigma^2}{n-1}+\\frac{n^2\\sigma^4}{n-1}$'},"c":"C"},
]

FB = [
    {"no":11,"d":"中等","kp":["极限","积分"],"q":'$11.$ $\\lim_{x\\to0^+} \\frac{x\\int_x^{2x} \\sqrt{2xt-t^2} dt}{x-\\sin x} = \\underline{\\qquad\\qquad}$',"a":'$\\frac{4}{3}$'},
    {"no":12,"d":"中等","kp":["旋转体体积"],"q":'$12.$ 曲线 $y=\\lim_{n\\to\\infty} \\frac{x}{e^{-nx}-(x^2+1)}$ 与直线 $y=-\\frac{x}{2}$ 所围平面图形绕 $x$ 轴旋转所成旋转体的体积 $V=\\underline{\\qquad\\qquad}$',"a":'$\\frac{\\pi}{6}$'},
    {"no":13,"d":"中等","kp":["偏导数"],"q":'$13.$ 设可微函数 $f(x,y)$ 满足 $(\\frac{\\partial f}{\\partial x})^2+(\\frac{\\partial f}{\\partial y})^2=\\frac{1}{x^2+y^2}$，若极坐标系下 $f(x,y)$ 可表示为 $z(r,\\theta)$，则 $r^2(\\frac{\\partial z}{\\partial r})^2+(\\frac{\\partial z}{\\partial \\theta})^2=\\underline{\\qquad\\qquad}$',"a":'$1$'},
    {"no":14,"d":"中等","kp":["反常积分","无穷级数"],"q":'$14.$ 设反常积分 $\\int_1^{+\\infty} \\frac{dx}{(1+x)^\\lambda}$ 发散，无穷级数 $\\sum_{n=1}^\\infty (\\tan\\frac{1}{n}-\\frac{1}{n})^\\lambda$ 收敛，则 $\\lambda\\in\\underline{\\qquad\\qquad}$',"a":'$(-\\infty,1)$'},
    {"no":15,"d":"中等","kp":["行列式"],"q":'$15.$ 设 $a\\neq0$，则行列式 $D_4=\\begin{vmatrix} a & -a & 0 & 0 \\\\ 1 & 2a-1 & -2a & 0 \\\\ 0 & 2 & 3a-2 & -3a \\\\ 0 & 0 & 3 & 4a-3 \\end{vmatrix} = \\underline{\\qquad\\qquad}$',"a":'$a^4$'},
    {"no":16,"d":"中等","kp":["数字特征"],"q":'$16.$ 一袋中有 $a$ 只白球，$b$ 只黑球，现有放回地依次取出，直到白球、黑球都取到为止，设 $X$ 表示取球次数，则 $EX=\\underline{\\qquad\\qquad}$',"a":'$\\frac{a+b}{a} + \\frac{a+b}{b} - 1$'},
]

FR = [
    {"no":17,"d":"中等","s":10,"kp":["积分"],"q":'$17.$ (本题满分10分) 设函数 $\\varphi(x)=\\int_0^1 \\ln\\sqrt{x^2+t^2} dt$，$x>0$，求 $\\varphi\'(1)$。',"a":'$\\varphi\'(1)=\\frac{1}{2}\\ln 2$'},
    {"no":18,"d":"较难","s":12,"kp":["二重积分","极值"],"q":'$18.$ (本题满分12分) 已知 $(a,b)$ 为圆弧 $x^2+y^2=1$ 上任意一点，且 $0\\le a\\le b$，求 $f(a,b)=6\\iint_D |x-y| d\\sigma - (a-b)^3$ 的最大值与最小值，其中 $D=\\{(x,y)\\mid 0\\le x\\le a,0\\le y\\le b\\}$。',"a":'最大值 $2$，最小值 $-\\frac{1}{2}$'},
    {"no":19,"d":"较难","s":12,"kp":["曲面积分"],"q":'$19.$ (本题满分12分) 设 $\\Sigma$ 为空间闭区域 $|x|+|y|+|z|\\le 1$ 的全表面，取外侧，计算积分 $I=\\iint_{\\Sigma} \\frac{yz dy dz + xz dz dx - 2xy dx dy}{x^2+y^2+z^2}$。',"a":'$0$'},
    {"no":20,"d":"中等","s":12,"kp":["积分中值定理","微分中值定理"],"q":'$20.$ (本题满分12分) 设函数 $f(x)$ 在 $[a,b]$ 上连续，且 $\\int_a^b f(x)dx=0$。(I) 证明：存在 $\\xi\\in(a,b)$，使得 $f(\\xi)=0$。(II) 若 $f(x)$ 在 $(a,b)$ 上可导，且 $\\int_a^b xf(x)dx=0$，证明：存在 $\\eta\\in(a,b)$，使得 $f\'(\\eta)=0$。',"a":"证明略"},
    {"no":21,"d":"较难","s":12,"kp":["特征值","矩阵"],"q":'$21.$ (本题满分12分) 已知3阶实对称矩阵 $A$ 有3个互异的特征值 $\\lambda_1,\\lambda_2,\\lambda_3$，对应的特征向量分别为 $x_1,x_2,x_3$，$E$ 为三阶单位阵，记 $a=x_1+2x_2+3x_3$。(I) 证明 $a,Aa,A^2a$ 线性无关；(II) 若 $A^3a=-2a+Aa+2A^2a$，记 $P=(a,Aa,A^2a)$，求 $A$ 的特征值；(III) 记 $B=A^2+E$，其单特征值对应的特征向量为 $\\xi_1=(1,2,-2)^{\\mathrm{T}}$，求矩阵 $B$。',"a":'(I) 证明略 (II) $\\lambda_1=1,\\lambda_2=-1,\\lambda_3=2$ (III) $B=\\begin{pmatrix} 1 & 0 & 0 \\\\ 0 & 1 & 0 \\\\ 0 & 0 & 1 \\end{pmatrix}$'},
    {"no":22,"d":"较难","s":12,"kp":["多维随机变量"],"q":'$22.$ (本题满分12分) 设标准正态分布的密度函数为 $\\varphi(x)$，以及 $g(x)=\\begin{cases} x, & -1\\le x\\le 1 \\\\ 0, & \\text{其他} \\end{cases}$，设 $f(x,y)=\\varphi(x)\\varphi(y)+k x g(x) g(y)$（$-\\infty<x,y<+\\infty$）。(I) 求 $k$ 取值范围，使得 $f(x,y)$ 为随机变量 $(X,Y)$ 的联合密度函数；(II) 判断 $X$ 和 $Y$ 是否相关，是否独立。',"a":'(I) $k\\in[-1,1]$ (II) $X$ 与 $Y$ 不相关，当 $k=0$ 时独立，当 $k\\neq0$ 时不独立'},
]

def main():
    db = QuestionDB(); ok = fail = 0; all_q = []
    for q in MC: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"选择题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"options":q["o"],"correct_option":q["c"],"standard_answer":q["c"],"source":"import_hegongda_v9","solution_steps":[],"volume":V})
    for q in FB: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"填空题","question_no":q["no"],"score":5,"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v9","solution_steps":[],"options":{},"volume":V})
    for q in FR: all_q.append({"question_id":make_question_id(2026,MT,q["no"],V),"year":2026,"category":MT,"question_type":"解答题","question_no":q["no"],"score":q["s"],"difficulty":q["d"],"knowledge_points":q["kp"],"tags":q["kp"],"question":fix_cases(q["q"]),"standard_answer":fix_cases(q["a"]),"source":"import_hegongda_v9","solution_steps":[],"options":{},"volume":V})
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
