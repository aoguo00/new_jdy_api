import pandas as pd
import xlwt
import logging
from typing import Optional, List, Tuple, Any
# 修改导入路径为绝对导入
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint

logger = logging.getLogger(__name__)

# --- Input IO Table Column Constants (大部分将被 UploadedIOPoint 属性替代) ---
# INPUT_HMI_NAME_COL = "变量名称（HMI）" -> point.hmi_variable_name
# INPUT_PLC_ADDRESS_COL = "PLC绝对地址" -> point.plc_absolute_address
# INPUT_DESCRIPTION_COL = "变量描述" -> point.variable_description
# INPUT_DATA_TYPE_COL = "数据类型" -> point.data_type
# INPUT_CHANNEL_NO_COL = "通道位号" -> point.channel_tag
# INPUT_MODULE_TYPE_COL = "模块类型" -> point.module_type

# Intermediate Point Name Columns from Input IO Table (将映射到 UploadedIOPoint 属性)
# IP_SLL_SP_NAME_COL = "SLL设定点位" -> point.sll_set_point
# IP_SL_SP_NAME_COL  = "SL设定点位"  -> point.sl_set_point
# ... (其他类似映射)

# Intermediate Point PLC Address Columns from Input IO Table (将映射到 UploadedIOPoint 属性)
# IP_SLL_SP_PLC_ADDR_COL = "SLL设定点位_PLC地址" -> point.sll_set_point_plc_address
# ... (其他类似映射)

# --- Constants for Third-Party Input Sheet Columns (保持不变，因为第三方数据仍为DataFrame) ---
TP_INPUT_VAR_NAME_COL = "变量名称"
TP_INPUT_PLC_ADDRESS_COL = "PLC地址"
TP_INPUT_DESCRIPTION_COL = "变量描述"
TP_INPUT_DATA_TYPE_COL = "数据类型"
TP_INPUT_SLL_SET_COL = "SLL设定值"
TP_INPUT_SL_SET_COL = "SL设定值"
TP_INPUT_SH_SET_COL = "SH设定值"
TP_INPUT_SHH_SET_COL = "SHH设定值"

# Configuration for AI module's intermediate points
# 修改: name_col -> name_attr, addr_col -> addr_attr，值更新为 UploadedIOPoint 的属性名
INTERMEDIATE_POINTS_CONFIG_AI = [
    {'name_attr': 'sll_set_point', 'addr_attr': 'sll_set_point_plc_address', 'type': 'REAL', 'desc_suffix': 'SLL设定', 'name_suffix_for_reserved': '_LoLoLimit'},
    {'name_attr': 'sl_set_point',  'addr_attr': 'sl_set_point_plc_address',  'type': 'REAL', 'desc_suffix': 'SL设定',  'name_suffix_for_reserved': '_LoLimit'},
    {'name_attr': 'sh_set_point',  'addr_attr': 'sh_set_point_plc_address',  'type': 'REAL', 'desc_suffix': 'SH设定',  'name_suffix_for_reserved': '_HiLimit'},
    {'name_attr': 'shh_set_point', 'addr_attr': 'shh_set_point_plc_address', 'type': 'REAL', 'desc_suffix': 'SHH设定', 'name_suffix_for_reserved': '_HiHiLimit'},
    {'name_attr': 'll_alarm',  'addr_attr': 'll_alarm_plc_address',  'type': 'BOOL', 'desc_suffix': 'LL报警',  'name_suffix_for_reserved': '_LL'},
    {'name_attr': 'l_alarm',   'addr_attr': 'l_alarm_plc_address',   'type': 'BOOL', 'desc_suffix': 'L报警',   'name_suffix_for_reserved': '_L'},
    {'name_attr': 'h_alarm',   'addr_attr': 'h_alarm_plc_address',   'type': 'BOOL', 'desc_suffix': 'H报警',   'name_suffix_for_reserved': '_H'},
    {'name_attr': 'hh_alarm',  'addr_attr': 'hh_alarm_plc_address',  'type': 'BOOL', 'desc_suffix': 'HH报警',  'name_suffix_for_reserved': '_HH'},
    {'name_attr': 'maintenance_set_point', 'addr_attr': 'maintenance_set_point_plc_address', 'type': 'REAL', 'desc_suffix': '维护值设定', 'name_suffix_for_reserved': '_whz'},
    {'name_attr': 'maintenance_enable_switch_point',  'addr_attr': 'maintenance_enable_switch_point_plc_address',  'type': 'BOOL', 'desc_suffix': '维护使能',  'name_suffix_for_reserved': '_whzzt'},
]

def _is_value_empty_for_hmi_or_desc(value: Optional[str]) -> bool:
    """
    辅助函数：检查值是否被视为空（用于HMI名称和描述）。
    认为 None 和纯空格字符串为空。
    """
    return not (value and value.strip())

def _get_value_if_present(value): # 这个函数主要用于第三方DataFrame， pandas的NaN处理可能仍需保留
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
                                main_io_points: Optional[List[UploadedIOPoint]], # 修改：io_data_df -> main_io_points
                                main_sheet_output_name: str, # 修改：source_sheet_name -> main_sheet_output_name
                                output_path: str,
                                third_party_data: Optional[List[Tuple[str, pd.DataFrame]]] = None
                               ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时PLC点表。

        参数:
            main_io_points (Optional[List[UploadedIOPoint]]): 
                从主IO点表解析的数据列表 (使用UploadedIOPoint模型)。
            main_sheet_output_name (str): 在输出的XLS文件中，主IO点表Sheet的名称。
            output_path (str): 用户选择的 .xls 文件保存路径。
            third_party_data (Optional[List[Tuple[str, pd.DataFrame]]]): 
                一个包含元组的列表，每个元组代表一个第三方设备Sheet：(原始Sheet名, 该Sheet的DataFrame)。
                默认为None。

        返回:
            Tuple[bool, Optional[str]]: (操作是否成功, 错误消息或None)
        """
        logger.info(f"开始生成和利时PLC点表，主Sheet输出名称: '{main_sheet_output_name}', 输出路径: '{output_path}'")
        if third_party_data:
            tp_sheet_names = [name for name, _ in third_party_data]
            logger.info(f"同时处理第三方设备Sheets: {tp_sheet_names}")

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            
            # --- 1. 处理主IO点表 (第一个Sheet) ---
            main_sheet = workbook.add_sheet(main_sheet_output_name) # 使用传入的输出名称
            logger.info(f"主IO点表Sheet '{main_sheet_output_name}' 创建成功。")
            font_style = xlwt.XFStyle(); font = xlwt.Font(); font.name = '宋体'; font.height = 20 * 11; font_style.font = font
            alignment = xlwt.Alignment(); alignment.horz = xlwt.Alignment.HORZ_LEFT; alignment.vert = xlwt.Alignment.VERT_CENTER; font_style.alignment = alignment
            main_sheet.write(0, 0, f"{main_sheet_output_name}(COMMON)", font_style)
            headers = ["变量名", "直接地址", "变量说明", "变量类型", "初始值", "掉电保护", "可强制", "SOE使能"]
            for col_idx, header_title in enumerate(headers): main_sheet.write(1, col_idx, header_title, font_style)
            
            excel_write_row_counter = 1 # 从1开始，因为0是标题行，1是表头行
            if main_io_points:
                for point in main_io_points:
                    excel_write_row_counter += 1
                    current_main_excel_row = excel_write_row_counter
                    
                    # 从 UploadedIOPoint 对象获取数据
                    main_hmi_name_raw = point.hmi_variable_name
                    main_plc_address = str(point.plc_absolute_address or "").strip() # 确保是字符串且去除空格
                    main_description_raw = point.variable_description
                    main_data_type = str(point.data_type or "").upper()
                    main_channel_no_raw = str(point.channel_tag or "").strip()
                    module_type = str(point.module_type or "").upper()
                    
                    is_main_point_reserved = _is_value_empty_for_hmi_or_desc(main_hmi_name_raw)
                    
                    output_main_hmi_name: str
                    output_main_description: str
                    
                    if is_main_point_reserved:
                        channel_no_for_display = main_channel_no_raw if main_channel_no_raw else "未知"
                        output_main_hmi_name = f"YLDW{channel_no_for_display}"
                        output_main_description = f"预留点位{channel_no_for_display}"
                    else:
                        output_main_hmi_name = str(main_hmi_name_raw).strip() # main_hmi_name_raw 保证是 str
                        output_main_description = str(main_description_raw).strip() if not _is_value_empty_for_hmi_or_desc(main_description_raw) else ""
                    
                    if not main_plc_address and not is_main_point_reserved:
                        logger.warning(f"主点位 '{output_main_hmi_name}' 的PLC绝对地址为空，跳过此行及其关联点。")
                        excel_write_row_counter -=1 # 回退计数器
                        continue
                        
                    main_initial_value_to_write = 0 if main_data_type == "REAL" else "FALSE"
                    main_power_off_protection_to_write = "TRUE" if main_data_type == "REAL" else "FALSE"
                    main_can_force_to_write = "TRUE"
                    main_soe_enable_to_write = "TRUE" if main_data_type == "BOOL" else "FALSE"
                    
                    main_sheet.write(current_main_excel_row, 0, output_main_hmi_name, font_style)
                    main_sheet.write(current_main_excel_row, 1, main_plc_address, font_style)
                    main_sheet.write(current_main_excel_row, 2, output_main_description, font_style)
                    main_sheet.write(current_main_excel_row, 3, main_data_type if main_data_type else "", font_style)
                    main_sheet.write(current_main_excel_row, 4, main_initial_value_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 5, main_power_off_protection_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 6, main_can_force_to_write, font_style)
                    main_sheet.write(current_main_excel_row, 7, main_soe_enable_to_write, font_style)
                    
                    if module_type == 'AI':
                        for ip_config in INTERMEDIATE_POINTS_CONFIG_AI:
                            # 从 UploadedIOPoint 对象获取中间点数据
                            intermediate_address = str(getattr(point, ip_config['addr_attr'], None) or "").strip()
                            if not intermediate_address:
                                continue
                            
                            excel_write_row_counter += 1
                            current_ip_excel_row = excel_write_row_counter
                            intermediate_name_from_attr = getattr(point, ip_config['name_attr'], None)
                            
                            final_intermediate_name: str
                            if is_main_point_reserved:
                                final_intermediate_name = output_main_hmi_name + ip_config['name_suffix_for_reserved']
                            else:
                                if _is_value_empty_for_hmi_or_desc(intermediate_name_from_attr):
                                    base_name_for_ip = output_main_hmi_name
                                    final_intermediate_name = (base_name_for_ip if base_name_for_ip else "UNKNOWN_MAIN") + ip_config['name_suffix_for_reserved']
                                else:
                                    final_intermediate_name = str(intermediate_name_from_attr).strip()
                                    
                            final_intermediate_description = f"{output_main_description}_{ip_config['desc_suffix']}"
                            intermediate_data_type = ip_config['type']
                            
                            ip_initial_value_to_write = 0 if intermediate_data_type == "REAL" else "FALSE"
                            ip_power_off_protection_to_write = "TRUE" if intermediate_data_type == "REAL" else "FALSE"
                            ip_can_force_to_write = "TRUE"
                            ip_soe_enable_to_write = "TRUE" if intermediate_data_type == "BOOL" else "FALSE"
                            
                            main_sheet.write(current_ip_excel_row, 0, final_intermediate_name, font_style)
                            main_sheet.write(current_ip_excel_row, 1, intermediate_address, font_style)
                            main_sheet.write(current_ip_excel_row, 2, final_intermediate_description, font_style)
                            main_sheet.write(current_ip_excel_row, 3, intermediate_data_type, font_style)
                            main_sheet.write(current_ip_excel_row, 4, ip_initial_value_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 5, ip_power_off_protection_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 6, ip_can_force_to_write, font_style)
                            main_sheet.write(current_ip_excel_row, 7, ip_soe_enable_to_write, font_style)
            else:
                logger.info(f"主IO点表数据 (main_io_points) 为空。")
            
            main_sheet.col(0).width = 256 * 35; main_sheet.col(1).width = 256 * 20; main_sheet.col(2).width = 256 * 45; main_sheet.col(3).width = 256 * 15; main_sheet.col(4).width = 256 * 10; main_sheet.col(5).width = 256 * 12; main_sheet.col(6).width = 256 * 10; main_sheet.col(7).width = 256 * 12
            logger.info(f"主IO点表Sheet '{main_sheet_output_name}' 处理完毕。")

            # --- 2. 处理第三方设备点表 (后续Sheets) ---
            # 这部分逻辑基本保持不变，因为它已经处理DataFrame
            if third_party_data:
                for tp_idx, (tp_sheet_name, tp_df) in enumerate(third_party_data):
                    logger.info(f"开始处理第 {tp_idx+1} 个第三方设备Sheet: '{tp_sheet_name}'")
                    # Sheet名称长度限制由xlwt处理，或者可以在创建时截断
                    safe_tp_sheet_name = tp_sheet_name[:31] # 确保第三方sheet名称也不超过31字符
                    tp_output_sheet = workbook.add_sheet(safe_tp_sheet_name)
                    tp_output_sheet.write(0, 0, f"{safe_tp_sheet_name}(COMMON)", font_style) # 使用安全名称
                    for col_idx, header_title in enumerate(headers): tp_output_sheet.write(1, col_idx, header_title, font_style)

                    if tp_df.empty:
                        logger.warning(f"第三方设备Sheet '{tp_sheet_name}' (输出为 '{safe_tp_sheet_name}') 的数据为空。已创建带表头的空Sheet。")
                        # ... (设置列宽的代码保持不变)
                        tp_output_sheet.col(0).width = 256 * 35; tp_output_sheet.col(1).width = 256 * 20 # ... etc.
                        continue
                    
                    excel_tp_write_row_counter = 1 # 从1开始
                    for _, tp_row_data in tp_df.iterrows():
                        excel_tp_write_row_counter += 1
                        var_name = tp_row_data.get(TP_INPUT_VAR_NAME_COL, "")
                        plc_addr = str(tp_row_data.get(TP_INPUT_PLC_ADDRESS_COL, "")).strip()
                        desc = tp_row_data.get(TP_INPUT_DESCRIPTION_COL, "")
                        data_type = str(tp_row_data.get(TP_INPUT_DATA_TYPE_COL, "")).upper()
                        
                        if not var_name and not plc_addr:
                            logger.debug(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 的变量名和PLC地址均为空，跳过。")
                            excel_tp_write_row_counter -=1
                            continue

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

                            if len(present_settings) == 1:
                                try: initial_val_to_write = float(present_settings[0])
                                except (ValueError, TypeError): 
                                    logger.warning(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 点位 '{var_name}' 的设定值 '{present_settings[0]}' 不是有效数字，初始值将设为0。")
                                    initial_val_to_write = 0
                            elif len(present_settings) > 1:
                                logger.error(f"内部逻辑错误: 第三方Sheet '{tp_sheet_name}' 点位 '{var_name}' (行号参考 {excel_tp_write_row_counter}) 通过了validator校验，但在生成时仍检测到多个设定值: {present_settings}。将使用0作为初始值。")
                                initial_val_to_write = 0
                            else: # len(present_settings) == 0
                                initial_val_to_write = 0
                        elif data_type == "BOOL": initial_val_to_write = "FALSE"
                        else:
                            logger.warning(f"第三方Sheet '{tp_sheet_name}' 行 {excel_tp_write_row_counter} 点位 '{var_name}' 数据类型 '{data_type}' 未知，初始值将设为0。")
                            initial_val_to_write = 0
                        
                        power_off_prot_to_write = "TRUE" if data_type == "REAL" else "FALSE"
                        can_force_to_write = "TRUE"
                        soe_enable_to_write = "TRUE" if data_type == "BOOL" else "FALSE"
                        tp_output_sheet.write(excel_tp_write_row_counter, 0, var_name, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 1, plc_addr, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 2, desc, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 3, data_type if data_type else "", font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 4, initial_val_to_write, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 5, power_off_prot_to_write, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 6, can_force_to_write, font_style)
                        tp_output_sheet.write(excel_tp_write_row_counter, 7, soe_enable_to_write, font_style)

                    tp_output_sheet.col(0).width = 256 * 35; tp_output_sheet.col(1).width = 256 * 20; tp_output_sheet.col(2).width = 256 * 45; tp_output_sheet.col(3).width = 256 * 15; tp_output_sheet.col(4).width = 256 * 10; tp_output_sheet.col(5).width = 256 * 12; tp_output_sheet.col(6).width = 256 * 10; tp_output_sheet.col(7).width = 256 * 12
                    logger.info(f"第三方设备Sheet '{tp_sheet_name}' (输出为 '{safe_tp_sheet_name}') 处理完毕。")
            
            workbook.save(output_path)
            logger.info(f"和利时PLC点表已成功生成并保存到: {output_path} (包含主IO点表和所有第三方设备点表)")
            return True, None
        except KeyError as ke: # 虽然我们尽量避免了.get()，但万一有其他地方的KeyError
            error_msg = f"生成和利时点表失败：代码逻辑中可能存在未预期的键错误: {ke}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg
        except Exception as e:
            error_msg = f"生成和利时PLC点表时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    # 创建示例 UploadedIOPoint 数据
    sample_main_io_points: List[UploadedIOPoint] = [
        UploadedIOPoint(
            hmi_variable_name="AI_PT_001", plc_absolute_address="%MD100", variable_description="压力变送器001", 
            data_type="REAL", channel_tag="CH1", module_type="AI",
            sll_set_point="AI_PT_001_LoLoLimit", sll_set_point_plc_address="%MD104",
            sl_set_point="AI_PT_001_LoLimit", sl_set_point_plc_address="%MD108",
            sh_set_point="AI_PT_001_HiLimit", sh_set_point_plc_address="%MD112",
            shh_set_point="AI_PT_001_HiHiLimit", shh_set_point_plc_address="%MD116",
            ll_alarm="AI_PT_001_LL", ll_alarm_plc_address="%MX20.0",
            l_alarm="AI_PT_001_L", l_alarm_plc_address="%MX20.1",
            h_alarm="AI_PT_001_H", h_alarm_plc_address="%MX20.2",
            hh_alarm="AI_PT_001_HH", hh_alarm_plc_address="%MX20.3",
            maintenance_set_point="AI_PT_001_whz", maintenance_set_point_plc_address="%MD120",
            maintenance_enable_switch_point="AI_PT_001_whzzt", maintenance_enable_switch_point_plc_address="%MX20.4",
            # 其他字段根据需要填充或保持None
        ),
        UploadedIOPoint( # AI预留点位
            hmi_variable_name=None, plc_absolute_address="%MD200", variable_description=None, 
            data_type="REAL", channel_tag="CH2_AI_Res", module_type="AI",
            sll_set_point_plc_address="%MD204", # 假设预留点位的中间点名称属性为空
            sl_set_point_plc_address="%MD208",
            sh_set_point_plc_address="%MD212",
            shh_set_point_plc_address="%MD216",
            ll_alarm_plc_address="%MX21.0",
            l_alarm_plc_address="%MX21.1",
            h_alarm_plc_address="%MX21.2",
            hh_alarm_plc_address="%MX21.3",
            maintenance_set_point_plc_address="%MD220",
            maintenance_enable_switch_point_plc_address="%MX21.4",
        ),
        UploadedIOPoint(
            hmi_variable_name="DI_PUMP_01_RUN", plc_absolute_address="%MX30.0", variable_description="1号泵运行状态", 
            data_type="BOOL", channel_tag="CH3_DI", module_type="DI",
        ),
        UploadedIOPoint( # 主PLC地址为空的AI点 (应被跳过)
            hmi_variable_name="AI_TEST_NO_MAIN_ADDR", plc_absolute_address="", variable_description="无主地址AI点", 
            data_type="REAL", channel_tag="CH4", module_type="AI",
            sll_set_point="AI_TEST_NO_MAIN_ADDR_LoLoLimit", sll_set_point_plc_address="%MD404",
        ),
        UploadedIOPoint( # 完全空的点 (应被跳过，如果hmi_variable_name 和 plc_absolute_address 都为空)
            module_type="AI" # 假设至少有类型
        )
    ]

    # 创建示例第三方数据
    sample_tp_data_list = [
        {TP_INPUT_VAR_NAME_COL: "TP_VALVE_OPEN", TP_INPUT_PLC_ADDRESS_COL: "%MX500.0", TP_INPUT_DESCRIPTION_COL: "第三方阀门开", TP_INPUT_DATA_TYPE_COL: "BOOL"},
        {TP_INPUT_VAR_NAME_COL: "TP_MOTOR_SPEED", TP_INPUT_PLC_ADDRESS_COL: "%MD5000", TP_INPUT_DESCRIPTION_COL: "第三方马达速度", TP_INPUT_DATA_TYPE_COL: "REAL", TP_INPUT_SLL_SET_COL: "10.0"},
    ]
    tp_df1 = pd.DataFrame(sample_tp_data_list)
    third_party_input_for_test: List[Tuple[str, pd.DataFrame]] = [("第三方设备1", tp_df1)]
    
    empty_tp_df = pd.DataFrame(columns=[TP_INPUT_VAR_NAME_COL, TP_INPUT_PLC_ADDRESS_COL, TP_INPUT_DATA_TYPE_COL])
    third_party_input_with_empty: List[Tuple[str, pd.DataFrame]] = [("第三方设备1", tp_df1), ("空第三方", empty_tp_df)]


    generator = HollysysGenerator()
    output_main_sheet_name = "测试IO表_Output"
    
    output_file_complex = "test_hollysys_table_from_model_v1.xls"
    success, msg = generator.generate_hollysys_table(sample_main_io_points, output_main_sheet_name, output_file_complex, third_party_input_for_test)
    if success:
        print(f"复杂场景测试文件 '{output_file_complex}' 生成成功。")
    else:
        print(f"复杂场景测试文件 '{output_file_complex}' 生成失败: {msg}")

    output_file_no_main = "test_hollysys_no_main_v1.xls"
    success_no_main, msg_no_main = generator.generate_hollysys_table(None, "无主IO表", output_file_no_main, third_party_input_for_test)
    if success_no_main:
        print(f"无主IO点测试文件 '{output_file_no_main}' 生成成功。")
    else:
        print(f"无主IO点测试文件 '{output_file_no_main}' 生成失败: {msg_no_main}")

    output_file_no_tp = "test_hollysys_no_tp_v1.xls"
    success_no_tp, msg_no_tp = generator.generate_hollysys_table(sample_main_io_points, output_main_sheet_name, output_file_no_tp, None)
    if success_no_tp:
        print(f"无第三方数据测试文件 '{output_file_no_tp}' 生成成功。")
    else:
        print(f"无第三方数据测试文件 '{output_file_no_tp}' 生成失败: {msg_no_tp}")
        
    output_file_all_empty = "test_hollysys_all_empty_v1.xls"
    success_all_empty, msg_all_empty = generator.generate_hollysys_table(None, "全空表", output_file_all_empty, None)
    if success_all_empty: # 即使都为空，也应该能生成一个带表头的空文件
        print(f"全空输入测试文件 '{output_file_all_empty}' 生成成功。")
    else:
        print(f"全空输入测试文件 '{output_file_all_empty}' 生成失败: {msg_all_empty}")

    output_file_with_empty_tp = "test_hollysys_with_empty_tp_v1.xls"
    success_empty_tp, msg_empty_tp = generator.generate_hollysys_table(sample_main_io_points, output_main_sheet_name, output_file_with_empty_tp, third_party_input_with_empty)
    if success_empty_tp:
        print(f"包含空第三方Sheet的测试文件 '{output_file_with_empty_tp}' 生成成功。")
    else:
        print(f"包含空第三方Sheet的测试文件 '{output_file_with_empty_tp}' 生成失败: {msg_empty_tp}") 