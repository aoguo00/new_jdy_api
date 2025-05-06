"""模块管理对话框"""
import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QLineEdit, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox,
                           QComboBox, QGroupBox)
from PySide6.QtCore import Qt
from core.plc.hollysys.series import PLCSeriesManager

logger = logging.getLogger(__name__)

class ModuleManagerDialog(QDialog):
    """模块管理对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模块管理")
        self.resize(800, 800)  # 增加对话框高度以容纳系列管理部分
        
        self.series_manager = PLCSeriesManager()  # 用于管理所有系列
        self.current_series_manager = None  # 当前选中的系列管理器
        
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
            
    def create_delete_button(self, series_name):
        """创建删除按钮"""
        button = QPushButton("删除")
        button.clicked.connect(lambda: self.delete_series(series_name))
        return button

    def load_series_table(self):
        """加载系列表格"""
        series_list = self.series_manager.get_all_series()
        
        self.series_table.setRowCount(0)
        for series in series_list:
            row = self.series_table.rowCount()
            self.series_table.insertRow(row)
            self.series_table.setItem(row, 0, QTableWidgetItem(series['name']))
            self.series_table.setItem(row, 1, QTableWidgetItem(series['description']))
            
            # 使用专门的方法创建删除按钮
            delete_button = self.create_delete_button(series['name'])
            self.series_table.setCellWidget(row, 2, delete_button)
            
    def load_series_combo(self):
        """加载系列下拉框"""
        series_list = self.series_manager.get_all_series()
        
        current_text = self.series_combo.currentText()
        self.series_combo.clear()
        
        for series in series_list:
            self.series_combo.addItem(series['name'], series)
            
        # 尝试恢复之前选择的系列
        index = self.series_combo.findText(current_text)
        if index >= 0:
            self.series_combo.setCurrentIndex(index)
        elif self.series_combo.count() > 0:
            self.series_combo.setCurrentIndex(0)
            self.on_series_changed(self.series_combo.currentText())
            
    def add_series(self):
        """添加新系列"""
        name = self.series_name_input.text().strip()
        description = self.series_desc_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "警告", "请输入系列名称")
            return
            
        try:
            if self.series_manager.add_series(name, description):
                # 清空输入
                self.series_name_input.clear()
                self.series_desc_input.clear()
                
                # 刷新系列列表
                self.load_series_table()
                self.load_series_combo()
            else:
                QMessageBox.warning(self, "错误", "添加系列失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加系列失败: {str(e)}")
            
    def delete_series(self, series_name):
        """删除系列"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除系列 {series_name} 吗？这将同时删除该系列下的所有模块！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.series_manager.delete_series(series_name):
                    # 刷新系列列表
                    self.load_series_table()
                    self.load_series_combo()
                else:
                    QMessageBox.warning(self, "错误", "删除系列失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除系列失败: {str(e)}")
            
    def on_series_changed(self, series_name):
        """处理系列选择变更"""
        if not series_name:
            return
        self.current_series_manager = PLCSeriesManager(series_name)
        self.load_modules()
        
    def load_modules(self):
        """加载模块列表"""
        if not self.current_series_manager:
            return
            
        self.module_table.setRowCount(0)
        
        # 获取所有类型的模块
        for module_type in ['AI', 'AO', 'DI', 'DO']:
            modules = self.current_series_manager.get_modules_by_type(module_type)
            for module in modules:
                self.add_module_to_table(module)
            
    def add_module_to_table(self, module):
        """添加模块到表格"""
        row = self.module_table.rowCount()
        self.module_table.insertRow(row)
        
        # 添加模块信息
        self.module_table.setItem(row, 0, QTableWidgetItem(module['model']))
        self.module_table.setItem(row, 1, QTableWidgetItem(module['module_type']))
        self.module_table.setItem(row, 2, QTableWidgetItem(str(module['channels'])))
        self.module_table.setItem(row, 3, QTableWidgetItem(module['description']))
        
        # 添加删除按钮
        delete_button = QPushButton("删除")
        delete_button.clicked.connect(lambda: self.delete_module(module['model']))
        self.module_table.setCellWidget(row, 4, delete_button)
        
    def add_module(self):
        """添加新模块"""
        if not self.current_series_manager:
            return
            
        model = self.model_input.text().strip()
        module_type = self.type_combo.currentText()
        channels = self.channels_input.text().strip()
        description = self.desc_input.text().strip()
        
        # 验证输入
        if not all([model, channels]):
            QMessageBox.warning(self, "警告", "请填写完整的模块信息")
            return
            
        try:
            channels = int(channels)
            if channels <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "警告", "通道数必须为正整数")
            return
            
        # 添加到数据库
        try:
            if self.current_series_manager.add_module(model, module_type, channels, description):
                # 刷新列表
                self.load_modules()
                
                # 清空输入
                self.model_input.clear()
                self.channels_input.clear()
                self.desc_input.clear()
            else:
                QMessageBox.warning(self, "错误", "添加模块失败")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加模块失败: {str(e)}")
            
    def delete_module(self, model):
        """删除模块"""
        if not self.current_series_manager:
            return
            
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模块 {model} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.current_series_manager.delete_module(model):
                    self.load_modules()
                else:
                    QMessageBox.warning(self, "错误", "删除模块失败")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模块失败: {str(e)}")