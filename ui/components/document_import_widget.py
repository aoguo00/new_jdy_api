"""
设计院文档导入组件
提供完整的文档导入操作界面，包括文件选择、数据预览、映射确认、结果展示等功能
"""

import logging
import os
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QGroupBox, QFileDialog, QTextEdit, QProgressBar, QFrame,
    QMessageBox, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent, QPixmap, QPainter
from pathlib import Path

logger = logging.getLogger(__name__)


class DocumentImportWidget(QWidget):
    """设计院文档导入组件"""
    
    # 信号定义
    import_completed = Signal(str)  # 导入完成信号，携带结果文件路径
    goto_channel_assignment = Signal(str, str)  # 跳转到通道分配信号，传递project_id和scheme_id
    status_changed = Signal(str)    # 状态变化信号，携带状态信息
    
    def __init__(self, io_data_loader=None, current_site_name=None, parent=None):
        """
        初始化文档导入组件
        
        Args:
            io_data_loader: IO数据加载器
            current_site_name: 当前场站名称
            parent: 父窗口
        """
        super().__init__(parent)
        self.io_data_loader = io_data_loader
        self.current_site_name = current_site_name
        
        # 状态变量
        self.selected_file_path = None
        self.extracted_points = []
        self.parsed_points = []  # 用于导入功能的解析数据
        self.available_channels = {}
        self.mapping_result = []
        self.result_file_path = None

        # 数据存储
        from core.data_storage.parsed_data_dao import ParsedDataDAO
        from core.data_storage.data_models import ParsedPoint
        self.parsed_data_dao = ParsedDataDAO()
        self.current_project_id = None
        
        self.setup_ui()
        self.update_widget_states()

        # 启用拖拽功能
        self.setAcceptDrops(True)
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("设计院文档导入")
        title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建各个步骤区域
        self.setup_step1_file_selection(layout)
        self.setup_step2_data_preview(layout)
        self.setup_step3_mapping_confirmation(layout)
        self.setup_step4_result_display(layout)

        # 不添加弹性空间，让表格占据更多空间
        
    def setup_step1_file_selection(self, parent_layout):
        """设置第一步：文件选择区域"""
        step1_group = QGroupBox("📁 第一步：选择文档文件")
        step1_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        step1_group.setMaximumHeight(100)  # 限制最大高度，压缩空间
        step1_layout = QVBoxLayout(step1_group)
        step1_layout.setContentsMargins(8, 8, 8, 8)  # 减少内边距
        step1_layout.setSpacing(5)  # 减少间距

        # 文件选择区域
        file_selection_layout = QHBoxLayout()

        self.select_file_btn = QPushButton("选择Word文档")
        self.select_file_btn.setMinimumHeight(30)  # 减少按钮高度
        self.select_file_btn.clicked.connect(self.select_document_file)

        self.file_path_label = QLabel("未选择文件")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")

        file_selection_layout.addWidget(self.select_file_btn)
        file_selection_layout.addWidget(self.file_path_label, 1)

        step1_layout.addLayout(file_selection_layout)

        # 拖拽提示区域 - 更紧凑
        drag_hint_label = QLabel("或将Word文档拖拽到此区域")
        drag_hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drag_hint_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #ccc;
                border-radius: 5px;
                padding: 5px;
                color: #999;
                background-color: #f9f9f9;
                font-size: 12px;
            }
        """)
        drag_hint_label.setMaximumHeight(25)  # 大幅减少拖拽区域高度
        step1_layout.addWidget(drag_hint_label)

        parent_layout.addWidget(step1_group)
        
    def setup_step2_data_preview(self, parent_layout):
        """设置第二步：数据预览区域"""
        self.step2_group = QGroupBox("📋 第二步：数据预览")
        self.step2_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.step2_group.setEnabled(False)  # 初始禁用
        step2_layout = QVBoxLayout(self.step2_group)
        step2_layout.setContentsMargins(8, 8, 8, 8)  # 减少内边距
        step2_layout.setSpacing(5)  # 减少间距

        # 预览信息和解析按钮放在同一行，节省空间
        info_parse_layout = QHBoxLayout()
        self.preview_info_label = QLabel("等待文档解析...")
        self.preview_info_label.setStyleSheet("color: #666;")

        self.parse_document_btn = QPushButton("解析文档")
        self.parse_document_btn.setMinimumHeight(25)  # 减少按钮高度
        self.parse_document_btn.clicked.connect(self.parse_document)
        self.parse_document_btn.setEnabled(False)

        info_parse_layout.addWidget(self.preview_info_label, 1)
        info_parse_layout.addWidget(self.parse_document_btn)
        step2_layout.addLayout(info_parse_layout)

        # 预览表格 - 给更多空间
        self.preview_table = QTableWidget()
        self.setup_preview_table()
        step2_layout.addWidget(self.preview_table)

        parent_layout.addWidget(self.step2_group)
        
    def setup_step3_mapping_confirmation(self, parent_layout):
        """设置第三步：映射确认区域"""
        self.step3_group = QGroupBox("🔗 第三步：通道映射确认")
        self.step3_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.step3_group.setEnabled(False)  # 初始禁用
        # 移除高度限制，让映射区域获得更多空间
        step3_layout = QVBoxLayout(self.step3_group)
        step3_layout.setContentsMargins(8, 8, 8, 8)
        step3_layout.setSpacing(5)

        # 映射信息和按钮放在同一行，节省空间
        info_buttons_layout = QHBoxLayout()
        self.mapping_info_label = QLabel("等待数据解析完成...")
        self.mapping_info_label.setStyleSheet("color: #666;")

        # 批量操作按钮
        self.apply_suggestions_btn = QPushButton("采用建议")
        self.apply_suggestions_btn.setMaximumHeight(30)
        self.apply_suggestions_btn.clicked.connect(self.apply_all_suggestions)

        self.clear_mapping_btn = QPushButton("清空")
        self.clear_mapping_btn.setMaximumHeight(30)
        self.clear_mapping_btn.clicked.connect(self.clear_all_mappings)

        self.smart_match_btn = QPushButton("智能匹配")
        self.smart_match_btn.setMaximumHeight(30)
        self.smart_match_btn.clicked.connect(self.smart_channel_matching)

        info_buttons_layout.addWidget(self.mapping_info_label, 1)
        info_buttons_layout.addWidget(self.apply_suggestions_btn)
        info_buttons_layout.addWidget(self.clear_mapping_btn)
        info_buttons_layout.addWidget(self.smart_match_btn)

        step3_layout.addLayout(info_buttons_layout)

        # 映射表格 - 给予更多空间，这是用户主要工作区域
        self.mapping_table = QTableWidget()
        self.mapping_table.setMinimumHeight(400)  # 增加最小高度，给用户更多操作空间
        self.setup_mapping_table()
        step3_layout.addWidget(self.mapping_table)

        parent_layout.addWidget(self.step3_group)
        
    def setup_step4_result_display(self, parent_layout):
        """设置第四步：结果展示区域"""
        self.step4_group = QGroupBox("✅ 第四步：生成结果")
        self.step4_group.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.step4_group.setEnabled(False)  # 初始禁用
        self.step4_group.setMaximumHeight(100)  # 进一步减少高度，保持紧凑
        step4_layout = QVBoxLayout(self.step4_group)
        step4_layout.setContentsMargins(8, 8, 8, 8)
        step4_layout.setSpacing(3)  # 进一步减少间距

        # 状态信息、进度条和按钮都放在同一行，最大化节省空间
        all_in_one_layout = QHBoxLayout()

        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(25)  # 进一步减少高度
        self.status_text.setReadOnly(True)
        self.status_text.setPlainText("等待开始处理...")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setVisible(False)

        # 操作按钮 - 简化版本
        self.goto_assignment_btn = QPushButton("进入通道分配")
        self.goto_assignment_btn.setMaximumHeight(25)
        self.goto_assignment_btn.clicked.connect(self.goto_channel_assignment_page)
        self.goto_assignment_btn.setEnabled(False)
        self.goto_assignment_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; }")

        self.reset_btn = QPushButton("重置")
        self.reset_btn.setMaximumHeight(25)
        self.reset_btn.clicked.connect(self.reset_all)

        all_in_one_layout.addWidget(self.status_text, 3)
        all_in_one_layout.addWidget(self.progress_bar, 2)
        all_in_one_layout.addWidget(self.goto_assignment_btn, 1)
        all_in_one_layout.addWidget(self.reset_btn, 1)

        step4_layout.addLayout(all_in_one_layout)

        parent_layout.addWidget(self.step4_group)
        
    def setup_preview_table(self):
        """设置预览表格"""
        self.preview_table.setColumnCount(8)
        headers = ["仪表位号", "检测点名称", "信号范围", "数据范围", "单位", "信号类型", "现场供电", "IO类型"]
        self.preview_table.setHorizontalHeaderLabels(headers)

        # 设置列宽 - 优化显示效果
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)      # 仪表位号 - 固定宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)    # 检测点名称 - 自适应
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)      # 信号范围 - 固定宽度
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)      # 数据范围 - 固定宽度
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)      # 单位 - 固定宽度
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)      # 信号类型 - 固定宽度
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)      # 现场供电 - 固定宽度
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)      # IO类型 - 固定宽度

        # 设置具体列宽
        self.preview_table.setColumnWidth(0, 100)  # 仪表位号
        self.preview_table.setColumnWidth(2, 100)  # 信号范围
        self.preview_table.setColumnWidth(3, 100)  # 数据范围
        self.preview_table.setColumnWidth(4, 60)   # 单位
        self.preview_table.setColumnWidth(5, 80)   # 信号类型
        self.preview_table.setColumnWidth(6, 100)  # 现场供电
        self.preview_table.setColumnWidth(7, 80)   # IO类型

        self.preview_table.setAlternatingRowColors(True)

        # 设置表格高度 - 预览表格不需要太大，用户主要是查看解析结果
        self.preview_table.setMinimumHeight(200)  # 减少高度，只显示部分数据供预览
        self.preview_table.setMaximumHeight(300)  # 限制最大高度

        # 设置表格可以拉伸
        from PySide6.QtWidgets import QSizePolicy
        self.preview_table.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        # 设置行高，确保每行不会太高
        self.preview_table.verticalHeader().setDefaultSectionSize(25)  # 设置默认行高为25像素
        self.preview_table.verticalHeader().setMinimumSectionSize(20)   # 最小行高20像素
        self.preview_table.verticalHeader().setMaximumSectionSize(40)   # 最大行高40像素

        # 确保显示垂直滚动条
        from PySide6.QtCore import Qt
        self.preview_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.preview_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
    def setup_mapping_table(self):
        """设置映射表格"""
        self.mapping_table.setColumnCount(6)
        headers = ["仪表位号", "检测点名称", "信号类型", "IO类型", "建议通道", "确认通道"]
        self.mapping_table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        header = self.mapping_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        
        self.mapping_table.setAlternatingRowColors(True)
        
    def select_document_file(self):
        """选择文档文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要导入的设计院文档",
            "",
            "Word 文档 (*.docx);;所有文件 (*)"
        )
        
        if file_path:
            self.selected_file_path = file_path
            file_name = os.path.basename(file_path)
            self.file_path_label.setText(f"已选择：{file_name}")
            self.file_path_label.setStyleSheet("color: #333;")
            
            # 启用解析按钮
            self.parse_document_btn.setEnabled(True)
            self.update_widget_states()
            
            logger.info(f"用户选择了文档文件: {file_path}")
            
    def parse_document(self):
        """解析文档"""
        if not self.selected_file_path:
            QMessageBox.warning(self, "错误", "请先选择文档文件")
            return

        try:
            # 使用真实的文档解析功能
            self.real_document_parsing()
        except Exception as e:
            logger.error(f"文档解析失败: {e}")
            QMessageBox.critical(self, "解析失败", f"文档解析失败：\n{str(e)}")
            # 如果真实解析失败，回退到模拟解析
            self.simulate_document_parsing()
        
    def simulate_document_parsing(self):
        """模拟文档解析（临时实现）"""
        # 模拟解析出的点位数据
        self.extracted_points = [
            {
                'instrument_tag': 'PT-1101',
                'description': '进站压力检测',
                'signal_type': '4-20mA',
                'io_type': 'AI',
                'suggested_channel': 'AI-01'
            },
            {
                'instrument_tag': 'UA-1202',
                'description': '出站故障报警',
                'signal_type': '开关量',
                'io_type': 'DI',
                'suggested_channel': 'DI-01'
            },
            {
                'instrument_tag': 'XO-1101',
                'description': '进站紧急切断阀',
                'signal_type': '0/24VDC',
                'io_type': 'DO',
                'suggested_channel': 'DO-01'
            }
        ]
        
        # 更新预览表格
        self.update_preview_table()
        
        # 启用第三步
        self.step3_group.setEnabled(True)
        self.update_mapping_table()
        
        # 更新状态
        self.preview_info_label.setText(f"解析完成，识别到 {len(self.extracted_points)} 个点位")
        self.mapping_info_label.setText(f"请确认 {len(self.extracted_points)} 个点位的通道分配")
        
        logger.info(f"文档解析完成（模拟），识别到 {len(self.extracted_points)} 个点位")

    def real_document_parsing(self):
        """真实的文档解析实现"""
        try:
            print(f"\n=== 开始解析文档: {self.selected_file_path} ===")

            # 导入文档解析模块
            from core.document_parser.excel_parser import create_parser

            # 创建解析器
            parser = create_parser(self.selected_file_path)
            print(f"✅ 使用解析器: {type(parser).__name__}")

            # 解析文档
            raw_points = parser.parse_document(self.selected_file_path)
            print(f"✅ 解析到 {len(raw_points)} 个原始点位")

            # 打印原始解析结果
            print("\n--- 原始解析结果 ---")
            for i, point in enumerate(raw_points[:5]):  # 只显示前5个
                print(f"点位 {i+1}: {point}")
            if len(raw_points) > 5:
                print(f"... 还有 {len(raw_points) - 5} 个点位")

            # 简化处理：直接使用原始点位数据，添加基本的IO类型识别
            enhanced_points = []
            for point in raw_points:
                # 从raw_data中获取完整信息，如果直接字段为空的话
                raw_data = point.get('raw_data', point)

                enhanced_point = {
                    'instrument_tag': point.get('instrument_tag', ''),
                    'description': point.get('description', ''),
                    'signal_range': raw_data.get('signal_range', ''),  # 信号范围 (如 4~20mA)
                    'data_range': raw_data.get('data_range', ''),      # 数据范围 (如 0-6, -20~80)
                    'signal_type': point.get('signal_type', ''),       # 信号类型 (如 AI, DI)
                    'units': raw_data.get('units', ''),               # 单位 (如 MPa, ℃)
                    'power_supply': raw_data.get('power_supply', ''),  # 现场仪表供电
                    'isolation': raw_data.get('isolation', ''),       # 隔离
                    'io_type': self._simple_io_type_detection(point),
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

            # 统计信息
            stats = {}
            for point in enhanced_points:
                io_type = point['io_type']
                stats[io_type] = stats.get(io_type, 0) + 1

            print(f"\n--- IO类型统计 ---")
            # 按照优先级排序显示
            type_order = ['AI', 'AO', 'DI', 'DO', 'COMM', 'UNKNOWN']
            for io_type in type_order:
                if io_type in stats:
                    print(f"{io_type}: {stats[io_type]} 个")
            # 显示其他未预期的类型
            for io_type, count in sorted(stats.items()):
                if io_type not in type_order:
                    print(f"{io_type}: {count} 个")

            # 打印增强后的结果
            print(f"\n--- 增强后的点位信息 ---")
            for i, point in enumerate(enhanced_points[:3]):  # 只显示前3个
                print(f"点位 {i+1}: {point['instrument_tag']} -> {point['io_type']} -> {point['suggested_channel']}")

            # 更新提取的点位数据
            self.extracted_points = enhanced_points
            self.parsed_points = enhanced_points  # 同时设置parsed_points，供导入功能使用

            # 保存解析数据到数据库
            self._save_parsed_data(enhanced_points)

            # 更新预览表格
            self.update_preview_table()

            # 启用第三步
            self.step3_group.setEnabled(True)
            self.update_mapping_table()

            # 更新状态
            self.preview_info_label.setText(f"解析完成，识别到 {len(self.extracted_points)} 个点位")
            self.mapping_info_label.setText(f"请确认 {len(self.extracted_points)} 个点位的通道分配")

            # 显示统计信息
            stats_text = ", ".join([f"{k}: {v}" for k, v in stats.items()])
            self.status_changed.emit(f"文档解析完成 - {stats_text}")

            print(f"\n✅ 文档解析完成，共处理 {len(self.extracted_points)} 个点位")
            print("=== 解析完成 ===\n")

            # 自动跳转到通道分配页面
            self.goto_channel_assignment_page()

        except NotImplementedError as e:
            print(f"⚠️ 解析器功能未实现: {e}")
            QMessageBox.information(
                self,
                "功能提示",
                f"当前文件格式的解析功能正在开发中。\n\n{str(e)}\n\n将使用模拟数据进行演示。"
            )
            # 回退到模拟解析
            self.simulate_document_parsing()

        except Exception as e:
            print(f"❌ 真实文档解析失败: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _simple_io_type_detection(self, point):
        """简单的IO类型检测"""
        instrument_tag = point.get('instrument_tag', '').upper()
        description = point.get('description', '').lower()
        signal_type = point.get('signal_type', '').upper()

        # 打印调试信息
        print(f"检测IO类型: {instrument_tag} | {description} | {signal_type}")

        # 1. 优先根据信号类型判断
        if signal_type in ['AI', 'AO', 'DI', 'DO']:
            print(f"  -> 直接从信号类型识别: {signal_type}")
            return signal_type

        # 1.1 通信设备识别
        if signal_type in ['RS485', 'TCP/IP', 'MODBUS', 'PROFIBUS', 'CAN']:
            print(f"  -> 识别为通信设备: {signal_type}")
            return 'COMM'  # 通信设备

        # 2. 根据仪表位号前缀判断
        if instrument_tag:
            # AI类型前缀
            if any(instrument_tag.startswith(prefix) for prefix in ['PT', 'TT', 'FT', 'LT', 'PDT', 'TDT', 'FDT']):
                print(f"  -> 从位号前缀识别为AI: {instrument_tag}")
                return 'AI'
            # DI类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['XS', 'HS', 'LS', 'PS', 'TS', 'FS', 'UA', 'LA']):
                print(f"  -> 从位号前缀识别为DI: {instrument_tag}")
                return 'DI'
            # DO类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['XO', 'HO', 'LO', 'PO', 'TO', 'FO', 'XV', 'HV', 'ZSL', 'ZSH']):
                print(f"  -> 从位号前缀识别为DO: {instrument_tag}")
                return 'DO'
            # AO类型前缀
            elif any(instrument_tag.startswith(prefix) for prefix in ['PIC', 'TIC', 'FIC', 'LIC', 'PCV', 'TCV', 'FCV']):
                print(f"  -> 从位号前缀识别为AO: {instrument_tag}")
                return 'AO'

        # 3. 根据描述关键字判断
        # AI类型关键字
        if any(keyword in description for keyword in ['压力', '温度', '流量', '液位', '差压', '检测', '测量', '监测']):
            print(f"  -> 从描述关键字识别为AI: {description}")
            return 'AI'
        # DI类型关键字
        elif any(keyword in description for keyword in ['状态', '故障', '报警', '开关', '干接点', '位置', '反馈', '信号']):
            print(f"  -> 从描述关键字识别为DI: {description}")
            return 'DI'
        # DO类型关键字
        elif any(keyword in description for keyword in ['控制', '启动', '停止', '阀门', '继电器', '输出', '驱动', '操作']):
            print(f"  -> 从描述关键字识别为DO: {description}")
            return 'DO'
        # AO类型关键字
        elif any(keyword in description for keyword in ['设定', '调节', '控制输出', '模拟输出']):
            print(f"  -> 从描述关键字识别为AO: {description}")
            return 'AO'

        print(f"  -> 无法识别，标记为UNKNOWN")
        return 'UNKNOWN'

    def update_preview_table(self):
        """更新预览表格"""
        self.preview_table.setRowCount(len(self.extracted_points))

        for row, point in enumerate(self.extracted_points):
            self.preview_table.setItem(row, 0, QTableWidgetItem(point.get('instrument_tag', '')))     # 仪表位号
            self.preview_table.setItem(row, 1, QTableWidgetItem(point.get('description', '')))       # 检测点名称
            self.preview_table.setItem(row, 2, QTableWidgetItem(point.get('signal_range', '')))      # 信号范围
            self.preview_table.setItem(row, 3, QTableWidgetItem(point.get('data_range', '')))        # 数据范围
            self.preview_table.setItem(row, 4, QTableWidgetItem(point.get('units', '')))             # 单位
            self.preview_table.setItem(row, 5, QTableWidgetItem(point.get('signal_type', '')))       # 信号类型
            self.preview_table.setItem(row, 6, QTableWidgetItem(point.get('power_supply', '')))      # 现场供电
            self.preview_table.setItem(row, 7, QTableWidgetItem(point.get('io_type', '')))           # IO类型
            
    def update_mapping_table(self):
        """更新映射表格"""
        # TODO: 获取真实的可用通道列表
        self.available_channels = {
            'AI': ['AI-01', 'AI-02', 'AI-03', 'AI-04'],
            'DI': ['DI-01', 'DI-02', 'DI-03', 'DI-04'],
            'DO': ['DO-01', 'DO-02', 'DO-03', 'DO-04'],
            'AO': ['AO-01', 'AO-02']
        }
        
        self.mapping_table.setRowCount(len(self.extracted_points))
        
        for row, point in enumerate(self.extracted_points):
            # 基本信息
            self.mapping_table.setItem(row, 0, QTableWidgetItem(point.get('instrument_tag', '')))
            self.mapping_table.setItem(row, 1, QTableWidgetItem(point.get('description', '')))
            self.mapping_table.setItem(row, 2, QTableWidgetItem(point.get('signal_type', '')))
            self.mapping_table.setItem(row, 3, QTableWidgetItem(point.get('io_type', '')))
            self.mapping_table.setItem(row, 4, QTableWidgetItem(point.get('suggested_channel', '')))
            
            # 确认通道下拉框
            channel_combo = QComboBox()
            channel_combo.addItem("")  # 空选项
            
            io_type = point.get('io_type', '')
            if io_type in self.available_channels:
                for channel in self.available_channels[io_type]:
                    channel_combo.addItem(channel)
            
            # 设置建议通道为默认选择
            suggested_channel = point.get('suggested_channel', '')
            if suggested_channel:
                index = channel_combo.findText(suggested_channel)
                if index >= 0:
                    channel_combo.setCurrentIndex(index)
            
            self.mapping_table.setCellWidget(row, 5, channel_combo)
            
        # 启用第四步
        self.step4_group.setEnabled(True)
        self.goto_assignment_btn.setEnabled(True)
        
    def apply_all_suggestions(self):
        """应用所有建议的通道分配"""
        for row in range(self.mapping_table.rowCount()):
            suggested_channel = self.mapping_table.item(row, 4).text()
            if suggested_channel:
                combo = self.mapping_table.cellWidget(row, 5)
                if combo:
                    index = combo.findText(suggested_channel)
                    if index >= 0:
                        combo.setCurrentIndex(index)
        
        logger.info("已应用所有建议的通道分配")
        
    def clear_all_mappings(self):
        """清空所有映射"""
        for row in range(self.mapping_table.rowCount()):
            combo = self.mapping_table.cellWidget(row, 5)
            if combo:
                combo.setCurrentIndex(0)  # 设置为空选项
        
        logger.info("已清空所有通道映射")
        
    def smart_channel_matching(self):
        """智能通道匹配（预留功能）"""
        QMessageBox.information(self, "功能预告", "智能通道匹配功能将在后续版本中实现。")
        
    def confirm_import(self):
        """确认导入 - 实现真正的数据转换和导入逻辑"""
        try:
            # 检查是否有映射数据
            if not hasattr(self, 'parsed_points') or not self.parsed_points:
                QMessageBox.warning(self, "错误", "没有可导入的数据，请先解析文档。")
                return

            # 收集用户确认的映射关系
            mapping_data = self._collect_mapping_data()
            if not mapping_data:
                QMessageBox.warning(self, "错误", "请至少分配一个通道后再导入。")
                return

            # 开始导入流程
            self._start_real_import_process(mapping_data)

        except Exception as e:
            logger.error(f"确认导入时发生错误: {e}")
            QMessageBox.critical(self, "导入失败", f"导入过程中发生错误：\n{str(e)}")
            self.status_text.setPlainText("导入失败")

    def _collect_mapping_data(self) -> List[Dict[str, Any]]:
        """收集用户确认的映射关系数据"""
        mapping_data = []

        for row in range(self.mapping_table.rowCount()):
            # 获取通道分配下拉框
            channel_combo = self.mapping_table.cellWidget(row, 5)
            if not channel_combo or channel_combo.currentText() == "未分配":
                continue  # 跳过未分配的行

            # 收集该行的所有数据
            point_data = {
                'instrument_tag': self.mapping_table.item(row, 0).text(),
                'description': self.mapping_table.item(row, 1).text(),
                'signal_type': self.mapping_table.item(row, 2).text(),
                'io_type': self.mapping_table.item(row, 3).text(),
                'suggested_channel': self.mapping_table.item(row, 4).text(),
                'assigned_channel': channel_combo.currentText(),
                'original_data': self.parsed_points[row] if row < len(self.parsed_points) else {}
            }
            mapping_data.append(point_data)

        logger.info(f"收集到 {len(mapping_data)} 个有效的映射数据")
        return mapping_data

    def _start_real_import_process(self, mapping_data: List[Dict[str, Any]]):
        """开始真正的导入流程"""
        try:
            # 更新状态
            self.status_text.setPlainText("正在转换数据格式...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(10)

            # 第一步：转换为标准IO点表格式
            excel_file_path = self._convert_mapping_to_excel(mapping_data)
            self.progress_bar.setValue(40)

            # 第二步：调用现有的导入功能
            self.status_text.append("正在导入到IO点表...")
            success = self._import_excel_to_io_table(excel_file_path)
            self.progress_bar.setValue(80)

            if success:
                self.status_text.append("导入完成！")
                self.progress_bar.setValue(100)
                self.result_file_path = excel_file_path
                self.open_folder_btn.setEnabled(True)

                # 显示成功消息
                QMessageBox.information(
                    self,
                    "导入成功",
                    f"成功导入 {len(mapping_data)} 个点位数据！\n\n"
                    f"生成的文件：{excel_file_path}"
                )
            else:
                self.status_text.append("导入失败")
                QMessageBox.warning(self, "导入失败", "数据导入过程中发生错误，请检查日志。")

        except Exception as e:
            logger.error(f"导入流程发生错误: {e}")
            self.status_text.append(f"导入失败: {str(e)}")
            QMessageBox.critical(self, "导入失败", f"导入过程中发生错误：\n{str(e)}")
        finally:
            self.progress_bar.setVisible(False)

    def _convert_mapping_to_excel(self, mapping_data: List[Dict[str, Any]]) -> str:
        """将映射数据转换为标准IO点表Excel格式"""
        import pandas as pd
        import tempfile
        import os

        try:
            # 创建输出文件 - 保存到项目目录的outputs文件夹
            import os
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # 回到项目根目录
            output_dir = os.path.join(project_root, "outputs", "imported_io_tables")

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            excel_file_path = os.path.join(output_dir, f"导入的IO点表_{timestamp}.xlsx")

            # 去重处理 - 根据仪表位号去重，保留第一个出现的
            seen_tags = set()
            unique_mapping_data = []
            for point in mapping_data:
                tag = point.get('instrument_tag', '')
                if tag and tag not in seen_tags:
                    seen_tags.add(tag)
                    unique_mapping_data.append(point)
                elif tag:
                    logger.warning(f"发现重复的仪表位号 {tag}，已跳过")

            logger.info(f"去重前: {len(mapping_data)} 个点位，去重后: {len(unique_mapping_data)} 个点位")

            # 准备Excel数据 - 使用现有系统要求的列名
            excel_data = []
            for i, point in enumerate(unique_mapping_data, 1):
                # 解析通道信息
                assigned_channel = point['assigned_channel']
                channel_parts = assigned_channel.split('-')
                io_type = channel_parts[0] if len(channel_parts) > 0 else ''
                channel_num = channel_parts[1] if len(channel_parts) > 1 else ''

                # 推断数据类型
                data_type = self._infer_data_type(point['io_type'], point['signal_type'])

                # 构建Excel行数据（严格按照现有系统的HEADER_TO_ATTRIBUTE_MAP格式）
                row_data = {
                    # 必需的基础字段
                    '序号': str(i),
                    '通道位号': assigned_channel,  # 使用完整的通道位号，如 "AI-01"
                    '变量名称（HMI）': point['instrument_tag'],  # 使用仪表位号作为HMI变量名
                    '变量描述': point['description'],
                    '数据类型': data_type,

                    # 可选字段 - 从原始数据中提取
                    '单位': point['original_data'].get('units', ''),

                    # 模块信息 - 根据IO类型推断
                    '模块名称': f"{io_type}_Module",
                    '模块类型': self._get_module_type(io_type),

                    # 供电和线制信息
                    '供电类型（有源/无源）': self._infer_power_type(point['original_data'].get('power_supply', '')),
                    '线制': self._infer_wiring_system(point['signal_type']),

                    # 场站信息
                    '场站名': self.current_site_name or '',
                    '场站编号': '',  # 暂时留空，可以后续填充

                    # 其他字段暂时留空，符合系统要求
                    '保存历史': 'Y' if io_type == 'AI' else 'N',
                    '掉电保护': 'N',

                    # 量程信息
                    '量程低限': self._extract_range_low(point['original_data']),
                    '量程高限': self._extract_range_high(point['original_data']),

                    # 报警设定值 - 添加缺失的必需列
                    'SLL设定值': '',  # 超低低报警设定值
                    'SL设定值': '',   # 低报警设定值
                    'SH设定值': '',   # 高报警设定值
                    'SHH设定值': '',  # 超高高报警设定值

                    # PLC和通讯地址暂时留空，由系统后续生成
                    'PLC绝对地址': '',
                    '上位机通讯地址': '',
                }
                excel_data.append(row_data)

            # 创建DataFrame并保存为Excel，使用标准的工作表名称
            df = pd.DataFrame(excel_data)
            df.to_excel(excel_file_path, index=False, sheet_name='IO点表')  # 使用标准工作表名

            logger.info(f"成功生成标准格式Excel文件: {excel_file_path}")
            logger.info(f"包含 {len(excel_data)} 个IO点位数据")
            return excel_file_path

        except Exception as e:
            logger.error(f"转换Excel格式时发生错误: {e}")
            raise Exception(f"数据格式转换失败: {str(e)}")

    def _infer_data_type(self, io_type: str, signal_type: str) -> str:
        """根据IO类型和信号类型推断数据类型"""
        if io_type in ['AI', 'AO']:
            return 'REAL'  # 模拟量通常是实数
        elif io_type in ['DI', 'DO']:
            return 'BOOL'  # 数字量通常是布尔值
        else:
            return 'REAL'  # 默认为实数

    def _get_module_type(self, io_type: str) -> str:
        """根据IO类型获取模块类型"""
        module_types = {
            'AI': 'AI模块',
            'AO': 'AO模块',
            'DI': 'DI模块',
            'DO': 'DO模块'
        }
        return module_types.get(io_type, 'AI模块')

    def _infer_power_type(self, power_supply: str) -> str:
        """推断供电类型"""
        if not power_supply:
            return '有源'  # 默认有源

        power_supply_lower = power_supply.lower()
        if '无源' in power_supply or 'passive' in power_supply_lower:
            return '无源'
        else:
            return '有源'

    def _infer_wiring_system(self, signal_type: str) -> str:
        """推断线制"""
        if not signal_type:
            return '4线制'  # 默认4线制

        signal_lower = signal_type.lower()
        if '2线' in signal_type or '2-wire' in signal_lower:
            return '2线制'
        elif '3线' in signal_type or '3-wire' in signal_lower:
            return '3线制'
        else:
            return '4线制'  # 默认4线制

    def _extract_range_low(self, original_data: Dict[str, Any]) -> str:
        """提取量程低限"""
        data_range = original_data.get('data_range', '')
        signal_range = original_data.get('signal_range', '')

        # 尝试从数据范围或信号范围中提取低限
        for range_str in [data_range, signal_range]:
            if range_str and '~' in range_str:
                parts = range_str.split('~')
                if len(parts) >= 2:
                    try:
                        # 提取数字部分
                        low_str = parts[0].strip()
                        # 移除单位，只保留数字
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', low_str)
                        if numbers:
                            return numbers[0]
                    except:
                        pass
        return '0'  # 默认值

    def _extract_range_high(self, original_data: Dict[str, Any]) -> str:
        """提取量程高限"""
        data_range = original_data.get('data_range', '')
        signal_range = original_data.get('signal_range', '')

        # 尝试从数据范围或信号范围中提取高限
        for range_str in [data_range, signal_range]:
            if range_str and '~' in range_str:
                parts = range_str.split('~')
                if len(parts) >= 2:
                    try:
                        # 提取数字部分
                        high_str = parts[1].strip()
                        # 移除单位，只保留数字
                        import re
                        numbers = re.findall(r'-?\d+\.?\d*', high_str)
                        if numbers:
                            return numbers[0]
                    except:
                        pass
        return '100'  # 默认值

    def _import_excel_to_io_table(self, excel_file_path: str) -> bool:
        """调用现有的导入功能将Excel数据导入到IO点表"""
        try:
            # 使用现有的Excel数据加载功能
            from core.post_upload_processor.uploaded_file_processor.excel_reader import load_workbook_data
            from core.post_upload_processor.io_validation.validator import validate_io_table

            # 第一步：验证Excel文件格式
            logger.info(f"开始验证Excel文件: {excel_file_path}")
            is_valid, validation_message = validate_io_table(excel_file_path)

            if not is_valid:
                logger.error(f"Excel文件验证失败: {validation_message}")
                QMessageBox.warning(self.parent(), "文件验证失败", f"生成的Excel文件格式不符合要求：\n{validation_message}")
                return False

            # 第二步：加载Excel数据
            logger.info(f"开始加载Excel数据: {excel_file_path}")
            loaded_data_dict, error_msg_load = load_workbook_data(excel_file_path)

            if error_msg_load:
                logger.error(f"加载Excel数据失败: {error_msg_load}")
                QMessageBox.critical(self.parent(), "数据加载失败", f"加载Excel数据时发生错误：\n{error_msg_load}")
                return False

            if not loaded_data_dict:
                logger.error("加载的数据为空")
                QMessageBox.warning(self.parent(), "数据为空", "Excel文件中没有找到有效的IO点数据。")
                return False

            # 第三步：通知主窗口更新数据
            if hasattr(self, 'parent') and hasattr(self.parent(), 'loaded_io_data_by_sheet'):
                # 更新主窗口的数据
                self.parent().loaded_io_data_by_sheet = loaded_data_dict
                self.parent().verified_io_table_path = excel_file_path

                # 计算总点位数
                total_points = sum(len(points) for points in loaded_data_dict.values())
                logger.info(f"成功导入 {total_points} 个IO点位数据")

                # 更新主窗口状态
                if hasattr(self.parent(), 'status_bar'):
                    self.parent().status_bar.showMessage(f"成功导入 {total_points} 个IO点位", 5000)

                return True
            else:
                # 如果无法更新主窗口，至少验证数据加载成功
                total_points = sum(len(points) for points in loaded_data_dict.values())
                logger.info(f"Excel数据加载成功，共 {total_points} 个点位，但无法更新主窗口状态")
                return True

        except Exception as e:
            logger.error(f"调用现有导入功能时发生错误: {e}")
            QMessageBox.critical(self.parent(), "导入失败", f"导入过程中发生错误：\n{str(e)}")
            return False

    def simulate_import_process(self):
        """模拟导入过程"""
        self.progress_bar.setVisible(True)
        self.status_text.setPlainText("开始处理导入...\n")
        
        # 模拟进度
        for i in range(101):
            self.progress_bar.setValue(i)
            if i == 25:
                self.status_text.append("正在转换数据格式...")
            elif i == 50:
                self.status_text.append("正在生成IO点表文件...")
            elif i == 75:
                self.status_text.append("正在调用现有导入功能...")
            elif i == 100:
                self.status_text.append("导入完成！")
                
        # 模拟生成结果文件
        self.result_file_path = "IO点表模板/测试场站_IO_点表_导入填充.xlsx"
        self.status_text.append(f"\n生成文件：{self.result_file_path}")
        
        # 启用打开文件夹按钮
        self.open_folder_btn.setEnabled(True)
        
        # 发出完成信号
        self.import_completed.emit(self.result_file_path)
        
        logger.info("导入过程完成（模拟）")
        
    def open_result_folder(self):
        """打开结果文件夹"""
        if self.result_file_path:
            folder_path = os.path.dirname(self.result_file_path)
            os.startfile(folder_path)
        
    def reset_all(self):
        """重置所有状态"""
        # 重置状态变量
        self.selected_file_path = None
        self.extracted_points = []
        self.parsed_points = []
        self.available_channels = {}
        self.mapping_result = []
        self.result_file_path = None
        
        # 重置UI状态
        self.file_path_label.setText("未选择文件")
        self.file_path_label.setStyleSheet("color: #666; font-style: italic;")
        self.parse_document_btn.setEnabled(False)
        
        self.preview_info_label.setText("等待文档解析...")
        self.preview_table.setRowCount(0)
        
        self.mapping_info_label.setText("等待数据解析完成...")
        self.mapping_table.setRowCount(0)
        
        self.status_text.setPlainText("等待开始处理...")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
        # 重置按钮状态
        self.update_widget_states()
        
        logger.info("已重置所有状态")
        
    def update_widget_states(self):
        """更新组件状态"""
        # 根据当前状态启用/禁用相应的组件
        has_file = bool(self.selected_file_path)
        has_parsed_data = bool(self.extracted_points)
        
        self.step2_group.setEnabled(has_file)
        self.step3_group.setEnabled(has_parsed_data)
        self.step4_group.setEnabled(has_parsed_data)

        # self.confirm_import_btn.setEnabled(has_parsed_data)  # 按钮不存在，注释掉
        # self.open_folder_btn.setEnabled(bool(self.result_file_path))  # 按钮不存在，注释掉
        
    def set_current_site_name(self, site_name: str):
        """设置当前场站名称"""
        self.current_site_name = site_name
        logger.info(f"文档导入组件：当前场站已更新为 {site_name}")
        
    def set_io_data_loader(self, io_data_loader):
        """设置IO数据加载器"""
        self.io_data_loader = io_data_loader
        logger.info("文档导入组件：IO数据加载器已更新")

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
                    self.selected_file_path = file_path
                    file_name = os.path.basename(file_path)
                    self.file_path_label.setText(f"已选择：{file_name}")
                    self.file_path_label.setStyleSheet("color: #333;")

                    # 启用解析按钮
                    self.parse_document_btn.setEnabled(True)
                    self.update_widget_states()

                    logger.info(f"通过拖拽选择了文档文件: {file_path}")
                    event.acceptProposedAction()
                    return
        event.ignore()

    def _save_parsed_data(self, enhanced_points: List[Dict[str, Any]]):
        """保存解析数据到数据库"""
        try:
            # 如果没有当前项目，创建一个新项目
            if self.current_project_id is None:
                import os
                from datetime import datetime

                # 从文件名生成项目名
                if self.selected_file_path:
                    project_name = f"解析项目_{os.path.basename(self.selected_file_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                else:
                    project_name = f"解析项目_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                self.current_project_id = self.parsed_data_dao.create_project(
                    name=project_name,
                    description=f"从文档 {self.selected_file_path} 解析的数据"
                )
                logger.info(f"Created new project: {project_name} (ID: {self.current_project_id})")

            # 转换为ParsedPoint对象
            from core.data_storage.data_models import ParsedPoint
            parsed_points = []

            for point_data in enhanced_points:
                original_data = point_data.get('original_data', {})

                parsed_point = ParsedPoint(
                    project_id=self.current_project_id,
                    instrument_tag=point_data.get('instrument_tag', ''),
                    description=point_data.get('description', ''),
                    signal_type=point_data.get('signal_type', ''),
                    io_type=point_data.get('io_type', ''),
                    units=original_data.get('units', ''),
                    data_range=original_data.get('data_range', ''),
                    signal_range=original_data.get('signal_range', ''),
                    power_supply=original_data.get('power_supply', ''),
                    isolation=original_data.get('isolation', ''),
                    remarks=original_data.get('remarks', ''),
                    original_data=original_data
                )
                parsed_points.append(parsed_point)

            # 保存到数据库
            success = self.parsed_data_dao.save_parsed_points(self.current_project_id, parsed_points)
            if success:
                logger.info(f"Saved {len(parsed_points)} points to project {self.current_project_id}")
                self.status_text.append(f"✅ 已保存 {len(parsed_points)} 个点位到数据库")
            else:
                logger.error("Failed to save parsed points")
                self.status_text.append("❌ 保存解析数据失败")

        except Exception as e:
            logger.error(f"Error saving parsed data: {e}")
            self.status_text.append(f"❌ 保存数据时出错: {str(e)}")

    def goto_channel_assignment_page(self):
        """跳转到通道分配页面"""
        try:
            if not self.current_project_id:
                QMessageBox.warning(self, "错误", "没有可用的项目数据，请先解析文档。")
                return

            # 创建默认的分配方案
            from core.data_storage.assignment_dao import AssignmentDAO
            assignment_dao = AssignmentDAO()

            # 检查是否已有分配方案
            existing_schemes = assignment_dao.list_assignments(self.current_project_id)

            if existing_schemes:
                # 使用第一个现有方案
                scheme_id = existing_schemes[0].id
                logger.info(f"使用现有分配方案: {scheme_id}")
            else:
                # 创建新的分配方案
                from datetime import datetime
                scheme_name = f"默认方案_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                scheme_id = assignment_dao.create_assignment(
                    self.current_project_id,
                    scheme_name,
                    "从文档导入自动创建的分配方案"
                )

                if not scheme_id:
                    QMessageBox.critical(self, "错误", "创建分配方案失败")
                    return

                logger.info(f"创建新分配方案: {scheme_name} (ID: {scheme_id})")

            # 发出跳转信号
            self.goto_channel_assignment.emit(self.current_project_id, scheme_id)
            logger.info(f"跳转到通道分配页面: project_id={self.current_project_id}, scheme_id={scheme_id}")

        except Exception as e:
            logger.error(f"跳转到通道分配页面失败: {e}")
            QMessageBox.critical(self, "错误", f"跳转失败：\n{str(e)}")
