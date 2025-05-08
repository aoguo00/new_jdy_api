"""设备列表服务，负责获取和处理特定场站的设备数据"""

from typing import List, Dict, Any, Optional
import logging

# 依赖 API 客户端和数据处理器
from core.query_area import JianDaoYunAPI
from .device_processor import format_device_data_for_ui

logger = logging.getLogger(__name__)

class DeviceService:
    def __init__(self, jdy_api: JianDaoYunAPI):
        if not jdy_api:
            logger.error("DeviceService 初始化失败: 未提供 JianDaoYunAPI 实例。")
            raise ValueError("JianDaoYunAPI 实例是必需的")
        self.jdy_api = jdy_api
        logger.info("DeviceService 初始化完成。")

    def get_formatted_devices(self, site_name: str) -> List[Dict[str, Any]]:
        """获取并格式化指定场站的设备列表数据以供UI使用。"""
        try:
            logger.info(f"DeviceService: 开始查询场站 '{site_name}' 的设备数据")
            # 1. 调用 API 获取原始数据
            response_data = self.jdy_api.query_site_devices(site_name)
            
            # 2. 调用处理器提取和格式化设备数据
            all_devices = format_device_data_for_ui(response_data, site_name)
            logger.info(f"DeviceService: 查询并格式化了场站 '{site_name}' 的 {len(all_devices)} 条设备数据。")
            return all_devices
        except Exception as e:
            logger.error(f"DeviceService 获取场站 '{site_name}' 设备数据失败: {e}", exc_info=True)
            # raise # 或者根据策略返回空列表
            return [] 