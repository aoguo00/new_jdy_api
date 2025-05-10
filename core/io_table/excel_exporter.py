import logging
from typing import List, Dict, Any, Optional

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


class PLCAddressAllocator:
    """负责PLC地址的分配和管理。"""
    def __init__(self, start_md_address=320, start_mx_byte=20, start_mx_bit=0):
        self.current_md_address = start_md_address
        self.current_mx_byte = start_mx_byte
        self.current_mx_bit = start_mx_bit
        logger.info(f"PLCAddressAllocator initialized: MD starts at {self.current_md_address}, MX starts at {self.current_mx_byte}.{self.current_mx_bit}")

    def allocate_real_address(self) -> str:
        """分配一个REAL类型的地址 (%MD)。"""
        address = f"%MD{self.current_md_address}"
        self.current_md_address += 4
        # logger.debug(f"Allocated REAL address: {address}")
        return address

    def allocate_bool_address(self) -> str:
        """分配一个BOOL类型的地址 (%MX)。"""
        address = f"%MX{self.current_mx_byte}.{self.current_mx_bit}"
        # logger.debug(f"Allocating BOOL address: {address} (before increment: byte={self.current_mx_byte}, bit={self.current_mx_bit})")
        self.current_mx_bit += 1
        if self.current_mx_bit > 7:
            self.current_mx_bit = 0
            self.current_mx_byte += 1
            # logger.debug(f"BOOL address bit overflowed. New byte: {self.current_mx_byte}, new bit: {self.current_mx_bit}")
        return address


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
        "场站编号": 20,
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
            "场站名", "场站编号", "变量名称（HMI）", "变量描述", "数据类型", "读写属性",
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
        ] # 53列

    def populate_sheet(self, ws: Worksheet, plc_io_data: List[Dict[str, Any]], site_name: Optional[str], site_no: Optional[str]):
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

        address_allocator = PLCAddressAllocator() # 初始化地址分配器

        for idx, point_data in enumerate(plc_io_data, 1):
            channel_io_type = point_data.get('type', '')
            data_type_value = ""
            if channel_io_type in ["AI", "AO"]:
                data_type_value = "REAL"
            elif channel_io_type in ["DI", "DO"]:
                data_type_value = "BOOL"

            # 初始化PLC地址列为空字符串
            sll_set_plc_addr, sl_set_plc_addr, sh_set_plc_addr, shh_set_plc_addr = "", "", "", ""
            ll_alarm_plc_addr, l_alarm_plc_addr, h_alarm_plc_addr, hh_alarm_plc_addr = "", "", "", ""
            maint_val_set_plc_addr, maint_enable_plc_addr, plc_absolute_addr = "", "", ""

            # 根据模块主数据类型分配PLC绝对地址
            if data_type_value == "REAL":
                plc_absolute_addr = address_allocator.allocate_real_address()
            elif data_type_value == "BOOL":
                plc_absolute_addr = address_allocator.allocate_bool_address()

            # 根据模块IO类型分配其他相关地址
            if channel_io_type == "AI":
                sll_set_plc_addr = address_allocator.allocate_real_address()
                sl_set_plc_addr = address_allocator.allocate_real_address()
                sh_set_plc_addr = address_allocator.allocate_real_address()
                shh_set_plc_addr = address_allocator.allocate_real_address()
                ll_alarm_plc_addr = address_allocator.allocate_bool_address()
                l_alarm_plc_addr = address_allocator.allocate_bool_address()
                h_alarm_plc_addr = address_allocator.allocate_bool_address()
                hh_alarm_plc_addr = address_allocator.allocate_bool_address()
                maint_val_set_plc_addr = address_allocator.allocate_real_address()
                maint_enable_plc_addr = address_allocator.allocate_bool_address()
            elif channel_io_type == "DI":
                # DI模块：不分配LL, L, H, HH报警的PLC地址，不分配维护值设定PLC地址，也不分配维护使能开关点位_PLC地址。
                # maint_enable_plc_addr = address_allocator.allocate_bool_address() # 移除
                pass # DI模块除了绝对地址外，不主动分配其他特定用途的PLC地址
            elif channel_io_type == "AO":
                maint_val_set_plc_addr = address_allocator.allocate_real_address()
                maint_enable_plc_addr = address_allocator.allocate_bool_address()
            elif channel_io_type == "DO":
                # DO模块：除了绝对地址外，不主动分配其他特定用途的PLC地址 (包括维护使能开关)
                # maint_enable_plc_addr = address_allocator.allocate_bool_address() # 移除
                pass

            # 获取表头中各PLC地址列的索引，以便正确填充
            # 注意：如果表头顺序改变，这里的硬编码索引需要更新，更健壮的方法是动态查找索引
            # 但为了简化，我们暂时假设表头顺序固定
            # headers_plc 列表：
            # ..., "SLL设定点位_PLC地址" (idx 18), ..., "SL设定点位_PLC地址" (idx 22), ... 
            # "SH设定点位_PLC地址" (idx 26), ..., "SHH设定点位_PLC地址" (idx 30), ...
            # "LL报警_PLC地址" (idx 33), ..., "L报警_PLC地址" (idx 36), ..., "H报警_PLC地址" (idx 39), ...
            # "HH报警_PLC地址" (idx 42), ..., "维护值设定点位_PLC地址" (idx 46), ...
            # "维护使能开关点位_PLC地址" (idx 49), "PLC绝对地址" (idx 51)

            current_row_values = [
                idx, 
                point_data.get('model', ''), 
                channel_io_type, 
                "",  # 供电类型
                "",  # 线制
                point_data.get('address', ''), # 通道位号
                site_name if site_name else "",
                site_no if site_no else "",
                "",  # 变量名称（HMI）
                point_data.get('description', ''),
                data_type_value, # 数据类型
                "R/W", # 读写属性
                "是",   # 保存历史
                "是",   # 掉电保护
                "", "", # 量程低限, 量程高限
                "", "", sll_set_plc_addr, "",  # SLL设定值, SLL设定点位, SLL设定点位_PLC地址, SLL设定点位_通讯地址
                "", "", sl_set_plc_addr, "",   # SL...
                "", "", sh_set_plc_addr, "",   # SH...
                "", "", shh_set_plc_addr, "", # SHH...
                "", ll_alarm_plc_addr, "",    # LL报警, LL报警_PLC地址, LL报警_通讯地址
                "", l_alarm_plc_addr, "",     # L报警...
                "", h_alarm_plc_addr, "",     # H报警...
                "", hh_alarm_plc_addr, "",    # HH报警...
                "", "", maint_val_set_plc_addr, "", # 维护值设定, 维护值设定点位, 维护值设定点位_PLC地址, 维护值设定点位_通讯地址
                "", maint_enable_plc_addr, "", # 维护使能开关点位, 维护使能开关点位_PLC地址, 维护使能开关点位_通讯地址
                plc_absolute_addr,        # PLC绝对地址
                ""                        # 上位机通讯地址
            ]
            # 确保 row_data 长度与 headers_plc 一致
            if len(current_row_values) != len(self.headers_plc):
                logger.error(f"Row data length ({len(current_row_values)}) does not match headers length ({len(self.headers_plc)}). Aborting row append for safety.")
                # 根据实际情况决定是跳过此行，还是填充空值以匹配长度，或者抛出异常
                # 为安全起见，这里可以先不添加此行或添加填充了空值的行
                # 例如，补齐空值：
                # current_row_values.extend(["" for _ in range(len(self.headers_plc) - len(current_row_values))])
            else:
                 # 重新组织 row_data 以匹配 headers_plc 的顺序
                 # 这部分逻辑需要非常小心，确保每个值都放在正确的列
                 # 假设 self.headers_plc 是最终的列顺序权威来源
                final_row_data = ["" for _ in range(len(self.headers_plc))]
                final_row_data[0] = idx
                final_row_data[1] = point_data.get('model', '')
                final_row_data[2] = channel_io_type
                # final_row_data[3] = "" # 供电类型（有源/无源）
                # final_row_data[4] = "" # 线制
                final_row_data[5] = point_data.get('address', '') # 通道位号
                final_row_data[6] = site_name if site_name else ""
                final_row_data[7] = site_no if site_no else ""
                # final_row_data[8] = "" # 变量名称（HMI）
                final_row_data[9] = point_data.get('description', '')
                final_row_data[10] = data_type_value # 数据类型
                final_row_data[11] = "R/W" # 读写属性
                final_row_data[12] = "是"   # 保存历史
                final_row_data[13] = "是"   # 掉电保护
                # 量程 (14, 15) - 空
                # SLL (16设定值, 17设定点位, 18 PLC地址, 19通讯地址)
                final_row_data[18] = sll_set_plc_addr
                # SL (20设定值, 21设定点位, 22 PLC地址, 23通讯地址)
                final_row_data[22] = sl_set_plc_addr
                # SH (24设定值, 25设定点位, 26 PLC地址, 27通讯地址)
                final_row_data[26] = sh_set_plc_addr
                # SHH (28设定值, 29设定点位, 30 PLC地址, 31通讯地址)
                final_row_data[30] = shh_set_plc_addr
                # LL报警 (32报警, 33 PLC地址, 34通讯地址)
                final_row_data[33] = ll_alarm_plc_addr
                # L报警 (35报警, 36 PLC地址, 37通讯地址)
                final_row_data[36] = l_alarm_plc_addr
                # H报警 (38报警, 39 PLC地址, 40通讯地址)
                final_row_data[39] = h_alarm_plc_addr
                # HH报警 (41报警, 42 PLC地址, 43通讯地址)
                final_row_data[42] = hh_alarm_plc_addr
                # 维护值设定 (44值, 45点位, 46 PLC地址, 47通讯地址)
                final_row_data[46] = maint_val_set_plc_addr
                # 维护使能开关 (48点位, 49 PLC地址, 50通讯地址)
                final_row_data[49] = maint_enable_plc_addr
                # PLC绝对地址 (51)
                final_row_data[51] = plc_absolute_addr
                # 上位机通讯地址 (52) - 空

                ws.append(final_row_data)

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
                        site_name: Optional[str] = None,
                        site_no: Optional[str] = None) -> bool:
        """
        将PLC IO数据和/或第三方设备数据导出到指定的Excel文件。
        """
        logger.info(f"IOExcelExporter.export_to_excel called. filename='{filename}', site_name='{site_name}', site_no='{site_no}'")
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
            self.plc_sheet_exporter.populate_sheet(ws_plc, plc_io_data, site_name, site_no)
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
