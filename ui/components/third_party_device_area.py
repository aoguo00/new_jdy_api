"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog, QAbstractItemView, QSizePolicy)
from datetime import datetime
import logging
from PySide6.QtCore import Qt
from typing import Optional # 确保导入 Optional
from PySide6.QtGui import QColor, QBrush, QFont

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
        self.template_colors = {} # 存储每个模板的颜色

        self.setup_ui()
        self.setup_connections()
        self.update_third_party_table() # 初始加载数据
        
    def setup_ui(self):
        """设置第三方设备区域UI"""
        layout = QVBoxLayout(self)
        
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(7)
        self.third_party_table.setHorizontalHeaderLabels(
            ["设备模板", "变量名", "数据类型", "SLL设定值", "SL设定值", "SH设定值", "SHH设定值"]
        )
        self.third_party_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # 允许行选择
        self.third_party_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection) # 设置为单选模式

        # 设置表格占满可用空间，并配置列宽比例
        self.setup_table_column_widths()
        
        # 添加表格到布局，并设置为占据大部分空间
        layout.addWidget(self.third_party_table, 1)  # 比例因子为1，使表格尽可能占据可用空间

        button_layout = QVBoxLayout()
        self.third_party_btn = QPushButton("第三方设备点表配置")
        self.delete_selected_config_btn = QPushButton("删除选中模板所有点位") # 修改按钮文本更明确
        self.clear_config_btn = QPushButton("清空所有配置") # 修改文本以示区分

        button_layout.addWidget(self.third_party_btn)
        button_layout.addWidget(self.delete_selected_config_btn) # 添加到布局
        button_layout.addWidget(self.clear_config_btn)

        layout.addLayout(button_layout, 0)  # 比例因子为0，按钮区域占用固定空间
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
            
            # 生成模板颜色
            self.generate_template_colors(device_stats)
            
            # 按模板分组显示
            for device_index, device_summary in enumerate(device_stats):
                # 获取原始前缀和模板名称
                template_name = device_summary['template']
                variable_prefix = device_summary.get('variable_prefix', '')
                description_prefix_text = device_summary.get('description_prefix', '')
                
                # 获取该配置的所有点位
                configured_points = self.config_service.get_configured_points_by_template_and_prefix(
                    template_name, variable_prefix, description_prefix_text)
                
                # 添加模板分组标题行
                group_row = self.third_party_table.rowCount()
                self.third_party_table.insertRow(group_row)
                
                # 创建模板组标题项
                group_item = QTableWidgetItem(f"▼ 模板: {template_name} (前缀: {variable_prefix})")
                group_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                
                # 设置标题行字体和背景
                font = QFont()
                font.setBold(True)
                group_item.setFont(font)
                
                # 获取模板颜色
                template_color = self.template_colors.get(template_name, QColor(240, 240, 240))
                group_item.setBackground(QBrush(template_color.darker(120)))
                
                # 设置跨列显示
                self.third_party_table.setItem(group_row, 0, group_item)
                self.third_party_table.setSpan(group_row, 0, 1, 7)  # 合并整行
                
                # 保存用户数据用于删除操作
                group_item.setData(Qt.ItemDataRole.UserRole, {
                    'variable_prefix': variable_prefix,
                    'description_prefix': description_prefix_text,
                    'is_group_header': True,  # 标记为组标题
                    'template_name': template_name,
                    'points_count': len(configured_points) if configured_points else 0
                })
                
                # 如果没有配置点位，显示一个空行
                if not configured_points:
                    row = self.third_party_table.rowCount()
                    self.third_party_table.insertRow(row)
                    self.third_party_table.setItem(row, 0, QTableWidgetItem("(无点位)"))
                    empty_item = self.third_party_table.item(row, 0)
                    empty_item.setBackground(QBrush(template_color))
                    
                    # 添加空的数据类型和设定值列
                    for col in range(1, 7):
                        item = QTableWidgetItem("")
                        item.setBackground(QBrush(template_color))
                        self.third_party_table.setItem(row, col, item)
                    
                    # 保存用户数据用于删除操作
                    empty_item.setData(Qt.ItemDataRole.UserRole, {
                        'variable_prefix': variable_prefix,
                        'description_prefix': description_prefix_text,
                        'template_name': template_name,
                        'is_empty': True
                    })
                else:
                    # 为每个点位创建一行
                    for point in configured_points:
                        var_suffix = point.get('var_suffix', '')
                        
                        # 处理带*的格式，生成完整变量名
                        if '*' in variable_prefix:
                            prefix_parts = variable_prefix.split('*')
                            if len(prefix_parts) >= 2:
                                if var_suffix:
                                    full_var_name = f"{prefix_parts[0]}{var_suffix}{prefix_parts[1]}"
                                else:
                                    full_var_name = f"{prefix_parts[0]}{prefix_parts[1]}"
                            else:
                                if var_suffix:
                                    full_var_name = f"{prefix_parts[0]}{var_suffix}"
                                else:
                                    full_var_name = prefix_parts[0]
                        else:
                            # 直接拼接
                            full_var_name = f"{variable_prefix}{var_suffix}"
                        
                        # 添加一行到表格
                        row = self.third_party_table.rowCount()
                        self.third_party_table.insertRow(row)
                        
                        # 创建项并设置背景色
                        items = [
                            QTableWidgetItem(template_name),
                            QTableWidgetItem(full_var_name),
                            QTableWidgetItem(point.get('data_type', '')),
                            QTableWidgetItem(point.get('sll_setpoint', '')),
                            QTableWidgetItem(point.get('sl_setpoint', '')),
                            QTableWidgetItem(point.get('sh_setpoint', '')),
                            QTableWidgetItem(point.get('shh_setpoint', ''))
                        ]
                        
                        # 设置相同背景色以分组
                        for col, item in enumerate(items):
                            item.setBackground(QBrush(template_color))
                            self.third_party_table.setItem(row, col, item)
                        
                        # 保存用户数据用于删除操作
                        items[1].setData(Qt.ItemDataRole.UserRole, {
                            'variable_prefix': variable_prefix,
                            'description_prefix': description_prefix_text,
                            'template_name': template_name
                        })
                
                # 添加一个空行作为组间分隔符（如果不是最后一个组）
                if device_index < len(device_stats) - 1:
                    separator_row = self.third_party_table.rowCount()
                    self.third_party_table.insertRow(separator_row)
                    separator_item = QTableWidgetItem("")
                    separator_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 禁用此行
                    self.third_party_table.setItem(separator_row, 0, separator_item)
                    self.third_party_table.setSpan(separator_row, 0, 1, 7)  # 合并整行
        except Exception as e:
            logger.error(f"更新第三方设备列表时发生错误: {e}", exc_info=True)
            # 可选择通知用户，尽管这通常是后台更新
            # QMessageBox.warning(self, "更新错误", "无法刷新第三方设备列表。") 

    def generate_template_colors(self, device_stats):
        """为每个模板生成一个唯一的背景色"""
        base_colors = [
            QColor(230, 240, 250),  # 浅蓝
            QColor(240, 250, 230),  # 浅绿
            QColor(250, 240, 230),  # 浅橙
            QColor(250, 230, 240),  # 浅粉
            QColor(230, 250, 250),  # 浅青
            QColor(250, 250, 230),  # 浅黄
            QColor(240, 230, 250),  # 浅紫
            QColor(245, 245, 245)   # 浅灰
        ]
        
        # 重置颜色映射
        self.template_colors = {}
        
        # 为每个模板分配颜色
        for i, device_summary in enumerate(device_stats):
            template_name = device_summary['template']
            if template_name not in self.template_colors:
                color_index = i % len(base_colors)
                self.template_colors[template_name] = base_colors[color_index]

    def delete_selected_device_config(self):
        """删除表格中当前选中的第三方设备配置。"""
        selected_rows = self.third_party_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的设备配置。")
            return

        current_row = selected_rows[0].row()
        first_item = self.third_party_table.item(current_row, 0)
        
        if not first_item:
            QMessageBox.warning(self, "错误", "无法获取选中配置的详细信息。")
            return
            
        # 获取用户数据
        user_data = None
        # 先检查第一列
        if first_item and first_item.data(Qt.ItemDataRole.UserRole):
            user_data = first_item.data(Qt.ItemDataRole.UserRole)
        # 如果第一列没有数据，检查第二列
        elif self.third_party_table.item(current_row, 1) and self.third_party_table.item(current_row, 1).data(Qt.ItemDataRole.UserRole):
            user_data = self.third_party_table.item(current_row, 1).data(Qt.ItemDataRole.UserRole)
            
        if not isinstance(user_data, dict):
            QMessageBox.warning(self, "错误", "无法获取配置信息，请重新选择。")
            return
            
        # 获取模板信息
        template_name = user_data.get('template_name', '')
        variable_prefix = user_data.get('variable_prefix', '')
        description_prefix = user_data.get('description_prefix', '')
        points_count = user_data.get('points_count', 0)
        is_group_header = user_data.get('is_group_header', False)
        
        # 如果是分组标题行，直接使用组信息
        if not template_name and first_item:
            template_name = first_item.text()
            
        # 构建确认信息，强调将删除整个模板组
        confirm_message = (
            f"您选择了模板 '{template_name}' (变量前缀: '{variable_prefix}')\n\n"
            f"此操作将删除该模板下的所有点位配置"
        )
        
        if points_count > 0:
            confirm_message += f"，共计 {points_count} 个点位"
        
        confirm_message += "。\n\n确定要删除此模板的所有配置吗？此操作不可恢复。"
        
        reply = QMessageBox.question(
            self, "确认删除整个模板配置",
            confirm_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                success = self.config_service.delete_device_configuration(template_name, variable_prefix, description_prefix)
                if success:
                    self.update_third_party_table()
                    QMessageBox.information(self, "删除成功", f"设备配置组 '{template_name}' (变量前缀: '{variable_prefix}') 已成功删除。")
                else:
                    QMessageBox.warning(self, "删除失败", f"未能删除设备配置组。它可能已被删除或操作失败。")
            except Exception as e:
                logger.error(f"删除设备配置组 (模板: {template_name}, 变量前缀: {variable_prefix}) 时发生错误: {e}", exc_info=True)
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

    def setup_table_column_widths(self):
        """
        设置表格各列的宽度比例
        使用固定比例而非拉伸模式，确保比例正确显示
        """
        # 禁用表格自动拉伸，以便我们手动控制列宽
        self.third_party_table.horizontalHeader().setStretchLastSection(False)
        
        # 设置垂直表头（序号列）的宽度
        self.third_party_table.verticalHeader().setFixedWidth(50)  # 增加序号列宽度
        self.third_party_table.verticalHeader().setDefaultSectionSize(30)  # 行高
        
        # 列宽比例设置 - 使用具体像素值而非比例
        col_widths = {
            0: 300,  # 设备模板列 - 较宽
            1: 350,  # 变量名列 - 较宽
            2: 130,  # 数据类型列 - 中等宽度
            3: 100,   # SLL设定值列 - 较窄
            4: 100,   # SL设定值列 - 较窄
            5: 100,   # SH设定值列 - 较窄
            6: 100    # SHH设定值列 - 较窄
        }
        
        # 设置各列宽度为固定值
        header = self.third_party_table.horizontalHeader()
        for col, width in col_widths.items():
            self.third_party_table.setColumnWidth(col, width)
            # 设置为固定宽度模式，防止自动调整
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            
        # 表头对齐方式
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 启用水平滚动条
        self.third_party_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # 确保表格能随窗口大小变化而调整
        self.third_party_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        ) 