"""力控点表生成器模块"""
import csv # 导入 csv 模块
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

    def __init__(self):
        """初始化力控生成器"""
        pass

    def generate_basic_csv(self,
                           output_dir: str,
                           points_by_sheet: Dict[str, List[UploadedIOPoint]]
                           ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        生成力控点表的CSV文件: Basic.csv
        该文件包含预定义的TagType结构、表头，并根据输入数据填充点位信息。
        文件编码为 GBK。
        """
        main_io_sheet_key = MAIN_IO_SHEET_NAME_DEFAULT
        file_name = "Basic.csv"
        file_path = os.path.join(output_dir, file_name)

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
        
        if not default_site_name and not default_site_number:
            logger.warning(f"力控 Basic.csv: 未能在主IO表 '{main_io_sheet_key}' 中找到有效的全局默认场站名或场站编号。")
        else:
            logger.info(f"力控 Basic.csv: 使用全局默认场站名='{default_site_name}', 场站编号='{default_site_number}' (如果点位自身无特定信息)")

        real_points: List[UploadedIOPoint] = []
        bool_points: List[UploadedIOPoint] = []

        if points_by_sheet:
            for _, points_list in points_by_sheet.items():
                for point in points_list:
                    point_data_type_upper = str(point.data_type or "").upper().strip()
                    hmi_name_from_point = str(point.hmi_variable_name or "").strip()

                    if _is_value_empty_for_hmi(hmi_name_from_point):
                        logger.warning(f"点 (类型:'{point_data_type_upper}', 通道:'{point.channel_tag}') HMI名称为空或无效，跳过。")
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
                        
                        row_data['NodePath'] = f"{current_point_site_name}\\\\" if current_point_site_name else ""
                        row_data['NAME'] = f"{current_point_site_number}{point.hmi_variable_name.strip()}"
                        row_data['DESC'] = point.variable_description or ""
                        row_data['FORMAT'] = "3" 
                        row_data['LASTPV'] = "0.000"
                        row_data['PV'] = "0.000"
                        row_data['EU'] = "" 
                        logger.debug(f"点 '{row_data['NAME']}' 的 EU (工程单位) 因 UploadedIOPoint 中无对应属性而置空。")
                        
                        row_data['EULO'] = str(point.range_low_limit) if point.range_low_limit is not None and point.range_low_limit.strip() else "0.000" 
                        row_data['EUHI'] = str(point.range_high_limit) if point.range_high_limit is not None and point.range_high_limit.strip() else "100.000"
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
                            row_data['ALMENAB'] = "1" # 只要有一个报警值，就使能报警
                        else:
                            row_data['ALMENAB'] = "0" # 所有报警值都为空，则禁止报警
                            
                        row_data['DEADBAND'] = "0.000" 
                        
                        row_data['LL'] = str(point.sll_set_value) if has_sll else "8.000" 
                        row_data['LO'] = str(point.sl_set_value) if has_sl else "10.000"
                        row_data['HI'] = str(point.sh_set_value) if has_sh else "92.000"
                        row_data['HH'] = str(point.shh_set_value) if has_shh else "94.000"
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

                        row_data['NodePath'] = f"{current_point_site_name}\\\\" if current_point_site_name else ""
                        hmi_name = point.hmi_variable_name.strip() if point.hmi_variable_name else ""
                        row_data['NAME'] = f"{current_point_site_number}{hmi_name}"
                        row_data['DESC'] = point.variable_description or ""
                        
                        is_maintenance_switch = hmi_name.endswith("_whzzt")

                        if is_maintenance_switch:
                            row_data['PV'] = "0"
                            row_data['ALMENAB'] = "0"
                            row_data['ALARMPR'] = "0"
                            logger.debug(f"数字点 '{hmi_name}' 是维护值开关 (_whzzt)，PV设为0, ALMENAB设为0, ALARMPR设为0。")
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
                                                    logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 的 '{raw_value_attr_name}' ('{raw_alarm_value_from_excel_str}') 与通用默认值相同，ALMENAB保持为0。")
                                                else:
                                                    current_digital_almenab = "1" # 只有这种情况才使能
                                                    logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 的 '{raw_value_attr_name}' ('{raw_alarm_value_from_excel_str}') 已设定且非默认，ALMENAB设为1。")
                                            else:
                                                # current_digital_almenab 保持 "0"
                                                logger.debug(f"数字报警点 '{hmi_name}' 的父模拟量点 '{parent_hmi_name}' 未设定 '{raw_value_attr_name}'，ALMENAB保持为0。")
                                        else:
                                            # current_digital_almenab 保持 "0"
                                            logger.warning(f"派生数字报警点 '{hmi_name}' 未能找到父模拟量点 '{parent_hmi_name}'，ALMENAB保持为0。")
                                        break 
                            
                            # 如果不是已识别并成功处理的派生报警类型，ALMENAB 会是初始的 "0"
                            if not is_derived_analog_alarm_point and not is_maintenance_switch: #确保维护开关的逻辑不被覆盖
                                 logger.debug(f"数字点 '{hmi_name}' 非特定派生报警类型或未成功关联，ALMENAB设为0。")
                                 # current_digital_almenab 已经是 "0"

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
            UploadedIOPoint(data_type="FLOAT", hmi_variable_name="NoSiteInfoPoint", source_type="main_io", variable_description="无信息模拟量") # 无场站信息的点, 添加描述
        ],
        "第三方设备A": [
            UploadedIOPoint(site_name="TP_设备A", site_number="TPA01", hmi_variable_name="TP_REAL_1", data_type="REAL", source_type="third_party", variable_description="第三方实数点1"),
            UploadedIOPoint(site_name="TP_设备A", site_number="TPA01", hmi_variable_name="TP_BOOL_1", data_type="BOOL", source_type="third_party", variable_description="第三方布尔点1"),
            UploadedIOPoint(hmi_variable_name="TP_NoSite_REAL", data_type="REAL", source_type="third_party", variable_description="第三方无场站模拟量") # 第三方无场站信息, 添加描述
        ],
        "空Sheet": [],
        "只有无效类型的Sheet": [
            UploadedIOPoint(hmi_variable_name="BadTypePoint", data_type="STRING", source_type="main_io", variable_description="无效类型点")
        ]
    }

    logger.info("--- 测试场景1: 完整数据 ---")
    success1, file_path1, err_msg1 = generator.generate_basic_csv( # 修改调用
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
    success2, file_path2, err_msg2 = generator.generate_basic_csv( # 修改调用
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
    success3, file_path3, err_msg3 = generator.generate_basic_csv( # 修改调用
        output_dir=test_output_dir,
        points_by_sheet=points_data_s3
    )
    if success3: print(f"场景3成功: {file_path3}")
    else: print(f"场景3失败: {err_msg3}")
    
    # --- 场景4: 输入数据为空字典 ---
    points_data_s4: Dict[str, List[UploadedIOPoint]] = {}
    logger.info("--- 测试场景4: 输入数据为空字典 ---")
    success4, file_path4, err_msg4 = generator.generate_basic_csv( # 修改调用
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
    success5, file_path5, err_msg5 = generator.generate_basic_csv( # 修改调用
        output_dir=test_output_dir,
        points_by_sheet=points_data_s5
    )
    if success5: print(f"场景5成功: {file_path5}")
    else: print(f"场景5失败: {err_msg5}")
    
    # --- 场景6: 点位数据类型不匹配 (REAL/BOOL之外) ---
    points_data_s6: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="INT_Value_01", data_type="INT", source_type="main_io", variable_description="整型点"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="STR_Value_01", data_type="STRING", source_type="main_io", variable_description="字符串点")
        ]
    }
    logger.info("--- 测试场景6: 数据类型不匹配 ---")
    success6, file_path6, err_msg6 = generator.generate_basic_csv( # 修改调用
        output_dir=test_output_dir,
        points_by_sheet=points_data_s6
    )
    if success6: print(f"场景6成功 (预期不写入点): {file_path6}") # 应该生成空文件但操作成功
    else: print(f"场景6失败: {err_msg6}")

    # --- 场景7: HMI名称为空的点 ---
    points_data_s7: Dict[str, List[UploadedIOPoint]] = {
        "IO点表": [
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name=None, data_type="REAL", source_type="main_io", variable_description="HMI名为空模拟量"),
            UploadedIOPoint(site_name="LK测试站", site_number="LKS01", hmi_variable_name="  ", data_type="BOOL", source_type="main_io", variable_description="HMI名为空格布尔量")
        ]
    }
    logger.info("--- 测试场景7: HMI名称为空 ---")
    success7, file_path7, err_msg7 = generator.generate_basic_csv( # 修改调用
        output_dir=test_output_dir,
        points_by_sheet=points_data_s7
    )
    if success7: print(f"场景7成功 (预期不写入点): {file_path7}")
    else: print(f"场景7失败: {err_msg7}")