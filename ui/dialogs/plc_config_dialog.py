"""PLC配置对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt
from core.query_area import PLCHardwareService, PLCSeriesModel, PLCModuleModel 
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PLCConfigDialog(QDialog):
    """PLC配置对话框"""
    def __init__(self, plc_hardware_service: PLCHardwareService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC配置")
        self.resize(1200, 700)  # 增加对话框宽度
        
        self.plc_service = plc_hardware_service # 使用注入的服务
        if not self.plc_service:
            logger.error("PLCConfigDialog 初始化失败: PLCHardwareService 未提供。")
            # 适当处理错误，例如显示消息并禁用对话框，或引发异常
            QMessageBox.critical(self, "严重错误", "PLC硬件服务未能加载，对话框无法使用。")
            # self.accept() # 或 self.reject() 或禁用 UI
            # 暂时让它继续，但函数可能会失败
            # 更好的方法是在 MainWindow 中防止显示对话框（如果 service 为 None）

        self.rack_slots = ['' for _ in range(11)]  # LK117有11个槽位
        self.setup_ui()
        self.setup_connections()
        self.init_series()  # 初始化系列选择

    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)  # 设置布局间距
        
        # PLC系列选择区域
        series_layout = QHBoxLayout()
        series_layout.addWidget(QLabel("PLC系列:"))
        self.series_combo = QComboBox()
        self.series_combo.setFixedWidth(100)
        series_layout.addWidget(self.series_combo)
        series_layout.addStretch()
        layout.addLayout(series_layout)
        
        # 机架选择区域
        rack_layout = QHBoxLayout()
        rack_layout.addWidget(QLabel("机架型号:"))
        self.rack_combo = QComboBox()
        self.rack_combo.addItem("LK117", "LK117")  # 目前只支持LK117
        self.rack_combo.setFixedWidth(150)  # 设置下拉框宽度
        rack_layout.addWidget(self.rack_combo)
        rack_layout.addStretch()
        layout.addLayout(rack_layout)
        
        # 模块配置区域
        module_layout = QHBoxLayout()
        module_layout.setSpacing(20)  # 设置左右两边表格的间距
        
        # 左侧：模块选择
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("可用模块:"))
        
        # 模块类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['全部', 'AI', 'AO', 'DI', 'DO', 'DP'])
        self.type_combo.setFixedWidth(100)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        left_layout.addLayout(type_layout)
        
        # 左侧模块列表
        self.module_table = QTableWidget()
        self.module_table.setColumnCount(5)
        self.module_table.setHorizontalHeaderLabels(['序号', '型号', '类型', '通道数', '描述'])
        self.module_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.module_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.module_table.verticalHeader().setVisible(False)
        
        # 设置左侧表格列宽 - 加入序号列
        header_left = self.module_table.horizontalHeader()
        header_left.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 序号
        header_left.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 型号
        header_left.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 类型
        header_left.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 通道数
        header_left.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)      # 描述
        # header_left.setMinimumSectionSize(50) # 如果需要，调整最小尺寸
        
        # 设置表格样式
        self.module_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
                background-color: white;
                alternate-background-color: #f6f6f6;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
        self.module_table.setAlternatingRowColors(True)  # 启用隔行变色
        
        left_layout.addWidget(self.module_table)
        module_layout.addLayout(left_layout)
        
        # 中间：操作按钮
        mid_layout = QVBoxLayout()
        self.add_button = QPushButton("添加 →")
        self.remove_button = QPushButton("← 移除")
        self.add_button.setFixedWidth(100)
        self.remove_button.setFixedWidth(100)
        mid_layout.addStretch()
        mid_layout.addWidget(self.add_button)
        mid_layout.addWidget(self.remove_button)
        mid_layout.addStretch()
        module_layout.addLayout(mid_layout)
        
        # 右侧：已配置模块
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("已配置模块:"))
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setHorizontalHeaderLabels(['槽位', '型号', '类型', '通道数', '描述'])
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.config_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.config_table.verticalHeader().setVisible(False)
        
        # 设置右侧表格列宽 - 型号自适应，描述拉伸
        header_right = self.config_table.horizontalHeader()
        header_right.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 槽位
        header_right.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 型号 - 改为自适应内容
        header_right.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 类型
        header_right.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 通道数
        header_right.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)      # 描述 - 改回拉伸
        # header_right.setMinimumSectionSize(60) # 可以移除或调整
        
        # 设置相同的表格样式
        self.config_table.setStyleSheet(self.module_table.styleSheet())
        self.config_table.setAlternatingRowColors(True)
        
        right_layout.addWidget(self.config_table)
        module_layout.addLayout(right_layout)
        
        # 设置左右两侧布局的比例
        module_layout.setStretch(0, 1)  # 左侧表格
        module_layout.setStretch(2, 1)  # 右侧表格
        
        layout.addLayout(module_layout)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.ok_button.setFixedWidth(80)
        self.cancel_button.setFixedWidth(80)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.series_combo.currentTextChanged.connect(self.on_series_changed)
        self.type_combo.currentTextChanged.connect(self.load_modules)
        self.add_button.clicked.connect(self.add_module)
        self.remove_button.clicked.connect(self.remove_module)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def init_series(self):
        """初始化PLC系列"""
        self.series_combo.clear() # 清除之前的项目
        if not self.plc_service: return # 防止服务缺失
        
        try:
            series_list: List[PLCSeriesModel] = self.plc_service.get_all_series()
        except Exception as e:
            logger.error(f"初始化PLC系列失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载PLC系列列表失败: {str(e)}")
            series_list = [] # 确保出错时series_list为空列表
            
        for series in series_list:
            self.series_combo.addItem(series.name, userData=series.id) 
            
        if self.series_combo.count() > 0:
            self.series_combo.setCurrentIndex(0)
        else:
            # 处理没有加载系列的情况（例如，显示消息，禁用UI部分）
            logger.info("没有可用的PLC系列数据。")
            # self.on_series_changed(None) # 或直接清除表格
            self.module_table.setRowCount(0)
            self.config_table.setRowCount(0)
            self.current_series_id = None

    def on_series_changed(self, series_name: str): # series_name是显示的文本
        """处理系列选择变更"""
        current_index = self.series_combo.currentIndex()
        if current_index < 0:
            self.module_table.setRowCount(0)
            self.config_table.setRowCount(0)
            self.current_series_id = None
            return

        self.current_series_id = self.series_combo.itemData(current_index)
        
        if self.current_series_id is None:
            # 如果userData未设置，或series_name为None/空且combo为空，可能会发生这种情况
            logger.warning(f"无法获取系列 '{series_name}' 的ID (当前索引: {current_index})。")
            self.module_table.setRowCount(0)
            self.config_table.setRowCount(0) 
            return
        
        # 检测是否是LK系列
        self.is_lk_series = series_name.startswith('LK')
        logger.info(f"PLC系列已更改为: {series_name} (ID: {self.current_series_id}, LK系列: {self.is_lk_series})")
        
        self.load_modules()
        
        # 重置机架槽位配置
        self.rack_slots = ['' for _ in range(11)]  # 默认11个槽位
        
        # 对于LK系列，自动在第一个槽位添加DP模块
        if self.is_lk_series:
            # 查找DP通信模块添加到第一槽
            self.add_dp_module_to_first_slot()
            
        self.update_config_table()

    def load_modules(self):
        """加载模块列表"""
        self.module_table.setRowCount(0)
        if not self.plc_service: return # 防止服务缺失
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            # logger.warning("load_modules 调用时 current_series_id 未设置或为 None") # 如果没有选择系列，这可能是正常的
            return
            
        module_type_filter = self.type_combo.currentText()
        modules: List[PLCModuleModel] = []
        
        try:
            if module_type_filter == '全部':
                # 假设PLCHardwareService存在get_modules_by_series_id方法
                modules = self.plc_service.get_modules_by_series_id(self.current_series_id) 
            else:
                # 假设存在get_modules_by_series_and_type方法
                modules = self.plc_service.get_modules_by_series_and_type(self.current_series_id, module_type_filter)
        except Exception as e:
            logger.error(f"加载模块列表失败 (系列ID: {self.current_series_id}, 类型: {module_type_filter}): {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载模块列表失败: {str(e)}")
            modules = [] # 确保出错时modules为空列表
            
        for row, module in enumerate(modules):
            self.module_table.insertRow(row)
            # 设置带有更新索引的项目
            self.module_table.setItem(row, 0, QTableWidgetItem(str(row + 1)))       # 索引0: 序号
            self.module_table.setItem(row, 1, QTableWidgetItem(module.model))         # 索引1: 型号
            self.module_table.setItem(row, 2, QTableWidgetItem(module.module_type))   # 索引2: 类型
            self.module_table.setItem(row, 3, QTableWidgetItem(str(module.channels))) # 索引3: 通道数
            self.module_table.setItem(row, 4, QTableWidgetItem(module.description or "")) # 索引4: 描述

    def add_module(self):
        """添加模块到配置"""
        current_row = self.module_table.currentRow()
        if current_row < 0:
            return
            
        # 获取模块信息
        module_model = self.module_table.item(current_row, 1).text()
        module_type = self.module_table.item(current_row, 2).text()
        module_channels = self.module_table.item(current_row, 3).text()
        module_desc = self.module_table.item(current_row, 4).text()
        
        # 获取可用槽位
        # 对于LK系列，第一个槽位预留给DP模块，所以从第二个槽位开始分配
        if hasattr(self, 'is_lk_series') and self.is_lk_series:
            available_slots = []
            # 检查槽位1是否已有DP模块
            has_dp_in_slot1 = bool(self.rack_slots[0])
            
            # 遍历所有槽位（从1开始，索引从0开始）
            for i, slot_content in enumerate(self.rack_slots):
                if i == 0 and not has_dp_in_slot1:
                    # 如果槽位1没有DP模块且当前要添加的是DP类型模块，则槽位1可用
                    if module_type == 'DP':
                        available_slots.append(i + 1)  # 槽位号 = 索引 + 1
                elif i > 0 and not slot_content:  # 非第一槽位且为空
                    available_slots.append(i + 1)  # 槽位号 = 索引 + 1
        else:
            # 非LK系列，所有空槽位均可用
            available_slots = [i + 1 for i, slot in enumerate(self.rack_slots) if not slot]
            
        if not available_slots:
            QMessageBox.warning(self, "警告", "所有槽位已被占用")
            return
        
        # 分配到第一个可用槽位
        slot = available_slots[0]
        self.rack_slots[slot - 1] = module_model
        
        # 如果是添加DP模块到LK系列的第一个槽位，提示用户
        if hasattr(self, 'is_lk_series') and self.is_lk_series and slot == 1 and module_type == 'DP':
            logger.info(f"已在第一槽位添加DP通信模块: {module_model}")
            
        self.update_config_table()

    def remove_module(self):
        """从配置中移除模块"""
        current_row = self.config_table.currentRow()
        if current_row < 0:
            return
            
        # 获取槽位信息
        slot = int(self.config_table.item(current_row, 0).text())
        module_type = self.config_table.item(current_row, 2).text()
        
        # 如果是LK系列的第一个槽位且模块类型为DP，提示用户确认
        if hasattr(self, 'is_lk_series') and self.is_lk_series and slot == 1 and module_type == 'DP':
            reply = QMessageBox.question(
                self, 
                "确认移除",
                "移除LK系列第一槽位的DP通信模块可能导致配置无效。确定要移除吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return  # 用户取消移除
                
        self.rack_slots[slot - 1] = ''  # 清空槽位
        self.update_config_table()
        
        # 如果移除后是LK系列且第一槽位为空，提示用户添加DP模块
        if hasattr(self, 'is_lk_series') and self.is_lk_series and slot == 1:
            QMessageBox.information(
                self, 
                "提示", 
                "已移除LK系列第一槽位的模块。建议在第一槽位添加一个DP通信模块。"
            )

    def update_config_table(self):
        """更新配置表格"""
        self.config_table.setRowCount(0)
        
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            logger.warning("update_config_table 调用时 current_series_id 未设置或为 None, 无法获取模块详情。")
            # 如果这种状态是有问题的，可能需要清除self.rack_slots或显示错误
            return

        for slot, module_model_str in enumerate(self.rack_slots, 1):
            if module_model_str:  # 如果槽位有模块型号字符串
                # 从新的PLCManager获取模块信息，需要 series_id 和 model string
                module_details: Optional[PLCModuleModel] = self.plc_service.get_module_info(self.current_series_id, module_model_str)
                
                if module_details:
                    row = self.config_table.rowCount()
                    self.config_table.insertRow(row)
                    self.config_table.setItem(row, 0, QTableWidgetItem(str(slot)))
                    self.config_table.setItem(row, 1, QTableWidgetItem(module_details.model))
                    self.config_table.setItem(row, 2, QTableWidgetItem(module_details.module_type))
                    self.config_table.setItem(row, 3, QTableWidgetItem(str(module_details.channels)))
                    self.config_table.setItem(row, 4, QTableWidgetItem(module_details.description or ""))
                else:
                    # 如果找不到模块详细信息 (例如，数据不一致或模块已从数据库删除但仍存在于rack_slots中)
                    logger.warning(f"无法在系列ID {self.current_series_id} 中找到型号为 '{module_model_str}' 的模块详情。将在配置表中显示为未知模块。")
                    row = self.config_table.rowCount()
                    self.config_table.insertRow(row)
                    self.config_table.setItem(row, 0, QTableWidgetItem(str(slot)))
                    self.config_table.setItem(row, 1, QTableWidgetItem(f"{module_model_str} (未知)"))
                    self.config_table.setItem(row, 2, QTableWidgetItem("N/A"))
                    self.config_table.setItem(row, 3, QTableWidgetItem("N/A"))
                    self.config_table.setItem(row, 4, QTableWidgetItem("模块信息在数据库中未找到"))
        
    def get_selected_configuration(self) -> List[Dict[str, Any]]:
        # 添加实现代码
        pass # 添加pass以满足linter对空方法体的要求

    def accept(self):
        # 添加实现代码
        pass # 添加pass以满足linter对空方法体的要求
        super().accept() # 假设这是原始意图或应该在这里

    def reject(self):
        # 添加实现代码
        pass # 添加pass以满足linter对空方法体的要求
        super().reject() # 假设这是原始意图或应该在这里

    def add_dp_module_to_first_slot(self):
        """为LK系列在第一个槽位添加DP通信模块"""
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            logger.warning("add_dp_module_to_first_slot 调用时 current_series_id 未设置或为 None，无法添加DP模块。")
            return
            
        try:
            # 获取当前系列的所有DP类型模块
            dp_modules = self.plc_service.get_modules_by_series_and_type(self.current_series_id, 'DP')
            
            if not dp_modules:
                logger.warning(f"系列ID {self.current_series_id} 没有找到DP类型的模块，无法自动添加到第一槽位。")
                return
                
            # 选择第一个DP模块添加到第一个槽位
            dp_module = dp_modules[0]
            self.rack_slots[0] = dp_module.model  # 第一个槽位(索引0)设置为DP模块
            logger.info(f"已自动在第一槽位添加DP通信模块: {dp_module.model}")
            
        except Exception as e:
            logger.error(f"添加DP模块到第一槽位失败: {e}", exc_info=True)
            # 无需弹窗，因为这是自动操作，失败不应阻断用户继续配置

# 示例用法（用于测试，可以保留或删除）