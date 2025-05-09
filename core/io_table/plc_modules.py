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

# 和利时LE系列功能扩展板定义
HOLLYSYS_LE_MODULES = [
    {
        "model": "LE5118",
        "type": "CPU",
        "channels": 40, # 总IO点数
        "description": "LE系列CPU模块, DC24V供电, 自带40点I/O (DI24, DO16晶体管)",
        "sub_channels": {"DI": 24, "DO": 16}, # 自带IO的详细分布
        "power_supply": "DC24V"
    },
    {
        "model": "LE5600",
        "type": "COM",
        "channels": 0,
        "description": "RS232通讯扩展板"
    },
    {
        "model": "LE5601",
        "type": "COM",
        "channels": 0,
        "description": "RS485通讯扩展板"
    },
    {
        "model": "LE5610",
        "type": "DI",
        "channels": 4,
        "description": "4通道数字量输入扩展板"
    },
    {
        "model": "LE5620",
        "type": "DO",
        "channels": 4,
        "description": "4通道数字量输出扩展板"
    },
    {
        "model": "LE5611",
        "type": "AI",
        "channels": 2,
        "description": "2通道模拟量输入扩展板"
    },
    {
        "model": "LE5621",
        "type": "AO",
        "channels": 1,
        "description": "1通道模拟量输出扩展板"
    },
    {
        "model": "LE5210",
        "type": "DI",
        "channels": 8,
        "description": "8通道数字量输入模块"
    },
    {
        "model": "LE5211",
        "type": "DI",
        "channels": 16,
        "description": "16通道数字量输入模块"
    },
    {
        "model": "LE5212",
        "type": "DI",
        "channels": 32,
        "description": "32通道数字量输入模块"
    },
    {
        "model": "LE5220",
        "type": "DO",
        "channels": 8,
        "description": "8通道数字量输出模块"
    },
    {
        "model": "LE5221",
        "type": "DO",
        "channels": 8,
        "description": "8通道数字量输出模块"
    },
    {
        "model": "LE5223",
        "type": "DO",
        "channels": 16,
        "description": "16通道数字量输出模块"
    },
    {
        "model": "LE5224",
        "type": "DO",
        "channels": 32,
        "description": "32通道数字量输出模块"
    },
    {
        "model": "LE5230",
        "type": "DI/DO",
        "channels": 16,
        "description": "8通道数字量输入/8通道数字量输出模块",
        "sub_channels": {"DI": 8, "DO": 8}
    },
    {
        "model": "LE5231",
        "type": "DI/DO",
        "channels": 16,
        "description": "8通道数字量输入/8通道数字量输出模块",
        "sub_channels": {"DI": 8, "DO": 8}
    },
    {
        "model": "LE5310",
        "type": "AI",
        "channels": 4,
        "description": "4通道模拟量输入模块"
    },
    {
        "model": "LE5311",
        "type": "AI",
        "channels": 8,
        "description": "8通道模拟量输入模块"
    },
    {
        "model": "LE5340",
        "type": "AI",
        "channels": 4,
        "description": "4通道热电偶输入模块"
    },
    {
        "model": "LE5341",
        "type": "AI",
        "channels": 4,
        "description": "4通道热电阻输入模块"
    },
    {
        "model": "LE5341T",
        "type": "AI",
        "channels": 4,
        "description": "4通道热电阻输入模块 (T型)"
    },
    {
        "model": "LE5342",
        "type": "AI",
        "channels": 8,
        "description": "8通道热敏电阻输入模块"
    },
    {
        "model": "LE5320",
        "type": "AO",
        "channels": 2,
        "description": "2通道模拟量输出模块"
    },
    {
        "model": "LE5321",
        "type": "AO",
        "channels": 4,
        "description": "4通道模拟量输出模块"
    },
    {
        "model": "LE5330",
        "type": "AI/AO",
        "channels": 6,
        "description": "4通道模拟量输入/2通道模拟量输出模块",
        "sub_channels": {"AI": 4, "AO": 2}
    },
    {
        "model": "LE5400",
        "type": "COM",
        "channels": 0,
        "description": "串口扩展模块"
    },
    {
        "model": "LE5401",
        "type": "COM",
        "channels": 0,
        "description": "PROFIBUS-DP 从站通讯模块"
    },
    {
        "model": "LE5403",
        "type": "COM",
        "channels": 0,
        "description": "以太网通讯模块"
    },
    {
        "model": "LE5404",
        "type": "COM",
        "channels": 0,
        "description": "GPRS 通讯模块"
    }
]

# 模块类型映射，用于通过型号前缀判断模块类型
MODULE_TYPE_PREFIXES = {
    "CPU": ["LE5118"],
    "AI": ["LK41", "LE5611", "LE531", "LE534"],
    "AO": ["LK51", "LE5621", "LE532"],
    "AI/AO": ["LE533"],
    "DI": ["LK61", "LE5610", "LE521"],
    "DO": ["LK71", "LE5620", "LE522"],
    "DI/DO": ["LE523"],
    "DP": ["LK81", "LK82", "PROFIBUS-DP"], # PROFIBUS-DP 作为通用DP主站型号
    "COM": ["LK238", "LE5600", "LE5601", "LE540", "LE5401", "LE5403", "LE5404"],
    "RACK": ["LK117"]
}

# 模块系列定义
PLC_SERIES = {
    "LK": {
        "name": "和利时LK系列",
        "prefixes": ["LK"],
        "modules": HOLLYSYS_LK_MODULES
    },
    "LE": {
        "name": "和利时LE系列", # 名称统一
        "prefixes": ["LE"], 
        "modules": HOLLYSYS_LE_MODULES
    }
}

# 模块类型对应的默认通道数
MODULE_TYPE_CHANNELS = {
    "CPU": 0,
    "AI": 8,
    "AO": 4,
    "DI": 16,
    "DO": 16,
    "DI/DO": 16,
    "AI/AO": 6,
    "DP": 0,
    "COM": 0,
    "RACK": 0,
}

# 模块类型描述
MODULE_TYPE_DESCRIPTIONS = {
    "CPU": "中央处理单元",
    "AI": "模拟量输入",
    "AO": "模拟量输出",
    "DI": "数字量输入",
    "DO": "数字量输出",
    "DI/DO": "数字量输入/输出",
    "AI/AO": "模拟量输入/输出",
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
        Dict: 包含模块信息的字典，如果未找到则返回包含推断信息的字典
    """
    model_upper = model.upper()
    
    # 优先在预定义模块中查找 (覆盖LK和LE系列)
    for series_info in PLC_SERIES.values():
        for module in series_info["modules"]:
            if module["model"].upper() == model_upper:
                return module # 如果直接匹配到型号，返回完整信息
    
    # 如果没直接找到型号，通过型号前缀判断系列和类型
    module_type = "未录入"
    channels = 0 # 重置channels
    description = f"未知模块 ({model})"
    sub_channels = None
    matched_series_name = None

    for series_key, series_info in PLC_SERIES.items():
        if any(model_upper.startswith(prefix) for prefix in series_info["prefixes"]):
            matched_series_name = series_info["name"]
            # 匹配到系列后，再根据模块类型前缀确定具体类型
            for type_name, type_prefixes in MODULE_TYPE_PREFIXES.items():
                if any(model_upper.startswith(tp) for tp in type_prefixes):
                    # 确保此前缀确实是当前检测系列的一部分或通用（不属于其他特定系列）
                    is_prefix_for_this_series = any(tp.startswith(p) for p in series_info["prefixes"])
                    is_general_prefix = not any(
                        s_info["name"] != matched_series_name and any(tp.startswith(p_other) for p_other in s_info["prefixes"])
                        for _, s_info in PLC_SERIES.items()
                    )
                    if is_prefix_for_this_series or is_general_prefix:
                        module_type = type_name
                        break # 找到类型就跳出类型前缀循环
            if module_type != "未录入":
                break # 找到系列且确定类型就跳出系列循环

    # 如果通过系列前缀未能确定类型，则再次遍历 MODULE_TYPE_PREFIXES 进行通用匹配
    if module_type == "未录入":
        for type_name, prefixes in MODULE_TYPE_PREFIXES.items():
            if any(model_upper.startswith(prefix) for prefix in prefixes):
                module_type = type_name
                break

    # 根据确定的类型获取默认通道数和描述
    if module_type != "未录入":
        description_base = MODULE_TYPE_DESCRIPTIONS.get(module_type, "未知模块")
        description = f"{description_base} ({model})"
        if module_type in MODULE_TYPE_CHANNELS:
            channels = MODULE_TYPE_CHANNELS[module_type]
        if module_type == "DI/DO": # 特殊处理DI/DO的子通道信息
            # 这是一个通用推断，实际DI/DO模块应在其定义中明确sub_channels
            # 若无精确匹配，这里可以尝试根据型号数字部分猜测，或默认为空
            pass # 暂时不为未定义DI/DO模块推断sub_channels
    
    if matched_series_name and module_type == "未录入":
        description = f"{matched_series_name} - {description}"

    # 构建返回字典
    result = {
        "model": model,
        "type": module_type,
        "channels": channels, 
        "description": description,
        "is_master": module_type == "DP",
        "slot_required": 1 if module_type == "DP" else None
    }
    if sub_channels: # 只有当sub_channels被赋值时才添加
        result["sub_channels"] = sub_channels
        
    return result

# 获取所有预定义模块
def get_all_modules() -> List[Dict[str, Any]]:
    """
    获取所有预定义的PLC模块
    
    Returns:
        List[Dict]: 包含所有模块信息的列表
    """
    all_modules_list = []
    for series_info in PLC_SERIES.values():
        all_modules_list.extend(series_info["modules"])
    return all_modules_list.copy() # 返回副本以防止外部修改

# 根据类型获取模块
def get_modules_by_type(module_type_filter: str, use_predefined: bool = False) -> List[Dict[str, Any]]:
    """
    根据类型获取模块
    
    Args:
        module_type_filter: 模块类型 (AI, AO, DI, DO, DP, COM 或 "全部")
        use_predefined: 是否强制使用预定义模块列表，默认为False (此参数在此函数中实际不起作用，因为总是基于预定义列表)
        
    Returns:
        List[Dict]: 指定类型的模块列表。如果module_type_filter为 "全部", 则返回所有模块。
    """
    # use_predefined 在此函数内没有实际的条件分支，因为总是从预定义模块获取
    # 但保留参数以维持接口一致性
    
    all_defined_modules = get_all_modules() # 获取所有已定义的模块

    if module_type_filter == "全部":
        return all_defined_modules
    
    return [module for module in all_defined_modules if module["type"] == module_type_filter] 