from dataclasses import dataclass

@dataclass
class ConfiguredDevicePointModel:
    template_name: str    # 使用的模板名称
    device_prefix: str    # 用户为这组设备设置的变量名前缀
    var_suffix: str       # 来自模板的点位变量名后缀
    desc_suffix: str      # 来自模板的点位描述后缀
    data_type: str        # 来自模板的点位数据类型

    @property
    def variable_name(self) -> str:
        return f"{self.device_prefix}_{self.var_suffix}"

    @property
    def description(self) -> str:
        return f"{self.device_prefix} {self.desc_suffix}" 