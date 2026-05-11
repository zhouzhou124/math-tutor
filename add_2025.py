"""Add 2025 exam (22 questions)."""
import json
from pathlib import Path
from datetime import datetime

DATA = Path('E:/math_tutor/storage/questions/data')
IDX = Path('E:/math_tutor/storage/questions/_index.json')

def qq(qid, qt, kp, diff, s, question, answer, opts=None, corr=None):
    no = int(qid.split('-')[-1])
    return {'question_id':qid,'year':2025,'category':'数学一','question_type':qt,
            'question_no':no,'knowledge_points':kp,'difficulty':diff,'score':s,
            'question':question,'standard_answer':answer,'solution_steps':[],
            'common_mistakes':[],'tags':kp,'source':'manual_2025',
            'options':opts or {},'correct_option':corr}

qs = [
qq('2025-数一-001','选择题',['导数与微分','定积分'],'中等',5,"$1.$ $f(x) = \\int_{0}^{x} e^{t^{2}} \\sin t \\, dt, g(x) = \\int_{0}^{x} e^{t^{2}} dt \\cdot \\sin^{2} x$，则（ ）\n\n$(A)$ $x = 0$ 是 $f(x)$ 的极值点，也是 $g(x)$ 的极值点\n$(B)$ $x = 0$ 是 $f(x)$ 的极值点，$(0,0)$ 是曲线 $y = g(x)$ 的拐点\n$(C)$ $x = 0$ 是 $f(x)$ 的极值点，$(0,0)$ 是曲线 $y = f(x)$ 的拐点\n$(D)$ $(0,0)$ 是曲线 $y = f(x)$ 的拐点，也是曲线 $y = g(x)$ 的拐点","B.",{'A':'A','B':'B','C':'C','D':'D'},'B'),
qq('2025-数一-002','选择题',['无穷级数'],'中等',5,"$2.$ 已知级数：① $\\sum_{n=1}^{\\infty} \\frac{\\sin (n\\pi + \\frac{\\pi}{3})}{n^2 + 1}$；② $\\sum_{n=1}^{\\infty} (-1)^{n-1} \\left( \\frac{1}{n} - \\tan \\frac{1}{n} \\right)$，则（ ）\n\n$(A)$ ①与②均条件收敛\n$(B)$ ①条件收敛，②绝对收敛\n$(C)$ ①绝对收敛，②条件收敛\n$(D)$ ①与②均绝对收敛","B.",{'A':'A','B':'B','C':'C','D':'D'},'B'),
qq('2025-数一-003','选择题',['导数与微分','极限与连续'],'中等',5,"$3.$ 设函数 $f(x)$ 在区间 $(0,+\\infty)$ 上可导，则（ ）\n\n$(A)$ 当 $\\lim_{x\\to+\\infty}f(x)$ 存在时，$\\lim_{x\\to+\\infty}f'(x)$ 存在\n$(B)$ 当 $\\lim_{x\\to+\\infty}f'(x)$ 存在时，$\\lim_{x\\to+\\infty}f(x)$ 存在\n$(C)$ 当 $\\lim_{x\\to+\\infty}\\frac{\\int_0^x f(t)dt}{x}$ 存在时，$\\lim_{x\\to+\\infty}f(x)$ 存在\n$(D)$ 当 $\\lim_{x\\to+\\infty}f(x)$ 存在时，$\\lim_{x\\to+\\infty}\\frac{\\int_0^x f(t)dt}{x}$ 存在","D.",{'A':'A','B':'B','C':'C','D':'D'},'D'),
qq('2025-数一-004','选择题',['二重积分'],'较难',5,"$4.$ 设函数 $f(x,y)$ 连续，则 $\\int_{-2}^{2} dx \\int_{4-x^{2}}^{4} f(x,y) dy =$（ ）\n\n$(A)$ $\\int_{0}^{4}[\\int_{-2}^{-\\sqrt{4-y}}f(x,y)dx+\\int_{\\sqrt{4-y}}^{2}f(x,y)dx]dy$\n$(B)$ $\\int_{0}^{4}[\\int_{-2}^{-\\sqrt{4-y}}f(x,y)dx+\\int_{\\sqrt{4-y}}^{2}f(x,y)dx]dy$\n$(C)$ $\\int_{0}^{4}[\\int_{-2}^{-\\sqrt{4-y}}f(x,y)dx+\\int_{\\sqrt{4-y}}^{2}f(x,y)dx]dy$\n$(D)$ $\\int_{0}^{4} dy \\int_{\\sqrt{4-y}}^{2} f(x,y) dx$","A.",{'A':'A','B':'B','C':'C','D':'D'},'A'),
qq('2025-数一-005','选择题',['二次型'],'基础',5,"$5.$ 二次型 $f(x_1,x_2,x_3) = x_1^2 + 2x_1x_2 + 2x_1x_3$ 的正惯性指数为（ ）\n\n$(A)$ 0\n$(B)$ 1\n$(C)$ 2\n$(D)$ 3","B.",{'A':'0','B':'1','C':'2','D':'3'},'B'),
qq('2025-数一-006','选择题',['向量组与线性空间'],'中等',5,"$6.$ 设 $\\alpha_1,\\alpha_2,\\alpha_3,\\alpha_4$ 是 $n$ 维列向量，$\\alpha_1,\\alpha_2$ 线性无关，$\\alpha_1,\\alpha_2,\\alpha_3$ 线性相关，且 $\\alpha_1+\\alpha_2+\\alpha_4=0$。关于 $x,y,z$ 的方程组 $x\\alpha_1+y\\alpha_2+z\\alpha_3=\\alpha_4$ 的几何图形是（ ）\n\n$(A)$ 过原点的一个平面\n$(B)$ 过原点的一条直线\n$(C)$ 不过原点的一个平面\n$(D)$ 不过原点的一条直线","D.",{'A':'A','B':'B','C':'C','D':'D'},'D'),
qq('2025-数一-007','选择题',['矩阵运算'],'较难',5,"$7.$ 设 $n$ 阶矩阵 $A,B,C$ 满足 $r(A)+r(B)+r(C)=r(ABC)+2n$，下列结论：①$r(ABC)+n=r(AB)+r(C)$；②$r(AB)+n=r(A)+r(B)$；③$r(A)=r(B)=r(C)=n$；④$r(AB)=r(BC)=n$。其中正确结论的序号是（ ）\n\n$(A)$ ①②\n$(B)$ ①③\n$(C)$ ②④\n$(D)$ ③④","A.",{'A':'①②','B':'①③','C':'②④','D':'③④'},'A'),
qq('2025-数一-008','选择题',['数字特征'],'中等',5,"$8.$ 设二维随机变量 $(X,Y)$ 服从正态分布 $N(0,0;1,1;\\rho)$，$\\rho\\in(-1,1)$。若 $a,b$ 满足 $a^2+b^2=1$，则 $D(aX+bY)$ 的最大值为（ ）\n\n$(A)$ 1\n$(B)$ 2\n$(C)$ $1+|\\rho|$\n$(D)$ $1+\\rho^2$","C.",{'A':'1','B':'2','C':'$1+|\\rho|$','D':'$1+\\rho^2$'},'C'),
qq('2025-数一-009','选择题',['数理统计'],'中等',5,"$9.$ 设 $X_1,\\cdots,X_{20}$ 是来自总体 $B(1,0.1)$ 的简单随机样本。令 $T=\\sum_{i=1}^{20} X_i$，利用泊松分布近似，$P\\{T\\le 1\\}\\approx$（ ）\n\n$(A)$ $\\frac{1}{e^2}$\n$(B)$ $\\frac{2}{e^2}$\n$(C)$ $\\frac{3}{e^2}$\n$(D)$ $\\frac{4}{e^2}$","C.",{'A':'$1/e^2$','B':'$2/e^2$','C':'$3/e^2$','D':'$4/e^2$'},'C'),
qq('2025-数一-010','选择题',['数理统计'],'中等',5,"$10.$ 设 $X_1,\\cdots,X_n$ 为来自正态总体 $N(\\mu,2)$ 的简单随机样本。记 $\\bar{X}=\\frac{1}{n}\\sum_{i=1}^n X_i$，$Z_\\alpha$ 为标准正态分布的上侧 $\\alpha$ 分位数。$H_0:\\mu\\le 1, H_1:\\mu>1$ 的显著性水平为 $\\alpha$ 的检验拒绝域为（ ）\n\n$(A)$ $\\bar{X}>1+\\frac{2}{n}Z_\\alpha$\n$(B)$ $\\bar{X}>1+\\frac{\\sqrt{2}}{n}Z_\\alpha$\n$(C)$ $\\bar{X}>1+\\frac{2}{\\sqrt{n}}Z_\\alpha$\n$(D)$ $\\bar{X}>1+\\sqrt{\\frac{2}{n}}Z_\\alpha$","D.",{'A':'A','B':'B','C':'C','D':'D'},'D'),
qq('2025-数一-011','填空题',['极限与连续'],'中等',5,"$11.$ $\\lim_{x \\to 0^+} \\frac{x^x - 1}{\\ln x \\cdot \\ln(1-x)} = \\underline{\\qquad\\qquad}$","$-1$."),
qq('2025-数一-012','填空题',['无穷级数'],'较难',5,"$12.$ 已知函数 $f(x) = \\begin{cases} 0, & 0 \\le x < \\frac{1}{2} \\\\ x^2, & \\frac{1}{2} \\le x \\le 1 \\end{cases}$ 的傅里叶级数为 $\\sum_{n=1}^\\infty b_n \\sin n\\pi x$，$S(x)$ 为和函数，则 $S(-\\frac{7}{2}) = \\underline{\\qquad\\qquad}$","$\\frac{1}{8}$."),
qq('2025-数一-013','填空题',['多元函数微分'],'中等',5,"$13.$ 已知函数 $u(x,y,z) = xy^2z^3$，向量 $\\mathbf{n} = (2,2,-1)$，则 $\\left.\\frac{\\partial u}{\\partial \\mathbf{n}}\\right|_{(1,1,1)} = \\underline{\\qquad\\qquad}$","$1$."),
qq('2025-数一-014','填空题',['曲线曲面积分'],'较难',5,"$14.$ 已知有向曲线 $L$ 是沿抛物线 $y = 1 - x^2$ 从点 $(1,0)$ 到点 $(-1,0)$ 的一段，则 $\\int_L (y + \\cos x) dx + (2x + \\cos y) dy = \\underline{\\qquad\\qquad}$","$\\frac{4}{3} - 2\\sin 1$."),
qq('2025-数一-015','填空题',['线性方程组','矩阵运算'],'较难',5,"$15.$ 设矩阵 $A = \\begin{pmatrix} 4 & -2 & 3 \\\\ 3 & a & -4 \\\\ 5 & 7 & b \\end{pmatrix}$，若方程组 $A^2 x = 0$ 与 $Ax = 0$ 不同解，则 $a - b = \\underline{\\qquad\\qquad}$","$-4$."),
qq('2025-数一-016','填空题',['随机事件与概率'],'中等',5,"$16.$ 设 $A,B$ 为两个随机事件，$A$ 与 $B$ 相互独立，已知 $P(A)=2P(B), P(A\\cup B)=\\frac{5}{8}$，则在 $A,B$ 至少有一个发生的条件下，$A,B$ 中恰有一个发生的概率为 $\\underline{\\qquad\\qquad}$","$\\frac{4}{5}$."),
qq('2025-数一-017','解答题',['不定积分'],'中等',10,"$17.$ （本题满分10分）计算 $\\int_0^1 \\frac{1}{(x+1)(x^2 - 2x + 2)} dx$。","$\\frac{3}{10}\\ln 2 + \\frac{1}{10}\\pi$。"),
qq('2025-数一-018','解答题',['多元函数微分','微分方程'],'较难',10,"$18.$ （本题满分10分）已知 $f(u)$ 在 $(0,+\\infty)$ 内具有二阶导数，记 $g(x,y)=f(\\frac{x}{y})$。若 $g$ 满足 $x^2g_{xx}+xyg_{xy}+y^2g_{yy}=1$，且 $g(x,x)=1$，$g_x|_{(x,x)}=\\frac{2}{x}$，求 $f(u)$。","$f(u)=\\frac{1}{2}\\ln^2 u + 2\\ln u + 1$。"),
qq('2025-数一-019','证明题',['导数与微分','中值定理'],'较难',10,"$19.$ （本题满分10分）设函数 $f(x)$ 在区间 $(a,b)$ 内可导。证明导函数 $f'(x)$ 在 $(a,b)$ 内严格单调增加的充要条件是：对 $(a,b)$ 内任意的 $x_1<x_2<x_3$ 有 $\\frac{f(x_2)-f(x_1)}{x_2-x_1}<\\frac{f(x_3)-f(x_2)}{x_3-x_2}$。","证明略。"),
qq('2025-数一-020','解答题',['曲线曲面积分'],'较难',10,"$20.$ （本题满分10分）设 $\\Sigma$ 是由直线 $\\begin{cases} x=0 \\\\ y=0 \\end{cases}$ 绕直线 $\\begin{cases} x=t \\\\ y=t \\\\ z=t \\end{cases}$ 旋转一周得到的曲面，$\\Sigma_1$ 是 $\\Sigma$ 介于 $x+y+z=0$ 与 $x+y+z=1$ 之间部分的外侧，计算 $I = \\iint_{\\Sigma_1} x dy dz + (y+1) dz dx + (z+2) dx dy$。","$\\frac{\\sqrt{2}}{4}\\pi - 1$。"),
qq('2025-数一-021','解答题',['特征值与特征向量','矩阵运算'],'较难',10,"$21.$ （本题满分10分）设矩阵 $A = \\begin{pmatrix} 0 & -1 & 2 \\\\ -1 & 0 & 2 \\\\ -1 & -1 & a \\end{pmatrix}$，已知1是$A$的特征多项式的重根。\n$(1)$ 求 $a$；\n$(2)$ 求所有满足 $A\\alpha=\\alpha+\\beta$，$A^2\\alpha=\\alpha+2\\beta$ 的非零列向量 $\\alpha,\\beta$。","$(1)$ $a=3$。\n$(2)$ $\\beta=(2a_3-a_1-a_2)\\begin{pmatrix}1\\\\1\\\\1\\end{pmatrix}$，$\\alpha$ 满足 $a_1+a_2\\neq 2a_3$。"),
qq('2025-数一-022','解答题',['随机变量及其分布','数理统计'],'较难',12,"$22.$ （本题满分12分）损失事件发生时，赔付额 $Y$ 与损失额 $X$ 的关系为 $Y=\\begin{cases}0,&X\\le 100\\\\X-100,&X>100\\end{cases}$，$X$ 的概率密度为 $f_X(x)=\\frac{2\\cdot 100^2}{(100+x)^3}(x>0)$。\n$(1)$ 求 $P\\{Y>0\\}$ 及 $EY$；\n$(2)$ 损失事件一年发生 $N\\sim P(8)$ 次，在 $N=n$ 条件下 $M\\sim B(n,p)$，$p=P\\{Y>0\\}$，求 $M$ 的概率分布。","$(1)$ $P\\{Y>0\\}=\\frac{1}{4}$，$EY=50$。\n$(2)$ $M\\sim P(2)$，$P\\{M=m\\}=\\frac{2^m}{m!}e^{-2}$。"),
]

for q in qs:
    with open(DATA / f"{q['question_id']}.json", 'w', encoding='utf-8') as f:
        json.dump(q, f, ensure_ascii=False, indent=2)

with open(IDX, 'r', encoding='utf-8') as f: idx = json.load(f)
cats = idx.setdefault('categories',{}).setdefault('数学一',{})
cats['2025'] = {'选择题':[f'2025-数一-{n:03d}' for n in range(1,11)],'填空题':[f'2025-数一-{n:03d}' for n in range(11,17)],'解答题':[f'2025-数一-{n:03d}' for n in range(17,23)]}
ki,di = idx.setdefault('knowledge_index',{}), idx.setdefault('difficulty_index',{})
for q in qs:
    for k in q['knowledge_points']: ki.setdefault(k,[]).append(q['question_id'])
    di.setdefault(q['difficulty'],[]).append(q['question_id'])
idx['knowledge_index']=ki; idx['difficulty_index']=di
total=sum(len(ids) for cd in cats.values() for yids in cd.values() for ids in (yids.values() if isinstance(yids,dict) else [yids]))
idx['metadata']['total_questions']=total
idx['metadata']['years_covered']=sorted(int(y) for y in cats['数学一'] if y.isdigit())
idx['metadata']['last_updated']=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
with open(IDX,'w',encoding='utf-8') as f: json.dump(idx,f,ensure_ascii=False,indent=2)
print(f'Written {len(qs)} files. Total: {total}')
