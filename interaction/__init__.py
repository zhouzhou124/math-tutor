"""interaction/ — 交互层核心模块

提供状态感知的交互能力，支持：
- 点击步骤展开/折叠
- 错误传播路径查看
- 依赖路径高亮
- 交互式推理探索

架构设计：
┌─────────────────────────────────────────────────────────┐
│                    Interaction Layer                    │
├─────────────────────────────────────────────────────────┤
│  StateManager — 管理交互状态（选中、展开、高亮等）      │
│  EventHandler — 处理用户事件（点击、悬停、拖拽等）      │
│  SelectionEngine — 选择逻辑（单选、多选、范围选择）    │
│  NavigationEngine — 导航逻辑（前进、后退、跳转）      │
└─────────────────────────────────────────────────────────┘
"""
from typing import Any, Callable, Dict, List, Optional, Set, Union
from enum import Enum
from dataclasses import dataclass, field


class InteractionType(Enum):
    """交互类型枚举"""
    CLICK = "click"
    HOVER = "hover"
    SELECT = "select"
    EXPAND = "expand"
    COLLAPSE = "collapse"
    DRAG = "drag"
    NAVIGATE = "navigate"


class SelectionMode(Enum):
    """选择模式"""
    SINGLE = "single"
    MULTIPLE = "multiple"
    RANGE = "range"


@dataclass
class InteractionState:
    """交互状态数据类"""
    selected_ids: Set[str] = field(default_factory=set)
    expanded_ids: Set[str] = field(default_factory=set)
    highlighted_ids: Set[str] = field(default_factory=set)
    focused_id: Optional[str] = None
    selection_mode: SelectionMode = SelectionMode.SINGLE
    history: List["InteractionState"] = field(default_factory=list)
    history_index: int = -1


class StateManager:
    """状态管理器 — 管理所有交互状态"""
    
    def __init__(self):
        self.state = InteractionState()
        self.listeners: List[Callable[[InteractionState], None]] = []
    
    def select(self, item_id: str, multi_select: bool = False):
        """选择项目"""
        self._save_history()
        
        if multi_select:
            if item_id in self.state.selected_ids:
                self.state.selected_ids.remove(item_id)
            else:
                self.state.selected_ids.add(item_id)
        else:
            self.state.selected_ids = {item_id}
        
        self._notify_listeners()
    
    def toggle_expand(self, item_id: str):
        """切换展开/折叠状态"""
        self._save_history()
        
        if item_id in self.state.expanded_ids:
            self.state.expanded_ids.remove(item_id)
        else:
            self.state.expanded_ids.add(item_id)
        
        self._notify_listeners()
    
    def set_highlighted(self, item_ids: Set[str]):
        """设置高亮项目"""
        self.state.highlighted_ids = item_ids
        self._notify_listeners()
    
    def focus(self, item_id: Optional[str]):
        """聚焦到指定项目"""
        self.state.focused_id = item_id
        self._notify_listeners()
    
    def is_selected(self, item_id: str) -> bool:
        """检查项目是否被选中"""
        return item_id in self.state.selected_ids
    
    def is_expanded(self, item_id: str) -> bool:
        """检查项目是否展开"""
        return item_id in self.state.expanded_ids
    
    def is_highlighted(self, item_id: str) -> bool:
        """检查项目是否高亮"""
        return item_id in self.state.highlighted_ids
    
    def is_focused(self, item_id: str) -> bool:
        """检查项目是否聚焦"""
        return self.state.focused_id == item_id
    
    def clear_all(self):
        """清除所有状态"""
        self._save_history()
        self.state.selected_ids.clear()
        self.state.expanded_ids.clear()
        self.state.highlighted_ids.clear()
        self.state.focused_id = None
        self._notify_listeners()
    
    def undo(self):
        """撤销上一步操作"""
        if self.state.history_index > 0:
            self.state.history_index -= 1
            self.state = self.state.history[self.state.history_index].copy()
            self._notify_listeners()
    
    def redo(self):
        """重做下一步操作"""
        if self.state.history_index < len(self.state.history) - 1:
            self.state.history_index += 1
            self.state = self.state.history[self.state.history_index].copy()
            self._notify_listeners()
    
    def add_listener(self, listener: Callable[[InteractionState], None]):
        """添加状态变更监听器"""
        self.listeners.append(listener)
    
    def remove_listener(self, listener: Callable[[InteractionState], None]):
        """移除状态变更监听器"""
        if listener in self.listeners:
            self.listeners.remove(listener)
    
    def _save_history(self):
        """保存当前状态到历史记录"""
        # 截断当前位置之后的历史
        self.state.history = self.state.history[:self.state.history_index + 1]
        
        # 创建状态副本
        new_state = InteractionState(
            selected_ids=set(self.state.selected_ids),
            expanded_ids=set(self.state.expanded_ids),
            highlighted_ids=set(self.state.highlighted_ids),
            focused_id=self.state.focused_id,
            selection_mode=self.state.selection_mode,
            history=self.state.history.copy(),
            history_index=self.state.history_index + 1,
        )
        
        self.state.history.append(new_state)
        
        # 限制历史记录数量
        if len(self.state.history) > 50:
            self.state.history = self.state.history[-50:]
    
    def _notify_listeners(self):
        """通知所有监听器状态变更"""
        for listener in self.listeners:
            listener(self.state)


class EventHandler:
    """事件处理器 — 处理用户交互事件"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def handle_click(self, item_id: str, modifiers: Dict[str, bool] = None):
        """处理点击事件"""
        modifiers = modifiers or {}
        multi_select = modifiers.get('ctrl', False) or modifiers.get('meta', False)
        self.state_manager.select(item_id, multi_select)
    
    def handle_double_click(self, item_id: str):
        """处理双击事件 — 切换展开状态"""
        self.state_manager.toggle_expand(item_id)
    
    def handle_hover(self, item_id: str, enter: bool):
        """处理悬停事件"""
        if enter:
            self.state_manager.set_highlighted({item_id})
        else:
            self.state_manager.set_highlighted(set())
    
    def handle_key_press(self, key: str, modifiers: Dict[str, bool] = None):
        """处理键盘事件"""
        modifiers = modifiers or {}
        
        if key == 'Escape':
            self.state_manager.clear_all()
        elif key == 'z' and (modifiers.get('ctrl') or modifiers.get('meta')):
            if modifiers.get('shift'):
                self.state_manager.redo()
            else:
                self.state_manager.undo()


class SelectionEngine:
    """选择引擎 — 处理选择逻辑"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
    
    def select_range(self, start_id: str, end_id: str, item_order: List[str]):
        """选择范围内的项目"""
        try:
            start_idx = item_order.index(start_id)
            end_idx = item_order.index(end_id)
            min_idx, max_idx = min(start_idx, end_idx), max(start_idx, end_idx)
            
            self.state_manager._save_history()
            self.state_manager.state.selected_ids = set(item_order[min_idx:max_idx + 1])
            self.state_manager._notify_listeners()
        except ValueError:
            pass
    
    def select_all(self, item_ids: List[str]):
        """选择所有项目"""
        self.state_manager._save_history()
        self.state_manager.state.selected_ids = set(item_ids)
        self.state_manager._notify_listeners()
    
    def invert_selection(self, item_ids: List[str]):
        """反选"""
        self.state_manager._save_history()
        current = self.state_manager.state.selected_ids
        new_selection = set(item_ids) - current
        self.state_manager.state.selected_ids = new_selection
        self.state_manager._notify_listeners()


class NavigationEngine:
    """导航引擎 — 处理导航逻辑"""
    
    def __init__(self, state_manager: StateManager):
        self.state_manager = state_manager
        self.current_position = 0
        self.total_items = 0
    
    def go_to(self, position: int):
        """跳转到指定位置"""
        if 0 <= position < self.total_items:
            self.current_position = position
            # 可以在这里触发视图滚动等操作
    
    def next(self):
        """下一个"""
        if self.current_position < self.total_items - 1:
            self.current_position += 1
    
    def previous(self):
        """上一个"""
        if self.current_position > 0:
            self.current_position -= 1
    
    def first(self):
        """第一个"""
        self.current_position = 0
    
    def last(self):
        """最后一个"""
        self.current_position = max(0, self.total_items - 1)


# 全局状态管理器实例
_global_state_manager = StateManager()


def get_state_manager() -> StateManager:
    """获取全局状态管理器"""
    return _global_state_manager


def create_state_manager() -> StateManager:
    """创建新的状态管理器实例"""
    return StateManager()
