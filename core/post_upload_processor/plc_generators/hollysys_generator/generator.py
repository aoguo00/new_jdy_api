import pandas as pd
import xlwt
import logging
from typing import Optional, List, Tuple, Any, Dict
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

# --- Constants for Third-Party Input Sheet Columns (这些将不再使用，因为数据已是UploadedIOPoint) ---
# TP_INPUT_VAR_NAME_COL = "变量名称"
# TP_INPUT_PLC_ADDRESS_COL = "PLC地址"
# TP_INPUT_DESCRIPTION_COL = "变量描述"
# TP_INPUT_DATA_TYPE_COL = "数据类型"
# TP_INPUT_SLL_SET_COL = "SLL设定值"
# TP_INPUT_SL_SET_COL = "SL设定值"
# TP_INPUT_SH_SET_COL = "SH设定值"
# TP_INPUT_SHH_SET_COL = "SHH设定值"

# Configuration for AI module's intermediate points
# 修改: name_col -> name_attr, addr_col -> addr_attr，值更新为 UploadedIOPoint 的属性名
# INTERMEDIATE_POINTS_CONFIG_AI = [
#     {'name_attr': 'sll_set_point', 'addr_attr': 'sll_set_point_plc_address', 'type': 'REAL', 'desc_suffix': 'SLL设定', 'name_suffix_for_reserved': '_LoLoLimit'},
#     {'name_attr': 'sl_set_point',  'addr_attr': 'sl_set_point_plc_address',  'type': 'REAL', 'desc_suffix': 'SL设定',  'name_suffix_for_reserved': '_LoLimit'},
#     {'name_attr': 'sh_set_point',  'addr_attr': 'sh_set_point_plc_address',  'type': 'REAL', 'desc_suffix': 'SH设定',  'name_suffix_for_reserved': '_HiLimit'},
#     {'name_attr': 'shh_set_point', 'addr_attr': 'shh_set_point_plc_address', 'type': 'REAL', 'desc_suffix': 'SHH设定', 'name_suffix_for_reserved': '_HiHiLimit'},
#     {'name_attr': 'll_alarm',  'addr_attr': 'll_alarm_plc_address',  'type': 'BOOL', 'desc_suffix': 'LL报警',  'name_suffix_for_reserved': '_LL'},
#     {'name_attr': 'l_alarm',   'addr_attr': 'l_alarm_plc_address',   'type': 'BOOL', 'desc_suffix': 'L报警',   'name_suffix_for_reserved': '_L'},
#     {'name_attr': 'h_alarm',   'addr_attr': 'h_alarm_plc_address',   'type': 'BOOL', 'desc_suffix': 'H报警',   'name_suffix_for_reserved': '_H'},
#     {'name_attr': 'hh_alarm',  'addr_attr': 'hh_alarm_plc_address',  'type': 'BOOL', 'desc_suffix': 'HH报警',  'name_suffix_for_reserved': '_HH'},
#     {'name_attr': 'maintenance_set_point', 'addr_attr': 'maintenance_set_point_plc_address', 'type': 'REAL', 'desc_suffix': '维护值设定', 'name_suffix_for_reserved': '_whz'},
#     {'name_attr': 'maintenance_enable_switch_point',  'addr_attr': 'maintenance_enable_switch_point_plc_address',  'type': 'BOOL', 'desc_suffix': '维护使能',  'name_suffix_for_reserved': '_whzzt'},
# ]

def _is_value_empty(value: Optional[str]) -> bool:
    """
    辅助函数：检查字符串值是否为空或仅包含空格。
    """
    return not (value and value.strip())

def _get_value_if_present(value): # 这个函数主要用于第三方DataFrame， pandas的NaN处理可能仍需保留
    """辅助函数：如果值存在（非NaN，非None，非空字符串），则返回该值，否则返回None。"""
    if pd.isna(value) or value is None or (isinstance(value, str) and not value.strip()):
        return None
    return value

class HollysysGenerator:
    """
    负责根据已处理的 UploadedIOPoint 数据列表生成和利时PLC点表 (.xls格式)。
    """

    def __init__(self):
        pass

    def _write_data_to_sheet(self, 
                             sheet: xlwt.Worksheet, 
                             points_for_sheet: List[UploadedIOPoint], 
                             sheet_title: str) -> int:
        """
        将指定点位列表的数据写入到给定的xlwt工作表中。
        返回写入的数据行数。
        """
        font_style = xlwt.XFStyle()
        font = xlwt.Font()
        font.name = '宋体'
        font.height = 20 * 11 # 11号字
        font_style.font = font
        alignment = xlwt.Alignment()
        alignment.horz = xlwt.Alignment.HORZ_LEFT
        alignment.vert = xlwt.Alignment.VERT_CENTER
        font_style.alignment = alignment
        
        # 写入工作表特定的大标题，例如 "IO点表(COMMON)"
        sheet.write(0, 0, f"{sheet_title}(COMMON)", font_style)
        headers = ["变量名", "直接地址", "变量说明", "变量类型", "初始值", "掉电保护", "可强制", "SOE使能"]
        for col_idx, header_title in enumerate(headers):
            sheet.write(1, col_idx, header_title, font_style)
        
        excel_write_row_counter = 1 # 从1开始，因为0是标题行，1是表头行

        if not points_for_sheet:
            logger.info(f"工作表 '{sheet_title}' 的IO点数据列表为空。将只包含表头。")
        else:
            for point_idx, point in enumerate(points_for_sheet):
                hmi_name = point.hmi_variable_name or ""
                plc_address = point.plc_absolute_address or ""
                description = point.variable_description or ""
                data_type = (point.data_type or "").upper()
                source_sheet_from_point = point.source_sheet_name or "N/A" # 实际点位记录的来源
                source_type = point.source_type or "N/A"

                if _is_value_empty(plc_address):
                    if _is_value_empty(hmi_name):
                        logger.debug(f"工作表 '{sheet_title}', 点位索引 {point_idx}: 跳过点位: HMI名和PLC地址均为空。来源: {source_sheet_from_point}/{source_type}")
                    else:
                        logger.warning(f"工作表 '{sheet_title}', 点位索引 {point_idx}: 点位 '{hmi_name}' (描述: '{description}', 来源: {source_sheet_from_point}/{source_type}) PLC地址为空，跳过。")
                    continue
                
                if _is_value_empty(hmi_name):
                    logger.warning(f"工作表 '{sheet_title}', 点位索引 {point_idx}: 点位PLC地址 '{plc_address}' 但HMI名为空。来源: {source_sheet_from_point}/{source_type}。将用PLC地址作名称。")
                    hmi_name = plc_address

                initial_value_to_write: Any
                if data_type == "REAL": initial_value_to_write = 0
                elif data_type == "BOOL": initial_value_to_write = "FALSE"
                else:
                    logger.warning(f"工作表 '{sheet_title}', 点位 '{hmi_name}' (地址: {plc_address}, 来源: {source_sheet_from_point}/{source_type}) 数据类型 '{data_type}' 未知或为空，初始值设为0。")
                    initial_value_to_write = "0"

                power_off_protection_to_write = "TRUE" if data_type == "REAL" else "FALSE"
                can_force_to_write = "TRUE"
                soe_enable_to_write = "TRUE" if data_type == "BOOL" else "FALSE"
                
                excel_write_row_counter += 1
                current_excel_row = excel_write_row_counter
                
                sheet.write(current_excel_row, 0, hmi_name, font_style)
                sheet.write(current_excel_row, 1, plc_address, font_style)
                sheet.write(current_excel_row, 2, description, font_style)
                sheet.write(current_excel_row, 3, data_type if data_type else "", font_style)
                sheet.write(current_excel_row, 4, initial_value_to_write, font_style)
                sheet.write(current_excel_row, 5, power_off_protection_to_write, font_style)
                sheet.write(current_excel_row, 6, can_force_to_write, font_style)
                sheet.write(current_excel_row, 7, soe_enable_to_write, font_style)
        
        # 设置列宽 (针对当前sheet)
        sheet.col(0).width = 256 * 35
        sheet.col(1).width = 256 * 20
        sheet.col(2).width = 256 * 45
        sheet.col(3).width = 256 * 15
        sheet.col(4).width = 256 * 10
        sheet.col(5).width = 256 * 12
        sheet.col(6).width = 256 * 10
        sheet.col(7).width = 256 * 12
        
        return excel_write_row_counter - 1 # 返回实际写入的数据行数

    def generate_hollysys_table(self, 
                                points_by_sheet: Dict[str, List[UploadedIOPoint]], # 修改：接收按工作表分组的点位字典
                                output_path: str
                               ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时PLC点表。
        会为传入字典中的每个原始工作表名创建一个对应的目标工作表，并写入其点位数据。

        参数:
            points_by_sheet (Dict[str, List[UploadedIOPoint]]): 
                一个字典，键是原始工作表名，值是该工作表对应的 UploadedIOPoint 列表。
            output_path (str): 用户选择的 .xls 文件保存路径。

        返回:
            Tuple[bool, Optional[str]]: (操作是否成功, 错误消息或None)
        """
        logger.info(f"--- HollysysGenerator: generate_hollysys_table 方法开始 (多工作表模式) ---")
        logger.info(f"传入参数: output_path='{output_path}'")
        logger.info(f"接收到 {len(points_by_sheet)} 个工作表的数据进行处理。")

        if not points_by_sheet:
            logger.warning("传入的点位数据字典为空，无法生成任何工作表。")
            # 决定是生成一个空文件还是返回错误。这里选择不生成文件并返回提示。
            return False, "没有提供任何工作表数据来生成点表。"

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            total_points_written = 0
            sheets_created_count = 0

            for sheet_name, points_list_for_this_sheet in points_by_sheet.items():
                # 对工作表名进行清理，确保符合xlwt的要求 (例如长度和特殊字符)
                safe_sheet_name = "".join(c for c in sheet_name if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_sheet_name = safe_sheet_name[:31] # xlwt 工作表名长度限制为31
                if not safe_sheet_name: # 如果清理后为空，给一个默认名
                    # 生成一个基于原始键列表索引的唯一名称，以防多个清理后为空的表名
                    original_keys = list(points_by_sheet.keys())
                    try:
                        idx = original_keys.index(sheet_name) + 1
                        safe_sheet_name = f"Sheet_{idx}"
                    except ValueError:
                        # 理论上不应发生，因为 sheet_name 来自于 keys
                        safe_sheet_name = f"AutoGenSheet_{sheets_created_count + 1}"
                
                logger.info(f"尝试为原始工作表 '{sheet_name}' 添加目标工作表，名称为: '{safe_sheet_name}'")
                
                try:
                    sheet = workbook.add_sheet(safe_sheet_name)
                    logger.info(f"成功添加工作表: '{sheet.name}' (源: '{sheet_name}') 到工作簿。")
                    sheets_created_count += 1
                except Exception as e_add_sheet:
                    logger.error(f"为源工作表 '{sheet_name}' 添加目标工作表 '{safe_sheet_name}' 失败: {e_add_sheet}. 跳过此工作表。")
                    continue # 跳过这个工作表，继续处理下一个

                # 即使点位列表为空，也调用写入，_write_data_to_sheet 会处理这种情况（只写表头）
                rows_written_for_sheet = self._write_data_to_sheet(sheet, points_list_for_this_sheet, safe_sheet_name) 
                total_points_written += rows_written_for_sheet
                logger.info(f"工作表 '{safe_sheet_name}' (源: '{sheet_name}') 处理完毕。写入了 {rows_written_for_sheet} 行数据。")
            
            if sheets_created_count > 0:
                logger.info(f"准备保存工作簿到 '{output_path}'。总共创建 {sheets_created_count} 个工作表，写入了 {total_points_written} 个点位。")
                workbook.save(output_path)
                logger.info(f"和利时PLC点表已成功生成并保存到: {output_path}")
                logger.info(f"--- HollysysGenerator: generate_hollysys_table 方法结束 (多工作表模式) ---")
                return True, None
            else:
                logger.warning("没有成功创建任何工作表，因此不保存文件。")
                logger.info(f"--- HollysysGenerator: generate_hollysys_table 方法结束 (多工作表模式，无输出) ---")
                return False, "未能成功创建任何工作表（可能是由于工作表名称问题或所有源表都无法添加）。"
            
        except Exception as e:
            error_msg = f"生成和利时PLC点表时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            logger.info(f"--- HollysysGenerator: generate_hollysys_table 方法因错误而结束 (多工作表模式) ---")
            return False, error_msg

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    # 创建示例 UploadedIOPoint 数据，现在是字典结构
    sample_points_by_sheet: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(hmi_variable_name="AI_PT_001", plc_absolute_address="%MD100", variable_description="压力变送器001", data_type="REAL", source_sheet_name="IO点表", source_type="main_io"),
            UploadedIOPoint(hmi_variable_name="AI_PT_001_SLL设定", plc_absolute_address="%MD102", variable_description="压力变送器001_SLL设定",data_type="REAL", source_sheet_name="IO点表", source_type="intermediate_from_main"),
            UploadedIOPoint(hmi_variable_name="DI_PUMP_01_RUN", plc_absolute_address="%MX30.0", variable_description="1号泵运行状态", data_type="BOOL", source_sheet_name="IO点表", source_type="main_io"),
            UploadedIOPoint(hmi_variable_name="NO_PLC_FOR_IO_SHEET", plc_absolute_address=None, data_type="REAL", source_sheet_name="IO点表", source_type="main_io") # 应跳过
        ],
        "第三方设备A": [
            UploadedIOPoint(hmi_variable_name="TP_VALVE_OPEN", plc_absolute_address="%MX500.0", variable_description="第三方阀门开", data_type="BOOL", source_sheet_name="第三方设备A", source_type="third_party"),
            UploadedIOPoint(hmi_variable_name="TP_MOTOR_SPEED", plc_absolute_address="%MD5000", variable_description="第三方马达速度", data_type="REAL", source_sheet_name="第三方设备A", source_type="third_party")
        ],
        "空设备表": [], # 测试空点位列表的工作表创建
        "特殊字符表名[]:*?/\\": [ # 测试特殊字符表名清理
            UploadedIOPoint(hmi_variable_name="SPEC_CHAR_POINT", plc_absolute_address="%MW100", data_type="WORD", source_sheet_name="特殊字符表名[]:*?/\\", source_type="third_party")
        ],
        "超长工作表名这是一个非常非常非常非常非常非常长的名字用来测试截断": [
             UploadedIOPoint(hmi_variable_name="LONG_NAME_SHT_PT", plc_absolute_address="%MW200", data_type="WORD")
        ]
    }

    generator = HollysysGenerator()
    
    output_file_multisheet = "test_hollysys_multisheet_v1.xls"
    logger.info(f"\\n--- 开始测试: 多工作表模式 ({output_file_multisheet}) ---")
    success, msg = generator.generate_hollysys_table(sample_points_by_sheet, output_file_multisheet)
    if success:
        print(f"多工作表测试文件 '{output_file_multisheet}' 生成成功。")
    else:
        print(f"多工作表测试文件 '{output_file_multisheet}' 生成失败: {msg}")

    output_file_empty_dict = "test_hollysys_empty_dict_v1.xls"
    logger.info(f"\\n--- 开始测试: 空字典输入 ({output_file_empty_dict}) ---")
    success_empty, msg_empty = generator.generate_hollysys_table({}, output_file_empty_dict)
    if success_empty:
        print(f"空字典输入测试文件 '{output_file_empty_dict}' 生成成功。") # 预期是失败或不生成文件
    else:
        print(f"空字典输入测试文件 '{output_file_empty_dict}' 生成失败或未生成: {msg_empty}") 