"""已配置设备点表相关的Pydantic领域模型"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, computed_field, ConfigDict

class ConfiguredDevicePointModel(BaseModel):
    """表示一个基于模板配置生成的具体设备点位实例"""
    model_config = ConfigDict(from_attributes=True) # Pydantic V2 config

    id: Optional[int] = Field(default=None, description="数据库中的ID")
    # 关联信息
    template_name: str = Field(..., description="生成此点位所使用的模板名称 (快照)")
    variable_prefix: str = Field(..., description="应用模板时指定的变量前缀")
    description_prefix: str = Field(default="", description="应用模板时指定的描述前缀")
    # 来自模板的点位信息 (快照)
    var_suffix: str = Field(..., description="来自模板的点位变量名后缀")
    desc_suffix: str = Field(..., description="来自模板的点位描述后缀")
    data_type: str = Field(..., description="来自模板的点位数据类型")
    sll_setpoint: Optional[str] = Field(default="", description="SLL设定值 (来自模板的快照)")
    sl_setpoint: Optional[str] = Field(default="", description="SL设定值 (来自模板的快照)")
    sh_setpoint: Optional[str] = Field(default="", description="SH设定值 (来自模板的快照)")
    shh_setpoint: Optional[str] = Field(default="", description="SHH设定值 (来自模板的快照)")
    # 时间戳
    created_at: Optional[datetime] = Field(default=None, description="配置生成时间")

    # 计算属性 (Pydantic V2 使用 @computed_field)
    @computed_field
    @property
    def variable_name(self) -> str:
        """完整的变量名 (例如 DEV01_AI)"""
        # 简单的下划线连接，如果规则复杂需要调整
        connector = "_" if self.variable_prefix and self.var_suffix else ""
        return f"{self.variable_prefix}{connector}{self.var_suffix}"

    @computed_field
    @property
    def description(self) -> str:
        """完整的描述 (例如 DEV01 温度传感器)"""
        desc_parts = []
        if self.description_prefix:
            desc_parts.append(self.description_prefix)
        if self.desc_suffix:
            desc_parts.append(self.desc_suffix)
        return "".join(desc_parts).strip() 