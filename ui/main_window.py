"""主窗口UI模块"""

from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QLabel, QLineEdit, QPushButton, QTableWidget,
                           QTableWidgetItem, QGroupBox, QHeaderView,
                           QSizePolicy, QMenu, QMessageBox, QFileDialog,
                               QDialog)
from PySide6.QtCore import Signal, Slot, QSize, Qt
from PySide6.QtGui import QScreen
from core.third_device.device_manager import DeviceManager
from ui.dialogs.device_point_dialog import DevicePointDialog
from ui.dialogs.plc_config_dialog import PLCConfigDialog
from core.jiandaoyun_api import JianDaoYunAPI
import logging
from datetime import datetime

# 简单的日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class QueryArea(QGroupBox):
    """查询条件区域"""
    # 定义信号
    query_requested = Signal(str, str)  # 项目编号, 场站编号
    clear_requested = Signal()
    generate_points_requested = Signal()
    upload_hmi_requested = Signal(str)  # HMI类型
    upload_plc_requested = Signal(str)  # PLC类型
    plc_config_requested = Signal()  # PLC配置信号
    module_manage_requested = Signal()  # 新增模块管理信号

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
        self.module_manage_button = QPushButton("模块管理")  # 新增模块管理按钮
        buttons = [self.query_btn, self.clear_btn, self.generate_btn, 
                  self.upload_hmi_btn, self.upload_plc_btn, 
                  self.plc_config_button, self.module_manage_button]  # 添加到按钮列表
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

        # 新增PLC配置按钮连接
        self.plc_config_button.clicked.connect(self.on_plc_config_clicked)

        # 新增模块管理按钮连接
        self.module_manage_button.clicked.connect(self.on_module_manage_clicked)

    def _on_query_clicked(self):
        """处理查询按钮点击"""
        project_no = self.project_input.text().strip()
        site_no = self.station_input.text().strip()
        self.query_requested.emit(project_no, site_no)

    def clear_inputs(self):
        """清空输入框"""
        self.project_input.clear()
        self.station_input.clear()

    def on_plc_config_clicked(self):
        """处理PLC配置按钮点击"""
        self.plc_config_requested.emit()

    def on_module_manage_clicked(self):
        """处理模块管理按钮点击"""
        self.module_manage_requested.emit()

class ProjectListArea(QGroupBox):
    """项目列表区域"""
    # 定义信号
    project_selected = Signal(str)  # 场站名称

    def __init__(self, parent=None):
        super().__init__("项目列表", parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置项目列表区域UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(5)
        self.project_table.setHorizontalHeaderLabels(
            ["项目名称", "场站", "项目编号", "深化设计编号", "客户名称"])

        # 设置列宽和自适应
        header = self.project_table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # 设置表格选择行为
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        layout.addWidget(self.project_table)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.project_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _on_selection_changed(self):
        """处理选择变更"""
        selected_items = self.project_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            site_name = self.project_table.item(row, 1).text()
            self.project_selected.emit(site_name)

    def update_project_list(self, data):
        """更新项目列表"""
        self.project_table.setRowCount(0)
        for row_data in data:
            row = self.project_table.rowCount()
            self.project_table.insertRow(row)
            self.project_table.setItem(row, 0, QTableWidgetItem(row_data.get('_widget_1635777114903', '')))
            self.project_table.setItem(row, 1, QTableWidgetItem(row_data.get('_widget_1635777114991', '')))
            self.project_table.setItem(row, 2, QTableWidgetItem(row_data.get('_widget_1635777114935', '')))
            self.project_table.setItem(row, 3, QTableWidgetItem(row_data.get('_widget_1636359817201', '')))
            self.project_table.setItem(row, 4, QTableWidgetItem(row_data.get('_widget_1635777114972', '')))

    def clear_table(self):
        """清空表格"""
        self.project_table.setRowCount(0)

class DeviceListArea(QGroupBox):
    """设备清单区域"""
    # 定义信号
    device_selected = Signal(str, int)  # 设备名称, 设备数量

    def __init__(self, parent=None):
        super().__init__("设备清单", parent)
        self.setup_ui()
        
    def setup_ui(self):
        """设置设备清单区域UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(7)
        self.device_table.setHorizontalHeaderLabels(
            ["设备名称", "品牌", "规格型号", "技术参数", "数量", "单位", "技术参数(外部)"])

        # 设置列宽和自适应
        header = self.device_table.horizontalHeader()
        header.setStretchLastSection(False)
        column_ratios = [2, 1, 1.5, 2, 0.8, 0.7, 2]
        total_ratio = sum(column_ratios)
        for i, ratio in enumerate(column_ratios):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            self.device_table.setColumnWidth(i, int(780 * ratio / total_ratio))

        layout.addWidget(self.device_table)
        self.setLayout(layout)

    def update_device_list(self, devices):
        """更新设备列表"""
        self.device_table.setRowCount(0)
        for device_info in devices:
            row = self.device_table.rowCount()
            self.device_table.insertRow(row)
            self.device_table.setItem(row, 0, QTableWidgetItem(str(device_info.get('_widget_1635777115211', ''))))
            self.device_table.setItem(row, 1, QTableWidgetItem(str(device_info.get('_widget_1635777115248', ''))))
            self.device_table.setItem(row, 2, QTableWidgetItem(str(device_info.get('_widget_1635777115287', ''))))
            self.device_table.setItem(row, 3, QTableWidgetItem(str(device_info.get('_widget_1641439264111', ''))))
            self.device_table.setItem(row, 4, QTableWidgetItem(str(device_info.get('_widget_1635777485580', ''))))
            self.device_table.setItem(row, 5, QTableWidgetItem(str(device_info.get('_widget_1654703913698', ''))))
            self.device_table.setItem(row, 6, QTableWidgetItem(str(device_info.get('_widget_1641439463480', ''))))

    def clear_table(self):
        """清空表格"""
        self.device_table.setRowCount(0)

class ThirdPartyDeviceArea(QGroupBox):
    """已配置的第三方设备区域"""
    def __init__(self, device_manager, parent=None):
        super().__init__("已配置的第三方设备", parent)
        self.device_manager = device_manager
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout()
        
        # 第三方设备表格
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(4)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "变量名", "点位数量", "状态"])

        # 设置列宽
        header = self.third_party_table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.third_party_table)

        # 按钮区域
        button_layout = QVBoxLayout()
        
        self.third_party_btn = QPushButton("第三方设备点表配置")
        self.export_btn = QPushButton("导出点表")
        self.clear_config_btn = QPushButton("清空配置")

        button_layout.addWidget(self.third_party_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.clear_config_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.third_party_btn.clicked.connect(self.configure_third_party_device)
        self.export_btn.clicked.connect(self.export_points_table)
        self.clear_config_btn.clicked.connect(self.clear_device_config)

    def configure_third_party_device(self):
        """配置第三方设备点表"""
        try:
            dialog = DevicePointDialog(self)
            if dialog.exec() == QDialog.Accepted:
                new_points = dialog.get_device_points()
                if new_points:
                    self.device_manager.add_device_points(new_points)
                    self.update_third_party_table()
                    QMessageBox.information(self, "成功", f"已配置 {len(new_points)} 个点位")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"配置设备点表时发生错误: {str(e)}")

    def update_third_party_table(self):
        """更新第三方设备列表"""
        try:
            self.third_party_table.setRowCount(0)
            device_stats = self.device_manager.update_third_party_table_data()
            
            for device in device_stats:
                row = self.third_party_table.rowCount()
                self.third_party_table.insertRow(row)
                self.third_party_table.setItem(row, 0, QTableWidgetItem(device['template']))
                self.third_party_table.setItem(row, 1, QTableWidgetItem(device['variable']))
                self.third_party_table.setItem(row, 2, QTableWidgetItem(str(device['count'])))
                self.third_party_table.setItem(row, 3, QTableWidgetItem(device['status']))
        except Exception as e:
            logging.error(f"更新第三方设备列表时发生错误: {e}")

    def clear_device_config(self):
        """清空设备配置"""
        if not self.device_manager.get_device_points():
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.device_manager.clear_device_points()
            self.update_third_party_table()
            QMessageBox.information(self, "已清空", "已清空所有设备配置")

    def export_points_table(self, parent=None):
        """导出点表"""
        if not self.device_manager.get_device_points():
            QMessageBox.warning(self, "警告", "没有可导出的点位数据")
            return

        default_filename = f"第三方设备点表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            parent or self, "保存点表", default_filename, "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                self.device_manager.export_to_excel(file_path)
                QMessageBox.information(parent or self, "成功", f"点表已成功导出至 {file_path}")
            except Exception as e:
                QMessageBox.critical(parent or self, "错误", f"导出失败: {str(e)}")

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("深化设计数据查询工具")
        
        # 获取主屏幕并设置窗口大小
        screen = self.screen()
        self.resize(screen.size())
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        # 初始化API客户端和设备管理器
        self.jdy_api = JianDaoYunAPI()
        self.device_manager = DeviceManager()

        # 创建UI
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 左侧区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # 创建各个区域
        self.query_area = QueryArea()
        self.project_list_area = ProjectListArea()
        self.device_list_area = DeviceListArea()
        self.third_party_area = ThirdPartyDeviceArea(self.device_manager)
        
        # 添加到左侧布局
        left_layout.addWidget(self.query_area)
        left_layout.addWidget(self.project_list_area, stretch=1)
        left_layout.addWidget(self.device_list_area, stretch=2)

        # 添加到主布局
        main_layout.addWidget(left_widget, stretch=7)
        main_layout.addWidget(self.third_party_area, stretch=3)

    def setup_connections(self):
        """设置信号连接"""
        # 查询区域信号连接
        self.query_area.query_requested.connect(self._handle_query)
        self.query_area.clear_requested.connect(self._handle_clear)
        self.query_area.generate_points_requested.connect(self._handle_generate_points)
        self.query_area.upload_hmi_requested.connect(self._handle_upload_hmi)
        self.query_area.upload_plc_requested.connect(self._handle_upload_plc)
        self.query_area.plc_config_requested.connect(self.show_plc_config_dialog)
        self.query_area.module_manage_requested.connect(self.show_module_manager)

        # 项目列表区域信号连接
        self.project_list_area.project_selected.connect(self._handle_project_selected)

    @Slot(str, str)
    def _handle_query(self, project_no, site_no):
        """处理查询请求"""
        try:
            data = self.jdy_api.query_data(project_no, site_no)
            self.project_list_area.update_project_list(data)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")

    @Slot()
    def _handle_clear(self):
        """处理清空请求"""
        self.query_area.clear_inputs()
        self.project_list_area.clear_table()
        self.device_list_area.clear_table()

    @Slot()
    def _handle_generate_points(self):
        """处理生成点表请求"""
        if not self.device_manager.get_device_points():
            reply = QMessageBox.question(
                self, "提示", 
                "尚未配置设备点位，是否现在配置?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.third_party_area.configure_third_party_device()

    @Slot(str)
    def _handle_upload_hmi(self, hmi_type):
        """处理HMI点表上传请求"""
        if not self.device_manager.get_device_points():
            QMessageBox.warning(self, "警告", "没有设备点表可上传")
            return
        # TODO: 实现HMI点表上传逻辑

    @Slot(str)
    def _handle_upload_plc(self, plc_type):
        """处理PLC点表上传请求"""
        if not self.device_manager.get_device_points():
            QMessageBox.warning(self, "警告", "没有设备点表可上传")
            return
        # TODO: 实现PLC点表上传逻辑

    @Slot(str)
    def _handle_project_selected(self, site_name):
        """处理项目选择"""
        try:
            response_data = self.jdy_api.query_site_devices(site_name)
            
            all_devices = []
            for data_item in response_data:
                device_list = data_item.get('_widget_1635777115095', [])
                if device_list:
                    all_devices.extend(device_list)
            
            self.device_list_area.update_device_list(all_devices)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取场站设备数据失败: {str(e)}")

    @Slot()
    def show_plc_config_dialog(self):
        """显示PLC配置对话框"""
        dialog = PLCConfigDialog(self)
        dialog.exec()

    @Slot()
    def show_module_manager(self):
        """显示模块管理对话框"""
        from ui.dialogs.module_manager_dialog import ModuleManagerDialog
        dialog = ModuleManagerDialog(self)
        dialog.exec()
