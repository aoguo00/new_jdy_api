"""
智能表头检测器
用于识别不同格式的IO点表表头
"""

import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)


class SmartHeaderDetector:
    """智能表头检测器"""
    
    def __init__(self):
        # 定义更全面的字段同义词库
        self.field_synonyms = {
            'instrument_tag': {
                'primary': ['位号', '仪表位号', 'tag', 'TAG'],
                'secondary': ['设备位号', '点位号', '标号', '编号', '序号', '测点号', '变量号'],
                'english': ['instrument_tag', 'device_tag', 'point_tag', 'NO', 'No', 'ID'],
                'patterns': [r'.*位号.*', r'.*tag.*', r'.*编号.*', r'.*序号.*']
            },
            'description': {
                'primary': ['名称', '描述', '检测点名称', 'description'],
                'secondary': ['说明', '功能描述', '测点名称', '点位名称', '变量名称', '仪表名称'],
                'english': ['name', 'Name', 'function', 'purpose'],
                'patterns': [r'.*名称.*', r'.*描述.*', r'.*说明.*', r'.*检测点.*']
            },
            'signal_range': {
                'primary': ['信号范围', '信号', 'signal'],
                'secondary': ['量程', '范围', '输入范围', '测量范围', '信号量程'],
                'english': ['range', 'signal_range', 'input_range'],
                'patterns': [r'.*信号.*', r'.*量程.*', r'.*范围.*']
            },
            'data_range': {
                'primary': ['数据范围', '工程量', '工程值'],
                'secondary': ['测量值', '数值范围', '量程范围', '工程量程', '显示范围'],
                'english': ['data_range', 'engineering_range', 'value_range'],
                'patterns': [r'.*数据.*', r'.*工程.*', r'.*测量值.*']
            },
            'signal_type': {
                'primary': ['信号类型', '类型', 'type'],
                'secondary': ['IO类型', '通道类型', '输入类型', '输出类型', '接口类型'],
                'english': ['signal_type', 'io_type', 'channel_type'],
                'patterns': [r'.*类型.*', r'.*Type.*', r'.*IO.*']
            },
            'units': {
                'primary': ['单位', 'unit'],
                'secondary': ['工程单位', '量纲', '计量单位', '测量单位'],
                'english': ['units', 'engineering_unit'],
                'patterns': [r'.*单位.*', r'.*unit.*']
            },
            'power_supply': {
                'primary': ['供电', '现场仪表供电', 'power'],
                'secondary': ['电源', '仪表供电', '供电方式', '电源类型'],
                'english': ['power_supply', 'supply', 'voltage'],
                'patterns': [r'.*供电.*', r'.*电源.*', r'.*power.*']
            },
            'isolation': {
                'primary': ['隔离', 'isolation'],
                'secondary': ['隔离器', '安全栅', '隔离方式', '隔离类型'],
                'english': ['isolator', 'barrier', 'safety_barrier'],
                'patterns': [r'.*隔离.*', r'.*isolation.*']
            },
            'remarks': {
                'primary': ['备注', '说明', 'remarks'],
                'secondary': ['注释', '其他', '附注', '补充说明', '特殊说明'],
                'english': ['note', 'notes', 'comment'],
                'patterns': [r'.*备注.*', r'.*说明.*', r'.*note.*']
            }
        }
    
    def detect_headers(self, header_texts: List[str]) -> Dict[str, int]:
        """
        智能检测表头映射
        
        Args:
            header_texts: 表头文本列表
            
        Returns:
            Dict[str, int]: 字段名到列索引的映射
        """
        logger.info(f"开始智能检测表头，共 {len(header_texts)} 列")
        
        # 打印所有表头用于调试
        print(f"\n=== 智能表头检测 ===")
        for i, text in enumerate(header_texts):
            print(f"列 {i}: '{text}'")
        
        header_mapping = {}
        used_columns = set()
        
        # 第一轮：精确匹配主要关键字
        for field_name, synonyms in self.field_synonyms.items():
            best_match = self._find_best_match(header_texts, synonyms, used_columns, exact_match=True)
            if best_match:
                col_index, matched_text, score = best_match
                header_mapping[field_name] = col_index
                used_columns.add(col_index)
                print(f"✅ 精确匹配: '{matched_text}' -> {field_name} (列 {col_index}, 得分: {score})")
        
        # 第二轮：模糊匹配和模式匹配
        for field_name, synonyms in self.field_synonyms.items():
            if field_name in header_mapping:
                continue  # 已经匹配过了
                
            best_match = self._find_best_match(header_texts, synonyms, used_columns, exact_match=False)
            if best_match:
                col_index, matched_text, score = best_match
                header_mapping[field_name] = col_index
                used_columns.add(col_index)
                print(f"✅ 模糊匹配: '{matched_text}' -> {field_name} (列 {col_index}, 得分: {score})")
        
        # 第三轮：基于位置的智能推断
        if len(header_mapping) < 2:  # 如果匹配的字段太少，尝试智能推断
            inferred_mapping = self._infer_by_position(header_texts, header_mapping, used_columns)
            header_mapping.update(inferred_mapping)
        
        print(f"✅ 最终检测结果: {header_mapping}")
        return header_mapping
    
    def _find_best_match(self, header_texts: List[str], synonyms: Dict[str, List], 
                        used_columns: set, exact_match: bool = False) -> Optional[Tuple[int, str, float]]:
        """
        为字段找到最佳匹配的列
        
        Args:
            header_texts: 表头文本列表
            synonyms: 同义词字典
            used_columns: 已使用的列索引集合
            exact_match: 是否只进行精确匹配
            
        Returns:
            Optional[Tuple[int, str, float]]: (列索引, 匹配文本, 得分)
        """
        best_match = None
        best_score = 0
        
        for col_index, header_text in enumerate(header_texts):
            if col_index in used_columns or not header_text.strip():
                continue
            
            # 计算匹配得分
            score = self._calculate_match_score(header_text, synonyms, exact_match)
            
            if score > best_score:
                best_score = score
                best_match = (col_index, header_text, score)
        
        # 只返回得分足够高的匹配
        threshold = 0.8 if exact_match else 0.5
        if best_match and best_match[2] >= threshold:
            return best_match
        
        return None
    
    def _calculate_match_score(self, header_text: str, synonyms: Dict[str, List], exact_match: bool) -> float:
        """
        计算匹配得分
        
        Args:
            header_text: 表头文本
            synonyms: 同义词字典
            exact_match: 是否只进行精确匹配
            
        Returns:
            float: 匹配得分 (0-1)
        """
        header_text = header_text.strip()
        max_score = 0
        
        # 检查主要关键字（权重最高）
        for keyword in synonyms.get('primary', []):
            if exact_match:
                if header_text == keyword:
                    max_score = max(max_score, 1.0)
                elif keyword in header_text:
                    max_score = max(max_score, 0.9)
            else:
                similarity = SequenceMatcher(None, header_text.lower(), keyword.lower()).ratio()
                if similarity > 0.8:
                    max_score = max(max_score, similarity * 0.9)
        
        # 检查次要关键字（权重中等）
        for keyword in synonyms.get('secondary', []):
            if exact_match:
                if keyword in header_text:
                    max_score = max(max_score, 0.8)
            else:
                similarity = SequenceMatcher(None, header_text.lower(), keyword.lower()).ratio()
                if similarity > 0.7:
                    max_score = max(max_score, similarity * 0.7)
        
        # 检查英文关键字（权重中等）
        for keyword in synonyms.get('english', []):
            if keyword.lower() in header_text.lower():
                max_score = max(max_score, 0.8)
        
        # 检查正则表达式模式（权重较低）
        if not exact_match:
            for pattern in synonyms.get('patterns', []):
                if re.search(pattern, header_text, re.IGNORECASE):
                    max_score = max(max_score, 0.6)
        
        return max_score
    
    def _infer_by_position(self, header_texts: List[str], existing_mapping: Dict[str, int], 
                          used_columns: set) -> Dict[str, int]:
        """
        基于位置推断字段映射
        
        Args:
            header_texts: 表头文本列表
            existing_mapping: 已有的映射
            used_columns: 已使用的列索引集合
            
        Returns:
            Dict[str, int]: 推断的映射
        """
        inferred = {}
        
        # 如果没有找到位号列，通常第一列是位号
        if 'instrument_tag' not in existing_mapping and 0 not in used_columns:
            if len(header_texts) > 0:
                inferred['instrument_tag'] = 0
                used_columns.add(0)
                print(f"⚠️ 位置推断: 第1列 '{header_texts[0]}' -> instrument_tag")
        
        # 如果没有找到描述列，通常第二列是描述
        if 'description' not in existing_mapping and 1 not in used_columns:
            if len(header_texts) > 1:
                inferred['description'] = 1
                used_columns.add(1)
                print(f"⚠️ 位置推断: 第2列 '{header_texts[1]}' -> description")
        
        return inferred
