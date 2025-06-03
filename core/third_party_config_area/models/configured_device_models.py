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
        # 处理*号作为变量占位符的情况
        if '*' in self.variable_prefix:
            # 根据*号分割自定义变量
            prefix_parts = self.variable_prefix.split('*')
            if len(prefix_parts) >= 2:
                # 前缀部分 + 模板变量 + 后缀部分
                return f"{prefix_parts[0]}{self.var_suffix}{prefix_parts[1]}"
            else:
                # 如果只有前半部分，则按前半部分+模板变量处理
                return f"{prefix_parts[0]}{self.var_suffix}"
        else:
            # 原始下划线连接方式
            connector = "_" if self.variable_prefix and self.var_suffix else ""
            return f"{self.variable_prefix}{connector}{self.var_suffix}"

    @computed_field
    @property
    def description(self) -> str:
        """完整的描述，支持*占位符"""
        # 处理*号作为描述占位符的情况
        if self.description_prefix and '*' in self.description_prefix:
            # 根据*号分割自定义描述
            desc_prefix_parts = self.description_prefix.split('*')
            if len(desc_prefix_parts) >= 2:
                # 前缀部分 + 模板描述 + 后缀部分
                # 如果模板描述为空，则只连接前缀和后缀
                if not self.desc_suffix:
                    return f"{desc_prefix_parts[0]}{desc_prefix_parts[1]}"
                else:
                    return f"{desc_prefix_parts[0]}{self.desc_suffix}{desc_prefix_parts[1]}"
            else:
                # 如果只有前半部分(如a*)，且模板描述为空，则仅显示前缀
                if not self.desc_suffix:
                    return desc_prefix_parts[0]
                else:
                    return f"{desc_prefix_parts[0]}{self.desc_suffix}"
        else:
            # 原始直接拼接方式
            return f"{self.description_prefix}{self.desc_suffix}" if self.description_prefix and self.desc_suffix else (self.description_prefix or self.desc_suffix or "")