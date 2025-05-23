# -*- coding: utf-8 -*-
"""
PLC配置组件包

包含PLC硬件配置相关的所有组件：
- 模型定义 (models.py)
- 增强版穿梭框 (enhanced_transfer_widget.py)
- 机架显示组件 (rack_widget.py)
- 配置主组件 (plc_config_widget.py)
- 适配器组件 (plc_config_adapter.py)
"""

from .models import PLCModule, TransferItem, TransferDirection, TransferListState
from .enhanced_transfer_widget import EnhancedTransferWidget
from .rack_widget import RackDisplayWidget, SlotWidget
from .plc_config_widget import PLCConfigWidget
from .plc_config_adapter import PLCConfigAdapter

__all__ = [
    'PLCModule',
    'TransferItem', 
    'TransferDirection',
    'TransferListState',
    'EnhancedTransferWidget',
    'RackDisplayWidget',
    'SlotWidget',
    'PLCConfigWidget',
    'PLCConfigAdapter'
]

__version__ = "1.0.0" 