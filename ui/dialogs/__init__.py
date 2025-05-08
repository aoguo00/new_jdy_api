"""对话框模块，包含所有对话框UI组件"""

from .device_point_dialog import DevicePointDialog
from .plc_config_dialog import PLCConfigDialog
# 移除对模块管理对话框的导入
# from .module_manager_dialog import ModuleManagerDialog
from .template_manage_dialog import TemplateManageDialog

__all__ = [
    'DevicePointDialog',
    'PLCConfigDialog',
    # 'ModuleManagerDialog', # 移除模块管理对话框
    'TemplateManageDialog'
]
