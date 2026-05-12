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
    """解题图中的一个节点（一个判分单元 + 推理语义层）"""
    id: str
    type: str                         # 来自 NODE_TYPES（底层操作：differentiate, simplify...）
    label: str = ""                   # 自然语言标签
    output: str = ""                  # 期望输出 (LaTeX)
    input_state: str = ""             # 该步骤的输入数学状态
    operation: str = ""               # 该步骤执行的运算（如 "differentiate", "simplify"）
    input_refs: list[str] = field(default_factory=list)  # 依赖的前驱节点 ID
    weight: float = 0.0               # 得分权重
    required: bool = True
    alternatives: list[str] = field(default_factory=list)  # 等价输出列表
    # ═══ 推理语义层 ═══
    goal: str = ""                    # 本步目标（如"求驻点"、"判断符号"、"消元"）
    strategy: str = ""                # 所用策略（如"隐函数求导"、"换元降次"、"配方"）
    reasoning: str = ""               # 为什么这步是合理的（教学解释）

    def to_dict(self):
        d = {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "output": self.output,
            "input_refs": self.input_refs,
            "weight": self.weight,
            "required": self.required,
            "alternatives": self.alternatives,
        }
        if self.input_state:
            d["input_state"] = self.input_state
        if self.operation:
            d["operation"] = self.operation
        if self.goal:
            d["goal"] = self.goal
        if self.strategy:
            d["strategy"] = self.strategy
        if self.reasoning:
            d["reasoning"] = self.reasoning
        return d


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
# SolutionMethod & CanonicalSolutionTrace
# ═══════════════════════════════════════════════

@dataclass
class SolutionMethod:
    """一种标准解法：包含方法名、解题 DAG、最终答案、知识点"""
    method_name: str
    graph: SolutionGraph
    final_answer: str
    knowledge_points: list[str] = field(default_factory=list)
    common_mistakes: list[str] = field(default_factory=list)
    usage_count: int = 0       # 此方法被使用的次数
    source: str = "ai"         # "ai" | "student"（来源）
    method_id: str = ""        # 唯一标识，自动生成

    def __post_init__(self):
        if not self.method_id:
            fp = self.fingerprint
            import hashlib
            self.method_id = hashlib.md5(fp.encode()).hexdigest()[:8]

    @property
    def fingerprint(self) -> str:
        """生成方法指纹：操作序列签名，用于去重和方法聚类。"""
        ops = [n.operation or n.type for n in self.graph.nodes]
        return ":".join(ops)

    @property
    def method_signature(self) -> dict:
        """返回方法的结构签名，用于和 student trace 快速比对。"""
        return {
            "ops_sequence": self.fingerprint,
            "op_count": {op: 0 for op in set(n.operation or n.type for n in self.graph.nodes)},
            "node_count": len(self.graph.nodes),
            "final_answer": self.final_answer,
        }

    def to_dict(self):
        return {
            "method_name": self.method_name,
            "method_id": self.method_id,
            "graph": self.graph.to_dict(),
            "final_answer": self.final_answer,
            "knowledge_points": self.knowledge_points,
            "common_mistakes": self.common_mistakes,
            "usage_count": self.usage_count,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'SolutionMethod':
        gd = d["graph"]
        nodes = []
        for nd in gd.get("nodes", []):
            nodes.append(GraphNode(**{k: v for k, v in nd.items()
                                      if k in GraphNode.__dataclass_fields__}))
        edges = [GraphEdge(e[0], e[1]) for e in gd.get("edges", [])]
        graph = SolutionGraph(
            question_id=gd.get("question_id", ""),
            final_answer=gd.get("final_answer", ""),
            nodes=nodes, edges=edges,
            total_score=gd.get("total_score", 10),
            grading_mode=gd.get("grading_mode", "step"),
        )
        return cls(
            method_name=d.get("method_name", ""),
            graph=graph,
            final_answer=d.get("final_answer", ""),
            knowledge_points=d.get("knowledge_points", []),
            common_mistakes=d.get("common_mistakes", []),
            usage_count=d.get("usage_count", 0),
            source=d.get("source", "ai"),
            method_id=d.get("method_id", ""),
        )


@dataclass
class CanonicalSolutionTrace:
    """规范解题轨迹：一道题可有多解法，每个解法是一个 verified SolutionGraph"""
    question_id: str
    methods: list[SolutionMethod]
    verified: bool = False
    verification_log: list[dict] = field(default_factory=list)
    rubric: list[dict] = field(default_factory=list)

    def best_method(self, student_answer: str | None = None) -> SolutionMethod | None:
        """返回最佳匹配方法。有 student_answer 时按相似度选择，否则返回最高频的方法。"""
        if not self.methods:
            return None
        if len(self.methods) == 1:
            return self.methods[0]
        if not student_answer:
            # 按 usage_count 降序
            return sorted(self.methods, key=lambda m: m.usage_count, reverse=True)[0]
        return self._select_best_method(student_answer)

    def all_scores_against_student(self, student_text: str) -> list[tuple[SolutionMethod, float]]:
        """对学生文本与所有方法评分，返回按分数降序排列的列表。"""
        if not student_text:
            return []
        scored = [(m, self._score_method_against_text(m, student_text))
                  for m in self.methods]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def best_match_score(self, student_text: str) -> tuple[SolutionMethod | None, float]:
        """返回最佳匹配方法及其得分。"""
        scored = self.all_scores_against_student(student_text)
        if not scored:
            return None, 0.0
        return scored[0]

    def add_method(self, method: SolutionMethod, source: str = "ai",
                   dedup: bool = True) -> str | None:
        """
        动态添加一种解法。返回 method_id（新增）或 None（已存在）。

        Args:
            method: 新解法
            source: 来源 "ai" | "student"
            dedup: 是否去重（相同 fingerprint 视为同方法）
        """
        method.source = source
        fp = method.fingerprint

        # 去重检查
        if dedup:
            for existing in self.methods:
                if existing.fingerprint == fp:
                    existing.usage_count += 1
                    return None  # 已存在，不重复添加

        method.usage_count = 1
        self.methods.append(method)
        self.verified = False  # 新方法加入需重新验证
        return method.method_id

    def get_method_by_fingerprint(self, fp: str) -> SolutionMethod | None:
        """按指纹查找方法。"""
        for m in self.methods:
            if m.fingerprint == fp:
                return m
        return None

    def method_count(self) -> int:
        return len(self.methods)

    def is_multimethod(self) -> bool:
        return len(self.methods) > 1

    def _select_best_method(self, student_text: str) -> SolutionMethod:
        """对每个方法评分，返回最匹配学生作答的方法。"""
        scored = [
            (m, self._score_method_against_text(m, student_text))
            for m in self.methods
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        # 分数接近（差 < 0.1）时回退第一个方法
        if len(scored) >= 2 and scored[0][1] - scored[1][1] < 0.1:
            return self.methods[0]
        return scored[0][0]

    def _score_method_against_text(self, method: SolutionMethod, text: str) -> float:
        """用文本匹配给方法打分，不需要 LLM 调用。"""
        if not text:
            return 0.0
        text_lower = text.lower()
        score = 0.0

        # 1. 节点输出覆盖 (权重 0.5)
        nodes = [n for n in method.graph.nodes if n.output and n.type != "final_answer"]
        if nodes:
            hits = 0
            for n in nodes:
                out = n.output.strip()
                if len(out) <= 2:
                    if out in text:
                        hits += 1
                else:
                    core = out.lower().replace(" ", "").replace("$", "")
                    if core and core in text_lower.replace(" ", ""):
                        hits += 1
            score += 0.5 * (hits / len(nodes))

        # 2. 操作序列指纹 (权重 0.3)
        ops = [n.operation for n in method.graph.nodes if n.operation]
        if ops:
            op_keywords = {
                "differentiate": ["求导", "导数", "偏导", "微分", "diff"],
                "integrate": ["积分", "∫", "int"],
                "compute_limit": ["极限", "lim"],
                "solve_equation": ["解方程", "方程"],
                "simplify": ["化简", "整理"],
                "substitute": ["代入", "换元"],
                "expand": ["展开"],
                "factor": ["因式", "分解"],
            }
            op_hits = 0
            for op in ops:
                keywords = op_keywords.get(op, [op])
                if any(kw in text_lower for kw in keywords):
                    op_hits += 1
            score += 0.3 * (op_hits / len(ops))

        # 3. 方法名/知识点匹配 (权重 0.2)
        labels = [method.method_name] + method.knowledge_points
        labels = [l for l in labels if l]
        if labels:
            label_hits = sum(1 for l in labels if l in text)
            score += 0.2 * (label_hits / len(labels))

        return score

    def to_dict(self):
        return {
            "question_id": self.question_id,
            "methods": [m.to_dict() for m in self.methods],
            "verified": self.verified,
            "verification_log": self.verification_log,
            "rubric": self.rubric,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'CanonicalSolutionTrace':
        methods = []
        for md in d.get("methods", []):
            methods.append(SolutionMethod.from_dict(md))
        return cls(
            question_id=d.get("question_id", ""),
            methods=methods,
            verified=d.get("verified", False),
            verification_log=d.get("verification_log", []),
            rubric=d.get("rubric", []),
        )

    @classmethod
    def from_question_json(cls, data: dict) -> 'CanonicalSolutionTrace | None':
        """
        从 question JSON 加载（兼容新旧格式）。

        新格式: {"canonical_solutions": [{...method...}, ...]}
        旧格式: {"canonical_solution": {"methods": [...]}}
        """
        # 优先新格式：canonical_solutions 数组
        sols = data.get("canonical_solutions", [])
        if sols:
            methods = []
            for sol in sols:
                if "methods" in sol:
                    # 嵌套格式
                    for md in sol.get("methods", []):
                        methods.append(SolutionMethod.from_dict(md))
                elif "graph" in sol:
                    methods.append(SolutionMethod.from_dict(sol))
            return cls(
                question_id=data.get("question_id", ""),
                methods=methods,
                verified=data.get("canonical_trace_verified", False),
                verification_log=[],
                rubric=[],
            )

        # 回退旧格式：canonical_solution 单对象
        old = data.get("canonical_solution")
        if old:
            return cls.from_dict(old)

        return None

    def save_to_question_json(self, data: dict) -> dict:
        """
        将 CanonicalSolutionTrace 写入 question JSON 的数据字段。
        不写文件，返回修改后的 data dict。
        """
        # 主格式：canonical_solutions 数组（每个方法独立存储）
        data["canonical_solutions"] = [m.to_dict() for m in self.methods]
        data["canonical_trace_verified"] = self.verified
        # 同时保留旧格式兼容
        data["canonical_solution"] = self.to_dict()
        return data


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
