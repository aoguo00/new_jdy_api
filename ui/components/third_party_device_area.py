"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog)
from datetime import datetime
import logging

# 更新的服务和模型导入
# from core.services import DeviceConfigurationService, TemplateService # 旧导入
from core.third_party_config_area import ConfigService, TemplateService # 新导入
# from core.models.device_models import ConfiguredDevicePointModel # 这里不直接使用

from ui.dialogs.device_point_dialog import DevicePointDialog

logger = logging.getLogger(__name__) # 添加日志记录器

class ThirdPartyDeviceArea(QGroupBox):
    """已配置的第三方设备区域"""
    def __init__(self, 
                 config_service: ConfigService, 
                 template_service: TemplateService, 
                 parent=None):
        super().__init__("已配置的第三方设备", parent)
        
        self.config_service = config_service # 使用注入的ConfigService
        self.template_service = template_service # 使用注入的TemplateService

        self.setup_ui()
        self.setup_connections()
        self.update_third_party_table() # 初始加载数据
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout(self) # 将self添加到QVBoxLayout
        
        # 第三方设备表格
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(4)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "设备前缀", "点位数量", "状态"] # "变量名"改为"设备前缀"
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
            # 确保关键字参数与实际DevicePointDialog __init__签名匹配
            dialog = DevicePointDialog(
                template_service=self.template_service, # 传递新的TemplateService
                config_service=self.config_service,     # 传递新的ConfigService
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
            # 从配置服务获取摘要数据
            device_stats = self.config_service.get_configuration_summary()
            
            for device_summary in device_stats: # 为清晰起见更改变量名
                row = self.third_party_table.rowCount()
                self.third_party_table.insertRow(row)
                self.third_party_table.setItem(row, 0, QTableWidgetItem(device_summary['template']))
                self.third_party_table.setItem(row, 1, QTableWidgetItem(device_summary['variable'])) # 这是设备前缀
                self.third_party_table.setItem(row, 2, QTableWidgetItem(str(device_summary['count'])))
                self.third_party_table.setItem(row, 3, QTableWidgetItem(device_summary['status']))
        except Exception as e:
            logger.error(f"更新第三方设备列表时发生错误: {e}", exc_info=True)
            # 可选择通知用户，尽管这通常是后台更新
            # QMessageBox.warning(self, "更新错误", "无法刷新第三方设备列表。") 

    def clear_device_config(self):
        """清空设备配置"""
        # 首先检查是否有内容可以清除
        if not self.config_service or not self.config_service.get_all_configured_points():
            QMessageBox.information(self, "提示", "没有已配置的设备点表可以清空。")
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的第三方设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # 默认为否
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.config_service.clear_all_configurations()
                if success:
                    self.update_third_party_table() # 刷新表格
                    QMessageBox.information(self, "已清空", "已清空所有第三方设备配置。")
            except Exception as e:
                logger.error(f"清空设备配置时发生错误: {e}", exc_info=True)
                QMessageBox.critical(self, "错误", f"清空配置失败: {str(e)}")

    def export_points_table(self):
        """导出点表"""
        # 使用新服务检查是否有数据可导出
        if not self.config_service or not self.config_service.get_all_configured_points():
            QMessageBox.warning(self, "警告", "没有可导出的第三方设备点位数据。")
            return

        default_filename = f"第三方设备点表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        # 确保parent是self以便QFileDialog正确居中
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存点表", default_filename, "Excel Files (*.xlsx)"
        )
        if file_path:
            try:
                self.config_service.export_to_excel(file_path)
                QMessageBox.information(self, "成功", f"点表已成功导出至 {file_path}")
            except ValueError as ve: # 专门捕获来自服务的无数据错误
                logger.warning(f"导出点表失败 (ValueError): {ve}")
                QMessageBox.warning(self, "导出失败", str(ve))
            except Exception as e:
                logger.error(f"导出点表时发生未知错误: {e}", exc_info=True)
                QMessageBox.critical(self, "导出失败", f"导出点表时发生未知错误: {str(e)}") 