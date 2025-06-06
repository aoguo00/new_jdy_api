"""
基础文档解析器抽象类
定义文档解析器的通用接口和基础功能
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseDocumentParser(ABC):
    """文档解析器基础抽象类"""
    
    def __init__(self):
        """初始化基础解析器"""
        self.supported_extensions = []
        self.extracted_points = []
        
    @abstractmethod
    def parse_document(self, file_path: str) -> List[Dict[str, Any]]:
        """
        解析文档并提取点位信息
        
        Args:
            file_path (str): 文档文件路径
            
        Returns:
            List[Dict[str, Any]]: 提取的点位信息列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式不支持或内容无效
            Exception: 解析过程中的其他错误
        """
        pass
        
    def validate_file(self, file_path: str) -> bool:
        """
        验证文件是否存在且格式支持
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            bool: 文件是否有效
        """
        try:
            path = Path(file_path)
            
            # 检查文件是否存在
            if not path.exists():
                logger.error(f"文件不存在: {file_path}")
                return False
                
            # 检查文件扩展名
            if path.suffix.lower() not in self.supported_extensions:
                logger.error(f"不支持的文件格式: {path.suffix}")
                return False
                
            # 检查文件大小（避免过大的文件）
            file_size = path.stat().st_size
            max_size = 50 * 1024 * 1024  # 50MB
            if file_size > max_size:
                logger.error(f"文件过大: {file_size} bytes > {max_size} bytes")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"文件验证失败: {e}")
            return False
            
    def standardize_point_data(self, raw_point: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化点位数据格式
        
        Args:
            raw_point (Dict[str, Any]): 原始点位数据
            
        Returns:
            Dict[str, Any]: 标准化后的点位数据
        """
        # 定义标准字段映射
        standard_point = {
            'instrument_tag': '',           # 仪表位号
            'description': '',              # 检测点名称/描述
            'signal_type': '',              # 信号类型
            'io_type': '',                  # IO类型 (AI/DI/DO/AO)
            'range_low': '',                # 量程下限
            'range_high': '',               # 量程上限
            'units': '',                    # 单位
            'suggested_channel': '',        # 建议通道
            'raw_data': raw_point           # 保存原始数据
        }
        
        # 从原始数据中提取标准字段
        for key, value in raw_point.items():
            if isinstance(value, str):
                value = value.strip()
                
            # 映射常见的字段名
            key_lower = key.lower()
            if any(keyword in key_lower for keyword in ['位号', 'tag', '标号']):
                standard_point['instrument_tag'] = str(value)
            elif any(keyword in key_lower for keyword in ['名称', '描述', 'description', 'name']):
                standard_point['description'] = str(value)
            elif any(keyword in key_lower for keyword in ['信号', 'signal', '类型']):
                standard_point['signal_type'] = str(value)
            elif any(keyword in key_lower for keyword in ['单位', 'unit']):
                standard_point['units'] = str(value)
            elif any(keyword in key_lower for keyword in ['下限', 'low', 'min']):
                standard_point['range_low'] = str(value)
            elif any(keyword in key_lower for keyword in ['上限', 'high', 'max']):
                standard_point['range_high'] = str(value)
                
        return standard_point
        
    def get_supported_extensions(self) -> List[str]:
        """
        获取支持的文件扩展名列表
        
        Returns:
            List[str]: 支持的扩展名列表
        """
        return self.supported_extensions.copy()
        
    def get_parser_info(self) -> Dict[str, Any]:
        """
        获取解析器信息
        
        Returns:
            Dict[str, Any]: 解析器信息
        """
        return {
            'name': self.__class__.__name__,
            'supported_extensions': self.supported_extensions,
            'description': self.__doc__ or '无描述'
        }


class DocumentParserError(Exception):
    """文档解析器异常类"""
    pass


class UnsupportedFormatError(DocumentParserError):
    """不支持的文件格式异常"""
    pass


class ParseError(DocumentParserError):
    """解析错误异常"""
    pass
