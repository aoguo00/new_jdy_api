import os
from typing import List
from openpyxl import Workbook
from .uploaded_file_processor.io_data_model import UploadedIOPoint


def generate_communication_table_excel(output_path: str, io_points: List[UploadedIOPoint]) -> bool:
    """
    生成上下位通讯点表Excel文件。
    第一列是序号，第二列是 "过程控制"，其数据来自 io_points 中的 hmi_variable_name。
    :param output_path: 输出文件的完整路径
    :param io_points: 从IO点表解析出的 UploadedIOPoint 对象列表
    :return: 是否生成成功
    """
    # 表头字段，按截图顺序
    headers: List[str] = [
        "序号", "过程控制", "检测点名称", "信号范围", "数据范围", "单位", "信号类型", "供电", "备注"
    ]
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "上下位通讯点表"
        ws.append(headers)

        # Filter for actual hardware IO points
        # We need points that are from the main IO sheet and are of type AI, AO, DI, or DO.
        hard_io_points = [
            p for p in io_points
            if p and p.source_type == "main_io" and p.module_type in ["AI", "AO", "DI", "DO"]
        ]

        # 填充数据
        for index, point in enumerate(hard_io_points):
            serial_number = index + 1
            process_control_value = point.hmi_variable_name if point.hmi_variable_name else ""
            detection_point_name = point.variable_description if point.variable_description else ""

            signal_range_value = ""
            data_range_value = ""

            if point.module_type in ["AI", "AO"]:
                signal_range_value = "4~20mA"
                
                # Handle Data Range for AI/AO
                low_limit = point.range_low_limit
                high_limit = point.range_high_limit
                
                if low_limit is not None and str(low_limit).strip() != "" and \
                   high_limit is not None and str(high_limit).strip() != "":
                    data_range_value = f"{str(low_limit).strip()}~{str(high_limit).strip()}"
                elif low_limit is not None and str(low_limit).strip() != "":
                    data_range_value = str(low_limit).strip()
                elif high_limit is not None and str(high_limit).strip() != "":
                    data_range_value = str(high_limit).strip()

            row_data = [
                serial_number,
                process_control_value,
                detection_point_name,
                signal_range_value,  # 信号范围
                data_range_value,    # 数据范围
                "",  # 单位
                point.module_type if point and point.module_type else "",  # 信号类型
                point.power_supply_type if point and point.power_supply_type else "",  # 供电
                ""   # 备注
            ]
            ws.append(row_data)
        
        wb.save(output_path)
        return True
    except Exception as e:
        print(f"生成上下位通讯点表失败: {e}")
        return False

# 中文注释：
# 1. 该函数会在指定路径生成一个Excel文件，sheet名为"上下位通讯点表"。
# 2. 第一列为自动递增的序号。
# 3. 第二列 "过程控制" 来自传入的 io_points 列表中的 hmi_variable_name 属性。
# 4. 其他列暂时留空，后续可以扩展内容写入逻辑。 