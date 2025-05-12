# -*- coding: utf-8 -*-
"""
存储 IO 点表校验相关的常量
"""
from typing import List

# --- 主IO点表Sheet列名 ---
HMI_NAME_COL: str = "变量名称（HMI）"
DESCRIPTION_COL: str = "变量描述"
POWER_SUPPLY_TYPE_COL: str = "供电类型（有源/无源）"
WIRING_SYSTEM_COL: str = "线制"
MODULE_TYPE_COL: str = "模块类型"
RANGE_LOW_LIMIT_COL: str = "量程低限"
RANGE_HIGH_LIMIT_COL: str = "量程高限"
SLL_SET_COL: str = "SLL设定值" # 主IO点表的SLL
SL_SET_COL: str = "SL设定值"   # 主IO点表的SL
SH_SET_COL: str = "SH设定值"   # 主IO点表的SH
SHH_SET_COL: str = "SHH设定值" # 主IO点表的SHH
PLC_IO_SHEET_NAME: str = "IO点表" # 主 IO 表的Sheet名称

# --- 第三方设备点表Sheet列名 ---
TP_INPUT_VAR_NAME_COL: str = "变量名称" # 用于错误消息中定位点位
TP_INPUT_DATA_TYPE_COL: str = "数据类型"
TP_INPUT_SLL_SET_COL: str = "SLL设定值"
TP_INPUT_SL_SET_COL: str = "SL设定值"
TP_INPUT_SH_SET_COL: str = "SH设定值"
TP_INPUT_SHH_SET_COL: str = "SHH设定值"

# --- 允许值常量 ---
ALLOWED_POWER_SUPPLY_VALUES: List[str] = ["有源", "无源"]
ALLOWED_WIRING_SYSTEM_VALUES_AI_AO: List[str] = ["2线制", "两线制", "三线制", "四线制", "3线制", "4线制"]
ALLOWED_WIRING_SYSTEM_VALUES_DI_DO: List[str] = ["常开", "常闭"]

# --- 数据类型常量 ---
DATA_TYPE_REAL: str = "REAL"
DATA_TYPE_BOOL: str = "BOOL"

# --- 模块类型常量 ---
MODULE_TYPE_AI: str = "AI"
MODULE_TYPE_AO: str = "AO"
MODULE_TYPE_DI: str = "DI"
MODULE_TYPE_DO: str = "DO"

# --- Sheet 名称 ---
# PLC_IO_SHEET_NAME 已在上面定义 

# 第三方表校验设定值所需的列 (内部使用，方便检查)
TP_INPUT_REQUIRED_COLS_FOR_SETPOINT_CHECK = [
    TP_INPUT_VAR_NAME_COL, TP_INPUT_DATA_TYPE_COL,
    TP_INPUT_SLL_SET_COL, TP_INPUT_SL_SET_COL,
    TP_INPUT_SH_SET_COL, TP_INPUT_SHH_SET_COL
] 