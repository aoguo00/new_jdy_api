#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调试通道分配顺序问题
"""

import logging
import pandas as pd
from core.channel_assignment.algorithms.smart_assignment import SmartChannelAssignmentEngine
from core.document_parser.word_parser import WordDocumentParser

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_channel_order():
    """调试通道分配顺序"""
    
    # 1. 加载IO模板
    template_path = r"C:\Users\DELL\Desktop\code\new_jdy_api\IO点表模板\路口铺门站_IO_点表.xlsx"
    logger.info(f"加载IO模板: {template_path}")
    
    template_df = pd.read_excel(template_path)
    logger.info(f"IO模板包含 {len(template_df)} 行数据")
    
    # 2. 创建分配引擎
    engine = SmartChannelAssignmentEngine()
    
    # 3. 分析模板数据
    template_data = template_df.to_dict('records')
    
    # 4. 构建通道索引
    channels_by_type = engine._build_available_channels_index(template_data)
    
    # 5. 检查每种类型的通道顺序
    for signal_type, channels in channels_by_type.items():
        logger.info(f"\n=== {signal_type} 通道顺序 ===")
        logger.info(f"总数: {len(channels)}")
        
        # 显示前10个通道的地址
        for i, channel in enumerate(channels[:10]):
            address = channel.get('address', '')
            logger.info(f"  {i+1:2d}. {address}")
        
        if len(channels) > 10:
            logger.info(f"  ... 还有 {len(channels) - 10} 个通道")
        
        # 检查地址排序是否正确
        addresses = [ch.get('address', '') for ch in channels]
        sorted_addresses = sorted(addresses)
        
        if addresses == sorted_addresses:
            logger.info(f"✅ {signal_type} 通道地址排序正确")
        else:
            logger.warning(f"❌ {signal_type} 通道地址排序有问题")
            logger.info("原始顺序:")
            for addr in addresses[:5]:
                logger.info(f"  {addr}")
            logger.info("应该的顺序:")
            for addr in sorted_addresses[:5]:
                logger.info(f"  {addr}")

def debug_assignment_process():
    """调试分配过程"""
    
    # 1. 解析Word文档
    word_path = r"C:\Users\DELL\Downloads\临湘IO点表\7 路口铺门站IO表.docx"
    logger.info(f"解析Word文档: {word_path}")
    
    parser = WordDocumentParser()
    points = parser.parse_document(word_path)
    logger.info(f"从Word文档解析到 {len(points)} 个点位")
    
    # 2. 加载IO模板
    template_path = r"C:\Users\DELL\Desktop\code\new_jdy_api\IO点表模板\路口铺门站_IO_点表.xlsx"
    template_df = pd.read_excel(template_path)
    template_data = template_df.to_dict('records')
    
    # 3. 创建分配引擎
    engine = SmartChannelAssignmentEngine()
    
    # 4. 将字典转换为对象格式（模拟界面的转换过程）
    from core.data_storage.data_models import ParsedPoint
    parsed_points = []
    for point_data in points:
        parsed_point = ParsedPoint(
            instrument_tag=point_data.get('instrument_tag', ''),
            description=point_data.get('description', ''),
            signal_type=point_data.get('signal_type', ''),
            io_type=point_data.get('io_type', ''),
            units=point_data.get('units', ''),
            data_range=point_data.get('data_range', ''),
            signal_range=point_data.get('signal_range', ''),
            power_supply=point_data.get('power_supply', ''),
            isolation=point_data.get('isolation', ''),
            remarks=point_data.get('remarks', ''),
            original_data=point_data
        )
        parsed_points.append(parsed_point)

    logger.info(f"转换为 {len(parsed_points)} 个ParsedPoint对象")

    # 5. 执行分配
    result = engine.smart_assign_channels(parsed_points, template_data)

    # 5.1 检查DIDO分配的具体情况
    logger.info(f"\n=== DIDO分配详细分析 ===")
    for point in parsed_points:
        if point.id in result.get('assignments', {}):
            signal_type = point.signal_type
            if signal_type in ['DI', 'DO']:
                instrument_tag = point.instrument_tag
                channel_address = result['assignments'][point.id]
                logger.info(f"DIDO点位 {instrument_tag} ({signal_type}) -> {channel_address}")

                # 检查是否是HS设备（DIDO设备）
                if 'HS' in instrument_tag:
                    logger.info(f"  ✅ 这是HS设备的DIDO点位")

    # 6. 分析分配结果
    assignments = result.get('assignments', {})
    logger.info(f"\n=== 分配结果分析 ===")
    logger.info(f"成功分配: {len(assignments)} 个点位")

    # 按信号类型分组分析
    assigned_by_type = {}
    for point_id, channel_address in assignments.items():
        # 从点位ID找到对应的点位
        point = next((p for p in parsed_points if p.id == point_id), None)
        if point:
            signal_type = point.signal_type
            if signal_type not in assigned_by_type:
                assigned_by_type[signal_type] = []
            assigned_by_type[signal_type].append(channel_address)
    
    # 检查每种类型的分配是否连续
    for signal_type, addresses in assigned_by_type.items():
        logger.info(f"\n=== {signal_type} 分配分析 ===")
        logger.info(f"分配数量: {len(addresses)}")
        
        # 排序地址
        sorted_addresses = sorted(addresses)
        logger.info("分配的通道地址:")
        for i, addr in enumerate(sorted_addresses[:10]):
            logger.info(f"  {i+1:2d}. {addr}")
        
        if len(sorted_addresses) > 10:
            logger.info(f"  ... 还有 {len(sorted_addresses) - 10} 个")
        
        # 检查模块内连续性
        if signal_type in ['AI', 'DI', 'DO', 'AO']:
            # 按模块分组分析
            modules = {}
            for addr in sorted_addresses:
                try:
                    # 假设地址格式为 1_1_AI_0, 1_1_AI_1 等
                    parts = addr.split('_')
                    if len(parts) >= 4:
                        rack_id = parts[0]
                        slot_id = parts[1]
                        signal_type_part = parts[2]
                        channel_num = int(parts[-1])

                        module_key = f"{rack_id}_{slot_id}_{signal_type_part}"
                        if module_key not in modules:
                            modules[module_key] = []
                        modules[module_key].append(channel_num)
                except:
                    pass

            if modules:
                logger.info(f"模块分布:")
                all_continuous = True

                for module_key, channel_nums in modules.items():
                    channel_nums.sort()
                    logger.info(f"  模块 {module_key}: 通道 {channel_nums}")

                    # 检查模块内是否连续
                    module_continuous = True
                    if len(channel_nums) > 1:
                        for i in range(1, len(channel_nums)):
                            if channel_nums[i] != channel_nums[i-1] + 1:
                                module_continuous = False
                                break

                    if not module_continuous:
                        all_continuous = False
                        logger.warning(f"    ❌ 模块 {module_key} 内通道不连续")
                    else:
                        logger.info(f"    ✅ 模块 {module_key} 内通道连续")

                if all_continuous:
                    logger.info(f"✅ {signal_type} 所有模块内通道分配连续")
                else:
                    logger.warning(f"❌ {signal_type} 存在模块内通道不连续")

if __name__ == "__main__":
    logger.info("开始调试通道分配顺序问题")
    
    logger.info("\n=== 第一步：检查通道索引构建 ===")
    debug_channel_order()
    
    logger.info("\n=== 第二步：检查分配过程 ===")
    debug_assignment_process()
    
    logger.info("\n调试完成！")
