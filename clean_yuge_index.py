"""clean_yuge_index.py — 清理宇哥八套卷索引"""
import json

INDEX_PATH = 'storage/questions/_index.json'

# 读取索引文件
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    index = json.load(f)

# 删除宇哥八套卷分类
if '26宇哥八套卷' in index['categories']:
    del index['categories']['26宇哥八套卷']
    print('已删除宇哥八套卷分类')

# 清理知识点索引中的宇哥八套卷题目
for kp, qids in list(index['knowledge_index'].items()):
    new_qids = [qid for qid in qids if '宇哥' not in qid]
    if len(new_qids) != len(qids):
        index['knowledge_index'][kp] = new_qids
        print(f'清理知识点 {kp} 中的宇哥题目')

# 清理难度索引中的宇哥八套卷题目
for diff, qids in list(index['difficulty_index'].items()):
    new_qids = [qid for qid in qids if '宇哥' not in qid]
    if len(new_qids) != len(qids):
        index['difficulty_index'][diff] = new_qids
        print(f'清理难度 {diff} 中的宇哥题目')

# 更新统计
index['metadata']['total_questions'] -= 1  # 删除了一道题

# 保存索引文件
with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print('索引清理完成！')