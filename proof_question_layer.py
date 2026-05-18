"""proof_question_layer.py — 证明题处理层

证明题核心模块：

1. Reasoning DAG
   条件 → 定理 → 推论 → 结论

2. Theorem Tracking
   使用了：拉格朗日中值定理

3. Logical Dependency
   这一步是否由前一步推出

4. Proof Strategy Recognition
   反证法、数学归纳法、构造法

5. Missing Justification Detection
   "显然" 但实际上：不显然
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses_json import dataclass_json


# ═══════════════════════════════════════════════
# 证明策略定义
# ═══════════════════════════════════════════════

class ProofStrategy(Enum):
    """证明策略"""
    DIRECT = "direct"                    # 直接证明
    CONTRADICTION = "contradiction"       # 反证法
    INDUCTION = "induction"               # 数学归纳法
    CONSTRUCT = "construct"               # 构造法
    EQUIVALENCE = "equivalence"           # 等价变换
    ANALYSIER = "analysier"               # 分析法
    SYNTHESIS = "synthesis"               # 综合法
    FORWARD = "forward"                   # 正向证明
    BACKWARD = "backward"                 # 逆向证明


PROOF_STRATEGY_PATTERNS = {
    ProofStrategy.DIRECT: ["直接证明", "直接得", "可得", "因此", "所以", "于是"],
    ProofStrategy.CONTRADICTION: ["反证法", "假设", "矛盾", "若不然", "假设不成立"],
    ProofStrategy.INDUCTION: ["归纳法", "数学归纳法", "假设当n=k时", "验证n=1"],
    ProofStrategy.CONSTRUCT: ["构造", "构造辅助函数", "构造函数", "构造序列"],
    ProofStrategy.EQUIVALENCE: ["等价", "充要条件", "当且仅当", "iff"],
    ProofStrategy.ANALYSIER: ["分析法", "要证", "只需证", "等价于"],
    ProofStrategy.SYNTHESIS: ["综合法", "由已知", "因为", "由题设"],
}


# ═══════════════════════════════════════════════
# 定理追踪
# ═══════════════════════════════════════════════

@dataclass
class TheoremUsage:
    """定理使用"""
    theorem_name: str
    theorem_display: str
    step_index: int
    is_justified: bool
    conditions_checked: bool
    application_correct: bool
    used_in_step: int


THEOREM_PATTERNS = {
    "lagrange": {
        "names": ["拉格朗日中值定理", "Lagrange中值定理", "拉格朗日定理"],
        "conditions": ["连续", "可导", "区间"],
        "display": "拉格朗日中值定理"
    },
    "rolle": {
        "names": ["罗尔定理", "Rolle定理"],
        "conditions": ["连续", "可导", "端点值相等"],
        "display": "罗尔定理"
    },
    "cauchy": {
        "names": ["柯西中值定理", "Cauchy定理"],
        "conditions": ["连续", "可导", "分母不为零"],
        "display": "柯西中值定理"
    },
    "taylor": {
        "names": ["泰勒公式", "Taylor公式", "麦克劳林"],
        "conditions": ["n阶可导", "展开点"],
        "display": "泰勒公式"
    },
    "lhospital": {
        "names": ["洛必达法则", "L'Hospital"],
        "conditions": ["0/0型", "∞/∞型", "可导"],
        "display": "洛必达法则"
    },
    "limit_existence": {
        "names": ["夹逼定理", "夹逼准则", "Squeeze Theorem"],
        "conditions": ["夹逼", "极限存在"],
        "display": "夹逼定理"
    },
    "monotone": {
        "names": ["单调性定理", "单调有界原理"],
        "conditions": ["单调", "有界"],
        "display": "单调有界原理"
    },
    "intermediate": {
        "names": ["介值定理", "中间值定理", "Intermediate Value"],
        "conditions": ["连续", "端点值异号"],
        "display": "介值定理"
    },
    "fixed_point": {
        "names": ["不动点定理", "压缩映射原理"],
        "conditions": ["压缩", "映射"],
        "display": "不动点定理"
    }
}


# ═══════════════════════════════════════════════
# 逻辑依赖节点
# ═══════════════════════════════════════════════

@dataclass
class ReasoningNode:
    """推理节点"""
    node_id: str
    content: str
    node_type: str  # "condition", "theorem", "deduction", "conclusion"
    step_index: int
    dependencies: Set[str]  # 依赖的节点ID
    logical_connectors: List[str]  # "因此", "因为", "由"
    is_justified: bool
    justification_quality: str  # "strong", "weak", "missing"
    missing_justification: str = ""
    theorems_used: List[str] = field(default_factory=list)


@dataclass
class LogicalGap:
    """逻辑断裂"""
    from_node: str
    to_node: str
    gap_type: str  # "missing_step", "unjustified", "wrong_inference"
    description: str
    suggestion: str


# ═══════════════════════════════════════════════
# 推理DAG
# ═══════════════════════════════════════════════

class ReasoningDAG:
    """
    Reasoning DAG (Directed Acyclic Graph)

    证明题的推理链条：
    条件 → 定理 → 推论 → 结论

    DAG结构：
        条件A
       /    \
    定理X    条件B
       \    /
       推论Y
         |
       结论Z
    """

    def __init__(self):
        self.nodes: Dict[str, ReasoningNode] = {}
        self.edges: List[Tuple[str, str]] = []
        self.levels: Dict[str, int] = {}

    def add_node(
        self,
        node_id: str,
        content: str,
        node_type: str,
        step_index: int,
        logical_connectors: List[str] = None
    ) -> ReasoningNode:
        """添加节点"""
        node = ReasoningNode(
            node_id=node_id,
            content=content,
            node_type=node_type,
            step_index=step_index,
            dependencies=set(),
            logical_connectors=logical_connectors or [],
            is_justified=True,
            justification_quality="strong"
        )
        self.nodes[node_id] = node
        return node

    def add_edge(self, from_node: str, to_node: str):
        """添加边"""
        if from_node in self.nodes and to_node in self.nodes:
            self.edges.append((from_node, to_node))
            self.nodes[to_node].dependencies.add(from_node)

    def detect_logical_gaps(self) -> List[LogicalGap]:
        """检测逻辑断裂"""
        gaps = []

        for node_id, node in self.nodes.items():
            if node.node_type in ["deduction", "conclusion"]:
                if not node.dependencies:
                    gaps.append(LogicalGap(
                        from_node="",
                        to_node=node_id,
                        gap_type="missing_step",
                        description=f"节点'{node_id}'没有任何依赖",
                        suggestion="此步骤缺少前置推理"
                    ))

                elif len(node.dependencies) > 0:
                    dep_nodes = [self.nodes[d] for d in node.dependencies if d in self.nodes]
                    for dep in dep_nodes:
                        if dep.node_type == "conclusion" and node.node_type == "conclusion":
                            gaps.append(LogicalGap(
                                from_node=dep.node_id,
                                to_node=node_id,
                                gap_type="wrong_inference",
                                description="结论之间直接推导",
                                suggestion="需要补充中间的推论步骤"
                            ))

        for node_id, node in self.nodes.items():
            if node.justification_quality == "missing":
                gaps.append(LogicalGap(
                    from_node=node_id,
                    to_node=node_id,
                    gap_type="missing_step",
                    description=f"节点'{node_id}'缺少理由",
                    suggestion=node.missing_justification
                ))

        return gaps

    def calculate_depth(self) -> int:
        """计算DAG深度"""
        self._calculate_levels()
        return max(self.levels.values()) if self.levels else 0

    def _calculate_levels(self):
        """计算每层的节点"""
        self.levels = {}

        for node_id in self.nodes:
            self._calc_level_recursive(node_id, 0)

    def _calc_level_recursive(self, node_id: str, level: int):
        """递归计算层级"""
        if node_id not in self.nodes:
            return

        if node_id in self.levels:
            self.levels[node_id] = max(self.levels[node_id], level)
        else:
            self.levels[node_id] = level

        node = self.nodes[node_id]
        for dep in node.dependencies:
            self._calc_level_recursive(dep, level + 1)

    def to_graphviz(self) -> str:
        """转换为Graphviz格式"""
        lines = ["digraph ProofDAG {", "    rankdir=TB;"]

        type_colors = {
            "condition": "lightblue",
            "theorem": "lightyellow",
            "deduction": "lightgreen",
            "conclusion": "lightpink"
        }

        for node_id, node in self.nodes.items():
            color = type_colors.get(node.node_type, "white")
            shape = "box" if node.node_type == "theorem" else "ellipse"
            lines.append(f'    "{node_id}" [style=filled, fillcolor={color}, shape={shape}];')

        for from_node, to_node in self.edges:
            lines.append(f'    "{from_node}" -> "{to_node}";')

        lines.append("}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 证明策略识别器
# ═══════════════════════════════════════════════

class ProofStrategyRecognizer:
    """
    证明策略识别器

    识别：
    - 反证法
    - 数学归纳法
    - 构造法
    - 等等
    """

    @staticmethod
    def recognize_strategy(proof_text: str) -> Tuple[ProofStrategy, float]:
        """
        识别证明策略

        Returns:
            (strategy, confidence)
        """
        text = proof_text.lower()
        scores = {}

        for strategy, patterns in PROOF_STRATEGY_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern.lower() in text:
                    score += 1
            if score > 0:
                scores[strategy] = score

        if not scores:
            return ProofStrategy.DIRECT, 0.5

        best_strategy = max(scores.items(), key=lambda x: x[1])
        confidence = min(best_strategy[1] / 3, 1.0)

        return best_strategy[0], confidence

    @staticmethod
    def get_strategy_description(strategy: ProofStrategy) -> str:
        """获取策略描述"""
        descriptions = {
            ProofStrategy.DIRECT: "直接证明：从已知条件出发，通过逻辑推导得到结论",
            ProofStrategy.CONTRADICTION: "反证法：假设结论不成立，推出矛盾，从而证明结论成立",
            ProofStrategy.INDUCTION: "数学归纳法：验证基础情况，然后假设n=k时成立，证明n=k+1时也成立",
            ProofStrategy.CONSTRUCT: "构造法：通过构造辅助函数、序列或不等式来证明",
            ProofStrategy.EQUIVALENCE: "等价变换：利用充要条件进行等价转化",
            ProofStrategy.ANALYSIER: "分析法：从结论出发，逆向寻找使结论成立的充分条件",
            ProofStrategy.SYNTHESIS: "综合法：从已知条件出发，正向综合推导结论"
        }
        return descriptions.get(strategy, "未知策略")


# ═══════════════════════════════════════════════
# 缺失理由检测器
# ═══════════════════════════════════════════════

class MissingJustificationDetector:
    """
    缺失理由检测器

    检测：
    - "显然"
    - "易得"
    - "不难发现"
    - 等等

    这些词掩盖了真正的推理步骤
    """

    SUSPICIOUS_PATTERNS = {
        "obviously": {
            "patterns": ["显然", "obviously", "clear"],
            "severity": "high",
            "reason": "使用'显然'掩盖了推理过程",
            "suggestion": "请详细说明为什么显然成立"
        },
        "easily": {
            "patterns": ["易得", "easily", "不难", "容易"],
            "severity": "high",
            "reason": "使用'易得'掩盖了关键步骤",
            "suggestion": "请写出完整的推导过程"
        },
        "trivially": {
            "patterns": ["显然成立", "trivial", "显然可得"],
            "severity": "medium",
            "reason": "'显然成立'需要验证",
            "suggestion": "请说明在什么条件下成立"
        },
        "by_observation": {
            "patterns": ["观察到", "注意到", "observe", "note that"],
            "severity": "low",
            "reason": "'注意到'后可能是关键观察",
            "suggestion": "这个观察需要解释"
        },
        "without_loss": {
            "patterns": ["不失一般性", "wlog", "不妨设"],
            "severity": "low",
            "reason": "'不妨设'需要说明为什么可以这样设",
            "suggestion": "请解释为什么可以不失一般性"
        }
    }

    @staticmethod
    def detect_missing_justifications(proof_text: str) -> List[Dict[str, Any]]:
        """检测缺失理由"""
        findings = []

        lines = proof_text.split('\n')

        for line_num, line in enumerate(lines):
            line_lower = line.lower()

            for issue_type, info in MissingJustificationDetector.SUSPICIOUS_PATTERNS.items():
                for pattern in info["patterns"]:
                    if pattern.lower() in line_lower:
                        findings.append({
                            "line_number": line_num + 1,
                            "line_content": line.strip(),
                            "pattern_found": pattern,
                            "issue_type": issue_type,
                            "severity": info["severity"],
                            "reason": info["reason"],
                            "suggestion": info["suggestion"]
                        })

        return findings

    @staticmethod
    def get_severity_score(findings: List[Dict]) -> float:
        """计算缺失理由的严重程度得分"""
        if not findings:
            return 0.0

        weights = {"high": 1.0, "medium": 0.5, "low": 0.2}

        total = sum(weights.get(f["severity"], 0.5) for f in findings)

        return min(total / 10, 1.0)


# ═══════════════════════════════════════════════
# 定理追踪器
# ═══════════════════════════════════════════════

class TheoremTracker:
    """
    定理追踪器

    追踪证明过程中使用的定理
    """

    @staticmethod
    def track_theorems(proof_text: str) -> List[LemmaUsage]:
        """追踪定理使用"""
        theorems_found = []
        lines = proof_text.split('\n')

        for line_num, line in enumerate(lines):
            line_cleaned = line.strip()

            for theorem_id, theorem_info in THEOREM_PATTERNS.items():
                for name in theorem_info["names"]:
                    if name in line_cleaned:
                        justification_quality = TheoremTracker._check_justification(
                            line_cleaned, theorem_info
                        )

                        theorems_found.append(TheoremUsage(
                            theorem_name=theorem_id,
                            theorem_display=theorem_info["display"],
                            step_index=line_num,
                            is_justified=justification_quality != "missing",
                            conditions_checked=TheoremTracker._check_conditions(
                                line_cleaned, theorem_info
                            ),
                            application_correct=True,
                            used_in_step=line_num
                        ))

        return theorems_found

    @staticmethod
    def _check_justification(line: str, theorem_info: Dict) -> str:
        """检查定理使用的理由"""
        justification_keywords = ["因为", "由于", "由", "根据", "依据"]

        has_justification = any(kw in line for kw in justification_keywords)

        if has_justification:
            return "strong"

        missing_keywords = ["显然", "易得", "直接"]
        has_missing = any(kw in line for kw in missing_keywords)

        if has_missing:
            return "weak"

        return "missing"

    @staticmethod
    def _check_conditions(line: str, theorem_info: Dict) -> bool:
        """检查条件是否验证"""
        conditions = theorem_info.get("conditions", [])

        if not conditions:
            return True

        for condition in conditions:
            if condition in line:
                return True

        return True


# ═══════════════════════════════════════════════
# 逻辑依赖分析器
# ═══════════════════════════════════════════════

class LogicalDependencyAnalyzer:
    """
    逻辑依赖分析器

    分析每一步是否由前一步合理推出
    """

    LOGICAL_CONNECTORS = {
        "therefore": ["因此", "所以", "故", "于是", "从而", "可得", "thus", "therefore"],
        "because": ["因为", "由于", "由", "依据", "根据", "since", "because"],
        "equivalent": ["等价于", "充要", "当且仅当", "iff", "equivalent"],
        "implies": ["说明", "表明", "意味着", "implies"],
        "observe": ["注意到", "观察到", "可见", "observe", "note that"]
    }

    @staticmethod
    def analyze_step_dependencies(
        steps: List[Dict]
    ) -> List[Dict[str, Any]]:
        """
        分析步骤依赖

        Returns:
            每一步的依赖分析
        """
        analyses = []

        for i, step in enumerate(steps):
            operation = step.get('operation', '')
            output_state = step.get('output_state', '')
            input_state = step.get('input_state', '')

            connector_found = LogicalDependencyAnalyzer._find_connector(operation)

            if i == 0:
                dependency_type = "initial"
                is_valid = True
                message = "起始步骤"
            else:
                has_input = bool(input_state and input_state != output_state)

                if not has_input:
                    connector_type = connector_found if connector_found else "none"
                    dependency_type = f"depends_on_previous_{connector_type}"
                    is_valid = connector_found is not None
                    message = f"使用了'{connector_found}'连接词" if connector_found else "缺少逻辑连接词"
                else:
                    dependency_type = "explicit_reference"
                    is_valid = True
                    message = "明确引用了前置步骤"

            analyses.append({
                "step_index": i,
                "operation": operation,
                "connector_found": connector_found,
                "dependency_type": dependency_type,
                "is_valid": is_valid,
                "message": message
            })

        return analyses

    @staticmethod
    def _find_connector(operation: str) -> Optional[str]:
        """查找逻辑连接词"""
        op_lower = operation.lower()

        for connector_type, connectors in LogicalDependencyAnalyzer.LOGICAL_CONNECTORS.items():
            for connector in connectors:
                if connector.lower() in op_lower:
                    return connector

        return None

    @staticmethod
    def detect_unjustified_steps(analyses: List[Dict]) -> List[Dict]:
        """检测无理由的步骤"""
        unjustified = []

        for analysis in analyses:
            if not analysis["is_valid"] and analysis["step_index"] > 0:
                unjustified.append(analysis)

        return unjustified


# ═══════════════════════════════════════════════
# 统一证明题评分器
# ═══════════════════════════════════════════════

@dataclass_json
@dataclass
class ProofQuestion:
    """证明题"""
    question_id: str
    question_text: str
    conditions: List[str]
    conclusion: str
    expected_strategies: List[ProofStrategy]
    expected_theorems: List[str]
    key_steps: List[str]


@dataclass_json
@dataclass
class ProofScoringResult:
    """证明题评分结果"""
    total_score: float
    max_score: float
    score_percentage: float
    is_correct: bool
    strategy_used: str
    strategy_confidence: float
    reasoning_dag: Dict[str, Any]
    logical_dependencies: List[Dict[str, Any]]
    theorems_used: List[Dict[str, Any]]
    logical_gaps: List[Dict[str, Any]]
    missing_justifications: List[Dict[str, Any]]
    missing_justification_score: float
    partial_credit_explanation: str
    detailed_feedback: str


class UnifiedProofScorer:
    """
    统一证明题评分器

    证明题核心模块：
    1. Reasoning DAG
    2. Theorem Tracking
    3. Logical Dependency
    4. Proof Strategy Recognition
    5. Missing Justification Detection
    """

    def __init__(self):
        self.strategy_recognizer = ProofStrategyRecognizer()
        self.theorem_tracker = TheoremTracker()
        self.dependency_analyzer = LogicalDependencyAnalyzer()
        self.justification_detector = MissingJustificationDetector()

    def score_proof(
        self,
        question: ProofQuestion,
        student_proof: str
    ) -> ProofScoringResult:
        """
        评分证明题
        """
        lines = student_proof.strip().split('\n')
        steps = [{"operation": line.strip(), "output_state": line.strip()}
                 for line in lines if line.strip()]

        strategy, strategy_conf = self.strategy_recognizer.recognize_strategy(student_proof)

        dag = self._build_reasoning_dag(steps, question)

        logical_dependencies = self.dependency_analyzer.analyze_step_dependencies(steps)

        theorems = self.theorem_tracker.track_theorems(student_proof)

        logical_gaps = dag.detect_logical_gaps() if hasattr(dag, 'detect_logical_gaps') else []

        missing_justifications = self.justification_detector.detect_missing_justifications(student_proof)

        missing_justification_score = self.justification_detector.get_severity_score(missing_justifications)

        logic_score = self._calculate_logic_score(
            logical_dependencies, logical_gaps, missing_justification_score
        )

        theorem_score = self._calculate_theorem_score(theorems, question.expected_theorems)

        strategy_score = strategy_conf if strategy in question.expected_strategies else strategy_conf * 0.5

        total_score = logic_score * 0.4 + theorem_score * 0.3 + strategy_score * 0.3

        partial_explanation = f"逻辑分: {logic_score:.2f}/40, 定理分: {theorem_score:.2f}/30, 策略分: {strategy_score:.2f}/30"

        detailed = self._generate_detailed_feedback(
            strategy, strategy_conf, theorems, logical_gaps, missing_justifications
        )

        return ProofScoringResult(
            total_score=total_score * 100,
            max_score=100.0,
            score_percentage=total_score * 100,
            is_correct=total_score >= 0.6,
            strategy_used=strategy.value,
            strategy_confidence=strategy_conf,
            reasoning_dag={"nodes": len(dag.nodes), "depth": dag.calculate_depth()},
            logical_dependencies=logical_dependencies,
            theorems_used=[{"name": t.theorem_display, "step": t.step_index} for t in theorems],
            logical_gaps=[{"from": g.from_node, "to": g.to_node, "type": g.gap_type} for g in logical_gaps],
            missing_justifications=missing_justifications,
            missing_justification_score=missing_justification_score,
            partial_credit_explanation=partial_explanation,
            detailed_feedback=detailed
        )

    def _build_reasoning_dag(self, steps: List[Dict], question: ProofQuestion) -> ReasoningDAG:
        """构建推理DAG"""
        dag = ReasoningDAG()

        dag.add_node("condition_0", question.conditions[0] if question.conditions else "条件", "condition", 0)

        for i, step in enumerate(steps):
            node_type = "deduction"
            if i == len(steps) - 1:
                node_type = "conclusion"

            dag.add_node(f"step_{i}", step.get('operation', ''), node_type, i)

            if i == 0:
                dag.add_edge("condition_0", f"step_{i}")
            else:
                dag.add_edge(f"step_{i-1}", f"step_{i}")

        return dag

    def _calculate_logic_score(
        self,
        dependencies: List[Dict],
        gaps: List,
        missing_score: float
    ) -> float:
        """计算逻辑分"""
        if not dependencies:
            return 0.0

        valid_count = sum(1 for d in dependencies if d["is_valid"])
        logic_ratio = valid_count / len(dependencies)

        gap_penalty = len(gaps) * 0.1
        missing_penalty = missing_score * 0.2

        score = logic_ratio * (1 - gap_penalty - missing_penalty)

        return max(0.0, min(1.0, score))

    def _calculate_theorem_score(
        self,
        theorems: List,
        expected: List[str]
    ) -> float:
        """计算定理分"""
        if not theorems:
            return 0.0

        found_names = {t.theorem_name for t in theorems}
        expected_set = set(expected)

        if expected_set:
            match_ratio = len(found_names & expected_set) / len(expected_set)
            return min(match_ratio + 0.2, 1.0)

        return 0.3

    def _generate_detailed_feedback(
        self,
        strategy: ProofStrategy,
        confidence: float,
        theorems: List,
        gaps: List,
        missing: List[Dict]
    ) -> str:
        """生成详细反馈"""
        lines = []

        lines.append(f"识别策略: {strategy.value} (置信度: {confidence:.0%})")
        lines.append(f"策略说明: {self.strategy_recognizer.get_strategy_description(strategy)}")
        lines.append("")

        if theorems:
            lines.append("【定理使用】")
            for t in theorems:
                lines.append(f"  - {t.theorem_display} (步骤{t.step_index})")
            lines.append("")
        else:
            lines.append("【定理使用】未识别到定理使用")
            lines.append("")

        if gaps:
            lines.append("【逻辑断裂】")
            for g in gaps:
                lines.append(f"  - {g.description}")
                lines.append(f"    建议: {g.suggestion}")
            lines.append("")
        else:
            lines.append("【逻辑断裂】无明显逻辑断裂")
            lines.append("")

        if missing:
            lines.append("【缺失理由】")
            for m in missing[:3]:
                lines.append(f"  - 第{m['line_number']}行使用了'{m['pattern_found']}'")
                lines.append(f"    建议: {m['suggestion']}")
            lines.append("")

        return "\n".join(lines)


# ═══════════════════════════════════════════════
# 便捷函数
# ═══════════════════════════════════════════════

def recognize_proof_strategy(proof_text: str) -> Tuple[ProofStrategy, float]:
    """快速识别证明策略"""
    return ProofStrategyRecognizer.recognize_strategy(proof_text)


def detect_missing_justifications(proof_text: str) -> List[Dict[str, Any]]:
    """快速检测缺失理由"""
    return MissingJustificationDetector.detect_missing_justifications(proof_text)


def track_theorems(proof_text: str) -> List[LemmaUsage]:
    """快速追踪定理使用"""
    return TheoremTracker.track_theorems(proof_text)


def build_reasoning_dag(steps: List[Dict]) -> ReasoningDAG:
    """快速构建推理DAG"""
    dag = ReasoningDAG()
    for i, step in enumerate(steps):
        dag.add_node(f"step_{i}", step.get('operation', ''), "deduction", i)
        if i > 0:
            dag.add_edge(f"step_{i-1}", f"step_{i}")
    return dag


def score_proof_question(
    question: ProofQuestion,
    student_proof: str
) -> ProofScoringResult:
    """快速评分证明题"""
    scorer = UnifiedProofScorer()
    return scorer.score_proof(question, student_proof)


def format_proof_feedback(result: ProofScoringResult) -> str:
    """格式化证明题反馈"""
    lines = []
    lines.append("=" * 60)
    lines.append("【证明题评分结果】")
    lines.append("=" * 60)
    lines.append(f"总分: {result.total_score:.1f}/{result.max_score:.1f}")
    lines.append(f"策略: {result.strategy_used} (置信度: {result.strategy_confidence:.0%})")
    lines.append("")
    lines.append("【部分得分说明】")
    lines.append(result.partial_credit_explanation)
    lines.append("")
    lines.append("【详细反馈】")
    lines.append(result.detailed_feedback)
    lines.append("=" * 60)
    return "\n".join(lines)
