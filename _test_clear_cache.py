import json
from database.question_db import QuestionDB

# 创建新的数据库实例（会清除缓存）
db = QuestionDB()

# 清除索引缓存
db._clear_index_cache()

# 清除题目缓存
db._question_cache = {}

# 重新加载题目
q = db.get("26李擂八套卷-卷六-020")
print("卷六-020题内容:")
print(f"  question_id: {q.get('question_id')}")
print(f"  question:\n{q.get('question')}")
print(f"\n  standard_answer:\n{q.get('standard_answer')}")
