"""One-off import: 26李擂八套卷 卷八 (22 questions)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "storage/questions/simulations4"
INDEX_PATH = ROOT / "storage/questions/_index.json"
SOURCE = "import_lilei8_v8_user"
VOL = "卷八"
CAT = "26李擂八套卷"


def base(qno: int, qtype: str, question: str, answer: str, **extra) -> dict:
    qid = f"{CAT}-{VOL}-{qno:03d}"
    row = {
        "question_id": qid,
        "year": 2026,
        "category": CAT,
        "math_type": CAT,
        "volume": VOL,
        "question_type": qtype,
        "question_no": qno,
        "score": 5 if qtype in ("选择题", "填空题") else 10,
        "difficulty": extra.get("difficulty", "中等"),
        "knowledge_points": extra.get("knowledge_points", []),
        "tags": extra.get("tags", extra.get("knowledge_points", [])),
        "question": question,
        "options": extra.get("options", {}),
        "correct_option": extra.get("correct_option", ""),
        "standard_answer": extra.get("standard_answer", answer),
        "source": SOURCE,
        "_original_answer": "",
        "solution_steps": extra.get("solution_steps", []),
        "raw_question_text": question,
        "raw_answer_text": extra.get("standard_answer", answer),
    }
    return row


QUESTIONS: list[dict] = []

# --- 选择题 ---
QUESTIONS.append(
    base(
        1,
        "选择题",
        "设 $f(x)$ 是连续函数，$F(t)=\\displaystyle\\int_0^{t^2}dy\\int_{\\sqrt y}^{t}f(x)\\,dx$，$t>0$，则 $F'(t)=$",
        "A",
        correct_option="A",
        options={
            "A": "$t^2f(t)$",
            "B": "$tf(t)$",
            "C": "$\\displaystyle\\int_0^t xf(x)\\,dx$",
            "D": "$t\\displaystyle\\int_0^t f(x)\\,dx$",
        },
        knowledge_points=["二重积分", "变限积分"],
        tags=["二重积分", "变限积分", "求导"],
    )
)
QUESTIONS.append(
    base(
        2,
        "选择题",
        "函数 $y=f(x)$ 由方程 $|x|\\cos y+2y+e^y=1$ 确定，则 $f(x)$ 在 $x=0$ 处",
        "B",
        correct_option="B",
        options={
            "A": "不可导，不取极值",
            "B": "不可导，取极值",
            "C": "可导，不取极值",
            "D": "可导，取极值",
        },
        knowledge_points=["隐函数", "极值"],
    )
)
QUESTIONS.append(
    base(
        3,
        "选择题",
        "设有一木质球体浸没在水中，水的密度是球体的两倍，球体的半径为 $a$，现将球体下压到顶部距离水面 $2a$ 的位置从静止释放，球体在浮力作用下开始上浮，假设在球体上浮过程中水面的高度不变，球体的表面绝对光滑，并假设球体在上浮过程中只受到浮力和重力两个力的作用，则在球体上升到最高点时，其底部离开水面的高度为",
        "B",
        correct_option="B",
        options={"A": "$a$", "B": "$2a$", "C": "$3a$", "D": "$4a$"},
        knowledge_points=["物理应用", "能量守恒"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        4,
        "选择题",
        "设数列 $\\{x_n\\}$ 为方程 $e^{-x}=\\tan x$ 的第 $n$ 个正根，按照从小到大的顺序排列，则下列说法中错误的有几个：① 级数 $\\displaystyle\\sum_{n=1}^{\\infty}\\frac{(-1)^n}{x_n}$ 条件收敛；② 级数 $\\displaystyle\\sum_{n=1}^{\\infty}\\frac1{x_n^\\alpha}$ 收敛的充要条件是 $\\alpha>1$；③ 级数 $\\displaystyle\\sum_{n=1}^{\\infty}(-1)^n[x_n-(n-1)\\pi]$ 收敛。",
        "A",
        correct_option="A",
        options={"A": "$0$", "B": "$1$", "C": "$2$", "D": "$3$"},
        knowledge_points=["级数收敛", "方程根"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        5,
        "选择题",
        "设 $A,B$ 均为 $n$ 阶矩阵，$r(AB)<r(BA)$，则",
        "C",
        correct_option="C",
        options={
            "A": "$AB^*=O$",
            "B": "$B^*A=O$",
            "C": "$AB^*\\ne O$",
            "D": "$B^*A\\ne O$",
        },
        standard_answer=(
            "C。按题面条件四个选项不能唯一推出；若补充 $r(B)=n-1$，"
            "则可推出 $AB^*\\ne O$，对应 C。"
        ),
        knowledge_points=["矩阵秩", "伴随矩阵"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        6,
        "选择题",
        "已知 $A=\\begin{pmatrix}1&2&1\\\\ a&3&-4\\\\ 4&2a+3&-2\\end{pmatrix}$，$b=\\begin{pmatrix}1\\\\ 5\\\\ 3a+1\\end{pmatrix}$，若线性方程组 $Ax=b$ 有无穷多解，则 $a=$",
        "A",
        correct_option="A",
        options={"A": "$2$", "B": "$-2$", "C": "$\\displaystyle\\frac{19}{2}$", "D": "$-\\displaystyle\\frac{19}{2}$"},
        knowledge_points=["线性方程组", "无穷多解"],
    )
)
QUESTIONS.append(
    base(
        7,
        "选择题",
        "二次曲面 $2(x+y-2z)(3x-y+z)-3z^2=1$ 的类型是",
        "C",
        correct_option="C",
        options={"A": "椭球面", "B": "双曲柱面", "C": "双叶双曲面", "D": "单叶双曲面"},
        knowledge_points=["二次曲面"],
    )
)
QUESTIONS.append(
    base(
        8,
        "选择题",
        "某工厂生产的一批产品由 $400$ 件一等品和 $800$ 件二等品组成，现从中随机抽取 $5$ 件，用二项分布近似估计可以得到至少抽到两件一等品的概率约为",
        "A",
        correct_option="A",
        options={
            "A": "$\\displaystyle\\frac{131}{243}$",
            "B": "$\\displaystyle\\frac{125}{243}$",
            "C": "$\\displaystyle\\frac{119}{243}$",
            "D": "$\\displaystyle\\frac{113}{243}$",
        },
        knowledge_points=["二项分布", "概率近似"],
    )
)
QUESTIONS.append(
    base(
        9,
        "选择题",
        "设 $(X,Y)$ 服从二维正态分布 $N(0,0;1,4;0)$，则 $X$ 和 $XY^2$ 的相关系数为",
        "B",
        correct_option="B",
        options={
            "A": "$-\\displaystyle\\frac1{\\sqrt3}$",
            "B": "$\\displaystyle\\frac1{\\sqrt3}$",
            "C": "$-\\displaystyle\\frac1{\\sqrt2}$",
            "D": "$\\displaystyle\\frac1{\\sqrt2}$",
        },
        knowledge_points=["相关系数", "二维正态分布"],
    )
)
QUESTIONS.append(
    base(
        10,
        "选择题",
        "设一批零件的长度服从正态分布 $N(\\mu,\\sigma^2)$，其中 $\\mu$ 和 $\\sigma$ 均未知，现从中随机抽取 $36$ 个零件，测得样本均值 $\\overline x=50$ cm，样本标准差 $S=2.52$ cm，则 $\\mu$ 的置信度为 $0.98$ 的置信区间是（其中 $t_\\alpha(n)$ 表示自由度为 $n$ 的 $t$ 分布的上 $\\alpha$ 分位点）",
        "C",
        correct_option="C",
        options={
            "A": "$(50-0.42t_{0.02}(35),\\ 50+0.42t_{0.02}(35))$",
            "B": "$(50-0.21t_{0.02}(35),\\ 50+0.21t_{0.02}(35))$",
            "C": "$(50-0.42t_{0.01}(35),\\ 50+0.42t_{0.01}(35))$",
            "D": "$(50-0.21t_{0.01}(35),\\ 50+0.21t_{0.01}(35))$",
        },
        knowledge_points=["置信区间", "t分布"],
    )
)

# --- 填空题 ---
QUESTIONS.append(
    base(
        11,
        "填空题",
        "$\\displaystyle\\lim_{x\\to0^+}\\left(\\frac{x^x+1}{2}\\right)^{\\frac1{x\\ln(x+x^2)}}=\\_\\_\\_\\_\\_$",
        "$\\displaystyle\\sqrt e$",
        knowledge_points=["极限", "幂指函数"],
    )
)
QUESTIONS.append(
    base(
        12,
        "填空题",
        "设正项级数 $\\displaystyle\\sum_{n=1}^{\\infty}a_n$ 发散，数列 $\\{a_n\\}$ 单调递减，$S_n=\\displaystyle\\sum_{k=1}^{n}a_k$，则级数 $\\displaystyle\\sum_{n=1}^{\\infty}\\frac{n^2}{4+S_n}x^{2n+1}$ 的收敛半径为 $\\_\\_\\_\\_\\_$",
        "$1$",
        knowledge_points=["幂级数", "收敛半径"],
    )
)
QUESTIONS.append(
    base(
        13,
        "填空题",
        "曲面 $x^2+2y^2+z^2+xy=2$ 在 $x$ 轴和 $z$ 轴上截距均为 $2$ 的切平面方程为 $\\_\\_\\_\\_\\_$",
        "$2x+y+2z=4$",
        knowledge_points=["切平面", "曲面"],
    )
)
QUESTIONS.append(
    base(
        14,
        "填空题",
        "设 $\\Sigma$ 为空间区域 $\\{(x,y,z)\\mid |x|+|y|+z^2\\le1,\\ 0\\le z\\le1\\}$ 表面的外侧，则 $\\displaystyle\\iint_{\\Sigma}\\left[xy+\\ln(1-x^2+y^4)\\right]\\,dy\\,dz+\\left[yz+\\cos(x^4y)\\right]\\,dz\\,dx+z\\sin(x^3+y^3)\\,dx\\,dy=\\_\\_\\_\\_\\_$",
        "$\\displaystyle\\frac13$",
        knowledge_points=["高斯公式", "曲面积分"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        15,
        "填空题",
        "设 $3$ 阶矩阵 $A$ 满足 $(A+E)(A-E)(A+2E)=O$，且矩阵 $A+2E$ 的伴随矩阵的秩 $r[(A+2E)^*]=1$，则矩阵 $A^2+E$ 的伴随矩阵的迹 $\\operatorname{tr}[(A^2+E)^*]=\\_\\_\\_\\_\\_$",
        "$24$",
        knowledge_points=["伴随矩阵", "矩阵方程"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        16,
        "填空题",
        "设随机事件 $A,B,C$ 两两独立，$ABC=\\varnothing$，$P(A)=P(B)=\\frac12$，$P(C)=\\frac13$，则 $P(\\overline A\\cup B\\mid C)=\\_\\_\\_\\_\\_$",
        "$\\displaystyle\\frac12$",
        knowledge_points=["条件概率", "独立事件"],
    )
)

# --- 解答题 / 证明题 ---
QUESTIONS.append(
    base(
        17,
        "解答题",
        "求反常积分 $\\displaystyle\\int_0^{+\infty}\\frac{\\arctan x}{(1+x)^3}\\,dx$。",
        "$\\displaystyle\\int_0^{+\infty}\\frac{\\arctan x}{(1+x)^3}\\,dx=\\left[-\\frac{\\arctan x}{2(1+x)^2}\\right]_0^{+\infty}+\\frac12\\int_0^{+\infty}\\frac{dx}{(1+x)^2(1+x^2)}=\\frac14$。",
        knowledge_points=["反常积分", "分部积分"],
    )
)
QUESTIONS.append(
    base(
        18,
        "解答题",
        "设 $L:y=y(x)$，$x>0$ 是过点 $(1,0)$ 的一条光滑曲线，$P$ 是曲线 $L$ 上任意一点，已知曲线 $L$ 在点 $P$ 处的法线在 $y$ 轴上的截距等于点 $P$ 到坐标原点的距离，则\n(I) 求曲线 $y=y(x)$ 的方程；\n(II) 过点 $P$ 作曲线 $L$ 的切线，该切线与两个坐标轴围成一个三角形，求使得该三角形绕 $y$ 轴旋转一周所得的旋转体体积最小时 $P$ 的坐标。",
        "(I) $y=\\frac{x^2-1}{2}$。(II) $P=\\left(\\frac1{\\sqrt2},-\\frac14\\right)$。",
        knowledge_points=["微分方程", "旋转体体积"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        19,
        "解答题",
        "设有向闭合曲线 $L$ 为椭圆 $x^2+xy+2y^2=1$，方向沿逆时针，求曲线积分 $\\displaystyle\\oint_L\\frac{y\\,dx-x\\,dy}{2x^2+xy+y^2}$。",
        "$\\displaystyle\\oint_L\\frac{y\\,dx-x\\,dy}{2x^2+xy+y^2}=-\\frac{4\\pi}{\\sqrt7}$。",
        knowledge_points=["曲线积分", "格林公式"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        20,
        "证明题",
        "设 $n$ 为正整数，证明：当 $0\\le x\\le n$ 时，恒有 $\\displaystyle x-\\frac{x^3}{3n}\\le n\\int_0^{\\frac xn}(1-t)^ne^{nt}\\,dt$。",
        "令 $u=nt$，则 $n\\int_0^{\\frac xn}(1-t)^ne^{nt}\\,dt=\\int_0^x\\left(1-\\frac un\\right)^ne^u\\,du$。对 $0\\le u\\le n$，令 $s=\\frac un$，有 $e^s(1-s)\\ge(1+s)(1-s)=1-s^2$。因而 $\\left(1-\\frac un\\right)^ne^u=\\left[e^{\\frac un}\\left(1-\\frac un\\right)\\right]^n\\ge\\left(1-\\frac{u^2}{n^2}\\right)^n\\ge1-\\frac{u^2}{n}$。所以 $n\\int_0^{\\frac xn}(1-t)^ne^{nt}\\,dt\\ge\\int_0^x\\left(1-\\frac{u^2}{n}\\right)\\,du=x-\\frac{x^3}{3n}$。",
        knowledge_points=["积分不等式", "证明题"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        21,
        "解答题",
        "设 $A=\\begin{pmatrix}-1&b&a\\\\ -3&2&2\\\\ -1&1&1\\end{pmatrix}$ 相似于 $B=\\begin{pmatrix}1&0&0\\\\ 1&1&0\\\\ 0&0&0\\end{pmatrix}$。\n(I) 求 $a,b$；\n(II) 求一个可逆矩阵 $P$，使得 $P^{-1}AP=B$。",
        "(I) $a=b=1$。(II) $P=\\begin{pmatrix}0&1&0\\\\ 1&1&-1\\\\ 0&1&1\\end{pmatrix}$，则 $P^{-1}AP=B$。",
        knowledge_points=["矩阵相似", "特征值"],
        difficulty="困难",
    )
)
QUESTIONS.append(
    base(
        22,
        "解答题",
        "设 $(X,Y)$ 的概率密度为 $f(x,y)=\\begin{cases} e^{-x-y},&x\\ge0,\\ y\\ge0,\\\\ 0,&\\text{其他}, \\end{cases}$ 令 $Z=X+Y$，$U=\\begin{cases} X+Y,&Y>X,\\\\ -X-Y,&Y\\le X, \\end{cases}$\n(I) 求 $U$ 的概率密度；\n(II) 判断 $Z$ 和 $U$ 是否不相关，是否独立。",
        "(I) $f_U(u)=\\frac{|u|}{2}e^{-|u|}$（$u\\ne0$）。(II) $Z$ 与 $U$ 不相关但不独立。",
        knowledge_points=["概率密度", "独立性"],
        difficulty="困难",
    )
)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for row in QUESTIONS:
        path = OUT / f"{row['question_id']}.json"
        path.write_text(json.dumps(row, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    vol8 = {
        "选择题": [f"{CAT}-{VOL}-{i:03d}" for i in range(1, 11)],
        "填空题": [f"{CAT}-{VOL}-{i:03d}" for i in range(11, 17)],
        "解答题": [f"{CAT}-{VOL}-{i:03d}" for i in (17, 18, 19, 21, 22)],
        "证明题": [f"{CAT}-{VOL}-020"],
    }
    idx["categories"][CAT]["卷八"] = vol8
    INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(QUESTIONS)} questions to {OUT}")


if __name__ == "__main__":
    main()
