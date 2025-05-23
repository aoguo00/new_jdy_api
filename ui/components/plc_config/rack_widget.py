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
    from .module_styles import get_module_style, get_module_icon, get_module_color
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.module_styles import get_module_style, get_module_icon, get_module_color

logger = logging.getLogger(__name__)


class SlotWidget(QFrame):
    """
    单个槽位组件
    显示槽位号和模块信息
    """
    
    # 槽位点击信号
    slotClicked = Signal(int, int)  # rack_id, slot_id
    
    def __init__(self, slot_id: int, rack_id: int = 0, parent=None):
        super().__init__(parent)
        self.slot_id = slot_id
        self.rack_id = rack_id  # 保存rack_id用于信号
        self.module_name = None
        self.module_info = None  # 存储完整的模块信息
        self.setup_ui()
    
    def setup_ui(self):
        """设置UI"""
        self.setFixedSize(100, 80)  # 增加高度以显示更多信息
        self.setFrameStyle(QFrame.Box)
        
        # 布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # 槽位号标签
        self.slot_label = QLabel(f"槽位 {self.slot_id}")
        self.slot_label.setAlignment(Qt.AlignCenter)
        self.slot_label.setFont(QFont("Microsoft YaHei", 8))
        self.slot_label.setStyleSheet("""
            QLabel {
                color: #8c8c8c;
                font-size: 10px;
                padding: 2px;
            }
        """)
        layout.addWidget(self.slot_label)
        
        # 模块内容区域（包含图标和类型）
        self.module_content_widget = QWidget()
        self.module_content_layout = QVBoxLayout(self.module_content_widget)
        self.module_content_layout.setContentsMargins(0, 0, 0, 0)
        self.module_content_layout.setSpacing(2)
        
        # 模块图标和类型标签
        self.module_icon_label = QLabel("空")
        self.module_icon_label.setAlignment(Qt.AlignCenter)
        self.module_icon_label.setFont(QFont("Microsoft YaHei", 16))  # 更大的图标
        self.module_content_layout.addWidget(self.module_icon_label)
        
        # 模块型号标签
        self.module_name_label = QLabel("")
        self.module_name_label.setAlignment(Qt.AlignCenter)
        self.module_name_label.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.module_name_label.setWordWrap(True)
        self.module_content_layout.addWidget(self.module_name_label)
        
        layout.addWidget(self.module_content_widget)
        layout.addStretch()
        
        # 设置初始样式
        self._update_style()
    
    def set_module(self, module_name: str, module_info: Dict[str, Any] = None):
        """
        设置模块
        
        Args:
            module_name: 模块型号
            module_info: 模块完整信息（包含type, channels等）
        """
        self.module_name = module_name
        self.module_info = module_info or {}
        
        if module_name:
            # 获取模块类型
            module_type = self.module_info.get('type', '未知')
            
            # 设置图标
            icon = get_module_icon(module_type)
            self.module_icon_label.setText(icon)
            
            # 设置型号
            self.module_name_label.setText(module_name)
            
            # 设置工具提示
            self._update_tooltip()
        else:
            self.clear_module()
        
        self._update_style()
    
    def clear_module(self):
        """清空模块"""
        self.module_name = None
        self.module_info = None
        self.module_icon_label.setText("空")
        self.module_name_label.setText("")
        self.setToolTip(f"槽位 {self.slot_id}: 空")
        self._update_style()
    
    def _update_style(self):
        """更新样式"""
        if self.module_name and self.module_info:
            # 获取模块类型
            module_type = self.module_info.get('type', '未知')
            
            # 获取样式配置
            style_dict = get_module_style(module_type, for_rack=True)
            
            # 构建样式字符串
            style_parts = [
                "QFrame {",
                f"    background-color: {style_dict['background-color']};",
                f"    border: {style_dict['border']};",
                "    border-radius: 6px;",
                "}"
            ]
            
            self.setStyleSheet('\n'.join(style_parts))
            
            # 设置文字颜色
            self.module_name_label.setStyleSheet(f"""
                QLabel {{
                    color: {style_dict['color']};
                    font-weight: {style_dict['font-weight']};
                }}
            """)
            
            # 图标稍微透明
            self.module_icon_label.setStyleSheet("""
                QLabel {
                    background: transparent;
                }
            """)
        else:
            # 空槽位样式
            self.setStyleSheet("""
                QFrame {
                    background-color: #f5f5f5;
                    border: 2px dashed #d9d9d9;
                    border-radius: 6px;
                }
            """)
            self.module_icon_label.setStyleSheet("color: #bfbfbf;")
    
    def _update_tooltip(self):
        """更新工具提示"""
        if not self.module_name:
            self.setToolTip(f"槽位 {self.slot_id}: 空")
            return
        
        tooltip_lines = [f"槽位 {self.slot_id}"]
        tooltip_lines.append(f"型号: {self.module_name}")
        
        if self.module_info:
            if 'type' in self.module_info:
                tooltip_lines.append(f"类型: {self.module_info['type']}")
            
            if 'channels' in self.module_info and self.module_info['channels'] > 0:
                tooltip_lines.append(f"通道数: {self.module_info['channels']}")
            
            if 'description' in self.module_info:
                tooltip_lines.append(f"描述: {self.module_info['description']}")
            
            # 显示子通道信息
            if 'sub_channels' in self.module_info:
                sub_ch = self.module_info['sub_channels']
                sub_info = []
                for ch_type, ch_count in sub_ch.items():
                    sub_info.append(f"{ch_type}:{ch_count}")
                tooltip_lines.append(f"子通道: {', '.join(sub_info)}")
        
        self.setToolTip('\n'.join(tooltip_lines))

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
        
        # 机架标题（显示编号从1开始，内部ID从0开始）
        title = QLabel(f"机架 {self.rack_id + 1}")
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
            slot_widget = SlotWidget(i, self.rack_id, self)
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
    
    def set_module_at_slot(self, slot_id: int, module_name: str, module_info: Dict[str, Any] = None):
        """在指定槽位设置模块"""
        if 0 <= slot_id < len(self.slot_widgets):
            self.slot_widgets[slot_id].set_module(module_name, module_info)
        else:
            logger.warning(f"槽位ID超出范围: {slot_id}")
    
    def clear_all_slots(self):
        """清空所有槽位"""
        for slot_widget in self.slot_widgets:
            slot_widget.clear_module()
    
    def get_module_at_slot(self, slot_id: int) -> Optional[Dict[str, Any]]:
        """获取指定槽位的模块信息"""
        if 0 <= slot_id < len(self.slot_widgets):
            return self.slot_widgets[slot_id].module_info
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
        self.io_data_loader = None  # 添加IODataLoader引用
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
            for rack_id in range(rack_count):  # 从0开始
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
        
        # 槽位号转换逻辑
        # LE系统：内部槽位号就是显示槽位号（0-10）
        # LK系统：内部槽位号是1-11，显示槽位号是0-10
        system_type = self.rack_info.get('system_type', 'LK')
        if system_type == 'LE_CPU':
            # LE系统：槽位号不需要转换
            display_slot_id = slot_id
        else:
            # LK系统：内部槽位从1开始，界面显示从0开始
            display_slot_id = slot_id - 1 if slot_id > 0 else 0
        
        # 确保槽位ID在有效范围内
        if display_slot_id < 0 or display_slot_id >= len(rack_widget.slot_widgets):
            logger.warning(f"槽位ID超出范围: 内部槽位{slot_id}, 显示槽位{display_slot_id}")
            return
        
        # 获取模块的准确信息
        module_info = self._get_module_info(model_name)
        
        rack_widget.set_module_at_slot(display_slot_id, model_name, module_info)
        logger.debug(f"在机架{rack_id}内部槽位{slot_id}(显示槽位{display_slot_id})设置模块: {model_name}")
    
    def _get_module_info(self, model_name: str) -> Dict[str, Any]:
        """获取模块的准确信息"""
        # 优先从IODataLoader获取
        if self.io_data_loader:
            module_info = self.io_data_loader.get_module_by_model(model_name)
            if module_info:
                return {
                    'type': module_info.get('type', '未知'),
                    'model': model_name,
                    'channels': module_info.get('channels', 0),
                    'description': module_info.get('description', ''),
                    'sub_channels': module_info.get('sub_channels', {}),
                    'manufacturer': module_info.get('manufacturer', '和利时'),
                    'details': module_info.get('details', {})
                }
        
        # 如果没有IODataLoader或找不到模块信息，使用原来的猜测方法
        return {
            'type': self._guess_module_type(model_name),
            'model': model_name,
            'channels': self._guess_channels(model_name),
            'description': self._guess_description(model_name),
            'sub_channels': self._guess_sub_channels(model_name)
        }
    
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
    
    def _guess_channels(self, model_name: str) -> int:
        """根据模块型号猜测通道数"""
        model_upper = model_name.upper()
        
        if 'CPU' in model_upper or 'LE5118' in model_upper:
            return 0  # 默认CPU没有通道
        elif 'LK610' in model_upper or (any(x in model_upper for x in ['DI']) and 'DO' not in model_upper):
            return 1  # 默认DI有1个通道
        elif 'LK710' in model_upper or (any(x in model_upper for x in ['DO']) and 'DI' not in model_upper):
            return 1  # 默认DO有1个通道
        elif 'LK411' in model_upper or (any(x in model_upper for x in ['AI']) and 'AO' not in model_upper):
            return 1  # 默认AI有1个通道
        elif 'LK421' in model_upper or (any(x in model_upper for x in ['AO']) and 'AI' not in model_upper):
            return 1  # 默认AO有1个通道
        elif 'LK238' in model_upper or 'COM' in model_upper:
            return 0  # 默认COM没有通道
        elif 'PROFIBUS-DP' in model_upper or model_upper == 'DP':
            return 0  # 默认DP没有通道
        else:
            return 0  # 其他类型默认没有通道
    
    def _guess_description(self, model_name: str) -> str:
        """根据模块型号猜测描述"""
        model_upper = model_name.upper()
        
        if 'CPU' in model_upper or 'LE5118' in model_upper:
            return 'CPU模块'
        elif 'LK610' in model_upper or (any(x in model_upper for x in ['DI']) and 'DO' not in model_upper):
            return '数字输入模块'
        elif 'LK710' in model_upper or (any(x in model_upper for x in ['DO']) and 'DI' not in model_upper):
            return '数字输出模块'
        elif 'LK411' in model_upper or (any(x in model_upper for x in ['AI']) and 'AO' not in model_upper):
            return '模拟输入模块'
        elif 'LK421' in model_upper or (any(x in model_upper for x in ['AO']) and 'AI' not in model_upper):
            return '模拟输出模块'
        elif 'LK238' in model_upper or 'COM' in model_upper:
            return '通信模块'
        elif 'PROFIBUS-DP' in model_upper or model_upper == 'DP':
            return 'PROFIBUS-DP模块'
        else:
            return '未知模块'
    
    def _guess_sub_channels(self, model_name: str) -> Dict[str, Dict[str, int]]:
        """根据模块型号猜测子通道信息"""
        model_upper = model_name.upper()
        
        if 'CPU' in model_upper or 'LE5118' in model_upper:
            return {}  # CPU没有子通道
        elif 'LK610' in model_upper or (any(x in model_upper for x in ['DI']) and 'DO' not in model_upper):
            return {'DI': {x: 1 for x in ['A', 'B']}}
        elif 'LK710' in model_upper or (any(x in model_upper for x in ['DO']) and 'DI' not in model_upper):
            return {'DO': {x: 1 for x in ['A', 'B']}}
        elif 'LK411' in model_upper or (any(x in model_upper for x in ['AI']) and 'AO' not in model_upper):
            return {'AI': {x: 1 for x in ['A', 'B']}}
        elif 'LK421' in model_upper or (any(x in model_upper for x in ['AO']) and 'AI' not in model_upper):
            return {'AO': {x: 1 for x in ['A', 'B']}}
        elif 'LK238' in model_upper or 'COM' in model_upper:
            return {}  # COM没有子通道
        elif 'PROFIBUS-DP' in model_upper or model_upper == 'DP':
            return {}  # DP没有子通道
        else:
            return {}  # 其他类型默认没有子通道
    
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
                if slot_widget.module_info:
                    occupied_slots += 1
        
        return {
            'total_racks': len(self.rack_widgets),
            'total_slots': total_slots,
            'occupied_slots': occupied_slots,
            'free_slots': total_slots - occupied_slots,
            'occupancy_rate': (occupied_slots / total_slots * 100) if total_slots > 0 else 0
        }

    def set_io_data_loader(self, io_data_loader):
        """设置IODataLoader引用"""
        self.io_data_loader = io_data_loader 