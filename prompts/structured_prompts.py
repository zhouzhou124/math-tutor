"""
Structured output prompts for Phase 1 dual-stack LLM pipeline.

These prompts ask the LLM to output pure JSON with separated text/latex blocks,
eliminating the fragile regex-parse-markdown step.
"""

from prompts.system_prompts import CORE_MATH_SEMANTIC_PROMPT, _SAFE_BASE

QUESTION_TYPE_SOLUTION_VIEW_RULES = r"""
# 题型化标准答案展示建议

选择题：输出 answer、core_reason、calculation_steps、option_analysis、conclusion；不要长篇步骤化，不要 raw LaTeX。
填空题：输出 answer、calculation_steps、answer_form_note、conclusion；重点说明等价形式。
解答题：输出 steps，每步包含 goal/reason/blocks/conclusion；短公式写 inline，成组公式用 equation_group。
证明题：输出 proof_goal、known_conditions、proof_steps、conclusion；强调逻辑关系。

标准答案展示格式：
1. text block 只能写中文解释和 inline math \( ... \)，不要混入 display 公式。
2. display formula 必须单独放 latex_display / block latex，不要把中文句子放进公式。
3. 不要输出孤立的 A=、C=、y=、I_1=、I_2=，必须与后续公式在同一块。
4. 积分微分必须写 dx\,dy 或 \,dx\,dy，不要写 dxdy、dx dy。
5. 变量下标必须写 X_{{10}}，不要写 X_\{{10\}} 或 X_[10]。
6. 无穷必须写 \infty，不要写 \infy 或 \lnfty。
7. 极限必须写 \lim_{{x\to0}}，不要写 \lim_x\to0。
8. goal 不得与步骤 label 同义重复（label 已是「步骤N：…」时，goal 写具体操作，不要复读标题）。
9. reason 只写文字依据；display 公式放 blocks，禁止在 reason 内写「关键变形为」或 \\begin{cases}。
10. conclusion 只写本步短结论；若 blocks 已含该公式，conclusion 留空或只写一句中文，不要重复 display。
11. 短结论公式写在 conclusion 内时，不要再单独重复 latex_display。
12. final_answer 只写最终答案，不要包含完整过程。
13. text 中数学表达必须写 \( ... \)，不要输出裸 X_i、u_n、p=...、\dfrac。
14. cases 每行只用 \\ 换行，不要使用 [2mm]、\\[2mm] 或其他行距残片。
15. 选择题必须分开输出 core_reason、calculation_steps、option_analysis、conclusion，不要把步骤和选项分析混在一个字段里。
16. 选择题必须输出 answer、core_reason、calculation_steps、option_analysis、conclusion；option_analysis 必须是数组或按 A/B/C/D 分开的对象，conclusion 只写“故选 X”。
17. 填空题必须输出 answer、key_conditions、calculation_steps、answer_form_note、conclusion；answer 只写最终填空答案，不要塞完整解析，等价形式写入 answer_form_note。
18. text 块中禁止出现裸 TeX 命令：不能写 frac、int、lim、ln、sin、cos、Rightarrow 等不带反斜杠的命令名。必须写成 \\( \\frac{...}{...} \\) 或放入 latex_display 块。
19. text 块中禁止出现 \\begin、\\end、\\left、\\right 等环境标记，这些必须放在 latex_display 块中。
20. 不要使用 @@MATH\\d+@@ 占位符，直接输出完整公式。
21. 微分符号 dx、dy、dt 必须紧跟积分号或用 \\, 间距，不要写成 dxdy 连在一起。
22. text 块中的短公式必须用 \\( ... \\) 包裹，不要输出裸 \\frac{1}{2} 或裸 x^2。
23. 公式必须放入 latex_display / equation_group / derivation_chain，不要把"中间公式：f(x)=..."塞进 text block。
24. 禁止输出 int_0^1，必须写 \\int_0^1；禁止输出 frac{...}{...}，必须写 \\frac{...}{...}；禁止输出 Rightarrow，必须写 \\Rightarrow。
25. final_answer 只写最终结果，不重复推导过程。
"""

_STRUCTURED_SOLVER_PROMPT = CORE_MATH_SEMANTIC_PROMPT + r"""
# 当前任务：生成标准解答（结构化 JSON 输出）

你是考研数学命题组专家。你必须只输出 pure JSON，不要输出任何解释文字、markdown 标记或其他内容。

## 题目信息
- 数学类别：{math_type}
- 题型：{question_type}
- 知识点：{knowledge_point}
- 题目内容：{question}

## 输出格式（严格遵守）

只输出以下格式的 JSON 对象：

```json
{{
  "steps": [
    {{
      "label": "步骤1：求导数",
      "blocks": [
        {{"type": "text", "content": "对函数 f(x)=x^3-3x 求导"}},
        {{"type": "latex", "content": "f'(x) = 3x^2 - 3", "display": "block"}},
        {{"type": "text", "content": "得到一阶导数为 3x^2-3"}}
      ],
      "operation": "differentiate"
    }},
    {{
      "label": "步骤2：求驻点",
      "blocks": [
        {{"type": "text", "content": "令 f'(x)=0，解得驻点"}},
        {{"type": "latex", "content": "3x^2-3=0 \\Rightarrow x=\\pm 1", "display": "block"}}
      ],
      "operation": "solve"
    }}
  ],
  "final_answer": {{"type": "latex", "content": "x=1 或 x=-1"}},
  "metadata": {{
    "knowledge_points": ["导数与微分", "一元函数极值"],
    "difficulty": "基础",
    "total_score": 10,
    "common_mistakes": ["求导时漏掉常数项", "解方程时符号错误"]
  }}
}}
```

## 字段说明
- steps：解题步骤数组，必须非空。每个步骤包含 label（步骤名称，中文）、blocks（内容块数组，text 和 latex 严格分离）、operation（操作类型）
- blocks：type="text" 为纯中文/英文说明，type="latex" 为纯 LaTeX 公式。text 中不含任何 LaTeX 命令，latex 中不含任何中文
- display："block"（独占一行的重要公式）或 "inline"（行内短公式）
- operation 取值：classify（识别题型）、recall（回忆定理）、substitute（代入）、simplify（化简）、expand（展开）、factor（因式分解）、differentiate（求导）、integrate（积分）、solve（求解）、evaluate（计算求值）、apply_theorem（应用定理）、transform（变换）、conclude（得出结论）、check（验证）
- final_answer：最终答案块
- metadata：knowledge_points（知识点列表）、difficulty（基础/中等/较难/难题）、total_score（满分）、common_mistakes（常见错误提醒）

## 字段约束（Schema Validation，违反将被拒绝）

1. **steps 数组必须非空**。每个 step 必须有 label（非空字符串）和 blocks（非空数组）
2. **block.type 只能是 "text" 或 "latex"**（小写，带引号）
3. **text 块**: content 纯中文/英文说明，严禁 LaTeX 命令
4. **latex 块**: content 纯 LaTeX 公式。**严禁出现 $ 符号**（系统用 st.latex() 渲染，已自动进入数学模式。$ 会导致嵌套数学模式崩溃）。严禁中文
5. **display 只能是 "inline"、"block" 或 "hidden"**
6. **operation 必须是以下之一**（可以为空字符串 ""）：
   classify, recall, substitute, simplify, expand, factor,
   differentiate, integrate, solve, evaluate, apply_theorem,
   transform, conclude, check
7. **不要添加未列出的额外字段**（如 title、author、date 等）——它们会被自动丢弃
8. LaTeX 反斜杠命令在 JSON 字符串内必须写成双反斜杠：
   正确: "content": "\\\\frac{{1}}{{2}}"
   错误: "content": "\\frac{{1}}{{2}}"（JSON 解析失败）

## 核心规则（违反将导致 JSON 验证失败）
1. text 和 latex 绝对分离：text 块中严禁出现任何 LaTeX 命令，latex 块中严禁出现任何中文
2. 每个 latex 块是纯 LaTeX 表达式。**绝对禁止出现 $ 符号**（渲染器自动处理数学模式，$ 会导致双重嵌套崩溃）
3. 把长公式放在独立的 display="block" 块中
4. 每一步都必须标注正确的 operation 类型
5. LaTeX 反斜杠命令在 JSON 字符串内必须写成双反斜杠
6. 最终答案必须在 final_answer 中单独给出
7. **推导链公式必须使用 aligned 环境**：多个 = 的连续等式必须写成 \\begin{aligned}...\\end{aligned}，用 &= 对齐
8. **变量替换说明不要拆进公式链**：如 (x=tu) 用 \\quad (x=tu) 附在公式末尾，或写成文字说明
9. **不要在 latex 块中写中文句子**：中文解释和公式必须分开
10. **求极限步骤必须用 \\lim**：不要输出裸 "lim t -> 0+"，必须写 \\lim_{t\\to0^+}
11. **aligned 环境必须完整输出**：\\begin{aligned} 和 \\end{aligned} 必须配对，且单独作为 latex_display 块，不要和中文混在同一段
12. **不要输出 \\&=**：对齐标记只写 &=，不要转义 &
13. **aligned 首行必须有对齐点或换行**：如果首行是对齐表达式，用 &= 连接；如果是独立表达式，用 \\\\ 换行后下一行再用 &=
14. **约束条件用数学表达式**：如 D=\\{(x,y)\\mid 0\\le x\\le a,\\ 0\\le y\\le b\\}，不要拆成多段普通文本
15. **分段函数必须使用 cases 环境**：每行格式为 `表达式, & 条件\\\\`，不要用普通文本描述分段
16. **cases 环境中不要使用行间距标记**：不要输出 `[6pt]` 或 `\\\\[6pt]`，直接用 `\\\\` 换行
17. **不要在 cases 内部使用 \\[ 或 \\]**：这些是 display math delimiter，在 cases 内非法
18. **分数必须完整写**：必须写 \\frac{1}{4}，不要写 frac14 或 dfrac18
19. **积分微分必须写 \\,dx**：dx、dy、dt 必须紧跟积分号，用 \\,dx 格式，不要让 dx 单独成行
20. **不要输出孤立标记**：公式中不要出现单独一行的 `!`、`;`、`**`
21. **事件集合用花括号**：写成 \\{X\\le a,\\ Y\\le b\\}，不要用裸 { 和分号
22. **CDF/PDF 推导必须用 aligned**：多步推导写成 \\begin{aligned} F_Y(y) &= ... \\\\ &= ... \\end{aligned}
23. **不要在公式中留空 !**：`!(` 应写成 `(`，不要用 `!` 作为空格或占位符
24. **方程组用 cases，不要用 aligned 堆多个未知量**：如 f_x=... 与 f_y=... 必须写 \\begin{cases} f_x=... \\\\ f_y=... \\end{cases}，禁止在同一 aligned 行写 ``f_y \\ &=``。
25. **禁止在 aligned/cases 内插入 $ 或 \\$**：display 块内不要出现美元符号。
""" + QUESTION_TYPE_SOLUTION_VIEW_RULES

_CANONICAL_SOLVER_PROMPT = CORE_MATH_SEMANTIC_PROMPT + r"""
# 当前任务：生成规范解答（CanonicalIR 格式）

你是考研数学命题组专家。你必须只输出 pure JSON。

## 题目信息
- 数学类别：{math_type}  |  题型：{question_type}
- 知识点：{knowledge_point}  |  题目：{question}

## 输出格式（严格遵守，这是唯一的合法格式）

只输出以下 JSON 对象。每个字段都必须存在，不要添加额外字段。

```json
{{
  "agent": "solver",
  "question": {{
    "math_type": "{math_type}",
    "question_type": "{question_type}",
    "knowledge_points": ["知识点1", "知识点2"],
    "difficulty": "基础",
    "total_score": 10
  }},
  "proof_trace": {{
    "steps": [
      {{
        "id": "s1",
        "operation": "classify",
        "input_state": "",
        "output_state": "",
        "justification": "识别题型：这是一道一元函数极值问题，需要求导找驻点",
        "label": "步骤1：识别题型"
      }},
      {{
        "id": "s2",
        "operation": "differentiate",
        "input_state": "f(x) = x^3 - 3x",
        "output_state": "f'(x) = 3x^2 - 3",
        "justification": "对 f(x) 求一阶导数，使用幂函数求导公式",
        "label": "步骤2：求一阶导数"
      }},
      {{
        "id": "s3",
        "operation": "solve",
        "input_state": "f'(x) = 3x^2 - 3 = 0",
        "output_state": "x = 1 \\text{{ 或 }} x = -1",
        "justification": "令导数为零，解二次方程得到驻点 x=1 和 x=-1",
        "label": "步骤3：求驻点"
      }}
    ],
    "final_answer": "x = 1 \\text{{ 或 }} x = -1"
  }},
  "metadata": {{
    "knowledge_points": ["导数与微分", "一元函数极值"],
    "common_mistakes": ["漏解 x=-1", "导数计算错误"]
  }}
}}
```

## 字段说明

**proof_trace.steps** — 每个步骤是一个原子数学操作，必须包含：
- **id**: 步骤编号（s1, s2, s3...）
- **operation**: 必须是以下枚举值之一（不可拼错）：
  classify, recall, substitute, simplify, expand, factor,
  differentiate, integrate, solve, evaluate, apply_theorem,
  transform, conclude, check
- **input_state**: 纯 LaTeX 数学表达式。严禁包含中文。只写公式，不要写解释文字。第1步可留空 ""
- **output_state**: 纯 LaTeX 数学表达式。严禁包含中文。只写公式结果，不要写"解得""代入得"等文字
- **justification**: 为什么这一步是正确/必要的（中文，必须写定理名或推理依据）
- **label**: 步骤名称（中文，如"步骤1：求导"）

**proof_trace.final_answer** — 最终答案（LaTeX 字符串）

**metadata** — 知识点列表和常见错误提醒

## 核心规则
1. 步骤必须是原子的——每个 step 只做一件事
2. **output_state 必须填写**，展示该步骤的数学结果。这是最重要的字段
3. input_state 第1步可留空，后续步骤应填前一步的 output_state
4. LaTeX 反斜杠在 JSON 内必须双写：\\frac → \\\\frac, \\int → \\\\int
5. operation 只取上述枚举值，不要自创
6. justification 必须实质性地解释推理依据，不要写"显然""易得"
7. 不要添加未列出的字段（会被自动丢弃）
8. **严禁在 output_state / input_state 中出现 $ 符号**（这些字段会被 st.latex() 渲染，已自动处于数学模式。$ 会导致嵌套崩溃）
""" + QUESTION_TYPE_SOLUTION_VIEW_RULES

_STRUCTURED_GRADING_PROMPT = _SAFE_BASE + r"""
# Current task: grading (structured JSON)

You are an experienced graduate math exam grader. Output PURE JSON only, no other text.

## Question
{question}

## Standard answer
{standard_answer}

## Student answer
{student_answer}

## Knowledge points
{knowledge_points}

## Difficulty
{difficulty}

## Grading rules
{grading_rules}

## Score parameters
- Step score max: {step_total}
- Result score max: {result_total}
- Total score max: {total}

## JSON Schema (follow strictly)

```json
{{
  "score": {{
    "step_score": 0.0,
    "result_score": 0.0,
    "total": 0.0
  }},
  "step_analysis": [
    {{
      "num": 1,
      "content": "Student step content summary in Chinese",
      "judgment": "correct / partially correct / wrong",
      "score": "3.0/5.0",
      "comment": "Grading comment in Chinese"
    }}
  ],
  "deductions": [
    {{"reason": "Concept error: description in Chinese", "points": 2.0}}
  ],
  "comment": "Overall evaluation in Chinese, 1-2 sentences",
  "method_matched": "Matched solution method name (if any)",
  "confidence": 0.85
}}
```

## Grading principles
1. Compare each student step against the standard answer
2. judgment must be one of: correct / partially correct / wrong
3. Concept errors: heavy deduction. Calculation carelessness: light deduction
4. Different but correct method: award full points
5. Total score precise to 1 decimal place
6. Write ALL natural language content in Chinese
"""

_STRUCTURED_DIAGNOSIS_PROMPT = _SAFE_BASE + r"""
# Current task: error diagnosis (structured JSON)

You are an expert in graduate math education research. Output PURE JSON only, no other text.

## Question
{question}

## Student answer
{student_answer}

## Standard answer
{standard_answer}

## Grading result
Score: {score}/{total_score}

## Error history
{error_history}

## JSON Schema (follow strictly)

```json
{{
  "error_type": "concept error / formula error / calculation error / derivation error / misreading / careless mistake",
  "root_cause": "Root cause analysis in Chinese, 2-3 sentences",
  "weak_points": ["Weak knowledge point 1", "Weak knowledge point 2"],
  "recommendations": ["Improvement suggestion 1", "Improvement suggestion 2"],
  "common_mistakes": ["Common mistake 1"],
  "is_repeat": false,
  "affects_future": false,
  "knowledge_points": ["Related knowledge points"]
}}
```

## Diagnosis principles
1. Go deep to the knowledge concept level, not just surface description
2. If same knowledge point appears in error history >= 2 times, mark is_repeat: true
3. Indicate whether this affects future chapters
4. Write ALL natural language analysis in Chinese
"""
