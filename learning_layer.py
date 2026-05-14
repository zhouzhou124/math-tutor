"""learning_layer.py — 学习层 (Learning Layer)

负责：长期学习分析

分析内容：
  - 知识点掌握度
  - 高频错误
  - 方法偏好
  - 易错步骤

架构：
  ┌─────────────────────────────────────────────────────────────┐
  │                   Learning Layer                                │
  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
  │  │MasteryTracker│  │ErrorAnalyzer │  │MethodProfiler│     │
  │  │   掌握度追踪 │  │   错误分析   │  │   方法画像   │     │
  │  └──────────────┘  └──────────────┘  └──────────────┘     │
  │                           │                                   │
  │                    LearningAnalyzer                           │
  │                       学习分析器                              │
  └─────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses_json import dataclass_json

from diagnosis_layer import DiagnosisErrorType


# ═══════════════════════════════════════════════
# 数据模型定义
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class KnowledgePointMastery:
    """知识点掌握度"""
    topic: str
    topic_display: str
    total_attempts: int = 0
    correct_attempts: int = 0
    mastery_level: float = 0.0
    trend: str = "stable"
    last_practiced: str = ""
    weak_aspects: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class ErrorPattern:
    """错误模式"""
    error_type: str
    frequency: int = 0
    severity: str = ""
    affected_topics: List[str] = field(default_factory=list)
    recent_occurrences: List[str] = field(default_factory=list)
    suggestion: str = ""


@dataclass_json
@dataclass
class MethodPreference:
    """方法偏好"""
    method_name: str
    method_display: str
    usage_count: int = 0
    success_rate: float = 0.0
    average_score: float = 0.0
    is_preferred: bool = False


@dataclass_json
@dataclass
class ErrorStepPattern:
    """易错步骤模式"""
    step_type: str
    step_display: str
    error_count: int = 0
    total_count: int = 0
    error_rate: float = 0.0
    examples: List[str] = field(default_factory=list)


@dataclass_json
@dataclass
class LearningReport:
    """学习分析报告"""
    student_id: str
    report_date: str
    knowledge_mastery: List[KnowledgePointMastery] = field(default_factory=list)
    error_patterns: List[ErrorPattern] = field(default_factory=list)
    method_preferences: List[MethodPreference] = field(default_factory=list)
    error_step_patterns: List[ErrorStepPattern] = field(default_factory=list)
    overall_strengths: List[str] = field(default_factory=list)
    overall_weaknesses: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    study_time_range: str = ""


@dataclass_json
@dataclass
class PracticeRecord:
    """练习记录"""
    question_id: str
    question_topic: str
    timestamp: str
    score: float
    max_score: float
    methods_used: List[str]
    errors_made: List[str]
    time_spent: int = 0


# ═══════════════════════════════════════════════
# 知识点映射
# ═══════════════════════════════════════════════

TOPIC_MAPPING = {
    "limit": {"display": "极限", "keywords": ["极限", "limit", "lim"]},
    "derivative": {"display": "导数", "keywords": ["导数", "derivative", "求导"]},
    "integral": {"display": "积分", "keywords": ["积分", "integral", "不定积分", "定积分"]},
    "taylor": {"display": "泰勒展开", "keywords": ["taylor", "泰勒", "麦克劳林"]},
    "l_hospital": {"display": "洛必达法则", "keywords": ["l'hospital", "洛必达", "洛比达"]},
    "mean_value": {"display": "中值定理", "keywords": ["中值定理", "mean value", "拉格朗日", "罗尔"]},
    "series": {"display": "级数", "keywords": ["级数", "series", "收敛", "发散"]},
    "differential": {"display": "微分方程", "keywords": ["微分方程", "differential equation"]},
    "algebra": {"display": "代数运算", "keywords": ["化简", "代数", "运算"]},
    "proof": {"display": "证明题", "keywords": ["证明", "proof", "QED"]}
}

ERROR_TYPE_MAPPING = {
    "conceptual_error": {"display": "概念错误", "severity": "一级(重)"},
    "algebraic_error": {"display": "代数错误", "severity": "二级(中)"},
    "arithmetic_error": {"display": "算术错误", "severity": "三级(轻)"},
    "logical_gap": {"display": "推理断裂", "severity": "二级(中)"},
    "method_error": {"display": "方法错误", "severity": "一级(重)"},
    "missing_step": {"display": "缺失步骤", "severity": "二级(中)"}
}

METHOD_MAPPING = {
    "taylor_expansion": {"display": "泰勒展开", "keywords": ["taylor", "泰勒"]},
    "l_hospital": {"display": "洛必达法则", "keywords": ["l'hospital", "洛必达"]},
    "mean_value_theorem": {"display": "中值定理", "keywords": ["中值定理", "mean value", "拉格朗日"]},
    "substitution": {"display": "换元法", "keywords": ["换元", "substitution", "令"]},
    "integration_by_parts": {"display": "分部积分", "keywords": ["分部积分", "integration by parts"]},
    "direct_computation": {"display": "直接计算", "keywords": ["直接", "代入", "计算"]},
    "proof_by_contradiction": {"display": "反证法", "keywords": ["反证", "contradiction"]},
    "mathematical_induction": {"display": "数学归纳法", "keywords": ["归纳", "induction"]}
}


# ═══════════════════════════════════════════════
# 掌握度追踪器
# ═══════════════════════════════════════════════

class MasteryTracker:
    """知识点掌握度追踪器"""

    @staticmethod
    def calculate_mastery(
        topic: str,
        practice_history: List[PracticeRecord]
    ) -> KnowledgePointMastery:
        """计算某个知识点的掌握度"""
        topic_info = TOPIC_MAPPING.get(topic, {"display": topic})
        topic_practices = [
            p for p in practice_history
            if topic in p.question_topic.lower() or
               any(kw in p.question_topic.lower() for kw in topic_info.get("keywords", []))
        ]

        total = len(topic_practices)
        if total == 0:
            return KnowledgePointMastery(
                topic=topic,
                topic_display=topic_info["display"],
                mastery_level=0.0,
                trend="no_data"
            )

        correct = sum(1 for p in topic_practices if p.score >= p.max_score * 0.8)
        mastery = correct / total

        recent_practices = topic_practices[-5:] if len(topic_practices) > 5 else topic_practices
        if len(recent_practices) >= 3:
            recent_correct = sum(1 for p in recent_practices if p.score >= p.max_score * 0.8)
            older_practices = topic_practices[:-5] if len(topic_practices) > 5 else topic_practices[:-3]
            older_correct = sum(1 for p in older_practices if p.score >= p.max_score * 0.8) if older_practices else 0

            if recent_correct / len(recent_practices) > older_correct / len(older_practices) + 0.1:
                trend = "improving"
            elif recent_correct / len(recent_practices) < older_correct / len(older_practices) - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        weak_aspects = MasteryTracker._identify_weak_aspects(topic_practices)

        return KnowledgePointMastery(
            topic=topic,
            topic_display=topic_info["display"],
            total_attempts=total,
            correct_attempts=correct,
            mastery_level=mastery,
            trend=trend,
            last_practiced=topic_practices[-1].timestamp if topic_practices else "",
            weak_aspects=weak_aspects
        )

    @staticmethod
    def _identify_weak_aspects(practices: List[PracticeRecord]) -> List[str]:
        """识别薄弱环节"""
        error_freq = {}
        for p in practices:
            for error in p.errors_made:
                error_freq[error] = error_freq.get(error, 0) + 1

        weak = sorted(error_freq.items(), key=lambda x: x[1], reverse=True)[:3]
        return [f"{ERROR_TYPE_MAPPING.get(e, {'display': e})['display']}({cnt}次)" for e, cnt in weak]


# ═══════════════════════════════════════════════
# 错误分析器
# ═══════════════════════════════════════════════

class ErrorAnalyzer:
    """错误模式分析器"""

    @staticmethod
    def analyze_error_patterns(
        practice_history: List[PracticeRecord]
    ) -> List[ErrorPattern]:
        """分析错误模式"""
        error_freq = {}
        error_topics = {}

        for p in practice_history:
            for error in p.errors_made:
                if error not in error_freq:
                    error_freq[error] = 0
                    error_topics[error] = []
                error_freq[error] += 1
                error_topics[error].append(p.question_topic)

        patterns = []
        for error_type, freq in sorted(error_freq.items(), key=lambda x: x[1], reverse=True):
            error_info = ERROR_TYPE_MAPPING.get(error_type, {"display": error_type, "severity": "未知"})

            recent = [p for p in practice_history if error_type in p.errors_made][-3:]
            recent_times = [p.timestamp for p in recent]

            patterns.append(ErrorPattern(
                error_type=error_type,
                frequency=freq,
                severity=error_info["severity"],
                affected_topics=list(set(error_topics[error_type]))[:5],
                recent_occurrences=recent_times,
                suggestion=ErrorAnalyzer._get_error_suggestion(error_type)
            ))

        return patterns[:10]

    @staticmethod
    def _get_error_suggestion(error_type: str) -> str:
        """获取错误建议"""
        suggestions = {
            "conceptual_error": "建议重新学习相关概念，确保理解定理的适用条件和正确用法",
            "algebraic_error": "建议多做代数运算练习，注意符号和化简规则",
            "arithmetic_error": "建议仔细检查计算过程，可以尝试验算",
            "logical_gap": "建议补充推导步骤，使逻辑更加连贯",
            "method_error": "建议学习更多解题方法，选择最合适的方法",
            "missing_step": "建议在关键步骤处详细写出推导过程"
        }
        return suggestions.get(error_type, "建议复习相关知识点")


# ═══════════════════════════════════════════════
# 方法画像器
# ═══════════════════════════════════════════════

class MethodProfiler:
    """方法使用画像"""

    @staticmethod
    def analyze_method_preferences(
        practice_history: List[PracticeRecord]
    ) -> List[MethodPreference]:
        """分析学生的方法偏好"""
        method_stats = {}

        for p in practice_history:
            for method in p.methods_used:
                if method not in method_stats:
                    method_stats[method] = {
                        "usage": 0,
                        "total_score": 0.0,
                        "correct": 0
                    }
                method_stats[method]["usage"] += 1
                method_stats[method]["total_score"] += p.score / p.max_score * 100
                if p.score >= p.max_score * 0.8:
                    method_stats[method]["correct"] += 1

        preferences = []
        for method, stats in method_stats.items():
            method_info = METHOD_MAPPING.get(method, {"display": method})
            success_rate = stats["correct"] / stats["usage"] if stats["usage"] > 0 else 0
            avg_score = stats["total_score"] / stats["usage"] if stats["usage"] > 0 else 0

            preferences.append(MethodPreference(
                method_name=method,
                method_display=method_info["display"],
                usage_count=stats["usage"],
                success_rate=success_rate,
                average_score=avg_score
            ))

        preferences.sort(key=lambda x: x.usage_count, reverse=True)
        if preferences:
            max_usage = preferences[0].usage_count
            for p in preferences:
                p.is_preferred = p.usage_count >= max_usage * 0.5

        return preferences


# ═══════════════════════════════════════════════
# 易错步骤分析器
# ═══════════════════════════════════════════════

class ErrorStepAnalyzer:
    """易错步骤分析器"""

    @staticmethod
    def analyze_error_step_patterns(
        practice_history: List[PracticeRecord]
    ) -> List[ErrorStepPattern]:
        """分析易错步骤模式"""
        step_stats = {}

        step_type_keywords = {
            "start": ["开始", "start", "题目"],
            "condition_check": ["条件", "condition", "验证"],
            "apply_method": ["应用", "使用", "采用"],
            "derive": ["推导", "derive", "计算"],
            "simplify": ["化简", "simplify", "变形"],
            "conclude": ["结论", "conclude", "所以"]
        }

        for p in practice_history:
            for method in p.methods_used:
                for step_type, keywords in step_type_keywords.items():
                    if any(kw in method.lower() for kw in keywords):
                        if step_type not in step_stats:
                            step_stats[step_type] = {"total": 0, "errors": 0, "examples": []}
                        step_stats[step_type]["total"] += 1
                        if any(e in p.errors_made for e in ERROR_TYPE_MAPPING.keys()):
                            step_stats[step_type]["errors"] += 1
                            if len(step_stats[step_type]["examples"]) < 3:
                                step_stats[step_type]["examples"].append(
                                    f"{p.question_topic} ({p.timestamp})"
                                )

        patterns = []
        for step_type, stats in step_stats.items():
            error_rate = stats["errors"] / stats["total"] if stats["total"] > 0 else 0
            display_names = {
                "start": "起始步骤",
                "condition_check": "条件验证",
                "apply_method": "方法应用",
                "derive": "推导计算",
                "simplify": "化简变形",
                "conclude": "得出结论"
            }

            patterns.append(ErrorStepPattern(
                step_type=step_type,
                step_display=display_names.get(step_type, step_type),
                error_count=stats["errors"],
                total_count=stats["total"],
                error_rate=error_rate,
                examples=stats["examples"]
            ))

        patterns.sort(key=lambda x: x.error_rate, reverse=True)
        return patterns


# ═══════════════════════════════════════════════
# 学习分析器
# ═══════════════════════════════════════════════

class LearningAnalyzer:
    """
    学习分析器

    综合分析学生的学习数据，生成完整的学习报告
    """

    def __init__(self, student_id: str = "default"):
        self.student_id = student_id
        self.mastery_tracker = MasteryTracker()
        self.error_analyzer = ErrorAnalyzer()
        self.method_profiler = MethodProfiler()
        self.error_step_analyzer = ErrorStepAnalyzer()

    def generate_learning_report(
        self,
        practice_history: List[PracticeRecord],
        time_range_days: int = 30
    ) -> LearningReport:
        """生成学习分析报告"""

        cutoff_date = datetime.now() - timedelta(days=time_range_days)
        recent_practices = [
            p for p in practice_history
            if datetime.strptime(p.timestamp, "%Y-%m-%d %H:%M:%S") >= cutoff_date
        ] if practice_history else []

        knowledge_mastery = self._analyze_knowledge_mastery(recent_practices)
        error_patterns = self.error_analyzer.analyze_error_patterns(recent_practices)
        method_preferences = self.method_profiler.analyze_method_preferences(recent_practices)
        error_step_patterns = self.error_step_analyzer.analyze_error_step_patterns(recent_practices)

        strengths = self._identify_strengths(knowledge_mastery, method_preferences)
        weaknesses = self._identify_weaknesses(knowledge_mastery, error_patterns, error_step_patterns)
        recommendations = self._generate_recommendations(
            knowledge_mastery, error_patterns, method_preferences
        )

        time_range = f"最近{time_range_days}天"

        return LearningReport(
            student_id=self.student_id,
            report_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            knowledge_mastery=knowledge_mastery,
            error_patterns=error_patterns,
            method_preferences=method_preferences,
            error_step_patterns=error_step_patterns,
            overall_strengths=strengths,
            overall_weaknesses=weaknesses,
            recommendations=recommendations,
            study_time_range=time_range
        )

    def _analyze_knowledge_mastery(
        self,
        practices: List[PracticeRecord]
    ) -> List[KnowledgePointMastery]:
        """分析各知识点掌握度"""
        mastery_list = []
        for topic in TOPIC_MAPPING.keys():
            mastery = self.mastery_tracker.calculate_mastery(topic, practices)
            if mastery.total_attempts > 0:
                mastery_list.append(mastery)

        mastery_list.sort(key=lambda x: x.mastery_level)
        return mastery_list

    def _identify_strengths(
        self,
        mastery: List[KnowledgePointMastery],
        methods: List[MethodPreference]
    ) -> List[str]:
        """识别优势"""
        strengths = []

        high_mastery = [m for m in mastery if m.mastery_level >= 0.8]
        for m in high_mastery:
            strengths.append(f"{m.topic_display}掌握良好（{m.mastery_level:.0%}正确率）")

        preferred_success = [m for m in methods if m.is_preferred and m.success_rate >= 0.8]
        for m in preferred_success:
            strengths.append(f"擅长使用{m.method_display}（{m.success_rate:.0%}成功率）")

        return strengths[:5]

    def _identify_weaknesses(
        self,
        mastery: List[KnowledgePointMastery],
        errors: List[ErrorPattern],
        error_steps: List[ErrorStepPattern]
    ) -> List[str]:
        """识别薄弱环节"""
        weaknesses = []

        low_mastery = [m for m in mastery if m.mastery_level < 0.5]
        for m in low_mastery:
            weaknesses.append(f"{m.topic_display}需要加强（{m.mastery_level:.0%}正确率）")

        frequent_errors = errors[:3]
        for e in frequent_errors:
            weaknesses.append(f"{ERROR_TYPE_MAPPING.get(e.error_type, {'display': e.error_type})['display']}频发")

        high_error_steps = [s for s in error_steps if s.error_rate > 0.3][:2]
        for s in high_error_steps:
            weaknesses.append(f"{s.step_display}容易出错（{s.error_rate:.0%}错误率）")

        return weaknesses[:5]

    def _generate_recommendations(
        self,
        mastery: List[KnowledgePointMastery],
        errors: List[ErrorPattern],
        methods: List[MethodPreference]
    ) -> List[str]:
        """生成学习建议"""
        recommendations = []

        if errors:
            top_error = errors[0]
            recommendations.append(f"重点改进：{ERROR_TYPE_MAPPING.get(top_error.error_type, {'display': top_error.error_type})['display']}")

        low_mastery_topics = [m for m in mastery if m.mastery_level < 0.6]
        if low_mastery_topics:
            topics_str = "、".join([m.topic_display for m in low_mastery_topics[:3]])
            recommendations.append(f"建议加强练习：{topics_str}")

        preferred_but_low_success = [
            m for m in methods
            if m.is_preferred and m.success_rate < 0.6
        ]
        for m in preferred_but_low_success:
            recommendations.append(f"您常用的{m.method_display}方法成功率较低，建议深入学习该方法的技巧")

        if len(recommendations) < 3:
            recommendations.append("建议每天坚持练习，保持手感")
            recommendations.append("注意总结错题，避免重复犯错")

        return recommendations[:5]


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def generate_learning_report(
    student_id: str,
    practice_history: List[PracticeRecord],
    time_range_days: int = 30
) -> LearningReport:
    """快速生成学习报告"""
    analyzer = LearningAnalyzer(student_id)
    return analyzer.generate_learning_report(practice_history, time_range_days)


def format_learning_report_text(report: LearningReport) -> str:
    """格式化学习报告为文本"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"【学习分析报告】- {report.report_date}")
    lines.append(f"学生ID: {report.student_id}")
    lines.append(f"统计周期: {report.study_time_range}")
    lines.append("=" * 60)

    lines.append("\n## 知识点掌握度")
    if report.knowledge_mastery:
        for m in report.knowledge_mastery[:5]:
            trend_icon = {"improving": "↑", "declining": "↓", "stable": "→", "no_data": "?"}.get(m.trend, "?")
            lines.append(f"  {m.topic_display}: {m.mastery_level:.0%} {trend_icon}")
            lines.append(f"    练习次数: {m.total_attempts}, 正确: {m.correct_attempts}")
    else:
        lines.append("  暂无数据")

    lines.append("\n## 高频错误")
    if report.error_patterns:
        for e in report.error_patterns[:5]:
            lines.append(f"  [{e.severity}] {ERROR_TYPE_MAPPING.get(e.error_type, {'display': e.error_type})['display']} - {e.frequency}次")
            lines.append(f"    建议: {e.suggestion}")
    else:
        lines.append("  暂无数据")

    lines.append("\n## 方法偏好")
    if report.method_preferences:
        for m in report.method_preferences[:5]:
            pref_icon = "★" if m.is_preferred else "☆"
            lines.append(f"  {pref_icon} {m.method_display}: 使用{m.usage_count}次，成功率{m.success_rate:.0%}")
    else:
        lines.append("  暂无数据")

    lines.append("\n## 易错步骤")
    if report.error_step_patterns:
        for s in report.error_step_patterns[:3]:
            lines.append(f"  {s.step_display}: {s.error_rate:.0%}错误率")
    else:
        lines.append("  暂无数据")

    lines.append("\n## 优势")
    if report.overall_strengths:
        for s in report.overall_strengths:
            lines.append(f"  [+] {s}")
    else:
        lines.append("  暂无明显优势")

    lines.append("\n## 薄弱环节")
    if report.overall_weaknesses:
        for w in report.overall_weaknesses:
            lines.append(f"  [-] {w}")
    else:
        lines.append("  暂无明显薄弱环节")

    lines.append("\n## 学习建议")
    if report.recommendations:
        for i, r in enumerate(report.recommendations, 1):
            lines.append(f"  {i}. {r}")
    else:
        lines.append("  暂无建议")

    lines.append("=" * 60)

    return "\n".join(lines)
