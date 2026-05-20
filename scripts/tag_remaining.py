"""Manual tagging for 21 questions that AI + keyword matching missed."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS = os.path.join(ROOT, "storage", "questions", "exams")

MANUAL_TAGS = {
    # 2009 数一
    "2009-数一-001.json": ["极限与连续"],
    "2009-数一-003.json": ["定积分", "定积分应用"],
    "2009-数一-011.json": ["曲线积分"],
    "2009-数一-014.json": ["参数估计"],
    "2009-数一-015.json": ["多元函数微分"],
    "2009-数一-016.json": ["定积分应用", "无穷级数"],
    "2009-数一-017.json": ["定积分应用"],
    "2009-数一-020.json": ["特征值与特征向量", "线性方程组"],

    # 2010 数一
    "2010-数一-004.json": ["定积分", "极限与连续"],
    "2010-数一-012.json": ["三重积分"],
    "2010-数一-013.json": ["向量组与线性空间"],
    "2010-数一-016.json": ["定积分", "导数与微分"],
    "2010-数一-017.json": ["定积分", "无穷级数"],

    # 2011 数一
    "2011-数一-001.json": ["导数与微分", "中值定理"],
    "2011-数一-004.json": ["定积分"],
    "2011-数一-009.json": ["定积分应用"],
    "2011-数一-011.json": ["多元函数微分", "定积分"],
    "2011-数一-013.json": ["二次型"],
    "2011-数一-017.json": ["导数与微分", "中值定理"],
    "2011-数一-018.json": ["无穷级数", "极限与连续"],
    "2011-数一-023.json": ["参数估计"],
}

count = 0
for fname, tags in MANUAL_TAGS.items():
    path = os.path.join(EXAMS, fname)
    if not os.path.exists(path):
        print(f"WARNING: {fname} not found")
        continue
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["knowledge_points"] = tags
    data["tags"] = tags
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Tagged {fname}: {tags}")
    count += 1

print(f"\nDone. Tagged {count} files.")
