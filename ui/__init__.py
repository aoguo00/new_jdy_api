"""UI模块，包含所有界面相关组件"""

from .main_window import MainWindow
from .components.query_area import QueryArea
from .components.project_list_area import ProjectListArea
from .components.device_list_area import DeviceListArea
from .components.third_party_device_area import ThirdPartyDeviceArea
from .dialogs.device_point_dialog import DevicePointDialog
from .dialogs.plc_config_dialog import PLCConfigEmbeddedWidget

__all__ = [
    'MainWindow',
    'QueryArea',
    'ProjectListArea',
    'DeviceListArea',
    'ThirdPartyDeviceArea',
    'DevicePointDialog',
    'PLCConfigEmbeddedWidget',
]
