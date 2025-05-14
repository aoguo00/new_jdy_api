"""力控点表生成器模块"""
import xlwt
import logging
import os
from typing import Tuple, Optional, List, Dict, Any
import pandas as pd

# 从 Shared Models 导入 UploadedIOPoint
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint

logger = logging.getLogger(__name__)

# 定义力控生成器使用的第三方表列名常量
class LK_TP_COLS:
    VAR_NAME = "变量名称"    # 第三方表中的变量名列
    DATA_TYPE = "数据类型"  # 第三方表中的数据类型列
    # 根据需要，未来可以添加更多，例如如果第三方表有自己的场站/设备信息时
    # SITE_NAME = "设备名" # 示例
    # SITE_NUMBER = "设备编号" # 示例

# --- 和利时 PLC 生成器中的 AI 中间点配置 --- (直接复制并重命名)
# 这个配置是核心，力控将尝试复用其逻辑
LK_INTERMEDIATE_POINTS_CONFIG_AI = [
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
                           main_io_points: Optional[List[UploadedIOPoint]] = None,
                           third_party_data: Optional[List[Tuple[str, pd.DataFrame]]] = None
                           ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控点表的第一个文件: Basic.xls
        该文件包含预定义的Sheet结构、表头，并根据输入数据填充点位信息。
        """
        self._reset_row_counters() # 每次生成新文件时重置行计数器
        file_name = "Basic.xls"
        file_path = os.path.join(output_dir, file_name)

        # 尝试从主IO点列表中提取默认的场站名和场站编号
        default_site_name = ""
        default_site_number = ""
        if main_io_points and len(main_io_points) > 0:
            first_point_with_site_name = next((p for p in main_io_points if p.site_name and p.site_name.strip()), None)
            if first_point_with_site_name:
                default_site_name = first_point_with_site_name.site_name.strip()
            
            first_point_with_site_number = next((p for p in main_io_points if p.site_number and p.site_number.strip()), None)
            if first_point_with_site_number:
                default_site_number = first_point_with_site_number.site_number.strip()
        
        logger.debug(f"力控 Basic.xls: 默认场站名='{default_site_name}', 默认场站编号='{default_site_number}'")

        try:
            workbook = xlwt.Workbook(encoding='utf-8')
            sheet1 = workbook.add_sheet("Sheet1") # Empty sheet
            basic_sheet = workbook.add_sheet("Basic")
            basic_sheet.write(0, 0, "Ver", self.style)
            basic_sheet.write(1, 0, 10, self.style)
            basic_sheet.col(0).width = 256 * 10

            io_sheet_names_map = {
                "模拟I_O量": "REAL",
                "数字I_O量": "BOOL"
            }
            all_sheet_names_for_structure = [
                "模拟I_O量", "数字I_O量", "累计量", 
                "控制量", "运算量", "组合量", "字符类型点"
            ]
            column_keys = ['NodePath', 'NAME']
            header_row_content = ["点所在的节点路径", "点名"]

            for sheet_name_for_structure in all_sheet_names_for_structure:
                sheet = workbook.add_sheet(sheet_name_for_structure)
                sheet.write(0, 0, column_keys[0], self.style)
                sheet.write(0, 1, column_keys[1], self.style)
                sheet.write(1, 0, header_row_content[0], self.style)
                sheet.write(1, 1, header_row_content[1], self.style)
                sheet.col(0).width = 256 * 30 # 稍宽一点以适应场站名+
                sheet.col(1).width = 256 * 45 # Increased NAME width

            # 处理主IO点
            if main_io_points:
                logger.info(f"力控 Basic.xls: 处理 {len(main_io_points)} 个主IO点...")
                for point_idx, point in enumerate(main_io_points):
                    point_data_type_upper = str(point.data_type or "").upper().strip()
                    module_type_upper = str(getattr(point, 'module_type', None) or "").upper().strip()
                    
                    # --- 1. Process the main point itself --- 
                    main_point_target_sheet_name = None
                    for s_name, s_type in io_sheet_names_map.items():
                        if point_data_type_upper == s_type:
                            main_point_target_sheet_name = s_name
                            break
                    
                    effective_site_name_for_main = str(point.site_name or default_site_name or "").strip()
                    effective_site_number_for_main = str(point.site_number or default_site_number or "").strip()
                    node_path_for_point_and_derived = f"{effective_site_name_for_main}\\"

                    hmi_name_raw = point.hmi_variable_name
                    is_main_point_reserved_name = _is_value_empty_for_hmi(hmi_name_raw)
                    
                    base_name_part_for_main_point: str
                    if is_main_point_reserved_name:
                        channel_tag_str = str(point.channel_tag or "").strip()
                        placeholder_id = channel_tag_str if channel_tag_str else f"ResM{point_idx + 1}"
                        base_name_part_for_main_point = f"YLDW{placeholder_id}"
                    else:
                        base_name_part_for_main_point = str(hmi_name_raw).strip()
                    
                    # 力控的最终NAME是 场站编号 + (YLDW{通道} 或 HMI名)
                    final_name_for_main_point = f"{effective_site_number_for_main}{base_name_part_for_main_point}"

                    if main_point_target_sheet_name: # If main point type matches a sheet
                        current_sheet = workbook.get_sheet(main_point_target_sheet_name)
                        if current_sheet:
                            row_to_write = self._get_next_row_idx(main_point_target_sheet_name)
                            current_sheet.write(row_to_write, 0, node_path_for_point_and_derived, self.style)
                            current_sheet.write(row_to_write, 1, final_name_for_main_point, self.style)
                    
                    # --- 2. Process REAL intermediate setpoints if it's a REAL AI module type --- 
                    if module_type_upper == 'AI':
                        for ip_config in LK_INTERMEDIATE_POINTS_CONFIG_AI:
                            intermediate_addr_raw = getattr(point, ip_config['addr_attr'], None)
                            intermediate_addr = str(intermediate_addr_raw or "").strip()
                            
                            if not intermediate_addr:
                                continue

                            intermediate_point_type = ip_config['type'].upper()
                            intermediate_target_sheet_name = None
                            if intermediate_point_type in io_sheet_names_map.values():
                                for s_name, s_type in io_sheet_names_map.items():
                                    if intermediate_point_type == s_type:
                                        intermediate_target_sheet_name = s_name
                                        break
                            
                            if not intermediate_target_sheet_name:
                                logger.debug(f"AI主点 '{final_name_for_main_point}' 的中间点 '{ip_config['desc_suffix']}' (类型 {intermediate_point_type}) 无对应力控Sheet，跳过派生。")
                                continue

                            current_intermediate_sheet = workbook.get_sheet(intermediate_target_sheet_name)
                            if not current_intermediate_sheet: continue # Should not happen if sheet name is valid
                            
                            # 构建中间点的NAME (参考和利时逻辑)
                            # final_name_for_main_point 是主AI点的完整NAME (场站编号+基础部分)
                            # base_name_part_for_main_point 是主AI点的基础部分 (YLDW{通道} 或 HMI名)
                            intermediate_name_from_attr_raw = getattr(point, ip_config['name_attr'], None)
                            
                            final_intermediate_name_part: str
                            if is_main_point_reserved_name: # 如果主点是预留名 (YLDW...)
                                final_intermediate_name_part = f"{base_name_part_for_main_point}{ip_config['name_suffix_for_reserved']}"
                            else: # 主点有正常的HMI名
                                if _is_value_empty_for_hmi(intermediate_name_from_attr_raw):
                                    # 用户未在主点行为此中间点指定独立名称，则用 主点HMI名 + 后缀
                                    final_intermediate_name_part = f"{base_name_part_for_main_point}{ip_config['name_suffix_for_reserved']}"
                                else:
                                    # 用户为此中间点指定了独立名称，直接使用
                                    final_intermediate_name_part = str(intermediate_name_from_attr_raw).strip()
                            
                            # 力控的最终派生NAME是 场站编号 + 派生点名称部分
                            final_name_for_intermediate_point = f"{effective_site_number_for_main}{final_intermediate_name_part}"
                            
                            row_to_write = self._get_next_row_idx(intermediate_target_sheet_name)
                            current_intermediate_sheet.write(row_to_write, 0, node_path_for_point_and_derived, self.style)
                            current_intermediate_sheet.write(row_to_write, 1, final_name_for_intermediate_point, self.style)
                logger.info("力控生成器: 主IO点处理完毕。")

            # 处理第三方数据
            if third_party_data:
                logger.info(f"力控 Basic.xls: 处理 {len(third_party_data)} 个第三方数据表...")
                for tp_table_idx, (original_sheet_name, tp_df) in enumerate(third_party_data):
                    logger.info(f"力控生成器: 处理第三方表 '{original_sheet_name}' (索引 {tp_table_idx})...")
                    if tp_df.empty:
                        logger.debug(f"第三方表 '{original_sheet_name}' 为空，跳过。")
                        continue
                    for tp_row_idx, tp_row in tp_df.iterrows():
                        tp_point_data_type = str(tp_row.get(LK_TP_COLS.DATA_TYPE) or "").upper().strip()
                        target_sheet_name = None
                        for s_name, s_type in io_sheet_names_map.items():
                            if tp_point_data_type == s_type:
                                target_sheet_name = s_name
                                break
                        
                        if not target_sheet_name:
                            continue # 此第三方点的数据类型不映射到目标Sheet

                        tp_var_name = str(tp_row.get(LK_TP_COLS.VAR_NAME) or "").strip()
                        if not tp_var_name: # 如果第三方变量名为空，则跳过此点
                            logger.debug(f"第三方表 '{original_sheet_name}' 行 {tp_row_idx} 因变量名为空而被跳过。DataType: '{tp_point_data_type}'")
                            continue

                        current_sheet = workbook.get_sheet(target_sheet_name)
                        if not current_sheet: continue
                        
                        # 第三方点使用从主IO点提取的默认场站信息
                        node_path_val = f"{default_site_name}\\"
                        name_val = f"{default_site_number}{tp_var_name}"
                        
                        row_to_write = self._get_next_row_idx(target_sheet_name)
                        current_sheet.write(row_to_write, 0, node_path_val, self.style)
                        current_sheet.write(row_to_write, 1, name_val, self.style)
                logger.info("力控生成器: 第三方数据处理完毕。")

            workbook.save(file_path)
            logger.info(f"成功生成力控基础文件 (含数据点): {file_path}")
            return True, file_path, None

        except Exception as e:
            error_msg = f"生成 Basic.xls 文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
        finally:
            self._reset_row_counters() # 确保计数器被重置，无论成功与否

if __name__ == '__main__':
    # 用于测试的简单示例
    # 请确保在项目根目录下创建 test_output 文件夹
    
    # 获取当前脚本所在的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 构建到项目根目录的路径 (假设此脚本在 core/post_upload_processor/hmi_generators/lk_generator/ 下)
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", "..", "..", ".."))
    test_output_dir = os.path.join(project_root, "test_output_lk")

    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)
        print(f"创建测试输出目录: {test_output_dir}")

    generator = LikongGenerator()
    success, fp, err = generator.generate_basic_xls(output_dir=test_output_dir)

    if success:
        print(f"测试文件已生成: {fp}")
    else:
        print(f"测试失败: {err}") 