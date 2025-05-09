"""通用数据库服务模块"""
import sqlite3
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from contextlib import contextmanager
from .sql import TEMPLATE_SQL, CONFIGURED_DEVICE_SQL

logger = logging.getLogger(__name__)

class DatabaseService:
    """
    通用数据库服务，提供数据库基础操作和表初始化。
    这是一个单例类。
    """
    _instance = None
    
    def __new__(cls, *args, **kwargs): # 修改为接受 *args, **kwargs 以增加灵活性
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False # 实例是否已初始化标志，确保 __init__ 只执行一次
        return cls._instance

    def __init__(self, db_name: str = "data.db", db_subfolder: str = "db"):
        """
        初始化数据库服务。
        :param db_name: 数据库文件名。
        :param db_subfolder: 存放数据库文件的子目录名（相对于项目根目录）。
        """
        if not self.initialized: # 防止重复初始化
            try:
                # 项目根目录定位：当前文件 -> parent (database) -> parent (third_party_config_area) -> parent (core) -> parent (project_root)
                project_root = Path(__file__).resolve().parent.parent.parent.parent
                self.db_dir = project_root / db_subfolder
                self.db_dir.mkdir(parents=True, exist_ok=True) # parents=True 表示如果父目录不存在则一并创建，exist_ok=True 表示如果目录已存在则不抛出异常
                self.db_path = self.db_dir / db_name
                
                logger.info(f"数据库文件路径设置为: {self.db_path}")
                
                self.init_databases() # 初始化所有表结构
                self.initialized = True
                logger.info("DatabaseService 初始化完成。")
            except Exception as e:
                logger.error(f"DatabaseService 初始化失败: {e}", exc_info=True)
                raise

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute('PRAGMA foreign_keys = ON') # 启用外键约束
        return conn

    def init_databases(self):
        """
        初始化所有应用程序所需的数据库表。
        使用 "CREATE TABLE IF NOT EXISTS" 确保幂等性。
        """
        logger.info("开始初始化所有数据库表结构...")
        try:
            with self.transaction() as cursor: # 使用事务确保所有初始化操作的原子性

                # 初始化第三方设备模板相关表
                logger.info("初始化第三方设备模板相关表...")
                cursor.execute(TEMPLATE_SQL['CREATE_TEMPLATES_TABLE'])
                cursor.execute(TEMPLATE_SQL['CREATE_POINTS_TABLE'])
                logger.info("第三方设备模板相关表初始化完成。")

                # 初始化已配置第三方设备点表
                logger.info("初始化已配置第三方设备点表...")
                cursor.execute(CONFIGURED_DEVICE_SQL['CREATE_CONFIGURED_POINTS_TABLE'])
                logger.info("已配置第三方设备点表初始化完成。")
            
            logger.info("所有数据库表结构初始化完毕。")
        except Exception as e:
            logger.error(f"数据库表结构初始化过程中发生错误: {e}", exc_info=True)
            raise


    def execute(self, sql: str, params: tuple = None) -> sqlite3.Cursor:
        """
        执行单条SQL语句 (如 INSERT, UPDATE, DELETE)。
        不适合用于 SELECT 查询后获取大量数据。
        自动处理连接的打开、提交和关闭。
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ()) # 如果 params 为 None，则使用空元组，防止SQL错误
            conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"执行SQL失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
            if conn:
                conn.rollback() # 如果连接已建立，在发生错误时回滚事务
            raise
        finally:
            if conn:
                conn.close() # 确保连接在最后关闭

    def execute_many(self, sql: str, params_list: List[tuple]) -> sqlite3.Cursor:
        """
        批量执行SQL语句。
        自动处理连接的打开、提交和关闭。
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executemany(sql, params_list)
            conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"批量执行SQL失败: {sql}, 错误: {e}", exc_info=True)
            if conn:
                conn.rollback() # 如果连接已建立，在发生错误时回滚事务
            raise
        finally:
            if conn:
                conn.close() # 确保连接在最后关闭

    def fetch_one(self, sql: str, params: tuple = None) -> Optional[Dict[str, Any]]:
        """查询单条记录，并以字典形式返回。"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row # 返回字典而不是元组
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"查询单条记录失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close() # 确保连接在最后关闭

    def fetch_all(self, sql: str, params: tuple = None) -> List[Dict[str, Any]]:
        """查询多条记录，并以字典列表形式返回。"""
        conn = None
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"查询多条记录失败: {sql}, 参数: {params}, 错误: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close() # 确保连接在最后关闭

    @contextmanager
    def transaction(self):
        """
        提供一个事务上下文管理器。
        用法: with db_service.transaction() as cursor: ...
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # logger.debug("数据库事务开始...")
            yield cursor
            conn.commit()
            # logger.debug("数据库事务已提交。")
        except Exception as e:
            if conn:
                conn.rollback()
                # logger.error(f"数据库事务回滚: {e}", exc_info=True)
            raise
        finally:
            if conn:
                conn.close() # 确保连接在事务结束时关闭
                # logger.debug("数据库连接已关闭（事务结束）。")


