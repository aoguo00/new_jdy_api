"""
分配方案访问对象
负责通道分配方案的持久化存储和检索
"""

import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from .data_models import ChannelAssignment, PointChannelMapping, ProjectData
from .parsed_data_dao import ParsedDataDAO

logger = logging.getLogger(__name__)


class AssignmentDAO:
    """分配方案访问对象"""
    
    def __init__(self, data_dir: str = None):
        """初始化DAO"""
        if data_dir is None:
            # 默认使用项目根目录下的data文件夹
            project_root = Path(__file__).resolve().parents[2]
            data_dir = project_root / "data" / "parsed_documents"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 使用相同的数据源
        self.parsed_data_dao = ParsedDataDAO(data_dir)
        
        logger.info(f"AssignmentDAO initialized with data directory: {self.data_dir}")
    
    def save_assignment(self, assignment: ChannelAssignment) -> bool:
        """保存分配方案"""
        projects = self.parsed_data_dao._load_projects()
        
        if assignment.project_id not in projects:
            logger.warning(f"Project not found: {assignment.project_id}")
            return False
        
        project = projects[assignment.project_id]
        
        # 查找是否已存在相同ID的方案
        existing_index = -1
        for i, scheme in enumerate(project.assignment_schemes):
            if scheme.id == assignment.id:
                existing_index = i
                break
        
        if existing_index >= 0:
            # 更新现有方案
            assignment.updated_at = datetime.now()
            project.assignment_schemes[existing_index] = assignment
            logger.info(f"Updated assignment scheme: {assignment.scheme_name}")
        else:
            # 添加新方案
            project.assignment_schemes.append(assignment)
            logger.info(f"Added new assignment scheme: {assignment.scheme_name}")
        
        project.updated_at = datetime.now()
        self.parsed_data_dao._save_projects(projects)
        
        return True
    
    def load_assignment(self, project_id: str, scheme_id: str) -> Optional[ChannelAssignment]:
        """加载分配方案"""
        project = self.parsed_data_dao.get_project(project_id)
        if project is None:
            logger.warning(f"Project not found: {project_id}")
            return None
        
        for scheme in project.assignment_schemes:
            if scheme.id == scheme_id:
                return scheme
        
        logger.warning(f"Assignment scheme not found: {scheme_id}")
        return None
    
    def list_assignments(self, project_id: str) -> List[ChannelAssignment]:
        """列出项目的所有分配方案"""
        project = self.parsed_data_dao.get_project(project_id)
        if project is None:
            logger.warning(f"Project not found: {project_id}")
            return []
        
        return project.assignment_schemes
    
    def delete_assignment(self, project_id: str, scheme_id: str) -> bool:
        """删除分配方案"""
        projects = self.parsed_data_dao._load_projects()
        
        if project_id not in projects:
            logger.warning(f"Project not found: {project_id}")
            return False
        
        project = projects[project_id]
        original_count = len(project.assignment_schemes)
        project.assignment_schemes = [s for s in project.assignment_schemes if s.id != scheme_id]
        
        if len(project.assignment_schemes) == original_count:
            logger.warning(f"Assignment scheme not found: {scheme_id}")
            return False
        
        project.updated_at = datetime.now()
        self.parsed_data_dao._save_projects(projects)
        
        logger.info(f"Deleted assignment scheme: {scheme_id}")
        return True
    
    def create_assignment(self, project_id: str, scheme_name: str, description: str = "") -> Optional[str]:
        """创建新的分配方案"""
        project = self.parsed_data_dao.get_project(project_id)
        if project is None:
            logger.warning(f"Project not found: {project_id}")
            return None
        
        assignment = ChannelAssignment(
            project_id=project_id,
            scheme_name=scheme_name,
            description=description
        )
        
        if self.save_assignment(assignment):
            logger.info(f"Created new assignment scheme: {scheme_name} (ID: {assignment.id})")
            return assignment.id
        
        return None
    
    def add_point_assignment(self, project_id: str, scheme_id: str, 
                           point_id: str, channel_id: str, channel_type: str) -> bool:
        """添加点位分配"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return False
        
        # 检查通道是否已被使用
        used_channels = assignment.get_used_channels()
        if channel_id in used_channels:
            logger.warning(f"Channel {channel_id} is already assigned")
            return False
        
        # 移除该点位的现有分配（如果存在）
        assignment.remove_assignment(point_id)
        
        # 添加新分配
        assignment.add_assignment(point_id, channel_id, channel_type)
        
        return self.save_assignment(assignment)
    
    def remove_point_assignment(self, project_id: str, scheme_id: str, point_id: str) -> bool:
        """移除点位分配"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return False

        assignment.remove_assignment(point_id)
        return self.save_assignment(assignment)

    def clear_all_assignments(self, project_id: str, scheme_id: str) -> bool:
        """清空指定方案的所有分配"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return False

        assignment.assignments.clear()
        assignment.updated_at = datetime.now()
        return self.save_assignment(assignment)
    
    def get_point_assignment(self, project_id: str, scheme_id: str, point_id: str) -> Optional[PointChannelMapping]:
        """获取点位的分配信息"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return None
        
        return assignment.get_assignment(point_id)
    
    def get_used_channels(self, project_id: str, scheme_id: str) -> List[str]:
        """获取已使用的通道列表"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return []
        
        return assignment.get_used_channels()
    
    def get_assignments_by_type(self, project_id: str, scheme_id: str, channel_type: str) -> List[PointChannelMapping]:
        """按通道类型获取分配"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return []
        
        return assignment.get_assignments_by_type(channel_type)
    
    def validate_assignment(self, project_id: str, scheme_id: str) -> Dict[str, Any]:
        """验证分配方案"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return {'valid': False, 'errors': ['Assignment scheme not found']}
        
        errors = []
        warnings = []
        
        # 检查通道冲突
        used_channels = {}
        for mapping in assignment.assignments:
            if mapping.channel_id in used_channels:
                errors.append(f"Channel {mapping.channel_id} is assigned to multiple points")
            else:
                used_channels[mapping.channel_id] = mapping.point_id
        
        # 检查点位是否存在
        parsed_points = self.parsed_data_dao.get_parsed_points(project_id)
        point_ids = {point.id for point in parsed_points}
        
        for mapping in assignment.assignments:
            if mapping.point_id not in point_ids:
                warnings.append(f"Point {mapping.point_id} not found in parsed data")
        
        # 检查通道类型匹配
        for mapping in assignment.assignments:
            point = next((p for p in parsed_points if p.id == mapping.point_id), None)
            if point and point.signal_type != mapping.channel_type:
                warnings.append(f"Point {point.instrument_tag} signal type ({point.signal_type}) "
                              f"doesn't match channel type ({mapping.channel_type})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_assignments': len(assignment.assignments),
            'total_points': len(parsed_points),
            'coverage': len(assignment.assignments) / len(parsed_points) if parsed_points else 0
        }
    
    def update_assignments(self, scheme_id: str, assignments_dict: Dict[str, str]) -> bool:
        """批量更新分配方案的所有分配

        Args:
            scheme_id: 分配方案ID
            assignments_dict: 分配字典，格式为 {point_id: channel_id}

        Returns:
            bool: 更新是否成功
        """
        try:
            # 查找包含该方案的项目
            projects = self.parsed_data_dao._load_projects()
            target_project = None
            target_assignment = None

            for project in projects.values():
                for scheme in project.assignment_schemes:
                    if scheme.id == scheme_id:
                        target_project = project
                        target_assignment = scheme
                        break
                if target_assignment:
                    break

            if not target_assignment:
                logger.warning(f"Assignment scheme not found: {scheme_id}")
                return False

            # 清空现有分配
            target_assignment.assignments.clear()

            # 添加新的分配
            for point_id, channel_id in assignments_dict.items():
                # 从通道ID推断通道类型
                channel_type = self._infer_channel_type(channel_id)
                target_assignment.add_assignment(point_id, channel_id, channel_type)

            # 更新时间戳
            target_assignment.updated_at = datetime.now()
            target_project.updated_at = datetime.now()

            # 保存到文件
            self.parsed_data_dao._save_projects(projects)

            logger.info(f"Updated assignment scheme: {target_assignment.scheme_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update assignments: {e}")
            return False

    def _infer_channel_type(self, channel_id: str) -> str:
        """从通道ID推断通道类型"""
        if '_AI_' in channel_id:
            return 'AI'
        elif '_DI_' in channel_id:
            return 'DI'
        elif '_AO_' in channel_id:
            return 'AO'
        elif '_DO_' in channel_id:
            return 'DO'
        else:
            # 默认返回AI类型
            logger.warning(f"Cannot infer channel type from {channel_id}, defaulting to AI")
            return 'AI'

    def get_assignment_statistics(self, project_id: str, scheme_id: str) -> Dict[str, Any]:
        """获取分配方案统计信息"""
        assignment = self.load_assignment(project_id, scheme_id)
        if assignment is None:
            return {}

        stats = {
            'total_assignments': len(assignment.assignments),
            'by_type': {
                'AI': len(assignment.get_assignments_by_type('AI')),
                'DI': len(assignment.get_assignments_by_type('DI')),
                'AO': len(assignment.get_assignments_by_type('AO')),
                'DO': len(assignment.get_assignments_by_type('DO'))
            },
            'used_channels': assignment.get_used_channels(),
            'created_at': assignment.created_at.isoformat(),
            'updated_at': assignment.updated_at.isoformat()
        }

        return stats
