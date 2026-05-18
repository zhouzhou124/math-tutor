"""rendering/graph_renderer.py — 图渲染抽象层

提供统一的图渲染接口，支持多种后端：
- Mermaid（轻量级，适合快速渲染）
- Cytoscape（功能强大，适合复杂交互）
- D3.js（高度自定义，适合定制化需求）

架构设计：
┌─────────────────────────────────────────────────────────┐
│                   GraphRenderer                         │
├─────────────────────────────────────────────────────────┤
│  GraphIR — 图的中间表示（节点、边、属性）              │
│  RendererBackend — 渲染后端接口                       │
│  MermaidRenderer — Mermaid 后端实现                   │
│  CytoscapeRenderer — Cytoscape 后端实现               │
│  D3Renderer — D3.js 后端实现                          │
└─────────────────────────────────────────────────────────┘
"""
from typing import Any, Dict, List, Optional, Protocol, Union
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class NodeType(Enum):
    """节点类型枚举"""
    STEP = "step"           # 推理步骤
    FORMULA = "formula"     # 公式节点
    CONCEPT = "concept"     # 概念节点
    ERROR = "error"         # 错误节点
    THEOREM = "theorem"     # 定理节点
    CONSTRAINT = "constraint" # 约束节点
    GOAL = "goal"           # 目标节点


class EdgeType(Enum):
    """边类型枚举"""
    DEPENDS_ON = "depends_on"       # 依赖关系
    IMPLIES = "implies"             # 蕴含关系
    ERROR_PROPAGATES = "error_propagates" # 错误传播
    USES = "uses"                   # 使用关系
    TRANSFORMS = "transforms"       # 变换关系
    PART_OF = "part_of"             # 组成关系


@dataclass
class GraphNode:
    """图节点数据类"""
    id: str
    label: str
    node_type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)
    position: Optional[Dict[str, float]] = None
    
    @property
    def style_class(self) -> str:
        """获取节点样式类"""
        return f"node-{self.node_type.value}"


@dataclass
class GraphEdge:
    """图边数据类"""
    source: str
    target: str
    edge_type: EdgeType
    label: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def style_class(self) -> str:
        """获取边样式类"""
        return f"edge-{self.edge_type.value}"


@dataclass
class GraphIR:
    """图的中间表示（Intermediate Representation）"""
    nodes: List[GraphNode] = field(default_factory=list)
    edges: List[GraphEdge] = field(default_factory=list)
    title: Optional[str] = None
    layout: str = "dagre"  # dagre, force, circular, hierarchical
    
    def add_node(self, node: GraphNode):
        """添加节点"""
        self.nodes.append(node)
    
    def add_edge(self, edge: GraphEdge):
        """添加边"""
        self.edges.append(edge)
    
    def get_node_by_id(self, node_id: str) -> Optional[GraphNode]:
        """根据ID获取节点"""
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None
    
    def get_edges_by_source(self, source_id: str) -> List[GraphEdge]:
        """获取从指定节点出发的边"""
        return [e for e in self.edges if e.source == source_id]
    
    def get_edges_by_target(self, target_id: str) -> List[GraphEdge]:
        """获取指向指定节点的边"""
        return [e for e in self.edges if e.target == target_id]
    
    def get_dependencies(self, node_id: str) -> List[GraphNode]:
        """获取节点的依赖节点"""
        dependencies = []
        for edge in self.get_edges_by_target(node_id):
            node = self.get_node_by_id(edge.source)
            if node:
                dependencies.append(node)
        return dependencies
    
    def get_dependents(self, node_id: str) -> List[GraphNode]:
        """获取依赖于指定节点的节点"""
        dependents = []
        for edge in self.get_edges_by_source(node_id):
            node = self.get_node_by_id(edge.target)
            if node:
                dependents.append(node)
        return dependents


class RendererBackend(ABC):
    """渲染后端接口"""
    
    @abstractmethod
    def render(self, graph: GraphIR) -> str:
        """渲染图，返回HTML字符串"""
        pass
    
    @abstractmethod
    def render_interactive(self, graph: GraphIR, **kwargs) -> str:
        """渲染交互式图，返回HTML字符串"""
        pass


class MermaidRenderer(RendererBackend):
    """Mermaid 渲染后端实现"""
    
    def render(self, graph: GraphIR) -> str:
        """渲染为 Mermaid 图表"""
        lines = ["```mermaid"]
        
        # 根据布局选择图表类型
        if graph.layout == "dagre" or graph.layout == "hierarchical":
            lines.append("graph TD")
        elif graph.layout == "circular":
            lines.append("graph LR")
        else:
            lines.append("graph TD")
        
        # 添加节点
        for node in graph.nodes:
            shape = self._get_node_shape(node.node_type)
            color = self._get_node_color(node.node_type)
            lines.append(f'    {node.id}{shape}"{self._escape_label(node.label)}" style="fill:{color}"')
        
        # 添加边
        for edge in graph.edges:
            arrow = self._get_edge_arrow(edge.edge_type)
            edge_color = self._get_edge_color(edge.edge_type)
            if edge.label:
                lines.append(f'    {edge.source}{arrow}{edge.target}|" {self._escape_label(edge.label)} " style="stroke:{edge_color}"')
            else:
                lines.append(f'    {edge.source}{arrow}{edge.target} style="stroke:{edge_color}"')
        
        lines.append("```")
        return "\n".join(lines)
    
    def render_interactive(self, graph: GraphIR, **kwargs) -> str:
        """渲染交互式 Mermaid 图表"""
        # Mermaid 支持基本的点击事件
        mermaid_code = self.render(graph)
        return f"""
<div class="graph-container">
    <div class="graph-title">{graph.title or ''}</div>
    {mermaid_code}
</div>
<script>
    // 可以在这里添加额外的交互逻辑
</script>
"""
    
    def _get_node_shape(self, node_type: NodeType) -> str:
        """获取节点形状"""
        shapes = {
            NodeType.STEP: "[",
            NodeType.FORMULA: "((",
            NodeType.CONCEPT: "[",
            NodeType.ERROR: "{",
            NodeType.THEOREM: "[",
            NodeType.CONSTRAINT: "[",
            NodeType.GOAL: "((",
        }
        shape = shapes.get(node_type, "[")
        if shape == "[":
            return shape + "]-"
        elif shape == "((":
            return shape + "))-"
        elif shape == "{":
            return shape + "}-"
        return shape
    
    def _get_node_color(self, node_type: NodeType) -> str:
        """获取节点颜色"""
        colors = {
            NodeType.STEP: "#e0f2fe",
            NodeType.FORMULA: "#fef3c7",
            NodeType.CONCEPT: "#dcfce7",
            NodeType.ERROR: "#fee2e2",
            NodeType.THEOREM: "#fce7f3",
            NodeType.CONSTRAINT: "#e0e7ff",
            NodeType.GOAL: "#d1fae5",
        }
        return colors.get(node_type, "#ffffff")
    
    def _get_edge_arrow(self, edge_type: EdgeType) -> str:
        """获取边箭头类型"""
        arrows = {
            EdgeType.DEPENDS_ON: "-->",
            EdgeType.IMPLIES: "==>",
            EdgeType.ERROR_PROPAGATES: "--x",
            EdgeType.USES: "-.-",
            EdgeType.TRANSFORMS: "--|>",
            EdgeType.PART_OF: "--o",
        }
        return arrows.get(edge_type, "-->")
    
    def _get_edge_color(self, edge_type: EdgeType) -> str:
        """获取边颜色"""
        colors = {
            EdgeType.DEPENDS_ON: "#6b7280",
            EdgeType.IMPLIES: "#22c55e",
            EdgeType.ERROR_PROPAGATES: "#ef4444",
            EdgeType.USES: "#8b5cf6",
            EdgeType.TRANSFORMS: "#f59e0b",
            EdgeType.PART_OF: "#3b82f6",
        }
        return colors.get(edge_type, "#6b7280")
    
    def _escape_label(self, label: str) -> str:
        """转义标签中的特殊字符"""
        return label.replace('"', '\\"').replace("\n", "<br>")


class CytoscapeRenderer(RendererBackend):
    """Cytoscape 渲染后端实现"""
    
    def render(self, graph: GraphIR) -> str:
        """渲染为 Cytoscape 图表"""
        nodes_json = []
        for node in graph.nodes:
            nodes_json.append({
                "data": {
                    "id": node.id,
                    "label": node.label,
                    "type": node.node_type.value,
                    **node.properties
                },
                "position": node.position or {}
            })
        
        edges_json = []
        for edge in graph.edges:
            edges_json.append({
                "data": {
                    "source": edge.source,
                    "target": edge.target,
                    "label": edge.label,
                    "type": edge.edge_type.value,
                    **edge.properties
                }
            })
        
        return f"""
<div id="cy-container" style="height: 500px; width: 100%; border: 1px solid #e5e7eb; border-radius: 8px;"></div>
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.29.0/dist/cytoscape.min.js"></script>
<script>
    var cy = cytoscape({{
        container: document.getElementById('cy-container'),
        elements: {{
            nodes: {nodes_json},
            edges: {edges_json}
        }},
        style: [
            {{
                selector: 'node',
                style: {{
                    'background-color': 'data(bgColor)',
                    'label': 'data(label)',
                    'font-size': '12px',
                    'text-wrap': 'wrap',
                    'text-max-width': '120px',
                    'border-width': 2,
                    'border-color': '#e5e7eb',
                    'padding': '8px'
                }}
            }},
            {{
                selector: 'edge',
                style: {{
                    'width': 2,
                    'line-color': 'data(color)',
                    'target-arrow-color': 'data(color)',
                    'target-arrow-shape': 'triangle',
                    'label': 'data(label)',
                    'font-size': '10px'
                }}
            }},
            {{
                selector: '.node-step',
                style: {{ 'background-color': '#e0f2fe' }}
            }},
            {{
                selector: '.node-formula',
                style: {{ 'background-color': '#fef3c7' }}
            }},
            {{
                selector: '.node-error',
                style: {{ 'background-color': '#fee2e2' }}
            }}
        ],
        layout: {{
            name: '{graph.layout}',
            rankDir: 'TB',
            nodeSpacing: 50,
            edgeLength: 100
        }}
    }});
    
    // 基本交互
    cy.on('click', 'node', function(evt) {{
        var node = evt.target;
        node.toggleClass('selected');
    }});
    
    cy.on('mouseover', 'node', function(evt) {{
        var node = evt.target;
        node.addClass('highlighted');
    }});
    
    cy.on('mouseout', 'node', function(evt) {{
        var node = evt.target;
        node.removeClass('highlighted');
    }});
</script>
"""
    
    def render_interactive(self, graph: GraphIR, **kwargs) -> str:
        """渲染交互式 Cytoscape 图表"""
        return self.render(graph)


class D3Renderer(RendererBackend):
    """D3.js 渲染后端实现"""
    
    def render(self, graph: GraphIR) -> str:
        """渲染为 D3.js 图表"""
        return f"""
<div id="d3-container" style="height: 500px; width: 100%; border: 1px solid #e5e7eb; border-radius: 8px;"></div>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script>
    // D3.js 实现（简化版）
    var width = document.getElementById('d3-container').clientWidth;
    var height = 500;
    
    var svg = d3.select('#d3-container')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // 节点数据
    var nodes = {[{'id': n.id, 'label': n.label, 'type': n.node_type.value} for n in graph.nodes]};
    
    // 边数据
    var links = {[{'source': e.source, 'target': e.target, 'type': e.edge_type.value} for e in graph.edges]};
    
    // 简单布局
    var nodeElements = svg.selectAll('.node')
        .data(nodes)
        .enter()
        .append('g')
        .attr('class', function(d) {{ return 'node node-' + d.type; }});
    
    nodeElements.append('rect')
        .attr('width', 100)
        .attr('height', 40)
        .attr('rx', 8)
        .attr('fill', function(d) {{
            var colors = {{'step':'#e0f2fe', 'formula':'#fef3c7', 'error':'#fee2e2', 'concept':'#dcfce7'}};
            return colors[d.type] || '#ffffff';
        }})
        .attr('stroke', '#e5e7eb');
    
    nodeElements.append('text')
        .attr('x', 50)
        .attr('y', 25)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .text(function(d) {{ return d.label.substring(0, 15) + (d.label.length > 15 ? '...' : ''); }});
    
    // 简单布局定位
    nodeElements.attr('transform', function(d, i) {{
        var row = Math.floor(i / 4);
        var col = i % 4;
        return 'translate(' + (col * 120 + 50) + ',' + (row * 80 + 50) + ')';
    }});
</script>
"""
    
    def render_interactive(self, graph: GraphIR, **kwargs) -> str:
        """渲染交互式 D3.js 图表"""
        return self.render(graph)


class GraphRenderer:
    """图渲染器 — 统一接口"""
    
    def __init__(self, backend: str = "mermaid"):
        """
        初始化图渲染器
        
        Args:
            backend: 渲染后端，可选值：'mermaid', 'cytoscape', 'd3'
        """
        self.backend = self._create_backend(backend)
    
    def _create_backend(self, backend: str) -> RendererBackend:
        """创建渲染后端实例"""
        backends = {
            "mermaid": MermaidRenderer(),
            "cytoscape": CytoscapeRenderer(),
            "d3": D3Renderer(),
        }
        return backends.get(backend.lower(), MermaidRenderer())
    
    def render(self, graph: GraphIR) -> str:
        """渲染图"""
        return self.backend.render(graph)
    
    def render_interactive(self, graph: GraphIR, **kwargs) -> str:
        """渲染交互式图"""
        return self.backend.render_interactive(graph, **kwargs)
    
    def set_backend(self, backend: str):
        """切换渲染后端"""
        self.backend = self._create_backend(backend)


# 便捷函数
def render_reasoning_graph(steps: List[Dict], backend: str = "mermaid") -> str:
    """从推理步骤生成并渲染推理图"""
    graph = GraphIR(title="推理图", layout="dagre")
    
    # 添加节点
    for i, step in enumerate(steps):
        node_type = NodeType.STEP
        if step.get("is_error"):
            node_type = NodeType.ERROR
        elif step.get("type") == "formula":
            node_type = NodeType.FORMULA
        
        graph.add_node(GraphNode(
            id=f"step_{i}",
            label=step.get("content", f"步骤{i+1}"),
            node_type=node_type,
            properties={"score": step.get("score"), "is_error": step.get("is_error")}
        ))
    
    # 添加边
    for i in range(len(steps) - 1):
        edge_type = EdgeType.TRANSFORMS
        if steps[i].get("is_error") or steps[i+1].get("is_error"):
            edge_type = EdgeType.ERROR_PROPAGATES
        
        graph.add_edge(GraphEdge(
            source=f"step_{i}",
            target=f"step_{i+1}",
            edge_type=edge_type
        ))
    
    renderer = GraphRenderer(backend)
    return renderer.render(graph)
