"""设备点位配置对话框"""

import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QComboBox, QLineEdit, QTableWidget,
                               QTableWidgetItem, QPushButton, QHeaderView,
                               QSplitter, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from typing import Optional, List
from core.third_party_config_area import TemplateService, ConfigService
from core.third_party_config_area.models import DeviceTemplateModel, TemplatePointModel
from ui.dialogs.template_manage_dialog import TemplateManageDialog

logger = logging.getLogger(__name__)

class DevicePointDialog(QDialog):
    """设备点位配置对话框"""

    def __init__(self,
                 template_service: TemplateService,
                 config_service: ConfigService,
                 parent=None,
                 initial_template_name=""):
        super().__init__(parent)
        self.setWindowTitle("第三方设备点表配置")
        self.resize(900, 700)

        self.template_service = template_service
        self.config_service = config_service
        
        if not self.template_service or not self.config_service:
             logger.error("DevicePointDialog 初始化失败: 服务未提供。")
             QMessageBox.critical(self, "严重错误", "所需服务未能加载，对话框无法使用。")
             # Handle error
        
        self.current_template_id: Optional[int] = None
        self.template: Optional[DeviceTemplateModel] = None 
        self.initial_template_name_to_select = initial_template_name

        self.setup_ui()

    def _setup_table_widget(self, table_widget: QTableWidget, column_headers: List[str]):
        """辅助方法：设置QTableWidget的通用属性"""
        table_widget.setColumnCount(len(column_headers))
        table_widget.setHorizontalHeaderLabels(column_headers)
        header = table_widget.horizontalHeader()

        # 假设列的顺序，第二列 (索引1) 是描述列 (例如 "描述后缀" 或 "完整描述")
        # 我们希望描述列能拉伸以填充空间，其他列可交互并初始适应内容。
        if len(column_headers) > 1: # 确保至少有两列，索引1才有效
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch) # 描述列 (索引1) 拉伸

        for i in range(len(column_headers)):
            if i != 1: # 对于非描述列 (即非索引1的列)
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
        
        # 让所有被设置为 Interactive 的列先根据其内容调整初始宽度
        # Stretch 列会自动处理剩余空间，所以 resizeColumnsToContents() 对它的影响不大，
        # 但对 Interactive 列是有效的。
        table_widget.resizeColumnsToContents() 

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

        # 变量前缀输入框
        self.variable_prefix_input = QLineEdit()
        self.variable_prefix_input.setPlaceholderText("请输入变量名前缀 (例如 PT0101)，不需要请留空！")
        self.variable_prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("变量前缀:", self.variable_prefix_input)

        # 描述前缀输入框
        self.description_prefix_input = QLineEdit()
        self.description_prefix_input.setPlaceholderText("请输入描述前缀 (例如 温度传感器)，不需要请留空！")
        self.description_prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("描述前缀:", self.description_prefix_input)

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
        point_table_headers = [
            "变量名后缀", "描述后缀", "数据类型",
            "SLL设定值", "SL设定值", "SH设定值", "SHH设定值"
        ]
        self._setup_table_widget(self.point_table, point_table_headers)

        points_layout.addWidget(self.point_table)
        config_group.setLayout(points_layout)
        config_layout.addWidget(config_group)

        # 模板管理按钮
        template_btn_layout = QHBoxLayout()
        template_manage_btn = QPushButton("管理设备模板")
        template_manage_btn.clicked.connect(lambda: self.manage_templates(self.template_service))
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
        preview_table_headers = [
            "完整变量名", "完整描述", "数据类型",
            "SLL设定值", "SL设定值", "SH设定值", "SHH设定值"
        ]
        self._setup_table_widget(self.preview_table, preview_table_headers)

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
            templates: List[DeviceTemplateModel] = self.template_service.get_all_templates()
            if not templates:
                logger.info("模板库为空或加载失败")
            for tmpl_model in templates:
                self.template_combo.addItem(tmpl_model.name, tmpl_model.id)
        except Exception as e:
            logger.error(f"加载模板列表失败: {e}")
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")

    def manage_templates(self, tm: TemplateService):
        """打开模板管理对话框"""
        dialog = TemplateManageDialog(template_service=self.template_service, parent=self)
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
            if hasattr(self, 'variable_prefix_input'): # 检查UI是否已设置
                 self.variable_prefix_input.clear() 
            if hasattr(self, 'description_prefix_input'):
                 self.description_prefix_input.clear()
            self.update_point_table()
            self.update_preview()
            return

        self.current_template_id = self.template_combo.itemData(index)
        if self.current_template_id is None:
            logger.warning("选中的模板没有关联的ID (itemData is None)")
            self.template = None
            if hasattr(self, 'variable_prefix_input'):
                self.variable_prefix_input.clear()
            if hasattr(self, 'description_prefix_input'):
                self.description_prefix_input.clear()
            self.update_point_table()
            self.update_preview()
            return

        try:
            self.template = self.template_service.get_template_by_id(self.current_template_id)
        except Exception as e:
            logger.error(f"获取模板详情失败 (ID: {self.current_template_id}): {e}")
            QMessageBox.critical(self, "错误", f"加载模板详情失败: {str(e)}")
            self.template = None

        # 当模板改变时，我们不清空用户已输入的前缀，除非没有有效模板
        # 用户可能希望对不同模板使用相同的前缀
        # 但是，如果之前没有有效模板，或者新选的模板也无效，则清空前缀
        if not self.template:
            logger.warning(f"未能加载ID为 {self.current_template_id} 的模板详情。")
            if hasattr(self, 'variable_prefix_input'):
                self.variable_prefix_input.clear() 
            if hasattr(self, 'description_prefix_input'):
                self.description_prefix_input.clear()

        # 注意：这里不再从 self.template.prefix 设置 prefix_input 的值
        # self.prefix_input.setText(self.template.prefix or "") 这一行是错误的，因为模板的 prefix 已移除

        self.update_point_table()
        self.update_preview() # 模板更改会触发预览更新，预览会使用当前 prefix_input 的内容

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
                self.point_table.setItem(row, 3, QTableWidgetItem(point_model.sll_setpoint or ""))
                self.point_table.setItem(row, 4, QTableWidgetItem(point_model.sl_setpoint or ""))
                self.point_table.setItem(row, 5, QTableWidgetItem(point_model.sh_setpoint or ""))
                self.point_table.setItem(row, 6, QTableWidgetItem(point_model.shh_setpoint or ""))

    def update_preview(self):
        """更新预览表格"""
        self.preview_table.setRowCount(0)

        variable_prefix = ""
        if hasattr(self, 'variable_prefix_input'): 
            variable_prefix = self.variable_prefix_input.text().strip()
        
        description_prefix = ""
        if hasattr(self, 'description_prefix_input'):
            description_prefix = self.description_prefix_input.text().strip()

        if self.template and self.template.points:
            for point_model in self.template.points:
                row = self.preview_table.rowCount()
                self.preview_table.insertRow(row)
                
                full_var_name = f"{variable_prefix}_{point_model.var_suffix}" if variable_prefix and point_model.var_suffix else (variable_prefix or point_model.var_suffix or "")
                
                desc_parts = []
                if description_prefix:
                    desc_parts.append(description_prefix)
                if point_model.desc_suffix:
                    desc_parts.append(point_model.desc_suffix)
                full_desc = "".join(desc_parts).strip()
                
                self.preview_table.setItem(row, 0, QTableWidgetItem(full_var_name))
                self.preview_table.setItem(row, 1, QTableWidgetItem(full_desc))
                self.preview_table.setItem(row, 2, QTableWidgetItem(point_model.data_type))
                self.preview_table.setItem(row, 3, QTableWidgetItem(point_model.sll_setpoint or ""))
                self.preview_table.setItem(row, 4, QTableWidgetItem(point_model.sl_setpoint or ""))
                self.preview_table.setItem(row, 5, QTableWidgetItem(point_model.sh_setpoint or ""))
                self.preview_table.setItem(row, 6, QTableWidgetItem(point_model.shh_setpoint or ""))

    def save_config(self):
        """保存配置"""
        if not self.template:
            QMessageBox.warning(self, "警告", "请先选择一个设备模板。")
            return

        variable_prefix = ""
        if hasattr(self, 'variable_prefix_input'):
            variable_prefix = self.variable_prefix_input.text().strip()
        
        description_prefix = ""
        if hasattr(self, 'description_prefix_input'):
            description_prefix = self.description_prefix_input.text().strip()
        
        template_name = self.template.name 

        points_to_save = []
        if self.template.points:
            for point_model in self.template.points:
                # 保存原始后缀，而不是拼接后的完整名称
                points_to_save.append({
                    "var_suffix": point_model.var_suffix,
                    "desc_suffix": point_model.desc_suffix,
                    "data_type": point_model.data_type,
                    "sll_setpoint": point_model.sll_setpoint or "", #确保提供默认值
                    "sl_setpoint": point_model.sl_setpoint or "",
                    "sh_setpoint": point_model.sh_setpoint or "",
                    "shh_setpoint": point_model.shh_setpoint or ""
                })
        
        if not points_to_save and self.template.points: # 模板有点位但生成列表为空
             logger.warning(f"模板 {template_name} 有点位，但保存列表为空。变量前缀: {variable_prefix}, 描述前缀: {description_prefix}")
        
        if not points_to_save: # 如果模板本身为空，或处理后确实没有点位
            reply = QMessageBox.question(self, "确认操作",
                                       f"模板 '{template_name}' 不包含任何点位，或者处理后未生成点位。\\n是否仍要为变量前缀 '{variable_prefix}' 和描述前缀 '{description_prefix}' 应用此空配置？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            logger.info(f"准备保存配置: 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}', 模板='{template_name}', 原始点位数={(len(self.template.points) if self.template.points else 0)}")
            
            was_existing = self.config_service.does_configuration_exist(template_name, variable_prefix, description_prefix)
            
            success, message = self.config_service.save_device_configuration(
                template_name=template_name,
                variable_prefix=variable_prefix, 
                description_prefix=description_prefix,
                points_data=points_to_save 
            )
            
            if success:
                action_text = "更新" if was_existing else "创建"
                point_count_message = f"（模板包含 {len(self.template.points or [])} 个原始点位）"
                if not points_to_save: 
                    point_count_message = "（配置了0个点位）"
                
                QMessageBox.information(self, f"配置已{action_text}",
                                        f"模板 '{template_name}' (变量前缀 '{variable_prefix}', 描述前缀 '{description_prefix}') 的配置已成功{action_text}。\n{point_count_message}")
                self.accept()
            else:
                QMessageBox.critical(self, "保存失败", message)

        except ValueError as ve: 
             logger.error(f"保存配置 (变量前缀:'{variable_prefix}', 描述前缀:'{description_prefix}', 模板:'{template_name}') 失败 (ValueError): {ve}", exc_info=True)
             QMessageBox.critical(self, "保存失败", str(ve))
        except Exception as e: 
            logger.error(f"保存设备点表配置 (变量前缀:'{variable_prefix}', 描述前缀:'{description_prefix}', 模板:'{template_name}') 时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时发生未知错误: {str(e)}")
