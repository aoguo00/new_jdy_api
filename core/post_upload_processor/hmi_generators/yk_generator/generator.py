import xlwt
import logging
import os
import pandas as pd
from typing import Tuple, Optional, List, Dict, Any, Union
from collections import defaultdict

# 修改导入路径为绝对导入
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint

# 假设常量C的定义保持不变，因为它可能仍用于第三方表的列名或亚控输出文件的结构定义
class C:
    PLC_IO_SHEET_NAME = "IO点表" # 虽然读取时不再直接用这个名字筛选主表，但作为标识可能有其他用途
    HMI_NAME_COL = "变量名称（HMI）" # UploadedIOPoint.hmi_variable_name
    DESCRIPTION_COL = "变量描述"     # UploadedIOPoint.variable_description
    DATA_TYPE_COL = "数据类型"       # UploadedIOPoint.data_type
    COMM_ADDR_COL = "上位机通讯地址" # UploadedIOPoint.hmi_communication_address
    CHANNEL_NO_COL = "通道位号"     # UploadedIOPoint.channel_tag
    SITE_NO_COL = "场站编号"       # UploadedIOPoint.site_number
    SITE_NAME_COL = "场站名"       # UploadedIOPoint.site_name
    SLL_SET_COL = "SLL设定值"      # UploadedIOPoint.sll_set_value
    SL_SET_COL = "SL设定值"        # UploadedIOPoint.sl_set_value
    SH_SET_COL = "SH设定值"        # UploadedIOPoint.sh_set_value
    SHH_SET_COL = "SHH设定值"      # UploadedIOPoint.shh_set_value
    # 第三方表特定的列 (保持不变)
    TP_VAR_NAME_COL = "变量名称"
    TP_DESCRIPTION_COL = "变量描述"
    TP_MODBUS_ADDR_COL = "MODBUS地址"
    TP_DATA_TYPE_COL = "数据类型"

logger = logging.getLogger(__name__)

# --- 结构信息定义 (保持不变) ---
IO_SERVER_SHEETS = { # ... (结构定义保持不变) ...
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
DATA_DICTIONARY_SHEETS = { # ... (结构定义保持不变) ...
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
def _is_value_present(value: Optional[str]) -> bool: # 确保类型提示正确
    if value is None: return False # 首先检查None
    # pd.isna 在这里不适用，因为我们处理的是 UploadedIOPoint 的 str 属性
    if isinstance(value, str) and not value.strip(): return False
    return True

class KingViewGenerator:
    def __init__(self):
        self.default_style = xlwt.XFStyle()
        font = xlwt.Font(); font.name = '宋体'; font.height = 200
        self.default_style.font = font
        self._reset_data()

    def _reset_data(self):
        self._io_server_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in IO_SERVER_SHEETS}
        self._data_dict_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in DATA_DICTIONARY_SHEETS}
        self._io_server_tag_id_counter = 1
        self._data_dict_tag_id_counter = 1

    def _process_single_point(self, 
                              point: UploadedIOPoint, 
                              apply_main_sheet_logic: bool, 
                              site_name_from_file: Optional[str], 
                              site_no_from_file: Optional[str],
                              point_index_for_log: int): # 新增：用于日志记录的点位原始索引
        """
        处理单个UploadedIOPoint对象。
        apply_main_sheet_logic: 一个布尔值，指示是否应用主表特定的逻辑（如预留点命名）。
        """
        
        data_type_raw = point.data_type
        point_name_part_raw = point.hmi_variable_name
        description_raw = point.variable_description
        comm_address_raw = point.hmi_communication_address
        channel_no_raw = point.channel_tag
        sll_val_raw = point.sll_set_value
        sl_val_raw = point.sl_set_value
        sh_val_raw = point.sh_set_value
        shh_val_raw = point.shh_set_value

        # ===== DETAILED LOGGING: Start processing a point =====
        logger.debug(f"Processing UploadedIOPoint (Sheet: '{point.source_sheet_name}', Type: '{point.source_type}', Index in original list: {point_index_for_log}): "
                     f"HMI_Name='{point.hmi_variable_name}', DataType='{point.data_type}', "
                     f"CommAddr='{point.hmi_communication_address}', PLCAddr='{point.plc_absolute_address}', "
                     f"Desc='{point.variable_description}'")
        # =======================================================

        data_type = str(data_type_raw or "").upper().strip()
        log_sheet_type = "主表逻辑适用" if apply_main_sheet_logic else "第三方逻辑适用"

        if not data_type:
            logger.warning(f"跳过点位 (源: {point.source_sheet_name}, HMI: {point_name_part_raw or 'N/A'}, 索引: {point_index_for_log}): 数据类型为空。")
            return

        tag_name: str
        description: str
        point_name_part_for_ioaccess: str
        comm_address = str(comm_address_raw or "").strip()
        is_point_name_empty = not (point_name_part_raw and point_name_part_raw.strip())

        if apply_main_sheet_logic and is_point_name_empty:
            effective_channel_no = str(channel_no_raw or f"Row{point_index_for_log + 1}").strip() # 使用传入的索引
            tag_name = f'{site_no_from_file or ""}YLDW{effective_channel_no}'
            description = f"预留点位{effective_channel_no}"
            point_name_part_for_ioaccess = tag_name
            logger.debug(f"  点位 (源: {point.source_sheet_name}, 索引: {point_index_for_log}) 应用主表预留点逻辑，生成 TagName: {tag_name}")
        elif is_point_name_empty:
            logger.warning(f"跳过点位 (源: {point.source_sheet_name}, 索引: {point_index_for_log}): HMI变量名为空或无效，且不适用主表预留点逻辑。")
            return
        else:
            point_name_part_for_ioaccess = str(point_name_part_raw).strip()
            tag_name = f'{site_no_from_file or ""}{point_name_part_for_ioaccess}'
            description = str(description_raw or "").strip()
        
        final_comm_address = comm_address
        if data_type == "BOOL":
            if comm_address.isdigit() and not comm_address.startswith('0'):
                final_comm_address = f"0{comm_address}"

        io_server_common = {
            'TagName': tag_name, 'Description': description, 'ChannelName': "Network1", 
            'DeviceName': site_name_from_file or "", 'ChannelDriver': "ModbusMaster", 
            'DeviceSeries': "ModbusTCP", 'DeviceSeriesType': 0, 'CollectControl': "否", 
            'CollectInterval': 1000, 'CollectOffset': 0, 'TimeZoneBias': 0, 
            'TimeAdjustment': 0, 'Enable': "是", 'ForceWrite': "否", 
            'ItemName': final_comm_address, 'HisRecordMode': "不记录", 
            'HisDeadBand': 0, 'HisInterval': 60, 'TagGroup': site_name_from_file or "", 
        }
        data_dict_common = {
            'ContainerType': 1, 'TagName': tag_name, 'Description': description,
            'SecurityZoneID': None, 'RecordEvent': False, 'SaveValue': True, 
            'SaveParameter': True, 'AccessByOtherApplication': False, 
            'ExtentField1': None, 'ExtentField2': None, 'ExtentField3': None,
            'ExtentField4': None, 'ExtentField5': None, 'ExtentField6': None,
            'ExtentField7': None, 'ExtentField8': None,
            'AlarmGroup': site_name_from_file or "", 'IOConfigControl': True, 
            'IOAccess': f'Server1.{point_name_part_for_ioaccess}.Value',
            'IOEnable': True, 'ForceRead': False, 'ForceWrite': False, 
            'StateEnumTable': None, 
        }

        current_io_server_tag_id = self._io_server_tag_id_counter
        current_data_dict_tag_id = self._data_dict_tag_id_counter
            
        if data_type == "BOOL":
            io_server_disc_row_dict = {**io_server_common, 'TagID': current_io_server_tag_id, 'TagType': "用户变量", 'TagDataType': "IODisc", 'RegName': 0, 'RegType': 0, 'ItemDataType': "BIT", 'ItemAccessMode': "读写"}
            io_server_disc_row_list = [io_server_disc_row_dict.get(h, '') for h in IO_SERVER_SHEETS['IO_DISC']]
            logger.debug(f"  => IO Server (IO_DISC) data for '{tag_name}': {io_server_disc_row_list}")
            self._io_server_data['IO_DISC'].append(io_server_disc_row_list)
            
            data_dict_disc_row_dict = {**data_dict_common, 'TagID': current_data_dict_tag_id, 'InitialValueBool': False, 'HisRecMode': 2, 'HisRecInterval': 60, 'AlarmType': 256, 'CloseString': "关闭", 'OpenString': "打开", 'AlarmDelay': 0, 'AlarmPriority': 1, 'DiscInhibitor': None, 'CloseToOpen': "关到开", 'OpenToClose': "开到关", 'DataConvertMode': 1}
            data_dict_disc_row_list = [data_dict_disc_row_dict.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_DISC']]
            logger.debug(f"  => Data Dictionary (IO_DISC) data for '{tag_name}': {data_dict_disc_row_list}")
            self._data_dict_data['IO_DISC'].append(data_dict_disc_row_list)
            
            self._io_server_tag_id_counter += 1
            self._data_dict_tag_id_counter += 1
        elif data_type == "REAL":
            io_server_float_row_dict = {**io_server_common, 'TagID': current_io_server_tag_id, 'TagType': "用户变量", 'TagDataType': "IOFloat", 'MaxRawValue': 1000000000, 'MinRawValue': -1000000000, 'MaxValue': 1000000000, 'MinValue': -1000000000, 'NonLinearTableName': None, 'ConvertType': "无", 'IsFilter': "否", 'DeadBand': 0, 'Unit': None, 'RegName': 4, 'RegType': 3, 'ItemDataType': "FLOAT", 'ItemAccessMode': "读写"}
            io_server_float_row_list = [io_server_float_row_dict.get(h, '') for h in IO_SERVER_SHEETS['IO_FLOAT']]
            logger.debug(f"  => IO Server (IO_FLOAT) data for '{tag_name}': {io_server_float_row_list}")
            self._io_server_data['IO_FLOAT'].append(io_server_float_row_list)
            
            sll_val = str(sll_val_raw or '').strip()
            sl_val = str(sl_val_raw or '').strip()
            sh_val = str(sh_val_raw or '').strip()
            shh_val = str(shh_val_raw or '').strip()

            sll_enabled = bool(sll_val)
            sl_enabled = bool(sl_val)
            sh_enabled = bool(sh_val)
            shh_enabled = bool(shh_val)

            data_dict_float_row_dict = {**data_dict_common, 'TagID': current_data_dict_tag_id, 'MaxValue': 1000000000, 'MinValue': -1000000000, 'InitialValue': 0, 'Sensitivity': 0, 'EngineerUnits': None, 'HisRecMode': 2, 'HisRecChangeDeadband': 0, 'HisRecInterval': 60,
                                 'HiHiEnabled': shh_enabled, 'HiHiLimit': shh_val if shh_enabled else '', 'HiHiText': "高高", 'HiHiPriority': 1, 'HiHiInhibitor': None,
                                 'HiEnabled': sh_enabled, 'HiLimit': sh_val if sh_enabled else '', 'HiText': "高", 'HiPriority': 1, 'HiInhibitor': None,
                                 'LoEnabled': sl_enabled, 'LoLimit': sl_val if sl_enabled else '', 'LoText': "低", 'LoPriority': 1, 'LoInhibitor': None,
                                 'LoLoEnabled': sll_enabled, 'LoLoLimit': sll_val if sll_enabled else '', 'LoLoText': "低低", 'LoLoPriority': 1, 'LoLoInhibitor': None,
                                 'LimitDeadband': 0, 'LimitDelay': 0, 'DevMajorEnabled': False, 'DevMajorLimit': 80, 'DevMajorText': "主要", 'DevMajorPriority': 1, 'MajorInhibitor': None, 'DevMinorEnabled': False, 'DevMinorLimit': 20, 'DevMinorText': "次要", 'DevMinorPriority': 1, 'MinorInhibitor': None, 'DevDeadband': 0, 'DevTargetValue': 100, 'DevDelay': 0, 'RocEnabled': False, 'RocPercent': 20, 'RocTimeUnit': 0, 'RocText': "变化率", 'RocDelay': 0, 'RocPriority': 1, 'RocInhibitor': None, 'StatusAlarmTableID': 0, 'StatusAlarmEnabled': False, 'StatusAlarmTableName': None, 'StatusInhibitor': None, 'MaxRaw': 1000000000, 'MinRaw': -1000000000, 'DataConvertMode': 1, 'NlnTableID': 0, 'AddupMaxVal': 0, 'AddupMinVal': 0}
            data_dict_float_row_list = [data_dict_float_row_dict.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_FLOAT']]
            logger.debug(f"  => Data Dictionary (IO_FLOAT) data for '{tag_name}': {data_dict_float_row_list}")
            self._data_dict_data['IO_FLOAT'].append(data_dict_float_row_list)
            
            self._io_server_tag_id_counter += 1
            self._data_dict_tag_id_counter += 1
        else:
            log_point_name = point_name_part_raw if point_name_part_raw and point_name_part_raw.strip() else f"(索引 {point_index_for_log})"
            logger.warning(f"跳过点位 '{log_point_name}' (源: {point.source_sheet_name}, {log_sheet_type}): 不支持的数据类型 '{data_type}' (原始: {data_type_raw})。仅支持 'BOOL' 或 'REAL'。")

    def _create_file_with_structure(self, filepath: str, sheet_structure: dict, sheet_data: Dict[str, List[List[Any]]]) -> Tuple[bool, Optional[str]]:
        # ... (此方法保持不变) ...
        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            for sheet_name, headers in sheet_structure.items():
                safe_sheet_name = sheet_name[:31]
                if len(sheet_name) > 31:
                    logger.warning(f"Sheet名称 '{sheet_name}' 过长，已截断为 '{safe_sheet_name}'")
                sheet = workbook.add_sheet(safe_sheet_name)
                for col_idx, header_title in enumerate(headers):
                    sheet.write(0, col_idx, header_title, self.default_style)
                data_rows_for_sheet = sheet_data.get(sheet_name, []) 
                for row_idx, data_row in enumerate(data_rows_for_sheet):
                    if len(data_row) > len(headers):
                         logger.warning(f"Sheet '{safe_sheet_name}' 行 {row_idx + 2} 数据列数 ({len(data_row)}) 超过表头列数 ({len(headers)})，将截断数据。")
                         data_row = data_row[:len(headers)]
                    elif len(data_row) < len(headers):
                         data_row.extend([''] * (len(headers) - len(data_row)))
                    for col_idx, cell_value in enumerate(data_row):
                        if isinstance(cell_value, bool):
                            cell_value_to_write = str(cell_value).upper()
                        elif cell_value is None:
                             cell_value_to_write = ''
                        elif pd.isna(cell_value):
                            cell_value_to_write = ''
                        else:
                             cell_value_to_write = cell_value
                        try:
                            sheet.write(row_idx + 1, col_idx, cell_value_to_write, self.default_style)
                        except Exception as e_write_cell:
                            logger.error(f"写入单元格失败 (Sheet: '{safe_sheet_name}', Row: {row_idx+2}, Col: {col_idx+1}, Value: '{str(cell_value_to_write)[:50]}...'): {e_write_cell}")
                logger.info(f"  Sheet '{safe_sheet_name}' (共 {len(headers)} 列，{len(data_rows_for_sheet)} 行数据) 创建、写入表头和数据成功。")
            workbook.save(filepath)
            logger.info(f"成功创建并填充文件: {filepath}")
            return True, None
        except Exception as e:
            error_msg = f"创建或写入文件 '{filepath}' 时发生错误: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def generate_kingview_files(self,
                                points_by_sheet: Dict[str, List[UploadedIOPoint]], # 修改：接收字典
                                output_dir: str,
                                base_io_filename: str
                               ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        生成两个亚控点表文件，数据从传入的按工作表组织的 UploadedIOPoint 对象字典获取。
        场站编号和场站名称将从 points_by_sheet 中第一个源自主要IO工作表的点位中提取。
        """
        # 将所有工作表的点位合并到一个列表中
        all_points_list: List[UploadedIOPoint] = []
        for sheet_name, points_list_for_sheet in points_by_sheet.items():
            if isinstance(points_list_for_sheet, list):
                all_points_list.extend(points_list_for_sheet)
            else:
                logger.warning(f"工作表 '{sheet_name}' 的数据不是预期的列表类型，已跳过。类型: {type(points_list_for_sheet)}")
        
        logger.info(f"开始生成亚控点表文件 (统一数据模型，共 {len(all_points_list)} 个点位，来自 {len(points_by_sheet)} 个源工作表)，输出目录: {output_dir}")
        self._reset_data()

        extracted_site_no: Optional[str] = None
        extracted_site_name: Optional[str] = None

        # 从 all_points_list (已合并) 中查找第一个主IO点以获取场站信息
        # (或者可以更精确地遍历 points_by_sheet 来查找主表，但当前逻辑基于合并列表也可行)
        first_main_io_point = next((p for p in all_points_list if p.source_sheet_name == C.PLC_IO_SHEET_NAME or p.source_type == "main_io"), None)

        if first_main_io_point:
            if first_main_io_point.site_number and first_main_io_point.site_number.strip():
                extracted_site_no = first_main_io_point.site_number.strip()
                logger.info(f"从点位 '{first_main_io_point.hmi_variable_name}' (源: {first_main_io_point.source_sheet_name}) 成功读取场站编号: {extracted_site_no}")
            else:
                logger.warning(f"用于提取场站信息的点位 '{first_main_io_point.hmi_variable_name}' 场站编号为空或无效。")
            
            if first_main_io_point.site_name and first_main_io_point.site_name.strip():
                extracted_site_name = first_main_io_point.site_name.strip()
                logger.info(f"从点位 '{first_main_io_point.hmi_variable_name}' (源: {first_main_io_point.source_sheet_name}) 成功读取场站名称: {extracted_site_name}")
            else:
                logger.warning(f"用于提取场站信息的点位 '{first_main_io_point.hmi_variable_name}' 场站名称为空或无效。DeviceName/TagGroup可能为空。")
        else:
            logger.warning("在提供的所有点位数据中未找到源自主要IO工作表的点，无法提取场站编号和场站名称。")

        # 处理数据
        try:
            logger.info(f"开始处理 {len(all_points_list)} 个点位 (UploadedIOPoint 列表)...") # 使用合并后的 all_points_list
            for index, point_obj in enumerate(all_points_list): # 使用合并后的 all_points_list
                # 判断是否应用主表逻辑，基于点的来源
                # (假设 excel_reader.py 在转换时正确设置了 point.source_sheet_name 或 point.source_type)
                apply_main_logic = (point_obj.source_sheet_name == C.PLC_IO_SHEET_NAME or \
                                    point_obj.source_type == "main_io" or \
                                    point_obj.source_type == "intermediate_from_main")
                
                self._process_single_point(point_obj, 
                                           apply_main_sheet_logic=apply_main_logic, 
                                           site_name_from_file=extracted_site_name, 
                                           site_no_from_file=extracted_site_no,
                                           point_index_for_log=index) # 传递原始索引用于日志
            logger.info("所有点位数据处理完成。")
            
        except Exception as e_proc:
            error_msg = f"处理IO点数据时发生错误: {e_proc}"
            logger.error(error_msg, exc_info=True)
            return False, None, None, error_msg

        # --- 3. 生成文件 (逻辑不变) ---
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
        
        final_error_message = "\\n".join(error_messages) if error_messages else None

        if all_success: logger.info("所有亚控点表文件均已成功生成并填充数据。")
        else: logger.error(f"生成亚控点表文件时发生错误: {final_error_message}")
        return all_success, io_server_filepath, data_dictionary_filepath, final_error_message


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # 创建示例 UploadedIOPoint 数据 (修改为字典结构)
    sample_points_by_sheet_data: Dict[str, List[UploadedIOPoint]] = {
        C.PLC_IO_SHEET_NAME: [ # 主IO表
            UploadedIOPoint(source_sheet_name=C.PLC_IO_SHEET_NAME, source_type="main_io", site_name="测试站", site_number="S007", hmi_variable_name="YK_AI_01", variable_description="亚控模拟输入1", data_type="REAL", hmi_communication_address="40001", channel_tag="AI_CH1", sll_set_value="1", sl_set_value="2", sh_set_value="98", shh_set_value="99"),
            UploadedIOPoint(source_sheet_name=C.PLC_IO_SHEET_NAME, source_type="main_io", site_name="测试站", site_number="S007", hmi_variable_name="YK_DI_01", variable_description="亚控数字输入1", data_type="BOOL", hmi_communication_address="10001", channel_tag="DI_CH1"),
            UploadedIOPoint(source_sheet_name=C.PLC_IO_SHEET_NAME, source_type="main_io", site_name="测试站", site_number="S007", hmi_variable_name=None, channel_tag="Res_CH1", variable_description=None, data_type="REAL", hmi_communication_address="40002"), # 预留点
        ],
        "第三方设备表A": [ # 第三方表
            UploadedIOPoint(source_sheet_name="第三方设备表A", source_type="third_party", site_name="测试站", site_number="S007", hmi_variable_name="TP_BOOL_1", variable_description="第三方1布尔", data_type="BOOL", hmi_communication_address="2001"),
            UploadedIOPoint(source_sheet_name="第三方设备表A", source_type="third_party", site_name="测试站", site_number="S007", hmi_variable_name="TP_REAL_1", variable_description="第三方1实数", data_type="REAL", hmi_communication_address="50001", sll_set_value="5.5"),
        ]
    }
    sample_empty_points_dict: Dict[str, List[UploadedIOPoint]] = {}
   
    test_output_dir = "./test_kingview_output_unified_model"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    generator = KingViewGenerator()

    logger.info("--- 测试场景1: 包含主表和第三方数据的合并列表 ---")
    success1, f1_1, f2_1, err1 = generator.generate_kingview_files(
        sample_points_by_sheet_data, test_output_dir, "UnifiedDataTest" # 使用新的字典数据
    )
    if success1: print(f"场景1成功: {f1_1}, {f2_1}")
    else: print(f"场景1失败: {err1}")

    generator._reset_data() 
    logger.info("--- 测试场景2: 空的点位列表 ---")
    success2, f1_2, f2_2, err2 = generator.generate_kingview_files(
        sample_empty_points_dict, test_output_dir, "EmptyListTest" # 使用空的字典
    )
    if success2: print(f"场景2成功: {f1_2}, {f2_2}") # 应该能生成空的结构文件
    else: print(f"场景2失败: {err2}") 