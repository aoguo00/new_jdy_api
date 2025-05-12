# core/post_upload_processor/io_validation/validator.py
import os
import pandas as pd
from typing import Tuple, List

# 定义常量，方便维护
# --- 主IO点表Sheet列名 ---
HMI_NAME_COL = "变量名称（HMI）"
DESCRIPTION_COL = "变量描述"
POWER_SUPPLY_TYPE_COL = "供电类型（有源/无源）"
WIRING_SYSTEM_COL = "线制"
MODULE_TYPE_COL = "模块类型" # 虽然当前规则未直接使用，但保留以备将来参考
RANGE_LOW_LIMIT_COL = "量程低限"
RANGE_HIGH_LIMIT_COL = "量程高限"
SLL_SET_COL = "SLL设定值" # 主IO点表的SLL
SL_SET_COL = "SL设定值"   # 主IO点表的SL
SH_SET_COL = "SH设定值"   # 主IO点表的SH
SHH_SET_COL = "SHH设定值" # 主IO点表的SHH
PLC_IO_SHEET_NAME = "IO点表" # 这是 excel_exporter.py 中 PLCSheetExporter 生成的表名

# --- 第三方设备点表Sheet列名 (新增) ---
TP_INPUT_VAR_NAME_COL = "变量名称" # 用于错误消息中定位点位
TP_INPUT_DATA_TYPE_COL = "数据类型"
TP_INPUT_SLL_SET_COL = "SLL设定值"
TP_INPUT_SL_SET_COL = "SL设定值"
TP_INPUT_SH_SET_COL = "SH设定值"
TP_INPUT_SHH_SET_COL = "SHH设定值"

# 允许值常量
ALLOWED_POWER_SUPPLY_VALUES: List[str] = ["有源", "无源"]
ALLOWED_WIRING_SYSTEM_VALUES: List[str] = ["2线制", "两线制", "三线制", "四线制", "3线制", "4线制"]
ALLOWED_WIRING_SYSTEM_VALUES_DI_DO: List[str] = ["常开", "常闭"] # 新增DI/DO线制允许值

def _is_value_present(value) -> bool:
    """
    辅助函数：检查单元格的值是否被视为空。
    considère NaN, None, et les chaînes de caractères vides (après suppression des espaces) comme vides.
    """
    if pd.isna(value): # 处理 NaN 和 None
        return False
    if isinstance(value, str) and not value.strip(): # 处理空字符串或只包含空格的字符串
        return False
    return True

def _is_numeric(value) -> bool:
    """辅助函数：检查值是否可以转换为浮点数。"""
    if not _is_value_present(value): # 如果本身就空，不算数字（也不算错误，除非是必填项）
        return True # 对于"允许为空但填写了必须是数字"的场景，空值通过此检查
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def validate_io_table(file_path: str) -> Tuple[bool, str]:
    """
    验证上传的IO点表文件。
    包括主IO点表和所有其他（第三方设备）点表。
    主IO点表规则：
    1. 在 "IO点表" Sheet页中，"变量名称（HMI）" 和 "变量描述" 必须同时填写或同时为空。
    2. 基于上述规则：
        - 如果是预留点位（HMI名称和描述都为空）："供电类型"和"线制"必须为空。
        - 如果不是预留点位："供电类型"和"线制"必须填写。
            - "供电类型" 只能是 "有源" 或 "无源"。
            - "线制" 只能是 ["2线制", "两线制", "三线制", "四线制", "3线制", "4线制"] 中的一个。
    3. "量程低限" 和 "量程高限":
        - 如果是预留点位：必须为空。
        - 如果不是预留点位：必须填写。
    4. "SLL设定值", "SL设定值", "SH设定值", "SHH设定值":
        - 如果是预留点位：必须为空。
        - 如果不是预留点位：如果填写了，则内容必须是整数或小数 (允许为空)。
    第三方设备点表规则 (新增):
    1. 对于数据类型为 "REAL" 的点，其 "SLL设定值", "SL设定值", "SH设定值", "SHH设定值" 中最多只能有一个被有效填写。

    参数:
        file_path (str): 文件的完整路径。

    返回:
        Tuple[bool, str]: (验证是否通过, 消息)
    """
    error_messages: List[str] = []

    if not file_path:
        return False, "错误：未提供文件路径。"
    if not os.path.exists(file_path):
        return False, f"文件未找到: {file_path}。"
    _, ext = os.path.splitext(file_path)
    if ext.lower() not in ['.xlsx', '.xls']:
        return False, f"文件格式无效: {ext}。\n请上传有效的 Excel 文件 (.xlsx 或 .xls)。"

    try:
        xls = pd.ExcelFile(file_path)
        sheet_names = xls.sheet_names

        if not sheet_names:
            return False, f'验证失败：Excel文件 "{os.path.basename(file_path)}" 中不包含任何工作表。'

        # --- 1. 校验主IO点表 (PLC_IO_SHEET_NAME) ---
        if PLC_IO_SHEET_NAME in sheet_names:
            try:
                df_main = pd.read_excel(xls, sheet_name=PLC_IO_SHEET_NAME)
                required_cols_main = [
                    HMI_NAME_COL, DESCRIPTION_COL, POWER_SUPPLY_TYPE_COL, WIRING_SYSTEM_COL,
                    MODULE_TYPE_COL, RANGE_LOW_LIMIT_COL, RANGE_HIGH_LIMIT_COL,
                    SLL_SET_COL, SL_SET_COL, SH_SET_COL, SHH_SET_COL
                ]
                missing_cols_main = [col for col in required_cols_main if col not in df_main.columns]
                if missing_cols_main:
                    for col_name in missing_cols_main:
                        error_messages.append(f'验证失败：主工作表"{PLC_IO_SHEET_NAME}"中缺少必需的列"{col_name}"。')
                else: # 只有在主表列齐全的情况下才进行行校验
                    for index, row in df_main.iterrows():
                        excel_row_number = index + 2
                        hmi_name_value = row.get(HMI_NAME_COL)
                        description_value = row.get(DESCRIPTION_COL)
                        power_supply_value = row.get(POWER_SUPPLY_TYPE_COL)
                        wiring_system_value = row.get(WIRING_SYSTEM_COL)
                        low_limit_value = row.get(RANGE_LOW_LIMIT_COL)
                        high_limit_value = row.get(RANGE_HIGH_LIMIT_COL)
                        sll_value = row.get(SLL_SET_COL)
                        sl_value = row.get(SL_SET_COL)
                        sh_value = row.get(SH_SET_COL)
                        shh_value = row.get(SHH_SET_COL)
                        module_type_value = str(row.get(MODULE_TYPE_COL, "")).upper().strip()
                        hmi_name_has_content = _is_value_present(hmi_name_value)
                        description_has_content = _is_value_present(description_value)
                        power_supply_has_content = _is_value_present(power_supply_value)
                        wiring_system_has_content = _is_value_present(wiring_system_value)
                        low_limit_has_content = _is_value_present(low_limit_value)
                        high_limit_has_content = _is_value_present(high_limit_value)
                        sll_has_content = _is_value_present(sll_value)
                        sl_has_content = _is_value_present(sl_value)
                        sh_has_content = _is_value_present(sh_value)
                        shh_has_content = _is_value_present(shh_value)
                        if hmi_name_has_content != description_has_content:
                            col1_status = "已填写" if hmi_name_has_content else "为空"
                            col2_status = "已填写" if description_has_content else "为空"
                            error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n"{HMI_NAME_COL}"({col1_status}) 与 "{DESCRIPTION_COL}"({col2_status}) 状态不一致。\n两者必须同时填写或同时为空。')
                        is_reserved_point = not hmi_name_has_content
                        if is_reserved_point:
                            if power_supply_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n该行为预留点位，但"{POWER_SUPPLY_TYPE_COL}"不为空("{power_supply_value}")。\n预留点位的此列必须为空。')
                            if wiring_system_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n该行为预留点位，但"{WIRING_SYSTEM_COL}"不为空("{wiring_system_value}")。\n预留点位的此列必须为空。')
                            if module_type_value == "AI":
                                if low_limit_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n该行为预留点位，但"{RANGE_LOW_LIMIT_COL}"不为空("{low_limit_value}")。\n预留点位的此列必须为空。')
                                if high_limit_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n该行为预留点位，但"{RANGE_HIGH_LIMIT_COL}"不为空("{high_limit_value}")。\n预留点位的此列必须为空。')
                                set_points_to_check_reserved = { SLL_SET_COL: (sll_value, sll_has_content), SL_SET_COL: (sl_value, sl_has_content), SH_SET_COL: (sh_value, sh_has_content), SHH_SET_COL: (shh_value, shh_has_content),}
                                for col_name, (val, val_has_content) in set_points_to_check_reserved.items():
                                    if val_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n该行为预留点位，但"{col_name}"不为空("{val}")。\n预留点位的此列必须为空。')
                        else: # 非预留点位
                            if not power_supply_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n该行为非预留点位，但"{POWER_SUPPLY_TYPE_COL}"为空。\n此列必填。')
                            elif str(power_supply_value).strip() not in ALLOWED_POWER_SUPPLY_VALUES: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n"{POWER_SUPPLY_TYPE_COL}"的值("{str(power_supply_value).strip()}")无效。\n只允许填写: {", ".join(ALLOWED_POWER_SUPPLY_VALUES)}。')
                            if not wiring_system_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value if module_type_value else "未知"}):\n该行为非预留点位，但"{WIRING_SYSTEM_COL}"为空。\n此列必填。')
                            else:
                                actual_wiring_system_value = str(wiring_system_value).strip()
                                if module_type_value in ["AI", "AO"]:
                                    if actual_wiring_system_value not in ALLOWED_WIRING_SYSTEM_VALUES: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n"{WIRING_SYSTEM_COL}"的值("{actual_wiring_system_value}")对AI/AO模块无效。\n允许的值为: {", ".join(ALLOWED_WIRING_SYSTEM_VALUES)}。')
                                elif module_type_value in ["DI", "DO"]:
                                    if actual_wiring_system_value not in ALLOWED_WIRING_SYSTEM_VALUES_DI_DO: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n"{WIRING_SYSTEM_COL}"的值("{actual_wiring_system_value}")对DI/DO模块无效。\n允许的值为: {", ".join(ALLOWED_WIRING_SYSTEM_VALUES_DI_DO)}。')
                                elif not module_type_value: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n"{MODULE_TYPE_COL}"为空，无法确定"{WIRING_SYSTEM_COL}"的有效值。\n请填写模块类型。')
                            if module_type_value == "AI":
                                if not low_limit_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n该行为非预留点位AI模块，但"{RANGE_LOW_LIMIT_COL}"为空。\n此列必填。')
                                if not high_limit_has_content: error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n该行为非预留点位AI模块，但"{RANGE_HIGH_LIMIT_COL}"为空。\n此列必填。')
                                set_points_to_check_non_reserved = {SLL_SET_COL: (sll_value, sll_has_content), SL_SET_COL: (sl_value, sl_has_content), SH_SET_COL: (sh_value, sh_has_content), SHH_SET_COL: (shh_value, shh_has_content),}
                                for col_name, (val, val_has_content) in set_points_to_check_non_reserved.items():
                                    if val_has_content and not _is_numeric(val): error_messages.append(f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n"{col_name}"的值("{val}")无效。\n必须为整数或小数。')
            except ValueError as ve: # 主IO点表Sheet读取错误
                if f"Worksheet named '{PLC_IO_SHEET_NAME}' not found" in str(ve) or f"No sheet named <{PLC_IO_SHEET_NAME}>" in str(ve):
                    error_messages.append(f'验证警告：在Excel文件中未找到强制要求的主工作表"{PLC_IO_SHEET_NAME}"。将继续校验其他工作表（如果存在）。')
                else:
                    error_messages.append(f'验证失败：读取主工作表"{PLC_IO_SHEET_NAME}"时出错: {str(ve)}。')
            except Exception as e_read_main_sheet: # pylint: disable=broad-except
                error_messages.append(f'验证失败：读取主工作表"{PLC_IO_SHEET_NAME}"时发生未知错误: {str(e_read_main_sheet)}。')
        else: # 主IO点表Sheet不存在
            error_messages.append(f'验证警告：在Excel文件中未找到强制要求的主工作表"{PLC_IO_SHEET_NAME}"。将继续校验其他工作表（如果存在）。')

        # --- 2. 校验其他所有工作表 (视为第三方设备点表) ---
        for sheet_name in sheet_names:
            if sheet_name == PLC_IO_SHEET_NAME:
                continue # 主IO点表已在上面校验过

            try:
                df_tp = pd.read_excel(xls, sheet_name=sheet_name)
                if df_tp.empty:
                    # error_messages.append(f'验证提示：工作表 "{sheet_name}" 为空，已跳过此表的校验。') # 或者静默处理空表
                    continue

                # 检查第三方表所需列是否存在
                required_tp_cols_for_setpoint_check = [
                    TP_INPUT_VAR_NAME_COL, TP_INPUT_DATA_TYPE_COL,
                    TP_INPUT_SLL_SET_COL, TP_INPUT_SL_SET_COL,
                    TP_INPUT_SH_SET_COL, TP_INPUT_SHH_SET_COL
                ]
                missing_tp_cols = [col for col in required_tp_cols_for_setpoint_check if col not in df_tp.columns]
                if missing_tp_cols:
                    for col_name in missing_tp_cols:
                        error_messages.append(f'验证失败：工作表"{sheet_name}"中缺少校验设定值所必需的列"{col_name}"。无法对该表执行设定值唯一性校验。')
                    continue # 如果缺少关键列，跳过此表该项校验

                for index, row in df_tp.iterrows():
                    excel_row_number = index + 2 # Excel行号通常从1开始，加上表头行
                    
                    data_type_value = str(row.get(TP_INPUT_DATA_TYPE_COL, "")).upper().strip()
                    var_name_value = str(row.get(TP_INPUT_VAR_NAME_COL, f"行 {excel_row_number} 未命名点位"))

                    if data_type_value == "REAL":
                        sll_val_tp = row.get(TP_INPUT_SLL_SET_COL)
                        sl_val_tp = row.get(TP_INPUT_SL_SET_COL)
                        sh_val_tp = row.get(TP_INPUT_SH_SET_COL)
                        shh_val_tp = row.get(TP_INPUT_SHH_SET_COL)

                        present_settings_count = 0
                        settings_values = [] # 用于错误消息中显示具体值
                        if _is_value_present(sll_val_tp):
                            present_settings_count += 1
                            settings_values.append(f"{TP_INPUT_SLL_SET_COL}='{sll_val_tp}'")
                        if _is_value_present(sl_val_tp):
                            present_settings_count += 1
                            settings_values.append(f"{TP_INPUT_SL_SET_COL}='{sl_val_tp}'")
                        if _is_value_present(sh_val_tp):
                            present_settings_count += 1
                            settings_values.append(f"{TP_INPUT_SH_SET_COL}='{sh_val_tp}'")
                        if _is_value_present(shh_val_tp):
                            present_settings_count += 1
                            settings_values.append(f"{TP_INPUT_SHH_SET_COL}='{shh_val_tp}'")
                        
                        if present_settings_count > 1:
                            error_messages.append(
                                f'验证失败 (工作表:"{sheet_name}", Excel行号:{excel_row_number}, 点位:{var_name_value}):\n'
                                f'数据类型为REAL的点，其SLL, SL, SH, SHH设定值中存在多个有效值 ({", ".join(settings_values)})。\n'
                                f'一个点在这些列中最多只能有一个有效值。'
                            )
            except Exception as e_read_other_sheet: # pylint: disable=broad-except
                error_messages.append(f'验证失败：读取或校验工作表"{sheet_name}"时发生错误: {str(e_read_other_sheet)}。')

    except pd.errors.EmptyDataError: # 这通常是整个文件没有表头或内容，或者特定sheet为空但尝试读取
        return False, f'文件"{os.path.basename(file_path)}"为空或不包含可读数据，或特定工作表为空。'
    except Exception as e: # pylint: disable=broad-except
        return False, f'读取或验证Excel文件时发生未知错误: {str(e)}。'

    if error_messages:
        return False, "\\n".join(error_messages)

    success_msg = (
        f'文件"{os.path.basename(file_path)}"的所有工作表数据验证通过。'
    )
    return True, success_msg 