"""查询区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMenu, QMessageBox)
from PySide6.QtCore import Signal
import os # Add os import for basename
from typing import Optional

class QueryArea(QGroupBox):
    """查询条件区域"""
    # 定义信号
    query_requested = Signal(str)  # 项目编号 (移除了场站编号)
    clear_requested = Signal()
    # upload_hmi_requested = Signal(str)  # HMI类型  -- REMOVED
    # upload_plc_requested = Signal(str)  # PLC类型  -- REMOVED
    # upload_io_table_requested = Signal() # 新增信号：上传IO点表 -- REMOVED

    def __init__(self, parent=None):
        super().__init__("查询条件", parent)
        self.setup_ui()
        self.setup_connections()
        self.update_io_table_status(None, 0) # 初始化状态显示
        
    def setup_ui(self):
        """设置查询区域UI"""
        query_form_layout = QVBoxLayout()
        query_form_layout.setContentsMargins(5, 5, 5, 5)

        # 输入框区域
        input_container = QHBoxLayout()
        input_layout = QHBoxLayout()

        # 项目编号输入
        project_layout = QHBoxLayout()
        project_layout.addWidget(QLabel("项目编号:"))
        self.project_input = QLineEdit()
        self.project_input.setFixedWidth(200)
        project_layout.addWidget(self.project_input)
        input_layout.addLayout(project_layout)

        # 场站编号输入
        station_layout = QHBoxLayout()
        station_layout.addWidget(QLabel("场站编号:"))
        self.station_input = QLineEdit()
        self.station_input.setFixedWidth(200)
        station_layout.addWidget(self.station_input)
        input_layout.addLayout(station_layout)

        input_container.addStretch()
        input_container.addLayout(input_layout)
        input_container.addStretch()

        # 新增：IO点表状态显示区域
        io_status_layout = QHBoxLayout()
        self.io_status_label = QLabel("未加载IO点表")
        self.io_status_label.setStyleSheet("font-style: italic; color: gray;") # 初始样式
        io_status_layout.addStretch()
        io_status_layout.addWidget(self.io_status_label)
        io_status_layout.addStretch()

        # 按钮区域
        button_container = QHBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 创建按钮
        self.query_btn = QPushButton("查询")
        self.clear_btn = QPushButton("清空")
        # self.upload_io_table_btn = QPushButton("上传IO点表") # 新增：上传IO点表按钮 -- REMOVED
        
        # 创建HMI点表下拉菜单按钮
        # self.upload_hmi_btn = QPushButton("上传HMI点表") -- REMOVED
        # hmi_menu = QMenu(self.upload_hmi_btn) -- REMOVED
        # hmi_menu.addAction("亚控") -- REMOVED
        # hmi_menu.addAction("力控") -- REMOVED
        # self.upload_hmi_btn.setMenu(hmi_menu) -- REMOVED

        # 创建PLC点表下拉菜单按钮
        # self.upload_plc_btn = QPushButton("上传PLC点表") -- REMOVED
        # plc_menu = QMenu(self.upload_plc_btn) -- REMOVED
        # plc_menu.addAction("和利时") -- REMOVED
        # plc_menu.addAction("中控PLC") -- REMOVED
        # self.upload_plc_btn.setMenu(plc_menu) -- REMOVED

        # 统一设置按钮大小
        buttons = [self.query_btn, self.clear_btn] # REMOVED upload_io_table_btn, upload_hmi_btn, upload_plc_btn
                   # self.upload_io_table_btn, 
                   # self.upload_hmi_btn, self.upload_plc_btn
                   # ]
        for btn in buttons:
            btn.setFixedWidth(100)
            button_layout.addWidget(btn)

        button_container.addStretch()
        button_container.addLayout(button_layout)
        button_container.addStretch()

        query_form_layout.addLayout(input_container)
        query_form_layout.addLayout(io_status_layout) # 在输入和按钮之间添加状态显示
        query_form_layout.addLayout(button_container)
        self.setLayout(query_form_layout)

    def setup_connections(self):
        """设置信号连接"""
        self.query_btn.clicked.connect(self._on_query_clicked)
        self.clear_btn.clicked.connect(self.clear_requested)
        # self.upload_io_table_btn.clicked.connect(self.upload_io_table_requested.emit) # 新增：连接上传IO点表按钮的信号 -- REMOVED

        # 设置HMI菜单动作
        # hmi_menu = self.upload_hmi_btn.menu() -- REMOVED
        # hmi_menu.triggered.connect(lambda action: self.upload_hmi_requested.emit(action.text())) -- REMOVED

        # 设置PLC菜单动作
        # plc_menu = self.upload_plc_btn.menu() -- REMOVED
        # plc_menu.triggered.connect(lambda action: self.upload_plc_requested.emit(action.text())) -- REMOVED

    def _on_query_clicked(self):
        """处理查询按钮点击"""
        project_no = self.project_input.text().strip()
        # site_no 不再通过此信号发送，但仍可用于其他目的
        # site_no = self.station_input.text().strip() 
        self.query_requested.emit(project_no)

    def clear_inputs(self):
        """清空输入框"""
        self.project_input.clear()
        self.station_input.clear()
        # MainWindow._clear_loaded_io_data 会调用 self.update_io_table_status(None, 0)
        # 来重置状态标签，所以这里通常不需要再次显式调用，除非QueryArea的clear_inputs有独立于MainWindow的清除逻辑。

    def update_io_table_status(self, file_path: Optional[str], point_count: int):
        """
        更新IO点表加载状态的显示标签。

        参数:
            file_path (Optional[str]): 加载的IO点表文件的完整路径，或None如果未加载。
            point_count (int): 解析出的IO点数量。
        """
        if file_path:
            file_name = os.path.basename(file_path)
            self.io_status_label.setText(f"当前IO表: {file_name} ({point_count} 点)")
            self.io_status_label.setStyleSheet("color: green;") # 加载成功时的样式
            self.io_status_label.setToolTip(file_path) # 鼠标悬停时显示完整路径
        else:
            self.io_status_label.setText("未加载IO点表")
            self.io_status_label.setStyleSheet("font-style: italic; color: gray;") # 未加载时的样式
            self.io_status_label.setToolTip("") 