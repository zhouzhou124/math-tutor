"""fix_yuge_index.py — 修复宇哥八套卷索引错误"""
import json

INDEX_PATH = 'storage/questions/_index.json'

# 读取索引文件
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    index = json.load(f)

# 修复宇哥八套卷的索引
if '26宇哥八套卷' in index['categories']:
    for volume_name, volume_data in index['categories']['26宇哥八套卷'].items():
        if isinstance(volume_data, dict):
            # 获取实际存在的题目ID（解答题）
            solution_qids = volume_data.get('解答题', [])
            
            # 清空选择题和填空题（因为目前没有这些题）
            if '选择题' in volume_data:
                del volume_data['选择题']
                print(f'删除空的选择题分类: 26宇哥八套卷/{volume_name}')
            
            if '填空题' in volume_data:
                del volume_data['填空题']
                print(f'删除空的填空题分类: 26宇哥八套卷/{volume_name}')

# 保存索引文件
with open(INDEX_PATH, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, indent=2)

print('索引已修复完成！')