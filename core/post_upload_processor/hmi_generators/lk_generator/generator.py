"""力控点表生成器模块"""
import xlwt
import logging
import os
from typing import Tuple, Optional, List, Dict, Any

# 从 Shared Models 导入 UploadedIOPoint
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint
# 导入用于获取主IO表名的常量 (如果 excel_reader 定义了这样一个可导出的常量)
# from core.post_upload_processor.uploaded_file_processor.excel_reader import MAIN_IO_SHEET_NAME # 假设存在

logger = logging.getLogger(__name__)

# MAIN_IO_SHEET_NAME_DEFAULT 用于在无法从外部导入时提供一个默认值
MAIN_IO_SHEET_NAME_DEFAULT = "IO点表"

# LK_TP_COLS 不再需要，因为所有数据都来自 UploadedIOPoint 对象

# LK_INTERMEDIATE_POINTS_CONFIG_AI 也不再需要，因为中间点由 excel_reader 生成
# 并通过 point.source_type == 'intermediate_from_main' 来识别。

def _is_value_empty_for_hmi(value: Optional[str]) -> bool:
    """辅助函数：检查值是否被视为空（用于HMI名称）。"""
    return not (value and value.strip())

class LikongGenerator:
    """力控点表生成器"""

    def __init__(self):
        """初始化力控生成器"""
        self.font = xlwt.Font()
        self.font.name = 'Arial'
        self.font.height = 20 * 10
        self.style = xlwt.XFStyle()
        self.style.font = self.font
        self._sheet_row_counters: Dict[str, int] = {}

    def _reset_row_counters(self):
        """重置每个sheet的行计数器"""
        self._sheet_row_counters = {}

    def _get_next_row_idx(self, sheet_name: str) -> int:
        """获取指定sheet的下一个可用行索引 (0-based)，数据从第2行开始"""
        if sheet_name not in self._sheet_row_counters:
            self._sheet_row_counters[sheet_name] = 2 # 表头在0, 描述在1, 数据从2开始
        row_idx = self._sheet_row_counters[sheet_name]
        self._sheet_row_counters[sheet_name] += 1
        return row_idx

    def generate_basic_xls(self,
                           output_dir: str,
                           points_by_sheet: Dict[str, List[UploadedIOPoint]] # 修改：接收新的数据结构
                           ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控点表的第一个文件: Basic.xls
        该文件包含预定义的Sheet结构、表头，并根据输入数据填充点位信息。
        """
        self._reset_row_counters() # 每次生成新文件时重置行计数器
        # 决定主IO工作表的名称，优先使用导入的常量，否则使用默认值
        # main_io_sheet_key = MAIN_IO_SHEET_NAME if 'MAIN_IO_SHEET_NAME' in globals() else MAIN_IO_SHEET_NAME_DEFAULT
        # 为了简单起见，如果excel_reader.py中的MAIN_IO_SHEET_NAME固定为"IO点表",可以直接使用它
        main_io_sheet_key = MAIN_IO_SHEET_NAME_DEFAULT # 使用 "IO点表" 作为主表键名

        file_name = "Basic.xls" # 力控要求的文件名通常是固定的
        file_path = os.path.join(output_dir, file_name)

        default_site_name = ""
        default_site_number = ""

        # 尝试从主IO点列表中提取默认的场站名和场站编号
        main_io_points_list = points_by_sheet.get(main_io_sheet_key)
        if main_io_points_list and len(main_io_points_list) > 0:
            first_valid_main_point_for_site_info = next((
                p for p in main_io_points_list 
                if (p.site_name and p.site_name.strip()) or (p.site_number and p.site_number.strip())
            ), None)

            if first_valid_main_point_for_site_info:
                if first_valid_main_point_for_site_info.site_name and first_valid_main_point_for_site_info.site_name.strip():
                    default_site_name = first_valid_main_point_for_site_info.site_name.strip()
                if first_valid_main_point_for_site_info.site_number and first_valid_main_point_for_site_info.site_number.strip():
                    default_site_number = first_valid_main_point_for_site_info.site_number.strip()
        
        if not default_site_name and not default_site_number:
            logger.warning(f"力控 Basic.xls: 未能在主IO表 '{main_io_sheet_key}' 中找到有效的全局默认场站名或场站编号。")
        else:
            logger.info(f"力控 Basic.xls: 使用全局默认场站名='{default_site_name}', 场站编号='{default_site_number}' (如果点位自身无特定信息)")

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            # 创建固定的 "Sheet1" 和 "Basic" sheet (结构不变)
            sheet1 = workbook.add_sheet("Sheet1") 
            basic_sheet = workbook.add_sheet("Basic")
            basic_sheet.write(0, 0, "Ver", self.style)
            basic_sheet.write(1, 0, 10, self.style) # 版本号通常是10
            basic_sheet.col(0).width = 256 * 10

            # 力控 Basic.xls 中数据点所在的Sheet名称及其对应的数据类型
            # (通常模拟量和数字量就够了，其他如累计量、控制量等如果需要，再添加映射)
            lk_data_sheet_map = {
                "模拟I_O量": "REAL", # 映射到 UploadedIOPoint.data_type == "REAL"
                "数字I_O量": "BOOL"  # 映射到 UploadedIOPoint.data_type == "BOOL"
            }
            # 所有需要在 Basic.xls 中创建结构的Sheet名称列表
            all_lk_sheets_to_create = [
                "模拟I_O量", "数字I_O量", "累计量", 
                "控制量", "运算量", "组合量", "字符类型点"
            ]
            # 表头定义
            column_keys = ['NodePath', 'NAME'] # 列的内部标识符 (非实际Excel表头)
            header_row_content = ["点所在的节点路径", "点名"] # Excel 中实际的表头文字

            # 创建所有结构表并写入表头
            for sheet_name_to_create in all_lk_sheets_to_create:
                sheet = workbook.add_sheet(sheet_name_to_create)
                sheet.write(0, 0, column_keys[0], self.style) # 第1行第1列 (0-indexed)
                sheet.write(0, 1, column_keys[1], self.style) # 第1行第2列
                sheet.write(1, 0, header_row_content[0], self.style) # 第2行第1列
                sheet.write(1, 1, header_row_content[1], self.style) # 第2行第2列
                sheet.col(0).width = 256 * 35 # NodePath 列宽
                sheet.col(1).width = 256 * 50 # NAME 列宽

            # --- 开始处理所有点位 ---
            total_points_processed_for_lk = 0
            if not points_by_sheet:
                logger.info("力控 Basic.xls: 传入的 points_by_sheet 为空，不处理任何点位。")
            else:
                for sheet_name_from_source, points_list in points_by_sheet.items():
                    if not points_list:
                        logger.debug(f"力控 Basic.xls: 源工作表 '{sheet_name_from_source}' 的点位列表为空，跳过。")
                        continue
                    
                    logger.info(f"力控 Basic.xls: 开始处理源工作表 '{sheet_name_from_source}' 的 {len(points_list)} 个点位...")
                    
                    for point_idx, point in enumerate(points_list):
                        point_data_type_upper = str(point.data_type or "").upper().strip()
                        hmi_name_from_point = str(point.hmi_variable_name or "").strip()

                        # 确定此点应写入力控的哪个Sheet
                        target_lk_sheet_name: Optional[str] = None
                        for lk_sheet, mapped_type in lk_data_sheet_map.items():
                            if point_data_type_upper == mapped_type:
                                target_lk_sheet_name = lk_sheet
                                break
                        
                        if not target_lk_sheet_name:
                            # logger.debug(f"点 {point_idx+1} (HMI:'{hmi_name_from_point}', 源:'{sheet_name_from_source}', 类型:'{point_data_type_upper}') 的数据类型不映射到力控目标Sheet，跳过。")
                            continue # 如果点的数据类型不是REAL或BOOL，则不写入这两个主要的数据Sheet

                        if _is_value_empty_for_hmi(hmi_name_from_point):
                            logger.warning(f"点 {point_idx+1} (源:'{sheet_name_from_source}', 类型:'{point_data_type_upper}', 通道:'{point.channel_tag}') HMI名称为空或无效，跳过写入力控表。")
                            continue

                        # 确定场站信息 (优先点位自身，其次全局默认)
                        current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
                        current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()

                        # 构建 NodePath: "场站名\" (确保是单个反斜杠在路径中)
                        # xlwt 会处理转义，所以直接用 "场站名\" 即可
                        node_path_value = f"{current_point_site_name}\\" if current_point_site_name else ""
                        
                        # 构建 NAME: "场站编号" + "HMI名"
                        # HMI名已经由 excel_reader 处理过 (包括预留点YLDW前缀、中间点后缀等)
                        # 如果点位是和利时相关的预留点，并且 excel_reader 已移除了场站编号前缀，
                        # 那么这里的 current_point_site_number 可能是空的（如果该点也没有自己的场站号）
                        # 或者 hmi_name_from_point 已经是 YLDWxxx (不含场站号)。
                        # 力控的点名规则是：场站编号 + HMI变量名（HMI变量名可能已经是YLDWxxx）
                        # 如果 current_point_site_number 为空，则NAME就是 hmi_name_from_point
                        
                        name_value = f"{current_point_site_number}{hmi_name_from_point}"

                        # 获取目标Sheet对象并写入
                        try:
                            lk_sheet_obj = workbook.get_sheet(target_lk_sheet_name) # get_sheet by name
                            if lk_sheet_obj:
                                row_to_write = self._get_next_row_idx(target_lk_sheet_name)
                                lk_sheet_obj.write(row_to_write, 0, node_path_value, self.style)
                                lk_sheet_obj.write(row_to_write, 1, name_value, self.style)
                                total_points_processed_for_lk +=1
                            else: # Should not happen if sheet names are correct
                                logger.error(f"未能获取到名为 '{target_lk_sheet_name}' 的Sheet对象。")
                        except Exception as e_sheet_write:
                             logger.error(f"写入点到Sheet '{target_lk_sheet_name}' 时出错 (HMI: {hmi_name_from_point}): {e_sheet_write}")
                    
                    logger.info(f"力控 Basic.xls: 源工作表 '{sheet_name_from_source}' 处理完成。")
            
            if total_points_processed_for_lk > 0:
                logger.info(f"力控 Basic.xls: 总共成功处理并写入 {total_points_processed_for_lk} 个点位到各数据类型Sheet。")
            else:
                logger.info("力控 Basic.xls: 未处理或写入任何有效点位。")

            workbook.save(file_path)
            logger.info(f"成功生成力控基础文件 (Basic.xls): {file_path}")
            return True, file_path, None

        except Exception as e:
            error_msg = f"生成 Basic.xls 文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
        finally:
            self._reset_row_counters() # 确保重置，即使发生错误


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    generator = LikongGenerator()
    test_output_dir = os.path.join(os.getcwd(), "test_likong_output_new_model")
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    # --- 构建测试数据 ---
    # 场景1: 包含主IO点 (常规点、预留点、AI派生点) 和第三方点
    points_data_s1: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [ # 主IO表
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_01", data_type="REAL", source_type="main_io", module_type="AI", channel_tag="CH_AI01", variable_description="模拟量输入1"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_01_HiLimit", data_type="REAL", source_type="intermediate_from_main", module_type="AI", channel_tag="CH_AI01", variable_description="模拟量输入1_SH设定"), # 假设这是excel_reader派生的
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_01_H", data_type="BOOL", source_type="intermediate_from_main", module_type="AI", channel_tag="CH_AI01", variable_description="模拟量输入1_H报警"), # 假设这是excel_reader派生的
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="DI_Status_01", data_type="BOOL", source_type="main_io", module_type="DI", channel_tag="CH_DI01", variable_description="数字量状态1"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="YLDW_CH_AI02", data_type="REAL", source_type="main_io", module_type="AI", channel_tag="CH_AI02", variable_description="预留模拟量2"), # 预留点 (假设excel_reader生成了这个名字)
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="YLDW_CH_DI02", data_type="BOOL", source_type="main_io", module_type="DI", channel_tag="CH_DI02", variable_description="预留数字量2"),
            UploadedIOPoint(data_type="FLOAT", hmi_variable_name="NoSiteInfoPoint", source_type="main_io") # 无场站信息的点
        ],
        "第三方设备A": [
            UploadedIOPoint(site_name="TP_设备A", site_number="TPA01", hmi_variable_name="TP_REAL_1", data_type="REAL", source_type="third_party", variable_description="第三方实数点1"),
            UploadedIOPoint(site_name="TP_设备A", site_number="TPA01", hmi_variable_name="TP_BOOL_1", data_type="BOOL", source_type="third_party", variable_description="第三方布尔点1"),
            UploadedIOPoint(hmi_variable_name="TP_NoSite_REAL", data_type="REAL", source_type="third_party") # 第三方无场站信息
        ],
        "空Sheet": [],
        "只有无效类型的Sheet": [
            UploadedIOPoint(hmi_variable_name="BadTypePoint", data_type="STRING", source_type="main_io")
        ]
    }

    logger.info("--- 测试场景1: 完整数据 ---")
    success1, file_path1, err_msg1 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s1
    )
    if success1: print(f"场景1成功: {file_path1}")
    else: print(f"场景1失败: {err_msg1}")

    # --- 场景2: 只有主IO点 ---
    points_data_s2: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": points_data_s1["IO点表"]
    }
    logger.info("--- 测试场景2: 只有主IO点 ---")
    success2, file_path2, err_msg2 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s2
    )
    if success2: print(f"场景2成功: {file_path2}")
    else: print(f"场景2失败: {err_msg2}")

    # --- 场景3: 只有第三方点 (无主IO表，全局场站信息应为空) ---
    points_data_s3: Dict[str, List[UploadedIOPoint]] = {
        "第三方设备A": points_data_s1["第三方设备A"]
    }
    logger.info("--- 测试场景3: 只有第三方点 ---")
    success3, file_path3, err_msg3 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s3
    )
    if success3: print(f"场景3成功: {file_path3}")
    else: print(f"场景3失败: {err_msg3}")
    
    # --- 场景4: 输入数据为空字典 ---
    points_data_s4: Dict[str, List[UploadedIOPoint]] = {}
    logger.info("--- 测试场景4: 输入数据为空字典 ---")
    success4, file_path4, err_msg4 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s4
    )
    if success4: print(f"场景4成功: {file_path4}")
    else: print(f"场景4失败: {err_msg4}")

    # --- 场景5: 主IO表存在但为空列表，有第三方数据 ---
    points_data_s5: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [],
        "第三方设备A": points_data_s1["第三方设备A"]
    }
    logger.info("--- 测试场景5: 主IO表为空列表，有第三方 ---")
    success5, file_path5, err_msg5 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s5
    )
    if success5: print(f"场景5成功: {file_path5}")
    else: print(f"场景5失败: {err_msg5}")
    
    # --- 场景6: 点位数据类型不匹配 (REAL/BOOL之外) ---
    points_data_s6: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="INT_Value_01", data_type="INT", source_type="main_io"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="STR_Value_01", data_type="STRING", source_type="main_io")
        ]
    }
    logger.info("--- 测试场景6: 数据类型不匹配 ---")
    success6, file_path6, err_msg6 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s6
    )
    if success6: print(f"场景6成功 (预期不写入点): {file_path6}") # 应该生成空文件但操作成功
    else: print(f"场景6失败: {err_msg6}")

    # --- 场景7: HMI名称为空的点 ---
    points_data_s7: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name=None, data_type="REAL", source_type="main_io"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="  ", data_type="BOOL", source_type="main_io")
        ]
    }
    logger.info("--- 测试场景7: HMI名称为空 ---")
    success7, file_path7, err_msg7 = generator.generate_basic_xls(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s7
    )
    if success7: print(f"场景7成功 (预期不写入点): {file_path7}")
    else: print(f"场景7失败: {err_msg7}") 