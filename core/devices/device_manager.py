"""设备管理模块，处理设备相关的所有操作"""
import logging
from typing import List, Dict, Optional
from .template_manager import TemplateManager

# Updated import paths for services and models
from core.services.device_configuration_service import DeviceConfigurationService
from core.models.templates.models import DeviceTemplateModel, TemplatePointModel
from core.models.third_party_devices.models import ThirdPartyConfiguredPointModel

logger = logging.getLogger(__name__)

class DeviceManager:
    """设备管理类，现在主要作为门面，将具体逻辑委托给服务类"""

    def __init__(self):
        """初始化设备管理器"""
        # self.device_points = [] # 不再直接管理点位列表
        self.config_service = DeviceConfigurationService()
        self.template_manager = TemplateManager() # 暂时保留，看 get_template_name_by_suffix 是否仍需
        logger.info("DeviceManager 初始化完成，使用 DeviceConfigurationService")

    # def get_device_points(self) -> List[Dict]: # 旧方法，返回字典列表
    #     """获取设备点位列表 (旧版兼容，不推荐直接使用)"""
    #     # 这个方法如果还需要，应该明确其用途，以及为何不直接使用服务层方法
    #     # 暂时返回空，或者抛出 NotImplementedError
    #     logger.warning("get_device_points (List[Dict]) 已废弃，请使用服务层方法")
    #     return [] 

    def get_configured_device_points_models(self) -> List[ThirdPartyConfiguredPointModel]:
        """获取所有已配置的第三方设备点位模型列表。"""
        return self.config_service.get_all_configured_points()

    # add_device_points(self, points: List[Dict]) 已移除
    # 它被 DeviceConfigurationService.add_configured_points(template, prefix) 替代
    # 调用方 (DevicePointDialog) 需要调整

    # set_device_points(self, points: List[Dict]) 已移除
    # 点位配置通过服务层进行管理

    def clear_device_points(self) -> None:
        """清空所有已配置的设备点位。"""
        logger.info("通过 DeviceManager 请求清空所有设备点位配置")
        self.config_service.clear_all_configurations()

    def update_third_party_table_data(self) -> List[Dict]:
        """获取用于UI显示的第三方设备统计数据。"""
        logger.info("通过 DeviceManager 请求第三方设备表格数据")
        return self.config_service.get_configuration_summary()

    def get_template_name_by_suffix(self, suffix: str) -> str:
        """
        根据变量名后缀获取模板名称。
        首先在已配置的点位中查找，如果找不到，则在模板库中查找。
        """
        try:
            logger.debug(f"开始根据后缀 '{suffix}' 查找模板名称")
            # 1. 在已配置的点位中查找
            configured_points: List[ThirdPartyConfiguredPointModel] = self.config_service.get_all_configured_points()
            for point_model in configured_points:
                if point_model.var_suffix == suffix:
                    logger.debug(f"在已配置点位中找到模板 '{point_model.template_name}' 对于后缀 '{suffix}'")
                    return point_model.template_name

            # 2. 如果在已配置点位中没找到，从模板库中查找
            logger.debug(f"后缀 '{suffix}' 在已配置点位中未找到，开始搜索模板库")
            all_library_templates = self.template_manager.get_all_templates() # 返回 List[DeviceTemplateModel] (基本信息)
            
            for basic_template_model in all_library_templates:
                # 需要获取模板的完整点位信息进行匹配
                detailed_template_model = self.template_manager.get_template_by_id(basic_template_model.id)
                if detailed_template_model and detailed_template_model.points:
                    for point_detail_model in detailed_template_model.points: # points 是 List[TemplatePointModel]
                        if point_detail_model.var_suffix == suffix:
                            logger.debug(f"在模板库 '{detailed_template_model.name}' 中找到后缀 '{suffix}'")
                            return detailed_template_model.name

            logger.warning(f"后缀 '{suffix}' 未能在任何模板中找到")
            return "未知模板"

        except Exception as e:
            logger.error(f"根据后缀获取模板名称时发生错误: {e}, 后缀: {suffix}")
            return "未知模板"

    def export_to_excel(self, file_path: str) -> None:
        """将已配置的第三方设备点表导出到Excel文件。"""
        try:
            logger.info(f"通过 DeviceManager 请求导出点表到: {file_path}")
            self.config_service.export_to_excel(file_path)
            logger.info(f"点表成功导出到: {file_path}")
        except ValueError as ve:
            logger.warning(f"导出点表失败: {ve}") # 通常是"没有可导出的点位数据"
            raise # 将原始ValueError再次抛出，让调用方处理（例如弹窗提示）
        except Exception as e:
            logger.error(f"导出点表时发生严重错误: {e}")
            raise # 抛出其他异常，让调用方处理

# 移除 DeviceManager 原有的 main 测试代码 (如果有的话)

