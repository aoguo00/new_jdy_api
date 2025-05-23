# -*- coding: utf-8 -*-
"""
PLC配置工具类

提供常量定义、辅助函数和数据转换工具
"""

from typing import List, Dict, Any, Optional
from enum import Enum

# 模块类型常量
class ModuleType:
    """PLC模块类型常量"""
    CPU = "CPU"           # CPU模块
    DI = "DI"            # 数字输入
    DO = "DO"            # 数字输出
    AI = "AI"            # 模拟输入
    AO = "AO"            # 模拟输出
    COMM = "COMM"        # 通讯模块
    POWER = "POWER"      # 电源模块
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        """获取所有模块类型"""
        return [cls.CPU, cls.DI, cls.DO, cls.AI, cls.AO, cls.COMM, cls.POWER]
    
    @classmethod
    def get_io_types(cls) -> List[str]:
        """获取IO模块类型"""
        return [cls.DI, cls.DO, cls.AI, cls.AO]


# 模块图标映射
MODULE_ICONS = {
    ModuleType.CPU: '🖥️',
    ModuleType.DI: '📥',
    ModuleType.DO: '📤',
    ModuleType.AI: '📊',
    ModuleType.AO: '📈',
    ModuleType.COMM: '🔗',
    ModuleType.POWER: '🔌',
}

# 默认列表样式
DEFAULT_LIST_STYLE = {
    'width': 300,
    'height': 400,
    'border': '1px solid #d9d9d9',
    'border_radius': '4px',
    'background_color': '#fafafa'
}

# 颜色主题
COLORS = {
    'primary': '#1890ff',
    'success': '#52c41a',
    'warning': '#faad14',
    'error': '#f5222d',
    'border': '#d9d9d9',
    'background': '#fafafa',
    'text': '#262626',
    'text_secondary': '#8c8c8c',
    'hover': '#e6f7ff',
    'selected': '#bae7ff'
}


def get_module_icon(module_type: str) -> str:
    """
    根据模块类型获取图标
    
    Args:
        module_type: 模块类型
        
    Returns:
        str: 对应的emoji图标
    """
    return MODULE_ICONS.get(module_type.upper(), '🔧')


def convert_legacy_module_to_transfer_item(legacy_module: Dict[str, Any]) -> Dict[str, Any]:
    """
    将现有系统的模块字典转换为TransferItem格式
    
    Args:
        legacy_module: 现有系统的模块字典
        
    Returns:
        Dict: TransferItem格式的字典
    """
    module_type = legacy_module.get('type', '').upper()
    model = legacy_module.get('model', '')
    
    return {
        'key': legacy_module.get('unique_id', ''),
        'title': model,
        'description': f"{model} - {module_type}" + 
                      (f" ({legacy_module.get('channels', 0)}通道)" if legacy_module.get('channels', 0) > 0 else ""),
        'icon': get_module_icon(module_type),
        'model': model,
        'module_type': module_type,
        'channels': legacy_module.get('channels', 0),
        'unique_id': legacy_module.get('unique_id', ''),
        'manufacturer': legacy_module.get('manufacturer', '和利时'),
        'series': legacy_module.get('series', ''),
    }


def batch_convert_legacy_modules(legacy_modules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    批量转换现有系统的模块列表
    
    Args:
        legacy_modules: 现有系统的模块列表
        
    Returns:
        List[Dict]: TransferItem格式的模块列表
    """
    converted_modules = []
    for module in legacy_modules:
        try:
            converted = convert_legacy_module_to_transfer_item(module)
            converted_modules.append(converted)
        except Exception as e:
            print(f"转换模块失败: {module}, 错误: {e}")
    return converted_modules


def create_plc_render_template():
    """
    创建PLC模块的自定义渲染模板
    
    Returns:
        Callable: 渲染函数
    """
    from PySide6.QtWidgets import QListWidgetItem, QWidget, QHBoxLayout, QLabel, QVBoxLayout
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    
    def render_plc_module(transfer_item):
        """PLC模块自定义渲染函数"""
        list_item = QListWidgetItem()
        
        # 创建自定义widget
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 图标标签
        icon_label = QLabel(transfer_item.icon or '🔧')
        icon_label.setFont(QFont("Segoe UI Emoji", 16))
        layout.addWidget(icon_label)
        
        # 文本信息
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        # 主标题
        title_label = QLabel(transfer_item.title)
        title_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        text_layout.addWidget(title_label)
        
        # 描述信息
        if transfer_item.description:
            desc_label = QLabel(transfer_item.description)
            desc_label.setFont(QFont("Microsoft YaHei", 8))
            desc_label.setStyleSheet("color: #8c8c8c;")
            text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        # 设置到列表项
        list_item.setSizeHint(widget.sizeHint())
        
        return list_item
    
    return render_plc_module


def validate_transfer_item_data(data: Dict[str, Any]) -> bool:
    """
    验证TransferItem数据的有效性
    
    Args:
        data: 要验证的数据字典
        
    Returns:
        bool: 数据是否有效
    """
    required_fields = ['key', 'title']
    
    for field in required_fields:
        if field not in data or not data[field]:
            return False
    
    return True


def filter_modules_by_type(modules: List[Dict[str, Any]], module_types: List[str]) -> List[Dict[str, Any]]:
    """
    按模块类型过滤模块列表
    
    Args:
        modules: 模块列表
        module_types: 要过滤的模块类型列表
        
    Returns:
        List[Dict]: 过滤后的模块列表
    """
    if not module_types or '全部' in module_types:
        return modules
    
    filtered = []
    for module in modules:
        module_type = module.get('module_type', '').upper()
        if module_type in [t.upper() for t in module_types]:
            filtered.append(module)
    
    return filtered


def group_modules_by_type(modules: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    按模块类型分组
    
    Args:
        modules: 模块列表
        
    Returns:
        Dict: 按类型分组的模块字典
    """
    grouped = {}
    
    for module in modules:
        module_type = module.get('module_type', 'UNKNOWN').upper()
        if module_type not in grouped:
            grouped[module_type] = []
        grouped[module_type].append(module)
    
    return grouped


def calculate_rack_requirements(selected_modules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算机架需求
    
    Args:
        selected_modules: 已选择的模块列表
        
    Returns:
        Dict: 机架需求信息
    """
    total_modules = len(selected_modules)
    io_modules = [m for m in selected_modules if m.get('module_type', '').upper() in ModuleType.get_io_types()]
    cpu_modules = [m for m in selected_modules if m.get('module_type', '').upper() == ModuleType.CPU]
    
    # 假设每个机架16个槽位，第0个槽位放CPU
    slots_per_rack = 16
    available_slots_per_rack = slots_per_rack - 1  # 减去CPU槽位
    
    # 计算需要的机架数量
    rack_count = 1  # 至少需要一个机架
    if len(io_modules) > available_slots_per_rack:
        rack_count = (len(io_modules) + available_slots_per_rack - 1) // available_slots_per_rack
    
    return {
        'total_modules': total_modules,
        'io_modules': len(io_modules),
        'cpu_modules': len(cpu_modules),
        'required_racks': rack_count,
        'slots_per_rack': slots_per_rack,
        'estimated_usage': (len(io_modules) / (rack_count * available_slots_per_rack)) * 100
    }


class EventEmitter:
    """
    简单的事件发射器
    用于组件间通信
    """
    
    def __init__(self):
        self._callbacks = {}
    
    def on(self, event: str, callback):
        """注册事件监听器"""
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)
    
    def off(self, event: str, callback=None):
        """移除事件监听器"""
        if event not in self._callbacks:
            return
        
        if callback is None:
            del self._callbacks[event]
        else:
            try:
                self._callbacks[event].remove(callback)
            except ValueError:
                pass
    
    def emit(self, event: str, *args, **kwargs):
        """发射事件"""
        if event in self._callbacks:
            for callback in self._callbacks[event]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"事件处理器错误: {e}")


# 装饰器工具
def debounce(wait_time: float):
    """
    防抖装饰器
    在wait_time秒内只执行最后一次调用
    
    Args:
        wait_time: 等待时间（秒）
    """
    from PySide6.QtCore import QTimer
    
    def decorator(func):
        timer = QTimer()
        timer.setSingleShot(True)
        
        def wrapper(*args, **kwargs):
            timer.timeout.disconnect()
            timer.timeout.connect(lambda: func(*args, **kwargs))
            timer.start(int(wait_time * 1000))
        
        return wrapper
    return decorator


def throttle(wait_time: float):
    """
    节流装饰器
    在wait_time秒内最多执行一次
    
    Args:
        wait_time: 等待时间（秒）
    """
    import time
    
    def decorator(func):
        last_called = 0
        
        def wrapper(*args, **kwargs):
            nonlocal last_called
            now = time.time()
            if now - last_called >= wait_time:
                last_called = now
                return func(*args, **kwargs)
        
        return wrapper
    return decorator 