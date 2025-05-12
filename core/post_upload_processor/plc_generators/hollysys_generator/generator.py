import pandas as pd
import xlwt
import logging
from typing import Optional, List, Tuple

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

# --- Constants for Third-Party Input Sheet Columns (based on "电动阀" example) ---
TP_INPUT_VAR_NAME_COL = "变量名称"
TP_INPUT_PLC_ADDRESS_COL = "PLC地址"
TP_INPUT_DESCRIPTION_COL = "变量描述"
TP_INPUT_DATA_TYPE_COL = "数据类型"

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
                                third_party_data: Optional[List[Tuple[str, pd.DataFrame]]] = None) -> bool:
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
            bool: True 表示成功，False 表示失败。
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

            font_style = xlwt.XFStyle()
            font = xlwt.Font()
            font.name = '宋体'
            font.height = 20 * 11
            font_style.font = font

            alignment = xlwt.Alignment()
            alignment.horz = xlwt.Alignment.HORZ_LEFT
            alignment.vert = xlwt.Alignment.VERT_CENTER
            font_style.alignment = alignment

            main_sheet.write(0, 0, f"{source_sheet_name}(COMMON)", font_style)

            headers = [
                "变量名", "直接地址", "变量说明", "变量类型",
                "初始值", "掉电保护", "可强制", "SOE使能"
            ]
            for col_idx, header_title in enumerate(headers):
                main_sheet.write(1, col_idx, header_title, font_style)

            if not io_data_df.empty:
                excel_write_row_counter = 1 
                for _, main_row_data in io_data_df.iterrows():
                    excel_write_row_counter += 1
                    current_main_excel_row = excel_write_row_counter
                    # --- 1. 处理主I/O点 --- 
                    main_hmi_name_raw = main_row_data.get(INPUT_HMI_NAME_COL)
                    main_plc_address = str(main_row_data.get(INPUT_PLC_ADDRESS_COL, "")).strip()
                    main_description_raw = main_row_data.get(INPUT_DESCRIPTION_COL)
                    main_data_type = str(main_row_data.get(INPUT_DATA_TYPE_COL, "")).upper()
                    main_channel_no_raw = str(main_row_data.get(INPUT_CHANNEL_NO_COL, "")).strip()
                    module_type = str(main_row_data.get(INPUT_MODULE_TYPE_COL, "")).upper()

                    is_main_point_reserved = _is_value_empty_for_hmi_or_desc(main_hmi_name_raw)
                    output_main_hmi_name: str
                    output_main_description: str

                    if is_main_point_reserved:
                        channel_no_for_display = main_channel_no_raw if main_channel_no_raw else "未知"
                        output_main_hmi_name = f"YLDW{channel_no_for_display}"
                        output_main_description = f"预留点位{channel_no_for_display}"
                    else:
                        output_main_hmi_name = str(main_hmi_name_raw).strip()
                        output_main_description = str(main_description_raw).strip() if not _is_value_empty_for_hmi_or_desc(main_description_raw) else ""
                    
                    if not main_plc_address and not is_main_point_reserved: # 预留点位即使没PLC地址也可能要生成，但非预留点没有地址则跳过
                        logger.warning(f"主点位 '{output_main_hmi_name}' 的PLC绝对地址为空，跳过此行及其关联点。")
                        excel_write_row_counter -=1 
                        continue
                    
                    # --- 根据方案A确定各属性值 ---
                    # 初始值
                    main_initial_value_to_write = 0 if main_data_type == "REAL" else "FALSE"
                    
                    # 掉电保护 (方案A: REAL为TRUE，其他全为FALSE)
                    main_power_off_protection_to_write = "TRUE" if main_data_type == "REAL" else "FALSE"
                    
                    # 可强制 (始终为TRUE)
                    main_can_force_to_write = "TRUE"
                    
                    # SOE使能 (BOOL为TRUE，其他为FALSE)
                    main_soe_enable_to_write = "TRUE" if main_data_type == "BOOL" else "FALSE"
                    
                    main_sheet.write(current_main_excel_row, 0, output_main_hmi_name, font_style)
                    main_sheet.write(current_main_excel_row, 1, main_plc_address, font_style)
                    main_sheet.write(current_main_excel_row, 2, output_main_description, font_style)
                    main_sheet.write(current_main_excel_row, 3, main_data_type if main_data_type else "", font_style)
                    main_sheet.write(current_main_excel_row, 4, main_initial_value_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 5, main_power_off_protection_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 6, main_can_force_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 7, main_soe_enable_to_write, font_style)

                    # --- 2. 处理关联的中间点 (主要针对 AI 模块) ---
                    if module_type == 'AI':
                        for ip_config in INTERMEDIATE_POINTS_CONFIG_AI:
                            intermediate_address = str(main_row_data.get(ip_config['addr_col'], "")).strip()
                            if not intermediate_address:
                                logger.debug(f"中间点 '{ip_config['name_col']}' for main HMI '{output_main_hmi_name}' 的PLC地址为空，跳过。")
                                continue
                            
                            excel_write_row_counter += 1
                            current_ip_excel_row = excel_write_row_counter

                            intermediate_name_from_cell = main_row_data.get(ip_config['name_col'])
                            final_intermediate_name: str

                            if is_main_point_reserved:
                                final_intermediate_name = output_main_hmi_name + ip_config['name_suffix_for_reserved']
                            else:
                                if _is_value_empty_for_hmi_or_desc(intermediate_name_from_cell):
                                    base_name_for_ip = output_main_hmi_name
                                    if not base_name_for_ip: 
                                        logger.warning(f"非预留主点位的HMI名称在处理后为空，用于中间点 '{ip_config['name_col']}'。将使用 'UNKNOWN_MAIN' 作为基础。")
                                        base_name_for_ip = "UNKNOWN_MAIN"
                                    final_intermediate_name = base_name_for_ip + ip_config['name_suffix_for_reserved']
                                else:
                                    final_intermediate_name = str(intermediate_name_from_cell).strip()
                            
                            final_intermediate_description = f"{output_main_description}_{ip_config['desc_suffix']}"
                            intermediate_data_type = ip_config['type']

                            # --- 根据方案A确定AI中间点各属性值 ---
                            # 初始值
                            ip_initial_value_to_write = 0 if intermediate_data_type == "REAL" else "FALSE"
                            
                            # 掉电保护 (方案A: REAL为TRUE，其他全为FALSE)
                            ip_power_off_protection_to_write = "TRUE" if intermediate_data_type == "REAL" else "FALSE"
                            
                            # 可强制 (始终为TRUE)
                            ip_can_force_to_write = "TRUE"
                            
                            # SOE使能 (BOOL为TRUE，其他为FALSE)
                            ip_soe_enable_to_write = "TRUE" if intermediate_data_type == "BOOL" else "FALSE"

                            main_sheet.write(current_ip_excel_row, 0, final_intermediate_name, font_style)
                            main_sheet.write(current_ip_excel_row, 1, intermediate_address, font_style)
                            main_sheet.write(current_ip_excel_row, 2, final_intermediate_description, font_style)
                            main_sheet.write(current_ip_excel_row, 3, intermediate_data_type, font_style)
                            main_sheet.write(current_ip_excel_row, 4, ip_initial_value_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 5, ip_power_off_protection_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 6, ip_can_force_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 7, ip_soe_enable_to_write, font_style)
            
            # --- 列宽调整 (一次性完成) ---
            main_sheet.col(0).width = 256 * 35  # 变量名
            main_sheet.col(1).width = 256 * 20  # 直接地址
            main_sheet.col(2).width = 256 * 45  # 变量说明 (可能更长)
            main_sheet.col(3).width = 256 * 15  # 变量类型
            main_sheet.col(4).width = 256 * 10  # 初始值
            main_sheet.col(5).width = 256 * 12  # 掉电保护
            main_sheet.col(6).width = 256 * 10  # 可强制
            main_sheet.col(7).width = 256 * 12  # SOE使能

            logger.info(f"主IO点表Sheet '{source_sheet_name}' 处理完毕。")

            # --- 2. 处理第三方设备点表 (后续Sheets) ---
            if third_party_data:
                for tp_idx, (tp_sheet_name, tp_df) in enumerate(third_party_data):
                    logger.info(f"开始处理第 {tp_idx+1} 个第三方设备Sheet: '{tp_sheet_name}'")
                    if tp_df.empty:
                        logger.warning(f"第三方设备Sheet '{tp_sheet_name}' 的数据为空，跳过。")
                        # 创建一个空sheet并写入A1和表头，以保持一致性，或者完全跳过
                        tp_output_sheet = workbook.add_sheet(tp_sheet_name)
                        tp_output_sheet.write(0, 0, f"{tp_sheet_name}(COMMON)", font_style)
                        for col_idx, header_title in enumerate(headers): # 使用与主表相同的headers
                            tp_output_sheet.write(1, col_idx, header_title, font_style)
                        logger.info(f"为空的第三方设备Sheet '{tp_sheet_name}' 已创建表头。")
                        # 设置列宽
                        tp_output_sheet.col(0).width = 256 * 35
                        tp_output_sheet.col(1).width = 256 * 20
                        tp_output_sheet.col(2).width = 256 * 45
                        tp_output_sheet.col(3).width = 256 * 15
                        tp_output_sheet.col(4).width = 256 * 10
                        tp_output_sheet.col(5).width = 256 * 12
                        tp_output_sheet.col(6).width = 256 * 10
                        tp_output_sheet.col(7).width = 256 * 12
                        continue

                    tp_output_sheet = workbook.add_sheet(tp_sheet_name)
                    tp_output_sheet.write(0, 0, f"{tp_sheet_name}(COMMON)", font_style)

                    for col_idx, header_title in enumerate(headers): # 使用与主表相同的headers
                        tp_output_sheet.write(1, col_idx, header_title, font_style)

                    excel_tp_write_row_counter = 1 # Excel行索引，表头在第1行, 数据从第2行开始
                    for _, tp_row_data in tp_df.iterrows():
                        excel_tp_write_row_counter += 1
                        current_tp_excel_row = excel_tp_write_row_counter

                        # 从第三方Sheet的输入行提取数据
                        var_name = tp_row_data.get(TP_INPUT_VAR_NAME_COL, "")
                        plc_addr = str(tp_row_data.get(TP_INPUT_PLC_ADDRESS_COL, "")).strip()
                        desc = tp_row_data.get(TP_INPUT_DESCRIPTION_COL, "")
                        data_type = str(tp_row_data.get(TP_INPUT_DATA_TYPE_COL, "")).upper()

                        if not var_name and not plc_addr: # 如果关键信息缺失，可以考虑跳过此行
                            logger.debug(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 的变量名和PLC地址均为空，跳过。")
                            excel_tp_write_row_counter -=1 # 回滚计数器
                            continue
                            
                        # 应用方案A计算属性值
                        initial_val_to_write = 0 if data_type == "REAL" else "FALSE"
                        power_off_prot_to_write = "TRUE" if data_type == "REAL" else "FALSE"
                        can_force_to_write = "TRUE"
                        soe_enable_to_write = "TRUE" if data_type == "BOOL" else "FALSE"

                        # 写入到输出的第三方Sheet
                        tp_output_sheet.write(current_tp_excel_row, 0, var_name, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 1, plc_addr, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 2, desc, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 3, data_type if data_type else "", font_style)
                        tp_output_sheet.write(current_tp_excel_row, 4, initial_val_to_write, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 5, power_off_prot_to_write, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 6, can_force_to_write, font_style)
                        tp_output_sheet.write(current_tp_excel_row, 7, soe_enable_to_write, font_style)
                    
                    # 设置列宽 (与主Sheet一致)
                    tp_output_sheet.col(0).width = 256 * 35
                    tp_output_sheet.col(1).width = 256 * 20
                    tp_output_sheet.col(2).width = 256 * 45
                    tp_output_sheet.col(3).width = 256 * 15
                    tp_output_sheet.col(4).width = 256 * 10
                    tp_output_sheet.col(5).width = 256 * 12
                    tp_output_sheet.col(6).width = 256 * 10
                    tp_output_sheet.col(7).width = 256 * 12
                    logger.info(f"第三方设备Sheet '{tp_sheet_name}' 处理完毕。")
            
            workbook.save(output_path)
            logger.info(f"和利时PLC点表已成功生成并保存到: {output_path} (包含主IO点表和所有第三方设备点表)")
            return True

        except KeyError as ke:
            logger.error(f"生成和利时点表失败：输入数据中缺少必需的列: {ke}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"生成和利时PLC点表时发生未知错误: {e}", exc_info=True)
            return False

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