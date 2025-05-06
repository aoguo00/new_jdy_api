"""和利时PLC系列管理模块"""
import logging
from typing import Dict, List, Optional
from core.db.db_manager import DBManager

logger = logging.getLogger(__name__)

class PLCSeriesManager:
    """PLC系列管理器"""
    
    def __init__(self, series_name: str = None):
        """
        初始化PLC系列管理器
        :param series_name: PLC系列名称，如果不指定则可以管理所有系列
        """
        self.series_name = series_name
        self.db_manager = DBManager()
        self._series_id = self._get_series_id() if series_name else None
    
    def _get_series_id(self) -> Optional[int]:
        """获取当前系列ID"""
        if not self.series_name:
            return None
        series = self.db_manager.get_series_by_name(self.series_name)
        return series['id'] if series else None
    
    def get_all_series(self) -> List[Dict]:
        """获取所有PLC系列"""
        return self.db_manager.get_all_plc_series()
    
    def add_series(self, name: str, description: str) -> bool:
        """添加新的PLC系列"""
        return self.db_manager.add_plc_series(name, description)
    
    def delete_series(self, name: str) -> bool:
        """删除PLC系列"""
        series = self.db_manager.get_series_by_name(name)
        if not series:
            return False
        return self.db_manager.delete_plc_series(series['id'])
    
    def add_module(self, model: str, module_type: str, channels: int, description: str) -> bool:
        """添加新模块"""
        if not self._series_id:
            logger.error(f"系列 {self.series_name} 不存在")
            return False
        return self.db_manager.add_module(self._series_id, model, module_type, channels, description)
    
    def delete_module(self, model: str) -> bool:
        """删除模块"""
        if not self._series_id:
            logger.error(f"系列 {self.series_name} 不存在")
            return False
        return self.db_manager.delete_module(self._series_id, model)
    
    def get_modules_by_type(self, module_type: str) -> List[Dict]:
        """获取指定类型的模块列表"""
        if not self._series_id:
            logger.error(f"系列 {self.series_name} 不存在")
            return []
        return self.db_manager.get_modules_by_type(self._series_id, module_type)
    
    def get_module_info(self, model: str) -> Optional[Dict]:
        """获取模块信息"""
        if not self._series_id:
            logger.error(f"系列 {self.series_name} 不存在")
            return None
        return self.db_manager.get_module_info(self._series_id, model) 