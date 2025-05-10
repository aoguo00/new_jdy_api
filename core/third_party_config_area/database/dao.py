# core/third_party_config_area/database/dao.py
"""数据访问对象 (DAO)，封装数据库交互"""
import logging
import sqlite3
from typing import Optional, List, Dict, Any

# from core.database.database_service import DatabaseService # For string type hint 'DatabaseService'

# 本地 SQL 定义
from .sql import TEMPLATE_SQL, CONFIGURED_DEVICE_SQL
# 本地模型定义
from ..models.template_models import DeviceTemplateModel, TemplatePointModel
from ..models.configured_device_models import ConfiguredDevicePointModel

logger = logging.getLogger(__name__)

# --- Template DAO --- 
class TemplateDAO:
    """设备模板DAO，封装模板和点位的数据库交互。"""

    def __init__(self, db_service: 'DatabaseService'): # Use new type hint
        self.db_service = db_service # Use new attribute name
        logger.info("TemplateDAO 初始化完成，使用 DatabaseService。")

    # --- 辅助转换方法 (保持不变, 内部不直接引用 db_service) ---
    def _row_to_template_model(self, row: Optional[Dict[str, Any]], points: List[TemplatePointModel] = None) -> Optional[DeviceTemplateModel]:
        if not row: return None
        try: 
            model = DeviceTemplateModel.model_validate(row, from_attributes=True)
            model.points = points or [] # Assign points after validation
            return model
        except Exception as e: 
            logger.error(f"数据库行转换为DeviceTemplateModel失败: {row}, 错误: {e}", exc_info=True)
            return None

    def _rows_to_template_list(self, rows: List[Dict[str, Any]]) -> List[DeviceTemplateModel]:
        return [model for model in (self._row_to_template_model(row) for row in rows) if model is not None]

    def _row_to_point_model(self, row: Optional[Dict[str, Any]]) -> Optional[TemplatePointModel]:
        if not row: return None
        try: 
            return TemplatePointModel.model_validate(row, from_attributes=True)
        except Exception as e: 
            logger.error(f"数据库行转换为TemplatePointModel失败: {row}, 错误: {e}", exc_info=True)
            return None

    def _rows_to_point_list(self, rows: List[Dict[str, Any]]) -> List[TemplatePointModel]:
        return [model for model in (self._row_to_point_model(row) for row in rows) if model is not None]

    # --- 模板操作 (更新对 db_service 的调用) --- 
    def create_template_with_points(self, template_data: DeviceTemplateModel) -> Optional[DeviceTemplateModel]:
        """创建模板及其点位（事务性操作，已移除模板前缀处理）。"""
        try:
            with self.db_service.transaction() as cursor:
                sql_tmpl = TEMPLATE_SQL['INSERT_TEMPLATE']
                # prefix 不再从 template_data 获取，SQL语句也已修改
                params_tmpl = (template_data.name,)
                cursor.execute(sql_tmpl, params_tmpl)
                template_id = cursor.lastrowid
                if not template_id:
                    raise Exception("创建模板后未能获取 template_id")
                
                if template_data.points:
                    sql_point = TEMPLATE_SQL['INSERT_POINT']
                    point_params_list = [
                        (template_id, p.var_suffix, p.desc_suffix, p.data_type,
                         p.sll_setpoint, p.sl_setpoint, p.sh_setpoint, p.shh_setpoint)
                        for p in template_data.points
                    ]
                    cursor.executemany(sql_point, point_params_list)
                
            logger.info(f"模板 '{template_data.name}' 及 {len(template_data.points)} 个点位创建成功，ID: {template_id}")
            return self.get_template_by_id(template_id)
        
        except sqlite3.IntegrityError as ie:
            if "UNIQUE constraint failed: third_device_templates.name" in str(ie):
                logger.warning(f"创建模板失败：名称 '{template_data.name}' 已存在。")
                raise ValueError(f"模板名称 '{template_data.name}' 已存在。") from ie
            else:
                logger.error(f"创建模板 '{template_data.name}' 时发生数据库完整性错误: {ie}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"创建模板 '{template_data.name}' 时发生未知错误: {e}", exc_info=True)
            raise

    def get_template_by_id(self, template_id: int) -> Optional[DeviceTemplateModel]:
        """根据ID获取模板（包含点位）。"""
        sql = TEMPLATE_SQL['GET_TEMPLATE_BY_ID']
        try:
            template_row = self.db_service.fetch_one(sql, (template_id,)) # Use db_service
            if not template_row:
                return None
            points = self.get_points_by_template_id(template_id)
            model = DeviceTemplateModel.model_validate(template_row, from_attributes=True)
            model.points = points
            return model
        except Exception as e:
            logger.error(f"通过ID获取模板 {template_id} 失败: {e}", exc_info=True)
            return None # Or re-raise

    def get_template_by_name(self, name: str) -> Optional[DeviceTemplateModel]:
        """根据名称获取模板（包含点位）。"""
        sql = TEMPLATE_SQL['GET_TEMPLATE_BY_NAME']
        try:
            template_row = self.db_service.fetch_one(sql, (name,)) # Use db_service
            if not template_row:
                return None
            points = self.get_points_by_template_id(template_row['id'])
            model = DeviceTemplateModel.model_validate(template_row, from_attributes=True)
            model.points = points
            return model
        except Exception as e:
            logger.error(f"通过名称 '{name}' 获取模板失败: {e}", exc_info=True)
            return None

    def get_all_templates(self) -> List[DeviceTemplateModel]:
        """获取所有模板的基本信息（不含点位）。"""
        sql = TEMPLATE_SQL['GET_ALL_TEMPLATES']
        try:
            rows = self.db_service.fetch_all(sql) # Use db_service
            return [DeviceTemplateModel.model_validate(row, from_attributes=True) for row in rows]
        except Exception as e:
            logger.error(f"获取所有模板失败: {e}", exc_info=True)
            return []

    def update_template_with_points(self, template_id: int, template_data: DeviceTemplateModel) -> Optional[DeviceTemplateModel]:
        """更新模板及其点位（事务性操作，已移除模板前缀处理）。"""
        try:
            with self.db_service.transaction() as cursor:
                sql_tmpl = TEMPLATE_SQL['UPDATE_TEMPLATE']
                # prefix 不再从 template_data 获取，SQL语句也已修改
                params_tmpl = (template_data.name, template_id)
                cursor.execute(sql_tmpl, params_tmpl)
                if cursor.rowcount == 0:
                    logger.warning(f"更新模板失败：未找到ID为 {template_id} 的模板。")
                    return None

                sql_del_points = TEMPLATE_SQL['DELETE_POINTS_BY_TEMPLATE_ID']
                cursor.execute(sql_del_points, (template_id,))

                if template_data.points:
                    sql_point = TEMPLATE_SQL['INSERT_POINT']
                    point_params_list = [
                        (template_id, p.var_suffix, p.desc_suffix, p.data_type,
                         p.sll_setpoint, p.sl_setpoint, p.sh_setpoint, p.shh_setpoint)
                        for p in template_data.points
                    ]
                    cursor.executemany(sql_point, point_params_list)

            logger.info(f"模板 ID {template_id} 更新成功。")
            return self.get_template_by_id(template_id)
        except sqlite3.IntegrityError as ie:
            if "UNIQUE constraint failed" in str(ie):
                logger.warning(f"更新模板失败：名称 '{template_data.name}' 已被其他模板使用。")
                raise ValueError(f"模板名称 '{template_data.name}' 已被其他模板使用。") from ie
            else:
                logger.error(f"更新模板 ID {template_id} 时发生数据库完整性错误: {ie}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"更新模板 ID {template_id} 时发生未知错误: {e}", exc_info=True)
            raise

    def delete_template(self, template_id: int) -> bool:
        """删除模板。"""
        sql = TEMPLATE_SQL['DELETE_TEMPLATE']
        try:
            # DatabaseService.execute returns a cursor, check its rowcount
            cursor = self.db_service.execute(sql, (template_id,)) # Use db_service
            if cursor and cursor.rowcount > 0:
                logger.info(f"模板 ID {template_id} 已删除。")
                return True
            logger.warning(f"删除模板 ID {template_id} 失败或未找到该模板 (受影响行数: {cursor.rowcount if cursor else 'N/A'})。")
            return False
        except Exception as e:
            logger.error(f"删除模板 ID {template_id} 失败: {e}", exc_info=True)
            return False

    def get_points_by_template_id(self, template_id: int) -> List[TemplatePointModel]:
        """获取指定模板ID的所有点位。"""
        sql = TEMPLATE_SQL['GET_POINTS_BY_TEMPLATE_ID']
        try:
            rows = self.db_service.fetch_all(sql, (template_id,)) # Use db_service
            return self._rows_to_point_list(rows)
        except Exception as e:
            logger.error(f"获取模板ID {template_id} 的点位失败: {e}", exc_info=True)
            return []

# --- Configured Device DAO --- 
class ConfiguredDeviceDAO:
    """已配置设备点表DAO，封装数据库交互。"""
    def __init__(self, db_service: 'DatabaseService'): # Use new type hint
        self.db_service = db_service # Use new attribute name
        logger.info("ConfiguredDeviceDAO 初始化完成，使用 DatabaseService。")

    def save_configured_points(self, points: List[ConfiguredDevicePointModel]) -> bool:
        """批量保存已配置的设备点位。如果发生唯一性约束冲突，则抛出ValueError。"""
        if not points:
            return True 
        
        sql = CONFIGURED_DEVICE_SQL['INSERT_CONFIGURED_POINTS_BATCH']
        params_list = [
            (p.template_name, p.variable_prefix, p.description_prefix, 
             p.var_suffix, p.desc_suffix, p.data_type,
             p.sll_setpoint, p.sl_setpoint, p.sh_setpoint, p.shh_setpoint)
            for p in points
        ]
        try:
            self.db_service.execute_many(sql, params_list)
            logger.info(f"成功保存 {len(points)} 个配置点位。")
            return True
        except sqlite3.IntegrityError as ie:
            logger.error(f"保存配置点位时发生数据库完整性冲突 (可能是变量名重复): {ie}", exc_info=True)
            # 提取第一个点位的前缀信息用于更具体的错误提示
            first_point = points[0] if points else None
            vp = first_point.variable_prefix if first_point else ''
            dp = first_point.description_prefix if first_point else ''
            raise ValueError(f"保存点位失败：变量名冲突。在配置 (模板: {first_point.template_name if first_point else ''}, 变量前缀: '{vp}', 描述前缀: '{dp}') 下可能存在重复的变量后缀。") from ie
        except Exception as e:
            logger.error(f"批量保存配置点位失败: {e}", exc_info=True)
            return False # 对于其他未知错误，返回False

    def get_all_configured_points(self) -> List[ConfiguredDevicePointModel]:
        """获取所有已配置的设备点位。"""
        sql = CONFIGURED_DEVICE_SQL['GET_ALL_CONFIGURED_POINTS']
        try:
            rows = self.db_service.fetch_all(sql) # Use db_service
            return [ConfiguredDevicePointModel.model_validate(row, from_attributes=True) for row in rows]
        except Exception as e:
            logger.error(f"获取所有已配置点位失败: {e}", exc_info=True)
            return []

    def delete_all_configured_points(self) -> bool:
        """删除所有已配置的设备点位。"""
        sql = CONFIGURED_DEVICE_SQL['DELETE_ALL_CONFIGURED_POINTS']
        try:
            cursor = self.db_service.execute(sql)
            logger.info(f"成功删除 {cursor.rowcount if cursor else '未知数量'} 条配置点位。")
            return True
        except Exception as e:
            logger.error(f"删除所有配置点位失败: {e}", exc_info=True)
            return False

    def delete_configured_points_by_template_and_prefixes(self, template_name: str, variable_prefix: str, description_prefix: str) -> bool:
        """根据模板名称、变量前缀和描述前缀删除一组已配置的设备点位。"""
        sql = CONFIGURED_DEVICE_SQL['DELETE_CONFIGURED_POINTS_BY_TEMPLATE_AND_PREFIXES']
        params = (template_name, variable_prefix, description_prefix)
        try:
            cursor = self.db_service.execute(sql, params)
            if cursor and cursor.rowcount > 0:
                logger.info(f"成功删除模板 \'{template_name}\' (变量前缀=\'{variable_prefix}\', 描述前缀=\'{description_prefix}\') 的 {cursor.rowcount} 条配置点位。")
                return True
            # 如果 rowcount 是 0，表示没有匹配的点位被删除，这通常不应视为错误，而是操作成功但无效果
            logger.info(f"模板 \'{template_name}\' (变量前缀=\'{variable_prefix}\', 描述前缀=\'{description_prefix}\') 没有找到匹配的点位进行删除。")
            return True # 保持与旧逻辑一致，删除0行也算成功
        except Exception as e:
            logger.error(f"删除配置点位 (模板 \'{template_name}\', 变量前缀 \'{variable_prefix}\', 描述前缀 \'{description_prefix}\') 失败: {e}", exc_info=True)
            return False

    def get_configuration_summary_raw(self) -> List[Dict[str, Any]]:
        """获取原始的配置摘要信息（按模板名称、变量前缀和描述前缀分组）。"""
        sql = CONFIGURED_DEVICE_SQL['GET_CONFIGURATION_SUMMARY_RAW']
        try:
            rows = self.db_service.fetch_all(sql)
            # 确保返回的字典键与SQL查询中的列名一致
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            logger.error(f"获取配置摘要原始数据失败: {e}", exc_info=True)
            return []

    def does_configuration_exist(self, template_name: str, variable_prefix: str, description_prefix: str) -> bool:
        """检查具有指定模板名称、变量前缀和描述前缀的配置是否已在数据库中至少存在一个点位。"""
        sql = CONFIGURED_DEVICE_SQL['CHECK_CONFIGURATION_EXISTS']
        params = (template_name, variable_prefix, description_prefix)
        try:
            result = self.db_service.fetch_one(sql, params)
            return bool(result) # 如果查询到任何行，则存在
        except Exception as e:
            logger.error(f"检查配置是否存在 (模板 \'{template_name}\', 变量前缀 \'{variable_prefix}\', 描述前缀 \'{description_prefix}\') 失败: {e}", exc_info=True)
            return False 