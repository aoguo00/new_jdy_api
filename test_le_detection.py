#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LE系列设备识别测试脚本

用于测试和验证LE系列设备（特别是LE5118）的识别逻辑是否正常工作
"""

import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_le_device_detection():
    """测试LE系列设备识别"""
    try:
        from core.io_table.get_data import IODataLoader, DeviceDataProcessor, SystemSetupManager, ModuleInfoProvider
        
        logger.info("开始测试LE系列设备识别...")
        
        # 创建测试数据 - 模拟从简道云API获取的设备数据
        test_devices = [
            {
                'id': 1,
                '_widget_1635777115211': 'LE5118 CPU模块',  # 设备名称
                '_widget_1635777115248': '和利时',           # 品牌
                '_widget_1635777115287': 'LE5118',          # 规格型号
                '_widget_1641439264111': 'DC24V供电',       # 技术参数
                '_widget_1635777485580': '1',               # 数量
                '_widget_1654703913698': '台',              # 单位
                '_widget_1641439463480': '自带40点I/O'      # 技术参数(外部)
            },
            {
                'id': 2,
                '_widget_1635777115211': 'LE5210数字量输入模块',
                '_widget_1635777115248': '和利时',
                '_widget_1635777115287': 'LE5210',
                '_widget_1641439264111': '8通道数字量输入',
                '_widget_1635777485580': '2',
                '_widget_1654703913698': '台',
                '_widget_1641439463480': ''
            },
            {
                'id': 3,
                '_widget_1635777115211': 'LE5220数字量输出模块',
                '_widget_1635777115248': '和利时',
                '_widget_1635777115287': 'LE5220',
                '_widget_1641439264111': '8通道数字量输出',
                '_widget_1635777485580': '1',
                '_widget_1654703913698': '台',
                '_widget_1641439463480': ''
            }
        ]
        
        logger.info(f"测试数据包含 {len(test_devices)} 个设备")
        
        # 创建IODataLoader实例
        io_loader = IODataLoader()
        
        # 设置测试数据
        io_loader.set_devices_data(test_devices, force_update=True)
        
        # 获取机架信息
        rack_info = io_loader.get_rack_info()
        
        logger.info("=== 测试结果 ===")
        logger.info(f"系统类型: {rack_info.get('system_type', '未知')}")
        logger.info(f"机架数量: {rack_info.get('rack_count', 0)}")
        logger.info(f"每机架槽位数: {rack_info.get('slots_per_rack', 0)}")
        
        # 检查处理后的设备数据
        processed_devices = io_loader.processed_enriched_devices
        logger.info(f"处理后的设备数量: {len(processed_devices)}")
        
        le_devices = []
        for device in processed_devices:
            model = device.get('model', '')
            device_type = device.get('type', '')
            if 'LE' in model.upper():
                le_devices.append(device)
                logger.info(f"LE设备: {model} -> 类型: {device_type}")
        
        logger.info(f"识别到的LE系列设备数量: {len(le_devices)}")
        
        # 验证系统类型识别
        expected_system_type = "LE_CPU"
        actual_system_type = rack_info.get('system_type')
        
        if actual_system_type == expected_system_type:
            logger.info("✅ 系统类型识别正确！")
            return True
        else:
            logger.error(f"❌ 系统类型识别错误！期望: {expected_system_type}, 实际: {actual_system_type}")
            return False
            
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        return False

def test_module_info_provider():
    """测试模块信息提供者对LE5118的识别"""
    try:
        from core.io_table.get_data import ModuleInfoProvider
        
        logger.info("测试ModuleInfoProvider对LE5118的识别...")
        
        provider = ModuleInfoProvider()
        
        # 测试LE5118识别
        le5118_info = provider.get_predefined_module_by_model('LE5118')
        if le5118_info:
            logger.info(f"✅ LE5118模块信息: {le5118_info}")
            if le5118_info.get('type') == 'CPU':
                logger.info("✅ LE5118类型识别正确为CPU")
                return True
            else:
                logger.error(f"❌ LE5118类型识别错误: {le5118_info.get('type')}")
                return False
        else:
            logger.error("❌ 未找到LE5118模块信息")
            return False
            
    except Exception as e:
        logger.error(f"测试ModuleInfoProvider时发生错误: {e}", exc_info=True)
        return False

def main():
    """主测试函数"""
    logger.info("开始LE系列设备识别测试")
    
    # 测试1: 模块信息提供者
    test1_result = test_module_info_provider()
    
    # 测试2: 设备识别
    test2_result = test_le_device_detection()
    
    # 总结
    logger.info("=== 测试总结 ===")
    logger.info(f"模块信息提供者测试: {'通过' if test1_result else '失败'}")
    logger.info(f"设备识别测试: {'通过' if test2_result else '失败'}")
    
    if test1_result and test2_result:
        logger.info("🎉 所有测试通过！LE系列设备识别功能正常")
        return True
    else:
        logger.error("❌ 部分测试失败，需要检查LE系列设备识别逻辑")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
