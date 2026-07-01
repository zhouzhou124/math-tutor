import json
from database.question_db import QuestionDB

db = QuestionDB()

# Test searching by volume
print("Testing search by volume...")
results = db.search(volume='卷七', math_type='26李擂八套卷', limit=30)
print(f'Found {len(results)} questions for 26李擂八套卷-卷七')

for q in results:
    qid = q.get("question_id", "")
    qtype = q.get("question_type", "")
    has_answer = bool(q.get("standard_answer"))
    print(f'  - {qid}: {qtype}, has_answer={has_answer}')

# Verify specific questions
print("\nVerifying answers...")
for qid in ["26李擂八套卷-卷七-001", "26李擂八套卷-卷七-012", "26李擂八套卷-卷七-020"]:
    q = db.get(qid)
    if q:
        print(f'  {qid}: answer={q.get("standard_answer", "N/A")}')
