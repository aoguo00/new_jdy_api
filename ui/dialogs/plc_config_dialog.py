"""PLC配置对话框"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                           QComboBox, QPushButton, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox, QAbstractItemView)
from PySide6.QtCore import Qt
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class PLCConfigDialog(QDialog):
    """PLC配置对话框 - 仅界面版本，不包含数据库操作"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PLC配置")
        self.resize(1200, 700)  # 增加对话框宽度
        
        # 初始化本地变量
        self.rack_slots = ['' for _ in range(11)]  # 默认11个槽位
        
        # 设置UI
        self.setup_ui()
        self.setup_connections()
        
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
        header_left.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)      # 描述
        
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
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(5)
        self.config_table.setHorizontalHeaderLabels(['槽位', '型号', '类型', '通道数', '描述'])
        self.config_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.config_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.config_table.verticalHeader().setVisible(False)
        
        # 设置右侧表格列宽
        header_right = self.config_table.horizontalHeader()
        header_right.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # 槽位
        header_right.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # 型号
        header_right.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # 类型
        header_right.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents) # 通道数
        header_right.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)      # 描述
        
        # 设置相同的表格样式
        self.config_table.setStyleSheet(self.module_table.styleSheet())
        self.config_table.setAlternatingRowColors(True)
        
        right_layout.addWidget(self.config_table)
        module_layout.addLayout(right_layout)
        
        # 设置左右两侧布局的比例
        module_layout.setStretch(0, 1)  # 左侧表格
        module_layout.setStretch(2, 1)  # 右侧表格
        
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

    def setup_connections(self):
        """设置信号连接"""
        self.type_combo.currentTextChanged.connect(self.load_modules)
        self.add_button.clicked.connect(self.add_module)
        self.remove_button.clicked.connect(self.remove_module)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def load_modules(self):
        """加载模块列表（准备实现实际数据加载）"""
        self.module_table.setRowCount(0)
        # 实际数据加载逻辑将在以后实现

    def add_module(self):
        """添加模块到配置表"""
        selected_rows = self.module_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要添加的模块")
            return
        
        # 获取所选行
        row = selected_rows[0].row()
        
        # 获取模块数据
        model = self.module_table.item(row, 1).text()
        module_type = self.module_table.item(row, 2).text()
        channels = self.module_table.item(row, 3).text()
        description = self.module_table.item(row, 4).text()
        
        # 查找空槽位
        empty_slot_index = -1
        for i, slot_model in enumerate(self.rack_slots):
            if not slot_model:  # 空槽位
                empty_slot_index = i
                break
        
        # 如果没有空槽位，提示用户
        if empty_slot_index == -1:
            QMessageBox.warning(self, "提示", "所有槽位已满，请先移除一个模块")
            return
        
        # 添加到槽位
        self.rack_slots[empty_slot_index] = model
        
        # 更新配置表格
        self.update_config_table()

    def remove_module(self):
        """从配置表中移除模块"""
        selected_rows = self.config_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要移除的模块")
            return
        
        # 获取所选行
        row = selected_rows[0].row()
        
        # 获取槽位号
        slot_text = self.config_table.item(row, 0).text()
        if not slot_text.isdigit():
            return
            
        slot_index = int(slot_text) - 1
        
        # 清空该槽位
        self.rack_slots[slot_index] = ''
        
        # 更新配置表格
        self.update_config_table()

    def update_config_table(self):
        """更新配置表格"""
        self.config_table.setRowCount(0)
        
        # 真实数据加载逻辑将在以后实现
        # 目前仅保留基本结构

    def get_current_configuration(self) -> List[Dict[str, Any]]:
        """获取当前配置"""
        config = []
        for i, model in enumerate(self.rack_slots):
            if model:  # 有模块的槽位
                config.append({
                    "slot": i+1,  # 槽位号从1开始
                    "model": model
                })
        return config

    def accept(self):
        """确定按钮点击事件"""
        # 获取当前配置
        config = self.get_current_configuration()
        if not config:
            reply = QMessageBox.question(
                self, "提示", 
                "当前未配置任何模块，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 实际保存配置的逻辑将在以后实现
        super().accept()
        
    def reject(self):
        """取消按钮点击事件"""
        super().reject()

# 示例用法（用于测试，可以保留或删除）