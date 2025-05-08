# core/third_party_config_area/models/__init__.py

from .template_models import DeviceTemplateModel, TemplatePointModel
from .configured_device_models import ConfiguredDevicePointModel

__all__ = [
    "DeviceTemplateModel",
    "TemplatePointModel",
    "ConfiguredDevicePointModel"
] 