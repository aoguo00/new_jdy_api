"""第三方设备点表配置服务"""
import logging
from typing import List, Dict, Any

# DAO 和领域模型
from .database.dao import ConfiguredDeviceDAO
from .models.configured_device_models import ConfiguredDevicePointModel
# from .models.template_models import DeviceTemplateModel # DeviceTemplateModel 仅用于 configure_points_from_template

logger = logging.getLogger(__name__)

class ConfigService:
    """处理第三方设备点表配置的生成、持久化和导出。"""

    def __init__(self, config_dao: ConfiguredDeviceDAO):
        if not config_dao:
            logger.error("ConfigService 初始化失败: 未提供 ConfiguredDeviceDAO 实例。")
            raise ValueError("ConfiguredDeviceDAO 实例是必需的")
        self.config_dao = config_dao
        logger.info("ConfigService 初始化完成。")

    def save_device_configuration(self, template_name: str, variable_prefix: str, description_prefix: str, points_data: List[Dict[str, Any]]) -> tuple[bool, str]:
        """根据UI提供的原始点位数据、模板名称、变量前缀和描述前缀保存设备配置。

        Args:
            template_name (str): 配置所基于的模板名称。
            variable_prefix (str): 用户为这批点位输入的变量前缀。
            description_prefix (str): 用户为这批点位输入的描述前缀。
            points_data (List[Dict[str, Any]]): 来自模板的点位原始数据列表，
                                                每个字典包含 'var_suffix', 'desc_suffix', 'data_type'等。
        Returns:
            tuple[bool, str]: (成功标志, 消息字符串)
        """
        if not template_name:
            msg = "模板名称不能为空。"
            logger.warning(f"保存设备配置失败: {msg}")
            return False, msg
        
        # 前缀现在允许为空，由UI层面或业务需求决定是否强制

        configured_points_to_save: List[ConfiguredDevicePointModel] = []
        for point_raw in points_data:
            try:
                # 假设 ConfiguredDevicePointModel 已更新以接受新前缀
                configured_point = ConfiguredDevicePointModel(
                    template_name=template_name,
                    variable_prefix=variable_prefix,       # 新增/替换
                    description_prefix=description_prefix, # 新增
                    var_suffix=point_raw['var_suffix'],
                    desc_suffix=point_raw.get('desc_suffix', ""),
                    data_type=point_raw['data_type'],
                    sll_setpoint=point_raw.get('sll_setpoint', ""),
                    sl_setpoint=point_raw.get('sl_setpoint', ""),
                    sh_setpoint=point_raw.get('sh_setpoint', ""),
                    shh_setpoint=point_raw.get('shh_setpoint', "")
                )
                configured_points_to_save.append(configured_point)
            except KeyError as ke:
                msg = f"点位数据缺少必要字段: {ke}。数据: {point_raw}"
                logger.error(f"创建ConfiguredDevicePointModel失败: {msg}")
                return False, msg
            
        try:
            # 假设DAO方法更新为 delete_configured_points_by_template_and_prefixes
            logger.info(f"保存配置前，尝试删除旧配置: 模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}'")
            delete_success = self.config_dao.delete_configured_points_by_template_and_prefixes(
                template_name, variable_prefix, description_prefix
            ) # DAO 方法需要修改
            if delete_success:
                logger.info(f"旧配置 (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 删除成功或不存在。")
            else:
                logger.warning(f"删除旧配置 (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 时返回False。")

            if not configured_points_to_save:
                msg = f"模板 '{template_name}' (变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 配置成功（0个点位）。"
                logger.info(msg)
                return True, msg

            success = self.config_dao.save_configured_points(configured_points_to_save)
            if success:
                msg = f"为模板 '{template_name}' (变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 成功配置并保存了 {len(configured_points_to_save)} 个点位。"
                logger.info(msg)
                return True, msg
            else:
                msg = f"保存点位时DAO返回False (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}')。"
                logger.error(msg)
                return False, msg
        except ValueError as ve: 
            logger.warning(f"服务层保存配置点位失败: {ve} - 模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}'")
            return False, str(ve)
        except Exception as e:
            logger.error(f"服务层保存配置点位时发生未知错误: {e} - 模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}'", exc_info=True)
            return False, f"保存点位时发生严重错误: {e}"

    def does_configuration_exist(self, template_name: str, variable_prefix: str, description_prefix: str) -> bool:
        """检查具有指定模板名称、变量前缀和描述前缀的配置是否已在数据库中存在。"""
        # 根据实际需求，前缀是否允许为空字符串，或者是否必须提供，可能影响这里的判断
        # if not template_name: # 模板名通常是必须的
        #     logger.warning("检查配置是否存在请求缺少模板名称。")
        #     return False 
        try:
            # 假设DAO方法更新为接受三个参数
            return self.config_dao.does_configuration_exist(template_name, variable_prefix, description_prefix)
        except Exception as e:
            logger.error(f"服务层检查配置是否存在时发生错误 (模板: '{template_name}', 变量前缀: '{variable_prefix}', 描述前缀: '{description_prefix}'): {e}")
            return False

    def get_all_configured_points(self) -> List[ConfiguredDevicePointModel]:
        """从数据库获取所有已配置的设备点位。"""
        try:
            return self.config_dao.get_all_configured_points()
        except Exception as e:
            logger.error(f"服务层获取所有已配置点位失败: {e}", exc_info=True)
            return []

    def clear_all_configurations(self) -> bool:
        """从数据库删除所有已配置的设备点位。"""
        try:
            return self.config_dao.delete_all_configured_points()
        except Exception as e:
            logger.error(f"服务层清空所有配置失败: {e}", exc_info=True)
            return False

    def delete_device_configuration(self, template_name: str, variable_prefix: str, description_prefix: str) -> bool:
        """根据模板名称、变量前缀和描述前缀删除指定的设备配置及其所有点位。"""
        if not template_name: # 模板名通常是必须的
            logger.warning("删除设备配置请求缺少模板名称。")
            return False
        try:
            logger.info(f"请求删除设备配置: 模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}'")
            # 假设DAO方法更新为 delete_configured_points_by_template_and_prefixes
            success = self.config_dao.delete_configured_points_by_template_and_prefixes(
                template_name, variable_prefix, description_prefix
            ) # DAO 方法需要修改
            if success:
                logger.info(f"设备配置 (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 已成功删除。")
            else:
                logger.warning(f"未能删除设备配置 (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}')。")
            return success
        except Exception as e:
            logger.error(f"服务层删除设备配置 (模板='{template_name}', 变量前缀='{variable_prefix}', 描述前缀='{description_prefix}') 时发生错误: {e}", exc_info=True)
            return False

    def get_configuration_summary(self) -> List[Dict]:
        """获取配置摘要信息 (用于UI显示)。"""
        try:
            raw_summary = self.config_dao.get_configuration_summary_raw() # DAO方法可能需要调整返回的列
            
            summary_list = []
            for row in raw_summary:
                # 假设 raw_summary 返回的字典中键已更新为 variable_prefix 和 description_prefix
                summary_list.append({
                    'template': row['template_name'],
                    'variable_prefix': row.get('variable_prefix', ''), # 兼容旧数据或不同DAO实现
                    'description_prefix': row.get('description_prefix', ''), # 新增
                    'count': row['point_count'],
                    'status': "已配置"
                })
            return summary_list
        except Exception as e:
            logger.error(f"服务层获取配置摘要失败: {e}", exc_info=True)
            return []

    def get_configured_points_by_template_and_prefix(self, template_name: str, variable_prefix: str, description_prefix: str) -> List[Dict]:
        """
        获取特定模板名称、变量前缀和描述前缀的所有配置点位。

        Args:
            template_name (str): 模板名称
            variable_prefix (str): 变量前缀
            description_prefix (str): 描述前缀

        Returns:
            List[Dict]: 配置点位列表，每个点位包含变量后缀等信息
        """
        try:
            # 调用DAO方法获取配置点位
            configured_points = self.config_dao.get_configured_points_by_template_and_prefixes(
                template_name, variable_prefix, description_prefix
            )
            
            # 将模型对象转换为字典列表，方便UI使用
            result = []
            for point in configured_points:
                # 使用模型的计算属性获取完整描述
                full_description = point.description
                
                result.append({
                    'var_suffix': point.var_suffix,
                    'desc_suffix': point.desc_suffix,
                    'data_type': point.data_type,
                    'sll_setpoint': point.sll_setpoint,
                    'sl_setpoint': point.sl_setpoint,
                    'sh_setpoint': point.sh_setpoint,
                    'shh_setpoint': point.shh_setpoint,
                    'full_description': full_description  # 添加完整描述字段
                })
            return result
        except Exception as e:
            logger.error(f"获取配置点位失败 (模板: '{template_name}', 变量前缀: '{variable_prefix}', 描述前缀: '{description_prefix}'): {e}", exc_info=True)
            return []
