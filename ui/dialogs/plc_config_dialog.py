"""PLC配置对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
                           QTabWidget, QWidget, QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from typing import List, Dict, Any, Optional, Tuple
import logging

# 导入IODataLoader
from core.io_table import IODataLoader

logger = logging.getLogger(__name__)

class PLCConfigDialogUI:
    """
    负责 PLCConfigDialog 的用户界面 (UI) 的创建、布局和基本更新。
    这个类不包含业务逻辑或复杂的事件处理。
    """
    def __init__(self, widget: QWidget):
        """
        构造函数。

        Args:
            widget (QWidget): 将要承载这些UI元素的主QWidget实例。
        """
        self.widget = widget # 保存对主对话框的引用，以便在其上设置布局

        # --- UI元素定义 ---
        # 左侧面板元素
        self.type_combo: Optional[QComboBox] = None
        self.module_table: Optional[QTableWidget] = None
        
        # 中间操作按钮
        self.add_button: Optional[QPushButton] = None
        self.remove_button: Optional[QPushButton] = None
        
        # 右侧面板元素
        self.rack_combo: Optional[QComboBox] = None
        self.rack_tabs: Optional[QTabWidget] = None
        
        # 底部按钮
        self.ok_button: Optional[QPushButton] = None
        self.cancel_button: Optional[QPushButton] = None

        # 信息标签 (如果需要从UI类管理)
        # self.info_label: Optional[QLabel] = None 
        # 注意: info_label 在原代码中似乎没有被显式创建为self的属性，
        # 而是在 create_rack_tabs 中作为局部变量创建并添加到布局中。
        # 如果需要从外部更新，需要将其提升为 self.view.info_label。
        # 暂时不在这里创建，看主类如何处理。
        
    def setup_ui(self):
        """创建并布局所有UI元素。"""
        main_layout = QVBoxLayout(self.widget) # 在主对话框上设置主布局
        main_layout.setSpacing(10)
        
        # 模块配置区域 (上部主水平布局)
        module_config_area_layout = QHBoxLayout()
        module_config_area_layout.setSpacing(20)
        
        # --- 左侧：模块选择面板 ---
        left_panel_layout = QVBoxLayout()
        left_panel_layout.addWidget(QLabel("可用模块:"))
        
        type_filter_layout = QHBoxLayout()
        type_filter_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['全部', 'AI', 'AO', 'DI', 'DO', 'DP'])
        self.type_combo.setFixedWidth(100)
        type_filter_layout.addWidget(self.type_combo)
        type_filter_layout.addStretch()
        left_panel_layout.addLayout(type_filter_layout)
        
        self.module_table = QTableWidget()
        self.module_table.setColumnCount(5)
        self.module_table.setHorizontalHeaderLabels(['序号', '型号', '类型', '通道数', '描述'])
        self.module_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.module_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.module_table.verticalHeader().setVisible(False)
        header_left = self.module_table.horizontalHeader()
        header_left.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header_left.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header_left.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header_left.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header_left.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
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
        self.module_table.setAlternatingRowColors(True)
        left_panel_layout.addWidget(self.module_table)
        module_config_area_layout.addLayout(left_panel_layout)
        
        # --- 中间：操作按钮面板 ---
        middle_action_layout = QVBoxLayout()
        self.add_button = QPushButton("添加 →")
        self.remove_button = QPushButton("← 移除")
        self.add_button.setFixedWidth(100)
        self.remove_button.setFixedWidth(100)
        middle_action_layout.addStretch()
        middle_action_layout.addWidget(self.add_button)
        middle_action_layout.addWidget(self.remove_button)
        middle_action_layout.addStretch()
        module_config_area_layout.addLayout(middle_action_layout)
        
        # --- 右侧：已配置模块面板 ---
        right_panel_layout = QVBoxLayout()
        right_panel_layout.addWidget(QLabel("已配置模块:"))
        
        rack_selection_layout = QHBoxLayout()
        rack_selection_layout.addWidget(QLabel("机架:"))
        self.rack_combo = QComboBox()
        rack_selection_layout.addWidget(self.rack_combo)
        rack_selection_layout.addStretch()
        right_panel_layout.addLayout(rack_selection_layout)
        
        self.rack_tabs = QTabWidget()
        self.rack_tabs.setTabPosition(QTabWidget.TabPosition.North)
        right_panel_layout.addWidget(self.rack_tabs)
        module_config_area_layout.addLayout(right_panel_layout)
        
        module_config_area_layout.setStretch(0, 1) # 左侧面板比例
        module_config_area_layout.setStretch(2, 2) # 右侧面板比例
        
        main_layout.addLayout(module_config_area_layout)
        
        # --- 底部按钮面板 ---
        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.ok_button.setFixedWidth(80)
        self.cancel_button.setFixedWidth(80)
        bottom_button_layout.addWidget(self.ok_button)
        bottom_button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(bottom_button_layout)
        
        # self.dialog.setLayout(main_layout) # 主对话框的布局已在 QVBoxLayout(self.dialog) 中设置
        logger.info("PLCConfigDialogUI: UI elements created and layout set on the dialog.")

    def populate_module_table(self, modules: List[Dict[str, Any]]):
        """填充左侧的可用模块表格。"""
        if not self.module_table: return
        self.module_table.setRowCount(0)
        for index, module in enumerate(modules):
            row = self.module_table.rowCount()
            self.module_table.insertRow(row)
            module_model = module.get('model', module.get('_widget_1635777115287', ''))
            module_type = module.get('io_type', module.get('type', '未录入'))
            module_channels = str(module.get('channels', 0))
            main_desc = module.get('description', module.get('_widget_1641439264111', ''))
            ext_desc = module.get('ext_params', module.get('_widget_1641439463480', ''))
            module_desc = f"{main_desc}; {ext_desc}" if main_desc and ext_desc and ext_desc != main_desc else main_desc or ext_desc
            
            display_id = index + 1
            id_item = QTableWidgetItem(str(display_id))
            model_item = QTableWidgetItem(module_model)
            type_item = QTableWidgetItem(module_type)
            channels_item = QTableWidgetItem(module_channels)
            desc_item = QTableWidgetItem(module_desc)
            
            self.module_table.setItem(row, 0, id_item)
            self.module_table.setItem(row, 1, model_item)
            self.module_table.setItem(row, 2, type_item)
            self.module_table.setItem(row, 3, channels_item)
            self.module_table.setItem(row, 4, desc_item)
            
            if 'unique_id' in module:
                id_item.setData(Qt.ItemDataRole.UserRole, module['unique_id'])
        logger.debug(f"PLCConfigDialogUI: Module table populated with {len(modules)} items.")

    def show_no_data_in_module_table(self, message: str):
        """在左侧模块表格中显示无数据提示。"""
        if not self.module_table: return
        self.module_table.setRowCount(0)
        row = self.module_table.rowCount()
        self.module_table.insertRow(row)
        info_item = QTableWidgetItem(message)
        info_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.module_table.setSpan(row, 0, 1, 5)
        self.module_table.setItem(row, 0, info_item)
        logger.debug(f"PLCConfigDialogUI: Showing message in module table: {message}")

    def update_rack_combo(self, rack_count: int):
        """更新机架选择下拉框。"""
        if not self.rack_combo: return
        self.rack_combo.clear()
        if rack_count <= 0: rack_count = 1
        for i in range(rack_count):
            self.rack_combo.addItem(f"机架 {i+1}")
        logger.debug(f"PLCConfigDialogUI: Rack combo updated with {rack_count} racks.")

    def update_config_table_for_rack(self, rack_id: int, config_items: List[Dict[str, Any]], system_type: str):
        """更新指定机架选项卡中的配置表格。"""
        if not self.rack_tabs: return
        # rack_id 是从1开始的，tab_index 是从0开始的
        tab_index = rack_id - 1
        if tab_index < 0 or tab_index >= self.rack_tabs.count():
            logger.warning(f"PLCConfigDialogUI: Invalid rack_id {rack_id} for updating config table.")
            return
        
        rack_page_widget = self.rack_tabs.widget(tab_index)
        if not rack_page_widget:
            logger.warning(f"PLCConfigDialogUI: No widget found for rack tab {tab_index}.")
            return

        config_table = rack_page_widget.findChild(QTableWidget, f"rack_table_{rack_id}")
        if not config_table:
            logger.error(f"PLCConfigDialogUI: Config table 'rack_table_{rack_id}' not found in rack page {rack_id}.")
            return

        config_table.setRowCount(0)
        for item_data in config_items: # item_data is like {'slot_id', 'model', 'type', 'channels', 'description'}
            slot_id = item_data['slot_id']
            model = item_data['model']
            module_type = item_data.get('type', '未知')
            channels = str(item_data.get('channels', 0))
            description = item_data.get('description', '')

            row = config_table.rowCount()
            config_table.insertRow(row)
            config_table.setItem(row, 0, QTableWidgetItem(str(slot_id)))
            config_table.setItem(row, 1, QTableWidgetItem(model))
            config_table.setItem(row, 2, QTableWidgetItem(module_type))
            config_table.setItem(row, 3, QTableWidgetItem(channels))
            config_table.setItem(row, 4, QTableWidgetItem(description))

            if slot_id == 1:
                color = Qt.GlobalColor.lightGray
                for col in range(config_table.columnCount()):
                    table_item = config_table.item(row, col)
                    if table_item: table_item.setBackground(color)
        logger.debug(f"PLCConfigDialogUI: Config table for rack {rack_id} updated.")

    def create_rack_tab_page(self, rack_id: int, slots_per_rack: int, system_type: str) -> QWidget:
        """为单个机架创建一个新的选项卡页面和其中的配置表格。"""
        rack_page = QWidget()
        rack_layout = QVBoxLayout(rack_page)
        
        info_text = f"机架 {rack_id} (槽位1-{slots_per_rack})"
        if system_type == "LK":
            info_text = f"机架 {rack_id} (LK系统: 槽位1固定为DP模块, 可配置槽位2-{slots_per_rack})"
        elif system_type == "LE_CPU":
            info_text = f"机架 {rack_id} (LE系统: 槽位1请配置LE5118 CPU, 可配置槽位2-{slots_per_rack})"
        
        info_label = QLabel(info_text)
        rack_layout.addWidget(info_label)

        config_table = QTableWidget()
        config_table.setObjectName(f"rack_table_{rack_id}") # 重要：用于后续查找
        config_table.setColumnCount(5)
        config_table.setHorizontalHeaderLabels(['槽位', '型号', '类型', '通道数', '描述'])
        config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        config_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        config_table.verticalHeader().setVisible(False)
        header = config_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) 
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        if self.module_table: # 复用左侧表格的样式表
             config_table.setStyleSheet(self.module_table.styleSheet())
        config_table.setAlternatingRowColors(True)
        
        rack_layout.addWidget(config_table)
        
        return rack_page

    def clear_rack_tabs(self):
        """清除所有机架选项卡。"""
        if self.rack_tabs:
            self.rack_tabs.clear()
            logger.debug("PLCConfigDialogUI: All rack tabs cleared.")

    def add_rack_tab(self, page_widget: QWidget, tab_name: str):
        """添加一个新的机架选项卡。"""
        if self.rack_tabs:
            self.rack_tabs.addTab(page_widget, tab_name)
            logger.debug(f"PLCConfigDialogUI: Rack tab '{tab_name}' added.")
    
    def set_current_rack_tab(self, index: int):
        """设置当前显示的机架选项卡。"""
        if self.rack_tabs and 0 <= index < self.rack_tabs.count():
            self.rack_tabs.setCurrentIndex(index)

    def set_current_rack_combo(self, index: int):
        """设置机架下拉框的当前选项。"""
        if self.rack_combo and 0 <= index < self.rack_combo.count():
            self.rack_combo.setCurrentIndex(index)

class PLCConfigEmbeddedWidget(QWidget):
    """PLC配置嵌入式Widget - 支持多机架布局及不同系统类型（LK, LE_CPU）"""
    # 定义一个信号，当配置应用时发出
    # configuration_applied = Signal(bool) # True for success, False for failure

    def __init__(self, io_data_loader: IODataLoader, devices_data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(1000, 600)

        if not io_data_loader:
            logger.error("PLCConfigEmbeddedWidget 初始化错误: IODataLoader 实例未提供。")
            # 在UI上显示错误信息
            error_label = QLabel("错误：IO数据服务不可用，PLC配置功能无法加载。")
            error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            error_label.setStyleSheet("color: red; font-weight: bold;")
            main_layout = QVBoxLayout(self)
            main_layout.addWidget(error_label)
            self.io_data_loader = None # 标记为None，其他方法需要检查
            self.view = None # 视图也无法初始化
            return # 提前返回，不进行后续初始化
        
        self.io_data_loader = io_data_loader
        self.view = PLCConfigDialogUI(self) # UI部分
        self.view.setup_ui()

        # 修改按钮文本和可见性
        if self.view.ok_button:
            self.view.ok_button.setText("应用配置")
        if self.view.cancel_button:
            self.view.cancel_button.setVisible(False) # 通常嵌入式Widget不需要取消按钮

        # --- 状态变量初始化为默认/空状态 ---
        self.current_config: Dict[Tuple[int, int], str] = {} 
        self.all_available_modules: List[Dict[str, Any]] = [] 
        self.current_modules_pool: List[Dict[str, Any]] = [] 
        self.configured_modules: Dict[Tuple[int, int], Dict[str, Any]] = {} 
        
        self.module_type_filter: str = '全部' 
        self.next_module_id_counter: int = 1 
        
        self.system_type: str = "LK" # 默认系统类型
        self.rack_info: Dict[str, Any] = {'rack_count': 0, 'slots_per_rack': 0} # 默认空机架信息

        self.setup_connections() # 连接信号和槽

        if devices_data is not None: 
            logger.info("PLCConfigEmbeddedWidget __init__: 传入了初始设备数据，将调用 set_devices_data 进行处理...")
            self.set_devices_data(devices_data) # 这会处理所有数据加载和UI填充
        else:
            logger.info("PLCConfigEmbeddedWidget __init__: 未传入初始设备数据。Widget将以空状态初始化。")
            # 初始化UI到空/默认状态
            if self.view and self.view.module_table:
                self.view.show_no_data_in_module_table("请先选择一个项目/场站")
            
            # rack_info 当前是空的，create_rack_tabs 会据此创建UI
            # (通常是1个默认的空机架tab)
            self.create_rack_tabs() 
            self.update_all_config_tables() # 更新右侧配置表以反映空状态
            
            # 确保 module_type_filter 与UI一致
            if self.view and self.view.type_combo:
                 self.module_type_filter = self.view.type_combo.currentText()

    def _ensure_module_unique_id(self, module: Dict[str, Any]) -> None:
        """确保模块字典有一个 'unique_id'，如果没有则生成一个。"""
        if 'unique_id' not in module or module['unique_id'] is None:
            module['unique_id'] = f"mod_{self.next_module_id_counter}"
            self.next_module_id_counter += 1
            
    def _load_all_available_modules_with_unique_ids(self, module_type_filter: str = '全部') -> None:
        """
        从 IODataLoader 加载指定类型的可用模块，确保每个模块都有 unique_id，
        并更新 self.all_available_modules。
        这个方法现在是填充 self.all_available_modules 的主要途径。
        """
        logger.debug(f"_load_all_available_modules_with_unique_ids called with filter: {module_type_filter}")
        # 注意：io_data_loader.load_available_modules 现在只用于获取原始列表，
        # unique_id 的赋予和 self.all_available_modules 的填充在此处完成。
        raw_modules_from_loader, _ = self.io_data_loader.load_available_modules(module_type_filter) # 使用UI的过滤器
        
        temp_all_modules = []
        for module in raw_modules_from_loader:
            m_copy = module.copy()
            self._ensure_module_unique_id(m_copy) # 确保 unique_id
            temp_all_modules.append(m_copy)
        
        self.all_available_modules = temp_all_modules
        logger.info(f"self.all_available_modules re-populated with {len(self.all_available_modules)} modules (filter: {module_type_filter}).")

    def _rebuild_current_modules_pool(self) -> None:
        """
        根据 self.all_available_modules 和 self.configured_modules 重新计算
        self.current_modules_pool (左侧穿梭框应显示的模块)。
        """
        configured_unique_ids = {
            mod.get('unique_id') for mod in self.configured_modules.values() if mod and mod.get('unique_id') is not None
        }
        
        # self.all_available_modules 此刻应该已经根据UI的类型过滤器刷新过了
        # 如果没有，这里的过滤可能不完整。但 load_modules 方法处理了类型过滤问题。
        # 实际上，all_available_modules 应该总是包含所有类型的模块（由 _load_all_available_modules_with_unique_ids('全部') 填充）
        # 而类型过滤是在准备显示给UI时（populate_module_table之前）再应用。

        # 我们假设 self.all_available_modules 是完整的未经过类型过滤的池
        # 然后，基于当前的 self.module_type_filter，从 self.all_available_modules 构建 current_modules_pool

        filtered_by_type_pool = []
        if self.module_type_filter == '全部':
            filtered_by_type_pool = self.all_available_modules[:] # 副本
        else:
            for module in self.all_available_modules:
                # 使用模块字典中已有的 'type' 或 'io_type'
                module_actual_type = module.get('type', module.get('io_type', ''))
                if module_actual_type == self.module_type_filter:
                    filtered_by_type_pool.append(module)
        
        self.current_modules_pool = [
            m for m in filtered_by_type_pool if m.get('unique_id') not in configured_unique_ids
        ]
        logger.info(f"_rebuild_current_modules_pool: Rebuilt pool with {len(self.current_modules_pool)} modules for type '{self.module_type_filter}'.")

    def _initialize_dialog_state(self):
        """根据 io_data_loader 初始化配置状态 (current_config, configured_modules, system_type, rack_info)。"""
        if not self.io_data_loader:
            logger.warning("_initialize_dialog_state: io_data_loader is None.")
            self.system_type = "LK"; self.rack_info = {}; self.current_config = {}; self.configured_modules = {}
            return

        loaded_plc_config = self.io_data_loader.get_current_plc_config()
        self.current_config = loaded_plc_config.copy() if loaded_plc_config else {}
        
        self.configured_modules = {}
        for (r_id, s_id), model_name in self.current_config.items():
            # 从 self.all_available_modules (应已填充并含unique_id) 中查找模块详情
            # 这是为了确保 configured_modules 中的模块对象与 all_available_modules 中的是"相同"的（具有相同的unique_id和属性）
            found_module_detail = next((m.copy() for m in self.all_available_modules if m.get('model') == model_name), None)
            
            if found_module_detail:
                # self._ensure_module_unique_id(found_module_detail) # all_available_modules 中的应该已经有了
                self.configured_modules[(r_id, s_id)] = found_module_detail
            else:
                # 如果在 all_available_modules 中找不到 (理论上不应该，除非 all_available_modules 未正确加载所有可能的模块)
                # 则回退到直接从 io_data_loader 获取，并确保 unique_id
                logger.warning(f"Module {model_name} for config ({r_id},{s_id}) not found in preloaded all_available_modules. Fetching from loader.")
                module_detail_from_loader = self.io_data_loader.get_module_by_model(model_name)
                if module_detail_from_loader:
                    m_copy = module_detail_from_loader.copy()
                    self._ensure_module_unique_id(m_copy)
                    self.configured_modules[(r_id, s_id)] = m_copy
                else:
                    logger.error(f"CRITICAL: Cannot find details for configured module {model_name} at ({r_id},{s_id}) from any source.")
                    # 放入一个占位符，以避免后续代码出错，但标记问题
                    self.configured_modules[(r_id, s_id)] = {'model': model_name, 'type': '未知_ERROR', 'unique_id': f"error_{r_id}_{s_id}"}


        rack_info_from_loader = self.io_data_loader.get_rack_info()
        self.system_type = rack_info_from_loader.get('system_type', "LK")
        self.rack_info = rack_info_from_loader
        logger.info(f"PLCConfigEmbeddedWidget state initialized: System type '{self.system_type}', {len(self.current_config)} configured items.")
        
    def set_devices_data(self, devices_data: List[Dict[str, Any]]):
        if not self.io_data_loader:
            logger.error("PLCConfigEmbeddedWidget.set_devices_data: IODataLoader is not initialized.")
            return

        logger.info(f"set_devices_data called with {len(devices_data)} devices.")
        self.next_module_id_counter = 1 # 重置 unique_id 计数器
        
        self.io_data_loader.set_devices_data(devices_data) # Loader 更新其内部状态 (包括 system_type, rack_info)
        
        # 1. 基于新的设备数据（可能影响了io_data_loader中可用模块的来源）重新加载完整的模块池
        self._load_all_available_modules_with_unique_ids('全部') # 总是加载所有类型以填充 all_available_modules

        # 2. 同步配置状态 (current_config, configured_modules)
        self._initialize_dialog_state() 
        
        # 3. 根据当前的UI过滤器和已配置模块，重建左侧穿梭框的内容
        #    load_modules 方法现在负责这个
        self.load_modules() # 这会使用当前的 self.module_type_filter

        # 4. 更新UI的静态和动态部分
        self.create_rack_tabs() 
        self.update_all_config_tables() 

        logger.info(f"set_devices_data completed. UI refreshed. System type: {self.system_type}, Racks: {self.view.rack_tabs.count() if self.view.rack_tabs else 'N/A'}")

    def load_modules(self):
        """
        加载模块到左侧穿梭框。
        它会读取当前的UI类型过滤器，然后调用 _rebuild_current_modules_pool 来准备数据，
        最后更新UI表格。
        前提: 
        - self.all_available_modules 已被 _load_all_available_modules_with_unique_ids('全部') 正确填充。
        - self.configured_modules 已被 _initialize_dialog_state 或 add/remove 操作正确更新。
        """
        try:
            if not self.view.module_table or not self.view.type_combo:
                logger.warning("load_modules: UI elements (module_table or type_combo) not ready.")
                return

            # 如果没有有效的机架信息（通常意味着没有加载项目数据），则不加载模块
            if self.rack_info.get('rack_count', 0) == 0 and not self.configured_modules: # 增加条件：也没有已配置模块
                logger.info("load_modules: No rack data or configured modules, showing 'select project' message.")
                self.view.show_no_data_in_module_table("请先选择一个项目并加载设备数据")
                self.current_modules_pool = [] # 确保池是空的
                return

            # 1. 获取UI当前的类型过滤器，并更新 self.module_type_filter
            self.module_type_filter = self.view.type_combo.currentText() if self.view.type_combo else '全部'
            logger.debug(f"load_modules called. Current UI filter: '{self.module_type_filter}'")

            # 步骤1: 确保 self.all_available_modules 是最新的（基于当前 io_data_loader 状态）
            # 并且包含所有类型的模块，unique_id已处理。
            # 注意：_load_all_available_modules_with_unique_ids 内部现在也接受一个过滤器，
            # 但为了保持 all_available_modules 的完整性，我们可能应该总是加载'全部'，
            # 然后在 _rebuild_current_modules_pool 中应用 self.module_type_filter。
            # 或者，_load_all_available_modules_with_unique_ids 直接使用 self.module_type_filter。
            # 为了简化，我们假设 _load_all_available_modules_with_unique_ids 已经填充了基于'全部'类型的模块池。
            # 如果不是，这里需要先调用 _load_all_available_modules_with_unique_ids('全部')
            if not self.all_available_modules: # 仅在非常初次或被清空时
                 self._load_all_available_modules_with_unique_ids('全部')


            # 步骤2: 根据已配置模块和当前UI的类型过滤器，重建 current_modules_pool
            self._rebuild_current_modules_pool()
            
            # 步骤3: 更新UI表格
            if self.current_modules_pool:
                self.view.populate_module_table(self.current_modules_pool)
            else:
                self.view.show_no_data_in_module_table(f"无匹配 '{self.module_type_filter}' 类型模块或已全部配置")
            
            logger.info(f"load_modules: Displaying {len(self.current_modules_pool)} modules in UI for filter '{self.module_type_filter}'.")
            
        except Exception as e:
            logger.error(f"加载模块数据失败 (load_modules): {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载模块数据失败: {str(e)}")

    def add_module(self):
        if not self.view.module_table or not self.view.rack_tabs: return

        selected_rows = self.view.module_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要添加的模块"); return
        
        row = selected_rows[0].row()
        if self.view.module_table.rowSpan(row, 0) > 1: 
            QMessageBox.warning(self, "提示", "无可用模块数据"); return

        module_unique_id_from_table = self.view.module_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        selected_module_obj = next((m.copy() for m in self.current_modules_pool if m.get('unique_id') == module_unique_id_from_table), None)
        
        if not selected_module_obj:
            model_text = self.view.module_table.item(row, 1).text() if self.view.module_table.item(row, 1) else "N/A"
            logger.error(f"Cannot find module with unique_id {module_unique_id_from_table} (model: {model_text}) in current_modules_pool.")
            QMessageBox.warning(self, "错误", "无法找到所选模块的内部数据，请刷新或检查日志。")
            return
            
        model = selected_module_obj['model']
        module_type = selected_module_obj.get('type', selected_module_obj.get('io_type', '未录入'))
        
        current_rack_id = self.view.rack_tabs.currentIndex() + 1
        # ... (rest of add_module logic for placement validation) ...
        # ... ensure self.io_data_loader.validate_module_placement is called ...
        validation_result = self.io_data_loader.validate_module_placement(current_rack_id, -1, model) # Placeholder slot_id for now

        # Simplified placement logic for this example, actual slot finding is complex
        assigned_slot_id = None
        slots_per_rack = self.rack_info.get('slots_per_rack', 11)
        start_slot = 2 if self.system_type == "LK" else 1
        if self.system_type == "LE_CPU" and module_type == "CPU": start_slot = 1 # CPU must be in slot 1 for LE

        for slot_id_candidate in range(start_slot, slots_per_rack + 1):
            if self.system_type == "LE_CPU" and module_type == "CPU" and slot_id_candidate != 1: continue # CPU only in slot 1
            if self.system_type == "LK" and slot_id_candidate == 1 and module_type != "DP": continue # Slot 1 for DP in LK
            if self.system_type == "LK" and module_type == "DP" and slot_id_candidate != 1: continue # DP only in slot 1 for LK

            temp_validation = self.io_data_loader.validate_module_placement(current_rack_id, slot_id_candidate, model)
            if temp_validation['valid'] and (current_rack_id, slot_id_candidate) not in self.current_config:
                assigned_slot_id = slot_id_candidate
                break
        
        if assigned_slot_id is None:
            QMessageBox.warning(self, "提示", f"机架 {current_rack_id} 没有可用的有效槽位放置模块 {model}")
            return

        self.current_config[(current_rack_id, assigned_slot_id)] = model
        self.configured_modules[(current_rack_id, assigned_slot_id)] = selected_module_obj # Store the object with unique_id
        
        logger.info(f"Module {model} ({module_unique_id_from_table}) added to rack {current_rack_id}, slot {assigned_slot_id}.")

        # Refresh pools and UI
        self._rebuild_current_modules_pool()
        self.view.populate_module_table(self.current_modules_pool)
        self.update_current_config_table()

    def remove_module(self):
        if not self.view.rack_tabs: return
        current_rack_id = self.view.rack_tabs.currentIndex() + 1
        rack_page_widget = self.view.rack_tabs.currentWidget()
        if not rack_page_widget: return
        config_table = rack_page_widget.findChild(QTableWidget, f"rack_table_{current_rack_id}")
        if not config_table: return
        
        selected_rows = config_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移除的模块"); return
        
        row = selected_rows[0].row()
        slot_text_item = config_table.item(row, 0)
        model_text_item = config_table.item(row, 1) # For logging/finding unique_id
        if not slot_text_item or not slot_text_item.text().isdigit() or not model_text_item: return
        
        slot_id = int(slot_text_item.text())
        # model_name_in_table = model_text_item.text() # Not directly used to find, use configured_modules

        # ... (LK slot 1 check remains) ...
        if self.system_type == "LK" and slot_id == 1:
             QMessageBox.warning(self, "提示", "LK系统槽位1的DP模块是预设的，不能移除。")
             return
        
        module_to_remove_key = (current_rack_id, slot_id)
        removed_module_obj = self.configured_modules.pop(module_to_remove_key, None)
        if removed_module_obj:
            del self.current_config[module_to_remove_key]
            logger.info(f"Module {removed_module_obj.get('model')} (unique_id: {removed_module_obj.get('unique_id')}) removed from config.")
            # No need to explicitly add back to self.current_modules_pool here,
            # _rebuild_current_modules_pool will correctly include it when called.
        else:
            logger.warning(f"Attempted to remove module from ({current_rack_id},{slot_id}), but it was not found in configured_modules.")
            # Fallback: try to remove from current_config if it's somehow there without being in configured_modules
            if module_to_remove_key in self.current_config:
                del self.current_config[module_to_remove_key]


        # Refresh pools and UI
        self._rebuild_current_modules_pool()
        self.view.populate_module_table(self.current_modules_pool)
        self.update_current_config_table()

    def create_rack_tabs(self):
        """创建机架选项卡界面，根据系统类型调整槽位1的说明"""
        if not self.io_data_loader or not self.view.rack_tabs or not self.view.rack_combo:
            logger.warning("create_rack_tabs: UI elements or io_data_loader not ready.")
            return

        self.view.clear_rack_tabs()
        self.view.update_rack_combo(0) # 先清空并用0更新组合框
        
        # self.rack_info 应该在 _initialize_dialog_state 中被填充
        rack_count = self.rack_info.get('rack_count', 0)
        slots_per_rack = self.rack_info.get('slots_per_rack', 11) # 默认11
        
        logger.info(f"Creating rack tabs: System type='{self.system_type}', Rack count={rack_count}, Slots/Rack={slots_per_rack}")
        
        # 先断开旧的信号连接，防止重复连接或连接到旧的tab实例
        try:
            self.view.rack_tabs.currentChanged.disconnect(self.on_rack_tab_changed)
        except RuntimeError: # 'disconnect' may raise RuntimeError if not connected
            pass
        try:
            self.view.rack_combo.currentIndexChanged.disconnect(self.on_rack_combo_changed)
        except RuntimeError:
            pass

        actual_rack_count_for_combo = rack_count # 初始化 actual_rack_count_for_combo

        if rack_count == 0:
            logger.info("create_rack_tabs: rack_count is 0. No rack tabs will be created. Displaying placeholder.")
            # 可选：在右侧面板显示一个提示，如果PLCConfigDialogUI支持
            # self.view.show_no_rack_data_message("无PLC机架配置信息，请选择项目。")
            # 确保 rack_combo 也反映无机架状态
            self.view.update_rack_combo(0) # 传递0，UI类内部可能显示 "无机架" 或禁用
            actual_rack_count_for_combo = 0 # 当 rack_count 为 0 时，也更新它
            # 清除可能存在的旧的右侧表格双击连接 (虽然 clear_rack_tabs 应该处理了tab widget)
            # _initialize_slot1_for_lk_system_if_needed 不应被调用
            # update_all_config_tables 也不应尝试更新不存在的表
        else:
            # actual_rack_count_for_combo = rack_count # 这行现在移到前面了
            pass # 如果 rack_count > 0, actual_rack_count_for_combo 已被正确设置为 rack_count

        # 只有当 rack_count 大于 0 时，才用 actual_rack_count_for_combo 更新，因为等于0时上面已经用0更新了
        if rack_count > 0:
            self.view.update_rack_combo(actual_rack_count_for_combo)
        
        display_rack_count = rack_count

        for i in range(1, display_rack_count + 1):
            rack_id_iter = i
            page_widget = self.view.create_rack_tab_page(rack_id_iter, slots_per_rack, self.system_type)
            self.view.add_rack_tab(page_widget, f"机架 {rack_id_iter}")

            # 查找 config_table_in_page 和连接信号的部分也移到循环内
            config_table_in_page = page_widget.findChild(QTableWidget, f"rack_table_{rack_id_iter}")
            if config_table_in_page:
                try: # 先尝试断开，以防万一在重建tab时旧连接残留
                    config_table_in_page.itemDoubleClicked.disconnect(self._handle_right_table_double_click)
                except RuntimeError: pass # 如果未连接，则忽略错误
                config_table_in_page.itemDoubleClicked.connect(self._handle_right_table_double_click)
                logger.debug(f"Connected itemDoubleClicked for rack {rack_id_iter}'s config table.")
            else:
                logger.warning(f"Config table not found in new tab page for rack {rack_id_iter}.")
            
        # LK系统预设DP模块 (这部分逻辑保持在循环外部，因为它会迭代所有已创建的机架)
        # 但它依赖于 self.rack_info.get('rack_count', 0) > 0
        # _initialize_slot1_for_lk_system_if_needed 内部有自己的 rack_count 检查，所以这里可以简化
        if self.system_type == "LK" and rack_count > 0: # 显式检查 rack_count > 0
            self._initialize_slot1_for_lk_system_if_needed()
        
        # 重新连接 rack_tabs 和 rack_combo 的信号 (仅当有tab时)
        if self.view.rack_tabs and self.view.rack_tabs.count() > 0: 
            self.view.rack_tabs.currentChanged.connect(self.on_rack_tab_changed)
        if self.view.rack_combo: # rack_combo 也只在有 rack 时才有意义
            self.view.rack_combo.currentIndexChanged.connect(self.on_rack_combo_changed)
            
        logger.info(f"Rack tabs creation/update complete. Total tabs: {self.view.rack_tabs.count() if self.view.rack_tabs else 0}. System: '{self.system_type}'.")

    def _initialize_slot1_for_lk_system_if_needed(self):
        """
        如果当前是LK系统，则为每个机架的槽位1预设DP模块。
        这应该在 self.current_config 和 self.configured_modules 初始化之后，
        但在UI完全刷新之前调用。
        它会修改 self.current_config 和 self.configured_modules。
        前提: rack_count > 0 已经在外部检查。
        """
        if self.system_type != "LK" or not self.io_data_loader:
            return
        
        # 从 self.rack_info 获取真实的机架数量，如果为0则不应执行
        rack_count = self.rack_info.get('rack_count', 0)
        if rack_count == 0:
            logger.info("_initialize_slot1_for_lk_system_if_needed: rack_count is 0, skipping DP preset.")
            return

            logger.info("LK System: Attempting to preset DP module for slot 1 in all racks if not already set by config.")
            rack_info = self.io_data_loader.get_rack_info()
            rack_count = rack_info.get('rack_count', 0)
            
            for rack_id in range(1, rack_count + 1):
                dp_modules, _ = self.io_data_loader.load_available_modules('DP') 
                dp_model_to_set = "PROFIBUS-DP" 
                all_predefined_modules = self.io_data_loader.module_info_provider.get_all_predefined_modules()
                predefined_dp = [m for m in all_predefined_modules if m.get('type') == 'DP']
                if predefined_dp:
                    dp_model_to_set = predefined_dp[0]['model']
                logger.info(f"为LK机架 {rack_id} 槽位1设置DP模块: {dp_model_to_set}")
                dp_module_obj = self.io_data_loader.get_module_by_model(dp_model_to_set)
                if not dp_module_obj: 
                    dp_module_obj = {'model': dp_model_to_set, 'type': 'DP', 'channels': 0, 'description': 'DP通讯模块 (自动配置)'}
                if 'unique_id' not in dp_module_obj:
                    dp_module_obj['unique_id'] = self.next_module_id_counter
                self.next_module_id_counter +=1
                self.current_config[(rack_id, 1)] = dp_model_to_set
                self.configured_modules[(rack_id, 1)] = dp_module_obj
                self.current_modules_pool = [
                    m for m in self.current_modules_pool 
                    if not (m.get('model') == dp_model_to_set and m.get('unique_id') == dp_module_obj.get('unique_id'))
                ]
            self.load_modules() 

    def on_rack_tab_changed(self, index):
        if self.view.rack_combo: # 检查UI元素是否存在
             self.view.set_current_rack_combo(index)
        
    def on_rack_combo_changed(self, index):
        if self.view.rack_tabs: # 检查UI元素是否存在
            self.view.set_current_rack_tab(index)

    def setup_connections(self):
        if self.view.type_combo:
            self.view.type_combo.currentTextChanged.connect(self.load_modules)
        if self.view.add_button:
            self.view.add_button.clicked.connect(self.add_module)
        if self.view.remove_button:
            self.view.remove_button.clicked.connect(self.remove_module)
        if self.view.ok_button: # "应用配置" 按钮
            self.view.ok_button.clicked.connect(self.apply_configuration) # << 连接到新方法
        if self.view.cancel_button and self.view.cancel_button.isVisible(): # 如果取消按钮可见
            # self.view.cancel_button.clicked.connect(self.reload_configuration_from_loader) # << 连接到新方法
            pass # 暂时不连接，因为取消按钮被隐藏了

        if self.view.module_table:
            self.view.module_table.itemDoubleClicked.connect(self._handle_left_table_double_click)
        # itemDoubleClicked for right tables is connected within create_rack_tabs

    def _handle_left_table_double_click(self, item: QTableWidgetItem):
        """处理左侧可用模块列表双击事件，相当于点击添加按钮。"""
        if not self.view.module_table or not item:
            return
        logger.debug(f"左侧模块表双击: {item.row()}, {item.column()}, text: {item.text()}")
        current_row = item.row()
        # 确保双击的不是提示信息的合并单元格
        if self.view.module_table.rowSpan(current_row, 0) > 1: 
            logger.debug("双击了提示信息行，忽略。")
            return
        self.view.module_table.setCurrentCell(current_row, 0) 
        self.add_module() 

    def _handle_right_table_double_click(self, item: QTableWidgetItem):
        """处理右侧已配置模块列表双击事件，相当于点击移除按钮。"""
        if not self.view.rack_tabs or not item:
            return
        
        source_table = item.tableWidget() 
        if not source_table:
            logger.warning("右侧双击事件无法获取源表格")
            return
            
        logger.debug(f"右侧配置表双击: {item.row()}, {item.column()}, text: {item.text()} in table {source_table.objectName()}")
        current_row = item.row()
        # 确保双击的不是空行或表头（尽管 setCurrentCell 可能处理部分情况）
        if source_table.item(current_row, 0) is None or not source_table.item(current_row, 0).text():
            logger.debug("右侧双击了空行或无效行，忽略。")
            return
        source_table.setCurrentCell(current_row, 0) 
        self.remove_module() 

    def update_all_config_tables(self):
        if not self.view.rack_tabs: return
        current_index = self.view.rack_tabs.currentIndex()
        rack_info = self.io_data_loader.get_rack_info()
        rack_count = rack_info.get('rack_count', 0) 
        logger.info(f"更新所有配置表格: 机架数量 = {rack_count}")
        
        if rack_count > 0 and rack_count != self.view.rack_tabs.count():
             logger.warning(f"选项卡数量 ({self.view.rack_tabs.count()}) 与机架数量 ({rack_count}) 不匹配，可能需要重新创建选项卡。")
             # 在这种情况下，create_rack_tabs 应该已经被调用或即将被调用以同步。
             # 此处仅更新已存在的tabs。
       
        for rack_id_iter in range(1, (self.view.rack_tabs.count() if self.view.rack_tabs else 0) + 1):
            logger.debug(f"更新机架 {rack_id_iter} 配置表格")
            try:
                self.view.set_current_rack_tab(rack_id_iter - 1)
                self.update_current_config_table() # 逻辑方法，内部会调用view更新
            except Exception as e:
                logger.error(f"更新机架 {rack_id_iter} 配置表格失败: {e}", exc_info=True)
        
        if self.view.rack_tabs and 0 <= current_index < self.view.rack_tabs.count():
            self.view.set_current_rack_tab(current_index)
            logger.debug(f"恢复到原选项卡 {current_index + 1}")
        elif self.view.rack_tabs and self.view.rack_tabs.count() > 0:
            self.view.set_current_rack_tab(0)
            logger.debug("原选项卡索引无效，选择第一个选项卡")
        
        logger.info(f"所有机架配置表格更新完成，共 {self.view.rack_tabs.count() if self.view.rack_tabs else 0} 个选项卡")

    def update_current_config_table(self):
        if not self.view.rack_tabs: return
        current_rack_id = self.view.rack_tabs.currentIndex() + 1
        
        rack_config_items_for_ui = []
        # 获取当前机架的配置项，并按槽位排序
        sorted_rack_config_tuples = sorted(
            [(slot_id, model) for (r_id, slot_id), model in self.current_config.items() if r_id == current_rack_id],
            key=lambda x: x[0]
        )
        
        for slot_id, model_name in sorted_rack_config_tuples:
            module_info_obj = self.configured_modules.get((current_rack_id, slot_id))
            if not module_info_obj: # 后备：如果configured_modules中没有，尝试从IODataLoader获取
                module_info_obj = self.io_data_loader.get_module_by_model(model_name)
            
            if module_info_obj:
                rack_config_items_for_ui.append({
                    'slot_id': slot_id,
                    'model': module_info_obj.get('model', model_name),
                    'type': module_info_obj.get('type', module_info_obj.get('io_type', '未知')),
                    'channels': str(module_info_obj.get('channels', 0)),
                    'description': module_info_obj.get('description', '')
                })
            else: # 实在找不到信息
                 rack_config_items_for_ui.append({
                    'slot_id': slot_id, 'model': model_name, 'type': "未知", 
                    'channels': '?', 'description': "模块信息缺失"
                })
        
        self.view.update_config_table_for_rack(current_rack_id, rack_config_items_for_ui, self.system_type)
        logger.debug(f"已请求UI更新机架 {current_rack_id} 的配置表格视图。")

    def get_current_configuration(self) -> List[Dict[str, Any]]:
        config = []
        for (rack_id, slot_id), model in self.current_config.items():
            config.append({
                "rack_id": rack_id,
                "slot_id": slot_id,
                "model": model
            })
        return config
    
    def apply_configuration(self):
        final_config_to_check = self.get_current_configuration()
        config_dict_for_validation = {}
        for item in final_config_to_check:
            config_dict_for_validation[(item["rack_id"], item["slot_id"])] = item["model"]
        try:
            if self.io_data_loader.save_configuration(config_dict_for_validation):
                logger.info(f"成功应用PLC配置: {len(config_dict_for_validation)} 个模块")
                QMessageBox.information(self, "配置已应用", "PLC模块配置已成功应用到内部数据模型。")
                # self.configuration_applied.emit(True) # 如果需要信号通知父级
            else:
                QMessageBox.warning(self, "警告", "应用配置失败，请检查日志或控制台输出获取详细错误信息。配置可能不合法。")
                # self.configuration_applied.emit(False)
        except Exception as e:
            logger.error(f"应用配置时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"应用配置时出错: {str(e)}")
            # self.configuration_applied.emit(False)

    def reset_to_initial_state(self):
        """将PLC配置区域重置到初始的、未加载项目数据的状态。"""
        logger.info("PLCConfigEmbeddedWidget: Attempting to reset to initial state.")
        try:
            # 1. 清空核心数据结构
            self.current_config = {}
            self.all_available_modules = []
            self.current_modules_pool = []
            self.configured_modules = {}
            self.next_module_id_counter = 1 

            # 2. 重置系统和机架信息
            self.system_type = "LK" 
            self.rack_info = {'rack_count': 0, 'slots_per_rack': 0}
            
            # 3. 通知 IODataLoader 清除
            if self.io_data_loader:
                if hasattr(self.io_data_loader, 'clear_current_project_configuration'):
                    self.io_data_loader.clear_current_project_configuration()
                    logger.info("PLCConfigEmbeddedWidget: Called io_data_loader.clear_current_project_configuration()")
                else:
                    logger.warning("PLCConfigEmbeddedWidget: IODataLoader lacks 'clear_current_project_configuration' method.")
                    if hasattr(self.io_data_loader, 'current_plc_config'): self.io_data_loader.current_plc_config = {}
                    if hasattr(self.io_data_loader, 'system_info'): self.io_data_loader.system_info = {'system_type': 'LK', 'rack_count': 0, 'slots_per_rack': 11}

            # 4. 更新UI显示
            if self.view:
                if self.view.module_table:
                    self.view.show_no_data_in_module_table("请先选择一个项目并加载设备数据")
                
                if self.view.type_combo:
                    self.view.type_combo.setCurrentIndex(0) 
                    self.module_type_filter = self.view.type_combo.currentText()

            self.create_rack_tabs()
            self.update_all_config_tables()
            
            logger.info("PLCConfigEmbeddedWidget: Successfully reset to initial state.")

        except AttributeError as e_attr:
            logger.error(f"PLCConfigEmbeddedWidget.reset_to_initial_state: AttributeError occurred INTERNALLY: {e_attr}", exc_info=True)
            # 重新引发异常，以便外部（如MainWindow）仍然可以按预期捕获它，如果需要的话
            # 或者在这里处理，例如显示一个特定的错误消息给用户
            raise # Re-raise the caught AttributeError to see if MainWindow still catches it
        except Exception as e_general:
            logger.error(f"PLCConfigEmbeddedWidget.reset_to_initial_state: A general error occurred: {e_general}", exc_info=True)
            raise # Re-raise for general errors too

