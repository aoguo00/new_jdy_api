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
    from openpyxl.styles import Font, Alignment
    from openpyxl.utils import get_column_letter
except ImportError:
    # 如果导入失败，定义一个占位符，以便类型提示不会引发错误
    # 实际的错误处理将在 IOExcelExporter 的 export_to_excel 方法中进行
    Worksheet = Any 
    Font = Any
    Alignment = Any
    get_column_letter = Any
    openpyxl = None


class BaseSheetExporter:
    """
    工作表导出器的基类，提供通用的列宽自适应方法。
    """
    # 预定义的列宽配置
    COLUMN_WIDTH_CONFIG = {
        # PLC IO表的列宽配置
        "序号": 5,
        "模块名称": 10,
        "模块类型": 10,
        "供电类型（有源/无源）": 25,
        "线制": 8,
        "通道位号": 15,
        "场站名": 20,
        "变量名称（HMI）": 25,
        "变量描述": 35,
        "数据类型": 12,
        "读写属性": 10,
        "保存历史": 10,
        "掉电保护": 10,
        "量程低限": 12,
        "量程高限": 12,
        "SLL设定值": 12,
        "SLL设定点位": 15,
        "SLL设定点位_PLC地址": 25,
        "SLL设定点位_通讯地址": 25,
        "SL设定值": 12,
        "SL设定点位": 15,
        "SL设定点位_PLC地址": 25,
        "SL设定点位_通讯地址": 25,
        "SH设定值": 12,
        "SH设定点位": 15,
        "SH设定点位_PLC地址": 25,
        "SH设定点位_通讯地址": 25,
        "SHH设定值": 12,
        "SHH设定点位": 15,
        "SHH设定点位_PLC地址": 25,
        "SHH设定点位_通讯地址": 25,
        "LL报警": 10,
        "LL报警_PLC地址": 20,
        "LL报警_通讯地址": 20,
        "L报警": 10,
        "L报警_PLC地址": 20,
        "L报警_通讯地址": 20,
        "H报警": 10,
        "H报警_PLC地址": 20,
        "H报警_通讯地址": 20,
        "HH报警": 10,
        "HH报警_PLC地址": 20,
        "HH报警_通讯地址": 20,
        "维护值设定": 12,
        "维护值设定点位": 20,
        "维护值设定点位_PLC地址": 25,
        "维护值设定点位_通讯地址": 25,
        "维护使能开关点位": 20,
        "维护使能开关点位_PLC地址": 25,
        "维护使能开关点位_通讯地址": 26,
        "PLC绝对地址": 20,
        "上位机通讯地址": 20,
        
        # 第三方设备表的列宽配置
        "MODBUS地址": 15,
    }

    def _adjust_column_widths(self, ws: Worksheet, headers: List[str]):
        """
        根据预定义的配置设置列宽。
        """
        if not openpyxl:
            return

        for col_idx, header in enumerate(headers):
            column_letter = get_column_letter(col_idx + 1)
            # 使用预定义的列宽，如果没有预定义则使用默认值
            width = self.COLUMN_WIDTH_CONFIG.get(header, 15)  # 默认宽度为15
            ws.column_dimensions[column_letter].width = width


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

        left_alignment = None
        if Alignment and Alignment is not Any: # Check if Alignment is properly imported
            left_alignment = Alignment(horizontal='left', vertical='center')

        ws.append(self.headers_plc)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            if left_alignment:
                cell.alignment = left_alignment

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
            if left_alignment:
                for cell in ws[ws.max_row]: # Apply to the newly added row
                    cell.alignment = left_alignment
        
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

        left_alignment = None
        if Alignment and Alignment is not Any: # Check if Alignment is properly imported
            left_alignment = Alignment(horizontal='left', vertical='center')

        ws.append(self.headers_tp)
        for cell in ws[1]:
            cell.font = Font(bold=True)
            if left_alignment:
                cell.alignment = left_alignment

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
            if left_alignment:
                for cell in ws[ws.max_row]: # Apply to the newly added row
                    cell.alignment = left_alignment
        
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
        global openpyxl, Worksheet, Font, get_column_letter, Alignment # 声明为全局，以便修改上面定义的占位符
        if openpyxl is None: # 检查是否在文件顶部成功导入
            try:
                import openpyxl as opxl_main # 使用别名避免与全局变量冲突
                from openpyxl.worksheet.worksheet import Worksheet as OpxlWorksheet
                from openpyxl.styles import Font as OpxlFont, Alignment as OpxlAlignment
                from openpyxl.utils import get_column_letter as opxl_get_column_letter
                
                # 更新全局变量
                openpyxl = opxl_main
                Worksheet = OpxlWorksheet
                Font = OpxlFont
                Alignment = OpxlAlignment
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
