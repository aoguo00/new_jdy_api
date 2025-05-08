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
    """PLC配置对话框 - 支持多机架布局"""
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
        
        # 设置UI
        self.setup_ui()
        self.setup_connections()
        
        # 设置设备数据 - 移到UI设置之后，在创建机架选项卡之前
        if devices_data:
            logger.info("传入了设备数据，正在处理...")
            self.set_devices_data(devices_data)
        else:
            logger.info("未传入设备数据，创建默认的机架选项卡")
            # 创建默认的机架选项卡
            self.create_rack_tabs()
            # 加载模块数据
            self.load_modules()
        
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
        """创建机架选项卡界面"""
        # 清空现有选项卡
        self.rack_tabs.clear()
        self.rack_combo.clear()
        
        # 获取机架信息
        rack_info = self.io_data_loader.get_rack_info()
        rack_count = rack_info['rack_count']
        
        logger.info(f"创建机架选项卡: 检测到 {rack_count} 个机架")
        
        # 如果没有机架信息，默认创建一个机架
        if rack_count <= 0:
            rack_count = 1
            logger.warning("未检测到机架信息，默认创建1个机架")
        elif rack_count > 10:
            logger.warning(f"检测到异常机架数量: {rack_count}，可能是数据错误")
        
        # 更新机架下拉框
        for i in range(rack_count):
            self.rack_combo.addItem(f"机架 {i+1}")
        
        # 为每个机架创建选项卡
        for rack_id in range(1, rack_count + 1):
            # 创建机架页
            rack_page = QWidget()
            rack_layout = QVBoxLayout(rack_page)
            
            # 创建配置表格
            config_table = QTableWidget()
            config_table.setObjectName(f"rack_table_{rack_id}")
            config_table.setColumnCount(5)
            config_table.setHorizontalHeaderLabels(['槽位', '型号', '类型', '通道数', '描述'])
            config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            config_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            config_table.verticalHeader().setVisible(False)
            
            # 配置表格列宽
            header = config_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 槽位
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 型号
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 类型
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 通道数
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)          # 描述
            
            # 设置表格样式
            config_table.setStyleSheet(self.module_table.styleSheet())
            config_table.setAlternatingRowColors(True)
            
            # 添加机架信息标签
            info_label = QLabel(f"机架 {rack_id} (槽位1固定为DP模块，可配置槽位2-{rack_info['slots_per_rack']})")
            rack_layout.addWidget(info_label)
            rack_layout.addWidget(config_table)
            
            # 添加选项卡
            self.rack_tabs.addTab(rack_page, f"机架 {rack_id}")
            
            logger.debug(f"创建机架 {rack_id} 选项卡，槽位数: {rack_info['slots_per_rack']}")
        
        # 根据机架数量设置默认状态
        if rack_count > 0:
            logger.info(f"设置 {rack_count} 个机架的默认配置")
            # 预设每个机架的第一槽为DP模块
            self.set_dp_modules()
            
            # 更新所有配置表格
            self.update_all_config_tables()
            
        # 连接选项卡切换信号
        self.rack_tabs.currentChanged.connect(self.on_rack_tab_changed)
        
        # 连接组合框变化信号
        self.rack_combo.currentIndexChanged.connect(self.on_rack_combo_changed)
        
        logger.info(f"机架选项卡创建完成，共 {self.rack_tabs.count()} 个选项卡")

    def on_rack_tab_changed(self, index):
        """处理选项卡切换事件"""
        # 同步更新组合框
        self.rack_combo.setCurrentIndex(index)
        
    def on_rack_combo_changed(self, index):
        """处理机架组合框变化事件"""
        # 同步更新选项卡
        if index >= 0 and index < self.rack_tabs.count():
            self.rack_tabs.setCurrentIndex(index)

    def set_dp_modules(self):
        """设置每个机架的第一槽为DP模块"""
        # 获取机架信息
        rack_info = self.io_data_loader.get_rack_info()
        rack_count = rack_info['rack_count']
        
        for rack_id in range(1, rack_count + 1):
            # 尝试查找DP模块
            dp_modules = []
            modules, _ = self.io_data_loader.load_available_modules('DP')
            if modules:
                dp_modules = modules
            
            # 如果找到DP模块，使用第一个；否则使用PROFIBUS-DP
            dp_model = "PROFIBUS-DP"  # 默认DP模块
            if dp_modules:
                dp_model = dp_modules[0]['model']
                
            # 设置到第一槽
            self.current_config[(rack_id, 1)] = dp_model
    
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
        """加载模块列表（使用IODataLoader处理数据）"""
        try:
            # 清空表格
            self.module_table.setRowCount(0)
            
            # 获取当前选择的模块类型
            module_type = self.type_combo.currentText()
            self.module_type_filter = module_type
            
            # 从IODataLoader获取模块数据
            modules, has_data = self.io_data_loader.load_available_modules(module_type)
            
            # 保存所有可用模块（如果是首次加载）
            if not self.all_available_modules:
                # 为每个模块分配唯一ID
                for module in modules:
                    if 'unique_id' not in module:
                        module['unique_id'] = self.next_module_id
                        self.next_module_id += 1
                
                self.all_available_modules = modules.copy()
                self.current_modules_pool = modules.copy()
            
            # 过滤可用模块
            available_modules = []
            
            # 获取已配置的所有模块的唯一ID
            configured_unique_ids = []
            for module_dict in self.configured_modules.values():
                if 'unique_id' in module_dict:
                    configured_unique_ids.append(module_dict['unique_id'])
            
            # 过滤掉已经配置的模块
            for module in self.current_modules_pool:
                # 如果模块有唯一ID且不在已配置列表中，则添加到可用列表
                if 'unique_id' in module and module['unique_id'] not in configured_unique_ids:
                    # 如果有类型过滤，检查模块类型是否匹配
                    if module_type == '全部' or module.get('type', '') == module_type:
                        available_modules.append(module)
            
            # 填充表格
            if available_modules:
                self._populate_module_table(available_modules)
            else:
                self._show_no_data_message("无匹配的可用模块或所有模块已配置")
            
            logger.info(f"已加载 {len(available_modules)} 个可用模块（类型：{module_type}）")
            
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
        """添加模块到配置表"""
        selected_rows = self.module_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要添加的模块")
            return
        
        # 获取所选行
        row = selected_rows[0].row()
        
        # 检查是否有合并单元格（表示无数据提示）
        if self.module_table.rowSpan(row, 0) > 1 or self.module_table.columnSpan(row, 0) > 1:
            QMessageBox.warning(self, "提示", "无可用模块数据，请先确保有和利时模块数据")
            return
        
        # 获取模块数据
        try:
            id_item = self.module_table.item(row, 0)
            display_id = int(id_item.text())
            model = self.module_table.item(row, 1).text()
            module_type = self.module_table.item(row, 2).text()
            channels = self.module_table.item(row, 3).text()
            description = self.module_table.item(row, 4).text()
            
            # 尝试获取存储在表格项中的唯一ID
            module_unique_id = id_item.data(Qt.ItemDataRole.UserRole)
            
            # 获取完整的模块对象
            selected_module = None
            
            # 如果有唯一ID，使用唯一ID查找
            if module_unique_id is not None:
                for module in self.current_modules_pool:
                    if module.get('unique_id') == module_unique_id:
                        selected_module = module
                        break
            else:
                # 备选方案：使用行索引查找
                if row < len(self.current_modules_pool):
                    selected_module = self.current_modules_pool[row]
                    
            if not selected_module:
                logger.warning(f"未找到模块 {model} 的完整信息，使用行号 {row}")
                # 创建一个基本模块对象并分配唯一ID
                selected_module = {
                    'model': model,
                    'type': module_type,
                    'channels': channels,
                    'description': description,
                    'unique_id': self.next_module_id
                }
                self.next_module_id += 1
                logger.info(f"为模块 {model} 创建新的唯一ID: {selected_module['unique_id']}")
        except (ValueError, AttributeError) as e:
            logger.error(f"获取模块数据失败: {e}", exc_info=True)
            QMessageBox.warning(self, "提示", "无法获取选中模块的数据")
            return
        
        # 获取模块信息验证是否为DP模块
        module_info = self.io_data_loader.get_module_by_model(model)
        is_dp_module = False
        if module_info and module_info.get('type') == 'DP':
            is_dp_module = True
            
        # 检查是否为背板模块
        is_rack_module = False
        if module_info and module_info.get('type') == 'RACK':
            QMessageBox.warning(self, "提示", "背板模块不能直接添加到配置中")
            return
        
        # 获取当前机架ID
        current_rack_id = self.rack_tabs.currentIndex() + 1
        
        # 获取机架信息
        rack_info = self.io_data_loader.get_rack_info()
        slots_per_rack = rack_info['slots_per_rack']
        total_racks = rack_info['rack_count']
        
        # 查找空槽位
        found_slot = False
        assigned_slot_id = None
        
        # 如果是DP模块，只能放在槽位1
        if is_dp_module:
            # 检查槽位1是否已被占用
            if (current_rack_id, 1) in self.current_config:
                QMessageBox.warning(self, "提示", f"槽位1已被DP模块占用: {self.current_config[(current_rack_id, 1)]}")
                return
            
            # 设置到槽位1
            self.current_config[(current_rack_id, 1)] = model
            self.configured_modules[(current_rack_id, 1)] = selected_module
            assigned_slot_id = 1
            found_slot = True
            logger.info(f"将DP模块 {model} 放置在机架 {current_rack_id} 槽位 1")
        else:
            # 非DP模块，只能放在槽位2及以后
            # 查找空槽位
            for slot_id in range(2, slots_per_rack + 1):
                if (current_rack_id, slot_id) not in self.current_config:
                    # 找到空槽位
                    self.current_config[(current_rack_id, slot_id)] = model
                    self.configured_modules[(current_rack_id, slot_id)] = selected_module
                    assigned_slot_id = slot_id
                    found_slot = True
                    logger.info(f"将模块 {model} 放置在机架 {current_rack_id} 槽位 {slot_id}")
                    break
        
        # 如果没有找到空槽位
        if not found_slot:
            # 检查是否有下一个机架
            if current_rack_id < total_racks:
                next_rack_id = current_rack_id + 1
                logger.info(f"当前机架 {current_rack_id} 已满，尝试添加到机架 {next_rack_id}")
                
                # 检查下一个机架是否有空槽位
                has_empty_slot = False
                for slot_id in range(2, slots_per_rack + 1):
                    if (next_rack_id, slot_id) not in self.current_config:
                        has_empty_slot = True
                        break
                        
                if has_empty_slot:
                    reply = QMessageBox.question(
                        self, "提示", 
                        f"当前机架已满，是否添加到机架 {next_rack_id}？",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.Yes
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        self.rack_tabs.setCurrentIndex(next_rack_id - 1)
                        QTimer.singleShot(100, lambda: self.add_module())  # 延迟一点执行
                    return
                else:
                    QMessageBox.warning(self, "提示", f"机架 {next_rack_id} 也已满")
            else:
                QMessageBox.warning(self, "提示", "所有机架的可用槽位已满")
        else:
            # 从可用模块列表中移除该特定模块
            if 'unique_id' in selected_module:
                unique_id_to_remove = selected_module['unique_id']
                self.current_modules_pool = [m for m in self.current_modules_pool 
                                            if m.get('unique_id', -1) != unique_id_to_remove]
            else:
                # 作为备选方案，移除当前表格中选中的行的模块
                if row < len(self.current_modules_pool):
                    del self.current_modules_pool[row]
            
            # 更新配置表格
            self.update_current_config_table()
            
            # 更新可用模块列表
            self.load_modules()
            
            logger.info(f"模块 {model} 已从可用列表中移除，添加到机架 {current_rack_id} 槽位 {assigned_slot_id}")

    def remove_module(self):
        """从配置表中移除模块"""
        # 获取当前选中的机架
        current_rack_id = self.rack_tabs.currentIndex() + 1
        
        # 获取当前机架的表格
        config_table = self.rack_tabs.currentWidget().findChild(QTableWidget, f"rack_table_{current_rack_id}")
        if not config_table:
            return
        
        selected_rows = config_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移除的模块")
            return
        
        # 获取所选行
        row = selected_rows[0].row()
        
        # 获取槽位号
        slot_text = config_table.item(row, 0).text()
        if not slot_text.isdigit():
            return
            
        slot_id = int(slot_text)
        
        # 检查是否为槽位1（保留给DP模块）
        if slot_id == 1:
            QMessageBox.warning(self, "提示", "槽位1保留给DP模块，不能移除")
            return
        
        # 记录要移除的模块
        if (current_rack_id, slot_id) in self.current_config:
            model = self.current_config[(current_rack_id, slot_id)]
            # 获取完整的模块信息
            module_to_restore = self.configured_modules.get((current_rack_id, slot_id))
            
            # 移除配置
            del self.current_config[(current_rack_id, slot_id)]
            if (current_rack_id, slot_id) in self.configured_modules:
                del self.configured_modules[(current_rack_id, slot_id)]
            
            # 将模块添加回可用模块池
            if module_to_restore:
                # 添加回可用模块池，不需要检查重复（因为每个模块有唯一ID）
                self.current_modules_pool.append(module_to_restore)
                logger.info(f"模块 {model} 已添加回可用模块池")
            else:
                # 如果没有完整模块信息，创建一个基本的模块信息
                module_info = self.io_data_loader.get_module_by_model(model)
                if module_info:
                    # 添加唯一ID并添加到可用模块池
                    module_info['unique_id'] = self.next_module_id
                    self.next_module_id += 1
                    self.current_modules_pool.append(module_info)
                    logger.info(f"模块 {model} 的基本信息已添加回可用模块池")
                else:
                    logger.warning(f"无法获取模块 {model} 的信息，无法完全恢复到可用列表")
            
            # 更新配置表格
            self.update_current_config_table()
            
            # 更新可用模块列表
            self.load_modules()
            
            logger.info(f"从机架 {current_rack_id} 槽位 {slot_id} 移除模块 {model}")
        else:
            logger.warning(f"尝试移除不存在的配置项: 机架 {current_rack_id} 槽位 {slot_id}")

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
        """更新当前机架的配置表格"""
        # 获取当前选中的机架
        current_rack_id = self.rack_tabs.currentIndex() + 1
        
        # 获取当前机架的表格
        config_table = self.rack_tabs.currentWidget().findChild(QTableWidget, f"rack_table_{current_rack_id}")
        if not config_table:
            logger.error(f"无法找到机架 {current_rack_id} 的配置表格")
            return
        
        # 清空表格
        config_table.setRowCount(0)
        
        # 获取当前机架的配置项
        rack_config = {slot_id: model for (rack_id, slot_id), model in self.current_config.items() 
                      if rack_id == current_rack_id}
        
        # 按槽位排序
        sorted_slots = sorted(rack_config.keys())
        
        # 填充表格
        for slot_id in sorted_slots:
            model = rack_config[slot_id]
            
            # 查找模块信息
            module_info = self.io_data_loader.get_module_by_model(model)
            
            # 如果仍然找不到，使用默认值
            if not module_info:
                module_info = {
                    'model': model,
                    'type': "未知",
                    'channels': 0,
                    'description': "模块信息不完整"
                }
                
            # 添加一行到配置表格
            row = config_table.rowCount()
            config_table.insertRow(row)
            
            # 创建表格项
            slot_item = QTableWidgetItem(str(slot_id))
            model_item = QTableWidgetItem(module_info['model'])
            type_item = QTableWidgetItem(module_info.get('type', module_info.get('io_type', '未知')))
            channels_item = QTableWidgetItem(str(module_info.get('channels', 0)))
            desc_item = QTableWidgetItem(module_info.get('description', ''))
            
            # 设置表格项
            config_table.setItem(row, 0, slot_item)
            config_table.setItem(row, 1, model_item)
            config_table.setItem(row, 2, type_item)
            config_table.setItem(row, 3, channels_item)
            config_table.setItem(row, 4, desc_item)
            
            # 如果是槽位1，设置背景色
            if slot_id == 1:
                for col in range(5):
                    item = config_table.item(row, col)
                    if item:
                        item.setBackground(Qt.GlobalColor.lightGray)

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
        """确认对话框"""
        # 验证每个机架的第一槽是否都有DP模块
        rack_info = self.io_data_loader.get_rack_info()
        missing_dp = []
        
        for rack_id in range(1, rack_info['rack_count'] + 1):
            if (rack_id, 1) not in self.current_config:
                missing_dp.append(rack_id)
            else:
                # 检查槽位1的模块是否为DP类型
                model = self.current_config[(rack_id, 1)]
                module_info = self.io_data_loader.get_module_by_model(model)
                if not module_info or module_info.get('type') != 'DP':
                    missing_dp.append(rack_id)
        
        if missing_dp:
            error_msg = f"以下机架的槽位1必须配置DP模块: {', '.join(map(str, missing_dp))}"
            QMessageBox.critical(self, "错误", error_msg)
            return
        
        # 将配置保存到IODataLoader
        try:
            config = self.get_current_configuration()
            if self.io_data_loader.save_configuration(config):
                logger.info(f"成功保存PLC配置: {len(config)} 个模块")
                super().accept()
            else:
                QMessageBox.warning(self, "警告", "保存配置失败，请检查配置是否合法")
        except Exception as e:
            logger.error(f"保存配置时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时出错: {str(e)}")

    def set_devices_data(self, devices_data: List[Dict[str, Any]]):
        """设置设备数据并刷新界面"""
        if not devices_data:
            logger.warning("传入的设备数据为空")
            return
            
        logger.info(f"设置设备数据: {len(devices_data)} 个设备")
        
        # 清空现有模块状态
        self.all_available_modules = []
        self.current_modules_pool = []
        self.configured_modules = {}
        self.next_module_id = 1
        
        # 检查LK117机架的数量
        lk117_devices = []
        lk117_count = 0
        for device in devices_data:
            model = device.get('model', device.get('_widget_1635777115287', '')).upper()
            if 'LK117' in model:
                # 获取数量
                quantity_str = device.get('quantity', device.get('_widget_1635777485580', '1'))
                try:
                    if quantity_str and str(quantity_str).isdigit():
                        quantity = int(quantity_str)
                        lk117_count += quantity
                    else:
                        lk117_count += 1
                        quantity_str = '1'
                except (ValueError, TypeError):
                    lk117_count += 1
                    quantity_str = '1'
                
                # 确保设备数据中有正确的model和quantity字段
                device_copy = device.copy()
                device_copy['model'] = 'LK117'
                device_copy['quantity'] = quantity_str
                device_copy['io_type'] = 'RACK'  # 确保类型正确
                lk117_devices.append(device_copy)
                    
        logger.info(f"在设备数据中发现 {lk117_count} 个LK117机架")
        
        try:
            # 如果需要，手动添加LK117机架设备
            if lk117_count == 0:
                logger.warning("未检测到LK117机架，添加一个默认机架")
                lk117_device = {
                    'id': len(devices_data) + 1,
                    'name': 'LK117背板',
                    'model': 'LK117',
                    'brand': '和利时',
                    'quantity': '1',
                    'io_type': 'RACK',
                    'description': 'PLC机架背板'
                }
                devices_data.append(lk117_device)
                lk117_devices.append(lk117_device)
                lk117_count = 1
            
            # 确保所有的LK117设备都有正确的字段
            for device in devices_data:
                model = device.get('model', device.get('_widget_1635777115287', '')).upper()
                if 'LK117' in model:
                    # 将LK117设备标准化
                    device['model'] = 'LK117'
                    device['io_type'] = 'RACK'
                    if not device.get('quantity'):
                        device['quantity'] = device.get('_widget_1635777485580', '1')
            
            # 在传给IODataLoader前记录一下LK117的状态
            logger.info(f"将设置 {lk117_count} 个LK117机架到IODataLoader")
            for i, dev in enumerate(lk117_devices):
                logger.info(f"LK117 #{i+1}: ID={dev.get('id')}, 数量={dev.get('quantity')}")
            
            # 设置数据到加载器
            self.io_data_loader.set_devices_data(devices_data)
            
            # 获取机架信息
            rack_info = self.io_data_loader.get_rack_info()
            rack_count = rack_info.get('rack_count', 0)
            logger.info(f"IODataLoader计算得到机架数量: {rack_count}")
            
            # 确保机架数量正确
            if rack_count != lk117_count:
                logger.warning(f"机架数量不匹配: IODataLoader计算得到 {rack_count}，而实际LK117数量为 {lk117_count}")
                
                # 如果IODataLoader识别不到正确数量，可以强制设置
                if hasattr(self.io_data_loader, 'rack_count'):
                    logger.info(f"强制设置IODataLoader机架数量为: {lk117_count}")
                    self.io_data_loader.rack_count = lk117_count
                    
                    # 重新创建机架数据
                    if hasattr(self.io_data_loader, 'racks_data'):
                        self.io_data_loader.racks_data = []
                        for i in range(lk117_count):
                            rack_data = {
                                'rack_id': i + 1,
                                'rack_name': f"机架{i + 1}",
                                'total_slots': self.io_data_loader.DEFAULT_RACK_SLOTS,
                                'available_slots': self.io_data_loader.DEFAULT_RACK_SLOTS - 1,
                                'start_slot': 2,
                                'modules': []
                            }
                            self.io_data_loader.racks_data.append(rack_data)
                        logger.info(f"已重新创建 {lk117_count} 个机架数据")
                
                # 再次获取机架信息以确认设置是否生效
                rack_info = self.io_data_loader.get_rack_info()
                rack_count = rack_info.get('rack_count', 0)
                logger.info(f"设置后IODataLoader机架数量: {rack_count}")
                
        except Exception as e:
            logger.error(f"设置设备数据时出错: {e}", exc_info=True)
            # 如果出错，确保至少有一个机架
            if hasattr(self.io_data_loader, 'rack_count'):
                if self.io_data_loader.rack_count <= 0:
                    self.io_data_loader.rack_count = 1
                    if hasattr(self.io_data_loader, 'racks_data'):
                        self.io_data_loader.racks_data = [{
                            'rack_id': 1,
                            'rack_name': "机架1",
                            'total_slots': self.io_data_loader.DEFAULT_RACK_SLOTS,
                            'available_slots': self.io_data_loader.DEFAULT_RACK_SLOTS - 1,
                            'start_slot': 2,
                            'modules': []
                        }]
                    logger.warning("出错后创建了一个默认机架")
        
        # 清空当前配置
        self.current_config = {}
        logger.debug("清空当前配置")
        
        # 重新创建机架选项卡 - 现在应该能够正确识别机架数量
        logger.info("正在创建机架选项卡...")
        self.create_rack_tabs()
        
        # 加载模块列表
        self.load_modules()
        
        logger.info(f"设备数据设置完成，UI已刷新，当前机架数: {self.rack_tabs.count()}")

