#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LE系列设备识别问题诊断脚本

用于诊断用户实际数据中LE系列设备识别问题
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

def diagnose_current_data():
    """诊断当前加载的数据"""
    try:
        from core.io_table.get_data import IODataLoader
        
        logger.info("开始诊断当前数据...")
        
        # 创建IODataLoader实例
        io_loader = IODataLoader()
        
        # 检查是否有当前数据
        if not hasattr(io_loader, 'original_devices_data') or not io_loader.original_devices_data:
            logger.warning("没有找到当前加载的设备数据")
            logger.info("请先在主程序中选择一个场站，然后再运行此诊断脚本")
            return False
        
        original_data = io_loader.original_devices_data
        logger.info(f"原始设备数据数量: {len(original_data)}")
        
        # 分析原始数据中的LE系列设备
        le_devices_in_raw = []
        for device in original_data:
            model = device.get('_widget_1635777115287', '').upper()  # 规格型号字段
            name = device.get('_widget_1635777115211', '').upper()   # 设备名称字段
            brand = device.get('_widget_1635777115248', '').upper()  # 品牌字段
            
            if 'LE' in model or 'LE5118' in name or 'LE' in brand:
                le_devices_in_raw.append({
                    'name': device.get('_widget_1635777115211', ''),
                    'brand': device.get('_widget_1635777115248', ''),
                    'model': device.get('_widget_1635777115287', ''),
                    'description': device.get('_widget_1641439264111', ''),
                    'quantity': device.get('_widget_1635777485580', ''),
                    'ext_params': device.get('_widget_1641439463480', '')
                })
        
        logger.info(f"原始数据中发现的LE系列设备: {len(le_devices_in_raw)}")
        for i, device in enumerate(le_devices_in_raw, 1):
            logger.info(f"  {i}. 名称: {device['name']}")
            logger.info(f"     品牌: {device['brand']}")
            logger.info(f"     型号: {device['model']}")
            logger.info(f"     描述: {device['description']}")
            logger.info(f"     数量: {device['quantity']}")
            logger.info(f"     参数: {device['ext_params']}")
            logger.info("")
        
        # 检查处理后的数据
        if hasattr(io_loader, 'processed_enriched_devices'):
            processed_data = io_loader.processed_enriched_devices
            logger.info(f"处理后的设备数据数量: {len(processed_data)}")
            
            le_devices_processed = []
            for device in processed_data:
                model = device.get('model', '').upper()
                if 'LE' in model:
                    le_devices_processed.append(device)
            
            logger.info(f"处理后数据中的LE系列设备: {len(le_devices_processed)}")
            for i, device in enumerate(le_devices_processed, 1):
                logger.info(f"  {i}. 型号: {device.get('model', '')}")
                logger.info(f"     类型: {device.get('type', '')}")
                logger.info(f"     IO类型: {device.get('io_type', '')}")
                logger.info(f"     通道数: {device.get('channels', 0)}")
                logger.info("")
        
        # 检查系统类型识别结果
        rack_info = io_loader.get_rack_info()
        system_type = rack_info.get('system_type', '未知')
        rack_count = rack_info.get('rack_count', 0)
        
        logger.info("=== 系统识别结果 ===")
        logger.info(f"系统类型: {system_type}")
        logger.info(f"机架数量: {rack_count}")
        
        # 诊断建议
        logger.info("=== 诊断建议 ===")
        if len(le_devices_in_raw) > 0:
            if system_type == "LE_CPU":
                logger.info("✅ LE系列设备已正确识别，系统类型为LE_CPU")
                logger.info("✅ 应该可以正常使用PLC配置功能")
            else:
                logger.warning("❌ 发现LE系列设备但系统类型不是LE_CPU")
                logger.warning("可能的原因:")
                logger.warning("1. LE5118设备的类型没有被正确识别为CPU")
                logger.warning("2. 设备数据中缺少关键信息")
                
                # 检查是否有LE5118且类型为CPU
                has_le5118_cpu = False
                for device in le_devices_processed:
                    if 'LE5118' in device.get('model', '').upper() and device.get('type', '').upper() == 'CPU':
                        has_le5118_cpu = True
                        break
                
                if not has_le5118_cpu:
                    logger.warning("3. 没有找到类型为CPU的LE5118设备")
                    logger.info("建议: 检查设备数据中LE5118的类型设置")
        else:
            logger.info("ℹ️ 没有发现LE系列设备，系统类型为LK是正确的")
        
        return True
        
    except Exception as e:
        logger.error(f"诊断过程中发生错误: {e}", exc_info=True)
        return False

def check_plc_modules_json():
    """检查PLC模块JSON文件中的LE系列定义"""
    try:
        import json
        
        json_path = Path("db/plc_modules.json")
        if not json_path.exists():
            logger.error(f"PLC模块JSON文件不存在: {json_path}")
            return False
        
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        le_modules = data.get('HOLLYSYS_LE_MODULES', [])
        logger.info(f"PLC模块JSON中定义的LE系列模块数量: {len(le_modules)}")
        
        # 查找LE5118
        le5118_found = False
        for module in le_modules:
            if module.get('model', '').upper() == 'LE5118':
                le5118_found = True
                logger.info(f"✅ 找到LE5118定义: {module}")
                break
        
        if not le5118_found:
            logger.error("❌ 在PLC模块JSON中没有找到LE5118定义")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"检查PLC模块JSON时发生错误: {e}", exc_info=True)
        return False

def main():
    """主诊断函数"""
    logger.info("开始LE系列设备识别问题诊断")
    logger.info("=" * 50)
    
    # 检查1: PLC模块JSON文件
    logger.info("检查1: PLC模块JSON文件")
    json_check = check_plc_modules_json()
    logger.info("")
    
    # 检查2: 当前数据诊断
    logger.info("检查2: 当前数据诊断")
    data_check = diagnose_current_data()
    logger.info("")
    
    # 总结
    logger.info("=== 诊断总结 ===")
    logger.info(f"PLC模块JSON检查: {'通过' if json_check else '失败'}")
    logger.info(f"当前数据检查: {'通过' if data_check else '失败'}")
    
    if json_check and data_check:
        logger.info("🎉 诊断完成，LE系列设备识别功能应该正常工作")
    else:
        logger.error("❌ 发现问题，请根据上述建议进行修复")
    
    logger.info("")
    logger.info("如果问题仍然存在，请:")
    logger.info("1. 确保在主程序中选择了包含LE系列设备的场站")
    logger.info("2. 检查设备数据中LE5118的型号字段是否正确")
    logger.info("3. 重新启动程序并重新选择场站")

if __name__ == '__main__':
    main()
