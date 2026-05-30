"""
用户闭环 — 做题→批改→诊断→错题入库→画像更新

支持两种模式:
  - offline: 用存储的standard_answer做基础对比（无需LLM）
  - online:  用LLM Agent做完整批改+诊断（需要API Key）
"""

import json
import time
from dataclasses import dataclass, field


@dataclass
class PracticeResult:
    """一次做题的完整结果"""
    question_id: str = ""
    question: str = ""
    student_answer: str = ""
    standard_answer: str = ""
    score: float = 0.0
    total_score: float = 10.0
    is_correct: bool = False
    error_type: str = ""
    error_reason: str = ""
    knowledge_point: str = ""
    question_type: str = ""
    difficulty: str = "中等"
    mode: str = "offline"  # offline | online
    warnings: list[str] = field(default_factory=list)


class UserLoop:
    """用户做题闭环编排器"""

    def __init__(self, question_db=None, memory_agent=None, llm_client=None):
        self.db = question_db
        self.memory = memory_agent
        self.llm_client = llm_client

    def select_question(self, math_type="数学一", question_type=None,
                        knowledge_point=None, difficulty=None) -> dict | None:
        """从题库选题"""
        if self.db is None:
            return None
        filters = {"limit": 1}
        if math_type:
            filters["math_type"] = math_type
        if question_type:
            filters["question_type"] = question_type
        if knowledge_point:
            filters["knowledge_point"] = knowledge_point
        if difficulty:
            filters["difficulty"] = difficulty
        results = self.db.search(**filters)
        return results[0] if results else None

    def submit_answer(self, question: dict, student_answer: str) -> PracticeResult:
        """提交作答，返回批改结果"""
        qid = question.get("question_id", "")
        qtext = question.get("raw_question_text") or question.get("question", "")
        std_ans = question.get("standard_answer", "")
        qtype = question.get("question_type", "解答题")
        kp = ", ".join(question.get("knowledge_points", []))
        difficulty = question.get("difficulty", "中等")
        total_score = question.get("score", 10)

        result = PracticeResult(
            question_id=qid,
            question=qtext,
            student_answer=student_answer,
            standard_answer=std_ans,
            total_score=total_score,
            knowledge_point=kp,
            question_type=qtype,
            difficulty=difficulty,
        )

        if self.llm_client:
            self._grade_online(result, question, student_answer)
        else:
            self._grade_offline(result)

        self._diagnose(result)

        # 错题入库
        if self.memory and not result.is_correct:
            self._save_error(result)

        return result

    def _grade_offline(self, result: PracticeResult):
        """离线批改：基于存储的standard_answer做基础对比"""
        std = result.standard_answer.strip()
        stu = result.student_answer.strip()

        if not std:
            result.score = 0
            result.is_correct = False
            result.error_reason = "无标准答案可供对比"
            result.warnings.append("offline: no standard answer available")
            return

        if not stu:
            result.score = 0
            result.is_correct = False
            result.error_reason = "未作答"
            result.warnings.append("offline: empty student answer")
            return

        # 选择题快速对比
        if result.question_type == "选择题":
            # 提取选项字母
            import re
            std_letter = _extract_choice_letter(std)
            stu_letter = _extract_choice_letter(stu)
            if std_letter and stu_letter:
                result.is_correct = (std_letter == stu_letter)
                result.score = result.total_score if result.is_correct else 0
                if not result.is_correct:
                    result.error_type = "选择题答案错误"
                    result.error_reason = f"正确: {std_letter}, 你的: {stu_letter}"
                return

        # 填空题/解答题：简单文本匹配
        if std in stu or stu in std:
            result.is_correct = True
            result.score = result.total_score
        elif len(stu) > 5 and len(std) > 5:
            # 模糊匹配
            from difflib import SequenceMatcher
            sim = SequenceMatcher(None, std[:200], stu[:200]).ratio()
            if sim > 0.85:
                result.is_correct = True
                result.score = result.total_score * 0.9
            elif sim > 0.60:
                result.score = result.total_score * 0.5
                result.error_reason = f"与标准答案部分匹配 (相似度{sim:.0%})"
            else:
                result.score = result.total_score * 0.1
                result.error_reason = f"与标准答案差异较大 (相似度{sim:.0%})"
        else:
            result.score = result.total_score * 0.3
            result.error_reason = "答案过短，无法精确对比"

        result.is_correct = result.score >= result.total_score * 0.85
        result.mode = "offline"

    def _grade_online(self, result: PracticeResult, question: dict, student_answer: str):
        """在线批改：优先用题库缓存答案，无缓存时才调用LLM"""
        from agents import SolverAgent, GradingAgent
        model = "deepseek-chat"

        # 题库已有标准答案 → 直接使用，跳过LLM生成
        cached_answer = question.get("standard_answer", "")
        if cached_answer and len(cached_answer.strip()) > 1:
            solution = {
                "success": True,
                "standard_answer": cached_answer,
                "total_score": question.get("score", 10),
            }
        else:
            try:
                solver = SolverAgent(self.llm_client, model)
                solution = solver.solve(
                    question=result.question,
                    math_type="数学一",
                    question_type=result.question_type,
                    knowledge_point=result.knowledge_point,
                )
            except Exception:
                solution = {"success": False, "standard_answer": "", "total_score": 10}

        try:
            if solution.get("success"):
                result.standard_answer = solution.get("standard_answer", "")
                result.total_score = solution.get("total_score", 10)

            grading = GradingAgent(self.llm_client, model)
            gresult = grading.grade(
                question=result.question,
                standard_answer=result.standard_answer,
                student_answer=student_answer,
                total_score=result.total_score,
                knowledge_points=result.knowledge_point,
                difficulty=result.difficulty,
                question_type=result.question_type,
            )
            if gresult.get("success"):
                result.score = gresult.get("total", 0)
                result.is_correct = result.score >= result.total_score * 0.85
            else:
                result.warnings.append(f"online grading failed: {gresult.get('comment', '')}")
                self._grade_offline(result)  # fallback
        except Exception as e:
            result.warnings.append(f"online error: {e}")
            self._grade_offline(result)  # fallback

        result.mode = "online"

    def _diagnose(self, result: PracticeResult):
        """错因诊断"""
        if result.is_correct:
            result.error_type = "无错误"
            return

        # 本地诊断
        if not result.error_type:
            stu = result.student_answer.strip()
            if not stu:
                result.error_type = "未作答"
            elif len(stu) < 10:
                result.error_type = "答案不完整"
            else:
                result.error_type = "答案错误"

        # LLM深度诊断
        if self.llm_client and not result.is_correct:
            try:
                from agents import DiagnosisAgent
                diagnosis = DiagnosisAgent(self.llm_client)
                history = self.memory.get_errors(knowledge_point=result.knowledge_point) if self.memory else []
                dresult = diagnosis.diagnose(
                    question=result.question,
                    student_answer=result.student_answer,
                    standard_answer=result.standard_answer,
                    grading_result={"total": result.score, "deductions": []},
                    error_history=history,
                )
                if dresult.get("error_type") and dresult["error_type"] != "未识别":
                    result.error_type = dresult["error_type"]
                    result.error_reason = dresult.get("root_cause", result.error_reason)
            except Exception:
                pass  # keep local diagnosis

    def _save_error(self, result: PracticeResult):
        """保存错题"""
        if self.memory is None:
            return
        record = {
            "math_type": "数学一",
            "question": result.question[:500],
            "student_answer": result.student_answer[:500],
            "standard_answer": result.standard_answer[:500],
            "knowledge_point": result.knowledge_point,
            "question_type": result.question_type,
            "difficulty": result.difficulty,
            "score": result.score,
            "total_score": result.total_score,
            "error_type": result.error_type,
            "error_reason": result.error_reason,
            "question_id": result.question_id,
        }
        self.memory.add_error(record)

    def get_recommendations(self, count: int = 5) -> list[dict]:
        """获取推荐题目（基于薄弱知识点 + 知识图谱扩展）"""
        if self.memory is None or self.db is None:
            return []

        profile = self.memory.get_profile()
        weak_points = profile.get("weak_points", [])
        if not weak_points:
            # 无薄弱点 → 随机推荐中等难度
            return self._search_questions({"difficulty": "中等"}, count)

        recs = []
        seen_ids = set()

        # 1. 直接薄弱知识点
        for kp in weak_points[:3]:
            qs = self._search_questions({"knowledge_point": kp}, 3)
            for q in qs:
                if q["question_id"] not in seen_ids:
                    recs.append(q)
                    seen_ids.add(q["question_id"])

        # 2. 相关知识点（知识图谱扩展）
        related = self._get_related_topics(weak_points[0]) if weak_points else []
        for kp in related[:3]:
            qs = self._search_questions({"knowledge_point": kp}, 2)
            for q in qs:
                if q["question_id"] not in seen_ids and len(recs) < count:
                    recs.append(q)
                    seen_ids.add(q["question_id"])

        # 3. 填充：同题型不同知识点
        if len(recs) < count:
            error_stats = self.memory.get_error_stats()
            by_type = error_stats.get("by_type", {})
            worst_type = max(by_type, key=by_type.get) if by_type else "概念错误"
            type_to_qtype = {
                "概念错误": "选择题", "计算错误": "填空题",
                "推导错误": "解答题", "审题错误": "选择题",
            }
            qtype = type_to_qtype.get(worst_type, "解答题")
            qs = self._search_questions({"question_type": qtype, "difficulty": "中等"}, count - len(recs))
            for q in qs:
                if q["question_id"] not in seen_ids:
                    recs.append(q)
                    seen_ids.add(q["question_id"])

        return recs[:count]

    def _search_questions(self, filters: dict, limit: int) -> list[dict]:
        """搜索题目"""
        if self.db is None:
            return []
        filters["limit"] = limit
        try:
            return self.db.search(**filters)
        except Exception:
            return []

    def _get_related_topics(self, topic: str) -> list[str]:
        """从知识图谱获取相关知识点"""
        # 预定义的知识点关联
        related_map = {
            "极限与连续": ["导数与微分", "中值定理", "无穷级数"],
            "导数与微分": ["极限与连续", "中值定理", "不定积分"],
            "中值定理": ["导数与微分", "极限与连续"],
            "不定积分": ["定积分", "导数与微分", "微分方程"],
            "定积分": ["不定积分", "定积分应用", "二重积分"],
            "定积分应用": ["定积分", "二重积分"],
            "微分方程": ["不定积分", "定积分", "导数与微分"],
            "多元函数微分": ["导数与微分", "二重积分"],
            "二重积分": ["定积分", "三重积分", "曲线曲面积分"],
            "三重积分": ["二重积分", "曲线曲面积分"],
            "曲线曲面积分": ["二重积分", "三重积分", "向量代数与空间解析几何"],
            "无穷级数": ["极限与连续", "幂级数"],
            "向量代数与空间解析几何": ["曲线曲面积分", "多元函数微分"],
            "行列式": ["矩阵运算", "线性方程组"],
            "矩阵运算": ["行列式", "特征值与特征向量", "线性方程组"],
            "线性方程组": ["矩阵运算", "向量组与线性空间"],
            "向量组与线性空间": ["线性方程组", "特征值与特征向量"],
            "特征值与特征向量": ["矩阵运算", "二次型", "向量组与线性空间"],
            "二次型": ["特征值与特征向量", "矩阵运算"],
            "随机事件与概率": ["条件概率与独立性", "随机变量及其分布"],
            "条件概率与独立性": ["随机事件与概率", "随机变量及其分布"],
            "随机变量及其分布": ["数字特征", "多维随机变量"],
            "多维随机变量": ["随机变量及其分布", "数字特征"],
            "数字特征": ["随机变量及其分布", "大数定律与中心极限定理"],
            "数理统计": ["数字特征", "随机变量及其分布"],
        }
        return related_map.get(topic, [])

    def get_stats(self) -> dict:
        """获取用户统计"""
        if self.memory is None:
            return {"total_errors": 0, "by_type": {}, "repeat_rate": 0}
        return self.memory.get_error_stats()


def _extract_choice_letter(text: str) -> str | None:
    """从文本中提取选择题答案字母"""
    import re
    # 单字母: A, B, C, D
    m = re.search(r'\b([A-D])\b', text.strip())
    if m:
        return m.group(1)
    # 括号: (A), （B）
    m = re.search(r'[（(]([A-D])[）)]', text)
    if m:
        return m.group(1)
    return None
