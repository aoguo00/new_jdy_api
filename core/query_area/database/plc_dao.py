"""PLC 数据访问对象 (DAO)，封装PLC相关的数据库交互"""
import logging
from typing import List, Optional, Dict, Any

# Import DatabaseService for type hinting (use string literal for forward reference)
# from core.database.database_service import DatabaseService 
from .sql import PLC_SQL # PLC_SQL is in core/query_area/database/sql.py

logger = logging.getLogger(__name__)

class PLCDAO:
    """PLC数据访问对象，处理PLC系列和模块的数据库操作。"""

    def __init__(self, db_service: 'DatabaseService'): # Type hint as string
        """
        初始化 PLCDAO。
        :param db_service: DatabaseService 的实例，用于执行数据库操作。
        """
        self.db_service = db_service
        logger.info("PLCDAO 初始化完成。")

    # ====== PLC系列相关操作 ======
    def get_all_plc_series(self) -> List[Dict[str, Any]]:
        """获取所有PLC系列"""
        return self.db_service.fetch_all(PLC_SQL['GET_ALL_SERIES'])
    
    def add_plc_series(self, name: str, description: Optional[str]) -> bool:
        """添加PLC系列"""
        try:
            self.db_service.execute(PLC_SQL['INSERT_SERIES'], (name, description))
            return True
        except Exception as e:
            logger.error(f"PLCDAO 添加PLC系列失败: {str(e)}", exc_info=True)
            return False # Consider re-raising or returning more specific error
    
    def delete_plc_series(self, series_id: int) -> bool:
        """删除PLC系列"""
        try:
            self.db_service.execute(PLC_SQL['DELETE_SERIES'], (series_id,))
            return True
        except Exception as e:
            logger.error(f"PLCDAO 删除PLC系列失败: {str(e)}", exc_info=True)
            return False
    
    def get_series_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取系列信息"""
        return self.db_service.fetch_one(PLC_SQL['GET_SERIES_BY_NAME'], (name,))
    
    # ====== 模块相关操作 ======
    def add_module(self, series_id: int, model: str, module_type: str,
                  channels: int, description: Optional[str]) -> bool:
        """添加模块"""
        try:
            self.db_service.execute(PLC_SQL['INSERT_MODULE'],
                        (series_id, model, module_type, channels, description))
            return True
        except Exception as e:
            logger.error(f"PLCDAO 添加模块失败: {str(e)}", exc_info=True)
            return False
    
    def delete_module(self, series_id: int, model: str) -> bool:
        """删除模块"""
        try:
            self.db_service.execute(PLC_SQL['DELETE_MODULE'], (series_id, model))
            return True
        except Exception as e:
            logger.error(f"PLCDAO 删除模块失败: {str(e)}", exc_info=True)
            return False
    
    def get_modules_by_type(self, series_id: int, module_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的模块列表"""
        return self.db_service.fetch_all(PLC_SQL['GET_MODULES_BY_TYPE'],
                            (series_id, module_type))
    
    def get_module_info(self, series_id: int, model: str) -> Optional[Dict[str, Any]]:
        """获取模块信息"""
        return self.db_service.fetch_one(PLC_SQL['GET_MODULE_INFO'],
                            (series_id, model))

    def get_modules_by_series_id(self, series_id: int) -> List[Dict[str, Any]]:
        """获取指定系列的所有模块 (已修正方法签名以接收 series_id)"""
        return self.db_service.fetch_all(PLC_SQL['GET_MODULES_BY_SERIES_ID'], (series_id,)) 