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

class PLCConfigDialog(QDialog):
    """PLC配置对话框 - 支持多机架布局及不同系统类型（LK, LE_CPU）"""
    def __init__(self, devices_data: List[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC配置")
        self.resize(1300, 800)  # 增加对话框尺寸
        
        # 初始化本地变量
        self.current_config = {}  # 使用字典存储配置 {(rack_id, slot_id): model}
        
        # 初始化数据加载器
        self.io_data_loader = IODataLoader()
        
        # 添加用于跟踪模块状态的变量
        self.all_available_modules = []  # 所有可用模块
        self.current_modules_pool = []   # 当前可选的模块池
        self.configured_modules = {}     # 已配置的模块，格式：{(rack_id, slot_id): module_dict}
        self.module_type_filter = '全部'  # 当前的模块类型过滤条件
        self.next_module_id = 1          # 为每个模块分配唯一ID
        
        # 对话框级别的系统类型，从IODataLoader获取
        self.system_type = "LK"

        # 设置UI
        self.setup_ui()
        self.setup_connections()
        
        # 设置设备数据 - 移到UI设置之后，在创建机架选项卡之前
        if devices_data:
            logger.info("传入了设备数据，正在处理...")
            self.set_devices_data(devices_data)
        else:
            logger.info("未传入设备数据，将使用默认IODataLoader状态创建机架和加载模块")
            # 如果没有设备数据，IODataLoader会按其默认状态初始化（可能是LK）
            # 我们仍需从IODataLoader获取system_type以正确设置UI
            rack_info_initial = self.io_data_loader.get_rack_info()
            self.system_type = rack_info_initial.get('system_type', "LK")
            logger.info(f"无设备数据时，从IODataLoader获取的系统类型: {self.system_type}")
            self.create_rack_tabs() # 基于获取的system_type创建机架
            self.load_modules()     # 加载可用模块，LE5118应在此列出
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)  # 设置布局间距
        
        # 模块配置区域
        module_layout = QHBoxLayout()
        module_layout.setSpacing(20)  # 设置左右两边表格的间距
        
        # 左侧：模块选择
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("可用模块:"))
        
        # 模块类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("类型:"))
        self.type_combo = QComboBox()
        self.type_combo.addItems(['全部', 'AI', 'AO', 'DI', 'DO', 'DP'])
        self.type_combo.setFixedWidth(100)
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        left_layout.addLayout(type_layout)
        
        # 左侧模块列表
        self.module_table = QTableWidget()
        self.module_table.setColumnCount(5)
        self.module_table.setHorizontalHeaderLabels(['序号', '型号', '类型', '通道数', '描述'])
        self.module_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.module_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.module_table.verticalHeader().setVisible(False)
        
        # 设置左侧表格列宽
        header_left = self.module_table.horizontalHeader()
        header_left.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 序号
        header_left.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 型号
        header_left.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 类型
        header_left.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 通道数
        header_left.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        
        # 设置表格样式
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
        self.module_table.setAlternatingRowColors(True)  # 启用隔行变色
        
        left_layout.addWidget(self.module_table)
        module_layout.addLayout(left_layout)
        
        # 中间：操作按钮
        mid_layout = QVBoxLayout()
        self.add_button = QPushButton("添加 →")
        self.remove_button = QPushButton("← 移除")
        self.add_button.setFixedWidth(100)
        self.remove_button.setFixedWidth(100)
        mid_layout.addStretch()
        mid_layout.addWidget(self.add_button)
        mid_layout.addWidget(self.remove_button)
        mid_layout.addStretch()
        module_layout.addLayout(mid_layout)
        
        # 右侧：已配置模块
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("已配置模块:"))
        
        # 机架选择控件
        rack_layout = QHBoxLayout()
        rack_layout.addWidget(QLabel("机架:"))
        self.rack_combo = QComboBox()
        rack_layout.addWidget(self.rack_combo)
        rack_layout.addStretch()
        right_layout.addLayout(rack_layout)
        
        # 使用选项卡控件显示不同机架
        self.rack_tabs = QTabWidget()
        self.rack_tabs.setTabPosition(QTabWidget.TabPosition.North)
        right_layout.addWidget(self.rack_tabs)
        
        module_layout.addLayout(right_layout)
        
        # 设置左右两侧布局的比例
        module_layout.setStretch(0, 1)  # 左侧表格
        module_layout.setStretch(2, 2)  # 右侧表格更宽
        
        layout.addLayout(module_layout)
        
        # 底部按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.ok_button.setFixedWidth(80)
        self.cancel_button.setFixedWidth(80)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 移除对create_rack_tabs的直接调用，将在设置设备数据后调用
        # self.create_rack_tabs()
        logger.info("UI界面初始化完成，将在设置设备数据后创建机架选项卡")

    def create_rack_tabs(self):
        """创建机架选项卡界面，根据系统类型调整槽位1的说明"""
        self.rack_tabs.clear()
        self.rack_combo.clear()
        
        rack_info = self.io_data_loader.get_rack_info() # rack_info现在包含system_type
        rack_count = rack_info.get('rack_count', 0)
        # self.system_type 已在调用此函数前被设置/更新
        
        logger.info(f"创建机架选项卡: 系统类型={self.system_type}, 检测到 {rack_count} 个机架")
        
        if rack_count <= 0: rack_count = 1 # 确保至少一个机架显示
        
        for i in range(rack_count): self.rack_combo.addItem(f"机架 {i+1}")
        
        for rack_id_iter in range(1, rack_count + 1):
            rack_page = QWidget()
            rack_layout = QVBoxLayout(rack_page)
            config_table = QTableWidget()
            config_table.setObjectName(f"rack_table_{rack_id_iter}")
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
            config_table.setStyleSheet(self.module_table.styleSheet())
            config_table.setAlternatingRowColors(True)

            slots_per_rack_display = rack_info.get('slots_per_rack', self.io_data_loader.DEFAULT_RACK_SLOTS)
            
            # 根据系统类型调整信息标签
            info_text = f"机架 {rack_id_iter} (槽位1-{slots_per_rack_display})"
            if self.system_type == "LK":
                info_text = f"机架 {rack_id_iter} (LK系统: 槽位1固定为DP模块, 可配置槽位2-{slots_per_rack_display})"
            elif self.system_type == "LE_CPU":
                 info_text = f"机架 {rack_id_iter} (LE系统: 槽位1请配置LE5118 CPU, 可配置槽位2-{slots_per_rack_display})"
            
            info_label = QLabel(info_text)
            rack_layout.addWidget(info_label)
            rack_layout.addWidget(config_table)
            self.rack_tabs.addTab(rack_page, f"机架 {rack_id_iter}")
            logger.debug(f"创建机架 {rack_id_iter} 选项卡，槽位数: {slots_per_rack_display}, 系统类型: {self.system_type}")
        
        if rack_count > 0:
            self.initialize_slot1_conditionally() # 调用新的初始化方法
            self.update_all_config_tables()
            
        self.rack_tabs.currentChanged.connect(self.on_rack_tab_changed)
        self.rack_combo.currentIndexChanged.connect(self.on_rack_combo_changed)
        logger.info(f"机架选项卡创建完成，共 {self.rack_tabs.count()} 个选项卡，系统类型 {self.system_type}")

    def initialize_slot1_conditionally(self):
        """根据系统类型初始化槽位1：LK系统预设DP，LE_CPU系统槽位1由用户配置"""
        if self.system_type == "LK":
            logger.info("LK系统：尝试为所有机架的槽位1预设DP模块...")
            rack_info = self.io_data_loader.get_rack_info()
            rack_count = rack_info.get('rack_count', 0)
            
            for rack_id in range(1, rack_count + 1):
                # 查找可用的DP模块
                dp_modules, _ = self.io_data_loader.load_available_modules('DP') 
                # 注意：load_available_modules 不应受配置中模块的影响，它应返回所有理论上可用的
                # 或者，我们直接用预定义的DP型号
                dp_model_to_set = "PROFIBUS-DP" # 默认的DP模块
                
                # 尝试从设备数据（如果已加载）或预定义模块中获取一个实际的DP型号
                # 这里的逻辑需要确保 self.io_data_loader.predefined_modules 被正确使用
                # 或 get_module_info_by_model (如果它能找到DP模块)
                
                # 简化：直接使用一个已知的DP模块型号，或者第一个找到的DP模块
                predefined_dp = [m for m in self.io_data_loader.predefined_modules if m.get('type') == 'DP']
                if predefined_dp:
                    dp_model_to_set = predefined_dp[0]['model']
                
                logger.info(f"为LK机架 {rack_id} 槽位1设置DP模块: {dp_model_to_set}")
                
                # 获取完整的模块对象用于 configured_modules
                dp_module_obj = self.io_data_loader.get_module_by_model(dp_model_to_set)
                if not dp_module_obj: # 万一找不到，创建一个临时的
                    dp_module_obj = {'model': dp_model_to_set, 'type': 'DP', 'channels': 0, 'description': 'DP通讯模块 (自动配置)'}
                
                # 确保分配unique_id
                if 'unique_id' not in dp_module_obj:
                    dp_module_obj['unique_id'] = self.next_module_id
                    self.next_module_id +=1

                self.current_config[(rack_id, 1)] = dp_model_to_set
                self.configured_modules[(rack_id, 1)] = dp_module_obj

                # 从可用模块池中移除这个DP模块实例 (如果它存在于池中)
                self.current_modules_pool = [
                    m for m in self.current_modules_pool 
                    if not (m.get('model') == dp_model_to_set and m.get('unique_id') == dp_module_obj.get('unique_id'))
                ]
            self.load_modules() # 更新左侧列表

        elif self.system_type == "LE_CPU":
            logger.info("LE_CPU系统：槽位1由用户从穿梭框选择LE5118 CPU，不在此处预设。")
            # 确保LE5118 CPU在load_modules()时是可见的
        
        self.update_all_config_tables()

    def on_rack_tab_changed(self, index):
        """处理选项卡切换事件"""
        # 同步更新组合框
        self.rack_combo.setCurrentIndex(index)
        
    def on_rack_combo_changed(self, index):
        """处理机架组合框变化事件"""
        # 同步更新选项卡
        if index >= 0 and index < self.rack_tabs.count():
            self.rack_tabs.setCurrentIndex(index)

    def setup_connections(self):
        """设置信号连接"""
        # 类型选择变化时重新加载模块列表
        self.type_combo.currentTextChanged.connect(self.load_modules)
        
        # 添加和移除模块的按钮连接
        self.add_button.clicked.connect(self.add_module)
        self.remove_button.clicked.connect(self.remove_module)
        
        # 确定和取消按钮
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def load_modules(self):
        """加载模块列表，确保CPU模块（如LE5118）在LE_CPU系统时可见"""
        try:
            self.module_table.setRowCount(0)
            module_type_filter = self.type_combo.currentText()
            self.module_type_filter = module_type_filter
            
            # 从IODataLoader获取模块数据 (它已经知道system_type)
            # load_available_modules 本身不应该受 system_type 影响其返回的 *所有* 可用模块
            # 而是 PLCConfigDialog 根据 system_type 决定如何使用这些模块
            
            raw_modules, has_data = self.io_data_loader.load_available_modules(module_type_filter)
            
            if not self.all_available_modules: # 首次加载，或数据重置后
                processed_raw_modules = []
                for module in raw_modules:
                    if 'unique_id' not in module: # 确保每个模块都有unique_id
                        module['unique_id'] = self.next_module_id
                        self.next_module_id += 1
                    processed_raw_modules.append(module)
                self.all_available_modules = processed_raw_modules.copy()
                self.current_modules_pool = processed_raw_modules.copy() # current_modules_pool是动态变化的
            else: # 非首次加载，使用 all_available_modules 作为基准池，然后过滤
                  # current_modules_pool 应该基于 all_available_modules 并排除已配置的
                  # 这部分逻辑有点复杂，需要确保 current_modules_pool 正确更新
                  # 重新构建 current_modules_pool 基于 all_available_modules 和已配置的模块
                
                configured_unique_ids = [
                    mod.get('unique_id') for mod in self.configured_modules.values() if mod.get('unique_id') is not None
                ]
                
                # 从 all_available_modules 开始，排除已配置的
                temp_pool = [m for m in self.all_available_modules if m.get('unique_id') not in configured_unique_ids]

                # 如果有类型过滤，应用过滤
                if module_type_filter != '全部':
                    self.current_modules_pool = [m for m in temp_pool if m.get('type', m.get('io_type', '')) == module_type_filter]
                else:
                    self.current_modules_pool = temp_pool


            # 这里的 available_modules 就是 self.current_modules_pool
            available_modules_to_display = self.current_modules_pool

            # 对于LE_CPU系统，如果选择了"全部"或"CPU"类型，确保LE5118在列表中（如果它尚未配置）
            # 这个逻辑可能在 io_data_loader.load_available_modules 中已经通过 ALLOWED_MODULE_TYPES 处理了CPU类型
            # 所以这里主要是确保过滤和已配置模块的排除正确

            if available_modules_to_display:
                self._populate_module_table(available_modules_to_display)
            else:
                self._show_no_data_message("无匹配的可用模块或所有模块已配置")
            
            logger.info(f"已加载 {len(available_modules_to_display)} 个可用模块（类型：{module_type_filter}，系统：{self.system_type}）到穿梭框")
            
        except Exception as e:
            logger.error(f"加载模块数据失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载模块数据失败: {str(e)}")

    def _populate_module_table(self, modules: List[Dict[str, Any]]):
        """填充模块表格"""
        # 清空表格以确保新数据准确显示
        self.module_table.setRowCount(0)
        
        # 为每个模块添加一行
        for index, module in enumerate(modules):
            row = self.module_table.rowCount()
            self.module_table.insertRow(row)
            
            # 获取字段值，同时考虑标准字段名和原始_widget_*字段名
            module_model = module.get('model', module.get('_widget_1635777115287', ''))
            module_type = module.get('io_type', module.get('type', '未录入'))
            module_channels = str(module.get('channels', 0))
            
            # 组合描述 - 使用技术参数作为描述，如果有多个技术参数字段则组合使用
            main_desc = module.get('description', module.get('_widget_1641439264111', ''))
            ext_desc = module.get('ext_params', module.get('_widget_1641439463480', ''))
            if ext_desc and ext_desc != main_desc:
                module_desc = f"{main_desc}; {ext_desc}" if main_desc else ext_desc
            else:
                module_desc = main_desc
            
            # 使用从1开始递增的简单序号作为显示ID
            display_id = index + 1  # 从1开始递增
                
            # 创建表格项并填充数据
            id_item = QTableWidgetItem(str(display_id))
            model_item = QTableWidgetItem(module_model)
            type_item = QTableWidgetItem(module_type)
            channels_item = QTableWidgetItem(module_channels)
            desc_item = QTableWidgetItem(module_desc)
            
            # 设置表格项
            self.module_table.setItem(row, 0, id_item)
            self.module_table.setItem(row, 1, model_item)
            self.module_table.setItem(row, 2, type_item)
            self.module_table.setItem(row, 3, channels_item)
            self.module_table.setItem(row, 4, desc_item)
            
            # 保存唯一ID为用户数据，方便后续操作
            if 'unique_id' in module:
                id_item.setData(Qt.ItemDataRole.UserRole, module['unique_id'])
            
        logger.info(f"已加载 {len(modules)} 个模块到表格")
    
    def _show_no_data_message(self, message: str):
        """在表格中显示无数据提示信息"""
        row = self.module_table.rowCount()
        self.module_table.insertRow(row)
        
        info_item = QTableWidgetItem(message)
        # 设置文本居中
        info_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 合并单元格显示提示信息
        self.module_table.setSpan(row, 0, 1, 5)
        self.module_table.setItem(row, 0, info_item)

    def add_module(self):
        """添加模块到配置表，根据系统类型验证槽位1的模块"""
        selected_rows = self.module_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要添加的模块"); return
        
        row = selected_rows[0].row()
        if self.module_table.rowSpan(row, 0) > 1: # 无数据提示行
            QMessageBox.warning(self, "提示", "无可用模块数据"); return

        try:
            id_item = self.module_table.item(row, 0)
            module_unique_id = id_item.data(Qt.ItemDataRole.UserRole) # 用 unique_id 来查找源模块
            
            selected_module_from_pool = None
            for module in self.current_modules_pool: # 应该从 current_modules_pool 中查找
                if module.get('unique_id') == module_unique_id:
                    selected_module_from_pool = module.copy() # 使用副本
                    break
            
            if not selected_module_from_pool:
                 # 如果current_modules_pool中没有，可能是逻辑错误，或从all_available_modules取（但不应发生）
                model_text = self.module_table.item(row, 1).text()
                logger.error(f"无法在current_modules_pool中找到unique_id {module_unique_id} (型号: {model_text}) 的模块")
                QMessageBox.warning(self, "错误", "无法找到所选模块的内部数据，请重试或检查日志。")
                return

            model = selected_module_from_pool['model']
            module_type = selected_module_from_pool.get('type', selected_module_from_pool.get('io_type', '未录入'))
            
        except Exception as e:
            logger.error(f"获取选中模块数据时出错: {e}", exc_info=True)
            QMessageBox.warning(self, "提示", "无法获取选中模块的数据")
            return

        current_rack_id = self.rack_tabs.currentIndex() + 1
        # 获取当前机架的实际系统类型（如果未来支持混合系统机架）
        # current_rack_obj = self.io_data_loader.racks_data[current_rack_id -1]
        # actual_system_type_for_rack = current_rack_obj.get('system_type', self.system_type)
        actual_system_type_for_rack = self.system_type # 简化

        slots_per_rack = self.io_data_loader.get_rack_info().get('slots_per_rack', self.io_data_loader.DEFAULT_RACK_SLOTS)
        
        # 使用 IODataLoader 进行放置验证
        validation_result = self.io_data_loader.validate_module_placement(current_rack_id, 1, model) # 先尝试槽位1
        
        assigned_slot_id = None
        
        # 特殊处理槽位1
        is_targeting_slot1 = False
        if (actual_system_type_for_rack == "LE_CPU" and module_type == "CPU") or \
           (actual_system_type_for_rack == "LK" and module_type == "DP"):
            if (current_rack_id, 1) not in self.current_config: # 如果槽位1未被占用
                is_targeting_slot1 = True
        
        if is_targeting_slot1:
            validation_slot1 = self.io_data_loader.validate_module_placement(current_rack_id, 1, model)
            if validation_slot1['valid']:
                assigned_slot_id = 1
            else: # 即使用户想放槽位1，但验证失败
                QMessageBox.warning(self, "放置错误", validation_slot1['error'])
                return
        else: # 非特殊模块 或 槽位1已占用/不适用，尝试其他槽位
            start_slot_for_others = 1 if actual_system_type_for_rack == "LE_CPU" and (current_rack_id,1) in self.current_config and self.current_config[(current_rack_id,1)]!=model else \
                                    (2 if actual_system_type_for_rack == "LK" else 1) # LE CPU槽位1被CPU占后从2开始
            if actual_system_type_for_rack == "LE_CPU" and module_type == "CPU": # LE CPU只能放槽位1
                 QMessageBox.warning(self, "放置错误", f"{model} (CPU) 只能放置在LE系统的槽位1。")
                 return


            for slot_id_candidate in range(start_slot_for_others, slots_per_rack + 1):
                if slot_id_candidate == 1 and actual_system_type_for_rack == "LK": continue # LK系统跳过槽位1给普通模块
                if slot_id_candidate == 1 and actual_system_type_for_rack == "LE_CPU" and module_type != "CPU": continue # LE系统槽位1跳过给非CPU模块
                
                if (current_rack_id, slot_id_candidate) not in self.current_config:
                    validation_candidate = self.io_data_loader.validate_module_placement(current_rack_id, slot_id_candidate, model)
                    if validation_candidate['valid']:
                        assigned_slot_id = slot_id_candidate
                        break
                    else: # 如果验证器说不能放，我们应该相信它
                        logger.debug(f"槽位 {slot_id_candidate} 对模块 {model} 验证失败: {validation_candidate['error']}")
                        # 不提示用户，继续找下一个槽位
        
        if assigned_slot_id is None:
            QMessageBox.warning(self, "提示", f"机架 {current_rack_id} 没有可用的有效槽位放置模块 {model}")
            return

        # 放置模块
        self.current_config[(current_rack_id, assigned_slot_id)] = model
        self.configured_modules[(current_rack_id, assigned_slot_id)] = selected_module_from_pool
        logger.info(f"模块 {model} ({module_type}) 已添加到机架 {current_rack_id} 槽位 {assigned_slot_id} (系统: {actual_system_type_for_rack})")

        # 从 current_modules_pool 中移除 (不是 all_available_modules)
        self.current_modules_pool = [
            m for m in self.current_modules_pool if m.get('unique_id') != selected_module_from_pool.get('unique_id')
        ]
        
        self.update_current_config_table()
        self.load_modules() # 这会用更新后的 current_modules_pool 重新填充左侧列表

    def remove_module(self):
        """从配置表中移除模块，根据系统类型验证槽位1的模块"""
        current_rack_id = self.rack_tabs.currentIndex() + 1
        config_table = self.rack_tabs.currentWidget().findChild(QTableWidget, f"rack_table_{current_rack_id}")
        if not config_table: return
        
        selected_rows = config_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移除的模块"); return
        
        row = selected_rows[0].row()
        slot_text = config_table.item(row, 0).text()
        if not slot_text.isdigit(): return
        slot_id = int(slot_text)

        # actual_system_type_for_rack = self.io_data_loader.racks_data[current_rack_id-1].get('system_type', self.system_type)
        actual_system_type_for_rack = self.system_type # 简化

        if slot_id == 1:
            if actual_system_type_for_rack == "LK":
                QMessageBox.warning(self, "提示", "LK系统槽位1的DP模块是预设的，不能移除。")
                return
            elif actual_system_type_for_rack == "LE_CPU":
                # LE系统中，CPU在槽位1，理论上也不应轻易移除，但如果用户就是想重新配置呢？
                # 暂时允许移除，但accept时会校验
                logger.info(f"允许从LE_CPU系统槽位1移除模块 (后续accept时会校验CPU是否存在)")
                # QMessageBox.warning(self, "提示", "LE系统槽位1的CPU模块是核心，移除后请重新配置。")
                # return 
        
        module_to_remove_key = (current_rack_id, slot_id)
        if module_to_remove_key in self.current_config:
            removed_module_obj = self.configured_modules.pop(module_to_remove_key, None)
            del self.current_config[module_to_remove_key]
            
            if removed_module_obj:
                # 将移除的模块重新放回 current_modules_pool (如果它来自那里)
                # 需要确保它也放回 all_available_modules 如果那是源头
                # 最简单的是确保它回到 current_modules_pool 然后 load_modules() 会处理显示
                # 我们需要确保不重复添加
                is_in_pool_already = any(m.get('unique_id') == removed_module_obj.get('unique_id') for m in self.current_modules_pool)
                if not is_in_pool_already:
                     # 检查是否应该基于当前类型过滤器添加
                    if self.module_type_filter == '全部' or \
                       removed_module_obj.get('type', removed_module_obj.get('io_type', '')) == self.module_type_filter:
                        self.current_modules_pool.append(removed_module_obj)

                logger.info(f"模块 {removed_module_obj.get('model')} 已从配置中移除，并尝试返回模块池")
            else:
                logger.warning(f"尝试移除的模块 {(current_rack_id, slot_id)} 不在 configured_modules 中")

            self.update_current_config_table()
            self.load_modules() # 重新加载左侧列表
        else:
            logger.warning(f"尝试移除的模块 {(current_rack_id, slot_id)} 不在 current_config 中")

    def update_all_config_tables(self):
        """更新所有机架的配置表格"""
        # 获取当前的选项卡索引，以便稍后恢复
        current_index = self.rack_tabs.currentIndex()
        
        # 检查机架数量
        rack_info = self.io_data_loader.get_rack_info()
        rack_count = rack_info.get('rack_count', 0) 
        logger.info(f"更新所有配置表格: 机架数量 = {rack_count}")
        
        # 确保选项卡数量与机架数量一致
        if rack_count != self.rack_tabs.count():
            logger.warning(f"选项卡数量 ({self.rack_tabs.count()}) 与机架数量 ({rack_count}) 不匹配")
            # 如果不一致，重新创建选项卡
            if rack_count > 0:
                logger.info("重新创建机架选项卡")
                self.create_rack_tabs()
                return
        
        # 遍历每个机架，更新配置表格
        for rack_id in range(1, self.rack_tabs.count() + 1):
            logger.debug(f"更新机架 {rack_id} 配置表格")
            try:
                # 临时切换到该选项卡并更新
                self.rack_tabs.setCurrentIndex(rack_id - 1)
                self.update_current_config_table()
            except Exception as e:
                logger.error(f"更新机架 {rack_id} 配置表格失败: {e}", exc_info=True)
        
        # 恢复到原来的选项卡
        if 0 <= current_index < self.rack_tabs.count():
            self.rack_tabs.setCurrentIndex(current_index)
            logger.debug(f"恢复到原选项卡 {current_index + 1}")
        else:
            logger.warning(f"无法恢复到原选项卡，索引 {current_index} 无效")
            # 如果原索引无效，选择第一个选项卡
            if self.rack_tabs.count() > 0:
                self.rack_tabs.setCurrentIndex(0)
                logger.debug("选择第一个选项卡")
        
        logger.info(f"所有机架配置表格更新完成，共 {self.rack_tabs.count()} 个选项卡")

    def update_current_config_table(self):
        """更新当前机架的配置表格，槽位1根据系统类型可能有特殊显示"""
        current_rack_id = self.rack_tabs.currentIndex() + 1
        config_table = self.rack_tabs.currentWidget().findChild(QTableWidget, f"rack_table_{current_rack_id}")
        if not config_table:
            logger.error(f"无法找到机架 {current_rack_id} 的配置表格")
            return
        
        config_table.setRowCount(0)
        
        # current_rack_system_type = self.io_data_loader.racks_data[current_rack_id-1].get('system_type', self.system_type)
        current_rack_system_type = self.system_type # 简化
        
        # 获取当前机架的配置项，并按槽位排序
        rack_config_items = sorted(
            [(slot_id, model) for (r_id, slot_id), model in self.current_config.items() if r_id == current_rack_id],
            key=lambda x: x[0]
        )
        
        for slot_id, model in rack_config_items:
            module_info = self.io_data_loader.get_module_by_model(model)
            if not module_info: # 如果在io_data_loader找不到，尝试从configured_modules获取
                module_info = self.configured_modules.get((current_rack_id, slot_id), {
                    'model': model, 'type': "未知(缓存)", 'channels': '?', 'description': "模块信息不完整 (缓存)"
                })

            row = config_table.rowCount()
            config_table.insertRow(row)
            
            slot_item = QTableWidgetItem(str(slot_id))
            model_item = QTableWidgetItem(module_info.get('model', model))
            type_item = QTableWidgetItem(module_info.get('type', module_info.get('io_type', '未知')))
            channels_item = QTableWidgetItem(str(module_info.get('channels', 0)))
            desc_item = QTableWidgetItem(module_info.get('description', ''))
            
            config_table.setItem(row, 0, slot_item)
            config_table.setItem(row, 1, model_item)
            config_table.setItem(row, 2, type_item)
            config_table.setItem(row, 3, channels_item)
            config_table.setItem(row, 4, desc_item)
            
            # 特殊高亮槽位1
            if slot_id == 1:
                color = Qt.GlobalColor.lightGray
                # if current_rack_system_type == "LE_CPU" and module_info.get('type') == "CPU":
                #     color = Qt.GlobalColor.cyan # 例如，给CPU用不同颜色
                # elif current_rack_system_type == "LK" and module_info.get('type') == "DP":
                #     color = Qt.GlobalColor.yellow # 例如，给DP用不同颜色
                
                for col in range(config_table.columnCount()):
                    item = config_table.item(row, col)
                    if item: item.setBackground(color)
        logger.debug(f"已更新机架 {current_rack_id} 的配置表格视图。")

    def get_current_configuration(self) -> List[Dict[str, Any]]:
        """获取当前配置"""
        config = []
        for (rack_id, slot_id), model in self.current_config.items():
            config.append({
                "rack_id": rack_id,
                "slot_id": slot_id,
                "model": model
            })
        return config
    
    def accept(self):
        """确认对话框，根据系统类型验证配置"""
        # 使用IODataLoader的验证逻辑，因为它已经知道系统类型
        # IODataLoader.save_configuration() 内部会进行验证
        # 我们这里可以做一个前端的快速检查，或者完全依赖后端的验证

        # 前端快速检查示例 (与IODataLoader.save_configuration中逻辑类似但可选)
        final_config_to_check = self.get_current_configuration() # 这是 [{rack_id, slot_id, model}, ...]
        
        # 转换为 IODataLoader.save_configuration 期望的字典格式 (rack_id, slot_id): model
        config_dict_for_validation = {}
        for item in final_config_to_check:
            config_dict_for_validation[(item["rack_id"], item["slot_id"])] = item["model"]

        # 将最终配置交给IODataLoader保存，它会进行最终验证
        try:
            if self.io_data_loader.save_configuration(config_dict_for_validation): # 传递字典格式
                logger.info(f"成功保存PLC配置: {len(config_dict_for_validation)} 个模块")
                super().accept()
            else:
                # IODataLoader.save_configuration 内部应该已经通过print/logger输出了错误原因
                QMessageBox.warning(self, "警告", "保存配置失败，请检查日志或控制台输出获取详细错误信息。配置可能不合法。")
        except Exception as e:
            logger.error(f"保存配置时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时出错: {str(e)}")

    def set_devices_data(self, devices_data: List[Dict[str, Any]]):
        """设置设备数据并刷新界面，包括更新系统类型"""
        if not devices_data:
            logger.warning("传入的设备数据为空")
            # 即使数据为空，也尝试获取IODataLoader的默认系统类型并创建标签页
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
        
        self.io_data_loader.set_devices_data(devices_data) # IODataLoader会计算system_type
        
        # 从IODataLoader获取更新后的系统类型和机架信息
        rack_info_updated = self.io_data_loader.get_rack_info()
        self.system_type = rack_info_updated.get('system_type', "LK")
        logger.info(f"处理设备数据后，系统类型更新为: {self.system_type}")
        
        self.create_rack_tabs() # 重新创建机架选项卡，会使用新的self.system_type
        self.load_modules()     # 重新加载模块列表
        
        logger.info(f"设备数据设置完成，UI已刷新，当前系统类型: {self.system_type}, 机架数: {self.rack_tabs.count()}")

