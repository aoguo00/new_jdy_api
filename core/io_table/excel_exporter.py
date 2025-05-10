import logging
from typing import List, Dict, Any, Optional
import re # 新增导入

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 尝试导入 openpyxl 及其组件，以便在类定义中引用类型提示
try:
    import openpyxl
    from openpyxl.worksheet.worksheet import Worksheet
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    # 如果导入失败，定义一个占位符，以便类型提示不会引发错误
    # 实际的错误处理将在 IOExcelExporter 的 export_to_excel 方法中进行
    Worksheet = Any 
    Font = Any
    Alignment = Any
    PatternFill = Any
    Border = Any
    Side = Any
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
    # Columns that always require user input
    ALWAYS_HIGHLIGHT_HEADERS = {
        "供电类型（有源/无源）",
        "线制",
        "变量名称（HMI）",
        "变量描述"
    }

    # Columns that require user input specifically for AI modules
    AI_SPECIFIC_HIGHLIGHT_HEADERS = {
        "量程低限",
        "量程高限",
        "SLL设定值",
        "SL设定值",
        "SH设定值",
        "SHH设定值"
    }

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

    def _get_modbus_address(self, plc_address: str) -> str:
        """
        根据PLC地址计算Modbus通讯地址。
        规则:
        - %MDx -> (x // 2) + 3000 + 1
        - %MXm.n -> (m * 8) + n + 3000 + 1
        如果PLC地址为空或无法识别，则返回空字符串。
        """
        if not plc_address:
            return ""

        md_match = re.fullmatch(r"%MD(\d+)", plc_address)
        if md_match:
            try:
                val = int(md_match.group(1))
                return str((val // 2) + 3000 + 40000 + 1)
            except ValueError:
                logger.warning(f"无法解析%MD地址中的数字: {plc_address}")
                return ""

        logger.debug(f"尝试匹配MX地址: {plc_address}") # 新增日志
        mx_match = re.fullmatch(r"%MX(\d+)\.(\d+)", plc_address) # 注意转义点号
        if mx_match:
            logger.debug(f"MX地址匹配成功: Groups={mx_match.groups()}") # 新增日志
            try:
                m_val = int(mx_match.group(1))
                n_val = int(mx_match.group(2))
                comm_addr = (m_val * 8) + n_val + 3000 + 1
                logger.debug(f"计算得到的MX通讯地址: {comm_addr} for {plc_address}") # 新增日志
                return str(comm_addr)
            except ValueError:
                logger.warning(f"无法解析%MX地址中的数字: {plc_address}, Groups={mx_match.groups()}")
                return ""
        else: # 新增else分支明确记录未匹配情况
            logger.debug(f"MX地址匹配失败: {plc_address}")
        
        # 这条日志现在应该只在两种类型都不匹配时执行
        logger.debug(f"未识别的PLC地址格式 (非MD也非MX)，无法转换为Modbus地址: {plc_address}") 
        return ""

    def populate_sheet(self, ws: Worksheet, plc_io_data: List[Dict[str, Any]], site_name: Optional[str], site_no: Optional[str]):
        """
        填充PLC IO数据到指定的工作表。
        """
        if not openpyxl: return

        left_alignment = None
        thin_border_style = None
        highlight_fill_color = "FFE4E1E1" # 默认为浅灰色，您可以更改此颜色代码
        user_input_fill = None

        if Alignment and Alignment is not Any:
            left_alignment = Alignment(horizontal='left', vertical='center')
        
        if Border and Side and Border is not Any and Side is not Any:
            thin_side = Side(border_style="thin", color="000000")
            thin_border_style = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
        
        if PatternFill and PatternFill is not Any:
            user_input_fill = PatternFill(start_color=highlight_fill_color, end_color=highlight_fill_color, fill_type="solid")

        ws.append(self.headers_plc)
        for cell in ws[1]: # Header row
            cell.font = Font(bold=True)
            if left_alignment:
                cell.alignment = left_alignment
            if thin_border_style:
                cell.border = thin_border_style

        address_allocator = PLCAddressAllocator() # 初始化地址分配器

        for idx, point_data in enumerate(plc_io_data, 1):
            # --- 1. 初始化 final_row_data 和填充基础信息 START ---
            final_row_data = ["" for _ in range(len(self.headers_plc))]
            final_row_data[0] = idx
            final_row_data[1] = point_data.get('model', '')
            channel_io_type = point_data.get('type', '') # 获取 channel_io_type
            final_row_data[2] = channel_io_type
            # final_row_data[3] = "" # 供电类型（有源/无源）
            # final_row_data[4] = "" # 线制
            final_row_data[5] = point_data.get('address', '') # 通道位号
            final_row_data[6] = site_name if site_name else ""
            final_row_data[7] = site_no if site_no else ""
            
            final_row_data[8] = "" # "变量名称（HMI）"列，用户填写

            final_row_data[9] = point_data.get('description', '')
            
            data_type_value = "" # 获取 data_type_value
            if channel_io_type in ["AI", "AO"]:
                data_type_value = "REAL"
            elif channel_io_type in ["DI", "DO"]:
                data_type_value = "BOOL"
            final_row_data[10] = data_type_value # 数据类型
            
            final_row_data[11] = "R/W" # 读写属性
            final_row_data[12] = "是"   # 保存历史
            final_row_data[13] = "是"   # 掉电保护
            # 量程 (14, 15) - 空
            # --- 1. 初始化 final_row_data 和填充基础信息 END ---

            # 初始化PLC地址列为空字符串 (这些变量用于后续的PLC地址和通讯地址的填充)
            sll_set_plc_addr, sl_set_plc_addr, sh_set_plc_addr, shh_set_plc_addr = "", "", "", ""
            ll_alarm_plc_addr, l_alarm_plc_addr, h_alarm_plc_addr, hh_alarm_plc_addr = "", "", "", ""
            maint_val_set_plc_addr, maint_enable_plc_addr, plc_absolute_addr = "", "", ""

            # 根据模块主数据类型分配PLC绝对地址
            if data_type_value == "REAL":
                plc_absolute_addr = address_allocator.allocate_real_address()
            elif data_type_value == "BOOL":
                plc_absolute_addr = address_allocator.allocate_bool_address()

            # 根据模块IO类型分配其他相关PLC地址 和 生成特定点位名称
            if channel_io_type == "AI":
                # PLC地址分配
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

                # Excel formulas for point/alarm names based on HMI Name column (column I)
                # Column I is get_column_letter(8 + 1)
                # Excel data row number is idx + 1 (idx is 1-based from enumerate)
                hmi_name_cell_ref = f"{get_column_letter(8 + 1)}{idx + 1}"

                final_row_data[17] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_LoLoLimit")' # SLL设定点位
                final_row_data[21] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_LoLimit")'   # SL设定点位
                final_row_data[25] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_HiLimit")'   # SH设定点位
                final_row_data[29] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_HiHiLimit")' # SHH设定点位
                
                final_row_data[32] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_LL")'        # LL报警
                final_row_data[35] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_L")'         # L报警
                final_row_data[38] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_H")'         # H报警
                final_row_data[41] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_HH")'        # HH报警
                
                final_row_data[45] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_whz")'       # 维护值设定点位
                final_row_data[48] = f'=IF(ISBLANK({hmi_name_cell_ref}), "", {hmi_name_cell_ref} & "_whzzt")'    # 维护使能开关点位

            elif channel_io_type == "DI":
                pass 

            elif channel_io_type == "AO":
                # PLC地址分配
                maint_val_set_plc_addr = address_allocator.allocate_real_address()
                maint_enable_plc_addr = address_allocator.allocate_bool_address()
                # 预留：未来可在此处为AO模块添加基于HMI名称的点位名称生成逻辑
                # if final_row_data[8]: 
                #     current_hmi_name = final_row_data[8]
                #     pass 

            elif channel_io_type == "DO":
                pass 

            # 计算对应的通讯地址 (这部分现在不需要显式初始化通讯地址变量，因为它们会在下面直接被赋值)
            # sll_set_comm_addr, sl_set_comm_addr, ... = "", "", ... (这些可以移除)
            
            # --- 2. 将所有地址和计算出的通讯地址填充到 final_row_data --- 
            # SLL (16设定值, 17设定点位(已在AI分支填充), 18 PLC地址, 19通讯地址)
            final_row_data[18] = sll_set_plc_addr
            final_row_data[19] = self._get_modbus_address(sll_set_plc_addr)
            # SL (20设定值, 21设定点位(已在AI分支填充), 22 PLC地址, 23通讯地址)
            final_row_data[22] = sl_set_plc_addr
            final_row_data[23] = self._get_modbus_address(sl_set_plc_addr)
            # SH (24设定值, 25设定点位(已在AI分支填充), 26 PLC地址, 27通讯地址)
            final_row_data[26] = sh_set_plc_addr
            final_row_data[27] = self._get_modbus_address(sh_set_plc_addr)
            # SHH (28设定值, 29设定点位(已在AI分支填充), 30 PLC地址, 31通讯地址)
            final_row_data[30] = shh_set_plc_addr
            final_row_data[31] = self._get_modbus_address(shh_set_plc_addr)
            
            # LL报警 (32报警(已在AI分支填充), 33 PLC地址, 34通讯地址)
            final_row_data[33] = ll_alarm_plc_addr
            final_row_data[34] = self._get_modbus_address(ll_alarm_plc_addr)
            # L报警 (35报警(已在AI分支填充), 36 PLC地址, 37通讯地址)
            final_row_data[36] = l_alarm_plc_addr
            final_row_data[37] = self._get_modbus_address(l_alarm_plc_addr)
            # H报警 (38报警(已在AI分支填充), 39 PLC地址, 40通讯地址)
            final_row_data[39] = h_alarm_plc_addr
            final_row_data[40] = self._get_modbus_address(h_alarm_plc_addr)
            # HH报警 (41报警(已在AI分支填充), 42 PLC地址, 43通讯地址)
            final_row_data[42] = hh_alarm_plc_addr
            final_row_data[43] = self._get_modbus_address(hh_alarm_plc_addr)
            
            # 维护值设定 (44值, 45点位(已在AI分支填充), 46 PLC地址, 47通讯地址)
            final_row_data[46] = maint_val_set_plc_addr
            final_row_data[47] = self._get_modbus_address(maint_val_set_plc_addr)
            # 维护使能开关 (48点位(已在AI分支填充), 49 PLC地址, 50通讯地址)
            final_row_data[49] = maint_enable_plc_addr
            final_row_data[50] = self._get_modbus_address(maint_enable_plc_addr)
            
            # PLC绝对地址 (51)
            final_row_data[51] = plc_absolute_addr
            # 上位机通讯地址 (52)
            final_row_data[52] = self._get_modbus_address(plc_absolute_addr)

            # logger.debug(f"准备写入行: LL报警通讯地址='{final_row_data[34]}', L报警通讯地址='{final_row_data[37]}', H报警通讯地址='{final_row_data[40]}', HH报警通讯地址='{final_row_data[43]}', 维护使能通讯地址='{final_row_data[50]}', 上位机通讯地址='{final_row_data[52]}'")
            ws.append(final_row_data)

            # Apply highlighting for user input cells and borders for all cells in the row
            current_excel_row = ws.max_row
            for col_idx, header in enumerate(self.headers_plc):
                cell = ws.cell(row=current_excel_row, column=col_idx + 1)
                
                # Apply highlight
                if user_input_fill:
                    should_highlight = False
                    if header in self.ALWAYS_HIGHLIGHT_HEADERS:
                        should_highlight = True
                    elif header in self.AI_SPECIFIC_HIGHLIGHT_HEADERS and channel_io_type == "AI":
                        should_highlight = True
                    
                    if should_highlight:
                        cell.fill = user_input_fill
                
                # Apply border
                if thin_border_style:
                    cell.border = thin_border_style
            
            if left_alignment: # This alignment was applied to the whole row before, keeping it if still desired
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
        global openpyxl, Worksheet, Font, get_column_letter, Alignment, PatternFill, Border, Side
        if openpyxl is None: # 检查是否在文件顶部成功导入
            try:
                import openpyxl as opxl_main # 使用别名避免与全局变量冲突
                from openpyxl.worksheet.worksheet import Worksheet as OpxlWorksheet
                from openpyxl.styles import Font as OpxlFont, Alignment as OpxlAlignment, PatternFill as OpxlPatternFill, Border as OpxlBorder, Side as OpxlSide
                from openpyxl.utils import get_column_letter as opxl_get_column_letter
                
                # 更新全局变量
                openpyxl = opxl_main
                Worksheet = OpxlWorksheet
                Font = OpxlFont
                Alignment = OpxlAlignment
                PatternFill = OpxlPatternFill
                Border = OpxlBorder
                Side = OpxlSide
                get_column_letter = opxl_get_column_letter
                logger.info("openpyxl library including PatternFill, Border, Side loaded successfully.")
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
