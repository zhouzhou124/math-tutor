"""推理链渲染器 - 消费 ChainViewModel，返回 HTML String

Renderer 只负责构建 HTML，不调用任何 UI 框架。
"""

from ..cards import ReasoningStepCard
from ..tokens import StepStatus, STATUS_CSS_CLASS
from presentation.viewmodels import ChainViewModel, StepCardViewModel


class ReasoningRenderer:
    """推理链渲染器 - 返回 HTML"""
    
    @staticmethod
    def render_chain(vm: ChainViewModel, title: str = "推理链") -> str:
        parts = [f"### {title}\n\n"]
        
        for i, step_vm in enumerate(vm.steps):
            parts.append(ReasoningStepCard.render(step_vm))
            
            if i < len(vm.connectors):
                connector = vm.connectors[i]
                is_error = connector == "❌"
                connector_class = " error" if is_error else ""
                parts.append(f'\n<div class="mt-chain-connector{connector_class}">{connector}</div>\n')
        
        if vm.final_answer:
            from ..components import FormulaBlock
            parts.append("\n" + FormulaBlock.render(vm.final_answer))
        
        return "\n".join(parts)
    
    @staticmethod
    def render_chain_with_errors(vm: ChainViewModel, error_vms: list, title: str = "推理链（含错误分析）") -> str:
        from ..cards import ErrorHighlight
        
        parts = [f"### {title}\n\n"]
        
        for i, step_vm in enumerate(vm.steps):
            parts.append(ReasoningStepCard.render(step_vm))
            
            for err_vm in error_vms:
                if hasattr(err_vm, '_step_index') and err_vm._step_index == i:
                    parts.append("\n" + ErrorHighlight.render(err_vm))
            
            if i < len(vm.connectors):
                connector = vm.connectors[i]
                is_error = connector == "❌"
                connector_class = " error" if is_error else ""
                parts.append(f'\n<div class="mt-chain-connector{connector_class}">{connector}</div>\n')
        
        return "\n".join(parts)
    
    @staticmethod
    def render_dag(nodes: list, edges: list, title: str = "推理 DAG") -> str:
        node_html = ""
        for node in nodes:
            node_id = node.get("id", "")
            label = node.get("label", node_id)
            node_type = node.get("type", "")
            
            css_class = f"mt-dag-node {node_type}" if node_type else "mt-dag-node"
            node_html += f'<span class="{css_class}">{label}</span>'
        
        return f"""
        ### {title}
        
        <div class="mt-dag-container">
            {node_html}
        </div>
        """
