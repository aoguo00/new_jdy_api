"""模板管理模块，处理模板相关的所有操作"""
import logging
import sqlite3
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from core.db_manipulate.db_manager import DBManager

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
            # 创建模板表
            self.db.execute('''
            CREATE TABLE IF NOT EXISTS third_device_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prefix TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # 创建模板点位表
            self.db.execute('''
            CREATE TABLE IF NOT EXISTS third_device_template_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                var_suffix TEXT,
                desc_suffix TEXT,
                data_type TEXT,
                init_value TEXT DEFAULT '0',
                power_protection INTEGER DEFAULT 0,
                forcible INTEGER DEFAULT 1,
                soe_enabled INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES third_device_templates (id) ON DELETE CASCADE
            )
            ''')
            
            logger.info("模板数据库表初始化完成")
                
        except Exception as e:
            logger.error(f"初始化模板数据库失败: {e}")
            raise

    def get_all_templates(self) -> List[Dict]:
        """获取所有模板"""
        try:
            logger.info("开始获取所有模板")
            templates = self.db.fetch_all('''
            SELECT id, name, prefix
            FROM third_device_templates
            ORDER BY name ASC
            ''')
            
            logger.info(f"从数据库获取到的模板数据: {templates}")
            
            result = [{
                'id': template['id'],
                'name': template['name'],
                'type': "用户模板",
                '变量前缀': template['prefix']
            } for template in templates]
            
            logger.info(f"返回的模板列表: {result}")
            return result
        except Exception as e:
            logger.error(f"获取所有模板失败: {e}")
            raise

    def get_template(self, name: str) -> Optional[Dict]:
        """根据名称获取模板"""
        try:
            logger.info(f"开始获取模板: {name}")
            # 获取模板基本信息
            template = self.db.fetch_one('''
            SELECT id, name, prefix
            FROM third_device_templates
            WHERE name = ?
            ''', (name,))
            
            logger.info(f"获取到的模板基本信息: {template}")
            
            if not template:
                logger.warning(f"未找到模板: {name}")
                return None

            # 获取模板点位
            points = self.db.fetch_all('''
            SELECT var_suffix, desc_suffix, data_type
            FROM third_device_template_points
            WHERE template_id = ?
            ''', (template['id'],))
            
            logger.info(f"获取到的模板点位: {points}")

            # 构建模板对象
            result = {
                'id': template['id'],
                'name': template['name'],
                '变量前缀': template['prefix'],
                '点位': [{
                    '变量名后缀': point['var_suffix'],
                    '描述后缀': point['desc_suffix'],
                    '类型': point['data_type']
                } for point in points]
            }
            
            logger.info(f"返回的模板数据: {result}")
            return result
        except Exception as e:
            logger.error(f"获取模板 {name} 失败: {e}")
            raise

    def get_template_by_id(self, template_id: int) -> Optional[Dict]:
        """根据ID获取模板"""
        try:
            template = self.db.fetch_one('''
            SELECT name FROM third_device_templates WHERE id = ?
            ''', (template_id,))
            
            if not template:
                return None
                
            return self.get_template(template['name'])
            
        except Exception as e:
            logger.error(f"获取模板失败 ID {template_id}: {e}")
            raise

    def create_template(self, name: str, template_data: Dict) -> Dict:
        """创建新模板"""
        try:
            # 插入模板基本信息
            self.db.execute('''
            INSERT INTO third_device_templates (name, prefix)
            VALUES (?, ?)
            ''', (name, template_data.get('变量前缀')))
            
            # 获取新插入的模板ID
            template = self.db.fetch_one('''
            SELECT id FROM third_device_templates WHERE name = ?
            ''', (name,))
            
            template_id = template['id']
            
            # 插入模板点位
            if '点位' in template_data:
                for point in template_data['点位']:
                    self.db.execute('''
                    INSERT INTO third_device_template_points (
                        template_id, var_suffix, desc_suffix, data_type
                    ) VALUES (?, ?, ?, ?)
                    ''', (
                        template_id,
                        point['变量名后缀'],
                        point['描述后缀'],
                        point['类型']
                    ))
            
            return self.get_template(name)
            
        except Exception as e:
            logger.error(f"创建模板失败: {e}")
            raise

    def update_template(self, template_id: int, template_data: Dict) -> Dict:
        """更新模板"""
        try:
            name = template_data['name']
            
            # 更新模板基本信息
            self.db.execute('''
            UPDATE third_device_templates
            SET name = ?, prefix = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            ''', (name, template_data.get('变量前缀', ''), template_id))
            
            # 删除现有点位
            self.db.execute('''
            DELETE FROM third_device_template_points
            WHERE template_id = ?
            ''', (template_id,))
            
            # 插入新点位
            if '点位' in template_data:
                for point in template_data['点位']:
                    self.db.execute('''
                    INSERT INTO third_device_template_points (
                        template_id, var_suffix, desc_suffix, data_type
                    ) VALUES (?, ?, ?, ?)
                    ''', (
                        template_id,
                        point['变量名后缀'],
                        point['描述后缀'],
                        point['类型']
                    ))
            
            return self.get_template(name)
            
        except Exception as e:
            logger.error(f"更新模板失败: {e}")
            raise

    def delete_template(self, template_id: int) -> Tuple[bool, str]:
        """删除模板"""
        try:
            self.db.execute('''
            DELETE FROM third_device_templates
            WHERE id = ?
            ''', (template_id,))
            return True, "模板删除成功"
            
        except Exception as e:
            error_msg = f"删除模板失败: {e}"
            logger.error(error_msg)
            return False, error_msg 