"""设备模板业务服务"""
import logging
from typing import List, Optional, Dict, Any

# DAO 和领域模型
from .database.dao import TemplateDAO
from .models.template_models import DeviceTemplateModel, TemplatePointModel

logger = logging.getLogger(__name__)

class TemplateService:
    """处理设备模板相关的业务逻辑，依赖TemplateDAO进行数据持久化。"""

    def __init__(self, template_dao: TemplateDAO):
        if not template_dao:
            logger.error("TemplateService 初始化失败: 未提供 TemplateDAO 实例。")
            raise ValueError("TemplateDAO 实例是必需的")
        self.template_dao = template_dao
        logger.info("TemplateService 初始化完成。")

    def get_all_templates(self) -> List[DeviceTemplateModel]:
        """获取所有模板的基本信息 (不含点位)。"""
        try:
            return self.template_dao.get_all_templates()
        except Exception as e:
            logger.error(f"服务层获取所有模板失败: {e}", exc_info=True)
            return []

    def get_template_by_id(self, template_id: int) -> Optional[DeviceTemplateModel]:
        """根据ID获取模板，包含点位详情。"""
        try:
            return self.template_dao.get_template_by_id(template_id)
        except Exception as e:
            logger.error(f"服务层获取模板ID {template_id} 失败: {e}", exc_info=True)
            return None

    def get_template_by_name(self, name: str) -> Optional[DeviceTemplateModel]:
        """根据名称获取模板，包含点位详情。"""
        try:
            return self.template_dao.get_template_by_name(name)
        except Exception as e:
            logger.error(f"服务层获取模板名称 '{name}' 失败: {e}", exc_info=True)
            return None

    def create_template(self, name: str, prefix: Optional[str], points_data: List[Dict[str, Any]]) -> Optional[DeviceTemplateModel]:
        """创建新模板及其点位。"""
        try:
            # Pydantic V2: model_validate (formerly from_dict/construct)
            points = [TemplatePointModel.model_validate(p_data) for p_data in points_data]
        except Exception as e: # Pydantic validation error
            logger.error(f"创建模板 '{name}' 失败：点位数据无效: {e}", exc_info=True)
            raise ValueError(f"点位数据无效: {e}") from e

        try:
            template_data = DeviceTemplateModel(name=name, prefix=prefix, points=points)
            # 调用DAO进行事务性创建 (DAO会处理名称唯一性检查)
            return self.template_dao.create_template_with_points(template_data)
        except ValueError as ve:
            raise ve # 重名等错误由DAO抛出并传递
        except Exception as e:
            logger.error(f"服务层创建模板 '{name}' 失败: {e}", exc_info=True)
            return None

    def update_template(self, template_id: int, name: str, prefix: Optional[str], points_data: List[Dict[str, Any]]) -> Optional[DeviceTemplateModel]:
        """更新模板及其点位。"""
        # 服务层检查：名称是否与其他模板冲突 (如果名称改变了)
        existing_template = self.get_template_by_id(template_id)
        if not existing_template:
            logger.warning(f"更新模板失败：ID {template_id} 不存在。")
            return None # 或者 raise NotFoundError
        if name != existing_template.name and self.get_template_by_name(name):
             logger.warning(f"更新模板失败：新名称 '{name}' 已被其他模板使用。")
             raise ValueError(f"模板名称 '{name}' 已被其他模板使用。")

        try:
            points = [TemplatePointModel.model_validate(p_data) for p_data in points_data]
        except Exception as e: # Pydantic validation error
            logger.error(f"更新模板 '{name}' 失败：点位数据无效: {e}", exc_info=True)
            raise ValueError(f"点位数据无效: {e}") from e

        try:
            template_update_data = DeviceTemplateModel(id=template_id, name=name, prefix=prefix, points=points)
            # 调用DAO进行事务性更新 (DAO会再次检查名称唯一性以防并发问题)
            return self.template_dao.update_template_with_points(template_id, template_update_data)
        except ValueError as ve:
             raise ve # 从DAO层传递上来的
        except Exception as e:
            logger.error(f"服务层更新模板 ID {template_id} 失败: {e}", exc_info=True)
            return None

    def delete_template(self, template_id: int) -> bool:
        """删除模板及其关联点位。"""
        try:
            # 可选：先检查模板是否存在，DAO层也会检查
            if not self.template_dao.get_template_by_id(template_id):
                logger.warning(f"尝试删除不存在的模板 ID: {template_id}")
                return False
            return self.template_dao.delete_template(template_id)
        except Exception as e:
            logger.error(f"服务层删除模板 ID {template_id} 失败: {e}", exc_info=True)
            return False 