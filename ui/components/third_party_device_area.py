"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog)
from datetime import datetime
import logging
from ui.dialogs.device_point_dialog import DevicePointDialog

class ThirdPartyDeviceArea(QGroupBox):
    """已配置的第三方设备区域"""
    def __init__(self, device_manager, parent=None):
        super().__init__("已配置的第三方设备", parent)
        self.device_manager = device_manager
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout()
        
        # 第三方设备表格
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(4)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "变量名", "点位数量", "状态"])

        # 设置列宽
        header = self.third_party_table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.third_party_table)

        # 按钮区域
        button_layout = QVBoxLayout()
        
        self.third_party_btn = QPushButton("第三方设备点表配置")
        self.export_btn = QPushButton("导出点表")
        self.clear_config_btn = QPushButton("清空配置")

        button_layout.addWidget(self.third_party_btn)
        button_layout.addWidget(self.export_btn)
        button_layout.addWidget(self.clear_config_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.third_party_btn.clicked.connect(self.configure_third_party_device)
        self.export_btn.clicked.connect(self.export_points_table)
        self.clear_config_btn.clicked.connect(self.clear_device_config)

    def configure_third_party_device(self):
        """配置第三方设备点表"""
        try:
            dialog = DevicePointDialog(self)
            if dialog.exec() == QDialog.Accepted:
                new_points = dialog.get_device_points()
                if new_points:
                    self.device_manager.add_device_points(new_points)
                    self.update_third_party_table()
                    QMessageBox.information(self, "成功", f"已配置 {len(new_points)} 个点位")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"配置设备点表时发生错误: {str(e)}")

    def update_third_party_table(self):
        """更新第三方设备列表"""
        try:
            self.third_party_table.setRowCount(0)
            device_stats = self.device_manager.update_third_party_table_data()
            
            for device in device_stats:
                row = self.third_party_table.rowCount()
                self.third_party_table.insertRow(row)
                self.third_party_table.setItem(row, 0, QTableWidgetItem(device['template']))
                self.third_party_table.setItem(row, 1, QTableWidgetItem(device['variable']))
                self.third_party_table.setItem(row, 2, QTableWidgetItem(str(device['count'])))
                self.third_party_table.setItem(row, 3, QTableWidgetItem(device['status']))
        except Exception as e:
            logging.error(f"更新第三方设备列表时发生错误: {e}")

    def clear_device_config(self):
        """清空设备配置"""
        if not self.device_manager.get_device_points():
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.device_manager.clear_device_points()
            self.update_third_party_table()
            QMessageBox.information(self, "已清空", "已清空所有设备配置")

    def export_points_table(self, parent=None):
        """导出点表"""
        if not self.device_manager.get_device_points():
            QMessageBox.warning(self, "警告", "没有可导出的点位数据")
            return

        default_filename = f"第三方设备点表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        file_path, _ = QFileDialog.getSaveFileName(
            parent or self, "保存点表", default_filename, "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                self.device_manager.export_to_excel(file_path)
                QMessageBox.information(parent or self, "成功", f"点表已成功导出至 {file_path}")
            except Exception as e:
                QMessageBox.critical(parent or self, "错误", f"导出失败: {str(e)}") 