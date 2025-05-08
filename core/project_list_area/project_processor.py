# core/project_list_area/project_processor.py
"""处理从API获取的项目列表数据，为UI准备数据"""

from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def format_project_data_for_ui(api_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """将API返回的项目数据列表格式化为ProjectListArea需要的格式。
    
    当前实现比较简单，直接返回API数据。
    未来可以扩展，例如：
    - 字段重命名以匹配表格列名。
    - 数据类型转换。
    - 添加/计算额外的列。
    - 排序或过滤。
    """
    if not isinstance(api_data, list):
        logger.warning(f"format_project_data_for_ui 接收到的数据不是列表: {type(api_data)}")
        return []
        
    # 目前直接返回原始数据，因为UI组件似乎直接使用API返回的字段
    # 如果UI需要不同格式，在这里进行转换
    processed_data = api_data
    return processed_data 