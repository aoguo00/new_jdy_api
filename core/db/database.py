"""统一的数据库管理模块"""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)

class Database:
    """数据库管理基类"""
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.ensure_db_directory()
        
    def ensure_db_directory(self):
        """确保数据库目录存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(str(self.db_path))
        
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