"""设备列表区域组件"""
from PySide6.QtWidgets import (QGroupBox, QVBoxLayout, QTableWidget,
                             QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Signal
import logging # 新增：导入logging

logger = logging.getLogger(__name__) # 新增：获取logger实例

class DeviceListArea(QGroupBox):
    """设备清单区域"""
    # 信号定义
    device_selected = Signal(str, int)  # 设备名称, 设备数量
    update_finished = Signal(int)  # 更新完成信号，参数为更新数量
    update_failed = Signal(str)  # 更新失败信号，参数为错误信息

    def __init__(self, parent=None):
        super().__init__("设备清单", parent)
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """设置设备清单区域UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(7)
        self.device_table.setHorizontalHeaderLabels(
            ["设备名称", "品牌", "规格型号", "技术参数", "数量", "单位", "技术参数(外部)"])

        # 设置列宽和自适应
        header = self.device_table.horizontalHeader()
        header.setStretchLastSection(False)
        column_ratios = [2, 1, 1.5, 2, 0.8, 0.7, 2]
        total_ratio = sum(column_ratios)
        for i, ratio in enumerate(column_ratios):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            self.device_table.setColumnWidth(i, int(780 * ratio / total_ratio))

        layout.addWidget(self.device_table)
        self.setLayout(layout)

    def setup_connections(self):
        """设置信号连接"""
        # 连接自定义信号
        self.update_finished.connect(self._on_update_finished)
        self.update_failed.connect(self._on_update_failed)

    def _on_update_finished(self, count: int):
        """处理更新完成"""
        QMessageBox.information(self, "更新完成", f"共更新 {count} 个设备")

    def _on_update_failed(self, error: str):
        """处理更新失败"""
        QMessageBox.critical(self, "错误", f"更新设备列表失败: {error}")

    def update_device_list(self, devices):
        """更新设备列表"""
        try:
            # 更新表格数据
            self.device_table.setRowCount(0)
            logger.info(f"[DeviceListArea] update_device_list CALLED with {len(devices) if devices else 0} devices.") # 修改日志，处理devices为None的情况
            if not devices: # 如果传入的devices是None或空列表，则不进行后续操作
                self.update_finished.emit(0)
                return

            for i, device_info in enumerate(devices):
                model_no = device_info.get('_widget_1635777115287', '')
                qty = device_info.get('_widget_1635777485580', '')
                # 筛选我们关心的模块进行日志记录
                if 'LK117' in model_no.upper():
                    logger.info(f"[DeviceListArea] Populating UI Table row {i+1}: Model={model_no}, Qty={qty}")
                elif 'LK610S' in model_no.upper():
                    logger.info(f"[DeviceListArea] Populating UI Table row {i+1}: Model={model_no}, Qty={qty}")

                row = self.device_table.rowCount()
                self.device_table.insertRow(row)
                self.device_table.setItem(row, 0, QTableWidgetItem(str(device_info.get('_widget_1635777115211', ''))))
                self.device_table.setItem(row, 1, QTableWidgetItem(str(device_info.get('_widget_1635777115248', ''))))
                self.device_table.setItem(row, 2, QTableWidgetItem(str(device_info.get('_widget_1635777115287', ''))))
                self.device_table.setItem(row, 3, QTableWidgetItem(str(device_info.get('_widget_1641439264111', ''))))
                self.device_table.setItem(row, 4, QTableWidgetItem(str(device_info.get('_widget_1635777485580', ''))))
                self.device_table.setItem(row, 5, QTableWidgetItem(str(device_info.get('_widget_1654703913698', ''))))
                self.device_table.setItem(row, 6, QTableWidgetItem(str(device_info.get('_widget_1641439463480', ''))))
            
            # 发出更新完成信号
            self.update_finished.emit(len(devices))
            
        except Exception as e:
            # 发出更新失败信号
            self.update_failed.emit(str(e))

    def clear_table(self):
        """清空表格"""
        self.device_table.setRowCount(0) 