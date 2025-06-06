"""
分配方案管理器
负责管理通道分配的业务逻辑
"""

import logging
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime

from .persistence.data_models import ParsedPoint, ChannelAssignment, PointChannelMapping
from ..data_storage.parsed_data_dao import ParsedDataDAO
from .persistence.assignment_dao import AssignmentDAO
from .channel_provider import ChannelProvider, ChannelInfo

logger = logging.getLogger(__name__)


class AssignmentManager:
    """分配方案管理器"""
    
    def __init__(self, data_dir: str = None):
        """初始化管理器"""
        self.parsed_data_dao = ParsedDataDAO(data_dir)
        self.assignment_dao = AssignmentDAO(data_dir)
        self.channel_provider = ChannelProvider()
        
        logger.info("AssignmentManager initialized")
    
    def create_assignment_scheme(self, project_id: str, scheme_name: str, 
                               description: str = "") -> Optional[str]:
        """创建新的分配方案"""
        # 验证项目是否存在
        project = self.parsed_data_dao.get_project(project_id)
        if project is None:
            logger.error(f"Project not found: {project_id}")
            return None
        
        # 检查方案名称是否重复
        existing_schemes = self.assignment_dao.list_assignments(project_id)
        for scheme in existing_schemes:
            if scheme.scheme_name == scheme_name:
                logger.error(f"Assignment scheme name already exists: {scheme_name}")
                return None
        
        scheme_id = self.assignment_dao.create_assignment(project_id, scheme_name, description)
        if scheme_id:
            logger.info(f"Created assignment scheme: {scheme_name} (ID: {scheme_id})")
        
        return scheme_id
    
    def assign_point_to_channel(self, project_id: str, scheme_id: str, 
                              point_id: str, channel_id: str) -> bool:
        """分配点位到通道"""
        # 获取点位信息
        points = self.parsed_data_dao.get_parsed_points(project_id)
        point = next((p for p in points if p.id == point_id), None)
        if point is None:
            logger.error(f"Point not found: {point_id}")
            return False
        
        # 验证通道
        channel_info = self.channel_provider.get_channel_info(channel_id)
        if channel_info is None:
            logger.error(f"Invalid channel: {channel_id}")
            return False
        
        # 检查信号类型匹配
        if point.signal_type != channel_info.type:
            logger.error(f"Signal type mismatch: point {point.signal_type} vs channel {channel_info.type}")
            return False
        
        # 检查通道是否已被使用
        used_channels = self.assignment_dao.get_used_channels(project_id, scheme_id)
        if channel_id in used_channels:
            logger.error(f"Channel already assigned: {channel_id}")
            return False
        
        # 执行分配
        success = self.assignment_dao.add_point_assignment(
            project_id, scheme_id, point_id, channel_id, channel_info.type
        )
        
        if success:
            logger.info(f"Assigned point {point.instrument_tag} to channel {channel_id}")
        
        return success
    
    def unassign_point(self, project_id: str, scheme_id: str, point_id: str) -> bool:
        """取消点位分配"""
        success = self.assignment_dao.remove_point_assignment(project_id, scheme_id, point_id)
        
        if success:
            logger.info(f"Unassigned point: {point_id}")
        
        return success
    
    def auto_assign_by_type(self, project_id: str, scheme_id: str,
                          signal_type: str = None, start_channel: str = None) -> Dict[str, any]:
        """按类型自动分配通道 - 优化版本，确保连续分配

        修复问题：
        1. 按信号类型顺序分配（AI, DI, AO, DO, COMM）确保连续性
        2. 对点位按仪表位号排序，确保分配顺序一致
        3. 为每种类型连续分配通道，避免跳跃和空隙
        """
        # 获取点位数据
        points = self.parsed_data_dao.get_parsed_points(project_id)
        if signal_type:
            points = [p for p in points if p.signal_type == signal_type]
        
        # 获取已使用的通道
        used_channels = set(self.assignment_dao.get_used_channels(project_id, scheme_id))
        
        # 获取已分配的点位
        assignment = self.assignment_dao.load_assignment(project_id, scheme_id)
        assigned_points = set()
        if assignment:
            assigned_points = {mapping.point_id for mapping in assignment.assignments}
        
        # 过滤未分配的点位
        unassigned_points = [p for p in points if p.id not in assigned_points]
        
        results = {
            'total_points': len(unassigned_points),
            'assigned': 0,
            'failed': 0,
            'assignments': [],
            'errors': []
        }
        
        # 按信号类型分组并排序（确保分配顺序一致）
        points_by_type = {}
        for point in unassigned_points:
            if point.signal_type not in points_by_type:
                points_by_type[point.signal_type] = []
            points_by_type[point.signal_type].append(point)

        # 对每种类型的点位按仪表位号排序，确保分配顺序一致
        for sig_type in points_by_type:
            points_by_type[sig_type].sort(key=lambda p: p.instrument_tag)

        # 按信号类型顺序分配（AI, DI, AO, DO, COMM）确保连续性
        type_order = ['AI', 'DI', 'AO', 'DO', 'COMM']
        sorted_types = []

        # 先添加有序的类型
        for t in type_order:
            if t in points_by_type:
                sorted_types.append(t)

        # 再添加其他类型
        for t in points_by_type:
            if t not in sorted_types:
                sorted_types.append(t)

        # 为每种类型连续分配通道
        for sig_type in sorted_types:
            type_points = points_by_type[sig_type]

            # 获取该类型的所有通道（按索引排序）
            all_channels = self.channel_provider.get_available_channels(sig_type, set())

            # 找到第一个可用的连续通道段
            available_channels = []
            for channel in all_channels:
                if channel.id not in used_channels:
                    available_channels.append(channel)

            # 如果指定了起始通道，从该通道开始
            if start_channel and sig_type == signal_type:
                start_info = self.channel_provider.get_channel_info(start_channel)
                if start_info and start_info.type == sig_type:
                    # 过滤出从起始通道开始的可用通道
                    available_channels = [ch for ch in available_channels if ch.index >= start_info.index]

            # 检查是否有足够的连续通道
            if len(available_channels) < len(type_points):
                error_msg = f"Not enough available {sig_type} channels: need {len(type_points)}, available {len(available_channels)}"
                results['errors'].append(error_msg)
                logger.warning(error_msg)
                # 仍然尝试分配可用的通道

            # 连续分配通道
            for i, point in enumerate(type_points):
                if i >= len(available_channels):
                    error_msg = f"No more available {sig_type} channels for point {point.instrument_tag}"
                    results['errors'].append(error_msg)
                    results['failed'] += 1
                    continue

                channel = available_channels[i]
                success = self.assignment_dao.add_point_assignment(
                    project_id, scheme_id, point.id, channel.id, channel.type
                )

                if success:
                    results['assigned'] += 1
                    results['assignments'].append({
                        'point_id': point.id,
                        'point_tag': point.instrument_tag,
                        'channel_id': channel.id
                    })
                    used_channels.add(channel.id)
                    logger.debug(f"Assigned {point.instrument_tag} to {channel.id}")
                else:
                    results['failed'] += 1
                    results['errors'].append(f"Failed to assign {point.instrument_tag} to {channel.id}")
        
        logger.info(f"Auto assignment completed: {results['assigned']} assigned, {results['failed']} failed")
        return results
    
    def get_assignment_overview(self, project_id: str, scheme_id: str) -> Dict[str, any]:
        """获取分配方案概览"""
        # 获取项目和方案信息
        project = self.parsed_data_dao.get_project(project_id)
        assignment = self.assignment_dao.load_assignment(project_id, scheme_id)
        
        if not project or not assignment:
            return {}
        
        # 统计信息
        total_points = len(project.parsed_points)
        assigned_points = len(assignment.assignments)
        
        # 按类型统计
        points_by_type = {}
        for point in project.parsed_points:
            if point.signal_type not in points_by_type:
                points_by_type[point.signal_type] = {'total': 0, 'assigned': 0}
            points_by_type[point.signal_type]['total'] += 1
        
        for mapping in assignment.assignments:
            if mapping.channel_type in points_by_type:
                points_by_type[mapping.channel_type]['assigned'] += 1
        
        # 通道使用统计
        used_channels = set(assignment.get_used_channels())
        channel_stats = self.channel_provider.get_channel_statistics(used_channels)
        
        return {
            'project_name': project.name,
            'scheme_name': assignment.scheme_name,
            'total_points': total_points,
            'assigned_points': assigned_points,
            'unassigned_points': total_points - assigned_points,
            'coverage': assigned_points / total_points if total_points > 0 else 0,
            'points_by_type': points_by_type,
            'channel_statistics': channel_stats,
            'created_at': assignment.created_at.isoformat(),
            'updated_at': assignment.updated_at.isoformat()
        }
    
    def validate_assignment_scheme(self, project_id: str, scheme_id: str) -> Dict[str, any]:
        """验证分配方案"""
        return self.assignment_dao.validate_assignment(project_id, scheme_id)
    
    def get_unassigned_points(self, project_id: str, scheme_id: str, 
                            signal_type: str = None) -> List[ParsedPoint]:
        """获取未分配的点位"""
        points = self.parsed_data_dao.get_parsed_points(project_id)
        assignment = self.assignment_dao.load_assignment(project_id, scheme_id)
        
        assigned_point_ids = set()
        if assignment:
            assigned_point_ids = {mapping.point_id for mapping in assignment.assignments}
        
        unassigned = [p for p in points if p.id not in assigned_point_ids]
        
        if signal_type:
            unassigned = [p for p in unassigned if p.signal_type == signal_type]
        
        return unassigned
    
    def get_available_channels_for_type(self, project_id: str, scheme_id: str, 
                                      signal_type: str) -> List[ChannelInfo]:
        """获取指定类型的可用通道"""
        used_channels = set(self.assignment_dao.get_used_channels(project_id, scheme_id))
        return self.channel_provider.get_available_channels(signal_type, used_channels)
    
    def suggest_optimal_assignment(self, project_id: str, scheme_id: str) -> Dict[str, any]:
        """建议最优分配方案"""
        # 获取未分配的点位
        unassigned_points = self.get_unassigned_points(project_id, scheme_id)
        
        # 按类型统计
        points_by_type = {}
        for point in unassigned_points:
            if point.signal_type not in points_by_type:
                points_by_type[point.signal_type] = 0
            points_by_type[point.signal_type] += 1
        
        # 获取已使用的通道
        used_channels = set(self.assignment_dao.get_used_channels(project_id, scheme_id))
        
        # 建议通道分配
        suggestions = self.channel_provider.suggest_channels_for_points(points_by_type, used_channels)
        
        return {
            'unassigned_points': len(unassigned_points),
            'points_by_type': points_by_type,
            'suggested_channels': suggestions,
            'feasible': all(len(channels) >= count for channels, count in 
                          zip(suggestions.values(), points_by_type.values()))
        }
