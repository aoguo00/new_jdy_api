"""设备模板数据库操作模块"""
import sqlite3
import os
import json
import logging
from pathlib import Path
from core.db.database import Database

logger = logging.getLogger(__name__)

class TemplateDatabase(Database):
    """模板数据库类"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            db_path = Path(__file__).parent / 'templates.db'
            cls._instance = super().__new__(cls)
            # 在这里不要设置属性，应该在__init__中设置
        return cls._instance

    def __init__(self):
        """初始化模板数据库"""
        if not hasattr(self, 'initialized'):
            db_path = Path(__file__).parent / 'templates.db'
            super().__init__(db_path)
            self.initialized = True
            logger.info(f"模板数据库初始化完成: {db_path}")

# 创建全局Database实例
_db = None

def get_db():
    """获取数据库实例"""
    global _db
    if _db is None:
        _db = TemplateDatabase()
    return _db

def init_db():
    """初始化数据库"""
    db = get_db()
    logger.info(f"初始化数据库: {db.db_path}")
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 创建模板表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                identifier TEXT NOT NULL,
                prefix TEXT
            )
            ''')

            # 创建模板点位表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS template_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER,
                var_suffix TEXT,
                desc_suffix TEXT,
                data_type TEXT,
                init_value TEXT DEFAULT '0',
                power_protection INTEGER DEFAULT 0,
                forcible INTEGER DEFAULT 1,
                soe_enabled INTEGER DEFAULT 0,
                FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE
            )
            ''')
            conn.commit()
            logger.info("数据库表创建完成")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        raise

def get_all_template_names():
    """获取所有模板名称"""
    try:
        templates = get_db().fetch_all('SELECT name FROM templates ORDER BY name')
        return [template['name'] for template in templates]
    except Exception as e:
        logger.error(f"获取模板名称列表失败: {e}")
        raise

def get_all_templates():
    """获取所有模板"""
    try:
        templates = get_db().fetch_all('''
        SELECT id, name, identifier
        FROM templates
        ORDER BY name ASC
        ''')
        
        return [{
            'id': template['id'],
            'name': template['name'],
            'identifier': template['identifier'],
            'type': "用户模板"
        } for template in templates]
    except Exception as e:
        logger.error(f"获取所有模板失败: {e}")
        raise

def get_template(name):
    """根据名称获取模板"""
    try:
        db = get_db()
        # 获取模板基本信息
        template = db.fetch_one('''
        SELECT id, name, identifier, prefix
        FROM templates
        WHERE name = ?
        ''', (name,))
        
        if not template:
            return None

        # 获取模板点位
        points = db.fetch_all('''
        SELECT var_suffix, desc_suffix, data_type
        FROM template_points
        WHERE template_id = ?
        ''', (template['id'],))

        # 构建模板对象
        return {
            'id': template['id'],
            'name': template['name'],
            '标识符': template['identifier'],
            '变量前缀': template['prefix'],
            '点位': [{
                '变量名后缀': point['var_suffix'],
                '描述后缀': point['desc_suffix'],
                '类型': point['data_type']
            } for point in points]
        }
    except Exception as e:
        logger.error(f"获取模板 {name} 失败: {e}")
        raise

def add_template(name, template_data):
    """添加一个新模板"""
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 获取模板基本信息
            identifier = template_data.get('标识符', '')
            prefix = template_data.get('变量前缀', '')

            # 插入模板
            cursor.execute('''
            INSERT INTO templates (name, identifier, prefix)
            VALUES (?, ?, ?)
            ''', (name, identifier, prefix))

            template_id = cursor.lastrowid

            # 插入点位
            if '点位' in template_data:
                for point in template_data['点位']:
                    var_suffix = point.get('变量名后缀', '')
                    desc_suffix = point.get('描述后缀', '')
                    data_type = point.get('类型', 'BOOL')
                    init_value = "0" if data_type in ("BOOL", "INT", "DINT") else "0.0"

                    cursor.execute('''
                    INSERT INTO template_points (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (template_id, var_suffix, desc_suffix, data_type, init_value, 0, 1, 0))

            conn.commit()
            return template_id

    except Exception as e:
        logger.error(f"添加模板失败: {e}")
        raise

def update_template(template_id, template_data):
    """更新模板"""
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 更新模板基本信息
            name = template_data.get('name', '')
            identifier = template_data.get('标识符', '')
            prefix = template_data.get('变量前缀', '')

            cursor.execute('''
            UPDATE templates
            SET name = ?, identifier = ?, prefix = ?
            WHERE id = ?
            ''', (name, identifier, prefix, template_id))

            # 删除现有点位
            cursor.execute('DELETE FROM template_points WHERE template_id = ?', (template_id,))

            # 添加新点位
            if '点位' in template_data:
                for point in template_data['点位']:
                    var_suffix = point.get('变量名后缀', '')
                    desc_suffix = point.get('描述后缀', '')
                    data_type = point.get('类型', 'BOOL')
                    init_value = "0" if data_type in ("BOOL", "INT", "DINT") else "0.0"

                    cursor.execute('''
                    INSERT INTO template_points (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (template_id, var_suffix, desc_suffix, data_type, init_value, 0, 1, 0))

            conn.commit()
            return True

    except Exception as e:
        logger.error(f"更新模板失败: {e}")
        raise

def delete_template(template_id):
    """删除模板"""
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 检查模板是否存在
            cursor.execute('SELECT id FROM templates WHERE id = ?', (template_id,))
            row = cursor.fetchone()

            if not row:
                return False, "模板不存在"

            # 删除模板点位
            cursor.execute('DELETE FROM template_points WHERE template_id = ?', (template_id,))
            # 删除模板
            cursor.execute('DELETE FROM templates WHERE id = ?', (template_id,))
            conn.commit()
            return True, "模板已删除"

    except Exception as e:
        logger.error(f"删除模板失败: {e}")
        raise

def copy_template(template_id, new_name):
    """复制模板"""
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 获取原模板信息
            cursor.execute('''
            SELECT name, identifier, prefix
            FROM templates
            WHERE id = ?
            ''', (template_id,))

            template_row = cursor.fetchone()
            if not template_row:
                return None

            _, identifier, prefix = template_row

            # 创建新模板
            cursor.execute('''
            INSERT INTO templates (name, identifier, prefix)
            VALUES (?, ?, ?)
            ''', (new_name, identifier, prefix))

            new_template_id = cursor.lastrowid

            # 获取原模板点位
            cursor.execute('''
            SELECT var_suffix, desc_suffix, data_type
            FROM template_points
            WHERE template_id = ?
            ''', (template_id,))

            # 复制点位
            for point_row in cursor.fetchall():
                var_suffix, desc_suffix, data_type = point_row
                init_value = "0" if data_type in ("BOOL", "INT", "DINT") else "0.0"

                cursor.execute('''
                INSERT INTO template_points (template_id, var_suffix, desc_suffix, data_type, init_value, power_protection, forcible, soe_enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (new_template_id, var_suffix, desc_suffix, data_type, init_value, 0, 1, 0))

            conn.commit()
            return new_template_id

    except Exception as e:
        logger.error(f"复制模板失败: {e}")
        raise

def get_template_by_id(template_id):
    """根据ID获取模板"""
    db = get_db()
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            # 获取模板基本信息
            cursor.execute('''
            SELECT id, name, identifier, prefix
            FROM templates
            WHERE id = ?
            ''', (template_id,))

            template_row = cursor.fetchone()
            if not template_row:
                return None

            template_id, name, identifier, prefix = template_row

            # 获取模板点位
            cursor.execute('''
            SELECT var_suffix, desc_suffix, data_type
            FROM template_points
            WHERE template_id = ?
            ''', (template_id,))

            points = []
            for point_row in cursor.fetchall():
                var_suffix, desc_suffix, data_type = point_row
                points.append({
                    '变量名后缀': var_suffix,
                    '描述后缀': desc_suffix,
                    '类型': data_type
                })

            # 构建模板对象
            template = {
                'id': template_id,
                'name': name,
                '标识符': identifier,
                '变量前缀': prefix,
                '点位': points
            }

            return template

    except Exception as e:
        logger.error(f"获取模板失败: {e}")
        raise
