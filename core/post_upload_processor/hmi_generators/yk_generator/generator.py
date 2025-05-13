import xlwt
import logging
import os
import pandas as pd # 导入 pandas
from typing import Tuple, Optional, List, Dict, Any # 增加类型提示
from collections import defaultdict

# 导入常量 (需要确保能找到这个路径)
# 假设 constants.py 在 io_validation 目录下，且该目录在 python path 中或使用相对导入
# 为了简单起见，我们直接定义需要的常量，或者确保导入路径正确
# from ...io_validation import constants as C # 尝试相对导入
# 如果相对导入复杂，直接定义或调整结构
class C: # 临时代替导入
    PLC_IO_SHEET_NAME = "IO点表"
    HMI_NAME_COL = "变量名称（HMI）"
    DESCRIPTION_COL = "变量描述"
    DATA_TYPE_COL = "数据类型" # 主表和第三方表都可能用
    PLC_ABS_ADDR_COL = "PLC绝对地址" # 似乎未使用？规则是 PLC绝对地址 -> 上位机通讯地址
    COMM_ADDR_COL = "上位机通讯地址" # 主表通讯地址来源 -> ItemName
    CHANNEL_NO_COL = "通道位号" # <<< 新增：添加通道位号常量
    SITE_NO_COL = "场站编号"  # <<< 新增：场站编号列名
    SITE_NAME_COL = "场站名"  # <<< 修改：确保与IO表示例一致
    SLL_SET_COL = "SLL设定值"
    SL_SET_COL = "SL设定值"
    SH_SET_COL = "SH设定值"
    SHH_SET_COL = "SHH设定值"
    # 第三方表特定的列
    TP_VAR_NAME_COL = "变量名称" # 第三方表点名
    TP_DESCRIPTION_COL = "变量描述" # 第三方表描述 (可能与主表同名)
    TP_MODBUS_ADDR_COL = "MODBUS地址" # 第三方表通讯地址来源 -> ItemName
    TP_DATA_TYPE_COL = "数据类型" # 明确第三方数据类型列

logger = logging.getLogger(__name__)

# --- 结构信息定义 ---
# 这是从 analyze_kingview_format.py 脚本的输出中提取的
# 1. io_server.xls 的结构
IO_SERVER_SHEETS = {
    'IO_DISC': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_CHAR': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_BYTE': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_SHORT': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_WORD': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_LONG': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_DWORD': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_INT64': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_FLOAT': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_DOUBLE': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'MaxRawValue', 'MinRawValue', 'MaxValue', 'MinValue', 'NonLinearTableName', 'ConvertType', 'IsFilter', 'DeadBand', 'Unit', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_STRING': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
    'IO_BLOB': ['TagID', 'TagName', 'Description', 'TagType', 'TagDataType', 'ChannelName', 'DeviceName', 'ChannelDriver', 'DeviceSeries', 'DeviceSeriesType', 'CollectControl', 'CollectInterval', 'CollectOffset', 'TimeZoneBias', 'TimeAdjustment', 'Enable', 'ForceWrite', 'ItemName', 'RegName', 'RegType', 'ItemDataType', 'ItemAccessMode', 'HisRecordMode', 'HisDeadBand', 'HisInterval', 'TagGroup'],
}

# 2. 数据词典点表.xls 的结构
DATA_DICTIONARY_SHEETS = {
    'STRUCT_TEMPLATE': ['Template', 'TempID', 'TempName', 'TemplateRefCount', 'TempDesc', 'MemberID', 'MemberName', 'MemberType', 'MemberDesc'],
    'STRUCT_TAG': ['StructTag', 'StructTagID', 'StructTagName', 'StructTagType', 'Description', 'MemberID', 'MemberName'],
    'REF_TAG': ['RefTag', 'RefTagID', 'RefTagName', 'RefTagType', 'Description'],
    'MEM_DISC': ['ContainerType', 'TagID', 'TagName', 'Description', 'InitialValueBool', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecInterval', 'AlarmType', 'CloseString', 'OpenString', 'AlarmDelay', 'AlarmPriority', 'DiscInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'CloseToOpen', 'OpenToClose', 'StateEnumTable'],
    'MEM_INT32': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable'],
    'MEM_INT64': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable'],
    'MEM_FLOAT': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable'],
    'MEM_DOUBLE': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable'],
    'MEM_STRING': ['ContainerType', 'TagID', 'TagName', 'Description', 'InitialValueStr', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8'],
    'IO_DISC': ['ContainerType', 'TagID', 'TagName', 'Description', 'InitialValueBool', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecInterval', 'AlarmType', 'CloseString', 'OpenString', 'AlarmDelay', 'AlarmPriority', 'DiscInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'CloseToOpen', 'OpenToClose', 'StateEnumTable', 'IOConfigControl', 'IOAccess', 'IOEnable', 'ForceRead', 'ForceWrite', 'DataConvertMode'],
    'IO_INT32': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable', 'IOConfigControl', 'IOAccess', 'MaxRaw', 'MinRaw', 'IOEnable', 'ForceRead', 'ForceWrite', 'DataConvertMode', 'NlnTableID', 'AddupMaxVal', 'AddupMinVal'],
    'IO_INT64': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable', 'IOConfigControl', 'IOAccess', 'MaxRaw', 'MinRaw', 'IOEnable', 'ForceRead', 'ForceWrite', 'DataConvertMode', 'NlnTableID', 'AddupMaxVal', 'AddupMinVal'],
    'IO_FLOAT': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable', 'IOConfigControl', 'IOAccess', 'MaxRaw', 'MinRaw', 'IOEnable', 'ForceRead', 'ForceWrite', 'DataConvertMode', 'NlnTableID', 'AddupMaxVal', 'AddupMinVal'],
    'IO_DOUBLE': ['ContainerType', 'TagID', 'TagName', 'Description', 'MaxValue', 'MinValue', 'InitialValue', 'Sensitivity', 'EngineerUnits', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'HisRecMode', 'HisRecChangeDeadband', 'HisRecInterval', 'HiHiEnabled', 'HiHiLimit', 'HiHiText', 'HiHiPriority', 'HiHiInhibitor', 'HiEnabled', 'HiLimit', 'HiText', 'HiPriority', 'HiInhibitor', 'LoEnabled', 'LoLimit', 'LoText', 'LoPriority', 'LoInhibitor', 'LoLoEnabled', 'LoLoLimit', 'LoLoText', 'LoLoPriority', 'LoLoInhibitor', 'LimitDeadband', 'LimitDelay', 'DevMajorEnabled', 'DevMajorLimit', 'DevMajorText', 'DevMajorPriority', 'MajorInhibitor', 'DevMinorEnabled', 'DevMinorLimit', 'DevMinorText', 'DevMinorPriority', 'MinorInhibitor', 'DevDeadband', 'DevTargetValue', 'DevDelay', 'RocEnabled', 'RocPercent', 'RocTimeUnit', 'RocText', 'RocDelay', 'RocPriority', 'RocInhibitor', 'StatusAlarmTableID', 'StatusAlarmEnabled', 'StatusAlarmTableName', 'StatusInhibitor', 'AlarmGroup', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'StateEnumTable', 'IOConfigControl', 'IOAccess', 'MaxRaw', 'MinRaw', 'IOEnable', 'ForceRead', 'ForceWrite', 'DataConvertMode', 'NlnTableID', 'AddupMaxVal', 'AddupMinVal'],
    'IO_STRING': ['ContainerType', 'TagID', 'TagName', 'Description', 'InitialValueStr', 'SecurityZoneID', 'RecordEvent', 'SaveValue', 'SaveParameter', 'AccessByOtherApplication', 'ExtentField1', 'ExtentField2', 'ExtentField3', 'ExtentField4', 'ExtentField5', 'ExtentField6', 'ExtentField7', 'ExtentField8', 'IOConfigControl', 'IOAccess', 'IOEnable', 'ForceRead', 'ForceWrite'],
}

# 辅助函数：检查值是否存在（处理 NaN 和空字符串）
def _is_value_present(value):
    if pd.isna(value): return False
    if isinstance(value, str) and not value.strip(): return False
    return True

class KingViewGenerator:
    """
    负责生成亚控 (KingView) HMI 所需的两种点表文件：
    1. IO Server 点表 (io_server.xls)
    2. 数据词典点表 (数据词典点表.xls)
    根据提供的IO点表数据填充文件内容。
    """

    def __init__(self):
        # 创建一个默认样式，用于所有单元格
        self.default_style = xlwt.XFStyle()
        font = xlwt.Font()
        font.name = '宋体'  # 设置字体为宋体
        font.height = 200  # 设置字号为10 (20 * 10)
        self.default_style.font = font
        # 可以选择性地添加其他样式，如对齐
        # alignment = xlwt.Alignment()
        # alignment.horz = xlwt.Alignment.HORZ_LEFT
        # alignment.vert = xlwt.Alignment.VERT_CENTER
        # self.default_style.alignment = alignment
        
        # 初始化用于存储待写入数据的字典
        self._io_server_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in IO_SERVER_SHEETS}
        self._data_dict_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in DATA_DICTIONARY_SHEETS}
        self._io_server_tag_id_counter = 1
        self._data_dict_tag_id_counter = 1

    def _reset_data(self):
        """重置内部数据存储和计数器，用于新的生成任务。"""
        self._io_server_data = {sheet_name: [] for sheet_name in IO_SERVER_SHEETS}
        self._data_dict_data = {sheet_name: [] for sheet_name in DATA_DICTIONARY_SHEETS}
        self._io_server_tag_id_counter = 1
        self._data_dict_tag_id_counter = 1

    def _process_point_data(self, df: pd.DataFrame, is_main_sheet: bool, site_name_from_file: Optional[str], site_no_from_file: Optional[str]):
        """处理来自单个Sheet (DataFrame) 的点位数据。"""
        data_type_col_name = C.DATA_TYPE_COL # 两个表都用这个列名
        # 增加通道位号列到必需检查 (仅主表需要)
        base_required_cols = [data_type_col_name]
        channel_no_col = None # 初始化
        if is_main_sheet:
             # 主表需要 HMI名、描述、通讯地址、通道号 (用于默认名)
             var_name_col = C.HMI_NAME_COL
             desc_col = C.DESCRIPTION_COL
             comm_addr_col = C.COMM_ADDR_COL
             channel_no_col = C.CHANNEL_NO_COL # 明确主表需要通道号
             base_required_cols.extend([var_name_col, desc_col, comm_addr_col, channel_no_col])
        else:
             # 第三方表需要 变量名、描述、Modbus地址
             var_name_col = C.TP_VAR_NAME_COL
             desc_col = C.TP_DESCRIPTION_COL # 假设第三方描述列也叫这个，如果不同需要修改
             comm_addr_col = C.TP_MODBUS_ADDR_COL
             # channel_no_col 保持 None
             base_required_cols.extend([var_name_col, desc_col, comm_addr_col])

        # 检查必需列
        if not all(col in df.columns for col in base_required_cols):
            missing = [col for col in base_required_cols if col not in df.columns]
            sheet_type = "主IO表" if is_main_sheet else "第三方表"
            logger.warning(f"{sheet_type} DataFrame缺少必需的列: {missing}，处理可能会受影响或跳过某些行。")
            # 不直接返回，尝试处理现有列

        for index, row in df.iterrows(): # 使用 index 替代 _
            data_type_raw = row.get(data_type_col_name)
            data_type = str(data_type_raw).upper().strip() if pd.notna(data_type_raw) else "" # 获取数据类型

            if not data_type: # 如果数据类型为空，则跳过
                 logger.warning(f"跳过行 {index + 2}: 数据类型为空。")
                 continue

            # SLL/SL/SH/SHH 在主表和第三方表中使用相同的列名常量
            sll_col, sl_col, sh_col, shh_col = C.SLL_SET_COL, C.SL_SET_COL, C.SH_SET_COL, C.SHH_SET_COL

            # 获取基础信息
            point_name_part_raw = row.get(var_name_col)
            description_raw = row.get(desc_col)
            comm_address_raw = row.get(comm_addr_col)

            tag_name: str
            description: str
            point_name_part_for_ioaccess: str # 用于 IOAccess 拼接
            comm_address = str(comm_address_raw).strip() if pd.notna(comm_address_raw) else ""

            if is_main_sheet:
                # --- 主表处理逻辑 ---
                point_name_part = str(point_name_part_raw).strip() if pd.notna(point_name_part_raw) else ""

                if not point_name_part: # HMI 名称为空，视为预留点位
                    if channel_no_col is None: # 安全检查，理论上主表时不会是None
                         logger.error("内部错误：处理主表预留点位时通道号列名未定义。")
                         channel_no = f"Row{index + 2}"
                    else:
                        channel_no_raw = row.get(channel_no_col) # channel_no_col 在 is_main_sheet 时已定义
                        channel_no = str(channel_no_raw).strip() if pd.notna(channel_no_raw) and str(channel_no_raw).strip() else f"Row{index + 2}"
                    
                    # 修改：为预留点位的 TagName 也加上场站编号前缀
                    tag_name = f'{site_no_from_file or ""}YLDW{channel_no}' 
                    description = f"预留点位{channel_no}"
                    point_name_part_for_ioaccess = tag_name # IOAccess 使用生成的完整 YLDW 名称 (含前缀)
                    logger.debug(f"检测到主IO表第 {index + 2} 行为预留点位 (通道: {channel_no})，生成默认 TagName: {tag_name}")
                else: # HMI 名称存在
                    point_name_part_for_ioaccess = point_name_part # IOAccess 使用原始点名部分
                    tag_name = f'{site_no_from_file or ""}{point_name_part}'
                    description = str(description_raw).strip() if pd.notna(description_raw) else ""
            else:
                # --- 第三方表处理逻辑 ---
                point_name_part = str(point_name_part_raw).strip() if pd.notna(point_name_part_raw) else ""
                if not point_name_part: # 如果第三方表的变量名也为空，可以选择跳过或生成默认名
                     logger.warning(f"跳过第三方表行 {index + 2}: 变量名为空。")
                     continue # 保持原有逻辑，跳过无名第三方点位
                point_name_part_for_ioaccess = point_name_part # IOAccess 使用原始点名部分
                tag_name = f'{site_no_from_file or ""}{point_name_part}' # 第三方点位也加上场站号前缀
                description = str(description_raw).strip() if pd.notna(description_raw) else ""

            # --- 后续公共处理逻辑 ---

            # 准备公共字段
            io_server_common = {
                'TagName': tag_name,
                'Description': description,
                'ChannelName': "Network1", # 默认值
                'DeviceName': site_name_from_file or "", # 使用从文件读取的场站名
                'ChannelDriver': "ModbusMaster", # 默认值
                'DeviceSeries': "ModbusTCP", # 默认值
                'DeviceSeriesType': 0, # 默认值
                'CollectControl': "否", # 默认值
                'CollectInterval': 1000, # 默认值
                'CollectOffset': 0, # 默认值
                'TimeZoneBias': 0, # 默认值
                'TimeAdjustment': 0, # 默认值
                'Enable': "是", # 默认值
                'ForceWrite': "否", # 默认值
                'ItemName': comm_address, # 使用对应的通讯地址 (主表用上位机地址，第三方用Modbus地址)
                'HisRecordMode': "不记录", # 默认值
                'HisDeadBand': 0, # 默认值
                'HisInterval': 60, # 默认值
                'TagGroup': site_name_from_file or "", # 使用从文件读取的场站名
            }
            data_dict_common = {
                'ContainerType': 1, # 固定值
                'TagName': tag_name,
                'Description': description,
                'SecurityZoneID': None, # 固定值或空
                'RecordEvent': False, # 固定值
                'SaveValue': True, # 固定值
                'SaveParameter': True, # 固定值
                'AccessByOtherApplication': False, # 固定值
                'ExtentField1': None, 'ExtentField2': None, 'ExtentField3': None,
                'ExtentField4': None, 'ExtentField5': None, 'ExtentField6': None,
                'ExtentField7': None, 'ExtentField8': None,
                'AlarmGroup': site_name_from_file or "", # 使用从文件读取的场站名
                'IOConfigControl': True, # 固定值
                # IOAccess 拼接: 使用 point_name_part_for_ioaccess
                'IOAccess': f'Server1.{point_name_part_for_ioaccess}.Value',
                'IOEnable': True, # 固定值
                'ForceRead': False, # 固定值
                'ForceWrite': False, # 固定值
                'StateEnumTable': None, # 固定值或空
            }

            # 分配 TagID
            current_io_server_tag_id = self._io_server_tag_id_counter
            current_data_dict_tag_id = self._data_dict_tag_id_counter
            self._io_server_tag_id_counter += 1
            self._data_dict_tag_id_counter += 1

            if data_type == "BOOL":
                # --- 填充 IO Server - IO_DISC ---
                io_server_disc_row = {
                    **io_server_common,
                    'TagID': current_io_server_tag_id,
                    'TagType': "用户变量", # 固定值
                    'TagDataType': "IODisc", # 固定值
                    'RegName': 0, 'RegType': 0, # 固定值
                    'ItemDataType': "BIT", # 固定值
                    'ItemAccessMode': "读写", # 固定值
                }
                self._io_server_data['IO_DISC'].append([io_server_disc_row.get(h, '') for h in IO_SERVER_SHEETS['IO_DISC']])

                # --- 填充 数据词典 - IO_DISC ---
                data_dict_disc_row = {
                    **data_dict_common,
                    'TagID': current_data_dict_tag_id,
                    'InitialValueBool': False, # 固定值
                    'HisRecMode': 2, # 固定值
                    'HisRecInterval': 60, # 固定值
                    'AlarmType': 256, # 固定值
                    'CloseString': "关闭", 'OpenString': "打开", # 固定值
                    'AlarmDelay': 0, 'AlarmPriority': 1, # 固定值
                    'DiscInhibitor': None, # 固定值或空
                    'CloseToOpen': "关到开", 'OpenToClose': "开到关", # 固定值
                    'DataConvertMode': 1, # 固定值
                }
                self._data_dict_data['IO_DISC'].append([data_dict_disc_row.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_DISC']])

            elif data_type == "REAL":
                # --- 填充 IO Server - IO_FLOAT ---
                io_server_float_row = {
                    **io_server_common,
                    'TagID': current_io_server_tag_id,
                    'TagType': "用户变量", # 固定值
                    'TagDataType': "IOFloat", # 对应 IO_FLOAT Sheet
                    'MaxRawValue': 1000000000, 'MinRawValue': -1000000000, # 固定值
                    'MaxValue': 1000000000, 'MinValue': -1000000000, # 固定值
                    'NonLinearTableName': None, # 空
                    'ConvertType': "无", 'IsFilter': "否", # 固定值
                    'DeadBand': 0, 'Unit': None, # 固定值或空
                    'RegName': 4, 'RegType': 3, # 固定值 (功能码3)
                    'ItemDataType': "FLOAT", # 固定值
                    'ItemAccessMode': "读写", # 固定值
                }
                self._io_server_data['IO_FLOAT'].append([io_server_float_row.get(h, '') for h in IO_SERVER_SHEETS['IO_FLOAT']])

                # --- 填充 数据词典 - IO_FLOAT ---
                # 获取设定值 (需要检查列是否存在)
                sll_val = row.get(sll_col) if sll_col in df.columns else None
                sl_val = row.get(sl_col) if sl_col in df.columns else None
                sh_val = row.get(sh_col) if sh_col in df.columns else None
                shh_val = row.get(shh_col) if shh_col in df.columns else None

                # 判断 Enabled 标志
                sll_enabled = _is_value_present(sll_val)
                sl_enabled = _is_value_present(sl_val)
                sh_enabled = _is_value_present(sh_val)
                shh_enabled = _is_value_present(shh_val)

                data_dict_float_row = {
                    **data_dict_common,
                    'TagID': current_data_dict_tag_id,
                    'MaxValue': 1000000000, 'MinValue': -1000000000, # 固定值
                    'InitialValue': 0, 'Sensitivity': 0, 'EngineerUnits': None, # 固定值或空
                    'HisRecMode': 2, 'HisRecChangeDeadband': 0, 'HisRecInterval': 60, # 固定值
                    # 报警设定值及相关字段
                    'HiHiEnabled': shh_enabled, 'HiHiLimit': shh_val if shh_enabled else '', 'HiHiText': "高高", 'HiHiPriority': 1, 'HiHiInhibitor': None,
                    'HiEnabled': sh_enabled, 'HiLimit': sh_val if sh_enabled else '', 'HiText': "高", 'HiPriority': 1, 'HiInhibitor': None,
                    'LoEnabled': sl_enabled, 'LoLimit': sl_val if sl_enabled else '', 'LoText': "低", 'LoPriority': 1, 'LoInhibitor': None,
                    'LoLoEnabled': sll_enabled, 'LoLoLimit': sll_val if sll_enabled else '', 'LoLoText': "低低", 'LoLoPriority': 1, 'LoLoInhibitor': None,
                    'LimitDeadband': 0, 'LimitDelay': 0, # 固定值
                    # 偏差报警
                    'DevMajorEnabled': False, 'DevMajorLimit': 80, 'DevMajorText': "主要", 'DevMajorPriority': 1, 'MajorInhibitor': None,
                    'DevMinorEnabled': False, 'DevMinorLimit': 20, 'DevMinorText': "次要", 'DevMinorPriority': 1, 'MinorInhibitor': None,
                    'DevDeadband': 0, 'DevTargetValue': 100, 'DevDelay': 0, # 固定值
                    # ROC 报警
                    'RocEnabled': False, 'RocPercent': 20, 'RocTimeUnit': 0, 'RocText': "变化率", 'RocDelay': 0, 'RocPriority': 1, 'RocInhibitor': None,
                    # Status 报警
                    'StatusAlarmTableID': 0, 'StatusAlarmEnabled': False, 'StatusAlarmTableName': None, 'StatusInhibitor': None,
                    # IO 相关
                    'MaxRaw': 1000000000, 'MinRaw': -1000000000, # 固定值
                    'DataConvertMode': 1, # 固定值
                    'NlnTableID': 0, 'AddupMaxVal': 0, 'AddupMinVal': 0, # 固定值
                }
                self._data_dict_data['IO_FLOAT'].append([data_dict_float_row.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_FLOAT']])
            else:
                # 严格按 "BOOL" / "REAL" 区分，忽略其他类型
                 # 使用原始点名或生成的默认名进行日志记录
                log_point_name = point_name_part if point_name_part else tag_name
                logger.warning(f"跳过点位 '{log_point_name}': 不支持的数据类型 '{data_type}' (原始: {data_type_raw})。仅支持 'BOOL' 或 'REAL'。")
                # 对于跳过的点位，不应该增加 TagID 计数器
                # 回退计数器 (因为之前可能已经增加了) - 或者更好的方式是在成功添加后才增加
                # --> 已将计数器增加移到成功添加之后

    def _process_main_io_data(self, main_io_df: pd.DataFrame) -> Dict[str, List[Dict]]:
        """
        处理主IO点表数据，根据数据类型分类。
        新增：处理预留点位（HMI变量名为空的情况）。

        Args:
            main_io_df (pd.DataFrame): 主IO点表数据。

        Returns:
            Dict[str, List[Dict]]: 按数据类型分类的点位数据字典。
        """
        logger.info("开始处理主IO点表数据...")
        processed_data: Dict[str, List[Dict]] = defaultdict(list)
        required_cols = [C.HMI_NAME_COL, C.COMM_ADDR_COL, C.DESCRIPTION_COL, C.DATA_TYPE_COL, C.CHANNEL_NO_COL] # 通讯地址和位号也加上用于生成默认名
        
        # 检查必需列是否存在
        missing_cols = [col for col in required_cols if col not in main_io_df.columns]
        if missing_cols:
            logger.error(f"主IO点表缺少必需的列: {', '.join(missing_cols)}")
            # 可以选择抛出异常或返回空字典，这里选择记录错误并继续尝试处理存在的列
            # return {} # 或者 raise ValueError(...)
            pass # 继续尝试处理，下方获取值时会用 .get() 避免 KeyError

        for index, row in main_io_df.iterrows():
            data_type_raw = row.get(C.DATA_TYPE_COL)
            data_type = str(data_type_raw).upper() if pd.notna(data_type_raw) else "UNKNOWN"
            hmi_name_raw = row.get(C.HMI_NAME_COL)
            comm_address_raw = row.get(C.COMM_ADDR_COL) # 获取通讯地址
            channel_no_raw = row.get(C.CHANNEL_NO_COL) # 获取位号

            # --- 新增：预留点位处理 ---
            is_reserved = pd.isna(hmi_name_raw) or (isinstance(hmi_name_raw, str) and not hmi_name_raw.strip())
            
            tag_name: str
            description: str

            if is_reserved:
                # 尝试使用通讯地址或通道号生成默认名称
                if pd.notna(comm_address_raw) and str(comm_address_raw).strip():
                    base_name = str(comm_address_raw).strip().replace('%', '') # 移除%等特殊字符
                    tag_name = f"Reserved_{base_name}"
                elif pd.notna(channel_no_raw) and str(channel_no_raw).strip():
                    base_name = str(channel_no_raw).strip()
                    tag_name = f"Reserved_{base_name}"
                else:
                    tag_name = f"Reserved_Row{index + 2}" # 使用Excel行号（假设从第2行开始）作为最后的备选方案
                
                description = "预留点位" # 默认描述
                logger.debug(f"检测到主IO表第 {index + 2} 行为预留点位，生成默认 TagName: {tag_name}")
            else:
                tag_name = str(hmi_name_raw).strip()
                description_raw = row.get(C.DESCRIPTION_COL)
                description = str(description_raw).strip() if pd.notna(description_raw) else ""
            # --- 预留点位处理结束 ---

            # 原始逻辑：根据数据类型分类
            point_data = {
                'TagName': tag_name,
                'Description': description,
                'CommAddress': str(comm_address_raw).strip() if pd.notna(comm_address_raw) else '', # 确保通讯地址存在
                # 其他字段根据需要从 row 中获取，并赋予默认值
                'ItemName': str(comm_address_raw).strip() if pd.notna(comm_address_raw) else '', # ItemName 也用通讯地址
                'Address': '', # 地址字段通常在亚控中由其他配置决定，这里可能留空或根据规则填写
                'DataType': data_type, # 记录原始数据类型用于分类
                 # 根据具体目标Sheet的需求，从row获取其他列的值...
                'AlarmHiHi': row.get(C.SHH_SET_COL), # 示例：获取报警值
                'AlarmHi': row.get(C.SH_SET_COL),
                'AlarmLo': row.get(C.SL_SET_COL),
                'AlarmLoLo': row.get(C.SLL_SET_COL),
                'DefaultValue': row.get('初始值'), # 示例
                'HiRange': row.get('工程上限'), # 示例
                'LoRange': row.get('工程下限'), # 示例
            }

            if data_type == "BOOL":
                processed_data['IO_DISC'].append(point_data)
            elif data_type == "REAL":
                # 亚控区分 FLOAT 和 DOUBLE，这里暂时都归到 FLOAT，如果需要区分，需增加逻辑
                processed_data['IO_FLOAT'].append(point_data)
            # 添加对其他数据类型的处理...
            # elif data_type == "INT": processed_data['IO_INT32'].append(point_data) # 假设INT对应INT32
            # elif data_type == "STRING": processed_data['IO_STRING'].append(point_data)
            # ... etc.
            else:
                # 对于未知或未处理的数据类型，可以选择记录日志或放入一个默认分类
                logger.warning(f"主IO点表中检测到未处理或未知的数据类型 '{data_type}' (原始: {data_type_raw})，点位 TagName: {tag_name}，行号: {index+2}。将跳过此点位。")

        logger.info("主IO点表数据处理完成。")
        return processed_data

    def _create_file_with_structure(self, 
                                    filepath: str, 
                                    sheet_structure: dict, 
                                    sheet_data: Dict[str, List[List[Any]]]
                                   ) -> Tuple[bool, Optional[str]]:
        """
        创建包含指定Sheet、表头和数据的Excel (.xls) 文件。
        """
        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            for sheet_name, headers in sheet_structure.items():
                # 检查Sheet名称长度是否超过31个字符
                safe_sheet_name = sheet_name[:31]
                if len(sheet_name) > 31:
                    logger.warning(f"Sheet名称 '{sheet_name}' 过长，已截断为 '{safe_sheet_name}'")
                
                sheet = workbook.add_sheet(safe_sheet_name) # 使用安全名称
                
                # 写入表头，使用默认样式
                for col_idx, header_title in enumerate(headers):
                    sheet.write(0, col_idx, header_title, self.default_style) # 应用 default_style
                
                # 写入数据行
                # 修正：应该使用原始 sheet_name 从 data_dict 获取数据
                data_rows_for_sheet = sheet_data.get(sheet_name, []) 
                
                for row_idx, data_row in enumerate(data_rows_for_sheet):
                    # 确保 data_row 长度不超过 headers 长度
                    if len(data_row) > len(headers):
                         logger.warning(f"Sheet '{safe_sheet_name}' 行 {row_idx + 2} 数据列数 ({len(data_row)}) 超过表头列数 ({len(headers)})，将截断数据。")
                         data_row = data_row[:len(headers)]
                    elif len(data_row) < len(headers):
                         # 如果数据列数少于表头，用空值填充末尾
                         data_row.extend([''] * (len(headers) - len(data_row)))

                    for col_idx, cell_value in enumerate(data_row):
                        # xlwt 对 bool 类型的处理：直接写入会变成 0/1，需要转为字符串
                        if isinstance(cell_value, bool):
                            cell_value_to_write = str(cell_value).upper() # 改为 TRUE/FALSE
                        # xlwt 不能直接处理 None，写入空字符串
                        elif cell_value is None:
                             cell_value_to_write = ''
                        # 处理 NaN (来自 pandas)
                        elif pd.isna(cell_value):
                            cell_value_to_write = ''
                        else:
                             cell_value_to_write = cell_value
                        
                        # 行号需要 +1 (因为表头占了第0行)
                        try:
                            # 写入数据单元格，使用默认样式
                            sheet.write(row_idx + 1, col_idx, cell_value_to_write, self.default_style) # 应用 default_style
                        except Exception as e_write_cell:
                            logger.error(f"写入单元格失败 (Sheet: '{safe_sheet_name}', Row: {row_idx+2}, Col: {col_idx+1}, Value: '{str(cell_value_to_write)[:50]}...'): {e_write_cell}")
                            # 可以选择继续写入其他单元格或抛出异常
                
                logger.info(f"  Sheet '{safe_sheet_name}' (共 {len(headers)} 列，{len(data_rows_for_sheet)} 行数据) 创建、写入表头和数据成功。")

            workbook.save(filepath)
            logger.info(f"成功创建并填充文件: {filepath}")
            return True, None
        except Exception as e:
            error_msg = f"创建或写入文件 '{filepath}' 时发生错误: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def generate_kingview_files(self,
                                io_table_path: str,
                                output_dir: str,
                                base_io_filename: str
                                # 移除 site_name 参数
                               ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        生成两个亚控点表文件（IO Server 和 数据词典），并根据输入IO点表填充数据。
        场站编号和场站名称将从IO点表文件的对应列读取。

        参数:
            io_table_path (str): 已验证的IO点表Excel文件路径。
            output_dir (str): 文件输出的目录。
            base_io_filename (str): 从上传的IO点表文件名提取的基础部分。
        """
        logger.info(f"开始生成亚控点表文件，源文件: {io_table_path}, 输出目录: {output_dir}")
        self._reset_data()

        extracted_site_no: Optional[str] = None
        extracted_site_name: Optional[str] = None # 新增：用于存储场站名称

        try:
            xls = pd.ExcelFile(io_table_path)
            sheet_names = xls.sheet_names
            if not sheet_names: return False, None, None, f"源IO点表文件 '{os.path.basename(io_table_path)}' 不包含任何工作表。"

            main_sheet_df: Optional[pd.DataFrame] = None
            third_party_dfs: List[pd.DataFrame] = []
            processed_sheet_names = []

            if C.PLC_IO_SHEET_NAME in sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=C.PLC_IO_SHEET_NAME)
                    if not df.empty:
                        main_sheet_df = df
                        logger.info(f"读取主IO点表Sheet: '{C.PLC_IO_SHEET_NAME}'")
                        processed_sheet_names.append(C.PLC_IO_SHEET_NAME)
                        
                        if C.SITE_NO_COL in df.columns:
                            first_site_no_val = df.loc[0, C.SITE_NO_COL]
                            if pd.notna(first_site_no_val):
                                extracted_site_no = str(first_site_no_val).strip()
                                logger.info(f"从主IO点表 '{C.SITE_NO_COL}' 列成功读取场站编号: {extracted_site_no}")
                            else: logger.warning(f"主IO点表的 '{C.SITE_NO_COL}' 列在第一行为空，无法获取场站编号。")
                        else: logger.warning(f"主IO点表未找到 '{C.SITE_NO_COL}' 列，无法获取场站编号。")

                        # --- 新增：读取场站名称 ---                        
                        if C.SITE_NAME_COL in df.columns:
                            first_site_name_val = df.loc[0, C.SITE_NAME_COL]
                            if pd.notna(first_site_name_val):
                                extracted_site_name = str(first_site_name_val).strip()
                                logger.info(f"从主IO点表 '{C.SITE_NAME_COL}' 列成功读取场站名称: {extracted_site_name}")
                            else:
                                logger.warning(f"主IO点表的 '{C.SITE_NAME_COL}' 列在第一行为空，无法获取场站名称。DeviceName/TagGroup可能为空。")
                        else:
                            logger.warning(f"主IO点表未找到 '{C.SITE_NAME_COL}' 列，无法获取场站名称。DeviceName/TagGroup可能为空。")
                        # --- 场站名称读取结束 --- 
                            
                    else: logger.warning(f"主IO点表Sheet '{C.PLC_IO_SHEET_NAME}' 为空...")
                    processed_sheet_names.append(C.PLC_IO_SHEET_NAME)
                except Exception as e_read_main: logger.error(f"读取主IO点表Sheet '{C.PLC_IO_SHEET_NAME}' 时出错: {e_read_main}"); processed_sheet_names.append(C.PLC_IO_SHEET_NAME)
            else: logger.warning(f"未找到名为 '{C.PLC_IO_SHEET_NAME}' 的主IO点表Sheet。")

            for sheet_name in sheet_names:
                if sheet_name in processed_sheet_names: continue
                try:
                    df_tp = pd.read_excel(xls, sheet_name=sheet_name)
                    if df_tp.empty: logger.info(f"跳过空的第三方Sheet: '{sheet_name}'"); continue
                    third_party_dfs.append(df_tp)
                    logger.info(f"读取第三方Sheet: '{sheet_name}'")
                except Exception as e_read_tp: logger.warning(f"读取第三方Sheet '{sheet_name}' 时出错: {e_read_tp}")
            
            if main_sheet_df is None and not third_party_dfs: return False, None, None, f"未能从 '{os.path.basename(io_table_path)}' 读取到任何有效数据Sheet。"

        except Exception as e: error_msg = f"读取源IO点表时发生错误: {e}"; logger.error(error_msg, exc_info=True); return False, None, None, error_msg

        try:
            if main_sheet_df is not None:
                logger.info("开始处理主IO点表数据...")
                self._process_point_data(main_sheet_df, is_main_sheet=True, site_name_from_file=extracted_site_name, site_no_from_file=extracted_site_no)
                logger.info("主IO点表数据处理完成。")
            if third_party_dfs:
                logger.info("开始处理第三方设备数据...")
                for i, tp_df_item in enumerate(third_party_dfs):
                    logger.info(f"处理第 {i+1} 个第三方DataFrame...")
                    self._process_point_data(tp_df_item, is_main_sheet=False, site_name_from_file=extracted_site_name, site_no_from_file=extracted_site_no)
                logger.info("所有第三方设备数据处理完成。")
        except Exception as e_proc: error_msg = f"处理IO点数据时发生错误: {e_proc}"; logger.error(error_msg, exc_info=True); return False, None, None, error_msg

        # --- 3. 生成文件 --- (逻辑不变)
        io_server_filename = f"{base_io_filename}_io_server.xls"
        data_dictionary_filename = f"{base_io_filename}_数据词典.xls"

        io_server_filepath = os.path.join(output_dir, io_server_filename)
        data_dictionary_filepath = os.path.join(output_dir, data_dictionary_filename)

        all_success = True; error_messages = []

        logger.info(f"准备创建并写入 IO Server 文件: {io_server_filepath}")
        success_io, err_io = self._create_file_with_structure(io_server_filepath, IO_SERVER_SHEETS, self._io_server_data)
        if not success_io: all_success = False; error_messages.append(f"IO Server 文件生成失败: {err_io}"); io_server_filepath = None

        logger.info(f"准备创建并写入数据词典文件: {data_dictionary_filepath}")
        success_dd, err_dd = self._create_file_with_structure(data_dictionary_filepath, DATA_DICTIONARY_SHEETS, self._data_dict_data)
        if not success_dd: all_success = False; error_messages.append(f"数据词典文件生成失败: {err_dd}"); data_dictionary_filepath = None
        final_error_message = "\n".join(error_messages) if error_messages else None

        if all_success: logger.info("所有亚控点表文件均已成功生成并填充数据。")
        else: logger.error(f"生成亚控点表文件时发生错误: {final_error_message}")
        return all_success, io_server_filepath, data_dictionary_filepath, final_error_message


# --- 本地测试部分 (需要更新) ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # 需要一个真实的、包含 "IO点表" 和其他Sheet的测试Excel文件
    # test_io_table_path = "path/to/your/test_io_table.xlsx" 
    test_io_table_path = "./test_data/Example_IO_Table_For_Kingview.xlsx" # 假设测试文件路径

    if not os.path.exists(test_io_table_path):
        print(f"测试所需的IO点表文件未找到: {test_io_table_path}")
        print("请创建或指定一个包含 'IO点表' Sheet 和可选的其他设备Sheet的Excel文件用于测试。")
        # 可以考虑创建一个简单的测试文件
        # exit()
        # 创建一个简单的测试文件用于演示
        print("正在创建一个简单的测试Excel文件...")
        test_dir = os.path.dirname(test_io_table_path)
        if test_dir and not os.path.exists(test_dir): os.makedirs(test_dir)
        
        # 确保列名与代码中的常量一致
        main_data = {
            C.HMI_NAME_COL: ["MAIN_BOOL_1", "MAIN_REAL_1", "", "MAIN_REAL_2"],
            C.DESCRIPTION_COL: ["主表布尔点", "主表实数点", "", "主表实数点2"],
            C.DATA_TYPE_COL: ["BOOL", "REAL", "BOOL", "REAL"],
            C.COMM_ADDR_COL: ["1001", "40001", "", "40002"],
            C.SLL_SET_COL: [None, None, None, 10.5],
            C.SL_SET_COL: [None, 5.0, None, None],
            C.SH_SET_COL: [None, 95.0, None, None],
            C.SHH_SET_COL: [None, None, None, 99.0]
            # 其他主表列可以留空或填默认
        }
        tp_data = {
             C.TP_VAR_NAME_COL: ["TP_BOOL_1", "TP_REAL_1", "TP_REAL_2"],
             #C.TP_DESCRIPTION_COL: ["第三方布尔", "第三方实数1", "第三方实数2"],
             C.DESCRIPTION_COL: ["第三方布尔", "第三方实数1", "第三方实数2"], # 假设第三方也用这个列名
             C.TP_DATA_TYPE_COL: ["BOOL", "REAL", "REAL"],
             C.TP_MODBUS_ADDR_COL: ["2001", "50001", "50002"],
             C.SLL_SET_COL: [None, 1.0, None],
             C.SL_SET_COL: [None, None, 15.0],
             C.SH_SET_COL: [None, 85.0, None],
             C.SHH_SET_COL: [None, None, None],
        }
        try:
            with pd.ExcelWriter(test_io_table_path) as writer:
                pd.DataFrame(main_data).to_excel(writer, sheet_name=C.PLC_IO_SHEET_NAME, index=False)
                pd.DataFrame(tp_data).to_excel(writer, sheet_name="第三方设备1", index=False)
            print(f"测试文件已创建: {test_io_table_path}")
        except Exception as e_create:
             print(f"创建测试文件失败: {e_create}")
             exit()


    test_output_dir = "./test_kingview_output_filled"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    test_base_filename = "TestIO_Filled"

    generator = KingViewGenerator()
    success, f1_path, f2_path, err_msg = generator.generate_kingview_files(
        test_io_table_path,
        test_output_dir,
        test_base_filename
    )

    if success:
        print(f"测试成功！已填充数据的亚控文件已生成:")
        if f1_path: print(f"  - {f1_path}")
        if f2_path: print(f"  - {f2_path}")
    else:
        print(f"测试失败。错误: {err_msg}") 