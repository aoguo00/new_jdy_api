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

    def _process_point_data(self, 
                            data_source: Union[List[UploadedIOPoint], pd.DataFrame], 
                            is_main_sheet: bool, 
                            site_name_from_file: Optional[str], 
                            site_no_from_file: Optional[str]):
        """处理来自单个数据源 (UploadedIOPoint列表 或 DataFrame) 的点位数据。"""
        
        # 根据 is_main_sheet 选择迭代方式和数据提取方式
        data_iterator: Any
        if is_main_sheet:
            if not isinstance(data_source, list): # 类型检查，确保主表数据是列表
                logger.error("内部错误：主表数据源期望是List[UploadedIOPoint]，但收到了其他类型。")
                return
            data_iterator = enumerate(data_source) # 主表迭代 UploadedIOPoint 列表
        else:
            if not isinstance(data_source, pd.DataFrame):
                logger.error("内部错误：第三方数据源期望是pd.DataFrame，但收到了其他类型。")
                return
            data_iterator = data_source.iterrows() # 第三方表迭代 DataFrame 行

        for index, item_data in data_iterator: # item_data 将是 UploadedIOPoint 或 pd.Series
            data_type_raw: Optional[str]
            point_name_part_raw: Optional[str]
            description_raw: Optional[str]
            comm_address_raw: Optional[str]
            channel_no_raw: Optional[str] # 仅用于主表预留点位
            # 报警限值
            sll_val_raw: Optional[str]
            sl_val_raw: Optional[str]
            sh_val_raw: Optional[str]
            shh_val_raw: Optional[str]

            if is_main_sheet:
                point: UploadedIOPoint = item_data # 明确类型
                data_type_raw = point.data_type
                point_name_part_raw = point.hmi_variable_name
                description_raw = point.variable_description
                comm_address_raw = point.hmi_communication_address # 主表使用上位机通讯地址
                channel_no_raw = point.channel_tag
                sll_val_raw = point.sll_set_value
                sl_val_raw = point.sl_set_value
                sh_val_raw = point.sh_set_value
                shh_val_raw = point.shh_set_value
            else: # is_main_sheet is False, processing a DataFrame row (pd.Series)
                row: pd.Series = item_data # 明确类型
                data_type_raw = str(row.get(C.TP_DATA_TYPE_COL, ""))
                point_name_part_raw = str(row.get(C.TP_VAR_NAME_COL, ""))
                description_raw = str(row.get(C.TP_DESCRIPTION_COL, ""))
                comm_address_raw = str(row.get(C.TP_MODBUS_ADDR_COL, "")) # 第三方表使用Modbus地址
                channel_no_raw = None # 第三方表通常不直接使用通道号来生成预留名
                sll_val_raw = str(row.get(C.SLL_SET_COL, ""))
                sl_val_raw = str(row.get(C.SL_SET_COL, ""))
                sh_val_raw = str(row.get(C.SH_SET_COL, ""))
                shh_val_raw = str(row.get(C.SHH_SET_COL, ""))

            data_type = str(data_type_raw or "").upper().strip()
            if not data_type:
                 logger.warning(f"跳过行/点 {index + (2 if not is_main_sheet else 1)}: 数据类型为空。") # DataFrame enumerate 从0开始，加2；List从0开始，加1
                 continue

            tag_name: str
            description: str
            point_name_part_for_ioaccess: str
            comm_address = str(comm_address_raw or "").strip()

            is_point_name_empty = not (point_name_part_raw and point_name_part_raw.strip())

            if is_main_sheet and is_point_name_empty: # 主表且HMI名称为空，视为预留点位
                channel_no = str(channel_no_raw or f"Row{index + 1}").strip()
                tag_name = f'{site_no_from_file or ""}YLDW{channel_no}'
                description = f"预留点位{channel_no}"
                point_name_part_for_ioaccess = tag_name
                logger.debug(f"检测到主IO表点位 {index + 1} 为预留点位 (通道: {channel_no})，生成默认 TagName: {tag_name}")
            elif not is_main_sheet and is_point_name_empty: # 第三方表且变量名为空
                 logger.warning(f"跳过第三方表行 {index + 2}: 变量名为空。")
                 continue
            else: # HMI 名称存在 (主表或第三方表)
                point_name_part_for_ioaccess = str(point_name_part_raw).strip() # 保证 point_name_part_raw 非空
                tag_name = f'{site_no_from_file or ""}{point_name_part_for_ioaccess}'
                description = str(description_raw or "").strip()
            
            # 根据数据类型调整通讯地址 (ItemName)
            final_comm_address = comm_address
            if data_type == "BOOL":
                if comm_address.isdigit() and not comm_address.startswith('0'):
                    final_comm_address = f"0{comm_address}"
                # 如果已经是 "0xxxx" 或者非纯数字（如 "M3010"），则不作改变

            # --- 后续公共处理逻辑 (与之前类似) ---
            io_server_common = {
                'TagName': tag_name,
                'Description': description,
                'ChannelName': "Network1", 
                'DeviceName': site_name_from_file or "", 
                'ChannelDriver': "ModbusMaster", 
                'DeviceSeries': "ModbusTCP", 
                'DeviceSeriesType': 0, 
                'CollectControl': "否", 
                'CollectInterval': 1000, 
                'CollectOffset': 0, 
                'TimeZoneBias': 0, 
                'TimeAdjustment': 0, 
                'Enable': "是", 
                'ForceWrite': "否", 
                'ItemName': final_comm_address, # 使用调整后的通讯地址
                'HisRecordMode': "不记录", 
                'HisDeadBand': 0, 
                'HisInterval': 60, 
                'TagGroup': site_name_from_file or "", 
            }
            data_dict_common = {
                'ContainerType': 1, 
                'TagName': tag_name,
                'Description': description,
                'SecurityZoneID': None, 
                'RecordEvent': False, 
                'SaveValue': True, 
                'SaveParameter': True, 
                'AccessByOtherApplication': False, 
                'ExtentField1': None, 'ExtentField2': None, 'ExtentField3': None,
                'ExtentField4': None, 'ExtentField5': None, 'ExtentField6': None,
                'ExtentField7': None, 'ExtentField8': None,
                'AlarmGroup': site_name_from_file or "", 
                'IOConfigControl': True, 
                'IOAccess': f'Server1.{point_name_part_for_ioaccess}.Value',
                'IOEnable': True, 
                'ForceRead': False, 
                'ForceWrite': False, 
                'StateEnumTable': None, 
            }

            current_io_server_tag_id = self._io_server_tag_id_counter
            current_data_dict_tag_id = self._data_dict_tag_id_counter
            # TagID计数器应该在成功添加条目后增加

            if data_type == "BOOL":
                io_server_disc_row = {**io_server_common, 'TagID': current_io_server_tag_id, 'TagType': "用户变量", 'TagDataType': "IODisc", 'RegName': 0, 'RegType': 0, 'ItemDataType': "BIT", 'ItemAccessMode': "读写"}
                self._io_server_data['IO_DISC'].append([io_server_disc_row.get(h, '') for h in IO_SERVER_SHEETS['IO_DISC']])
                data_dict_disc_row = {**data_dict_common, 'TagID': current_data_dict_tag_id, 'InitialValueBool': False, 'HisRecMode': 2, 'HisRecInterval': 60, 'AlarmType': 256, 'CloseString': "关闭", 'OpenString': "打开", 'AlarmDelay': 0, 'AlarmPriority': 1, 'DiscInhibitor': None, 'CloseToOpen': "关到开", 'OpenToClose': "开到关", 'DataConvertMode': 1}
                self._data_dict_data['IO_DISC'].append([data_dict_disc_row.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_DISC']])
                self._io_server_tag_id_counter += 1
                self._data_dict_tag_id_counter += 1
            elif data_type == "REAL":
                io_server_float_row = {**io_server_common, 'TagID': current_io_server_tag_id, 'TagType': "用户变量", 'TagDataType': "IOFloat", 'MaxRawValue': 1000000000, 'MinRawValue': -1000000000, 'MaxValue': 1000000000, 'MinValue': -1000000000, 'NonLinearTableName': None, 'ConvertType': "无", 'IsFilter': "否", 'DeadBand': 0, 'Unit': None, 'RegName': 4, 'RegType': 3, 'ItemDataType': "FLOAT", 'ItemAccessMode': "读写"}
                self._io_server_data['IO_FLOAT'].append([io_server_float_row.get(h, '') for h in IO_SERVER_SHEETS['IO_FLOAT']])
                
                sll_val = str(sll_val_raw or '').strip()
                sl_val = str(sl_val_raw or '').strip()
                sh_val = str(sh_val_raw or '').strip()
                shh_val = str(shh_val_raw or '').strip()

                sll_enabled = bool(sll_val)
                sl_enabled = bool(sl_val)
                sh_enabled = bool(sh_val)
                shh_enabled = bool(shh_val)

                data_dict_float_row = {**data_dict_common, 'TagID': current_data_dict_tag_id, 'MaxValue': 1000000000, 'MinValue': -1000000000, 'InitialValue': 0, 'Sensitivity': 0, 'EngineerUnits': None, 'HisRecMode': 2, 'HisRecChangeDeadband': 0, 'HisRecInterval': 60,
                                     'HiHiEnabled': shh_enabled, 'HiHiLimit': shh_val if shh_enabled else '', 'HiHiText': "高高", 'HiHiPriority': 1, 'HiHiInhibitor': None,
                                     'HiEnabled': sh_enabled, 'HiLimit': sh_val if sh_enabled else '', 'HiText': "高", 'HiPriority': 1, 'HiInhibitor': None,
                                     'LoEnabled': sl_enabled, 'LoLimit': sl_val if sl_enabled else '', 'LoText': "低", 'LoPriority': 1, 'LoInhibitor': None,
                                     'LoLoEnabled': sll_enabled, 'LoLoLimit': sll_val if sll_enabled else '', 'LoLoText': "低低", 'LoLoPriority': 1, 'LoLoInhibitor': None,
                                     'LimitDeadband': 0, 'LimitDelay': 0, 'DevMajorEnabled': False, 'DevMajorLimit': 80, 'DevMajorText': "主要", 'DevMajorPriority': 1, 'MajorInhibitor': None, 'DevMinorEnabled': False, 'DevMinorLimit': 20, 'DevMinorText': "次要", 'DevMinorPriority': 1, 'MinorInhibitor': None, 'DevDeadband': 0, 'DevTargetValue': 100, 'DevDelay': 0, 'RocEnabled': False, 'RocPercent': 20, 'RocTimeUnit': 0, 'RocText': "变化率", 'RocDelay': 0, 'RocPriority': 1, 'RocInhibitor': None, 'StatusAlarmTableID': 0, 'StatusAlarmEnabled': False, 'StatusAlarmTableName': None, 'StatusInhibitor': None, 'MaxRaw': 1000000000, 'MinRaw': -1000000000, 'DataConvertMode': 1, 'NlnTableID': 0, 'AddupMaxVal': 0, 'AddupMinVal': 0}
                self._data_dict_data['IO_FLOAT'].append([data_dict_float_row.get(h, '') for h in DATA_DICTIONARY_SHEETS['IO_FLOAT']])
                self._io_server_tag_id_counter += 1
                self._data_dict_tag_id_counter += 1
            else:
                log_point_name = point_name_part_raw if point_name_part_raw and point_name_part_raw.strip() else f"(点位{index+1})"
                logger.warning(f"跳过点位 '{log_point_name}': 不支持的数据类型 '{data_type}' (原始: {data_type_raw})。仅支持 'BOOL' 或 'REAL'。")

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
                                main_io_points: Optional[List[UploadedIOPoint]], # 修改：接收 UploadedIOPoint 列表
                                third_party_sheet_data: List[Tuple[str, pd.DataFrame]], # 修改：接收第三方数据列表
                                output_dir: str,
                                base_io_filename: str
                               ) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """
        生成两个亚控点表文件，数据从传入的参数获取。
        场站编号和场站名称将从 main_io_points (如果可用) 的第一个点位中提取。
        """
        logger.info(f"开始生成亚控点表文件 (新数据模型)，输出目录: {output_dir}")
        self._reset_data()

        extracted_site_no: Optional[str] = None
        extracted_site_name: Optional[str] = None

        # 从 main_io_points 获取场站信息
        if main_io_points and len(main_io_points) > 0:
            first_point = main_io_points[0]
            if first_point.site_number and first_point.site_number.strip():
                extracted_site_no = first_point.site_number.strip()
                logger.info(f"从主IO点数据成功读取场站编号: {extracted_site_no}")
            else:
                logger.warning("主IO点数据的第一个点位场站编号为空或无效。")
            
            if first_point.site_name and first_point.site_name.strip():
                extracted_site_name = first_point.site_name.strip()
                logger.info(f"从主IO点数据成功读取场站名称: {extracted_site_name}")
            else:
                logger.warning("主IO点数据的第一个点位场站名称为空或无效。DeviceName/TagGroup可能为空。")
        else:
            logger.warning("主IO点数据列表为空，无法提取场站编号和场站名称。")

        # 处理数据
        try:
            if main_io_points:
                logger.info("开始处理主IO点表数据 (UploadedIOPoint 列表)...")
                self._process_point_data(main_io_points, is_main_sheet=True, site_name_from_file=extracted_site_name, site_no_from_file=extracted_site_no)
                logger.info("主IO点表数据处理完成。")
            else:
                logger.info("没有主IO点数据 (main_io_points is None or empty)。")
            
            if third_party_sheet_data:
                logger.info(f"开始处理 {len(third_party_sheet_data)} 个第三方设备表 (DataFrame 列表)...")
                for i, (sheet_name, tp_df_item) in enumerate(third_party_sheet_data):
                    logger.info(f"处理第 {i+1} 个第三方DataFrame (Sheet: '{sheet_name}')...")
                    self._process_point_data(tp_df_item, is_main_sheet=False, site_name_from_file=extracted_site_name, site_no_from_file=extracted_site_no)
                logger.info("所有第三方设备数据处理完成。")
            else:
                logger.info("没有第三方设备数据 (third_party_sheet_data is empty)。")

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
        
        final_error_message = "\n".join(error_messages) if error_messages else None

        if all_success: logger.info("所有亚控点表文件均已成功生成并填充数据。")
        else: logger.error(f"生成亚控点表文件时发生错误: {final_error_message}")
        return all_success, io_server_filepath, data_dictionary_filepath, final_error_message


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # 创建示例 UploadedIOPoint 数据
    sample_main_points: List[UploadedIOPoint] = [
        UploadedIOPoint(site_name="测试站", site_number="S007", hmi_variable_name="YK_AI_01", variable_description="亚控模拟输入1", data_type="REAL", hmi_communication_address="40001", channel_tag="AI_CH1", sll_set_value="1", sl_set_value="2", sh_set_value="98", shh_set_value="99"),
        UploadedIOPoint(site_name="测试站", site_number="S007", hmi_variable_name="YK_DI_01", variable_description="亚控数字输入1", data_type="BOOL", hmi_communication_address="10001", channel_tag="DI_CH1"),
        UploadedIOPoint(site_name="测试站", site_number="S007", hmi_variable_name=None, channel_tag="Res_CH1", variable_description=None, data_type="REAL", hmi_communication_address="40002"), # 预留点
    ]
    sample_main_points_empty: List[UploadedIOPoint] = []

    # 创建示例第三方 DataFrame 数据
    tp_data1 = {
        C.TP_VAR_NAME_COL: ["TP1_BOOL_1", "TP1_REAL_1"],
        C.TP_DESCRIPTION_COL: ["第三方1布尔", "第三方1实数"],
        C.TP_DATA_TYPE_COL: ["BOOL", "REAL"],
        C.TP_MODBUS_ADDR_COL: ["2001", "50001"],
        C.SLL_SET_COL: [None, "5.5"],
    }
    df_tp1 = pd.DataFrame(tp_data1)
    tp_data2 = {
        C.TP_VAR_NAME_COL: ["TP2_BOOL_X"],
        C.TP_DESCRIPTION_COL: ["第三方2布尔X"],
        C.TP_DATA_TYPE_COL: ["BOOL"],
        C.TP_MODBUS_ADDR_COL: ["2005"],
    }
    df_tp2 = pd.DataFrame(tp_data2)
    df_tp_empty = pd.DataFrame(columns=[C.TP_VAR_NAME_COL, C.TP_DESCRIPTION_COL, C.TP_DATA_TYPE_COL, C.TP_MODBUS_ADDR_COL])

    third_party_sheets: List[Tuple[str, pd.DataFrame]] = [
        ("第三方设备表A", df_tp1),
        ("第三方设备表B_空", df_tp_empty),
        ("第三方设备表C", df_tp2),
    ]
    third_party_sheets_empty: List[Tuple[str, pd.DataFrame]] = []

    test_output_dir = "./test_kingview_output_new_model"
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    generator = KingViewGenerator()

    logger.info("--- 测试场景1: 完整数据 ---")
    success1, f1_1, f2_1, err1 = generator.generate_kingview_files(
        sample_main_points, third_party_sheets, test_output_dir, "FullDataTest"
    )
    if success1: print(f"场景1成功: {f1_1}, {f2_1}")
    else: print(f"场景1失败: {err1}")

    generator._reset_data() # 重置内部计数器和数据存储
    logger.info("--- 测试场景2: 只有主IO点数据 ---")
    success2, f1_2, f2_2, err2 = generator.generate_kingview_files(
        sample_main_points, third_party_sheets_empty, test_output_dir, "MainOnlyTest"
    )
    if success2: print(f"场景2成功: {f1_2}, {f2_2}")
    else: print(f"场景2失败: {err2}")

    generator._reset_data()
    logger.info("--- 测试场景3: 只有第三方数据 ---")
    success3, f1_3, f2_3, err3 = generator.generate_kingview_files(
        None, third_party_sheets, test_output_dir, "ThirdPartyOnlyTest"
    )
    if success3: print(f"场景3成功: {f1_3}, {f2_3}")
    else: print(f"场景3失败: {err3}")

    generator._reset_data()
    logger.info("--- 测试场景4: 主IO点数据为空列表 ---")
    success4, f1_4, f2_4, err4 = generator.generate_kingview_files(
        sample_main_points_empty, third_party_sheets, test_output_dir, "MainEmptyListTest"
    )
    if success4: print(f"场景4成功: {f1_4}, {f2_4}")
    else: print(f"场景4失败: {err4}")

    generator._reset_data()
    logger.info("--- 测试场景5: 所有输入都为空/None ---")
    success5, f1_5, f2_5, err5 = generator.generate_kingview_files(
        None, third_party_sheets_empty, test_output_dir, "AllEmptyTest"
    )
    if success5: print(f"场景5成功: {f1_5}, {f2_5}") # 应该能生成空的结构文件
    else: print(f"场景5失败: {err5}") 