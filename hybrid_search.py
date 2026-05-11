"""
Hybrid Search Engine — 数学题混合检索

检索流程:
  Query → Metadata Filter → BM25 Keyword → Vector Scorer → RRF Fusion → Top-K

当前实现: 文件存储版 (无需 PostgreSQL)
迁移路径: 相同接口, 替换为 pgvector + FTS 后端
"""
import json, os, re
from pathlib import Path
from collections import defaultdict
from embedding_builder import build_embedding_text

DATA_DIR = Path('E:/math_tutor/storage/questions/data')


# ═══════════════════════════════════════════════
# Metadata Filter
# ═══════════════════════════════════════════════

def metadata_filter(filters: dict) -> list[dict]:
    """
    SQL-like filter:
      year__gte=2010, question_type='解答题', difficulty__gte=0.7
    """
    results = []
    for fname in os.listdir(DATA_DIR):
        if not fname.endswith('.json'):
            continue
        with open(DATA_DIR / fname, 'r', encoding='utf-8') as f:
            q = json.load(f)

        match = True
        for key, val in filters.items():
            if '__gte' in key:
                k = key.replace('__gte', '')
                if q.get(k, 0) < val:
                    match = False
            elif '__lte' in key:
                k = key.replace('__lte', '')
                if q.get(k, 0) > val:
                    match = False
            elif '__in' in key:
                k = key.replace('__in', '')
                if q.get(k) not in val:
                    match = False
            elif '__contains' in key:
                k = key.replace('__contains', '')
                qval = q.get(k, [])
                if not any(val in str(v) for v in (qval if isinstance(qval, list) else [qval])):
                    match = False
            else:
                if q.get(key) != val:
                    match = False
        if match:
            results.append(q)
    return results


# ═══════════════════════════════════════════════
# BM25-like Keyword Scorer
# ═══════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    """Simple Chinese + English tokenizer."""
    tokens = []
    # Split Chinese characters individually
    for ch in text:
        if '一' <= ch <= '鿿':
            tokens.append(ch)
        elif ch.isalnum():
            tokens.append(ch.lower())
    # Also split by whitespace for multi-char terms
    for word in text.split():
        word = word.strip().lower()
        if len(word) >= 2:
            tokens.append(word)
    return tokens


def bm25_score(query: str, documents: list[dict]) -> list[tuple[dict, float]]:
    """
    BM25-like scoring using embedding_text.
    Returns [(doc, score), ...] sorted by score desc.
    """
    k1, b = 1.5, 0.75

    # Build term frequencies
    term_doc_count = defaultdict(int)
    doc_terms = []
    for doc in documents:
        emb = doc.get('embedding_text', build_embedding_text(doc))
        tokens = _tokenize(emb)
        doc_terms.append(tokens)
        for t in set(tokens):
            term_doc_count[t] += 1

    N = len(documents)
    avgdl = sum(len(t) for t in doc_terms) / max(N, 1)
    query_tokens = _tokenize(query)

    scored = []
    for i, (doc, terms) in enumerate(zip(documents, doc_terms)):
        score = 0.0
        dl = len(terms)
        for qt in query_tokens:
            if qt not in term_doc_count:
                continue
            tf = terms.count(qt)
            idf = max(0, (N - term_doc_count[qt] + 0.5) / (term_doc_count[qt] + 0.5))
            score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avgdl))
        scored.append((doc, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ═══════════════════════════════════════════════
# Simple Vector Scorer (no model — use keyword density as proxy)
# ═══════════════════════════════════════════════

def vector_score(query: str, documents: list[dict]) -> list[tuple[dict, float]]:
    """
    Simple vector-like scoring using concept overlap.
    Upgrade path: replace with BGE-M3 embedding cosine similarity.
    """
    query_tokens = set(_tokenize(query))
    scored = []
    for doc in documents:
        emb = doc.get('embedding_text', build_embedding_text(doc))
        doc_tokens = set(_tokenize(emb))
        overlap = len(query_tokens & doc_tokens) / max(len(query_tokens | doc_tokens), 1)
        scored.append((doc, overlap))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ═══════════════════════════════════════════════
# Reciprocal Rank Fusion
# ═══════════════════════════════════════════════

def rrf_fusion(ranked_lists: list[list[tuple[dict, float]]],
               k: int = 60) -> list[tuple[dict, float]]:
    """
    Reciprocal Rank Fusion: merge multiple ranked lists.
    """
    scores = defaultdict(float)
    for ranked in ranked_lists:
        for rank, (doc, _) in enumerate(ranked):
            qid = doc.get('question_id', '')
            scores[qid] += 1.0 / (k + rank + 1)

    # Sort by fused score
    doc_map = {}
    for ranked in ranked_lists:
        for doc, _ in ranked:
            doc_map[doc['question_id']] = doc

    fused = [(doc_map[qid], score) for qid, score in scores.items()]
    fused.sort(key=lambda x: x[1], reverse=True)
    return fused


# ═══════════════════════════════════════════════
# Hybrid Search API
# ═══════════════════════════════════════════════

def hybrid_search(query: str,
                  filters: dict = None,
                  top_k: int = 10,
                  weights: tuple = (0.5, 0.3, 0.2)) -> list[dict]:
    """
    Hybrid search: metadata + BM25 + vector → RRF → top_k.

    Args:
        query: natural language search query
        filters: metadata constraints {year__gte: 2010, question_type: '解答题'}
        top_k: number of results
        weights: (vector_weight, bm25_weight, metadata_weight)

    Example:
        results = hybrid_search('二重积分 极坐标 中等难度',
                                {'year__gte': 2010, 'question_type': '解答题'})
    """
    w_vector, w_bm25, w_meta = weights

    # Step 1: Metadata filter
    docs = metadata_filter(filters or {})

    if not docs:
        return []

    # Step 2: BM25
    bm25_ranked = bm25_score(query, docs)

    # Step 3: Vector (concept overlap)
    vec_ranked = vector_score(query, docs)

    # Step 4: RRF fusion
    fused = rrf_fusion([vec_ranked, bm25_ranked])

    # Return top_k
    results = []
    for doc, score in fused[:top_k]:
        doc['_search_score'] = round(score, 4)
        results.append(doc)

    return results


# ═══════════════════════════════════════════════
# Convenience: search with natural language
# ═══════════════════════════════════════════════

def quick_search(query: str, top_k: int = 5) -> list[dict]:
    """Quick search without filters."""
    return hybrid_search(query, top_k=top_k)


if __name__ == '__main__':
    # Demo
    results = hybrid_search(
        '二重积分 极坐标换元 中等偏难 解答题',
        {'year__gte': 2010},
        top_k=5
    )
    for r in results:
        print(f"{r['question_id']} ({r['question_type']}, {r['difficulty']}) "
              f"kp={r.get('knowledge_points',[])} score={r['_search_score']}")
