"""设备点位配置对话框"""

import logging
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QComboBox, QLineEdit, QTableWidget,
                               QTableWidgetItem, QPushButton, QHeaderView,
                               QSplitter, QWidget, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from typing import Optional, List, Dict, Any
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

        # 新增：批量配置功能
        self.pending_configurations: List[Dict[str, Any]] = []
        self.last_selected_template_name: Optional[str] = None

        self.setup_ui()

    def _setup_table_widget(self, table_widget: QTableWidget, column_headers: List[str]):
        """辅助方法：设置QTableWidget的通用属性"""
        table_widget.setColumnCount(len(column_headers))
        table_widget.setHorizontalHeaderLabels(column_headers)
        header = table_widget.horizontalHeader()

        # 设置所有列都可以交互式调整大小
        for i in range(len(column_headers)):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)

        # 根据内容调整初始列宽
        table_widget.resizeColumnsToContents()

        # 设置最小列宽，确保内容可见
        for i in range(len(column_headers)):
            table_widget.setColumnWidth(i, max(table_widget.columnWidth(i), 100))

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)

        # 设备信息区域
        info_group = QGroupBox("第三方设备信息")
        info_layout = QFormLayout()

        # 模板选择
        self.template_combo = QComboBox()
        self.load_template_list()

        # 优先使用记忆的模板，其次使用初始模板
        template_to_select = self.last_selected_template_name or self.initial_template_name_to_select
        if template_to_select:
            index = self.template_combo.findText(template_to_select)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)
            else:
                logger.warning(f"模板 '{template_to_select}' 在列表中未找到。")
                if self.template_combo.count() > 0:
                    self.template_combo.setCurrentIndex(0)
        elif self.template_combo.count() > 0:
             self.template_combo.setCurrentIndex(0)

        self.template_combo.currentIndexChanged.connect(self.template_selected)
        info_layout.addRow("设备模板:", self.template_combo)

        # 变量输入框
        self.variable_prefix_input = QLineEdit()
        self.variable_prefix_input.setPlaceholderText("请输入变量名 (例如 PT0101 或使用 a*b 格式，*代表模板变量位置)")
        # 使用textEdited信号来处理用户输入，不会触发程序性修改的循环
        self.variable_prefix_input.textEdited.connect(self.handle_prefix_input)
        self.variable_prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("变量名:", self.variable_prefix_input)

        # 描述输入框
        self.description_prefix_input = QLineEdit()
        self.description_prefix_input.setPlaceholderText("请输入自定义描述，支持使用*作为占位符")
        self.description_prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("描述:", self.description_prefix_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 创建水平分割器，分为左右两部分
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 左侧：配置和预览区域
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        # 左侧垂直分割器，分为上下两部分
        left_splitter = QSplitter(Qt.Orientation.Vertical)

        # 配置区域 (上部分)
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        config_group = QGroupBox("模板点位详情 (源模板)")
        points_layout = QVBoxLayout()

        self.point_table = QTableWidget()
        point_table_headers = [
            "自定义变量名", "自定义描述描述", "数据类型",
            "SLL设定值", "SL设定值", "SH设定值", "SHH设定值"
        ]
        self._setup_table_widget(self.point_table, point_table_headers)

        points_layout.addWidget(self.point_table)
        config_group.setLayout(points_layout)
        config_layout.addWidget(config_group)

        # 模板管理按钮
        template_btn_layout = QHBoxLayout()
        template_manage_btn = QPushButton("管理设备模板")
        template_manage_btn.clicked.connect(lambda: self.manage_templates())
        template_btn_layout.addStretch()
        template_btn_layout.addWidget(template_manage_btn)
        config_layout.addLayout(template_btn_layout)
        left_splitter.addWidget(config_widget)

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

        left_splitter.addWidget(preview_widget)

        # 设置左侧分割比例 (1:1)
        left_splitter.setSizes([self.height() // 2, self.height() // 2])
        left_layout.addWidget(left_splitter)

        # 右侧：待保存配置列表
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        # 待保存配置区域
        pending_group = QGroupBox("待保存配置列表")
        pending_layout = QVBoxLayout()

        # 配置数量标签
        self.pending_count_label = QLabel("待保存配置: 0 个")
        pending_layout.addWidget(self.pending_count_label)

        # 待保存配置表格
        self.pending_table = QTableWidget()
        pending_table_headers = ["模板名称", "变量名", "描述", "点位数量", "操作"]
        self._setup_table_widget(self.pending_table, pending_table_headers)
        pending_layout.addWidget(self.pending_table)

        pending_group.setLayout(pending_layout)
        right_layout.addWidget(pending_group)

        # 将左右两部分添加到主分割器
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)

        # 设置主分割器比例 (左侧占2/3，右侧占1/3)
        main_splitter.setSizes([800, 400])
        layout.addWidget(main_splitter)

        # 按钮区域
        buttons_layout = QHBoxLayout()

        # 新增：添加到列表按钮
        self.add_to_list_btn = QPushButton("添加到列表")
        self.add_to_list_btn.clicked.connect(self.add_to_pending_list)

        # 修改：批量保存按钮
        self.save_all_btn = QPushButton("应用并保存所有配置")
        self.save_all_btn.clicked.connect(self.save_all_configs)
        self.save_all_btn.setEnabled(False)  # 初始状态禁用

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_to_list_btn)
        buttons_layout.addWidget(self.save_all_btn)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

        # 加载初始模板
        if self.template_combo.count() > 0:
            self.template_selected(0)
        elif self.template_combo.count() == 0:
            QMessageBox.information(self, "提示", "模板库为空，请先通过'管理设备模板'添加模板。")

        # 添加批量配置功能说明
        QMessageBox.information(self, "批量配置功能说明",
                           "🎯 新的批量配置模式：\n\n"
                           "1. 选择设备模板（模板会保持选中状态）\n"
                           "2. 输入变量名和描述信息\n"
                           "3. 点击'添加到列表'按钮\n"
                           "4. 重复步骤2-3，添加更多配置\n"
                           "5. 最后点击'应用并保存所有配置'\n\n"
                           "💡 变量名和描述支持占位符格式：\n"
                           "- 普通格式: 'PT0101' → 'PT0101_模板变量'\n"
                           "- 占位符格式: 'a*b' → 'a_模板变量b'\n\n"
                           "✨ 优势：配置10个阀门只需选择1次模板！")

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

    def manage_templates(self):
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
            # 记住当前选择的模板
            if self.template:
                self.last_selected_template_name = self.template.name
                logger.info(f"记住模板选择: {self.last_selected_template_name}")
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

                # 使用统一的变量名生成逻辑（与模型保持一致）
                if '*' in variable_prefix:
                    # 根据*号分割变量前缀
                    prefix_parts = variable_prefix.split('*')
                    if len(prefix_parts) >= 2:
                        # 前缀部分 + 模板变量 + 后缀部分
                        if not point_model.var_suffix:
                            full_var_name = f"{prefix_parts[0]}{prefix_parts[1]}"
                        else:
                            full_var_name = f"{prefix_parts[0]}{point_model.var_suffix}{prefix_parts[1]}"
                    else:
                        # 如果只有前半部分(如a*)，且模板变量为空，则仅显示前缀
                        if not point_model.var_suffix:
                            full_var_name = prefix_parts[0]
                        else:
                            full_var_name = f"{prefix_parts[0]}{point_model.var_suffix}"
                else:
                    # 直接拼接，不做任何额外处理
                    full_var_name = f"{variable_prefix}{point_model.var_suffix}"

                # 新的描述前缀处理逻辑，使用*号作为描述占位符
                if description_prefix and '*' in description_prefix:
                    # 根据*号分割描述前缀
                    desc_prefix_parts = description_prefix.split('*')
                    if len(desc_prefix_parts) >= 2:
                        # 前缀部分 + 模板描述 + 后缀部分
                        # 如果模板描述为空，则只连接前缀和后缀
                        if not point_model.desc_suffix:
                            full_desc = f"{desc_prefix_parts[0]}{desc_prefix_parts[1]}"
                        else:
                            full_desc = f"{desc_prefix_parts[0]}{point_model.desc_suffix}{desc_prefix_parts[1]}"
                    else:
                        # 如果只有前半部分(如a*)，且模板描述为空，则仅显示前缀
                        if not point_model.desc_suffix:
                            full_desc = desc_prefix_parts[0]
                        else:
                            full_desc = f"{desc_prefix_parts[0]}{point_model.desc_suffix}"
                else:
                    # 原处理逻辑：直接拼接
                    full_desc = f"{description_prefix}{point_model.desc_suffix}" if description_prefix and point_model.desc_suffix else (description_prefix or point_model.desc_suffix or "")

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
             logger.warning(f"模板 {template_name} 有点位，但保存列表为空。自定义变量: {variable_prefix}, 自定义描述: {description_prefix}")

        if not points_to_save: # 如果模板本身为空，或处理后确实没有点位
            reply = QMessageBox.question(self, "确认操作",
                                       f"模板 '{template_name}' 不包含任何点位，或者处理后未生成点位。\\n是否仍要为变量前缀 '{variable_prefix}' 和描述前缀 '{description_prefix}' 应用此空配置？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            logger.info(f"准备保存配置: 自定义变量='{variable_prefix}', 自定义描述='{description_prefix}', 模板='{template_name}', 原始点位数={(len(self.template.points) if self.template.points else 0)}")

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
                                        f"模板 '{template_name}' (自定义变量 '{variable_prefix}', 自定义描述 '{description_prefix}') 的配置已成功{action_text}。\n{point_count_message}")
                self.accept()
            else:
                QMessageBox.critical(self, "保存失败", message)

        except ValueError as ve:
             logger.error(f"保存配置 (自定义变量:'{variable_prefix}', 自定义描述:'{description_prefix}', 模板:'{template_name}') 失败 (ValueError): {ve}", exc_info=True)
             QMessageBox.critical(self, "保存失败", str(ve))
        except Exception as e:
            logger.error(f"保存设备点表配置 (自定义变量:'{variable_prefix}', 自定义描述:'{description_prefix}', 模板:'{template_name}') 时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时发生未知错误: {str(e)}")

    def handle_prefix_input(self):
        """处理变量名输入"""
        # 移除自动删除*号的代码，让用户可以正常输入*号
        # 在update_preview方法中处理*号的解析逻辑，而不是在输入时干预
        pass

    def add_to_pending_list(self):
        """添加当前配置到待保存列表"""
        if not self.template:
            QMessageBox.warning(self, "警告", "请先选择一个设备模板。")
            return

        variable_prefix = self.variable_prefix_input.text().strip()
        description_prefix = self.description_prefix_input.text().strip()
        template_name = self.template.name

        # 检查是否重复配置
        for config in self.pending_configurations:
            if (config['template_name'] == template_name and
                config['variable_prefix'] == variable_prefix and
                config['description_prefix'] == description_prefix):
                QMessageBox.warning(self, "重复配置",
                                  f"相同的配置已存在：\n"
                                  f"模板: {template_name}\n"
                                  f"变量名: {variable_prefix}\n"
                                  f"描述: {description_prefix}")
                return

        # 准备点位数据
        points_to_save = []
        if self.template.points:
            for point_model in self.template.points:
                points_to_save.append({
                    "var_suffix": point_model.var_suffix,
                    "desc_suffix": point_model.desc_suffix,
                    "data_type": point_model.data_type,
                    "sll_setpoint": point_model.sll_setpoint or "",
                    "sl_setpoint": point_model.sl_setpoint or "",
                    "sh_setpoint": point_model.sh_setpoint or "",
                    "shh_setpoint": point_model.shh_setpoint or ""
                })

        # 添加到待保存列表
        config_data = {
            'template_name': template_name,
            'variable_prefix': variable_prefix,
            'description_prefix': description_prefix,
            'points_data': points_to_save,
            'point_count': len(points_to_save)
        }

        self.pending_configurations.append(config_data)
        self.update_pending_table()

        # 清空输入框，准备下一个配置
        self.variable_prefix_input.clear()
        self.description_prefix_input.clear()
        self.update_preview()

        QMessageBox.information(self, "添加成功",
                              f"配置已添加到列表：\n"
                              f"模板: {template_name}\n"
                              f"变量名: {variable_prefix}\n"
                              f"描述: {description_prefix}\n"
                              f"点位数量: {len(points_to_save)}")

    def update_pending_table(self):
        """更新待保存配置表格"""
        self.pending_table.setRowCount(len(self.pending_configurations))

        for row, config in enumerate(self.pending_configurations):
            # 模板名称
            self.pending_table.setItem(row, 0, QTableWidgetItem(config['template_name']))

            # 生成示例变量名（显示第一个点位的完整变量名作为示例）
            example_var_name = self._generate_example_variable_name(config)
            self.pending_table.setItem(row, 1, QTableWidgetItem(example_var_name))

            # 生成示例描述（显示第一个点位的完整描述作为示例）
            example_desc = self._generate_example_description(config)
            self.pending_table.setItem(row, 2, QTableWidgetItem(example_desc))

            # 点位数量
            self.pending_table.setItem(row, 3, QTableWidgetItem(str(config['point_count'])))

            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.clicked.connect(lambda _, r=row: self.remove_pending_config(r))
            self.pending_table.setCellWidget(row, 4, delete_btn)

        # 更新计数标签
        self.pending_count_label.setText(f"待保存配置: {len(self.pending_configurations)} 个")

        # 更新保存按钮状态
        self.save_all_btn.setEnabled(len(self.pending_configurations) > 0)

    def _generate_example_variable_name(self, config):
        """生成示例变量名（使用第一个点位作为示例）"""
        variable_prefix = config['variable_prefix']

        # 如果没有点位数据，返回原始输入
        if not config['points_data']:
            return variable_prefix

        # 使用第一个点位的后缀作为示例
        first_point = config['points_data'][0]
        var_suffix = first_point['var_suffix']

        # 使用与预览相同的逻辑生成完整变量名
        if '*' in variable_prefix:
            # 根据*号分割变量名
            prefix_parts = variable_prefix.split('*')
            if len(prefix_parts) >= 2:
                # 前半部分 + 模板变量 + 后半部分
                if not var_suffix:
                    full_var_name = f"{prefix_parts[0]}{prefix_parts[1]}"
                else:
                    full_var_name = f"{prefix_parts[0]}{var_suffix}{prefix_parts[1]}"
            else:
                # 如果只有前半部分(如a*)，且模板变量为空，则仅显示前半部分
                if not var_suffix:
                    full_var_name = prefix_parts[0]
                else:
                    full_var_name = f"{prefix_parts[0]}{var_suffix}"
        else:
            # 直接拼接，不做任何额外处理
            full_var_name = f"{variable_prefix}{var_suffix}"

        return full_var_name

    def _generate_example_description(self, config):
        """生成示例描述（使用第一个点位作为示例）"""
        description_prefix = config['description_prefix']

        # 如果没有点位数据，返回原始输入
        if not config['points_data']:
            return description_prefix

        # 使用第一个点位的后缀作为示例
        first_point = config['points_data'][0]
        desc_suffix = first_point['desc_suffix']

        # 使用与预览相同的逻辑生成完整描述
        if description_prefix and '*' in description_prefix:
            # 根据*号分割描述
            desc_prefix_parts = description_prefix.split('*')
            if len(desc_prefix_parts) >= 2:
                # 前半部分 + 模板描述 + 后半部分
                if not desc_suffix:
                    full_desc = f"{desc_prefix_parts[0]}{desc_prefix_parts[1]}"
                else:
                    full_desc = f"{desc_prefix_parts[0]}{desc_suffix}{desc_prefix_parts[1]}"
            else:
                # 如果只有前半部分(如a*)，且模板描述为空，则仅显示前半部分
                if not desc_suffix:
                    full_desc = desc_prefix_parts[0]
                else:
                    full_desc = f"{desc_prefix_parts[0]}{desc_suffix}"
        else:
            # 原处理逻辑：直接拼接
            full_desc = f"{description_prefix}{desc_suffix}" if description_prefix and desc_suffix else (description_prefix or desc_suffix or "")

        return full_desc

    def remove_pending_config(self, row: int):
        """删除指定行的待保存配置"""
        if 0 <= row < len(self.pending_configurations):
            config = self.pending_configurations[row]
            reply = QMessageBox.question(self, "确认删除",
                                       f"确定要删除以下配置吗？\n"
                                       f"模板: {config['template_name']}\n"
                                       f"变量名: {config['variable_prefix']}\n"
                                       f"描述: {config['description_prefix']}",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)

            if reply == QMessageBox.StandardButton.Yes:
                del self.pending_configurations[row]
                self.update_pending_table()
                QMessageBox.information(self, "删除成功", "配置已从列表中删除。")

    def save_all_configs(self):
        """批量保存所有待保存的配置"""
        if not self.pending_configurations:
            QMessageBox.warning(self, "警告", "没有待保存的配置。")
            return

        # 确认保存
        reply = QMessageBox.question(self, "确认保存",
                                   f"确定要保存 {len(self.pending_configurations)} 个配置吗？",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                   QMessageBox.StandardButton.Yes)

        if reply != QMessageBox.StandardButton.Yes:
            return

        success_count = 0
        failed_configs = []

        for i, config in enumerate(self.pending_configurations):
            try:
                logger.info(f"保存配置 {i+1}/{len(self.pending_configurations)}: "
                          f"模板='{config['template_name']}', "
                          f"变量名='{config['variable_prefix']}', "
                          f"描述='{config['description_prefix']}'")

                success, message = self.config_service.save_device_configuration(
                    template_name=config['template_name'],
                    variable_prefix=config['variable_prefix'],
                    description_prefix=config['description_prefix'],
                    points_data=config['points_data']
                )

                if success:
                    success_count += 1
                    logger.info(f"配置保存成功: {config['template_name']}")
                else:
                    failed_configs.append({
                        'config': config,
                        'error': message
                    })
                    logger.error(f"配置保存失败: {config['template_name']} - {message}")

            except Exception as e:
                error_msg = str(e)
                failed_configs.append({
                    'config': config,
                    'error': error_msg
                })
                logger.error(f"保存配置时发生异常: {config['template_name']} - {e}", exc_info=True)

        # 显示保存结果
        if success_count == len(self.pending_configurations):
            # 全部成功
            QMessageBox.information(self, "保存成功",
                                  f"所有 {success_count} 个配置已成功保存！")
            self.pending_configurations.clear()
            self.update_pending_table()
            self.accept()
        elif success_count > 0:
            # 部分成功
            failed_list = "\n".join([f"- {fc['config']['template_name']} ({fc['config']['variable_prefix']}): {fc['error']}"
                                   for fc in failed_configs])
            QMessageBox.warning(self, "部分保存成功",
                              f"成功保存: {success_count} 个\n"
                              f"保存失败: {len(failed_configs)} 个\n\n"
                              f"失败的配置:\n{failed_list}\n\n"
                              f"失败的配置仍保留在列表中，您可以修改后重试。")

            # 移除成功保存的配置
            self.pending_configurations = [fc['config'] for fc in failed_configs]
            self.update_pending_table()
        else:
            # 全部失败
            failed_list = "\n".join([f"- {fc['config']['template_name']} ({fc['config']['variable_prefix']}): {fc['error']}"
                                   for fc in failed_configs])
            QMessageBox.critical(self, "保存失败",
                               f"所有配置保存失败:\n{failed_list}")

    def save_config(self):
        """保留原有的单个保存功能（向后兼容）"""
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
             logger.warning(f"模板 {template_name} 有点位，但保存列表为空。变量名: {variable_prefix}, 描述: {description_prefix}")

        if not points_to_save: # 如果模板本身为空，或处理后确实没有点位
            reply = QMessageBox.question(self, "确认操作",
                                       f"模板 '{template_name}' 不包含任何点位，或者处理后未生成点位。\n是否仍要为变量名 '{variable_prefix}' 和描述 '{description_prefix}' 应用此空配置？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            logger.info(f"准备保存配置: 变量名='{variable_prefix}', 描述='{description_prefix}', 模板='{template_name}', 原始点位数={(len(self.template.points) if self.template.points else 0)}")

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
                                        f"模板 '{template_name}' (变量名 '{variable_prefix}', 描述 '{description_prefix}') 的配置已成功{action_text}。\n{point_count_message}")
                self.accept()
            else:
                QMessageBox.critical(self, "保存失败", message)

        except ValueError as ve:
             logger.error(f"保存配置 (变量名:'{variable_prefix}', 描述:'{description_prefix}', 模板:'{template_name}') 失败 (ValueError): {ve}", exc_info=True)
             QMessageBox.critical(self, "保存失败", str(ve))
        except Exception as e:
            logger.error(f"保存设备点表配置 (变量名:'{variable_prefix}', 描述:'{description_prefix}', 模板:'{template_name}') 时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"保存配置时发生未知错误: {str(e)}")
