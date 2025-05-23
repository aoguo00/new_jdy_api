# -*- coding: utf-8 -*-
"""
增强版穿梭框组件

在原有功能基础上添加高级用户体验功能：
- 拖拽支持
- 键盘快捷键
- 动画过渡效果
- 视觉优化
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from PySide6.QtWidgets import (
    QWidget, QListWidget, QListWidgetItem, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QFrame, QMessageBox, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QTimer, QRect, QPoint, 
    QParallelAnimationGroup, QSequentialAnimationGroup, QMimeData
)
from PySide6.QtGui import (
    QDragEnterEvent, QDragMoveEvent, QDropEvent, QDrag, QPixmap, QPainter,
    QColor, QFont, QKeySequence, QShortcut, QCursor
)

# 设置日志
logger = logging.getLogger(__name__)

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import TransferItem, TransferDirection, TransferListState
    from .module_styles import format_module_display, get_module_style, get_module_icon
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import TransferItem, TransferDirection, TransferListState
    from ui.components.plc_config.module_styles import format_module_display, get_module_style, get_module_icon


class DragDropListWidget(QListWidget):
    """
    支持拖拽的列表组件
    实现拖拽移动项目到另一个列表
    """
    
    # 拖拽信号
    itemDropped = Signal(str, list)  # 目标列表ID, 被拖拽的项目keys
    dragStarted = Signal(str, list)  # 源列表ID, 开始拖拽的项目keys
    selectionChanged = Signal(list)  # 选择变化信号
    
    def __init__(self, list_id: str, title: str = "", parent=None):
        super().__init__(parent)
        self.list_id = list_id
        self.title = title
        self._render_template: Optional[Callable] = None
        self._setup_drag_drop()
        self._setup_visual_effects()
        
        # 连接选择变化信号
        self.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _setup_drag_drop(self):
        """设置拖拽功能"""
        # 启用拖拽
        self.setDragDropMode(QListWidget.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        
        # 设置选择模式
        self.setSelectionMode(QListWidget.ExtendedSelection)
        
        # 拖拽样式
        self.setStyleSheet("""
            DragDropListWidget {
                border: 2px dashed transparent;
                border-radius: 6px;
                background-color: #fafafa;
            }
            DragDropListWidget[drag_over="true"] {
                border: 2px dashed #1890ff;
                background-color: #e6f7ff;
            }
            DragDropListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
                background-color: white;
                border: 1px solid #f0f0f0;
            }
            DragDropListWidget::item:selected {
                background-color: #e6f7ff;
                border-color: #1890ff;
            }
            DragDropListWidget::item:hover {
                background-color: #f5f5f5;
                border-color: #d9d9d9;
            }
        """)
    
    def _setup_visual_effects(self):
        """设置视觉效果"""
        # 阴影效果
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setOffset(2, 2)
        shadow.setColor(QColor(0, 0, 0, 30))
        self.setGraphicsEffect(shadow)
        
        # 拖拽状态标记
        self._is_drag_over = False
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasText():
            # 检查是否是来自其他列表的拖拽
            source_list_id = event.mimeData().text().split('|')[0]
            if source_list_id != self.list_id:
                event.acceptProposedAction()
                self._set_drag_over_style(True)
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event: QDragMoveEvent):
        """拖拽移动事件"""
        if event.mimeData().hasText():
            source_list_id = event.mimeData().text().split('|')[0]
            if source_list_id != self.list_id:
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开事件"""
        self._set_drag_over_style(False)
        super().dragLeaveEvent(event)
    
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        self._set_drag_over_style(False)
        
        if event.mimeData().hasText():
            data = event.mimeData().text()
            parts = data.split('|')
            if len(parts) >= 2:
                source_list_id = parts[0]
                dropped_keys = parts[1].split(',')
                
                if source_list_id != self.list_id:
                    # 发出拖拽完成信号
                    self.itemDropped.emit(self.list_id, dropped_keys)
                    event.acceptProposedAction()
                    
                    # 播放放下动画
                    self._play_drop_animation()
                else:
                    event.ignore()
        else:
            event.ignore()
    
    def startDrag(self, supportedActions):
        """开始拖拽"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        # 获取选中项目的keys
        selected_keys = []
        draggable_keys = []  # 可拖拽的keys
        
        # 检查是否有不可拖拽的模块（当从右侧拖拽时）
        if self.list_id == "right":
            # 查找父组件的can_remove_from_right方法
            parent_widget = self.parent()
            while parent_widget:
                if hasattr(parent_widget, 'parent'):
                    grand_parent = parent_widget.parent()
                    if grand_parent and hasattr(grand_parent, 'can_remove_from_right'):
                        # 过滤可拖拽的项目
                        for item in selected_items:
                            transfer_item = item.data(Qt.UserRole)
                            if transfer_item:
                                key = transfer_item.key
                                selected_keys.append(key)
                                if grand_parent.can_remove_from_right(key):
                                    draggable_keys.append(key)
                        break
                parent_widget = parent_widget.parent() if hasattr(parent_widget, 'parent') else None
            
            # 如果有不可拖拽的项目，显示提示
            if selected_keys and not draggable_keys:
                QMessageBox.warning(self, "操作受限", 
                    "选中的模块不能被移除。\n\nLE_CPU系统中，LE5118 CPU模块必须固定在槽位0。")
                return
            elif len(draggable_keys) < len(selected_keys):
                QMessageBox.information(self, "提示", 
                    f"部分模块不能被移除。只有 {len(draggable_keys)} 个模块可以被拖拽。")
            
            selected_keys = draggable_keys
        else:
            # 左侧的所有项目都可以拖拽
            for item in selected_items:
                transfer_item = item.data(Qt.UserRole)
                if transfer_item:
                    selected_keys.append(transfer_item.key)
        
        if not selected_keys:
            return
        
        # 发出拖拽开始信号
        self.dragStarted.emit(self.list_id, selected_keys)
        
        # 创建拖拽数据
        drag = QDrag(self)
        
        # 创建MIME数据
        mime_data = QMimeData()
        
        # 设置MIME数据：list_id|key1,key2,key3
        data = f"{self.list_id}|{','.join(selected_keys)}"
        mime_data.setText(data)
        drag.setMimeData(mime_data)
        
        # 创建拖拽图标 - 使用实际的选中项目数量
        pixmap = self._create_drag_pixmap(len(selected_keys))
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        # 播放拖拽开始动画
        self._play_drag_start_animation()
        
        # 执行拖拽
        result = drag.exec_(Qt.MoveAction)
    
    def _create_drag_pixmap(self, item_count: int) -> QPixmap:
        """创建拖拽时的图标"""
        # 创建一个小的预览图
        text = f"{item_count} 项"
        
        pixmap = QPixmap(80, 40)
        pixmap.fill(QColor(24, 144, 255, 180))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制文本
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        
        painter.end()
        return pixmap
    
    def _set_drag_over_style(self, is_over: bool):
        """设置拖拽悬停样式"""
        self._is_drag_over = is_over
        self.setProperty("drag_over", "true" if is_over else "false")
        self.style().polish(self)
    
    def _play_drag_start_animation(self):
        """播放拖拽开始动画"""
        effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(effect)
        
        self.drag_animation = QPropertyAnimation(effect, b"opacity")
        self.drag_animation.setDuration(200)
        self.drag_animation.setStartValue(1.0)
        self.drag_animation.setEndValue(0.7)
        self.drag_animation.setEasingCurve(QEasingCurve.OutCubic)
        self.drag_animation.start()
    
    def _play_drop_animation(self):
        """播放放下动画"""
        # 创建一个临时的视觉效果
        QTimer.singleShot(100, lambda: self._flash_effect())
    
    def _flash_effect(self):
        """闪烁效果"""
        original_color = self.palette().color(self.backgroundRole())
        
        # 快速改变背景色并恢复
        self.setStyleSheet(self.styleSheet() + """
            DragDropListWidget {
                background-color: #52c41a;
            }
        """)
        
        QTimer.singleShot(150, lambda: self.setStyleSheet(self.styleSheet().replace(
            "background-color: #52c41a;", ""
        )))

    def _on_selection_changed(self):
        """选择变化处理"""
        selected_keys = []
        for i in range(self.count()):
            item = self.item(i)
            if item.isSelected():
                transfer_item = item.data(Qt.UserRole)
                if transfer_item:
                    selected_keys.append(transfer_item.key)
        
        self.selectionChanged.emit(selected_keys)

    def set_render_template(self, template: Callable):
        """设置自定义渲染模板"""
        self._render_template = template

    def add_transfer_item(self, item: TransferItem):
        """添加穿梭框项目"""
        if self._render_template:
            list_item = self._render_template(item)
        else:
            list_item = self._create_default_item(item)
        
        if list_item:
            # 存储TransferItem到列表项
            list_item.setData(Qt.UserRole, item)
            self.addItem(list_item)

    def _create_default_item(self, item: TransferItem) -> QListWidgetItem:
        """创建默认的列表项"""
        list_item = QListWidgetItem()
        
        # 检查是否是PLCModule，以获取更多信息
        if hasattr(item, 'module_type') and hasattr(item, 'channels'):
            # 使用格式化函数生成显示文本
            display_text = format_module_display(
                item.title.replace(' 🔒', ''),  # 移除可能的锁图标
                item.module_type,
                item.channels
            )
            
            # 如果是固定模块，添加锁图标
            if '🔒' in item.title:
                display_text += ' 🔒'
                
            list_item.setText(display_text)
            
            # 获取样式
            style_dict = get_module_style(item.module_type, for_rack=False)
            
            # 创建内联样式
            style_parts = []
            for key, value in style_dict.items():
                style_parts.append(f"{key}: {value}")
            
            # 应用颜色样式到数据（稍后通过自定义绘制应用）
            list_item.setData(Qt.UserRole + 1, '; '.join(style_parts))
        else:
            # 原始方式
            icon_text = f"{item.icon} " if item.icon else "🔧 "
            text = f"{icon_text}{item.title}"
            list_item.setText(text)
        
        # 设置详细的工具提示
        tooltip_lines = []
        tooltip_lines.append(f"型号: {item.title}")
        
        if hasattr(item, 'module_type'):
            tooltip_lines.append(f"类型: {item.module_type}")
        
        if hasattr(item, 'channels') and item.channels > 0:
            tooltip_lines.append(f"通道数: {item.channels}")
        
        if item.description:
            tooltip_lines.append(f"描述: {item.description}")
        
        if hasattr(item, 'manufacturer'):
            tooltip_lines.append(f"制造商: {item.manufacturer}")
        
        # 如果有额外的详细信息
        if hasattr(item, 'data') and item.data:
            if 'details' in item.data:
                details = item.data['details']
                if isinstance(details, dict):
                    tooltip_lines.append("\n详细参数:")
                    for key, value in details.items():
                        # 转换键名为中文
                        key_cn = {
                            'input_voltage': '输入电压',
                            'power_consumption_max': '最大功耗',
                            'dimensions': '尺寸',
                            'operating_temperature': '工作温度',
                            'sensor_type': '传感器类型',
                            'signal_type': '信号类型',
                            'protocol': '通讯协议',
                            'features': '特性',
                            'nor_flash': 'NOR Flash容量',
                            'ddr_storage': 'DDR存储',
                            'mram_storage': 'MRAM存储',
                            'execution_speed': '执行速度',
                            'supports_protocols': '支持协议',
                            'installation_method': '安装方式',
                            'sram_storage': 'SRAM存储',
                            'dp_bus_speed': 'DP总线速度',
                            'pcie_bus_speed': 'PCIe总线速度',
                            'role': '角色',
                            'is_safety_module': '安全模块',
                            'is_master': '主站模块',
                            'slot_required': '需要槽位'
                        }.get(key, key)
                        
                        if isinstance(value, list):
                            tooltip_lines.append(f"  {key_cn}: {', '.join(str(v) for v in value)}")
                        elif isinstance(value, bool):
                            tooltip_lines.append(f"  {key_cn}: {'是' if value else '否'}")
                        else:
                            tooltip_lines.append(f"  {key_cn}: {value}")
        
        list_item.setToolTip('\n'.join(tooltip_lines))
        
        # 设置禁用状态
        if item.disabled:
            list_item.setFlags(list_item.flags() & ~Qt.ItemIsEnabled)
        
        # 存储原始TransferItem对象
        list_item.setData(Qt.UserRole, item)
        
        return list_item

    def get_selected_keys(self) -> List[str]:
        """获取选中项目的键列表"""
        selected_keys = []
        for i in range(self.count()):
            item = self.item(i)
            if item and item.isSelected():
                # 从item的data获取TransferItem对象，然后获取key
                transfer_item = item.data(Qt.UserRole)
                if transfer_item and hasattr(transfer_item, 'key'):
                    selected_keys.append(transfer_item.key)
                else:
                    # 如果没有TransferItem，使用text作为fallback
                    selected_keys.append(item.text())
        
        logger.debug(f"📋 获取选中键: {selected_keys}")
        return selected_keys
    
    def selectAll(self):
        """全选所有项目"""
        logger.info("🔘 执行全选操作")
        count = self.count()
        for i in range(count):
            item = self.item(i)
            if item:
                item.setSelected(True)
        logger.info(f"✅ 已全选 {count} 个项目")
        
        # 手动触发选择变化信号
        self._on_selection_changed()
    
    def clearSelection(self):
        """清除所有选择"""
        logger.info("🔄 清除所有选择")
        super().clearSelection()
        self._on_selection_changed()
    
    def deleteSelectedItems(self):
        """删除选中的项目"""
        selected_items = self.selectedItems()
        if not selected_items:
            logger.info("⚠️ 没有选中项目可删除")
            return []
        
        deleted_keys = []
        # 从后往前删除，避免索引问题
        for item in reversed(selected_items):
            # 从TransferItem获取key
            transfer_item = item.data(Qt.UserRole)
            if transfer_item and hasattr(transfer_item, 'key'):
                key = transfer_item.key
            else:
                key = item.text()
            deleted_keys.append(key)
            row = self.row(item)
            self.takeItem(row)
        
        logger.info(f"🗑️ 删除了 {len(deleted_keys)} 个项目: {deleted_keys}")
        self._on_selection_changed()
        return deleted_keys

    def clear_selection(self):
        """清空选择"""
        self.clearSelection()

    def clear_all(self):
        """清空所有项目"""
        self.clear()


class EnhancedTransferPanelWidget(QWidget):
    """
    增强版穿梭框面板
    添加拖拽支持和动画效果
    """
    
    def __init__(self, title: str, list_id: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.list_id = list_id
        self.setup_ui()
        self._replace_list_widget()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题栏
        header_layout = QHBoxLayout()
        
        # 标题标签
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        header_layout.addWidget(self.title_label)
        
        # 统计标签
        self.count_label = QLabel("0 项")
        self.count_label.setStyleSheet("color: #8c8c8c; font-size: 12px;")
        header_layout.addStretch()
        header_layout.addWidget(self.count_label)
        
        layout.addLayout(header_layout)
        
        # 列表组件占位（将在_replace_list_widget中创建）
        
        # 设置面板样式
        self.setStyleSheet("""
            EnhancedTransferPanelWidget {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 8px;
            }
        """)
    
    def update_count(self, count: int):
        """更新项目数量显示"""
        self.count_label.setText(f"{count} 项")
    
    def add_item(self, item: TransferItem):
        """添加项目"""
        self.list_widget.add_transfer_item(item)
        self.update_count(self.list_widget.count())
    
    def clear_items(self):
        """清空项目"""
        self.list_widget.clear_all()
        self.update_count(0)
    
    def _replace_list_widget(self):
        """创建支持拖拽的列表组件"""
        # 创建新的拖拽列表
        self.list_widget = DragDropListWidget(self.list_id, self.title, self)
        
        # 添加到布局（在标题后面）
        self.layout().addWidget(self.list_widget)
        
        # 连接拖拽信号
        self.list_widget.itemDropped.connect(self._on_item_dropped)
        self.list_widget.dragStarted.connect(self._on_drag_started)
    
    def _on_item_dropped(self, target_list_id: str, dropped_keys: List[str]):
        """处理项目拖拽放下"""
        logger.info(f"🎯 项目拖拽到 {target_list_id}: {dropped_keys}")
        # 这里应该触发传输逻辑
    
    def _on_drag_started(self, source_list_id: str, dragged_keys: List[str]):
        """处理拖拽开始"""
        logger.info(f"🎪 从 {source_list_id} 开始拖拽: {dragged_keys}")
    

class EnhancedTransferWidget(QWidget):
    """
    增强版穿梭框组件
    集成拖拽、键盘快捷键、动画等高级功能
    """
    
    # 信号定义 - 对应Angular事件
    selectChange = Signal(dict)      # 对应 (nzSelectChange)
    transferChange = Signal(dict)    # 对应 (nzChange)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 核心属性
        self._data_source: List[TransferItem] = []
        self._render_template: Optional[Callable] = None
        # 移除固定尺寸设置，改为最小尺寸
        self._min_size: Dict[str, Any] = {'width': 250, 'height': 350}
        
        # 状态管理
        self._state = TransferListState()
        
        # UI组件
        self.left_panel: Optional[EnhancedTransferPanelWidget] = None
        self.right_panel: Optional[EnhancedTransferPanelWidget] = None
        
        self.setup_ui()
        self.connect_signals()
        self._setup_enhanced_features()
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # 左侧面板
        self.left_panel = EnhancedTransferPanelWidget("可用模块", "left", self)
        # 设置拉伸因子，使面板能够自动扩展
        layout.addWidget(self.left_panel, 1)
        
        # 中间操作按钮区域
        button_layout = self.create_button_panel()
        layout.addLayout(button_layout)
        
        # 右侧面板
        self.right_panel = EnhancedTransferPanelWidget("已选模块", "right", self)
        # 设置拉伸因子，使面板能够自动扩展
        layout.addWidget(self.right_panel, 1)
        
        # 应用列表样式
        self.apply_list_style()
        
        # 设置主组件的焦点策略，确保能接收键盘事件
        self.setFocusPolicy(Qt.StrongFocus)
        logger.info("✅ 主组件焦点策略设置完成")
        
        # 设置tab顺序，确保焦点能正确在面板间切换
        self.setTabOrder(self.left_panel.list_widget, self.right_panel.list_widget)
        logger.info("✅ Tab顺序设置完成")
    
    def create_button_panel(self) -> QVBoxLayout:
        """创建中间操作按钮面板"""
        logger.info("🔧 开始创建按钮面板")
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.addStretch()
        
        # 移动到右侧按钮
        self.move_right_btn = QPushButton("►")
        self.move_right_btn.setFixedSize(32, 32)
        self.move_right_btn.setToolTip("移动到已选")
        self.move_right_btn.clicked.connect(lambda: self._on_move_right_clicked())
        layout.addWidget(self.move_right_btn)
        logger.info("✅ 右移按钮创建完成并连接信号")
        
        # 移动到左侧按钮
        self.move_left_btn = QPushButton("◄")
        self.move_left_btn.setFixedSize(32, 32)
        self.move_left_btn.setToolTip("移回可用")
        self.move_left_btn.clicked.connect(lambda: self._on_move_left_clicked())
        layout.addWidget(self.move_left_btn)
        logger.info("✅ 左移按钮创建完成并连接信号")
        
        layout.addStretch()
        
        # 按钮样式
        button_style = """
            QPushButton {
                background-color: #fafafa;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #e6f7ff;
                border-color: #40a9ff;
                color: #40a9ff;
            }
            QPushButton:pressed {
                background-color: #bae7ff;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                border-color: #d9d9d9;
                color: #bfbfbf;
            }
        """
        self.move_right_btn.setStyleSheet(button_style)
        self.move_left_btn.setStyleSheet(button_style)
        
        logger.info("🎨 按钮样式设置完成")
        return layout
    
    def connect_signals(self):
        """连接信号"""
        logger.info("🔗 开始连接信号")
        
        if self.left_panel and self.left_panel.list_widget:
            self.left_panel.list_widget.selectionChanged.connect(self._on_left_selection_changed)
            logger.info("✅ 左侧面板选择变化信号已连接")
        else:
            logger.error("❌ 左侧面板或列表组件未创建，无法连接信号")
            
        if self.right_panel and self.right_panel.list_widget:
            self.right_panel.list_widget.selectionChanged.connect(self._on_right_selection_changed)
            logger.info("✅ 右侧面板选择变化信号已连接")
        else:
            logger.error("❌ 右侧面板或列表组件未创建，无法连接信号")
        
        logger.info("🔗 信号连接完成")
    
    def apply_list_style(self):
        """应用列表样式"""
        if not (self.left_panel and self.right_panel):
            return
            
        width = self._min_size.get('width', 250)
        height = self._min_size.get('height', 350)
        
        # 设置面板最小尺寸而不是固定尺寸
        for panel in [self.left_panel, self.right_panel]:
            panel.setMinimumSize(width, height)
            # 设置大小策略，允许扩展
            panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # 列表组件也设置最小尺寸和大小策略
            panel.list_widget.setMinimumSize(width - 20, height - 60)
            panel.list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    
    def set_data_source(self, data: List[TransferItem]):
        """设置数据源"""
        # 保存旧数据用于动画对比
        old_left_count = len(self._state.left_items) if hasattr(self, '_state') else 0
        old_right_count = len(self._state.right_items) if hasattr(self, '_state') else 0
        
        self._data_source = data.copy()
        self._rebuild_state()
        self._refresh_display()
        
        # 播放数据加载动画
        self._play_data_load_animation(old_left_count, old_right_count)
    
    def _rebuild_state(self):
        """重建内部状态"""
        self._state = TransferListState()
        
        for item in self._data_source:
            if item.direction == TransferDirection.RIGHT:
                self._state.right_items.append(item)
            else:
                item.direction = TransferDirection.LEFT
                self._state.left_items.append(item)
    
    def _refresh_display(self):
        """刷新显示"""
        if not (self.left_panel and self.right_panel):
            return
        
        # 清空现有项目
        self.left_panel.clear_items()
        self.right_panel.clear_items()
        
        # 添加左侧项目
        for item in self._state.left_items:
            self.left_panel.add_item(item)
        
        # 添加右侧项目
        for item in self._state.right_items:
            self.right_panel.add_item(item)
        
        # 更新按钮状态
        self._update_button_states()
    
    def _on_left_selection_changed(self, selected_keys: List[str]):
        """左侧选择变化处理"""
        logger.info(f"📝 左侧选择变化: {selected_keys}")
        self._state.left_selected = set(selected_keys)
        self._update_button_states()
        
        # 发送选择变化事件
        select_data = {
            'direction': 'left',
            'checked': True,
            'list': selected_keys,
            'item': None
        }
        logger.info(f"📡 发送左侧选择变化信号: {select_data}")
        self.selectChange.emit(select_data)
    
    def _on_right_selection_changed(self, selected_keys: List[str]):
        """右侧选择变化处理"""
        logger.info(f"📝 右侧选择变化: {selected_keys}")
        self._state.right_selected = set(selected_keys)
        self._update_button_states()
        
        # 发送选择变化事件
        select_data = {
            'direction': 'right',
            'checked': True,
            'list': selected_keys,
            'item': None
        }
        logger.info(f"📡 发送右侧选择变化信号: {select_data}")
        self.selectChange.emit(select_data)
    
    def _update_button_states(self):
        """更新按钮启用状态"""
        left_count = len(self._state.left_selected)
        right_count = len(self._state.right_selected)
        
        # 右移按钮：左侧有选中项时启用
        right_enabled = left_count > 0
        self.move_right_btn.setEnabled(right_enabled)
        
        # 左移按钮：右侧有选中项时启用
        left_enabled = right_count > 0
        self.move_left_btn.setEnabled(left_enabled)
        
        logger.info(f"🔘 按钮状态更新: 左选{left_count}项->右移按钮{'启用' if right_enabled else '禁用'}, 右选{right_count}项->左移按钮{'启用' if left_enabled else '禁用'}")
    
    def move_to_right(self):
        """移动选中项到右侧"""
        logger.info(f"🔄 move_to_right 被调用，左侧选中项: {list(self._state.left_selected)}")
        
        if not self._state.left_selected:
            logger.warning("⚠️ move_to_right: 没有选中的项目")
            return
        
        selected_keys = list(self._state.left_selected)
        logger.info(f"🔄 准备移动项目到右侧: {selected_keys}")
        
        moved_keys = self._state.move_to_right(selected_keys)
        logger.info(f"🔄 状态管理器返回已移动项目: {moved_keys}")
        
        if moved_keys:
            self._refresh_display()
            logger.info(f"✅ 成功移动 {len(moved_keys)} 个项目到右侧")
            
            # 发送传输变化事件
            transfer_data = {
                'from': 'left',
                'to': 'right',
                'list': moved_keys
            }
            logger.info(f"📡 发送传输变化信号: {transfer_data}")
            self.transferChange.emit(transfer_data)
        else:
            logger.warning("⚠️ move_to_right: 没有项目被移动")
    
    def move_to_left(self):
        """移动选中项到左侧"""
        logger.info(f"🔄 move_to_left 被调用，右侧选中项: {list(self._state.right_selected)}")
        
        if not self._state.right_selected:
            logger.warning("⚠️ move_to_left: 没有选中的项目")
            return
        
        selected_keys = list(self._state.right_selected)
        logger.info(f"🔄 准备移动项目到左侧: {selected_keys}")
        
        # 默认情况下，所有选中的模块都可以移动
        movable_keys = selected_keys
        
        # 检查是否有不可移除的模块
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'can_remove_from_right'):
            parent_widget = parent_widget.parent()
        
        if parent_widget and hasattr(parent_widget, 'can_remove_from_right'):
            # 过滤掉不能移除的模块
            movable_keys = []
            blocked_keys = []
            
            for key in selected_keys:
                if parent_widget.can_remove_from_right(key):
                    movable_keys.append(key)
                else:
                    blocked_keys.append(key)
            
            if blocked_keys:
                # 显示提示信息
                if len(blocked_keys) == 1:
                    msg = f"模块 {blocked_keys[0]} 不能被移除。\n\nLE_CPU系统中，LE5118 CPU模块必须固定在槽位0。"
                else:
                    msg = f"以下模块不能被移除：\n{', '.join(blocked_keys)}\n\nLE_CPU系统中，LE5118 CPU模块必须固定在槽位0。"
                
                QMessageBox.warning(self, "操作受限", msg)
                
                # 如果没有可移动的模块，直接返回
                if not movable_keys:
                    logger.info("⚠️ 移动操作被阻止：所有模块都不能被移除")
                    return
        
        # 执行实际的移动操作
        moved_keys = self._state.move_to_left(movable_keys)
        logger.info(f"🔄 状态管理器返回已移动项目: {moved_keys}")
        
        if moved_keys:
            self._refresh_display()
            logger.info(f"✅ 成功移动 {len(moved_keys)} 个项目到左侧")
            
            # 发送传输变化事件
            transfer_data = {
                'from': 'right',
                'to': 'left',
                'list': moved_keys
            }
            logger.info(f"📡 发送传输变化信号: {transfer_data}")
            self.transferChange.emit(transfer_data)
        else:
            logger.warning("⚠️ move_to_left: 没有项目被移动")
    
    def get_right_items(self) -> List[TransferItem]:
        """获取右侧（已选）的所有项目"""
        return self._state.right_items.copy()
    
    def get_left_items(self) -> List[TransferItem]:
        """获取左侧（可用）的所有项目"""
        return self._state.left_items.copy()
    
    def clear_selections(self):
        """清空所有选择"""
        self._state.clear_selections()
        if self.left_panel:
            self.left_panel.list_widget.clear_selection()
        if self.right_panel:
            self.right_panel.list_widget.clear_selection()
        self._update_button_states()
    
    def _setup_enhanced_features(self):
        """设置增强功能"""
        # 设置拖拽连接（面板已在setup_ui中创建）
        self._connect_drag_signals()
        
        # 设置简化的全局快捷键
        self._setup_shortcuts()
        
        # 添加动画效果
        self._setup_animations()
        
        # 优化视觉效果
        self._enhance_visual_effects()
    
    def _connect_drag_signals(self):
        """连接拖拽信号"""
        # 连接拖拽信号到传输逻辑
        if self.left_panel:
            self.left_panel.list_widget.itemDropped.connect(self._handle_drag_drop)
        if self.right_panel:
            self.right_panel.list_widget.itemDropped.connect(self._handle_drag_drop)
    
    def _setup_animations(self):
        """设置动画效果"""
        # 创建动画组
        self.transfer_animation_group = QParallelAnimationGroup(self)
        
        # 按钮点击动画
        self._setup_button_animations()
    
    def _setup_button_animations(self):
        """设置按钮动画"""
        if hasattr(self, 'move_right_btn'):
            self.move_right_btn.clicked.connect(self._animate_move_right)
        if hasattr(self, 'move_left_btn'):
            self.move_left_btn.clicked.connect(self._animate_move_left)
    
    def _enhance_visual_effects(self):
        """增强视觉效果"""
        # 添加整体样式
        self.setStyleSheet("""
            EnhancedTransferWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8f9fa, stop: 1 #e9ecef);
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        # 添加面板间的分隔线
        self._add_separator_lines()
    
    def _add_separator_lines(self):
        """添加分隔线"""
        # 在按钮面板前后添加分隔线
        layout = self.layout()
        
        # 左分隔线
        left_separator = QFrame()
        left_separator.setFrameShape(QFrame.VLine)
        left_separator.setFrameShadow(QFrame.Sunken)
        left_separator.setStyleSheet("QFrame { color: #d9d9d9; }")
        layout.insertWidget(1, left_separator)
        
        # 右分隔线
        right_separator = QFrame()
        right_separator.setFrameShape(QFrame.VLine)
        right_separator.setFrameShadow(QFrame.Sunken)
        right_separator.setStyleSheet("QFrame { color: #d9d9d9; }")
        layout.insertWidget(4, right_separator)  # 考虑新添加的分隔线
    
    def _handle_drag_drop(self, target_list_id: str, dropped_keys: List[str]):
        """处理拖拽放下逻辑"""
        if target_list_id == "right":
            # 移动到右侧
            self._move_items_to_right(dropped_keys)
        elif target_list_id == "left":
            # 移动到左侧
            self._move_items_to_left(dropped_keys)
    
    def _handle_panel_move_request(self, source_list_id: str, selected_keys: List[str]):
        """处理面板移动请求（来自快捷键）"""
        if source_list_id == "left":
            # 从左侧移动到右侧
            self._move_items_to_right(selected_keys)
        elif source_list_id == "right":
            # 从右侧移动到左侧
            self._move_items_to_left(selected_keys)
    
    def _move_items_to_right(self, keys: List[str]):
        """通过拖拽移动项目到右侧"""
        # 设置选中状态
        self._state.left_selected = set(keys)
        
        # 执行移动
        self.move_to_right()
        
        # 播放传输动画
        self._play_transfer_animation("right")
    
    def _move_items_to_left(self, keys: List[str]):
        """通过拖拽移动项目到左侧"""
        # 默认情况下，所有选中的模块都可以移动
        movable_keys = keys
        
        # 检查是否有不可移除的模块
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'can_remove_from_right'):
            parent_widget = parent_widget.parent()
        
        if parent_widget and hasattr(parent_widget, 'can_remove_from_right'):
            # 过滤掉不能移除的模块
            movable_keys = []
            blocked_keys = []
            
            for key in keys:
                if parent_widget.can_remove_from_right(key):
                    movable_keys.append(key)
                else:
                    blocked_keys.append(key)
            
            if blocked_keys:
                # 显示提示信息
                if len(blocked_keys) == 1:
                    msg = f"模块 {blocked_keys[0]} 不能被移除。\n\nLE_CPU系统中，LE5118 CPU模块必须固定在槽位0。"
                else:
                    msg = f"以下模块不能被移除：\n{', '.join(blocked_keys)}\n\nLE_CPU系统中，LE5118 CPU模块必须固定在槽位0。"
                
                QMessageBox.warning(self, "操作受限", msg)
                
                # 如果没有可移动的模块，直接返回
                if not movable_keys:
                    logger.info("⚠️ 拖拽操作被阻止：所有模块都不能被移除")
                    return
        
        # 设置选中状态
        self._state.right_selected = set(movable_keys)
        
        # 执行移动
        self.move_to_left()
        
        # 播放传输动画
        self._play_transfer_animation("left")
    
    def _play_transfer_animation(self, direction: str):
        """播放传输动画"""
        # 创建简单的淡入淡出效果
        target_panel = self.right_panel if direction == "right" else self.left_panel
        
        effect = QGraphicsOpacityEffect()
        target_panel.setGraphicsEffect(effect)
        
        self.opacity_animation = QPropertyAnimation(effect, b"opacity")
        self.opacity_animation.setDuration(300)
        self.opacity_animation.setStartValue(0.5)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.OutBounce)
        self.opacity_animation.start()
        
        # 清理效果
        QTimer.singleShot(350, lambda: target_panel.setGraphicsEffect(None))
    
    def _animate_move_right(self):
        """右移按钮动画"""
        if not hasattr(self, 'move_right_btn'):
            return
            
        # 按钮缩放动画
        self._scale_button_animation(self.move_right_btn)
    
    def _animate_move_left(self):
        """左移按钮动画"""
        if not hasattr(self, 'move_left_btn'):
            return
            
        # 按钮缩放动画
        self._scale_button_animation(self.move_left_btn)
    
    def _scale_button_animation(self, button: QPushButton):
        """按钮缩放动画"""
        original_size = button.size()
        
        # 创建几何动画
        self.button_animation = QPropertyAnimation(button, b"geometry")
        self.button_animation.setDuration(150)
        
        # 计算缩放后的几何形状
        scaled_rect = QRect(button.geometry())
        center = scaled_rect.center()
        scaled_rect.setSize(original_size * 0.9)
        scaled_rect.moveCenter(center)
        
        self.button_animation.setStartValue(button.geometry())
        self.button_animation.setKeyValueAt(0.5, scaled_rect)
        self.button_animation.setEndValue(button.geometry())
        self.button_animation.setEasingCurve(QEasingCurve.OutElastic)
        self.button_animation.start()
    
    def _play_data_load_animation(self, old_left_count: int, old_right_count: int):
        """播放数据加载动画"""
        new_left_count = len(self._state.left_items)
        new_right_count = len(self._state.right_items)
        
        # 如果数据发生变化，播放数字计数动画
        if old_left_count != new_left_count:
            self._animate_count_change(self.left_panel, old_left_count, new_left_count)
        
        if old_right_count != new_right_count:
            self._animate_count_change(self.right_panel, old_right_count, new_right_count)
    
    def _animate_count_change(self, panel: EnhancedTransferPanelWidget, old_count: int, new_count: int):
        """播放计数变化动画"""
        # 创建一个临时的计数动画效果
        panel.count_label.setStyleSheet(panel.count_label.styleSheet() + """
            QLabel { 
                color: #52c41a; 
                font-weight: bold; 
            }
        """)
        
        # 延迟恢复样式 - 添加安全检查
        def restore_style():
            try:
                if panel and hasattr(panel, 'count_label') and panel.count_label:
                    current_style = panel.count_label.styleSheet()
                    if current_style and "color: #52c41a; font-weight: bold;" in current_style:
                        panel.count_label.setStyleSheet(
                            current_style.replace("color: #52c41a; font-weight: bold;", "")
                        )
            except RuntimeError:
                # 对象已被销毁，忽略
                pass
        
        QTimer.singleShot(1000, restore_style)
    
    def _on_move_right_clicked(self):
        """右移按钮点击处理"""
        logger.info("🖱️ 右移按钮被点击")
        self.move_to_right()
    
    def _on_move_left_clicked(self):
        """左移按钮点击处理"""
        logger.info("🖱️ 左移按钮被点击")
        self.move_to_left()
    
    def _setup_shortcuts(self):
        """设置快捷键"""
        logger.info("⌨️ 开始设置快捷键")
        
        # 确保列表组件可以接收焦点
        if self.left_panel and self.left_panel.list_widget:
            self.left_panel.list_widget.setFocusPolicy(Qt.StrongFocus)
        if self.right_panel and self.right_panel.list_widget:
            self.right_panel.list_widget.setFocusPolicy(Qt.StrongFocus)
        
        # Ctrl+A 全选
        self.shortcut_select_all = QShortcut(QKeySequence.SelectAll, self)
        self.shortcut_select_all.activated.connect(self._handle_select_all)
        logger.info("✅ Ctrl+A 快捷键设置完成")
        
        # Enter 移动
        self.shortcut_move = QShortcut(QKeySequence(Qt.Key_Return), self)
        self.shortcut_move.activated.connect(self._handle_move)
        logger.info("✅ Enter 快捷键设置完成")
        
        # Delete 删除
        self.shortcut_delete = QShortcut(QKeySequence.Delete, self)
        self.shortcut_delete.activated.connect(self._handle_delete)
        logger.info("✅ Delete 快捷键设置完成")
    
    def _handle_select_all(self):
        """处理全选"""
        logger.info("⌨️ Ctrl+A 被触发")
        
        # 获取当前焦点组件
        focus_widget = self.focusWidget()
        logger.info(f"🎯 当前焦点: {focus_widget}")
        
        # 检查焦点在哪个列表
        if (self.left_panel and self.left_panel.list_widget and 
            self.left_panel.list_widget.hasFocus()):
            logger.info("🎯 在左侧列表执行全选")
            self.left_panel.list_widget.selectAll()
        elif (self.right_panel and self.right_panel.list_widget and 
              self.right_panel.list_widget.hasFocus()):
            logger.info("🎯 在右侧列表执行全选")
            self.right_panel.list_widget.selectAll()
        else:
            # 如果没有明确焦点，默认左侧
            logger.info("🎯 默认左侧列表执行全选")
            if self.left_panel and self.left_panel.list_widget:
                self.left_panel.list_widget.setFocus()
                self.left_panel.list_widget.selectAll()
    
    def _handle_move(self):
        """处理移动"""
        logger.info("⌨️ Enter 被触发")
        
        focus_widget = self.focusWidget()
        logger.info(f"🎯 当前焦点: {focus_widget}")
        
        # 检查焦点在哪个列表并执行移动
        if (self.left_panel and self.left_panel.list_widget and 
            self.left_panel.list_widget.hasFocus()):
            logger.info("🎯 从左侧移动到右侧")
            selected_keys = self.left_panel.list_widget.get_selected_keys()
            if selected_keys:
                self._state.left_selected = set(selected_keys)
                self.move_to_right()
            else:
                logger.info("⚠️ 左侧没有选中项")
        elif (self.right_panel and self.right_panel.list_widget and 
              self.right_panel.list_widget.hasFocus()):
            logger.info("🎯 从右侧移动到左侧")
            selected_keys = self.right_panel.list_widget.get_selected_keys()
            if selected_keys:
                self._state.right_selected = set(selected_keys)
                self.move_to_left()
            else:
                logger.info("⚠️ 右侧没有选中项")
        else:
            logger.info("⚠️ 没有焦点列表")
    
    def _handle_delete(self):
        """处理删除"""
        logger.info("⌨️ Delete 被触发")
        
        focus_widget = self.focusWidget()
        logger.info(f"🎯 当前焦点: {focus_widget}")
        
        # 检查焦点在哪个列表并执行删除
        if (self.left_panel and self.left_panel.list_widget and 
            self.left_panel.list_widget.hasFocus()):
            logger.info("🎯 从左侧删除选中项")
            deleted_keys = self.left_panel.list_widget.deleteSelectedItems()
            # 从状态中移除删除的项目
            for key in deleted_keys:
                self._state.left_items = [item for item in self._state.left_items if item.key != key]
                self._state.left_selected.discard(key)
            self._update_button_states()
        elif (self.right_panel and self.right_panel.list_widget and 
              self.right_panel.list_widget.hasFocus()):
            logger.info("🎯 从右侧删除选中项（移回左侧）")
            selected_keys = self.right_panel.list_widget.get_selected_keys()
            if selected_keys:
                self._state.right_selected = set(selected_keys)
                self.move_to_left()  # 右侧删除=移回左侧
            else:
                logger.info("⚠️ 右侧没有选中项")
        else:
            logger.info("⚠️ 没有焦点列表") 