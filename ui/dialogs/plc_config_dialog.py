"""PLC配置对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
from core.plc.hollysys.lk_db import PLCModuleManager  # 修改为使用PLCModuleManager

class PLCConfigDialog(QDialog):
    """PLC配置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC配置")
        self.resize(1200, 700)  # 增加对话框宽度
        
        self.module_manager = None  # 初始化为None
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
        self.module_table.setColumnCount(4)
        self.module_table.setHorizontalHeaderLabels(['型号', '类型', '通道数', '描述'])
        
        # 设置左侧表格列宽
        header = self.module_table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)  # 最后一列自适应
        
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
        
        # 设置右侧表格列宽
        header = self.config_table.horizontalHeader()
        # 设置前四列固定宽度，最后一列自动拉伸
        self.config_table.setColumnWidth(0, 60)   # 槽位列
        self.config_table.setColumnWidth(1, 120)  # 型号列
        self.config_table.setColumnWidth(2, 80)   # 类型列
        self.config_table.setColumnWidth(3, 80)   # 通道数列
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # 槽位列固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # 型号列固定宽度
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # 类型列固定宽度
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # 通道数列固定宽度
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # 描述列自动拉伸填充剩余空间
        
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
        temp_manager = PLCModuleManager()  # 临时创建一个管理器来获取系列列表
        series_list = temp_manager.get_all_series()
        
        for series in series_list:
            self.series_combo.addItem(series['name'], series['description'])
            
        # 默认选择第一个系列
        if self.series_combo.count() > 0:
            self.on_series_changed(self.series_combo.currentText())
            
    def on_series_changed(self, series_name):
        """处理系列选择变更"""
        self.module_manager = PLCModuleManager(series_name)
        self.load_modules()

    def load_modules(self):
        """加载模块列表"""
        self.module_table.setRowCount(0)
        module_type = self.type_combo.currentText()
        
        if module_type == '全部':
            # 获取所有类型的模块
            modules = []
            for type_ in ['AI', 'AO', 'DI', 'DO']:
                modules.extend(self.module_manager.get_modules_by_type(type_))
        else:
            # 获取指定类型的模块
            modules = self.module_manager.get_modules_by_type(module_type)
            
        for module in modules:
            row = self.module_table.rowCount()
            self.module_table.insertRow(row)
            self.module_table.setItem(row, 0, QTableWidgetItem(module['model']))
            self.module_table.setItem(row, 1, QTableWidgetItem(module['module_type']))
            self.module_table.setItem(row, 2, QTableWidgetItem(str(module['channels'])))
            self.module_table.setItem(row, 3, QTableWidgetItem(module['description']))

    def add_module(self):
        """添加模块到配置"""
        current_row = self.module_table.currentRow()
        if current_row < 0:
            return
            
        # 获取可用槽位
        available_slots = [i + 1 for i, slot in enumerate(self.rack_slots) if not slot]
        if not available_slots:
            QMessageBox.warning(self, "警告", "所有槽位已被占用")
            return
            
        # 获取模块信息
        module_model = self.module_table.item(current_row, 0).text()
        module_type = self.module_table.item(current_row, 1).text()
        module_channels = self.module_table.item(current_row, 2).text()
        module_desc = self.module_table.item(current_row, 3).text()
        
        # 分配到第一个可用槽位
        slot = available_slots[0]
        self.rack_slots[slot - 1] = module_model
        self.update_config_table()

    def remove_module(self):
        """从配置中移除模块"""
        current_row = self.config_table.currentRow()
        if current_row < 0:
            return
            
        # 获取槽位信息
        slot = int(self.config_table.item(current_row, 0).text())
        self.rack_slots[slot - 1] = ''  # 清空槽位
        self.update_config_table()

    def update_config_table(self):
        """更新配置表格"""
        self.config_table.setRowCount(0)
        
        for slot, model in enumerate(self.rack_slots, 1):
            if model:  # 如果槽位有模块
                # 从数据库获取模块信息
                module_info = self.module_manager.get_module_info(model)
                
                if module_info:
                    row = self.config_table.rowCount()
                    self.config_table.insertRow(row)
                    self.config_table.setItem(row, 0, QTableWidgetItem(str(slot)))
                    self.config_table.setItem(row, 1, QTableWidgetItem(module_info['model']))
                    self.config_table.setItem(row, 2, QTableWidgetItem(module_info['module_type']))
                    self.config_table.setItem(row, 3, QTableWidgetItem(str(module_info['channels'])))
                    self.config_table.setItem(row, 4, QTableWidgetItem(module_info['description']))