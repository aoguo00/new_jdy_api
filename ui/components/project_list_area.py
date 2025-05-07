"""项目列表区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Signal

class ProjectListArea(QGroupBox):
    """项目列表区域"""
    # 信号定义
    project_selected = Signal(str)  # 场站名称
    update_finished = Signal(int)  # 更新完成信号，参数为更新数量
    update_failed = Signal(str)  # 更新失败信号，参数为错误信息

    def __init__(self, parent=None):
        super().__init__("项目列表", parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置项目列表区域UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.project_table = QTableWidget()
        self.project_table.setColumnCount(5)
        self.project_table.setHorizontalHeaderLabels(
            ["项目名称", "场站", "项目编号", "深化设计编号", "客户名称"])

        # 设置列宽和自适应
        header = self.project_table.horizontalHeader()
        header.setStretchLastSection(False)
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        # 设置表格选择行为
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        layout.addWidget(self.project_table)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.project_table.itemSelectionChanged.connect(self._on_selection_changed)
        
        # 连接自定义信号
        self.update_finished.connect(self._on_update_finished)
        self.update_failed.connect(self._on_update_failed)

    def _on_selection_changed(self):
        """处理选择变更"""
        selected_items = self.project_table.selectedItems()
        if selected_items:
            row = selected_items[0].row()
            site_name = self.project_table.item(row, 1).text()
            self.project_selected.emit(site_name)

    def _on_update_finished(self, count: int):
        """处理更新完成"""
        QMessageBox.information(self, "更新完成", f"共更新 {count} 条记录")

    def _on_update_failed(self, error: str):
        """处理更新失败"""
        QMessageBox.critical(self, "错误", f"更新项目列表失败: {error}")

    def update_project_list(self, data):
        """更新项目列表"""
        try:
            # 更新表格数据
            self.project_table.setRowCount(0)
            for row_data in data:
                row = self.project_table.rowCount()
                self.project_table.insertRow(row)
                self.project_table.setItem(row, 0, QTableWidgetItem(row_data.get('_widget_1635777114903', '')))
                self.project_table.setItem(row, 1, QTableWidgetItem(row_data.get('_widget_1635777114991', '')))
                self.project_table.setItem(row, 2, QTableWidgetItem(row_data.get('_widget_1635777114935', '')))
                self.project_table.setItem(row, 3, QTableWidgetItem(row_data.get('_widget_1636359817201', '')))
                self.project_table.setItem(row, 4, QTableWidgetItem(row_data.get('_widget_1635777114972', '')))
            
            # 发出更新完成信号
            self.update_finished.emit(len(data))
            
        except Exception as e:
            # 发出更新失败信号
            self.update_failed.emit(str(e))

    def clear_table(self):
        """清空表格"""
        self.project_table.setRowCount(0) 