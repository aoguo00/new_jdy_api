"""
可用通道提供器
负责提供可用的PLC通道信息
"""

import logging
from typing import List, Dict, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ChannelInfo:
    """通道信息"""
    id: str          # 通道ID，如 AI-01
    type: str        # 通道类型：AI, DI, AO, DO
    index: int       # 通道索引
    description: str = ""  # 通道描述
    is_available: bool = True  # 是否可用


class ChannelProvider:
    """可用通道提供器"""
    
    def __init__(self):
        """初始化通道提供器"""
        # 默认通道配置
        self.channel_config = {
            'AI': {'count': 32, 'prefix': 'AI'},
            'DI': {'count': 64, 'prefix': 'DI'},
            'AO': {'count': 16, 'prefix': 'AO'},
            'DO': {'count': 32, 'prefix': 'DO'}
        }
        
        logger.info("ChannelProvider initialized with default configuration")
    
    def set_channel_config(self, config: Dict[str, Dict[str, any]]):
        """设置通道配置"""
        self.channel_config = config
        logger.info(f"Channel configuration updated: {config}")
    
    def get_available_channels(self, channel_type: str, used_channels: Set[str] = None) -> List[ChannelInfo]:
        """获取指定类型的可用通道"""
        if used_channels is None:
            used_channels = set()
        
        if channel_type not in self.channel_config:
            logger.warning(f"Unknown channel type: {channel_type}")
            return []
        
        config = self.channel_config[channel_type]
        channels = []
        
        for i in range(1, config['count'] + 1):
            channel_id = f"{config['prefix']}-{i:02d}"
            is_available = channel_id not in used_channels
            
            channel = ChannelInfo(
                id=channel_id,
                type=channel_type,
                index=i,
                description=f"{channel_type} Channel {i}",
                is_available=is_available
            )
            channels.append(channel)
        
        return channels
    
    def get_all_channels(self, used_channels: Set[str] = None) -> Dict[str, List[ChannelInfo]]:
        """获取所有类型的通道"""
        all_channels = {}
        
        for channel_type in self.channel_config.keys():
            all_channels[channel_type] = self.get_available_channels(channel_type, used_channels)
        
        return all_channels
    
    def get_next_available_channel(self, channel_type: str, used_channels: Set[str] = None) -> ChannelInfo:
        """获取下一个可用通道"""
        channels = self.get_available_channels(channel_type, used_channels)
        
        for channel in channels:
            if channel.is_available:
                return channel
        
        logger.warning(f"No available channels for type: {channel_type}")
        return None
    
    def get_channel_info(self, channel_id: str) -> ChannelInfo:
        """获取指定通道的信息"""
        # 解析通道ID
        parts = channel_id.split('-')
        if len(parts) != 2:
            logger.warning(f"Invalid channel ID format: {channel_id}")
            return None
        
        channel_type = parts[0]
        try:
            index = int(parts[1])
        except ValueError:
            logger.warning(f"Invalid channel index: {parts[1]}")
            return None
        
        if channel_type not in self.channel_config:
            logger.warning(f"Unknown channel type: {channel_type}")
            return None
        
        config = self.channel_config[channel_type]
        if index < 1 or index > config['count']:
            logger.warning(f"Channel index out of range: {index}")
            return None
        
        return ChannelInfo(
            id=channel_id,
            type=channel_type,
            index=index,
            description=f"{channel_type} Channel {index}"
        )
    
    def validate_channel(self, channel_id: str, channel_type: str = None) -> bool:
        """验证通道是否有效"""
        channel_info = self.get_channel_info(channel_id)
        if channel_info is None:
            return False
        
        if channel_type and channel_info.type != channel_type:
            return False
        
        return True
    
    def get_channel_statistics(self, used_channels: Set[str] = None) -> Dict[str, Dict[str, int]]:
        """获取通道使用统计"""
        if used_channels is None:
            used_channels = set()
        
        stats = {}
        
        for channel_type in self.channel_config.keys():
            config = self.channel_config[channel_type]
            total = config['count']
            
            # 计算已使用的通道数
            used_count = 0
            for channel_id in used_channels:
                if channel_id.startswith(f"{config['prefix']}-"):
                    used_count += 1
            
            stats[channel_type] = {
                'total': total,
                'used': used_count,
                'available': total - used_count,
                'usage_rate': used_count / total if total > 0 else 0
            }
        
        return stats
    
    def suggest_channels_for_points(self, points_by_type: Dict[str, int], 
                                  used_channels: Set[str] = None) -> Dict[str, List[str]]:
        """为点位建议通道分配"""
        if used_channels is None:
            used_channels = set()
        
        suggestions = {}
        
        for signal_type, count in points_by_type.items():
            if signal_type not in self.channel_config:
                logger.warning(f"Unknown signal type: {signal_type}")
                continue
            
            channels = self.get_available_channels(signal_type, used_channels)
            available_channels = [ch for ch in channels if ch.is_available]
            
            if len(available_channels) < count:
                logger.warning(f"Not enough available channels for {signal_type}: "
                             f"need {count}, available {len(available_channels)}")
            
            # 建议前N个可用通道
            suggested = [ch.id for ch in available_channels[:count]]
            suggestions[signal_type] = suggested
            
            # 更新已使用通道列表
            used_channels.update(suggested)
        
        return suggestions
