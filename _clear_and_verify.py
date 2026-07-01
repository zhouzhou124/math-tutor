import json
from database.question_db import QuestionDB
import os

# 创建新的数据库实例
db = QuestionDB()

# 清除所有缓存
db._clear_index_cache()
db._question_cache = {}
if hasattr(db, '_stats_cache'):
    delattr(db, '_stats_cache')
if hasattr(db, '_stats_cache_time'):
    delattr(db, '_stats_cache_time')

# 重新加载所有卷六题目并验证
print("=== 验证卷六题目更新 ===")
results = db.search(volume='卷六', math_type='26李擂八套卷', limit=30)

for q in results:
    qid = q.get('question_id')
    qtype = q.get('question_type')
    question = q.get('question')[:80] + "..." if len(q.get('question')) > 80 else q.get('question')
    has_answer = bool(q.get('standard_answer'))
    print(f"{qid}: {qtype}, has_answer={has_answer}")
    print(f"   题目预览: {question}")

print("\n=== 验证完成 ===")
