"""
Solution Graph Engine v3 — 数学解题过程的结构化建模与对齐系统

核心思想:
  - 标准答案 = 解题 DAG, 不是文本
  - 批改 = Graph Diff, 不是字符串匹配
  - AI 仅做 diff → 语言解释, 不做判分
"""
import json, re
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════
# Node Types
# ═══════════════════════════════════════════════

NODE_TYPES = {
    "differentiate":     "求导/偏导",
    "integrate":         "积分",
    "solve_system":      "解方程组",
    "hessian_test":      "Hessian 判别",
    "substitute":        "代入",
    "simplify":          "化简",
    "classify":          "分类讨论",
    "compute_limit":     "求极限",
    "expand_series":     "级数展开",
    "matrix_op":         "矩阵运算",
    "eigen_solve":       "特征值/特征向量",
    "orthogonalize":     "正交化",
    "quadratic_form":    "二次型标准化",
    "probability_calc":  "概率计算",
    "expectation":       "期望/方差",
    "mle_derive":        "极大似然推导",
    "moment_estimate":   "矩估计",
    "apply_theorem":     "应用定理",
    "select_option":     "选择选项",
    "fill_blank":        "填空",
    "final_answer":      "最终答案",
}


@dataclass
class GraphNode:
    """解题图中的一个节点（一个判分单元）"""
    id: str
    type: str                         # 来自 NODE_TYPES
    label: str = ""                   # 自然语言标签
    output: str = ""                  # 期望输出 (LaTeX)
    input_refs: list[str] = field(default_factory=list)  # 依赖的前驱节点 ID
    weight: float = 0.0               # 得分权重
    required: bool = True
    alternatives: list[str] = field(default_factory=list)  # 等价输出列表

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "output": self.output,
            "input_refs": self.input_refs,
            "weight": self.weight,
            "required": self.required,
            "alternatives": self.alternatives,
        }


@dataclass
class GraphEdge:
    """解题图中的边（依赖关系）"""
    source: str   # from node id
    target: str   # to node id


@dataclass
class SolutionGraph:
    """完整解题 DAG"""
    question_id: str
    final_answer: str
    nodes: list[GraphNode]
    edges: list[GraphEdge] = field(default_factory=list)
    total_score: float = 10.0
    grading_mode: str = "step"   # step | result | hybrid

    def to_dict(self):
        return {
            "question_id": self.question_id,
            "final_answer": self.final_answer,
            "total_score": self.total_score,
            "grading_mode": self.grading_mode,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [[e.source, e.target] for e in self.edges],
        }

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        nodes = [GraphNode(**n) for n in d["nodes"]]
        edges = [GraphEdge(e[0], e[1]) for e in d.get("edges", [])]
        return cls(
            question_id=d["question_id"],
            final_answer=d["final_answer"],
            nodes=nodes,
            edges=edges,
            total_score=d.get("total_score", 10),
            grading_mode=d.get("grading_mode", "step"),
        )

    # ═══════════════════════════════════════════════
    # Graph Diff Engine
    # ═══════════════════════════════════════════════

    def diff(self, student_text: str) -> dict:
        """
        对比学生文本 vs 标准解题图。
        返回 GraphDiff 结构。
        """
        standard_nodes = {n.id: n for n in self.nodes}
        present = set()
        wrong = []

        for nid, node in standard_nodes.items():
            # 简单规则匹配：检查学生文本中是否包含节点的关键输出
            if node.output and self._fuzzy_match(node.output, student_text):
                present.add(nid)
            elif node.label and self._fuzzy_match(node.label, student_text):
                present.add(nid)
            elif node.output and node.output in student_text:
                present.add(nid)

        missing = [nid for nid in standard_nodes if nid not in present]

        # 结构分: 检查依赖链完整性
        structure_broken = False
        for nid in present:
            node = standard_nodes[nid]
            for dep in node.input_refs:
                if dep not in present:
                    structure_broken = True
                    break

        # 计算分数
        score = 0.0
        node_map = {n.id: n for n in self.nodes}
        for nid in present:
            if nid in node_map:
                score += node_map[nid].weight

        return {
            "missing_nodes": missing,
            "present_nodes": sorted(present),
            "wrong_nodes": wrong,
            "structure_broken": structure_broken,
            "coverage": len(present) / max(len(self.nodes), 1),
            "score": round(score, 1),
            "total": self.total_score,
        }

    def _fuzzy_match(self, target: str, text: str) -> bool:
        """宽松匹配: 忽略空格, 部分匹配"""
        def norm(s):
            return re.sub(r'\s+', '', s.lower())
        t = norm(target)
        if len(t) < 3:
            return t in norm(text)
        # 至少 60% 的字符匹配
        chars = set(t) - set("(){}$\\")
        if not chars:
            return t in norm(text)
        matched = sum(1 for c in chars if c in norm(text))
        return matched / len(chars) >= 0.6

    def explain_diff(self, diff_result: dict) -> str:
        """将 GraphDiff 翻译为人话（供 AI 或直接展示）"""
        parts = []
        missing = diff_result.get("missing_nodes", [])
        node_map = {n.id: n for n in self.nodes}

        if missing:
            labels = [node_map[nid].label or node_map[nid].type for nid in missing if nid in node_map]
            if labels:
                parts.append(f"缺失步骤: {', '.join(labels)}")

        if diff_result.get("structure_broken"):
            parts.append("解题逻辑链断裂: 缺少前置步骤导致后续步骤无效")

        if diff_result["coverage"] == 0:
            parts.append("学生未展示任何有效解题过程")
        elif diff_result["coverage"] < 0.3:
            parts.append("解题过程严重不完整")
        elif diff_result["coverage"] < 0.7:
            parts.append("部分步骤缺失")

        score = diff_result["score"]
        total = diff_result["total"]
        if score >= total * 0.9:
            parts.append("解题完整, 结构正确")
        elif score >= total * 0.6:
            parts.append("基本正确, 部分步骤可优化")

        return "; ".join(parts) if parts else "解题过程完整"


# ═══════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════

def make_choice_graph(qid: str, answer: str, score: float = 5.0) -> SolutionGraph:
    return SolutionGraph(
        question_id=qid,
        final_answer=answer,
        nodes=[GraphNode(id="n1", type="select_option", label="选择正确选项",
                         output=answer, weight=score)],
        edges=[],
        total_score=score,
        grading_mode="result",
    )


def make_fill_blank_graph(qid: str, answer: str, score: float = 5.0) -> SolutionGraph:
    return SolutionGraph(
        question_id=qid,
        final_answer=answer,
        nodes=[GraphNode(id="n1", type="compute", label="计算填空值",
                         output=answer, weight=score)],
        edges=[],
        total_score=score,
        grading_mode="result",
    )


def make_solution_graph(qid: str, final_answer: str, nodes: list[GraphNode],
                        edges: list[GraphEdge] = None,
                        total: float = 10.0) -> SolutionGraph:
    if sum(n.weight for n in nodes) == 0:
        w = total / len(nodes)
        for n in nodes:
            n.weight = round(w, 1)
    return SolutionGraph(
        question_id=qid,
        final_answer=final_answer,
        nodes=nodes,
        edges=edges or [],
        total_score=total,
        grading_mode="step",
    )


# ═══════════════════════════════════════════════
# 预置: 常见考研题型 Solution Graph 模板
# ═══════════════════════════════════════════════

def make_multivar_extremum_graph(qid: str, final_answer: str) -> SolutionGraph:
    """多元函数极值: 求偏导 → 解驻点 → Hessian → 分类"""
    n1 = GraphNode(id="n1", type="differentiate", label="求偏导数 fx, fy",
                   output="fx=..., fy=...", weight=2.5)
    n2 = GraphNode(id="n2", type="solve_system", label="解驻点方程组 fx=0, fy=0",
                   output="驻点坐标", weight=2.5, input_refs=["n1"])
    n3 = GraphNode(id="n3", type="hessian_test", label="计算 Hessian 矩阵并判别",
                   output="极小值/极大值/鞍点", weight=3.0, input_refs=["n2"])
    n4 = GraphNode(id="n4", type="final_answer", label="写出最终结论",
                   output=final_answer, weight=2.0, input_refs=["n3"])
    return make_solution_graph(qid, final_answer, [n1, n2, n3, n4],
                               edges=[GraphEdge("n1","n2"), GraphEdge("n2","n3"), GraphEdge("n3","n4")])


def make_limit_graph(qid: str, final_answer: str) -> SolutionGraph:
    """求极限: 识别类型 → 等价无穷小/洛必达 → 化简 → 极限值"""
    n1 = GraphNode(id="n1", type="compute_limit", label="识别极限类型",
                   output="0/0型/∞/∞型", weight=2.0)
    n2 = GraphNode(id="n2", type="simplify", label="等价替换或洛必达",
                   output="化简后的表达式", weight=4.0, input_refs=["n1"])
    n3 = GraphNode(id="n3", type="final_answer", label="写出极限值",
                   output=final_answer, weight=4.0, input_refs=["n2"])
    return make_solution_graph(qid, final_answer, [n1, n2, n3],
                               edges=[GraphEdge("n1","n2"), GraphEdge("n2","n3")])


def make_eigenvalue_graph(qid: str, final_answer: str) -> SolutionGraph:
    """特征值/特征向量: 特征方程 → 特征值 → 特征向量 → 正交化"""
    n1 = GraphNode(id="n1", type="eigen_solve", label="写出特征方程 |λE-A|=0",
                   output="特征多项式", weight=3.0)
    n2 = GraphNode(id="n2", type="eigen_solve", label="求解特征值",
                   output="λ1,λ2,λ3", weight=3.0, input_refs=["n1"])
    n3 = GraphNode(id="n3", type="eigen_solve", label="求解特征向量",
                   output="p1,p2,p3", weight=2.0, input_refs=["n2"])
    n4 = GraphNode(id="n4", type="orthogonalize", label="正交化/单位化",
                   output="标准正交基", weight=2.0, input_refs=["n3"])
    return make_solution_graph(qid, final_answer, [n1, n2, n3, n4],
                               edges=[GraphEdge("n1","n2"),GraphEdge("n2","n3"),GraphEdge("n3","n4")])
