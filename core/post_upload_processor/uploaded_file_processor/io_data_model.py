from dataclasses import dataclass
from typing import Optional

@dataclass
class UploadedIOPoint:
    """
    用于存储从用户上传的IO点表Excel文件中解析出的单行数据模型。
    字段名基于原始Excel表头，转换为更适合编程的蛇形命名法 (snake_case)。
    所有字段都定义为 Optional[str]，因为用户上传时可能存在空单元格。
    """
    # 原始表头：序号
    serial_number: Optional[str] = None  # 序号
    # 原始表头：模块名称
    module_name: Optional[str] = None  # 模块名称
    # 原始表头：模块类型
    module_type: Optional[str] = None  # 模块类型
    # 原始表头：供电类型（有源/无源）
    power_supply_type: Optional[str] = None  # 供电类型（有源/无源）
    # 原始表头：线制
    wiring_system: Optional[str] = None  # 线制
    # 原始表头：通道位号
    channel_tag: Optional[str] = None  # 通道位号
    # 原始表头：场站名
    site_name: Optional[str] = None  # 场站名
    # 原始表头：场站编号
    site_number: Optional[str] = None  # 场站编号
    # 原始表头：变量名称（HMI）
    hmi_variable_name: Optional[str] = None  # 变量名称（HMI）
    # 原始表头：变量描述
    variable_description: Optional[str] = None  # 变量描述
    # 原始表头：数据类型
    data_type: Optional[str] = None  # 数据类型
    # 原始表头：读写属性
    read_write_property: Optional[str] = None  # 读写属性
    # 原始表头：保存历史
    save_history: Optional[str] = None  # 保存历史
    # 原始表头：掉电保护
    power_off_protection: Optional[str] = None  # 掉电保护
    # 原始表头：量程低限
    range_low_limit: Optional[str] = None  # 量程低限
    # 原始表头：量程高限
    range_high_limit: Optional[str] = None  # 量程高限
    # 原始表头：SLL设定值
    sll_set_value: Optional[str] = None  # SLL设定值
    # 原始表头：SLL设定点位
    sll_set_point: Optional[str] = None  # SLL设定点位
    # 原始表头：SLL设定点位_PLC地址
    sll_set_point_plc_address: Optional[str] = None  # SLL设定点位_PLC地址
    # 原始表头：SLL设定点位_通讯地址
    sll_set_point_comm_address: Optional[str] = None  # SLL设定点位_通讯地址
    # 原始表头：SL设定值
    sl_set_value: Optional[str] = None  # SL设定值
    # 原始表头：SL设定点位
    sl_set_point: Optional[str] = None  # SL设定点位
    # 原始表头：SL设定点位_PLC地址
    sl_set_point_plc_address: Optional[str] = None  # SL设定点位_PLC地址
    # 原始表头：SL设定点位_通讯地址
    sl_set_point_comm_address: Optional[str] = None  # SL设定点位_通讯地址
    # 原始表头：SH设定值
    sh_set_value: Optional[str] = None  # SH设定值
    # 原始表头：SH设定点位
    sh_set_point: Optional[str] = None  # SH设定点位
    # 原始表头：SH设定点位_PLC地址
    sh_set_point_plc_address: Optional[str] = None  # SH设定点位_PLC地址
    # 原始表头：SH设定点位_通讯地址
    sh_set_point_comm_address: Optional[str] = None  # SH设定点位_通讯地址
    # 原始表头：SHH设定值
    shh_set_value: Optional[str] = None  # SHH设定值
    # 原始表头：SHH设定点位
    shh_set_point: Optional[str] = None  # SHH设定点位
    # 原始表头：SHH设定点位_PLC地址
    shh_set_point_plc_address: Optional[str] = None  # SHH设定点位_PLC地址
    # 原始表头：SHH设定点位_通讯地址
    shh_set_point_comm_address: Optional[str] = None  # SHH设定点位_通讯地址
    # 原始表头：LL报警
    ll_alarm: Optional[str] = None  # LL报警
    # 原始表头：LL报警_PLC地址
    ll_alarm_plc_address: Optional[str] = None  # LL报警_PLC地址
    # 原始表头：LL报警_通讯地址
    ll_alarm_comm_address: Optional[str] = None  # LL报警_通讯地址
    # 原始表头：L报警
    l_alarm: Optional[str] = None  # L报警
    # 原始表头：L报警_PLC地址
    l_alarm_plc_address: Optional[str] = None  # L报警_PLC地址
    # 原始表头：L报警_通讯地址
    l_alarm_comm_address: Optional[str] = None  # L报警_通讯地址
    # 原始表头：H报警
    h_alarm: Optional[str] = None  # H报警
    # 原始表头：H报警_PLC地址
    h_alarm_plc_address: Optional[str] = None  # H报警_PLC地址
    # 原始表头：H报警_通讯地址
    h_alarm_comm_address: Optional[str] = None  # H报警_通讯地址
    # 原始表头：HH报警
    hh_alarm: Optional[str] = None  # HH报警
    # 原始表头：HH报警_PLC地址
    hh_alarm_plc_address: Optional[str] = None  # HH报警_PLC地址
    # 原始表头：HH报警_通讯地址
    hh_alarm_comm_address: Optional[str] = None  # HH报警_通讯地址
    # 原始表头：维护值设定
    maintenance_set_value: Optional[str] = None  # 维护值设定
    # 原始表头：维护值设定点位
    maintenance_set_point: Optional[str] = None  # 维护值设定点位
    # 原始表头：维护值设定点位_PLC地址
    maintenance_set_point_plc_address: Optional[str] = None  # 维护值设定点位_PLC地址
    # 原始表头：维护值设定点位_通讯地址
    maintenance_set_point_comm_address: Optional[str] = None  # 维护值设定点位_通讯地址
    # 原始表头：维护使能开关点位
    maintenance_enable_switch_point: Optional[str] = None  # 维护使能开关点位
    # 原始表头：维护使能开关点位_PLC地址
    maintenance_enable_switch_point_plc_address: Optional[str] = None  # 维护使能开关点位_PLC地址
    # 原始表头：维护使能开关点位_通讯地址
    maintenance_enable_switch_point_comm_address: Optional[str] = None  # 维护使能开关点位_通讯地址
    # 原始表头：PLC绝对地址
    plc_absolute_address: Optional[str] = None  # PLC绝对地址
    # 原始表头：上位机通讯地址
    hmi_communication_address: Optional[str] = None  # 上位机通讯地址

    # 你可以根据需要添加额外的方法，例如从字典创建实例的工厂方法
    # 或者验证数据的方法等 