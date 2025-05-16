import xlwt
import logging
from typing import Optional, List, Tuple, Any, Dict

# 导入数据模型和模块信息提供者
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint
from core.io_table.get_data import ModuleInfoProvider

logger = logging.getLogger(__name__)

def _is_value_empty_safety(value: Optional[str]) -> bool:
    """
    辅助函数：检查字符串值是否为空或仅包含空格 (安全型生成器专用)。
    """
    return not (value and value.strip())

class SafetyHollysysGenerator:
    """
    负责根据已处理的 UploadedIOPoint 数据列表生成和利时安全型PLC点表 (.xls格式)。
    """

    def __init__(self, module_info_provider: ModuleInfoProvider):
        """
        初始化安全型和利时点表生成器。

        Args:
            module_info_provider (ModuleInfoProvider): 用于查询模块信息的提供者。
                                                    虽然在此类的当前版本中可能不直接用于数据写入逻辑，
                                                    但保留它是为了将来的扩展或更复杂的安全相关逻辑。
        """
        self.module_info_provider = module_info_provider
        logger.info("SafetyHollysysGenerator initialized.")

    def _write_safety_variable_sheet_data(self, 
                                         sheet: xlwt.Worksheet, 
                                         points_for_sheet: List[UploadedIOPoint], 
                                         sheet_title: str) -> int:
        """
        将指定点位列表的数据写入到给定的xlwt工作表中 (安全型变量表格式)。
        返回写入的数据行数 (不含标题和表头)。
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
        
        # 第一行：工作表特定的大标题，例如 "GV_Group(COMMON)"
        sheet.write(0, 0, f"{sheet_title}(COMMON)", font_style)
        
        # 第二行：安全型变量表表头
        headers = ["变量名", "变量说明", "变量类型", "初始值", "区域"]
        for col_idx, header_title in enumerate(headers):
            sheet.write(1, col_idx, header_title, font_style)
        
        excel_write_row_counter = 1 # 数据从 Excel 的第三行开始计数，此计数器基于已写入的表头行

        if not points_for_sheet:
            logger.info(f"安全型工作表 '{sheet_title}' 的IO点数据列表为空。将只包含表头。")
        else:
            for point_idx, point in enumerate(points_for_sheet):
                # 优先使用 HMI 变量名
                hmi_name = point.hmi_variable_name or ""
                # 安全型变量表不直接使用PLC地址，但如果HMI名为空，可以考虑用描述或一个占位符
                # 根据用户之前的表头，没有PLC地址列。如果HMI名必须有，这里需要策略。
                # 假设：如果HMI名为空，则该点位不适用于此表，或者使用一个通用名称。
                # 当前：如果HMI名为空，则尝试使用变量描述，如果都为空，则跳过。
                variable_description = point.variable_description or ""

                if _is_value_empty_safety(hmi_name):
                    if _is_value_empty_safety(variable_description):
                        logger.debug(f"安全型工作表 '{sheet_title}', 点位索引 {point_idx}: 跳过点位: HMI名和变量描述均为空。")
                        continue
                    else: # 如果HMI名为空但描述存在，是否可以用描述作为变量名？或者需要一个策略
                        logger.warning(f"安全型工作表 '{sheet_title}', 点位索引 {point_idx}: HMI名为空，变量描述为 '{variable_description}'。当前跳过，后续可调整策略。")
                        # hmi_name = variable_description # 暂不使用描述作为变量名，除非明确指示
                        continue 

                data_type = (point.data_type or "").upper()
                
                # "初始值" 逻辑 (安全型)
                initial_value_to_write: str
                if data_type == "BOOL":
                    # 根据用户要求，BOOL类型初始值为字符串 "0" 或 "1"
                    # 假设 UploadedIOPoint 中没有直接的布尔初始值字段，通常IO点表不包含它
                    # 这里我们根据类型默认，实际可能需要从 point 的某个属性获取
                    initial_value_to_write = "0" # 默认为 "0" (FALSE)
                elif data_type == "REAL":
                    initial_value_to_write = "0" # 或 "0.0"
                else:
                    logger.warning(f"安全型工作表 '{sheet_title}', 点位 '{hmi_name}' 数据类型 '{data_type}' 未知或为空，初始值设为字符串'0'。")
                    initial_value_to_write = "0"

                # "区域" 逻辑 (安全型)
                area_to_write: str
                if data_type == "BOOL":
                    area_to_write = "G区"
                elif data_type == "REAL":
                    area_to_write = "R区"
                else:
                    area_to_write = "" # 其他类型区域为空或默认值
                    logger.info(f"安全型工作表 '{sheet_title}', 点位 '{hmi_name}' 数据类型 '{data_type}' 未知或为空，区域设为空。")

                excel_write_row_counter += 1 # 数据行号
                current_excel_row = excel_write_row_counter # Excel行号 (从2开始，即第三行)
                
                sheet.write(current_excel_row, 0, hmi_name, font_style)
                sheet.write(current_excel_row, 1, variable_description, font_style)
                sheet.write(current_excel_row, 2, data_type if data_type else "", font_style)
                sheet.write(current_excel_row, 3, initial_value_to_write, font_style)
                sheet.write(current_excel_row, 4, area_to_write, font_style)
        
        # 设置列宽 (安全型变量表)
        sheet.col(0).width = 256 * 40 # 变量名
        sheet.col(1).width = 256 * 50 # 变量说明
        sheet.col(2).width = 256 * 15 # 变量类型
        sheet.col(3).width = 256 * 10 # 初始值
        sheet.col(4).width = 256 * 10 # 区域
        
        return excel_write_row_counter - 1 # 返回实际写入的数据行数

    def generate_safety_hollysys_table(self, 
                                       points_by_sheet: Dict[str, List[UploadedIOPoint]], 
                                       output_path: str
                                      ) -> Tuple[bool, Optional[str]]:
        """
        生成安全型和利时PLC点表。
        当前版本主要关注生成符合安全型格式的变量表 (GV_Group, DI_Group等)。
        后续可以扩展以支持其他安全相关的表单。

        参数:
            points_by_sheet (Dict[str, List[UploadedIOPoint]]): 
                一个字典，键是原始工作表名 (例如 "GV_Group", "DI_Group"), 
                值是该工作表对应的 UploadedIOPoint 列表。
            output_path (str): 用户选择的 .xls 文件保存路径。

        返回:
            Tuple[bool, Optional[str]]: (操作是否成功, 错误消息或None)
        """
        logger.info(f"--- SafetyHollysysGenerator: generate_safety_hollysys_table 方法开始 ---")
        logger.info(f"传入参数: output_path='{output_path}'")
        logger.info(f"接收到 {len(points_by_sheet)} 个工作表的数据进行处理。")

        if not points_by_sheet:
            logger.warning("传入的点位数据字典为空 (安全型)，无法生成任何工作表。")
            return False, "没有提供任何工作表数据来生成安全型点表。"

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            total_points_written = 0
            sheets_created_count = 0

            # 遍历传入的每个工作表数据
            for original_sheet_name, points_list_for_this_sheet in points_by_sheet.items():
                # 工作表名清理和长度限制 (与非安全型生成器逻辑保持一致)
                safe_sheet_name = "".join(c for c in original_sheet_name if c.isalnum() or c in (' ', '_', '-')).strip()
                safe_sheet_name = safe_sheet_name[:31] 
                if not safe_sheet_name: 
                    original_keys_list = list(points_by_sheet.keys())
                    try:
                        idx = original_keys_list.index(original_sheet_name) + 1
                        safe_sheet_name = f"SafetySheet_{idx}"
                    except ValueError: # Should not happen
                        safe_sheet_name = f"AutoGenSafetySheet_{sheets_created_count + 1}"
                
                logger.info(f"尝试为原始安全型工作表 '{original_sheet_name}' 添加目标工作表，名称为: '{safe_sheet_name}'")
                
                try:
                    sheet = workbook.add_sheet(safe_sheet_name)
                    logger.info(f"成功添加安全型工作表: '{sheet.name}' (源: '{original_sheet_name}') 到工作簿。")
                    sheets_created_count += 1
                except Exception as e_add_sheet:
                    logger.error(f"为源安全型工作表 '{original_sheet_name}' 添加目标工作表 '{safe_sheet_name}' 失败: {e_add_sheet}. 跳过此工作表。")
                    continue 

                # 写入当前工作表的数据 (变量表格式)
                rows_written_for_sheet = self._write_safety_variable_sheet_data(
                    sheet, 
                    points_list_for_this_sheet, 
                    original_sheet_name # 传递原始工作表名给写入函数，用于生成 (COMMON) 标题
                )
                total_points_written += rows_written_for_sheet
                logger.info(f"安全型工作表 '{safe_sheet_name}' (源: '{original_sheet_name}') 处理完毕。写入了 {rows_written_for_sheet} 行数据。")
            
            if sheets_created_count > 0:
                logger.info(f"准备保存安全型工作簿到 '{output_path}'。总共创建 {sheets_created_count} 个工作表，写入了 {total_points_written} 个点位。")
                workbook.save(output_path)
                logger.info(f"安全型和利时PLC点表已成功生成并保存到: {output_path}")
                logger.info(f"--- SafetyHollysysGenerator: generate_safety_hollysys_table 方法结束 ---")
                return True, None
            else:
                logger.warning("没有成功创建任何安全型工作表，因此不保存文件。")
                logger.info(f"--- SafetyHollysysGenerator: generate_safety_hollysys_table 方法结束 (无输出) ---")
                return False, "未能成功创建任何安全型工作表。"
            
        except Exception as e:
            error_msg = f"生成安全型和利时PLC点表时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            logger.info(f"--- SafetyHollysysGenerator: generate_safety_hollysys_table 方法因错误而结束 ---")
            return False, error_msg

    # --- MODBUS 点表生成方法 (与 HollysysGenerator 中的逻辑相同) ---
    def _prepare_modbus_data(self, all_points: List[UploadedIOPoint]) -> Dict[str, List[Dict[str, Any]]]:
        """
        准备Modbus点表所需的数据结构。
        根据规则筛选点位并计算偏移地址。
        BOOL类型 -> 线圈
        REAL类型 -> 保持寄存器
        (此方法与非安全型生成器中的版本逻辑一致)
        """
        modbus_data: Dict[str, List[Dict[str, Any]]] = {
            "线圈": [],
            "输入离散量": [],
            "输入寄存器": [],
            "保持寄存器": []
        }

        for point in all_points:
            comm_addr = point.hmi_communication_address
            if not comm_addr or not str(comm_addr).strip():
                logger.debug(f"Modbus (Safety): 点 '{point.hmi_variable_name}' 无通讯地址，跳过。")
                continue

            comm_addr_str = str(comm_addr).strip()
            offset_str = ""

            if len(comm_addr_str) > 1:
                try:
                    offset_val = int(comm_addr_str[1:])
                    offset_str = str(offset_val)
                except ValueError:
                    logger.warning(f"Modbus (Safety): 点 '{point.hmi_variable_name}' 的通讯地址 '{comm_addr_str}' 格式无效 (偏移部分非数字)，跳过。")
                    continue
            else:
                logger.warning(f"Modbus (Safety): 点 '{point.hmi_variable_name}' 的通讯地址 '{comm_addr_str}' 过短或格式不符合预期，无法提取偏移，跳过。")
                continue
            
            row_data = {
                "变量组名": point.source_sheet_name or "", 
                "变量名": point.hmi_variable_name or "",
                "区内偏移": offset_str 
            }

            if point.data_type == "BOOL":
                modbus_data["线圈"].append(row_data)
            elif point.data_type == "REAL":
                modbus_data["保持寄存器"].append(row_data)
            else:
                logger.debug(f"Modbus (Safety): 点 '{point.hmi_variable_name}' 数据类型 '{point.data_type}' 非 BOOL 或 REAL，不生成Modbus条目。")
        
        return modbus_data

    def generate_modbus_excel(self, 
                              points_by_sheet_dict: Dict[str, List[UploadedIOPoint]], 
                              output_path: str
                             ) -> Tuple[bool, Optional[str]]:
        """
        生成和利时安全型Modbus点表 (.xls格式)。
        包含四个固定的工作表：线圈, 输入离散量, 输入寄存器, 保持寄存器。
        BOOL类型点位进入"线圈"，REAL类型点位进入"保持寄存器"。
        (此方法与非安全型生成器中的版本逻辑一致)
        """
        logger.info(f"--- SafetyHollysysGenerator: generate_modbus_excel 方法开始 ---")
        logger.info(f"安全型Modbus点表将保存到: {output_path}")

        all_points_flat_list: List[UploadedIOPoint] = []
        for points_list in points_by_sheet_dict.values():
            all_points_flat_list.extend(points_list)
        
        if not all_points_flat_list:
            logger.warning("Modbus (Safety): 传入的总点位列表为空，无法生成Modbus点表。")
            return False, "没有提供任何点位数据来生成安全型Modbus点表。"

        modbus_sheets_content = self._prepare_modbus_data(all_points_flat_list)

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            modbus_sheet_names = ["线圈", "输入离散量", "输入寄存器", "保持寄存器"]
            headers = ["变量组名", "变量名", "区内偏移"]

            font_style = xlwt.XFStyle()
            font = xlwt.Font(); font.name = '宋体'; font.height = 20 * 11
            font_style.font = font
            alignment = xlwt.Alignment(); alignment.horz = xlwt.Alignment.HORZ_LEFT; alignment.vert = xlwt.Alignment.VERT_CENTER
            font_style.alignment = alignment

            for sheet_name in modbus_sheet_names:
                sheet = workbook.add_sheet(sheet_name)
                
                for col_idx, header_title in enumerate(headers):
                    sheet.write(0, col_idx, header_title, font_style)

                current_data_for_sheet = modbus_sheets_content.get(sheet_name, [])
                if current_data_for_sheet:
                    for row_idx, row_data_dict in enumerate(current_data_for_sheet, start=1):
                        sheet.write(row_idx, 0, row_data_dict.get("变量组名", ""), font_style)
                        sheet.write(row_idx, 1, row_data_dict.get("变量名", ""), font_style)
                        sheet.write(row_idx, 2, row_data_dict.get("区内偏移", ""), font_style)
                else:
                    logger.info(f"Modbus (Safety) 工作表 '{sheet_name}' 没有数据点。")

                sheet.col(0).width = 256 * 30 # 变量组名
                sheet.col(1).width = 256 * 40 # 变量名
                sheet.col(2).width = 256 * 15 # 区内偏移

            # 新增：在末尾添加一个名为 "Sheet1" 的空工作表
            workbook.add_sheet("Sheet1")
            logger.info("已在Modbus安全型点表末尾添加一个空的 'Sheet1' 工作表。")

            workbook.save(output_path)
            logger.info(f"安全型和利时Modbus点表已成功生成并保存到: {output_path}")
            logger.info(f"--- SafetyHollysysGenerator: generate_modbus_excel 方法结束 ---")
            return True, None

        except Exception as e:
            error_msg = f"生成安全型和利时Modbus点表时发生未知错误: {e}"
            logger.error(error_msg, exc_info=True)
            logger.info(f"--- SafetyHollysysGenerator: generate_modbus_excel 方法因错误而结束 ---")
            return False, error_msg

if __name__ == '__main__':
    # 简易测试 (需要 ModuleInfoProvider 的模拟或实例)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')

    # 模拟 ModuleInfoProvider (如果需要被 __init__ 调用)
    class MockModuleInfoProvider:
        def get_module_info_by_model(self, model_name: str) -> Optional[Dict[str, Any]]:
            # 按需实现，当前 SafetyHollysysGenerator 未直接使用其返回值
            if "LK220S" in model_name:
                return {"model": model_name, "type": "CPU", "is_safety_module": True}
            return None

    mock_provider = MockModuleInfoProvider()
    safety_generator = SafetyHollysysGenerator(module_info_provider=mock_provider)

    sample_safety_points: Dict[str, List[UploadedIOPoint]] = {
        "GV_Group": [
            UploadedIOPoint(hmi_variable_name="TAG_GV_BOOL_01", variable_description="安全布尔变量1", data_type="BOOL", source_sheet_name="GV_Group"),
            UploadedIOPoint(hmi_variable_name="TAG_GV_REAL_01", variable_description="安全实数变量1", data_type="REAL", source_sheet_name="GV_Group"),
            UploadedIOPoint(hmi_variable_name="TAG_GV_INT_01", variable_description="安全整数变量1", data_type="INT", source_sheet_name="GV_Group"), # 测试其他类型
        ],
        "DI_Group_Safety": [
            UploadedIOPoint(hmi_variable_name="S_DI_EmergencyStop", variable_description="安全急停按钮", data_type="BOOL", source_sheet_name="DI_Group_Safety"),
            UploadedIOPoint(hmi_variable_name="", variable_description="无变量名安全点", data_type="BOOL", source_sheet_name="DI_Group_Safety"), # 应跳过
        ]
    }

    output_file_safety = "test_hollysys_safety_table_v1.xls"
    logger.info(f"\n--- 开始测试: 安全型和利时点表 ({output_file_safety}) ---")
    success, msg = safety_generator.generate_safety_hollysys_table(sample_safety_points, output_file_safety)
    
    if success:
        print(f"安全型测试文件 '{output_file_safety}' 生成成功。")
    else:
        print(f"安全型测试文件 '{output_file_safety}' 生成失败: {msg}")

    output_file_empty_safety = "test_hollysys_safety_empty_v1.xls"
    logger.info(f"\n--- 开始测试: 安全型空字典输入 ({output_file_empty_safety}) ---")
    success_empty, msg_empty = safety_generator.generate_safety_hollysys_table({}, output_file_empty_safety)
    if success_empty:
        print(f"安全型空字典测试文件 '{output_file_empty_safety}' 生成成功。")
    else:
        print(f"安全型空字典测试文件 '{output_file_empty_safety}' 生成失败或未生成: {msg_empty}") 