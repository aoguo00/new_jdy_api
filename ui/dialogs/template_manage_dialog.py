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

class TemplateManageDialogUI:
    """设备模板管理对话框的UI视图部分。此类负责UI元素的创建、布局和提供更新接口。"""
    def __init__(self):
        """构造函数：初始化UI类中将要使用的所有UI元素（声明为None，在setup_ui中实例化）。"""
        self.template_list: 'QTableWidget' = None
        self.new_template_btn: 'QPushButton' = None
        self.delete_template_btn: 'QPushButton' = None
        self.template_name_input: 'QLineEdit' = None
        self.point_table: 'QTableWidget' = None
        self.add_point_btn: 'QPushButton' = None
        self.edit_point_btn: 'QPushButton' = None
        self.delete_point_btn: 'QPushButton' = None
        self.save_template_btn: 'QPushButton' = None
        self.button_box: 'QDialogButtonBox' = None

    def setup_ui(self, dialog_instance: 'QDialog'):
        """设置并初始化所有UI界面元素。

        Args:
            dialog_instance (QDialog): 承载这些UI元素的主对话框实例 (TemplateManageDialog)。
        """
        layout = QVBoxLayout(dialog_instance)

        h_layout = QHBoxLayout()
        template_list_group = QGroupBox("模板列表")
        template_list_layout = QVBoxLayout()
        self.template_list = QTableWidget()
        self.template_list.setColumnCount(1)
        self.template_list.setHorizontalHeaderLabels(["模板名称"])
        self.template_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.template_list.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        header = self.template_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        template_list_layout.addWidget(self.template_list)
        template_btn_layout = QHBoxLayout()
        self.new_template_btn = QPushButton("新建模板")
        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.setEnabled(False)
        template_btn_layout.addWidget(self.new_template_btn)
        template_btn_layout.addWidget(self.delete_template_btn)
        template_list_layout.addLayout(template_btn_layout)
        template_list_group.setLayout(template_list_layout)
        h_layout.addWidget(template_list_group)

        template_detail_group = QGroupBox("模板详情")
        template_detail_layout = QVBoxLayout()
        info_form = QFormLayout()
        self.template_name_input = QLineEdit()
        info_form.addRow("模板名称:", self.template_name_input)
        template_detail_layout.addLayout(info_form)

        point_list_group = QGroupBox("点位列表")
        point_list_layout = QVBoxLayout()
        self.point_table = QTableWidget()
        self.point_table.setColumnCount(3)
        self.point_table.setHorizontalHeaderLabels(["变量名后缀", "描述后缀", "类型"])
        header_points = self.point_table.horizontalHeader()
        for i in range(3):
            header_points.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        point_list_layout.addWidget(self.point_table)

        point_btn_layout = QHBoxLayout()
        self.add_point_btn = QPushButton("添加点位")
        self.add_point_btn.setEnabled(False)
        self.edit_point_btn = QPushButton("编辑点位")
        self.edit_point_btn.setEnabled(False)
        self.delete_point_btn = QPushButton("删除点位")
        self.delete_point_btn.setEnabled(False)
        point_btn_layout.addWidget(self.add_point_btn)
        point_btn_layout.addWidget(self.edit_point_btn)
        point_btn_layout.addWidget(self.delete_point_btn)
        point_list_layout.addLayout(point_btn_layout)
        point_list_group.setLayout(point_list_layout)
        template_detail_layout.addWidget(point_list_group)

        save_layout = QHBoxLayout()
        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.setEnabled(False)
        save_layout.addStretch()
        save_layout.addWidget(self.save_template_btn)
        template_detail_layout.addLayout(save_layout)
        template_detail_group.setLayout(template_detail_layout)
        h_layout.addWidget(template_detail_group)

        layout.addLayout(h_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        layout.addWidget(self.button_box)
        logger.info("TemplateManageDialogUI: UI setup complete (prefix field removed).")

class TemplateManageDialog(QDialog):
    """设备模板管理对话框 - 控制器部分。
    此类负责管理对话框的整体行为，包括：
    - 初始化UI视图 (TemplateManageDialogUI)。
    - 连接UI事件到处理逻辑 (槽函数)。
    - 管理对话框状态 (如当前选中的模板ID，是否有未保存的修改)。
    - 与模板服务 (TemplateService) 交互以加载、保存、删除模板和点位数据。
    - 处理用户交互，如模板选择、新建、编辑、删除、点位操作等。
    - 管理子对话框的创建和数据获取（如点位编辑对话框）。
    """

    def __init__(self, template_service: TemplateService, parent=None):
        """构造函数。

        Args:
            template_service (TemplateService): 模板服务的实例，用于后端数据操作。
            parent (QWidget, optional): 父QWidget。默认为None。
        """
        super().__init__(parent)
        self.setWindowTitle("设备模板管理")
        self.resize(1000, 700)

        self.template_service = template_service
        if not self.template_service:
            logger.error("TemplateManageDialog 初始化失败: TemplateService 未提供。")
            QMessageBox.critical(self, "严重错误", "模板服务未能加载，对话框无法使用。")
            return

        self.current_template_id: Optional[int] = None
        self.current_template: Optional[DeviceTemplateModel] = None
        self.template_modified = False

        self.view = TemplateManageDialogUI()
        self.view.setup_ui(self)
        self._connect_signals()
        self.load_templates()

    def _connect_signals(self):
        """内部辅助方法：连接所有UI元素的信号到相应的槽函数。"""
        if not self.view: return
        self.view.template_list.selectionModel().selectionChanged.connect(self.template_selected)
        self.view.new_template_btn.clicked.connect(self.create_new_template_ui_flow)
        self.view.delete_template_btn.clicked.connect(self.delete_template)
        self.view.template_name_input.textChanged.connect(self.template_data_changed)
        self.view.point_table.itemSelectionChanged.connect(self.update_point_buttons_state)
        self.view.add_point_btn.clicked.connect(self.add_point)
        self.view.edit_point_btn.clicked.connect(self.edit_point)
        self.view.delete_point_btn.clicked.connect(self.delete_point)
        self.view.save_template_btn.clicked.connect(self.save_template)
        self.view.button_box.accepted.connect(self.accept)
        self.view.button_box.rejected.connect(self.reject)
        logger.info("TemplateManageDialog: Signals connected (prefix signal removed).")

    def load_templates(self):
        """从服务加载所有模板的列表，并将其填充到UI的模板表格中。
        如果加载成功且列表不为空，则默认选中第一个模板。
        """
        if not self.view or not self.template_service: return
        self.view.template_list.setRowCount(0)
        try:
            templates = self.template_service.get_all_templates()
            if not templates:
                self.clear_template_details_ui() # 清空右侧详情
                logger.info("No templates found to load.")
                return

            for i, template_model in enumerate(templates):
                self.view.template_list.insertRow(i)
                item = QTableWidgetItem(template_model.name)
                if template_model.id is not None:
                    item.setData(Qt.ItemDataRole.UserRole + 1, template_model.id)
                else:
                    logger.warning(f"Template '{template_model.name}' loaded without an ID.")
                self.view.template_list.setItem(i, 0, item)
            
            if templates: # 如果加载了模板，默认选中第一个
                self.view.template_list.selectRow(0)
            else: # 如果没有模板（理论上上面已处理，双重保险）
                self.clear_template_details_ui()
            logger.info(f"Loaded {len(templates)} templates.")

        except Exception as e:
            logger.error(f"加载模板列表时出错: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载模板列表失败: {str(e)}")
            self.clear_template_details_ui()

    def _prompt_unsaved_changes(self) -> bool:
        """内部辅助方法：检查当前是否有未保存的修改。
        如果有，则向用户显示确认对话框，询问是否要放弃更改并继续。
        
        Returns:
            bool: 如果用户选择继续 (Yes) 或没有未保存的更改，则返回True。
                  如果用户选择不继续 (No)，则返回False。
        """
        if self.template_modified:
            reply = QMessageBox.question(
                self, "未保存的修改",
                "当前模板有未保存的修改，继续操作将丢失这些修改。确定要继续吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            return reply == QMessageBox.StandardButton.Yes
        return True # 没有未保存的更改，可以直接继续

    def template_selected(self, selected, deselected):
        """处理模板列表中用户选择发生变化时的逻辑。
        主要步骤包括：
        1. 检查是否有未保存的修改，如果用户不想放弃则阻止切换。
        2. 获取选中模板的ID和详细信息。
        3. 在UI的详情区域填充模板名称和点位列表。
        4. 更新相关按钮（如删除、添加点位）的启用状态。
        5. 重置模板已修改标志。
        Args:
            selected (QItemSelection): 新选中的项。
            deselected (QItemSelection): 取消选中的项。
        """
        if not self.view: return
        if not self._prompt_unsaved_changes():
            current_row = -1
            if self.current_template_id:
                for r in range(self.view.template_list.rowCount()):
                    item = self.view.template_list.item(r, 0)
                    if item and item.data(Qt.ItemDataRole.UserRole + 1) == self.current_template_id:
                        current_row = r
                        break
            if current_row != -1:
                self.view.template_list.selectionModel().selectionChanged.disconnect(self.template_selected)
                self.view.template_list.selectRow(current_row)
                self.view.template_list.selectionModel().selectionChanged.connect(self.template_selected)
            return

        selected_items = self.view.template_list.selectedItems()
        if not selected_items:
            self.clear_template_details_ui()
            return
        item = selected_items[0]
        if not item: return
        template_id = item.data(Qt.ItemDataRole.UserRole + 1)
        if not template_id:
            logger.warning("未找到选中模板的ID")
            self.clear_template_details_ui()
            return
        
        self.current_template_id = template_id
        self.current_template = self.template_service.get_template_by_id(template_id)
        
        if not self.current_template:
            logger.warning(f"未找到ID为 {template_id} 的模板详情")
            self.clear_template_details_ui()
            return

        self.view.template_name_input.setText(self.current_template.name or '')

        self.view.point_table.setRowCount(0)
        if self.current_template.points:
            for i, point_model in enumerate(self.current_template.points):
                self.view.point_table.insertRow(i)
                self.view.point_table.setItem(i, 0, QTableWidgetItem(point_model.var_suffix or '')) 
                self.view.point_table.setItem(i, 1, QTableWidgetItem(point_model.desc_suffix or ''))
                self.view.point_table.setItem(i, 2, QTableWidgetItem(point_model.data_type or 'BOOL'))
        
        self.view.delete_template_btn.setEnabled(True)
        self.view.add_point_btn.setEnabled(True)
        self.update_point_buttons_state()
        self.view.save_template_btn.setEnabled(False)
        self.template_modified = False
        logger.info(f"Template ID {template_id} selected and details loaded (prefix handling removed).")

    def clear_template_details_ui(self, for_new_template_creation=False):
        """清空模板详情区域的UI元素（名称、点位表）并重置相关状态变量。
        Args:
            for_new_template_creation (bool, optional): 如果为True，表示此次清空是为了创建新模板...
        """
        if not self.view: return
        self.view.template_name_input.clear()
        self.view.point_table.setRowCount(0)
        if not for_new_template_creation:
            self.current_template_id = None
            self.current_template = None
        self.template_modified = False 
        self.view.delete_template_btn.setEnabled(False)
        self.view.add_point_btn.setEnabled(for_new_template_creation or (self.current_template_id is not None))
        self.view.edit_point_btn.setEnabled(False)
        self.view.delete_point_btn.setEnabled(False)
        self.view.save_template_btn.setEnabled(False)
        logger.debug("Template details UI cleared (prefix field removed).")

    def create_new_template_ui_flow(self):
        """处理用户点击"新建模板"按钮的交互流程。
        主要步骤：
        1. 检查并提示未保存的更改。
        2. 如果用户同意继续，则清空模板详情UI，为新模板输入做准备。
        3. 将内部状态设置为正在创建新模板 (current_template_id = None)。
        4. 聚焦到模板名称输入框。
        5. 初始时模板保存按钮禁用，添加点位按钮启用。
        """
        if not self.view: return
        if not self._prompt_unsaved_changes():
            return

        logger.info("Initiating new template creation flow.")
        self.current_template_id = None # 明确表示正在创建新模板
        self.current_template = None
        self.clear_template_details_ui(for_new_template_creation=True) # 清空详情，但保留一些状态用于新模板
        
        self.view.template_name_input.setFocus()
        self.template_modified = False # 新建时，初始状态为未修改，直到用户输入
        # 保存按钮在 template_data_changed 中根据输入激活
        # 添加点位按钮已在 clear_template_details_ui 中根据 for_new_template_creation 启用

    def template_data_changed(self):
        """当模板的元数据（如名称）在UI输入框中被修改时调用此方法。
        它会标记模板已被修改 (self.template_modified = True)，
        并根据模板名称是否为空来启用或禁用保存按钮。
        """
        if not self.view: return
        self.template_modified = True
        can_save = bool(self.view.template_name_input.text().strip())
        self.view.save_template_btn.setEnabled(can_save)

    def delete_template(self):
        """处理用户点击"删除模板"按钮的逻辑。
        主要步骤：
        1. 确认当前已选中一个模板。
        2. 弹出确认对话框，防止误删。
        3. 如果用户确认删除，则调用template_service执行删除操作。
        4. 根据服务层返回的结果，显示成功或失败消息。
        5. 如果删除成功，则重新加载模板列表。
        """
        if not self.view or not self.template_service: return
        if not self.current_template_id or not self.current_template:
            QMessageBox.information(self, "提示", "请先选择一个模板进行删除。")
            return

        template_name_to_delete = self.current_template.name 
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template_name_to_delete}' 吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            deletion_successful = self.template_service.delete_template(self.current_template_id)
            if deletion_successful:
                QMessageBox.information(self, "删除成功", f"模板 '{template_name_to_delete}' 已成功删除。")
                self.template_modified = False # 删除成功后，重置修改状态
                self.load_templates() # 重新加载列表（会自动清空或选中第一个）
            else:
                QMessageBox.warning(self, "删除失败", f"删除模板 '{template_name_to_delete}' 失败。请查看日志了解详情。")
        except Exception as e:
            logger.error(f"删除模板ID {self.current_template_id} 时发生错误: {e}", exc_info=True)
            QMessageBox.critical(self, "删除失败", f"删除模板时发生未知错误: {str(e)}")

    def add_point(self):
        """为当前正在编辑或新建的模板添加一个新的点位信息。
        主要步骤：
        1. 检查是否可以添加点位（例如，新模板是否已输入名称）。
        2. 调用 _create_point_dialog 创建并显示点位编辑对话框。
        3. 如果用户在对话框中确认输入，则获取点位数据并在UI的点位表格中添加新行。
        4. 标记模板已修改。
        """
        if not self.view: return
        # 无论是编辑现有模板还是创建新模板，都可以添加点位
        # 如果是新模板，current_template_id 为 None，但此时UI流程应允许添加
        if self.current_template_id is None and not self.view.template_name_input.text().strip():
             QMessageBox.warning(self, "提示", "请先为新模板输入一个名称。")
             return

        dialog = self._create_point_dialog() # 使用内部方法创建对话框
        if dialog.exec() == QDialog.Accepted:
            point_data = dialog.get_point_data()
            row = self.view.point_table.rowCount()
            self.view.point_table.insertRow(row)
            self.view.point_table.setItem(row, 0, QTableWidgetItem(point_data['var_suffix']))
            self.view.point_table.setItem(row, 1, QTableWidgetItem(point_data['desc_suffix']))
            self.view.point_table.setItem(row, 2, QTableWidgetItem(point_data['data_type']))
            
            self.template_data_changed() # 点位变动也算数据变动
            self.update_point_buttons_state()

    def edit_point(self):
        """编辑当前在点位表格中选中的点位信息。
        主要步骤：
        1. 确认用户已在点位表格中选中一个点位。
        2. 使用选中点位的现有数据预填充并显示点位编辑对话框 (_create_point_dialog)。
        3. 如果用户确认修改，则更新UI表格中对应行的数据。
        4. 标记模板已修改。
        """
        if not self.view: return
        selected_items = self.view.point_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要编辑的点位。")
            return

        row = selected_items[0].row()
        dialog = self._create_point_dialog(
            var_suffix=self.view.point_table.item(row, 0).text(),
            desc_suffix=self.view.point_table.item(row, 1).text(),
            data_type=self.view.point_table.item(row, 2).text()
        )

        if dialog.exec() == QDialog.Accepted:
            point_data = dialog.get_point_data()
            self.view.point_table.setItem(row, 0, QTableWidgetItem(point_data['var_suffix']))
            self.view.point_table.setItem(row, 1, QTableWidgetItem(point_data['desc_suffix']))
            self.view.point_table.setItem(row, 2, QTableWidgetItem(point_data['data_type']))
            self.template_data_changed() # 点位变动也算数据变动

    def delete_point(self):
        """从当前模板的点位列表中删除一个或多个选中的点位。
        主要步骤：
        1. 确认用户已在点位表格中选中至少一个点位。
        2. 弹出确认对话框。
        3. 如果用户确认，则从UI表格中移除选中的行。
        4. 标记模板已修改。
        """
        if not self.view: return
        selected_items = self.view.point_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要删除的点位。")
            return

        rows_to_delete = sorted(list(set(item.row() for item in selected_items)), reverse=True)
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除选中的 {len(rows_to_delete)} 个点位吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        for row in rows_to_delete:
            self.view.point_table.removeRow(row)
        
        self.template_data_changed() # 点位变动也算数据变动
        self.update_point_buttons_state()

    def _create_point_dialog(self, var_suffix="", desc_suffix="", data_type="BOOL") -> 'QDialog':
        """内部辅助方法：创建并配置一个用于添加或编辑单个点位信息的对话框。
        
        Args:
            var_suffix (str, optional): 变量名后缀的初始值 (用于编辑)。默认为 ""。
            desc_suffix (str, optional): 描述后缀的初始值 (用于编辑)。默认为 ""。
            data_type (str, optional): 数据类型的初始值 (用于编辑)。默认为 "BOOL"。
            
        Returns:
            QDialog: 配置好的点位编辑对话框实例。该对话框实例上会附加一个 get_point_data 方法，
                     用于获取用户输入的数据。
        """
        dialog = QDialog(self) # 父窗口是 TemplateManageDialog 实例
        dialog.setWindowTitle("编辑点位")
        layout = QVBoxLayout(dialog)
        form = QFormLayout()

        var_suffix_input = QLineEdit(var_suffix)
        form.addRow("变量名后缀:", var_suffix_input)
        desc_suffix_input = QLineEdit(desc_suffix)
        form.addRow("描述后缀:", desc_suffix_input)
        type_combo = QComboBox()
        type_combo.addItems(["BOOL", "INT", "REAL", "DINT"]) # 根据需要扩展类型
        type_combo.setCurrentText(data_type)
        form.addRow("数据类型:", type_combo)
        layout.addLayout(form)

        button_box_point = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box_point.accepted.connect(dialog.accept)
        button_box_point.rejected.connect(dialog.reject)
        layout.addWidget(button_box_point)

        # 将输入控件附加到对话框实例上，以便 get_point_data 可以访问它们
        dialog.var_suffix_input = var_suffix_input
        dialog.desc_suffix_input = desc_suffix_input
        dialog.type_combo = type_combo
        
        def get_point_data_method():
            return {
                'var_suffix': dialog.var_suffix_input.text().strip(),
                'desc_suffix': dialog.desc_suffix_input.text().strip(),
                'data_type': dialog.type_combo.currentText()
            }
        dialog.get_point_data = get_point_data_method # 将方法附加到对话框实例
        return dialog

    def save_template(self):
        """保存当前正在编辑的模板（可能是新建的或从列表中选中的已修改模板）。
        主要步骤：
        1. 从UI获取模板名称和所有点位数据。
        2. 进行必要的验证，如名称不能为空、新模板名称是否与现有冲突等。
        3. 根据当前状态（是新建模板还是更新现有模板）调用template_service的相应方法。
        4. 处理服务层返回的结果，显示成功或失败消息。
        5. 如果保存成功，则重置"已修改"标志，禁用保存按钮，并可能重新加载模板列表（特别是新建时）。
        """
        if not self.view or not self.template_service: return

        name = self.view.template_name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "输入错误", "模板名称不能为空。")
            return

        points_ui_data = []
        for row in range(self.view.point_table.rowCount()):
            points_ui_data.append({
                'var_suffix': self.view.point_table.item(row, 0).text(),
                'desc_suffix': self.view.point_table.item(row, 1).text(),
                'data_type': self.view.point_table.item(row, 2).text()
            })
        
        is_creating_new = self.current_template_id is None
        try:
            existing_templates = self.template_service.get_all_templates()
            if is_creating_new:
                if any(t.name == name for t in existing_templates):
                    QMessageBox.warning(self, "名称冲突", f"模板名称 '{name}' 已存在。")
                    return
            elif self.current_template and self.current_template.name != name:
                if any(t.name == name and t.id != self.current_template_id for t in existing_templates):
                    QMessageBox.warning(self, "名称冲突", f"模板名称 '{name}' 已被其他模板使用。")
                    return
        except Exception as e_fetch:
            logger.error(f"保存前检查模板名称冲突时，获取所有模板失败: {e_fetch}", exc_info=True)
            QMessageBox.critical(self, "错误", f"无法验证模板名称唯一性: {e_fetch}")
            return
            
        if is_creating_new and not points_ui_data:
            reply = QMessageBox.question(self, "确认", "新模板不包含任何点位，确定要创建吗？",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.No:
                return
        
        if not is_creating_new and not self.template_modified:
             QMessageBox.information(self, "提示", "模板内容未修改。")
             self.view.save_template_btn.setEnabled(False)
             return

        try:
            if is_creating_new:
                logger.info(f"尝试创建新模板: 名称='{name}'")
                created_template = self.template_service.create_template(name, points_ui_data)
                if created_template:
                    QMessageBox.information(self, "成功", f"模板 '{name}' 创建成功。")
                    self.template_modified = False 
                    self.view.save_template_btn.setEnabled(False)
                    self.load_templates()
                    for i in range(self.view.template_list.rowCount()):
                        item = self.view.template_list.item(i, 0)
                        if item and item.text() == created_template.name:
                            self.view.template_list.setCurrentItem(item)
                            break
                else:
                    QMessageBox.warning(self, "创建失败", f"创建模板 '{name}' 失败 (服务层返回 None)。")
            else: 
                if self.current_template_id is None: 
                    QMessageBox.critical(self, "内部错误", "尝试更新但当前模板ID未设置。")
                    return
                logger.info(f"尝试更新模板 ID: {self.current_template_id}, 名称='{name}'")
                updated_template = self.template_service.update_template(
                    self.current_template_id, name, points_ui_data
                )
                if updated_template:
                    QMessageBox.information(self, "成功", f"模板 '{name}' 更新成功。")
                    self.template_modified = False 
                    self.view.save_template_btn.setEnabled(False)
                    current_row = self.view.template_list.currentRow()
                    if current_row >= 0:
                        list_item = self.view.template_list.item(current_row, 0)
                        if list_item: list_item.setText(updated_template.name)
                    self.current_template = updated_template
                else:
                    QMessageBox.warning(self, "更新失败", f"更新模板 '{name}' 失败 (服务层返回 None)。")

        except ValueError as ve: 
            logger.error(f"保存模板时发生值错误: {ve}", exc_info=True)
            QMessageBox.critical(self, "保存失败", str(ve))
        except Exception as e:
            logger.error(f"保存模板时发生未知错误: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存模板时发生未知错误: {str(e)}")

    def update_point_buttons_state(self):
        """根据当前点位表格的选择状态以及模板是否可编辑，更新"添加点位"、"编辑点位"、"删除点位"按钮的启用/禁用状态。"""
        if not self.view: return
        has_points_in_table = self.view.point_table.rowCount() > 0
        point_row_selected = bool(self.view.point_table.selectedItems())
        
        # 添加点位按钮：只要有模板被选中或正在创建新模板（且名称不为空）就应启用
        can_add_points = (self.current_template_id is not None) or \
                         (self.current_template_id is None and bool(self.view.template_name_input.text().strip()))

        self.view.add_point_btn.setEnabled(can_add_points)
        self.view.edit_point_btn.setEnabled(has_points_in_table and point_row_selected)
        self.view.delete_point_btn.setEnabled(has_points_in_table and point_row_selected)

    def accept(self):
        """重写QDialog的accept方法。
        在对话框通过"确定"按钮关闭前，检查是否有未保存的修改。
        如果用户选择不放弃修改，则阻止对话框关闭。
        """
        if not self._prompt_unsaved_changes():
            return # 用户选择不放弃更改，对话框不关闭
        super().accept()

    def reject(self):
        """重写QDialog的reject方法。
        在对话框通过"取消"按钮关闭或按ESC键关闭前，检查是否有未保存的修改。
        如果用户选择不放弃修改，则阻止对话框关闭。
        """
        if not self._prompt_unsaved_changes():
            return # 用户选择不放弃更改，对话框不关闭
        super().reject()

    def closeEvent(self, event: 'QCloseEvent'):
        """重写QWidget的closeEvent方法。
        在用户尝试通过窗口控件（如右上角关闭按钮）关闭对话框时被调用。
        检查是否有未保存的修改，如果用户选择不放弃修改，则忽略关闭事件，阻止窗口关闭。
        
        Args:
            event (QCloseEvent): 窗口关闭事件对象。
        """
        if not self._prompt_unsaved_changes():
            event.ignore() # 用户选择不放弃更改，阻止窗口关闭
            return
        event.accept()
