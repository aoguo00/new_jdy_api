import logging
from typing import List, Dict, Any, Optional
# import openpyxl #  我们将依赖调用者确保openpyxl可用或处理其缺失
# from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
# from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# 尝试导入 openpyxl 及其组件，以便在类定义中引用类型提示
try:
    import openpyxl
    from openpyxl.worksheet.worksheet import Worksheet
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
except ImportError:
    # 如果导入失败，定义一个占位符，以便类型提示不会引发错误
    # 实际的错误处理将在 IOExcelExporter 的 export_to_excel 方法中进行
    Worksheet = Any 
    Font = Any
    get_column_letter = Any
    openpyxl = None


class BaseSheetExporter:
    """
    工作表导出器的基类，提供通用的列宽自适应方法。
    """

    def _get_string_visual_length(self, text_str: str, is_bold: bool = False) -> float:
        """计算字符串的视觉长度，考虑CJK字符和字体加粗。"""
        visual_len = 0.0
        if not text_str: # 处理空字符串或None的情况
            return visual_len

        for char in str(text_str): #确保是字符串
            # CJK Unified Ideographs, Hangul Compatibility Jamo, Hangul Syllables, CJK Comp. Ideographs, CJK Comp. Forms, CJK Symbols and Punctuation, Fullwidth forms
            if (('\u4e00' <= char <= '\u9fff') or      # 基本CJK表意文字 (常用汉字)
                ('\u3130' <= char <= '\u318f') or      # 韩文兼容字母
                ('\uac00' <= char <= '\ud7af') or      # 韩文音节
                ('\uf900' <= char <= '\ufaff') or      # CJK兼容表意文字
                ('\u2f00' <= char <= '\u2fdf') or      # 康熙部首
                ('\u3000' <= char <= '\u303f') or      # CJK 符号和标点 (包括全角空格)
                ('\uff01' <= char <= '\uff5e')):     # 全角ASCII、半角片假名和全角片假名块中的全角符号
                visual_len += 2.0
            else:
                visual_len += 1.0
        
        if is_bold:
            visual_len *= 1.15  # 为粗体文本增加约15%的宽度，可以调整
        return visual_len

    def _adjust_column_widths(self, ws: Worksheet, headers: List[str]):
        """
        根据表头和内容自适应调整列宽，特别考虑CJK字符和全角符号，以及表头加粗。
        """
        if not openpyxl: # 确保 openpyxl 已加载
            return

        for col_idx, header_text_val in enumerate(headers): # col_idx is 0-based
            column_letter = get_column_letter(col_idx + 1)
            max_visual_len = 0.0

            # --- 计算表头的视觉长度 (表头是加粗的) ---
            header_visual_len = self._get_string_visual_length(str(header_text_val), is_bold=True)
            if header_visual_len > max_visual_len:
                max_visual_len = header_visual_len

            # --- 遍历列中的数据单元格 (从第二行开始)，计算内容的最大视觉长度 ---
            # 假设数据单元格默认非加粗
            for row_idx in range(2, ws.max_row + 1): # 遍历所有有效行，从第2行开始
                cell = ws.cell(row=row_idx, column=col_idx + 1) # col_idx 是0-based, cell列是1-based
                if cell.value is not None:
                    # cell_is_bold = cell.font and cell.font.b # 实际检查单元格是否加粗 (如果需要)
                    cell_visual_len = self._get_string_visual_length(str(cell.value), is_bold=False) # 假设数据非粗体
                    if cell_visual_len > max_visual_len:
                        max_visual_len = cell_visual_len
            
            # --- 设置列宽 ---
            padding = 6 # 字符宽度的填充
            adjusted_width = max_visual_len + padding
            
            if max_visual_len == 0: # 如果列完全为空（或只有空字符串的表头且无数据）
                adjusted_width = 10 # 为空列设置一个默认的最小宽度
            
            # 应用最小宽度限制
            min_width = 8       # 保证列不会太窄
            adjusted_width = max(min_width, adjusted_width)
            # 最大宽度限制已被移除

            ws.column_dimensions[column_letter].width = adjusted_width


class PLCSheetExporter(BaseSheetExporter):
    """
    负责生成 "IO点表" (PLC IO数据) 的Sheet页。
    """
    def __init__(self):
        self.headers_plc = [
            "序号", "模块名称", "模块类型", "供电类型（有源/无源）", "线制", "通道位号",
            "场站名", "变量名称（HMI）", "变量描述", "数据类型", "读写属性",
            "保存历史", "掉电保护", "量程低限", "量程高限", "SLL设定值", "SLL设定点位",
            "SLL设定点位_PLC地址", "SLL设定点位_通讯地址", "SL设定值", "SL设定点位",
            "SL设定点位_PLC地址", "SL设定点位_通讯地址", "SH设定值", "SH设定点位",
            "SH设定点位_PLC地址", "SH设定点位_通讯地址", "SHH设定值", "SHH设定点位",
            "SHH设定点位_PLC地址", "SHH设定点位_通讯地址", "LL报警", "LL报警_PLC地址",
            "LL报警_通讯地址", "L报警", "L报警_PLC地址", "L报警_通讯地址", "H报警",
            "H报警_PLC地址", "H报警_通讯地址", "HH报警", "HH报警_PLC地址", "HH报警_通讯地址",
            "维护值设定", "维护值设定点位", "维护值设定点位_PLC地址", "维护值设定点位_通讯地址",
            "维护使能开关点位", "维护使能开关点位_PLC地址", "维护使能开关点位_通讯地址",
            "PLC绝对地址", "上位机通讯地址"
        ] # 52列

    def populate_sheet(self, ws: Worksheet, plc_io_data: List[Dict[str, Any]], site_name: Optional[str]):
        """
        填充PLC IO数据到指定的工作表。
        """
        if not openpyxl: return

        ws.append(self.headers_plc)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for idx, point_data in enumerate(plc_io_data, 1):
            channel_io_type = point_data.get('type', '')
            data_type_value = ""
            if channel_io_type in ["AI", "AO"]:
                data_type_value = "REAL"
            elif channel_io_type in ["DI", "DO"]:
                data_type_value = "BOOL"

            row_data = [
                idx, 
                point_data.get('model', ''), 
                channel_io_type, 
                "", 
                "", 
                point_data.get('address', ''),
                site_name if site_name else "",
                "", 
                point_data.get('description', ''),
                data_type_value,
                "R/W", 
                "是", 
                "是", 
                "", "", "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "", "", "",
                "", "", "", "", "", "", "", "", "", "", "", "",
                "", "", ""
            ]
            ws.append(row_data)
        
        self._adjust_column_widths(ws, self.headers_plc)


class ThirdPartySheetExporter(BaseSheetExporter):
    """
    负责生成第三方设备点表的Sheet页。
    """
    def __init__(self):
        self.headers_tp = [
            "场站名", "变量名称", "变量描述", "数据类型", 
            "SH设定值", "SHH设定值", "PLC地址", "MODBUS地址"
        ]

    def populate_sheet(self, ws: Worksheet, points_in_template: List[Dict[str, Any]], site_name: Optional[str]):
        """
        填充第三方设备数据到指定的工作表。
        """
        if not openpyxl: return

        ws.append(self.headers_tp)
        for cell in ws[1]:
            cell.font = Font(bold=True)

        for tp_point in points_in_template:
            row_data_tp = [
                site_name if site_name else "",
                tp_point.get('point_name', ''),
                tp_point.get('description', ''),
                tp_point.get('data_type', ''),
                "", 
                "", 
                "", 
                ""  
            ]
            ws.append(row_data_tp)
        
        self._adjust_column_widths(ws, self.headers_tp)


class IOExcelExporter:
    """
    负责将IO点数据导出到Excel文件。
    使用 PLCSheetExporter 和 ThirdPartySheetExporter 来处理具体的Sheet页生成。
    """

    def __init__(self):
        self.plc_sheet_exporter = PLCSheetExporter()
        self.third_party_sheet_exporter = ThirdPartySheetExporter()

    def export_to_excel(self,
                        plc_io_data: Optional[List[Dict[str, Any]]],
                        third_party_data: Optional[List[Dict[str, Any]]] = None,
                        filename: str = "IO_Table.xlsx",
                        site_name: Optional[str] = None) -> bool:
        """
        将PLC IO数据和/或第三方设备数据导出到指定的Excel文件。
        """
        logger.info(f"IOExcelExporter.export_to_excel called. filename='{filename}', site_name='{site_name}'")
        logger.info(f"Received plc_io_data type: {type(plc_io_data)}, length: {len(plc_io_data) if plc_io_data is not None else 'None'}")
        logger.info(f"Received third_party_data type: {type(third_party_data)}, content: {third_party_data}")

        # 模块的导入移到这里，确保在尝试使用前检查
        global openpyxl, Worksheet, Font, get_column_letter # 声明为全局，以便修改上面定义的占位符
        if openpyxl is None: # 检查是否在文件顶部成功导入
            try:
                import openpyxl as opxl_main # 使用别名避免与全局变量冲突
                from openpyxl.worksheet.worksheet import Worksheet as OpxlWorksheet
                from openpyxl.styles import Font as OpxlFont
                from openpyxl.utils import get_column_letter as opxl_get_column_letter
                
                # 更新全局变量
                openpyxl = opxl_main
                Worksheet = OpxlWorksheet
                Font = OpxlFont
                get_column_letter = opxl_get_column_letter
                logger.info("openpyxl library loaded successfully.")
            except ImportError:
                logger.error("导出Excel失败：openpyxl 库未安装。请运行 'pip install openpyxl'")
                return False

        if not plc_io_data and not third_party_data:
            logger.warning("没有PLC IO数据或第三方设备数据可供导出。")
            return False

        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            default_sheet = wb["Sheet"]
            wb.remove(default_sheet)
            logger.info("Removed default 'Sheet'.")

        # --- 处理PLC IO数据 ---
        if plc_io_data:
            logger.info("Processing PLC IO data...")
            ws_plc = wb.create_sheet(title="IO点表")
            self.plc_sheet_exporter.populate_sheet(ws_plc, plc_io_data, site_name)
            logger.info("'IO点表' sheet populated.")

        # --- 处理第三方设备数据 ---
        if third_party_data:
            logger.info("Processing third-party data...")
            grouped_tp_data = {}
            for point in third_party_data:
                template_name = point.get('template_name', 'Default_Template') # 提供默认模板名
                if template_name not in grouped_tp_data:
                    grouped_tp_data[template_name] = []
                grouped_tp_data[template_name].append(point)

            for template_name, points_in_template in grouped_tp_data.items():
                safe_sheet_name = template_name.replace('[', '').replace(']', '').replace('*', '').replace('?', '').replace(':', '').replace('/', '').replace('\\\\', '')
                safe_sheet_name = safe_sheet_name[:31] # Excel sheet name length limit
                logger.info(f"尝试为模板 '{template_name}' 创建Sheet，安全名称为: '{safe_sheet_name}'")
                
                ws_tp = wb.create_sheet(title=safe_sheet_name)
                self.third_party_sheet_exporter.populate_sheet(ws_tp, points_in_template, site_name)
                logger.info(f"Sheet '{safe_sheet_name}' for template '{template_name}' populated. Current sheets: {wb.sheetnames}")
        
        if not wb.sheetnames:
            logger.error("没有创建任何Sheet页。可能 plc_io_data 和 third_party_data 都为空或处理失败。")
            # openpyxl 在没有可见sheet时保存会出错，确保至少有一个sheet页或明确不保存
            # 但前面的 if not plc_io_data and not third_party_data: 应该已经捕获了这种情况
            # 如果流程到这里还没有sheet，说明逻辑有误，但还是尝试创建一个空sheet避免保存错误
            # 不过更好的做法是如果真的没数据就不尝试保存
            if not plc_io_data and not third_party_data: # 双重检查
                 return False # 明确不保存
            # 如果有数据但sheet创建失败，这是个更深的问题
            # 为防止 'At least one sheet must be visible' 错误，如果到这里还没有sheet，且有数据要写，这是个错误
            # 但我们期望 populate_sheet 总是创建sheet
            # 这里的检查是最后的防线
            logger.warning("Workbook has no sheets, but data was provided. This indicates an issue in sheet creation.")
            #  不应该在这里创建默认sheet，因为这会掩盖问题，如果之前的逻辑正确，这里总会有sheet
            #  如果真的没有sheet，保存会失败，这是期望的行为，以暴露错误。

        try:
            wb.save(filename)
            logger.info(f"数据已成功导出到 {filename}")
            return True
        except Exception as e:
            # 特别处理 openpyxl 因没有可见工作表而引发的错误
            if "At least one sheet must be visible" in str(e):
                logger.error(f"导出Excel文件时出错: {e}. 这通常意味着没有成功创建任何工作表，或者所有工作表都被隐藏了。")
            else:
                logger.error(f"导出Excel文件时出错: {e}")
            return False
