"""服务层，用于管理PLC系列和模块的业务逻辑"""

import logging
from typing import List, Optional, Dict, Any, Tuple

# 数据访问层
from core.db_manipulate.db_manager import DBManager

# 数据模型
from core.models.plc.models import PLCSeriesModel, PLCModuleModel # PLCBackplaneModel 暂不实现服务

# SQL 查询 (仍然需要SQL语句)
from core.db_manipulate.sql_queries import PLC_SQL 

logger = logging.getLogger(__name__)

class PLCManagementService:
    """处理 PLC 系列和模块相关的 CRUD 操作和服务逻辑"""

    def __init__(self):
        """初始化PLC管理服务，获取DBManager实例"""
        try:
            # DBManager 是单例，直接获取实例
            self.db = DBManager() 
            # 可以在这里添加额外的初始化检查，比如确认相关表已存在
            logger.info("PLCManagementService 初始化完成")
        except Exception as e:
            logger.error(f"PLCManagementService 初始化失败: {e}", exc_info=True)
            # 根据应用的错误处理策略，可能需要再次抛出异常
            raise

    # --- 辅助转换方法 --- 
    def _db_row_to_plc_series_model(self, row: Dict[str, Any]) -> Optional[PLCSeriesModel]:
        """将数据库行（字典）转换为 PLCSeriesModel 对象"""
        if not row:
            return None
        return PLCSeriesModel(
            id=row.get('id'),
            name=row.get('name', '未知系列'), # 提供默认值以防万一
            description=row.get('description'),
            created_at=row.get('created_at') # created_at 可能需要类型转换
        )

    def _db_row_to_plc_module_model(self, row: Dict[str, Any]) -> Optional[PLCModuleModel]:
        """将数据库行（字典）转换为 PLCModuleModel 对象"""
        if not row:
            return None
        # 确保 series_id 存在且是整数 (从旧的db_manager看，add_module时会传入)
        series_id = row.get('series_id')
        if series_id is None:
             logger.warning(f"数据库返回的模块数据缺少 series_id: {row}")
             # 或者可以根据 model 查询 series_id? 暂时返回 None
             return None
             
        return PLCModuleModel(
            id=row.get('id'),
            model=row.get('model', '未知型号'),
            module_type=row.get('module_type', '未知类型'),
            series_id=int(series_id), # 确保是整数
            channels=row.get('channels', 0),
            description=row.get('description'),
            created_at=row.get('created_at') # created_at 可能需要类型转换
        )

    # --- PLC 系列 (Series) 操作 --- 
    def get_all_series(self) -> List[PLCSeriesModel]:
        """获取所有已定义的 PLC 系列列表"""
        try:
            series_rows = self.db.fetch_all(PLC_SQL['GET_ALL_SERIES'])
            series_models = [self._db_row_to_plc_series_model(row) for row in series_rows]
            # 过滤掉转换失败的 None 值
            return [model for model in series_models if model is not None]
        except Exception as e:
            logger.error(f"获取所有 PLC 系列失败: {e}", exc_info=True)
            return [] # 返回空列表表示失败或无数据
            
    def get_series_by_name(self, name: str) -> Optional[PLCSeriesModel]:
        """根据名称查找 PLC 系列"""
        try:
            series_row = self.db.fetch_one(PLC_SQL['GET_SERIES_BY_NAME'], (name,))
            return self._db_row_to_plc_series_model(series_row)
        except Exception as e:
            logger.error(f"根据名称 '{name}' 获取 PLC 系列失败: {e}", exc_info=True)
            return None

    def add_series(self, name: str, description: Optional[str] = None) -> Optional[PLCSeriesModel]:
        """添加一个新的 PLC 系列"""
        # 检查名称是否已存在
        if self.get_series_by_name(name):
            logger.warning(f"添加 PLC 系列失败：名称 '{name}' 已存在。")
            # 可以抛出异常或返回 None/False
            raise ValueError(f"PLC 系列名称 '{name}' 已存在。") 
            # return None 

        try:
            # 注意：PLC_SQL['INSERT_SERIES'] 的参数顺序是 (name, description)
            cursor = self.db.execute(PLC_SQL['INSERT_SERIES'], (name, description))
            new_series_id = cursor.lastrowid
            if new_series_id:
                # 添加成功后，可以根据ID或名称获取并返回完整的模型对象
                # 这里选择根据名称获取
                return self.get_series_by_name(name)
            else:
                logger.error(f"添加 PLC 系列 '{name}' 后无法获取 ID。")
                return None
        except Exception as e:
            logger.error(f"添加 PLC 系列 '{name}' 失败: {e}", exc_info=True)
            # 如果是因为名称唯一性约束失败，上面的检查应该已经捕获，但以防万一
            if "UNIQUE constraint failed" in str(e):
                 raise ValueError(f"PLC 系列名称 '{name}' 已存在。") from e
            return None
            
    def delete_series(self, series_id: int) -> bool:
        """删除一个 PLC 系列及其下所有模块 (通过外键级联删除)"""
        try:
            # 确认系列是否存在 (可选)
            # series = self.get_series_by_id(series_id) # 需要先实现 get_series_by_id
            # if not series:
            #     logger.warning(f"尝试删除不存在的 PLC 系列 ID: {series_id}")
            #     return False
            
            self.db.execute(PLC_SQL['DELETE_SERIES'], (series_id,))
            # 可以添加检查确保真的删除了
            # if self.get_series_by_id(series_id) is None:
            logger.info(f"成功删除 PLC 系列 ID: {series_id}")
            return True
            # else:
            #    logger.error(f"删除 PLC 系列 ID: {series_id} 失败，记录仍存在")
            #    return False
        except Exception as e:
            logger.error(f"删除 PLC 系列 ID: {series_id} 失败: {e}", exc_info=True)
            return False
            
    # --- PLC 模块 (Module) 操作 --- 
    def get_modules_by_series_id(self, series_id: int) -> List[PLCModuleModel]:
        """获取指定系列下的所有模块"""
        try:
            # 使用 PLC_SQL 中的查询替换硬编码的SQL
            module_rows = self.db.fetch_all(
                PLC_SQL['GET_MODULES_BY_SERIES_ID'], 
                (series_id,)
            )
            module_models = [self._db_row_to_plc_module_model(row) for row in module_rows]
            return [model for model in module_models if model is not None]
        except Exception as e:
             logger.error(f"获取系列 ID {series_id} 的所有模块失败: {e}", exc_info=True)
             return []
             
    def get_modules_by_series_and_type(self, series_id: int, module_type: str) -> List[PLCModuleModel]:
        """获取指定系列和类型的模块列表"""
        try:
            module_rows = self.db.fetch_all(PLC_SQL['GET_MODULES_BY_TYPE'], (series_id, module_type))
            # SQL 查询已更新，确保返回所有需要的字段，包括 id 和 series_id
            module_models = [self._db_row_to_plc_module_model(row) for row in module_rows]
            return [model for model in module_models if model is not None]
            
        except Exception as e:
            logger.error(f"获取系列 ID {series_id} 类型 '{module_type}' 的模块失败: {e}", exc_info=True)
            return []

    def add_module(self, series_id: int, model: str, module_type: str, channels: int = 0, description: Optional[str] = None) -> Optional[PLCModuleModel]:
        """向指定系列添加一个新模块"""
        try:
            # 检查模块是否已存在 (可选)
            # existing = self.get_module_info(series_id, model)
            # if existing:
            #     logger.warning(f"添加模块失败：系列ID {series_id} 下已存在型号为 '{model}' 的模块。")
            #     raise ValueError(f"模块型号 '{model}' 在该系列下已存在。")

            # PLC_SQL['INSERT_MODULE'] 参数顺序: (series_id, model, module_type, channels, description)
            cursor = self.db.execute(PLC_SQL['INSERT_MODULE'], (series_id, model, module_type, channels, description))
            new_module_id = cursor.lastrowid
            if new_module_id:
                # 可以根据 ID 获取新添加的模块，但需要先实现 get_module_by_id
                # 暂时根据 series_id 和 model 获取
                return self.get_module_info(series_id, model)
            else:
                 logger.error(f"添加模块 '{model}' 到系列 ID {series_id} 后无法获取 ID。")
                 return None
        except Exception as e:
            logger.error(f"添加模块 '{model}' 到系列 ID {series_id} 失败: {e}", exc_info=True)
            # 检查是否因为唯一性约束 (如果数据库有的话)
            # if "UNIQUE constraint failed" in str(e): ...
            return None

    def get_module_info(self, series_id: int, model: str) -> Optional[PLCModuleModel]:
        """获取特定系列下特定型号模块的信息"""
        try:
            # SQL 查询已更新，确保返回所有需要的字段，包括 id 和 series_id
            module_row = self.db.fetch_one(PLC_SQL['GET_MODULE_INFO'], (series_id, model))
            return self._db_row_to_plc_module_model(module_row)
        except Exception as e:
            logger.error(f"获取系列 ID {series_id} 模块 '{model}' 信息失败: {e}", exc_info=True)
            return None
            
    def delete_module(self, series_id: int, model: str) -> bool:
        """删除指定系列下的特定型号模块"""
        try:
            # 确认模块是否存在 (可选)
            # module = self.get_module_info(series_id, model)
            # if not module:
            #     logger.warning(f"尝试删除不存在的模块：系列ID {series_id}, 型号 '{model}'")
            #     return False
                
            self.db.execute(PLC_SQL['DELETE_MODULE'], (series_id, model))
            # 检查是否真的删除 (可选)
            # if self.get_module_info(series_id, model) is None:
            logger.info(f"成功删除系列 ID {series_id} 下的模块 '{model}'")
            return True
            # else: ...
        except Exception as e:
             logger.error(f"删除系列 ID {series_id} 模块 '{model}' 失败: {e}", exc_info=True)
             return False

    # TODO: 可能需要添加 update_series, update_module, get_series_by_id, get_module_by_id 等方法
    # TODO: 实现与 PLCBackplaneModel 相关的服务方法 (如果需要) 