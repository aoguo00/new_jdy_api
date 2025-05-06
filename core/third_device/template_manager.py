"""模板管理模块，处理模板相关的业务逻辑"""
import logging
from pathlib import Path
from core.third_device import template_db

logger = logging.getLogger(__name__)

class TemplateManager:
    """模板管理类，负责模板相关的业务逻辑"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.initialized = False
            logger.info("创建新的TemplateManager实例")
        return cls._instance

    def __init__(self):
        """初始化模板管理器"""
        if not self.initialized:
            try:
                # 初始化模板数据库
                template_db.init_db()
                self.initialized = True
                logger.info("TemplateManager初始化完成")
            except Exception as e:
                logger.error(f"TemplateManager初始化失败: {e}")
                raise

    def get_all_templates(self):
        """获取所有模板"""
        try:
            logger.info("开始获取所有模板")
            templates = template_db.get_all_templates()
            logger.info(f"获取到 {len(templates)} 个模板")
            return templates
        except Exception as e:
            logger.error(f"获取所有模板失败: {e}")
            raise

    def get_template_by_id(self, template_id):
        """根据ID获取模板"""
        try:
            logger.info(f"开始获取模板 ID: {template_id}")
            template = template_db.get_template_by_id(template_id)
            if template:
                logger.info(f"成功获取模板: {template.get('name', 'unknown')}")
            else:
                logger.warning(f"未找到模板 ID: {template_id}")
            return template
        except Exception as e:
            logger.error(f"获取模板失败 ID {template_id}: {e}")
            raise

    def get_template_by_name(self, name):
        """根据名称获取模板"""
        return template_db.get_template(name)

    def add_template(self, name, template_data):
        """添加模板"""
        return template_db.add_template(name, template_data)

    def update_template(self, template_id, template_data):
        """更新模板"""
        return template_db.update_template(template_id, template_data)

    def delete_template(self, template_id):
        """删除模板"""
        return template_db.delete_template(template_id)

    def copy_template(self, template_id, new_name):
        """复制模板"""
        return template_db.copy_template(template_id, new_name)
