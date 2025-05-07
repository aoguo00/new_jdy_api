"""PLC管理模块"""
import logging
from typing import Dict, List, Optional
from core.db_manipulate.db_manager import DBManager

logger = logging.getLogger(__name__)

class PLCManager:
    """PLC管理器类，用于管理所有PLC系列的通用功能"""
    
    def __init__(self, series_name: str = None):
        """
        初始化PLC管理器
        Args:
            series_name: PLC系列名称，如果不指定则可以通过set_series方法later设置
        """
        self.db_manager = DBManager()
        self._series_name = None
        self._series_id = None
        
        if series_name:
            self.set_series(series_name)
    
    def set_series(self, series_name: str) -> bool:
        """
        设置当前操作的PLC系列
        Args:
            series_name: PLC系列名称
        Returns:
            bool: 是否设置成功
        """
        if not series_name:
            return False
            
        # 检查系列是否存在
        series = self.db_manager.get_series_by_name(series_name)
        if not series:
            logger.warning(f"系列 {series_name} 不存在，将在首次使用时创建")
            
        self._series_name = series_name
        self._series_id = series['id'] if series else None
        return True  # 即使系列不存在也返回True，因为它会在首次使用时创建
    
    def _get_series_id(self) -> Optional[int]:
        """获取当前系列ID"""
        if not self._series_name:
            return None
            
        series = self.db_manager.get_series_by_name(self._series_name)
        return series['id'] if series else None
    
    def _ensure_series_exists(self) -> bool:
        """确保系列存在，如果不存在则创建"""
        if not self._series_name:
            return False
            
        if not self._series_id:
            success = self.db_manager.add_plc_series(
                self._series_name, 
                f"{self._series_name}系列PLC"
            )
            if success:
                self._series_id = self._get_series_id()
            return success
        return True
    
    def get_all_series(self) -> List[Dict]:
        """获取所有PLC系列"""
        return self.db_manager.get_all_plc_series()
    
    def add_module(self, model: str, module_type: str, channels: int, description: str) -> bool:
        """
        添加新模块
        Args:
            model: 模块型号
            module_type: 模块类型
            channels: 通道数
            description: 描述
        Returns:
            bool: 是否添加成功
        """
        if not self._ensure_series_exists():
            logger.error(f"系列 {self._series_name} 创建失败")
            return False
            
        return self.db_manager.add_module(
            self._series_id, model, module_type, channels, description
        )
    
    def delete_module(self, model: str) -> bool:
        """
        删除模块
        Args:
            model: 模块型号
        Returns:
            bool: 是否删除成功
        """
        if not self._series_id:
            logger.error(f"系列 {self._series_name} 不存在")
            return False
            
        return self.db_manager.delete_module(self._series_id, model)
    
    def get_modules_by_type(self, module_type: str) -> List[Dict]:
        """
        获取指定类型的模块列表
        Args:
            module_type: 模块类型
        Returns:
            List[Dict]: 模块列表
        """
        if not self._series_id:
            logger.error(f"系列 {self._series_name} 不存在")
            return []
            
        return self.db_manager.get_modules_by_type(self._series_id, module_type)
    
    def get_module_info(self, model: str) -> Optional[Dict]:
        """
        获取模块信息
        Args:
            model: 模块型号
        Returns:
            Optional[Dict]: 模块信息
        """
        if not self._series_id:
            logger.error(f"系列 {self._series_name} 不存在")
            return None
            
        return self.db_manager.get_module_info(self._series_id, model) 