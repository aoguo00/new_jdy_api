"""设备管理模块，处理设备相关的业务逻辑"""

from core.third_device.device_model import ThirdPartyDeviceManager

class DeviceManager:
    """设备管理类，负责设备相关的业务逻辑"""

    def __init__(self):
        """初始化设备管理器"""
        # 创建第三方设备管理器实例
        self.third_party_manager = ThirdPartyDeviceManager()

    def get_device_points(self):
        """获取设备点位列表"""
        return self.third_party_manager.get_device_points()

    def set_device_points(self, points):
        """设置设备点位列表（替换现有点位）"""
        self.third_party_manager.set_device_points(points)

    def add_device_points(self, points):
        """添加设备点位（追加到现有点位）"""
        self.third_party_manager.add_device_points(points)

    def clear_device_points(self):
        """清空设备点位列表"""
        self.third_party_manager.clear_device_points()

    def update_third_party_table_data(self):
        """获取第三方设备表格数据"""
        return self.third_party_manager.update_third_party_table_data()

    def export_to_excel(self, file_path):
        """导出点表为Excel格式"""
        self.third_party_manager.export_to_excel(file_path)
