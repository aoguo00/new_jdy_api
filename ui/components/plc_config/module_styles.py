# -*- coding: utf-8 -*-
"""
PLC模块样式配置

定义不同类型模块的颜色、图标和显示样式
"""

from typing import Dict, Tuple

# 模块类型颜色配置 - 使用更柔和的颜色
MODULE_TYPE_COLORS: Dict[str, str] = {
    # 输入模块 - 蓝色系
    'AI': '#4A90E2',      # 模拟输入 - 明亮蓝
    'DI': '#5DADE2',      # 数字输入 - 天蓝
    
    # 输出模块 - 绿色系  
    'AO': '#52C41A',      # 模拟输出 - 鲜绿
    'DO': '#73D13D',      # 数字输出 - 亮绿
    
    # 混合模块 - 紫色系
    'AI/AO': '#9B59B6',   # 模拟混合 - 紫色
    'DI/DO': '#BB8FCE',   # 数字混合 - 淡紫
    
    # 控制模块 - 橙色系
    'CPU': '#FA8C16',     # CPU - 亮橙
    'RACK': '#FFA940',    # 机架 - 淡橙
    
    # 通讯模块 - 青色系
    'COM': '#13C2C2',     # 通讯 - 青色
    'DP': '#36CFC9',      # DP总线 - 淡青
    
    # 默认
    '未知': '#8C8C8C'      # 灰色
}

# 模块图标配置 - 使用更专业的Unicode图标
MODULE_TYPE_ICONS: Dict[str, str] = {
    # 输入模块
    'AI': '📊',  # 或 '⊳' 模拟信号波形
    'DI': '📥',  # 或 '▣' 数字信号
    
    # 输出模块
    'AO': '📈',  # 或 '⊲' 模拟输出
    'DO': '📤',  # 或 '▢' 数字输出
    
    # 混合模块
    'AI/AO': '🔄',  # 双向箭头
    'DI/DO': '⇄',   # 双向传输
    
    # 控制模块
    'CPU': '💻',     # 或 '▦' CPU
    'RACK': '🗄️',   # 机架
    
    # 通讯模块
    'COM': '🔗',     # 通讯链接
    'DP': '🌐',      # 网络
    
    # 特殊模块
    'POWER': '⚡',    # 电源
    '未知': '❓'       # 未知
}

# 专业的ASCII图标（备选方案）
MODULE_ASCII_ICONS: Dict[str, str] = {
    'AI': '[AI]',
    'DI': '[DI]',
    'AO': '[AO]',
    'DO': '[DO]',
    'AI/AO': '[A↔]',
    'DI/DO': '[D↔]',
    'CPU': '[CPU]',
    'COM': '[COM]',
    'DP': '[DP]',
    'RACK': '[RK]',
    '未知': '[?]'
}

# 模块背景颜色（更淡的版本，用于机架显示）
MODULE_BG_COLORS: Dict[str, str] = {
    # 输入模块 - 淡蓝色系
    'AI': '#E6F3FF',      
    'DI': '#E8F4FD',      
    
    # 输出模块 - 淡绿色系  
    'AO': '#F0FFF0',      
    'DO': '#F0FFF4',      
    
    # 混合模块 - 淡紫色系
    'AI/AO': '#FAF0FF',   
    'DI/DO': '#FCF4FF',   
    
    # 控制模块 - 淡橙色系
    'CPU': '#FFF7E6',     
    'RACK': '#FFFBE6',    
    
    # 通讯模块 - 淡青色系
    'COM': '#E6FFFB',     
    'DP': '#E6FFFA',      
    
    # 默认
    '未知': '#F5F5F5'      
}

def get_module_color(module_type: str, is_background: bool = False) -> str:
    """
    获取模块颜色
    
    Args:
        module_type: 模块类型
        is_background: 是否返回背景色
        
    Returns:
        颜色代码
    """
    if is_background:
        return MODULE_BG_COLORS.get(module_type.upper(), MODULE_BG_COLORS['未知'])
    else:
        return MODULE_TYPE_COLORS.get(module_type.upper(), MODULE_TYPE_COLORS['未知'])

def get_module_icon(module_type: str, use_ascii: bool = False) -> str:
    """
    获取模块图标
    
    Args:
        module_type: 模块类型
        use_ascii: 是否使用ASCII图标
        
    Returns:
        图标字符
    """
    if use_ascii:
        return MODULE_ASCII_ICONS.get(module_type.upper(), MODULE_ASCII_ICONS['未知'])
    else:
        return MODULE_TYPE_ICONS.get(module_type.upper(), MODULE_TYPE_ICONS['未知'])

def get_module_style(module_type: str, for_rack: bool = False) -> Dict[str, str]:
    """
    获取模块的完整样式
    
    Args:
        module_type: 模块类型
        for_rack: 是否用于机架显示
        
    Returns:
        样式字典
    """
    bg_color = get_module_color(module_type, is_background=True)
    border_color = get_module_color(module_type, is_background=False)
    
    if for_rack:
        # 机架显示样式 - 更柔和
        return {
            'background-color': bg_color,
            'border': f'2px solid {border_color}',
            'color': '#262626',  # 深灰色文字
            'font-weight': 'bold'
        }
    else:
        # 穿梭框样式 - 更清晰
        return {
            'background-color': '#FFFFFF',
            'border': f'1px solid {border_color}',
            'border-left': f'4px solid {border_color}',
            'color': '#262626'
        }

def format_module_display(model: str, module_type: str, channels: int = 0) -> str:
    """
    格式化模块显示文本
    
    Args:
        model: 模块型号
        module_type: 模块类型
        channels: 通道数
        
    Returns:
        格式化的显示文本
    """
    icon = get_module_icon(module_type)
    
    # 基础格式：图标 型号 [类型]
    text = f"{icon} {model} [{module_type}]"
    
    # 如果有通道数，添加通道信息
    if channels > 0:
        text += f" ({channels}CH)"
    
    return text 