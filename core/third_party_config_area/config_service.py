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

    def save_device_configuration(self, template_name: str, device_prefix: str, points_data: List[Dict[str, Any]]) -> tuple[bool, str]:
        """根据UI提供的原始点位数据、模板名称和设备前缀保存设备配置。

        Args:
            template_name (str): 配置所基于的模板名称。
            device_prefix (str): 用户为这批点位输入的设备前缀。
            points_data (List[Dict[str, Any]]): 来自模板的点位原始数据列表，
                                                每个字典包含 'var_suffix', 'desc_suffix', 'data_type'。
        Returns:
            tuple[bool, str]: (成功标志, 消息字符串)
        """
        if not template_name:
            msg = "模板名称不能为空。"
            logger.warning(f"保存设备配置失败: {msg}")
            return False, msg
        # if not device_prefix: # 允许设备前缀为空，移除此校验
        #     msg = "设备前缀不能为空。"
        #     logger.warning(f"保存设备配置失败: {msg}")
        #     return False, msg 
        
        # DevicePointDialog 应该已经处理了空点位列表的确认逻辑。
        # 此处不再需要对 points_data 为空的初步日志记录或特殊处理，
        # 因为后续的 configured_points_to_save 列表如果为空，
        # 会在删除旧配置后正确地返回一个表示"成功配置0个点位"的结果。
        # 移除以下代码块：
        # if not points_data:
        #     logger.info(f"为模板 '{template_name}' 和前缀 '{device_prefix}' 保存空配置（0个点位）。")
            # ... (各种注释和pass)

        configured_points_to_save: List[ConfiguredDevicePointModel] = []
        for point_raw in points_data:
            try:
                configured_point = ConfiguredDevicePointModel(
                    template_name=template_name, 
                    device_prefix=device_prefix,
                    var_suffix=point_raw['var_suffix'],
                    desc_suffix=point_raw.get('desc_suffix', ""), # desc_suffix 可能为空
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
            # 在调用DAO之前，应该先删除该 template_name 和 device_prefix 的旧配置
            # 这是一个"覆盖保存"的逻辑
            logger.info(f"保存配置前，尝试删除旧配置: 模板='{template_name}', 前缀='{device_prefix}'")
            delete_success = self.config_dao.delete_configured_points_by_template_and_prefix(template_name, device_prefix)
            if delete_success:
                logger.info(f"旧配置 (模板='{template_name}', 前缀='{device_prefix}') 删除成功或不存在。")
            else:
                # 如果删除失败，可能不是关键错误，除非有特定要求。这里只记录日志。
                logger.warning(f"删除旧配置 (模板='{template_name}', 前缀='{device_prefix}') 时返回False，可能影响覆盖逻辑。")

            if not configured_points_to_save: # 如果处理后没有点位（例如模板为空，用户仍确认）
                msg = f"模板 '{template_name}' (前缀 '{device_prefix}') 配置成功（0个点位）。"
                logger.info(msg)
                return True, msg # 认为成功配置了一个"空"设备实例

            success = self.config_dao.save_configured_points(configured_points_to_save)
            if success:
                msg = f"为模板 '{template_name}' 和前缀 '{device_prefix}' 成功配置并保存了 {len(configured_points_to_save)} 个点位。"
                logger.info(msg)
                return True, msg
            else:
                msg = f"保存点位时DAO返回False (模板='{template_name}', 前缀='{device_prefix}')。"
                logger.error(msg)
                return False, msg
        except ValueError as ve: 
            logger.warning(f"服务层保存配置点位失败 (可能是变量名/唯一约束冲突): {ve} - 模板='{template_name}', 前缀='{device_prefix}'")
            return False, str(ve)
        except Exception as e:
            logger.error(f"服务层保存配置点位时发生未知错误: {e} - 模板='{template_name}', 前缀='{device_prefix}'", exc_info=True)
            return False, f"保存点位时发生严重错误: {e}"

    def does_configuration_exist(self, template_name: str, device_prefix: str) -> bool:
        """检查具有指定模板名称和设备前缀的配置是否已在数据库中存在。"""
        if not template_name or not device_prefix:
            logger.warning("检查配置是否存在请求缺少模板名称或设备前缀。")
            return False # 或者抛出ValueError，因为这是不正常的调用
        try:
            return self.config_dao.does_configuration_exist(template_name, device_prefix)
        except Exception as e:
            # DAO层面已记录具体错误，服务层可只记录调用失败
            logger.error(f"服务层检查配置是否存在时发生错误 (模板: '{template_name}', 前缀: '{device_prefix}'): {e}")
            return False # 保守返回False

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

    def delete_device_configuration(self, template_name: str, device_prefix: str) -> bool:
        """根据模板名称和设备前缀删除指定的设备配置及其所有点位。"""
        if not template_name or not device_prefix:
            logger.warning("删除设备配置请求缺少模板名称或设备前缀。")
            return False
        try:
            logger.info(f"请求删除设备配置: 模板='{template_name}', 前缀='{device_prefix}'")
            success = self.config_dao.delete_configured_points_by_template_and_prefix(template_name, device_prefix)
            if success:
                logger.info(f"设备配置 (模板='{template_name}', 前缀='{device_prefix}') 已成功删除。")
            else:
                logger.warning(f"未能删除设备配置 (模板='{template_name}', 前缀='{device_prefix}')，可能配置不存在或删除失败。")
            return success
        except Exception as e:
            logger.error(f"服务层删除设备配置 (模板='{template_name}', 前缀='{device_prefix}') 时发生错误: {e}", exc_info=True)
            return False

    def get_configuration_summary(self) -> List[Dict]:
        """获取配置摘要信息 (用于UI显示)。"""
        try:
            # 从DAO获取原始分组数据
            raw_summary = self.config_dao.get_configuration_summary_raw()
            
            # 格式化为UI需要的结构
            summary_list = []
            for row in raw_summary:
                summary_list.append({
                    'template': row['template_name'],
                    'variable': row['device_prefix'], # UI中使用'variable'作为键
                    'count': row['point_count'],
                    'status': "已配置" # 状态总是"已配置"
                })
            return summary_list
        except Exception as e:
            logger.error(f"服务层获取配置摘要失败: {e}", exc_info=True)
            return []
