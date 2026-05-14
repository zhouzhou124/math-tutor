"""fix_latex_options.py — 清理选项中的多余LaTeX命令"""
import json
import os

DATA_PATH = 'storage/questions/data'

# 需要清理的命令
clean_patterns = [
    r'\\quad\s*$',      # 末尾的 \quad
    r'\\quad\s*$',      # 末尾的 \quad（带空格）
    r'\\qquad\s*$',     # 末尾的 \qquad
]

# 遍历所有2026年的题目文件
for filename in os.listdir(DATA_PATH):
    if filename.startswith('2026-数一-') and filename.endswith('.json'):
        filepath = os.path.join(DATA_PATH, filename)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        modified = False
        
        # 清理选项中的 \quad
        if 'options' in data and isinstance(data['options'], dict):
            for key, value in data['options'].items():
                # 去除末尾的 \quad 和空格
                clean_value = value.rstrip()
                clean_value = clean_value.rstrip('\\quad')
                clean_value = clean_value.rstrip('\\qquad')
                clean_value = clean_value.rstrip()
                
                if clean_value != value:
                    data['options'][key] = clean_value
                    modified = True
                    print(f'清理 {filename} 选项 {key}: "{value}" -> "{clean_value}"')
        
        # 清理题目中的问题
        if 'question' in data:
            # 检查是否有其他问题...
            pass
        
        # 如果有修改，保存文件
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

print('\n清理完成！')