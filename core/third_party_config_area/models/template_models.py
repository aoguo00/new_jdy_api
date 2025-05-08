"""设备模板相关的Pydantic领域模型"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class TemplatePointModel(BaseModel):
    """表示设备模板中的一个点位"""
    model_config = ConfigDict(from_attributes=True) # Pydantic V2 config

    id: Optional[int] = Field(default=None, description="数据库中的ID")
    template_id: Optional[int] = Field(default=None, description="所属模板的ID (外键)")
    var_suffix: str = Field(..., description="变量名后缀") # Required field
    desc_suffix: str = Field(..., description="描述后缀")   # Required field
    data_type: str = Field(..., description="数据类型")     # Required field
    # 以下字段可以根据需要添加默认值或设为可选
    init_value: str = Field(default='0', description="初始值")
    power_protection: int = Field(default=0, description="是否掉电保护 (例如 0:否, 1:是)")
    forcible: int = Field(default=1, description="是否可强制 (例如 0:否, 1:是)")
    soe_enabled: int = Field(default=0, description="是否启用SOE (例如 0:否, 1:是)")
    # created_at: Optional[datetime] = Field(default=None, description="创建时间")

class DeviceTemplateModel(BaseModel):
    """表示一个设备模板，包含基本信息和点位列表"""
    model_config = ConfigDict(from_attributes=True) # Pydantic V2 config

    id: Optional[int] = Field(default=None, description="数据库中的ID")
    name: str = Field(..., description="模板名称") # Required field
    prefix: Optional[str] = Field(default=None, description="默认设备前缀")
    points: List[TemplatePointModel] = Field(default_factory=list, description="模板包含的点位列表")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="最后更新时间") 