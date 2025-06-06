"""
模板自动填写器
将通道分配结果转换为IO点表模板数据，自动填写灰色高亮字段
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TemplateFiller:
    """模板自动填写器"""
    
    def __init__(self):
        """初始化填写器"""
        logger.info("TemplateFiller initialized")
    
    def convert_assignment_to_plc_data(self, 
                                     project_id: str, 
                                     scheme_id: str,
                                     site_name: str = "",
                                     site_no: str = "") -> List[Dict[str, Any]]:
        """
        将通道分配结果转换为PLC导出器期望的数据格式
        
        Args:
            project_id: 项目ID
            scheme_id: 分配方案ID
            site_name: 场站名称
            site_no: 场站编号
            
        Returns:
            List[Dict]: PLC导出器期望的数据格式
        """
        try:
            # 导入数据访问对象
            from core.data_storage.parsed_data_dao import ParsedDataDAO
            from core.channel_assignment.persistence.assignment_dao import AssignmentDAO
            
            parsed_data_dao = ParsedDataDAO()
            assignment_dao = AssignmentDAO()
            
            # 获取解析的点位数据
            parsed_points = parsed_data_dao.get_parsed_points(project_id)
            if not parsed_points:
                logger.warning(f"项目 {project_id} 中没有找到解析的点位数据")
                return []
            
            # 获取分配方案
            assignment = assignment_dao.load_assignment(project_id, scheme_id)
            if not assignment:
                logger.warning(f"没有找到分配方案 {scheme_id}")
                return []
            
            # 创建点位ID到分配信息的映射
            assignment_map = {}
            for mapping in assignment.assignments:
                assignment_map[mapping.point_id] = mapping
            
            # 转换为PLC数据格式
            plc_data = []
            for point in parsed_points:
                # 检查是否有分配
                if point.id not in assignment_map:
                    logger.debug(f"点位 {point.instrument_tag} 未分配通道，跳过")
                    continue
                
                mapping = assignment_map[point.id]
                
                # 转换为PLC导出器期望的格式
                plc_point = self._convert_point_to_plc_format(
                    point, mapping, site_name, site_no
                )
                plc_data.append(plc_point)
            
            logger.info(f"成功转换 {len(plc_data)} 个点位为PLC数据格式")
            return plc_data
            
        except Exception as e:
            logger.error(f"转换分配数据为PLC格式时出错: {e}")
            return []
    
    def _convert_point_to_plc_format(self, 
                                   point, 
                                   mapping, 
                                   site_name: str, 
                                   site_no: str) -> Dict[str, Any]:
        """
        将单个点位和分配信息转换为PLC格式
        
        Args:
            point: ParsedPoint对象
            mapping: PointChannelMapping对象
            site_name: 场站名称
            site_no: 场站编号
            
        Returns:
            Dict: PLC导出器期望的点位数据格式
        """
        # 解析通道信息
        channel_parts = mapping.channel_id.split('-')
        io_type = channel_parts[0] if len(channel_parts) > 0 else ''
        channel_num = channel_parts[1] if len(channel_parts) > 1 else ''
        
        # 推断模块信息
        model_name = self._infer_module_name(io_type)
        module_type = self._infer_module_type(io_type)
        
        # 构建PLC数据格式
        plc_point = {
            # 基础信息 - 来自通道分配
            'address': mapping.channel_id,  # 通道位号，如 AI-01
            'type': io_type,               # 模块类型，如 AI
            'model': model_name,           # 模块名称
            
            # 自动填写的灰色字段 - 来自解析数据
            'hmi_variable': point.instrument_tag,  # 变量名称（HMI）
            'description': point.description,      # 变量描述
            'units': point.units,                  # 单位
            'power_supply': self._infer_power_type(point.power_supply),  # 供电类型
            'wiring': self._infer_wiring_system(point.signal_type),      # 线制
            
            # 量程信息 - 从解析数据提取
            'range_low': self._extract_range_low(point.data_range),
            'range_high': self._extract_range_high(point.data_range),
            
            # 报警设定值 - 可以从原始数据中提取或留空让用户填写
            'sll_setpoint': '',  # SLL设定值
            'sl_setpoint': '',   # SL设定值
            'sh_setpoint': '',   # SH设定值
            'shh_setpoint': '',  # SHH设定值
            
            # 场站信息
            'site_name': site_name,
            'site_no': site_no,
            
            # 原始数据保留
            'original_point_data': point.to_dict(),
            'assignment_info': {
                'channel_id': mapping.channel_id,
                'channel_type': mapping.channel_type,
                'assigned_at': mapping.assigned_at.isoformat()
            }
        }
        
        return plc_point
    
    def _infer_module_name(self, io_type: str) -> str:
        """推断模块名称"""
        module_names = {
            'AI': 'AI_Module',
            'AO': 'AO_Module', 
            'DI': 'DI_Module',
            'DO': 'DO_Module'
        }
        return module_names.get(io_type, f'{io_type}_Module')
    
    def _infer_module_type(self, io_type: str) -> str:
        """推断模块类型"""
        # 这里可以根据实际的模块类型映射规则来实现
        return io_type
    
    def _infer_power_type(self, power_supply: str) -> str:
        """推断供电类型"""
        if not power_supply:
            return ""
        
        power_supply_lower = power_supply.lower()
        if '回路供电' in power_supply_lower or '二线制' in power_supply_lower:
            return "无源"
        elif '外供电' in power_supply_lower or '四线制' in power_supply_lower:
            return "有源"
        else:
            return power_supply  # 保持原始值
    
    def _infer_wiring_system(self, signal_type: str) -> str:
        """推断线制"""
        if not signal_type:
            return ""
        
        # 根据信号类型推断线制
        if signal_type in ['AI', 'AO']:
            return "4-20mA"  # 模拟量通常是4-20mA
        elif signal_type in ['DI', 'DO']:
            return "24VDC"   # 数字量通常是24VDC
        else:
            return ""
    
    def _extract_range_low(self, data_range: str) -> str:
        """从数据范围提取低限值"""
        if not data_range:
            return ""
        
        try:
            # 处理常见的范围格式：0~100, 0-100, 0 to 100
            import re
            
            # 匹配模式：数字~数字 或 数字-数字
            pattern = r'(-?\d+(?:\.\d+)?)\s*[~\-to]\s*(-?\d+(?:\.\d+)?)'
            match = re.search(pattern, data_range)
            
            if match:
                return match.group(1)
            
            # 如果没有匹配到范围，尝试提取第一个数字
            number_pattern = r'(-?\d+(?:\.\d+)?)'
            number_match = re.search(number_pattern, data_range)
            if number_match:
                return number_match.group(1)
                
        except Exception as e:
            logger.debug(f"提取量程低限时出错: {e}, 数据范围: {data_range}")
        
        return ""
    
    def _extract_range_high(self, data_range: str) -> str:
        """从数据范围提取高限值"""
        if not data_range:
            return ""
        
        try:
            import re
            
            # 匹配模式：数字~数字 或 数字-数字
            pattern = r'(-?\d+(?:\.\d+)?)\s*[~\-to]\s*(-?\d+(?:\.\d+)?)'
            match = re.search(pattern, data_range)
            
            if match:
                return match.group(2)
                
        except Exception as e:
            logger.debug(f"提取量程高限时出错: {e}, 数据范围: {data_range}")
        
        return ""
    
    def generate_filled_template(self, 
                               project_id: str, 
                               scheme_id: str,
                               output_filename: str = None,
                               site_name: str = "",
                               site_no: str = "") -> Optional[str]:
        """
        生成自动填写的IO点表模板
        
        Args:
            project_id: 项目ID
            scheme_id: 分配方案ID
            output_filename: 输出文件名
            site_name: 场站名称
            site_no: 场站编号
            
        Returns:
            str: 生成的文件路径，失败时返回None
        """
        try:
            # 转换分配数据为PLC格式
            plc_data = self.convert_assignment_to_plc_data(
                project_id, scheme_id, site_name, site_no
            )
            
            if not plc_data:
                logger.error("没有可用的分配数据")
                return None
            
            # 生成输出文件名
            if not output_filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"自动填写的IO点表_{timestamp}.xlsx"
            
            # 确保输出目录存在
            import os
            from pathlib import Path
            
            project_root = Path(__file__).resolve().parents[2]
            output_dir = project_root / "outputs" / "filled_templates"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = output_dir / output_filename
            
            # 使用现有的导出器生成Excel
            from core.io_table.excel_exporter import IOExcelExporter
            
            exporter = IOExcelExporter()
            success = exporter.export_to_excel(
                plc_io_data=plc_data,
                filename=str(output_path),
                site_name=site_name,
                site_no=site_no
            )
            
            if success:
                logger.info(f"成功生成自动填写的IO点表: {output_path}")
                return str(output_path)
            else:
                logger.error("生成IO点表失败")
                return None
                
        except Exception as e:
            logger.error(f"生成自动填写模板时出错: {e}")
            return None
