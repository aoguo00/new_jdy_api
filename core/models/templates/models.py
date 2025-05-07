from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class TemplatePointModel:
    var_suffix: str
    desc_suffix: str
    data_type: str
    id: Optional[int] = None  # 数据库中的 ID
    template_id: Optional[int] = None # 外键关联到模板
    init_value: str = '0'
    power_protection: int = 0 
    forcible: int = 1         
    soe_enabled: int = 0      
    # created_at: Optional[datetime] = None # 暂时不加入，看后续是否必要

@dataclass
class DeviceTemplateModel:
    name: str
    id: Optional[int] = None
    prefix: Optional[str] = None
    points: List[TemplatePointModel] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None 