"""
Similar Question Recommender — 同类题推荐

给定当前题目和诊断结果，找到适合专项练习的同类题。
策略：同知识点同难度 → 同知识点邻近难度 → hybrid_search 融合。排除已答题目。
"""

from hybrid_search import hybrid_search
from database.question_db import QuestionDB


def recommend_similar(
    question: dict,
    diagnosis: dict | None = None,
    question_db: QuestionDB | None = None,
    top_k: int = 3,
    exclude_ids: set[str] | None = None,
) -> list[dict]:
    """
    为当前题目推荐同类练习。

    Args:
        question: 当前题目 dict（需包含 knowledge_points, difficulty, question_type, year）
        diagnosis: 诊断结果 dict（可选，含 error_type, root_cause）
        question_db: QuestionDB 实例（可选，若提供则用 db.search 做精确筛选）
        top_k: 返回结果数
        exclude_ids: 排除的 question_id 集合（已练习过的题）

    Returns:
        list of question dicts
    """
    exclude = exclude_ids or set()
    current_id = question.get("question_id", "")
    exclude.add(current_id)

    knowledge_points = question.get("knowledge_points", [])
    difficulty = question.get("difficulty", "中等")
    year = question.get("year")

    results: list[dict] = []
    seen_ids: set[str] = {current_id}

    # ── 第1层: 同知识点 + 同难度 ──
    if question_db and knowledge_points:
        for kp in knowledge_points[:2]:
            try:
                candidates = question_db.search(
                    knowledge_point=kp,
                    difficulty=difficulty if difficulty != "全部" else None,
                    limit=top_k * 3,
                )
                for q in candidates:
                    qid = q.get("question_id", "")
                    if qid not in seen_ids:
                        results.append(q)
                        seen_ids.add(qid)
            except Exception:
                pass

    # ── 第2层: 同知识点 + 邻近难度 ──
    if question_db and knowledge_points and len(results) < top_k:
        neighbor_diffs = _adjacent_difficulties(difficulty)
        for nd in neighbor_diffs:
            for kp in knowledge_points[:1]:
                try:
                    candidates = question_db.search(
                        knowledge_point=kp,
                        difficulty=nd,
                        limit=top_k,
                    )
                    for q in candidates:
                        qid = q.get("question_id", "")
                        if qid not in seen_ids:
                            results.append(q)
                            seen_ids.add(qid)
                except Exception:
                    pass

    # ── 第3层: hybrid_search 融合 ──
    if len(results) < top_k and knowledge_points:
        query_text = question.get("raw_question_text") or question.get("question", " ".join(knowledge_points))
        try:
            search_results = hybrid_search(
                query=query_text[:200],
                filters={"question_type": question.get("question_type", "")},
                top_k=top_k * 2,
            )
            for q in search_results:
                qid = q.get("question_id", "")
                if qid not in seen_ids and qid not in exclude:
                    results.append(q)
                    seen_ids.add(qid)
        except Exception:
            pass

    # ── 多样性: 尽量来自不同年份 ──
    results = _diversify_by_year(results, top_k, year)

    return results[:top_k]


def _adjacent_difficulties(diff: str) -> list[str]:
    """返回邻近难度（优先更简单的）。"""
    from config import DIFFICULTY_LEVELS as DL
    try:
        idx = DL.index(diff)
    except ValueError:
        return []
    neighbors = []
    if idx > 0:
        neighbors.append(DL[idx - 1])  # 更容易的
    if idx < len(DL) - 1:
        neighbors.append(DL[idx + 1])  # 更难的
    return neighbors


def _diversify_by_year(results: list[dict], top_k: int, exclude_year=None) -> list[dict]:
    """确保推荐结果来自不同年份。"""
    if len(results) <= 1:
        return results

    diversified: list[dict] = []
    seen_years: set[int] = set()
    if exclude_year:
        seen_years.add(exclude_year)

    for q in results:
        y = q.get("year")
        if y not in seen_years:
            diversified.append(q)
            seen_years.add(y)
            if len(diversified) >= top_k:
                break

    # 如果还没凑够，追加非重复年份的
    for q in results:
        if len(diversified) >= top_k:
            break
        if q not in diversified:
            diversified.append(q)

    return diversified
