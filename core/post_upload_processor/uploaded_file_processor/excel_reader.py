# core/post_upload_processor/uploaded_file_processor/excel_reader.py
import openpyxl
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from .io_data_model import UploadedIOPoint
import logging

logger = logging.getLogger(__name__)

# 主IO点表在Excel中通常的名称
MAIN_IO_SHEET_NAME = "IO点表"

# 这个映射表是核心，它将Excel中的中文表头映射到UploadedIOPoint数据类的属性名
# 我们需要确保这个映射是完整和正确的，基于 excel_exporter.py 中的 headers_plc
HEADER_TO_ATTRIBUTE_MAP: Dict[str, str] = {
    "序号": "serial_number",
    "模块名称": "module_name",
    "模块类型": "module_type",
    "供电类型（有源/无源）": "power_supply_type",
    "线制": "wiring_system",
    "通道位号": "channel_tag",
    "场站名": "site_name",
    "场站编号": "site_number",
    "变量名称（HMI）": "hmi_variable_name",
    "变量描述": "variable_description",
    "数据类型": "data_type",
    "读写属性": "read_write_property",
    "保存历史": "save_history",
    "掉电保护": "power_off_protection",
    "量程低限": "range_low_limit",
    "量程高限": "range_high_limit",
    "SLL设定值": "sll_set_value",
    "SLL设定点位": "sll_set_point",
    "SLL设定点位_PLC地址": "sll_set_point_plc_address",
    "SLL设定点位_通讯地址": "sll_set_point_comm_address",
    "SL设定值": "sl_set_value",
    "SL设定点位": "sl_set_point",
    "SL设定点位_PLC地址": "sl_set_point_plc_address",
    "SL设定点位_通讯地址": "sl_set_point_comm_address",
    "SH设定值": "sh_set_value",
    "SH设定点位": "sh_set_point",
    "SH设定点位_PLC地址": "sh_set_point_plc_address",
    "SH设定点位_通讯地址": "sh_set_point_comm_address",
    "SHH设定值": "shh_set_value",
    "SHH设定点位": "shh_set_point",
    "SHH设定点位_PLC地址": "shh_set_point_plc_address",
    "SHH设定点位_通讯地址": "shh_set_point_comm_address",
    "LL报警": "ll_alarm",
    "LL报警_PLC地址": "ll_alarm_plc_address",
    "LL报警_通讯地址": "ll_alarm_comm_address",
    "L报警": "l_alarm",
    "L报警_PLC地址": "l_alarm_plc_address",
    "L报警_通讯地址": "l_alarm_comm_address",
    "H报警": "h_alarm",
    "H报警_PLC地址": "h_alarm_plc_address",
    "H报警_通讯地址": "h_alarm_comm_address",
    "HH报警": "hh_alarm",
    "HH报警_PLC地址": "hh_alarm_plc_address",
    "HH报警_通讯地址": "hh_alarm_comm_address",
    "维护值设定": "maintenance_set_value",
    "维护值设定点位": "maintenance_set_point",
    "维护值设定点位_PLC地址": "maintenance_set_point_plc_address",
    "维护值设定点位_通讯地址": "maintenance_set_point_comm_address",
    "维护使能开关点位": "maintenance_enable_switch_point",
    "维护使能开关点位_PLC地址": "maintenance_enable_switch_point_plc_address",
    "维护使能开关点位_通讯地址": "maintenance_enable_switch_point_comm_address",
    "PLC绝对地址": "plc_absolute_address",
    "上位机通讯地址": "hmi_communication_address"
}

def _parse_io_sheet_to_uploaded_points(sheet: openpyxl.worksheet.worksheet.Worksheet) -> List[UploadedIOPoint]:
    """
    将单个符合IO点表结构的工作表 (openpyxl.worksheet) 解析为 UploadedIOPoint 对象列表。
    """
    processed_data: List[UploadedIOPoint] = []
    
    # 获取表头
    header_row_cells = sheet[1] # 第一行为表头
    header_row = [cell.value for cell in header_row_cells]
    
    # 验证表头是否包含所有期望的映射键 (与原逻辑类似，可选增强)
    for expected_header in HEADER_TO_ATTRIBUTE_MAP.keys():
        if expected_header not in header_row:
            logger.warning(f"工作表 \'{sheet.title}\' 中，期望的表头 \'{expected_header}\' 未找到。该列数据将无法解析。")

    # 创建一个从当前文件表头到 UploadedIOPoint 属性的映射
    current_file_header_to_attr_map: Dict[str, str] = {}
    for col_idx, header_cell_value in enumerate(header_row):
        if isinstance(header_cell_value, str) and header_cell_value in HEADER_TO_ATTRIBUTE_MAP:
            current_file_header_to_attr_map[header_cell_value] = HEADER_TO_ATTRIBUTE_MAP[header_cell_value]

    # 从第二行开始读取数据行 (跳过表头)
    for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2): # min_row=2 表示从第二行开始
        row_data: Dict[str, Any] = {}
        is_empty_row = True
        for col_idx, cell in enumerate(row):
            header_name = header_row[col_idx] if col_idx < len(header_row) else None
            if header_name and header_name in current_file_header_to_attr_map:
                attribute_name = current_file_header_to_attr_map[header_name]
                cell_value = cell.value
                row_data[attribute_name] = str(cell_value) if cell_value is not None else None
                if cell_value is not None:
                    is_empty_row = False
        
        if not is_empty_row: # 只有非空行才创建对象
            try:
                # 确保所有 UploadedIOPoint 的字段都在 row_data 中，如果缺少则用 None 填充
                # dataclass 会自动处理默认值为 None 的情况，但如果映射不全，**kwargs 会失败
                # 因此，确保 HEADER_TO_ATTRIBUTE_MAP 涵盖所有 UploadedIOPoint 的字段是重要的
                # 或者在创建 UploadedIOPoint 前，确保 row_data 包含所有预期的键（即使值是 None）
                # (当前 UploadedIOPoint 所有字段都有默认值 None，所以直接解包是安全的)
                point = UploadedIOPoint(**row_data)
                processed_data.append(point)
            except TypeError as e:
                logger.error(f"在工作表 \'{sheet.title}\' 创建 UploadedIOPoint 实例时出错 (行 {row_idx}): {e}. 数据: {row_data}")
        
    logger.info(f"成功从工作表 \'{sheet.title}\' 读取并处理了 {len(processed_data)} 条IO点数据。")
    return processed_data


def load_workbook_data(file_path: str) -> Tuple[Optional[List[UploadedIOPoint]], List[Tuple[str, pd.DataFrame]], Optional[str]]:
    """
    加载Excel工作簿中的所有数据。
    主IO点表 (默认为 "IO点表") 被解析为 List[UploadedIOPoint]。
    其他所有工作表被加载为 pandas DataFrame。

    Args:
        file_path (str): Excel文件的路径。

    Returns:
        Tuple[Optional[List[UploadedIOPoint]], List[Tuple[str, pd.DataFrame]], Optional[str]]:
            - main_io_points: 从主IO点表解析的数据列表，如果未找到或解析失败则为 None。
            - third_party_sheet_data: 其他工作表的列表，每个元素为 (sheet_name, DataFrame)。
            - error_message: 如果发生严重错误，则为错误消息字符串，否则为 None。
    """
    main_io_points: Optional[List[UploadedIOPoint]] = None
    third_party_sheet_data: List[Tuple[str, pd.DataFrame]] = []

    try:
        # 1. 使用 openpyxl 加载整个工作簿，主要用于精确解析主IO点表
        opxl_workbook = openpyxl.load_workbook(file_path, data_only=True)
        
        # 2. 使用 pandas.ExcelFile 获取所有sheet名称并方便地读取其他sheet为DataFrame
        #    这是因为pandas读取DataFrame更直接，而openpyxl逐行解析对特定模型更灵活
        try:
            pd_excel_file = pd.ExcelFile(file_path)
            all_sheet_names_from_pandas = pd_excel_file.sheet_names
        except Exception as e_pd:
            logger.error(f"Pandas无法打开Excel文件以获取工作表名称列表: {file_path}, 错误: {e_pd}")
            return None, [], f"无法使用Pandas分析文件结构: {e_pd}"

        # 处理主IO点表
        if MAIN_IO_SHEET_NAME in opxl_workbook.sheetnames:
            logger.info(f"找到主IO点表: '{MAIN_IO_SHEET_NAME}'。开始使用openpyxl解析...")
            io_sheet_obj = opxl_workbook[MAIN_IO_SHEET_NAME]
            parsed_points = _parse_io_sheet_to_uploaded_points(io_sheet_obj)
            if parsed_points: # 仅当解析结果非空时赋值
                main_io_points = parsed_points
            else:
                logger.info(f"主IO点表 '{MAIN_IO_SHEET_NAME}' 解析后数据为空。")
        else:
            logger.warning(f"在文件 '{file_path}' 中未找到预期主IO点表: '{MAIN_IO_SHEET_NAME}'。")

        # 处理其他第三方工作表
        for sheet_name in all_sheet_names_from_pandas:
            if sheet_name == MAIN_IO_SHEET_NAME:
                continue # 主表已由openpyxl处理

            logger.info(f"尝试将工作表 '{sheet_name}' 作为第三方设备表加载 (使用pandas)...")
            try:
                df = pd.read_excel(pd_excel_file, sheet_name=sheet_name)
                if not df.empty:
                    third_party_sheet_data.append((sheet_name, df))
                    logger.info(f"成功将工作表 '{sheet_name}' 加载为DataFrame (包含 {len(df)} 行数据)。")
                else:
                    logger.info(f"工作表 '{sheet_name}' 为空，已跳过。")
            except Exception as e_read_tp_pd:
                logger.warning(f"使用pandas读取第三方工作表 '{sheet_name}' 时出错: {e_read_tp_pd}。将跳过此表。")
        
        return main_io_points, third_party_sheet_data, None

    except FileNotFoundError:
        logger.error(f"Excel文件未找到: {file_path}")
        return None, [], f"Excel文件未找到: {file_path}"
    except Exception as e_opxl: # 其他 openpyxl 加载错误
        logger.error(f"使用openpyxl打开或处理Excel文件 '{file_path}' 时发生错误: {e_opxl}", exc_info=True)
        return None, [], f"打开或处理Excel文件时发生错误: {e_opxl}"


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    test_file_path = "test_multi_sheet_io_table.xlsx"

    # --- 创建一个包含 "IO点表" 和其他工作表的测试Excel文件 ---
    logger.info(f"准备创建测试Excel文件: {test_file_path}")
    wb_test = openpyxl.Workbook()
    
    # 1. 创建 "IO点表"
    ws_io = wb_test.active
    if ws_io is not None: # 确保 active sheet 存在
        ws_io.title = MAIN_IO_SHEET_NAME
        headers_for_io_test = list(HEADER_TO_ATTRIBUTE_MAP.keys())
        ws_io.append(headers_for_io_test)
        # 示例数据 (与之前的测试类似)
        ws_io.append([
            "1", "S7-1200_Main", "AI", "有源", "2线", "AI01_M", 
            "主站", "S001", "TE_MAIN_01", "主温度1", "REAL", "R/W", "是", "是", 
            "0", "100", "1", "TE_MAIN_01_SLL", "%MD1000", "41001",
            "2", "TE_MAIN_01_SL", "%MD1004", "41003", 
            "98", "TE_MAIN_01_SH", "%MD1008", "41005",
            "99", "TE_MAIN_01_SHH", "%MD1012", "41007",
            "AL_LL_M", "%MX100.0", "30101", "AL_L_M", "%MX100.1", "30102",
            "AL_H_M", "%MX100.2", "30103", "AL_HH_M", "%MX100.3", "30104",
            "50_M", "MaintVal_M", "%MD1016", "41009", "MaintEn_M", "%MX100.4", "30105",
            "%MD1020", "41011"
        ] + [None] * (len(headers_for_io_test) - 53)) # 填充以匹配表头长度
        ws_io.append([
            "2", "S7-1200_Main", "DI", "无源", "2线", "DI01_M", 
            "主站", "S001", "XS_MAIN_01", "主限位1", "BOOL", "R", "否", "否", 
            None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,
            None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,None,
            None,None,None, "%MX100.5", "30106"
        ] + [None] * (len(headers_for_io_test) - 53))
        logger.info(f"\'{MAIN_IO_SHEET_NAME}\' 已准备数据。")
    else:
        logger.error("无法获取active worksheet来创建IO点表。")

    # 2. 创建一个第三方设备表 "电动阀"
    ws_tp1 = wb_test.create_sheet(title="电动阀")
    headers_tp1 = ["序号", "变量名称", "变量描述", "数据类型", "PLC地址", "MODBUS地址", "SLL设定值"]
    ws_tp1.append(headers_tp1)
    ws_tp1.append([1, "Valve_01_OpenFBK", "电动阀01开反馈", "BOOL", "%MX200.0", "30201", None])
    ws_tp1.append([2, "Valve_01_Cmd", "电动阀01开指令", "BOOL", "%MX200.1", "30202", None])
    ws_tp1.append([3, "Valve_01_Position", "电动阀01位置", "REAL", "%MD2000", "42001", 0])
    logger.info("\'电动阀\' sheet 已准备数据。")

    # 3. 创建另一个空的第三方设备表 "传感器组"
    ws_tp2 = wb_test.create_sheet(title="传感器组")
    headers_tp2 = ["设备名称", "传感器型号", "安装位置"]
    ws_tp2.append(headers_tp2)
    # 此表故意留空数据行
    logger.info("\'传感器组\' sheet (空数据表) 已准备。")

    try:
        wb_test.save(test_file_path)
        logger.info(f"测试Excel文件 \'{test_file_path}\' 已成功创建/覆盖。")
    except Exception as e_save:
        logger.error(f"保存测试Excel文件时出错: {e_save}")
        # 如果保存失败，后续加载可能会失败，这里可以选择退出或让它继续尝试加载
    
    # --- 测试加载功能 ---
    logger.info(f"开始测试 load_workbook_data 函数，文件: {test_file_path}")
    main_points, tp_data_list, error_msg = load_workbook_data(test_file_path)

    if error_msg:
        logger.error(f"load_workbook_data 执行时返回错误: {error_msg}")
    else:
        logger.info("load_workbook_data 执行完毕。")
        if main_points:
            logger.info(f"成功从 \'{MAIN_IO_SHEET_NAME}\' 读取了 {len(main_points)} 个主IO点:")
            for i, point in enumerate(main_points):
                logger.debug(f"  主点 {i+1}: HMI='{point.hmi_variable_name}', PLC='{point.plc_absolute_address}', Type='{point.data_type}'")
        else:
            logger.warning(f"未能从 \'{MAIN_IO_SHEET_NAME}\' 读取到任何主IO点数据。")

        if tp_data_list:
            logger.info(f"成功加载了 {len(tp_data_list)} 个第三方工作表:")
            for sheet_name, df in tp_data_list:
                logger.info(f"  第三方表: '{sheet_name}', 行数: {len(df)}, 列: {list(df.columns)}")
                if not df.empty:
                    logger.debug(f"    前几行数据:\n{df.head().to_string()}")
        else:
            logger.info("没有加载任何第三方工作表数据。") 