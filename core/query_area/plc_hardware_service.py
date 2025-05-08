"""服务层，用于管理PLC系列和模块的业务逻辑"""

import logging
from typing import List, Optional, Dict, Any

# Updated imports
from core.database.database_service import DatabaseService
from .database.plc_dao import PLCDAO
from .plc_models import PLCSeriesModel, PLCModuleModel
# PLC_SQL is now used by PLCDAO, not directly here unless for some specific reason.

logger = logging.getLogger(__name__)

class PLCHardwareService:
    """处理 PLC 系列和模块相关的 CRUD 操作和服务逻辑"""

    def __init__(self):
        """初始化PLC管理服务"""
        try:
            self.db_service = DatabaseService() # Get/Create instance of DatabaseService
            self.plc_dao = PLCDAO(self.db_service) # Create PLCDAO with DatabaseService
            logger.info("PLCHardwareService 初始化完成")
        except Exception as e:
            logger.error(f"PLCHardwareService 初始化失败: {e}", exc_info=True)
            raise

    # --- 辅助转换方法 --- 
    def _db_row_to_plc_series_model(self, row: Dict[str, Any]) -> Optional[PLCSeriesModel]:
        """将数据库行（字典）转换为 PLCSeriesModel 对象"""
        if not row:
            return None
        return PLCSeriesModel(
            id=row.get('id'),
            name=row.get('name', '未知系列'),
            description=row.get('description'),
            created_at=row.get('created_at')
        )

    def _db_row_to_plc_module_model(self, row: Dict[str, Any]) -> Optional[PLCModuleModel]:
        """将数据库行（字典）转换为 PLCModuleModel 对象"""
        if not row:
            return None
        series_id = row.get('series_id')
        if series_id is None:
             logger.warning(f"数据库返回的模块数据缺少 series_id: {row}")
             return None
             
        return PLCModuleModel(
            id=row.get('id'),
            model=row.get('model', '未知型号'),
            module_type=row.get('module_type', '未知类型'),
            series_id=int(series_id),
            channels=row.get('channels', 0),
            description=row.get('description'),
            created_at=row.get('created_at')
        )

    # --- PLC 系列 (Series) 操作 --- 
    def get_all_series(self) -> List[PLCSeriesModel]:
        """获取所有已定义的 PLC 系列列表"""
        try:
            series_rows = self.plc_dao.get_all_plc_series()
            series_models = [self._db_row_to_plc_series_model(row) for row in series_rows]
            return [model for model in series_models if model is not None]
        except Exception as e:
            logger.error(f"获取所有 PLC 系列失败: {e}", exc_info=True)
            return []
            
    def get_series_by_name(self, name: str) -> Optional[PLCSeriesModel]:
        """根据名称查找 PLC 系列"""
        try:
            series_row = self.plc_dao.get_series_by_name(name)
            return self._db_row_to_plc_series_model(series_row)
        except Exception as e:
            logger.error(f"根据名称 '{name}' 获取 PLC 系列失败: {e}", exc_info=True)
            return None

    def add_series(self, name: str, description: Optional[str] = None) -> Optional[PLCSeriesModel]:
        """添加一个新的 PLC 系列"""
        if self.get_series_by_name(name):
            logger.warning(f"添加 PLC 系列失败：名称 '{name}' 已存在。")
            raise ValueError(f"PLC 系列名称 '{name}' 已存在。") 
        try:
            success = self.plc_dao.add_plc_series(name, description)
            if success:
                # Fetch the newly added series to return the model (DAO returns raw dict or ID)
                # Assuming get_series_by_name is suitable here
                return self.get_series_by_name(name) 
            return None
        except Exception as e: # Catch potential errors from DAO or here
            logger.error(f"添加 PLC 系列 '{name}' 失败: {e}", exc_info=True)
            # Re-raise specific errors if needed, e.g. for duplicate names if DAO doesn't handle
            if "UNIQUE constraint failed" in str(e) or isinstance(e, ValueError): # Or if DAO raises ValueError
                 raise ValueError(f"PLC 系列名称 '{name}' 已存在。") from e
            return None
            
    def delete_series(self, series_id: int) -> bool:
        """删除一个 PLC 系列及其下所有模块"""
        try:
            return self.plc_dao.delete_plc_series(series_id)
        except Exception as e:
            logger.error(f"删除 PLC 系列 ID: {series_id} 失败: {e}", exc_info=True)
            return False
            
    # --- PLC 模块 (Module) 操作 --- 
    def get_modules_by_series_id(self, series_id: int) -> List[PLCModuleModel]:
        """获取指定系列下的所有模块"""
        try:
            module_rows = self.plc_dao.get_modules_by_series_id(series_id) # Use corrected method name
            module_models = [self._db_row_to_plc_module_model(row) for row in module_rows]
            return [model for model in module_models if model is not None]
        except Exception as e:
             logger.error(f"获取系列 ID {series_id} 的所有模块失败: {e}", exc_info=True)
             return []
             
    def get_modules_by_series_and_type(self, series_id: int, module_type: str) -> List[PLCModuleModel]:
        """获取指定系列和类型的模块列表"""
        try:
            module_rows = self.plc_dao.get_modules_by_type(series_id, module_type)
            module_models = [self._db_row_to_plc_module_model(row) for row in module_rows]
            return [model for model in module_models if model is not None]
        except Exception as e:
            logger.error(f"获取系列 ID {series_id} 类型 '{module_type}' 的模块失败: {e}", exc_info=True)
            return []

    def add_module(self, series_id: int, model: str, module_type: str, channels: int = 0, description: Optional[str] = None) -> Optional[PLCModuleModel]:
        """向指定系列添加一个新模块"""
        try:
            # Check if series exists
            series = self.get_series_by_name(self.plc_dao.get_all_series()[series_id-1]["name"]) # This is a bit hacky way to get series name
            # A better way would be self.plc_dao.get_series_by_id(series_id) if it exists
            if not series:
                raise ValueError(f"系列 ID {series_id} 不存在，无法添加模块。")
            
            # Check if module already exists in this series (optional, DAO might handle unique constraints)
            if self.get_module_info(series_id, model):
                raise ValueError(f"模块型号 '{model}' 已在系列ID {series_id} 中存在。")

            success = self.plc_dao.add_module(series_id, model, module_type, channels, description)
            if success:
                return self.get_module_info(series_id, model)
            return None
        except Exception as e:
            logger.error(f"添加模块 '{model}' 到系列 ID {series_id} 失败: {e}", exc_info=True)
            if isinstance(e, ValueError): raise e # Re-raise known ValueErrors
            return None

    def get_module_info(self, series_id: int, model: str) -> Optional[PLCModuleModel]:
        """获取特定系列下特定型号模块的信息"""
        try:
            module_row = self.plc_dao.get_module_info(series_id, model)
            return self._db_row_to_plc_module_model(module_row)
        except Exception as e:
            logger.error(f"获取系列 ID {series_id} 模块 '{model}' 信息失败: {e}", exc_info=True)
            return None
            
    def delete_module(self, series_id: int, model: str) -> bool:
        """删除指定系列下的特定型号模块"""
        try:
            return self.plc_dao.delete_module(series_id, model)
        except Exception as e:
             logger.error(f"删除系列 ID {series_id} 模块 '{model}' 失败: {e}", exc_info=True)
             return False

    # TODO: 可能需要添加 update_series, update_module, get_series_by_id, get_module_by_id 等方法
    # TODO: 实现与 PLCBackplaneModel 相关的服务方法 (如果需要) 