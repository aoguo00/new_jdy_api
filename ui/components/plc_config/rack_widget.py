# -*- coding: utf-8 -*-
"""
机架显示组件

可视化显示PLC机架布局和模块配置，支持：
- 多机架显示
- 模块槽位状态
- 实时配置更新
- 可视化反馈
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QScrollArea, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPalette

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import PLCModule, TransferDirection
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import PLCModule, TransferDirection

logger = logging.getLogger(__name__)


class SlotWidget(QWidget):
    """
    单个槽位显示组件
    """
    
    # 槽位点击信号
    slotClicked = Signal(int, int)  # rack_id, slot_id
    
    def __init__(self, rack_id: int, slot_id: int, parent=None):
        super().__init__(parent)
        self.rack_id = rack_id
        self.slot_id = slot_id
        self.module: Optional[PLCModule] = None
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        
        # 槽位号标签
        self.slot_label = QLabel(f"{self.slot_id}")
        self.slot_label.setAlignment(Qt.AlignCenter)
        self.slot_label.setFixedHeight(16)
        self.slot_label.setStyleSheet("""
            QLabel {
                font-size: 10px;
                font-weight: bold;
                color: #666;
                background-color: #f0f0f0;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.slot_label)
        
        # 模块显示区域
        self.module_display = QLabel("空")
        self.module_display.setAlignment(Qt.AlignCenter)
        self.module_display.setFixedSize(80, 50)
        self.module_display.setWordWrap(True)
        self._update_empty_style()
        layout.addWidget(self.module_display)
        
        # 设置整体固定大小
        self.setFixedSize(90, 75)
        
        # 设置可点击
        self.setStyleSheet("SlotWidget:hover { background-color: #f5f5f5; }")
    
    def set_module(self, module: Optional[PLCModule]):
        """设置模块"""
        self.module = module
        if module:
            self._update_module_style()
        else:
            self._update_empty_style()
    
    def _update_module_style(self):
        """更新模块样式"""
        if not self.module:
            return
        
        # 显示模块信息
        icon = self.module.icon if self.module.icon else "🔧"
        text = f"{icon}\n{self.module.model}"
        self.module_display.setText(text)
        
        # 根据模块类型设置颜色
        type_colors = {
            'CPU': '#1890ff',
            'DI': '#52c41a', 
            'DO': '#fa8c16',
            'AI': '#13c2c2',
            'AO': '#722ed1',
            'COM': '#eb2f96',
            'DP': '#f5222d'
        }
        
        bg_color = type_colors.get(self.module.module_type, '#d9d9d9')
        border_color = bg_color
        
        self.module_display.setStyleSheet(f"""
            QLabel {{
                border: 2px solid {border_color};
                border-radius: 4px;
                background-color: {bg_color}15;
                font-size: 9px;
                font-weight: bold;
                color: {bg_color};
                padding: 2px;
            }}
        """)
        
        # 设置工具提示
        tooltip = f"模块: {self.module.model}\n类型: {self.module.module_type}"
        if self.module.channels > 0:
            tooltip += f"\n通道数: {self.module.channels}"
        if self.module.description:
            tooltip += f"\n描述: {self.module.description}"
        self.module_display.setToolTip(tooltip)
    
    def _update_empty_style(self):
        """更新空槽位样式"""
        self.module_display.setText("空")
        self.module_display.setStyleSheet("""
            QLabel {
                border: 1px dashed #d9d9d9;
                border-radius: 4px;
                background-color: #fafafa;
                font-size: 10px;
                color: #8c8c8c;
                padding: 2px;
            }
        """)
        self.module_display.setToolTip("空槽位")
    
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.slotClicked.emit(self.rack_id, self.slot_id)
        super().mousePressEvent(event)


class RackWidget(QWidget):
    """
    单个机架显示组件
    """
    
    # 机架信号
    slotClicked = Signal(int, int)  # rack_id, slot_id
    
    def __init__(self, rack_id: int, slots_count: int = 16, parent=None):
        super().__init__(parent)
        self.rack_id = rack_id
        self.slots_count = slots_count
        self.slot_widgets: List[SlotWidget] = []
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 机架标题
        title = QLabel(f"机架 {self.rack_id}")
        title.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title.setStyleSheet("""
            QLabel {
                color: #1890ff;
                padding: 4px;
                border-bottom: 2px solid #1890ff;
            }
        """)
        layout.addWidget(title)
        
        # 槽位网格
        slots_container = QWidget()
        grid_layout = QGridLayout(slots_container)
        grid_layout.setSpacing(4)
        
        # 创建槽位 (假设2行布局)
        rows = 2
        cols = (self.slots_count + rows - 1) // rows  # 向上取整
        
        for i in range(self.slots_count):
            slot_widget = SlotWidget(self.rack_id, i, self)
            slot_widget.slotClicked.connect(self.slotClicked.emit)
            
            row = i // cols
            col = i % cols
            grid_layout.addWidget(slot_widget, row, col)
            
            self.slot_widgets.append(slot_widget)
        
        layout.addWidget(slots_container)
        
        # 设置样式
        self.setStyleSheet("""
            RackWidget {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                background-color: white;
                margin: 4px;
            }
        """)
    
    def set_module_at_slot(self, slot_id: int, module: Optional[PLCModule]):
        """在指定槽位设置模块"""
        if 0 <= slot_id < len(self.slot_widgets):
            self.slot_widgets[slot_id].set_module(module)
        else:
            logger.warning(f"槽位ID超出范围: {slot_id}")
    
    def clear_all_slots(self):
        """清空所有槽位"""
        for slot_widget in self.slot_widgets:
            slot_widget.set_module(None)
    
    def get_module_at_slot(self, slot_id: int) -> Optional[PLCModule]:
        """获取指定槽位的模块"""
        if 0 <= slot_id < len(self.slot_widgets):
            return self.slot_widgets[slot_id].module
        return None


class RackDisplayWidget(QWidget):
    """
    机架显示主组件
    
    管理多个机架的显示和交互
    """
    
    # 信号定义
    slotClicked = Signal(int, int)  # rack_id, slot_id
    configurationChanged = Signal(dict)  # 配置变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rack_widgets: List[RackWidget] = []
        self.rack_info: Dict[str, Any] = {}
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 状态信息
        self.status_label = QLabel("请选择项目以显示机架配置")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 12px;
                padding: 20px;
                border: 1px dashed #d9d9d9;
                border-radius: 4px;
                background-color: #fafafa;
            }
        """)
        layout.addWidget(self.status_label)
        
        # 滚动区域用于显示机架
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # 机架容器
        self.racks_container = QWidget()
        self.racks_layout = QVBoxLayout(self.racks_container)
        self.racks_layout.setSpacing(12)
        
        self.scroll_area.setWidget(self.racks_container)
        layout.addWidget(self.scroll_area)
        
        # 初始状态隐藏滚动区域
        self.scroll_area.hide()
        
        logger.info("RackDisplayWidget: UI设置完成")
    
    def set_rack_info(self, rack_info: Dict[str, Any]):
        """设置机架信息"""
        self.rack_info = rack_info.copy()
        
        rack_count = rack_info.get('rack_count', 0)
        slots_per_rack = rack_info.get('slots_per_rack', 16)
        system_type = rack_info.get('system_type', '未知')
        
        logger.info(f"设置机架信息: {rack_count}个机架, 每个{slots_per_rack}槽位, 系统类型: {system_type}")
        
        # 清除现有机架
        self.clear_racks()
        
        if rack_count > 0:
            # 创建机架组件
            for rack_id in range(1, rack_count + 1):
                self._add_rack(rack_id, slots_per_rack)
            
            # 显示机架区域
            self.status_label.hide()
            self.scroll_area.show()
        else:
            # 显示空状态
            self.status_label.setText("未检测到PLC机架配置")
            self.status_label.show()
            self.scroll_area.hide()
    
    def _add_rack(self, rack_id: int, slots_count: int):
        """添加机架"""
        rack_widget = RackWidget(rack_id, slots_count, self)
        rack_widget.slotClicked.connect(self._on_slot_clicked)
        
        self.rack_widgets.append(rack_widget)
        self.racks_layout.addWidget(rack_widget)
        
        logger.debug(f"添加机架 {rack_id}, {slots_count} 个槽位")
    
    def _on_slot_clicked(self, rack_id: int, slot_id: int):
        """处理槽位点击"""
        logger.info(f"槽位点击: 机架{rack_id}, 槽位{slot_id}")
        self.slotClicked.emit(rack_id, slot_id)
    
    def update_configuration(self, config: Dict[Tuple[int, int], str]):
        """
        更新配置显示
        
        Args:
            config: 配置字典 {(rack_id, slot_id): model_name}
        """
        logger.info(f"更新机架配置显示: {len(config)} 个模块")
        
        # 清空所有槽位
        for rack_widget in self.rack_widgets:
            rack_widget.clear_all_slots()
        
        # 应用新配置
        for (rack_id, slot_id), model_name in config.items():
            self._set_module_at_position(rack_id, slot_id, model_name)
        
        self.configurationChanged.emit({'type': 'display_updated', 'config': config})
    
    def _set_module_at_position(self, rack_id: int, slot_id: int, model_name: str):
        """在指定位置设置模块"""
        # 查找对应的机架
        rack_widget = self._find_rack_widget(rack_id)
        if not rack_widget:
            logger.warning(f"找不到机架 {rack_id}")
            return
        
        # 将内部槽位号转换为界面显示槽位号
        # 内部槽位从1开始，界面显示从0开始
        display_slot_id = slot_id - 1 if slot_id > 0 else 0
        
        # 确保槽位ID在有效范围内
        if display_slot_id < 0 or display_slot_id >= len(rack_widget.slot_widgets):
            logger.warning(f"槽位ID超出范围: 内部槽位{slot_id} -> 显示槽位{display_slot_id}")
            return
        
        # 创建简化的模块对象用于显示
        # 这里可以根据model_name从IODataLoader获取详细信息
        module = PLCModule(
            key=f"rack_{rack_id}_slot_{slot_id}",
            title=model_name,
            description=f"机架{rack_id} 槽位{display_slot_id}",  # 使用显示槽位号
            model=model_name,
            module_type=self._guess_module_type(model_name),
            manufacturer="和利时",
            icon=self._get_module_icon(model_name)
        )
        
        rack_widget.set_module_at_slot(display_slot_id, module)
        logger.debug(f"在机架{rack_id}内部槽位{slot_id}(显示槽位{display_slot_id})设置模块: {model_name}")
    
    def _find_rack_widget(self, rack_id: int) -> Optional[RackWidget]:
        """查找指定ID的机架组件"""
        for rack_widget in self.rack_widgets:
            if rack_widget.rack_id == rack_id:
                return rack_widget
        return None
    
    def _guess_module_type(self, model_name: str) -> str:
        """根据模块型号猜测类型"""
        model_upper = model_name.upper()
        
        if 'CPU' in model_upper or 'LE5118' in model_upper:
            return 'CPU'
        elif 'LK610' in model_upper or (any(x in model_upper for x in ['DI']) and 'DO' not in model_upper):
            return 'DI'
        elif 'LK710' in model_upper or (any(x in model_upper for x in ['DO']) and 'DI' not in model_upper):
            return 'DO'
        elif 'LK411' in model_upper or (any(x in model_upper for x in ['AI']) and 'AO' not in model_upper):
            return 'AI'
        elif 'LK421' in model_upper or (any(x in model_upper for x in ['AO']) and 'AI' not in model_upper):
            return 'AO'
        elif 'LK238' in model_upper or 'COM' in model_upper:
            return 'COM'
        elif 'PROFIBUS-DP' in model_upper or model_upper == 'DP':
            return 'DP'
        else:
            return 'OTHER'
    
    def _get_module_icon(self, model_name: str) -> str:
        """根据模块型号获取图标"""
        module_type = self._guess_module_type(model_name)
        
        icon_map = {
            'CPU': '🖥️',
            'DI': '📥',
            'DO': '📤',
            'AI': '📊',
            'AO': '📈',
            'COM': '🌐',
            'DP': '🔗',
            'OTHER': '🔧'
        }
        
        return icon_map.get(module_type, '🔧')
    
    def clear_rack(self):
        """清空机架显示"""
        for rack_widget in self.rack_widgets:
            rack_widget.clear_all_slots()
        
        logger.info("已清空所有机架显示")
    
    def clear_racks(self):
        """清除所有机架组件"""
        for rack_widget in self.rack_widgets:
            self.racks_layout.removeWidget(rack_widget)
            rack_widget.deleteLater()
        
        self.rack_widgets.clear()
        logger.info("已清除所有机架组件")
    
    def get_rack_count(self) -> int:
        """获取机架数量"""
        return len(self.rack_widgets)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_slots = sum(rack.slots_count for rack in self.rack_widgets)
        occupied_slots = 0
        
        for rack_widget in self.rack_widgets:
            for slot_widget in rack_widget.slot_widgets:
                if slot_widget.module is not None:
                    occupied_slots += 1
        
        return {
            'total_racks': len(self.rack_widgets),
            'total_slots': total_slots,
            'occupied_slots': occupied_slots,
            'free_slots': total_slots - occupied_slots,
            'occupancy_rate': (occupied_slots / total_slots * 100) if total_slots > 0 else 0
        } 