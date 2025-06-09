"""
通道分配界面组件
提供交互式的点位到通道分配功能
"""

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QSplitter, QComboBox, QLineEdit,
    QFrame, QCheckBox,
    QDialog, QDialogButtonBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class PointSelectionDialog(QDialog):
    """点位选择对话框"""

    point_selected = Signal(str)  # point_id

    def __init__(self, channel_id: str, channel_type: str, available_points: List, parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.available_points = available_points
        self.selected_point_id = None

        self.setup_ui()
        self.setup_connections()
        self.load_points()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle(f"为通道 {self.channel_id} 选择点位")
        self.setModal(True)
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # 信息标签
        info_label = QLabel(f"通道：{self.channel_id} ({self.channel_type})")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(info_label)

        # 说明
        instruction_label = QLabel("双击点位完成分配，或选择点位后点击确定")
        instruction_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(instruction_label)

        # 搜索框
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("搜索："))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入仪表位号或描述...")
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 点位表格
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(3)
        self.points_table.setHorizontalHeaderLabels(["仪表位号", "描述", "信号类型"])

        # 设置表格属性
        self.points_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.points_table.setSelectionMode(QTableWidget.SingleSelection)
        self.points_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁用编辑

        # 设置列宽
        header = self.points_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        layout.addWidget(self.points_table)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        self.ok_button.setText("分配")
        self.ok_button.setEnabled(False)

        button_box.button(QDialogButtonBox.Cancel).setText("取消")
        layout.addWidget(button_box)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

    def setup_connections(self):
        """设置信号连接"""
        self.points_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.points_table.itemDoubleClicked.connect(self.on_point_double_clicked)
        self.points_table.itemClicked.connect(self.on_point_clicked)
        self.search_input.textChanged.connect(self.filter_points)

    def load_points(self):
        """加载点位数据"""
        try:
            # 过滤匹配类型的点位
            matching_points = [p for p in self.available_points if p.signal_type == self.channel_type]

            self.points_table.setRowCount(len(matching_points))

            for row, point in enumerate(matching_points):
                # 仪表位号
                self.points_table.setItem(row, 0, QTableWidgetItem(point.instrument_tag))

                # 描述
                self.points_table.setItem(row, 1, QTableWidgetItem(point.description))

                # 信号类型
                self.points_table.setItem(row, 2, QTableWidgetItem(point.signal_type))

                # 存储点位ID
                self.points_table.item(row, 0).setData(Qt.UserRole, point.id)

        except Exception as e:
            logger.error(f"加载点位数据失败: {e}")

    def filter_points(self):
        """过滤点位 - 支持类型过滤和搜索过滤"""
        try:
            # 获取过滤条件
            selected_type = self.type_filter.currentText()
            search_text = self.search_input.text().lower().strip()

            for row in range(self.points_table.rowCount()):
                # 获取行数据
                tag_item = self.points_table.item(row, 0)  # 仪表位号
                desc_item = self.points_table.item(row, 1)  # 描述
                signal_type_item = self.points_table.item(row, 2)  # 信号类型

                if not tag_item or not desc_item:
                    continue

                # 类型过滤
                type_match = True
                if selected_type != "全部" and signal_type_item:
                    signal_type = signal_type_item.text().upper()
                    type_match = (signal_type == selected_type.upper())

                # 搜索过滤
                search_match = True
                if search_text:
                    tag_text = tag_item.text().lower()
                    desc_text = desc_item.text().lower()
                    search_match = (search_text in tag_text or search_text in desc_text)

                # 显示/隐藏行
                visible = type_match and search_match
                self.points_table.setRowHidden(row, not visible)

        except Exception as e:
            logger.error(f"过滤点位失败: {e}")

    def on_selection_changed(self):
        """选择变化"""
        selected_items = self.points_table.selectedItems()
        self.ok_button.setEnabled(len(selected_items) > 0)

    def on_point_clicked(self, item):
        """单击点位 - 选择该行"""
        # 获取当前行的第一列项目（包含点位ID）
        row = self.points_table.row(item)
        first_col_item = self.points_table.item(row, 0)

        if first_col_item:
            point_id = first_col_item.data(Qt.UserRole)
            if point_id:
                self.selected_point_id = point_id
                # 选择整行
                self.points_table.selectRow(row)

    def on_point_double_clicked(self, item):
        """双击点位"""
        # 获取当前行的第一列项目（包含点位ID）
        row = self.points_table.row(item)
        first_col_item = self.points_table.item(row, 0)

        if first_col_item:
            point_id = first_col_item.data(Qt.UserRole)
            if point_id:
                self.selected_point_id = point_id
                self.accept()

    def accept(self):
        """确定按钮"""
        if not self.selected_point_id:
            # 获取当前选择的点位
            current_row = self.points_table.currentRow()
            if current_row >= 0:
                # 总是从第一列获取点位ID
                first_col_item = self.points_table.item(current_row, 0)
                if first_col_item:
                    self.selected_point_id = first_col_item.data(Qt.UserRole)

        if self.selected_point_id:
            self.point_selected.emit(self.selected_point_id)

        super().accept()


class DraggablePointItem(QTableWidgetItem):
    """可拖拽的点位项"""
    
    def __init__(self, text: str, point_data: Dict[str, Any]):
        super().__init__(text)
        self.point_data = point_data
        self.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)


class ChannelTableWidget(QTableWidget):
    """通道表格组件"""
    
    channel_assigned = Signal(str, str)  # point_id, channel_id
    
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragDropMode(QTableWidget.DropOnly)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasText():
            # 获取拖拽的点位数据
            point_id = event.mimeData().text()
            
            # 获取目标通道
            item = self.itemAt(event.pos())
            if item:
                row = self.row(item)
                channel_item = self.item(row, 0)  # 通道ID在第0列
                if channel_item:
                    channel_id = channel_item.text()
                    self.channel_assigned.emit(point_id, channel_id)
            
            event.acceptProposedAction()
        else:
            event.ignore()


class ChannelAssignmentWidget(QWidget):
    """通道分配界面主组件"""
    
    # 信号定义
    assignment_completed = Signal(str)  # scheme_id
    
    def __init__(self):
        super().__init__()
        self.current_project_id = None
        self.current_scheme_id = None
        self.parsed_points = []
        self.available_channels = {}
        self.assignments = {}  # point_id -> channel_id

        # 初始化数据访问对象
        from core.channel_assignment.persistence.assignment_dao import AssignmentDAO
        from core.data_storage.parsed_data_dao import ParsedDataDAO
        self.assignment_dao = AssignmentDAO()
        self.parsed_data_dao = ParsedDataDAO()

        self.setup_ui()
        self.setup_connections()

        logger.info("ChannelAssignmentWidget initialized")
    
    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout(self)
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel("通道分配（含文档导入）")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        layout.addLayout(title_layout)
        
        # 信息面板
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel)
        info_layout = QHBoxLayout(info_frame)
        
        self.project_info_label = QLabel("项目：未选择")
        self.points_info_label = QLabel("点位：0 个")
        self.assigned_info_label = QLabel("已分配：0 个")
        self.progress_label = QLabel("进度：0%")
        
        info_layout.addWidget(self.project_info_label)
        info_layout.addWidget(QLabel("|"))
        info_layout.addWidget(self.points_info_label)
        info_layout.addWidget(QLabel("|"))
        info_layout.addWidget(self.assigned_info_label)
        info_layout.addWidget(QLabel("|"))
        info_layout.addWidget(self.progress_label)
        info_layout.addStretch()
        
        layout.addWidget(info_frame)
        
        # 主分割器 - 垂直分割（上下布局）
        main_splitter = QSplitter(Qt.Vertical)

        # 上半部分：解析的点位列表（占70%空间）
        top_widget = self.create_points_panel()
        main_splitter.addWidget(top_widget)

        # 下半部分：通道分配区域（占30%空间）
        bottom_widget = self.create_bottom_assignment_area()
        main_splitter.addWidget(bottom_widget)

        # 设置分割器比例 - 上40%，下60%，给通道区域更多空间
        main_splitter.setStretchFactor(0, 4)  # 点位列表
        main_splitter.setStretchFactor(1, 6)  # 通道分配区域

        layout.addWidget(main_splitter)
        
        # 底部操作区域
        bottom_layout = self.create_bottom_panel()
        layout.addLayout(bottom_layout)
    
    def create_points_panel(self) -> QWidget:
        """创建点位列表面板"""
        group = QGroupBox("解析的点位")
        layout = QVBoxLayout(group)

        # 文档导入区域
        import_frame = self.create_document_import_area()
        layout.addWidget(import_frame)

        # 过滤器
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("类型过滤："))

        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部", "AI", "DI", "AO", "DO", "COMM"])
        filter_layout.addWidget(self.type_filter)

        filter_layout.addWidget(QLabel("搜索："))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入仪表位号或描述...")
        filter_layout.addWidget(self.search_input)

        layout.addLayout(filter_layout)

        # 点位表格 - 显示所有解析到的数据列
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(9)
        self.points_table.setHorizontalHeaderLabels([
            "仪表位号", "描述", "信号类型", "信号范围", "数据范围",
            "单位", "供电类型", "隔离", "状态"
        ])

        # 设置表格属性
        self.points_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.points_table.setDragEnabled(True)
        self.points_table.setDragDropMode(QTableWidget.DragOnly)
        self.points_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁用编辑

        # 设置列宽
        header = self.points_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 仪表位号
        header.setSectionResizeMode(1, QHeaderView.Stretch)           # 描述
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 信号类型
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 信号范围
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 数据范围
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 单位
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 供电类型
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 隔离
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # 状态

        layout.addWidget(self.points_table)

        # 统计信息
        self.points_stats_label = QLabel("统计：AI: 0, DI: 0, AO: 0, DO: 0")
        layout.addWidget(self.points_stats_label)

        return group

    def create_document_import_area(self) -> QWidget:
        """创建文档导入区域"""
        import_frame = QFrame()
        import_frame.setFrameStyle(QFrame.StyledPanel)
        import_frame.setMaximumHeight(80)
        import_layout = QHBoxLayout(import_frame)
        import_layout.setContentsMargins(8, 8, 8, 8)

        # 上传按钮
        self.upload_btn = QPushButton("📁 上传Word文档")
        self.upload_btn.setMaximumHeight(30)
        self.upload_btn.setMinimumWidth(120)
        self.upload_btn.clicked.connect(self.select_and_parse_document)
        import_layout.addWidget(self.upload_btn)

        # 文件状态标签
        self.file_status_label = QLabel("请上传Word文档或拖拽文件到此区域")
        self.file_status_label.setStyleSheet("color: #666; font-style: italic;")
        import_layout.addWidget(self.file_status_label, 1)

        # 解析状态标签
        self.parse_status_label = QLabel("")
        self.parse_status_label.setStyleSheet("color: #2196F3; font-weight: bold;")
        import_layout.addWidget(self.parse_status_label)

        # 启用拖拽功能
        import_frame.setAcceptDrops(True)
        import_frame.dragEnterEvent = self.dragEnterEvent
        import_frame.dropEvent = self.dropEvent

        return import_frame

    def create_bottom_assignment_area(self) -> QWidget:
        """创建下半部分的通道分配区域"""
        # 只返回通道列表面板，删除右侧分配操作区域
        channels_widget = self.create_channels_panel()
        return channels_widget


    
    def create_channels_panel(self) -> QWidget:
        """创建通道列表面板"""
        group = QGroupBox("可用通道")
        layout = QVBoxLayout(group)
        
        # 通道类型选择和导入按钮
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("通道类型："))

        self.channel_type_combo = QComboBox()
        self.channel_type_combo.addItems(["AI", "DI", "AO", "DO"])
        type_layout.addWidget(self.channel_type_combo)

        type_layout.addWidget(QLabel("显示："))
        self.show_available_only = QCheckBox("仅显示可用")
        self.show_available_only.setChecked(True)
        type_layout.addWidget(self.show_available_only)

        # 添加导入IO模板按钮
        self.import_template_btn = QPushButton("导入IO模板")
        self.import_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        type_layout.addWidget(self.import_template_btn)

        # 添加自动分配按钮
        self.auto_assign_btn = QPushButton("自动分配")
        self.auto_assign_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
        """)
        type_layout.addWidget(self.auto_assign_btn)

        # 添加清空分配按钮
        self.clear_assignments_btn = QPushButton("清空分配")
        self.clear_assignments_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        type_layout.addWidget(self.clear_assignments_btn)

        # 添加显示模式切换按钮
        self.mode_toggle_btn = QPushButton("📋 显示所有点位")
        self.mode_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        type_layout.addWidget(self.mode_toggle_btn)

        type_layout.addStretch()

        # 显示模式：True=仅显示未分配，False=显示所有点位
        self.show_unassigned_only = True
        layout.addLayout(type_layout)
        
        # 通道表格
        self.channels_table = ChannelTableWidget()
        self.channels_table.setColumnCount(7)
        self.channels_table.setHorizontalHeaderLabels(["通道", "状态", "仪表位号", "描述", "信号类型", "信号范围", "数据范围"])

        # 设置表格属性
        self.channels_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.channels_table.setEditTriggers(QTableWidget.NoEditTriggers)  # 禁用编辑
        
        # 设置列宽
        header = self.channels_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 通道
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 仪表位号
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # 描述
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 信号类型
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 信号范围
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 数据范围
        
        layout.addWidget(self.channels_table)
        
        # 通道统计
        self.channel_stats_label = QLabel("📋 请先生成IO点表模板，然后点击'导入IO模板'按钮")
        layout.addWidget(self.channel_stats_label)
        
        return group
    
    def create_bottom_panel(self) -> QHBoxLayout:
        """创建底部操作面板"""
        layout = QHBoxLayout()
        layout.addStretch()  # 添加弹性空间，让布局居中

        # 完成分配按钮
        self.complete_btn = QPushButton("完成分配")
        self.complete_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")
        self.complete_btn.setMinimumWidth(120)
        layout.addWidget(self.complete_btn)

        return layout
    
    def setup_connections(self):
        """设置信号连接"""
        # 基本连接（移除返回按钮连接）
        
        # 表格选择变化
        self.points_table.itemSelectionChanged.connect(self.on_point_selection_changed)
        self.channels_table.itemSelectionChanged.connect(self.on_channel_selection_changed)

        # 通道表格点击事件
        self.channels_table.itemClicked.connect(self.on_channel_clicked)

        # 双击分配
        self.points_table.itemDoubleClicked.connect(self.on_point_double_clicked)
        
        # 过滤器
        self.type_filter.currentTextChanged.connect(self.filter_points)
        self.search_input.textChanged.connect(self.filter_points)
        self.channel_type_combo.currentTextChanged.connect(self.update_channels_display)
        

        
        # 通道拖拽分配
        self.channels_table.channel_assigned.connect(self.assign_point_to_channel)
        
        # 完成操作
        self.complete_btn.clicked.connect(self.complete_assignment)

        # 导入IO模板按钮
        self.import_template_btn.clicked.connect(self.import_io_template)

        # 自动分配按钮
        self.auto_assign_btn.clicked.connect(self.auto_assign_all_points)

        # 清空分配按钮
        self.clear_assignments_btn.clicked.connect(self.clear_all_assignments)

        # 显示模式切换按钮
        self.mode_toggle_btn.clicked.connect(self.toggle_display_mode)

        # 启用拖拽功能
        self.setAcceptDrops(True)
    
    def load_project_data(self, project_id: str, scheme_id: str):
        """加载项目数据和分配方案，同时需要PLC模板数据"""
        try:
            self.current_project_id = project_id
            self.current_scheme_id = scheme_id

            # 导入数据访问对象
            from core.data_storage.parsed_data_dao import ParsedDataDAO
            from core.channel_assignment.persistence.assignment_dao import AssignmentDAO

            self.parsed_data_dao = ParsedDataDAO()
            self.assignment_dao = AssignmentDAO()

            # 加载解析的点位数据
            self.parsed_points = self.parsed_data_dao.get_parsed_points(project_id)

            # 加载分配方案
            assignment = self.assignment_dao.load_assignment(project_id, scheme_id)

            # 构建分配映射
            self.assignments = {}
            if assignment:
                for mapping in assignment.assignments:
                    self.assignments[mapping.point_id] = mapping.channel_id

            # 检查是否有PLC模板数据
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                logger.info("没有PLC模板数据，用户需要手动导入")

            # 更新界面显示
            project = self.parsed_data_dao.get_project(project_id)
            project_name = project.name if project else f"项目_{project_id[:8]}"

            self.project_info_label.setText(f"项目：{project_name}")
            self.points_info_label.setText(f"点位：{len(self.parsed_points)} 个")
            self.assigned_info_label.setText(f"已分配：{len(self.assignments)} 个")

            # 计算进度
            progress = 0
            if self.parsed_points:
                progress = int((len(self.assignments) / len(self.parsed_points)) * 100)
            self.progress_label.setText(f"进度：{progress}%")

            # 加载点位表格
            self.load_points_table()

            # 加载通道表格（基于PLC模板）
            self.load_channels_table()

            # 方案管理功能已删除

            logger.info(f"成功加载项目数据: {len(self.parsed_points)} 个点位, {len(self.assignments)} 个分配")

        except Exception as e:
            logger.error(f"加载项目数据失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"加载项目数据失败：\n{str(e)}")





    def set_plc_template_data(self, plc_template_data: List[Dict[str, Any]]):
        """设置PLC模板数据"""
        self.plc_template_data = plc_template_data
        logger.info(f"设置PLC模板数据: {len(plc_template_data)} 个通道")

        # 如果已经有项目数据，重新加载界面
        if hasattr(self, 'current_project_id') and self.current_project_id:
            self.load_channels_table()

    def toggle_display_mode(self):
        """切换显示模式"""
        try:
            self.show_unassigned_only = not self.show_unassigned_only

            if self.show_unassigned_only:
                self.mode_toggle_btn.setText("📋 显示所有点位")
            else:
                self.mode_toggle_btn.setText("📋 仅显示未分配")

            # 重新加载点位表格
            self.load_points_table()

            logger.info(f"切换显示模式: {'仅显示未分配' if self.show_unassigned_only else '显示所有点位'}")

        except Exception as e:
            logger.error(f"切换显示模式失败: {e}")

    def load_points_table(self):
        """加载点位表格"""
        try:
            # 清空表格
            self.points_table.setRowCount(0)

            if not self.parsed_points:
                return

            # 根据显示模式过滤点位
            display_points = []
            for point in self.parsed_points:
                if self.show_unassigned_only:
                    # 仅显示未分配的点位
                    if point.id not in self.assignments:
                        display_points.append(point)
                else:
                    # 显示所有点位
                    display_points.append(point)

            # 设置行数
            self.points_table.setRowCount(len(display_points))

            # 填充数据 - 显示所有解析到的列
            for row, point in enumerate(display_points):
                # 0. 仪表位号
                self.points_table.setItem(row, 0, QTableWidgetItem(point.instrument_tag))

                # 1. 描述
                self.points_table.setItem(row, 1, QTableWidgetItem(point.description))

                # 2. 信号类型
                self.points_table.setItem(row, 2, QTableWidgetItem(point.signal_type))

                # 3. 信号范围
                signal_range = getattr(point, 'signal_range', '') or ''
                self.points_table.setItem(row, 3, QTableWidgetItem(signal_range))

                # 4. 数据范围
                data_range = getattr(point, 'data_range', '') or ''
                self.points_table.setItem(row, 4, QTableWidgetItem(data_range))

                # 5. 单位
                units = getattr(point, 'units', '') or ''
                self.points_table.setItem(row, 5, QTableWidgetItem(units))

                # 6. 供电类型
                power_supply = getattr(point, 'power_supply', '') or ''
                self.points_table.setItem(row, 6, QTableWidgetItem(power_supply))

                # 7. 隔离
                isolation = getattr(point, 'isolation', '') or ''
                self.points_table.setItem(row, 7, QTableWidgetItem(isolation))

                # 8. 状态
                status = "已分配" if point.id in self.assignments else "未分配"
                status_item = QTableWidgetItem(status)
                if status == "已分配":
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.yellow)
                self.points_table.setItem(row, 8, status_item)

                # 存储点位ID用于后续操作
                self.points_table.item(row, 0).setData(Qt.UserRole, point.id)

            # 更新统计
            self.update_points_statistics()

        except Exception as e:
            logger.error(f"加载点位表格失败: {e}")

    def load_channels_table(self):
        """基于PLC模板数据加载通道表格"""
        try:
            # 检查是否有PLC模板数据
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                self.channels_table.setRowCount(0)
                self.channel_stats_label.setText("📋 请先生成IO点表模板，然后点击'导入IO模板'按钮")
                return

            # 获取当前选择的通道类型
            channel_type = self.channel_type_combo.currentText()

            # 从PLC模板数据中提取对应类型的通道
            template_channels = []
            for template_point in self.plc_template_data:
                point_type = template_point.get('type', '')
                if point_type == channel_type:
                    template_channels.append(template_point)

            # 清空表格
            self.channels_table.setRowCount(0)

            if not template_channels:
                self.channel_stats_label.setText(f"统计：{channel_type} 类型无可用通道")
                return

            # 获取已使用的通道
            used_channels = set(self.assignments.values())

            # 设置行数
            display_channels = []
            for channel in template_channels:
                channel_id = channel.get('address', '')
                is_available = channel_id not in used_channels

                # 显示所有通道，包括已分配的通道
                display_channels.append({
                    'id': channel_id,
                    'is_available': is_available,
                    'template_data': channel
                })

            self.channels_table.setRowCount(len(display_channels))

            # 填充数据
            for row, channel in enumerate(display_channels):
                # 通道
                self.channels_table.setItem(row, 0, QTableWidgetItem(channel['id']))

                # 状态
                status = "可用" if channel['is_available'] else "已用"
                status_item = QTableWidgetItem(status)
                if status == "可用":
                    status_item.setBackground(Qt.green)
                else:
                    status_item.setBackground(Qt.red)
                self.channels_table.setItem(row, 1, status_item)

                # 查找分配到此通道的点位信息
                assigned_point = None
                if not channel['is_available']:
                    for point_id, channel_id in self.assignments.items():
                        if channel_id == channel['id']:
                            # 查找点位详细信息
                            for point in self.parsed_points:
                                if point.id == point_id:
                                    assigned_point = point
                                    break
                            break

                # 仪表位号
                instrument_tag = assigned_point.instrument_tag if assigned_point else ""
                self.channels_table.setItem(row, 2, QTableWidgetItem(instrument_tag))

                # 描述
                description = assigned_point.description if assigned_point else ""
                self.channels_table.setItem(row, 3, QTableWidgetItem(description))

                # 信号类型
                signal_type = assigned_point.signal_type if assigned_point else ""
                self.channels_table.setItem(row, 4, QTableWidgetItem(signal_type))

                # 信号范围
                signal_range = assigned_point.signal_range if assigned_point else ""
                self.channels_table.setItem(row, 5, QTableWidgetItem(signal_range))

                # 数据范围
                data_range = assigned_point.data_range if assigned_point else ""
                self.channels_table.setItem(row, 6, QTableWidgetItem(data_range))

            # 更新统计
            self.update_channel_statistics_from_template()

        except Exception as e:
            logger.error(f"加载通道表格失败: {e}")

    def update_channel_statistics_from_template(self):
        """基于PLC模板更新通道统计"""
        try:
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                self.channel_stats_label.setText("统计：无PLC模板数据")
                return

            channel_type = self.channel_type_combo.currentText()
            used_channels = set(self.assignments.values())

            # 统计该类型的总通道数
            total = 0
            for template_point in self.plc_template_data:
                if template_point.get('type', '') == channel_type:
                    total += 1

            # 统计已使用的通道数
            used = 0
            for template_point in self.plc_template_data:
                if (template_point.get('type', '') == channel_type and
                    template_point.get('address', '') in used_channels):
                    used += 1

            available = total - used
            self.channel_stats_label.setText(f"统计：总计: {total}, 可用: {available}, 已用: {used}")

        except Exception as e:
            logger.error(f"更新通道统计失败: {e}")

    def update_points_statistics(self):
        """更新点位统计"""
        try:
            if not self.parsed_points:
                self.points_stats_label.setText("统计：AI: 0, DI: 0, AO: 0, DO: 0")
                return

            # 按类型统计
            stats = {}
            for point in self.parsed_points:
                signal_type = point.signal_type
                if signal_type not in stats:
                    stats[signal_type] = 0
                stats[signal_type] += 1

            # 格式化显示
            stats_text = "统计："
            for signal_type in ['AI', 'DI', 'AO', 'DO']:
                count = stats.get(signal_type, 0)
                stats_text += f" {signal_type}: {count},"

            # 添加其他类型
            for signal_type, count in stats.items():
                if signal_type not in ['AI', 'DI', 'AO', 'DO']:
                    stats_text += f" {signal_type}: {count},"

            stats_text = stats_text.rstrip(',')
            self.points_stats_label.setText(stats_text)

        except Exception as e:
            logger.error(f"更新点位统计失败: {e}")

    def update_channel_statistics(self):
        """更新通道统计"""
        try:
            channel_type = self.channel_type_combo.currentText()
            used_channels = set(self.assignments.values())
            available_channels = self.channel_provider.get_available_channels(channel_type, used_channels)

            total = len(available_channels)
            used = len([ch for ch in available_channels if not ch.is_available])
            available = total - used

            self.channel_stats_label.setText(f"统计：总计: {total}, 可用: {available}, 已用: {used}")

        except Exception as e:
            logger.error(f"更新通道统计失败: {e}")



    def on_point_double_clicked(self, item):
        """双击点位自动分配到对应类型的可用通道"""
        try:
            # 获取当前行的第一列项目（包含点位ID）
            row = self.points_table.row(item)

            # 获取点位ID（从第一列获取）
            first_col_item = self.points_table.item(row, 0)
            if not first_col_item:
                logger.error("无法获取第一列项目")
                return

            point_id = first_col_item.data(Qt.UserRole)
            if not point_id:
                logger.error("无法获取点位ID")
                return

            # 查找点位信息
            point = next((p for p in self.parsed_points if p.id == point_id), None)
            if not point:
                logger.error(f"未找到点位: {point_id}")
                return

            # 检查是否已分配
            if point_id in self.assignments:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "已分配", f"点位 {point.instrument_tag} 已分配到通道 {self.assignments[point_id]}")
                return

            # 查找对应类型的第一个可用通道
            signal_type = point.signal_type
            available_channel = self.find_first_available_channel(signal_type)

            if not available_channel:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "无可用通道", f"没有可用的 {signal_type} 类型通道")
                return

            # 执行分配
            self.assign_point_to_channel(point_id, available_channel)

        except Exception as e:
            logger.error(f"双击分配失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "分配失败", f"双击分配失败：\n{str(e)}")

    def find_first_available_channel(self, signal_type: str) -> str:
        """查找指定类型的第一个可用通道"""
        try:
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                return ""

            used_channels = set(self.assignments.values())

            # 查找对应类型的可用通道
            for template_point in self.plc_template_data:
                if (template_point.get('type', '') == signal_type and
                    template_point.get('address', '') not in used_channels):
                    return template_point.get('address', '')

            return ""

        except Exception as e:
            logger.error(f"查找可用通道失败: {e}")
            return ""

    def on_channel_clicked(self, item):
        """通道被点击时，弹出点位选择对话框"""
        try:
            # 获取通道信息
            row = self.channels_table.row(item)
            channel_item = self.channels_table.item(row, 0)
            status_item = self.channels_table.item(row, 1)

            if not channel_item or not status_item:
                return

            channel_id = channel_item.text()
            status = status_item.text()

            # 检查通道是否已被使用 - 允许重新分配
            if status == "已用":
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, "通道已使用",
                    f"通道 {channel_id} 已被分配。\n\n是否要重新分配此通道？",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return

                # 🔥 修复：重新分配时显示所有相同信号类型的点位
                # 获取通道类型
                channel_type = self.get_channel_type(channel_id)
                if not channel_type:
                    QMessageBox.warning(self, "错误", f"无法确定通道 {channel_id} 的类型")
                    return

                # 获取当前分配的点位ID
                current_assigned_point_id = None
                for point_id, assigned_channel_id in self.assignments.items():
                    if assigned_channel_id == channel_id:
                        current_assigned_point_id = point_id
                        break

                # 显示所有相同信号类型的点位（包括已分配的），用于重新分配
                available_points = []
                for point in self.parsed_points:
                    if point.signal_type == channel_type:
                        available_points.append(point)

                if not available_points:
                    QMessageBox.information(self, "无可分配点位", f"没有 {channel_type} 类型的点位")
                    return

                # 弹出重新分配对话框
                dialog = PointExchangeDialog(channel_id, channel_type, available_points, current_assigned_point_id, self)
                dialog.point_exchange_requested.connect(
                    lambda target_point_id: self.reassign_channel_to_point(channel_id, target_point_id)
                )
                dialog.exec()
                return

            # 获取通道类型
            channel_type = self.get_channel_type(channel_id)

            # 获取可分配的点位
            available_points = []

            # 正常分配，只显示未分配的点位
            for point in self.parsed_points:
                if (point.id not in self.assignments and
                    point.signal_type == channel_type):
                    available_points.append(point)

            if not available_points:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "无可分配点位", f"没有可分配的 {channel_type} 类型点位")
                return

            # 弹出点位选择对话框
            dialog = PointSelectionDialog(channel_id, channel_type, available_points, self)
            # 🔥 修复：重新分配时允许覆盖现有分配
            is_reassign = (status == "已用")
            dialog.point_selected.connect(lambda point_id: self.assign_point_to_channel(point_id, channel_id, allow_reassign=is_reassign))
            dialog.exec()

        except Exception as e:
            logger.error(f"处理通道点击失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"处理通道点击失败：\n{str(e)}")

    # 占位方法 - 后续实现具体逻辑
    def on_point_selection_changed(self): pass
    def on_channel_selection_changed(self): pass
    def update_channels_display(self):
        """更新通道显示"""
        self.load_channels_table()

    def filter_points(self):
        """过滤点位 - 支持类型过滤和搜索过滤"""
        try:
            # 获取过滤条件
            selected_type = self.type_filter.currentText()
            search_text = self.search_input.text().lower().strip()

            for row in range(self.points_table.rowCount()):
                # 获取行数据
                tag_item = self.points_table.item(row, 0)  # 仪表位号
                desc_item = self.points_table.item(row, 1)  # 描述
                signal_type_item = self.points_table.item(row, 2)  # 信号类型

                if not tag_item or not desc_item:
                    continue

                # 类型过滤
                type_match = True
                if selected_type != "全部" and signal_type_item:
                    signal_type = signal_type_item.text().upper()
                    type_match = (signal_type == selected_type.upper())

                # 搜索过滤
                search_match = True
                if search_text:
                    tag_text = tag_item.text().lower()
                    desc_text = desc_item.text().lower()
                    search_match = (search_text in tag_text or search_text in desc_text)

                # 显示/隐藏行
                visible = type_match and search_match
                self.points_table.setRowHidden(row, not visible)

        except Exception as e:
            logger.error(f"过滤点位失败: {e}")


    def assign_point_to_channel(self, point_id: str, channel_id: str, allow_reassign: bool = False) -> bool:
        """分配点位到通道"""
        try:
            # 验证点位
            point = next((p for p in self.parsed_points if p.id == point_id), None)
            if not point:
                logger.error(f"未找到点位: {point_id}")
                return False

            # 从PLC模板数据中验证通道
            channel_info = None
            if hasattr(self, 'plc_template_data') and self.plc_template_data:
                for template_point in self.plc_template_data:
                    if template_point.get('address', '') == channel_id:
                        channel_info = template_point
                        break

            if not channel_info:
                logger.error(f"通道 {channel_id} 在PLC模板中不存在")
                return False

            # 检查信号类型匹配
            channel_type = channel_info.get('type', '')
            if point.signal_type != channel_type:
                logger.error(f"点位信号类型 {point.signal_type} 与通道类型 {channel_type} 不匹配")
                return False

            # 🔥 修复：检查通道是否已被使用（重新分配时允许）
            if not allow_reassign and channel_id in self.assignments.values():
                logger.error(f"通道 {channel_id} 已被其他点位使用")
                return False

            # 🔥 如果是重新分配，先清除该通道的现有分配
            if allow_reassign and channel_id in self.assignments.values():
                # 找到并移除现有分配
                existing_point_id = None
                for pid, cid in self.assignments.items():
                    if cid == channel_id:
                        existing_point_id = pid
                        break

                if existing_point_id:
                    del self.assignments[existing_point_id]
                    logger.info(f"清除通道 {channel_id} 的现有分配: {existing_point_id}")

            # 执行分配
            success = self.assignment_dao.add_point_assignment(
                self.current_project_id, self.current_scheme_id,
                point_id, channel_id, channel_type
            )

            if success:
                # 更新本地分配映射
                self.assignments[point_id] = channel_id

                # 刷新界面
                self.load_points_table()
                self.load_channels_table()

                # 更新进度
                progress = int((len(self.assignments) / len(self.parsed_points)) * 100)
                self.assigned_info_label.setText(f"已分配：{len(self.assignments)} 个")
                self.progress_label.setText(f"进度：{progress}%")

                logger.info(f"成功分配点位 {point.instrument_tag} 到通道 {channel_id}")
                return True
            else:
                logger.error("分配点位到通道失败")
                return False

        except Exception as e:
            logger.error(f"分配点位到通道失败: {e}")
            return False

    def exchange_point_assignments(self, current_point_id: str, target_point_id: str, current_channel_id: str):
        """交换两个点位的通道分配"""
        try:
            # 🔥 修复：如果current_point_id为None，说明通道未分配，这是错误状态
            if current_point_id is None:
                logger.error(f"通道 {current_channel_id} 没有找到当前分配的点位")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "错误", f"通道 {current_channel_id} 没有找到当前分配的点位")
                return

            # 如果选择的是同一个点位，不需要交换
            if current_point_id == target_point_id:
                logger.info("选择了相同的点位，无需交换")
                return

            # 找到目标点位当前分配的通道
            target_channel_id = self.assignments.get(target_point_id)

            if target_channel_id:
                # 情况1：两个点位都已分配，进行交换
                logger.info(f"交换分配: {current_point_id} ({current_channel_id}) <-> {target_point_id} ({target_channel_id})")

                # 🔥 修复：先移除旧分配，再添加新分配
                if current_point_id in self.assignments:
                    del self.assignments[current_point_id]
                if target_point_id in self.assignments:
                    del self.assignments[target_point_id]

                # 添加新分配
                self.assignments[current_point_id] = target_channel_id
                self.assignments[target_point_id] = current_channel_id

                logger.info("点位交换完成")
            else:
                # 情况2：目标点位未分配，直接重新分配
                logger.info(f"重新分配: {target_point_id} -> {current_channel_id}")

                # 移除当前分配
                if current_point_id in self.assignments:
                    del self.assignments[current_point_id]

                # 分配新点位
                self.assignments[target_point_id] = current_channel_id

                logger.info("点位重新分配完成")

            # 🔥 修复：更新数据库
            if hasattr(self, 'current_scheme_id') and self.current_scheme_id:
                self.assignment_dao.update_assignments(self.current_scheme_id, self.assignments)

            # 🔥 修复：强制刷新界面
            self.load_points_table()
            self.load_channels_table()

            # 更新进度
            progress = int((len(self.assignments) / len(self.parsed_points)) * 100) if self.parsed_points else 0
            self.assigned_info_label.setText(f"已分配：{len(self.assignments)} 个")
            self.progress_label.setText(f"进度：{progress}%")

            logger.info(f"界面刷新完成，当前分配数量: {len(self.assignments)}")

        except Exception as e:
            logger.error(f"交换点位分配失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"交换点位分配失败：\n{str(e)}")

    def complete_assignment(self):
        """完成分配，生成自动填写的IO点表"""
        try:
            if not self.assignments:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "无分配数据", "请先分配点位到通道")
                return

            # 🔥 修复：去掉验证弹窗，但仍需要模板数据
            # 用户可以直接使用设计文件导入或之前生成的IO模板
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "缺少模板数据",
                                  "请先导入IO模板文件。\n\n"
                                  "您可以：\n"
                                  "1. 导入之前生成的IO模板文件\n"
                                  "2. 先生成IO模板，再进行通道分配")
                return

            # 🔥 修复：优先从原始模板获取场站信息，避免使用默认值覆盖
            site_name, site_no = self._get_site_info_from_template_or_main_window()
            logger.info(f"最终使用的场站信息: 名称='{site_name}', 编号='{site_no}'")

            # 基于分配结果和PLC模板生成填写的IO点表
            filled_plc_data = self.generate_filled_plc_data()

            if not filled_plc_data:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "数据生成失败", "无法生成填写的PLC数据")
                return

            # 获取第三方设备数据
            third_party_data = self._get_third_party_data()

            # 生成Excel文件
            from core.io_table.excel_exporter import IOExcelExporter
            from datetime import datetime
            import os

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"通道分配结果_{timestamp}.xlsx"

            # 确保输出目录存在
            output_dir = os.path.join(os.getcwd(), "通道分配结果")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, filename)

            exporter = IOExcelExporter()
            success = exporter.export_to_excel(
                plc_io_data=filled_plc_data,
                third_party_data=third_party_data,
                filename=output_path,
                site_name=site_name,
                site_no=site_no
            )

            if success:
                from PySide6.QtWidgets import QMessageBox
                reply = QMessageBox.question(
                    self, "生成成功",
                    f"已生成通道分配结果IO点表：\n{output_path}\n\n是否打开文件夹？",
                    QMessageBox.Yes | QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    import subprocess
                    import platform

                    folder_path = os.path.dirname(output_path)
                    if platform.system() == "Windows":
                        subprocess.run(["explorer", folder_path])
                    elif platform.system() == "Darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])

                # 发出完成信号
                self.assignment_completed.emit(self.current_scheme_id)

            else:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "生成失败", "生成IO点表失败")

        except Exception as e:
            logger.error(f"完成分配失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"完成分配失败：\n{str(e)}")

    def generate_filled_plc_data(self) -> List[Dict[str, Any]]:
        """基于分配结果生成填写的PLC数据 - 只处理灰色高亮字段"""
        try:
            filled_data = []

            # 🔥 修复：遍历原始模板的所有通道，而不是只遍历已分配的点位
            # 这样可以确保生成的IO点表包含所有通道，与原始模板保持一致
            for template_point in self.plc_template_data:
                channel_id = template_point.get('address', '')

                # 🔥 修复：完整保留原始模板数据，并正确映射字段名
                filled_point = template_point.copy()

                # 🔥 修复：映射导出器需要的所有字段，但只在灰色高亮字段中填入分配数据
                # 策略：给导出器提供完整的数据结构，但保持原始模板数据不变

                # === 导出器必需的字段映射（保持原始数据）===
                # 模块名称字段映射 (Excel导出器必需 'model')
                if 'module_name' in filled_point:
                    filled_point['model'] = filled_point['module_name']
                elif '模块名称' in filled_point:
                    filled_point['model'] = filled_point['模块名称']

                # 模块类型字段映射 (Excel导出器必需 'type')
                if 'module_type' in filled_point:
                    filled_point['type'] = filled_point['module_type']
                elif '模块类型' in filled_point:
                    filled_point['type'] = filled_point['模块类型']

                # 通道位号字段映射 (Excel导出器必需 'address')
                if 'channel_address' in filled_point:
                    filled_point['address'] = filled_point['channel_address']
                elif '通道位号' in filled_point:
                    filled_point['address'] = filled_point['通道位号']

                # 场站信息字段映射 (Excel导出器需要 'site_name', 'site_no')
                if '场站名' in filled_point:
                    filled_point['site_name'] = filled_point['场站名']
                if '场站编号' in filled_point:
                    filled_point['site_no'] = filled_point['场站编号']

                # === 灰色高亮字段映射（这些字段会被分配数据覆盖）===
                # 供电类型字段映射 (Excel导出器期望 'power_supply') - 灰色高亮字段
                if '供电类型（有源/无源）' in filled_point:
                    filled_point['power_supply'] = filled_point['供电类型（有源/无源）']
                elif '供电类型' in filled_point:
                    filled_point['power_supply'] = filled_point['供电类型']

                # 线制字段映射 (Excel导出器期望 'wiring') - 灰色高亮字段
                if '线制' in filled_point:
                    filled_point['wiring'] = filled_point['线制']

                # 变量名称字段映射 (Excel导出器期望 'hmi_variable') - 灰色高亮字段
                if 'variable_name' in filled_point:
                    filled_point['hmi_variable'] = filled_point['variable_name']
                elif '变量名称（HMI）' in filled_point:
                    filled_point['hmi_variable'] = filled_point['变量名称（HMI）']
                elif '变量名称' in filled_point:
                    filled_point['hmi_variable'] = filled_point['变量名称']

                # 变量描述字段映射 (Excel导出器期望 'description') - 灰色高亮字段
                if '变量描述' in filled_point:
                    filled_point['description'] = filled_point['变量描述']
                elif '描述' in filled_point:
                    filled_point['description'] = filled_point['描述']

                # 单位字段映射 (Excel导出器期望 'units') - 灰色高亮字段
                if '单位' in filled_point:
                    filled_point['units'] = filled_point['单位']

                # 🔥 调试：输出第一个通道的映射信息
                if channel_id == list(self.plc_template_data)[0].get('address', ''):
                    logger.info(f"原始模板数据键: {list(template_point.keys())}")
                    logger.info(f"映射后数据键: {list(filled_point.keys())}")
                    logger.info(f"供电类型映射: {filled_point.get('power_supply', 'N/A')}")
                    logger.info(f"线制映射: {filled_point.get('wiring', 'N/A')}")
                    # 🔥 删除：不再处理模块名称、场站信息等非高亮字段

                # 检查这个通道是否有分配的点位
                assigned_point = None

                # 查找分配给这个通道的点位
                for point_id, assigned_channel_id in self.assignments.items():
                    if assigned_channel_id == channel_id:
                        assigned_point = next((p for p in self.parsed_points if p.id == point_id), None)
                        break

                # 如果有分配的点位，则填写灰色字段
                if assigned_point:
                    logger.debug(f"通道 {channel_id} 已分配点位 {assigned_point.instrument_tag}")

                    # 🔥 修复：只更新真正的灰色高亮字段，完全不处理非高亮字段
                    # 灰色高亮字段：变量名称（HMI）、变量描述、单位、量程低限、量程高限、供电类型、线制、设定值
                    # 非高亮字段：模块名称、模块类型、通道位号、场站名、场站编号等 - 完全不处理
                    filled_point.update({
                        'hmi_variable': assigned_point.instrument_tag,  # 变量名称（HMI）- 灰色字段
                        'description': assigned_point.description,      # 变量描述 - 灰色字段
                        'units': assigned_point.units or '',            # 单位 - 灰色字段
                        'range_low': self._extract_range_low(assigned_point.data_range),           # 量程低限 - 灰色字段
                        'range_high': self._extract_range_high(assigned_point.data_range),         # 量程高限 - 灰色字段
                        # 🔥 删除：不再处理供电类型和线制，让原始模板数据保持不变
                        # 🔥 删除：不再处理场站信息，让原始模板数据保持不变
                    })
                else:
                    logger.debug(f"通道 {channel_id} 未分配点位，清空所有灰色字段")

                    # 🔥 修复：未分配的通道只清空灰色字段，完全不处理非高亮字段
                    # 只清空：变量名称（HMI）、变量描述、单位、量程低限、量程高限
                    # 完全不处理：模块名称、模块类型、供电类型、线制、通道位号、场站名、场站编号等
                    filled_point.update({
                        'hmi_variable': '',      # 清空变量名称 - 灰色字段
                        'description': '',       # 清空变量描述 - 灰色字段
                        'units': '',            # 清空单位 - 灰色字段
                        'range_low': '',        # 清空量程低限 - 灰色字段
                        'range_high': '',       # 清空量程高限 - 灰色字段
                        # 🔥 删除：不再处理任何非高亮字段
                    })

                filled_data.append(filled_point)

            logger.info(f"生成了 {len(filled_data)} 个PLC数据（包含 {len(self.assignments)} 个已分配点位）")
            return filled_data

        except Exception as e:
            logger.error(f"生成填写的PLC数据失败: {e}")
            return []

    def _infer_power_type(self, power_supply: str) -> str:
        """推断供电类型 - 只有明确信息才填写，否则留空"""
        if not power_supply:
            return ""

        power_supply_lower = power_supply.lower()
        # 只有明确包含这些关键词才判断
        if '回路供电' in power_supply_lower or '二线制' in power_supply_lower:
            return "无源"
        elif '外供电' in power_supply_lower or '四线制' in power_supply_lower:
            return "有源"
        else:
            # 不确定的情况下留空，不要乱填
            return ""

    def _infer_wiring_system(self, signal_type: str) -> str:
        """推断线制 - 不要乱写，不确定就留空"""
        if not signal_type:
            return ""

        # 不要根据信号类型乱推断线制，这个需要具体的信号范围信息
        # 只有在有明确信号范围信息时才填写
        return ""

    def _get_power_supply_info(self, power_supply: str) -> str:
        """获取供电类型信息 - 只返回明确的信息"""
        if not power_supply:
            return ""

        # 直接返回原始信息，不做推断
        return power_supply.strip()

    def _get_wiring_info(self, signal_range: str) -> str:
        """从信号范围获取线制信息 - 只有明确信息才填写"""
        if not signal_range:
            return ""

        signal_range_lower = signal_range.lower()

        # 只有明确包含这些信息才填写
        if '4-20ma' in signal_range_lower or '4~20ma' in signal_range_lower:
            return "4-20mA"
        elif '0-20ma' in signal_range_lower or '0~20ma' in signal_range_lower:
            return "0-20mA"
        elif '24vdc' in signal_range_lower or '24v' in signal_range_lower:
            return "24VDC"
        elif '220vac' in signal_range_lower or '220v' in signal_range_lower:
            return "220VAC"
        else:
            # 不确定的情况下留空
            return ""

    def _extract_range_low(self, data_range: str) -> str:
        """从数据范围提取低限值"""
        if not data_range:
            return ""

        try:
            import re
            pattern = r'(-?\d+(?:\.\d+)?)\s*[~\-to]\s*(-?\d+(?:\.\d+)?)'
            match = re.search(pattern, data_range)

            if match:
                return match.group(1)

            # 如果没有匹配到范围，尝试提取第一个数字
            number_pattern = r'(-?\d+(?:\.\d+)?)'
            number_match = re.search(number_pattern, data_range)
            if number_match:
                return number_match.group(1)

        except Exception as e:
            logger.debug(f"提取量程低限时出错: {e}, 数据范围: {data_range}")

        return ""

    def _extract_range_high(self, data_range: str) -> str:
        """从数据范围提取高限值"""
        if not data_range:
            return ""

        try:
            import re
            pattern = r'(-?\d+(?:\.\d+)?)\s*[~\-to]\s*(-?\d+(?:\.\d+)?)'
            match = re.search(pattern, data_range)

            if match:
                return match.group(2)

        except Exception as e:
            logger.debug(f"提取量程高限时出错: {e}, 数据范围: {data_range}")

        return ""

    def _get_site_info_from_template_or_main_window(self) -> tuple[str, str]:
        """优先从模板获取场站信息，如果模板中没有则从主窗口获取"""
        try:
            # 🔥 修复：优先从原始模板数据中获取场站信息
            template_site_name = ""
            template_site_no = ""

            if hasattr(self, 'plc_template_data') and self.plc_template_data:
                # 从第一个模板数据中获取场站信息
                first_template = self.plc_template_data[0]

                # 尝试获取场站名称
                if '场站名' in first_template and first_template['场站名']:
                    template_site_name = first_template['场站名']
                elif 'site_name' in first_template and first_template['site_name']:
                    template_site_name = first_template['site_name']

                # 尝试获取场站编号
                if '场站编号' in first_template and first_template['场站编号']:
                    template_site_no = first_template['场站编号']
                elif 'site_no' in first_template and first_template['site_no']:
                    template_site_no = first_template['site_no']

                logger.info(f"从模板获取到场站信息: 名称='{template_site_name}', 编号='{template_site_no}'")

            # 如果模板中有完整的场站信息，直接使用
            if template_site_name and template_site_no:
                return template_site_name, template_site_no

            # 如果模板中信息不完整，从主窗口获取补充
            main_site_name, main_site_no = self._get_site_info_from_main_window()

            # 优先使用模板中的信息，缺失的部分用主窗口信息补充
            final_site_name = template_site_name if template_site_name else main_site_name
            final_site_no = template_site_no if template_site_no else main_site_no

            # 如果还是没有信息，使用默认值
            if not final_site_name:
                final_site_name = "未知场站"
                logger.warning("无法获取场站名称，使用默认值")
            if not final_site_no:
                final_site_no = "未知编号"
                logger.warning("无法获取场站编号，使用默认值")

            return final_site_name, final_site_no

        except Exception as e:
            logger.error(f"获取场站信息失败: {e}")
            return "未知场站", "未知编号"

    def _get_site_info_from_main_window(self) -> tuple[str, str]:
        """从主窗口获取场站信息"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                logger.error("无法获取QApplication实例")
                return "", ""

            # 查找主窗口 - 修复：使用正确的属性名
            main_window = None
            for widget in app.topLevelWidgets():
                # 检查是否是主窗口（有current_site_name属性）
                if hasattr(widget, 'current_site_name') and hasattr(widget, 'query_area'):
                    main_window = widget
                    break

            if not main_window:
                logger.error("无法找到主窗口实例")
                return "", ""

            # 获取场站名称
            site_name = ""
            if hasattr(main_window, 'current_site_name') and main_window.current_site_name:
                site_name = main_window.current_site_name

            # 获取场站编号
            site_no = ""
            if hasattr(main_window, 'query_area') and main_window.query_area:
                if hasattr(main_window.query_area, 'station_input'):
                    site_no = main_window.query_area.station_input.text().strip()

            logger.info(f"从主窗口获取到场站信息: 名称='{site_name}', 编号='{site_no}'")
            return site_name, site_no

        except Exception as e:
            logger.error(f"从主窗口获取场站信息失败: {e}")
            return "", ""

    def _get_third_party_data(self) -> Optional[List[Dict[str, Any]]]:
        """获取第三方设备数据"""
        try:
            from PySide6.QtWidgets import QApplication
            app = QApplication.instance()
            if not app:
                logger.error("无法获取QApplication实例")
                return None

            # 查找主窗口
            main_window = None
            for widget in app.topLevelWidgets():
                if hasattr(widget, 'tp_config_service'):
                    main_window = widget
                    break

            if not main_window:
                logger.warning("无法找到主窗口实例，跳过第三方设备数据")
                return None

            # 获取第三方设备配置服务
            if not hasattr(main_window, 'tp_config_service') or not main_window.tp_config_service:
                logger.info("第三方设备配置服务未初始化，跳过第三方设备数据")
                return None

            # 获取已配置的第三方设备点位
            configured_tp_models = main_window.tp_config_service.get_all_configured_points()
            if not configured_tp_models:
                logger.info("没有已配置的第三方设备点位")
                return None

            # 转换为导出格式
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

            logger.info(f"获取到 {len(third_party_points_for_export)} 个第三方设备点位")
            return third_party_points_for_export

        except Exception as e:
            logger.error(f"获取第三方设备数据失败: {e}")
            return None

    def dragEnterEvent(self, event):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith('.docx'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        """拖拽放下事件"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                file_path = urls[0].toLocalFile()
                if file_path.lower().endswith('.docx'):
                    self.parse_document_file(file_path)
                    event.acceptProposedAction()
                    return
        event.ignore()

    def select_and_parse_document(self):
        """选择并解析文档文件"""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的设计院文档",
            "",
            "Word 文档 (*.docx);;所有文件 (*)"
        )

        if file_path:
            self.parse_document_file(file_path)

    def parse_document_file(self, file_path: str):
        """解析文档文件"""
        try:
            import os
            file_name = os.path.basename(file_path)
            self.file_status_label.setText(f"正在解析：{file_name}")
            self.parse_status_label.setText("解析中...")

            logger.info(f"开始解析文档: {file_path}")

            # 导入文档解析模块
            from core.document_parser.excel_parser import create_parser

            # 创建解析器
            parser = create_parser(file_path)
            logger.info(f"使用解析器: {type(parser).__name__}")

            # 解析文档
            raw_points = parser.parse_document(file_path)
            logger.info(f"解析到 {len(raw_points)} 个原始点位")

            # 增强点位数据
            enhanced_points = self.enhance_parsed_points(raw_points)

            # 保存解析数据
            self.save_parsed_data_to_project(enhanced_points, file_name)

            # 更新界面
            self.load_points_table()
            self.update_points_statistics()

            # 更新状态
            self.file_status_label.setText(f"已解析：{file_name}")
            self.parse_status_label.setText(f"✅ {len(enhanced_points)} 个点位")

            logger.info(f"文档解析完成: {len(enhanced_points)} 个点位")

        except Exception as e:
            logger.error(f"文档解析失败: {e}")
            self.file_status_label.setText("解析失败")
            self.parse_status_label.setText("❌ 错误")

            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "解析失败", f"文档解析失败：\n{str(e)}")



    def enhance_parsed_points(self, raw_points: list) -> list:
        """增强解析的点位数据"""
        enhanced_points = []

        for point in raw_points:
            # 从raw_data中获取完整信息
            raw_data = point.get('raw_data', point)

            enhanced_point = {
                'instrument_tag': point.get('instrument_tag', ''),
                'description': point.get('description', ''),
                'signal_range': raw_data.get('signal_range', ''),
                'data_range': raw_data.get('data_range', ''),
                'signal_type': point.get('signal_type', ''),
                'units': raw_data.get('units', ''),
                'power_supply': raw_data.get('power_supply', ''),
                'isolation': raw_data.get('isolation', ''),
                'io_type': self.detect_io_type(point),
                'range_low': point.get('range_low', ''),
                'range_high': point.get('range_high', ''),
                'suggested_channel': '',
                'confidence': 0.8,
                'raw_data': raw_data
            }
            enhanced_points.append(enhanced_point)

        # 生成建议通道
        channel_counters = {'AI': 1, 'DI': 1, 'DO': 1, 'AO': 1, 'COMM': 1}
        for point in enhanced_points:
            io_type = point['io_type']
            if io_type != 'UNKNOWN':
                point['suggested_channel'] = f"{io_type}-{channel_counters[io_type]:02d}"
                channel_counters[io_type] += 1

        return enhanced_points

    def detect_io_type(self, point):
        """检测IO类型"""
        instrument_tag = point.get('instrument_tag', '').upper()
        description = point.get('description', '').lower()
        signal_type = point.get('signal_type', '').upper()

        # 1. 优先根据信号类型判断
        if signal_type in ['AI', 'AO', 'DI', 'DO']:
            return signal_type

        # 1.1 通信设备识别
        if signal_type in ['RS485', 'TCP/IP', 'MODBUS', 'PROFIBUS', 'CAN']:
            return 'COMM'

        # 2. 根据仪表位号前缀判断
        if instrument_tag:
            # AI类型前缀
            if any(instrument_tag.startswith(prefix) for prefix in ['PT', 'TT', 'FT', 'LT', 'PDT', 'TDT', 'FDT']):
                return 'AI'
            # DI类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['XS', 'HS', 'LS', 'PS', 'TS', 'FS', 'UA', 'LA']):
                return 'DI'
            # DO类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['XO', 'HO', 'LO', 'PO', 'TO', 'FO', 'XV', 'HV', 'ZSL', 'ZSH']):
                return 'DO'
            # AO类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['PIC', 'TIC', 'FIC', 'LIC', 'PCV', 'TCV', 'FCV']):
                return 'AO'

        # 3. 根据描述关键字判断
        if any(keyword in description for keyword in ['压力', '温度', '流量', '液位', '差压', '检测', '测量', '监测']):
            return 'AI'
        elif any(keyword in description for keyword in ['状态', '故障', '报警', '开关', '干接点', '位置', '反馈', '信号']):
            return 'DI'
        elif any(keyword in description for keyword in ['控制', '启动', '停止', '阀门', '继电器', '输出', '驱动', '操作']):
            return 'DO'
        elif any(keyword in description for keyword in ['设定', '调节', '控制输出', '模拟输出']):
            return 'AO'

        return 'UNKNOWN'

    def save_parsed_data_to_project(self, enhanced_points: list, file_name: str):
        """保存解析数据到项目"""
        try:
            # 导入数据访问对象
            from core.data_storage.parsed_data_dao import ParsedDataDAO
            from core.channel_assignment.persistence.assignment_dao import AssignmentDAO
            from core.channel_assignment.persistence.data_models import ParsedPoint
            from datetime import datetime

            parsed_data_dao = ParsedDataDAO()
            assignment_dao = AssignmentDAO()

            # 创建新项目
            project_name = f"解析项目_{file_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            project_id = parsed_data_dao.create_project(
                name=project_name,
                description=f"从文档 {file_name} 解析的数据"
            )

            # 转换为ParsedPoint对象
            parsed_points = []
            for point_data in enhanced_points:
                parsed_point = ParsedPoint(
                    project_id=project_id,
                    instrument_tag=point_data.get('instrument_tag', ''),
                    description=point_data.get('description', ''),
                    signal_type=point_data.get('signal_type', ''),
                    io_type=point_data.get('io_type', ''),
                    units=point_data.get('units', ''),
                    data_range=point_data.get('data_range', ''),
                    signal_range=point_data.get('signal_range', ''),
                    power_supply=point_data.get('power_supply', ''),
                    isolation=point_data.get('isolation', ''),
                    remarks='',
                    original_data=point_data.get('raw_data', {})
                )
                parsed_points.append(parsed_point)

            # 保存到数据库
            success = parsed_data_dao.save_parsed_points(project_id, parsed_points)
            if not success:
                raise Exception("保存解析数据失败")

            # 创建默认分配方案
            scheme_name = f"默认方案_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            scheme_id = assignment_dao.create_assignment(
                project_id,
                scheme_name,
                "从文档导入自动创建的分配方案"
            )

            if not scheme_id:
                raise Exception("创建分配方案失败")

            # 更新当前项目和方案
            self.current_project_id = project_id
            self.current_scheme_id = scheme_id
            self.parsed_points = parsed_points
            self.assignments = {}

            # 更新项目信息显示
            self.project_info_label.setText(f"项目：{project_name}")
            self.points_info_label.setText(f"点位：{len(parsed_points)} 个")
            self.assigned_info_label.setText(f"已分配：0 个")
            self.progress_label.setText(f"进度：0%")

            logger.info(f"成功保存解析数据: 项目ID={project_id}, 方案ID={scheme_id}, 点位数={len(parsed_points)}")

        except Exception as e:
            logger.error(f"保存解析数据失败: {e}")
            raise

    def import_io_template(self):
        """导入IO模板文件"""
        try:
            from PySide6.QtWidgets import QFileDialog, QMessageBox
            import os

            # 设置默认目录为IO点表模板生成目录
            default_dir = os.path.join(os.getcwd(), "IO点表模板")

            # 确保目录存在，如果不存在则使用当前工作目录
            if not os.path.exists(default_dir):
                default_dir = os.getcwd()
                logger.warning(f"IO点表模板目录不存在，使用当前工作目录: {default_dir}")
            else:
                logger.info(f"设置文件对话框默认目录为: {default_dir}")

            # 打开文件对话框选择Excel文件
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择IO点表模板文件",
                default_dir,  # 设置默认目录
                "Excel 文件 (*.xlsx *.xls);;所有文件 (*)"
            )

            if not file_path:
                logger.info("用户取消了文件选择")
                return

            logger.info(f"用户选择了IO模板文件: {file_path}")

            # 检查文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "文件错误", "选择的文件不存在")
                return

            # 解析Excel文件获取PLC模板数据
            template_data = self.parse_io_template_file(file_path)

            if not template_data:
                QMessageBox.warning(self, "解析失败", "无法从文件中解析出有效的IO模板数据")
                return

            # 设置模板数据
            self.set_plc_template_data(template_data)

            # 更新界面显示
            self.load_channels_table()

            # 显示成功消息
            file_name = os.path.basename(file_path)
            QMessageBox.information(
                self,
                "导入成功",
                f"成功导入IO模板：{file_name}\n"
                f"共解析到 {len(template_data)} 个通道"
            )

            logger.info(f"✅ 成功导入IO模板: {len(template_data)} 个通道")

        except Exception as e:
            logger.error(f"导入IO模板失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "导入失败", f"导入IO模板失败：\n{str(e)}")

    def parse_io_template_file(self, file_path: str) -> List[Dict[str, Any]]:
        """解析IO模板Excel文件"""
        try:
            import pandas as pd

            # 读取Excel文件的第一个工作表（IO点表）
            df = pd.read_excel(file_path, sheet_name=0)  # 读取第一个工作表

            template_data = []

            logger.info(f"Excel文件列名: {df.columns.tolist()}")
            logger.info(f"Excel文件行数: {len(df)}")

            # 遍历每一行数据
            for index, row in df.iterrows():
                # 跳过空行
                if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                    continue

                try:
                    # 🔥 修复：完整保留原始模板的所有列数据
                    channel_data = {}

                    # 首先保存所有列的原始数据
                    for col in df.columns:
                        # 保存原始列名和值
                        value = str(row[col]).strip() if pd.notna(row[col]) else ''
                        channel_data[col] = value

                    # 然后检查必要字段并进行标准化映射

                    # 通道位号 (address) - 必须字段
                    address = None
                    if '通道位号' in df.columns:
                        address = str(row['通道位号']).strip()
                    elif '通道' in df.columns:
                        address = str(row['通道']).strip()

                    if not address:
                        continue  # 跳过没有通道位号的行

                    channel_data['address'] = address

                    # 模块类型 (type) - 必须字段
                    module_type = None
                    if '模块类型' in df.columns:
                        module_type = str(row['模块类型']).strip()

                    if module_type not in ['AI', 'DI', 'AO', 'DO']:
                        continue  # 跳过不是标准IO类型的行

                    channel_data['type'] = module_type

                    # 标准化其他重要字段的映射（保持向后兼容）

                    # 变量描述
                    if '变量描述' in df.columns:
                        channel_data['description'] = str(row['变量描述']).strip()
                    elif '描述' in df.columns:
                        channel_data['description'] = str(row['描述']).strip()

                    # 变量名称
                    if '变量名称（HMI）' in df.columns:
                        channel_data['variable_name'] = str(row['变量名称（HMI）']).strip()
                    elif '变量名称' in df.columns:
                        channel_data['variable_name'] = str(row['变量名称']).strip()

                    # PLC地址
                    if 'PLC绝对地址' in df.columns:
                        channel_data['plc_address'] = str(row['PLC绝对地址']).strip()

                    # 模块名称
                    if '模块名称' in df.columns:
                        channel_data['module_name'] = str(row['模块名称']).strip()

                    # 场站名称
                    if '场站名' in df.columns:
                        channel_data['site_name'] = str(row['场站名']).strip()

                    # 场站编号
                    if '场站编号' in df.columns:
                        channel_data['site_no'] = str(row['场站编号']).strip()

                    # 供电类型
                    if '供电类型（有源/无源）' in df.columns:
                        channel_data['power_supply'] = str(row['供电类型（有源/无源）']).strip()
                    elif '供电类型' in df.columns:
                        channel_data['power_supply'] = str(row['供电类型']).strip()

                    # 线制
                    if '线制' in df.columns:
                        channel_data['wiring'] = str(row['线制']).strip()

                    # 验证必要字段后添加到结果中
                    template_data.append(channel_data)
                    logger.debug(f"解析通道: {channel_data['address']} ({channel_data['type']})")

                except Exception as e:
                    logger.warning(f"解析第 {index+1} 行时出错: {e}")
                    continue

            logger.info(f"从Excel文件解析到 {len(template_data)} 个有效通道")

            # 🔥 调试：输出前几个模板数据的结构
            if template_data:
                logger.info(f"模板数据示例（前3个）:")
                for i, data in enumerate(template_data[:3]):
                    logger.info(f"  通道 {i+1}: {data}")

            return template_data

        except Exception as e:
            logger.error(f"解析IO模板文件失败: {e}")
            raise

    def update_points_statistics(self):
        """更新点位统计信息"""
        if not self.parsed_points:
            self.points_stats_label.setText("统计：AI: 0, DI: 0, AO: 0, DO: 0")
            return

        stats = {}
        for point in self.parsed_points:
            io_type = point.io_type if hasattr(point, 'io_type') else 'UNKNOWN'
            stats[io_type] = stats.get(io_type, 0) + 1

        stats_text = ", ".join([f"{k}: {v}" for k, v in sorted(stats.items())])
        self.points_stats_label.setText(f"统计：{stats_text}")

    def auto_assign_all_points(self):
        """自动分配所有未分配的点位"""
        try:
            from PySide6.QtWidgets import QMessageBox, QProgressDialog
            from PySide6.QtCore import Qt

            if not self.parsed_points:
                QMessageBox.warning(self, "无点位数据", "请先解析文档获取点位数据")
                return

            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                QMessageBox.warning(self, "无通道数据", "请先导入IO模板获取通道数据")
                return

            # 获取未分配的点位
            unassigned_points = [point for point in self.parsed_points if point.id not in self.assignments]

            if not unassigned_points:
                QMessageBox.information(self, "无需分配", "所有点位都已分配")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self, "自动分配确认",
                f"将自动分配 {len(unassigned_points)} 个未分配的点位。\n\n是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 创建进度对话框
            progress = QProgressDialog("正在自动分配点位...", "取消", 0, len(unassigned_points), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)

            assigned_count = 0
            failed_count = 0
            failed_points = []

            # 按类型分组点位
            points_by_type = {}
            for point in unassigned_points:
                signal_type = point.signal_type
                if signal_type not in points_by_type:
                    points_by_type[signal_type] = []
                points_by_type[signal_type].append(point)

            current_progress = 0

            # 为每种类型的点位分配通道
            for signal_type, type_points in points_by_type.items():
                # 获取该类型的可用通道
                available_channels = self.get_available_channels_for_type(signal_type)

                if len(available_channels) < len(type_points):
                    logger.warning(f"可用 {signal_type} 通道不足：需要 {len(type_points)}，可用 {len(available_channels)}")

                # 分配通道
                for i, point in enumerate(type_points):
                    if progress.wasCanceled():
                        break

                    progress.setValue(current_progress)
                    progress.setLabelText(f"正在分配 {signal_type} 点位: {point.instrument_tag}")

                    if i < len(available_channels):
                        channel_id = available_channels[i]['address']
                        success = self.assign_point_to_channel(point.id, channel_id)

                        if success:
                            assigned_count += 1
                            logger.info(f"自动分配成功: {point.instrument_tag} -> {channel_id}")
                        else:
                            failed_count += 1
                            failed_points.append(f"{point.instrument_tag} ({signal_type})")
                            logger.error(f"自动分配失败: {point.instrument_tag}")
                    else:
                        failed_count += 1
                        failed_points.append(f"{point.instrument_tag} ({signal_type}) - 无可用通道")
                        logger.warning(f"无可用通道: {point.instrument_tag}")

                    current_progress += 1

                if progress.wasCanceled():
                    break

            progress.close()

            # 显示结果
            result_msg = f"自动分配完成！\n\n成功分配：{assigned_count} 个\n失败：{failed_count} 个"

            if failed_points:
                result_msg += f"\n\n失败的点位：\n" + "\n".join(failed_points[:10])
                if len(failed_points) > 10:
                    result_msg += f"\n... 还有 {len(failed_points) - 10} 个"

            QMessageBox.information(self, "自动分配结果", result_msg)

            # 更新界面显示
            self.load_channels_table()
            # self.update_assignment_info()  # 这个方法不存在，暂时注释掉

            logger.info(f"自动分配完成: 成功 {assigned_count}, 失败 {failed_count}")

        except Exception as e:
            logger.error(f"自动分配失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "自动分配失败", f"自动分配过程中出错：\n{str(e)}")

    def clear_all_assignments(self):
        """清空所有分配"""
        try:
            from PySide6.QtWidgets import QMessageBox

            if not self.assignments:
                QMessageBox.information(self, "无分配数据", "当前没有任何分配需要清空")
                return

            # 确认对话框
            reply = QMessageBox.question(
                self, "清空分配确认",
                f"将清空所有 {len(self.assignments)} 个点位的分配。\n\n此操作不可撤销，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 清空分配字典
            self.assignments.clear()

            # 🔥 修复：同时清空数据库中的分配记录
            if hasattr(self, 'current_scheme_id') and self.current_scheme_id:
                success = self.assignment_dao.clear_all_assignments(
                    self.current_project_id, self.current_scheme_id
                )
                if not success:
                    logger.warning("清空数据库分配记录失败，但内存已清空")

            # 更新界面显示
            self.load_channels_table()
            self.load_points_table()  # 也要更新点位表格

            # 更新进度信息
            self.assigned_info_label.setText(f"已分配：0 个")
            self.progress_label.setText(f"进度：0%")

            QMessageBox.information(self, "清空完成", "所有分配已清空")
            logger.info("已清空所有通道分配")

        except Exception as e:
            logger.error(f"清空分配失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "清空失败", f"清空分配时出错：\n{str(e)}")

    def unassign_channel(self, channel_id: str):
        """取消指定通道的分配"""
        try:
            # 查找并移除分配
            point_to_remove = None
            for point_id, assigned_channel in self.assignments.items():
                if assigned_channel == channel_id:
                    point_to_remove = point_id
                    break

            if point_to_remove:
                del self.assignments[point_to_remove]
                logger.info(f"取消通道分配: {channel_id}")

                # 🔥 修复：保存到数据库
                if hasattr(self, 'current_scheme_id') and self.current_scheme_id:
                    self.assignment_dao.update_assignments(self.current_scheme_id, self.assignments)

                # 更新界面显示
                self.load_channels_table()
                self.load_points_table()  # 也要更新点位表格

                # 更新进度信息
                progress = int((len(self.assignments) / len(self.parsed_points)) * 100) if self.parsed_points else 0
                self.assigned_info_label.setText(f"已分配：{len(self.assignments)} 个")
                self.progress_label.setText(f"进度：{progress}%")

                return True
            else:
                logger.warning(f"未找到通道 {channel_id} 的分配记录")
                return False

        except Exception as e:
            logger.error(f"取消通道分配失败: {e}")
            return False

    def get_channel_type(self, channel_id: str) -> str:
        """从通道ID获取通道类型"""
        try:
            if '_AI_' in channel_id:
                return 'AI'
            elif '_DI_' in channel_id:
                return 'DI'
            elif '_AO_' in channel_id:
                return 'AO'
            elif '_DO_' in channel_id:
                return 'DO'
            else:
                logger.warning(f"无法从通道ID {channel_id} 推断类型")
                return ''
        except Exception as e:
            logger.error(f"获取通道类型失败: {e}")
            return ''

    def reassign_channel_to_point(self, channel_id: str, new_point_id: str) -> bool:
        """重新分配通道到新的点位"""
        try:
            # 获取新点位信息
            new_point = None
            for point in self.parsed_points:
                if point.id == new_point_id:
                    new_point = point
                    break

            if not new_point:
                logger.error(f"未找到点位: {new_point_id}")
                return False

            # 检查信号类型是否匹配
            channel_type = self.get_channel_type(channel_id)
            if new_point.signal_type != channel_type:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "类型不匹配",
                                  f"点位 {new_point.instrument_tag} 的信号类型 ({new_point.signal_type}) "
                                  f"与通道 {channel_id} 的类型 ({channel_type}) 不匹配")
                return False

            # 如果新点位已经分配给其他通道，需要处理交换
            old_channel_for_new_point = self.assignments.get(new_point_id)
            old_point_for_channel = None

            # 找到当前分配给该通道的点位
            for point_id, assigned_channel in self.assignments.items():
                if assigned_channel == channel_id:
                    old_point_for_channel = point_id
                    break

            # 执行重新分配
            if old_channel_for_new_point:
                # 新点位已分配，需要交换
                if old_point_for_channel:
                    # 交换分配
                    self.assignments[old_point_for_channel] = old_channel_for_new_point
                    self.assignments[new_point_id] = channel_id
                    logger.info(f"交换分配: {old_point_for_channel} <-> {new_point_id}")
                else:
                    # 只是重新分配新点位
                    self.assignments[new_point_id] = channel_id
                    logger.info(f"重新分配点位 {new_point_id} 到通道 {channel_id}")
            else:
                # 新点位未分配
                if old_point_for_channel:
                    # 移除旧分配，添加新分配
                    del self.assignments[old_point_for_channel]

                self.assignments[new_point_id] = channel_id
                logger.info(f"重新分配通道 {channel_id} 到点位 {new_point_id}")

            # 保存到数据库
            if hasattr(self, 'current_scheme_id') and self.current_scheme_id:
                self.assignment_dao.update_assignments(self.current_scheme_id, self.assignments)

            # 更新界面
            self.load_channels_table()
            self.load_points_table()

            # 更新进度信息
            progress = int((len(self.assignments) / len(self.parsed_points)) * 100) if self.parsed_points else 0
            self.assigned_info_label.setText(f"已分配：{len(self.assignments)} 个")
            self.progress_label.setText(f"进度：{progress}%")

            return True

        except Exception as e:
            logger.error(f"重新分配通道失败: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"重新分配通道失败：\n{str(e)}")
            return False

    def get_available_channels_for_type(self, signal_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的可用通道"""
        try:
            if not hasattr(self, 'plc_template_data') or not self.plc_template_data:
                return []

            # 过滤出指定类型且未分配的通道
            available_channels = []
            assigned_channels = set(self.assignments.values())

            for channel in self.plc_template_data:
                if (channel.get('type') == signal_type and
                    channel.get('address') not in assigned_channels):
                    available_channels.append(channel)

            # 按地址排序
            available_channels.sort(key=lambda x: x.get('address', ''))

            return available_channels

        except Exception as e:
            logger.error(f"获取可用通道失败: {e}")
            return []

    # 其他占位方法已删除


class PointExchangeDialog(QDialog):
    """点位交换对话框"""
    point_exchange_requested = Signal(str)

    def __init__(self, channel_id: str, channel_type: str, available_points: List, current_point_id: str, parent=None):
        super().__init__(parent)
        self.channel_id = channel_id
        self.channel_type = channel_type
        self.available_points = available_points
        self.current_point_id = current_point_id
        self.setup_ui()
        self.load_points()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle(f"重新分配通道 {self.channel_id}")
        self.setModal(True)
        self.resize(700, 500)

        layout = QVBoxLayout(self)

        # 说明标签
        info_label = QLabel(f"通道 {self.channel_id} ({self.channel_type}) 重新分配\n"
                           f"选择一个点位来替换当前分配，或与其他已分配点位进行交换：")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 点位表格
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(5)
        self.points_table.setHorizontalHeaderLabels(["仪表位号", "描述", "信号类型", "信号范围", "分配状态"])
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.points_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.points_table.doubleClicked.connect(self.on_point_double_clicked)
        layout.addWidget(self.points_table)

        # 按钮
        button_layout = QHBoxLayout()
        self.exchange_button = QPushButton("交换/重新分配")
        self.exchange_button.clicked.connect(self.on_exchange_clicked)
        self.exchange_button.setEnabled(False)

        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(self.exchange_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # 选择变化事件
        self.points_table.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def load_points(self):
        """加载点位数据"""
        # 获取父窗口的分配信息
        parent_widget = self.parent()
        assignments = getattr(parent_widget, 'assignments', {})

        # 过滤匹配类型的点位
        matching_points = [p for p in self.available_points if p.signal_type == self.channel_type]

        self.points_table.setRowCount(len(matching_points))

        for row, point in enumerate(matching_points):
            self.points_table.setItem(row, 0, QTableWidgetItem(point.instrument_tag))
            self.points_table.setItem(row, 1, QTableWidgetItem(point.description))
            self.points_table.setItem(row, 2, QTableWidgetItem(point.signal_type))
            self.points_table.setItem(row, 3, QTableWidgetItem(point.signal_range))

            # 显示分配状态
            if point.id == self.current_point_id:
                status_item = QTableWidgetItem("当前分配")
                status_item.setBackground(QColor(255, 255, 0, 100))  # 黄色背景
            elif point.id in assignments:
                assigned_channel = assignments[point.id]
                status_item = QTableWidgetItem(f"已分配到 {assigned_channel}")
                status_item.setBackground(QColor(255, 200, 200, 100))  # 浅红色背景
            else:
                status_item = QTableWidgetItem("未分配")
                status_item.setBackground(QColor(200, 255, 200, 100))  # 浅绿色背景

            self.points_table.setItem(row, 4, status_item)

            # 存储点位ID
            self.points_table.item(row, 0).setData(Qt.UserRole, point.id)

        # 调整列宽
        self.points_table.resizeColumnsToContents()

    def on_selection_changed(self):
        """选择变化"""
        selected_rows = self.points_table.selectionModel().selectedRows()
        if selected_rows:
            current_row = selected_rows[0].row()
            point_id = self.points_table.item(current_row, 0).data(Qt.UserRole)
            # 不能选择当前已分配的点位
            self.exchange_button.setEnabled(point_id != self.current_point_id)
        else:
            self.exchange_button.setEnabled(False)

    def on_exchange_clicked(self):
        """交换按钮点击"""
        current_row = self.points_table.currentRow()
        if current_row >= 0:
            point_id = self.points_table.item(current_row, 0).data(Qt.UserRole)
            if point_id != self.current_point_id:
                self.point_exchange_requested.emit(point_id)
                self.accept()

    def on_point_double_clicked(self):
        """点位双击"""
        self.on_exchange_clicked()
