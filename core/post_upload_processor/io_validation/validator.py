# core/post_upload_processor/io_validation/validator.py
import os
import pandas as pd
from typing import Tuple, List, Dict, Any, Optional
from abc import ABC, abstractmethod # 导入 ABC 和 abstractmethod

# 从 constants.py 导入常量
from . import constants as C

# 定义常量，方便维护
# --- 主IO点表Sheet列名 ---
# HMI_NAME_COL = "变量名称（HMI）"
# DESCRIPTION_COL = "变量描述"
# POWER_SUPPLY_TYPE_COL = "供电类型（有源/无源）"
# WIRING_SYSTEM_COL = "线制"
# MODULE_TYPE_COL = "模块类型" # 虽然当前规则未直接使用，但保留以备将来参考
# RANGE_LOW_LIMIT_COL = "量程低限"
# RANGE_HIGH_LIMIT_COL = "量程高限"
# SLL_SET_COL = "SLL设定值" # 主IO点表的SLL
# SL_SET_COL = "SL设定值"   # 主IO点表的SL
# SH_SET_COL = "SH设定值"   # 主IO点表的SH
# SHH_SET_COL = "SHH设定值" # 主IO点表的SHH
# PLC_IO_SHEET_NAME = "IO点表" # 这是 excel_exporter.py 中 PLCSheetExporter 生成的表名

# --- 第三方设备点表Sheet列名 (新增) ---
# TP_INPUT_VAR_NAME_COL = "变量名称" # 用于错误消息中定位点位
# TP_INPUT_DATA_TYPE_COL = "数据类型"
# TP_INPUT_SLL_SET_COL = "SLL设定值"
# TP_INPUT_SL_SET_COL = "SL设定值"
# TP_INPUT_SH_SET_COL = "SH设定值"
# TP_INPUT_SHH_SET_COL = "SHH设定值"

# 允许值常量
# ALLOWED_POWER_SUPPLY_VALUES: List[str] = ["有源", "无源"]
# ALLOWED_WIRING_SYSTEM_VALUES: List[str] = ["2线制", "两线制", "三线制", "四线制", "3线制", "4线制"]
# ALLOWED_WIRING_SYSTEM_VALUES_DI_DO: List[str] = ["常开", "常闭"] # 新增DI/DO线制允许值

# --- 辅助函数 ---

def _is_value_present(value) -> bool:
    """
    辅助函数：检查单元格的值是否被视为空。
    将 NaN, None, 和空字符串（去除空格后）视为空。
    """
    if pd.isna(value): # 处理 NaN 和 None
        return False
    if isinstance(value, str) and not value.strip(): # 处理空字符串或只包含空格的字符串
        return False
    # Check for numeric types that might be zero but are still present
    # if isinstance(value, (int, float)) and value == 0:
    #     return True # 0 is considered present
    return True


def _is_numeric(value) -> bool:
    """辅助函数：检查值是否可以转换为浮点数。"""
    if not _is_value_present(value): # 如果本身就空，不算数字（也不算错误，除非是必填项）
        return True # 对于"允许为空但填写了必须是数字"的场景，空值通过此检查
    # 显式排除布尔类型
    if isinstance(value, bool):
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def _format_error_message(
    sheet_name: str,
    row_number: int,
    message: str,
    point_name: Optional[str] = None,
    column_name: Optional[str] = None,
    value: Optional[Any] = None,
) -> str:
    """
    统一格式化错误消息。

    参数:
        sheet_name (str): 工作表名称。
        row_number (int): Excel 中的行号（从1开始，表头为第1行）。
        message (str): 主要错误描述。
        point_name (Optional[str]): 点位名称（如果适用）。
        column_name (Optional[str]): 相关的列名（如果适用）。
        value (Optional[Any]): 相关的值（如果适用）。

    返回:
        str: 格式化后的错误消息。
    """
    location = f'工作表:"{sheet_name}", Excel行号:{row_number}'
    if point_name:
        location += f', 点位:{point_name}'
    if column_name:
        location += f', 列:"{column_name}"'
    if _is_value_present(value): # 仅在值非空时显示
         # 避免在消息中打印过长或复杂的对象，只取其字符串表示的前50个字符
        value_str = str(value)
        display_value = value_str[:50] + '...' if len(value_str) > 50 else value_str
        location += f', 值:"{display_value}"'

    return f'验证失败 ({location}):\n{message}'


# --- 校验规则定义 --- #

class ValidationContext:
    """存储校验过程中可能需要的上下文信息。"""
    def __init__(self, row: pd.Series, excel_row_number: int, sheet_name: str):
        self.row = row
        self.excel_row_number = excel_row_number
        self.sheet_name = sheet_name
        # 预计算一些常用值，避免重复获取和计算
        self.hmi_name = row.get(C.HMI_NAME_COL)
        self.description = row.get(C.DESCRIPTION_COL)
        self.module_type = str(row.get(C.MODULE_TYPE_COL, "")).upper().strip()
        self.data_type = str(row.get(C.TP_INPUT_DATA_TYPE_COL, "")).upper().strip()

        self.hmi_name_present = _is_value_present(self.hmi_name)
        self.description_present = _is_value_present(self.description)
        # 主 IO 表判断是否为预留点位（基于 HMI 名称）
        self.is_main_reserved = not self.hmi_name_present

class ValidationRule(ABC):
    """校验规则的抽象基类。"""

    @abstractmethod
    def validate(self, context: ValidationContext) -> List[str]:
        """执行校验逻辑，返回错误消息列表 (空列表表示无错误)。"""
        pass

# --- 主 IO 表规则实现 --- #

class HmiDescriptionConsistencyRule(ValidationRule):
    """规则：HMI 名称和描述必须同时填写或同时为空。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if context.hmi_name_present != context.description_present:
            col1_status = "已填写" if context.hmi_name_present else "为空"
            col2_status = "已填写" if context.description_present else "为空"
            errors.append(_format_error_message(
                context.sheet_name, context.excel_row_number,
                f'"{C.HMI_NAME_COL}"({col1_status}) 与 "{C.DESCRIPTION_COL}"({col2_status}) 状态不一致。两者必须同时填写或同时为空。'
            ))
        return errors

class ReservedPointEmptyRule(ValidationRule):
    """规则：预留点位的某些列必须为空。"""
    def __init__(self, column: str, column_name_cn: str):
        self.column = column
        self.column_name_cn = column_name_cn

    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if context.is_main_reserved:
            value = context.row.get(self.column)
            if _is_value_present(value):
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'该行为预留点位，但"{self.column_name_cn}"不为空。预留点位的此列必须为空。',
                    column_name=self.column_name_cn, value=value
                ))
        return errors

class NonReservedRequiredRule(ValidationRule):
    """规则：非预留点位的某些列必须填写。"""
    def __init__(self, column: str, column_name_cn: str):
        self.column = column
        self.column_name_cn = column_name_cn

    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if not context.is_main_reserved:
            value = context.row.get(self.column)
            if not _is_value_present(value):
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'该行为非预留点位，但"{self.column_name_cn}"为空。此列必填。',
                    column_name=self.column_name_cn
                ))
        return errors

class PowerSupplyValueRule(ValidationRule):
    """规则：非预留点位的供电类型值必须有效。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if not context.is_main_reserved:
            value = context.row.get(C.POWER_SUPPLY_TYPE_COL)
            if _is_value_present(value): # 只有在填写了才校验值
                actual_value = str(value).strip()
                if actual_value not in C.ALLOWED_POWER_SUPPLY_VALUES:
                    errors.append(_format_error_message(
                        context.sheet_name, context.excel_row_number,
                        f'"{C.POWER_SUPPLY_TYPE_COL}"的值无效。只允许填写: {", ".join(C.ALLOWED_POWER_SUPPLY_VALUES)}。',
                        column_name=C.POWER_SUPPLY_TYPE_COL, value=actual_value
                    ))
        return errors

# --- 新增的主 IO 表规则 ---

class WiringSystemValueRule(ValidationRule):
    """规则：非预留点位的线制值必须有效，且符合其模块类型的要求。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if not context.is_main_reserved:
            value = context.row.get(C.WIRING_SYSTEM_COL)
            if _is_value_present(value): # 只有在填写了才校验值
                actual_value = str(value).strip()
                module_type = context.module_type

                if module_type in [C.MODULE_TYPE_AI, C.MODULE_TYPE_AO]:
                    if actual_value not in C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO:
                        errors.append(_format_error_message(
                            context.sheet_name, context.excel_row_number,
                            f'"{C.WIRING_SYSTEM_COL}"的值对AI/AO模块无效 (模块类型: {module_type})。允许的值为: {", ".join(C.ALLOWED_WIRING_SYSTEM_VALUES_AI_AO)}。',
                            column_name=C.WIRING_SYSTEM_COL, value=actual_value
                        ))
                elif module_type in [C.MODULE_TYPE_DI, C.MODULE_TYPE_DO]:
                    if actual_value not in C.ALLOWED_WIRING_SYSTEM_VALUES_DI_DO:
                        errors.append(_format_error_message(
                            context.sheet_name, context.excel_row_number,
                            f'"{C.WIRING_SYSTEM_COL}"的值对DI/DO模块无效 (模块类型: {module_type})。允许的值为: {", ".join(C.ALLOWED_WIRING_SYSTEM_VALUES_DI_DO)}。',
                            column_name=C.WIRING_SYSTEM_COL, value=actual_value
                        ))
                elif not module_type: # 未知模块类型
                     errors.append(_format_error_message(
                         context.sheet_name, context.excel_row_number,
                         f'"{C.MODULE_TYPE_COL}"为空，无法确定"{C.WIRING_SYSTEM_COL}"的有效值。请填写模块类型。',
                         column_name=C.MODULE_TYPE_COL))
                # else: 其他模块类型，线制不做校验
        return errors

class RangeRequiredAiRule(ValidationRule):
    """规则：非预留AI模块点位，量程上下限必须填写。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if not context.is_main_reserved and context.module_type == C.MODULE_TYPE_AI:
            low_limit = context.row.get(C.RANGE_LOW_LIMIT_COL)
            high_limit = context.row.get(C.RANGE_HIGH_LIMIT_COL)
            if not _is_value_present(low_limit):
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'该行为非预留点位AI模块，但"{C.RANGE_LOW_LIMIT_COL}"为空。此列必填。',
                    column_name=C.RANGE_LOW_LIMIT_COL
                ))
            if not _is_value_present(high_limit):
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'该行为非预留点位AI模块，但"{C.RANGE_HIGH_LIMIT_COL}"为空。此列必填。',
                    column_name=C.RANGE_HIGH_LIMIT_COL
                ))
        return errors

class NumericValueRule(ValidationRule):
    """基础规则：校验指定列的值（如果存在）是否为数字。"""
    def __init__(self, column: str, column_name_cn: str):
        self.column = column
        self.column_name_cn = column_name_cn

    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        value = context.row.get(self.column)
        if _is_value_present(value) and not _is_numeric(value):
            errors.append(_format_error_message(
                context.sheet_name, context.excel_row_number,
                f'"{self.column_name_cn}"的值无效。必须为整数或小数。',
                column_name=self.column_name_cn, value=value
            ))
        return errors

class RangeNumericAiRule(NumericValueRule):
    """规则：非预留AI模块点位，量程上下限（如果存在）必须为数字。"""
    def __init__(self, column: str, column_name_cn: str):
        super().__init__(column, column_name_cn)

    def validate(self, context: ValidationContext) -> List[str]:
        # 只对非预留 AI 模块应用此规则
        if not context.is_main_reserved and context.module_type == C.MODULE_TYPE_AI:
            return super().validate(context)
        return []

class SetpointNumericAiRule(NumericValueRule):
    """规则：非预留AI模块点位，设定值（如果存在）必须为数字。"""
    def __init__(self, column: str, column_name_cn: str):
        super().__init__(column, column_name_cn)

    def validate(self, context: ValidationContext) -> List[str]:
        # 只对非预留 AI 模块应用此规则
        if not context.is_main_reserved and context.module_type == C.MODULE_TYPE_AI:
            return super().validate(context)
        return []


class ReservedAiSpecificEmptyRule(ValidationRule):
    """规则：预留AI模块点位，量程和设定值相关列必须为空。"""
    def __init__(self, column: str, column_name_cn: str):
        self.column = column
        self.column_name_cn = column_name_cn

    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        # 只对预留 AI 模块应用此规则
        if context.is_main_reserved and context.module_type == C.MODULE_TYPE_AI:
            value = context.row.get(self.column)
            if _is_value_present(value):
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'该行为预留点位(模块类型: {context.module_type})，但"{self.column_name_cn}"不为空。预留点位的此列必须为空。',
                    column_name=self.column_name_cn, value=value
                ))
        return errors


# --- 第三方表规则实现 --- #

class RealSetpointUniquenessRule(ValidationRule):
    """规则：数据类型为 REAL 的点，其 SLL, SL, SH, SHH 中最多只能有一个有效值。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if context.data_type == C.DATA_TYPE_REAL:
            setpoint_cols = {
                C.TP_INPUT_SLL_SET_COL: context.row.get(C.TP_INPUT_SLL_SET_COL),
                C.TP_INPUT_SL_SET_COL: context.row.get(C.TP_INPUT_SL_SET_COL),
                C.TP_INPUT_SH_SET_COL: context.row.get(C.TP_INPUT_SH_SET_COL),
                C.TP_INPUT_SHH_SET_COL: context.row.get(C.TP_INPUT_SHH_SET_COL),
            }
            present_settings_count = 0
            settings_values = []
            for col_name, val in setpoint_cols.items():
                if _is_value_present(val):
                    present_settings_count += 1
                    settings_values.append(f"{col_name}='{val}'")

            if present_settings_count > 1:
                var_name_value = str(context.row.get(C.TP_INPUT_VAR_NAME_COL, f"行 {context.excel_row_number} 未命名点位"))
                errors.append(_format_error_message(
                    context.sheet_name, context.excel_row_number,
                    f'数据类型为REAL的点，其SLL, SL, SH, SHH设定值中存在多个有效值 ({", ".join(settings_values)})。一个点在这些列中最多只能有一个有效值。',
                    point_name=var_name_value
                ))
        return errors

# --- 新增的第三方表规则 --- #

class BoolSetpointEmptyRule(ValidationRule):
    """规则：数据类型为 BOOL 的点，其 SLL, SL, SH, SHH 设定值列必须为空。"""
    def validate(self, context: ValidationContext) -> List[str]:
        errors = []
        if context.data_type == C.DATA_TYPE_BOOL: # 检查是否为 BOOL 类型
            setpoint_cols_to_check = {
                C.TP_INPUT_SLL_SET_COL: "SLL 设定值",
                C.TP_INPUT_SL_SET_COL: "SL 设定值",
                C.TP_INPUT_SH_SET_COL: "SH 设定值",
                C.TP_INPUT_SHH_SET_COL: "SHH 设定值",
            }
            for col_const, col_name_cn in setpoint_cols_to_check.items():
                value = context.row.get(col_const)
                if _is_value_present(value):
                    var_name_value = str(context.row.get(C.TP_INPUT_VAR_NAME_COL, f"行 {context.excel_row_number} 未命名点位"))
                    errors.append(_format_error_message(
                        context.sheet_name, context.excel_row_number,
                        f'数据类型为BOOL的点，其设定值列 "{col_name_cn}" 不应填写数据。请清空该单元格。',
                        point_name=var_name_value,
                        column_name=col_name_cn,
                        value=value
                    ))
            # 因为可能同时填了多个，所以检查完所有列再返回
        return errors

# --- 规则注册表 (更新) --- #

MAIN_IO_RULES: List[ValidationRule] = [
    # 通用规则
    HmiDescriptionConsistencyRule(),
    # 针对预留点位
    ReservedPointEmptyRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）"),
    ReservedPointEmptyRule(C.WIRING_SYSTEM_COL, "线制"),
    # 针对预留 AI 点位
    ReservedAiSpecificEmptyRule(C.RANGE_LOW_LIMIT_COL, "量程低限"),
    ReservedAiSpecificEmptyRule(C.RANGE_HIGH_LIMIT_COL, "量程高限"),
    ReservedAiSpecificEmptyRule(C.SLL_SET_COL, "SLL设定值"),
    ReservedAiSpecificEmptyRule(C.SL_SET_COL, "SL设定值"),
    ReservedAiSpecificEmptyRule(C.SH_SET_COL, "SH设定值"),
    ReservedAiSpecificEmptyRule(C.SHH_SET_COL, "SHH设定值"),
    # 针对非预留点位
    NonReservedRequiredRule(C.POWER_SUPPLY_TYPE_COL, "供电类型（有源/无源）"),
    NonReservedRequiredRule(C.WIRING_SYSTEM_COL, "线制"),
    PowerSupplyValueRule(),
    WiringSystemValueRule(),
    # 针对非预留 AI 点位
    RangeRequiredAiRule(),
    RangeNumericAiRule(C.RANGE_LOW_LIMIT_COL, "量程低限"),
    RangeNumericAiRule(C.RANGE_HIGH_LIMIT_COL, "量程高限"),
    SetpointNumericAiRule(C.SLL_SET_COL, "SLL设定值"),
    SetpointNumericAiRule(C.SL_SET_COL, "SL设定值"),
    SetpointNumericAiRule(C.SH_SET_COL, "SH设定值"),
    SetpointNumericAiRule(C.SHH_SET_COL, "SHH设定值"),
]

THIRD_PARTY_RULES: List[ValidationRule] = [
    RealSetpointUniquenessRule(),
    BoolSetpointEmptyRule(), # 添加新规则
]

# --- 重构后的行级校验函数 (示例) --- #

def _validate_row_with_rules(row: pd.Series, excel_row_number: int, sheet_name: str, rules: List[ValidationRule]) -> List[str]:
    """使用指定的规则列表校验单行数据。"""
    all_errors: List[str] = []
    context = ValidationContext(row, excel_row_number, sheet_name)

    for rule in rules:
        # 可以添加一个 applies_to 方法到规则类，用于更精细的控制
        # if rule.applies_to(context):
        errors = rule.validate(context)
        all_errors.extend(errors)

    return all_errors

# --- Sheet 级校验函数 (需要更新以使用新行级校验) --- #

def _validate_main_io_sheet(df: pd.DataFrame, sheet_name: str) -> List[str]:
    """校验主IO点表Sheet (使用规则注册表)。"""
    errors: List[str] = []
    required_cols_main = [
        C.HMI_NAME_COL, C.DESCRIPTION_COL, C.POWER_SUPPLY_TYPE_COL, C.WIRING_SYSTEM_COL,
        C.MODULE_TYPE_COL, C.RANGE_LOW_LIMIT_COL, C.RANGE_HIGH_LIMIT_COL,
        C.SLL_SET_COL, C.SL_SET_COL, C.SH_SET_COL, C.SHH_SET_COL
    ]
    missing_cols_main = [col for col in required_cols_main if col not in df.columns]
    if missing_cols_main:
        for col_name in missing_cols_main:
            errors.append(f'验证失败：主工作表"{sheet_name}"中缺少必需的列"{col_name}"。')
        return errors # 缺少列则不进行行校验

    for index, row in df.iterrows():
        excel_row_number = index + 2 # Excel行号从1开始，Dataframe索引从0开始，表头占1行
        # 使用新的基于规则的校验函数
        row_errors = _validate_row_with_rules(row, excel_row_number, sheet_name, MAIN_IO_RULES)
        errors.extend(row_errors)

    return errors

def _validate_third_party_sheet(df: pd.DataFrame, sheet_name: str) -> List[str]:
    """校验第三方设备点表Sheet (使用规则注册表)。"""
    errors: List[str] = []
    # 检查第三方表校验设定值所需的列是否存在 (这部分逻辑可以保留)
    required_tp_cols_for_setpoint_check = [
        C.TP_INPUT_VAR_NAME_COL, C.TP_INPUT_DATA_TYPE_COL,
        C.TP_INPUT_SLL_SET_COL, C.TP_INPUT_SL_SET_COL,
        C.TP_INPUT_SH_SET_COL, C.TP_INPUT_SHH_SET_COL
    ]
    missing_tp_cols = [col for col in required_tp_cols_for_setpoint_check if col not in df.columns]
    if missing_tp_cols:
        for col_name in missing_tp_cols:
            errors.append(f'验证失败：工作表"{sheet_name}"中缺少校验设定值所必需的列"{col_name}"。无法对该表执行设定值唯一性校验。')
        # 即使缺少列，仍可以继续用规则校验其他列，所以不直接 return

    for index, row in df.iterrows():
        excel_row_number = index + 2
        # 使用新的基于规则的校验函数
        # 注意：RealSetpointUniquenessRule 需要的列如果缺失，它内部应该能处理或我们在调用前检查
        row_errors = _validate_row_with_rules(row, excel_row_number, sheet_name, THIRD_PARTY_RULES)
        errors.extend(row_errors)

    return errors

# --- 主校验入口函数 (无需大改，因为它调用 Sheet 级函数) --- #

def validate_io_table(file_path: str) -> Tuple[bool, str]:
    """
    验证上传的IO点表文件。包括主IO点表和所有其他（第三方设备）点表。
    (文档字符串可能需要更新以反映实现方式的变化)
    """
    error_messages: List[str] = []

    # --- 文件存在性和格式基础校验 ---
    if not file_path:
        return False, "错误：未提供文件路径。"
    if not os.path.exists(file_path):
        return False, f"错误：文件未找到: {file_path}。"
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in ['.xlsx', '.xls']:
        return False, f"错误：文件格式无效: {ext}。请上传有效的 Excel 文件 (.xlsx 或 .xls)。"

    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names

        if not sheet_names:
            return False, f'验证失败：Excel文件 "{os.path.basename(file_path)}" 中不包含任何工作表。'

        main_sheet_found = False
        # --- 遍历所有Sheet进行校验 ---
        for sheet_name in sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=sheet_name)

                if df.empty:
                    continue

                if sheet_name == C.PLC_IO_SHEET_NAME:
                    main_sheet_found = True
                    # 调用更新后的 Sheet 校验函数
                    sheet_errors = _validate_main_io_sheet(df, sheet_name)
                    error_messages.extend(sheet_errors)
                else:
                    # 调用更新后的 Sheet 校验函数
                    sheet_errors = _validate_third_party_sheet(df, sheet_name)
                    error_messages.extend(sheet_errors)

            except ValueError as ve: # 特定Sheet读取错误 (例如找不到名字 - 虽然我们是迭代获取的，理论上不会发生)
                 error_messages.append(f'验证失败：读取工作表"{sheet_name}"时出错: {str(ve)}。')
            except Exception as e_read_sheet: # pylint: disable=broad-except
                 error_messages.append(f'验证失败：处理工作表"{sheet_name}"时发生未知错误: {str(e_read_sheet)}。')

        # 检查主IO点表是否存在
        if not main_sheet_found:
             error_messages.append(f'验证警告：在Excel文件中未找到强制要求的主工作表"{C.PLC_IO_SHEET_NAME}"。已完成对其他工作表的校验（如果存在）。')


    except pd.errors.EmptyDataError:
        return False, f'文件"{os.path.basename(file_path)}"为空或不包含可读数据。'
    except FileNotFoundError: # ExcelFile 构造时可能抛出
         return False, f"错误：文件未找到: {file_path}。"
    except ValueError as ve_general: # 可能由 ExcelFile 引起，如文件损坏
         return False, f'读取Excel文件时发生错误: {str(ve_general)}。文件可能已损坏或格式不兼容。'
    except Exception as e: # pylint: disable=broad-except
        # 捕获未预料到的其他异常，例如权限问题
        return False, f'验证过程中发生未知错误: {str(e)}。'

    # --- 返回结果 ---
    if error_messages:
        # 使用换行符连接所有错误消息
        return False, "\n".join(error_messages)
    else:
        success_msg = f'文件"{os.path.basename(file_path)}"的所有工作表数据验证通过。'
    return True, success_msg 

# validate_io_table 函数体较长，可拆分为多个小函数（如：主表校验、第三方表校验、单行校验等）。
# 错误信息的拼接可用专门的格式化函数，提升一致性。
# 批量错误收集：错误信息收集已做得很好，但如有更复杂的校验（如跨Sheet、跨行的依赖），可考虑引入"校验规则注册表"模式，便于统一管理和扩展。
# 代码结构解耦（如常量集中、函数拆分）

# 错误信息的拼接可用专门的格式化函数，提升一致性。
# 批量错误收集：错误信息收集已做得很好，但如有更复杂的校验（如跨Sheet、跨行的依赖），可考虑引入"校验规则注册表"模式，便于统一管理和扩展。
# 代码结构解耦（如常量集中、函数拆分） 