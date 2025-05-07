"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog)
from datetime import datetime
import logging

# Updated imports for services and models
from core.services.device_configuration_service import DeviceConfigurationService
from core.devices.template_manager import TemplateManager # For DevicePointDialog
# from core.models.device_models import ConfiguredDevicePointModel # Not directly used here, but service returns it

from ui.dialogs.device_point_dialog import DevicePointDialog

logger = logging.getLogger(__name__) # Added logger

class ThirdPartyDeviceArea(QGroupBox):
    """已配置的第三方设备区域，使用DeviceConfigurationService"""
    def __init__(self, 
                 device_config_service: DeviceConfigurationService, 
                 template_manager: TemplateManager, # Needed for DevicePointDialog
                 parent=None):
        super().__init__("已配置的第三方设备", parent)
        
        # self.device_manager = device_manager # Replaced
        self.config_service = device_config_service
        self.template_manager = template_manager # Store for passing to dialog

        self.setup_ui()
        self.setup_connections()
        self.update_third_party_table() # Initial load of data
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout(self) # Added self to QVBoxLayout
        
        # 第三方设备表格
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(4)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "设备前缀", "点位数量", "状态"] # "变量名" changed to "设备前缀"
        )

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
            # Ensure keyword arguments match the actual DevicePointDialog __init__ signature
            dialog = DevicePointDialog(
                template_manager=self.template_manager, # Reverted to match DPD's actual param name
                config_service=self.config_service,   # Reverted to match DPD's actual param name
                parent=self
            )
            if dialog.exec() == QDialog.Accepted:
                self.update_third_party_table()
                QMessageBox.information(self, "成功", "设备点表配置已更新。")
        except Exception as e:
            logger.error(f"打开或处理设备点表配置对话框时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"配置设备点表时发生错误: {str(e)}")

    def update_third_party_table(self):
        """更新第三方设备列表"""
        try:
            self.third_party_table.setRowCount(0)
            # Get summary data from the configuration service
            device_stats = self.config_service.get_configuration_summary()
            
            for device_summary in device_stats: # Changed variable name for clarity
                row = self.third_party_table.rowCount()
                self.third_party_table.insertRow(row)
                self.third_party_table.setItem(row, 0, QTableWidgetItem(device_summary['template']))
                self.third_party_table.setItem(row, 1, QTableWidgetItem(device_summary['variable'])) # This is device_prefix
                self.third_party_table.setItem(row, 2, QTableWidgetItem(str(device_summary['count'])))
                self.third_party_table.setItem(row, 3, QTableWidgetItem(device_summary['status']))
        except Exception as e:
            logger.error(f"更新第三方设备列表时发生错误: {e}", exc_info=True)
            # Optionally, inform the user, though this is usually a background update
            # QMessageBox.warning(self, "更新错误", "无法刷新第三方设备列表。") 

    def clear_device_config(self):
        """清空设备配置"""
        # Check if there's anything to clear first
        if not self.config_service.get_all_configured_points():
            QMessageBox.information(self, "提示", "没有已配置的设备点表可以清空。")
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的第三方设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # Default to No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.config_service.clear_all_configurations()
                self.update_third_party_table() # Refresh table
                QMessageBox.information(self, "已清空", "已清空所有第三方设备配置。")
            except Exception as e:
                logger.error(f"清空设备配置时发生错误: {e}", exc_info=True)
                QMessageBox.critical(self, "错误", f"清空配置失败: {str(e)}")

    def export_points_table(self):
        """导出点表"""
        # Check if there is data to export
        if not self.config_service.get_all_configured_points():
            QMessageBox.warning(self, "警告", "没有可导出的第三方设备点位数据。")
            return

        default_filename = f"第三方设备点表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        # Ensure parent is self for QFileDialog to center it correctly
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存点表", default_filename, "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                self.config_service.export_to_excel(file_path)
                QMessageBox.information(self, "成功", f"点表已成功导出至 {file_path}")
            except ValueError as ve: # Specifically catch no data error from service
                logger.warning(f"导出点表失败 (ValueError): {ve}")
                QMessageBox.warning(self, "导出失败", str(ve))
            except Exception as e:
                logger.error(f"导出点表时发生未知错误: {e}", exc_info=True)
                QMessageBox.critical(self, "导出失败", f"导出点表时发生未知错误: {str(e)}") 