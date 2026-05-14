"""cleanup_index.py — 清理索引文件，确保与实际文件一致"""
import json
import os

INDEX_PATH = 'storage/questions/_index.json'
DATA_PATH = 'storage/questions/data'

# 读取索引文件
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    index = json.load(f)

# 获取实际存在的题目文件
existing_files = set()
for filename in os.listdir(DATA_PATH):
    if filename.endswith('.json'):
        qid = filename[:-5]  # 去掉 .json
        existing_files.add(qid)

print(f'实际文件数量: {len(existing_files)}')

# 清理 categories (嵌套结构: 数学一 -> 年份 -> 题型 -> 题目列表)
all_valid_qids = set()
for cat_name, cat_data in list(index['categories'].items()):
    if isinstance(cat_data, dict):
        for year_name, year_data in list(cat_data.items()):
            if isinstance(year_data, dict):
                for qtype_name, qids in list(year_data.items()):
                    valid_qids = [qid for qid in qids if qid in existing_files]
                    if not valid_qids:
                        del year_data[qtype_name]
                        print(f'删除空题型: {cat_name}/{year_name}/{qtype_name}')
                    else:
                        year_data[qtype_name] = valid_qids
                        all_valid_qids.update(valid_qids)
                
                if not year_data:
                    del cat_data[year_name]
                    print(f'删除空年份: {cat_name}/{year_name}')
        
        if not cat_data:
            del index['categories'][cat_name]
            print(f'删除空类别: {cat_name}')

# 清理 knowledge_index
for kp, qids in list(index['knowledge_index'].items()):
    valid_qids = [qid for qid in qids if qid in existing_files]
    if not valid_qids:
        del index['knowledge_index'][kp]
        print(f'删除空知识点: {kp}')
    else:
        index['knowledge_index'][kp] = valid_qids

# 清理 difficulty_index
for diff, qids in list(index['difficulty_index'].items()):
    valid_qids = [qid for qid in qids if qid in existing_files]
    if not valid_qids:
        del index['difficulty_index'][diff]
        print(f'删除空难度级别: {diff}')
    else:
        index['difficulty_index'][diff] = valid_qids

# 更新统计信息
index['metadata']['total_questions'] = len(all_valid_qids)
index['metadata']['knowledge_points_count'] = len(index['knowledge_index'])
index['metadata']['difficulty_levels_count'] = len(index['difficulty_index'])

# 更新年份列表
years = set()
for cat_data in index['categories'].values():
    if isinstance(cat_data, dict):
        years.update(cat_data.keys())
index['metadata']['years_covered'] = sorted([int(y) for y in years])

# 保存索引文件
with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print(f'\n索引已清理完成')
print(f'题目总数: {index["metadata"]["total_questions"]}')
print(f'知识点数: {index["metadata"]["knowledge_points_count"]}')
print(f'难度级别数: {index["metadata"]["difficulty_levels_count"]}')
print(f'覆盖年份: {index["metadata"]["years_covered"]}')