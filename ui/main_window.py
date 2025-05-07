"""主窗口UI模块"""

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from core.api import JianDaoYunAPI
from core.devices import DeviceManager
from ui.components.query_area import QueryArea
from ui.components.project_list_area import ProjectListArea
from ui.components.device_list_area import DeviceListArea
from ui.components.third_party_device_area import ThirdPartyDeviceArea
from ui.dialogs.plc_config_dialog import PLCConfigDialog
from ui.dialogs.module_manager_dialog import ModuleManagerDialog

# 日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("深化设计数据查询工具")
        
        # 设置窗口大小
        screen = self.screen()
        self.resize(screen.size())
        self.setWindowState(Qt.WindowState.WindowMaximized)
        
        # 初始化管理器
        self.jdy_api = JianDaoYunAPI()
        self.device_manager = DeviceManager()

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

        # 创建组件
        self.query_area = QueryArea()
        self.project_list_area = ProjectListArea()
        self.device_list_area = DeviceListArea()
        self.third_party_area = ThirdPartyDeviceArea(self.device_manager)
        
        # 添加组件到布局
        left_layout.addWidget(self.query_area)
        left_layout.addWidget(self.project_list_area, stretch=1)
        left_layout.addWidget(self.device_list_area, stretch=2)

        main_layout.addWidget(left_widget, stretch=7)
        main_layout.addWidget(self.third_party_area, stretch=3)

    def setup_connections(self):
        """设置信号连接"""
        # 查询区域信号
        self.query_area.query_requested.connect(self._handle_query)
        self.query_area.clear_requested.connect(self._handle_clear)
        self.query_area.generate_points_requested.connect(self._handle_generate_points)
        self.query_area.plc_config_requested.connect(self.show_plc_config_dialog)
        self.query_area.module_manage_requested.connect(self.show_module_manager)

        # 项目列表信号
        self.project_list_area.project_selected.connect(self._handle_project_selected)

    def _handle_query(self, project_no: str, site_no: str):
        """处理查询请求"""
        try:
            # 执行查询
            data = self.jdy_api.query_data(project_no, site_no)
            # 更新列表
            self.project_list_area.update_project_list(data)
        except Exception as e:
            logger.error(f"查询失败: {e}")
            QMessageBox.critical(self, "错误", f"查询失败: {str(e)}")

    def _handle_clear(self):
        """处理清空请求"""
        self.query_area.clear_inputs()
        self.project_list_area.clear_table()
        self.device_list_area.clear_table()

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

    def _handle_project_selected(self, site_name: str):
        """处理项目选择"""
        try:
            # 执行查询
            response_data = self.jdy_api.query_site_devices(site_name)
            
            # 处理数据
            all_devices = []
            for data_item in response_data:
                device_list = data_item.get('_widget_1635777115095', [])
                if device_list:
                    all_devices.extend(device_list)
            
            # 更新设备列表
            self.device_list_area.update_device_list(all_devices)
            
        except Exception as e:
            logger.error(f"获取场站设备数据失败: {e}")
            QMessageBox.critical(self, "错误", f"获取场站设备数据失败: {str(e)}")

    def show_plc_config_dialog(self):
        """显示PLC配置对话框"""
        dialog = PLCConfigDialog(self)
        dialog.exec()

    def show_module_manager(self):
        """显示模块管理对话框"""
        dialog = ModuleManagerDialog(self)
        dialog.exec()
