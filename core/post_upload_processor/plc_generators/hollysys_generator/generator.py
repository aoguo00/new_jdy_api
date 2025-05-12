import pandas as pd
import xlwt
import logging
from typing import Optional, List, Tuple, Any

logger = logging.getLogger(__name__)

# --- Input IO Table Column Constants ---
INPUT_HMI_NAME_COL = "变量名称（HMI）"
INPUT_PLC_ADDRESS_COL = "PLC绝对地址"
INPUT_DESCRIPTION_COL = "变量描述"
INPUT_DATA_TYPE_COL = "数据类型"
INPUT_CHANNEL_NO_COL = "通道位号"
INPUT_MODULE_TYPE_COL = "模块类型"

# Intermediate Point Name Columns from Input IO Table
IP_SLL_SP_NAME_COL = "SLL设定点位"
IP_SL_SP_NAME_COL  = "SL设定点位"
IP_SH_SP_NAME_COL  = "SH设定点位"
IP_SHH_SP_NAME_COL = "SHH设定点位"
IP_LL_AL_NAME_COL  = "LL报警"
IP_L_AL_NAME_COL   = "L报警"
IP_H_AL_NAME_COL   = "H报警"
IP_HH_AL_NAME_COL  = "HH报警"
IP_MAINT_VAL_SP_NAME_COL = "维护值设定点位"
IP_MAINT_EN_SW_NAME_COL  = "维护使能开关点位"

# Intermediate Point PLC Address Columns from Input IO Table
IP_SLL_SP_PLC_ADDR_COL = "SLL设定点位_PLC地址"
IP_SL_SP_PLC_ADDR_COL  = "SL设定点位_PLC地址"
IP_SH_SP_PLC_ADDR_COL  = "SH设定点位_PLC地址"
IP_SHH_SP_PLC_ADDR_COL = "SHH设定点位_PLC地址"
IP_LL_AL_PLC_ADDR_COL  = "LL报警_PLC地址"
IP_L_AL_PLC_ADDR_COL   = "L报警_PLC地址"
IP_H_AL_PLC_ADDR_COL   = "H报警_PLC地址"
IP_HH_AL_PLC_ADDR_COL  = "HH报警_PLC地址"
IP_MAINT_VAL_SP_PLC_ADDR_COL = "维护值设定点位_PLC地址"
IP_MAINT_EN_SW_PLC_ADDR_COL  = "维护使能开关点位_PLC地址"

# --- Constants for Third-Party Input Sheet Columns (based on "电动阀" and "可燃气体探测器" examples) ---
TP_INPUT_VAR_NAME_COL = "变量名称"
TP_INPUT_PLC_ADDRESS_COL = "PLC地址"
TP_INPUT_DESCRIPTION_COL = "变量描述"
TP_INPUT_DATA_TYPE_COL = "数据类型"
TP_INPUT_SLL_SET_COL = "SLL设定值"
TP_INPUT_SL_SET_COL = "SL设定值"
TP_INPUT_SH_SET_COL = "SH设定值"
TP_INPUT_SHH_SET_COL = "SHH设定值"

# Configuration for AI module's intermediate points
# Structure: (name_col, addr_col, data_type, desc_suffix, name_suffix_for_reserved_main_point)
INTERMEDIATE_POINTS_CONFIG_AI = [
    {'name_col': IP_SLL_SP_NAME_COL, 'addr_col': IP_SLL_SP_PLC_ADDR_COL, 'type': 'REAL', 'desc_suffix': 'SLL设定', 'name_suffix_for_reserved': '_LoLoLimit'},
    {'name_col': IP_SL_SP_NAME_COL,  'addr_col': IP_SL_SP_PLC_ADDR_COL,  'type': 'REAL', 'desc_suffix': 'SL设定',  'name_suffix_for_reserved': '_LoLimit'},
    {'name_col': IP_SH_SP_NAME_COL,  'addr_col': IP_SH_SP_PLC_ADDR_COL,  'type': 'REAL', 'desc_suffix': 'SH设定',  'name_suffix_for_reserved': '_HiLimit'},
    {'name_col': IP_SHH_SP_NAME_COL, 'addr_col': IP_SHH_SP_PLC_ADDR_COL, 'type': 'REAL', 'desc_suffix': 'SHH设定', 'name_suffix_for_reserved': '_HiHiLimit'},
    {'name_col': IP_LL_AL_NAME_COL,  'addr_col': IP_LL_AL_PLC_ADDR_COL,  'type': 'BOOL', 'desc_suffix': 'LL报警',  'name_suffix_for_reserved': '_LL'},
    {'name_col': IP_L_AL_NAME_COL,   'addr_col': IP_L_AL_PLC_ADDR_COL,   'type': 'BOOL', 'desc_suffix': 'L报警',   'name_suffix_for_reserved': '_L'},
    {'name_col': IP_H_AL_NAME_COL,   'addr_col': IP_H_AL_PLC_ADDR_COL,   'type': 'BOOL', 'desc_suffix': 'H报警',   'name_suffix_for_reserved': '_H'},
    {'name_col': IP_HH_AL_NAME_COL,  'addr_col': IP_HH_AL_PLC_ADDR_COL,  'type': 'BOOL', 'desc_suffix': 'HH报警',  'name_suffix_for_reserved': '_HH'},
    {'name_col': IP_MAINT_VAL_SP_NAME_COL, 'addr_col': IP_MAINT_VAL_SP_PLC_ADDR_COL, 'type': 'REAL', 'desc_suffix': '维护值设定', 'name_suffix_for_reserved': '_whz'},
    {'name_col': IP_MAINT_EN_SW_NAME_COL,  'addr_col': IP_MAINT_EN_SW_PLC_ADDR_COL,  'type': 'BOOL', 'desc_suffix': '维护使能',  'name_suffix_for_reserved': '_whzzt'},
]

def _is_value_empty_for_hmi_or_desc(value) -> bool:
    """
    辅助函数：检查值是否被视为空（用于HMI名称和描述）。
    认为 NaN, None, 和纯空格字符串为空。
    """
    if pd.isna(value):  # 处理 NaN 和 None
        return True
    if isinstance(value, str) and not value.strip():  # 处理空字符串或只包含空格的字符串
        return True
    return False

def _get_value_if_present(value):
    """辅助函数：如果值存在（非NaN，非None，非空字符串），则返回该值，否则返回None。"""
    if pd.isna(value) or value is None or (isinstance(value, str) and not value.strip()):
        return None
    return value

class HollysysGenerator:
    """
    负责根据已验证的IO点表数据生成和利时PLC点表 (.xls格式)。
    """

    def __init__(self):
        pass

    def generate_hollysys_table(self, 
                                io_data_df: pd.DataFrame, 
                                source_sheet_name: str, 
                                output_path: str,
                                third_party_data: Optional[List[Tuple[str, pd.DataFrame]]] = None
                               ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时PLC点表。

        参数:
            io_data_df (pd.DataFrame): 从源Excel文件第一个Sheet中读取的数据。
            source_sheet_name (str): 源Excel文件中第一个实际读取数据的Sheet的名称。
            output_path (str): 用户选择的 .xls 文件保存路径。
            third_party_data (Optional[List[Tuple[str, pd.DataFrame]]]): 
                一个包含元组的列表，每个元组代表一个第三方设备Sheet：(原始Sheet名, 该Sheet的DataFrame)。
                默认为None。

        返回:
            Tuple[bool, Optional[str]]: (操作是否成功, 错误消息或None)
        """
        logger.info(f"开始生成和利时PLC点表，主源Sheet: '{source_sheet_name}', 输出路径: '{output_path}'")
        if third_party_data:
            tp_sheet_names = [name for name, _ in third_party_data]
            logger.info(f"同时处理第三方设备Sheets: {tp_sheet_names}")

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            
            # --- 1. 处理主IO点表 (第一个Sheet) ---
            main_sheet = workbook.add_sheet(source_sheet_name)
            logger.info(f"主IO点表Sheet '{source_sheet_name}' 创建成功。")
            font_style = xlwt.XFStyle(); font = xlwt.Font(); font.name = '宋体'; font.height = 20 * 11; font_style.font = font
            alignment = xlwt.Alignment(); alignment.horz = xlwt.Alignment.HORZ_LEFT; alignment.vert = xlwt.Alignment.VERT_CENTER; font_style.alignment = alignment
            main_sheet.write(0, 0, f"{source_sheet_name}(COMMON)", font_style)
            headers = ["变量名", "直接地址", "变量说明", "变量类型", "初始值", "掉电保护", "可强制", "SOE使能"]
            for col_idx, header_title in enumerate(headers): main_sheet.write(1, col_idx, header_title, font_style)
            if not io_data_df.empty:
                excel_write_row_counter = 1 
                for _, main_row_data in io_data_df.iterrows():
                    excel_write_row_counter += 1
                    current_main_excel_row = excel_write_row_counter
                    main_hmi_name_raw = main_row_data.get(INPUT_HMI_NAME_COL); main_plc_address = str(main_row_data.get(INPUT_PLC_ADDRESS_COL, "")).strip()
                    main_description_raw = main_row_data.get(INPUT_DESCRIPTION_COL); main_data_type = str(main_row_data.get(INPUT_DATA_TYPE_COL, "")).upper()
                    main_channel_no_raw = str(main_row_data.get(INPUT_CHANNEL_NO_COL, "")).strip(); module_type = str(main_row_data.get(INPUT_MODULE_TYPE_COL, "")).upper()
                    is_main_point_reserved = _is_value_empty_for_hmi_or_desc(main_hmi_name_raw)
                    output_main_hmi_name: str; output_main_description: str
                    if is_main_point_reserved: channel_no_for_display = main_channel_no_raw if main_channel_no_raw else "未知"; output_main_hmi_name = f"YLDW{channel_no_for_display}"; output_main_description = f"预留点位{channel_no_for_display}"
                    else: output_main_hmi_name = str(main_hmi_name_raw).strip(); output_main_description = str(main_description_raw).strip() if not _is_value_empty_for_hmi_or_desc(main_description_raw) else ""
                    if not main_plc_address and not is_main_point_reserved: logger.warning(f"主点位 '{output_main_hmi_name}' 的PLC绝对地址为空，跳过此行及其关联点。"); excel_write_row_counter -=1; continue
                    main_initial_value_to_write = 0 if main_data_type == "REAL" else "FALSE"; main_power_off_protection_to_write = "TRUE" if main_data_type == "REAL" else "FALSE"
                    main_can_force_to_write = "TRUE"; main_soe_enable_to_write = "TRUE" if main_data_type == "BOOL" else "FALSE"
                    main_sheet.write(current_main_excel_row, 0, output_main_hmi_name, font_style); main_sheet.write(current_main_excel_row, 1, main_plc_address, font_style); main_sheet.write(current_main_excel_row, 2, output_main_description, font_style); main_sheet.write(current_main_excel_row, 3, main_data_type if main_data_type else "", font_style); main_sheet.write(current_main_excel_row, 4, main_initial_value_to_write, font_style); main_sheet.write(current_main_excel_row, 5, main_power_off_protection_to_write, font_style); main_sheet.write(current_main_excel_row, 6, main_can_force_to_write, font_style); main_sheet.write(current_main_excel_row, 7, main_soe_enable_to_write, font_style)
                    if module_type == 'AI':
                        for ip_config in INTERMEDIATE_POINTS_CONFIG_AI:
                            intermediate_address = str(main_row_data.get(ip_config['addr_col'], "")).strip()
                            if not intermediate_address: continue
                            excel_write_row_counter += 1; current_ip_excel_row = excel_write_row_counter; intermediate_name_from_cell = main_row_data.get(ip_config['name_col']); final_intermediate_name: str
                            if is_main_point_reserved: final_intermediate_name = output_main_hmi_name + ip_config['name_suffix_for_reserved']
                            else:
                                if _is_value_empty_for_hmi_or_desc(intermediate_name_from_cell): base_name_for_ip = output_main_hmi_name; final_intermediate_name = (base_name_for_ip if base_name_for_ip else "UNKNOWN_MAIN") + ip_config['name_suffix_for_reserved']
                                else: final_intermediate_name = str(intermediate_name_from_cell).strip()
                            final_intermediate_description = f"{output_main_description}_{ip_config['desc_suffix']}"; intermediate_data_type = ip_config['type']
                            ip_initial_value_to_write = 0 if intermediate_data_type == "REAL" else "FALSE"; ip_power_off_protection_to_write = "TRUE" if intermediate_data_type == "REAL" else "FALSE"; ip_can_force_to_write = "TRUE"; ip_soe_enable_to_write = "TRUE" if intermediate_data_type == "BOOL" else "FALSE"
                            main_sheet.write(current_ip_excel_row, 0, final_intermediate_name, font_style); main_sheet.write(current_ip_excel_row, 1, intermediate_address, font_style); main_sheet.write(current_ip_excel_row, 2, final_intermediate_description, font_style); main_sheet.write(current_ip_excel_row, 3, intermediate_data_type, font_style); main_sheet.write(current_ip_excel_row, 4, ip_initial_value_to_write, font_style); main_sheet.write(current_ip_excel_row, 5, ip_power_off_protection_to_write, font_style); main_sheet.write(current_ip_excel_row, 6, ip_can_force_to_write, font_style); main_sheet.write(current_ip_excel_row, 7, ip_soe_enable_to_write, font_style)
            else: logger.info(f"主IO点表Sheet '{source_sheet_name}' 的输入数据为空。")
            main_sheet.col(0).width = 256 * 35; main_sheet.col(1).width = 256 * 20; main_sheet.col(2).width = 256 * 45; main_sheet.col(3).width = 256 * 15; main_sheet.col(4).width = 256 * 10; main_sheet.col(5).width = 256 * 12; main_sheet.col(6).width = 256 * 10; main_sheet.col(7).width = 256 * 12
            logger.info(f"主IO点表Sheet '{source_sheet_name}' 处理完毕。")

            # --- 2. 处理第三方设备点表 (后续Sheets) ---
            if third_party_data:
                for tp_idx, (tp_sheet_name, tp_df) in enumerate(third_party_data):
                    logger.info(f"开始处理第 {tp_idx+1} 个第三方设备Sheet: '{tp_sheet_name}'")
                    tp_output_sheet = workbook.add_sheet(tp_sheet_name)
                    tp_output_sheet.write(0, 0, f"{tp_sheet_name}(COMMON)", font_style)
                    for col_idx, header_title in enumerate(headers): tp_output_sheet.write(1, col_idx, header_title, font_style)

                    if tp_df.empty:
                        logger.warning(f"第三方设备Sheet '{tp_sheet_name}' 的数据为空。已创建带表头的空Sheet。")
                        tp_output_sheet.col(0).width = 256 * 35; tp_output_sheet.col(1).width = 256 * 20; tp_output_sheet.col(2).width = 256 * 45; tp_output_sheet.col(3).width = 256 * 15; tp_output_sheet.col(4).width = 256 * 10; tp_output_sheet.col(5).width = 256 * 12; tp_output_sheet.col(6).width = 256 * 10; tp_output_sheet.col(7).width = 256 * 12
                        continue
                    
                    excel_tp_write_row_counter = 1
                    for _, tp_row_data in tp_df.iterrows():
                        excel_tp_write_row_counter += 1
                        var_name = tp_row_data.get(TP_INPUT_VAR_NAME_COL, ""); plc_addr = str(tp_row_data.get(TP_INPUT_PLC_ADDRESS_COL, "")).strip(); desc = tp_row_data.get(TP_INPUT_DESCRIPTION_COL, ""); data_type = str(tp_row_data.get(TP_INPUT_DATA_TYPE_COL, "")).upper()
                        if not var_name and not plc_addr: logger.debug(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 的变量名和PLC地址均为空，跳过。"); excel_tp_write_row_counter -=1; continue

                        initial_val_to_write: Any
                        if data_type == "REAL":
                            sll_val = _get_value_if_present(tp_row_data.get(TP_INPUT_SLL_SET_COL))
                            sl_val = _get_value_if_present(tp_row_data.get(TP_INPUT_SL_SET_COL))
                            sh_val = _get_value_if_present(tp_row_data.get(TP_INPUT_SH_SET_COL))
                            shh_val = _get_value_if_present(tp_row_data.get(TP_INPUT_SHH_SET_COL))
                            
                            present_settings = []
                            if sll_val is not None: present_settings.append(sll_val)
                            if sl_val is not None: present_settings.append(sl_val)
                            if sh_val is not None: present_settings.append(sh_val)
                            if shh_val is not None: present_settings.append(shh_val)

                            # 校验逻辑已移至 validator.py, 此处直接取值或报错
                            if len(present_settings) == 1:
                                try: initial_val_to_write = float(present_settings[0])
                                except (ValueError, TypeError): 
                                    logger.warning(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 点位 '{var_name}' 的设定值 '{present_settings[0]}' 不是有效数字，初始值将设为0。 (此警告理论上不应出现，若校验通过)"); 
                                    initial_val_to_write = 0
                            elif len(present_settings) > 1:
                                # 此情况理论上不应发生，因为 validator.py 应该已经捕获
                                # 但为保持健壮性，仍可记录一个更严重的错误或抛出内部异常
                                logger.error(f"内部逻辑错误: 第三方Sheet '{tp_sheet_name}' 点位 '{var_name}' (行号参考 {excel_tp_write_row_counter}) 通过了validator校验，但在生成时仍检测到多个设定值: {present_settings}。将使用0作为初始值。")
                                initial_val_to_write = 0 # 或者可以 return False, "内部逻辑错误..." 
                            else: # len(present_settings) == 0
                                initial_val_to_write = 0
                        elif data_type == "BOOL": initial_val_to_write = "FALSE"
                        else: logger.warning(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 点位 '{var_name}' 数据类型 '{data_type}' 未知，初始值将设为0。"); initial_val_to_write = 0
                        
                        power_off_prot_to_write = "TRUE" if data_type == "REAL" else "FALSE"
                        can_force_to_write = "TRUE"
                        soe_enable_to_write = "TRUE" if data_type == "BOOL" else "FALSE"
                        tp_output_sheet.write(excel_tp_write_row_counter, 0, var_name, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 1, plc_addr, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 2, desc, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 3, data_type if data_type else "", font_style); tp_output_sheet.write(excel_tp_write_row_counter, 4, initial_val_to_write, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 5, power_off_prot_to_write, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 6, can_force_to_write, font_style); tp_output_sheet.write(excel_tp_write_row_counter, 7, soe_enable_to_write, font_style)

                    tp_output_sheet.col(0).width = 256 * 35; tp_output_sheet.col(1).width = 256 * 20; tp_output_sheet.col(2).width = 256 * 45; tp_output_sheet.col(3).width = 256 * 15; tp_output_sheet.col(4).width = 256 * 10; tp_output_sheet.col(5).width = 256 * 12; tp_output_sheet.col(6).width = 256 * 10; tp_output_sheet.col(7).width = 256 * 12
                    logger.info(f"第三方设备Sheet '{tp_sheet_name}' 处理完毕。")
            
            workbook.save(output_path)
            logger.info(f"和利时PLC点表已成功生成并保存到: {output_path} (包含主IO点表和所有第三方设备点表)")
            return True, None
        except KeyError as ke:
            error_msg = f"生成和利时点表失败：输入数据中缺少必需的列: {ke}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"生成和利时PLC点表时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    sample_io_data_list = [
        {
            INPUT_HMI_NAME_COL: "AI_PT_001", INPUT_PLC_ADDRESS_COL: "%MD100", INPUT_DESCRIPTION_COL: "压力变送器001", 
            INPUT_DATA_TYPE_COL: "REAL", INPUT_CHANNEL_NO_COL: "CH1", INPUT_MODULE_TYPE_COL: "AI",
            IP_SLL_SP_NAME_COL: "AI_PT_001_LoLoLimit", IP_SLL_SP_PLC_ADDR_COL: "%MD104",
            IP_SL_SP_NAME_COL: "AI_PT_001_LoLimit", IP_SL_SP_PLC_ADDR_COL: "%MD108",
            IP_SH_SP_NAME_COL: "AI_PT_001_HiLimit", IP_SH_SP_PLC_ADDR_COL: "%MD112",
            IP_SHH_SP_NAME_COL: "AI_PT_001_HiHiLimit", IP_SHH_SP_PLC_ADDR_COL: "%MD116",
            IP_LL_AL_NAME_COL: "AI_PT_001_LL", IP_LL_AL_PLC_ADDR_COL: "%MX20.0",
            IP_L_AL_NAME_COL: "AI_PT_001_L", IP_L_AL_PLC_ADDR_COL: "%MX20.1",
            IP_H_AL_NAME_COL: "AI_PT_001_H", IP_H_AL_PLC_ADDR_COL: "%MX20.2",
            IP_HH_AL_NAME_COL: "AI_PT_001_HH", IP_HH_AL_PLC_ADDR_COL: "%MX20.3",
            IP_MAINT_VAL_SP_NAME_COL: "AI_PT_001_whz", IP_MAINT_VAL_SP_PLC_ADDR_COL: "%MD120",
            IP_MAINT_EN_SW_NAME_COL: "AI_PT_001_whzzt", IP_MAINT_EN_SW_PLC_ADDR_COL: "%MX20.4",
        },
        { # AI预留点位
            INPUT_HMI_NAME_COL: None, INPUT_PLC_ADDRESS_COL: "%MD200", INPUT_DESCRIPTION_COL: None, 
            INPUT_DATA_TYPE_COL: "REAL", INPUT_CHANNEL_NO_COL: "CH2_AI_Res", INPUT_MODULE_TYPE_COL: "AI",
            IP_SLL_SP_NAME_COL: "", IP_SLL_SP_PLC_ADDR_COL: "%MD204", # 假设预留点位的中间点名称单元格为空
            IP_SL_SP_NAME_COL: None, IP_SL_SP_PLC_ADDR_COL: "%MD208",
            IP_SH_SP_NAME_COL: pd.NA, IP_SH_SP_PLC_ADDR_COL: "%MD212",
            IP_SHH_SP_NAME_COL: float('nan'), IP_SHH_SP_PLC_ADDR_COL: "%MD216",
            IP_LL_AL_NAME_COL: "", IP_LL_AL_PLC_ADDR_COL: "%MX21.0",
            IP_L_AL_NAME_COL: " ", IP_L_AL_PLC_ADDR_COL: "%MX21.1",
            IP_H_AL_NAME_COL: None, IP_H_AL_PLC_ADDR_COL: "%MX21.2",
            IP_HH_AL_NAME_COL: None, IP_HH_AL_PLC_ADDR_COL: "%MX21.3",
            IP_MAINT_VAL_SP_NAME_COL: None, IP_MAINT_VAL_SP_PLC_ADDR_COL: "%MD220",
            IP_MAINT_EN_SW_NAME_COL: None, IP_MAINT_EN_SW_PLC_ADDR_COL: "%MX21.4",
        },
        {
            INPUT_HMI_NAME_COL: "DI_PUMP_01_RUN", INPUT_PLC_ADDRESS_COL: "%MX30.0", INPUT_DESCRIPTION_COL: "1号泵运行状态", 
            INPUT_DATA_TYPE_COL: "BOOL", INPUT_CHANNEL_NO_COL: "CH3_DI", INPUT_MODULE_TYPE_COL: "DI",
            # DI模块通常没有这些特定的中间点，这些列在实际IO表中可能不存在或为空
        },
        { # 主PLC地址为空的AI点 (应被跳过)
            INPUT_HMI_NAME_COL: "AI_TEST_NO_MAIN_ADDR", INPUT_PLC_ADDRESS_COL: "", INPUT_DESCRIPTION_COL: "无主地址AI点", 
            INPUT_DATA_TYPE_COL: "REAL", INPUT_CHANNEL_NO_COL: "CH4", INPUT_MODULE_TYPE_COL: "AI",
            IP_SLL_SP_NAME_COL: "AI_TEST_NO_MAIN_ADDR_LoLoLimit", IP_SLL_SP_PLC_ADDR_COL: "%MD404",
        }
    ]
    sample_df = pd.DataFrame(sample_io_data_list)

    generator = HollysysGenerator()
    source_sheet = "测试IO表"
    
    output_file_complex = "test_hollysys_table_complex_v3.xls"
    if generator.generate_hollysys_table(sample_df, source_sheet, output_file_complex):
        print(f"复杂场景测试文件 '{output_file_complex}' 生成成功。")
    else:
        print(f"复杂场景测试文件 '{output_file_complex}' 生成失败。")

    empty_df = pd.DataFrame(columns=sample_df.columns)
    if not generator.generate_hollysys_table(empty_df, source_sheet, "empty_test.xls"):
        print(f"空数据测试文件生成失败 (符合预期)。")

    missing_col_df = sample_df.drop(columns=[INPUT_PLC_ADDRESS_COL])
    if not generator.generate_hollysys_table(missing_col_df, source_sheet, "missing_col_test.xls"):
        print(f"列缺失测试文件生成失败 (符合预期)。") 