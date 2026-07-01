# Test script to verify question import
import json
from database.question_db import QuestionDB

db = QuestionDB()

# Test searching by volume
print("Testing search by volume...")
results = db.search(volume='卷六', math_type='26李擂八套卷', limit=30)
print(f'Found {len(results)} questions for 26李擂八套卷-卷六')

for q in results:
    print(f'  - {q.get("question_id")}: {q.get("question_type")}')

# Test getting a single question with answer
print("\nTesting question with answer...")
q = db.get("26李擂八套卷-卷六-001")
if q:
    print(f'  Got question: {q.get("question_id")}')
    print(f'  Question type: {q.get("question_type")}')
    print(f'  Has answer: {bool(q.get("standard_answer"))}')
