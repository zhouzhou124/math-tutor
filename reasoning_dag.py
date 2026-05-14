"""reasoning_dag.py — 推理有向无环图（Reasoning DAG）

实现数学问题解答的推理过程表示，支持：
- 步骤级推理图构建
- 依赖分析
- 错误回溯
- Mermaid可视化
- 知识图谱集成
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from uuid import uuid4
from expression_ast import ExprNode
from operations import Op


# 全局知识图谱实例
_global_knowledge_graph = None

def get_knowledge_graph() -> 'KnowledgeGraph':
    """获取全局知识图谱实例"""
    global _global_knowledge_graph
    if _global_knowledge_graph is None:
        from knowledge_graph import KnowledgeGraph
        _global_knowledge_graph = KnowledgeGraph()
    return _global_knowledge_graph


class NodeType(Enum):
    """推理图节点类型"""
    PREMISE = "premise"           # 前提条件
    EXPRESSION = "expression"     # 表达式
    OPERATION = "operation"       # 操作
    CONCLUSION = "conclusion"     # 结论
    ASSUMPTION = "assumption"     # 假设
    GOAL = "goal"                 # 目标
    ERROR = "error"               # 错误节点


class EdgeType(Enum):
    """推理图边类型"""
    DEPENDS_ON = "depends_on"     # 依赖关系
    DERIVES_FROM = "derives_from" # 推导关系
    INPUT_TO = "input_to"         # 输入关系
    OUTPUT_FROM = "output_from"   # 输出关系
    ASSUMES = "assumes"           # 假设关系


@dataclass
class DagNode:
    """推理图节点"""
    id: str
    type: NodeType
    label: str = ""
    content: str = ""
    expression: Optional[ExprNode] = None
    operation: Optional[Op] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "type": self.type.value,
            "label": self.label,
            "content": self.content,
            "operation": self.operation.value if self.operation else None,
            "metadata": self.metadata
        }


@dataclass
class DagEdge:
    """推理图边"""
    source_id: str
    target_id: str
    type: EdgeType
    label: str = ""
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.type.value,
            "label": self.label,
            "weight": self.weight
        }


class ReasoningDAG:
    """推理有向无环图"""
    
    def __init__(self):
        self.nodes: Dict[str, DagNode] = {}
        self.edges: List[DagEdge] = []
        self._node_counter = 0
    
    def _generate_id(self, prefix: str = "node") -> str:
        """生成唯一节点ID"""
        self._node_counter += 1
        return f"{prefix}_{self._node_counter}_{uuid4().hex[:8]}"
    
    def add_node(self, 
                 node_type: NodeType, 
                 label: str = "", 
                 content: str = "",
                 expression: Optional[ExprNode] = None,
                 operation: Optional[Op] = None,
                 **kwargs) -> str:
        """添加节点"""
        node_id = self._generate_id()
        self.nodes[node_id] = DagNode(
            id=node_id,
            type=node_type,
            label=label,
            content=content,
            expression=expression,
            operation=operation,
            metadata=kwargs
        )
        return node_id
    
    def add_edge(self, 
                 source_id: str, 
                 target_id: str, 
                 edge_type: EdgeType,
                 label: str = "",
                 weight: float = 1.0) -> None:
        """添加边"""
        if source_id not in self.nodes:
            raise ValueError(f"源节点不存在: {source_id}")
        if target_id not in self.nodes:
            raise ValueError(f"目标节点不存在: {target_id}")
        
        # 检查是否已存在相同边
        for edge in self.edges:
            if edge.source_id == source_id and edge.target_id == target_id:
                # 更新现有边
                edge.type = edge_type
                edge.label = label
                edge.weight = weight
                return
        
        self.edges.append(DagEdge(
            source_id=source_id,
            target_id=target_id,
            type=edge_type,
            label=label,
            weight=weight
        ))
    
    def get_node(self, node_id: str) -> Optional[DagNode]:
        """获取节点"""
        return self.nodes.get(node_id)
    
    def get_edges_from(self, node_id: str) -> List[DagEdge]:
        """获取从指定节点出发的边"""
        return [e for e in self.edges if e.source_id == node_id]
    
    def get_edges_to(self, node_id: str) -> List[DagEdge]:
        """获取指向指定节点的边"""
        return [e for e in self.edges if e.target_id == node_id]
    
    def get_dependencies(self, node_id: str) -> List[str]:
        """获取节点的所有依赖节点ID"""
        dependencies = set()
        edges_to = self.get_edges_to(node_id)
        for edge in edges_to:
            if edge.type in (EdgeType.DEPENDS_ON, EdgeType.DERIVES_FROM, EdgeType.INPUT_TO):
                dependencies.add(edge.source_id)
        return list(dependencies)
    
    def get_dependents(self, node_id: str) -> List[str]:
        """获取依赖指定节点的所有节点ID"""
        dependents = set()
        edges_from = self.get_edges_from(node_id)
        for edge in edges_from:
            if edge.type in (EdgeType.DEPENDS_ON, EdgeType.DERIVES_FROM, EdgeType.OUTPUT_FROM):
                dependents.add(edge.target_id)
        return list(dependents)
    
    def topological_sort(self) -> List[str]:
        """拓扑排序"""
        in_degree = {node_id: 0 for node_id in self.nodes}
        for edge in self.edges:
            in_degree[edge.target_id] += 1
        
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []
        
        while queue:
            node_id = queue.pop(0)
            result.append(node_id)
            
            for edge in self.get_edges_from(node_id):
                in_degree[edge.target_id] -= 1
                if in_degree[edge.target_id] == 0:
                    queue.append(edge.target_id)
        
        if len(result) != len(self.nodes):
            raise ValueError("图中存在环")
        
        return result
    
    def find_cycles(self) -> List[List[str]]:
        """查找图中的环"""
        visited = set()
        rec_stack = set()
        cycles = []
        
        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for edge in self.get_edges_from(node_id):
                target_id = edge.target_id
                if target_id not in visited:
                    dfs(target_id, path.copy())
                elif target_id in rec_stack:
                    # 找到环
                    cycle_start = path.index(target_id)
                    cycle = path[cycle_start:] + [target_id]
                    cycles.append(cycle)
            
            rec_stack.remove(node_id)
        
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id, [])
        
        return cycles
    
    def mark_error(self, node_id: str, error_message: str) -> None:
        """标记节点为错误节点"""
        if node_id in self.nodes:
            self.nodes[node_id].type = NodeType.ERROR
            self.nodes[node_id].metadata["error"] = error_message
    
    def get_error_path(self, error_node_id: str) -> List[str]:
        """获取错误回溯路径"""
        path = []
        current_id = error_node_id
        
        while current_id:
            path.append(current_id)
            dependencies = self.get_dependencies(current_id)
            if dependencies:
                # 选择第一个依赖（可以改进为选择最相关的）
                current_id = dependencies[0]
            else:
                current_id = None
        
        return path[::-1]  # 反转，从前提到错误
    
    def to_mermaid(self, view_type: str = "full") -> str:
        """转换为Mermaid图表"""
        lines = ["graph TD"]
        
        # 添加节点
        for node_id, node in self.nodes.items():
            style = ""
            if node.type == NodeType.PREMISE:
                style = "style fill:#E8F4FD,stroke:#2563EB"
            elif node.type == NodeType.OPERATION:
                style = "style fill:#FEF3C7,stroke:#D97706"
            elif node.type == NodeType.CONCLUSION:
                style = "style fill:#D1FAE5,stroke:#059669"
            elif node.type == NodeType.ERROR:
                style = "style fill:#FEE2E2,stroke:#DC2626"
            elif node.type == NodeType.GOAL:
                style = "style fill:#E9D5FF,stroke:#7C3AED"
            
            label = node.label if node.label else node.content[:30] + "..." if len(node.content) > 30 else node.content
            lines.append(f'    {node_id}["{label}"]')
            if style:
                lines.append(f'    {node_id}{style}')
        
        # 添加边
        for edge in self.edges:
            edge_label = f"|{edge.label}|" if edge.label else ""
            lines.append(f'    {edge.source_id} -->{edge_label} {edge.target_id}')
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges]
        }
    
    def __len__(self) -> int:
        """返回节点数量"""
        return len(self.nodes)
    
    def __repr__(self) -> str:
        return f"ReasoningDAG(nodes={len(self.nodes)}, edges={len(self.edges)})"
    
    def analyze_knowledge_points(self) -> List[dict]:
        """分析推理图中涉及的知识点"""
        kg = get_knowledge_graph()
        knowledge_points = []
        
        for node_id, node in self.nodes.items():
            # 根据操作类型查找知识点
            if node.operation:
                op_name = node.operation.value
                # 搜索相关知识点
                results = kg.search_by_name(op_name)
                for result_id in results:
                    entity = kg.get_entity(result_id)
                    if entity:
                        knowledge_points.append({
                            "node_id": node_id,
                            "node_label": node.label,
                            "knowledge_id": result_id,
                            "knowledge_name": entity.name,
                            "knowledge_type": entity.type.value,
                            "difficulty": entity.difficulty
                        })
            
            # 根据表达式内容查找知识点
            if node.content:
                keywords = ["导数", "积分", "极限", "求导", "微分"]
                for keyword in keywords:
                    if keyword in node.content:
                        results = kg.search_by_name(keyword)
                        for result_id in results:
                            entity = kg.get_entity(result_id)
                            if entity and result_id not in [k["knowledge_id"] for k in knowledge_points]:
                                knowledge_points.append({
                                    "node_id": node_id,
                                    "node_label": node.label,
                                    "knowledge_id": result_id,
                                    "knowledge_name": entity.name,
                                    "knowledge_type": entity.type.value,
                                    "difficulty": entity.difficulty
                                })
        
        # 去重
        seen = set()
        unique = []
        for kp in knowledge_points:
            key = (kp["knowledge_id"], kp["node_id"])
            if key not in seen:
                seen.add(key)
                unique.append(kp)
        
        return unique
    
    def get_knowledge_suggestions(self, 
                                  known_knowledge_ids: List[str] = None) -> List[dict]:
        """获取学习建议"""
        kg = get_knowledge_graph()
        
        # 获取当前推理图涉及的知识点
        current_knowledge = self.analyze_knowledge_points()
        current_ids = [kp["knowledge_id"] for kp in current_knowledge]
        
        # 合并已知知识点
        all_known = set(current_ids + (known_knowledge_ids or []))
        
        # 获取建议
        suggestions = kg.suggest_next_steps(list(all_known))
        
        return suggestions
    
    def diagnose_errors_with_knowledge(self) -> List[dict]:
        """使用知识图谱诊断错误"""
        diagnoses = []
        
        # 查找错误节点
        for node_id, node in self.nodes.items():
            if node.type == NodeType.ERROR:
                error_msg = node.metadata.get("error", "")
                
                # 获取当前节点涉及的知识点
                current_knowledge = self.analyze_knowledge_points()
                current_ids = [kp["knowledge_id"] for kp in current_knowledge]
                
                # 使用知识图谱诊断
                kg = get_knowledge_graph()
                results = kg.diagnose_error(error_msg, current_ids)
                
                for result in results:
                    diagnoses.append({
                        "node_id": node_id,
                        "node_label": node.label,
                        **result
                    })
        
        return diagnoses


class DagBuilder:
    """推理图构建器"""
    
    def __init__(self):
        self.dag = ReasoningDAG()
    
    def add_premise(self, content: str, expression: Optional[ExprNode] = None) -> str:
        """添加前提节点"""
        return self.dag.add_node(
            NodeType.PREMISE,
            label=f"前提",
            content=content,
            expression=expression
        )
    
    def add_expression(self, content: str, expression: ExprNode) -> str:
        """添加表达式节点"""
        return self.dag.add_node(
            NodeType.EXPRESSION,
            label=f"表达式",
            content=content,
            expression=expression
        )
    
    def add_operation(self, operation: Op, description: str = "") -> str:
        """添加操作节点"""
        return self.dag.add_node(
            NodeType.OPERATION,
            label=f"操作: {operation.value}",
            content=description,
            operation=operation
        )
    
    def add_conclusion(self, content: str, expression: Optional[ExprNode] = None) -> str:
        """添加结论节点"""
        return self.dag.add_node(
            NodeType.CONCLUSION,
            label=f"结论",
            content=content,
            expression=expression
        )
    
    def add_goal(self, content: str) -> str:
        """添加目标节点"""
        return self.dag.add_node(
            NodeType.GOAL,
            label=f"目标",
            content=content
        )
    
    def connect_depends(self, source_id: str, target_id: str, label: str = "") -> None:
        """连接依赖关系"""
        self.dag.add_edge(source_id, target_id, EdgeType.DEPENDS_ON, label)
    
    def connect_derives(self, source_id: str, target_id: str, label: str = "") -> None:
        """连接推导关系"""
        self.dag.add_edge(source_id, target_id, EdgeType.DERIVES_FROM, label)
    
    def connect_input(self, source_id: str, target_id: str, label: str = "") -> None:
        """连接输入关系"""
        self.dag.add_edge(source_id, target_id, EdgeType.INPUT_TO, label)
    
    def connect_output(self, source_id: str, target_id: str, label: str = "") -> None:
        """连接输出关系"""
        self.dag.add_edge(source_id, target_id, EdgeType.OUTPUT_FROM, label)
    
    def build(self) -> ReasoningDAG:
        """构建完成，返回DAG"""
        return self.dag


def demo_dag_construction():
    """演示DAG构建"""
    from expression_parser import parse_latex
    
    builder = DagBuilder()
    
    # 添加前提
    premise1 = builder.add_premise("已知函数 f(x) = x^2")
    premise2 = builder.add_premise("求 f'(x)")
    
    # 添加目标
    goal = builder.add_goal("求导 f(x) = x^2")
    
    # 添加操作
    op = builder.add_operation(Op.DIFFERENTIATE, "对 x^2 求导")
    
    # 添加中间表达式
    expr1 = builder.add_expression("f(x) = x^2", parse_latex("x^2"))
    expr2 = builder.add_expression("f'(x) = 2x", parse_latex("2x"))
    
    # 添加结论
    conclusion = builder.add_conclusion("f'(x) = 2x", parse_latex("2x"))
    
    # 连接关系
    builder.connect_depends(premise1, expr1, "定义")
    builder.connect_depends(premise2, goal, "目标")
    builder.connect_input(expr1, op, "输入")
    builder.connect_output(op, expr2, "输出")
    builder.connect_derives(expr2, conclusion, "结论")
    builder.connect_depends(goal, conclusion, "达成")
    
    dag = builder.build()
    
    print("DAG构建完成:")
    print(f"  节点数: {len(dag)}")
    print(f"  边数: {len(dag.edges)}")
    print(f"  是否有环: {len(dag.find_cycles()) > 0}")
    
    print("\nMermaid图表:")
    print(dag.to_mermaid())
    
    return dag


if __name__ == "__main__":
    demo_dag_construction()