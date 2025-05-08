"""模板管理对话框"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem,
                               QPushButton, QHeaderView, QMessageBox,
                               QDialogButtonBox, QComboBox, QListWidgetItem)
from PySide6.QtCore import Qt
from core.third_party_config_area import TemplateService
from core.third_party_config_area.models import DeviceTemplateModel, TemplatePointModel
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

class TemplateManageDialog(QDialog):
    """设备模板管理对话框"""

    def __init__(self, template_service: TemplateService, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设备模板管理")
        self.resize(1000, 700)

        self.template_service = template_service
        if not self.template_service:
            logger.error("TemplateManageDialog 初始化失败: TemplateService 未提供。")
            QMessageBox.critical(self, "严重错误", "模板服务未能加载，对话框无法使用。")
            # Handle error

        self.current_template_id: Optional[int] = None
        self.current_template: Optional[DeviceTemplateModel] = None
        self.template_modified = False

        self.setup_ui()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)

        # 模板列表和详情的水平布局
        h_layout = QHBoxLayout()

        # 左侧模板列表
        template_list_group = QGroupBox("模板列表")
        template_list_layout = QVBoxLayout()

        self.template_list = QTableWidget()
        self.template_list.setColumnCount(1)  # 只显示模板名称
        self.template_list.setHorizontalHeaderLabels(["模板名称"])
        self.template_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.template_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.template_list.selectionModel().selectionChanged.connect(self.template_selected)

        # 设置表格列宽
        header = self.template_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)

        template_list_layout.addWidget(self.template_list)

        # 模板操作按钮
        template_btn_layout = QHBoxLayout()

        self.new_template_btn = QPushButton("新建模板")
        self.new_template_btn.clicked.connect(self.create_new_template)

        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.delete_template_btn.setEnabled(False)

        template_btn_layout.addWidget(self.new_template_btn)
        template_btn_layout.addWidget(self.delete_template_btn)

        template_list_layout.addLayout(template_btn_layout)
        template_list_group.setLayout(template_list_layout)

        h_layout.addWidget(template_list_group)

        # 右侧模板详情
        template_detail_group = QGroupBox("模板详情")
        template_detail_layout = QVBoxLayout()

        # 模板基本信息
        info_form = QFormLayout()

        self.template_name_input = QLineEdit()
        self.template_name_input.textChanged.connect(self.template_name_changed)
        info_form.addRow("模板名称:", self.template_name_input)

        self.template_prefix_input = QLineEdit()
        self.template_prefix_input.textChanged.connect(self.template_prefix_changed)
        info_form.addRow("模板前缀:", self.template_prefix_input)

        template_detail_layout.addLayout(info_form)

        # 点位列表
        point_list_group = QGroupBox("点位列表")
        point_list_layout = QVBoxLayout()

        self.point_table = QTableWidget()
        self.point_table.setColumnCount(3)
        self.point_table.setHorizontalHeaderLabels([
            "变量名后缀", "描述后缀", "类型"
        ])

        # 设置表格列宽
        header = self.point_table.horizontalHeader()
        for i in range(3):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)

        point_list_layout.addWidget(self.point_table)

        # 点位操作按钮
        point_btn_layout = QHBoxLayout()

        self.add_point_btn = QPushButton("添加点位")
        self.add_point_btn.clicked.connect(self.add_point)
        self.add_point_btn.setEnabled(False)

        self.edit_point_btn = QPushButton("编辑点位")
        self.edit_point_btn.clicked.connect(self.edit_point)
        self.edit_point_btn.setEnabled(False)

        self.delete_point_btn = QPushButton("删除点位")
        self.delete_point_btn.clicked.connect(self.delete_point)
        self.delete_point_btn.setEnabled(False)

        point_btn_layout.addWidget(self.add_point_btn)
        point_btn_layout.addWidget(self.edit_point_btn)
        point_btn_layout.addWidget(self.delete_point_btn)

        point_list_layout.addLayout(point_btn_layout)
        point_list_group.setLayout(point_list_layout)

        template_detail_layout.addWidget(point_list_group)

        # 保存模板按钮
        save_layout = QHBoxLayout()
        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.clicked.connect(self.save_template)
        self.save_template_btn.setEnabled(False)
        save_layout.addStretch()
        save_layout.addWidget(self.save_template_btn)

        template_detail_layout.addLayout(save_layout)
        template_detail_group.setLayout(template_detail_layout)

        h_layout.addWidget(template_detail_group)

        layout.addLayout(h_layout)

        # 对话框按钮
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # 加载模板列表
        self.load_templates()

    def load_templates(self):
        """加载模板列表"""
        self.template_list.setRowCount(0)
        try:
            templates = self.template_service.get_all_templates() # Returns List[DeviceTemplateModel]
            if not templates:
                 # Optionally, show a message or disable some UI elements
                 return

            for i, template_model in enumerate(templates):
                self.template_list.insertRow(i)
                item = QTableWidgetItem(template_model.name) # Use attribute access

                # 保存模板ID以便后续操作
                if template_model.id is not None:
                    item.setData(Qt.ItemDataRole.UserRole + 1, template_model.id) # Use attribute access
                else:
                    # Log warning if ID is None, though it should usually be present from DB
                    logger.warning(f"Template '{template_model.name}' loaded without an ID.")

                self.template_list.setItem(i, 0, item)
        except Exception as e:
            logger.error(f"加载模板列表时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")

    def template_selected(self, selected, deselected):
        """模板选中时的处理"""
        try:
            selected_items = self.template_list.selectedItems()
            if not selected_items:
                # Clear details area
                self.clear_template_details_ui()
                return

            item = selected_items[0]
            if not item:
                return

            template_id = item.data(Qt.ItemDataRole.UserRole + 1)
            if not template_id:
                logger.warning("未找到选中模板的ID")
                return

            self.current_template_id = template_id

            # Get template details (returns DeviceTemplateModel or None)
            self.current_template = self.template_service.get_template_by_id(template_id)
            
            if not self.current_template:
                logger.warning(f"未找到ID为 {template_id} 的模板详情")
                # Clear UI and disable buttons if template not found
                self.clear_template_details_ui()
                return

            # Populate template details using attribute access
            self.template_name_input.setText(self.current_template.name or '')
            self.template_prefix_input.setText(self.current_template.prefix or '')

            # Populate points table using attribute access
            self.point_table.setRowCount(0)
            if self.current_template.points: # Check if the points list exists and is not empty
                for i, point_model in enumerate(self.current_template.points): # Iterate through TemplatePointModel objects
                    self.point_table.insertRow(i)
                    # Use attribute access for point details
                    self.point_table.setItem(i, 0, QTableWidgetItem(point_model.var_suffix or '')) 
                    self.point_table.setItem(i, 1, QTableWidgetItem(point_model.desc_suffix or ''))
                    self.point_table.setItem(i, 2, QTableWidgetItem(point_model.data_type or 'BOOL')) # Default if empty, though should have a value
            # else: # If template_model.points is empty or None
                # The table is already cleared, nothing more needed here.
                # logger.debug(f"Template '{template_model.name}' has no points to display.")

            # Enable relevant buttons
            self.delete_template_btn.setEnabled(True)
            self.add_point_btn.setEnabled(True)
            # Enable edit/delete point buttons only if points exist and one is selected
            # We need a separate connection for point selection to handle this accurately.
            # For now, enable them if points exist and a row is selected in point_table
            self.point_table.itemSelectionChanged.connect(self.update_point_buttons_state) # 连接信号
            self.update_point_buttons_state() #初始状态更新
            
            self.save_template_btn.setEnabled(False) # Enable save only when modified
            self.template_modified = False # Reset modification flag

        except Exception as e:
            logger.error(f"模板选择处理时发生错误: {e}", exc_info=True)
            # Clear UI on error
            self.clear_template_details_ui()
            QMessageBox.critical(self, "错误", f"加载模板详情时出错: {str(e)}")

    def clear_template_details_ui(self):
        """清空模板详情区域的UI元素并重置状态。"""
        self.template_name_input.clear()
        if hasattr(self, 'template_prefix_input'): # 确保前缀输入框已创建
            self.template_prefix_input.clear()
        self.point_table.setRowCount(0)
        
        self.current_template_id = None
        self.current_template = None
        self.template_modified = False
        
        # 更新按钮状态
        self.delete_template_btn.setEnabled(False)
        self.add_point_btn.setEnabled(False) # 通常在未选中模板时不应能添加点
        self.edit_point_btn.setEnabled(False)
        self.delete_point_btn.setEnabled(False)
        self.save_template_btn.setEnabled(False)

    def create_new_template(self):
        """创建新模板"""
        # 创建新模板对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("创建新模板")
        
        layout = QVBoxLayout(dialog)
        form = QFormLayout()
        
        # 模板名称输入
        name_input = QLineEdit()
        form.addRow("模板名称:", name_input)
        
        layout.addLayout(form)
        
        # 对话框按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() != QDialog.Accepted:
            return
            
        # 获取输入数据
        name = name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "错误", "模板名称不能为空")
            return
            
        # 检查名称是否已存在
        if any(item.text() == name for item in self.template_list.findItems(name, Qt.MatchFlag.MatchExactly)):
            QMessageBox.warning(self, "错误", f"模板名称 '{name}' 已存在")
            return
            
        # 为新模板准备参数
        prefix_for_new_template = ""  # 新模板的默认前缀
        points_for_new_template = []  # 新模板默认为空点位列表
        
        try:
            # 创建新模板
            created_template = self.template_service.create_template(
                name=name, 
                prefix=prefix_for_new_template, 
                points_data=points_for_new_template
            ) # Returns Optional[DeviceTemplateModel]
            if not created_template:
                QMessageBox.warning(self, "错误", "创建模板失败 (服务层返回空)")
                return
                
            # 添加到列表
            row = self.template_list.rowCount()
            self.template_list.insertRow(row)
            item = QTableWidgetItem(created_template.name) # Use attribute access for name
            if created_template.id is not None: # Check if id exists before setting data
                 item.setData(Qt.ItemDataRole.UserRole + 1, created_template.id) # Use attribute access for id
            else:
                 logger.warning(f"Newly created template '{created_template.name}' has no ID.")
            self.template_list.setItem(row, 0, item)
            
            # 选中新模板
            self.template_list.selectRow(row)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建模板时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

    def template_name_changed(self):
        """模板名称修改处理"""
        if not self.current_template_id: # Or if no template is effectively loaded
            return
            
        self.template_modified = True
        self.save_template_btn.setEnabled(True)

    def template_prefix_changed(self):
        """模板前缀修改处理"""
        if not self.current_template_id: # Or if no template is effectively loaded
            return
        self.template_modified = True
        self.save_template_btn.setEnabled(True)

    def delete_template(self):
        """删除模板"""
        if not self.current_template_id:
            QMessageBox.information(self, "提示", "请先选择一个模板进行删除。")
            return

        template_name = self.template_name_input.text() # Get name for messages

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template_name}' 吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No # Default to No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除模板
        deletion_successful = self.template_service.delete_template(self.current_template_id)

        if deletion_successful:
            success_message = f"模板 '{template_name}' 已成功删除。"
            QMessageBox.information(self, "删除成功", success_message)

            # 刷新模板列表
            self.load_templates() 
            # load_templates 之后，如果列表为空，或者没有自动选中项，
            # template_selected 可能不会被有效触发以清空详情。
            # 因此，在删除成功后主动清空详情区是个好主意。
            if not self.template_list.selectedItems(): # 如果删除后没有选中项了
                 self.clear_template_details_ui()

        else:
            failure_message = f"删除模板 '{template_name}' 失败。\\n请查看日志了解详情。"
            QMessageBox.warning(self, "删除失败", failure_message)

    def add_point(self):
        """添加点位"""
        if not self.current_template_id:
            return

        dialog = self.create_point_dialog()
        if dialog.exec() == QDialog.Accepted:
            point_data = dialog.get_point_data()

            # 添加到表格
            row = self.point_table.rowCount()
            self.point_table.insertRow(row)
            self.point_table.setItem(row, 0, QTableWidgetItem(point_data['变量名后缀']))
            self.point_table.setItem(row, 1, QTableWidgetItem(point_data['描述后缀']))
            self.point_table.setItem(row, 2, QTableWidgetItem(point_data['类型']))

            # 标记有未保存的更改
            self.template_modified = True
            self.save_template_btn.setEnabled(True)

    def edit_point(self):
        """编辑点位"""
        selected_items = self.point_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要编辑的点位")
            return

        # 获取选中的行
        row = selected_items[0].row()

        # 创建点位编辑对话框
        dialog = self.create_point_dialog(
            var_suffix=self.point_table.item(row, 0).text(),
            desc_suffix=self.point_table.item(row, 1).text(),
            data_type=self.point_table.item(row, 2).text()
        )

        if dialog.exec() != QDialog.Accepted:
            return

        # 获取点位数据
        point_data = dialog.get_point_data()

        # 更新表格
        self.point_table.setItem(row, 0, QTableWidgetItem(point_data['变量名后缀']))
        self.point_table.setItem(row, 1, QTableWidgetItem(point_data['描述后缀']))
        self.point_table.setItem(row, 2, QTableWidgetItem(point_data['类型']))

        # 标记有未保存的更改
        self.template_modified = True
        self.save_template_btn.setEnabled(True)

    def delete_point(self):
        """删除点位"""
        selected_items = self.point_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要删除的点位")
            return

        # 获取选中的行
        rows = set()
        for item in selected_items:
            rows.add(item.row())

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(rows)} 个点位吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 从后往前删除，避免索引变化
        for row in sorted(rows, reverse=True):
            self.point_table.removeRow(row)

        # 标记有未保存的更改
        self.template_modified = True
        self.save_template_btn.setEnabled(True)

    def create_point_dialog(self, var_suffix="", desc_suffix="", data_type="BOOL"):
        """创建点位编辑对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑点位")

        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        # 变量名后缀
        var_suffix_input = QLineEdit(var_suffix)
        form.addRow("变量名后缀:", var_suffix_input)
        dialog.var_suffix_input = var_suffix_input

        # 描述后缀
        desc_suffix_input = QLineEdit(desc_suffix)
        form.addRow("描述后缀:", desc_suffix_input)
        dialog.desc_suffix_input = desc_suffix_input

        # 数据类型
        type_combo = QComboBox()
        type_combo.addItems(["BOOL", "INT", "REAL", "DINT"])
        type_combo.setCurrentText(data_type)
        form.addRow("数据类型:", type_combo)
        dialog.type_combo = type_combo

        layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        # 添加获取点位数据方法
        def get_point_data():
            return {
                '变量名后缀': dialog.var_suffix_input.text().strip(),
                '描述后缀': dialog.desc_suffix_input.text().strip(),
                '类型': dialog.type_combo.currentText()
            }

        dialog.get_point_data = get_point_data

        return dialog

    def save_template(self):
        """保存模板"""
        if not self.current_template_id and not self.template_list.findItems(self.template_name_input.text().strip(), Qt.MatchFlag.MatchExactly):
            # This case implies we are in a state to create a new template if the name is new
            # or update an existing one if current_template_id is set.
            # The button should ideally only be active if current_template_id or a new valid name is present.
            pass # Let it proceed to logic below
        elif not self.current_template_id:
            # No template selected from list, and not a distinct new name for creation.
            # This state should ideally be prevented by disabling save_template_btn.
            QMessageBox.warning(self, "操作无效", "请选择一个模板进行修改，或输入一个全新的模板名称进行创建。")
            return
        
        if not self.template_modified and self.current_template_id:
            QMessageBox.information(self, "提示", "模板内容未修改。")
            return

        # 获取表单数据
        name = self.template_name_input.text().strip()
        prefix = self.template_prefix_input.text().strip() # Get prefix from the UI input

        if not name:
            QMessageBox.warning(self, "输入错误", "模板名称不能为空。")
            return

        # 收集点位数据
        points = [] # This is the correct variable holding points data from the table
        for row in range(self.point_table.rowCount()):
            points.append({
                'var_suffix': self.point_table.item(row, 0).text(),
                'desc_suffix': self.point_table.item(row, 1).text(),
                'data_type': self.point_table.item(row, 2).text()
                # Add other fields if they are in the table and needed by TemplatePointModel
            })

        if not points and self.current_template_id is None: # Only enforce for new templates from UI perspective
            # For existing templates, user might want to delete all points.
            # Service layer can decide if an empty template is valid.
            reply = QMessageBox.question(self, "确认", "模板不包含任何点位，确定要创建吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        # 在这里决定是创建还是更新
        is_creating_new = False
        if self.current_template_id is None:
            # 检查名称是否已存在 (服务层也会检查，但UI层先检查可以提供更及时的反馈)
            existing_templates = self.template_service.get_all_templates()
            if any(t.name == name for t in existing_templates):
                QMessageBox.warning(self, "名称冲突", f"模板名称 '{name}' 已存在，请使用其他名称。")
                return
            is_creating_new = True
        elif self.current_template and self.current_template.name != name:
            # 如果是重命名，也检查新名称是否与其他模板冲突 (除了自身)
            existing_templates = self.template_service.get_all_templates()
            if any(t.name == name and t.id != self.current_template_id for t in existing_templates):
                 QMessageBox.warning(self, "名称冲突", f"模板名称 '{name}' 已被其他模板使用。")
                 return

        try:
            if is_creating_new:
                logger.info(f"尝试创建新模板: {name}, 前缀: {prefix}")
                created_template = self.template_service.create_template(name, prefix, points) # Use 'points'
                if created_template:
                    QMessageBox.information(self, "成功", f"模板 '{name}' 创建成功。")
                    self.template_modified = False # Reset flag
                    self.load_templates() # Reload to get new ID and select
                    # Find and select the newly created template
                    for i in range(self.template_list.rowCount()):
                        if self.template_list.item(i, 0).text() == created_template.name:
                            self.template_list.setCurrentItem(self.template_list.item(i, 0))
                            break
                else:
                    QMessageBox.warning(self, "创建失败", f"创建模板 '{name}' 失败 (服务层返回 None)。")
            else: # 更新现有模板
                if self.current_template_id is None: # Should not happen if logic is correct
                    QMessageBox.critical(self, "错误", "尝试更新但未选中模板ID。")
                    return
                    
                logger.info(f"尝试更新模板 ID: {self.current_template_id}, 名称: {name}, 前缀: {prefix}")
                updated_template = self.template_service.update_template(self.current_template_id, name, prefix, points) # Use 'points'
                if updated_template:
                    QMessageBox.information(self, "成功", f"模板 '{name}' 更新成功。")
                    self.template_modified = False # Reset flag
                    # 更新UI中列表项的名称（如果改变了）和前缀
                    current_row = self.template_list.currentRow()
                    if current_row >= 0:
                        self.template_list.item(current_row, 0).setText(updated_template.name)
                        # Note: prefix is not displayed in the list currently, but current_template object needs update
                    self.current_template = updated_template # Update the cached current_template
                    self.save_template_btn.setEnabled(False)
                else:
                    QMessageBox.warning(self, "更新失败", f"更新模板 '{name}' 失败 (服务层返回 None)。")

        except ValueError as ve: # Catch specific errors from service (e.g., duplicate name on update)
            logger.error(f"保存模板时发生值错误: {ve}", exc_info=True)
            QMessageBox.critical(self, "保存失败", str(ve))
        except Exception as e:
            logger.error(f"保存模板时发生未知错误: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存模板时发生未知错误: {str(e)}")
            # import traceback
            # traceback.print_exc()

    def update_point_buttons_state(self):
        """根据点位表格的选择状态更新编辑和删除点位按钮的可用性"""
        has_points = self.point_table.rowCount() > 0
        point_selected = bool(self.point_table.selectedItems())
        
        self.edit_point_btn.setEnabled(has_points and point_selected)
        self.delete_point_btn.setEnabled(has_points and point_selected)

    def closeEvent(self, event):
        """关闭对话框时检查是否有未保存的修改"""
        if self.template_modified:
            reply = QMessageBox.question(
                self, "未保存的修改",
                "有未保存的修改，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return

        event.accept()
