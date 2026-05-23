"""
Embedding Text Builder — 数学语义文本生成器

核心: 不是 embedding LaTeX, 而是 embedding "数学语义描述"

对每道题生成:
  embedding_text = metadata + 知识点 + 方法 + 题型 + 难度
  用于 pgvector / BGE 向量检索
"""
import json, os, re
from pathlib import Path

DATA_DIR = Path('E:/math_tutor/storage/questions/data')

# Math concept patterns: LaTeX command → natural language tag
CONCEPT_PATTERNS = [
    (r'\\int', '积分'),
    (r'\\iint|\\iiint|\\oint', '重积分 曲线积分'),
    (r'\\sum', '级数 求和'),
    (r'\\lim', '极限'),
    (r'\\frac\{d\}', '导数'),
    (r'\\partial', '偏导数'),
    (r'\\sin|\\cos|\\tan|\\arcsin|\\arccos|\\arctan', '三角函数'),
    (r'\\ln|\\log|\\exp|e\^', '对数指数函数'),
    (r'\\begin\{pmatrix\}|\\begin\{bmatrix\}|矩阵|行列式', '矩阵运算'),
    (r'特征值|特征向量|\\lambda', '特征值 特征向量'),
    (r'二次型|标准形|规范形', '二次型 标准化'),
    (r'正交变换|正交矩阵|正交化', '正交变换'),
    (r'概率|分布|期望|方差|协方差|相关系数', '概率统计'),
    (r'估计|似然|MLE|矩估计', '参数估计 极大似然'),
    (r'假设检验|置信区间|显著性', '假设检验'),
    (r'中值定理|拉格朗日|罗尔|柯西', '微分中值定理'),
    (r'泰勒|麦克劳林|Taylor', '泰勒展开'),
    (r'级数.*收敛|绝对收敛|条件收敛', '级数收敛性'),
    (r'傅里叶|Fourier', '傅里叶级数'),
    (r'格林公式|高斯公式|斯托克斯', '积分公式'),
    (r'极值|极大值|极小值|驻点', '函数极值'),
    (r'渐近线|渐近', '曲线渐近线'),
    (r'切线|法线|切平面', '切线与法线'),
    (r'线性无关|线性相关|极大无关组', '向量线性关系'),
    (r'基础解系|通解|特解|微分方程', '微分方程求解'),
    (r'旋度|散度|梯度|方向导数', '向量场微积分'),
    (r'曲面|曲线|旋转体|体积|面积', '几何应用'),
]

DIFFICULTY_LABELS = {
    '基础': '基础题', '中等': '中等难度', '较难': '较难题', '难题': '高难度题',
}


def build_embedding_text(question: dict) -> str:
    """
    从 question dict 生成 embedding_text.

    格式: 考研数学一 {year} {题型} {知识点串} {方法提示} {难度标签}
    """
    parts = []

    # 1. Exam metadata
    year = question.get('year', '')
    qtype = question.get('question_type', '')
    parts.append(f'考研数学一 {year}年 {qtype}')

    # 2. Knowledge points
    kps = question.get('knowledge_points', [])
    if kps:
        parts.append('知识点: ' + ' '.join(kps))

    # 3. Extract math concepts from LaTeX
    latex = question.get('raw_question_text') or question.get('question', '')
    concepts = set()
    for pattern, tag in CONCEPT_PATTERNS:
        if re.search(pattern, latex):
            concepts.add(tag)
    if concepts:
        parts.append('数学概念: ' + ' '.join(sorted(concepts)))

    # 4. Difficulty
    diff = question.get('difficulty', '中等')
    parts.append(DIFFICULTY_LABELS.get(diff, diff))

    # 5. Score
    score = question.get('score', 0)
    if score:
        parts.append(f'{score}分题')

    # 6. Question ID (for exact match)
    parts.append(question.get('question_id', ''))

    return ' '.join(parts)


def build_all_embeddings(dry_run: bool = False):
    """为所有题目生成 embedding_text 并保存."""
    count = 0
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith('.json'):
            continue
        path = DATA_DIR / fname
        with open(path, 'r', encoding='utf-8') as f:
            q = json.load(f)

        emb_text = build_embedding_text(q)
        q['embedding_text'] = emb_text

        if not dry_run:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(q, f, ensure_ascii=False, indent=2)
        count += 1

    print(f'Built embedding_text for {count} questions' + (' (dry-run)' if dry_run else ''))


if __name__ == '__main__':
    build_all_embeddings(dry_run=False)
