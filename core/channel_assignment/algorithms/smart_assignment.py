"""
智能通道分配算法
实现模块感知、DIDO配对、机架级约束、负载均衡等功能
"""

import logging
import re
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class DeviceGroup:
    """设备分组"""
    device_id: str              # 设备标识（如仪表位号前缀）
    points: List[Any]           # 该设备的所有点位
    required_channels: Dict[str, int]  # 需要的通道类型和数量
    is_dido_device: bool = False  # 是否为DIDO设备（需要DI+DO配对）


@dataclass
class ModuleAllocation:
    """模块分配信息"""
    module_id: str              # 模块ID
    module_type: str            # 模块类型（AI/DI/AO/DO）
    rack_id: int                # 机架ID
    slot_id: int                # 槽位ID
    total_channels: int         # 总通道数
    used_channels: int = 0      # 已使用通道数
    allocated_points: List[str] = None  # 分配的点位ID列表
    
    def __post_init__(self):
        if self.allocated_points is None:
            self.allocated_points = []
    
    @property
    def available_channels(self) -> int:
        """可用通道数"""
        return self.total_channels - self.used_channels
    
    @property
    def utilization_rate(self) -> float:
        """利用率"""
        return self.used_channels / self.total_channels if self.total_channels > 0 else 0


class SmartChannelAssignmentEngine:
    """智能通道分配引擎"""
    
    def __init__(self):
        """初始化分配引擎"""
        self.device_groups: List[DeviceGroup] = []
        self.module_allocations: Dict[str, ModuleAllocation] = {}
        self.rack_modules: Dict[int, List[ModuleAllocation]] = defaultdict(list)
        
        # 配置参数
        self.dido_keywords = ['阀', '阀门', 'VALVE', 'XV', 'HV', 'PV', 'CV']  # DIDO设备关键词
        self.device_prefix_patterns = [
            r'^([A-Z]+\d+)',      # 如 FT001, PT002
            r'^(\d+[A-Z]+)',      # 如 001FT, 002PT
            r'^([A-Z]+)',         # 如 FT, PT
        ]
        
        logger.info("SmartChannelAssignmentEngine initialized")
    
    def analyze_template_data(self, template_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析模板数据，提取模块和机架信息"""
        try:
            # 解析模块信息
            self._parse_modules_from_template(template_data)
            
            # 统计信息
            stats = {
                'total_modules': len(self.module_allocations),
                'modules_by_type': defaultdict(int),
                'modules_by_rack': defaultdict(int),
                'total_channels_by_type': defaultdict(int),
                'rack_count': len(self.rack_modules)
            }
            
            for module in self.module_allocations.values():
                stats['modules_by_type'][module.module_type] += 1
                stats['modules_by_rack'][module.rack_id] += 1
                stats['total_channels_by_type'][module.module_type] += module.total_channels
            
            logger.info(f"模板分析完成: {stats['total_modules']} 个模块, {stats['rack_count']} 个机架")
            return stats
            
        except Exception as e:
            logger.error(f"分析模板数据失败: {e}")
            return {}
    
    def _parse_modules_from_template(self, template_data: List[Dict[str, Any]]):
        """从模板数据解析模块信息"""
        # 按地址分组通道，推断模块结构
        channels_by_module = defaultdict(list)

        for channel in template_data:
            # 尝试多种字段名获取地址和类型
            address = channel.get('address', '') or channel.get('通道位号', '') or channel.get('channel_id', '')
            channel_type = channel.get('type', '') or channel.get('模块类型', '') or channel.get('channel_type', '')

            if not address or not channel_type:
                logger.debug(f"跳过无效通道数据: {channel}")
                continue

            # 从地址推断模块信息
            module_info = self._infer_module_from_address(address, channel_type)
            if module_info:
                module_key = f"{module_info['rack_id']}_{module_info['slot_id']}_{module_info['type']}"
                channels_by_module[module_key].append(channel)
            else:
                logger.debug(f"无法推断模块信息: address={address}, type={channel_type}")

        # 创建模块分配对象
        for module_key, channels in channels_by_module.items():
            parts = module_key.split('_')
            if len(parts) >= 3:
                rack_id = int(parts[0])
                slot_id = int(parts[1])
                module_type = parts[2]

                module_allocation = ModuleAllocation(
                    module_id=module_key,
                    module_type=module_type,
                    rack_id=rack_id,
                    slot_id=slot_id,
                    total_channels=len(channels)
                )

                self.module_allocations[module_key] = module_allocation
                self.rack_modules[rack_id].append(module_allocation)

                logger.debug(f"创建模块分配: {module_key}, 通道数: {len(channels)}")

        logger.info(f"解析模块完成: {len(self.module_allocations)} 个模块, {len(self.rack_modules)} 个机架")
    
    def _infer_module_from_address(self, address: str, channel_type: str) -> Optional[Dict[str, Any]]:
        """从通道地址推断模块信息"""
        try:
            # 支持多种地址格式
            # 格式1: 1_1_AI_0 (机架_槽位_类型_通道)
            # 格式2: AI-01 (类型-通道号)

            if '_' in address:
                # 格式: 1_1_AI_0
                parts = address.split('_')
                if len(parts) >= 4:
                    rack_id = int(parts[0])
                    slot_id = int(parts[1])
                    type_part = parts[2]
                    channel_index = int(parts[3])

                    return {
                        'rack_id': rack_id,
                        'slot_id': slot_id,
                        'type': type_part
                    }
                elif len(parts) >= 3:
                    # 可能是简化格式
                    rack_id = int(parts[0])
                    slot_id = int(parts[1])
                    type_part = parts[2]

                    return {
                        'rack_id': rack_id,
                        'slot_id': slot_id,
                        'type': type_part
                    }
            elif '-' in address:
                # 格式: AI-01
                parts = address.split('-')
                if len(parts) == 2:
                    type_part = parts[0]
                    index_part = parts[1]

                    # 简单的模块推断逻辑
                    # 假设每个模块有16个通道，每个机架有多个模块
                    channel_index = int(index_part)
                    slot_id = (channel_index - 1) // 16 + 1  # 每16个通道一个模块
                    rack_id = 1  # 简化为单机架

                    return {
                        'rack_id': rack_id,
                        'slot_id': slot_id,
                        'type': type_part
                    }
            else:
                # 尝试从channel_type推断
                if channel_type:
                    return {
                        'rack_id': 1,
                        'slot_id': 1,
                        'type': channel_type
                    }

        except Exception as e:
            logger.debug(f"解析地址失败 {address}: {e}")

        return None
    
    def group_devices_by_instrument(self, points: List[Any]) -> List[DeviceGroup]:
        """按仪表设备分组点位"""
        device_groups = defaultdict(list)
        
        for point in points:
            instrument_tag = getattr(point, 'instrument_tag', '')
            description = getattr(point, 'description', '')
            
            # 提取设备标识
            device_id = self._extract_device_id(instrument_tag)
            if not device_id:
                device_id = f"UNKNOWN_{len(device_groups)}"
            
            device_groups[device_id].append(point)
        
        # 创建设备分组对象
        groups = []
        for device_id, device_points in device_groups.items():
            # 统计所需通道类型
            required_channels = defaultdict(int)
            for point in device_points:
                signal_type = getattr(point, 'signal_type', '')
                if signal_type:
                    required_channels[signal_type] += 1
            
            # 判断是否为DIDO设备
            is_dido = self._is_dido_device(device_id, device_points)
            
            group = DeviceGroup(
                device_id=device_id,
                points=device_points,
                required_channels=dict(required_channels),
                is_dido_device=is_dido
            )
            groups.append(group)
        
        logger.info(f"设备分组完成: {len(groups)} 个设备组")
        return groups
    
    def _extract_device_id(self, instrument_tag: str) -> str:
        """从仪表位号提取设备标识"""
        if not instrument_tag:
            return ""

        # 清理仪表位号
        clean_tag = instrument_tag.strip().upper()

        # 尝试多种模式匹配
        for pattern in self.device_prefix_patterns:
            match = re.match(pattern, clean_tag)
            if match:
                return match.group(1)

        # 特殊处理：如果包含下划线，可能是复合标识
        if '_' in clean_tag:
            parts = clean_tag.split('_')
            if len(parts) >= 2:
                # 取前两部分作为设备标识
                return f"{parts[0]}_{parts[1]}"
            else:
                return parts[0]

        # 如果没有匹配，返回前几个字符
        return clean_tag[:4] if len(clean_tag) >= 4 else clean_tag
    
    def _is_dido_device(self, device_id: str, points: List[Any]) -> bool:
        """判断是否为DIDO设备（需要DI+DO配对）"""
        # 检查设备标识中的关键词
        for keyword in self.dido_keywords:
            if keyword.upper() in device_id.upper():
                return True

        # 检查点位描述中的关键词
        for point in points:
            description = getattr(point, 'description', '').upper()
            instrument_tag = getattr(point, 'instrument_tag', '').upper()

            for keyword in self.dido_keywords:
                if keyword.upper() in description or keyword.upper() in instrument_tag:
                    return True

        # 检查是否同时有DI和DO点位（这是DIDO设备的强特征）
        signal_types = set()
        for point in points:
            signal_type = getattr(point, 'signal_type', '')
            signal_types.add(signal_type)

        has_di_do = 'DI' in signal_types and 'DO' in signal_types

        # 如果同时有DI和DO，且点位数量合理（通常2-4个点位），认为是DIDO设备
        if has_di_do and 2 <= len(points) <= 6:
            return True

        return False

    def _filter_communication_points(self, points: List[Any]) -> List[Any]:
        """
        过滤掉通讯软点位，只保留需要分配IO通道的硬点位

        Args:
            points: 所有点位列表

        Returns:
            过滤后的点位列表
        """
        # 定义通讯软点位的信号类型
        communication_types = {
            'RS485', 'TCP/IP', 'MODBUS', 'PROFIBUS', 'CAN', 'HART',
            'ETHERNET', 'FIELDBUS', 'DEVICENET', 'FOUNDATION'
        }

        filtered_points = []
        communication_points = []

        for point in points:
            signal_type = getattr(point, 'signal_type', '').upper().strip()
            instrument_tag = getattr(point, 'instrument_tag', '')

            # 检查是否为通讯软点位
            is_communication = False

            # 1. 直接信号类型匹配
            if signal_type in communication_types:
                is_communication = True

            # 2. 信号类型包含通讯关键字
            elif any(comm_type in signal_type for comm_type in communication_types):
                is_communication = True

            # 3. 仪表位号模式识别（如RS-开头的点位）
            elif instrument_tag.upper().startswith(('RS-', 'GT-', 'COMM-', 'NET-')):
                is_communication = True

            if is_communication:
                communication_points.append(point)
                logger.debug(f"跳过通讯软点位: {instrument_tag} ({signal_type})")
            else:
                filtered_points.append(point)

        if communication_points:
            logger.info(f"识别到 {len(communication_points)} 个通讯软点位，已排除:")
            for point in communication_points[:5]:  # 只显示前5个
                logger.info(f"  - {getattr(point, 'instrument_tag', '')} ({getattr(point, 'signal_type', '')})")
            if len(communication_points) > 5:
                logger.info(f"  ... 还有 {len(communication_points) - 5} 个通讯软点位")

        return filtered_points

    def _analyze_signal_types(self, points: List[Any]) -> None:
        """分析点位的信号类型分布"""
        signal_type_stats = defaultdict(int)
        empty_signal_types = []

        for point in points:
            signal_type = getattr(point, 'signal_type', '').strip()
            if not signal_type:
                signal_type = 'EMPTY'
                empty_signal_types.append(point)
            signal_type_stats[signal_type] += 1

        logger.info("=== 信号类型分布分析 ===")
        for signal_type, count in sorted(signal_type_stats.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"{signal_type}: {count} 个点位")

        if empty_signal_types:
            logger.warning(f"发现 {len(empty_signal_types)} 个点位的信号类型为空:")
            for i, point in enumerate(empty_signal_types[:5]):
                tag = getattr(point, 'instrument_tag', '')
                desc = getattr(point, 'description', '')
                logger.warning(f"  {i+1}. {tag} - {desc}")
            if len(empty_signal_types) > 5:
                logger.warning(f"  ... 还有 {len(empty_signal_types) - 5} 个")

    def smart_assign_channels(self, points: List[Any], template_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """智能分配通道"""
        try:
            # 1. 过滤掉通讯软点位（不需要分配IO通道）
            filtered_points = self._filter_communication_points(points)
            logger.info(f"过滤通讯软点位后，剩余 {len(filtered_points)} 个需要分配IO通道的点位")

            # 2. 分析模板数据
            template_stats = self.analyze_template_data(template_data)

            # 3. 分析信号类型分布
            self._analyze_signal_types(filtered_points)

            # 4. 设备分组
            device_groups = self.group_devices_by_instrument(filtered_points)

            # 4. 执行分配
            assignment_results = self._execute_smart_assignment(device_groups, template_data)

            return {
                'success': True,
                'assignments': assignment_results.get('assignments', {}),
                'statistics': {
                    'total_points': len(points),
                    'filtered_points': len(filtered_points),
                    'communication_points': len(points) - len(filtered_points),
                    'assigned_points': assignment_results.get('assigned_count', 0),
                    'failed_points': assignment_results.get('failed_count', 0),
                    'device_groups': len(device_groups),
                    'dido_devices': len([g for g in device_groups if g.is_dido_device]),
                    'template_stats': template_stats
                },
                'errors': assignment_results.get('errors', [])
            }

        except Exception as e:
            logger.error(f"智能分配失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'assignments': {},
                'statistics': {},
                'errors': [str(e)]
            }

    def _execute_smart_assignment(self, device_groups: List[DeviceGroup], template_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行智能分配 - 全局连续分配策略"""
        assignments = {}
        assigned_count = 0
        failed_count = 0
        errors = []

        # 创建可用通道索引
        available_channels = self._build_available_channels_index(template_data)

        logger.info(f"开始执行全局连续分配算法，共 {len(device_groups)} 个设备组")

        # 收集所有点位并按信号类型分组
        all_points = []
        for group in device_groups:
            all_points.extend(group.points)

        points_by_type = defaultdict(list)
        for point in all_points:
            signal_type = getattr(point, 'signal_type', '')
            if signal_type:
                points_by_type[signal_type].append(point)

        logger.info(f"=== 信号类型分布分析 ===")
        for signal_type, points in points_by_type.items():
            logger.info(f"{signal_type}: {len(points)} 个点位")

        # 全局连续分配所有点位（禁用DIDO配对以确保模块内连续性）
        remaining_assignments, remaining_errors, remaining_assigned, remaining_failed = self._assign_remaining_points_globally(
            all_points, {}, available_channels  # 传递空的existing_assignments，确保所有点位都参与全局连续分配
        )
        assignments.update(remaining_assignments)
        errors.extend(remaining_errors)
        assigned_count += remaining_assigned
        failed_count += remaining_failed

        logger.info(f"全局连续分配完成: 成功 {assigned_count} 个，失败 {failed_count} 个")
        return {
            'assignments': assignments,
            'assigned_count': assigned_count,
            'failed_count': failed_count,
            'errors': errors
        }

    def _build_available_channels_index(self, template_data: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """构建可用通道索引"""
        channels_by_type = defaultdict(list)

        for channel in template_data:
            # 尝试多种字段名获取类型和地址
            channel_type = channel.get('type', '') or channel.get('模块类型', '') or channel.get('channel_type', '')
            address = channel.get('address', '') or channel.get('通道位号', '') or channel.get('channel_id', '')

            if channel_type and address:
                # 确保通道数据包含必要的字段
                normalized_channel = {
                    'type': channel_type,
                    'address': address,
                    **channel  # 保留原始数据
                }
                channels_by_type[channel_type].append(normalized_channel)

        # 按地址排序
        for channel_type in channels_by_type:
            channels_by_type[channel_type].sort(key=lambda x: x.get('address', ''))

        logger.info(f"构建通道索引: {dict((k, len(v)) for k, v in channels_by_type.items())}")
        return dict(channels_by_type)

    def _sort_device_groups_by_priority(self, device_groups: List[DeviceGroup]) -> List[DeviceGroup]:
        """按优先级排序设备组"""
        def priority_key(group: DeviceGroup) -> Tuple[int, int, str]:
            # 优先级：1. DIDO设备优先 2. 点位数量多的优先 3. 设备ID字母序
            dido_priority = 0 if group.is_dido_device else 1
            point_count_priority = -len(group.points)  # 负数使得数量多的排前面
            return (dido_priority, point_count_priority, group.device_id)

        return sorted(device_groups, key=priority_key)

    def _assign_dido_device(self, group: DeviceGroup, available_channels: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """分配DIDO设备（优先同一机架，但允许跨机架）"""
        assignments = {}
        assigned_count = 0
        failed_count = 0
        errors = []

        try:
            # 分离DI和DO点位
            di_points = [p for p in group.points if getattr(p, 'signal_type', '') == 'DI']
            do_points = [p for p in group.points if getattr(p, 'signal_type', '') == 'DO']
            other_points = [p for p in group.points if getattr(p, 'signal_type', '') not in ['DI', 'DO']]

            # 处理DI和DO点位（优先同一机架，但允许跨机架）
            if di_points and do_points:
                # 同时有DI和DO，尝试在同一机架分配
                rack_assignment = self._find_rack_for_dido_pair(
                    len(di_points), len(do_points), available_channels
                )

                if rack_assignment:
                    logger.info(f"DIDO设备 {group.device_id} 在机架 {rack_assignment['rack_id']} 内分配")

                    # 分配DI点位
                    for i, point in enumerate(di_points):
                        if i < len(rack_assignment['di_channels']):
                            channel = rack_assignment['di_channels'][i]
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            available_channels['DI'].remove(channel)
                        else:
                            failed_count += 1
                            errors.append(f"DI点位 {getattr(point, 'instrument_tag', '')} 无可用通道")

                    # 分配DO点位
                    for i, point in enumerate(do_points):
                        if i < len(rack_assignment['do_channels']):
                            channel = rack_assignment['do_channels'][i]
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            available_channels['DO'].remove(channel)
                        else:
                            failed_count += 1
                            errors.append(f"DO点位 {getattr(point, 'instrument_tag', '')} 无可用通道")
                else:
                    # 无法在同一机架分配，使用普通分配（允许跨机架）
                    logger.info(f"DIDO设备 {group.device_id} 无法在同一机架分配，允许跨机架分配")

                    # 分配DI点位
                    for point in di_points:
                        if available_channels.get('DI'):
                            channel = available_channels['DI'].pop(0)
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"DI点位 {getattr(point, 'instrument_tag', '')} 无可用通道")

                    # 分配DO点位
                    for point in do_points:
                        if available_channels.get('DO'):
                            channel = available_channels['DO'].pop(0)
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                        else:
                            failed_count += 1
                            errors.append(f"DO点位 {getattr(point, 'instrument_tag', '')} 无可用通道")
            else:
                # 只有DI或只有DO，直接分配
                for point in di_points:
                    if available_channels.get('DI'):
                        channel = available_channels['DI'].pop(0)
                        assignments[point.id] = channel['address']
                        assigned_count += 1
                        logger.debug(f"分配DI点位 {getattr(point, 'instrument_tag', '')} -> {channel['address']}")
                    else:
                        failed_count += 1
                        errors.append(f"DI点位 {getattr(point, 'instrument_tag', '')} 无可用通道")

                for point in do_points:
                    if available_channels.get('DO'):
                        channel = available_channels['DO'].pop(0)
                        assignments[point.id] = channel['address']
                        assigned_count += 1
                        logger.debug(f"分配DO点位 {getattr(point, 'instrument_tag', '')} -> {channel['address']}")
                    else:
                        failed_count += 1
                        errors.append(f"DO点位 {getattr(point, 'instrument_tag', '')} 无可用通道")

            # 分配其他类型点位（AI、AO等）
            for point in other_points:
                signal_type = getattr(point, 'signal_type', '')
                instrument_tag = getattr(point, 'instrument_tag', '')

                if signal_type in available_channels and available_channels[signal_type]:
                    channel = available_channels[signal_type].pop(0)
                    assignments[point.id] = channel['address']
                    assigned_count += 1
                    logger.debug(f"DIDO设备分配其他类型点位 {instrument_tag} ({signal_type}) -> {channel['address']}")
                else:
                    failed_count += 1
                    error_msg = f"点位 {instrument_tag} 无可用 {signal_type} 通道"
                    errors.append(error_msg)
                    logger.warning(error_msg)

        except Exception as e:
            error_msg = f"DIDO设备分配失败: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            failed_count = len(group.points)

        return {
            'assignments': assignments,
            'assigned_count': assigned_count,
            'failed_count': failed_count,
            'errors': errors
        }

    def _find_rack_for_dido_pair(self, di_count: int, do_count: int, available_channels: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """寻找能容纳DI+DO配对的机架，确保模块内连续分配"""
        try:
            # 按机架分组可用通道
            di_by_rack = self._group_channels_by_rack(available_channels.get('DI', []))
            do_by_rack = self._group_channels_by_rack(available_channels.get('DO', []))

            # 寻找同时有足够DI和DO通道的机架
            for rack_id in di_by_rack.keys():
                if rack_id in do_by_rack:
                    # 按模块分组并选择连续通道
                    di_channels = self._select_continuous_channels_by_module(di_by_rack[rack_id], di_count)
                    do_channels = self._select_continuous_channels_by_module(do_by_rack[rack_id], do_count)

                    if len(di_channels) >= di_count and len(do_channels) >= do_count:
                        return {
                            'rack_id': rack_id,
                            'di_channels': di_channels[:di_count],
                            'do_channels': do_channels[:do_count]
                        }

            return None

        except Exception as e:
            logger.error(f"寻找DIDO机架失败: {e}")
            return None

    def _select_continuous_channels_by_module(self, channels: List[Dict[str, Any]], needed_count: int) -> List[Dict[str, Any]]:
        """按模块选择连续通道"""
        if not channels or needed_count <= 0:
            return []

        # 按模块分组
        channels_by_module = self._group_channels_by_module(channels)
        selected_channels = []

        # 按模块顺序选择连续通道
        for module_id in sorted(channels_by_module.keys()):
            module_channels = channels_by_module[module_id]

            # 在当前模块内选择连续通道
            available_in_module = min(len(module_channels), needed_count - len(selected_channels))
            if available_in_module > 0:
                selected_channels.extend(module_channels[:available_in_module])

                # 如果已经选够了，就停止
                if len(selected_channels) >= needed_count:
                    break

        return selected_channels

    def _group_channels_by_rack(self, channels: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """按机架分组通道"""
        rack_channels = defaultdict(list)

        for channel in channels:
            # 从地址推断机架ID（需要根据实际格式调整）
            rack_id = self._infer_rack_from_address(channel.get('address', ''))
            if rack_id:
                rack_channels[rack_id].append(channel)

        return dict(rack_channels)

    def _infer_rack_from_address(self, address: str) -> Optional[int]:
        """从通道地址推断机架ID"""
        try:
            # 支持多种地址格式
            if '_' in address:
                # 格式: 1_1_AI_0 (机架_槽位_类型_通道)
                parts = address.split('_')
                if len(parts) >= 1:
                    return int(parts[0])
            elif '-' in address:
                # 格式: AI-01，简化为机架1
                return 1
            else:
                # 默认机架1
                return 1
        except Exception as e:
            logger.debug(f"从地址推断机架ID失败 {address}: {e}")
            return 1

    def _assign_regular_device(self, group: DeviceGroup, available_channels: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """分配普通设备（优先同模块，允许跨模块）"""
        assignments = {}
        assigned_count = 0
        failed_count = 0
        errors = []

        try:
            # 按信号类型分组点位
            points_by_type = defaultdict(list)
            for point in group.points:
                signal_type = getattr(point, 'signal_type', '')
                if signal_type:
                    points_by_type[signal_type].append(point)

            # 为每种类型分配通道
            for signal_type, type_points in points_by_type.items():
                if signal_type in available_channels and available_channels[signal_type]:
                    available = available_channels[signal_type]

                    # 优先尝试在同一模块内分配
                    if len(type_points) > 1:
                        module_assignment = self._assign_to_same_module(type_points, available)

                        if module_assignment and module_assignment['assigned_count'] == len(type_points):
                            # 成功在同一模块分配所有点位
                            logger.debug(f"设备 {group.device_id} 的 {signal_type} 点位在同一模块分配")
                            assignments.update(module_assignment['assignments'])
                            assigned_count += module_assignment['assigned_count']

                            # 移除已使用的通道
                            for channel in module_assignment['used_channels']:
                                if channel in available:
                                    available.remove(channel)
                            continue

                    # 无法在同一模块分配或只有单个点位，使用顺序分配
                    for point in type_points:
                        if available:
                            channel = available.pop(0)
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            logger.debug(f"分配点位 {getattr(point, 'instrument_tag', '')} -> {channel['address']}")
                        else:
                            failed_count += 1
                            error_msg = f"点位 {getattr(point, 'instrument_tag', '')} 无可用 {signal_type} 通道"
                            errors.append(error_msg)
                            logger.warning(error_msg)
                else:
                    # 没有该类型的可用通道
                    failed_count += len(type_points)
                    for point in type_points:
                        error_msg = f"点位 {getattr(point, 'instrument_tag', '')} 无可用 {signal_type} 通道"
                        errors.append(error_msg)
                        logger.warning(error_msg)

        except Exception as e:
            error_msg = f"普通设备分配失败: {e}"
            errors.append(error_msg)
            logger.error(error_msg)
            failed_count = len(group.points)

        return {
            'assignments': assignments,
            'assigned_count': assigned_count,
            'failed_count': failed_count,
            'errors': errors
        }

    def _assign_to_same_module(self, points: List[Any], available_channels: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """尝试将点位分配到同一模块"""
        try:
            # 按模块分组可用通道
            channels_by_module = self._group_channels_by_module(available_channels)

            # 寻找能容纳所有点位的模块
            for module_id, module_channels in channels_by_module.items():
                if len(module_channels) >= len(points):
                    assignments = {}
                    used_channels = []

                    for i, point in enumerate(points):
                        if i < len(module_channels):
                            channel = module_channels[i]
                            assignments[point.id] = channel['address']
                            used_channels.append(channel)

                    return {
                        'assignments': assignments,
                        'assigned_count': len(assignments),
                        'failed_count': 0,
                        'errors': [],
                        'used_channels': used_channels
                    }

            return None

        except Exception as e:
            logger.error(f"同模块分配失败: {e}")
            return None

    def _group_channels_by_module(self, channels: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按模块分组通道，并在模块内按通道编号排序"""
        module_channels = defaultdict(list)

        for channel in channels:
            # 从地址推断模块ID（需要根据实际格式调整）
            module_id = self._infer_module_from_channel(channel)
            if module_id:
                module_channels[module_id].append(channel)

        # 在每个模块内按通道编号排序
        for module_id, module_channel_list in module_channels.items():
            module_channel_list.sort(key=lambda ch: self._extract_channel_number(ch))

        return dict(module_channels)

    def _extract_channel_number(self, channel: Dict[str, Any]) -> int:
        """从通道地址中提取通道编号"""
        try:
            address = channel.get('address', '')
            if '_' in address:
                # 格式: 1_1_AI_0 (机架_槽位_类型_通道)
                parts = address.split('_')
                if len(parts) >= 4:
                    return int(parts[-1])  # 最后一部分是通道编号
            elif '-' in address:
                # 格式: AI-01
                parts = address.split('-')
                if len(parts) == 2:
                    return int(parts[1])
            return 0
        except:
            return 0

    def _infer_module_from_channel(self, channel: Dict[str, Any]) -> Optional[str]:
        """从通道信息推断模块ID"""
        try:
            address = channel.get('address', '')
            channel_type = channel.get('type', '')

            # 支持多种地址格式
            if '_' in address:
                # 格式: 1_1_AI_0 (机架_槽位_类型_通道)
                parts = address.split('_')
                if len(parts) >= 3:
                    rack_id = parts[0]
                    slot_id = parts[1]
                    type_part = parts[2]
                    return f"rack{rack_id}_slot{slot_id}_{type_part}"
            elif '-' in address:
                # 格式: AI-01
                parts = address.split('-')
                if len(parts) == 2:
                    index = int(parts[1])
                    # 假设每16个通道一个模块
                    module_slot = (index - 1) // 16 + 1
                    return f"rack1_slot{module_slot}_{channel_type}"
            else:
                # 使用通道类型作为模块标识
                return f"rack1_slot1_{channel_type}"

            return None

        except Exception as e:
            logger.debug(f"从通道推断模块ID失败: {e}")
            return None

    def _assign_dido_pairs_globally(self, device_groups: List[DeviceGroup], available_channels: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, str], List[str], int, int]:
        """全局DIDO配对分配"""
        assignments = {}
        errors = []
        assigned_count = 0
        failed_count = 0

        # 识别DIDO设备组
        dido_groups = [group for group in device_groups if group.is_dido_device]

        logger.info(f"识别到 {len(dido_groups)} 个DIDO设备组")

        for group in dido_groups:
            # 分离DI和DO点位
            di_points = [p for p in group.points if getattr(p, 'signal_type', '') == 'DI']
            do_points = [p for p in group.points if getattr(p, 'signal_type', '') == 'DO']

            if di_points and do_points:
                # 尝试在同一机架分配DI+DO配对
                rack_assignment = self._find_rack_for_dido_pair(
                    len(di_points), len(do_points), available_channels
                )

                if rack_assignment:
                    logger.info(f"DIDO设备 {group.device_id} 在机架 {rack_assignment['rack_id']} 内配对分配")

                    # 分配DI点位
                    for i, point in enumerate(di_points):
                        if i < len(rack_assignment['di_channels']):
                            channel = rack_assignment['di_channels'][i]
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            available_channels['DI'].remove(channel)

                    # 分配DO点位
                    for i, point in enumerate(do_points):
                        if i < len(rack_assignment['do_channels']):
                            channel = rack_assignment['do_channels'][i]
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            available_channels['DO'].remove(channel)
                else:
                    logger.info(f"DIDO设备 {group.device_id} 无法在同一机架配对，将在全局分配中处理")

        return assignments, errors, assigned_count, failed_count

    def _assign_remaining_points_globally(self, all_points: List, existing_assignments: Dict[str, str], available_channels: Dict[str, List[Dict[str, Any]]]) -> Tuple[Dict[str, str], List[str], int, int]:
        """全局连续分配剩余点位 - 优化模块内连续性"""
        assignments = {}
        errors = []
        assigned_count = 0
        failed_count = 0

        # 过滤出未分配的点位
        unassigned_points = [p for p in all_points if p.id not in existing_assignments]

        # 按信号类型分组
        points_by_type = defaultdict(list)
        for point in unassigned_points:
            signal_type = getattr(point, 'signal_type', '')
            if signal_type:
                points_by_type[signal_type].append(point)

        logger.info(f"全局连续分配剩余点位: {len(unassigned_points)} 个")

        # 按信号类型顺序分配（优化模块内连续性）
        for signal_type in ['AI', 'DI', 'DO', 'AO']:  # 按优先级顺序
            if signal_type in points_by_type and signal_type in available_channels:
                type_points = points_by_type[signal_type]
                available = available_channels[signal_type]

                logger.info(f"连续分配 {signal_type} 类型: {len(type_points)} 个点位，可用通道: {len(available)} 个")

                # 按模块分组可用通道，优先填满每个模块
                channels_by_module = self._group_channels_by_module(available)

                # 按模块顺序分配，优先填满每个模块
                point_index = 0
                for module_id in sorted(channels_by_module.keys()):
                    module_channels = channels_by_module[module_id]
                    logger.debug(f"模块 {module_id} 有 {len(module_channels)} 个 {signal_type} 通道")

                    # 在当前模块内连续分配
                    for channel in module_channels:
                        if point_index < len(type_points):
                            point = type_points[point_index]
                            assignments[point.id] = channel['address']
                            assigned_count += 1
                            instrument_tag = getattr(point, 'instrument_tag', '')
                            logger.debug(f"模块内连续分配 {instrument_tag} ({signal_type}) -> {channel['address']}")

                            # 从可用通道中移除
                            if channel in available:
                                available.remove(channel)

                            point_index += 1
                        else:
                            break

                # 处理剩余未分配的点位（如果有）
                for i in range(point_index, len(type_points)):
                    point = type_points[i]
                    failed_count += 1
                    instrument_tag = getattr(point, 'instrument_tag', '')
                    error_msg = f"点位 {instrument_tag} 无可用 {signal_type} 通道"
                    errors.append(error_msg)
                    logger.warning(error_msg)

        logger.info(f"全局连续分配完成: 成功 {assigned_count} 个，失败 {failed_count} 个")
        return assignments, errors, assigned_count, failed_count
