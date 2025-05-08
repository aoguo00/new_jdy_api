"""模块管理对话框"""
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox,
                           QComboBox, QGroupBox, QInputDialog, QTreeWidgetItem)
from PySide6.QtCore import Qt
from core.query_area import PLCHardwareService, PLCSeriesModel, PLCModuleModel
from typing import List, Optional

logger = logging.getLogger(__name__)

class ModuleManagerDialog(QDialog):
    """模块管理对话框"""
    def __init__(self, plc_hardware_service: PLCHardwareService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模块管理")
        self.resize(900, 600)
        
        self.plc_service = plc_hardware_service
        if not self.plc_service:
            logger.error("ModuleManagerDialog 初始化失败: PLCHardwareService 未提供。")
            QMessageBox.critical(self, "严重错误", "PLC硬件服务未能加载，对话框无法使用。")
            return

        self.current_series_id: Optional[int] = None
        self._is_editing_new_module = False

        self.setup_ui()
        self.setup_connections()
        self.init_series()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 系列管理区域
        series_group = QGroupBox("PLC系列管理")
        series_layout = QVBoxLayout()
        
        # 系列添加区域
        add_series_layout = QHBoxLayout()
        add_series_layout.addWidget(QLabel("系列名称:"))
        self.series_name_input = QLineEdit()
        self.series_name_input.setFixedWidth(100)
        add_series_layout.addWidget(self.series_name_input)
        
        add_series_layout.addWidget(QLabel("描述:"))
        self.series_desc_input = QLineEdit()
        add_series_layout.addWidget(self.series_desc_input)
        
        self.add_series_button = QPushButton("添加系列")
        self.add_series_button.setFixedWidth(80)
        add_series_layout.addWidget(self.add_series_button)
        series_layout.addLayout(add_series_layout)
        
        # 系列列表
        self.series_table = QTableWidget()
        self.series_table.setColumnCount(3)
        self.series_table.setHorizontalHeaderLabels(['系列名称', '描述', '操作'])
        
        # 设置系列表格列宽
        header = self.series_table.horizontalHeader()
        self.series_table.setColumnWidth(0, 100)  # 系列名称列
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # 描述列
        self.series_table.setColumnWidth(2, 80)   # 操作列
        
        series_layout.addWidget(self.series_table)
        series_group.setLayout(series_layout)
        layout.addWidget(series_group)
        
        # 原有的模块管理区域
        module_group = QGroupBox("模块管理")
        module_layout = QVBoxLayout()
        
        # PLC系列选择区域
        series_layout = QHBoxLayout()
        series_layout.addWidget(QLabel("PLC系列:"))
        self.series_combo = QComboBox()
        self.series_combo.setFixedWidth(100)
        series_layout.addWidget(self.series_combo)
        series_layout.addStretch()
        module_layout.addLayout(series_layout)
        
        # 添加模块区域
        add_group_layout = QHBoxLayout()
        
        # 型号输入
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("型号:"))
        self.model_input = QLineEdit()
        self.model_input.setFixedWidth(100)
        model_layout.addWidget(self.model_input)
        add_group_layout.addLayout(model_layout)
        
        # 类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['AI', 'AO', 'DI', 'DO'])
        self.type_combo.setFixedWidth(80)
        type_layout.addWidget(self.type_combo)
        add_group_layout.addLayout(type_layout)
        
        # 通道数输入
        channels_layout = QHBoxLayout()
        channels_layout.addWidget(QLabel("通道数:"))
        self.channels_input = QLineEdit()
        self.channels_input.setFixedWidth(60)
        channels_layout.addWidget(self.channels_input)
        add_group_layout.addLayout(channels_layout)
        
        # 描述输入
        desc_layout = QHBoxLayout()
        desc_layout.addWidget(QLabel("描述:"))
        self.desc_input = QLineEdit()
        desc_layout.addWidget(self.desc_input)
        add_group_layout.addLayout(desc_layout)
        
        # 添加按钮
        self.add_button = QPushButton("添加")
        self.add_button.setFixedWidth(60)
        add_group_layout.addWidget(self.add_button)
        
        module_layout.addLayout(add_group_layout)
        
        # 模块列表
        self.module_table = QTableWidget()
        self.module_table.setColumnCount(5)
        self.module_table.setHorizontalHeaderLabels(['型号', '类型', '通道数', '描述', '操作'])
        
        # 设置列宽
        header = self.module_table.horizontalHeader()
        self.module_table.setColumnWidth(0, 100)  # 型号列
        self.module_table.setColumnWidth(1, 80)   # 类型列
        self.module_table.setColumnWidth(2, 80)   # 通道数列
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # 描述列
        self.module_table.setColumnWidth(4, 80)   # 操作列
        
        module_layout.addWidget(self.module_table)
        module_group.setLayout(module_layout)
        layout.addWidget(module_group)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.ok_button.setFixedWidth(80)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def setup_connections(self):
        """设置信号连接"""
        self.add_series_button.clicked.connect(self.add_series)
        self.series_combo.currentTextChanged.connect(self.on_series_changed)
        self.add_button.clicked.connect(self.add_module)
        self.ok_button.clicked.connect(self.accept)
        
    def init_series(self):
        """初始化PLC系列"""
        self.load_series_table()  # 加载系列表格
        self.load_series_combo()  # 加载系列下拉框
            
    def create_delete_button(self, series_id: int):
        """创建删除按钮，现在接收 series_id"""
        button = QPushButton("删除")
        # Pass series_id to the delete_series method
        button.clicked.connect(lambda: self.delete_series(series_id))
        return button

    def load_series_table(self):
        """加载系列表格"""
        series_list: List[PLCSeriesModel] = self.plc_service.get_all_series()
        
        self.series_table.setRowCount(0)
        for series in series_list:
            row = self.series_table.rowCount()
            self.series_table.insertRow(row)
            self.series_table.setItem(row, 0, QTableWidgetItem(series.name))
            self.series_table.setItem(row, 1, QTableWidgetItem(series.description or ""))
            
            # 使用系列ID创建删除按钮
            if series.id is not None: # Ensure series.id is not None before using
                delete_button = self.create_delete_button(series.id)
                self.series_table.setCellWidget(row, 2, delete_button)
            else:
                logger.warning(f"Series '{series.name}' has no ID, cannot create delete button.")
            
    def load_series_combo(self):
        """加载系列下拉框"""
        if not self.plc_service: return
        try:
            series_list: List[PLCSeriesModel] = self.plc_service.get_all_series()
        except Exception as e:
            logger.error(f"加载系列下拉框失败: {e}", exc_info=True)
            # Optionally show message to user
            series_list = []
        
        current_selection_id = None
        if self.series_combo.count() > 0:
            current_selection_id = self.series_combo.currentData() # Get ID of currently selected item

        self.series_combo.clear()
        
        idx_to_select = -1
        for i, series in enumerate(series_list):
            self.series_combo.addItem(series.name, userData=series.id) # Store series.id
            if series.id == current_selection_id:
                idx_to_select = i
            
        if idx_to_select != -1:
            self.series_combo.setCurrentIndex(idx_to_select)
        elif self.series_combo.count() > 0:
            self.series_combo.setCurrentIndex(0)
            # No explicit call to on_series_changed if setCurrentIndex(0) is the first time or series changes
            # The currentTextChanged signal should handle it if the text actually changes.
            # If it's the first population or combo is empty then repopulated, 
            # ensure on_series_changed is triggered if an item is selected.
            # However, init_series already calls load_series_combo and then on_series_changed might be called by signal.

    def add_series(self):
        """添加新系列 (读取界面输入框)"""
        if not self.plc_service: return
        name = self.series_name_input.text().strip() # Removed .upper() unless intended
        description = self.series_desc_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "系列名称不能为空")
            return
            
        try:
            # 调用服务层添加，传入描述
            created_series = self.plc_service.add_series(name, description) 
            if created_series:
                self.series_name_input.clear() # Clear inputs on success
                self.series_desc_input.clear()
                QMessageBox.information(self, "成功", f"系列 '{name}' 添加成功。")
                # Reload both table and combo box
                self.load_series_table() 
                self.load_series_combo()
            else:
                # This case might be reached if service returns None on non-exception failure
                QMessageBox.warning(self, "失败", f"系列 '{name}' 添加失败，请检查日志。")
        except ValueError as ve: # Handles name already exists from service
            QMessageBox.warning(self, "失败", str(ve))
        except Exception as e:
            logger.error(f"添加系列 '{name}' 失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"添加系列时发生未知错误: {str(e)}")
            
    def delete_series(self, series_id: int):
        """删除系列，现在接收 series_id"""
        if not self.plc_service: return
        
        series_to_delete = next((s for s in self.plc_service.get_all_series() if s.id == series_id), None)
        series_name_for_msg = series_to_delete.name if series_to_delete else f"ID {series_id}"

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除系列 '{series_name_for_msg}' 吗？\n此操作将同时删除该系列下的所有模块！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.plc_service.delete_series(series_id):
                self.load_series_table()
                self.load_series_combo()
                QMessageBox.information(self, "成功", f"系列 '{series_name_for_msg}' 已删除。")
            else:
                QMessageBox.warning(self, "错误", f"删除系列 '{series_name_for_msg}' 失败。")
                
    def on_series_changed(self, series_name: str): # series_name is the displayed text
        """处理系列选择变更（用于模块部分的下拉框）"""
        current_index = self.series_combo.currentIndex()
        if current_index < 0: # No item selected
            self.current_series_id = None
            self.module_table.setRowCount(0) # Clear module table
            logger.info("系列下拉框未选择任何项目或为空。")
            return

        selected_series_id = self.series_combo.itemData(current_index)
        
        if selected_series_id is None:
            # This case should ideally not happen if items are added correctly with userData
            QMessageBox.warning(self, "错误", f"系列 '{series_name}' 数据无效。")
            self.current_series_id = None
            self.module_table.setRowCount(0)
            return
            
        self.current_series_id = selected_series_id
        logger.info(f"模块管理的PLC系列已更改为: {series_name} (ID: {self.current_series_id})")
        self.load_modules() # Load modules for the newly selected series
        
    def load_modules(self):
        """加载模块列表 (特定于当前选择的系列)"""
        self.module_table.setRowCount(0) # Clear existing module rows
        if not self.plc_service: return
        
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            # logger.warning("load_modules - current_series_id 未设置，无法加载模块。") # Normal if no series selected
            return

        try:
            # Corrected method name: get_modules_by_series_id
            modules: List[PLCModuleModel] = self.plc_service.get_modules_by_series_id(self.current_series_id)
        except Exception as e:
            logger.error(f"加载系列 {self.current_series_id} 的模块失败: {e}", exc_info=True)
            QMessageBox.warning(self, "错误", f"加载模块列表失败: {str(e)}")
            modules = [] # Ensure list is empty on error
        
        for module in modules:
            row = self.module_table.rowCount()
            self.module_table.insertRow(row)
            self.module_table.setItem(row, 0, QTableWidgetItem(module.model))
            self.module_table.setItem(row, 1, QTableWidgetItem(module.module_type))
            self.module_table.setItem(row, 2, QTableWidgetItem(str(module.channels)))
            self.module_table.setItem(row, 3, QTableWidgetItem(module.description or ""))
            
            # Add delete button for each module
            delete_module_button = QPushButton("删除")
            # Pass module.model (or module.id if available and preferred for deletion)
            delete_module_button.clicked.connect(lambda checked=False, m_model=module.model: self.delete_module(m_model))
            self.module_table.setCellWidget(row, 4, delete_module_button)
            
    def add_module(self):
        """添加新模块到当前选定的系列"""
        if not self.plc_service: return
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            QMessageBox.warning(self, "错误", "请先选择一个PLC系列。")
            return

        model = self.model_input.text().strip() # Removed .upper()
        module_type = self.type_combo.currentText()
        channels_text = self.channels_input.text().strip()
        description = self.desc_input.text().strip()
        
        if not model:
            QMessageBox.warning(self, "错误", "模块型号不能为空。")
            return
            
        try:
            channels = int(channels_text) if channels_text else 0
        except ValueError:
            QMessageBox.warning(self, "错误", "通道数必须是有效的数字。")
            return
            
        try:
            # Call the service to add the module
            new_module = self.plc_service.add_module(
                series_id=self.current_series_id,
                model=model,
                module_type=module_type,
                channels=channels,
                description=description
            )
            if new_module:
                # Clear input fields
                self.model_input.clear()
                # self.type_combo.setCurrentIndex(0) # Optionally reset type
                self.channels_input.clear()
                self.desc_input.clear()
                # Reload the module table for the current series
                self.load_modules() 
                QMessageBox.information(self, "成功", f"模块 '{model}' 添加成功。")
            else:
                # This might be reached if service returns None for non-exception failure
                QMessageBox.warning(self, "错误", f"添加模块 '{model}' 失败。可能是型号已存在或其他错误。")
        except ValueError as ve:
             QMessageBox.warning(self, "错误", str(ve)) # Catch specific errors like duplicate model if service raises it
        except Exception as e:
            logger.error(f"添加模块 '{model}' 到系列 {self.current_series_id} 失败: {e}", exc_info=True)
            QMessageBox.critical(self, "严重错误", f"添加模块时发生意外错误: {e}")

    def delete_module(self, module_model: str):
        """删除指定型号的模块 (从当前选定的系列中)"""
        if not self.plc_service: return
        if not hasattr(self, 'current_series_id') or self.current_series_id is None:
            QMessageBox.warning(self, "错误", "系列未选定，无法删除模块。")
            return
            
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要从当前系列中删除模块 '{module_model}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Use delete_module from service which requires series_id and model string
            if self.plc_service.delete_module(self.current_series_id, module_model):
                self.load_modules() # Reload module table
                QMessageBox.information(self, "成功", f"模块 '{module_model}' 已删除。")
            else:
                QMessageBox.warning(self, "错误", f"删除模块 '{module_model}' 失败。")

    def accept(self):
        # ... existing code ...
        pass # Add pass to satisfy linter
        super().accept() # Call parent's accept method

# Example usage (for testing)