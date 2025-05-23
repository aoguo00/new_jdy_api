# -*- coding: utf-8 -*-
"""
PLC配置数据模型

定义穿梭框和PLC模块相关的数据结构
对应Angular TransferItem接口
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Dict
from enum import Enum


class TransferDirection(Enum):
    """穿梭框方向枚举"""
    LEFT = "left"       # 左侧（可用）
    RIGHT = "right"     # 右侧（已选）


@dataclass
class TransferItem:
    """
    穿梭框数据项 - 对应Angular的TransferItem接口
    
    复刻ng-zorro-antd的TransferItem数据结构：
    interface TransferItem {
        key: string;
        title: string;
        description?: string;
        direction?: 'left' | 'right';
        disabled?: boolean;
    }
    """
    key: str                                          # 唯一标识符
    title: str                                        # 显示标题
    description: str = ""                             # 描述信息
    direction: Optional[TransferDirection] = None     # 当前位置
    disabled: bool = False                            # 是否禁用
    selected: bool = False                            # 是否选中
    icon: Optional[str] = None                        # 图标名称
    data: Dict[str, Any] = field(default_factory=dict)  # 额外数据
    
    def __post_init__(self):
        """初始化后处理"""
        # 确保key不为空
        if not self.key:
            raise ValueError("TransferItem的key不能为空")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'key': self.key,
            'title': self.title,
            'description': self.description,
            'direction': self.direction.value if self.direction else None,
            'disabled': self.disabled,
            'selected': self.selected,
            'icon': self.icon,
            'data': self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransferItem':
        """从字典创建实例"""
        direction = None
        if data.get('direction'):
            direction = TransferDirection(data['direction'])
        
        return cls(
            key=data['key'],
            title=data['title'],
            description=data.get('description', ''),
            direction=direction,
            disabled=data.get('disabled', False),
            selected=data.get('selected', False),
            icon=data.get('icon'),
            data=data.get('data', {})
        )


@dataclass  
class PLCModule(TransferItem):
    """
    PLC模块数据模型
    继承TransferItem，添加PLC特有的属性
    """
    model: str = ""                    # 模块型号
    module_type: str = ""              # 模块类型 (AI/AO/DI/DO等)
    channels: int = 0                  # 通道数量
    unique_id: str = ""                # 模块唯一ID
    manufacturer: str = "和利时"        # 制造商
    series: str = ""                   # 系列
    rack_id: Optional[int] = None      # 机架号
    slot_id: Optional[int] = None      # 槽位号
    
    def __post_init__(self):
        """初始化后处理"""
        super().__post_init__()
        
        # 如果没有设置unique_id，使用key
        if not self.unique_id:
            self.unique_id = self.key
            
        # 设置默认图标（基于模块类型）
        if not self.icon:
            self.icon = self._get_default_icon()
            
        # 如果没有设置描述，生成默认描述
        if not self.description:
            self.description = f"{self.model} - {self.module_type}"
            if self.channels > 0:
                self.description += f" ({self.channels}通道)"
    
    def _get_default_icon(self) -> str:
        """根据模块类型获取默认图标"""
        icon_map = {
            'CPU': '🖥️',
            'DI': '📥',     # 数字输入
            'DO': '📤',     # 数字输出  
            'AI': '📊',     # 模拟输入
            'AO': '📈',     # 模拟输出
            'COMM': '🔗',   # 通讯模块
            'POWER': '🔌',  # 电源模块
        }
        return icon_map.get(self.module_type.upper(), '🔧')
    
    def is_placed(self) -> bool:
        """检查模块是否已放置到机架"""
        return self.rack_id is not None and self.slot_id is not None
    
    def get_placement_info(self) -> Optional[str]:
        """获取放置位置信息"""
        if self.is_placed():
            return f"机架{self.rack_id}-槽位{self.slot_id}"
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = super().to_dict()
        data.update({
            'model': self.model,
            'module_type': self.module_type,
            'channels': self.channels,
            'unique_id': self.unique_id,
            'manufacturer': self.manufacturer,
            'series': self.series,
            'rack_id': self.rack_id,
            'slot_id': self.slot_id,
        })
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PLCModule':
        """从字典创建实例"""
        # 先创建基础TransferItem
        base_item = TransferItem.from_dict(data)
        
        # 创建PLCModule实例
        return cls(
            key=base_item.key,
            title=base_item.title,
            description=base_item.description,
            direction=base_item.direction,
            disabled=base_item.disabled,
            selected=base_item.selected,
            icon=base_item.icon,
            data=base_item.data,
            model=data.get('model', ''),
            module_type=data.get('module_type', ''),
            channels=data.get('channels', 0),
            unique_id=data.get('unique_id', ''),
            manufacturer=data.get('manufacturer', '和利时'),
            series=data.get('series', ''),
            rack_id=data.get('rack_id'),
            slot_id=data.get('slot_id'),
        )
    
    @classmethod
    def from_legacy_dict(cls, legacy_data: Dict[str, Any]) -> 'PLCModule':
        """
        从现有的模块字典格式创建实例
        兼容当前系统的数据格式
        """
        return cls(
            key=legacy_data.get('unique_id', ''),
            title=legacy_data.get('model', ''),
            description=legacy_data.get('description', ''),
            model=legacy_data.get('model', ''),
            module_type=legacy_data.get('type', ''),
            channels=legacy_data.get('channels', 0),
            unique_id=legacy_data.get('unique_id', ''),
            manufacturer=legacy_data.get('manufacturer', '和利时'),
            series=legacy_data.get('series', ''),
        )


@dataclass
class TransferListState:
    """
    穿梭框列表状态
    管理左右两个列表的状态信息
    """
    left_items: list[TransferItem] = field(default_factory=list)    # 左侧项目
    right_items: list[TransferItem] = field(default_factory=list)   # 右侧项目
    left_selected: set[str] = field(default_factory=set)           # 左侧选中项
    right_selected: set[str] = field(default_factory=set)          # 右侧选中项
    
    def get_all_items(self) -> list[TransferItem]:
        """获取所有项目"""
        return self.left_items + self.right_items
    
    def find_item_by_key(self, key: str) -> Optional[TransferItem]:
        """根据key查找项目"""
        for item in self.get_all_items():
            if item.key == key:
                return item
        return None
    
    def move_to_right(self, keys: list[str]) -> list[str]:
        """移动项目到右侧，返回成功移动的keys"""
        moved_keys = []
        for key in keys:
            if key in self.left_selected:
                item = self.find_item_by_key(key)
                if item and item in self.left_items:
                    item.direction = TransferDirection.RIGHT
                    self.left_items.remove(item)
                    self.right_items.append(item)
                    self.left_selected.discard(key)
                    moved_keys.append(key)
        return moved_keys
    
    def move_to_left(self, keys: list[str]) -> list[str]:
        """移动项目到左侧，返回成功移动的keys"""
        moved_keys = []
        for key in keys:
            if key in self.right_selected:
                item = self.find_item_by_key(key)
                if item and item in self.right_items:
                    item.direction = TransferDirection.LEFT
                    self.right_items.remove(item)
                    self.left_items.append(item)
                    self.right_selected.discard(key)
                    moved_keys.append(key)
        return moved_keys
    
    def clear_selections(self):
        """清空所有选择"""
        self.left_selected.clear()
        self.right_selected.clear() 