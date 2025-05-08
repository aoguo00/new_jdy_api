"""查询区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QMenu)
from PySide6.QtCore import Signal

class QueryArea(QGroupBox):
    """查询条件区域"""
    # 定义信号
    query_requested = Signal(str, str)  # 项目编号, 场站编号
    clear_requested = Signal()
    generate_points_requested = Signal()
    upload_hmi_requested = Signal(str)  # HMI类型
    upload_plc_requested = Signal(str)  # PLC类型
    plc_config_requested = Signal()  # PLC配置信号

    def __init__(self, parent=None):
        super().__init__("查询条件", parent)
        self.setup_ui()
        self.setup_connections()
        
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

        # 按钮区域
        button_container = QHBoxLayout()
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 创建按钮
        self.query_btn = QPushButton("查询")
        self.clear_btn = QPushButton("清空")
        self.generate_btn = QPushButton("生成点表")
        
        # 创建HMI点表下拉菜单按钮
        self.upload_hmi_btn = QPushButton("上传HMI点表")
        hmi_menu = QMenu(self.upload_hmi_btn)
        hmi_menu.addAction("亚控")
        hmi_menu.addAction("力控")
        self.upload_hmi_btn.setMenu(hmi_menu)

        # 创建PLC点表下拉菜单按钮
        self.upload_plc_btn = QPushButton("上传PLC点表")
        plc_menu = QMenu(self.upload_plc_btn)
        plc_menu.addAction("和利时")
        plc_menu.addAction("中控PLC")
        self.upload_plc_btn.setMenu(plc_menu)

        # 新增PLC配置按钮
        self.plc_config_button = QPushButton("PLC配置")

        # 统一设置按钮大小
        buttons = [self.query_btn, self.clear_btn, self.generate_btn, 
                  self.upload_hmi_btn, self.upload_plc_btn, 
                  self.plc_config_button]
        for btn in buttons:
            btn.setFixedWidth(100)
            button_layout.addWidget(btn)

        button_container.addStretch()
        button_container.addLayout(button_layout)
        button_container.addStretch()

        query_form_layout.addLayout(input_container)
        query_form_layout.addLayout(button_container)
        self.setLayout(query_form_layout)

    def setup_connections(self):
        """设置信号连接"""
        self.query_btn.clicked.connect(self._on_query_clicked)
        self.clear_btn.clicked.connect(self.clear_requested)
        self.generate_btn.clicked.connect(self.generate_points_requested)

        # 设置HMI菜单动作
        hmi_menu = self.upload_hmi_btn.menu()
        hmi_menu.triggered.connect(lambda action: self.upload_hmi_requested.emit(action.text()))

        # 设置PLC菜单动作
        plc_menu = self.upload_plc_btn.menu()
        plc_menu.triggered.connect(lambda action: self.upload_plc_requested.emit(action.text()))

        # PLC配置按钮连接
        self.plc_config_button.clicked.connect(self.plc_config_requested.emit)

    def _on_query_clicked(self):
        """处理查询按钮点击"""
        project_no = self.project_input.text().strip()
        site_no = self.station_input.text().strip()
        self.query_requested.emit(project_no, site_no)

    def clear_inputs(self):
        """清空输入框"""
        self.project_input.clear()
        self.station_input.clear() 