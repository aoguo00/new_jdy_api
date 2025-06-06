"""
解析数据访问对象
负责解析数据的持久化存储和检索
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .data_models import ParsedPoint, ProjectData

logger = logging.getLogger(__name__)


class ParsedDataDAO:
    """解析数据访问对象"""
    
    def __init__(self, data_dir: str = None):
        """初始化DAO"""
        if data_dir is None:
            # 默认使用项目根目录下的data文件夹
            project_root = Path(__file__).resolve().parents[2]
            data_dir = project_root / "data" / "parsed_documents"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 项目数据文件
        self.projects_file = self.data_dir / "projects.json"
        
        logger.info(f"ParsedDataDAO initialized with data directory: {self.data_dir}")
    
    def _load_projects(self) -> Dict[str, ProjectData]:
        """加载所有项目数据"""
        if not self.projects_file.exists():
            return {}
        
        try:
            with open(self.projects_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            projects = {}
            for project_id, project_data in data.items():
                projects[project_id] = ProjectData.from_dict(project_data)
            
            return projects
        except Exception as e:
            logger.error(f"Failed to load projects: {e}")
            return {}
    
    def _save_projects(self, projects: Dict[str, ProjectData]):
        """保存所有项目数据"""
        try:
            data = {}
            for project_id, project in projects.items():
                data[project_id] = project.to_dict()
            
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved {len(projects)} projects to {self.projects_file}")
        except Exception as e:
            logger.error(f"Failed to save projects: {e}")
            raise
    
    def create_project(self, name: str, description: str = "") -> str:
        """创建新项目"""
        projects = self._load_projects()
        
        project = ProjectData(
            name=name,
            description=description
        )
        
        projects[project.id] = project
        self._save_projects(projects)
        
        logger.info(f"Created new project: {name} (ID: {project.id})")
        return project.id
    
    def get_project(self, project_id: str) -> Optional[ProjectData]:
        """获取项目数据"""
        projects = self._load_projects()
        return projects.get(project_id)
    
    def list_projects(self) -> List[ProjectData]:
        """列出所有项目"""
        projects = self._load_projects()
        return list(projects.values())
    
    def update_project(self, project_id: str, name: str = None, description: str = None) -> bool:
        """更新项目信息"""
        projects = self._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        project = projects[project_id]
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        
        project.updated_at = datetime.now()
        
        self._save_projects(projects)
        logger.info(f"Updated project: {project_id}")
        return True
    
    def delete_project(self, project_id: str) -> bool:
        """删除项目"""
        projects = self._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        del projects[project_id]
        self._save_projects(projects)
        
        logger.info(f"Deleted project: {project_id}")
        return True
    
    def save_parsed_points(self, project_id: str, points: List[ParsedPoint]) -> bool:
        """保存解析的点位数据"""
        projects = self._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        # 设置项目ID
        for point in points:
            point.project_id = project_id
        
        project = projects[project_id]
        project.parsed_points = points
        project.updated_at = datetime.now()
        
        self._save_projects(projects)
        
        logger.info(f"Saved {len(points)} parsed points to project {project_id}")
        return True
    
    def get_parsed_points(self, project_id: str) -> List[ParsedPoint]:
        """获取项目的解析点位数据"""
        project = self.get_project(project_id)
        if project is None:
            logger.warning(f"Project not found: {project_id}")
            return []
        
        return project.parsed_points
    
    def add_parsed_points(self, project_id: str, points: List[ParsedPoint]) -> bool:
        """添加解析的点位数据（追加模式）"""
        projects = self._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        # 设置项目ID
        for point in points:
            point.project_id = project_id
        
        project = projects[project_id]
        project.parsed_points.extend(points)
        project.updated_at = datetime.now()
        
        self._save_projects(projects)
        
        logger.info(f"Added {len(points)} parsed points to project {project_id}")
        return True
    
    def delete_parsed_point(self, project_id: str, point_id: str) -> bool:
        """删除指定的解析点位"""
        projects = self._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        project = projects[project_id]
        original_count = len(project.parsed_points)
        project.parsed_points = [p for p in project.parsed_points if p.id != point_id]
        
        if len(project.parsed_points) == original_count:
            logger.warning(f"Point not found: {point_id}")
            return False
        
        project.updated_at = datetime.now()
        self._save_projects(projects)
        
        logger.info(f"Deleted point {point_id} from project {project_id}")
        return True
    
    def find_points_by_tag(self, project_id: str, instrument_tag: str) -> List[ParsedPoint]:
        """根据仪表位号查找点位"""
        points = self.get_parsed_points(project_id)
        return [p for p in points if p.instrument_tag == instrument_tag]
    
    def find_points_by_type(self, project_id: str, signal_type: str) -> List[ParsedPoint]:
        """根据信号类型查找点位"""
        points = self.get_parsed_points(project_id)
        return [p for p in points if p.signal_type == signal_type]
    
    def get_points_statistics(self, project_id: str) -> Dict[str, int]:
        """获取点位统计信息"""
        points = self.get_parsed_points(project_id)
        
        stats = {
            'total': len(points),
            'AI': 0,
            'DI': 0,
            'AO': 0,
            'DO': 0,
            'COMM': 0
        }
        
        for point in points:
            signal_type = point.signal_type
            if signal_type in stats:
                stats[signal_type] += 1
        
        return stats
