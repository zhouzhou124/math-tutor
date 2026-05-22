"""Import 26合工大超越卷（数学一）第三套 into the question bank."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.question_db import QuestionDB, make_question_id

MATH_TYPE = "26合工大超越"
VOLUME = "卷三"

MC = [
    {
        "no": 1, "difficulty": "中等",
        "knowledge_points": ["极限", "泰勒展开"],
        "question": r"$1.$ 设 $f(x)$ 在点 $x=0$ 的某邻域内二阶可导，且 $\lim_{x\to 0} \frac{\sin x + x f(x)}{x^3} = \frac{1}{3}$，若 $\frac{f(x)}{1+x} = a + bx + cx^2 + o(x^2)$，则 "
                   r"$(A)$ $a=1,b=-1,c=\frac{1}{2}$ $(B)$ $a=-1,b=1,c=-\frac{1}{2}$ $(C)$ $a=1,b=1,c=-\frac{1}{2}$ $(D)$ $a=-1,b=1,c=\frac{1}{2}$",
        "options": {"A": r"$a=1,b=-1,c=\frac{1}{2}$", "B": r"$a=-1,b=1,c=-\frac{1}{2}$", "C": r"$a=1,b=1,c=-\frac{1}{2}$", "D": r"$a=-1,b=1,c=\frac{1}{2}$"},
        "correct_option": "A",
    },
    {
        "no": 2, "difficulty": "中等",
        "knowledge_points": ["函数性质", "有界性"],
        "question": r"$2.$ 下列命题正确的个数为 "
                   r"① $f(x)=\int_0^x \frac{x}{\cos t} dt$ 在 $(0,+\infty)$ 内有界；"
                   r"② 在 $(-\infty,+\infty)$ 上连续的周期函数 $f(x)$ 一定有界；"
                   r"③ 若 $f(x)$ 在 $(a,b)$ 内可导，且导函数有界，则 $f(x)$ 在 $(a,b)$ 内一定有界；"
                   r"④ 若 $f(x)$ 在 $[0,+\infty)$ 内可导，且 $\lim_{x\to+\infty} f'(x)=0$，则 $f(x)$ 在 $[0,+\infty)$ 内有界。"
                   r"$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_option": "C",
    },
    {
        "no": 3, "difficulty": "中等",
        "knowledge_points": ["多元函数微分学", "全微分"],
        "question": r"$3.$ 设 $f(x,y)$ 为可微函数，$f(x^2, e^x-1)=xe^x$，$f(\ln x, x-1)=(1-x)^2$，则 $df(0,0)=$ "
                   r"$(A)$ $dy$ $(B)$ $-dx+dy$ $(C)$ $dx-dy$ $(D)$ $dx+dy$",
        "options": {"A": r"$dy$", "B": r"$-dx+dy$", "C": r"$dx-dy$", "D": r"$dx+dy$"},
        "correct_option": "B",
    },
    {
        "no": 4, "difficulty": "中等",
        "knowledge_points": ["曲线积分", "格林公式"],
        "question": r"$4.$ 设曲线积分 $\int_L \frac{(ax+by)dx - (cx+dy)dy}{x^2+2y^2}$ 在任何不包围原点，也不经过原点的有向闭曲线 $C$ 上积分恒等于0，则 $a,b,c,d$ 满足的关系为 "
                   r"$(A)$ $2a=d, b=c$ $(B)$ $-2a=d, b=c$ $(C)$ $a=d, b=2c$ $(D)$ $a=-d, b=2c$",
        "options": {"A": r"$2a=d, b=c$", "B": r"$-2a=d, b=c$", "C": r"$a=d, b=2c$", "D": r"$a=-d, b=2c$"},
        "correct_option": "A",
    },
    {
        "no": 5, "difficulty": "中等",
        "knowledge_points": ["矩阵", "合同"],
        "question": r"$5.$ 设 $A$ 为3阶非奇异矩阵，且 $A^{-1}=3E-A$，其中 $E$ 为3阶单位矩阵，则与矩阵 $(A-E)^{\mathrm{T}}(A-E)$ 合同的是 "
                   r"$(A)$ $\begin{pmatrix} 0 & 0 \\ 0 & 1 \end{pmatrix}$ $(B)$ $\begin{pmatrix} 0 & 1 \\ 1 & 1 \end{pmatrix}$ $(C)$ $\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$ $(D)$ $\begin{pmatrix} 1 & 1 \\ 1 & 1 \end{pmatrix}$",
        "options": {"A": r"$\begin{pmatrix}0&0\\0&1\end{pmatrix}$", "B": r"$\begin{pmatrix}0&1\\1&1\end{pmatrix}$", "C": r"$\begin{pmatrix}1&0\\0&1\end{pmatrix}$", "D": r"$\begin{pmatrix}1&1\\1&1\end{pmatrix}$"},
        "correct_option": "B",
    },
    {
        "no": 6, "difficulty": "较难",
        "knowledge_points": ["特征值", "线性方程组"],
        "question": r"$6.$ 已知3阶实对称矩阵 $A$ 的秩 $r(A)=1$，$\alpha_1=(1,-1,1)^{\mathrm{T}}$ 是 $A$ 的属于特征值 $\lambda_1=\frac{1}{2}$ 的特征向量，$k_1,k_2$ 为任意常数，则非齐次线性方程组 $Ax=\alpha_1$ 的通解是 "
                   r"$(A)$ $k_1(1,1,0)^{\mathrm{T}}+k_2(1,0,-1)^{\mathrm{T}}+(1,-1,1)^{\mathrm{T}}$ "
                   r"$(B)$ $k_1(1,0,-1)^{\mathrm{T}}+k_2(-1,1,2)^{\mathrm{T}}+(\frac{1}{2},-\frac{1}{2},\frac{1}{2})^{\mathrm{T}}$ "
                   r"$(C)$ $k_1(1,1,0)^{\mathrm{T}}+k_2(1,0,1)^{\mathrm{T}}+(2,-2,2)^{\mathrm{T}}$ "
                   r"$(D)$ $k_1(1,1,0)^{\mathrm{T}}+k_2(-1,1,2)^{\mathrm{T}}+(2,-2,2)^{\mathrm{T}}$",
        "options": {"A": r"$k_1(1,1,0)^T+k_2(1,0,-1)^T+(1,-1,1)^T$", "B": r"$k_1(1,0,-1)^T+k_2(-1,1,2)^T+(\frac12,-\frac12,\frac12)^T$", "C": r"$k_1(1,1,0)^T+k_2(1,0,1)^T+(2,-2,2)^T$", "D": r"$k_1(1,1,0)^T+k_2(-1,1,2)^T+(2,-2,2)^T$"},
        "correct_option": "D",
    },
    {
        "no": 7, "difficulty": "中等",
        "knowledge_points": ["矩阵", "秩"],
        "question": r"$7.$ 设 $A$ 为 $3\times 2$ 矩阵，$B$ 为 $2\times 3$ 矩阵，且 $r(AB)=2$，$(AB)^2=AB$，则下列说法中一定成立的有 "
                   r"① $BAB=B$；② $ABA=A$；③ $BA=\begin{pmatrix} 1 & 0 \\ 0 & 1 \end{pmatrix}$；④ $AB=\begin{pmatrix} 1 & 0 & 0 \\ 0 & 1 & 0 \\ 0 & 0 & 0 \end{pmatrix}$。"
                   r"$(A)$ 1 $(B)$ 2 $(C)$ 3 $(D)$ 4",
        "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
        "correct_option": "B",
    },
    {
        "no": 8, "difficulty": "中等",
        "knowledge_points": ["概率", "条件概率"],
        "question": r"$8.$ 设随机变量 $(X,Y)$ 的概率密度 $f(x,y)=\begin{cases} x+y, & 0<x<1,0<y<1 \\ 0, & \text{其他} \end{cases}$。"
                   r"记 $A=\{X\ge \frac{1}{2}\}$，$B=\{Y\ge \frac{1}{4}\}$，$C=\{X+Y\le 1\}$，则 $P(AB\cup C \mid AC)=$ "
                   r"$(A)$ $\frac{7}{8}$ $(B)$ $\frac{3}{4}$ $(C)$ $\frac{29}{40}$ $(D)$ $\frac{29}{80}$",
        "options": {"A": r"$\frac{7}{8}$", "B": r"$\frac{3}{4}$", "C": r"$\frac{29}{40}$", "D": r"$\frac{29}{80}$"},
        "correct_option": "A",
    },
    {
        "no": 9, "difficulty": "中等",
        "knowledge_points": ["多维随机变量", "变量变换"],
        "question": r"$9.$ 设随机变量 $(X,Y)$ 的概率密度为 $f(x,y)$，令 $U=-Y$，$V=2X+Y$，则 $(U,V)$ 的概率密度为 "
                   r"$(A)$ $\frac{1}{2}f(\frac{u+v}{2},-u)$ $(B)$ $\frac{1}{2}f(\frac{u+v}{2},u)$ $(C)$ $f(\frac{u+v}{2},-u)$ $(D)$ $f(\frac{u+v}{2},u)$",
        "options": {"A": r"$\frac{1}{2}f(\frac{u+v}{2},-u)$", "B": r"$\frac{1}{2}f(\frac{u+v}{2},u)$", "C": r"$f(\frac{u+v}{2},-u)$", "D": r"$f(\frac{u+v}{2},u)$"},
        "correct_option": "A",
    },
    {
        "no": 10, "difficulty": "较难",
        "knowledge_points": ["数理统计", "分布"],
        "question": r"$10.$ 设随机变量 $X_1$ 与 $X_2$ 相互独立，$X_1\sim N(0,1)$，$X_2\sim N(0,1)$。记 $T=\frac{X_1-X_2}{|X_1+X_2|}$，给定 $a(0<a<0.5)$，常数 $C$ 满足 $P(T>C)=a$，则 $P(\frac{1}{T^2}>C^2)=$ "
                   r"$(A)$ $a$ $(B)$ $1-a$ $(C)$ $2a$ $(D)$ $1-2a$",
        "options": {"A": r"$a$", "B": r"$1-a$", "C": r"$2a$", "D": r"$1-2a$"},
        "correct_option": "C",
    },
]

FB = [
    {"no": 11, "difficulty": "中等", "knowledge_points": ["旋转体体积"],
     "question": r"$11.$ 曲线 $x^2+y^2=|x|-|y|$ 围成的区域绕 $y$ 轴旋转一周形成的旋转体体积是 $\underline{\qquad\qquad}$",
     "standard_answer": r"$\frac{\pi}{2}$"},
    {"no": 12, "difficulty": "中等", "knowledge_points": ["方向导数", "条件极值"],
     "question": r"$12.$ 函数 $f(x,y,z)$ 为 $u=3x^2+4y^3-9z^2$ 在点 $(x,y,z)$ 处沿 $\mathbf{n}=(1,1,1)$ 的方向导数，则 $f(x,y,z)$ 在条件 $x^2+2y^2+z^2=1$ 下的最大值为 $\underline{\qquad\qquad}$",
     "standard_answer": r"$6$"},
    {"no": 13, "difficulty": "较难", "knowledge_points": ["曲面积分"],
     "question": r"$13.$ 设 $\Sigma$ 为曲面 $z=\sqrt{x^2+y^2}$（$0\le z\le 1$）位于第一卦限部分，取下侧，$f(t)$ 为非常量连续函数，则曲面积分 $I=\iint_{\Sigma} \frac{[1+yf(z)]dy dz + [1-xf(z)]dz dx}{1+\sqrt{x^2+y^2}} = \underline{\qquad\qquad}$",
     "standard_answer": r"$0$"},
    {"no": 14, "difficulty": "中等", "knowledge_points": ["反常积分"],
     "question": r"$14.$ $\int_{-\infty}^{0} \frac{e^{\frac{z}{\xi}}}{1+e^{\frac{z}{\xi}}+e^{\frac{z}{\eta}}} d\xi = \underline{\qquad\qquad}$",
     "standard_answer": r"$\ln\frac{1+e^{\frac{z}{\eta}}}{1+e^{\frac{z}{\xi}}}$"},
    {"no": 15, "difficulty": "中等", "knowledge_points": ["行列式", "矩阵"],
     "question": r"$15.$ 设 $\alpha,\beta,\gamma$ 为三维列向量，且 $\alpha,\beta,\gamma$ 线性无关，记 $A=(\alpha,\beta,\gamma)$，$B=(2\alpha+3\gamma,3\alpha+\beta,\alpha+2\gamma)$，已知 $|A^{-1}+B^{-1}|=6$，则 $|A|=\underline{\qquad\qquad}$",
     "standard_answer": r"$\frac{1}{3}$"},
    {"no": 16, "difficulty": "中等", "knowledge_points": ["数字特征", "泊松分布"],
     "question": r"$16.$ 设随机变量 $X_1,X_2,\dots,X_n$ 相互独立，且 $X_i\sim P(\lambda_i)$，$\lambda_i>0$，$i=1,2,\dots,n$。已知 $P\{\sum_{i=1}^n X_i \ge 1\}=1-e^{-1}$，则期望 $E(2^{X_1})=\underline{\qquad\qquad}$",
     "standard_answer": r"$e^{\lambda_1} \cdot e^{-1+\sum_{i=1}^n \lambda_i}$"},
]

FR = [
    {"no": 17, "difficulty": "中等", "score": 10, "knowledge_points": ["极限"],
     "question": r"$17.$ (本题满分10分) 求极限 $\lim_{n\to\infty} n^2[ (1+\frac{1}{n+1})^{n+1} - (1+\frac{1}{n})^n ]$。",
     "standard_answer": r"$\frac{1}{2}e$"},
    {"no": 18, "difficulty": "较难", "score": 12, "knowledge_points": ["微分方程", "曲线积分"],
     "question": r"$18.$ (本题满分12分) 设 $f(x)$ 具有二阶连续导数，$f(0)=1$，$f'(0)=\frac{1}{2}$。可微函数 $u(x,y)$ 的全微分为 $du(x,y)=[f'(x+y)-e^{x+y}]dx + [\int_0^{x+y} f(t)dt + 2y]dy$。\n$(I)$ 求 $f(x)$；\n$(II)$ 求 $u(x,y)$；\n$(III)$ 计算曲线积分 $I=\int_{(0,0)}^{(1,1)} [f'(x+y)-e^{x+y}]dx + [\int_0^{x+y} f(t)dt + 2y]dy$。",
     "standard_answer": r"(I) $f(x)=e^{\frac{x}{2}}$\n(II) $u(x,y)=e^{\frac{x+y}{2}} - e^{x+y} + y^2 + C$\n(III) $I = e - e^2 + 1$"},
    {"no": 19, "difficulty": "较难", "score": 12, "knowledge_points": ["无穷级数"],
     "question": r"$19.$ (本题满分12分) 讨论级数 $\sum_{n=1}^\infty \frac{1}{n^p \ln^q(n+1)}$ 的敛散性，其中 $p,q$ 为正实数参数。",
     "standard_answer": r"当 $p>1$ 时收敛；当 $p=1$ 且 $q>1$ 时收敛；当 $p<1$ 或 $p=1$ 且 $q\le 1$ 时发散"},
    {"no": 20, "difficulty": "中等", "score": 12, "knowledge_points": ["不等式证明"],
     "question": r"$20.$ (本题满分12分) 已知当 $x\in(0,+\infty)$ 时，$(1+ax)\ln(1+x) > x$ 恒成立，求常数 $a$ 的取值范围。",
     "standard_answer": r"$a \ge \frac{1}{2}$"},
    {"no": 21, "difficulty": "较难", "score": 12, "knowledge_points": ["矩阵方程", "二次型"],
     "question": r"$21.$ (本题满分12分) 设 $A=\begin{pmatrix} 1 & -1 \\ 1 & 1 \\ a & b \end{pmatrix}$，$C=\begin{pmatrix} 1 & 1 & a \\ 1 & 2 & 1 \\ a & 1 & 1 \end{pmatrix}$。\n$(I)$ 求参数 $a,b$，使得存在矩阵 $B$，满足 $AB=C$。\n$(II)$ 求矩阵 $B$。\n$(III)$ 令 $x=(x_1,x_2)^{\mathrm{T}}$，求二次型 $f=x^{\mathrm{T}}BAx$ 的正负惯性指数。",
     "standard_answer": r"(I) $a=1$，$b=0$\n(II) $B = \begin{pmatrix} 1 & 1 & 1 \\ 0 & 1 & 0 \end{pmatrix}$\n(III) 正惯性指数为2，负惯性指数为0"},
    {"no": 22, "difficulty": "较难", "score": 12, "knowledge_points": ["多维随机变量", "协方差"],
     "question": r"$22.$ (本题满分12分) 设随机变量 $X$ 与 $Y$ 相互独立，$X$ 服从区间 $[0,2]$ 上的均匀分布，$Y$ 服从参数为1的指数分布，令 $Z=\begin{cases} Y, & 0\le X\le 1 \\ X, & 1<X\le 2 \end{cases}$。\n$(I)$ 求 $Z$ 的概率密度；\n$(II)$ 求协方差 $\operatorname{Cov}(X,Z)$。",
     "standard_answer": r"(I) $f_Z(z) = \begin{cases} \frac{1}{2}e^{-z} + \frac{1}{2}, & 0<z<1 \\ \frac{1}{2}e^{-z}, & z\ge 1 \\ 0, & z\le 0 \end{cases}$\n(II) $\operatorname{Cov}(X,Z) = -\frac{1}{4}$"},
]


def main():
    db = QuestionDB()
    ok = fail = 0
    all_questions = []

    for q in MC:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026, "category": MATH_TYPE,
            "question_type": "选择题", "question_no": q["no"], "score": 5,
            "difficulty": q["difficulty"], "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"], "question": q["question"],
            "options": q["options"], "correct_option": q["correct_option"],
            "standard_answer": q["correct_option"], "source": "import_hegongda_v3",
            "solution_steps": [], "volume": VOLUME,
        })
    for q in FB:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026, "category": MATH_TYPE,
            "question_type": "填空题", "question_no": q["no"], "score": 5,
            "difficulty": q["difficulty"], "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"], "question": q["question"],
            "standard_answer": q["standard_answer"], "source": "import_hegongda_v3",
            "solution_steps": [], "options": {}, "volume": VOLUME,
        })
    for q in FR:
        qid = make_question_id(2026, MATH_TYPE, q["no"], VOLUME)
        all_questions.append({
            "question_id": qid, "year": 2026, "category": MATH_TYPE,
            "question_type": "解答题", "question_no": q["no"], "score": q["score"],
            "difficulty": q["difficulty"], "knowledge_points": q["knowledge_points"],
            "tags": q["knowledge_points"], "question": q["question"],
            "standard_answer": q["standard_answer"], "source": "import_hegongda_v3",
            "solution_steps": [], "options": {}, "volume": VOLUME,
        })

    for q in all_questions:
        try:
            result = db.insert(q)
            if result.get("success"): ok += 1
            else: fail += 1; print(f"  FAIL: {q['question_id']}")
        except Exception as e: fail += 1; print(f"  ERROR: {e}")

    print(f"Done: {ok} imported, {fail} failed (total {len(all_questions)})")

if __name__ == "__main__": main()
