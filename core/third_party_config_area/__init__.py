# core/third_party_config_area/__init__.py 

# 导出服务
from .template_service import TemplateService
from .config_service import ConfigService

# 也可以选择性地导出模型或数据库相关类，如果外部需要直接访问的话
# from .models import DeviceTemplateModel, ConfiguredDevicePointModel
# from .database import TemplateDAO, ConfiguredDeviceDAO

__all__ = [
    "TemplateService",
    "ConfigService"
    # 添加其他需要导出的类名
] 