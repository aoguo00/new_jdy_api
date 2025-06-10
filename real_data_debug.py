#!/usr/bin/env python3
"""
使用真实数据调试通道分配问题
"""

import logging
import sys
import os
from collections import defaultdict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.document_parser.word_parser import WordDocumentParser
from core.channel_assignment.algorithms.smart_assignment import SmartChannelAssignmentEngine
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_real_data():
    """加载真实的文档和IO模板数据"""
    
    # 1. 解析Word文档
    doc_path = r"C:\Users\DELL\Downloads\临湘IO点表\7 路口铺门站IO表.docx"
    logger.info(f"解析Word文档: {doc_path}")
    
    parser = WordDocumentParser()
    points_data = parser.parse_document(doc_path)

    if not points_data:
        logger.error("文档解析失败或没有解析到点位")
        return None, None

    logger.info(f"从Word文档解析到 {len(points_data)} 个点位")
    
    # 分析点位的信号类型分布
    signal_type_stats = defaultdict(int)
    for point in points_data:
        signal_type = point.get('signal_type', '') or 'EMPTY'
        signal_type_stats[signal_type] += 1
    
    logger.info("=== Word文档中的信号类型分布 ===")
    for signal_type, count in sorted(signal_type_stats.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"{signal_type}: {count} 个点位")
        # 显示几个例子
        examples = [p for p in points_data if p.get('signal_type', '') == signal_type][:3]
        for example in examples:
            logger.info(f"  例子: {example.get('instrument_tag', '')} - {example.get('description', '')}")
    
    # 2. 加载IO模板
    template_path = r"C:\Users\DELL\Desktop\code\new_jdy_api\IO点表模板\路口铺门站_IO_点表.xlsx"
    logger.info(f"加载IO模板: {template_path}")
    
    try:
        df = pd.read_excel(template_path)
        logger.info(f"IO模板包含 {len(df)} 行数据")
        logger.info(f"IO模板列名: {list(df.columns)}")
        
        # 分析模板中的模块类型分布
        if '模块类型' in df.columns:
            module_type_stats = df['模块类型'].value_counts()
            logger.info("=== IO模板中的模块类型分布 ===")
            for module_type, count in module_type_stats.items():
                logger.info(f"{module_type}: {count} 个通道")
        
        # 转换为字典格式
        template_data = []
        for _, row in df.iterrows():
            template_data.append(row.to_dict())
            
    except Exception as e:
        logger.error(f"加载IO模板失败: {e}")
        return points_data, None
    
    return points_data, template_data

def analyze_assignment_failure(points_data, template_data):
    """分析分配失败的原因"""
    
    if not points_data or not template_data:
        logger.error("缺少必要的数据")
        return
    
    # 创建智能分配引擎
    engine = SmartChannelAssignmentEngine()
    
    # 转换点位数据为对象格式
    class MockPoint:
        def __init__(self, data):
            self.id = data.get('id', f"point_{hash(str(data))}")
            self.instrument_tag = data.get('instrument_tag', '')
            self.description = data.get('description', '')
            self.signal_type = data.get('signal_type', '')
            self.signal_range = data.get('signal_range', '')
            self.data_range = data.get('data_range', '')

    points = [MockPoint(p) for p in points_data]

    # 显示前几个点位的详细信息
    logger.info("\n=== 点位数据示例 ===")
    for i, point in enumerate(points[:5]):
        logger.info(f"点位 {i+1}: {point.instrument_tag}")
        logger.info(f"  描述: {point.description}")
        logger.info(f"  信号类型: '{point.signal_type}'")
        logger.info(f"  信号范围: {point.signal_range}")
        logger.info(f"  数据范围: {point.data_range}")
        logger.info("")
    
    # 分析模板数据
    logger.info("\n=== 分析IO模板 ===")
    template_stats = engine.analyze_template_data(template_data)
    
    # 构建可用通道索引
    available_channels = engine._build_available_channels_index(template_data)
    logger.info(f"\n=== 可用通道统计 ===")
    for channel_type, channels in available_channels.items():
        logger.info(f"{channel_type}: {len(channels)} 个通道")
    
    # 设备分组
    device_groups = engine.group_devices_by_instrument(points)
    logger.info(f"\n=== 设备分组结果 ===")
    logger.info(f"总共分为 {len(device_groups)} 个设备组")
    
    # 分析每个设备组的需求
    total_required = defaultdict(int)
    for group in device_groups:
        logger.info(f"设备组 {group.device_id}: {len(group.points)} 个点位, DIDO设备: {group.is_dido_device}")
        for signal_type, count in group.required_channels.items():
            logger.info(f"  需要 {signal_type}: {count} 个通道")
            total_required[signal_type] += count
    
    # 对比需求和供给
    logger.info(f"\n=== 需求 vs 供给对比 ===")
    for signal_type, required_count in total_required.items():
        available_count = len(available_channels.get(signal_type, []))
        status = "✅ 充足" if available_count >= required_count else "❌ 不足"
        logger.info(f"{signal_type}: 需要 {required_count}, 可用 {available_count} {status}")
        
        if available_count < required_count:
            shortage = required_count - available_count
            logger.warning(f"  缺少 {shortage} 个 {signal_type} 通道")
    
    # 执行实际分配
    logger.info(f"\n=== 执行智能分配 ===")
    result = engine.smart_assign_channels(points, template_data)
    
    if result.get('success'):
        stats = result.get('statistics', {})
        assigned = stats.get('assigned_points', 0)
        failed = stats.get('failed_points', 0)
        filtered = stats.get('filtered_points', 0)

        logger.info(f"分配结果:")
        logger.info(f"  总点位: {len(points)}")
        logger.info(f"  过滤后: {filtered}")
        logger.info(f"  成功分配: {assigned}")
        logger.info(f"  分配失败: {failed}")

        if assigned + failed != filtered:
            logger.error(f"❌ 数据不一致！成功({assigned}) + 失败({failed}) != 过滤后({filtered})")

        # 显示分配结果
        assignments = result.get('assignments', {})
        if assignments:
            logger.info(f"\n=== 成功分配的点位 (前10个) ===")
            count = 0
            for point_id, channel_id in assignments.items():
                point = next((p for p in points if p.id == point_id), None)
                if point and count < 10:
                    logger.info(f"{count+1}. {point.instrument_tag} ({point.signal_type}) -> {channel_id}")
                    count += 1
            if len(assignments) > 10:
                logger.info(f"... 还有 {len(assignments) - 10} 个成功分配")

        errors = result.get('errors', [])
        if errors:
            logger.warning(f"\n=== 分配错误 (前10个) ===")
            for i, error in enumerate(errors[:10]):
                logger.warning(f"{i+1}. {error}")
            if len(errors) > 10:
                logger.warning(f"... 还有 {len(errors) - 10} 个错误")
    else:
        logger.error(f"智能分配失败: {result.get('error', '未知错误')}")

def main():
    """主函数"""
    try:
        logger.info("开始使用真实数据调试通道分配问题")
        
        # 加载真实数据
        points_data, template_data = load_real_data()
        
        # 分析分配失败原因
        analyze_assignment_failure(points_data, template_data)
        
        logger.info("\n调试完成！")
        
    except Exception as e:
        logger.error(f"调试过程中出错: {e}", exc_info=True)

if __name__ == "__main__":
    main()
