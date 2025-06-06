"""主窗口UI模块"""

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QDialog, QFileDialog, QStatusBar, QTabWidget, QPushButton, QLabel, QMenu, QApplication
from PySide6.QtCore import Qt
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd # 确保导入 pandas
import os
import configparser  # 新增：用于读取配置文件

# API and old DeviceManager (if still needed for other parts, though ideally not for third_party)
from core.query_area import JianDaoYunAPI
# from core.devices import DeviceManager # Replaced by services for third_party logic

# Updated import for DatabaseService
# from core.db_manipulate.db_manager import DBManager # Old DBManager
from core.third_party_config_area.database.database_service import DatabaseService # New DatabaseService

# Import new services, DAOs, and DBManager for third_party_config_area
from core.third_party_config_area.database.dao import TemplateDAO, ConfiguredDeviceDAO
from core.third_party_config_area.template_service import TemplateService
from core.third_party_config_area.config_service import ConfigService

# 导入新的 IO 数据加载器
from core.io_table import IODataLoader, IOExcelExporter

# 新增：导入我们统一的Excel数据加载器
from core.post_upload_processor.uploaded_file_processor.excel_reader import load_workbook_data
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint # 导入数据模型

# 导入文件验证器
from core.post_upload_processor.io_validation.validator import validate_io_table # 导入校验函数
# from core.post_upload_processor.io_validation.constants import PLC_IO_SHEET_NAME # 这个常量现在主要由 excel_reader 内部使用

# 导入点表生成器
from core.post_upload_processor.plc_generators.hollysys_generator.generator import HollysysGenerator
from core.post_upload_processor.plc_generators.hollysys_generator.safety_generator import SafetyHollysysGenerator # 新增：导入安全型生成器
from core.post_upload_processor.hmi_generators.yk_generator.generator import KingViewGenerator, C
from core.post_upload_processor.hmi_generators.lk_generator.generator import LikongGenerator # 新增：导入力控生成器
from core.post_upload_processor.fat_generators import generate_fat_checklist_from_source # 修改: 导入正确的函数

# Import new data processors
from core.project_list_area import ProjectService
from core.device_list_area import DeviceService

# UI Components
from ui.components.query_area import QueryArea
from ui.components.project_list_area import ProjectListArea
from ui.components.device_list_area import DeviceListArea
from ui.components.third_party_device_area import ThirdPartyDeviceArea
# 移除文档导入组件的导入，功能已整合到通道分配页面

# Dialogs - 修改：导入PLC配置组件
from ui.dialogs.plc_config_dialog import PLCConfigEmbeddedWidget
from ui.dialogs.error_display_dialog import ErrorDisplayDialog

# 新增：导入新的PLC配置组件
try:
    from ui.components.plc_config.plc_config_adapter import PLCConfigAdapter
    MODERN_PLC_CONFIG_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("PLC配置组件可用")
except ImportError as e:
    MODERN_PLC_CONFIG_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"PLC配置组件不可用: {e}")

# 移除模块管理对话框导入
# from ui.dialogs.module_manager_dialog import ModuleManagerDialog

# logger setup should ideally be in main.py or a dedicated logging config module
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self, db_path: str):
        super().__init__()
        self.setWindowTitle("工控系统点表管理软件V1.0")

        screen = self.screen()
        # self.resize(screen.size()) # Maximizing anyway
        # self.setWindowState(Qt.WindowState.WindowMaximized)
        # For development, a fixed reasonable size might be better than always maximized
        self.resize(1280, 800)

        # 初始化状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        # 初始化当前场站名称
        self.current_site_name: Optional[str] = None
        # 新增：用于存储已验证的IO点表路径和选择的PLC类型
        self.verified_io_table_path: Optional[str] = None
        self.selected_plc_type_for_upload: Optional[str] = None

        # 修改：用于存储从IO点表加载的所有已解析数据，按工作表名分组
        self.loaded_io_data_by_sheet: Optional[Dict[str, List[UploadedIOPoint]]] = None

        # 新增：存储数据库路径用于配置读取
        self.db_path = db_path

        # 创建上传按钮成员变量 (移到这里，以便 setup_ui 和 setup_connections 都能访问)
        self.upload_io_table_btn = QPushButton("上传IO点表")
        self.upload_io_table_btn.setMinimumHeight(28)
        self.upload_io_table_btn.setStyleSheet("QPushButton { padding-bottom: 2px; }")

        # 新增：创建生成上下位通讯点表按钮
        self.generate_communication_table_btn = QPushButton("生成上下位通讯点表")
        self.generate_communication_table_btn.setMinimumHeight(28)
        self.generate_communication_table_btn.setStyleSheet("QPushButton { padding-bottom: 2px; }")

        # 新增：创建生成FAT点表按钮
        self.generate_fat_table_btn = QPushButton("生成FAT点表")
        self.generate_fat_table_btn.setMinimumHeight(28)
        self.generate_fat_table_btn.setStyleSheet("QPushButton { padding-bottom: 2px; }")

        self.upload_hmi_btn = QPushButton("生成HMI点表")
        self.upload_hmi_btn.setMinimumHeight(28)
        self.upload_hmi_btn.setStyleSheet("QPushButton { padding-bottom: 2px; }")
        hmi_menu = QMenu(self.upload_hmi_btn) # QMenu 需要父对象
        hmi_menu.addAction("亚控")
        hmi_menu.addAction("力控")
        self.upload_hmi_btn.setMenu(hmi_menu)

        self.upload_plc_btn = QPushButton("生成PLC点表")
        self.upload_plc_btn.setMinimumHeight(28)
        self.upload_plc_btn.setStyleSheet("QPushButton { padding-bottom: 2px; }")
        plc_menu = QMenu(self.upload_plc_btn) # QMenu 需要父对象
        plc_menu.addAction("和利时PLC") # 恢复为统一的"和利时"选项
        plc_menu.addAction("中控PLC")
        self.upload_plc_btn.setMenu(plc_menu)

        # 初始化核心服务和管理器
        try:
            self.jdy_api = JianDaoYunAPI()
            # self.template_manager = TemplateManager() # Remove old one
            # self.config_service = DeviceConfigurationService() # Remove old one

            self.project_service = ProjectService(self.jdy_api)
            self.device_service = DeviceService(self.jdy_api)

            # Instantiate new DatabaseService (singleton) with the provided db_path
            self.db_service = DatabaseService(db_path=db_path)

            # Instantiate DAOs for third_party_config_area with the DatabaseService
            self.template_dao = TemplateDAO(self.db_service)
            self.config_dao = ConfiguredDeviceDAO(self.db_service)

            # Instantiate Services for third_party_config_area with their respective DAOs
            self.tp_template_service = TemplateService(self.template_dao)
            self.tp_config_service = ConfigService(self.config_dao)

            # 初始化IO数据加载器
            self.io_data_loader = IODataLoader()

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
            self.io_data_loader = None
            QMessageBox.critical(self, "初始化错误", f"核心服务初始化失败: {str(e)}\n请检查数据库或配置文件。应用部分功能可能无法使用。")

        self.setup_ui()
        self.setup_connections()

    def _get_config_value(self, key: str, default_value: Any) -> Any:
        """
        读取配置文件中的值

        Args:
            key: 配置键，支持点分隔的路径如 'ui.use_modern_plc_config'
            default_value: 默认值

        Returns:
            配置值或默认值
        """
        try:
            config = configparser.ConfigParser()
            # 修复：配置文件应该在项目根目录
            config_file_path = os.path.join(os.getcwd(), 'config.ini')

            if not os.path.exists(config_file_path):
                logger.warning(f"配置文件不存在: {config_file_path}，使用默认值")
                return default_value

            config.read(config_file_path, encoding='utf-8')

            # 解析点分隔的键
            parts = key.split('.')
            if len(parts) != 2:
                logger.warning(f"配置键格式无效: {key}，使用默认值")
                return default_value

            section, option = parts

            if not config.has_section(section.upper()):
                logger.warning(f"配置节不存在: {section}，使用默认值")
                return default_value

            if not config.has_option(section.upper(), option):
                logger.warning(f"配置项不存在: {key}，使用默认值")
                return default_value

            # 根据默认值类型进行转换
            value = config.get(section.upper(), option)

            if isinstance(default_value, bool):
                return value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default_value, int):
                return int(value)
            elif isinstance(default_value, float):
                return float(value)
            else:
                return value

        except Exception as e:
            logger.error(f"读取配置失败: {e}，使用默认值")
            return default_value

    def setup_ui(self):
        """设置UI界面"""
        central_widget = QWidget() # central_widget 仍然需要，QTabWidget 将设置在其上
        self.setCentralWidget(central_widget)

        # 创建 QTabWidget作为主窗口的主要布局管理器
        main_tab_widget = QTabWidget(central_widget) # 将 central_widget 作为 QTabWidget 的父对象

        # --- 第一个标签页：主功能区 (查询、项目、设备列表) ---
        main_functional_tab = QWidget()
        main_functional_layout = QVBoxLayout(main_functional_tab) # 为此标签页创建一个垂直布局
        main_functional_layout.setContentsMargins(5, 5, 5, 5) # 可以根据需要调整页边距
        main_functional_layout.setSpacing(10)

        # 创建和添加原左侧区域的组件到第一个标签页
        self.query_area = QueryArea()
        self.project_list_area = ProjectListArea()
        self.device_list_area = DeviceListArea()

        main_functional_layout.addWidget(self.query_area) # stretch 默认为0，通常查询区不需要拉伸
        main_functional_layout.addWidget(self.project_list_area, stretch=1) # 项目列表可以拉伸
        main_functional_layout.addWidget(self.device_list_area, stretch=2) # 设备列表可以拉伸更多

        main_tab_widget.addTab(main_functional_tab, "数据查询")

        # --- PLC硬件配置标签页 (新旧版本可配置切换) ---
        plc_config_tab_container = QWidget()
        plc_config_layout = QVBoxLayout(plc_config_tab_container)
        plc_config_layout.setContentsMargins(5,5,5,5)

        if self.io_data_loader:
            # 读取配置决定使用新版还是旧版
            use_modern_ui = self._get_config_value('ui.use_modern_plc_config', True)
            show_comparison = self._get_config_value('ui.show_comparison_mode', False)

            logger.info(f"PLC配置界面设置: use_modern_ui={use_modern_ui}, show_comparison={show_comparison}")

            if show_comparison:
                # 对比模式：同时显示新旧版本
                self._setup_comparison_plc_config(plc_config_layout)
                tab_title = "PLC硬件配置 (对比模式)"
            elif use_modern_ui and MODERN_PLC_CONFIG_AVAILABLE:
                # 使用新版组件
                try:
                    self.embedded_plc_config_widget = PLCConfigAdapter(
                        io_data_loader=self.io_data_loader,
                        devices_data=None,
                        parent=self
                    )
                    plc_config_layout.addWidget(self.embedded_plc_config_widget)
                    tab_title = "PLC硬件配置"
                    logger.info("成功加载PLC配置组件")
                except Exception as e:
                    logger.error(f"加载PLC配置组件失败，回退到旧版: {e}", exc_info=True)
                    self._setup_legacy_plc_config(plc_config_layout)
                    tab_title = "PLC硬件配置 (回退到旧版)"
            else:
                # 使用旧版组件
                self._setup_legacy_plc_config(plc_config_layout)
                tab_title = "PLC硬件配置 (经典版)"
                if not MODERN_PLC_CONFIG_AVAILABLE:
                    logger.info("PLC配置组件不可用，使用旧版组件")
        else:
            # IO数据加载器不可用
            error_label_main = QLabel("错误：PLC配置模块因IO数据服务不可用而无法加载。")
            error_label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label_main.setStyleSheet("color: red; font-size: 14px;")
            plc_config_layout.addWidget(error_label_main)
            self.embedded_plc_config_widget = None
            tab_title = "PLC硬件配置 (不可用)"

        main_tab_widget.addTab(plc_config_tab_container, tab_title)

        # --- 第三方设备配置标签页 ---
        self.third_party_area = ThirdPartyDeviceArea(
            config_service=self.tp_config_service,
            template_service=self.tp_template_service,
            parent=self
        )
        main_tab_widget.addTab(self.third_party_area, "第三方设备配置") # 第三方移到前面

        # --- IO点表模板生成标签页 (移到前面) ---
        io_template_tab = QWidget()
        io_template_layout = QVBoxLayout(io_template_tab)
        io_template_layout.setContentsMargins(20, 20, 20, 20)
        io_template_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.generate_io_template_btn = QPushButton("生成当前PLC配置的IO点表模板")
        self.generate_io_template_btn.setFixedWidth(300)
        self.generate_io_template_btn.setFixedHeight(40)
        description_label = QLabel("此功能会根据当前在'<b>'PLC硬件配置'</b>'选项卡中应用的模块配置，<br>生成一个包含对应通道地址的Excel点表模板文件。<br>请确保PLC硬件配置已应用。场站编号将从上方查询区域获取。")
        description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description_label.setWordWrap(True)

        io_template_layout.addStretch(1)
        io_template_layout.addWidget(description_label)
        io_template_layout.addSpacing(20)
        io_template_layout.addWidget(self.generate_io_template_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        io_template_layout.addStretch(2)

        main_tab_widget.addTab(io_template_tab, "IO点表模板生成") # IO模板生成移到前面

        # --- 通道分配标签页（已整合文档导入功能）---
        from ui.components.channel_assignment_widget import ChannelAssignmentWidget
        self.channel_assignment_widget = ChannelAssignmentWidget()
        main_tab_widget.addTab(self.channel_assignment_widget, "通道分配")

        # --- 将 QTabWidget 设置为 central_widget 的布局 (使其充满central_widget) ---
        # 为了让 QTabWidget 充满 central_widget，我们需要给 central_widget 也设置一个布局
        # 并将 main_tab_widget 添加到这个布局中。
        outer_layout_for_central_widget = QHBoxLayout(central_widget) # 或者 QVBoxLayout
        outer_layout_for_central_widget.setContentsMargins(0,0,0,0) # 确保 QTabWidget 填满
        outer_layout_for_central_widget.addWidget(main_tab_widget)
        # central_widget.setLayout(outer_layout_for_central_widget) # 这一步已在创建布局时通过传递父对象完成

        # 创建包含上传按钮的角部控件
        upload_buttons_widget = QWidget(main_tab_widget) # 父对象设为 main_tab_widget 或 self
        upload_buttons_layout = QHBoxLayout(upload_buttons_widget)
        upload_buttons_layout.setContentsMargins(5, 0, 5, 0) # 修改后：上下边距为0
        upload_buttons_layout.setSpacing(5) # 按钮之间的间距

        # 此处直接使用已在 __init__ 中创建的按钮实例
        upload_buttons_layout.addWidget(self.upload_io_table_btn)
        upload_buttons_layout.addWidget(self.generate_communication_table_btn)
        upload_buttons_layout.addWidget(self.generate_fat_table_btn)
        upload_buttons_layout.addWidget(self.upload_hmi_btn)
        upload_buttons_layout.addWidget(self.upload_plc_btn)
        upload_buttons_widget.setLayout(upload_buttons_layout) # 确保布局被设置

        # 将包含按钮的QWidget设置为标签栏的角部控件 (例如，右上角)
        main_tab_widget.setCornerWidget(upload_buttons_widget, Qt.Corner.TopRightCorner)

    def _setup_legacy_plc_config(self, layout: QVBoxLayout):
        """设置旧版PLC配置组件"""
        self.embedded_plc_config_widget = PLCConfigEmbeddedWidget(
            io_data_loader=self.io_data_loader,
            devices_data=None,
            parent=self
        )
        layout.addWidget(self.embedded_plc_config_widget)
        logger.info("已设置旧版PLC配置组件")

    def _setup_comparison_plc_config(self, layout: QVBoxLayout):
        """设置对比模式PLC配置组件"""
        from PySide6.QtWidgets import QSplitter

        # 创建水平分割器
        splitter = QSplitter(Qt.Horizontal)

        # 左侧：旧版组件
        left_frame = QWidget()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(4, 4, 4, 4)

        left_title = QLabel("📝 经典版 PLCConfigEmbeddedWidget")
        left_title.setStyleSheet("font-weight: bold; color: #fa8c16; font-size: 14px;")
        left_layout.addWidget(left_title)

        self.embedded_plc_config_widget = PLCConfigEmbeddedWidget(
            io_data_loader=self.io_data_loader,
            devices_data=None,
            parent=self
        )
        left_layout.addWidget(self.embedded_plc_config_widget)

        # 右侧：新版组件
        right_frame = QWidget()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(4, 4, 4, 4)

        right_title = QLabel("🚀  PLCConfigAdapter")
        right_title.setStyleSheet("font-weight: bold; color: #52c41a; font-size: 14px;")
        right_layout.addWidget(right_title)

        if MODERN_PLC_CONFIG_AVAILABLE:
            try:
                self.modern_plc_config_widget = PLCConfigAdapter(
                    io_data_loader=self.io_data_loader,
                    devices_data=None,
                    parent=self
                )
                right_layout.addWidget(self.modern_plc_config_widget)
            except Exception as e:
                error_label = QLabel(f"组件加载失败: {str(e)}")
                error_label.setStyleSheet("color: red; font-size: 12px;")
                right_layout.addWidget(error_label)
                logger.error(f"对比模式中组件加载失败: {e}", exc_info=True)
        else:
            unavailable_label = QLabel("组件不可用")
            unavailable_label.setStyleSheet("color: #8c8c8c; font-size: 12px;")
            right_layout.addWidget(unavailable_label)

        # 添加到分割器
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([700, 700])

        layout.addWidget(splitter)
        logger.info("已设置对比模式PLC配置组件")

    def setup_connections(self):
        """设置信号连接"""
        # 查询区域信号
        self.query_area.query_requested.connect(self._handle_query)
        self.query_area.clear_requested.connect(self._handle_clear)

        # 直接连接在MainWindow中创建的上传按钮的信号
        self.upload_io_table_btn.clicked.connect(self._handle_upload_io_table)
        # 新增：连接生成上下位通讯点表按钮的信号
        self.generate_communication_table_btn.clicked.connect(self._handle_generate_communication_table)
        # HMI 和 PLC 按钮的菜单信号连接
        if self.upload_hmi_btn.menu():
            self.upload_hmi_btn.menu().triggered.connect(
                lambda action: self._handle_hmi_generation_requested(action.text())
            )
        if self.upload_plc_btn.menu():
            self.upload_plc_btn.menu().triggered.connect(
                lambda action: self._handle_plc_generation_requested(action.text())
            )

        # 项目列表信号
        self.project_list_area.project_selected.connect(self._handle_project_selected)

        # IO点表模板生成按钮信号
        if hasattr(self, 'generate_io_template_btn'):
            self.generate_io_template_btn.clicked.connect(self._trigger_generate_points)

        # 新增：生成FAT点表按钮信号
        if hasattr(self, 'generate_fat_table_btn'):
            self.generate_fat_table_btn.clicked.connect(self._handle_generate_fat_table)

        # PLC配置重置信号连接
        if hasattr(self, 'embedded_plc_config_widget') and self.embedded_plc_config_widget:
            # 检查组件类型并连接相应的重置信号
            if hasattr(self.embedded_plc_config_widget, 'configuration_reset'):
                # 组件（PLCConfigAdapter）
                self.embedded_plc_config_widget.configuration_reset.connect(self._handle_plc_config_reset)
                logger.info("已连接PLC配置组件的重置信号")
            elif hasattr(self.embedded_plc_config_widget, 'configurationReset'):
                # 直接使用PLCConfigWidget的情况
                self.embedded_plc_config_widget.configurationReset.connect(self._handle_plc_config_reset)
                logger.info("已连接PLCConfigWidget的重置信号")

        # 对比模式下的组件信号连接
        if hasattr(self, 'modern_plc_config_widget') and self.modern_plc_config_widget:
            if hasattr(self.modern_plc_config_widget, 'configuration_reset'):
                self.modern_plc_config_widget.configuration_reset.connect(self._handle_plc_config_reset)
                logger.info("已连接对比模式PLC配置组件的重置信号")

        # 文档导入功能已整合到通道分配页面，无需单独连接信号

    def _handle_query(self, project_no: str):
        """处理查询请求"""
        # 新增: 校验项目编号是否为空
        if not project_no or not project_no.strip():
            QMessageBox.warning(self, "输入错误", "请输入有效的项目编号后再查询。")
            logger.warning("用户尝试在项目编号为空时执行查询。")
            self.status_bar.showMessage("请输入项目编号。")
            return

        try:
            # 执行查询 (调用 ProjectService)
            if not self.project_service:
                raise Exception("项目服务未初始化")
            projects = self.project_service.get_formatted_projects(project_no=project_no)
            # 更新列表
            self.project_list_area.update_project_list(projects)
        except Exception as e:
            logger.error(f"查询项目列表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "查询错误", f"查询项目列表失败: {str(e)}")

    def _handle_clear(self):
        """处理清空按钮点击事件。"""
        self.query_area.clear_inputs()
        self.project_list_area.clear_table()
        self.device_list_area.clear_table()
        self.loaded_io_data_by_sheet = {} # 清空已加载的IO点表数据
        self.verified_io_table_path = None # 清空已验证的IO路径
        self.selected_plc_type_for_upload = None # 清空已选的PLC类型
        # 新增：通知QueryArea更新状态标签
        self.query_area.update_io_table_status(None, 0)
        logger.info("查询条件、项目列表、设备列表及已加载IO数据已清空。")

        # 新增：如果PLC配置嵌入式组件存在，则重置其状态
        if hasattr(self, 'embedded_plc_config_widget') and self.embedded_plc_config_widget:
            logger.info(f"Attempting to reset PLCConfigEmbeddedWidget. Type: {type(self.embedded_plc_config_widget)}")
            logger.info(f"Attributes of embedded_plc_config_widget: {dir(self.embedded_plc_config_widget)}")
            try:
                self.embedded_plc_config_widget.reset_to_initial_state()
                logger.info("PLC hardware configuration tab has been reset to its initial state.")
            except AttributeError: # 防御性编程，以防方法名不匹配或对象状态问题
                logger.error("PLCConfigEmbeddedWidget might not have 'reset_to_initial_state' or encountered an issue.")
            except Exception as e:
                logger.error(f"An unexpected error occurred while resetting PLCConfigEmbeddedWidget: {e}", exc_info=True)
        else:
            logger.info("PLCConfigEmbeddedWidget is not available, skipping its reset.")

        QMessageBox.information(self, "操作完成", "所有相关区域已清空。")

    def _handle_generate_points(self, site_no: str):
        """
        处理生成空的IO点表模板的请求。
        文件将保存到应用程序工作目录下的 "IO点表模板" 子文件夹中。

        Args:
            site_no (str): 当前操作的场站编号。
        """
        logger.info(f"Attempting to generate IO table template for site_no: {site_no}")

        if not self.io_data_loader or not self.io_data_loader.current_plc_config:
            logger.warning("PLC configuration is empty. Aborting IO table template generation.")
            QMessageBox.warning(self, "提示", "请先完成PLC模块配置，再生成IO点表模板。")
            return

        try:
            if not self.io_data_loader:
                logger.error("IODataLoader 未初始化，无法生成点表模板。")
                QMessageBox.warning(self, "错误", "IO数据加载服务未准备就绪。")
                return

            plc_io_points = self.io_data_loader.get_channel_addresses() # 获取PLC硬件配置生成的点

            third_party_points_for_export: Optional[List[Dict[str, Any]]] = None
            if self.tp_config_service:
                try:
                    configured_tp_models = self.tp_config_service.get_all_configured_points()
                    if configured_tp_models:
                        third_party_points_for_export = []
                        for tp_model in configured_tp_models:
                            point_dict = {
                                'template_name': tp_model.template_name,
                                'point_name': tp_model.variable_name,
                                'address': tp_model.variable_name,
                                'data_type': tp_model.data_type,
                                'description': tp_model.description,
                                'device_name': tp_model.variable_prefix,
                                'functional_location': '',
                                'sll_setpoint': getattr(tp_model, 'sll_setpoint', ""),
                                'sl_setpoint': getattr(tp_model, 'sl_setpoint', ""),
                                'sh_setpoint': getattr(tp_model, 'sh_setpoint', ""),
                                'shh_setpoint': getattr(tp_model, 'shh_setpoint', "")
                            }
                            third_party_points_for_export.append(point_dict)
                except Exception as e_tp_fetch:
                    logger.error(f"获取或转换第三方设备点位数据以生成模板时出错: {e_tp_fetch}", exc_info=True)
                    # 不中断，允许仅导出PLC数据

            if not plc_io_points and not third_party_points_for_export:
                logger.info("没有已配置的PLC IO点或第三方设备点位可供导出模板。")
                QMessageBox.information(self, "提示", "没有可导出为模板的IO点数据。")
                return

            default_filename = "IO_点表.xlsx"
            if self.current_site_name:
                safe_site_name = "".join(c if c.isalnum() or c in ['-', '_', ' '] else '_' for c in self.current_site_name.strip()).replace(' ', '_').strip('_')
                if safe_site_name: default_filename = f"{safe_site_name}_IO_点表.xlsx"

            output_base_dir = "IO点表模板"
            output_dir = os.path.join(os.getcwd(), output_base_dir)
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, default_filename)
            logger.info(f"IO点表模板将保存到: {file_path}")

            try:
                exporter = IOExcelExporter()
                success = exporter.export_to_excel(plc_io_data=plc_io_points,
                                                   third_party_data=third_party_points_for_export,
                                                   filename=file_path,
                                                   site_name=self.current_site_name,
                                                   site_no=site_no)
                if success:
                    # 保存PLC模板数据供通道分配使用
                    self.last_generated_plc_template = plc_io_points
                    self.channel_assignment_widget.set_plc_template_data(plc_io_points)

                    QMessageBox.information(self, "成功", f"IO点表模板已成功导出到:\\n{file_path}")
                    self.status_bar.showMessage(f"IO点表模板已导出: {file_path}", 7000)
                else:
                    QMessageBox.warning(self, "导出失败", "IO点表模板导出失败。\\\\n请检查日志获取详细信息。")
                    self.status_bar.showMessage("IO点表模板导出失败。")

            except ImportError as e_import_inner:
                logger.error(f"导出Excel模板所需的库缺失 (openpyxl likely): {e_import_inner}", exc_info=True)
                QMessageBox.critical(self, "依赖缺失", f"导出Excel功能需要 openpyxl 库。\\\\n请通过 pip install openpyxl 安装它。\\\\n错误详情: {e_import_inner}")
                self.status_bar.showMessage("导出Excel依赖缺失。")
            except Exception as e_inner_export:
                logger.error(f"生成IO点表模板过程中（导出步骤）出错: {e_inner_export}", exc_info=True)
                QMessageBox.critical(self, "错误", f"生成IO点表模板的导出步骤失败: {str(e_inner_export)}")
                self.status_bar.showMessage("IO点表模板导出时出错。")

        except Exception as e_outer_general:
            logger.error(f"处理生成IO点表模板请求时发生总体错误: {e_outer_general}", exc_info=True)
            QMessageBox.critical(self, "错误", f"生成IO点表模板失败: {str(e_outer_general)}")
            self.status_bar.showMessage("生成IO点表模板失败（常规错误）。")

    def _handle_project_selected(self, site_name: str):
        """处理项目选择事件"""
        try:
            # 更新当前场站名称
            self.current_site_name = site_name
            logger.info(f"_handle_project_selected FOR {site_name} CALLED") # 新增日志
            logger.info(f"当前选定的场站已更新为: {self.current_site_name}")

            # 设置IODataLoader的当前场站名称（用于缓存管理）
            if hasattr(self, 'io_data_loader') and self.io_data_loader:
                self.io_data_loader.set_current_site(site_name)
                logger.info(f"已设置IODataLoader的当前场站为: {site_name}")

            # 执行查询 (调用 DeviceService)
            if not self.device_service:
                raise Exception("设备服务未初始化")
            all_devices = self.device_service.get_formatted_devices(site_name)

            logger.info(f"原始 all_devices 列表长度: {len(all_devices) if all_devices else 0}") # 新增日志
            if all_devices: # 仅当all_devices非空时记录详情
                raw_lk117_count = sum(1 for d in all_devices if d.get('_widget_1635777115287', '').upper() == 'LK117')
                # 统计LK610S的条目数及其基于数量的总实例数
                raw_lk610s_entries = [d for d in all_devices if d.get('_widget_1635777115287', '').upper() == 'LK610S']
                raw_lk610s_entry_count = len(raw_lk610s_entries)
                # 安全地将数量字符串转换为整数，如果为空或无效则视为0
                raw_lk610s_instance_count = sum(int(d.get('_widget_1635777485580', '0') or '0') for d in raw_lk610s_entries)
                logger.info(f"原始数据中 LK117 条目数: {raw_lk117_count}")
                logger.info(f"原始数据中 LK610S 条目数: {raw_lk610s_entry_count}, 基于数量的实例总数: {raw_lk610s_instance_count}")

            # 更新设备列表
            self.device_list_area.update_device_list(all_devices)

            # 更新第三方设备区域的当前场站信息
            if hasattr(self, 'third_party_area') and self.third_party_area:
                self.third_party_area.set_current_site_name(site_name)

            # 文档导入功能已整合到通道分配页面

            # 更新内嵌的PLC配置区域的设备数据
            if hasattr(self, 'embedded_plc_config_widget') and self.embedded_plc_config_widget:
                logger.info(f"准备调用 get_current_devices，当前 device_table 行数: {self.device_list_area.device_table.rowCount() if self.device_list_area and self.device_list_area.device_table else 'N/A'}") # 新增日志
                current_devices_for_plc_config = self.get_current_devices() # 获取最新的设备数据
                logger.info(f"get_current_devices 返回后，列表长度: {len(current_devices_for_plc_config) if current_devices_for_plc_config else 0}") # 新增日志
                if current_devices_for_plc_config: # 仅当列表非空时记录详情
                    processed_lk117_count = sum(1 for d in current_devices_for_plc_config if d.get('_widget_1635777115287', '').upper() == 'LK117')
                    processed_lk610s_count = sum(1 for d in current_devices_for_plc_config if d.get('_widget_1635777115287', '').upper() == 'LK610S')
                    logger.info(f"get_current_devices 返回的列表中 LK117 实例数: {processed_lk117_count}")
                    logger.info(f"get_current_devices 返回的列表中 LK610S 实例数: {processed_lk610s_count}")
                self.embedded_plc_config_widget.set_devices_data(current_devices_for_plc_config)

            self.status_bar.showMessage(f"已选择场站: {site_name}，设备列表已更新。")

        except Exception as e:
            logger.error(f"处理项目选择时出错: {e}", exc_info=True) # 更新日志信息
            QMessageBox.critical(self, "项目选择错误", f"处理项目 '{site_name}' 选择失败: {str(e)}")

    def _handle_upload_io_table(self):
        """处理 '上传IO点表' 按钮点击或信号。"""
        if self.loaded_io_data_by_sheet:
            reply = QMessageBox.question(self, "确认覆盖",
                                         "当前已加载IO点表数据。重新上传将覆盖现有数据，确定吗？",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
            else:
                self._clear_loaded_io_data() # 清除旧数据

        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(self, "选择要上传的IO点表文件", "", "Excel 文件 (*.xlsx *.xls);;所有文件 (*)")

        if not file_path:
            self.status_bar.showMessage("未选择文件")
            logger.info("用户取消了选择IO点表文件。")
            return

        file_name = os.path.basename(file_path)
        logger.info(f"用户选择了IO点表文件进行上传和加载: {file_path}")
        self.status_bar.showMessage(f"正在验证文件: {file_name}...")

        is_valid, message = validate_io_table(file_path)

        if not is_valid:
            self.status_bar.showMessage(f"文件验证失败: {file_name}")
            error_dialog = ErrorDisplayDialog(message, self)
            error_dialog.exec()
            logger.warning(f"IO点表文件 '{file_path}' 验证失败: {message}")
            return

        logger.info(f"IO点表文件 '{file_path}' 验证通过。准备加载数据...")
        self.status_bar.showMessage(f"文件验证通过: {file_name}。正在加载数据...")

        try:
            loaded_data_dict, error_msg_load = load_workbook_data(file_path)

            if error_msg_load:
                self._clear_loaded_io_data()
                logger.error(f"从 '{file_path}' 加载数据时返回错误: {error_msg_load}")
                QMessageBox.critical(self, "数据加载错误", f"加载IO点表数据时发生错误: {error_msg_load}")
                self.status_bar.showMessage(f"文件 '{file_name}' 数据加载失败。")
                return

            self.loaded_io_data_by_sheet = loaded_data_dict
            self.verified_io_table_path = file_path

            if not self.loaded_io_data_by_sheet: # 检查字典是否为空
                final_load_msg = f"文件 '{file_name}' 加载完成，但未解析到任何工作表的有效数据。"
                logger.warning(final_load_msg)
                QMessageBox.warning(self, "数据加载提示", final_load_msg)
                if hasattr(self.query_area, 'update_io_table_status'):
                    self.query_area.update_io_table_status(None, 0)
            else:
                num_sheets = len(self.loaded_io_data_by_sheet)
                total_points = sum(len(points) for points in self.loaded_io_data_by_sheet.values())
                final_load_msg = f"文件 '{file_name}' 数据已加载: 从 {num_sheets} 个工作表共解析 {total_points} 个点位。"
                logger.info(final_load_msg)
                if hasattr(self.query_area, 'update_io_table_status'):
                    self.query_area.update_io_table_status(self.verified_io_table_path, total_points)

            self.status_bar.showMessage(final_load_msg + " 等待后续生成操作。", 10000)

        except Exception as e_load:
            self._clear_loaded_io_data()
            logger.error(f"从 '{file_path}' 加载数据失败: {e_load}", exc_info=True)
            QMessageBox.critical(self, "数据加载错误", f"加载IO点表数据失败: {str(e_load)}")
            self.status_bar.showMessage(f"文件 '{file_name}' 数据加载失败。")

    def _handle_plc_generation_requested(self, plc_generation_type: str):
        """
        处理用户选择的PLC点表生成请求。
        对于和利时，将一次性生成变量表和Modbus点表。
        点表将保存到应用程序工作目录下的 "PLC点表/<PLC厂家>" 子文件夹中。

        Args:
            plc_generation_type (str): 用户选择的PLC点表生成类型，如 "和利时PLC", "中控PLC"。
        """
        logger.info(f"用户选择了PLC点表生成类型: {plc_generation_type}")

        if not self.loaded_io_data_by_sheet:
            QMessageBox.warning(self, "操作无效", "请先上传、验证并成功加载一个IO点表文件。")
            logger.warning("用户在未成功加载IO数据的情况下尝试生成PLC点表。")
            self.status_bar.showMessage("请先上传并加载IO点表")
            return

        file_name_base_with_ext = os.path.basename(self.verified_io_table_path or "Uploaded_IO_Table.xlsx")
        base_io_filename, _ = os.path.splitext(file_name_base_with_ext)
        base_io_filename_cleaned = base_io_filename.replace("_(已校验)", "").replace("(已校验)","").replace("_IO_点表","", 1).replace("IO_点表","", 1).replace("_模板", "").replace("模板", "")

        self.status_bar.showMessage(f"准备为已加载数据生成 '{plc_generation_type}' 相关点表...")

        if plc_generation_type == "和利时PLC": # 统一处理和利时请求
            self._generate_hollysys_all_tables(base_io_filename_cleaned)
        elif plc_generation_type == "中控PLC":
            logger.info(f"准备根据已加载数据生成中控PLC点表。")
            QMessageBox.information(self, "功能待实现", f"已选择根据已加载数据生成 '{plc_generation_type}' PLC点表。\n该功能正在开发中。")
        else:
            QMessageBox.warning(self, "类型不支持", f"目前不支持生成PLC点表类型 '{plc_generation_type}'。")
            logger.warning(f"用户尝试为不支持的PLC点表类型 '{plc_generation_type}' 生成。")
            self.status_bar.showMessage(f"不支持的PLC点表类型: {plc_generation_type}")

    def _generate_hollysys_all_tables(self, base_io_filename_cleaned: str):
        """为和利时PLC生成所有相关点表（变量表和Modbus表）。"""
        plc_manufacturer = "和利时"
        logger.info(f"准备为和利时PLC生成点表。")

        is_safety_system = self._is_safety_plc()
        generator: Any # Type hint for generator

        if is_safety_system:
            logger.info("检测到安全PLC模块，将使用 SafetyHollysysGenerator。")
            # 确保 SafetyHollysysGenerator 初始化时需要 module_info_provider
            if not self.io_data_loader or not hasattr(self.io_data_loader, 'module_info_provider'):
                QMessageBox.critical(self, "错误", "无法初始化安全PLC点表生成器：缺少模块信息提供者。")
                logger.error("无法初始化SafetyHollysysGenerator: io_data_loader或module_info_provider不可用。")
                self.status_bar.showMessage("安全PLC点表生成失败：初始化错误。")
                return
            generator = SafetyHollysysGenerator(module_info_provider=self.io_data_loader.module_info_provider)
        else:
            logger.info("未检测到安全PLC模块，将使用 HollysysGenerator。")
            generator = HollysysGenerator()

        # --- 1. 生成变量表 ---
        try:
            base_output_dir_vars = os.path.join(os.getcwd(), "PLC点表")
            target_plc_mfg_dir_vars = os.path.join(base_output_dir_vars, plc_manufacturer)
            os.makedirs(target_plc_mfg_dir_vars, exist_ok=True)

            variable_table_filename_suffix: str
            if is_safety_system:
                variable_table_filename_suffix = "安全型变量表"
            else:
                # 非安全型，恢复原始文件名后缀 (或您期望的后缀)
                # 根据日志，非安全型变量表的后缀是 "变量表"
                variable_table_filename_suffix = "变量表"

            output_filename_vars = f"{base_io_filename_cleaned}_和利时{variable_table_filename_suffix}.xls"
            save_path_vars = os.path.join(target_plc_mfg_dir_vars, output_filename_vars)
            logger.info(f"和利时PLC{'安全型' if is_safety_system else ''}变量表将保存到: {save_path_vars}")

            success_vars: bool
            error_message_vars: Optional[str]

            if is_safety_system:
                # SafetyHollysysGenerator 调用 generate_safety_hollysys_table
                success_vars, error_message_vars = generator.generate_safety_hollysys_table(
                    points_by_sheet=self.loaded_io_data_by_sheet,
                    output_path=save_path_vars
                )
            else:
                # HollysysGenerator 调用 generate_hollysys_table
                success_vars, error_message_vars = generator.generate_hollysys_table(
                    points_by_sheet=self.loaded_io_data_by_sheet,
                    output_path=save_path_vars
                )

            if success_vars:
                QMessageBox.information(self, "变量表生成成功", f"和利时PLC{'安全型' if is_safety_system else ''}变量表已成功导出到:\n{save_path_vars}")
                self.status_bar.showMessage(f"和利时{'安全型' if is_safety_system else ''}变量表已生成: {output_filename_vars}", 7000)
            else:
                detailed_error_msg_vars = error_message_vars if error_message_vars else f"生成和利时PLC{'安全型' if is_safety_system else ''}变量表失败。"
                QMessageBox.critical(self, "变量表生成失败", detailed_error_msg_vars)
                logger.error(f"和利时{'安全型' if is_safety_system else ''}变量表生成失败: {detailed_error_msg_vars}")
                self.status_bar.showMessage(f"和利时{'安全型' if is_safety_system else ''}变量表生成失败。")

        except Exception as e_vars:
            logger.error(f"生成和利时PLC{'安全型' if is_safety_system else ''}变量表时发生未知错误: {e_vars}", exc_info=True)
            QMessageBox.critical(self, "变量表生成错误", f"生成和利时PLC{'安全型' if is_safety_system else ''}变量表时发生未知错误:\n{e_vars}")
            self.status_bar.showMessage(f"和利时{'安全型' if is_safety_system else ''}变量表生成时发生错误。")
            # 如果变量表生成失败，对于安全系统，也应考虑是否继续生成Modbus表，目前是继续
            # 对于非安全系统，到此结束

        # --- 2. 只有安全系统才生成Modbus点表 ---
        if is_safety_system:
            # 确保 generator 是 SafetyHollysysGenerator 的实例，它有 generate_modbus_excel
            if not isinstance(generator, SafetyHollysysGenerator):
                 logger.error("逻辑错误: 尝试为安全系统生成Modbus表，但生成器不是SafetyHollysysGenerator实例。")
                 QMessageBox.critical(self, "内部错误", "尝试为安全系统生成Modbus表时发生配置错误。")
                 self.status_bar.showMessage("Modbus表生成失败：内部配置错误。")
                 return # 发生此错误则不继续

            logger.info("安全系统，继续生成Modbus点表...")
            try:
                base_output_dir_modbus = os.path.join(os.getcwd(), "PLC点表")
                target_plc_mfg_dir_modbus = os.path.join(base_output_dir_modbus, plc_manufacturer)
                os.makedirs(target_plc_mfg_dir_modbus, exist_ok=True)

                output_filename_modbus = f"{base_io_filename_cleaned}_和利时Modbus表.xls"
                save_path_modbus = os.path.join(target_plc_mfg_dir_modbus, output_filename_modbus)
                logger.info(f"和利时PLC安全型Modbus点表将保存到: {save_path_modbus}")

                success_modbus, error_message_modbus = generator.generate_modbus_excel(
                    points_by_sheet_dict=self.loaded_io_data_by_sheet, # 修改参数名
                    output_path=save_path_modbus
                )

                if success_modbus:
                    QMessageBox.information(self, "Modbus表生成成功", f"和利时PLC安全型Modbus点表已成功导出到:\n{save_path_modbus}")
                    self.status_bar.showMessage(f"和利时安全型Modbus表已生成: {output_filename_modbus}", 7000)
                else:
                    detailed_error_msg_modbus = error_message_modbus if error_message_modbus else "生成和利时PLC安全型Modbus点表失败。"
                    QMessageBox.critical(self, "Modbus表生成失败", detailed_error_msg_modbus)
                    logger.error(f"和利时安全型Modbus表生成失败: {detailed_error_msg_modbus}")
                    self.status_bar.showMessage("和利时安全型Modbus表生成失败。")

            except AttributeError as e_attr_modbus:
                logger.error(f"生成和利时PLC安全型Modbus点表时发生属性错误 (方法可能不存在): {e_attr_modbus}", exc_info=True)
                QMessageBox.critical(self, "Modbus表生成错误", f"尝试调用Modbus生成功能时出错 (可能方法未找到):\n{e_attr_modbus}")
                self.status_bar.showMessage("和利时安全型Modbus表生成时发生属性错误。")
            except Exception as e_modbus:
                logger.error(f"生成和利时PLC安全型Modbus点表时发生未知错误: {e_modbus}", exc_info=True)
                QMessageBox.critical(self, "Modbus表生成错误", f"生成和利时PLC安全型Modbus点表时发生未知错误:\n{e_modbus}")
                self.status_bar.showMessage("和利时安全型Modbus表生成时发生错误。")
        else:
            logger.info("非安全系统，不生成Modbus点表。和利时点表生成流程结束。")

    def _handle_hmi_generation_requested(self, hmi_type: str):
        """
        处理生成特定HMI类型点表的请求。
        HMI点表将保存到应用程序工作目录下的 "HMI点表/<HMI类型>" 子文件夹中。

        Args:
            hmi_type (str): 用户选择的HMI类型，如 "亚控", "力控"。
        """
        if not self.loaded_io_data_by_sheet:
            QMessageBox.warning(self, "未加载数据", "请先上传并成功加载IO点表数据，然后再生成HMI点表。")
            return

        # 从 self.loaded_io_data_by_sheet 中提取所有点位到一个列表中
        all_points: List[UploadedIOPoint] = []
        for sheet_name, points_in_sheet in self.loaded_io_data_by_sheet.items():
            all_points.extend(points_in_sheet)

        if not all_points:
            QMessageBox.warning(self, "无数据点", "加载的IO点表中未找到有效的数据点。")
            return

        # 获取文件名基础 (不含扩展名)
        base_file_name = os.path.splitext(os.path.basename(self.verified_io_table_path))[0] if self.verified_io_table_path else "HMI_Export"
        # default_dir = os.path.expanduser("~/Downloads") # 不再使用用户下载目录

        # 新增：定义固定的输出目录结构
        # 例如 D:\\project\\HMI点表\\亚控
        output_base_dir = os.path.join(os.getcwd(), "HMI点表")
        hmi_specific_output_dir = os.path.join(output_base_dir, hmi_type) # 特定HMI类型的子目录
        os.makedirs(hmi_specific_output_dir, exist_ok=True) # 确保目录存在
        logger.info(f"{hmi_type} HMI点表将保存到目录: {hmi_specific_output_dir}")

        logger.info(f"用户选择了HMI类型进行生成: {hmi_type}")
        self.status_bar.showMessage(f"准备生成 {hmi_type} HMI点表...")
        QApplication.processEvents() # 允许UI更新

        try:
            if hmi_type == "亚控":
                logger.info(f"准备根据已加载数据生成亚控HMI点表。")
                logger.info(f"来自 {len(self.loaded_io_data_by_sheet)} 个工作表的总共 {len(all_points)} 个点位将传递给生成器。")

                # KingViewGenerator.generate_kingview_files 的 output_dir 参数现在是目标文件夹
                # 文件名由生成器内部逻辑或 base_io_filename 决定，并会被保存到 output_dir
                success, ioserver_path, db_path, error_msg = KingViewGenerator().generate_kingview_files(
                    points_by_sheet=self.loaded_io_data_by_sheet,
                    output_dir=hmi_specific_output_dir, # 传递新的固定输出目录
                    base_io_filename=base_file_name
                )
                if success and ioserver_path and db_path:
                    QMessageBox.information(self, "生成成功",
                                            f"""亚控HMI点表已成功生成:
 - IO Server 点表: {os.path.basename(ioserver_path)}
 - 数据词典点表: {os.path.basename(db_path)}
文件已保存到目录: {hmi_specific_output_dir}""")
                    logger.info(f"""亚控HMI点表已成功生成:
 - IO Server 点表: {ioserver_path}
 - 数据词典点表: {db_path}""")
                    self.status_bar.showMessage(f"亚控HMI点表生成成功。")
                else:
                    err_to_show = error_msg if error_msg else "亚控HMI点表生成失败，未知原因。"
                    QMessageBox.critical(self, "生成失败", f"生成亚控HMI点表失败: {err_to_show}")
                    logger.error(f"亚控HMI点表生成失败: {err_to_show}")
                    self.status_bar.showMessage(f"亚控HMI点表生成失败。")

            elif hmi_type == "力控":
                logger.info(f"准备根据已加载数据生成力控HMI点表。")
                logger.info(f"来自 {len(self.loaded_io_data_by_sheet)} 个工作表的总共 {len(all_points)} 个点位将传递给生成器。")

                likong_gen = LikongGenerator()
                # 调用新的 generate_all_csvs 方法
                all_results = likong_gen.generate_all_csvs(
                    output_dir=hmi_specific_output_dir,
                    points_by_sheet=self.loaded_io_data_by_sheet
                )

                files_generated_successfully = []
                errors_occurred = []
                any_success = False

                for file_name, success, file_path, err_msg in all_results:
                    if success and file_path:
                        files_generated_successfully.append(f"{os.path.basename(file_path)}")
                        logger.info(f"力控HMI文件 '{os.path.basename(file_path)}' 已成功生成在: {hmi_specific_output_dir}")
                        any_success = True
                    else:
                        errors_occurred.append(f"生成 '{file_name}' 失败: {err_msg if err_msg else '未知错误'}")
                        logger.error(f"生成力控HMI文件 '{file_name}' 失败: {err_msg if err_msg else '未知错误'}")

                if any_success and not errors_occurred:
                    QMessageBox.information(self, "生成成功",
                                            f"""所有力控HMI相关文件已成功生成:
{', '.join(files_generated_successfully)}
已保存到目录: {hmi_specific_output_dir}""")
                    self.status_bar.showMessage(f"力控HMI点表生成成功。")
                elif any_success and errors_occurred:
                    QMessageBox.warning(self, "部分成功",
                                        f"""力控HMI点表生成部分成功:
成功: {', '.join(files_generated_successfully)}
失败: {'; '.join(errors_occurred)}
文件保存在: {hmi_specific_output_dir}""")
                    self.status_bar.showMessage(f"力控HMI点表部分生成成功。")
                else: # 全都失败
                    error_summary = "; ".join(errors_occurred) if errors_occurred else "未知原因导致所有文件生成失败。"
                    QMessageBox.critical(self, "生成失败", f"生成所有力控HMI点表文件失败: {error_summary}")
                    logger.error(f"生成所有力控HMI点表文件失败: {error_summary}")
                    self.status_bar.showMessage(f"力控HMI点表生成失败。")

            else:
                QMessageBox.warning(self, "类型不支持", f"暂不支持生成 {hmi_type} 类型的HMI点表。")
                logger.warning(f"请求生成不受支持的HMI类型: {hmi_type}")
                self.status_bar.showMessage(f"HMI点表生成失败: 类型不支持。")
                return

        except Exception as e:
            logger.error(f"生成 {hmi_type} HMI点表失败: {e}", exc_info=True)
            QMessageBox.critical(self, "生成失败", f"生成 {hmi_type} HMI点表时发生错误: {str(e)}")
            self.status_bar.showMessage(f"{hmi_type} HMI点表生成失败。")

    def get_current_devices(self) -> List[Dict[str, Any]]:
        """获取当前加载的设备数据，用于传递给其他对话框"""
        try:
            # 从设备列表区域获取当前加载的设备数据
            if hasattr(self, 'device_list_area') and self.device_list_area:
                # 获取表格中的数据
                devices_data = []
                table = self.device_list_area.device_table

                if table:
                    for row in range(table.rowCount()):
                        try:
                            # 从表格中提取设备信息（使用原始的_widget_*字段名）
                            device = {
                                'id': row + 1,  # 生成ID
                                '_widget_1635777115211': table.item(row, 0).text() if table.item(row, 0) else "",  # 设备名称
                                '_widget_1635777115248': table.item(row, 1).text() if table.item(row, 1) else "",  # 品牌
                                '_widget_1635777115287': table.item(row, 2).text() if table.item(row, 2) else "",  # 规格型号
                                '_widget_1641439264111': table.item(row, 3).text() if table.item(row, 3) else "",  # 技术参数
                                '_widget_1635777485580': table.item(row, 4).text() if table.item(row, 4) else "1",  # 数量
                                '_widget_1654703913698': table.item(row, 5).text() if table.item(row, 5) else "",  # 单位
                                '_widget_1641439463480': table.item(row, 6).text() if table.item(row, 6) else ""   # 技术参数(外部)
                            }

                            # 记录原始数据，方便调试
                            logger.debug(f"设备 #{row+1}:")
                            logger.debug(f"  名称: {device['_widget_1635777115211']}")
                            logger.debug(f"  品牌: {device['_widget_1635777115248']}")
                            logger.debug(f"  型号: {device['_widget_1635777115287']}")
                            logger.debug(f"  数量: {device['_widget_1635777485580']}")

                            # 根据数量创建多个设备实例
                            try:
                                quantity_str = device['_widget_1635777485580']
                                # 如果数量为空字符串或仅含空白，则默认为1；否则尝试转换为整数
                                quantity = int(quantity_str) if quantity_str and quantity_str.strip() else 1

                                if quantity <= 0: # 处理数量为0或负数的情况
                                    logger.warning(f"设备 #{row+1} 型号 {device['_widget_1635777115287']} 原始数量为 '{quantity_str}'，被修正为1个实例")
                                    quantity = 1

                                # 为所有设备（包括LK117）都根据其数量创建实例
                                for i in range(quantity):
                                    device_copy = device.copy()
                                    device_copy['instance_index'] = i + 1  # 实例索引
                                    # 特殊记录LK117或LK610S的创建，便于追踪
                                    model_upper = device_copy['_widget_1635777115287'].upper()
                                    if "LK117" in model_upper:
                                        logger.info(f"创建LK117实例 (源行: {row+1}, 型号: {device_copy['_widget_1635777115287']}, 解析数量: {quantity}, 当前实例号: {i+1}), devices_data已有 {len(devices_data)} 条")
                                    elif "LK610S" in model_upper:
                                        logger.info(f"创建LK610S实例 (源行: {row+1}, 型号: {device_copy['_widget_1635777115287']}, 解析数量: {quantity}, 当前实例号: {i+1}), devices_data已有 {len(devices_data)} 条")
                                    devices_data.append(device_copy)

                                # 避免为单个非LK117/非LK610S设备或数量为1的设备重复记录下面的debug日志
                                if not ("LK117" in device['_widget_1635777115287'].upper() or "LK610S" in device['_widget_1635777115287'].upper()) and quantity > 1:
                                    logger.debug(f"  已为设备 #{row+1} 型号 {device['_widget_1635777115287']} (原始数量: {quantity_str}) 创建 {quantity} 个实例")

                            except (ValueError, TypeError) as e_qty:
                                logger.warning(f"设备 #{row+1} 型号 {device['_widget_1635777115287']} 数量 '{device['_widget_1635777485580']}' 解析失败 ({e_qty})，默认为1个实例. devices_data已有 {len(devices_data)} 条")
                                device['instance_index'] = 1 # 确保原始device也有instance_index
                                devices_data.append(device) # 添加原始device作为单个实例

                        except Exception as row_e:
                            logger.warning(f"处理设备表格第 {row+1} 行数据时出错: {row_e}")
                            continue

                logger.info(f"获取到 {len(devices_data)} 个设备实例（考虑数量后）")
                return devices_data
            else:
                logger.warning("设备列表区域未初始化，无法获取设备数据")
                return []
        except Exception as e:
            logger.error(f"获取设备数据失败: {e}", exc_info=True)
            return []

    def _clear_loaded_io_data(self):
        """清除已加载的IO点表数据和相关状态。"""
        self.loaded_io_data_by_sheet = {}
        self.verified_io_table_path = None
        # 不需要再次选择 PLC 类型，因为这是针对生成特定PLC格式的点表，而不是原始IO模板
        # self.selected_plc_type_for_upload = None
        logger.info("已清空之前加载的IO点表数据和路径。")
        self.status_bar.showMessage("已清空IO点表数据。")
        # 通知QueryArea更新其状态显示
        if hasattr(self, 'query_area') and self.query_area: # 确保query_area已初始化
            self.query_area.update_io_table_status(None, 0)

    def _trigger_generate_points(self):
        """触发IO点表模板生成的辅助方法"""
        if not self.query_area or not hasattr(self.query_area, 'station_input'):
            QMessageBox.critical(self, "错误", "查询区域未正确初始化，无法获取场站编号。")
            return

        site_no = self.query_area.station_input.text().strip()
        if not site_no:
            QMessageBox.warning(self, "需要场站编号", "请在查询区域输入有效的场站编号后重试。")
            return

        # 新增：验证PLC硬件配置是否已完成
        logger.info(f"_trigger_generate_points: Checking PLC config. IODataLoader instance: {id(self.io_data_loader)}")
        if self.io_data_loader:
            logger.info(f"_trigger_generate_points: Current PLC config in IODataLoader: {self.io_data_loader.current_plc_config}")
        else:
            logger.warning("_trigger_generate_points: IODataLoader is None!")

        if not self.io_data_loader or not self.io_data_loader.current_plc_config:
            logger.warning("Attempted to generate IO template, but PLC configuration is empty or IODataLoader is missing.")
            QMessageBox.warning(self, "PLC配置缺失", "请先在<b>'PLC硬件配置'</b>选项卡中完成并应用模块配置，然后再生成IO点表模板。")
            return

        # 如果场站编号和PLC配置都有效，则继续
        self._handle_generate_points(site_no)

    def _is_safety_plc(self) -> bool:
        """
        检查当前加载的IO数据中是否包含安全PLC模块。

        Returns:
            bool: 如果检测到任何安全模块，则为True，否则为False。
        """
        if not self.loaded_io_data_by_sheet:
            logger.info("_is_safety_plc: No IO data loaded.")
            return False

        if not self.io_data_loader or not hasattr(self.io_data_loader, 'module_info_provider') or not self.io_data_loader.module_info_provider:
            logger.warning("_is_safety_plc: IODataLoader or ModuleInfoProvider is not available. Cannot determine if it's a safety PLC.")
            return False # 无法判断，按非安全处理

        try:
            for sheet_name, points_in_sheet in self.loaded_io_data_by_sheet.items():
                for point in points_in_sheet:
                    if point.module_name: # module_name 来自Excel的"模块名称"列
                        # 使用正确的 get_predefined_module_by_model 方法名
                        module_info = self.io_data_loader.module_info_provider.get_predefined_module_by_model(point.module_name)
                        if module_info and module_info.get('is_safety_module', False):
                            logger.info(f"_is_safety_plc: Safety module '{point.module_name}' detected. System is considered a safety PLC system.")
                            return True
            logger.info("_is_safety_plc: No safety modules detected.")
            return False
        except Exception as e:
            logger.error(f"_is_safety_plc: Error while checking for safety modules: {e}", exc_info=True)
            return False # 出错时，按非安全处理

    def _handle_generate_fat_table(self):
        """处理点击"生成FAT点表"按钮的事件。"""
        if not self.verified_io_table_path:
            QMessageBox.warning(self, "操作无效", "请先上传并验证IO点表文件。")
            logger.warning("FAT表生成尝试失败：未找到已验证的IO点表路径。")
            return

        # 从已验证的IO点表路径中提取文件名（不含扩展名）作为基础
        original_filename_stem = os.path.splitext(os.path.basename(self.verified_io_table_path))[0]

        # 构造FAT点检表的输出文件名，例如：原始文件名_FAT.xlsx
        fat_output_filename = f"{original_filename_stem}_FAT.xlsx"

        # 恢复固定的输出目录逻辑
        output_base_dir_name = "FAT点表" # 定义子目录名
        output_dir = os.path.join(os.getcwd(), output_base_dir_name) # 拼接完整路径
        try:
            os.makedirs(output_dir, exist_ok=True) # 确保目录存在
            logger.info(f"FAT点表将保存到固定目录: {output_dir}")
        except OSError as e:
            error_msg_mkdir = f"创建FAT点表输出目录 '{output_dir}' 失败: {e}"
            QMessageBox.critical(self, "目录创建错误", error_msg_mkdir)
            logger.error(error_msg_mkdir)
            self.status_bar.showMessage("FAT点表目录创建失败。", 5000)
            return

        self.status_bar.showMessage("正在生成FAT点表...")
        QApplication.processEvents() # 确保UI更新

        # 构造最终的完整输出路径
        final_output_path = os.path.join(output_dir, fat_output_filename)

        # 调用FAT生成函数
        try:
            logger.info(f"开始生成FAT点表，输入文件: {self.verified_io_table_path}, 输出文件: {final_output_path}")

            success, generated_file_path, error_message = generate_fat_checklist_from_source(
                original_file_path=self.verified_io_table_path,
                output_dir=output_dir,
                output_filename=fat_output_filename
            )

            if success and generated_file_path:
                QMessageBox.information(self, "生成成功", f"FAT点表已生成，文件路径：\n{generated_file_path}")
                self.status_bar.showMessage("FAT点表生成成功！", 5000)
                logger.info(f"FAT点表生成成功: {generated_file_path}")
            else:
                error_msg = error_message or "未知错误"
                QMessageBox.critical(self, "生成失败", f"生成FAT点表失败：\n{error_msg}")
                self.status_bar.showMessage("FAT点表生成失败。", 5000)
                logger.error(f"FAT点表生成失败: {error_msg}")

        except Exception as e:
            QMessageBox.critical(self, "生成失败", f"生成FAT点表时发生异常：\n{str(e)}")
            self.status_bar.showMessage("FAT点表生成异常。", 5000)
            logger.error(f"FAT点表生成异常: {e}", exc_info=True)

    def _handle_generate_communication_table(self):
        """处理点击"生成上下位通讯点表"按钮的事件。"""
        if not self.verified_io_table_path:
            QMessageBox.warning(self, "操作无效", "请先上传并验证IO点表文件。")
            logger.warning("上下位通讯点表生成尝试失败：未找到已验证的IO点表路径。")
            return

        # 从已验证的IO点表路径中提取文件名（不含扩展名）作为基础
        original_filename_stem = os.path.splitext(os.path.basename(self.verified_io_table_path))[0]

        # 构造上下位通讯点表的输出文件名，例如：原始文件名_上下位通讯点表.xlsx
        communication_output_filename = f"{original_filename_stem}_上下位通讯点表.xlsx"

        # 定义输出目录
        output_base_dir_name = "上下位通讯点表" # 定义子目录名
        output_dir = os.path.join(os.getcwd(), output_base_dir_name) # 拼接完整路径
        try:
            os.makedirs(output_dir, exist_ok=True) # 确保目录存在
            logger.info(f"上下位通讯点表将保存到固定目录: {output_dir}")
        except OSError as e:
            error_msg_mkdir = f"创建上下位通讯点表输出目录 '{output_dir}' 失败: {e}"
            QMessageBox.critical(self, "目录创建错误", error_msg_mkdir)
            logger.error(error_msg_mkdir)
            self.status_bar.showMessage("上下位通讯点表目录创建失败。", 5000)
            return

        self.status_bar.showMessage("正在生成上下位通讯点表...")
        QApplication.processEvents() # 确保UI更新

        # 构造最终的完整输出路径
        final_output_path = os.path.join(output_dir, communication_output_filename)

        # 调用生成表头的函数
        try:
            # Import necessary functions and types
            from core.post_upload_processor.communication_table_generator import generate_communication_table_excel
            from core.post_upload_processor.uploaded_file_processor.excel_reader import load_workbook_data
            from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint # Ensure this import is present or added if not already
            from typing import List # Ensure List is imported

            # 1. Load IO data from the verified Excel file
            points_by_sheet, error_message = load_workbook_data(self.verified_io_table_path)

            if error_message:
                QMessageBox.critical(self, "数据加载失败", f"加载IO点表数据时发生错误: {error_message}")
                logger.error(f"上下位通讯点表生成失败: 无法加载IO数据从 {self.verified_io_table_path} - {error_message}")
                self.status_bar.showMessage("上下位通讯点表生成失败: IO数据加载错误。", 5000)
                return

            # 2. Consolidate all points from all sheets into a single list
            all_points: List[UploadedIOPoint] = []
            if points_by_sheet:
                for sheet_name, points_in_sheet in points_by_sheet.items():
                    if points_in_sheet: # Ensure there are points in the sheet
                        all_points.extend(points_in_sheet)
                logger.info(f"为上下位通讯点表加载了 {len(all_points)} 个点位，来源: {list(points_by_sheet.keys())}")

            if not all_points:
                QMessageBox.warning(self, "无数据点", "从IO点表中未提取到有效数据点，无法生成上下位通讯点表。")
                logger.warning(f"上下位通讯点表生成失败: 从 {self.verified_io_table_path} 未提取到数据点。")
                self.status_bar.showMessage("上下位通讯点表生成失败: 无数据点。", 5000)
                return

            # 3. Call the generation function with the loaded io_points
            success = generate_communication_table_excel(final_output_path, all_points) # Pass all_points
            if success:
                QMessageBox.information(self, "生成成功", f"上下位通讯点表已生成，文件路径：\n{final_output_path}")
                self.status_bar.showMessage("上下位通讯点表生成成功！", 5000)
            else:
                QMessageBox.critical(self, "生成失败", "生成上下位通讯点表失败，请检查日志或联系开发者。")
                self.status_bar.showMessage("上下位通讯点表生成失败。", 5000)
        except Exception as e:
            QMessageBox.critical(self, "生成失败", f"生成上下位通讯点表时发生异常：{e}")
            self.status_bar.showMessage("上下位通讯点表生成异常。", 5000)

    def _handle_plc_config_reset(self):
        """
        处理PLC配置重置信号

        当用户点击重置配置按钮时，重新从API获取最新的设备数据
        """
        try:
            if not hasattr(self, 'current_site_name') or not self.current_site_name:
                logger.warning("没有当前场站，无法重新加载设备数据")
                QMessageBox.warning(self, "无当前场站", "没有选中的场站，无法重新加载数据")
                return

            site_name = self.current_site_name
            logger.info(f"处理PLC配置重置，重新加载场站 '{site_name}' 的设备数据")

            # 显示加载状态
            self.status_bar.showMessage(f"正在重新加载场站 '{site_name}' 的最新数据...")

            # 重新调用项目选择处理逻辑，这会触发API查询获取最新数据
            self._handle_project_selected(site_name)

            # 显示完成状态
            self.status_bar.showMessage(f"场站 '{site_name}' 的数据已重新加载", 3000)

            logger.info(f"PLC配置重置处理完成，场站 '{site_name}' 的数据已更新")

        except Exception as e:
            logger.error(f"处理PLC配置重置失败: {e}", exc_info=True)
            QMessageBox.critical(self, "重置处理失败", f"重新加载数据时发生错误：\n{str(e)}")
            self.status_bar.showMessage("数据重新加载失败")

    def _handle_document_import_completed(self, result_file_path: str):
        """
        处理文档导入完成信号

        Args:
            result_file_path (str): 生成的结果文件路径
        """
        logger.info(f"文档导入完成，生成文件: {result_file_path}")
        self.status_bar.showMessage(f"文档导入完成: {os.path.basename(result_file_path)}", 5000)

        # 可以在这里添加其他后续处理逻辑
        # 例如：更新其他组件状态、发送通知等

    def _handle_document_import_status_changed(self, status_message: str):
        """
        处理文档导入状态变化信号

        Args:
            status_message (str): 状态信息
        """
        self.status_bar.showMessage(status_message, 3000)
        logger.debug(f"文档导入状态更新: {status_message}")

    # 文档导入功能已整合到通道分配页面，无需单独的切换方法


