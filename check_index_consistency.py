"""check_index_consistency.py"""
import json
from pathlib import Path

SIMUL_DIR = Path('storage/questions/simulations')
EXAM_DIR = Path('storage/questions/exams')
INDEX_PATH = Path('storage/questions/_index.json')

# 加载索引
with open(INDEX_PATH, encoding='utf-8') as f:
    index = json.load(f)

# 获取所有实际存在的题目ID
actual_qids = set()

# 从simulations目录
for f in SIMUL_DIR.glob('*.json'):
    qid = f.stem
    actual_qids.add(qid)

# 从exams目录
for f in EXAM_DIR.glob('*.json'):
    qid = f.stem
    actual_qids.add(qid)

print(f'=== 实际文件中的题目ID数量: {len(actual_qids)} ===')

# 获取索引中所有的题目ID
indexed_qids = set()

# 从分类索引
for cat, vols in index['categories'].items():
    for vol, qtypes in vols.items():
        for qtype, qids in qtypes.items():
            indexed_qids.update(qids)

# 从知识点索引
for kp, qids in index['knowledge_index'].items():
    indexed_qids.update(qids)

# 从难度索引
for diff, qids in index['difficulty_index'].items():
    indexed_qids.update(qids)

print(f'=== 索引中的题目ID数量: {len(indexed_qids)} ===')

# 找出问题
print('\n=== 问题分析 ===')

# 索引中有但实际不存在的题目
missing_in_files = indexed_qids - actual_qids
print(f'❌ 索引存在但文件不存在的题目: {len(missing_in_files)}个')
for qid in sorted(missing_in_files)[:10]:
    print(f'  {qid}')
if len(missing_in_files) > 10:
    print(f'  ... 还有 {len(missing_in_files)-10} 个')

# 文件存在但索引中没有的题目
missing_in_index = actual_qids - indexed_qids
print(f'\n❌ 文件存在但索引中没有的题目: {len(missing_in_index)}个')
for qid in sorted(missing_in_index)[:10]:
    print(f'  {qid}')
if len(missing_in_index) > 10:
    print(f'  ... 还有 {len(missing_in_index)-10} 个')

# 检查宇哥八套卷的索引
print('\n=== 宇哥八套卷索引详情 ===')
yuge = index['categories'].get('26宇哥八套卷', {})
print('卷号:', list(yuge.keys()))
for vol, qtypes in yuge.items():
    total = sum(len(ids) for ids in qtypes.values())
    print(f'  {vol}: {total}题')
    for qtype, qids in qtypes.items():
        print(f'    {qtype}: {len(qids)}题')
        # 检查每个题目是否存在
        for qid in qids:
            if qid not in actual_qids:
                print(f'      ❌ {qid} - 文件不存在')