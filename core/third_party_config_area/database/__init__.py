# core/third_party_config_area/database/__init__.py

from .sql import TEMPLATE_SQL, CONFIGURED_DEVICE_SQL
from .dao import TemplateDAO, ConfiguredDeviceDAO

__all__ = [
    "TEMPLATE_SQL",
    "CONFIGURED_DEVICE_SQL",
    "TemplateDAO",
    "ConfiguredDeviceDAO"
] 