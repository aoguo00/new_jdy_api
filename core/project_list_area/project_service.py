"""项目列表服务，负责获取和处理项目数据"""

from typing import List, Dict, Any, Optional
import logging

# 依赖 API 客户端和数据处理器
from core.query_area import JianDaoYunAPI
from .project_processor import format_project_data_for_ui

logger = logging.getLogger(__name__)

class ProjectService:
    def __init__(self, jdy_api: JianDaoYunAPI):
        if not jdy_api:
            logger.error("ProjectService 初始化失败: 未提供 JianDaoYunAPI 实例。")
            raise ValueError("JianDaoYunAPI 实例是必需的")
        self.jdy_api = jdy_api
        logger.info("ProjectService 初始化完成。")

    def get_formatted_projects(self, project_no: str = None, site_no: str = None) -> List[Dict[str, Any]]:
        """获取并格式化项目列表数据以供UI使用。"""
        try:
            logger.info(f"ProjectService: 开始查询项目数据 (项目号: {project_no}, 场站号: {site_no})")
            # 1. 调用 API 获取原始数据
            raw_data = self.jdy_api.query_data(project_no=project_no, site_no=site_no)
            
            # 2. 调用处理器格式化数据
            formatted_data = format_project_data_for_ui(raw_data)
            logger.info(f"ProjectService: 查询并格式化了 {len(formatted_data)} 条项目数据。")
            return formatted_data
        except Exception as e:
            # API 层或处理层应该已经记录了具体错误
            logger.error(f"ProjectService 获取项目数据失败: {e}", exc_info=True)
            # 向上层抛出异常或返回空列表，让调用者处理
            # raise # 或者根据策略返回空列表
            return [] 