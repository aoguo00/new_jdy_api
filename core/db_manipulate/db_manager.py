"""统一的数据库管理模块"""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from .sql_queries import PLC_SQL

logger = logging.getLogger(__name__)

class DBManager:
    """数据库管理器，提供数据库基础操作和业务逻辑管理"""
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        """初始化数据库管理器"""
        if not self.initialized:
            try:
                # 数据库文件放在项目根目录的db文件夹下
                self.db_dir = Path(__file__).parent.parent.parent / 'db'
                self.db_dir.mkdir(exist_ok=True)
                self.db_path = self.db_dir / 'data.db'
                
                # 初始化数据库表
                self.init_databases()
                self.initialized = True
                logger.info("数据库管理器初始化完成")
            except Exception as e:
                logger.error(f"数据库管理器初始化失败: {e}")
                raise

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        # 启用外键约束
        conn.execute('PRAGMA foreign_keys = ON')
        return conn

    def init_databases(self):
        """初始化所有数据库表"""
        # 初始化PLC模块数据库
        self.execute(PLC_SQL['CREATE_SERIES_TABLE'])
        self.execute(PLC_SQL['CREATE_BACKPLANES_TABLE'])
        self.execute(PLC_SQL['CREATE_MODULES_TABLE'])

    def execute(self, sql: str, params: tuple = None) -> Any:
        """执行SQL语句"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                conn.commit()
                return cursor
        except Exception as e:
            logger.error(f"执行SQL失败: {sql}, 参数: {params}, 错误: {str(e)}")
            raise

    def execute_many(self, sql: str, params_list: List[tuple]) -> Any:
        """执行多条SQL语句"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(sql, params_list)
                conn.commit()
                return cursor
        except Exception as e:
            logger.error(f"执行多条SQL失败: {sql}, 参数: {params_list}, 错误: {str(e)}")
            raise

    def fetch_one(self, sql: str, params: tuple = None) -> Optional[Dict]:
        """查询单条记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                    
                row = cursor.fetchone()
                if row:
                    return dict(zip([col[0] for col in cursor.description], row))
                return None
        except Exception as e:
            logger.error(f"查询单条记录失败: {sql}, 参数: {params}, 错误: {str(e)}")
            raise

    def fetch_all(self, sql: str, params: tuple = None) -> List[Dict]:
        """查询多条记录"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(sql, params)
                else:
                    cursor.execute(sql)
                    
                rows = cursor.fetchall()
                return [dict(zip([col[0] for col in cursor.description], row)) for row in rows]
        except Exception as e:
            logger.error(f"查询多条记录失败: {sql}, 参数: {params}, 错误: {str(e)}")
            raise

    # ====== PLC系列相关操作 ======
    def get_all_plc_series(self) -> List[Dict]:
        """获取所有PLC系列"""
        return self.fetch_all(PLC_SQL['GET_ALL_SERIES'])
    
    def add_plc_series(self, name: str, description: str) -> bool:
        """添加PLC系列"""
        try:
            self.execute(PLC_SQL['INSERT_SERIES'], (name, description))
            return True
        except Exception as e:
            logger.error(f"添加PLC系列失败: {str(e)}")
            return False
    
    def delete_plc_series(self, series_id: int) -> bool:
        """删除PLC系列"""
        try:
            self.execute(PLC_SQL['DELETE_SERIES'], (series_id,))
            return True
        except Exception as e:
            logger.error(f"删除PLC系列失败: {str(e)}")
            return False
    
    def get_series_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取系列信息"""
        return self.fetch_one(PLC_SQL['GET_SERIES_BY_NAME'], (name,))
    
    # ====== 模块相关操作 ======
    def add_module(self, series_id: int, model: str, module_type: str,
                  channels: int, description: str) -> bool:
        """添加模块"""
        try:
            self.execute(PLC_SQL['INSERT_MODULE'],
                        (series_id, model, module_type, channels, description))
            return True
        except Exception as e:
            logger.error(f"添加模块失败: {str(e)}")
            return False
    
    def delete_module(self, series_id: int, model: str) -> bool:
        """删除模块"""
        try:
            self.execute(PLC_SQL['DELETE_MODULE'], (series_id, model))
            return True
        except Exception as e:
            logger.error(f"删除模块失败: {str(e)}")
            return False
    
    def get_modules_by_type(self, series_id: int, module_type: str) -> List[Dict]:
        """获取指定类型的模块列表"""
        return self.fetch_all(PLC_SQL['GET_MODULES_BY_TYPE'],
                            (series_id, module_type))
    
    def get_module_info(self, series_id: int, model: str) -> Optional[Dict]:
        """获取模块信息"""
        return self.fetch_one(PLC_SQL['GET_MODULE_INFO'],
                            (series_id, model)) 