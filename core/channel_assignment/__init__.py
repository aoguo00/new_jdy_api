"""
通道分配模块
包含所有与通道分配相关的功能

主要组件：
- AssignmentManager: 分配方案管理器
- ChannelProvider: 通道提供器
- persistence: 数据持久化层
"""

from .assignment_manager import AssignmentManager
from .channel_provider import ChannelProvider, ChannelInfo
from .persistence import (
    AssignmentDAO,
    ParsedPoint,
    PointChannelMapping,
    ChannelAssignment,
    ProjectData
)

__all__ = [
    'AssignmentManager',
    'ChannelProvider',
    'ChannelInfo',
    'AssignmentDAO',
    'ParsedPoint',
    'PointChannelMapping',
    'ChannelAssignment',
    'ProjectData'
]
