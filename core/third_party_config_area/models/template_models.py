"""设备模板相关的Pydantic领域模型"""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class TemplatePointModel(BaseModel):
    """设备模板中的单个点位信息模型"""
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = Field(default=None, description="点位在数据库中的ID (如果是已存在的点位)")
    template_id: Optional[int] = Field(default=None, description="关联的模板ID (主要用于从数据库读取时)")
    var_suffix: str = Field(..., description="变量名后缀 (例如 _AI, _STATUS)")
    desc_suffix: str = Field(..., description="描述后缀 (例如 温度, 阀门状态)")
    data_type: str = Field(..., description="数据类型 (例如 REAL, BOOL)")

class DeviceTemplateModel(BaseModel):
    """表示一个设备模板，包含基本信息和点位列表"""
    model_config = ConfigDict(from_attributes=True) # Pydantic V2 config

    id: Optional[int] = Field(default=None, description="数据库中的ID")
    name: str = Field(..., description="模板名称") # Required field
    points: List[TemplatePointModel] = Field(default_factory=list, description="模板包含的点位列表")
    created_at: Optional[datetime] = Field(default=None, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="最后更新时间") 