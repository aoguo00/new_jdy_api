# -*- coding: utf-8 -*-
"""
现代化PLC配置主组件

集成高级穿梭框和机架显示，提供完整的PLC配置界面。
这是新架构的核心组件，用于替代旧版PLCConfigEmbeddedWidget。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QFrame, 
    QPushButton, QGroupBox, QGridLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor, QPalette

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import PLCModule, TransferDirection
    from .enhanced_transfer_widget import EnhancedTransferWidget
    from .rack_widget import RackDisplayWidget
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import PLCModule, TransferDirection
    from ui.components.plc_config.enhanced_transfer_widget import EnhancedTransferWidget
    from ui.components.plc_config.rack_widget import RackDisplayWidget

logger = logging.getLogger(__name__)


class SystemInfoWidget(QWidget):
    """
    系统信息显示组件
    显示PLC系统类型、机架信息、配置状态等
    """
    
    # 信号定义
    apply_clicked = Signal()  # 应用配置按钮点击信号
    reset_clicked = Signal()  # 重置配置按钮点击信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.reset_info()
    
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)  # 减少上下边距
        
        # 创建信息标签组
        self.system_type_label = QLabel("系统类型: 未知")
        self.rack_count_label = QLabel("机架数量: 0")
        self.config_status_label = QLabel("配置状态: 未配置")
        self.io_count_label = QLabel("IO通道: 0")
        self.save_status_label = QLabel("保存状态: 未保存")
        
        # 设置样式 - 减小字体和内边距
        label_style = """
            QLabel {
                font-size: 11px;
                color: #595959;
                padding: 3px 6px;
                background-color: #f5f5f5;
                border-radius: 3px;
                margin-right: 6px;
            }
        """
        
        for label in [self.system_type_label, self.rack_count_label, 
                     self.config_status_label, self.io_count_label, 
                     self.save_status_label]:
            label.setStyleSheet(label_style)
        
        # 添加到布局
        layout.addWidget(self.system_type_label)
        layout.addWidget(self.rack_count_label)
        layout.addWidget(self.config_status_label)
        layout.addWidget(self.io_count_label)
        layout.addWidget(self.save_status_label)
        layout.addStretch()
        
        # 创建按钮组
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用配置")
        self.apply_btn.setEnabled(False)  # 初始禁用
        self.apply_btn.clicked.connect(self.apply_clicked.emit)
        button_layout.addWidget(self.apply_btn)
        
        # 添加重置配置按钮
        self.reset_btn = QPushButton("重置配置")
        self.reset_btn.setToolTip("清除当前场站的保存配置，重新从API获取数据")
        self.reset_btn.clicked.connect(self.reset_clicked.emit)
        button_layout.addWidget(self.reset_btn)
        
        layout.addLayout(button_layout)
        
        # 设置按钮样式
        button_style = """
            QPushButton {
                font-size: 12px;
                padding: 6px 12px;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                background-color: #fafafa;
                min-width: 80px;
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
        
        # 应用配置按钮 - 主要按钮样式
        apply_style = button_style + """
            QPushButton {
                background-color: #1890ff;
                color: white;
                border-color: #1890ff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #40a9ff;
                border-color: #40a9ff;
                color: white;
            }
            QPushButton:pressed {
                background-color: #096dd9;
            }
        """
        
        # 重置按钮 - 警告样式
        reset_style = button_style + """
            QPushButton {
                background-color: #ff7875;
                color: white;
                border-color: #ff7875;
            }
            QPushButton:hover {
                background-color: #ff9c99;
                border-color: #ff9c99;
                color: white;
            }
            QPushButton:pressed {
                background-color: #d9363e;
            }
        """
        
        self.apply_btn.setStyleSheet(apply_style)
        self.reset_btn.setStyleSheet(reset_style)
        
        # 设置整体样式 - 减小高度
        self.setStyleSheet("""
            SystemInfoWidget {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                max-height: 36px;
            }
        """)
        
        # 设置固定高度
        self.setFixedHeight(40)
    
    def update_system_info(self, system_type: str, rack_count: int):
        """更新系统信息"""
        self.system_type_label.setText(f"系统类型: {system_type}")
        self.rack_count_label.setText(f"机架数量: {rack_count}")
        
        # 更新系统类型标签颜色
        if system_type == "LK":
            self.system_type_label.setStyleSheet(self.system_type_label.styleSheet() + 
                                                "QLabel { color: #52c41a; }")
        elif system_type == "LE_CPU":
            self.system_type_label.setStyleSheet(self.system_type_label.styleSheet() + 
                                                "QLabel { color: #1890ff; }")
    
    def update_config_status(self, configured_count: int, total_slots: int):
        """更新配置状态"""
        if configured_count == 0:
            status_text = "未配置"
            color = "#8c8c8c"
            # 没有配置时禁用应用按钮
            self.apply_btn.setEnabled(False)
        elif configured_count < total_slots * 0.5:
            status_text = f"部分配置 ({configured_count}/{total_slots})"
            color = "#fa8c16"
            # 有配置时启用应用按钮
            self.apply_btn.setEnabled(True)
        else:
            status_text = f"已配置 ({configured_count}/{total_slots})"
            color = "#52c41a"
            # 有配置时启用应用按钮
            self.apply_btn.setEnabled(True)
        
        self.config_status_label.setText(f"配置状态: {status_text}")
        self.config_status_label.setStyleSheet(self.config_status_label.styleSheet() + 
                                              f"QLabel {{ color: {color}; }}")
    
    def update_io_count(self, io_count: int):
        """更新IO通道数"""
        self.io_count_label.setText(f"IO通道: {io_count}")
        
        # 根据通道数设置颜色
        if io_count == 0:
            color = "#8c8c8c"
        elif io_count < 100:
            color = "#fa8c16"
        else:
            color = "#52c41a"
        
        self.io_count_label.setStyleSheet(self.io_count_label.styleSheet() + 
                                         f"QLabel {{ color: {color}; }}")
    
    def update_save_status(self, is_saved: bool, site_name: str = ""):
        """更新保存状态"""
        if is_saved:
            status_text = f"已保存"
            color = "#52c41a"
            if site_name:
                status_text += f" ({site_name})"
        else:
            status_text = "未保存"
            color = "#ff4d4f"
        
        self.save_status_label.setText(f"保存状态: {status_text}")
        self.save_status_label.setStyleSheet(self.save_status_label.styleSheet() + 
                                           f"QLabel {{ color: {color}; }}")
    
    def reset_info(self):
        """重置信息"""
        self.system_type_label.setText("系统类型: 未知")
        self.rack_count_label.setText("机架数量: 0")
        self.config_status_label.setText("配置状态: 未配置")
        self.io_count_label.setText("IO通道: 0")
        self.save_status_label.setText("保存状态: 未保存")
        
        # 重置样式
        base_style = """
            QLabel {
                font-size: 11px;
                color: #595959;
                padding: 3px 6px;
                background-color: #f5f5f5;
                border-radius: 3px;
                margin-right: 6px;
            }
        """
        for label in [self.system_type_label, self.rack_count_label, 
                     self.config_status_label, self.io_count_label,
                     self.save_status_label]:
            label.setStyleSheet(base_style)


class PLCConfigWidget(QWidget):
    """
    现代化PLC配置主组件
    
    这是新架构的核心组件，集成了：
    - 增强版穿梭框 (EnhancedTransferWidget)
    - 机架显示 (RackDisplayWidget) 
    - 系统信息面板 (SystemInfoWidget)
    - 配置管理功能
    """
    
    # 信号定义
    configurationApplied = Signal(bool)  # 配置应用完成信号
    configurationReset = Signal()       # 配置重置信号，通知主窗口重新加载数据
    configurationChanged = Signal(dict)  # 配置变化信号
    
    def __init__(self, io_data_loader, parent=None):
        """
        初始化PLC配置组件
        
        Args:
            io_data_loader: IODataLoader实例
            parent: 父组件
        """
        super().__init__(parent)
        
        if not io_data_loader:
            logger.error("PLCConfigWidget 初始化错误: IODataLoader 实例未提供")
            self._show_error_ui("IODataLoader未提供")
            return
        
        self.io_data_loader = io_data_loader
        self._current_data_source: List[PLCModule] = []
        self._rack_info: Dict[str, Any] = {}
        
        self.setup_ui()
        self.connect_signals()
        
        logger.info("PLCConfigWidget: 初始化完成")
    
    def _show_error_ui(self, error_message: str):
        """显示错误UI"""
        layout = QVBoxLayout(self)
        error_label = QLabel(f"错误: {error_message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        layout.addWidget(error_label)
        
        self.io_data_loader = None
    
    def setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 顶部：系统信息面板
        self.system_info = SystemInfoWidget(self)
        layout.addWidget(self.system_info)
        
        # 中间：水平分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：高级穿梭框
        left_panel = self.create_transfer_panel()
        splitter.addWidget(left_panel)
        
        # 右侧：机架显示
        right_panel = self.create_rack_panel()
        splitter.addWidget(right_panel)
        
        # 设置分割比例
        splitter.setSizes([800, 600])
        layout.addWidget(splitter)
        
        # 设置整体样式
        self.setStyleSheet("""
            PLCConfigWidget {
                background-color: #fafafa;
            }
        """)
        
        logger.info("PLCConfigWidget: UI设置完成")
    
    def create_transfer_panel(self) -> QWidget:
        """创建穿梭框面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 标题
        title = QLabel("🔧 模块配置")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet("color: #262626; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # 增强版穿梭框
        self.transfer_widget = EnhancedTransferWidget(self)
        layout.addWidget(self.transfer_widget)
        
        return panel
    
    def create_rack_panel(self) -> QWidget:
        """创建机架显示面板"""
        panel = QFrame()
        panel.setFrameStyle(QFrame.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 标题
        title = QLabel("🏗️ 机架布局")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setStyleSheet("color: #262626; margin-bottom: 8px;")
        layout.addWidget(title)
        
        # 机架显示组件
        self.rack_widget = RackDisplayWidget(self)
        layout.addWidget(self.rack_widget)
        
        return panel
    
    def connect_signals(self):
        """连接信号"""
        if not hasattr(self, 'transfer_widget') or not self.transfer_widget:
            return
        
        # 穿梭框信号
        self.transfer_widget.transferChange.connect(self._on_transfer_change)
        
        # 系统信息面板信号
        if hasattr(self, 'system_info') and self.system_info:
            self.system_info.apply_clicked.connect(self.apply_configuration)
            self.system_info.reset_clicked.connect(self._on_reset_clicked)
        
        logger.debug("PLCConfigWidget: 信号连接完成")
    
    def _on_transfer_change(self, transfer_data: dict):
        """处理穿梭框变化"""
        logger.info(f"传输变化: {transfer_data}")
        
        # 更新机架显示
        self._update_rack_display()
        
        # 更新系统信息
        self._update_system_info()
        
        # 发出配置变化信号
        self.configurationChanged.emit(transfer_data)
    
    def _update_rack_display(self):
        """更新机架显示"""
        if not hasattr(self, 'rack_widget') or not self.rack_widget:
            return
        
        # 获取当前配置
        config = self._get_current_module_config()
        
        # 更新机架显示
        self.rack_widget.update_configuration(config)
        
        logger.debug("机架显示已更新")
    
    def _update_system_info(self):
        """更新系统信息"""
        if not hasattr(self, 'system_info') or not self.system_info:
            return
        
        try:
            # 获取系统信息
            rack_info = self.io_data_loader.get_rack_info()
            system_type = rack_info.get('system_type', '未知')
            rack_count = rack_info.get('rack_count', 0)
            
            # 获取配置状态
            config = self._get_current_module_config()
            configured_count = len(config)
            # 修改：使用可用槽数而不是物理槽数进行显示
            # 每个机架的可用槽数 = 物理槽数 - 1（槽位0通常被系统占用）
            available_slots_per_rack = rack_info.get('slots_per_rack', 11) - 1
            total_available_slots = rack_count * available_slots_per_rack
            
            # 获取IO通道数
            io_count = self._calculate_io_count()
            
            # 检查保存状态
            current_site = getattr(self.io_data_loader, 'current_site_name', None)
            is_saved = False
            if current_site and hasattr(self.io_data_loader, 'persistence_manager'):
                is_saved = self.io_data_loader.persistence_manager.has_site_config(current_site)
            
            # 更新显示
            self.system_info.update_system_info(system_type, rack_count)
            self.system_info.update_config_status(configured_count, total_available_slots)
            self.system_info.update_io_count(io_count)
            self.system_info.update_save_status(is_saved, current_site if current_site else "")
            
        except Exception as e:
            logger.error(f"更新系统信息失败: {e}", exc_info=True)
    
    def _get_current_module_config(self) -> Dict[Tuple[int, int], str]:
        """
        获取当前模块配置
        
        Returns:
            Dict[Tuple[int, int], str]: {(机架ID, 槽位ID): 模块型号}
        """
        try:
            config = {}
            rack_info = self.io_data_loader.get_rack_info()
            system_type = rack_info.get('system_type', 'LK')
            
            # 获取右侧已选择的模块
            right_items = self.transfer_widget.get_right_items()
            
            # 为LE_CPU系统自动添加LE5118 CPU到槽位0
            if system_type == 'LE_CPU':
                rack_id = 1  # LE系统通常只有一个机架
                config[(rack_id, 0)] = 'LE5118'  # 槽位0固定为LE5118 CPU
                logger.info(f"LE_CPU系统：自动在槽位0配置LE5118 CPU")
                
                # 用户配置的模块从槽位1开始
                for index, item in enumerate(right_items):
                    slot_id = index + 1  # LE系列用户配置从槽位1开始
                    
                    # 从PLCModule对象获取模型名称
                    if hasattr(item, 'model') and item.model:
                        model_name = item.model
                    else:
                        # 如果没有model属性，尝试从标题提取
                        model_name = item.title
                    
                    config[(rack_id, slot_id)] = model_name
                    logger.debug(f"LE系统配置槽位{slot_id}: {model_name}")
                    
            elif system_type == 'LK':
                # LK系列：槽位1为DP模块，用户配置从槽位2开始
                rack_id = 1  # LK系统主机架
                config[(rack_id, 1)] = 'PROFIBUS-DP'  # 槽位1固定为DP模块
                logger.info(f"LK系统：自动在槽位1配置PROFIBUS-DP模块")
                
                # 用户配置的模块从槽位2开始
                for index, item in enumerate(right_items):
                    slot_id = index + 2  # LK系列用户配置从槽位2开始
                    
                    # 从PLCModule对象获取模型名称
                    if hasattr(item, 'model') and item.model:
                        model_name = item.model
                    else:
                        model_name = item.title
                    
                    config[(rack_id, slot_id)] = model_name
                    logger.debug(f"LK系统配置槽位{slot_id}: {model_name}")
            
            logger.info(f"获取当前模块配置: 系统类型={system_type}, 配置={len(config)}个模块")
            return config
            
        except Exception as e:
            logger.error(f"获取当前模块配置失败: {e}", exc_info=True)
            return {}
    
    def _calculate_io_count(self) -> int:
        """计算IO通道总数 - 基于旧版PLCConfigEmbeddedWidget的统计逻辑"""
        try:
            # 获取当前配置的模块
            current_config = self._get_current_module_config()
            if not current_config:
                return 0
            
            # 按旧版逻辑统计各类型通道数
            summary = {
                "AI": 0, "AO": 0, "DI": 0, "DO": 0, 
                "未录入_IO": 0, "CPU_count": 0
            }
            
            # 遍历每个配置的模块
            for (rack_id, slot_id), model_name in current_config.items():
                try:
                    # 获取模块信息
                    module_info = self.io_data_loader.get_module_by_model(model_name)
                    if not module_info:
                        logger.warning(f"无法获取模块 {model_name} 的信息")
                        continue
                    
                    module_type = module_info.get('type', '未知')
                    total_channels = module_info.get('channels', 0)
                    
                    io_counted_for_module = False
                    
                    # 处理带子通道的CPU模块 (如LE5118)
                    if module_type == "CPU" and "sub_channels" in module_info:
                        summary["CPU_count"] += 1
                        for sub_type, sub_count in module_info["sub_channels"].items():
                            if sub_type in summary:
                                summary[sub_type] += sub_count
                        io_counted_for_module = True
                        logger.debug(f"CPU模块 {model_name} 子通道: {module_info['sub_channels']}")
                    
                    # 处理带子通道的混合IO模块 (DI/DO, AI/AO)
                    elif module_type in ["DI/DO", "AI/AO"] and "sub_channels" in module_info:
                        for sub_type, sub_count in module_info["sub_channels"].items():
                            if sub_type in summary:
                                summary[sub_type] += sub_count
                        io_counted_for_module = True
                        logger.debug(f"混合模块 {model_name} 子通道: {module_info['sub_channels']}")
                    
                    # 处理标准的单一类型IO模块
                    elif module_type in summary and module_type not in ['DP', 'COM', 'CPU', 'RACK']:
                        summary[module_type] += total_channels
                        io_counted_for_module = True
                        logger.debug(f"标准IO模块 {model_name} ({module_type}): {total_channels} 通道")
                    
                    # 处理没有子通道的CPU模块（仅计数CPU，不计IO）
                    elif module_type == "CPU" and "sub_channels" not in module_info:
                        summary["CPU_count"] += 1
                        logger.debug(f"标准CPU模块 {model_name}: 不计入IO通道")
                    
                    # 未统计的模块且有通道数的，计入未录入IO
                    elif not io_counted_for_module and module_type not in ['DP', 'COM', 'CPU', 'RACK', '未录入'] and total_channels > 0:
                        summary["未录入_IO"] += total_channels
                        logger.debug(f"未录入类型模块 {model_name} ({module_type}): {total_channels} 通道")
                    
                    else:
                        logger.debug(f"模块 {model_name} ({module_type}): 不计入IO统计")
                        
                except Exception as e:
                    logger.error(f"处理模块 {model_name} 时出错: {e}")
                    continue
            
            # 计算总IO通道数
            total_io_channels = sum(summary.get(t, 0) for t in ['AI', 'AO', 'DI', 'DO', '未录入_IO'])
            
            logger.info(f"IO通道统计完成:")
            for ch_type in ['AI', 'AO', 'DI', 'DO']:
                if summary.get(ch_type, 0) > 0:
                    logger.info(f"  {ch_type} 通道数: {summary[ch_type]}")
            if summary.get("未录入_IO", 0) > 0:
                logger.info(f"  未录入类型IO通道数: {summary['未录入_IO']}")
            if summary.get("CPU_count", 0) > 0:
                logger.info(f"  CPU模块数量: {summary['CPU_count']}")
            logger.info(f"  总IO通道数: {total_io_channels}")
            
            return total_io_channels
            
        except Exception as e:
            logger.error(f"计算IO通道数失败: {e}", exc_info=True)
            return 0
    
    # ========== 公共接口方法 ==========
    
    def set_data_source(self, modules: List[PLCModule]):
        """
        设置模块数据源
        
        Args:
            modules: PLCModule列表
        """
        logger.info(f"PLCConfigWidget: 设置数据源 {len(modules)} 个模块")
        
        self._current_data_source = modules.copy()
        
        # 更新穿梭框数据
        if hasattr(self, 'transfer_widget') and self.transfer_widget:
            self.transfer_widget.set_data_source(modules)
        
        # 更新系统信息
        self.update_system_info(self.io_data_loader.get_rack_info())
        
        logger.info("数据源设置完成")
    
    def update_system_info(self, rack_info: Dict[str, Any]):
        """
        更新系统信息
        
        Args:
            rack_info: 机架信息字典
        """
        self._rack_info = rack_info.copy()
        
        # 更新机架显示
        if hasattr(self, 'rack_widget') and self.rack_widget:
            self.rack_widget.set_rack_info(rack_info)
        
        # 更新系统信息面板
        self._update_system_info()
        
        logger.info(f"系统信息已更新: {rack_info.get('system_type', '未知')}")
    
    def reset_configuration(self):
        """重置配置"""
        try:
            # 确认对话框
            from PySide6.QtWidgets import QMessageBox
            
            current_site = getattr(self.io_data_loader, 'current_site_name', '未知场站')
            reply = QMessageBox.question(
                self, 
                "确认重置", 
                f"确定要重置场站 '{current_site}' 的配置吗？\n\n"
                "此操作将：\n"
                "• 删除已保存的配置文件\n"
                "• 清除穿梭框中的已选模块\n"
                "• 重新从API获取最新数据\n\n"
                "此操作不可撤销！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                logger.info("用户取消了重置操作")
                return
            
            logger.info(f"开始重置场站 '{current_site}' 的配置")
            
            # 1. 调用IODataLoader重置配置
            if self.io_data_loader and hasattr(self.io_data_loader, 'reset_current_site_config'):
                reset_success = self.io_data_loader.reset_current_site_config()
                if not reset_success:
                    QMessageBox.warning(self, "重置失败", "配置重置失败，请查看日志了解详细信息")
                    return
            else:
                logger.error("IODataLoader不支持reset_current_site_config方法")
                QMessageBox.critical(self, "错误", "重置功能不可用，请联系技术支持")
                return
            
            # 2. 重置UI状态
            self._reset_ui_state()
            
            # 3. 触发重新加载数据
            self._trigger_data_reload()
            
            # 4. 显示成功消息
            QMessageBox.information(
                self, 
                "重置成功", 
                f"场站 '{current_site}' 的配置已重置。\n\n"
                "系统将重新从API获取最新数据。"
            )
            
            logger.info(f"场站 '{current_site}' 配置重置成功")
            
        except Exception as e:
            logger.error(f"重置配置失败: {e}", exc_info=True)
            QMessageBox.critical(self, "重置失败", f"配置重置过程中发生错误：\n{str(e)}")
    
    def _reset_ui_state(self):
        """重置UI状态"""
        try:
            # 清空穿梭框选择
            if self.transfer_widget:
                self.transfer_widget.clear_selections()
                # 清空右侧已选项目
                if hasattr(self.transfer_widget, '_state'):
                    self.transfer_widget._state.right_items.clear()
                    self.transfer_widget._state.left_selected.clear()
                    self.transfer_widget._state.right_selected.clear()
                    self.transfer_widget._refresh_display()
            
            # 重置机架显示
            if self.rack_widget:
                self.rack_widget.clear_racks()
            
            # 重置系统信息显示
            if self.system_info:
                self.system_info.update_system_type("未知")
                self.system_info.update_rack_count(0)
                self.system_info.update_config_status("无配置")
                self.system_info.update_io_count(0)
                self.system_info.update_save_status(False)
            
            logger.info("UI状态已重置")
            
        except Exception as e:
            logger.error(f"重置UI状态失败: {e}", exc_info=True)
    
    def _trigger_data_reload(self):
        """触发数据重新加载"""
        try:
            # 发送信号通知父组件重新加载数据
            # 这里需要主窗口重新调用API获取设备数据
            self.configurationReset.emit()
            
            logger.info("已发送配置重置信号，等待数据重新加载")
            
        except Exception as e:
            logger.error(f"触发数据重新加载失败: {e}", exc_info=True)
    
    def show_empty_state(self, message: str):
        """
        显示空状态
        
        Args:
            message: 提示消息
        """
        # 更新穿梭框显示空状态
        if hasattr(self, 'transfer_widget') and self.transfer_widget:
            # 这里需要EnhancedTransferWidget支持显示空状态
            pass
        
        # 重置系统信息
        if hasattr(self, 'system_info') and self.system_info:
            self.system_info.reset_info()
        
        logger.info(f"显示空状态: {message}")
    
    def get_current_configuration(self) -> List[Dict[str, Any]]:
        """
        获取当前配置
        
        Returns:
            配置数据列表
        """
        try:
            config_dict = self._get_current_module_config()
            
            # 转换为列表格式
            config_list = []
            for (rack_id, slot_id), model in config_dict.items():
                config_list.append({
                    'rack_id': rack_id,
                    'slot_id': slot_id,
                    'model': model
                })
            
            logger.info(f"获取当前配置: {len(config_list)} 项")
            return config_list
            
        except Exception as e:
            logger.error(f"获取当前配置失败: {e}", exc_info=True)
            return []
    
    def apply_configuration(self) -> bool:
        """
        应用配置 - 基于旧版PLCConfigEmbeddedWidget的保存逻辑
        
        Returns:
            bool: 应用是否成功
        """
        try:
            # 获取当前配置
            current_config = self._get_current_module_config()
            if not current_config:
                QMessageBox.warning(self, "警告", "没有可应用的配置，请先添加模块。")
                return False
            
            # 更新应用按钮状态，显示保存中
            if hasattr(self, 'system_info') and self.system_info:
                self.system_info.apply_btn.setText("保存中...")
                self.system_info.apply_btn.setEnabled(False)
            
            # 转换为旧版格式进行验证和保存
            config_dict_for_validation = {}
            for (rack_id, slot_id), model_name in current_config.items():
                config_dict_for_validation[(rack_id, slot_id)] = model_name
            
            logger.info(f"准备应用PLC配置: {len(config_dict_for_validation)} 个模块")
            logger.debug(f"配置详情: {config_dict_for_validation}")
            
            # 调用IODataLoader的保存方法，它会进行完整的验证和保存
            success = self.io_data_loader.save_configuration(config_dict_for_validation)
            
            # 恢复按钮状态
            if hasattr(self, 'system_info') and self.system_info:
                self.system_info.apply_btn.setText("应用配置")
                self.system_info.apply_btn.setEnabled(True)
            
            if success:
                logger.info(f"成功应用PLC配置: {len(config_dict_for_validation)} 个模块")
                
                # 更新IO通道统计 - 修复方法调用
                rack_info = self.io_data_loader.get_rack_info()
                self.update_system_info(rack_info)
                
                # 强制更新机架显示 - 确保配置保存后机架显示正确更新
                self._update_rack_display()
                
                # 立即更新保存状态显示
                current_site = getattr(self.io_data_loader, 'current_site_name', '')
                if hasattr(self, 'system_info') and self.system_info:
                    self.system_info.update_save_status(True, current_site)
                
                # 发出配置应用成功信号
                self.configurationApplied.emit(True)
                
                # 获取系统信息用于显示
                system_type = rack_info.get('system_type', '未知')
                io_count = self._calculate_io_count()
                
                # 改进的成功消息
                success_msg = f"✅ PLC配置保存成功！\n\n" \
                             f"📊 配置详情：\n" \
                             f"• 场站名称：{current_site}\n" \
                             f"• 系统类型：{system_type}\n" \
                             f"• 配置模块：{len(config_dict_for_validation)} 个\n" \
                             f"• IO通道数：{io_count} 个\n" \
                             f"• 配置文件：已自动保存到磁盘\n\n" \
                             f"💾 配置已持久化保存，切换场站时会自动恢复。"
                
                QMessageBox.information(self, "🎉 配置保存成功", success_msg)
                return True
            else:
                logger.warning("应用PLC配置失败，请检查配置是否合法")
                
                # 发出配置应用失败信号
                self.configurationApplied.emit(False)
                
                # 改进的失败消息
                error_msg = f"❌ 配置保存失败\n\n" \
                           f"🔍 可能的原因：\n" \
                           f"• LE_CPU系统：槽位0必须配置LE5118 CPU\n" \
                           f"• LK系统：槽位1必须配置PROFIBUS-DP模块\n" \
                           f"• 模块类型与系统类型不匹配\n" \
                           f"• 槽位分配不正确\n\n" \
                           f"📝 请检查控制台日志获取详细错误信息。"
                
                QMessageBox.warning(self, "⚠️ 配置保存失败", error_msg)
                return False
                
        except Exception as e:
            # 恢复按钮状态
            if hasattr(self, 'system_info') and self.system_info:
                self.system_info.apply_btn.setText("应用配置")
                self.system_info.apply_btn.setEnabled(True)
            
            logger.error(f"应用配置时出错: {e}", exc_info=True)
            
            # 发出配置应用失败信号
            self.configurationApplied.emit(False)
            
            QMessageBox.critical(self, "💥 系统错误", f"应用配置时发生系统错误：\n\n{str(e)}\n\n请联系开发人员解决。")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            config = self._get_current_module_config()
            rack_info = self._rack_info
            
            # 修改：使用可用槽数而不是物理槽数
            available_slots_per_rack = rack_info.get('slots_per_rack', 11) - 1
            total_available_slots = rack_info.get('rack_count', 0) * available_slots_per_rack
            
            stats = {
                'system_type': rack_info.get('system_type', '未知'),
                'rack_count': rack_info.get('rack_count', 0),
                'total_slots': total_available_slots,
                'configured_modules': len(config),
                'available_modules': len(self._current_data_source),
                'io_channels': self._calculate_io_count()
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            return {'error': str(e)}
    
    def is_configuration_valid(self) -> bool:
        """
        检查配置是否有效
        
        Returns:
            配置是否有效
        """
        try:
            config = self._get_current_module_config()
            return len(config) > 0
            
        except Exception as e:
            logger.error(f"检查配置有效性失败: {e}", exc_info=True)
            return False

    def _on_reset_clicked(self):
        """处理重置按钮点击"""
        self.reset_configuration() 