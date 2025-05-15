import pandas as pd
import xlwt
import logging
from typing import Optional, List, Tuple, Any, Dict
# 修改导入路径为绝对导入
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint

logger = logging.getLogger(__name__)

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
    负责根据已处理的 UploadedIOPoint 数据列表生成和利时PLC点表 (.xls格式) - 非安全型版本。
    """

    def __init__(self):
        pass

    def _write_data_to_sheet(self, 
                             sheet: xlwt.Worksheet, 
                             points_for_sheet: List[UploadedIOPoint], 
                             sheet_title: str) -> int:
        """
        将指定点位列表的数据写入到给定的xlwt工作表中 (非安全型格式)。
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
        # 根据用户之前的输出，第一行是 Sheet名(COMMON)
        # 第二行才是真正的表头
        sheet.write(0, 0, f"{sheet_title}(COMMON)", font_style) # 保持这个标题行
        
        # 非安全型表头 (根据之前的代码和标准和利时格式推断)
        headers = ["变量名", "直接地址", "变量说明", "变量类型", "初始值", "掉电保护", "可强制", "SOE使能"]
        for col_idx, header_title in enumerate(headers):
            sheet.write(1, col_idx, header_title, font_style) # 表头在第二行
        
        excel_write_row_counter = 1 # 数据从 Excel 的第三行开始，但计数器基于已写入的表头行

        if not points_for_sheet:
            logger.info(f"工作表 '{sheet_title}' 的IO点数据列表为空。将只包含表头。")
        else:
            for point_idx, point in enumerate(points_for_sheet):
                # 优先使用 HMI 变量名，如果为空则尝试PLC地址，如果都为空则跳过
                hmi_name = point.hmi_variable_name or ""
                plc_address = point.plc_absolute_address or ""
                description = point.variable_description or ""
                data_type = (point.data_type or "").upper()
                source_sheet_from_point = point.source_sheet_name or "N/A"
                source_type = point.source_type or "N/A"

                if _is_value_empty(plc_address):
                    if _is_value_empty(hmi_name):
                        logger.debug(f"工作表 '{sheet_title}', 点位索引 {point_idx}: 跳过点位: HMI名和PLC地址均为空。来源: {source_sheet_from_point}/{source_type}")
                        continue # 都为空则跳过
                    # 如果PLC地址为空但HMI名存在，则继续，但PLC地址列将为空
                    logger.warning(f"工作表 '{sheet_title}', 点位 '{hmi_name}' (来源: {source_sheet_from_point}/{source_type}) PLC地址为空。")
                
                if _is_value_empty(hmi_name):
                    # 如果HMI名为空但PLC地址存在，用PLC地址作为HMI名
                    logger.warning(f"工作表 '{sheet_title}', 点位PLC地址 '{plc_address}' (来源: {source_sheet_from_point}/{source_type}) HMI名为空。将用PLC地址作名称。")
                    hmi_name = plc_address
                
                # 初始值逻辑 (非安全型)
                initial_value_to_write: Any
                if data_type == "REAL": initial_value_to_write = "0" # 非安全型REAL初始值为字符串"0"
                elif data_type == "BOOL": initial_value_to_write = "FALSE" # 非安全型BOOL为字符串"FALSE"
                else:
                    logger.warning(f"工作表 '{sheet_title}', 点位 '{hmi_name}' (地址: {plc_address}, 来源: {source_sheet_from_point}/{source_type}) 数据类型 '{data_type}' 未知或为空，初始值设为字符串'0'。")
                    initial_value_to_write = "0"

                # 掉电保护 (非安全型)
                power_off_protection_to_write = "TRUE" if data_type == "REAL" else "FALSE"
                # 可强制 (非安全型)
                can_force_to_write = "TRUE"
                # SOE使能 (非安全型)
                soe_enable_to_write = "TRUE" if data_type == "BOOL" else "FALSE"
                
                excel_write_row_counter += 1 # 数据行号
                current_excel_row = excel_write_row_counter # Excel行号 (从2开始，即第三行)
                
                sheet.write(current_excel_row, 0, hmi_name, font_style)
                sheet.write(current_excel_row, 1, plc_address, font_style)
                sheet.write(current_excel_row, 2, description, font_style)
                sheet.write(current_excel_row, 3, data_type if data_type else "", font_style)
                sheet.write(current_excel_row, 4, initial_value_to_write, font_style)
                sheet.write(current_excel_row, 5, power_off_protection_to_write, font_style)
                sheet.write(current_excel_row, 6, can_force_to_write, font_style)
                sheet.write(current_excel_row, 7, soe_enable_to_write, font_style)
        
        # 设置列宽 (非安全型)
        sheet.col(0).width = 256 * 35 # 变量名
        sheet.col(1).width = 256 * 20 # 直接地址
        sheet.col(2).width = 256 * 45 # 变量说明
        sheet.col(3).width = 256 * 15 # 变量类型
        sheet.col(4).width = 256 * 10 # 初始值
        sheet.col(5).width = 256 * 12 # 掉电保护
        sheet.col(6).width = 256 * 10 # 可强制
        sheet.col(7).width = 256 * 12 # SOE使能
        
        return excel_write_row_counter - 1 # 返回实际写入的数据行数（不含表头）

    def generate_hollysys_table(self, 
                                points_by_sheet: Dict[str, List[UploadedIOPoint]], 
                                output_path: str
                               ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时PLC点表 (非安全型版本)。
        会为传入字典中的每个原始工作表名创建一个对应的目标工作表，并写入其点位数据。
        这个版本只生成一张符合非安全型格式的表，其内容基于 `_write_data_to_sheet`。
        """
        logger.info(f"--- HollysysGenerator (非安全型): generate_hollysys_table 方法开始 ---")
        logger.info(f"传入参数: output_path='{output_path}'")
        logger.info(f"接收到 {len(points_by_sheet)} 个工作表的数据进行处理。")

        if not points_by_sheet:
            logger.warning("传入的点位数据字典为空，无法生成任何工作表。")
            return False, "没有提供任何工作表数据来生成点表。"

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            total_points_written = 0
            sheets_created_count = 0

            for sheet_name_raw, points_list_for_this_sheet in points_by_sheet.items():
                # 对工作表名进行清理，确保符合xlwt的要求
                safe_sheet_name = "".join(c for c in sheet_name_raw if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_sheet_name = safe_sheet_name[:31] 
                if not safe_sheet_name: 
                    original_keys = list(points_by_sheet.keys())
                    try:
                        idx = original_keys.index(sheet_name_raw) + 1
                        safe_sheet_name = f"Sheet_{idx}"
                    except ValueError:
                        safe_sheet_name = f"AutoGenSheet_{sheets_created_count + 1}"
                
                logger.info(f"尝试为原始工作表 '{sheet_name_raw}' 添加目标工作表，名称为: '{safe_sheet_name}'")
                
                try:
                    sheet = workbook.add_sheet(safe_sheet_name)
                    logger.info(f"成功添加工作表: '{sheet.name}' (源: '{sheet_name_raw}') 到工作簿。")
                    sheets_created_count += 1
                except Exception as e_add_sheet:
                    logger.error(f"为源工作表 '{sheet_name_raw}' 添加目标工作表 '{safe_sheet_name}' 失败: {e_add_sheet}. 跳过此工作表。")
                    continue 

                # 即使点位列表为空，也调用写入，_write_data_to_sheet 会处理这种情况（只写表头）
                rows_written_for_sheet = self._write_data_to_sheet(sheet, points_list_for_this_sheet, sheet_name_raw) 
                total_points_written += rows_written_for_sheet
                logger.info(f"工作表 '{safe_sheet_name}' (源: '{sheet_name_raw}') 处理完毕。写入了 {rows_written_for_sheet} 行数据。")
            
            if sheets_created_count > 0:
                logger.info(f"准备保存工作簿到 '{output_path}'。总共创建 {sheets_created_count} 个工作表，写入了 {total_points_written} 个点位。")
                workbook.save(output_path)
                logger.info(f"和利时PLC点表 (非安全型) 已成功生成并保存到: {output_path}")
                logger.info(f"--- HollysysGenerator (非安全型): generate_hollysys_table 方法结束 ---")
                return True, None
            else:
                logger.warning("没有成功创建任何工作表，因此不保存文件。")
                logger.info(f"--- HollysysGenerator (非安全型): generate_hollysys_table 方法结束 (无输出) ---")
                return False, "未能成功创建任何工作表（可能是由于工作表名称问题或所有源表都无法添加）。"
            
        except Exception as e:
            error_msg = f"生成和利时PLC点表 (非安全型) 时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            logger.info(f"--- HollysysGenerator (非安全型): generate_hollysys_table 方法因错误而结束 ---")
            return False, error_msg

    # --- MODBUS 点表生成方法 (从 SafetyHollysysGenerator 复制而来) ---
    def _prepare_modbus_data(self, all_points: List[UploadedIOPoint]) -> Dict[str, List[Dict[str, Any]]]:
        """
        准备Modbus点表所需的数据结构。
        根据规则筛选点位并计算偏移地址。
        BOOL类型 -> 线圈
        REAL类型 -> 保持寄存器
        (此方法与安全型生成器中的版本逻辑一致)
        """
        modbus_data: Dict[str, List[Dict[str, Any]]] = {
            "线圈": [],
            "输入离散量": [], # 备用，当前逻辑不使用
            "输入寄存器": [], # 备用，当前逻辑不使用
            "保持寄存器": []
        }

        for point in all_points:
            # 优先使用 HMI 通讯地址 (通常来自 Excel 的 "通讯地址" 列)
            comm_addr = point.hmi_communication_address
            if not comm_addr or not str(comm_addr).strip():
                logger.debug(f"Modbus (Non-Safety): 点 '{point.hmi_variable_name}' 无通讯地址，跳过。")
                continue

            comm_addr_str = str(comm_addr).strip()
            offset_str = ""

            # 提取偏移地址的逻辑 (假设地址格式如 00001, 00002, 40001, 40002)
            # 和利时Modbus地址约定：
            # 线圈 (Coils): 0xxxx (00001 - 09999)
            # 离散输入 (Discrete Inputs): 1xxxx (10001 - 19999)
            # 输入寄存器 (Input Registers): 3xxxx (30001 - 39999)
            # 保持寄存器 (Holding Registers): 4xxxx (40001 - 49999)
            # 偏移是相对于该区的起始地址 (例如，40001的偏移是1，40002的偏移是2)

            if len(comm_addr_str) > 1: # 地址至少应有区域码和一位数字
                try:
                    # 假设用户在Excel中填写的通讯地址已经是PLC的绝对地址，例如 "00001", "40001"
                    # 我们需要的是 "区内偏移"，即去掉第一位区域码后的数字部分
                    # 但要注意，和利时软件中填写的通常是偏移量 (从1开始)
                    # 如果用户填的是 "00001"，偏移是1. 如果是 "1"，也应理解为偏移1.
                    # 为简化，我们假设用户填写的已经是"偏移量"或能直接转换为偏移量
                    # 例如，如果用户填的是 "00005"，我们取 "5" 作为偏移
                    # 如果用户填的是 "5"，我们也取 "5"
                    # 因此，我们直接尝试将整个地址字符串（去掉可能的非数字前缀后）转换为数字
                    
                    # 一个更稳健的做法是只取最后几位作为偏移，但这依赖于地址格式的一致性
                    # 当前简单处理：尝试将整个字符串转为整数，如果失败，则认为格式错误
                    # 更好的做法是根据地址的首位判断区域，然后提取后面的数字作为偏移
                    # 例如：如果地址是 "00001"，则区内偏移是 "1"。如果是 "40010"，偏移是 "10"。

                    numeric_part_str = ""
                    for char_idx in range(len(comm_addr_str) -1, -1, -1): # 从后往前找数字
                        if comm_addr_str[char_idx].isdigit():
                            numeric_part_str = comm_addr_str[char_idx] + numeric_part_str
                        elif numeric_part_str: # 如果已经找到数字，再遇到非数字就停止
                            break 
                        # 如果前面是非数字且还没找到数字，继续往前
                    
                    if numeric_part_str:
                        offset_val = int(numeric_part_str)
                        offset_str = str(offset_val) # 区内偏移
                    else: # 如果整个地址都找不到数字部分
                        logger.warning(f"Modbus (Non-Safety): 点 '{point.hmi_variable_name}' 的通讯地址 '{comm_addr_str}' 无法提取有效的数字偏移部分，跳过。")
                        continue

                except ValueError:
                    logger.warning(f"Modbus (Non-Safety): 点 '{point.hmi_variable_name}' 的通讯地址 '{comm_addr_str}' 格式无效 (数字偏移部分解析失败)，跳过。")
                    continue
            else:
                logger.warning(f"Modbus (Non-Safety): 点 '{point.hmi_variable_name}' 的通讯地址 '{comm_addr_str}' 过短或格式不符合预期，无法提取偏移，跳过。")
                continue
            
            # 准备写入行的数据
            row_data = {
                "变量组名": point.source_sheet_name or "", # 使用原始Excel工作表名作为变量组名
                "变量名": point.hmi_variable_name or "",
                "区内偏移": offset_str # 这里是计算得到的偏移
                # "数据类型" 和 "读写标志" 将在写入Excel时根据目标工作表固定
            }

            # 根据数据类型分配到不同的Modbus区域
            if point.data_type == "BOOL":
                # 如果是BOOL，放入"线圈" (Coils)
                modbus_data["线圈"].append(row_data)
            elif point.data_type == "REAL":
                # 如果是REAL，放入"保持寄存器" (Holding Registers)
                modbus_data["保持寄存器"].append(row_data)
            # 其他数据类型当前不处理，可以根据需求扩展
            else:
                logger.debug(f"Modbus (Non-Safety): 点 '{point.hmi_variable_name}' 数据类型为 '{point.data_type}'，当前Modbus逻辑未处理此类型，跳过。")
        
        return modbus_data

    def generate_modbus_excel(self, 
                              points_by_sheet_dict: Dict[str, List[UploadedIOPoint]], 
                              output_path: str
                             ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时PLC的Modbus点表 (.xls格式)。
        包含 "线圈" 和 "保持寄存器" 两个工作表。
        (此方法与安全型生成器中的版本逻辑一致)

        Args:
            points_by_sheet_dict (Dict[str, List[UploadedIOPoint]]): 
                一个字典，键是原始工作表名，值是该工作表对应的 UploadedIOPoint 列表。
                注意：这里我们会合并所有工作表的点位进行处理。
            output_path (str): 用户选择的 .xls 文件保存路径。

        Returns:
            Tuple[bool, Optional[str]]: (操作是否成功, 错误消息或None)
        """
        logger.info(f"--- HollysysGenerator (Non-Safety): generate_modbus_excel 方法开始 ---")
        logger.info(f"传入参数: output_path='{output_path}'")
        logger.info(f"接收到 {len(points_by_sheet_dict)} 个源工作表的数据进行Modbus点表生成。")

        if not points_by_sheet_dict:
            logger.warning("Modbus (Non-Safety): 传入的点位数据字典为空，无法生成Modbus点表。")
            return False, "没有提供任何工作表数据来生成Modbus点表。"

        # 合并所有工作表的点位到一个列表中
        all_points_flat: List[UploadedIOPoint] = []
        for sheet_name, points_list in points_by_sheet_dict.items():
            all_points_flat.extend(points_list)
        
        if not all_points_flat:
            logger.warning("Modbus (Non-Safety): 合并后所有点位列表为空，无法生成Modbus点表。")
            return False, "合并所有工作表后没有可处理的点位数据。"
        
        logger.info(f"Modbus (Non-Safety): 总共 {len(all_points_flat)} 个点位将用于Modbus数据准备。")

        prepared_modbus_data = self._prepare_modbus_data(all_points_flat)

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            font_style = xlwt.XFStyle()
            font = xlwt.Font()
            font.name = '宋体'
            font.height = 20 * 11 # 11号字
            font_style.font = font
            alignment = xlwt.Alignment()
            alignment.horz = xlwt.Alignment.HORZ_LEFT
            alignment.vert = xlwt.Alignment.VERT_CENTER
            font_style.alignment = alignment

            # Modbus 表头定义
            modbus_headers = ["变量组名", "变量名", "数据类型", "区内偏移", "读写标志"]
            
            # 需要创建的工作表和它们的固定数据类型及读写标志
            # 格式: { "目标工作表名": {"DataType": "类型", "Access": "标志", "PointsKey": "prepared_modbus_data中的键"} }
            sheets_to_create_map = {
                "线圈":          {"DataType": "BIT",    "Access": "R/W", "PointsKey": "线圈"},
                "输入离散量":    {"DataType": "BIT",    "Access": "R",   "PointsKey": "输入离散量"}, # 假设全只读
                "输入寄存器":   {"DataType": "WORD",   "Access": "R",   "PointsKey": "输入寄存器"}, # 假设全只读
                "保持寄存器":   {"DataType": "WORD",   "Access": "R/W", "PointsKey": "保持寄存器"}
            }
            
            sheets_created_count = 0

            for sheet_name, config in sheets_to_create_map.items():
                points_for_this_modbus_sheet = prepared_modbus_data.get(config["PointsKey"], [])
                
                if not points_for_this_modbus_sheet:
                    logger.info(f"Modbus (Non-Safety): 工作表 '{sheet_name}' (对应数据键 '{config['PointsKey']}') 没有点位数据，将跳过创建此工作表。")
                    continue # 如果没有这个类型的数据，就不创建该工作表

                logger.info(f"Modbus (Non-Safety): 准备为 '{sheet_name}' 工作表写入 {len(points_for_this_modbus_sheet)} 个点位。")
                sheet = workbook.add_sheet(sheet_name)
                sheets_created_count += 1

                # 写入表头
                for col_idx, header_title in enumerate(modbus_headers):
                    sheet.write(0, col_idx, header_title, font_style)

                # 写入数据行
                for row_idx, point_data_dict in enumerate(points_for_this_modbus_sheet):
                    excel_row = row_idx + 1 # 数据从Excel的第二行开始 (索引1)
                    sheet.write(excel_row, 0, point_data_dict.get("变量组名", ""), font_style)
                    sheet.write(excel_row, 1, point_data_dict.get("变量名", ""), font_style)
                    sheet.write(excel_row, 2, config["DataType"], font_style) # 固定数据类型
                    sheet.write(excel_row, 3, point_data_dict.get("区内偏移", ""), font_style)
                    sheet.write(excel_row, 4, config["Access"], font_style) # 固定读写标志
                
                # 设置列宽 (可以根据实际内容调整)
                sheet.col(0).width = 256 * 30 # 变量组名
                sheet.col(1).width = 256 * 40 # 变量名
                sheet.col(2).width = 256 * 15 # 数据类型
                sheet.col(3).width = 256 * 15 # 区内偏移
                sheet.col(4).width = 256 * 15 # 读写标志
                logger.info(f"Modbus (Non-Safety): 工作表 '{sheet_name}' 数据写入完成。")

            if sheets_created_count > 0:
                logger.info(f"Modbus (Non-Safety): 准备保存Modbus工作簿到 '{output_path}'。总共创建 {sheets_created_count} 个工作表。")
                workbook.save(output_path)
                logger.info(f"Modbus (Non-Safety): 和利时PLC Modbus点表已成功生成并保存到: {output_path}")
                logger.info(f"--- HollysysGenerator (Non-Safety): generate_modbus_excel 方法结束 ---")
                return True, None
            else:
                logger.warning("Modbus (Non-Safety): 没有成功创建任何Modbus工作表 (因为所有相关点位列表都为空)，因此不保存文件。")
                logger.info(f"--- HollysysGenerator (Non-Safety): generate_modbus_excel 方法结束 (无输出) ---")
                return False, "未能成功创建任何Modbus工作表 (所有点位列表为空)。"

        except Exception as e:
            error_msg = f"生成和利时PLC Modbus点表 (非安全型) 时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            logger.info(f"--- HollysysGenerator (Non-Safety): generate_modbus_excel 方法因错误而结束 ---")
            return False, error_msg
