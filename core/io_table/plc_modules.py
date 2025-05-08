"""
PLC模块定义文件
包含常用PLC模块的型号、类型、通道数和描述信息
"""

from typing import Dict, List, Any

# 和利时LK系列模块定义
HOLLYSYS_LK_MODULES = [
    {
        "model": "LK410",
        "type": "AI",
        "channels": 8,
        "description": "8通道电压型模拟量输入模块"
    },
    {
        "model": "LK411",
        "type": "AI",
        "channels": 8,
        "description": "8通道电流型模拟量输入模块"
    },
    {
        "model": "LK412",
        "type": "AI",
        "channels": 6,
        "description": "6通道隔离模拟量输入模块"
    },
    {
        "model": "LK510",
        "type": "AO",
        "channels": 4,
        "description": "4通道通道间隔离电压型模拟量输出模块"
    },
    {
        "model": "LK511",
        "type": "AO",
        "channels": 4,
        "description": "4通道通道间隔离电流型模拟量输出模块"
    },
    {
        "model": "LK512",
        "type": "AO",
        "channels": 8,
        "description": "8通道电压电流型模拟量输出模块"
    },
    {
        "model": "LK610",
        "type": "DI",
        "channels": 16,
        "description": "16通道24VDC混型数字量输入模块"
    },
    {
        "model": "LK616",
        "type": "DI",
        "channels": 32,
        "description": "32通道24VDC混型数字量输入模块"
    },
    {
        "model": "LK710",
        "type": "DO",
        "channels": 16,
        "description": "16通道10~30VDC源型数字量输出模块"
    },
    {
        "model": "LK716",
        "type": "DO",
        "channels": 32,
        "description": "32通道24VDC晶体管型数字量输出模块"
    },
    {
        "model": "LK720",
        "type": "DO",
        "channels": 8,
        "description": "8通道10~265VAC/5~125VDC常开继电器输出模块"
    },
    {
        "model": "PROFIBUS-DP",
        "type": "DP",
        "channels": 0,
        "description": "PROFIBUS-DP通讯接口模块",
        "is_master": True,
        "slot_required": 1  # 必须放在第1槽
    },
    {
        "model": "LK238",
        "type": "COM",
        "channels": 0,
        "description": "通讯模块"
    },
    {
        "model": "LK117",
        "type": "RACK",
        "channels": 0,
        "description": "11槽扩展背板",
        "slots": 11  # 可容纳11个模块（含1个DP模块）
    }
]

# 模块类型映射，用于通过型号前缀判断模块类型
MODULE_TYPE_PREFIXES = {
    "AI": ["LK41"],
    "AO": ["LK51"],
    "DI": ["LK61"],
    "DO": ["LK71"],
    "DP": ["LK81", "LK82"],
    "COM": ["LK238"],  # 通讯模块
    "RACK": ["LK117"]  # 扩展背板
}

# 模块类型对应的默认通道数
MODULE_TYPE_CHANNELS = {
    "AI": 8,   # 模拟量输入一般为8通道
    "AO": 4,   # 模拟量输出一般为4通道
    "DI": 16,  # 数字量输入一般为16通道
    "DO": 16,  # 数字量输出一般为16通道
    "DP": 0,   # PROFIBUS-DP通讯接口模块
    "COM": 0,  # 通讯模块
    "RACK": 0  # 扩展背板
}

# 模块类型描述
MODULE_TYPE_DESCRIPTIONS = {
    "AI": "模拟量输入",
    "AO": "模拟量输出",
    "DI": "数字量输入",
    "DO": "数字量输出",
    "DP": "PROFIBUS-DP通讯接口",
    "COM": "通讯模块",
    "RACK": "扩展背板",
    "未录入": "未录入模块"
}

# 通过型号查找模块信息
def get_module_info_by_model(model: str) -> Dict[str, Any]:
    """
    通过型号查找模块信息
    
    Args:
        model: 模块型号
        
    Returns:
        Dict: 包含模块信息的字典，如果未找到则返回空字典
    """
    # 首先在预定义模块中查找
    model_upper = model.upper()
    for module in HOLLYSYS_LK_MODULES:
        if module["model"].upper() == model_upper:
            return module
    
    # 如果没找到，通过型号前缀判断类型
    module_type = "未录入"
    for type_name, prefixes in MODULE_TYPE_PREFIXES.items():
        if any(model_upper.startswith(prefix) for prefix in prefixes):
            module_type = type_name
            break
            
    # 特殊处理LK238
    if model_upper == "LK238":
        module_type = "COM"
    
    # 确定通道数 - 从类型对应的默认通道数获取，避免估计
    channels = 0  # 未知类型默认为0通道
    if module_type in MODULE_TYPE_CHANNELS:
        channels = MODULE_TYPE_CHANNELS[module_type]
    
    # 返回模块信息
    description = MODULE_TYPE_DESCRIPTIONS.get(module_type, "未知模块")
    if module_type != "未录入":
        description = f"{description} ({model})"
        
    return {
        "model": model,
        "type": module_type,
        "channels": channels,
        "description": description,
        "is_master": module_type == "DP",  # DP模块为主模块
        "slot_required": 1 if module_type == "DP" else None  # DP模块必须放在第1槽
    }

# 获取所有预定义模块
def get_all_modules() -> List[Dict[str, Any]]:
    """
    获取所有预定义的PLC模块
    
    Returns:
        List[Dict]: 包含所有模块信息的列表
    """
    return HOLLYSYS_LK_MODULES.copy()

# 根据类型获取模块
def get_modules_by_type(module_type: str) -> List[Dict[str, Any]]:
    """
    根据类型获取模块
    
    Args:
        module_type: 模块类型 (AI, AO, DI, DO, DP, CP 或 "全部")
        
    Returns:
        List[Dict]: 指定类型的模块列表
    """
    if module_type == "全部":
        return get_all_modules()
    
    return [module for module in HOLLYSYS_LK_MODULES if module["type"] == module_type] 