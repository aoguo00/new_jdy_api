"""点位管理模块，处理点位相关的业务逻辑"""


class PointManager:
    """点位管理类，负责点位相关的业务逻辑"""

    def __init__(self):
        """初始化点位管理器"""
        pass

    def generate_points_from_template(self, template, prefix, include_metadata=True):
        """根据模板和前缀生成点位列表

        Args:
            template: 模板数据
            prefix: 变量名前缀
            include_metadata: 是否包含元数据（模板名称和变量名后缀）

        Returns:
            点位列表
        """
        if not template or '点位' not in template:
            return []

        points = []
        for point in template['点位']:
            var_suffix = point['变量名后缀']
            desc_suffix = point['描述后缀']
            data_type = point['类型']

            point_data = {
                '变量名': f"{prefix}_{var_suffix}",
                '描述': desc_suffix,
                '数据类型': data_type
            }

            # 如果需要包含元数据
            if include_metadata:
                point_data.update({
                    '模板名称': template['name'],
                    '变量名后缀': var_suffix
                })

            points.append(point_data)

        return points

    def generate_points_preview(self, template, prefix):
        """生成点位预览数据（不包含元数据）"""
        return self.generate_points_from_template(template, prefix, include_metadata=False)
