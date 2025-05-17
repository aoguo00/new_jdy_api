"""力控点表生成器模块"""
import csv # 导入 csv 模块
import logging
import os
from typing import Tuple, Optional, List, Dict, Any

# 尝试导入pypinyin，并设置一个标志
try:
    from pypinyin import pinyin, Style # 移除了 load_phrases_dict
    PYPINYIN_AVAILABLE = True
    # logger.info("pypinyin 自定义词组（如 '调压'）已成功加载，有助于提高DevName准确性。") # 移除相关日志
    # logger.error(f"pypinyin 自定义词组加载失败: {e_load_dict}。DevName生成可能受影响。") # 移除相关日志
except ImportError:
    PYPINYIN_AVAILABLE = False
    # 如果导入失败，在首次尝试使用时会记录日志

# 从 Shared Models 导入 UploadedIOPoint
from core.post_upload_processor.uploaded_file_processor.io_data_model import UploadedIOPoint
# 导入用于获取主IO表名的常量 (如果 excel_reader 定义了这样一个可导出的常量)
# from core.post_upload_processor.uploaded_file_processor.excel_reader import MAIN_IO_SHEET_NAME # 假设存在

logger = logging.getLogger(__name__)

# MAIN_IO_SHEET_NAME_DEFAULT 用于在无法从外部导入时提供一个默认值
MAIN_IO_SHEET_NAME_DEFAULT = "IO点表"

# CSV 文件中模拟量 (REAL) 的列定义 (来自 Basic.csv)
# TagType,0,TagTypeName,模拟I/O量,Count,动态计算,ParCount,62
LK_REAL_COLUMNS = [
    'NodePath', 'NAME', 'DESC', 'FORMAT', 'LASTPV', 'PV', 'EU', 'EULO', 'EUHI', 
    'PVRAW', 'SCALEFL', 'PVRAWLO', 'PVRAWHI', 'STATIS', 'ALMENAB', 'DEADBAND', 
    'LL', 'LO', 'HI', 'HH', 'RATE', 'DEV', 'LLPR', 'LOPR', 'HIPR', 'HHPR', 
    'RATEPR', 'DEVPR', 'RATECYC', 'SP', 'SQRTFL', 'ALARMDELAY', 'LINEFL', 
    'LINETBL', 'ROCFL', 'ROC', 'L3', 'L4', 'L5', 'L3PR', 'L4PR', 'L5PR', 
    'H3PR', 'H4PR', 'H5PR', 'H3', 'H4', 'H5', 'GROUP', 'INDEX', 'L5NAME', 
    'L4NAME', 'L3NAME', 'LLNAME', 'LONAME', 'HINAME', 'HHNAME', 'H3NAME', 
    'H4NAME', 'H5NAME', 'RATENAME', 'DEVNAME', 'ALMREMARK'
]
LK_REAL_COLUMNS_DESC = [
    "点所在的节点路径", "点名", "说明", "小数点位数", "上次采样值", "正常采样值", 
    "工程单位", "工程单位低限", "工程单位高限", "原始值", "量程转换开关", "原始值低限", 
    "原始值高限", "统计开关", "报警使能", "死区范围", "低低限", "低限", "高限", 
    "高高限", "变化率报警限值", "偏差报警限值", "低低限报警优先级", "低限报警优先级", 
    "高限报警优先级", "高高限报警优先级", "变化率报警优先级", "偏差报警优先级", 
    "变化周期", "目标值", "开平方转换开关", "报警延时", "折线化开关", "折线化表", 
    "突变率开关", "突变率值", "低3限", "低4限", "低5限", "低3限优先级", "低4限优先级", 
    "低5限优先级", "高3限优先级", "高4限优先级", "高5限优先级", "高3限", "高4限", "高5限", 
    "报警分组号", "序号", "低5限名称", "低4限名称", "低3限名称", "低低限名称", "低限名称", 
    "高限名称", "高高限名称", "高3限名称", "高4限名称", "高5限名称", "变化率名称", 
    "偏差名称", "报警备注"
]

# CSV 文件中数字量 (BOOL) 的列定义 (来自 Basic.csv)
# TagType,1,TagTypeName,数字I/O量,Count,动态计算,ParCount,13
LK_BOOL_COLUMNS = [
    'NodePath', 'NAME', 'DESC', 'PV', 'OFFMES', 'ONMES', 'ALMENAB', 
    'NORMALVAL', 'ALARMPR', 'GROUP', 'INDEX', 'ALMNAME', 'ALMREMARK', 'ALARMDELAY'
]
LK_BOOL_COLUMNS_DESC = [
    "点所在的节点路径", "点名", "说明", "正常采样值", "OFF状态信息", "ON状态信息", 
    "报警使能", "正常状态值", "状态异常报警优先级", "报警分组号", "序号", 
    "报警名称", "报警备注", "报警延时"
]


def _is_value_empty_for_hmi(value: Optional[str]) -> bool:
    """辅助函数：检查值是否被视为空（用于HMI名称）。"""
    return not (value and value.strip())

class LikongGenerator:
    """力控点表生成器 (CSV格式)"""

    # Link.csv 文件列定义 (基于提供的 Link.csv 示例)
    # 行3: 实际数据列的英文/拼音标识 (部分在示例文件中因编码问题显示为乱码, 此处尽量还原)
    LK_LINK_COLUMNS_LINE3 = [
        'NodePath', 'TagName', 'TagDesc', 'ParName', 'LinkDesc', '驱动标志',
        'modbus驱动标志', '位起始位', '扫描周期', '使能位', '数据类型',
        'I/O数据地址', '是否位访问', '表示读取数据时需要获取的数据长度',
        '高字节在前0低字节在前1高位在前', '读写标志', '取反(读出时)',
        '文件号', '显示数据的格式',
        '显示小数位的个数(若为一位 则 表示字节内部的高低字节 0 低字节 1 高字节)'
    ]
    # 行4: 中文描述性表头
    LK_LINK_COLUMNS_DESC_LINE4 = [
        "点所在的节点路径", "点名", "点描述", "参数名", "链接描述", "驱动标志",
        "modbus驱动标志", "位起始位", "扫描周期", "使能位", "数据类型",
        "I/O数据地址", "是否按位访问", "表示读取数据时需要获取的数据长度",
        "高字节在前0低字节在前1高位在前", "读写标志", "取反(读出时)",
        "文件号", "显示数据的格式",
        "显示小数位的个数(若为一位 则 表示字节内部的高低字节 0 低字节 1 高字节)"
    ]

    def __init__(self):
        """初始化力控生成器"""
        pass

    def _get_site_defaults(self, points_by_sheet: Dict[str, List[UploadedIOPoint]]) -> Tuple[str, str]:
        """辅助方法：从主IO表获取默认场站名和场站编号"""
        main_io_sheet_key = MAIN_IO_SHEET_NAME_DEFAULT
        default_site_name = ""
        default_site_number = ""

        main_io_points_list_for_site_info = points_by_sheet.get(main_io_sheet_key)
        if main_io_points_list_for_site_info and len(main_io_points_list_for_site_info) > 0:
            first_valid_main_point_for_site_info = next((
                p for p in main_io_points_list_for_site_info
                if (p.site_name and p.site_name.strip()) or (p.site_number and p.site_number.strip())
            ), None)
            if first_valid_main_point_for_site_info:
                if first_valid_main_point_for_site_info.site_name and first_valid_main_point_for_site_info.site_name.strip():
                    default_site_name = first_valid_main_point_for_site_info.site_name.strip()
                if first_valid_main_point_for_site_info.site_number and first_valid_main_point_for_site_info.site_number.strip():
                    default_site_number = first_valid_main_point_for_site_info.site_number.strip()
        
        if not default_site_name and not default_site_number: # DevName 主要依赖场站名，场站编号更多用于点名
            logger.warning(f"力控CSV生成器: 未能在主IO表 '{main_io_sheet_key}' 中找到有效的全局默认场站名。DevName可能无法正确生成。")
        else:
            logger.info(f"力控CSV生成器: 使用全局默认场站名='{default_site_name}', 场站编号='{default_site_number}' (如果点位自身无特定信息)")
        return default_site_name, default_site_number

    def _get_dev_name_from_site_name(self, site_name_chinese: Optional[str]) -> str:
        """
        从中文场站名获取拼音首字母大写缩写作为DevName。
        如果pypinyin库不可用或发生错误，则返回空字符串。
        """
        if not PYPINYIN_AVAILABLE:
            # 这个错误只在第一次尝试使用时记录，避免重复日志
            if not hasattr(self, '_pypinyin_error_logged'):
                logger.error("pypinyin库未安装或无法导入。无法动态生成DevName。请运行 'pip install pypinyin' 安装。")
                self._pypinyin_error_logged = True # 标记已记录错误
            return ""

        if not site_name_chinese or not site_name_chinese.strip():
            logger.debug("场站名为空，无法从中生成DevName。")
            return ""
        
        try:
            first_letters = []
            # strict=False 更健壮; errors='ignore' 会忽略无法转换的字符
            pinyin_list_of_lists = pinyin(site_name_chinese, style=Style.FIRST_LETTER, strict=False, errors='ignore') 
            
            for char_pinyins in pinyin_list_of_lists:
                # char_pinyins 是一个列表, e.g., ['x'] for '西'
                if char_pinyins and char_pinyins[0]: 
                    first_letters.append(char_pinyins[0][0].upper()) # 取首字母列表的第一个元素 (字符串), 再取其第一个字符并大写
            
            generated_name = "".join(first_letters)
            if not generated_name:
                 logger.warning(f"从场站名 '{site_name_chinese}' 生成的DevName为空字符串（可能包含非中文字符或pypinyin处理结果为空）。")
            return generated_name
        except Exception as e:
            logger.error(f"使用pypinyin从场站名 '{site_name_chinese}' 生成DevName时发生意外错误: {e}")
            return "" # 发生转换错误也返回空

    def _clamp_alarm_value(self, 
                           value_str: Optional[str], 
                           default_value_str: str, 
                           eulo_float: Optional[float], 
                           euhi_float: Optional[float],
                           alarm_type_name: str,
                           point_hmi_name: str) -> str:
        """辅助方法：检查、转换并钳位单个报警值到工程单位范围内。"""
        if value_str is None or value_str.strip() == "":
            return default_value_str # 用户未设置，使用硬编码默认值

        try:
            value_float = float(value_str.strip())
        except ValueError:
            logger.warning(f"点 '{point_hmi_name}' 的报警值 '{alarm_type_name}' ('{value_str}') 不是有效数字，将使用默认值 '{default_value_str}'。")
            return default_value_str

        # 仅当工程范围有效时才进行钳位
        final_value_str = value_str.strip() # 默认为用户提供的有效数字字符串
        clamped = False
        if eulo_float is not None and euhi_float is not None and eulo_float <= euhi_float:
            if value_float < eulo_float:
                final_value_str = str(eulo_float) # 使用 EULO 的字符串形式，确保格式
                clamped = True
            elif value_float > euhi_float:
                final_value_str = str(euhi_float) # 使用 EUHI 的字符串形式
                clamped = True
            
            if clamped:
                logger.warning(f"点 '{point_hmi_name}' 的报警值 '{alarm_type_name}' ('{value_str}') 超出工程范围 [{eulo_float}, {euhi_float}]，已被钳位到 '{final_value_str}'。")
        
        return final_value_str

    def generate_basic_csv(self,
                           output_dir: str,
                           points_by_sheet: Dict[str, List[UploadedIOPoint]]
                           ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控点表的CSV文件: Basic.csv
        该文件包含预定义的TagType结构、表头，并根据输入数据填充点位信息。
        文件编码为 GBK。
        """
        # 1. 获取全局默认场站信息
        default_site_name, default_site_number = self._get_site_defaults(points_by_sheet)
        
        file_name = "Basic.csv"
        file_path = os.path.join(output_dir, file_name)

        real_points: List[UploadedIOPoint] = []
        bool_points: List[UploadedIOPoint] = []

        if points_by_sheet:
            for _, points_list in points_by_sheet.items():
                for point in points_list:
                    point_data_type_upper = str(point.data_type or "").upper().strip()
                    hmi_name_from_point = str(point.hmi_variable_name or "").strip()

                    if _is_value_empty_for_hmi(hmi_name_from_point):
                        logger.warning(f"Basic.csv: 点 (类型:'{point_data_type_upper}', 通道:'{point.channel_tag}') HMI名称为空或无效，跳过。")
                        continue

                    if point_data_type_upper == "REAL" or point_data_type_upper == "FLOAT":
                        real_points.append(point)
                    elif point_data_type_upper == "BOOL":
                        bool_points.append(point)
        
        tag_types_to_generate = []
        if real_points: tag_types_to_generate.append("REAL")
        if bool_points: tag_types_to_generate.append("BOOL")
        
        # 为数字量报警点查找父模拟量点及其设定，预先创建查找表
        analog_points_lookup_by_hmi_name: Dict[str, UploadedIOPoint] = {}
        if real_points: # 确保 real_points 列表不是 None 或空
            analog_points_lookup_by_hmi_name = {p.hmi_variable_name: p for p in real_points if p.hmi_variable_name}

        try:
            with open(file_path, 'w', newline='', encoding='gbk') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Ver", "10"])
                writer.writerow(["TagTypeCount", "7"])
                total_points_written = 0

                # --- 1. 处理模拟量 (REAL) --- Type ID 0
                lk_real_count = len(real_points)
                # ParCount is the zero-based index of the last column
                real_par_count = len(LK_REAL_COLUMNS) - 1 if LK_REAL_COLUMNS else 0
                writer.writerow(["TagType", "0", "TagTypeName", "模拟I/O量", "Count", lk_real_count, "ParCount", real_par_count])
                writer.writerow(LK_REAL_COLUMNS)
                writer.writerow(LK_REAL_COLUMNS_DESC)
                if real_points:
                    logger.info(f"力控 Basic.csv: 开始写入 {lk_real_count} 个模拟量点位...")
                    for point in real_points:
                        row_data = {}
                        current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
                        current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()
                        
                        row_data['NodePath'] = f"{current_point_site_name}\\" if current_point_site_name else ""
                        row_data['NAME'] = f"{current_point_site_number}{point.hmi_variable_name.strip()}"
                        row_data['DESC'] = point.variable_description or ""
                        row_data['FORMAT'] = "3" 
                        row_data['LASTPV'] = "0.000"
                        row_data['PV'] = "0.000"
                        row_data['EU'] = "" 
                        # logger.debug(f"点 '{row_data['NAME']}' 的 EU (工程单位) 因 UploadedIOPoint 中无对应属性而置空。") # 注释掉原debug信息
                        
                        # 获取工程单位低限和高限的字符串及浮点数值，用于钳位
                        eulo_str = str(point.range_low_limit) if point.range_low_limit is not None and point.range_low_limit.strip() else "0.000"
                        euhi_str = str(point.range_high_limit) if point.range_high_limit is not None and point.range_high_limit.strip() else "100.000"
                        row_data['EULO'] = eulo_str
                        row_data['EUHI'] = euhi_str

                        eulo_float: Optional[float] = None
                        euhi_float: Optional[float] = None
                        try:
                            eulo_float = float(eulo_str)
                            euhi_float = float(euhi_str)
                            if eulo_float > euhi_float:
                                logger.warning(f"点 '{row_data['NAME']}' 的工程单位范围无效 (EULO: {eulo_float} > EUHI: {euhi_float})，报警值钳位可能不准确。") # error -> warning
                        except ValueError:
                            logger.warning(f"点 '{row_data['NAME']}' 的 EULO ('{eulo_str}') 或 EUHI ('{euhi_str}') 不是有效数字，无法进行报警值钳位。") # error -> warning
                        
                        row_data['PVRAW'] = "0.000"
                        row_data['SCALEFL'] = "0" 
                        row_data['PVRAWLO'] = "0.000" 
                        row_data['PVRAWHI'] = "4095.000" 
                        row_data['STATIS'] = "0" 

                        # ALMENAB 逻辑：检查是否有任何一个相关的报警设定值存在且不为空
                        has_sll = point.sll_set_value is not None and point.sll_set_value.strip() != ""
                        has_sl = point.sl_set_value is not None and point.sl_set_value.strip() != ""
                        has_sh = point.sh_set_value is not None and point.sh_set_value.strip() != ""
                        has_shh = point.shh_set_value is not None and point.shh_set_value.strip() != ""
                        
                        if has_sll or has_sl or has_sh or has_shh:
                            row_data['ALMENAB'] = "1"
                        else:
                            row_data['ALMENAB'] = "0"
                            
                        row_data['DEADBAND'] = "0.000" 
                        
                        # 应用钳位逻辑到报警值
                        row_data['LL'] = self._clamp_alarm_value(point.sll_set_value, "8.000", eulo_float, euhi_float, "LL", row_data['NAME'])
                        row_data['LO'] = self._clamp_alarm_value(point.sl_set_value, "10.000", eulo_float, euhi_float, "LO", row_data['NAME'])
                        row_data['HI'] = self._clamp_alarm_value(point.sh_set_value, "92.000", eulo_float, euhi_float, "HI", row_data['NAME'])
                        row_data['HH'] = self._clamp_alarm_value(point.shh_set_value, "94.000", eulo_float, euhi_float, "HH", row_data['NAME'])
                        row_data['RATE'] = "0.000" 
                        row_data['DEV'] = "0.000"  
                        
                        # 根据 ALMENAB 设置主要报警优先级
                        if row_data['ALMENAB'] == "1":
                            row_data['LLPR'] = "1"
                            row_data['LOPR'] = "1" 
                            row_data['HIPR'] = "1" 
                            row_data['HHPR'] = "1"
                        else:
                            row_data['LLPR'] = "0"
                            row_data['LOPR'] = "0"
                            row_data['HIPR'] = "0"
                            row_data['HHPR'] = "0"
                        
                        row_data['RATEPR'] = "0" # RATEPR 保持为0，除非有特定逻辑
                        row_data['DEVPR'] = "0"  # DEVPR 保持为0，除非有特定逻辑
                        row_data['RATECYC'] = "1" 
                        row_data['SP'] = "0.000" 
                        row_data['SQRTFL'] = "0" 
                        row_data['ALARMDELAY'] = "0" 
                        row_data['LINEFL'] = "0" 
                        row_data['LINETBL'] = "" 
                        row_data['ROCFL'] = "0" 
                        row_data['ROC'] = "0.000" 
                        
                        row_data['L3'], row_data['L4'], row_data['L5'] = "0.000", "0.000", "0.000"
                        row_data['H3'], row_data['H4'], row_data['H5'] = "0.000", "0.000", "0.000"
                        row_data['L3PR'], row_data['L4PR'], row_data['L5PR'] = "0", "0", "0"
                        row_data['H3PR'], row_data['H4PR'], row_data['H5PR'] = "0", "0", "0"
                        row_data['GROUP'] = "0" 
                        row_data['INDEX'] = "" # INDEX 列要求为空
                        
                        row_data['L5NAME'], row_data['L4NAME'], row_data['L3NAME'] = "低5限", "低4限", "低3限"
                        row_data['LLNAME'], row_data['LONAME'] = "低低报", "低报"
                        row_data['HINAME'], row_data['HHNAME'] = "高报", "高高报"
                        row_data['H3NAME'], row_data['H4NAME'], row_data['H5NAME'] = "高3限", "高4限", "高5限"
                        row_data['RATENAME'], row_data['DEVNAME'] = "变化率报警", "偏差报警"
                        row_data['ALMREMARK'] = "" 
                        
                        writer.writerow([row_data.get(col, "") for col in LK_REAL_COLUMNS])
                        total_points_written += 1
                    logger.info(f"力控 Basic.csv: 模拟量点位写入完成。")
                writer.writerow([]) # 空行分隔

                # --- 2. 处理数字量 (BOOL) --- Type ID 1
                lk_bool_count = len(bool_points)
                # ParCount is the zero-based index of the last column
                bool_par_count = len(LK_BOOL_COLUMNS) - 1 if LK_BOOL_COLUMNS else 0
                writer.writerow(["TagType", "1", "TagTypeName", "数字I/O量", "Count", lk_bool_count, "ParCount", bool_par_count])
                writer.writerow(LK_BOOL_COLUMNS)
                writer.writerow(LK_BOOL_COLUMNS_DESC)
                if bool_points:
                    logger.info(f"力控 Basic.csv: 开始写入 {lk_bool_count} 个数字量点位...")
                    
                    alarm_suffixes_map = {
                        "_LL": "sll_set_value", 
                        "_L": "sl_set_value", 
                        "_H": "sh_set_value", 
                        "_HH": "shh_set_value"
                    }
                    default_alarm_values_map = {
                        "_LL": "8.000", 
                        "_L": "10.000", 
                        "_H": "92.000", 
                        "_HH": "94.000"
                    }

                    for point in bool_points:
                        row_data = {}
                        current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
                        current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()

                        row_data['NodePath'] = f"{current_point_site_name}\\" if current_point_site_name else ""
                        hmi_name = point.hmi_variable_name.strip() if point.hmi_variable_name else ""
                        row_data['NAME'] = f"{current_point_site_number}{hmi_name}"
                        row_data['DESC'] = point.variable_description or ""
                        
                        is_maintenance_switch = hmi_name.endswith("_whzzt")

                        if is_maintenance_switch:
                            row_data['PV'] = "0"
                            row_data['ALMENAB'] = "0"
                            row_data['ALARMPR'] = "0"
                            # logger.debug(f"数字点 '{hmi_name}' 是维护值开关 (_whzzt)，PV设为0, ALMENAB设为0, ALARMPR设为0。")
                        else:
                            row_data['PV'] = "0" # 普通数字量PV默认也为0
                            # 数字量 ALMENAB 逻辑 (非维护值开关时)
                            # 默认情况下，ALMENAB 为 "0"，除非明确满足派生报警条件
                            current_digital_almenab = "0" 
                            is_derived_analog_alarm_point = False

                            if point.source_type == "intermediate_from_main" and hmi_name:
                                for suffix, raw_value_attr_name in alarm_suffixes_map.items():
                                    if hmi_name.endswith(suffix):
                                        is_derived_analog_alarm_point = True # 标记为已尝试处理的派生报警类型
                                        parent_hmi_name = hmi_name[:-len(suffix)]
                                        parent_analog_point = analog_points_lookup_by_hmi_name.get(parent_hmi_name)

                                        if parent_analog_point:
                                            raw_alarm_value_from_excel_str = getattr(parent_analog_point, raw_value_attr_name, None)
                                            
                                            if raw_alarm_value_from_excel_str is not None and raw_alarm_value_from_excel_str.strip() != "":
                                                if raw_alarm_value_from_excel_str.strip() == default_alarm_values_map[suffix]:
                                                    # current_digital_almenab 保持 "0"
                                                    # logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 的 '{raw_value_attr_name}' ('{raw_alarm_value_from_excel_str}') 与通用默认值相同，ALMENAB保持为0。")
                                                    pass # 保持为0
                                                else:
                                                    current_digital_almenab = "1" # 只有这种情况才使能
                                                    # logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 的 '{raw_value_attr_name}' ('{raw_alarm_value_from_excel_str}') 已设定且非默认，ALMENAB设为1。")
                                            else:
                                                # current_digital_almenab 保持 "0"
                                                # logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 未设定 '{raw_value_attr_name}'，ALMENAB保持为0。")
                                                pass # 保持为0
                                        else:
                                            # current_digital_almenab 保持 "0"
                                            logger.warning(f"派生数字报警点 '{hmi_name}' 未能找到父模拟量点 '{parent_hmi_name}'，ALMENAB保持为0。")
                                        break 
                            
                            # 如果不是已识别并成功处理的派生报警类型，ALMENAB 会是初始的 "0"
                            if not is_derived_analog_alarm_point and not is_maintenance_switch: #确保维护开关的逻辑不被覆盖
                                 # logger.debug(f"数字点 '{hmi_name}' 非特定派生报警类型或未成功关联，ALMENAB设为0。")
                                 pass # current_digital_almenab 已经是 "0"

                            row_data['ALMENAB'] = current_digital_almenab
                            if current_digital_almenab == "0":
                                row_data['ALARMPR'] = "0"
                            else:
                                row_data['ALARMPR'] = "1" # 只有当ALMENAB为1时，优先级才为1

                        # 通用数字量列
                        row_data['OFFMES'] = "关" 
                        row_data['ONMES'] = "开"   
                        row_data['NORMALVAL'] = "0" 
                        row_data['GROUP'] = "0" 
                        row_data['INDEX'] = "" 
                        row_data['ALMNAME'] = "状态异常" 
                        row_data['ALMREMARK'] = "" 
                        row_data['ALARMDELAY'] = "0" 

                        writer.writerow([row_data.get(col, "") for col in LK_BOOL_COLUMNS])
                        total_points_written += 1
                    logger.info(f"力控 Basic.csv: 数字量点位写入完成。")
                writer.writerow([])

                # --- 3. 其他空的 TagType 定义 (根据 Basic.csv 示例和用户截图精确调整) ---
                # 对于这些空的类型，ParCount 固定为1，且只有NodePath和NAME两列
                empty_tag_types_structure = [
                    ("2", "累计量"),
                    ("3", "控制量"),
                    ("4", "运算量"),
                    ("5", "组合量"),
                    ("12", "字符类型点")
                ]
                
                empty_type_columns = ["NodePath", "NAME"]
                empty_type_columns_desc = ["点所在的节点路径", "点名"]

                for type_id, type_name_cn in empty_tag_types_structure:
                    # For these empty types with 2 columns (NodePath, NAME), ParCount (zero-based last index) is 1.
                    # This was (len(empty_type_columns) - 1) = 2 - 1 = 1.
                    writer.writerow(["TagType", type_id, "TagTypeName", type_name_cn, "Count", 0, "ParCount", 1])
                    writer.writerow(empty_type_columns)
                    writer.writerow(empty_type_columns_desc) 
                    writer.writerow([]) # 空行分隔

            if total_points_written > 0:
                logger.info(f"力控 Basic.csv: 总共成功处理并写入 {total_points_written} 个点位。")
            else:
                logger.info("力控 Basic.csv: 未处理或写入任何有效点位。")

            logger.info(f"成功生成力控CSV文件 (Basic.csv): {file_path}")
            return True, file_path, None

        except Exception as e:
            error_msg = f"生成 Basic.csv 文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def generate_his_csv(self, 
                         output_dir: str, 
                         points_by_sheet: Dict[str, List[UploadedIOPoint]]
                         ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控历史记录配置文件: His.csv
        为所有在 Basic.csv 中生成的模拟量和数字量点记录其 PV 值。
        文件编码为 GBK。
        """
        file_name = "His.csv"
        file_path = os.path.join(output_dir, file_name)
        
        # 1. 获取全局默认场站信息 (与Basic.csv生成时一致)
        default_site_name, default_site_number = self._get_site_defaults(points_by_sheet)

        history_entries = []

        if points_by_sheet:
            for _, points_list in points_by_sheet.items():
                for point in points_list:
                    point_data_type_upper = str(point.data_type or "").upper().strip()
                    hmi_name_from_point = str(point.hmi_variable_name or "").strip()

                    if _is_value_empty_for_hmi(hmi_name_from_point):
                        # logger.warning(f"His.csv: 点 (类型:'{point_data_type_upper}', 通道:'{point.channel_tag}') HMI名称为空或无效，跳过。")
                        continue # 跳过HMI名称无效的点

                    if point_data_type_upper == "REAL" or point_data_type_upper == "FLOAT" or point_data_type_upper == "BOOL":
                        current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
                        current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()
                        
                        nodepath = f"{current_point_site_name}\\" if current_point_site_name else ""
                        tagname = f"{current_point_site_number}{hmi_name_from_point}"
                        
                        history_entries.append([
                            nodepath,
                            tagname,
                            "PV",       # ParName: 参数名
                            "0",        # SaveType (变化存储): 历史存储方式:0-变化存储;1-定时存储;2-按键或脚本存储
                            "0.000000", # SaveCfg (死区): 历史参数配置
                            "",         # SaveScript: 历史参数脚本
                            "",         # StatTime: 统计时间长度
                            ""          # StatUnit: 统计时间单位
                        ])
        
        try:
            with open(file_path, 'w', newline='', encoding='gbk') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Ver", "9"])
                writer.writerow(["Count", len(history_entries)])
                writer.writerow([
                    "NodePath", "TagName", "ParName", 
                    "SaveType", "SaveCfg", "SaveScript", 
                    "StatTime", "StatUnit"
                ])
                writer.writerow([
                    "点所在的节点路径", "点名", "参数名", 
                    "历史存储方式:0-变化存储;1-定时存储;2-按键或脚本存储", 
                    "历史参数配置", "历史参数脚本", 
                    "统计时间长度", "统计时间单位"
                ])
                
                # 写入所有数据行
                for entry in history_entries:
                    writer.writerow(entry)

                # 新增：写入文件末尾的固定内容
                writer.writerow([]) # 写入一个空行
                writer.writerow(['ExitSave', 'Count', '0', '', '', '', '', '']) 
                writer.writerow(['NodePath', 'TagName', 'ParName', '', '', '', '', '']) 

            logger.info(f"成功生成力控历史配置文件 (His.csv): {file_path}")
            return True, file_path, None

        except Exception as e:
            error_msg = f"生成 His.csv 文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def generate_link_csv(self,
                          output_dir: str,
                          points_by_sheet: Dict[str, List[UploadedIOPoint]]
                          ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控链接配置文件: Link.csv
        文件编码为 GBK。
        根据用户规则填充通讯地址等信息。
        """
        file_name = "Link.csv"
        file_path = os.path.join(output_dir, file_name)

        default_site_name, default_site_number = self._get_site_defaults(points_by_sheet)
        
        # 动态生成DevName
        dev_name_for_csv = self._get_dev_name_from_site_name(default_site_name)
        if not dev_name_for_csv: # 如果生成失败或为空
            dev_name_for_csv = "XBPQTYZ" # 回退到原始硬编码值或新的默认值
            logger.warning(f"无法从场站名 '{default_site_name}' 动态生成DevName，将使用默认值 '{dev_name_for_csv}'。请确保pypinyin已安装且场站名有效。")

        link_data_rows: List[List[str]] = [] 

        all_points: List[UploadedIOPoint] = []
        if points_by_sheet:
            for _, points_list_val in points_by_sheet.items():
                all_points.extend(points_list_val)

        for point in all_points:
            point_data_type_upper = str(point.data_type or "").upper().strip()
            hmi_name_from_point = str(point.hmi_variable_name or "").strip()
            communication_address_str = str(point.hmi_communication_address or "").strip()

            if _is_value_empty_for_hmi(hmi_name_from_point):
                logger.debug(f"Link.csv: 点 (类型:'{point_data_type_upper}', 上位机通讯地址:'{communication_address_str}') HMI名称为空或无效，跳过。")
                continue
            
            if not communication_address_str:
                logger.warning(f"Link.csv: 点 (HMI:'{hmi_name_from_point}', 类型:'{point_data_type_upper}') 上位机通讯地址 (hmi_communication_address) 为空，跳过生成Link.csv条目。")
                continue

            # 提取核心数字地址部分
            address_to_process = None
            parts = communication_address_str.split('_')
            if parts and parts[-1].isdigit(): # 检查最后一部分是否为数字
                address_to_process = parts[-1]
            elif communication_address_str.isdigit(): # 检查整个上位机通讯地址是否为数字
                address_to_process = communication_address_str
            
            if address_to_process is None:
                logger.warning(f"Link.csv: 点 (HMI:'{hmi_name_from_point}') 的上位机通讯地址 '{communication_address_str}' 无法解析出有效的数字部分，跳过。")
                continue

            row_dict: Dict[str, str] = {} 
            current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
            current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()

            row_dict['NodePath'] = f"{current_point_site_name}\\" if current_point_site_name else ""
            row_dict['TagName'] = f"{current_point_site_number}{hmi_name_from_point}" # 注意：示例文件中的TagName似乎不含场站编号，这里暂按原逻辑
            row_dict['TagDesc'] = point.variable_description or ""
            row_dict['ParName'] = "PV"

            row_dict['modbus驱动标志'] = "-9999"
            row_dict['位起始位'] = "0"
            row_dict['扫描周期'] = "0"
            row_dict['使能位'] = "0"
            row_dict['是否位访问'] = "0"
            row_dict['高字节在前0低字节在前1高位在前'] = "0"
            row_dict['读写标志'] = "0"
            row_dict['取反(读出时)'] = "1"
            row_dict[self.LK_LINK_COLUMNS_LINE3[-1]] = "0" # '显示小数位的个数(...)'

            io_address_calc_success = False

            if point_data_type_upper == "BOOL":
                row_dict['LinkDesc'] = f"DO{address_to_process}"
                row_dict['驱动标志'] = row_dict['LinkDesc']
                row_dict['数据类型'] = "1"
                row_dict['I/O数据地址'] = str(int(address_to_process) - 1)
                row_dict['表示读取数据时需要获取的数据长度'] = "1"
                row_dict['文件号'] = "2"
                row_dict['显示数据的格式'] = "0"
                io_address_calc_success = True

            elif point_data_type_upper == "REAL" or point_data_type_upper == "FLOAT":
                final_numeric_address_for_real = address_to_process
                if address_to_process.startswith('4') and len(address_to_process) > 1:
                    processed_val = address_to_process[1:]
                    if processed_val: 
                       final_numeric_address_for_real = processed_val
                    else: 
                        logger.warning(f"Link.csv: REAL点 '{hmi_name_from_point}' 的地址部分 '{address_to_process}' (来自 '{communication_address_str}') 在移除'4'后为空，跳过。")
                        continue
                
                row_dict['LinkDesc'] = f"HR Float:{final_numeric_address_for_real}"
                row_dict['驱动标志'] = row_dict['LinkDesc']
                row_dict['数据类型'] = "2"
                row_dict['I/O数据地址'] = str(int(final_numeric_address_for_real) - 1)
                row_dict['表示读取数据时需要获取的数据长度'] = "4" 
                row_dict['文件号'] = "7" 
                row_dict['显示数据的格式'] = "0"
                io_address_calc_success = True
            else:
                logger.info(f"Link.csv: 点 '{hmi_name_from_point}' 的数据类型 '{point_data_type_upper}' 非 BOOL 或 REAL，跳过生成Link.csv条目。")
                continue

            if io_address_calc_success:
                current_row_values = [row_dict.get(col_name, "") for col_name in self.LK_LINK_COLUMNS_LINE3]
                link_data_rows.append(current_row_values)
        
        # 新增：收集内部链接条目
        inter_link_entries: List[List[str]] = []
        for point in all_points:
            point_data_type_upper = str(point.data_type or "").upper().strip()
            if point_data_type_upper == "REAL" or point_data_type_upper == "FLOAT":
                current_point_site_name = (point.site_name if point.site_name and point.site_name.strip() else default_site_name).strip()
                current_point_site_number = (point.site_number if point.site_number and point.site_number.strip() else default_site_number).strip()
                
                source_np = f"{current_point_site_name}\\" if current_point_site_name else ""
                # 确保 HMI 名称不为空才继续，因为它是源标签名的一部分
                if not point.hmi_variable_name or not point.hmi_variable_name.strip():
                    continue
                source_tn = f"{current_point_site_number}{point.hmi_variable_name.strip()}"

                alarm_link_configs = [
                    ("LL", point.sll_set_point),
                    ("LO", point.sl_set_point),
                    ("HI", point.sh_set_point),
                    ("HH", point.shh_set_point)
                ]

                for par_name, target_hmi_name_attr in alarm_link_configs:
                    target_hmi_name_val = str(target_hmi_name_attr or "").strip()
                    if target_hmi_name_val:
                        # LinkLongTagName 结构: SourceNodePath + SiteNumber + TargetHMIVariableName
                        # (假设目标点与源点在同一NodePath下，使用相同的SiteNumber前缀)
                        link_long_tag_name = f"{source_np}{current_point_site_number}{target_hmi_name_val}"
                        inter_link_entries.append([source_np, source_tn, par_name, link_long_tag_name, "PV"])
                        logger.debug(f"Link.csv: 为点 '{source_tn}' 的参数 '{par_name}' 生成内部链接到 '{link_long_tag_name}'")

        try:
            with open(file_path, 'w', newline='', encoding='gbk') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Ver", "11"])
                writer.writerow(["DevCount", "1", "TextFormat", "1"])
                writer.writerow(["DevName", dev_name_for_csv, "LinkCount", str(len(link_data_rows))])
                writer.writerow(self.LK_LINK_COLUMNS_LINE3)
                for data_row_list_val in link_data_rows:
                    writer.writerow(data_row_list_val)
                
                writer.writerow([]) # 空行
                writer.writerow(["NetSourceCount", "0"])
                
                writer.writerow([]) # 空行
                writer.writerow(["InterLinkCount", str(len(inter_link_entries))])
                if inter_link_entries:
                    lk_interlink_headers = ["SourceNodePath", "SourceTagName", "SourceParName", "LinkLongTagName", "LinkParName"]
                    writer.writerow(lk_interlink_headers)
                    for inter_link_row in inter_link_entries:
                        writer.writerow(inter_link_row)
                
                writer.writerow([]) # 空行
                writer.writerow(["DataServerDriverCount", "0"])
            logger.info(f"成功生成力控链接配置文件 (Link.csv): {file_path}，包含 {len(link_data_rows)} 个主链接和 {len(inter_link_entries)} 个内部链接。")
            return True, file_path, None
        except Exception as e:
            error_msg = f"生成 Link.csv 文件失败: {e}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg

    def generate_all_csvs(self, 
                            output_dir: str, 
                            points_by_sheet: Dict[str, List[UploadedIOPoint]]
                            ) -> List[Tuple[str, bool, Optional[str], Optional[str]]]:
        """
        生成所有力控相关的CSV文件 (Basic.csv, His.csv, Link.csv)。
        返回每个文件生成结果的列表。
        """
        results = []
        
        # 生成 Basic.csv
        logger.info("开始生成 Basic.csv...")
        basic_success, basic_file_path, basic_err_msg = self.generate_basic_csv(output_dir, points_by_sheet)
        results.append(("Basic.csv", basic_success, basic_file_path, basic_err_msg))
        # Basic.csv 失败可能影响其他文件，但此处按顺序继续尝试生成其他文件

        # 生成 His.csv
        logger.info("开始生成 His.csv...")
        his_success, his_file_path, his_err_msg = self.generate_his_csv(output_dir, points_by_sheet)
        results.append(("His.csv", his_success, his_file_path, his_err_msg))

        # 生成 Link.csv
        logger.info("开始生成 Link.csv...")
        link_success, link_file_path, link_err_msg = self.generate_link_csv(output_dir, points_by_sheet)
        results.append(("Link.csv", link_success, link_file_path, link_err_msg))
        
        # 未来可以扩展以生成其他CSV文件，例如 Alm.csv
        
        return results

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
    
    generator = LikongGenerator()
    test_output_dir = os.path.join(os.getcwd(), "test_likong_output_new_model")
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)

    # 示例：构建一些包含量程、报警设定和通讯地址的测试点
    # 注意: UploadedIOPoint 需要有 channel_tag 属性才能正确生成 Link.csv
    points_data_s1_extended: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_01", data_type="REAL", 
                            variable_description="模拟量输入1-正常范围", channel_tag="CH01", hmi_communication_address="40001", # channel_tag 修改为示例，hmi_communication_address 为实际通讯地址
                            range_low_limit="0", range_high_limit="100", 
                            sll_set_value="5", sl_set_value="10", sh_set_value="90", shh_set_value="95"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_02", data_type="REAL", 
                            variable_description="模拟量输入2-低值超范围", channel_tag="CH02", hmi_communication_address="40002",
                            range_low_limit="10", range_high_limit="50", 
                            sll_set_value="5", sl_set_value="8"), # LL, LO会钳位到10
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_03", data_type="REAL", 
                            variable_description="模拟量输入3-高值超范围", channel_tag="CH03", hmi_communication_address="43210",
                            range_low_limit="0", range_high_limit="200", 
                            sh_set_value="210", shh_set_value="220"), # HI, HH会钳位到200
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_04", data_type="REAL", 
                            variable_description="模拟量输入4-量程无效", channel_tag="CH04", hmi_communication_address="40004",
                            range_low_limit="TEXT", range_high_limit="100", 
                            sll_set_value="5"), # 报警不钳位，用默认值
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="AI_Value_05", data_type="REAL", 
                            variable_description="模拟量输入5-报警值无效", channel_tag="CH05", hmi_communication_address="4000A", # 无效数字地址测试
                            range_low_limit="0", range_high_limit="100", 
                            sl_set_value="TEXT"), # LO用默认值10.000
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="DI_Status_01", data_type="BOOL", 
                            variable_description="数字量状态1", channel_tag="CH06", hmi_communication_address="1001"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="DI_NoCommAddr", data_type="BOOL",  # Renamed for clarity
                            variable_description="数字量状态2-无通讯地址", channel_tag="CH07", hmi_communication_address=None), # 测试无通讯地址
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="", data_type="BOOL", 
                            variable_description="数字量状态3-无HMI名称", channel_tag="CH08", hmi_communication_address="1003"), # 测试无HMI名称

        ],
         "第三方设备A": [
            UploadedIOPoint(site_name="TP_设备A", site_number="TPA01", hmi_variable_name="TP_REAL_1", data_type="REAL", 
                            variable_description="第三方实数点1", channel_tag="TP_CH01", hmi_communication_address="40101",
                            range_low_limit="-10", range_high_limit="10", sh_set_value="12") # HI 会被钳位到10
        ]
    }

    logger.info("--- 测试生成所有CSV文件 (Basic, His, Link) --- ")
    # 调用新的总入口
    all_results = generator.generate_all_csvs(
        output_dir=test_output_dir,
        points_by_sheet=points_data_s1_extended
    )

    for file_gen_name, success, file_gen_path, err_msg in all_results: # 变量名修改
        if success:
            print(f"文件 '{file_gen_name}' 生成成功: {file_gen_path}")
        else:
            print(f"文件 '{file_gen_name}' 生成失败: {err_msg}")