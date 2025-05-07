from typing import List, Dict
from core.models.third_party_devices.models import ThirdPartyConfiguredPointModel
from core.models.templates.models import DeviceTemplateModel

class DeviceConfigurationService:
    def __init__(self):
        self._configured_points: List[ThirdPartyConfiguredPointModel] = []

    def add_configured_points(self, template: DeviceTemplateModel, device_prefix: str) -> List[ThirdPartyConfiguredPointModel]:
        newly_added_points = []
        for point_model in template.points:
            configured_point = ThirdPartyConfiguredPointModel(
                template_name=template.name,
                device_prefix=device_prefix,
                var_suffix=point_model.var_suffix,
                desc_suffix=point_model.desc_suffix,
                data_type=point_model.data_type
            )
            self._configured_points.append(configured_point)
            newly_added_points.append(configured_point)
        return newly_added_points

    def get_all_configured_points(self) -> List[ThirdPartyConfiguredPointModel]:
        return self._configured_points

    def clear_all_configurations(self) -> None:
        self._configured_points = []

    def get_configuration_summary(self) -> List[Dict]:
        if not self._configured_points:
            return []
        summary_map: Dict[tuple[str, str], int] = {}
        for point in self._configured_points:
            key = (point.template_name, point.device_prefix)
            summary_map[key] = summary_map.get(key, 0) + 1
        summary_list = []
        for (template_name, device_prefix), count in summary_map.items():
            summary_list.append({
                'template': template_name,
                'variable': device_prefix, 
                'count': count,
                'status': "已配置" 
            })
        return summary_list

    def export_to_excel(self, file_path: str) -> None:
        from openpyxl import Workbook
        if not self._configured_points:
            raise ValueError("没有可导出的点位数据")
            
        grouped_points_by_template: Dict[str, List[ThirdPartyConfiguredPointModel]] = {}
        for point in self._configured_points:
            template_name = point.template_name
            if template_name not in grouped_points_by_template:
                grouped_points_by_template[template_name] = []
            grouped_points_by_template[template_name].append(point)
            
        wb = Workbook()
        wb.remove(wb.active) 
        
        for template_name, points_list in grouped_points_by_template.items():
            sheet_title = template_name[:31]
            ws = wb.create_sheet(title=sheet_title)
            ws.append(["变量名", "描述", "数据类型"]) 
            for point in points_list:
                ws.append([
                    point.variable_name,
                    point.description,
                    point.data_type
                ])
            for column_cells in ws.columns:
                max_length = 0
                column = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column].width = adjusted_width
                
        wb.save(file_path) 