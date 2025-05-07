"""模板管理模块，处理模板相关的所有操作"""
import logging
import sqlite3
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
from core.db_manipulate.db_manager import DBManager
from core.models.templates.models import DeviceTemplateModel, TemplatePointModel

logger = logging.getLogger(__name__)

class TemplateManager:
    """模板管理类，负责模板的所有操作，包括数据库访问"""
    _instance = None
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        """初始化模板管理器"""
        if not self.initialized:
            try:
                self.db = DBManager()
                self._init_tables()
                self.initialized = True
                logger.info("模板管理器初始化完成")
            except Exception as e:
                logger.error(f"模板管理器初始化失败: {e}")
                raise

    def _init_tables(self):
        """初始化数据库表"""
        try:
            # 创建模板表 (SQL语句中的字段名与模型属性名对应)
            self.db.execute('''
            CREATE TABLE IF NOT EXISTS third_device_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, -- 对应 DeviceTemplateModel.name
                prefix TEXT,             -- 对应 DeviceTemplateModel.prefix
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建模板点位表 (SQL语句中的字段名与模型属性名对应)
            self.db.execute('''
            CREATE TABLE IF NOT EXISTS third_device_template_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,      -- 外键
                var_suffix TEXT,          -- 对应 TemplatePointModel.var_suffix
                desc_suffix TEXT,         -- 对应 TemplatePointModel.desc_suffix
                data_type TEXT,           -- 对应 TemplatePointModel.data_type
                init_value TEXT DEFAULT '0', -- 对应 TemplatePointModel.init_value
                power_protection INTEGER DEFAULT 0, -- TemplatePointModel.power_protection
                forcible INTEGER DEFAULT 1,      -- TemplatePointModel.forcible
                soe_enabled INTEGER DEFAULT 0,   -- TemplatePointModel.soe_enabled
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES third_device_templates (id) ON DELETE CASCADE
            )
            ''')
            
            logger.info("模板数据库表初始化完成")
                
        except Exception as e:
            logger.error(f"初始化模板数据库失败: {e}")
            raise

    def _db_row_to_template_point_model(self, row: Dict[str, Any]) -> TemplatePointModel:
        return TemplatePointModel(
            id=row.get('id'),
            template_id=row.get('template_id'),
            var_suffix=row['var_suffix'],
            desc_suffix=row['desc_suffix'],
            data_type=row['data_type'],
            init_value=row.get('init_value', '0'),
            power_protection=row.get('power_protection', 0),
            forcible=row.get('forcible', 1),
            soe_enabled=row.get('soe_enabled', 0)
        )

    def _db_row_to_device_template_model(self, row: Dict[str, Any], points: List[TemplatePointModel] = None) -> DeviceTemplateModel:
        return DeviceTemplateModel(
            id=row['id'],
            name=row['name'],
            prefix=row.get('prefix'),
            points=points or [],
            created_at=row.get('created_at'), # TODO: Ensure datetime conversion if not handled by DBManager
            updated_at=row.get('updated_at')  # TODO: Ensure datetime conversion
        )

    def get_all_templates(self) -> List[DeviceTemplateModel]:
        """获取所有模板的基本信息 (不含点位详情)。"""
        try:
            logger.info("开始获取所有模板")
            # SQL字段名已经调整为与模型对应或在_db_row_to_device_template_model中处理
            template_rows = self.db.fetch_all('''
            SELECT id, name, prefix, created_at, updated_at
            FROM third_device_templates
            ORDER BY name ASC
            ''')
            
            templates = [self._db_row_to_device_template_model(row) for row in template_rows]
            logger.info(f"返回的模板列表 (模型): {len(templates)} 个")
            return templates
        except Exception as e:
            logger.error(f"获取所有模板失败: {e}")
            # raise # Re-raise or return empty list based on desired error handling
            return []

    def get_template_points(self, template_id: int) -> List[TemplatePointModel]:
        """获取指定模板的所有点位。"""
        point_rows = self.db.fetch_all('''
        SELECT id, template_id, var_suffix, desc_suffix, data_type, 
               init_value, power_protection, forcible, soe_enabled
        FROM third_device_template_points
        WHERE template_id = ?
        ''', (template_id,))
        return [self._db_row_to_template_point_model(row) for row in point_rows]

    def get_template(self, name: str) -> Optional[DeviceTemplateModel]:
        """根据名称获取模板及其所有点位。"""
        try:
            logger.info(f"开始获取模板: {name}")
            template_row = self.db.fetch_one('''
            SELECT id, name, prefix, created_at, updated_at
            FROM third_device_templates
            WHERE name = ?
            ''', (name,))
            
            if not template_row:
                logger.warning(f"未找到模板: {name}")
                return None

            points = self.get_template_points(template_row['id'])
            template = self._db_row_to_device_template_model(template_row, points)
            logger.info(f"返回的模板数据 (模型): {template.name}")
            return template
        except Exception as e:
            logger.error(f"获取模板 {name} 失败: {e}")
            return None # Or raise

    def get_template_by_id(self, template_id: int) -> Optional[DeviceTemplateModel]:
        """根据ID获取模板及其所有点位。"""
        try:
            logger.info(f"开始获取模板 ID: {template_id}")
            template_row = self.db.fetch_one('''
            SELECT id, name, prefix, created_at, updated_at
            FROM third_device_templates
            WHERE id = ?
            ''', (template_id,))
            
            if not template_row:
                logger.warning(f"未找到模板 ID: {template_id}")
                return None

            points = self.get_template_points(template_row['id'])
            template = self._db_row_to_device_template_model(template_row, points)
            logger.info(f"返回的模板数据 (模型) ID: {template.id}")
            return template
        except Exception as e:
            logger.error(f"获取模板失败 ID {template_id}: {e}")
            return None # Or raise

    def create_template(self, name: str, template_data: Dict[str, Any]) -> Optional[DeviceTemplateModel]:
        """
        创建新模板。
        template_data 字典结构: {'变量前缀': 'xxx', '点位': [{'变量名后缀': 'yy', '描述后缀': 'zz', '类型': 'AI'}, ...]}
        """
        try:
            logger.info(f"开始创建模板: {name}")
            # 检查模板名称是否已存在
            if self.get_template(name):
                logger.error(f"创建模板失败：模板名称 '{name}' 已存在。")
                raise ValueError(f"模板名称 '{name}' 已存在。")

            prefix = template_data.get('变量前缀')
            cursor = self.db.execute('''
            INSERT INTO third_device_templates (name, prefix, created_at, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (name, prefix))
            
            template_id = cursor.lastrowid
            if not template_id:
                 logger.error(f"创建模板 {name} 后无法获取 template_id")
                 raise Exception(f"创建模板 {name} 后无法获取 template_id")


            points_data = template_data.get('点位', [])
            if points_data:
                point_params_list = []
                for point_dict in points_data:
                    # TODO: 验证 point_dict 是否包含必要字段
                    point_params_list.append((
                        template_id,
                        point_dict.get('变量名后缀'), # var_suffix
                        point_dict.get('描述后缀'),   # desc_suffix
                        point_dict.get('类型'),       # data_type
                        point_dict.get('init_value', '0'),
                        point_dict.get('power_protection', 0),
                        point_dict.get('forcible', 1),
                        point_dict.get('soe_enabled', 0)
                    ))
                
                self.db.execute_many('''
                INSERT INTO third_device_template_points 
                (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', point_params_list)
            
            logger.info(f"模板 {name} 创建成功，ID: {template_id}")
            return self.get_template_by_id(template_id)
            
        except Exception as e:
            logger.error(f"创建模板 {name} 失败: {e}")
            # raise # Re-raise or return None based on desired error handling
            return None

    def update_template(self, template_id: int, template_data: Dict[str, Any]) -> Optional[DeviceTemplateModel]:
        """
        更新模板。
        template_data 字典结构: {'name': 'new_name', '变量前缀': 'xxx', '点位': [...]}
        """
        try:
            new_name = template_data['name'] # 必须提供 name
            logger.info(f"开始更新模板 ID: {template_id}，新名称: {new_name}")

            # 检查更新后的名称是否与另一个已存在的模板冲突
            existing_template_with_new_name = self.get_template(new_name)
            if existing_template_with_new_name and existing_template_with_new_name.id != template_id:
                logger.error(f"更新模板失败：模板名称 '{new_name}' 已被 ID 为 {existing_template_with_new_name.id} 的模板使用。")
                raise ValueError(f"模板名称 '{new_name}' 已被其他模板使用。")

            prefix = template_data.get('变量前缀')
            self.db.execute('''
            UPDATE third_device_templates
            SET name = ?, prefix = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (new_name, prefix, template_id))
            
            # 删除现有点位
            self.db.execute('''
            DELETE FROM third_device_template_points
            WHERE template_id = ?
            ''', (template_id,))
            
            # 插入新点位
            points_data = template_data.get('点位', [])
            if points_data:
                point_params_list = []
                for point_dict in points_data:
                    point_params_list.append((
                        template_id,
                        point_dict.get('变量名后缀'),
                        point_dict.get('描述后缀'),
                        point_dict.get('类型'),
                        point_dict.get('init_value', '0'),
                        point_dict.get('power_protection', 0),
                        point_dict.get('forcible', 1),
                        point_dict.get('soe_enabled', 0)
                    ))
                self.db.execute_many('''
                INSERT INTO third_device_template_points 
                (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', point_params_list)
            
            logger.info(f"模板 ID: {template_id} 更新成功")
            return self.get_template_by_id(template_id)
            
        except Exception as e:
            logger.error(f"更新模板 ID {template_id} 失败: {e}")
            # raise
            return None

    def delete_template(self, template_id: int) -> Tuple[bool, str]:
        """删除模板"""
        try:
            logger.info(f"开始删除模板 ID: {template_id}")
            # DBManager 的 execute 已经处理了外键级联删除，所以直接删除模板即可
            self.db.execute('''
            DELETE FROM third_device_templates
            WHERE id = ?
            ''', (template_id,))
            # 检查是否真的删除了 (可选)
            # if self.get_template_by_id(template_id) is None:
            logger.info(f"模板 ID: {template_id} 删除成功")
            return True, "模板删除成功"
            # else:
            #     logger.error(f"删除模板 ID: {template_id} 失败，记录仍然存在")
            #     return False, f"删除模板 ID: {template_id} 失败，记录仍然存在"
            
        except Exception as e:
            error_msg = f"删除模板 ID {template_id} 失败: {e}"
            logger.error(error_msg)
            return False, error_msg 