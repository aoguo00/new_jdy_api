"""对话框模块，包含所有对话框UI组件"""

# from .add_device_dialog import AddDeviceDialog # 移除此行
from .device_point_dialog import DevicePointDialog
from .error_display_dialog import ErrorDisplayDialog
from .plc_config_dialog import PLCConfigEmbeddedWidget
# 移除对模块管理对话框的导入
# from .module_manager_dialog import ModuleManagerDialog
from .template_manage_dialog import TemplateManageDialog

__all__ = [
    'DevicePointDialog',
    'PLCConfigEmbeddedWidget',
    # 'ModuleManagerDialog', # 移除模块管理对话框
    'TemplateManageDialog'
]
