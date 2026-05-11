"""
示例题目数据 — 用于演示系统功能

⚠️ 重要声明：这些题目为系统演示用途，非真实考研真题。
正式使用时请替换为真实真题数据。
"""

SEED_QUESTIONS = [
    {
        "year": 2024,
        "category": "数学一",
        "question_type": "解答题",
        "knowledge_points": [
            "二重积分",
            "极坐标换元"
        ],
        "difficulty": "中等",
        "score": 11,
        "question": "计算二重积分\n\n$$\\iint_D (x^2 + y^2) \\, dxdy$$\n\n其中 $D$ 是由 $x^2 + y^2 = 2x$ 和 $x^2 + y^2 = 1$ 所围成的环形区域在第一象限的部分。",
        "standard_answer": "## 标准解答\n\n### 步骤一【3分】\n区域 $D$ 边界为 $x^2 + y^2 = 2x$（即 $(x-1)^2 + y^2 = 1$）和 $x^2 + y^2 = 1$。\n采用极坐标变换：$x = r\\cos\\theta$, $y = r\\sin\\theta$，则 $dxdy = r\\, dr d\\theta$。\n\n### 步骤二【4分】\n边界 $x^2 + y^2 = 1$ 即 $r = 1$。\n边界 $x^2 + y^2 = 2x$ 即 $r = 2\\cos\\theta$。\n在第一象限，$\\theta \\in [0, \\pi/2]$。\n两边界相交：$1 = 2\\cos\\theta \\Rightarrow \\cos\\theta = 1/2 \\Rightarrow \\theta = \\pi/3$。\n当 $\\theta \\in [0, \\pi/3]$ 时 $r \\in [1, 2\\cos\\theta]$。\n当 $\\theta \\in [\\pi/3, \\pi/2]$ 时区域不在第一象限。\n\n### 步骤三【4分】\n\\begin{align*}\n\\iint_D (x^2 + y^2) \\, dxdy\n&= \\int_0^{\\pi/3} \\int_1^{2\\cos\\theta} r^2 \\cdot r \\, dr d\\theta \\\\\n&= \\int_0^{\\pi/3} \\left[\\frac{r^4}{4}\\right]_1^{2\\cos\\theta} \\, d\\theta \\\\\n&= \\int_0^{\\pi/3} \\left(4\\cos^4\\theta - \\frac{1}{4}\\right) \\, d\\theta \\\\\n&= \\frac{5\\pi}{12} - \\frac{3\\sqrt{3}}{8}\n\\end{align*}\n\n### 最终答案\n$$\\boxed{\\frac{5\\pi}{12} - \\frac{3\\sqrt{3}}{8}}$$",
        "solution_steps": [
            "极坐标变换，确定积分区域",
            "求出两边界交点，分区间确定积分限",
            "逐层积分，化简结果"
        ],
        "common_mistakes": [
            "Jacobian 行列式遗漏（忘记乘 r）",
            "积分限确定错误",
            "未考虑第一象限限制"
        ],
        "tags": [
            "高数",
            "积分",
            "极坐标"
        ]
    },
    {
        "year": 2024,
        "category": "数学一",
        "question_type": "选择题",
        "knowledge_points": [
            "极限",
            "洛必达法则"
        ],
        "difficulty": "基础",
        "score": 4,
        "question": "计算极限\n\n$$\\lim_{x \\to 0} \\frac{\\sin x - x}{x^3}$$",
        "standard_answer": "## 标准解答\n\n由泰勒展开 $\\sin x = x - \\frac{x^3}{6} + O(x^5)$，得\n$$\\lim_{x \\to 0} \\frac{\\sin x - x}{x^3} = \\lim_{x \\to 0} \\frac{-x^3/6 + O(x^5)}{x^3} = -\\frac{1}{6}$$\n\n最终答案：$$\\boxed{-\\frac{1}{6}}$$",
        "solution_steps": [
            "泰勒展开 sin x",
            "化简求极限"
        ],
        "common_mistakes": [
            "直接用洛必达求导3次（虽然可做但容易算错）",
            "忘记负号"
        ],
        "tags": [
            "高数",
            "极限"
        ]
    },
    {
        "year": 2023,
        "category": "数学一",
        "question_type": "证明题",
        "knowledge_points": [
            "中值定理",
            "定积分"
        ],
        "difficulty": "较难",
        "score": 12,
        "question": "设函数 $f(x)$ 在 $[0,1]$ 上连续，且满足\n$$\\int_0^1 f(x)\\,dx = \\int_0^1 x f(x)\\,dx = 0$$\n证明：存在两个不同的点 $\\xi_1, \\xi_2 \\in (0,1)$，使得 $f(\\xi_1) = f(\\xi_2) = 0$。",
        "standard_answer": "## 标准解答\n\n### 步骤一【3分】\n设 $F(x) = \\int_0^x f(t)\\,dt$，则 $F'(x) = f(x)$，且 $F(0) = 0$。\n由 $\\int_0^1 f(x)\\,dx = 0$ 知 $F(1) = 0$。\n\n### 步骤二【4分】\n由 $\\int_0^1 x f(x)\\,dx = 0$，分部积分：\n$$\\int_0^1 x f(x)\\,dx = [xF(x)]_0^1 - \\int_0^1 F(x)\\,dx = -\\int_0^1 F(x)\\,dx = 0$$\n故 $\\int_0^1 F(x)\\,dx = 0$。\n\n### 步骤三【3分】\n由积分中值定理，存在 $c \\in (0,1)$ 使得 $F(c) = 0$。\n于是 $F(0) = F(c) = F(1) = 0$。\n\n### 步骤四【2分】\n在 $[0,c]$ 和 $[c,1]$ 上分别应用 Rolle 定理，存在\n$\\xi_1 \\in (0,c)$, $\\xi_2 \\in (c,1)$ 使得 $F'(\\xi_1) = F'(\\xi_2) = 0$，\n即 $f(\\xi_1) = f(\\xi_2) = 0$ 且 $\\xi_1 \\neq \\xi_2$。证毕。",
        "solution_steps": [
            "构造辅助函数 F(x) = ∫₀ˣ f(t) dt",
            "分部积分处理第二个条件",
            "积分中值定理找出内部零点",
            "Rolle 定理应用于两个子区间"
        ],
        "common_mistakes": [
            "未说明 ξ₁ ≠ ξ₂",
            "分部积分符号错误",
            "未验证 Rolle 定理应用条件"
        ],
        "tags": [
            "高数",
            "中值定理",
            "证明"
        ]
    },
    {
        "year": 2024,
        "category": "数学一",
        "question_type": "选择题",
        "knowledge_points": [
            "特征值",
            "矩阵"
        ],
        "difficulty": "中等",
        "score": 4,
        "question": "设 $A$ 是三阶实对称矩阵，其特征值为 $\\lambda_1 = 1$, $\\lambda_2 = 2$, $\\lambda_3 = 3$，对应的特征向量分别为 $\\alpha_1, \\alpha_2, \\alpha_3$，且 $\\|\\alpha_i\\| = 1$。\n则 $A$ 的迹 $\\text{tr}(A)$ 和行列式 $|A|$ 分别为：",
        "standard_answer": "## 标准解答\n\n对于实对称矩阵，迹等于特征值之和，行列式等于特征值之积：\n$$\\text{tr}(A) = \\lambda_1 + \\lambda_2 + \\lambda_3 = 1 + 2 + 3 = 6$$\n$$|A| = \\lambda_1 \\cdot \\lambda_2 \\cdot \\lambda_3 = 1 \\times 2 \\times 3 = 6$$\n\n最终答案：$$\\boxed{\\text{tr}(A) = 6,\\ |A| = 6}$$",
        "solution_steps": [
            "回顾迹和行列式的特征值表达",
            "代入计算"
        ],
        "common_mistakes": [
            "混淆迹和行列式的定义",
            "忘记特征向量的单位化条件不影响迹和行列式"
        ],
        "tags": [
            "线代",
            "特征值"
        ]
    }
]
