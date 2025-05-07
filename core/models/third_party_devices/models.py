from dataclasses import dataclass

@dataclass
class ThirdPartyConfiguredPointModel: # 类名重命名
    """表示一个已配置的第三方设备点位实例"""
    template_name: str    # 使用的模板名称
    device_prefix: str    # 用户为这组设备设置的变量名前缀
    var_suffix: str       # 来自模板的点位变量名后缀
    desc_suffix: str      # 来自模板的点位描述后缀
    data_type: str        # 来自模板的点位数据类型

    @property
    def variable_name(self) -> str:
        """完整的变量名 (例如 DEV01_AI)"""
        return f"{self.device_prefix}_{self.var_suffix}"

    @property
    def description(self) -> str:
        """完整的描述 (例如 DEV01 温度)"""
        # 注意：这里的描述逻辑可能需要根据实际需求调整
        return f"{self.device_prefix} {self.desc_suffix}" 