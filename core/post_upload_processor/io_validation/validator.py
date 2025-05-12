# core/post_upload_processor/io_validation/validator.py
import os
import pandas as pd
from typing import Tuple, List

# 定义常量，方便维护
HMI_NAME_COL = "变量名称（HMI）"
DESCRIPTION_COL = "变量描述"
POWER_SUPPLY_TYPE_COL = "供电类型（有源/无源）"
WIRING_SYSTEM_COL = "线制"
MODULE_TYPE_COL = "模块类型" # 虽然当前规则未直接使用，但保留以备将来参考
RANGE_LOW_LIMIT_COL = "量程低限"
RANGE_HIGH_LIMIT_COL = "量程高限"
SLL_SET_COL = "SLL设定值"
SL_SET_COL = "SL设定值"
SH_SET_COL = "SH设定值"
SHH_SET_COL = "SHH设定值"
PLC_IO_SHEET_NAME = "IO点表" # 这是 excel_exporter.py 中 PLCSheetExporter 生成的表名

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
    规则：
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

    参数:
        file_path (str): 文件的完整路径。

    返回:
        Tuple[bool, str]: (验证是否通过, 消息)
    """
    error_messages: List[str] = [] # 用于收集所有错误信息

    if not file_path:
        return False, "错误：未提供文件路径。"

    if not os.path.exists(file_path):
        return False, f"文件未找到: {file_path}。"

    _, ext = os.path.splitext(file_path)
    if ext.lower() not in ['.xlsx', '.xls']:
        return False, f"文件格式无效: {ext}。\n请上传有效的 Excel 文件 (.xlsx 或 .xls)。"

    try:
        try:
            df = pd.read_excel(file_path, sheet_name=PLC_IO_SHEET_NAME)
        except ValueError as ve:
            if f"Worksheet named '{PLC_IO_SHEET_NAME}' not found" in str(ve) or \
               f"No sheet named <{PLC_IO_SHEET_NAME}>" in str(ve):
                return False, f'验证失败：在Excel文件中未找到名为"{PLC_IO_SHEET_NAME}"的工作表。'
            raise
        except Exception as e_read_sheet: # pylint: disable=broad-except
            return False, f'验证失败：读取工作表"{PLC_IO_SHEET_NAME}"时出错: {str(e_read_sheet)}。'

        required_cols = [
            HMI_NAME_COL, DESCRIPTION_COL, POWER_SUPPLY_TYPE_COL, WIRING_SYSTEM_COL,
            MODULE_TYPE_COL, # 确保模块类型列是必需的
            RANGE_LOW_LIMIT_COL, RANGE_HIGH_LIMIT_COL,
            SLL_SET_COL, SL_SET_COL, SH_SET_COL, SHH_SET_COL
        ]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            for col_name in missing_cols:
                error_messages.append(f'验证失败：工作表"{PLC_IO_SHEET_NAME}"中缺少必需的列"{col_name}"。')
            # 如果缺少了核心列，后续的行校验意义不大，可以提前返回
            return False, "\n".join(error_messages)

        for index, row in df.iterrows():
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
            module_type_value = str(row.get(MODULE_TYPE_COL, "")).upper().strip() # 获取模块类型并统一格式

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
                msg = (
                    f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                    f'"{HMI_NAME_COL}"({col1_status}) 与 "{DESCRIPTION_COL}"({col2_status}) 状态不一致。\n'
                    f'两者必须同时填写或同时为空。'
                )
                error_messages.append(msg)
            
            is_reserved_point = not hmi_name_has_content

            if is_reserved_point:
                if power_supply_has_content:
                    msg = (
                        f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                        f'该行为预留点位，但"{POWER_SUPPLY_TYPE_COL}"不为空("{power_supply_value}")。\n'
                        f'预留点位的此列必须为空。'
                    )
                    error_messages.append(msg)
                if wiring_system_has_content:
                    msg = (
                        f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                        f'该行为预留点位，但"{WIRING_SYSTEM_COL}"不为空("{wiring_system_value}")。\n'
                        f'预留点位的此列必须为空。'
                    )
                    error_messages.append(msg)
                
                # AI模块预留点位的特定列检查
                if module_type_value == "AI":
                    if low_limit_has_content:
                        msg = (
                            f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                            f'该行为预留点位，但"{RANGE_LOW_LIMIT_COL}"不为空("{low_limit_value}")。\n'
                            f'预留点位的此列必须为空。'
                        )
                        error_messages.append(msg)
                    if high_limit_has_content:
                        msg = (
                            f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                            f'该行为预留点位，但"{RANGE_HIGH_LIMIT_COL}"不为空("{high_limit_value}")。\n'
                            f'预留点位的此列必须为空。'
                        )
                        error_messages.append(msg)
                    # 预留点位的设定值列检查
                    set_points_to_check_reserved = {
                        SLL_SET_COL: (sll_value, sll_has_content),
                        SL_SET_COL: (sl_value, sl_has_content),
                        SH_SET_COL: (sh_value, sh_has_content),
                        SHH_SET_COL: (shh_value, shh_has_content),
                    }
                    for col_name, (val, val_has_content) in set_points_to_check_reserved.items():
                        if val_has_content:
                            msg = (
                                f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                                f'该行为预留点位，但"{col_name}"不为空("{val}")。\n'
                                f'预留点位的此列必须为空。'
                            )
                            error_messages.append(msg)
            else: # 非预留点位
                if not power_supply_has_content:
                    msg = (
                        f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                        f'该行为非预留点位，但"{POWER_SUPPLY_TYPE_COL}"为空。\n'
                        f'此列必填。'
                    )
                    error_messages.append(msg)
                elif str(power_supply_value).strip() not in ALLOWED_POWER_SUPPLY_VALUES:
                    actual_power_supply_value = str(power_supply_value).strip()
                    msg = (
                        f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                        f'"{POWER_SUPPLY_TYPE_COL}"的值("{actual_power_supply_value}")无效。\n'
                        f'只允许填写: {", ".join(ALLOWED_POWER_SUPPLY_VALUES)}。'
                    )
                    error_messages.append(msg)

                # 线制验证，区分模块类型
                if not wiring_system_has_content:
                    msg = (
                        f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value if module_type_value else "未知"}):\n'
                        f'该行为非预留点位，但"{WIRING_SYSTEM_COL}"为空。\n'
                        f'此列必填。'
                    )
                    error_messages.append(msg)
                else:
                    actual_wiring_system_value = str(wiring_system_value).strip()
                    if module_type_value in ["AI", "AO"]:
                        if actual_wiring_system_value not in ALLOWED_WIRING_SYSTEM_VALUES:
                            msg = (
                                f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                                f'"{WIRING_SYSTEM_COL}"的值("{actual_wiring_system_value}")对AI/AO模块无效。\n'
                                f'允许的值为: {", ".join(ALLOWED_WIRING_SYSTEM_VALUES)}。'
                            )
                            error_messages.append(msg)
                    elif module_type_value in ["DI", "DO"]:
                        if actual_wiring_system_value not in ALLOWED_WIRING_SYSTEM_VALUES_DI_DO:
                            msg = (
                                f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                                f'"{WIRING_SYSTEM_COL}"的值("{actual_wiring_system_value}")对DI/DO模块无效。\n'
                                f'允许的值为: {", ".join(ALLOWED_WIRING_SYSTEM_VALUES_DI_DO)}。'
                            )
                            error_messages.append(msg)
                    elif not module_type_value: # 模块类型为空
                         msg = (
                            f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}):\n'
                            f'"{MODULE_TYPE_COL}"为空，无法确定"{WIRING_SYSTEM_COL}"的有效值。\n'
                            f'请填写模块类型。'
                        )
                         error_messages.append(msg)
                    # else: # 其他模块类型，暂不强制线制或允许为空
                    #     pass

                # AI模块非预留点位的特定列检查
                if module_type_value == "AI":
                    if not low_limit_has_content:
                        msg = (
                            f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                            f'该行为非预留点位AI模块，但"{RANGE_LOW_LIMIT_COL}"为空。\n'
                            f'此列必填。'
                        )
                        error_messages.append(msg)
                    if not high_limit_has_content:
                        msg = (
                            f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                            f'该行为非预留点位AI模块，但"{RANGE_HIGH_LIMIT_COL}"为空。\n'
                            f'此列必填。'
                        )
                        error_messages.append(msg)

                    # 非预留点位的设定值列检查 (如果填写了，则必须是数字；允许为空)
                    set_points_to_check_non_reserved = {
                        SLL_SET_COL: (sll_value, sll_has_content),
                        SL_SET_COL: (sl_value, sl_has_content),
                        SH_SET_COL: (sh_value, sh_has_content),
                        SHH_SET_COL: (shh_value, shh_has_content),
                    }
                    for col_name, (val, val_has_content) in set_points_to_check_non_reserved.items():
                        if val_has_content and not _is_numeric(val):
                            msg = (
                                f'验证失败 (工作表:"{PLC_IO_SHEET_NAME}", Excel行号: {excel_row_number}, 模块类型: {module_type_value}):\n'
                                f'"{col_name}"的值("{val}")无效。\n'
                                f'必须为整数或小数。'
                            )
                            error_messages.append(msg)
                        
    except pd.errors.EmptyDataError:
        return False, f'文件"{os.path.basename(file_path)}"的工作表"{PLC_IO_SHEET_NAME}"为空或不包含数据。'
    except Exception as e: # pylint: disable=broad-except
        return False, f'读取或验证Excel文件(工作表:"{PLC_IO_SHEET_NAME}")时发生未知错误: {str(e)}。'

    if error_messages:
        return False, "\n".join(error_messages) # 用单个换行符分隔多条错误

    # 如果没有错误信息，则验证通过
    success_msg = (
        f'文件"{os.path.basename(file_path)}"(工作表:"{PLC_IO_SHEET_NAME}")的'
        f'数据验证通过。'
    )
    return True, success_msg 