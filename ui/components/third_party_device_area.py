"""第三方设备区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QPushButton, QMessageBox, QFileDialog, QDialog, QAbstractItemView, QSizePolicy)
from datetime import datetime
import logging
from PySide6.QtCore import Qt
from typing import Optional
from PySide6.QtGui import QColor, QBrush, QFont

from core.third_party_config_area import ConfigService, TemplateService
from ui.dialogs.device_point_dialog import DevicePointDialog

logger = logging.getLogger(__name__)

class ThirdPartyDeviceArea(QGroupBox):
    """已配置的第三方设备区域"""
    def __init__(self, 
                 config_service: ConfigService, 
                 template_service: TemplateService, 
                 parent=None):
        super().__init__("已配置的第三方设备", parent)
        
        # 服务和数据成员
        self.config_service = config_service
        self.template_service = template_service
        self.current_site_name: Optional[str] = None
        self.template_colors = {}  # 存储每个模板的颜色

        # 初始化UI和事件
        self.setup_ui()
        self.setup_connections()
        self.update_third_party_table()  # 初始加载数据
    
    #---------------------------------
    # UI初始化与布局
    #---------------------------------
    
    def setup_ui(self):
        """设置第三方设备区域UI"""
        # 主布局
        layout = QVBoxLayout(self)
        
        # 设置表格
        self.setup_table()
        layout.addWidget(self.third_party_table, 1)  # 比例因子为1，使表格尽可能占据可用空间
        
        # 设置按钮区域
        button_layout = self.setup_buttons()
        layout.addLayout(button_layout, 0)  # 比例因子为0，按钮区域占用固定空间
        
        self.setLayout(layout)
    
    def setup_table(self):
        """设置表格控件"""
        self.third_party_table = QTableWidget()
        self.third_party_table.setColumnCount(8)  # 增加一列用于显示描述
        self.third_party_table.setHorizontalHeaderLabels([
            "设备模板", "变量名", "描述", "数据类型", 
            "SLL设定值", "SL设定值", "SH设定值", "SHH设定值"
        ])
        self.third_party_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.third_party_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        # 设置表格列宽和格式
        self.setup_table_column_widths()
    
    def setup_buttons(self):
        """设置按钮区域"""
        button_layout = QVBoxLayout()
        
        self.third_party_btn = QPushButton("第三方设备点表配置")
        self.delete_selected_config_btn = QPushButton("删除选中模板所有点位")
        self.clear_config_btn = QPushButton("清空所有配置")
        
        button_layout.addWidget(self.third_party_btn)
        button_layout.addWidget(self.delete_selected_config_btn)
        button_layout.addWidget(self.clear_config_btn)
        
        return button_layout
    
    def setup_table_column_widths(self):
        """设置表格各列的宽度"""
        # 禁用表格自动拉伸，手动控制列宽
        self.third_party_table.horizontalHeader().setStretchLastSection(False)
        
        # 设置垂直表头（序号列）
        self.third_party_table.verticalHeader().setFixedWidth(50)
        self.third_party_table.verticalHeader().setDefaultSectionSize(30)  # 行高
        
        # 设置各列宽度
        col_widths = {
            0: 140,  # 设备模板列
            1: 240,  # 变量名列
            2: 300,  # 描述列 - 新增
            3: 100,  # 数据类型列
            4: 100,  # SLL设定值列
            5: 100,  # SL设定值列
            6: 100,  # SH设定值列
            7: 100   # SHH设定值列
        }
        
        # 应用列宽设置
        header = self.third_party_table.horizontalHeader()
        for col, width in col_widths.items():
            self.third_party_table.setColumnWidth(col, width)
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
    
    def setup_connections(self):
        """设置信号连接"""
        self.third_party_btn.clicked.connect(self.configure_third_party_device)
        self.delete_selected_config_btn.clicked.connect(self.delete_selected_device_config)
        self.clear_config_btn.clicked.connect(self.clear_device_config)
    
    #---------------------------------
    # 数据处理与表格更新
    #---------------------------------
    
    def update_third_party_table(self):
        """更新第三方设备列表"""
        try:
            self.third_party_table.setRowCount(0)
            device_stats = self.config_service.get_configuration_summary()
            
            # 生成模板颜色
            self.generate_template_colors(device_stats)
            
            # 按模板分组显示数据
            self.display_device_data_by_template(device_stats)
            
        except Exception as e:
            logger.error(f"更新第三方设备列表时发生错误: {e}", exc_info=True)
    
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
    
    def display_device_data_by_template(self, device_stats):
        """按模板分组显示设备数据"""
        for device_index, device_summary in enumerate(device_stats):
            # 获取模板名称和自定义变量
            template_name = device_summary['template']
            variable_prefix = device_summary.get('variable_prefix', '')  # 变量占位符
            description_prefix_text = device_summary.get('description_prefix', '')  # 描述占位符
            
            # 获取该配置的所有点位
            configured_points = self.config_service.get_configured_points_by_template_and_prefix(
                template_name, variable_prefix, description_prefix_text)
            
            # 添加模板分组标题行
            self.add_template_group_header(template_name, variable_prefix, description_prefix_text, configured_points)
            
            # 添加点位数据行
            if not configured_points:
                self.add_empty_point_row(template_name, variable_prefix, description_prefix_text)
            else:
                self.add_point_rows(template_name, variable_prefix, description_prefix_text, configured_points)
            
            # 添加分组分隔符
            if device_index < len(device_stats) - 1:
                self.add_group_separator()
    
    def add_template_group_header(self, template_name, variable_prefix, description_prefix_text, configured_points):
        """添加模板组标题行"""
        group_row = self.third_party_table.rowCount()
        self.third_party_table.insertRow(group_row)
        
        # 创建模板组标题项
        group_item = QTableWidgetItem(f"▼ 模板: {template_name}")
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
        self.third_party_table.setSpan(group_row, 0, 1, 8)  # 合并整行（8列）
        
        # 保存用户数据用于删除操作
        group_item.setData(Qt.ItemDataRole.UserRole, {
            'variable_prefix': variable_prefix,
            'description_prefix': description_prefix_text,
            'is_group_header': True,  # 标记为组标题
            'template_name': template_name,
            'points_count': len(configured_points) if configured_points else 0
        })
    
    def add_empty_point_row(self, template_name, variable_prefix, description_prefix_text):
        """添加空点位行（当模板没有配置点位时）"""
        row = self.third_party_table.rowCount()
        self.third_party_table.insertRow(row)
        
        # 获取模板颜色
        template_color = self.template_colors.get(template_name, QColor(240, 240, 240))
        
        # 创建空行项
        empty_item = QTableWidgetItem("(无点位)")
        empty_item.setBackground(QBrush(template_color))
        self.third_party_table.setItem(row, 0, empty_item)
        
        # 添加空的描述、数据类型和设定值列
        for col in range(1, 8):  # 扩展到8列
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
    
    def add_point_rows(self, template_name, variable_prefix, description_prefix_text, configured_points):
        """添加点位数据行"""
        template_color = self.template_colors.get(template_name, QColor(240, 240, 240))
        
        for point in configured_points:
            var_suffix = point.get('var_suffix', '')
            desc_suffix = point.get('desc_suffix', '')  # 获取描述后缀
            
            # 使用服务返回的完整变量名（来自模型的计算属性）
            full_var_name = point.get('full_variable_name', '')
            if not full_var_name:
                # 如果服务没有返回，则使用本地生成逻辑作为备用
                full_var_name = self.generate_full_variable_name(variable_prefix, var_suffix)
            
            # 优先使用服务返回的完整描述，如果没有则生成
            full_description = point.get('full_description', '')
            if not full_description:
                full_description = self.generate_full_description(description_prefix_text, desc_suffix)
            
            # 添加一行到表格
            row = self.third_party_table.rowCount()
            self.third_party_table.insertRow(row)
            
            # 创建点位项并设置背景色
            items = [
                QTableWidgetItem(template_name),
                QTableWidgetItem(full_var_name),
                QTableWidgetItem(full_description),  # 显示完整描述
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
                'template_name': template_name,
                'full_description': full_description  # 保存完整描述，便于后续使用
            })
    
    def generate_full_description(self, description_prefix, description_suffix):
        """根据描述占位符和后缀生成完整的描述文本"""
        # 使用与变量名相同的占位符逻辑处理描述
        if description_prefix and '*' in description_prefix:
            prefix_parts = description_prefix.split('*')
            if len(prefix_parts) >= 2:
                if description_suffix:
                    return f"{prefix_parts[0]}{description_suffix}{prefix_parts[1]}"
                else:
                    return f"{prefix_parts[0]}{prefix_parts[1]}"
            else:
                if description_suffix:
                    return f"{prefix_parts[0]}{description_suffix}"
                else:
                    return prefix_parts[0]
        else:
            # 直接拼接（没有占位符的情况）
            return f"{description_prefix}{description_suffix}" if description_prefix else description_suffix
    
    def generate_full_variable_name(self, variable_prefix, var_suffix):
        """根据变量占位符和后缀生成完整的变量名"""
        # 处理带*的格式，生成完整变量名（*作为占位符，可以在变量的任何位置）
        if '*' in variable_prefix:
            prefix_parts = variable_prefix.split('*')
            if len(prefix_parts) >= 2:
                if var_suffix:
                    return f"{prefix_parts[0]}{var_suffix}{prefix_parts[1]}"
                else:
                    return f"{prefix_parts[0]}{prefix_parts[1]}"
            else:
                if var_suffix:
                    return f"{prefix_parts[0]}{var_suffix}"
                else:
                    return prefix_parts[0]
        else:
            # 直接拼接，不做任何额外处理
            return f"{variable_prefix}{var_suffix}"
    
    def add_group_separator(self):
        """添加组间分隔符"""
        separator_row = self.third_party_table.rowCount()
        self.third_party_table.insertRow(separator_row)
        separator_item = QTableWidgetItem("")
        separator_item.setFlags(Qt.ItemFlag.NoItemFlags)  # 禁用此行
        self.third_party_table.setItem(separator_row, 0, separator_item)
        self.third_party_table.setSpan(separator_row, 0, 1, 8)  # 合并整行（8列）
    
    #---------------------------------
    # 用户交互与操作处理
    #---------------------------------
    
    def configure_third_party_device(self):
        """配置第三方设备点表"""
        try:
            dialog = DevicePointDialog(
                template_service=self.template_service,
                config_service=self.config_service,
                parent=self
            )
            if dialog.exec() == QDialog.Accepted:
                self.update_third_party_table()
                QMessageBox.information(self, "成功", "设备点表配置已更新。")
        except Exception as e:
            logger.error(f"打开或处理设备点表配置对话框时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"配置设备点表时发生错误: {str(e)}")
    
    def delete_selected_device_config(self):
        """删除表格中当前选中的第三方设备配置"""
        # 获取选中行
        selected_rows = self.third_party_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.information(self, "提示", "请先在列表中选择要删除的设备配置。")
            return
        
        # 获取选中项的模板信息
        template_info = self.get_selected_template_info(selected_rows[0].row())
        if not template_info:
            return
        
        # 确认删除
        if self.confirm_template_deletion(template_info):
            self.perform_template_deletion(template_info)
    
    def get_selected_template_info(self, row_index):
        """从选中行获取模板信息"""
        first_item = self.third_party_table.item(row_index, 0)
        if not first_item:
            QMessageBox.warning(self, "错误", "无法获取选中配置的详细信息。")
            return None
            
        # 获取用户数据
        user_data = None
        # 先检查第一列
        if first_item and first_item.data(Qt.ItemDataRole.UserRole):
            user_data = first_item.data(Qt.ItemDataRole.UserRole)
        # 如果第一列没有数据，检查第二列
        elif self.third_party_table.item(row_index, 1) and self.third_party_table.item(row_index, 1).data(Qt.ItemDataRole.UserRole):
            user_data = self.third_party_table.item(row_index, 1).data(Qt.ItemDataRole.UserRole)
            
        if not isinstance(user_data, dict):
            QMessageBox.warning(self, "错误", "无法获取配置信息，请重新选择。")
            return None
            
        # 提取模板信息
        template_info = {
            'template_name': user_data.get('template_name', ''),
            'variable_prefix': user_data.get('variable_prefix', ''),
            'description_prefix': user_data.get('description_prefix', ''),
            'points_count': user_data.get('points_count', 0),
            'is_group_header': user_data.get('is_group_header', False)
        }
        
        # 如果模板名称为空但第一项有文本，使用第一项文本
        if not template_info['template_name'] and first_item:
            template_info['template_name'] = first_item.text()
            
        return template_info
    
    def confirm_template_deletion(self, template_info):
        """确认是否删除模板配置"""
        # 构建确认信息，强调将删除整个模板组
        confirm_message = (
            f"您选择了模板 '{template_info['template_name']}'\n\n"
            f"此操作将删除该模板下的所有点位配置"
        )
        
        if template_info['points_count'] > 0:
            confirm_message += f"，共计 {template_info['points_count']} 个点位"
        
        confirm_message += "。\n\n确定要删除此模板的所有配置吗？此操作不可恢复。"
        
        reply = QMessageBox.question(
            self, "确认删除整个模板配置",
            confirm_message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        return reply == QMessageBox.StandardButton.Yes
    
    def perform_template_deletion(self, template_info):
        """执行模板配置删除操作"""
        try:
            success = self.config_service.delete_device_configuration(
                template_info['template_name'], 
                template_info['variable_prefix'], 
                template_info['description_prefix']
            )
            
            if success:
                self.update_third_party_table()
                QMessageBox.information(
                    self, "删除成功", 
                    f"设备配置模板 '{template_info['template_name']}' 已成功删除。"
                )
            else:
                QMessageBox.warning(
                    self, "删除失败", 
                    f"未能删除设备配置模板。它可能已被删除或操作失败。"
                )
        except Exception as e:
            logger.error(
                f"删除设备配置模板 '{template_info['template_name']}' (使用自定义变量) 时发生错误: {e}", 
                exc_info=True
            )
            QMessageBox.critical(self, "删除错误", f"删除设备配置时发生错误: {str(e)}")
    
    def clear_device_config(self):
        """清空所有设备配置"""
        if not self.config_service or not self.config_service.get_all_configured_points():
            QMessageBox.information(self, "提示", "没有已配置的设备点表可以清空。")
            return
        
        # 确认清空
        if not self.confirm_clear_all_configs():
            return
            
        # 执行清空操作
        try:
            success = self.config_service.clear_all_configurations()
            if success:
                self.update_third_party_table()
                QMessageBox.information(self, "已清空", "已清空所有第三方设备配置。")
        except Exception as e:
            logger.error(f"清空所有设备配置时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "清空错误", f"清空所有配置失败: {str(e)}")
    
    def confirm_clear_all_configs(self):
        """确认是否清空所有配置"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有已配置的第三方设备点表吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return reply == QMessageBox.StandardButton.Yes
    
    #---------------------------------
    # 公共接口
    #---------------------------------
    
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