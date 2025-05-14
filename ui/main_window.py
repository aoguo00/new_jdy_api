"""主窗口UI模块"""

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QDialog, QFileDialog, QStatusBar
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd # 确保导入 pandas
import os

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
from core.post_upload_processor.hmi_generators.yk_generator.generator import KingViewGenerator
from core.post_upload_processor.hmi_generators.lk_generator.generator import LikongGenerator # 新增：导入力控生成器

# Import new data processors
from core.project_list_area import ProjectService
from core.device_list_area import DeviceService

# UI Components
from ui.components.query_area import QueryArea
from ui.components.project_list_area import ProjectListArea
from ui.components.device_list_area import DeviceListArea
from ui.components.third_party_device_area import ThirdPartyDeviceArea

# Dialogs
from ui.dialogs.plc_config_dialog import PLCConfigDialog
from ui.dialogs.error_display_dialog import ErrorDisplayDialog
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

        # 初始化状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("准备就绪")

        # 初始化当前场站名称
        self.current_site_name: Optional[str] = None
        # 新增：用于存储已验证的IO点表路径和选择的PLC类型
        self.verified_io_table_path: Optional[str] = None
        self.selected_plc_type_for_upload: Optional[str] = None

        # 新增：用于存储从IO点表加载的已解析数据
        self.loaded_main_io_points: Optional[List[UploadedIOPoint]] = None
        self.loaded_third_party_data: Optional[List[Tuple[str, pd.DataFrame]]] = None

        # 初始化核心服务和管理器
        try:
            self.jdy_api = JianDaoYunAPI()
            # self.template_manager = TemplateManager() # Remove old one
            # self.config_service = DeviceConfigurationService() # Remove old one

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
        self.query_area.upload_io_table_requested.connect(self._handle_upload_io_table)
        self.query_area.upload_hmi_requested.connect(self._handle_hmi_generation_requested)
        self.query_area.upload_plc_requested.connect(self._handle_plc_generation_requested)
        # 移除模块管理信号连接
        # self.query_area.module_manage_requested.connect(self.show_module_manager)

        # 项目列表信号
        self.project_list_area.project_selected.connect(self._handle_project_selected)

    def _handle_query(self, project_no: str):
        """处理查询请求"""
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
        """处理清空请求"""
        self.query_area.clear_inputs()
        self.project_list_area.clear_table()
        self.device_list_area.clear_table()
        # Optionally, also clear third_party_area if desired, 
        # but it has its own clear button.
        # self.config_service.clear_all_configurations()
        # self.third_party_area.update_third_party_table()

    def _handle_generate_points(self, site_no: str):
        """处理生成空的IO点表模板的请求"""
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
            
            default_filename = "IO_点表_模板.xlsx"
            if self.current_site_name:
                safe_site_name = "".join(c if c.isalnum() or c in ['-', '_', ' '] else '_' for c in self.current_site_name.strip()).replace(' ', '_').strip('_')
                if safe_site_name: default_filename = f"{safe_site_name}_IO_点表_模板.xlsx"

            file_path, _ = QFileDialog.getSaveFileName(self, "保存IO点表模板", default_filename, "Excel 文件 (*.xlsx);;所有文件 (*)")

            if file_path:
                exporter = IOExcelExporter() # 这个Exporter主要用于生成模板
                success = exporter.export_to_excel(plc_io_data=plc_io_points, 
                                                   third_party_data=third_party_points_for_export,
                                                   filename=file_path,
                                                   site_name=self.current_site_name,
                                                   site_no=site_no) # site_no 从参数传入
                if success:
                    QMessageBox.information(self, "成功", f"IO点表模板已成功导出到:\n{file_path}")
                    self.status_bar.showMessage(f"IO点表模板已导出: {file_path}", 7000)
                else:
                    QMessageBox.warning(self, "导出失败", "IO点表模板导出失败。\n请检查日志获取详细信息。")
                    self.status_bar.showMessage("IO点表模板导出失败。")
            else:
                logger.info("用户取消了文件保存操作。")
                self.status_bar.showMessage("已取消导出IO点表模板。")

        except ImportError as e_import:
            logger.error(f"导出Excel模板所需的库缺失: {e_import}", exc_info=True)
            QMessageBox.critical(self, "依赖缺失", f"导出Excel功能需要 openpyxl 库。\n请通过 pip install openpyxl 安装它。\n错误详情: {e_import}")
        except Exception as e:
            logger.error(f"处理生成IO点表模板请求时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"生成IO点表模板失败: {str(e)}")
            self.status_bar.showMessage("生成IO点表模板失败。")

    def _handle_project_selected(self, site_name: str):
        """处理项目选择"""
        try:
            # 存储当前选择的场站名称
            self.current_site_name = site_name
            logger.info(f"当前选定的场站已更新为: {self.current_site_name}")

            # 执行查询 (调用 DeviceService)
            if not self.device_service:
                raise Exception("设备服务未初始化")
            all_devices = self.device_service.get_formatted_devices(site_name)
            
            # 更新设备列表
            self.device_list_area.update_device_list(all_devices)
            
        except Exception as e:
            logger.error(f"获取场站 '{site_name}' 的设备数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "数据加载错误", f"获取场站设备数据失败: {str(e)}")

    def _handle_upload_io_table(self):
        """处理上传IO点表请求，并加载数据到内存"""
        self._clear_loaded_io_data() # 先清除旧数据

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
            # 验证通过后，立即加载数据
            main_points, tp_data, error_msg_load = load_workbook_data(file_path)

            if error_msg_load:
                self._clear_loaded_io_data() # 加载时发生错误，清除状态
                logger.error(f"从 '{file_path}' 加载数据时返回错误: {error_msg_load}")
                QMessageBox.critical(self, "数据加载错误", f"加载IO点表数据时发生错误: {error_msg_load}")
                self.status_bar.showMessage(f"文件 '{file_name}' 数据加载失败。")
                return

            self.loaded_main_io_points = main_points
            self.loaded_third_party_data = tp_data
            self.verified_io_table_path = file_path # 仍然保存路径，可能用于显示或其他非核心逻辑

            loaded_msg_parts = []
            if self.loaded_main_io_points: loaded_msg_parts.append(f"{len(self.loaded_main_io_points)}个主IO点")
            if self.loaded_third_party_data: loaded_msg_parts.append(f"{len(self.loaded_third_party_data)}个第三方表")
            
            if not loaded_msg_parts:
                final_load_msg = f"文件 '{file_name}' 加载完成，但未解析到有效数据。"
                logger.warning(final_load_msg)
                QMessageBox.warning(self, "数据加载提示", final_load_msg)
            else:
                final_load_msg = f"文件 '{file_name}' 数据已加载: {', '.join(loaded_msg_parts)}。"
                logger.info(final_load_msg)

            self.status_bar.showMessage(final_load_msg + " 等待后续生成操作。", 10000)

        except Exception as e_load:
            self._clear_loaded_io_data() # 加载失败，清除所有相关状态
            logger.error(f"从 '{file_path}' 加载数据失败: {e_load}", exc_info=True)
            QMessageBox.critical(self, "数据加载错误", f"加载IO点表数据失败: {str(e_load)}")
            self.status_bar.showMessage(f"文件 '{file_name}' 数据加载失败。")

    def _handle_plc_generation_requested(self, plc_type: str):
        """处理用户选择的PLC点表生成请求（例如和利时、中控等）- 使用已加载数据"""
        logger.info(f"用户选择了PLC类型进行生成: {plc_type}")

        if not self.loaded_main_io_points and not self.loaded_third_party_data:
            QMessageBox.warning(self, "操作无效", "请先上传、验证并成功加载一个IO点表文件。")
            logger.warning("用户在未成功加载IO数据的情况下尝试生成PLC点表。")
            self.status_bar.showMessage("请先上传并加载IO点表")
            return

        # verified_io_table_path 应该在数据成功加载后被设置
        file_name_base_with_ext = os.path.basename(self.verified_io_table_path or "Uploaded_IO_Table.xlsx")
        base_io_filename, _ = os.path.splitext(file_name_base_with_ext)
        base_io_filename = base_io_filename.replace("_(已校验)", "").replace("(已校验)","")

        self.status_bar.showMessage(f"准备为已加载数据生成 '{plc_type}' PLC点表...")

        if plc_type == "和利时":
            logger.info(f"准备根据已加载数据生成和利时PLC点表。")
            try:
                output_dir = QFileDialog.getExistingDirectory(self, "选择保存和利时PLC点表的文件夹", ".")
                if not output_dir:
                    logger.info("用户取消选择输出目录。"); self.status_bar.showMessage("已取消生成和利时点表。"); return
                
                output_filename = f"{base_io_filename}_和利时点表.xls"
                save_path = os.path.join(output_dir, output_filename)

                generator = HollysysGenerator()
                # 使用已加载的数据
                success, error_message = generator.generate_hollysys_table(
                    main_io_points=self.loaded_main_io_points,
                    main_sheet_output_name="IO点表", # 或者您希望的任何名称
                    output_path=save_path,
                    third_party_data=self.loaded_third_party_data
                )
                if success:
                    QMessageBox.information(self, "成功", f"和利时PLC点表已成功导出到:\n{save_path}")
                    self.status_bar.showMessage(f"和利时点表已生成: {save_path}", 7000)
                else:
                    detailed_error_msg = error_message if error_message else "生成和利时PLC点表失败。"
                    QMessageBox.critical(self, "生成失败", detailed_error_msg)
                    logger.error(f"HollysysGenerator生成点表失败: {detailed_error_msg}")
                    self.status_bar.showMessage("和利时点表生成失败。")
            
            except Exception as e: #捕获任何在生成过程中可能发生的其他错误
                logger.error(f"生成和利时PLC点表时发生未知错误: {e}", exc_info=True)
                QMessageBox.critical(self, "生成错误", f"生成和利时PLC点表时发生未知错误:\n{e}")
                self.status_bar.showMessage("和利时点表生成失败 (未知错误)。")

        elif plc_type == "中控PLC":
            logger.info(f"准备根据已加载数据生成中控PLC点表。")
            QMessageBox.information(self, "功能待实现", f"已选择根据已加载数据生成 '{plc_type}' PLC点表。\n该功能正在开发中。")
        else:
            QMessageBox.warning(self, "类型不支持", f"目前不支持为PLC类型 '{plc_type}' 生成点表。")
            logger.warning(f"用户尝试为不支持的PLC类型 '{plc_type}' 生成点表。")
            self.status_bar.showMessage(f"不支持的PLC类型: {plc_type}")

    def _handle_hmi_generation_requested(self, hmi_type: str):
        """处理用户选择的HMI点表生成请求（例如亚控、力控等）- 使用已加载数据"""
        logger.info(f"用户选择了HMI类型进行生成: {hmi_type}")

        if not self.loaded_main_io_points and not self.loaded_third_party_data:
            QMessageBox.warning(self, "操作无效", "请先上传、验证并成功加载一个IO点表文件。")
            logger.warning("用户在未成功加载IO数据的情况下尝试生成HMI点表。")
            self.status_bar.showMessage("请先上传并加载IO点表")
            return

        # base_io_filename 的提取移到各自的生成逻辑内部，因为力控 Basic.xls 不需要它
        # file_name_base_with_ext = os.path.basename(self.verified_io_table_path or "Uploaded_IO_Table.xlsx")
        # base_io_filename, _ = os.path.splitext(file_name_base_with_ext)
        # base_io_filename = base_io_filename.replace("_(已校验)", "").replace("(已校验)","")
        
        self.status_bar.showMessage(f"准备为已加载数据生成 '{hmi_type}' HMI点表...")

        if hmi_type == "亚控":
            logger.info(f"准备根据已加载数据生成亚控HMI点表。")
            output_dir = QFileDialog.getExistingDirectory(self, f"选择保存亚控HMI点表的文件夹", ".")
            if not output_dir:
                logger.info("用户取消选择输出目录。")
                self.status_bar.showMessage("已取消生成亚控HMI点表。")
                return
            
            try:
                # base_io_filename 用于亚控生成器中构成最终文件名的一部分
                file_name_base_with_ext = os.path.basename(self.verified_io_table_path or "Uploaded_IO_Table.xlsx")
                base_io_filename, _ = os.path.splitext(file_name_base_with_ext)
                base_io_filename = base_io_filename.replace("_(已校验)", "").replace("(已校验)","")

                generator = KingViewGenerator()
                success, f1_path, f2_path, err_msg = generator.generate_kingview_files(
                    main_io_points=self.loaded_main_io_points,
                    third_party_sheet_data=self.loaded_third_party_data, 
                    output_dir=output_dir, 
                    base_io_filename=base_io_filename
                )

                if success:
                    msg = "亚控HMI点表已成功生成:"
                    if f1_path: msg += f"\n - IO Server 点表: {os.path.basename(f1_path)}"
                    if f2_path: msg += f"\n - 数据词典点表: {os.path.basename(f2_path)}"
                    QMessageBox.information(self, "成功", msg)
                    self.status_bar.showMessage("亚控HMI点表已生成。", 7000)
                    logger.info(msg)
                else:
                    detailed_error_msg = err_msg if err_msg else "生成亚控HMI点表失败。"
                    QMessageBox.critical(self, "生成失败", detailed_error_msg)
                    logger.error(f"KingViewGenerator生成亚控点表失败: {detailed_error_msg}")
                    self.status_bar.showMessage("亚控HMI点表生成失败。")
            
            except Exception as e:
                logger.error(f"生成亚控HMI点表时发生未知错误: {e}", exc_info=True)
                QMessageBox.critical(self, "生成错误", f"生成亚控HMI点表时发生未知错误:\n{e}")
                self.status_bar.showMessage("亚控HMI点表生成失败 (未知错误)。")

        elif hmi_type == "力控":
            logger.info(f"准备根据已加载数据生成力控HMI点表 (Basic.xls)。")
            output_dir = QFileDialog.getExistingDirectory(self, f"选择保存力控 Basic.xls 点表的文件夹", ".")
            if not output_dir:
                logger.info("用户取消选择输出目录。")
                self.status_bar.showMessage("已取消生成力控HMI点表。")
                return
            
            try:
                generator = LikongGenerator()
                success, file_path, err_msg = generator.generate_basic_xls(
                    output_dir=output_dir,
                    main_io_points=self.loaded_main_io_points,       # 传递主IO点数据
                    third_party_data=self.loaded_third_party_data  # 传递第三方数据
                )

                if success and file_path:
                    msg = f"力控点表 Basic.xls 已成功生成:\n{file_path}"
                    QMessageBox.information(self, "成功", msg)
                    self.status_bar.showMessage("力控 Basic.xls 点表已生成。", 7000)
                    logger.info(msg)
                else:
                    detailed_error_msg = err_msg if err_msg else "生成力控 Basic.xls 点表失败。"
                    QMessageBox.critical(self, "生成失败", detailed_error_msg)
                    logger.error(f"LikongGenerator生成 Basic.xls 点表失败: {detailed_error_msg}")
                    self.status_bar.showMessage("力控 Basic.xls 点表生成失败。")
            
            except Exception as e:
                logger.error(f"生成力控 Basic.xls 点表时发生未知错误: {e}", exc_info=True)
                QMessageBox.critical(self, "生成错误", f"生成力控 Basic.xls 点表时发生未知错误:\n{e}")
                self.status_bar.showMessage("力控 Basic.xls 点表生成失败 (未知错误)。")
        else:
            QMessageBox.warning(self, "类型不支持", f"目前不支持为HMI类型 '{hmi_type}' 生成点表。")
            logger.warning(f"用户尝试为不支持的HMI类型 '{hmi_type}' 生成点表。")
            self.status_bar.showMessage(f"不支持的HMI类型: {hmi_type}")

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
                                quantity = int(device['_widget_1635777485580'])
                                
                                # 检查是否是LK117背板（机架）
                                model = device['_widget_1635777115287'].upper()
                                if "LK117" in model:
                                    # 对于LK117背板，不创建多个实例，而是保留数量信息
                                    logger.info(f"检测到LK117背板，数量为{quantity}，作为机架信息保留")
                                    device['instance_index'] = 1
                                    devices_data.append(device)
                                else:
                                    # 为非背板设备创建多个实例
                                    for i in range(quantity):
                                        device_copy = device.copy()
                                        device_copy['instance_index'] = i + 1  # 实例索引，用于区分相同设备的不同实例
                                        devices_data.append(device_copy)
                                    logger.debug(f"  已为设备 #{row+1} 创建 {quantity} 个实例")
                            except (ValueError, TypeError):
                                # 数量解析失败，默认添加一个
                                logger.warning(f"设备 #{row+1} 数量无法解析: {device['_widget_1635777485580']}，默认为1")
                                device['instance_index'] = 1
                                devices_data.append(device)
                                
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

    def show_plc_config_dialog(self):
        """显示PLC配置对话框"""
        try:
            logger.info("正在打开PLC配置对话框...")
            
            if not self.io_data_loader:
                logger.error("MainWindow: IODataLoader 未初始化，无法打开PLC配置对话框。")
                QMessageBox.critical(self, "错误", "IO数据加载服务未准备就绪，无法配置PLC。")
                return

            current_devices = self.get_current_devices()
            if not current_devices:
                # logger.warning("没有获取到设备数据，请先查询并选择场站") # 这条日志在get_current_devices内部有了
                QMessageBox.information(self, "提示", "没有设备数据可用于PLC配置，请先查询并选择场站。")
                return
                
            logger.info(f"成功获取 {len(current_devices)} 个设备数据，准备传递给PLC配置对话框。")
                
            # 创建并显示对话框，传递 MainWindow 的 IODataLoader 实例和设备数据
            dialog = PLCConfigDialog(io_data_loader=self.io_data_loader, 
                                     devices_data=current_devices, 
                                     parent=self)
            
            result = dialog.exec()
            
            if result == QDialog.DialogCode.Accepted: # 检查对话框是否被接受
                logger.info("PLC配置对话框已确认并关闭。配置已通过共享的IODataLoader保存。")
                # 此处无需再调用 dialog.get_current_configuration() 或 io_data_loader.save_configuration()
                # 因为这些操作应该在 PLCConfigDialog.accept() 内部完成，并作用于共享的 io_data_loader 实例
            else:
                logger.info("PLC配置对话框已取消或关闭，未保存配置。")
                
        except Exception as e:
            logger.error(f"显示PLC配置对话框时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法显示PLC配置对话框: {str(e)}")

    def _clear_loaded_io_data(self):
        """清空已加载的IO数据和相关状态"""
        self.verified_io_table_path = None
        self.loaded_main_io_points = None
        self.loaded_third_party_data = None
        logger.info("已清空之前加载的IO点表数据和路径。")

