"""第三方设备管理模块，处理第三方设备相关的业务逻辑"""
import logging
from core.third_device import template_db

logger = logging.getLogger(__name__)

class ThirdPartyDeviceManager:
    """第三方设备管理类，负责第三方设备相关的业务逻辑"""

    def __init__(self):
        """初始化第三方设备管理器"""
        self.device_points = []
        try:
            # 确保模板数据库已初始化
            template_db.init_db()
        except Exception as e:
            logger.error(f"初始化模板数据库失败: {e}")
            raise RuntimeError("初始化第三方设备管理器失败，请检查数据库连接") from e

    def get_device_points(self):
        """获取设备点位列表"""
        return self.device_points

    def set_device_points(self, points):
        """设置设备点位列表（替换现有点位）"""
        if not isinstance(points, list):
            raise ValueError("点位数据必须是列表格式")
        self.device_points = points

    def add_device_points(self, points):
        """添加设备点位（追加到现有点位）"""
        if not isinstance(points, list):
            raise ValueError("点位数据必须是列表格式")
        self.device_points.extend(points)

    def clear_device_points(self):
        """清空设备点位列表"""
        self.device_points = []

    def update_third_party_table_data(self):
        """获取第三方设备表格数据"""
        if not self.device_points:
            return []

        # 按模板名称和变量前缀分组统计点位
        template_stats = {}
        for point in self.device_points:
            try:
                template_name = point.get('模板名称')
                var_name = point.get('变量名')
                
                if not template_name or not var_name:
                    logger.warning(f"点位数据不完整: {point}")
                    continue
                    
                var_parts = var_name.split('_')
                if len(var_parts) < 2:
                    logger.warning(f"变量名格式不正确: {var_name}")
                    continue
                    
                prefix = var_parts[0]  # 获取变量名前缀
                
                # 按模板名称分组
                if template_name not in template_stats:
                    template_stats[template_name] = {}
                    
                # 在模板内按变量前缀分组
                if prefix not in template_stats[template_name]:
                    template_stats[template_name][prefix] = 0
                template_stats[template_name][prefix] += 1
                
            except Exception as e:
                logger.error(f"处理点位时发生错误: {e}, 点位数据: {point}")
                continue

        # 构建表格数据
        table_data = []
        for template_name, prefixes in template_stats.items():
            for prefix, count in prefixes.items():
                table_data.append({
                    'template': template_name,
                    'variable': prefix,
                    'count': count,
                    'status': "已配置"
                })

        return table_data

    def get_template_name_by_suffix(self, suffix):
        """根据变量名后缀获取模板名称"""
        try:
            # 首先从已配置的点位中查找匹配的后缀
            for point in self.device_points:
                if point.get('变量名后缀') == suffix and '模板名称' in point:
                    return point['模板名称']

            # 如果在已配置点位中没找到，从模板库中查找
            templates = template_db.get_all_templates()
            for template in templates:
                template_points = template_db.get_template(template['name'])
                if not template_points or '点位' not in template_points:
                    continue

                # 检查每个点位的变量名后缀
                for point in template_points['点位']:
                    if point.get('变量名后缀', '') == suffix:
                        return template['name']

            # 如果都没找到，返回未知模板
            return "未知模板"

        except Exception as e:
            logger.error(f"获取模板名称时发生错误: {e}, 后缀: {suffix}")
            return "未知模板"

    def export_to_excel(self, file_path):
        """导出点表为Excel格式，按模板类型分工作簿"""
        from openpyxl import Workbook

        # 按模板类型分组点位
        template_groups = {}
        for point in self.device_points:
            template_name = point.get('模板名称', '未知模板')
            if template_name not in template_groups:
                template_groups[template_name] = []
            template_groups[template_name].append(point)

        # 创建Excel工作簿
        wb = Workbook()
        # 删除默认的Sheet
        default_sheet = wb.active
        wb.remove(default_sheet)

        # 为每个模板类型创建工作表
        for template_name, points in template_groups.items():
            # 创建工作表，名称为模板名称
            ws = wb.create_sheet(title=template_name)

            # 添加表头
            ws.append(["变量名", "描述", "数据类型"])

            # 添加数据
            for point in points:
                ws.append([
                    point['变量名'],
                    point['描述'],
                    point['数据类型']
                ])

            # 调整列宽
            for column in ws.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                adjusted_width = (max_length + 2) * 1.2
                ws.column_dimensions[column_letter].width = adjusted_width

        # 保存Excel文件
        wb.save(file_path)
