"""主窗口UI模块"""

import logging
from PySide6.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QDialog, QFileDialog
from typing import List, Dict, Any, Optional

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

        # 初始化当前场站名称
        self.current_site_name: Optional[str] = None

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
        logger.info("Attempting to generate IO table...")

        # 1. 暂时完全注释掉关于第三方设备点位的检查和提示
        # (这些检查现在由IOExcelExporter和后续的数据获取逻辑间接处理)

        # 2. 获取PLC IO点数据
        try:
            if not self.io_data_loader:
                logger.error("IODataLoader 未初始化，无法生成点表。")
                QMessageBox.warning(self, "错误", "IO数据加载服务未准备就绪。")
                return

            plc_io_points = self.io_data_loader.get_channel_addresses()
            
            # 3. 获取第三方设备点位数据并进行转换
            third_party_points_for_export: Optional[List[Dict[str, Any]]] = None
            if self.tp_config_service:
                try:
                    configured_tp_models = self.tp_config_service.get_all_configured_points()
                    if configured_tp_models:
                        logger.info(f"从ConfigService获取了 {len(configured_tp_models)} 个第三方配置点位模型。")
                        third_party_points_for_export = []
                        for tp_model in configured_tp_models:
                            # 将 ConfiguredDevicePointModel 转换为 IOExcelExporter 期望的字典格式
                            # IOExcelExporter的第三方表头占位符: 
                            # [\"点位名称\", \"地址/位号\", \"数据类型\", \"描述/备注\", \"所属设备\", \"功能位置\"]
                            point_dict = {
                                'template_name': tp_model.template_name,
                                # 尝试映射到 "点位名称" 或 "设备位号"
                                'point_name': tp_model.variable_name, # variable_name 是 device_prefix + var_suffix
                                # 尝试映射到 "地址/位号"
                                'address': tp_model.variable_name, # 暂时也用 variable_name 作为地址的占位
                                # 尝试映射到 "数据类型"
                                'data_type': tp_model.data_type,
                                # 尝试映射到 "描述/备注"
                                'description': tp_model.description, # description 是 device_prefix + desc_suffix
                                # 尝试映射到 "所属设备"
                                'device_name': tp_model.device_prefix,
                                # "功能位置" 在 ConfiguredDevicePointModel 中没有直接对应，暂时留空
                                'functional_location': '' 
                            }
                            third_party_points_for_export.append(point_dict)
                        logger.info(f"成功转换 {len(third_party_points_for_export)} 个第三方点位用于导出。")
                        # 在准备传递给Exporter前，打印转换后的列表内容
                        if third_party_points_for_export:
                            logger.info(f"转换后的第三方点位列表 (准备传递给Exporter): {third_party_points_for_export}")
                        else:
                            # 这理论上不应发生，因为上面已经检查了 configured_tp_models
                            logger.info("转换后的第三方点位列表为空。") 
                    else:
                        logger.info("ConfigService未返回任何第三方配置点位。")
                        third_party_points_for_export = None # 确保如果没有数据，则为None
                except Exception as e_tp_fetch:
                    logger.error(f"获取或转换第三方设备点位数据时出错: {e_tp_fetch}", exc_info=True)
                    QMessageBox.warning(self, "第三方数据错误", f"获取第三方设备点位数据失败: {str(e_tp_fetch)}")
                    # 根据需求决定是否在此处 return，或者允许仅导出PLC数据（如果存在）
                    # return # 如果获取第三方数据失败则不继续

            # 检查是否有数据可导出
            if not plc_io_points and not third_party_points_for_export:
                logger.info("没有已配置的PLC IO点或第三方设备点位可供导出。")
                QMessageBox.information(self, "提示", "没有可导出的IO点数据。")
                return

            log_message_parts = []
            if plc_io_points:
                log_message_parts.append(f"{len(plc_io_points)} 个PLC IO点")
            if third_party_points_for_export:
                log_message_parts.append(f"{len(third_party_points_for_export)} 个第三方设备点位")
            
            logger.info(f"准备导出: {', '.join(log_message_parts)}.")
            
            # 使用 QFileDialog 让用户选择保存路径和文件名
            # pylint: disable=line-too-long
            file_path, _ = QFileDialog.getSaveFileName(self, 
                                                       "保存IO点表", 
                                                       "IO_Table.xlsx", 
                                                       "Excel 文件 (*.xlsx);;所有文件 (*)")
            # pylint: enable=line-too-long

            if file_path:
                exporter = IOExcelExporter()
                success = exporter.export_to_excel(plc_io_data=plc_io_points, 
                                                   third_party_data=third_party_points_for_export,
                                                   filename=file_path,
                                                   site_name=self.current_site_name)
                if success:
                    QMessageBox.information(self, "成功", f"IO点表已成功导出到:\n{file_path}")
                else:
                    # IOExcelExporter 内部已经log了 openpyxl 未安装的错误
                    # 此处给一个通用失败消息
                    QMessageBox.warning(self, "导出失败", "IO点表导出失败。\n请检查日志获取详细信息。")
            else:
                logger.info("用户取消了文件保存操作。")

        except ImportError as e_import: # 主要捕获 openpyxl 的 ImportError
            logger.error(f"导出Excel所需的库缺失: {e_import}", exc_info=True)
            QMessageBox.critical(self, "依赖缺失", f"导出Excel功能需要 openpyxl 库。\n请通过 pip install openpyxl 安装它。\n错误详情: {e_import}")
        except Exception as e:
            logger.error(f"处理生成IO点表请求时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"生成IO点表失败: {str(e)}")

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

