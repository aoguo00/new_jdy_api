"""
通道映射确认对话框
用于设计院文档导入时的通道分配确认
"""

import logging
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QMessageBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class ChannelMappingDialog(QDialog):
    """通道映射确认对话框"""
    
    # 信号：用户确认映射后发出，携带映射结果
    mapping_confirmed = Signal(list)  # List[Dict[str, Any]]
    
    def __init__(self, extracted_points: List[Dict[str, Any]], 
                 available_channels: Dict[str, List[str]], 
                 source_file_name: str, 
                 parent=None):
        """
        初始化映射确认对话框
        
        Args:
            extracted_points: 从文档中提取的点位信息
            available_channels: 可用的通道列表，按IO类型分组
            source_file_name: 源文件名
            parent: 父窗口
        """
        super().__init__(parent)
        self.extracted_points = extracted_points
        self.available_channels = available_channels
        self.source_file_name = source_file_name
        self.mapping_result = []
        
        self.setWindowTitle("设计院文档导入 - 通道映射确认")
        self.setModal(True)
        self.resize(1000, 600)
        
        self.setup_ui()
        self.populate_table()
        
    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 标题区域
        title_layout = QHBoxLayout()
        title_label = QLabel(f"文件：{self.source_file_name}")
        title_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        count_label = QLabel(f"识别到 {len(self.extracted_points)} 个点位，请确认通道分配：")
        count_label.setFont(QFont("Arial", 9))
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(count_label)
        
        layout.addLayout(title_layout)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # 表格区域
        self.setup_table()
        layout.addWidget(self.table)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.apply_suggestions_btn = QPushButton("全部采用建议")
        self.apply_suggestions_btn.clicked.connect(self.apply_all_suggestions)
        
        self.clear_mapping_btn = QPushButton("清空映射")
        self.clear_mapping_btn.clicked.connect(self.clear_all_mappings)
        
        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.clicked.connect(self.save_mapping_template)
        self.save_template_btn.setEnabled(False)  # 暂时禁用，后续版本实现
        
        button_layout.addWidget(self.apply_suggestions_btn)
        button_layout.addWidget(self.clear_mapping_btn)
        button_layout.addWidget(self.save_template_btn)
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.confirm_btn = QPushButton("确认导入")
        self.confirm_btn.clicked.connect(self.confirm_mapping)
        self.confirm_btn.setDefault(True)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.confirm_btn)
        
        layout.addLayout(button_layout)
        
    def setup_table(self):
        """设置表格"""
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        
        headers = ["仪表位号", "检测点名称", "信号类型", "IO类型", "建议通道", "确认通道"]
        self.table.setHorizontalHeaderLabels(headers)
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # 仪表位号
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)           # 检测点名称
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # 信号类型
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # IO类型
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # 建议通道
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # 确认通道
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.extracted_points))
        
        for row, point in enumerate(self.extracted_points):
            # 仪表位号
            instrument_tag = point.get('instrument_tag', '')
            self.table.setItem(row, 0, QTableWidgetItem(instrument_tag))
            
            # 检测点名称
            description = point.get('description', '')
            self.table.setItem(row, 1, QTableWidgetItem(description))
            
            # 信号类型
            signal_type = point.get('signal_type', '')
            self.table.setItem(row, 2, QTableWidgetItem(signal_type))
            
            # IO类型
            io_type = point.get('io_type', '')
            self.table.setItem(row, 3, QTableWidgetItem(io_type))
            
            # 建议通道
            suggested_channel = point.get('suggested_channel', '')
            self.table.setItem(row, 4, QTableWidgetItem(suggested_channel))
            
            # 确认通道下拉框
            channel_combo = QComboBox()
            channel_combo.addItem("")  # 空选项
            
            # 添加对应IO类型的可用通道
            if io_type in self.available_channels:
                for channel in self.available_channels[io_type]:
                    channel_combo.addItem(channel)
            
            # 如果有建议通道，设置为默认选择
            if suggested_channel:
                index = channel_combo.findText(suggested_channel)
                if index >= 0:
                    channel_combo.setCurrentIndex(index)
            
            self.table.setCellWidget(row, 5, channel_combo)
            
    def apply_all_suggestions(self):
        """应用所有建议的通道分配"""
        for row in range(self.table.rowCount()):
            suggested_channel = self.table.item(row, 4).text()
            if suggested_channel:
                combo = self.table.cellWidget(row, 5)
                if combo:
                    index = combo.findText(suggested_channel)
                    if index >= 0:
                        combo.setCurrentIndex(index)
        
        logger.info("已应用所有建议的通道分配")
        
    def clear_all_mappings(self):
        """清空所有映射"""
        for row in range(self.table.rowCount()):
            combo = self.table.cellWidget(row, 5)
            if combo:
                combo.setCurrentIndex(0)  # 设置为空选项
        
        logger.info("已清空所有通道映射")
        
    def save_mapping_template(self):
        """保存映射模板（预留功能）"""
        QMessageBox.information(self, "功能预告", "映射模板保存功能将在后续版本中实现。")
        
    def confirm_mapping(self):
        """确认映射并生成结果"""
        self.mapping_result = []
        
        for row in range(self.table.rowCount()):
            point_data = self.extracted_points[row].copy()
            
            # 获取用户确认的通道
            combo = self.table.cellWidget(row, 5)
            confirmed_channel = combo.currentText() if combo else ""
            
            point_data['confirmed_channel'] = confirmed_channel
            self.mapping_result.append(point_data)
        
        # 检查是否有未分配通道的点位
        unassigned_count = sum(1 for point in self.mapping_result if not point['confirmed_channel'])
        
        if unassigned_count > 0:
            reply = QMessageBox.question(
                self, 
                "确认导入", 
                f"有 {unassigned_count} 个点位未分配通道，这些点位将被跳过。\n\n是否继续导入？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 发出确认信号
        self.mapping_confirmed.emit(self.mapping_result)
        self.accept()
        
        logger.info(f"用户确认映射，共 {len(self.mapping_result)} 个点位，其中 {len(self.mapping_result) - unassigned_count} 个已分配通道")
