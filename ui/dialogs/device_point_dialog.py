"""设备点位配置对话框"""

import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QComboBox, QLineEdit, QTableWidget,
                               QTableWidgetItem, QPushButton, QHeaderView,
                               QSplitter, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from typing import Optional, List
from core.devices.template_manager import TemplateManager
from core.services.device_configuration_service import DeviceConfigurationService
from core.models.templates.models import DeviceTemplateModel, TemplatePointModel
from ui.dialogs.template_manage_dialog import TemplateManageDialog

logger = logging.getLogger(__name__)

class DevicePointDialog(QDialog):
    """设备点位配置对话框，使用 TemplateManager 和 DeviceConfigurationService"""

    def __init__(self,
                 template_manager: TemplateManager,  # Use standard names
                 config_service: DeviceConfigurationService,  # Use standard names
                 parent=None,
                 initial_template_name=""):
        super().__init__(parent)
        self.setWindowTitle("第三方设备点表配置")
        self.resize(900, 700)

        self.template_manager = template_manager # Assign passed instance
        self.config_service = config_service   # Assign passed instance
        
        self.current_template_id: Optional[int] = None
        self.template: Optional[DeviceTemplateModel] = None 
        self.initial_template_name_to_select = initial_template_name

        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)

        # 设备信息区域
        info_group = QGroupBox("第三方设备信息")
        info_layout = QFormLayout()

        # 模板选择
        self.template_combo = QComboBox()
        self.load_template_list()

        if self.initial_template_name_to_select:
            index = self.template_combo.findText(self.initial_template_name_to_select)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)
            else:
                logger.warning(f"初始模板 '{self.initial_template_name_to_select}' 在列表中未找到。")
                if self.template_combo.count() > 0:
                    self.template_combo.setCurrentIndex(0)
        elif self.template_combo.count() > 0:
             self.template_combo.setCurrentIndex(0)

        self.template_combo.currentIndexChanged.connect(self.template_selected)
        info_layout.addRow("设备模板:", self.template_combo)

        # 变量名输入
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("请输入设备/变量名前缀")
        self.prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("设备前缀:", self.prefix_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 拆分为上下两部分
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 配置区域 (上部分)
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        config_group = QGroupBox("模板点位详情 (源模板)")
        points_layout = QVBoxLayout()

        self.point_table = QTableWidget()
        self.point_table.setColumnCount(3)
        self.point_table.setHorizontalHeaderLabels([
            "变量名后缀", "描述后缀", "数据类型"
        ])

        # 设置表格列宽
        header = self.point_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        points_layout.addWidget(self.point_table)
        config_group.setLayout(points_layout)
        config_layout.addWidget(config_group)

        # 模板管理按钮
        template_btn_layout = QHBoxLayout()
        template_manage_btn = QPushButton("管理设备模板")
        template_manage_btn.clicked.connect(lambda: self.manage_templates(self.template_manager))
        template_btn_layout.addStretch()
        template_btn_layout.addWidget(template_manage_btn)
        config_layout.addLayout(template_btn_layout)
        splitter.addWidget(config_widget)

        # 预览区域 (下部分)
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_group = QGroupBox("生成的设备点表预览")
        preview_table_layout = QVBoxLayout()

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels([
            "完整变量名", "完整描述", "数据类型"
        ])

        # 设置表格列宽
        header = self.preview_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        preview_table_layout.addWidget(self.preview_table)
        preview_group.setLayout(preview_table_layout)
        preview_layout.addWidget(preview_group)

        splitter.addWidget(preview_widget)

        # 设置初始分割比例 (1:1)
        splitter.setSizes([self.height() // 2, self.height() // 2])
        layout.addWidget(splitter)

        # 按钮区域
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("应用并保存配置")
        self.save_btn.clicked.connect(self.save_config)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

        # 加载初始模板
        if self.template_combo.count() > 0:
            self.template_selected(0)
        elif self.template_combo.count() == 0:
            QMessageBox.information(self, "提示", "模板库为空，请先通过'管理设备模板'添加模板。")

    def load_template_list(self):
        """加载模板列表"""
        self.template_combo.clear()
        try:
            templates: List[DeviceTemplateModel] = self.template_manager.get_all_templates()
            if not templates:
                logger.info("模板库为空或加载失败")
            for tmpl_model in templates:
                self.template_combo.addItem(tmpl_model.name, tmpl_model.id)
        except Exception as e:
            logger.error(f"加载模板列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")

    def manage_templates(self, tm: TemplateManager):
        """打开模板管理对话框"""
        dialog = TemplateManageDialog(parent=self)
        if dialog.exec() == QDialog.Accepted:
            current_id_before_reload = self.template_combo.currentData()
            current_text_before_reload = self.template_combo.currentText()
            self.load_template_list()
            if current_id_before_reload is not None:
                index = self.template_combo.findData(current_id_before_reload)
                if index >= 0:
                    self.template_combo.setCurrentIndex(index)
                else: 
                    index_by_text = self.template_combo.findText(current_text_before_reload)
                    if index_by_text >=0:
                        self.template_combo.setCurrentIndex(index_by_text)
                    elif self.template_combo.count() > 0:
                        self.template_combo.setCurrentIndex(0)
            elif self.template_combo.count() > 0:
                 self.template_combo.setCurrentIndex(0)
            else: 
                self.template = None
                self.update_point_table()
                self.update_preview()

    def template_selected(self, index: int):
        """模板选择改变时的处理"""
        if index < 0 or self.template_combo.count() == 0:
            self.template = None
            if hasattr(self, 'prefix_input'): # Check if UI setup
                 self.prefix_input.clear()
            self.update_point_table()
            self.update_preview()
            return

        self.current_template_id = self.template_combo.itemData(index)
        if self.current_template_id is None:
            logger.warning("选中的模板没有关联的ID (itemData is None)")
            self.template = None
            self.update_point_table()
            self.update_preview()
            return

        try:
            self.template = self.template_manager.get_template_by_id(self.current_template_id)
        except Exception as e:
            logger.error(f"获取模板详情失败 (ID: {self.current_template_id}): {e}")
            QMessageBox.critical(self, "错误", f"加载模板详情失败: {str(e)}")
            self.template = None

        if self.template:
            self.prefix_input.setText(self.template.prefix or "")
        elif hasattr(self, 'prefix_input'):
            self.prefix_input.clear()
            logger.warning(f"未能加载ID为 {self.current_template_id} 的模板详情。")
        
        self.update_point_table()
        self.update_preview()

    def update_point_table(self):
        """更新点位表格"""
        self.point_table.setRowCount(0)
        if self.template and self.template.points:
            for point_model in self.template.points:
                row = self.point_table.rowCount()
                self.point_table.insertRow(row)
                self.point_table.setItem(row, 0, QTableWidgetItem(point_model.var_suffix))
                self.point_table.setItem(row, 1, QTableWidgetItem(point_model.desc_suffix))
                self.point_table.setItem(row, 2, QTableWidgetItem(point_model.data_type))

    def update_preview(self):
        """更新预览表格"""
        self.preview_table.setRowCount(0)

        device_prefix = ""
        if hasattr(self, 'prefix_input'):
            device_prefix = self.prefix_input.text().strip()

        if not self.template or not self.template.points:
            return

        for point_model in self.template.points:
            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            
            full_var_name = f"{device_prefix}_{point_model.var_suffix}" if device_prefix else point_model.var_suffix
            # Generate description based on prefix and suffix
            full_desc = f"{device_prefix} {point_model.desc_suffix}" if device_prefix and point_model.desc_suffix else (device_prefix or point_model.desc_suffix or "")

            self.preview_table.setItem(row, 0, QTableWidgetItem(full_var_name))
            self.preview_table.setItem(row, 1, QTableWidgetItem(full_desc))
            self.preview_table.setItem(row, 2, QTableWidgetItem(point_model.data_type))

    def save_config(self):
        """保存配置"""
        device_prefix = self.prefix_input.text().strip()
        if not device_prefix:
            QMessageBox.warning(self, "警告", "请输入设备前缀。")
            self.prefix_input.setFocus()
            return

        if not self.template:
            QMessageBox.warning(self, "警告", "未选择有效的设备模板。")
            return
        
        if not self.template.points:
             reply = QMessageBox.question(self, "确认操作",
                                       f"模板 '{self.template.name}' 不包含任何点位。\n是否仍要以此空模板和前缀 '{device_prefix}' 应用配置？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
             if reply == QMessageBox.StandardButton.No:
                 return
        try:
            logger.info(f"准备保存配置: 设备前缀='{device_prefix}', 模板='{self.template.name}'")
            newly_added_points = self.config_service.add_configured_points(self.template, device_prefix)
            
            if newly_added_points:
                QMessageBox.information(self, "成功",
                                        f"已成功为设备前缀 '{device_prefix}' 应用模板 '{self.template.name}'，添加了 {len(newly_added_points)} 个点位。")
                self.accept()
            elif not self.template.points: 
                QMessageBox.information(self, "提示",
                                        f"已为设备前缀 '{device_prefix}' 应用空模板 '{self.template.name}'。未添加实际点位。")
                self.accept()
            else:
                QMessageBox.warning(self, "注意", "配置已应用，但服务层未明确报告新点位已添加（可能服务层逻辑如此）。")
                self.accept() 

        except Exception as e:
            logger.error(f"保存设备点表配置失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存配置时发生错误: {str(e)}")
