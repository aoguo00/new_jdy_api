"""处理从API获取的设备列表数据，为UI准备数据"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_device_data_for_ui(api_data: List[Dict[str, Any]], site_name: str) -> List[Dict[str, Any]]:
    """将API返回的场站设备数据列表格式化为DeviceListArea需要的格式。
    
    主要逻辑是提取嵌套在特定字段下的设备列表。
    """
    all_devices = []
    if not isinstance(api_data, list):
        logger.warning(f"format_device_data_for_ui 接收到的场站 '{site_name}' 数据不是列表: {type(api_data)}")
        return []

    for data_item in api_data:
        if not isinstance(data_item, dict):
            logger.warning(f"format_device_data_for_ui: 场站 '{site_name}' 的数据项不是字典: {type(data_item)}")
            continue
            
        # 提取嵌套的设备列表，字段名根据 MainWindow 中的逻辑
        device_list = data_item.get('_widget_1635777115095', []) 
        
        if device_list and isinstance(device_list, list):
            # 进一步检查列表中的项目是否是字典 (设备信息)
            for device_info in device_list:
                if isinstance(device_info, dict):
                    all_devices.append(device_info)
                else:
                    logger.warning(f"场站 '{site_name}' 设备列表中的项不是字典: {type(device_info)}")
        elif device_list: # 如果字段存在但不是列表
            logger.warning(f"场站 '{site_name}' 的设备列表字段 '_widget_1635777115095' 不是列表: {type(device_list)}")
            
    return all_devices 