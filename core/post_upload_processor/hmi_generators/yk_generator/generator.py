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
        # === 样式定义集中在初始化方法中 ===
        # 默认样式
        self.default_style = xlwt.XFStyle()
        font = xlwt.Font(); font.name = '宋体'; font.height = 200
        self.default_style.font = font
        
        # 数字格式样式
        self.number_style = xlwt.XFStyle()
        self.number_style.font = font
        self.number_style.num_format_str = '0'  # 设置为数字格式，不限制小数位数
        
        # 初始化数据存储
        self._reset_data()

    def _reset_data(self):
        """重置数据存储结构"""
        self._io_server_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in IO_SERVER_SHEETS}
        self._data_dict_data: Dict[str, List[List[Any]]] = {sheet_name: [] for sheet_name in DATA_DICTIONARY_SHEETS}
        self._io_server_tag_id_counter = 1
        self._data_dict_tag_id_counter = 1

    # === 数据处理相关方法 ===
    def _get_numeric_limit(self, raw_val_str: Optional[str]) -> Tuple[Optional[float], bool]:
        """
        尝试将原始字符串限值转换为浮点数。
        如果原始值为空或无效，则报警不启用，限值为None。
        
        Args:
            raw_val_str: 原始字符串值
            
        Returns:
            Tuple[Optional[float], bool]: (转换后的数字或None, 是否启用)
        """
        if raw_val_str is None or str(raw_val_str).strip() == "":
            return None, False # 如果原始值为空或仅含空格，则限值视为None，且报警不启用
        try:
            return float(raw_val_str), True # 尝试转换为float，转换成功则报警启用
        except ValueError:
            # 如果原始值非空但无法转换为float，记录警告，限值视为None，且报警不启用
            logger.warning(f"报警限值 '{raw_val_str}' 无法转换为数字，将视为无效并不启用该报警。")
            return None, False 

    def _is_reserved_point(self, point: UploadedIOPoint) -> bool:
        """
        判断是否为预留点位
        
        预留点位的特征：
        1. HMI名称以YLDW开头（系统生成的预留点位）
        2. 描述包含"预留"关键字
        3. 描述为空或包含"预留"关键字
        
        Args:
            point: UploadedIOPoint对象
            
        Returns:
            bool: 如果是预留点位返回True，否则返回False
        """
        hmi_name = point.hmi_variable_name
        description = point.variable_description
        
        # 1. 检查HMI名称是否以YLDW开头（系统生成的预留点位）
        if hmi_name and str(hmi_name).strip().startswith("YLDW"):
            return True
        
        # 2. 检查描述是否包含"预留"关键字
        if description and "预留" in str(description):
            return True
            
        return False

    def _process_single_point(self, 
                              point: UploadedIOPoint, 
                              apply_main_sheet_logic: bool, 
                              site_name_from_file: Optional[str], 
                              site_no_from_file: Optional[str],
                              point_index_for_log: int):
        """
        处理单个UploadedIOPoint对象。
        
        Args:
            point: 上传的IO点位对象
            apply_main_sheet_logic: 是否应用主表特定的逻辑（如预留点命名）
            site_name_from_file: 从文件中提取的场站名称
            site_no_from_file: 从文件中提取的场站编号
            point_index_for_log: 用于日志记录的点位原始索引
        """
        # 过滤掉预留点位，预留点位不生成到HMI点表中
        if self._is_reserved_point(point):
            logger.debug(f"亚控生成器: 跳过预留点位: {point.hmi_variable_name} (来源: {point.source_sheet_name})")
            return
        
        # 提取点位属性
        data_type_raw = point.data_type
        point_name_part_raw = point.hmi_variable_name
        description_raw = point.variable_description
        comm_address_raw = point.hmi_communication_address
        channel_no_raw = point.channel_tag
        sll_val_raw = point.sll_set_value
        sl_val_raw = point.sl_set_value
        sh_val_raw = point.sh_set_value
        shh_val_raw = point.shh_set_value

        # 日志记录
        logger.debug(f"Processing UploadedIOPoint (Sheet: '{point.source_sheet_name}', Type: '{point.source_type}', Index in original list: {point_index_for_log}): "
                     f"HMI_Name='{point.hmi_variable_name}', DataType='{point.data_type}', "
                     f"CommAddr='{point.hmi_communication_address}', PLCAddr='{point.plc_absolute_address}', "
                     f"Desc='{point.variable_description}'")

        # 数据类型处理
        data_type = str(data_type_raw or "").upper().strip()
        log_sheet_type = "主表逻辑适用" if apply_main_sheet_logic else "第三方逻辑适用"

        if not data_type:
            logger.warning(f"跳过点位 (源: {point.source_sheet_name}, HMI: {point_name_part_raw or 'N/A'}, 索引: {point_index_for_log}): 数据类型为空。")
            return

        # 点位名称处理
        tag_name: str
        description: str
        point_name_part_for_ioaccess: str
        comm_address = str(comm_address_raw or "").strip()
        is_point_name_empty = not (point_name_part_raw and point_name_part_raw.strip())

        if apply_main_sheet_logic and is_point_name_empty:
            effective_channel_no = str(channel_no_raw or f"Row{point_index_for_log + 1}").strip()
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
        
        # 通信地址处理
        final_comm_address = comm_address
        if data_type == "BOOL":
            if comm_address.isdigit() and not comm_address.startswith('0'):
                final_comm_address = f"0{comm_address}"

        # 准备公共属性
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
            'IOAccess': f'Server1.{tag_name}.Value',
            'IOEnable': True, 'ForceRead': False, 'ForceWrite': False, 
            'StateEnumTable': None, 
        }

        current_io_server_tag_id = self._io_server_tag_id_counter
        current_data_dict_tag_id = self._data_dict_tag_id_counter
        
        # 根据数据类型生成不同类型的点位
        if data_type == "BOOL":
            self._process_bool_point(tag_name, current_io_server_tag_id, current_data_dict_tag_id, 
                                    io_server_common, data_dict_common)
            
            self._io_server_tag_id_counter += 1
            self._data_dict_tag_id_counter += 1
        elif data_type == "REAL":
            self._process_real_point(tag_name, current_io_server_tag_id, current_data_dict_tag_id,
                                    io_server_common, data_dict_common,
                                    sll_val_raw, sl_val_raw, sh_val_raw, shh_val_raw)
            
            self._io_server_tag_id_counter += 1
            self._data_dict_tag_id_counter += 1
        else:
            log_point_name = point_name_part_raw if point_name_part_raw and point_name_part_raw.strip() else f"(索引 {point_index_for_log})"
            logger.warning(f"跳过点位 '{log_point_name}' (源: {point.source_sheet_name}, {log_sheet_type}): 不支持的数据类型 '{data_type}' (原始: {data_type_raw})。仅支持 'BOOL' 或 'REAL'。")

    def _process_bool_point(self, tag_name: str, io_server_tag_id: int, data_dict_tag_id: int,
                           io_server_common: dict, data_dict_common: dict):
        """处理布尔类型点位"""
        io_server_disc_row_dict = {
            **io_server_common, 
            'TagID': io_server_tag_id, 
            'TagType': "用户变量", 
            'TagDataType': "IODisc", 
            'RegName': 0, 
            'RegType': 0, 
            'ItemDataType': "BIT", 
            'ItemAccessMode': "读写"
        }
        
        io_server_disc_row_list = [io_server_disc_row_dict.get(h, '') for h in IO_SERVER_SHEETS['IO_DISC']]
        logger.debug(f"  => IO Server (IO_DISC) data for '{tag_name}': {io_server_disc_row_list}")
        self._io_server_data['IO_DISC'].append(io_server_disc_row_list)
        
        data_dict_disc_row_dict = {
            **data_dict_common, 
            'TagID': data_dict_tag_id, 
            'InitialValueBool': False, 
            'HisRecMode': 2, 
            'HisRecInterval': 60, 
            'AlarmType': 256, 
            'CloseString': "关闭", 
            'OpenString': "打开", 
            'AlarmDelay': 0, 
            'AlarmPriority': 1, 
            'DiscInhibitor': None, 
            'CloseToOpen': "关到开", 
            'OpenToClose': "开到关", 
            'DataConvertMode': 1
        }
        
        data_dict_disc_row_list = [data_dict_disc_row_dict.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_DISC']]
        logger.debug(f"  => Data Dictionary (IO_DISC) data for '{tag_name}': {data_dict_disc_row_list}")
        self._data_dict_data['IO_DISC'].append(data_dict_disc_row_list)

    def _process_real_point(self, tag_name: str, io_server_tag_id: int, data_dict_tag_id: int,
                           io_server_common: dict, data_dict_common: dict,
                           sll_val_raw: Optional[str], sl_val_raw: Optional[str], 
                           sh_val_raw: Optional[str], shh_val_raw: Optional[str]):
        """处理实数类型点位"""
        io_server_float_row_dict = {
            **io_server_common, 
            'TagID': io_server_tag_id, 
            'TagType': "用户变量", 
            'TagDataType': "IOFloat", 
            'MaxRawValue': 1000000000, 
            'MinRawValue': -1000000000, 
            'MaxValue': 1000000000, 
            'MinValue': -1000000000, 
            'NonLinearTableName': None, 
            'ConvertType': "无", 
            'IsFilter': "否", 
            'DeadBand': 0, 
            'Unit': None, 
            'RegName': 4, 
            'RegType': 3, 
            'ItemDataType': "FLOAT", 
            'ItemAccessMode': "读写"
        }
        
        io_server_float_row_list = [io_server_float_row_dict.get(h, '') for h in IO_SERVER_SHEETS['IO_FLOAT']]
        logger.debug(f"  => IO Server (IO_FLOAT) data for '{tag_name}': {io_server_float_row_list}")
        self._io_server_data['IO_FLOAT'].append(io_server_float_row_list)
        
        # 处理报警限值
        shh_limit_value, shh_enabled = self._get_numeric_limit(shh_val_raw)
        sh_limit_value, sh_enabled = self._get_numeric_limit(sh_val_raw)
        sl_limit_value, sl_enabled = self._get_numeric_limit(sl_val_raw)
        sll_limit_value, sll_enabled = self._get_numeric_limit(sll_val_raw)

        data_dict_float_row_dict = {
            **data_dict_common, 
            'TagID': data_dict_tag_id, 
            'MaxValue': 1000000000, 
            'MinValue': -1000000000, 
            'InitialValue': 0, 
            'Sensitivity': 0, 
            'EngineerUnits': None, 
            'HisRecMode': 2, 
            'HisRecChangeDeadband': 0, 
            'HisRecInterval': 60,
            # 报警限值设置
            'HiHiEnabled': shh_enabled, 
            'HiHiLimit': shh_limit_value,
            'HiHiText': "高高", 
            'HiHiPriority': 1, 
            'HiHiInhibitor': None,
            'HiEnabled': sh_enabled, 
            'HiLimit': sh_limit_value,
            'HiText': "高", 
            'HiPriority': 1, 
            'HiInhibitor': None,
            'LoEnabled': sl_enabled, 
            'LoLimit': sl_limit_value,
            'LoText': "低", 
            'LoPriority': 1, 
            'LoInhibitor': None,
            'LoLoEnabled': sll_enabled, 
            'LoLoLimit': sll_limit_value,
            'LoLoText': "低低", 
            'LoLoPriority': 1, 
            'LoLoInhibitor': None,
            # 其他设置
            'LimitDeadband': 0, 
            'LimitDelay': 0, 
            'DevMajorEnabled': False, 
            'DevMajorLimit': 80, 
            'DevMajorText': "主要", 
            'DevMajorPriority': 1, 
            'MajorInhibitor': None, 
            'DevMinorEnabled': False, 
            'DevMinorLimit': 20, 
            'DevMinorText': "次要", 
            'DevMinorPriority': 1, 
            'MinorInhibitor': None, 
            'DevDeadband': 0, 
            'DevTargetValue': 100, 
            'DevDelay': 0, 
            'RocEnabled': False, 
            'RocPercent': 20, 
            'RocTimeUnit': 0, 
            'RocText': "变化率", 
            'RocDelay': 0, 
            'RocPriority': 1, 
            'RocInhibitor': None, 
            'StatusAlarmTableID': 0, 
            'StatusAlarmEnabled': False, 
            'StatusAlarmTableName': None, 
            'StatusInhibitor': None, 
            'MaxRaw': 1000000000, 
            'MinRaw': -1000000000, 
            'DataConvertMode': 1, 
            'NlnTableID': 0, 
            'AddupMaxVal': 0, 
            'AddupMinVal': 0
        }
        
        data_dict_float_row_list = [data_dict_float_row_dict.get(h) for h in DATA_DICTIONARY_SHEETS['IO_FLOAT']]
        logger.debug(f"  => Data Dictionary (IO_FLOAT) data for '{tag_name}': {data_dict_float_row_list}")
        self._data_dict_data['IO_FLOAT'].append(data_dict_float_row_list)

    # === 文件操作相关方法 ===
    def _create_file_with_structure(self, filepath: str, sheet_structure: dict, sheet_data: Dict[str, List[List[Any]]]) -> Tuple[bool, Optional[str]]:
        """
        创建Excel文件并按照给定结构填充数据
        
        Args:
            filepath: 输出文件路径
            sheet_structure: 工作表结构定义
            sheet_data: 工作表数据
            
        Returns:
            (成功标志, 错误消息)
        """
        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            for sheet_name, headers in sheet_structure.items():
                # 工作表名称处理
                safe_sheet_name = sheet_name[:31]
                if len(sheet_name) > 31:
                    logger.warning(f"Sheet名称 '{sheet_name}' 过长，已截断为 '{safe_sheet_name}'")
                
                # 创建工作表并写入表头
                sheet = workbook.add_sheet(safe_sheet_name)
                for col_idx, header_title in enumerate(headers):
                    sheet.write(0, col_idx, header_title, self.default_style)
                
                # 写入数据
                data_rows_for_sheet = sheet_data.get(sheet_name, []) 
                for row_idx, data_row in enumerate(data_rows_for_sheet):
                    # 处理数据行
                    if len(data_row) > len(headers):
                         logger.warning(f"Sheet '{safe_sheet_name}' 行 {row_idx + 2} 数据列数 ({len(data_row)}) 超过表头列数 ({len(headers)})，将截断数据。")
                         data_row = data_row[:len(headers)]
                    elif len(data_row) < len(headers):
                         data_row.extend([None] * (len(headers) - len(data_row))) # 用None填充而不是空字符串
                    
                    # 写入单元格
                    for col_idx, cell_value in enumerate(data_row):
                        self._write_cell_with_proper_format(sheet, row_idx + 1, col_idx, cell_value, headers[col_idx] if col_idx < len(headers) else "")
                
                logger.info(f"  Sheet '{safe_sheet_name}' (共 {len(headers)} 列，{len(data_rows_for_sheet)} 行数据) 创建、写入表头和数据成功。")
            
            # 保存文件
            workbook.save(filepath)
            logger.info(f"成功创建并填充文件: {filepath}")
            return True, None
        except Exception as e:
            error_msg = f"创建或写入文件 '{filepath}' 时发生错误: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def _write_cell_with_proper_format(self, sheet, row_idx: int, col_idx: int, value_to_write: Any, column_name: str):
        """
        根据值和列名写入带有适当格式的单元格
        
        Args:
            sheet: 工作表对象
            row_idx: 行索引
            col_idx: 列索引
            value_to_write: 要写入的值
            column_name: 列名称
        """
        try:
            # 处理特殊值类型
            if isinstance(value_to_write, bool):
                value_to_write = str(value_to_write).lower()
            elif pd.isna(value_to_write): # 处理Pandas的NA/NaN
                value_to_write = None     # 将Pandas的NA视为空白单元格 (写入None)
            
            # 根据列名选择合适的样式
            if column_name in ['HiHiLimit', 'HiLimit', 'LoLimit', 'LoLoLimit']:
                sheet.write(row_idx, col_idx, value_to_write, self.number_style)
            else:
                sheet.write(row_idx, col_idx, value_to_write, self.default_style)
        except Exception as e_write_cell:
            logger.error(f"写入单元格失败 (Row: {row_idx+1}, Col: {col_idx+1}, Value: '{str(value_to_write)[:50]}...'): {e_write_cell}")

    # === 主方法 ===
    def generate_kingview_files(self,
                               points_by_sheet: Dict[str, List[UploadedIOPoint]],
                               output_dir: str,
                               base_io_filename: str
                              ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        生成两个亚控点表文件，数据从传入的按工作表组织的 UploadedIOPoint 对象字典获取。
        场站编号和场站名称将从 points_by_sheet 中第一个源自主要IO工作表的点位中提取。
        
        Args:
            points_by_sheet: 按工作表组织的UploadedIOPoint对象字典
            output_dir: 输出目录
            base_io_filename: 基础文件名
            
        Returns:
            (成功标志, IO服务器文件路径, 数据词典文件路径, 错误消息)
        """
        # 合并所有工作表的点位到一个列表
        all_points_list: List[UploadedIOPoint] = []
        for sheet_name, points_list_for_sheet in points_by_sheet.items():
            if isinstance(points_list_for_sheet, list):
                all_points_list.extend(points_list_for_sheet)
            else:
                logger.warning(f"工作表 '{sheet_name}' 的数据不是预期的列表类型，已跳过。类型: {type(points_list_for_sheet)}")
        
        logger.info(f"开始生成亚控点表文件 (统一数据模型，共 {len(all_points_list)} 个点位，来自 {len(points_by_sheet)} 个源工作表)，输出目录: {output_dir}")
        self._reset_data()

        # 提取场站信息
        extracted_site_no, extracted_site_name = self._extract_site_info(all_points_list)

        # 处理点位数据
        try:
            logger.info(f"开始处理 {len(all_points_list)} 个点位 (UploadedIOPoint 列表)...")
            for index, point_obj in enumerate(all_points_list):
                # 判断是否应用主表逻辑，基于点的来源
                apply_main_logic = (point_obj.source_sheet_name == C.PLC_IO_SHEET_NAME or 
                                   point_obj.source_type == "main_io" or 
                                   point_obj.source_type == "intermediate_from_main")
                
                self._process_single_point(point_obj, 
                                          apply_main_sheet_logic=apply_main_logic, 
                                          site_name_from_file=extracted_site_name, 
                                          site_no_from_file=extracted_site_no,
                                          point_index_for_log=index)
            logger.info("所有点位数据处理完成。")
            
        except Exception as e_proc:
            error_msg = f"处理IO点数据时发生错误: {e_proc}"
            logger.error(error_msg, exc_info=True)
            return False, None, None, error_msg

        # 生成输出文件
        return self._generate_output_files(output_dir, base_io_filename)

    def _extract_site_info(self, all_points_list: List[UploadedIOPoint]) -> Tuple[Optional[str], Optional[str]]:
        """
        从点位列表中提取场站信息
        
        Args:
            all_points_list: 所有点位列表
            
        Returns:
            (场站编号, 场站名称)
        """
        extracted_site_no: Optional[str] = None
        extracted_site_name: Optional[str] = None

        # 查找第一个主IO点以获取场站信息
        first_main_io_point = next((p for p in all_points_list 
                                   if p.source_sheet_name == C.PLC_IO_SHEET_NAME or p.source_type == "main_io"), None)

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
        
        return extracted_site_no, extracted_site_name

    def _generate_output_files(self, output_dir: str, base_io_filename: str) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        生成输出文件
        
        Args:
            output_dir: 输出目录
            base_io_filename: 基础文件名
            
        Returns:
            (成功标志, IO服务器文件路径, 数据词典文件路径, 错误消息)
        """
        io_server_filename = f"{base_io_filename}_io_server.xls"
        data_dictionary_filename = f"{base_io_filename}_数据词典.xls"

        io_server_filepath = os.path.join(output_dir, io_server_filename)
        data_dictionary_filepath = os.path.join(output_dir, data_dictionary_filename)

        all_success = True
        error_messages = []

        logger.info(f"准备创建并写入 IO Server 文件: {io_server_filepath}")
        success_io, err_io = self._create_file_with_structure(io_server_filepath, IO_SERVER_SHEETS, self._io_server_data)
        if not success_io: 
            all_success = False
            error_messages.append(f"IO Server 文件生成失败: {err_io}")
            io_server_filepath = None

        logger.info(f"准备创建并写入数据词典文件: {data_dictionary_filepath}")
        success_dd, err_dd = self._create_file_with_structure(data_dictionary_filepath, DATA_DICTIONARY_SHEETS, self._data_dict_data)
        if not success_dd: 
            all_success = False
            error_messages.append(f"数据词典文件生成失败: {err_dd}")
            data_dictionary_filepath = None
        
        final_error_message = "\\n".join(error_messages) if error_messages else None

        if all_success: 
            logger.info("所有亚控点表文件均已成功生成并填充数据。")
        else: 
            logger.error(f"生成亚控点表文件时发生错误: {final_error_message}")
            
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