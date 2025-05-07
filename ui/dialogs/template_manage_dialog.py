"""模板管理对话框"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QLineEdit, QTableWidget, QTableWidgetItem,
                               QPushButton, QHeaderView, QMessageBox,
                               QDialogButtonBox, QComboBox)
from PySide6.QtCore import Qt
from core.devices import TemplateManager

class TemplateManageDialog(QDialog):
    """设备模板管理对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设备模板管理")
        self.resize(900, 600)

        self.current_template_id = None
        self.template_modified = False
        self.template_manager = TemplateManager()

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

        self.copy_template_btn = QPushButton("复制模板")
        self.copy_template_btn.clicked.connect(self.copy_template)
        self.copy_template_btn.setEnabled(False)

        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.delete_template_btn.setEnabled(False)
        
        self.export_template_btn = QPushButton("导出模板")
        self.export_template_btn.clicked.connect(self.export_template)
        self.export_template_btn.setEnabled(False)

        template_btn_layout.addWidget(self.new_template_btn)
        template_btn_layout.addWidget(self.copy_template_btn)
        template_btn_layout.addWidget(self.delete_template_btn)
        template_btn_layout.addWidget(self.export_template_btn)

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

        templates = self.template_manager.get_all_templates()

        for i, template in enumerate(templates):
            self.template_list.insertRow(i)
            item = QTableWidgetItem(template['name'])

            # 保存模板ID以便后续操作
            item.setData(Qt.ItemDataRole.UserRole + 1, template['id'])

            self.template_list.setItem(i, 0, item)

    def template_selected(self, selected, deselected):
        """模板选中时的处理"""
        try:
            selected_items = self.template_list.selectedItems()
            if not selected_items:
                # 清空详情区域
                self.template_name_input.clear()
                self.point_table.setRowCount(0)
                self.current_template_id = None

                # 禁用按钮
                self.copy_template_btn.setEnabled(False)
                self.delete_template_btn.setEnabled(False)
                self.export_template_btn.setEnabled(False)
                self.add_point_btn.setEnabled(False)
                self.edit_point_btn.setEnabled(False)
                self.delete_point_btn.setEnabled(False)
                self.save_template_btn.setEnabled(False)

                return

            # 获取选中行的第一个单元格
            item = selected_items[0]
            if not item:
                return

            row = item.row()
            template_id = item.data(Qt.ItemDataRole.UserRole + 1)
            if not template_id:
                print("警告：未找到模板ID")
                return

            self.current_template_id = template_id

            # 获取模板详情
            template = self.template_manager.get_template_by_id(template_id)
            if not template:
                print(f"警告：未找到ID为{template_id}的模板")
                return

            # 检查模板数据的完整性
            if not isinstance(template, dict):
                print(f"警告：模板数据格式错误 - {type(template)}")
                return

            if '点位' not in template or not isinstance(template['点位'], list):
                print(f"警告：模板点位数据无效")
                template['点位'] = []

            # 填充模板详情
            self.template_name_input.setText(template.get('name', ''))

            # 填充点位表格
            self.point_table.setRowCount(0)

            for i, point in enumerate(template['点位']):
                if not isinstance(point, dict):
                    print(f"警告：点位数据格式错误 - {point}")
                    continue

                self.point_table.insertRow(i)
                self.point_table.setItem(i, 0, QTableWidgetItem(str(point.get('变量名后缀', ''))))
                self.point_table.setItem(i, 1, QTableWidgetItem(str(point.get('描述后缀', ''))))
                self.point_table.setItem(i, 2, QTableWidgetItem(str(point.get('类型', 'BOOL'))))

            # 启用按钮
            self.copy_template_btn.setEnabled(True)
            self.delete_template_btn.setEnabled(True)
            self.export_template_btn.setEnabled(True)
            self.add_point_btn.setEnabled(True)
            self.edit_point_btn.setEnabled(True)
            self.delete_point_btn.setEnabled(True)
            self.save_template_btn.setEnabled(True)

            # 重置修改标记
            self.template_modified = False

        except Exception as e:
            print(f"模板选择处理时发生错误: {e}")
            import traceback
            traceback.print_exc()
            # 出错时清空并禁用界面
            self.template_name_input.clear()
            self.point_table.setRowCount(0)
            self.current_template_id = None

            self.copy_template_btn.setEnabled(False)
            self.delete_template_btn.setEnabled(False)
            self.export_template_btn.setEnabled(False)
            self.add_point_btn.setEnabled(False)
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
            
        # 创建模板数据
        template_data = {
            "标识符": name,  # 使用名称作为标识符
            "变量前缀": "",  # 默认空前缀
            "点位": []  # 默认没有点位
        }
        
        try:
            # 创建新模板
            template = self.template_manager.create_template(name, template_data)
            if not template:
                QMessageBox.warning(self, "错误", "创建模板失败")
                return
                
            # 添加到列表
            row = self.template_list.rowCount()
            self.template_list.insertRow(row)
            item = QTableWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole + 1, template['id'])
            self.template_list.setItem(row, 0, item)
            
            # 选中新模板
            self.template_list.selectRow(row)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"创建模板时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

    def template_name_changed(self):
        """模板名称修改处理"""
        if not self.current_template_id:
            return
            
        self.template_modified = True
        self.save_template_btn.setEnabled(True)

    def copy_template(self):
        """复制模板"""
        if not self.current_template_id:
            return
            
        # 获取当前模板
        template = self.template_manager.get_template_by_id(self.current_template_id)
        if not template:
            QMessageBox.warning(self, "错误", "获取模板信息失败")
            return
            
        # 生成新名称
        base_name = template['name']
        new_name = f"{base_name} - 副本"
        counter = 1
        
        # 确保名称唯一
        while any(item.text() == new_name for item in self.template_list.findItems(new_name, Qt.MatchFlag.MatchExactly)):
            counter += 1
            new_name = f"{base_name} - 副本 {counter}"
            
        # 创建新模板数据
        template_data = {
            "标识符": new_name,  # 使用新名称作为标识符
            "变量前缀": template.get('变量前缀', ''),
            "点位": template.get('点位', [])
        }
        
        try:
            # 创建新模板
            new_template = self.template_manager.create_template(new_name, template_data)
            if not new_template:
                QMessageBox.warning(self, "错误", "复制模板失败")
                return
                
            # 添加到列表
            row = self.template_list.rowCount()
            self.template_list.insertRow(row)
            item = QTableWidgetItem(new_name)
            item.setData(Qt.ItemDataRole.UserRole + 1, new_template['id'])
            self.template_list.setItem(row, 0, item)
            
            # 选中新模板
            self.template_list.selectRow(row)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"复制模板时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

    def delete_template(self):
        """删除模板"""
        if not self.current_template_id:
            return

        template_name = self.template_name_input.text()

        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除模板 '{template_name}' 吗？此操作不可恢复。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # 删除模板
        success, message = self.template_manager.delete_template(self.current_template_id)

        if success:
            QMessageBox.information(self, "删除成功", message)

            # 刷新模板列表
            self.load_templates()

            # 清空详情区域
            self.template_name_input.clear()
            self.point_table.setRowCount(0)
            self.current_template_id = None

            # 禁用按钮
            self.copy_template_btn.setEnabled(False)
            self.delete_template_btn.setEnabled(False)
            self.export_template_btn.setEnabled(False)
            self.add_point_btn.setEnabled(False)
            self.edit_point_btn.setEnabled(False)
            self.delete_point_btn.setEnabled(False)
            self.save_template_btn.setEnabled(False)
        else:
            QMessageBox.warning(self, "删除失败", message)

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
        if not self.current_template_id or not self.template_modified:
            return

        # 获取表单数据
        name = self.template_name_input.text().strip()

        if not name:
            QMessageBox.warning(self, "输入错误", "模板名称不能为空")
            return

        # 收集点位数据
        points = []
        for row in range(self.point_table.rowCount()):
            points.append({
                '变量名后缀': self.point_table.item(row, 0).text(),
                '描述后缀': self.point_table.item(row, 1).text(),
                '类型': self.point_table.item(row, 2).text()
            })

        if not points:
            QMessageBox.warning(self, "输入错误", "模板必须至少包含一个点位")
            return

        # 构建更新数据
        template_data = {
            'name': name,
            '标识符': name,  # 使用名称作为标识符
            '变量前缀': "",  # 默认空前缀
            '点位': points
        }

        # 更新模板
        try:
            success = self.template_manager.update_template(self.current_template_id, template_data)

            if success:
                QMessageBox.information(self, "保存成功", "模板更新成功")

                # 刷新模板列表
                self.load_templates()

                # 重置修改标记
                self.template_modified = False
            else:
                QMessageBox.warning(self, "保存失败", "无法更新模板")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"更新模板时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

    def export_template(self):
        """导出模板到Excel"""
        if not self.current_template_id:
            return
            
        try:
            # 获取当前模板
            template = self.template_manager.get_template_by_id(self.current_template_id)
            if not template:
                QMessageBox.warning(self, "错误", "获取模板信息失败")
                return
                
            # 选择保存路径
            from PySide6.QtWidgets import QFileDialog
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出模板",
                f"{template['name']}.xlsx",
                "Excel Files (*.xlsx)"
            )
            
            if not file_path:
                return
                
            # 创建Excel工作簿
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = template['name']
            
            # 添加模板基本信息
            ws.append(["模板名称", template['name']])
            ws.append(["标识符", template.get('标识符', '')])
            ws.append(["变量前缀", template.get('变量前缀', '')])
            ws.append([])  # 空行
            
            # 添加点位表头
            ws.append(["变量名后缀", "描述后缀", "数据类型"])
            
            # 添加点位数据
            for point in template.get('点位', []):
                ws.append([
                    point.get('变量名后缀', ''),
                    point.get('描述后缀', ''),
                    point.get('类型', '')
                ])
                
            # 调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column_letter].width = adjusted_width
                
            # 保存文件
            wb.save(file_path)
            QMessageBox.information(self, "导出成功", f"模板已导出到：{file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出模板时发生错误：{str(e)}")
            import traceback
            traceback.print_exc()

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
