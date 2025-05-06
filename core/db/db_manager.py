"""统一的数据库管理器"""
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from .database import Database
from .sql_queries import PLC_SQL

logger = logging.getLogger(__name__)

class DBManager:
    """数据库管理器，单例模式"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_dir = Path(__file__).parent.parent.parent / 'data'
            self.db_dir.mkdir(parents=True, exist_ok=True)
            
            # 初始化数据库连接
            self.plc_db = Database(self.db_dir / 'plc_modules.db')
            
            # 初始化数据库表
            self.init_databases()
            self.initialized = True
    
    def init_databases(self):
        """初始化所有数据库表"""
        # 初始化PLC模块数据库
        self.plc_db.execute(PLC_SQL['CREATE_SERIES_TABLE'])
        self.plc_db.execute(PLC_SQL['CREATE_BACKPLANES_TABLE'])
        self.plc_db.execute(PLC_SQL['CREATE_MODULES_TABLE'])
    
    # PLC系列相关操作
    def get_all_plc_series(self) -> List[Dict]:
        """获取所有PLC系列"""
        return self.plc_db.fetch_all(PLC_SQL['GET_ALL_SERIES'])
    
    def add_plc_series(self, name: str, description: str) -> bool:
        """添加PLC系列"""
        try:
            self.plc_db.execute(PLC_SQL['INSERT_SERIES'], (name, description))
            return True
        except Exception as e:
            logger.error(f"添加PLC系列失败: {str(e)}")
            return False
    
    def delete_plc_series(self, series_id: int) -> bool:
        """删除PLC系列"""
        try:
            self.plc_db.execute(PLC_SQL['DELETE_SERIES'], (series_id,))
            return True
        except Exception as e:
            logger.error(f"删除PLC系列失败: {str(e)}")
            return False
    
    def get_series_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取系列信息"""
        return self.plc_db.fetch_one(PLC_SQL['GET_SERIES_BY_NAME'], (name,))
    
    # 模块相关操作
    def add_module(self, series_id: int, model: str, module_type: str,
                  channels: int, description: str) -> bool:
        """添加模块"""
        try:
            self.plc_db.execute(PLC_SQL['INSERT_MODULE'],
                              (series_id, model, module_type, channels, description))
            return True
        except Exception as e:
            logger.error(f"添加模块失败: {str(e)}")
            return False
    
    def delete_module(self, series_id: int, model: str) -> bool:
        """删除模块"""
        try:
            self.plc_db.execute(PLC_SQL['DELETE_MODULE'], (series_id, model))
            return True
        except Exception as e:
            logger.error(f"删除模块失败: {str(e)}")
            return False
    
    def get_modules_by_type(self, series_id: int, module_type: str) -> List[Dict]:
        """获取指定类型的模块列表"""
        return self.plc_db.fetch_all(PLC_SQL['GET_MODULES_BY_TYPE'],
                                   (series_id, module_type))
    
    def get_module_info(self, series_id: int, model: str) -> Optional[Dict]:
        """获取模块信息"""
        return self.plc_db.fetch_one(PLC_SQL['GET_MODULE_INFO'],
                                   (series_id, model)) 