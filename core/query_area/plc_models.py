# core/query_area/plc_models.py
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

@dataclass
class PLCSeriesModel:
    """表示一个PLC产品系列 (例如 和利时LK)"""
    name: str                   # 系列名称 (例如 'LK')
    description: Optional[str] = None # 系列描述
    id: Optional[int] = None          # 数据库中的ID
    created_at: Optional[datetime] = None # 创建时间 (数据库自动管理)

@dataclass
class PLCModuleModel:
    """表示一个PLC模块 (例如 AI模块, DI模块)"""
    model: str                  # 模块型号 (例如 'LK221')
    module_type: str            # 模块类型 (例如 'AI', 'DI', 'CPU')
    series_id: int              # 所属系列ID (外键)
    channels: int = 0           # 通道数 (对于IO模块)
    description: Optional[str] = None # 模块描述
    id: Optional[int] = None          # 数据库中的ID
    created_at: Optional[datetime] = None # 创建时间 (数据库自动管理)
        
@dataclass
class PLCBackplaneModel:
    """表示一个PLC底板/机架"""
    model: str                  # 底板型号
    slots: int                  # 插槽数量
    id: Optional[int] = None          # 数据库中的ID
    description: Optional[str] = None # 底板描述
    created_at: Optional[datetime] = None # 创建时间 (数据库自动管理) 