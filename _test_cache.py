import json
from database.question_db import QuestionDB

db = QuestionDB()

# 检查卷六第020题的内容
q = db.get("26李擂八套卷-卷六-020")
if q:
    print("卷六-020题内容:")
    print(f"  question_id: {q.get('question_id')}")
    print(f"  question_type: {q.get('question_type')}")
    print(f"  question: {q.get('question')[:150]}...")
    print(f"  standard_answer: {q.get('standard_answer')[:100]}...")

# 检查卷六第021题
q21 = db.get("26李擂八套卷-卷六-021")
if q21:
    print("\n卷六-021题内容:")
    print(f"  question_id: {q21.get('question_id')}")
    print(f"  question: {q21.get('question')[:150]}...")
