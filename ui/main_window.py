"""主窗口UI模块"""

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox
from PySide6.QtCore import Qt

# API and old DeviceManager (if still needed for other parts, though ideally not for third_party)
from core.query_area import JianDaoYunAPI, PLCHardwareService
# from core.devices import DeviceManager # Replaced by services for third_party logic

# Updated import for DatabaseService
# from core.db_manipulate.db_manager import DBManager # Old DBManager
from core.database.database_service import DatabaseService # New DatabaseService

# Import new services, DAOs, and DBManager for third_party_config_area
from core.third_party_config_area.database.dao import TemplateDAO, ConfiguredDeviceDAO
from core.third_party_config_area.template_service import TemplateService
from core.third_party_config_area.config_service import ConfigService

# Import new data processors
from core.project_list_area import format_project_data_for_ui, ProjectService
from core.device_list_area import format_device_data_for_ui, DeviceService

# UI Components
from ui.components.query_area import QueryArea
from ui.components.project_list_area import ProjectListArea
from ui.components.device_list_area import DeviceListArea
from ui.components.third_party_device_area import ThirdPartyDeviceArea

# Dialogs
from ui.dialogs.plc_config_dialog import PLCConfigDialog
# 移除模块管理对话框导入
# from ui.dialogs.module_manager_dialog import ModuleManagerDialog

# logger setup should ideally be in main.py or a dedicated logging config module
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("深化设计数据查询工具")
        
        screen = self.screen()
        # self.resize(screen.size()) # Maximizing anyway
        # self.setWindowState(Qt.WindowState.WindowMaximized)
        # For development, a fixed reasonable size might be better than always maximized
        self.resize(1280, 800)

        # 初始化核心服务和管理器
        try:
            self.jdy_api = JianDaoYunAPI()
            # self.template_manager = TemplateManager() # Remove old one
            # self.config_service = DeviceConfigurationService() # Remove old one
            self.plc_hardware_service = PLCHardwareService()
            self.project_service = ProjectService(self.jdy_api)
            self.device_service = DeviceService(self.jdy_api)
            
            # Instantiate new DatabaseService (singleton)
            self.db_service = DatabaseService() 
            
            # Instantiate DAOs for third_party_config_area with the DatabaseService
            self.template_dao = TemplateDAO(self.db_service)
            self.config_dao = ConfiguredDeviceDAO(self.db_service)
            
            # Instantiate Services for third_party_config_area with their respective DAOs
            self.tp_template_service = TemplateService(self.template_dao)
            self.tp_config_service = ConfigService(self.config_dao)
            
        except Exception as e:
            logger.error(f"核心服务初始化失败: {e}", exc_info=True)
            # Make sure other services are also set to None or handled
            self.jdy_api = None 
            # self.template_manager = None
            # self.config_service = None
            self.plc_hardware_service = None
            self.project_service = None
            self.device_service = None
            # Also set new DAOs/Services to None
            self.db_service = None
            self.template_dao = None
            self.config_dao = None
            self.tp_template_service = None
            self.tp_config_service = None
            QMessageBox.critical(self, "初始化错误", f"核心服务初始化失败: {str(e)}\n请检查数据库或配置文件。应用部分功能可能无法使用。")

        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置UI界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # Increased margins a bit

        # 左侧区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10) # Added spacing between left widgets

        # 创建组件
        self.query_area = QueryArea()
        self.project_list_area = ProjectListArea()
        self.device_list_area = DeviceListArea()
        
        # Instantiate ThirdPartyDeviceArea with the new services
        self.third_party_area = ThirdPartyDeviceArea(
            config_service=self.tp_config_service, # Pass new ConfigService
            template_service=self.tp_template_service, # Pass new TemplateService
            parent=self 
        )
        
        # 添加组件到布局
        left_layout.addWidget(self.query_area)
        left_layout.addWidget(self.project_list_area, stretch=1)
        left_layout.addWidget(self.device_list_area, stretch=2)

        main_layout.addWidget(left_widget, stretch=7)
        main_layout.addWidget(self.third_party_area, stretch=3)
        main_layout.setSpacing(10) # Added spacing between main areas

    def setup_connections(self):
        """设置信号连接"""
        # 查询区域信号
        self.query_area.query_requested.connect(self._handle_query)
        self.query_area.clear_requested.connect(self._handle_clear)
        self.query_area.generate_points_requested.connect(self._handle_generate_points)
        self.query_area.plc_config_requested.connect(self.show_plc_config_dialog)
        # 移除模块管理信号连接
        # self.query_area.module_manage_requested.connect(self.show_module_manager)

        # 项目列表信号
        self.project_list_area.project_selected.connect(self._handle_project_selected)

    def _handle_query(self, project_no: str, site_no: str):
        """处理查询请求"""
        try:
            # 执行查询 (调用 ProjectService)
            if not self.project_service:
                raise Exception("项目服务未初始化")
            projects = self.project_service.get_formatted_projects(project_no, site_no)
            # 更新列表
            self.project_list_area.update_project_list(projects)
        except Exception as e:
            logger.error(f"查询项目列表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "查询错误", f"查询项目列表失败: {str(e)}")

    def _handle_clear(self):
        """处理清空请求"""
        self.query_area.clear_inputs()
        self.project_list_area.clear_table()
        self.device_list_area.clear_table()
        # Optionally, also clear third_party_area if desired, 
        # but it has its own clear button.
        # self.config_service.clear_all_configurations()
        # self.third_party_area.update_third_party_table()

    def _handle_generate_points(self):
        """处理生成点表请求"""
        # Check if points are configured using the new service
        if not self.tp_config_service or not self.tp_config_service.get_all_configured_points():
            reply = QMessageBox.question(
                self, "提示", 
                "尚未配置第三方设备点位，是否现在配置?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes # Default to Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                # Ensure third_party_area is initialized before calling its method
                if hasattr(self, 'third_party_area') and self.third_party_area:
                     self.third_party_area.configure_third_party_device()
                else:
                     QMessageBox.warning(self, "错误", "第三方配置区域未初始化。")
        else:
            # Points are already configured, proceed with generation?
            # This is where the actual generation logic using tp_config_service would go.
            try:
                if not self.tp_config_service:
                     raise Exception("配置服务未初始化")
                
                # Example: Get data and maybe save to a default file or show preview
                points = self.tp_config_service.get_all_configured_points()
                if not points:
                    QMessageBox.information(self, "提示", "没有已配置的点位可供生成点表。")
                    return
                    
                # TODO: Define what "Generate Points Table" actually does.
                # For now, just show a success message with point count.
                QMessageBox.information(self, "生成点表 (占位符)", f"已获取 {len(points)} 个配置点位。\n(实际生成逻辑待实现)")
                
                # Example for future: Export to a default file
                # default_path = "generated_points.xlsx"
                # self.tp_config_service.export_to_excel(default_path)
                # QMessageBox.information(self, "成功", f"点表已生成到 {default_path}")
                
            except Exception as e:
                logger.error(f"生成点表时出错: {e}", exc_info=True)
                QMessageBox.critical(self, "错误", f"生成点表失败: {str(e)}")

    def _handle_project_selected(self, site_name: str):
        """处理项目选择"""
        try:
            # 执行查询 (调用 DeviceService)
            if not self.device_service:
                raise Exception("设备服务未初始化")
            all_devices = self.device_service.get_formatted_devices(site_name)
            
            # 更新设备列表
            self.device_list_area.update_device_list(all_devices)
            
        except Exception as e:
            logger.error(f"获取场站 '{site_name}' 的设备数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "数据加载错误", f"获取场站设备数据失败: {str(e)}")

    def show_plc_config_dialog(self):
        """显示PLC配置对话框"""
        # 使用新的不依赖数据库的PLC配置对话框
        dialog = PLCConfigDialog(parent=self)
        dialog.exec()

    # 移除模块管理对话框方法
    # def show_module_manager(self):
    #    """显示模块管理对话框"""
    #    if not self.plc_hardware_service:
    #        QMessageBox.warning(self, "错误", "PLC硬件服务不可用。")
    #        return
    #    dialog = ModuleManagerDialog(plc_hardware_service=self.plc_hardware_service, parent=self)
    #    dialog.exec()
