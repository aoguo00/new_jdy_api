"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog, QAbstractItemView)
from datetime import datetime
import logging
from PySide6.QtCore import Qt
from typing import Optional # 确保导入 Optional

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
        self.current_site_name: Optional[str] = None # 新增：存储当前场站名称

        self.setup_ui()
        self.setup_connections()
        self.update_third_party_table() # 初始加载数据
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout(self)
        
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(4)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "设备前缀", "点位数量", "状态"]
        )
        self.third_party_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # 允许行选择
        self.third_party_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # 设置为单选模式

        header = self.third_party_table.horizontalHeader()
        for i in range(4):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.third_party_table)

        button_layout = QVBoxLayout()
        self.third_party_btn = QPushButton("第三方设备点表配置")
        self.delete_selected_config_btn = QPushButton("删除选中配置") # 新增按钮
        self.clear_config_btn = QPushButton("清空所有配置") # 修改文本以示区分

        button_layout.addWidget(self.third_party_btn)
        button_layout.addWidget(self.delete_selected_config_btn) # 添加到布局
        button_layout.addWidget(self.clear_config_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        self.third_party_btn.clicked.connect(self.configure_third_party_device)
        self.delete_selected_config_btn.clicked.connect(self.delete_selected_device_config) # 连接新按钮的信号
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
                
                # 获取原始前缀
                variable_prefix = device_summary.get('variable_prefix', '')
                description_prefix_text = device_summary.get('description_prefix', '') 
                
                # 直接显示变量前缀，不添加示例后缀
                display_variable_name = variable_prefix
                # 特殊处理带*的格式
                if '*' in variable_prefix:
                    prefix_parts = variable_prefix.split('*')
                    if len(prefix_parts) >= 2:
                        # 当有前后两部分时，显示为：前缀+后缀，不再添加[*]标记
                        display_variable_name = f"{prefix_parts[0]}{prefix_parts[1]}"
                    else:
                        # 当只有前半部分时(如a*)，直接显示前缀部分
                        display_variable_name = prefix_parts[0]
                
                # 在表格中显示处理后的变量名
                item_var_prefix = QTableWidgetItem(display_variable_name)
                # 保存原始前缀和描述前缀作为用户数据，用于删除操作
                item_var_prefix.setData(Qt.ItemDataRole.UserRole, {
                    'variable_prefix': variable_prefix,
                    'description_prefix': description_prefix_text
                }) 
                
                self.third_party_table.setItem(row, 1, item_var_prefix)
                self.third_party_table.setItem(row, 2, QTableWidgetItem(str(device_summary['count'])))
                self.third_party_table.setItem(row, 3, QTableWidgetItem(device_summary['status']))
        except Exception as e:
            logger.error(f"更新第三方设备列表时发生错误: {e}", exc_info=True)
            # 可选择通知用户，尽管这通常是后台更新
            # QMessageBox.warning(self, "更新错误", "无法刷新第三方设备列表。") 

    def delete_selected_device_config(self):
        """删除表格中当前选中的第三方设备配置。"""
        selected_rows = self.third_party_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的设备配置。")
            return

        current_row = selected_rows[0].row()
        template_name_item = self.third_party_table.item(current_row, 0)
        variable_prefix_item = self.third_party_table.item(current_row, 1) # 第二列现在是显示名

        if not template_name_item or not variable_prefix_item:
            QMessageBox.warning(self, "错误", "无法获取选中配置的详细信息。")
            return

        template_name = template_name_item.text()
        # 从用户数据中获取原始的变量前缀和描述前缀
        user_data = variable_prefix_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(user_data, dict):
            variable_prefix = user_data.get('variable_prefix', '')
            description_prefix = user_data.get('description_prefix', '')
        else:
            # 兼容旧数据格式
            variable_prefix = variable_prefix_item.text()
            description_prefix = user_data if user_data else ""
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板为 '{template_name}' (变量前缀: '{variable_prefix}', 描述前缀: '{description_prefix}') 的配置吗？\n此操作将删除其所有相关点位，且不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.config_service.delete_device_configuration(template_name, variable_prefix, description_prefix)
                if success:
                    self.update_third_party_table()
                    QMessageBox.information(self, "删除成功", f"设备配置 '{template_name}' (变量前缀: '{variable_prefix}', 描述前缀: '{description_prefix}') 已成功删除。")
                else:
                    QMessageBox.warning(self, "删除失败", f"未能删除设备配置 '{template_name}' (变量前缀: '{variable_prefix}', 描述前缀: '{description_prefix}')。它可能已被删除或操作失败。")
            except Exception as e:
                logger.error(f"删除选中设备配置 (模板: {template_name}, 变量前缀: {variable_prefix}, 描述前缀: {description_prefix}) 时发生错误: {e}", exc_info=True)
                QMessageBox.critical(self, "删除错误", f"删除设备配置时发生错误: {str(e)}")

    def clear_device_config(self):
        """清空所有设备配置"""
        if not self.config_service or not self.config_service.get_all_configured_points():
            QMessageBox.information(self, "提示", "没有已配置的设备点表可以清空。")
            return

        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的第三方设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.config_service.clear_all_configurations()
                if success:
                    self.update_third_party_table()
                    QMessageBox.information(self, "已清空", "已清空所有第三方设备配置。")
                # else分支可以省略，因为如果clear_all_configurations返回False，通常表示没有东西可清除或操作本身不抛错但无效
            except Exception as e:
                logger.error(f"清空所有设备配置时发生错误: {e}", exc_info=True)
                QMessageBox.critical(self, "清空错误", f"清空所有配置失败: {str(e)}")

    # def export_points_table(self):
    #     \"\"\"导出点表\"\"\"
    #     # 使用新服务检查是否有数据可导出
    #     if not self.config_service or not self.config_service.get_all_configured_points():
    #         QMessageBox.warning(self, \"警告\", \"没有可导出的第三方设备点位数据。\")
    #         return

    #     default_filename = f\"第三方设备点表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx\"
    #     # 确保parent是self以便QFileDialog正确居中
    #     file_path, _ = QFileDialog.getSaveFileName(
    #         self, \"保存点表\", default_filename, \"Excel Files (*.xlsx)\"
    #     )
    #     if file_path:
    #         try:
    #             # self.config_service.export_to_excel(file_path) # 旧的调用
    #             # 这里不应该再调用旧的 config_service.export_to_excel
    #             # 统一导出已移至 MainWindow 的 _handle_generate_points
    #             # 如果确实需要从这里触发一个仅第三方设备的导出（不推荐，因为与统一导出冲突），
    #             # 那就需要重新思考如何调用 IOExcelExporter，并且 MainWindow 需要提供方法或信号。
    #             # 目前，我们假设这个按钮的功能已被主窗口的统一导出按钮完全覆盖。
    #             QMessageBox.information(self, \"提示\", \"此独立导出功能已由主窗口的统一导出替代。\")
    #             # logger.info(f\"旧的第三方点表导出按钮被点击，但功能已迁移。{file_path}\") # 示例日志

    #         except ValueError as ve: # 专门捕获来自服务的无数据错误
    #             logger.warning(f\"导出点表失败 (ValueError): {ve}\")
    #             QMessageBox.warning(self, \"导出失败\", str(ve))
    #         except Exception as e:
    #             logger.error(f\"导出点表时发生未知错误: {e}\", exc_info=True)
    #             QMessageBox.critical(self, \"导出失败\", f\"导出点表时发生未知错误: {str(e)}\") 

    def set_current_site_name(self, site_name: str):
        """
        设置当前选中的场站名称。
        Args:
            site_name (str): 选中的场站名称。
        """
        self.current_site_name = site_name
        logger.info(f"ThirdPartyDeviceArea: 当前场站已更新为 '{site_name}'")
        # 可选：如果 update_third_party_table 需要基于 site_name 刷新，
        # 可以在这里调用 self.update_third_party_table()。
        # 目前假设 update_third_party_table 显示的是全局配置。 