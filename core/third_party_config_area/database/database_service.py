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
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            # 关键：在 __new__ 中处理 db_path，确保单例初始化时路径被设置
            # 或者，更好的方式是，如果 db_path 是必需的，则在 __init__ 中强制要求
            # 并在 __new__ 中仅创建实例，让 __init__ 处理初始化逻辑
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False 
        return cls._instance

    def __init__(self, db_path: Optional[str] = None): # 修改：接收可选的 db_path
        """
        初始化数据库服务。
        :param db_path: 数据库文件的绝对路径。
                         如果为 None，并且服务尚未初始化，则会引发错误。
        """
        # 单例模式下，如果实例已完全初始化，则直接返回，防止重复初始化
        if hasattr(self, 'fully_initialized') and self.fully_initialized:
            if db_path is not None and Path(db_path).resolve() != self.db_path:
                logger.warning(f"DatabaseService 已使用路径 '{self.db_path}' 完全初始化。忽略新的路径 '{db_path}'。")
            return

        # 如果是首次尝试初始化 (instance.initialized 为 False)
        if not hasattr(self, 'initialized') or not self.initialized:
            if db_path is None:
                logger.error("DatabaseService 必须使用有效的 'db_path' 进行首次初始化。")
                raise ValueError("DatabaseService 首次初始化时 'db_path' 不能为空。")

            try:
                self.db_path = Path(db_path).resolve()
                db_dir = self.db_path.parent
                db_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"数据库文件路径设置为: {self.db_path}")

                # 在尝试进行数据库操作（如 init_databases）之前，标记为部分初始化成功（路径已设置）
                # 或者我们可以认为，一旦 db_path 设置成功，连接就可以尝试建立
                # 关键：在调用 init_databases 之前设置 initialized 为 True
                self.initialized = True 

                self.init_databases() # 初始化所有表结构
                
                # 所有步骤成功后，标记为完全初始化
                self.fully_initialized = True # 新增一个更明确的最终成功标志
                logger.info("DatabaseService 初始化完成。")

            except Exception as e:
                logger.error(f"DatabaseService 初始化失败: {e}", exc_info=True)
                # 如果初始化过程中（包括 init_databases）失败，重置 initialized 状态
                self.initialized = False
                self.fully_initialized = False # 确保最终状态也是失败
                raise
        elif db_path is not None and Path(db_path).resolve() != self.db_path:
            # 如果已设置过 self.initialized=True (例如在之前的尝试中)，但 fully_initialized 未成功
            # 并且传入了不同的 db_path，这可能是一个需要警告或处理的情况。
            # 目前行为是：如果 fully_initialized 不是 True，则允许用新的 db_path 重试初始化。
            # 这里逻辑可能需要根据单例的具体期望行为调整。
            # 为了简单起见，如果 initialized 是 True 但 fully_initialized 不是 True，
            # 且收到了新的 db_path，我们允许它重新尝试上面的 try 块。
            # 但这需要重置 self.initialized=False 以便上面的 if not self.initialized 块能进入
            # 或者修改上面的条件。
            # 一个更简单的处理：如果已有一个 self.db_path，并且新的 db_path 不同，则警告。
             logger.warning(f"DatabaseService 正在使用路径 '{self.db_path}' 进行初始化或已部分初始化。忽略新的路径 '{db_path}'。")

    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接。"""
        # 这里的检查现在依赖于 self.initialized being True 和 self.db_path 的存在
        if not hasattr(self, 'initialized') or not self.initialized or not hasattr(self, 'db_path') or not self.db_path:
            logger.error("DatabaseService 尚未成功初始化或db_path未设置。无法获取数据库连接。")
            raise RuntimeError("DatabaseService 尚未成功初始化或db_path未设置。")
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


