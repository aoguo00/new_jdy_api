"""
点位信息提取器
用于从解析的文档数据中提取和识别IO点位信息，包括IO类型识别和通道建议
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class PointInfoExtractor:
    """点位信息提取器"""
    
    def __init__(self):
        """初始化点位信息提取器"""
        # IO类型识别关键字
        self.io_type_keywords = {
            'AI': ['压力', '温度', '流量', '液位', '4-20mA', '0-10V'],
            'DI': ['状态', '故障', '报警', '开关', '干接点', '开关量'],
            'DO': ['控制', '启动', '停止', '阀门', '继电器', '0/24VDC'],
            'AO': ['设定', '输出', '调节', '4-20mA输出', '0-10V输出']
        }

        
    def extract_and_enhance_points(self, raw_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        提取并增强点位信息
        
        Args:
            raw_points (List[Dict[str, Any]]): 原始点位数据
            
        Returns:
            List[Dict[str, Any]]: 增强后的点位信息
        """
        logger.info(f"开始处理 {len(raw_points)} 个原始点位")
        
        enhanced_points = []
        for i, raw_point in enumerate(raw_points):
            try:
                enhanced_point = self._enhance_single_point(raw_point, i)
                if enhanced_point:
                    enhanced_points.append(enhanced_point)
                    
            except Exception as e:
                logger.warning(f"处理第 {i + 1} 个点位时出错: {e}")
                continue
                
        logger.info(f"成功处理 {len(enhanced_points)} 个点位")
        return enhanced_points
        
    def _enhance_single_point(self, raw_point: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
        """
        增强单个点位信息
        
        Args:
            raw_point (Dict[str, Any]): 原始点位数据
            index (int): 点位索引
            
        Returns:
            Optional[Dict[str, Any]]: 增强后的点位信息
        """
        # 获取基本信息
        instrument_tag = raw_point.get('instrument_tag', '').strip()
        description = raw_point.get('description', '').strip()
        signal_type = raw_point.get('signal_type', '').strip()
        
        # 基本验证
        if not instrument_tag and not description:
            logger.debug(f"点位 {index + 1} 缺少基本标识信息，跳过")
            return None
            
        # 创建增强的点位信息
        enhanced_point = {
            'instrument_tag': instrument_tag,
            'description': description,
            'signal_type': signal_type,
            'io_type': '',
            'range_low': '',
            'range_high': '',
            'units': '',
            'suggested_channel': '',
            'confidence': 0.0,  # 识别置信度
            'raw_data': raw_point
        }
        
        # 识别IO类型
        io_type, confidence = self._identify_io_type(instrument_tag, description, signal_type)
        enhanced_point['io_type'] = io_type
        enhanced_point['confidence'] = confidence
        
        # 简化：直接从原始数据中获取范围信息
        enhanced_point['range_low'] = raw_point.get('range_low', '')
        enhanced_point['range_high'] = raw_point.get('range_high', '')
        enhanced_point['units'] = raw_point.get('units', '')
            
        # 生成建议通道
        enhanced_point['suggested_channel'] = self._suggest_channel(io_type, index)
        
        logger.debug(f"点位 {index + 1} 增强完成: {instrument_tag} -> {io_type} (置信度: {confidence:.2f})")
        return enhanced_point
        
    def _identify_io_type(self, instrument_tag: str, description: str, signal_type: str) -> tuple:
        """
        识别IO类型

        Args:
            instrument_tag (str): 仪表位号
            description (str): 描述
            signal_type (str): 信号类型

        Returns:
            tuple: (IO类型, 置信度)
        """
        # 合并所有文本进行分析
        combined_text = f"{instrument_tag} {description} {signal_type}".lower()

        # 简单的关键字匹配
        for io_type, keywords in self.io_type_keywords.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    return io_type, 0.8  # 简化的置信度

        return 'UNKNOWN', 0.0

        
    def _suggest_channel(self, io_type: str, index: int) -> str:
        """
        建议通道分配
        
        Args:
            io_type (str): IO类型
            index (int): 点位索引
            
        Returns:
            str: 建议的通道
        """
        if io_type == 'UNKNOWN':
            return ''
            
        # 简单的顺序分配策略
        channel_number = (index % 16) + 1  # 假设每种类型最多16个通道
        return f"{io_type}-{channel_number:02d}"
        
    def get_io_type_statistics(self, points: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        获取IO类型统计信息
        
        Args:
            points (List[Dict[str, Any]]): 点位列表
            
        Returns:
            Dict[str, int]: IO类型统计
        """
        stats = {}
        for point in points:
            io_type = point.get('io_type', 'UNKNOWN')
            stats[io_type] = stats.get(io_type, 0) + 1
            
        return stats
        
    def validate_points(self, points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        验证和过滤点位数据
        
        Args:
            points (List[Dict[str, Any]]): 点位列表
            
        Returns:
            List[Dict[str, Any]]: 验证后的点位列表
        """
        valid_points = []
        
        for point in points:
            # 基本验证
            if not point.get('instrument_tag') and not point.get('description'):
                continue
                
            # 置信度验证
            if point.get('confidence', 0) < 0.1:  # 置信度太低
                logger.warning(f"点位 {point.get('instrument_tag', 'Unknown')} 置信度过低，跳过")
                continue
                
            valid_points.append(point)
            
        logger.info(f"验证完成，保留 {len(valid_points)}/{len(points)} 个有效点位")
        return valid_points
