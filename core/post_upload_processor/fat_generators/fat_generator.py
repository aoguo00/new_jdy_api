"""FAT点表生成器模块"""

import os
import logging
from typing import Tuple, Optional
import openpyxl # 导入 openpyxl
from openpyxl.utils import get_column_letter # 用于将列号转为字母（如果需要调试）

logger = logging.getLogger(__name__)

# 定义用户指定的列名
COL_HMI_VARIABLE_NAME = "变量名称（HMI）"
COL_VARIABLE_DESCRIPTION = "变量描述"
COL_CHANNEL_TAG = "通道位号"

def generate_fat_checklist_from_source(original_file_path: str, output_dir: str, output_filename: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    通过读取原始上传的IO点表文件，处理预留点位后，生成FAT点检表。
    此方法使用 openpyxl 以尽量保留原始格式和公式。
    如果"变量名称（HMI）"和"变量描述"为空，则根据"通道位号"自动填充它们。

    Args:
        original_file_path (str): 原始已验证IO点表Excel文件的路径 (应为 .xlsx)。
        output_dir (str): FAT点检表应保存的目录。
        output_filename (str): 生成的FAT点检表的输出文件名 (应为 .xlsx)。

    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (成功状态, 生成文件的路径, 错误消息)
    """
    if not original_file_path or not os.path.exists(original_file_path):
        error_msg = f"原始IO点表文件路径 '{original_file_path}' 无效或文件不存在。"
        logger.error(f"FAT生成失败 (原始文件问题): {error_msg}")
        return False, None, error_msg
    
    if not original_file_path.endswith('.xlsx'):
        error_msg = f"仅支持 .xlsx 格式的Excel文件以保留格式和公式。文件: {original_file_path}"
        logger.error(error_msg)
        return False, None, error_msg

    if not output_dir:
        error_msg = "未提供FAT点检表的输出目录。"
        logger.error(f"FAT生成失败 (输出目录问题): {error_msg}")
        return False, None, error_msg
        
    if not output_filename:
        error_msg = "未提供FAT点检表的输出文件名。"
        logger.error(f"FAT生成失败 (输出文件名问题): {error_msg}")
        return False, None, error_msg

    destination_path = os.path.join(output_dir, output_filename)

    try:
        # 加载工作簿
        workbook = openpyxl.load_workbook(original_file_path)
        
        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            logger.info(f"正在处理工作表: {sheet_name} 进行FAT点表预留点位处理 (使用openpyxl)")

            # 寻找标题行并映射列名到列索引 (1-based)
            header_row = None
            col_map = {}
            # 通常标题在第一行，但为了稳健可以搜索几行
            for r_idx, row in enumerate(sheet.iter_rows(min_row=1, max_row=min(5, sheet.max_row), values_only=False)):
                temp_map = {}
                possible_header = False
                for c_idx, cell in enumerate(row):
                    if cell.value:
                        if cell.value == COL_HMI_VARIABLE_NAME: temp_map[COL_HMI_VARIABLE_NAME] = c_idx + 1; possible_header=True
                        if cell.value == COL_VARIABLE_DESCRIPTION: temp_map[COL_VARIABLE_DESCRIPTION] = c_idx + 1; possible_header=True
                        if cell.value == COL_CHANNEL_TAG: temp_map[COL_CHANNEL_TAG] = c_idx + 1; possible_header=True
                if COL_HMI_VARIABLE_NAME in temp_map and COL_VARIABLE_DESCRIPTION in temp_map and COL_CHANNEL_TAG in temp_map:
                    col_map = temp_map
                    header_row = r_idx + 1
                    logger.info(f"在工作表 '{sheet_name}' 的第 {header_row} 行找到标题行。列映射: {col_map}")
                    break
            
            if not header_row or not col_map:
                logger.warning(f"工作表 '{sheet_name}' 未能找到包含所有必需列的标题行: {COL_HMI_VARIABLE_NAME}, {COL_VARIABLE_DESCRIPTION}, {COL_CHANNEL_TAG}. 该工作表将不被处理预留点位。")
                continue

            modified_count = 0
            # 从标题行之后开始遍历数据行
            for row_idx in range(header_row + 1, sheet.max_row + 1):
                hmi_cell = sheet.cell(row=row_idx, column=col_map[COL_HMI_VARIABLE_NAME])
                desc_cell = sheet.cell(row=row_idx, column=col_map[COL_VARIABLE_DESCRIPTION])
                channel_cell = sheet.cell(row=row_idx, column=col_map[COL_CHANNEL_TAG])

                hmi_val = hmi_cell.value
                desc_val = desc_cell.value
                channel_val = channel_cell.value

                is_hmi_empty = hmi_val is None or (isinstance(hmi_val, str) and not hmi_val.strip())
                is_desc_empty = desc_val is None or (isinstance(desc_val, str) and not desc_val.strip())
                is_channel_valid = channel_val is not None and str(channel_val).strip() != ""

                if is_hmi_empty and is_desc_empty and is_channel_valid:
                    channel_tag_str = str(channel_val).strip()
                    hmi_cell.value = f"YLDW{channel_tag_str}"
                    desc_cell.value = f"{channel_tag_str}预留点位"
                    modified_count += 1
            
            if modified_count > 0:
                logger.info(f"在工作表 '{sheet_name}' 中处理了 {modified_count} 个预留点位。")
            else:
                logger.info(f"在工作表 '{sheet_name}' 中未找到或未处理预留点位。")

        # 保存修改后的工作簿
        workbook.save(destination_path)
        
        logger.info(f"带预留点位处理的FAT点检表 (保留格式) 已成功生成于: {destination_path}")
        return True, destination_path, None

    except FileNotFoundError:
        error_msg = f"原始文件 '{original_file_path}' 未找到。"
        logger.error(error_msg)
        return False, None, error_msg
    except ImportError:
        error_msg = "处理Excel文件需要 openpyxl 库。请确保它已安装 (pip install openpyxl)。"
        logger.error(error_msg)
        return False, None, error_msg
    except Exception as e:
        error_msg = f"使用openpyxl处理Excel文件并生成FAT点检表时发生错误: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return False, None, error_msg 