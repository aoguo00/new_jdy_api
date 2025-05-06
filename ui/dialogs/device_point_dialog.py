"""设备点位配置对话框"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
                               QFormLayout, QComboBox, QLineEdit, QTableWidget,
                               QTableWidgetItem, QPushButton, QHeaderView,
                               QSplitter, QWidget, QMessageBox)
from PySide6.QtCore import Qt
from core.third_device import template_db
from core.point_manager import PointManager
from ui.dialogs.template_manage_dialog import TemplateManageDialog

class DevicePointDialog(QDialog):
    """设备点位配置对话框"""

    def __init__(self, parent=None, template_name="", device_name="", device_count=1):
        super().__init__(parent)
        self.setWindowTitle("第三方设备点表配置")
        self.resize(900, 700)

        self.template_name = template_name
        # device_name和device_count参数在当前实现中未使用
        self.device_points = []
        self.current_template_id = None
        self.template = None
        self.template_modified = False
        self.configured = False
        self.point_manager = PointManager()

        # 获取主窗口已配置的设备点位
        if parent and hasattr(parent, 'device_manager'):
            self.device_points = parent.device_manager.get_device_points()

        self.setup_ui()

        # 如果有已配置的点位，加载配置
        if self.device_points:
            self.load_existing_config()

    def load_existing_config(self):
        """加载已有的配置"""
        try:
            if not self.device_points:
                return

            # 从第一个点位中提取变量名前缀
            first_point = self.device_points[0]
            var_name = first_point['变量名']
            var_parts = var_name.split('_')
            if len(var_parts) >= 2:
                prefix = var_parts[0]
                self.prefix_input.setText(prefix)

            # 根据变量名后缀找到对应的模板
            templates = template_db.get_all_templates()
            for template in templates:
                if not template.get('点位'):
                    continue

                # 检查第一个点位的变量名后缀是否匹配模板中的点位
                template_point = template['点位'][0]
                if template_point['变量名后缀'] in var_name:
                    # 找到匹配的模板，设置为当前选中
                    index = self.template_combo.findText(template['name'])
                    if index >= 0:
                        self.template_combo.setCurrentIndex(index)
                        break

            # 更新预览表格
            self.update_preview()

        except Exception as e:
            print(f"加载已有配置时发生错误: {e}")
            import traceback
            traceback.print_exc()

    def setup_ui(self):
        """设置UI界面"""
        layout = QVBoxLayout(self)

        # 设备信息区域
        info_group = QGroupBox("第三方设备信息")
        info_layout = QFormLayout()

        # 模板选择
        self.template_combo = QComboBox()
        self.load_templates()
        if self.template_name:
            index = self.template_combo.findText(self.template_name)
            if index >= 0:
                self.template_combo.setCurrentIndex(index)
        self.template_combo.currentIndexChanged.connect(self.template_changed)
        info_layout.addRow("设备模板:", self.template_combo)

        # 变量名输入
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("请输入变量名")
        self.prefix_input.textChanged.connect(self.update_preview)
        info_layout.addRow("变量名:", self.prefix_input)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # 拆分为上下两部分
        splitter = QSplitter(Qt.Orientation.Vertical)

        # 配置区域 (上部分)
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)

        config_group = QGroupBox("点位配置")
        points_layout = QVBoxLayout()

        self.point_table = QTableWidget()
        self.point_table.setColumnCount(3)
        self.point_table.setHorizontalHeaderLabels([
            "变量名后缀", "描述后缀", "类型"
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
        template_manage_btn.clicked.connect(self.manage_templates)
        template_btn_layout.addStretch()
        template_btn_layout.addWidget(template_manage_btn)
        config_layout.addLayout(template_btn_layout)

        splitter.addWidget(config_widget)

        # 预览区域 (下部分)
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_group = QGroupBox("点表预览")
        preview_table_layout = QVBoxLayout()

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels([
            "变量名", "描述", "数据类型"
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
        splitter.setSizes([350, 350])
        layout.addWidget(splitter)

        # 按钮区域
        buttons_layout = QHBoxLayout()

        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self.save_config)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addWidget(self.cancel_btn)

        layout.addLayout(buttons_layout)

        # 加载初始模板
        if self.template_combo.count() > 0:
            self.template_changed()

    def load_templates(self):
        """加载模板列表"""
        self.template_combo.clear()
        templates = template_db.get_all_templates()
        for template in templates:
            self.template_combo.addItem(template['name'], template['id'])

    def manage_templates(self):
        """打开模板管理对话框"""
        dialog = TemplateManageDialog(self)
        if dialog.exec() == QDialog.Accepted:
            # 刷新模板列表
            current_id = self.template_combo.currentData()
            self.load_templates()
            # 尝试恢复之前选中的模板
            if current_id:
                index = self.template_combo.findData(current_id)
                if index >= 0:
                    self.template_combo.setCurrentIndex(index)

    def template_changed(self):
        """模板变更处理"""
        if self.template_combo.currentIndex() < 0:
            return

        self.current_template_id = self.template_combo.currentData()
        if not self.current_template_id:
            return

        self.template = template_db.get_template_by_id(self.current_template_id)
        if not self.template:
            return

        # 填充变量前缀
        if '变量前缀' in self.template:
            self.prefix_input.setText(self.template['变量前缀'])

        # 填充点位表格
        self.point_table.setRowCount(0)
        if '点位' in self.template:
            for point in self.template['点位']:
                row = self.point_table.rowCount()
                self.point_table.insertRow(row)
                self.point_table.setItem(row, 0, QTableWidgetItem(point['变量名后缀']))
                self.point_table.setItem(row, 1, QTableWidgetItem(point['描述后缀']))
                self.point_table.setItem(row, 2, QTableWidgetItem(point['类型']))

        # 更新预览
        self.update_preview()

    def update_preview(self):
        """更新预览表格"""
        # 清空预览表格
        self.preview_table.setRowCount(0)

        var_name = self.prefix_input.text().strip()
        if not var_name:
            return

        if not self.template or '点位' not in self.template:
            return

        # 填充预览表格
        for point in self.template['点位']:
            var_suffix = point['变量名后缀']
            desc_suffix = point['描述后缀']
            data_type = point['类型']

            row = self.preview_table.rowCount()
            self.preview_table.insertRow(row)
            self.preview_table.setItem(row, 0, QTableWidgetItem(f"{var_name}_{var_suffix}"))
            self.preview_table.setItem(row, 1, QTableWidgetItem(desc_suffix))  # 只显示描述后缀，让用户之后手动修改
            self.preview_table.setItem(row, 2, QTableWidgetItem(data_type))

    def save_config(self):
        """保存配置"""
        try:
            print("开始保存配置...")
            var_name = self.prefix_input.text().strip()
            if not var_name:
                QMessageBox.warning(self, "警告", "请输入变量名")
                return

            print(f"变量名: {var_name}")
            template_name = self.template_combo.currentText()
            print(f"模板名称: {template_name}")

            if not self.template or '点位' not in self.template:
                QMessageBox.warning(self, "警告", "未选择有效的模板")
                return

            print("开始构建设备点位数据...")
            # 构建设备点位数据
            device_points = []

            # 获取预览表格中的数据
            row_count = self.preview_table.rowCount()
            print(f"预览表格行数: {row_count}")

            for row in range(row_count):
                try:
                    var_name_item = self.preview_table.item(row, 0)
                    desc_item = self.preview_table.item(row, 1)
                    data_type_item = self.preview_table.item(row, 2)

                    if not all([var_name_item, desc_item, data_type_item]):
                        print(f"警告：第 {row + 1} 行存在空单元格")
                        continue

                    # 获取变量名后缀
                    full_var_name = var_name_item.text()
                    var_parts = full_var_name.split('_')
                    if len(var_parts) >= 2:
                        var_suffix = var_parts[1]
                    else:
                        var_suffix = ""

                    point_data = {
                        '变量名': var_name_item.text(),
                        '描述': desc_item.text(),
                        '数据类型': data_type_item.text(),
                        '模板名称': template_name,  # 添加模板名称
                        '变量名后缀': var_suffix  # 添加变量名后缀
                    }
                    print(f"添加点位: {point_data}")
                    device_points.append(point_data)
                except Exception as e:
                    print(f"处理第 {row + 1} 行时发生错误: {e}")
                    continue

            if not device_points:
                QMessageBox.warning(self, "警告", "没有有效的点位数据")
                return

            print(f"成功构建 {len(device_points)} 个点位数据")

            # 保存配置
            self.device_points = device_points
            self.configured = True

            print("配置已保存，准备关闭对话框")
            QMessageBox.information(self, "成功", "设备点位配置已保存")

            # 使用accept()而不是close()
            self.accept()

        except Exception as e:
            print(f"保存配置时发生错误: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"保存配置时发生错误: {str(e)}")

    def closeEvent(self, event):
        """处理对话框关闭事件"""
        try:
            # 无条件接受关闭事件
            event.accept()
        except Exception as e:
            print(f"关闭对话框时发生错误: {e}")
            event.accept()  # 确保对话框能够关闭

    def get_device_points(self):
        """获取设备点位"""
        return self.device_points

    def is_configured(self):
        """检查是否已配置"""
        return self.configured
