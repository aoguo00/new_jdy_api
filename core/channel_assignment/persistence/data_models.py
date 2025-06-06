"""
数据模型定义
定义解析数据和分配方案的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid


@dataclass
class ParsedPoint:
    """解析出的点位数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    instrument_tag: str = ""  # 仪表位号
    description: str = ""     # 描述
    signal_type: str = ""     # 信号类型 (AI, DI, AO, DO)
    io_type: str = ""         # IO类型
    units: str = ""           # 单位
    data_range: str = ""      # 数据范围
    signal_range: str = ""    # 信号范围
    power_supply: str = ""    # 供电类型
    isolation: str = ""       # 隔离
    remarks: str = ""         # 备注
    original_data: Dict[str, Any] = field(default_factory=dict)  # 原始解析数据
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'instrument_tag': self.instrument_tag,
            'description': self.description,
            'signal_type': self.signal_type,
            'io_type': self.io_type,
            'units': self.units,
            'data_range': self.data_range,
            'signal_range': self.signal_range,
            'power_supply': self.power_supply,
            'isolation': self.isolation,
            'remarks': self.remarks,
            'original_data': self.original_data,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedPoint':
        """从字典创建实例"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            project_id=data.get('project_id', ''),
            instrument_tag=data.get('instrument_tag', ''),
            description=data.get('description', ''),
            signal_type=data.get('signal_type', ''),
            io_type=data.get('io_type', ''),
            units=data.get('units', ''),
            data_range=data.get('data_range', ''),
            signal_range=data.get('signal_range', ''),
            power_supply=data.get('power_supply', ''),
            isolation=data.get('isolation', ''),
            remarks=data.get('remarks', ''),
            original_data=data.get('original_data', {}),
            created_at=created_at
        )


@dataclass
class PointChannelMapping:
    """点位通道映射关系"""
    point_id: str = ""
    channel_id: str = ""      # 如 AI-01, DI-15
    channel_type: str = ""    # AI, DI, AO, DO
    assigned_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'point_id': self.point_id,
            'channel_id': self.channel_id,
            'channel_type': self.channel_type,
            'assigned_at': self.assigned_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PointChannelMapping':
        """从字典创建实例"""
        assigned_at = data.get('assigned_at')
        if isinstance(assigned_at, str):
            assigned_at = datetime.fromisoformat(assigned_at)
        elif assigned_at is None:
            assigned_at = datetime.now()
            
        return cls(
            point_id=data.get('point_id', ''),
            channel_id=data.get('channel_id', ''),
            channel_type=data.get('channel_type', ''),
            assigned_at=assigned_at
        )


@dataclass
class ChannelAssignment:
    """通道分配方案"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str = ""
    scheme_name: str = ""     # 方案名称
    description: str = ""     # 方案描述
    assignments: List[PointChannelMapping] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'scheme_name': self.scheme_name,
            'description': self.description,
            'assignments': [mapping.to_dict() for mapping in self.assignments],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ChannelAssignment':
        """从字典创建实例"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
            
        assignments = []
        for mapping_data in data.get('assignments', []):
            assignments.append(PointChannelMapping.from_dict(mapping_data))
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            project_id=data.get('project_id', ''),
            scheme_name=data.get('scheme_name', ''),
            description=data.get('description', ''),
            assignments=assignments,
            created_at=created_at,
            updated_at=updated_at
        )
    
    def add_assignment(self, point_id: str, channel_id: str, channel_type: str):
        """添加点位分配"""
        mapping = PointChannelMapping(
            point_id=point_id,
            channel_id=channel_id,
            channel_type=channel_type
        )
        self.assignments.append(mapping)
        self.updated_at = datetime.now()
    
    def remove_assignment(self, point_id: str):
        """移除点位分配"""
        self.assignments = [a for a in self.assignments if a.point_id != point_id]
        self.updated_at = datetime.now()
    
    def get_assignment(self, point_id: str) -> Optional[PointChannelMapping]:
        """获取指定点位的分配"""
        for assignment in self.assignments:
            if assignment.point_id == point_id:
                return assignment
        return None
    
    def get_used_channels(self) -> List[str]:
        """获取已使用的通道列表"""
        return [assignment.channel_id for assignment in self.assignments]
    
    def get_assignments_by_type(self, channel_type: str) -> List[PointChannelMapping]:
        """按通道类型获取分配"""
        return [a for a in self.assignments if a.channel_type == channel_type]


@dataclass
class ProjectData:
    """项目数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    parsed_points: List[ParsedPoint] = field(default_factory=list)
    assignment_schemes: List[ChannelAssignment] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parsed_points': [point.to_dict() for point in self.parsed_points],
            'assignment_schemes': [scheme.to_dict() for scheme in self.assignment_schemes],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectData':
        """从字典创建实例"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
            
        updated_at = data.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.now()
            
        parsed_points = []
        for point_data in data.get('parsed_points', []):
            parsed_points.append(ParsedPoint.from_dict(point_data))
            
        assignment_schemes = []
        for scheme_data in data.get('assignment_schemes', []):
            assignment_schemes.append(ChannelAssignment.from_dict(scheme_data))
            
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            name=data.get('name', ''),
            description=data.get('description', ''),
            parsed_points=parsed_points,
            assignment_schemes=assignment_schemes,
            created_at=created_at,
            updated_at=updated_at
        )
