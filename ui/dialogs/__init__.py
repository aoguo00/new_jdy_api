"""对话框模块，包含所有对话框UI组件"""

from .device_point_dialog import DevicePointDialog
from .plc_config_dialog import PLCConfigDialog
from .module_manager_dialog import ModuleManagerDialog
from .template_manage_dialog import TemplateManageDialog

__all__ = [
    'DevicePointDialog',
    'PLCConfigDialog',
    'ModuleManagerDialog',
    'TemplateManageDialog'
]
