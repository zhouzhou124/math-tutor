"""
Question Registry — question_id 生成与唯一性校验
"""

import json
import os
from pathlib import Path
from .schema import QuestionEntity, EntityStatus


class QuestionRegistry:
    """题目注册中心"""

    def __init__(self, storage_dir: str = ""):
        self.storage_dir = Path(storage_dir) if storage_dir else None
        self._entities: dict[str, QuestionEntity] = {}
        self._hash_index: dict[str, str] = {}  # content_hash → question_id

    def register(self, entity: QuestionEntity) -> bool:
        """注册题目实体。返回 False 表示 ID 冲突。"""
        qid = entity.question_id

        # ID 冲突检查
        if qid in self._entities:
            existing = self._entities[qid]
            if existing.content_hash != entity.content_hash:
                # 内容漂移 → 版本升级
                entity.revision = existing.revision + 1
                entity.previous_hash = existing.content_hash
            else:
                return False  # 完全相同，跳过

        self._entities[qid] = entity
        self._hash_index[entity.content_hash] = qid
        return True

    def get(self, question_id: str) -> QuestionEntity | None:
        return self._entities.get(question_id)

    def get_by_hash(self, content_hash: str) -> QuestionEntity | None:
        qid = self._hash_index.get(content_hash)
        if qid:
            return self._entities.get(qid)
        return None

    def list_manual_review(self) -> list[QuestionEntity]:
        """列出所有待人工复核的实体"""
        return [
            e for e in self._entities.values()
            if e.status == EntityStatus.MANUAL_REVIEW
        ]

    def list_unresolved(self) -> list[QuestionEntity]:
        """列出所有未匹配的实体"""
        return [
            e for e in self._entities.values()
            if e.status == EntityStatus.UNRESOLVED
        ]

    def stats(self) -> dict:
        """注册中心统计"""
        total = len(self._entities)
        status_counts = {}
        for e in self._entities.values():
            s = e.status.name
            status_counts[s] = status_counts.get(s, 0) + 1

        with_answer = sum(
            1 for e in self._entities.values()
            if e.official_answer and e.official_answer.value
        )
        with_solution = sum(
            1 for e in self._entities.values()
            if e.official_solution and e.official_solution.steps_markdown
        )
        manual_review = len(self.list_manual_review())

        return {
            "total": total,
            "status_counts": status_counts,
            "with_answer": with_answer,
            "with_solution": with_solution,
            "manual_review": manual_review,
        }

    def to_dict_list(self) -> list[dict]:
        """转为可序列化的 dict 列表（用于 JSON 存储）"""
        result = []
        for entity in self._entities.values():
            d = {
                "question_id": entity.question_id,
                "year": entity.year,
                "subject": entity.subject,
                "status": entity.status.name,
                "question_type": entity.stem.question_type if entity.stem else "",
                "question": entity.stem.clean_text if entity.stem else "",
                "options": [
                    {"key": o.key, "text": o.text}
                    for o in (entity.stem.options if entity.stem else [])
                ],
                "standard_answer": entity.official_answer.value if entity.official_answer else "",
                "answer_confidence": entity.official_answer.confidence if entity.official_answer else 0,
                "answer_matched_by": entity.official_answer.matched_by if entity.official_answer else "",
                "solution_steps": (
                    entity.official_solution.steps_markdown.split("\n")
                    if entity.official_solution and entity.official_solution.steps_markdown
                    else []
                ),
                "knowledge_points": entity.knowledge_points,
                "difficulty": entity.difficulty,
                "score": entity.score,
                "content_hash": entity.content_hash,
                "revision": entity.revision,
                "alignment_score": entity.alignment.overall_score if entity.alignment else 0,
                "manual_review": entity.status == EntityStatus.MANUAL_REVIEW,
            }
            result.append(d)
        return result

    def save_to_json(self, path: str):
        """保存注册中心到 JSON"""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict_list(), f, ensure_ascii=False, indent=2)

    def load_from_json(self, path: str):
        """从 JSON 加载注册中心"""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        from .schema import (
            QuestionEntity, QuestionStem, ChoiceOption,
            OfficialAnswer, OfficialSolution, EntityStatus,
        )
        for d in data:
            stem = QuestionStem(
                raw_text=d["question"],
                clean_text=d["question"],
                options=[ChoiceOption(**o) for o in d.get("options", [])],
                question_type=d.get("question_type", "解答题"),
            )
            entity = QuestionEntity(
                question_id=d["question_id"],
                year=d["year"],
                subject=d["subject"],
                status=EntityStatus[d.get("status", "AUTO_MATCHED")],
                stem=stem,
                official_answer=OfficialAnswer(
                    value=d["standard_answer"],
                    confidence=d.get("answer_confidence", 0),
                    matched_by=d.get("answer_matched_by", ""),
                ) if d.get("standard_answer") else None,
                knowledge_points=d.get("knowledge_points", []),
                difficulty=d.get("difficulty", "中等"),
                score=d.get("score", 10),
                content_hash=d.get("content_hash", ""),
                revision=d.get("revision", 1),
            )
            self._entities[entity.question_id] = entity
            if entity.content_hash:
                self._hash_index[entity.content_hash] = entity.question_id
