"""PLC配置对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView,
                           QTabWidget, QWidget, QGridLayout, QGroupBox)
from PySide6.QtCore import Qt, QTimer
from typing import List, Dict, Any, Optional
import logging

# 导入IODataLoader
from core.io_table import IODataLoader

logger = logging.getLogger(__name__)

class PLCConfigDialogUI:
    """
    负责 PLCConfigDialog 的用户界面 (UI) 的创建、布局和基本更新。
    这个类不包含业务逻辑或复杂的事件处理。
    """
    def __init__(self, dialog: QDialog):
        """
        构造函数。

        Args:
            dialog (QDialog): 将要承载这些UI元素的主对话框实例。
        """
        self.dialog = dialog # 保存对主对话框的引用，以便在其上设置布局

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
        main_layout = QVBoxLayout(self.dialog) # 在主对话框上设置主布局
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

class PLCConfigDialog(QDialog):
    """PLC配置对话框 - 支持多机架布局及不同系统类型（LK, LE_CPU）"""
    def __init__(self, devices_data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC配置")
        self.resize(1300, 800)
        
        # 初始化UI管理器
        self.view = PLCConfigDialogUI(self)
        
        # 初始化本地变量 (这些是逻辑/状态相关的，保留在主类中)
        self.current_config = {} 
        self.io_data_loader = IODataLoader()
        self.all_available_modules = [] 
        self.current_modules_pool = []  
        self.configured_modules = {}    
        self.module_type_filter = '全部' 
        self.next_module_id = 1         
        self.system_type = "LK"

        # 设置UI (现在委托给UI管理器)
        self.view.setup_ui() # UI管理器会使用self (dialog)来设置布局
        
        self.setup_connections() # 信号槽连接逻辑保留在主类
        
        if devices_data:
            logger.info("传入了设备数据，正在处理...")
            self.set_devices_data(devices_data)
        else:
            logger.info("未传入设备数据，将使用默认IODataLoader状态创建机架和加载模块")
            rack_info_initial = self.io_data_loader.get_rack_info()
            self.system_type = rack_info_initial.get('system_type', "LK")
            logger.info(f"无设备数据时，从IODataLoader获取的系统类型: {self.system_type}")
            self.create_rack_tabs() 
            self.load_modules()    
        
    def setup_ui(self):
        """主对话框的UI设置，现在主要委托给PLCConfigDialogUI实例。"""
        # self.view.setup_ui() # 已在 __init__ 中调用
        # 保留此空方法或移除它，取决于是否还有其他dialog级别的UI设置。
        # 目前看来，所有UI创建都在PLCConfigDialogUI.setup_ui()中。
        logger.info("PLCConfigDialog: UI setup delegated to PLCConfigDialogUI.")

    def create_rack_tabs(self):
        """创建机架选项卡界面，根据系统类型调整槽位1的说明"""
        # self.rack_tabs.clear() # 改为 self.view.rack_tabs.clear() 或 self.view.clear_rack_tabs()
        # self.rack_combo.clear() # 改为 self.view.rack_combo.clear() 或封装方法
        self.view.clear_rack_tabs()
        self.view.update_rack_combo(0) # 清空后先用0更新，后续再根据rack_count填充
        
        rack_info = self.io_data_loader.get_rack_info()
        rack_count = rack_info.get('rack_count', 0)
        
        logger.info(f"创建机架选项卡: 系统类型={self.system_type}, 检测到 {rack_count} 个机架")
        
        actual_rack_count_for_combo = rack_count if rack_count > 0 else 1
        self.view.update_rack_combo(actual_rack_count_for_combo)
        
        if rack_count <= 0: rack_count = 1
        
        for rack_id_iter in range(1, rack_count + 1):
            slots_per_rack_display = rack_info.get('slots_per_rack')
            if slots_per_rack_display is None:
                slots_per_rack_display = 11 
                logger.warning("create_rack_tabs: rack_info did not contain 'slots_per_rack', using fallback 11.")
            
            # 创建新的tab页面和表格
            page_widget = self.view.create_rack_tab_page(rack_id_iter, slots_per_rack_display, self.system_type)
            self.view.add_rack_tab(page_widget, f"机架 {rack_id_iter}")
            logger.debug(f"创建机架 {rack_id_iter} 选项卡，槽位数: {slots_per_rack_display}, 系统类型: {self.system_type}")
        
        if rack_count > 0:
            self.initialize_slot1_conditionally()
            self.update_all_config_tables()
            
        # 连接信号，注意 rack_tabs 和 rack_combo 现在是 self.view 的属性
        if self.view.rack_tabs: 
            self.view.rack_tabs.currentChanged.connect(self.on_rack_tab_changed)
        if self.view.rack_combo:
            self.view.rack_combo.currentIndexChanged.connect(self.on_rack_combo_changed)
        logger.info(f"机架选项卡创建完成，共 {self.view.rack_tabs.count() if self.view.rack_tabs else 0} 个选项卡，系统类型 {self.system_type}")

    def initialize_slot1_conditionally(self):
        """根据系统类型初始化槽位1：LK系统预设DP，LE_CPU系统槽位1由用户配置"""
        if self.system_type == "LK":
            logger.info("LK系统：尝试为所有机架的槽位1预设DP模块...")
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
                    dp_module_obj['unique_id'] = self.next_module_id
                    self.next_module_id +=1
                self.current_config[(rack_id, 1)] = dp_model_to_set
                self.configured_modules[(rack_id, 1)] = dp_module_obj
                self.current_modules_pool = [
                    m for m in self.current_modules_pool 
                    if not (m.get('model') == dp_model_to_set and m.get('unique_id') == dp_module_obj.get('unique_id'))
                ]
            self.load_modules() 

        elif self.system_type == "LE_CPU":
            logger.info("LE_CPU系统：槽位1由用户从穿梭框选择LE5118 CPU，不在此处预设。")
        self.update_all_config_tables()

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
        if self.view.ok_button:
            self.view.ok_button.clicked.connect(self.accept)
        if self.view.cancel_button:
            self.view.cancel_button.clicked.connect(self.reject)
        # rack_tabs 和 rack_combo 的 currentChanged 连接已移至 create_rack_tabs 内部，
        # 因为它们是在那里动态创建的。

    def load_modules(self):
        try:
            # self.module_table.setRowCount(0) # 改为 self.view.populate_module_table([]) 或类似操作开始
            if not self.view.module_table: return # UI未就绪
            
            module_type_filter = self.view.type_combo.currentText() if self.view.type_combo else '全部'
            self.module_type_filter = module_type_filter
            
            raw_modules, has_data = self.io_data_loader.load_available_modules(module_type_filter)
            
            if not self.all_available_modules: 
                processed_raw_modules = []
                for module in raw_modules:
                    if 'unique_id' not in module: 
                        module['unique_id'] = self.next_module_id
                        self.next_module_id += 1
                    processed_raw_modules.append(module)
                self.all_available_modules = processed_raw_modules.copy()
                self.current_modules_pool = processed_raw_modules.copy() 
            else: 
                configured_unique_ids = [
                    mod.get('unique_id') for mod in self.configured_modules.values() if mod.get('unique_id') is not None
                ]
                temp_pool = [m for m in self.all_available_modules if m.get('unique_id') not in configured_unique_ids]
                if module_type_filter != '全部':
                    self.current_modules_pool = [m for m in temp_pool if m.get('type', m.get('io_type', '')) == module_type_filter]
                else:
                    self.current_modules_pool = temp_pool

            available_modules_to_display = self.current_modules_pool
            if available_modules_to_display:
                self.view.populate_module_table(available_modules_to_display)
            else:
                self.view.show_no_data_in_module_table("无匹配的可用模块或所有模块已配置")
            
            logger.info(f"已加载 {len(available_modules_to_display)} 个可用模块（类型：{module_type_filter}，系统：{self.system_type}) 到穿梭框")
            
        except Exception as e:
            logger.error(f"加载模块数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载模块数据失败: {str(e)}")

    def add_module(self):
        if not self.view.module_table or not self.view.rack_tabs: return

        selected_rows = self.view.module_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要添加的模块"); return
        
        row = selected_rows[0].row()
        if self.view.module_table.rowSpan(row, 0) > 1: 
            QMessageBox.warning(self, "提示", "无可用模块数据"); return

        try:
            id_item = self.view.module_table.item(row, 0)
            module_unique_id = id_item.data(Qt.ItemDataRole.UserRole) 
            selected_module_from_pool = None
            for module in self.current_modules_pool: 
                if module.get('unique_id') == module_unique_id:
                    selected_module_from_pool = module.copy()
                    break
            if not selected_module_from_pool:
                model_text = self.view.module_table.item(row, 1).text()
                logger.error(f"无法在current_modules_pool中找到unique_id {module_unique_id} (型号: {model_text}) 的模块")
                QMessageBox.warning(self, "错误", "无法找到所选模块的内部数据，请重试或检查日志。")
                return
            model = selected_module_from_pool['model']
            module_type = selected_module_from_pool.get('type', selected_module_from_pool.get('io_type', '未录入'))
        except Exception as e:
            logger.error(f"获取选中模块数据时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "提示", "无法获取选中模块的数据")
            return
        
        current_rack_id = self.view.rack_tabs.currentIndex() + 1
        actual_system_type_for_rack = self.system_type
        rack_info = self.io_data_loader.get_rack_info()
        slots_per_rack = rack_info.get('slots_per_rack')
        if slots_per_rack is None:
            logger.warning(f"In add_module: rack_info did not contain 'slots_per_rack' for rack {current_rack_id}, using a fallback value (11).")
            slots_per_rack = 11 
        
        assigned_slot_id = None
        is_targeting_slot1 = False
        if (actual_system_type_for_rack == "LE_CPU" and module_type == "CPU") or \
           (actual_system_type_for_rack == "LK" and module_type == "DP"):
            if (current_rack_id, 1) not in self.current_config:
                is_targeting_slot1 = True
        
        if is_targeting_slot1:
            validation_slot1 = self.io_data_loader.validate_module_placement(current_rack_id, 1, model)
            if validation_slot1['valid']:
                assigned_slot_id = 1
            else:
                QMessageBox.warning(self, "放置错误", validation_slot1['error'])
                return
        else: 
            start_slot_for_others = 1
            if actual_system_type_for_rack == "LK": start_slot_for_others = 2
            # Special handling for LE_CPU if slot 1 is taken by CPU
            if actual_system_type_for_rack == "LE_CPU" and (current_rack_id,1) in self.current_config and self.current_config[(current_rack_id,1)].startswith("LE5118") : # More robust check for CPU in slot 1
                 start_slot_for_others = 2

            if actual_system_type_for_rack == "LE_CPU" and module_type == "CPU" and assigned_slot_id != 1: # CPU for LE must be slot 1
                 QMessageBox.warning(self, "放置错误", f"{model} (CPU) 只能放置在LE系统的槽位1。")
                 return

            for slot_id_candidate in range(start_slot_for_others, slots_per_rack + 1):
                if slot_id_candidate == 1 and actual_system_type_for_rack == "LK": continue 
                if slot_id_candidate == 1 and actual_system_type_for_rack == "LE_CPU" and module_type != "CPU": continue
                
                if (current_rack_id, slot_id_candidate) not in self.current_config:
                    validation_candidate = self.io_data_loader.validate_module_placement(current_rack_id, slot_id_candidate, model)
                    if validation_candidate['valid']:
                        assigned_slot_id = slot_id_candidate
                        break
                    else: 
                        logger.debug(f"槽位 {slot_id_candidate} 对模块 {model} 验证失败: {validation_candidate['error']}")
        
        if assigned_slot_id is None:
            QMessageBox.warning(self, "提示", f"机架 {current_rack_id} 没有可用的有效槽位放置模块 {model}")
            return

        self.current_config[(current_rack_id, assigned_slot_id)] = model
        self.configured_modules[(current_rack_id, assigned_slot_id)] = selected_module_from_pool
        logger.info(f"模块 {model} ({module_type}) 已添加到机架 {current_rack_id} 槽位 {assigned_slot_id} (系统: {actual_system_type_for_rack})")

        self.current_modules_pool = [
            m for m in self.current_modules_pool if m.get('unique_id') != selected_module_from_pool.get('unique_id')
        ]
        self.update_current_config_table()
        self.load_modules()

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
        if not slot_text_item or not slot_text_item.text().isdigit(): return
        slot_id = int(slot_text_item.text())

        actual_system_type_for_rack = self.system_type
        if slot_id == 1:
            if actual_system_type_for_rack == "LK":
                QMessageBox.warning(self, "提示", "LK系统槽位1的DP模块是预设的，不能移除。")
            return
        elif actual_system_type_for_rack == "LE_CPU":
                logger.info(f"允许从LE_CPU系统槽位1移除模块 (后续accept时会校验CPU是否存在)")
        
        module_to_remove_key = (current_rack_id, slot_id)
        if module_to_remove_key in self.current_config:
            removed_module_obj = self.configured_modules.pop(module_to_remove_key, None)
            del self.current_config[module_to_remove_key]
            if removed_module_obj:
                is_in_pool_already = any(m.get('unique_id') == removed_module_obj.get('unique_id') for m in self.current_modules_pool)
                if not is_in_pool_already:
                    if self.module_type_filter == '全部' or \
                       removed_module_obj.get('type', removed_module_obj.get('io_type', '')) == self.module_type_filter:
                        self.current_modules_pool.append(removed_module_obj)
                logger.info(f"模块 {removed_module_obj.get('model')} 已从配置中移除，并尝试返回模块池")
            else:
                logger.warning(f"尝试移除的模块 {(current_rack_id, slot_id)} 不在 configured_modules 中")
            self.update_current_config_table()
            self.load_modules()
        else:
            logger.warning(f"尝试移除的模块 {(current_rack_id, slot_id)} 不在 current_config 中")

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
    
    def accept(self):
        final_config_to_check = self.get_current_configuration()
        config_dict_for_validation = {}
        for item in final_config_to_check:
            config_dict_for_validation[(item["rack_id"], item["slot_id"])] = item["model"]
        try:
            if self.io_data_loader.save_configuration(config_dict_for_validation):
                logger.info(f"成功保存PLC配置: {len(config_dict_for_validation)} 个模块")
                super().accept()
            else:
                QMessageBox.warning(self, "警告", "保存配置失败，请检查日志或控制台输出获取详细错误信息。配置可能不合法。")
        except Exception as e:
            logger.error(f"保存配置时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时出错: {str(e)}")

    def set_devices_data(self, devices_data: List[Dict[str, Any]]):
        if not devices_data:
            logger.warning("传入的设备数据为空")
            rack_info_empty = self.io_data_loader.get_rack_info()
            self.system_type = rack_info_empty.get('system_type', "LK")
            logger.info(f"设备数据为空时，系统类型: {self.system_type}")
            self.create_rack_tabs()
            self.load_modules()
            return
            
        logger.info(f"设置设备数据: {len(devices_data)} 个设备")
        self.all_available_modules = []
        self.current_modules_pool = []
        self.configured_modules = {}
        self.current_config = {} 
        self.next_module_id = 1
        self.io_data_loader.set_devices_data(devices_data)
        rack_info_updated = self.io_data_loader.get_rack_info()
        self.system_type = rack_info_updated.get('system_type', "LK")
        logger.info(f"处理设备数据后，系统类型更新为: {self.system_type}")
        self.create_rack_tabs()
        self.load_modules()
        logger.info(f"设备数据设置完成，UI已刷新，当前系统类型: {self.system_type}, 机架数: {self.view.rack_tabs.count() if self.view.rack_tabs else 0}")

