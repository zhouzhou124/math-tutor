"""knowledge_graph.py — 数学知识图谱

实现数学知识的结构化表示，支持：
- 知识点检索和关联
- 智能提示生成
- 错误诊断和修正建议
- 与推理DAG集成
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Union
from uuid import uuid4
import json


class EntityType(Enum):
    """知识图谱实体类型"""
    KNOWLEDGE_POINT = "knowledge_point"  # 知识点
    FORMULA = "formula"                   # 公式
    THEOREM = "theorem"                   # 定理
    METHOD = "method"                     # 方法
    CONCEPT = "concept"                   # 概念
    RULE = "rule"                         # 规则
    DEFINITION = "definition"             # 定义


class RelationType(Enum):
    """知识图谱关系类型"""
    PART_OF = "part_of"           # 属于
    DEPENDS_ON = "depends_on"     # 依赖
    DERIVES_FROM = "derives_from" # 推导自
    USES = "uses"                 # 使用
    IMPLIES = "implies"           # 蕴含
    SPECIALIZES = "specializes"   # 特化
    GENERALIZES = "generalizes"   # 泛化
    INSTANCE_OF = "instance_of"   # 实例


@dataclass
class KnowledgeEntity:
    """知识实体"""
    id: str
    type: EntityType
    name: str
    description: str = ""
    latex: str = ""
    examples: List[str] = field(default_factory=list)
    difficulty: str = "中等"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "description": self.description,
            "latex": self.latex,
            "examples": self.examples,
            "difficulty": self.difficulty,
            "metadata": self.metadata
        }


@dataclass
class KnowledgeRelation:
    """知识关系"""
    source_id: str
    target_id: str
    type: RelationType
    weight: float = 1.0
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "description": self.description
        }


class KnowledgeGraph:
    """数学知识图谱"""
    
    def __init__(self):
        self.entities: Dict[str, KnowledgeEntity] = {}
        self.relations: List[KnowledgeRelation] = []
        self._entity_counter = 0
        self._build_default_knowledge()
    
    def _generate_id(self, prefix: str = "entity") -> str:
        """生成唯一实体ID"""
        self._entity_counter += 1
        return f"{prefix}_{self._entity_counter}_{uuid4().hex[:8]}"
    
    def add_entity(self, 
                   entity_type: EntityType,
                   name: str,
                   description: str = "",
                   latex: str = "",
                   examples: List[str] = None,
                   difficulty: str = "中等",
                   **kwargs) -> str:
        """添加知识实体"""
        entity_id = self._generate_id()
        self.entities[entity_id] = KnowledgeEntity(
            id=entity_id,
            type=entity_type,
            name=name,
            description=description,
            latex=latex,
            examples=examples or [],
            difficulty=difficulty,
            metadata=kwargs
        )
        return entity_id
    
    def add_relation(self,
                     source_id: str,
                     target_id: str,
                     relation_type: RelationType,
                     weight: float = 1.0,
                     description: str = "") -> None:
        """添加关系"""
        if source_id not in self.entities:
            raise ValueError(f"源实体不存在: {source_id}")
        if target_id not in self.entities:
            raise ValueError(f"目标实体不存在: {target_id}")
        
        # 检查是否已存在相同关系
        for rel in self.relations:
            if rel.source_id == source_id and rel.target_id == target_id:
                rel.type = relation_type
                rel.weight = weight
                rel.description = description
                return
        
        self.relations.append(KnowledgeRelation(
            source_id=source_id,
            target_id=target_id,
            type=relation_type,
            weight=weight,
            description=description
        ))
    
    def get_entity(self, entity_id: str) -> Optional[KnowledgeEntity]:
        """获取实体"""
        return self.entities.get(entity_id)
    
    def get_relations_from(self, entity_id: str) -> List[KnowledgeRelation]:
        """获取从指定实体出发的关系"""
        return [r for r in self.relations if r.source_id == entity_id]
    
    def get_relations_to(self, entity_id: str) -> List[KnowledgeRelation]:
        """获取指向指定实体的关系"""
        return [r for r in self.relations if r.target_id == entity_id]
    
    def find_related_entities(self, 
                             entity_id: str,
                             relation_type: Optional[RelationType] = None) -> List[str]:
        """查找相关实体"""
        related = set()
        for rel in self.relations:
            if relation_type and rel.type != relation_type:
                continue
            if rel.source_id == entity_id:
                related.add(rel.target_id)
            elif rel.target_id == entity_id:
                related.add(rel.source_id)
        return list(related)
    
    def search_by_name(self, query: str) -> List[str]:
        """按名称搜索实体"""
        query = query.lower()
        results = []
        for entity_id, entity in self.entities.items():
            if query in entity.name.lower() or query in entity.description.lower():
                results.append(entity_id)
        return results
    
    def get_dependencies(self, entity_id: str) -> List[str]:
        """获取实体的依赖实体"""
        dependencies = set()
        for rel in self.get_relations_from(entity_id):
            if rel.type == RelationType.DEPENDS_ON:
                dependencies.add(rel.target_id)
        return list(dependencies)
    
    def suggest_next_steps(self, 
                          current_entity_ids: List[str],
                          goal_entity_id: Optional[str] = None) -> List[dict]:
        """根据当前知识点建议下一步学习内容"""
        suggestions = []
        
        for entity_id in current_entity_ids:
            # 获取当前实体的依赖
            dependencies = self.get_dependencies(entity_id)
            for dep_id in dependencies:
                dep = self.get_entity(dep_id)
                if dep:
                    suggestions.append({
                        "entity_id": dep_id,
                        "name": dep.name,
                        "type": dep.type.value,
                        "difficulty": dep.difficulty,
                        "reason": f"掌握 {self.get_entity(entity_id).name} 需要先掌握 {dep.name}"
                    })
        
        # 如果有目标，建议路径
        if goal_entity_id:
            path = self.find_path(current_entity_ids, goal_entity_id)
            if path:
                for entity_id in path:
                    entity = self.get_entity(entity_id)
                    if entity and entity_id not in current_entity_ids:
                        suggestions.append({
                            "entity_id": entity_id,
                            "name": entity.name,
                            "type": entity.type.value,
                            "difficulty": entity.difficulty,
                            "reason": f"这是到达目标 '{self.get_entity(goal_entity_id).name}' 的关键步骤"
                        })
        
        # 去重并按难度排序
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            key = s["entity_id"]
            if key not in seen:
                seen.add(key)
                unique_suggestions.append(s)
        
        # 按难度排序：简单 -> 中等 -> 困难
        difficulty_order = {"简单": 0, "中等": 1, "困难": 2}
        unique_suggestions.sort(key=lambda x: difficulty_order.get(x["difficulty"], 1))
        
        return unique_suggestions
    
    def find_path(self, 
                 start_ids: List[str],
                 target_id: str,
                 max_depth: int = 5) -> List[str]:
        """查找从起始实体到目标实体的路径"""
        visited = set(start_ids)
        queue = [(start_id, [start_id]) for start_id in start_ids]
        
        while queue:
            current_id, path = queue.pop(0)
            
            if current_id == target_id:
                return path
            
            if len(path) >= max_depth:
                continue
            
            for rel in self.get_relations_from(current_id):
                if rel.target_id not in visited:
                    visited.add(rel.target_id)
                    queue.append((rel.target_id, path + [rel.target_id]))
            
            for rel in self.get_relations_to(current_id):
                if rel.source_id not in visited:
                    visited.add(rel.source_id)
                    queue.append((rel.source_id, path + [rel.source_id]))
        
        return []
    
    def diagnose_error(self, 
                      error_context: str,
                      current_entity_ids: List[str]) -> List[dict]:
        """诊断错误并提供修正建议"""
        diagnoses = []
        
        # 分析错误上下文关键词
        keywords = ["导数", "积分", "极限", "求导", "微分", "不定积分", "定积分"]
        
        for keyword in keywords:
            if keyword in error_context:
                # 查找相关知识点
                related = self.search_by_name(keyword)
                for entity_id in related:
                    entity = self.get_entity(entity_id)
                    if entity:
                        dependencies = self.get_dependencies(entity_id)
                        missing_deps = [d for d in dependencies if d not in current_entity_ids]
                        
                        if missing_deps:
                            for dep_id in missing_deps[:3]:
                                dep = self.get_entity(dep_id)
                                if dep:
                                    diagnoses.append({
                                        "type": "missing_knowledge",
                                        "entity_id": dep_id,
                                        "name": dep.name,
                                        "suggestion": f"错误可能是因为缺少 '{dep.name}' 的知识，建议先学习"
                                    })
        
        # 通用诊断规则
        if "除以零" in error_context:
            diagnoses.append({
                "type": "common_error",
                "name": "除法运算错误",
                "suggestion": "检查分母是否为零，确保除法运算的合法性"
            })
        
        if "未定义" in error_context:
            diagnoses.append({
                "type": "common_error",
                "name": "未定义操作",
                "suggestion": "检查是否进行了未定义的数学操作，如负数开平方"
            })
        
        return diagnoses
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "entities": {eid: e.to_dict() for eid, e in self.entities.items()},
            "relations": [r.to_dict() for r in self.relations]
        }
    
    def save_to_file(self, filepath: str) -> None:
        """保存到文件"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def load_from_file(self, filepath: str) -> None:
        """从文件加载"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.entities = {}
        for eid, edata in data.get("entities", {}).items():
            self.entities[eid] = KnowledgeEntity(
                id=eid,
                type=EntityType(edata["type"]),
                name=edata["name"],
                description=edata.get("description", ""),
                latex=edata.get("latex", ""),
                examples=edata.get("examples", []),
                difficulty=edata.get("difficulty", "中等"),
                metadata=edata.get("metadata", {})
            )
        
        self.relations = []
        for rdata in data.get("relations", []):
            self.relations.append(KnowledgeRelation(
                source_id=rdata["source"],
                target_id=rdata["target"],
                type=RelationType(rdata["type"]),
                weight=rdata.get("weight", 1.0),
                description=rdata.get("description", "")
            ))
    
    def _build_default_knowledge(self):
        """构建默认知识图谱"""
        # === 微积分知识点 ===
        
        # 基础概念
        limit = self.add_entity(
            EntityType.KNOWLEDGE_POINT,
            "极限",
            "函数在某点附近的趋势值",
            difficulty="中等"
        )
        
        derivative = self.add_entity(
            EntityType.KNOWLEDGE_POINT,
            "导数",
            "函数的变化率",
            r"\frac{df}{dx} = \lim_{\Delta x \to 0} \frac{f(x+\Delta x) - f(x)}{\Delta x}",
            difficulty="中等"
        )
        
        integral = self.add_entity(
            EntityType.KNOWLEDGE_POINT,
            "积分",
            "函数曲线下的面积",
            r"\int f(x) dx",
            difficulty="中等"
        )
        
        # 导数公式
        power_rule = self.add_entity(
            EntityType.RULE,
            "幂函数求导法则",
            "x^n 的导数为 n*x^(n-1)",
            r"\frac{d}{dx} x^n = n x^{n-1}",
            difficulty="简单"
        )
        
        product_rule = self.add_entity(
            EntityType.RULE,
            "乘积法则",
            "两个函数乘积的导数",
            r"\frac{d}{dx}(u \cdot v) = u'v + uv'",
            difficulty="中等"
        )
        
        chain_rule = self.add_entity(
            EntityType.RULE,
            "链式法则",
            "复合函数求导",
            r"\frac{d}{dx} f(g(x)) = f'(g(x)) \cdot g'(x)",
            difficulty="困难"
        )
        
        # 积分公式
        power_integral = self.add_entity(
            EntityType.RULE,
            "幂函数积分公式",
            "x^n 的积分",
            r"\int x^n dx = \frac{x^{n+1}}{n+1} + C",
            difficulty="简单"
        )
        
        substitution = self.add_entity(
            EntityType.METHOD,
            "换元积分法",
            "通过变量替换简化积分",
            difficulty="中等"
        )
        
        integration_by_parts = self.add_entity(
            EntityType.METHOD,
            "分部积分法",
            "处理乘积形式的积分",
            r"\int u dv = uv - \int v du",
            difficulty="困难"
        )
        
        # 三角函数
        sin_derivative = self.add_entity(
            EntityType.RULE,
            "正弦函数求导",
            "sin(x) 的导数",
            r"\frac{d}{dx} \sin x = \cos x",
            difficulty="简单"
        )
        
        cos_derivative = self.add_entity(
            EntityType.RULE,
            "余弦函数求导",
            "cos(x) 的导数",
            r"\frac{d}{dx} \cos x = -\sin x",
            difficulty="简单"
        )
        
        # 关系
        self.add_relation(derivative, limit, RelationType.DEPENDS_ON, description="导数依赖极限概念")
        self.add_relation(integral, derivative, RelationType.DEPENDS_ON, description="积分是导数的逆运算")
        self.add_relation(power_rule, derivative, RelationType.PART_OF, description="幂函数求导是导数的基本规则")
        self.add_relation(product_rule, derivative, RelationType.PART_OF)
        self.add_relation(chain_rule, derivative, RelationType.PART_OF)
        self.add_relation(power_integral, integral, RelationType.PART_OF)
        self.add_relation(substitution, integral, RelationType.PART_OF)
        self.add_relation(integration_by_parts, integral, RelationType.PART_OF)
        self.add_relation(sin_derivative, derivative, RelationType.PART_OF)
        self.add_relation(cos_derivative, derivative, RelationType.PART_OF)
        self.add_relation(chain_rule, substitution, RelationType.USES, description="换元法使用链式法则")


def demo_knowledge_graph():
    """演示知识图谱功能"""
    kg = KnowledgeGraph()
    
    print("=" * 60)
    print("知识图谱演示")
    print("=" * 60)
    
    print(f"\n实体数量: {len(kg.entities)}")
    print(f"关系数量: {len(kg.relations)}")
    
    # 搜索知识点
    print("\n搜索 '导数':")
    results = kg.search_by_name("导数")
    for rid in results:
        entity = kg.get_entity(rid)
        print(f"  - {entity.name}: {entity.description}")
    
    # 查找依赖
    print("\n导数的依赖:")
    derivative_id = results[0]
    deps = kg.get_dependencies(derivative_id)
    for dep_id in deps:
        dep = kg.get_entity(dep_id)
        print(f"  - {dep.name}")
    
    # 建议下一步
    print("\n学习建议（当前掌握: 极限）:")
    suggestions = kg.suggest_next_steps([kg.search_by_name("极限")[0]])
    for s in suggestions[:3]:
        print(f"  - {s['name']}: {s['reason']}")
    
    # 错误诊断
    print("\n错误诊断（错误: '求导时出错'）:")
    diagnoses = kg.diagnose_error("求导时出错", [])
    for d in diagnoses[:3]:
        print(f"  - {d['suggestion']}")
    
    print("\n" + "=" * 60)
    return kg


if __name__ == "__main__":
    demo_knowledge_graph()