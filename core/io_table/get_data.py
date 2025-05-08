"""IO表格数据获取模块"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

# 导入模块定义
from .plc_modules import get_module_info_by_model, get_modules_by_type, get_all_modules

logger = logging.getLogger(__name__)

class IODataLoader:
    """IO数据加载器，负责获取和处理PLC IO配置数据"""
    
    # 和利时PLC产品前缀列表，用于过滤
    HOLLYSYS_PREFIXES = ['LK']
    
    # IO类型映射
    IO_TYPE_MAPPINGS = {
        'AI': ['AI', '模拟量输入', 'ANALOG INPUT'],
        'AO': ['AO', '模拟量输出', 'ANALOG OUTPUT'],
        'DI': ['DI', '数字量输入', '开关量输入', 'DIGITAL INPUT'],
        'DO': ['DO', '数字量输出', '开关量输出', 'DIGITAL OUTPUT'],
        'DP': ['DP', 'PROFIBUS', 'PROFIBUS-DP']
    }
    
    # 通道数默认映射
    CHANNEL_DEFAULTS = {
        'AI': 8,
        'AO': 4,
        'DI': 16,
        'DO': 16,
        'DP': 0,
        '未录入': 16
    }
    
    # 允许在穿梭框中显示的模块类型
    ALLOWED_MODULE_TYPES = ['AI', 'AO', 'DI', 'DO', 'DP']
    
    # 特殊允许的模块型号 (即使类型不在ALLOWED_MODULE_TYPES中也会显示)
    SPECIAL_ALLOWED_MODULES = ['LK238']
    
    # 每个机架的槽位数
    DEFAULT_RACK_SLOTS = 11  # 默认机架槽位数（LK117型号为11槽）
    
    def __init__(self):
        """初始化IO数据加载器"""
        self.modules_data = []  # 存储加载的模块数据
        self.original_devices_data = []  # 存储原始设备数据
        self.hollysys_filtered_devices = []  # 存储过滤后的和利时设备数据
        
        # 加载预定义的模块数据
        self.predefined_modules = get_all_modules()
        
        # 用于存储机架信息
        self.racks_data = []  # 机架数据
        self.rack_count = 0   # 机架数量
        
        logger.info(f"IODataLoader 初始化完成，加载了 {len(self.predefined_modules)} 个预定义模块")
    
    def set_devices_data(self, devices_data: List[Dict[str, Any]]) -> None:
        """
        设置设备数据并处理
        
        Args:
            devices_data: 设备数据列表
        """
        self.original_devices_data = devices_data or []
        
        # 处理设备数据，标准化字段
        processed_data = self._process_devices_data(self.original_devices_data)
        
        # 过滤和利时设备
        self.hollysys_filtered_devices = self._filter_hollysys_devices(processed_data)
        
        # 记录设备数据状态
        logger.info(f"收到原始设备数据: {len(self.original_devices_data)} 个")
        logger.info(f"处理后的和利时设备: {len(self.hollysys_filtered_devices)} 个")
        
        # 更新模块数据
        self.modules_data = self.hollysys_filtered_devices.copy()
        
        # 优化：为过滤后的设备补充预定义模块信息
        self._enrich_module_data()
        
        # 计算机架数量
        self._calculate_rack_info()
        
    def _calculate_rack_info(self):
        """计算机架数量并初始化机架数据"""
        # 查找LK117扩展背板数量 - 同时检查model字段和_widget_1635777115287字段
        rack_modules = [m for m in self.modules_data if 
                        'LK117' in m.get('model', '').upper() or 
                        'LK117' in m.get('_widget_1635777115287', '').upper()]
        logger.info(f"开始计算机架数量，找到 {len(rack_modules)} 条LK117背板记录")
        
        # 统计扩展背板数量 - LK117本身就是机架
        rack_count = 0
        
        # 先检查是否有LK117背板
        if rack_modules:
            # 先检查是否有数量信息
            for i, rack_module in enumerate(rack_modules):
                try:
                    # 尝试从quantity字段或_widget_1635777485580字段获取数量
                    quantity_str = rack_module.get('quantity', rack_module.get('_widget_1635777485580', ''))
                    model = rack_module.get('model', rack_module.get('_widget_1635777115287', ''))
                    device_id = rack_module.get('id', f'未知ID-{i}')
                    
                    logger.info(f"LK117背板 #{i+1} (ID={device_id}): 型号={model}, 数量字段值={quantity_str}")
                    
                    if quantity_str and quantity_str.isdigit():
                        current_count = int(quantity_str)
                        rack_count += current_count
                        logger.info(f"  -> 有效数量: {current_count}, 当前累计机架数: {rack_count}")
                    else:
                        # 如果没有quantity字段或非数字，默认数量为1
                        rack_count += 1
                        logger.warning(f"  -> 数量字段无效，默认为1, 当前累计机架数: {rack_count}")
                except (ValueError, TypeError) as e:
                    rack_count += 1
                    logger.error(f"  -> 解析数量时出错: {e}, 默认为1, 当前累计机架数: {rack_count}")
        else:
            # 如果没有找到LK117背板，至少有1个机架
            rack_count = 1
            logger.warning("未找到LK117背板记录，默认机架数量为1")
        
        # 确保至少有一个机架
        self.rack_count = max(1, rack_count)
        logger.info(f"最终计算得到机架数量: {self.rack_count} 个")
        
        # 创建机架数据
        self.racks_data = []
        for i in range(self.rack_count):
            rack_data = {
                'rack_id': i + 1,
                'rack_name': f"机架{i + 1}",
                'total_slots': self.DEFAULT_RACK_SLOTS,
                'available_slots': self.DEFAULT_RACK_SLOTS - 1,  # 第一槽位固定为DP模块
                'start_slot': 2,  # 用户可使用的起始槽位（从2开始）
                'modules': []
            }
            self.racks_data.append(rack_data)
            
        logger.info(f"系统配置: 共 {self.rack_count} 个机架，每个机架 {self.DEFAULT_RACK_SLOTS} 个槽位")
        logger.debug(f"背板模块记录列表: {[m.get('model', '') for m in rack_modules]}")
        
        # 记录关于机架的更多信息供调试
        if rack_modules:
            for i, module in enumerate(rack_modules):
                model = module.get('model', '')
                quantity = module.get('quantity', '1')
                logger.debug(f"背板 #{i+1}: 型号={model}, 数量={quantity}")
    
    def get_rack_info(self) -> Dict[str, Any]:
        """
        获取机架配置信息
        
        Returns:
            Dict[str, Any]: 机架配置信息
        """
        return {
            'rack_count': self.rack_count,
            'slots_per_rack': self.DEFAULT_RACK_SLOTS,
            'user_start_slot': 2,  # 用户可用的起始槽位（从2开始）
            'racks': self.racks_data
        }
    
    def get_slot_info(self, rack_id: int, slot_id: int) -> Dict[str, Any]:
        """
        获取特定槽位信息
        
        Args:
            rack_id: 机架ID（从1开始）
            slot_id: 槽位ID（从1开始）
            
        Returns:
            Dict[str, Any]: 槽位信息
        """
        # 校验输入
        if rack_id < 1 or rack_id > self.rack_count:
            return {'valid': False, 'error': f"机架ID {rack_id} 无效，系统共有 {self.rack_count} 个机架"}
            
        rack = self.racks_data[rack_id - 1]
        if slot_id < 1 or slot_id > rack['total_slots']:
            return {'valid': False, 'error': f"槽位ID {slot_id} 无效，机架 {rack_id} 共有 {rack['total_slots']} 个槽位"}
            
        # 槽位1为DP模块预留
        if slot_id == 1:
            return {
                'valid': True,
                'rack_id': rack_id,
                'slot_id': slot_id,
                'is_reserved': True,
                'reserved_for': 'DP',
                'message': "此槽位预留给PROFIBUS-DP通讯接口模块"
            }
            
        return {
            'valid': True,
            'rack_id': rack_id,
            'slot_id': slot_id,
            'is_reserved': False,
            'available': True,
            'message': f"机架 {rack_id} 槽位 {slot_id} 可用"
        }
    
    def get_available_slots(self) -> List[Dict[str, Any]]:
        """
        获取所有可用槽位信息
        
        Returns:
            List[Dict[str, Any]]: 可用槽位信息列表
        """
        available_slots = []
        
        for rack_id in range(1, self.rack_count + 1):
            rack = self.racks_data[rack_id - 1]
            # 从槽位2开始（槽位1预留给DP模块）
            for slot_id in range(2, rack['total_slots'] + 1):
                slot_info = {
                    'rack_id': rack_id,
                    'slot_id': slot_id,
                    'display_name': f"机架{rack_id}-槽位{slot_id}"
                }
                available_slots.append(slot_info)
                
        return available_slots
    
    def validate_module_placement(self, rack_id: int, slot_id: int, module_model: str) -> Dict[str, Any]:
        """
        验证模块放置是否有效
        
        Args:
            rack_id: 机架ID
            slot_id: 槽位ID
            module_model: 模块型号
            
        Returns:
            Dict[str, Any]: 验证结果
        """
        # 获取模块信息
        module_info = get_module_info_by_model(module_model)
        
        # 检查是否为DP模块
        if module_info.get('type') == 'DP':
            if slot_id != 1:
                return {
                    'valid': False,
                    'error': f"DP模块 {module_model} 只能放置在槽位1"
                }
        else:
            # 非DP模块不能放在槽位1
            if slot_id == 1:
                return {
                    'valid': False,
                    'error': f"槽位1只能放置DP模块，不能放置 {module_model}"
                }
        
        return {
            'valid': True,
            'message': f"模块 {module_model} 可以放置在机架 {rack_id} 槽位 {slot_id}"
        }

    def _process_devices_data(self, devices_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理设备数据，标准化字段
        
        Args:
            devices_data: 原始设备数据列表 (包含_widget_*字段)
            
        Returns:
            List[Dict[str, Any]]: 处理后的设备数据列表
        """
        processed_data = []
        
        # 字段映射关系 - 原始字段名 -> 标准字段名
        field_mapping = {
            '_widget_1635777115211': 'name',     # 设备名称
            '_widget_1635777115248': 'brand',    # 品牌
            '_widget_1635777115287': 'model',    # 规格型号
            '_widget_1641439264111': 'description',  # 技术参数
            '_widget_1635777485580': 'quantity', # 数量
            '_widget_1654703913698': 'unit',     # 单位
            '_widget_1641439463480': 'ext_params' # 技术参数(外部)
        }
        
        for i, device in enumerate(devices_data):
            try:
                # 创建新的设备字典，确保字段统一 - 转换原始_widget_*字段为标准名称
                processed_device = {
                    'id': device.get('id', i + 1),
                    'instance_index': device.get('instance_index', 1)  # 实例索引，用于区分相同设备的不同实例
                }
                
                # 映射原始字段到标准字段
                for widget_field, standard_field in field_mapping.items():
                    processed_device[standard_field] = device.get(widget_field, '').strip()
                    
                    # 同时保留原始字段名，以便后续处理
                    processed_device[widget_field] = device.get(widget_field, '').strip()
                
                # 设置类型字段 (如果没有type字段，则使用name作为type)
                if 'type' not in processed_device:
                    processed_device['type'] = processed_device.get('name', '')
                
                # 如果型号为空但品牌不为空，将型号设为品牌以便识别
                if not processed_device['model'] and processed_device['brand']:
                    processed_device['model'] = processed_device['brand']
                    logger.debug(f"设备 #{i+1}: 型号为空，使用品牌作为型号: {processed_device['brand']}")
                
                # 检查并设置IO类型
                processed_device['io_type'] = self._determine_io_type(processed_device)
                
                # 设置通道数
                processed_device['channels'] = self._determine_channels(processed_device)
                
                # 添加到处理后的列表
                processed_data.append(processed_device)
                
                # 输出调试信息
                logger.debug(f"处理设备 #{i+1}:")
                logger.debug(f"  名称: {processed_device['name']}")
                logger.debug(f"  品牌: {processed_device['brand']}")
                logger.debug(f"  型号: {processed_device['model']}")
                logger.debug(f"  IO类型: {processed_device['io_type']}")
                logger.debug(f"  通道数: {processed_device['channels']}")
                
            except Exception as e:
                logger.warning(f"处理设备数据时出错 (设备 #{i+1}): {e}")
                continue
                
        return processed_data
    
    def _enrich_module_data(self):
        """使用预定义的模块信息丰富过滤后的设备数据"""
        for device in self.hollysys_filtered_devices:
            model = device.get('model', '')
            if not model:
                continue
                
            # 查找预定义的模块信息
            module_info = get_module_info_by_model(model)
            if module_info:
                # 使用预定义信息更新设备数据
                device.update({
                    'type': module_info['type'],
                    'io_type': module_info['type'],
                    'channels': module_info['channels'],
                    'predefined_description': module_info['description']
                })
                
                # 如果原来没有描述，使用预定义描述
                if not device.get('description'):
                    device['description'] = module_info['description']
                    
                logger.debug(f"设备 {model} 使用预定义模块信息: {module_info['type']}, {module_info['channels']} 通道")

    def _determine_io_type(self, device: Dict[str, Any]) -> str:
        """
        根据设备信息确定IO类型
        
        Args:
            device: 设备字典 (可能包含标准字段名或_widget_*字段名)
            
        Returns:
            str: IO类型 (AI, AO, DI, DO, DP, 或 OTHER)
        """
        # 如果已有io_type字段且有效，则直接使用
        if device.get('io_type') and device['io_type'] in self.IO_TYPE_MAPPINGS:
            return device['io_type']
        
        # 首先尝试通过型号匹配预定义模块
        model = device.get('model', device.get('_widget_1635777115287', '')).upper()
        if model:
            module_info = get_module_info_by_model(model)
            if module_info and module_info['type'] in self.IO_TYPE_MAPPINGS:
                return module_info['type']
        
        # 如果未匹配到预定义模块，使用现有逻辑判断
        # 从型号和品牌中推断
        brand = device.get('brand', device.get('_widget_1635777115248', '')).upper()
        name = device.get('name', device.get('_widget_1635777115211', '')).upper()
        device_type = device.get('type', name).upper()  # 如果没有type字段，使用name
        description = device.get('description', device.get('_widget_1641439264111', '')).upper()
        ext_params = device.get('ext_params', device.get('_widget_1641439463480', '')).upper()
        
        # 合并所有文本字段，用于全文搜索关键字
        all_text = f"{model} {brand} {name} {device_type} {description} {ext_params}"
        
        # 检查是否为和利时产品
        is_hollysys = False
        if '和利时' in brand or 'HOLLYSYS' in brand or '和利时' in all_text or 'HOLLYSYS' in all_text:
            is_hollysys = True
        elif any(model.startswith(prefix) for prefix in self.HOLLYSYS_PREFIXES):
            is_hollysys = True
            
        # 和利时产品的型号通常遵循特定格式，可以更准确地推断
        if is_hollysys:
            # 和利时LK系列产品型号规则
            if 'LK41' in model:
                return 'AI'
            elif 'LK51' in model:
                return 'AO'
            elif 'LK61' in model:
                return 'DI'
            elif 'LK71' in model:
                return 'DO'
            elif 'LK81' in model or 'LK82' in model:
                return 'DP'
            elif 'LK9' in model:
                return 'CP'
            
            # 检查所有文本中的通用关键字
            if '模拟量输入' in all_text or 'ANALOG INPUT' in all_text:
                return 'AI'
            elif '模拟量输出' in all_text or 'ANALOG OUTPUT' in all_text:
                return 'AO'
            elif '数字量输入' in all_text or '开关量输入' in all_text or 'DIGITAL INPUT' in all_text:
                return 'DI'
            elif '数字量输出' in all_text or '开关量输出' in all_text or 'DIGITAL OUTPUT' in all_text:
                return 'DO'
            elif 'PROFIBUS' in all_text:
                return 'DP'
        
        # 通用逻辑：尝试从所有字段推断
        for io_type, keywords in self.IO_TYPE_MAPPINGS.items():
            for keyword in keywords:
                if keyword.upper() in all_text:
                    return io_type
        
        # 无法确定类型时的特殊处理
        if '1616' in model:  # 组合模块
            return 'DI/DO'
            
        # 特殊模块的类型处理
        if model == 'LK238' or model == 'LK238':
            return 'SP'  # 特殊类型，会被允许显示在穿梭框中
        
        return '未录入'
    
    def _determine_channels(self, device: Dict[str, Any]) -> int:
        """
        确定设备的通道数
        
        Args:
            device: 设备字典
            
        Returns:
            int: 通道数
        """
        # 首先尝试通过型号匹配预定义模块
        model = device.get('model', device.get('_widget_1635777115287', '')).upper()
        if model:
            module_info = get_module_info_by_model(model)
            if module_info:
                return module_info['channels']
        
        # 如果已有channels字段且有效，则直接使用
        if 'channels' in device and isinstance(device['channels'], (int, float, str)):
            try:
                return int(device['channels'])
            except (ValueError, TypeError):
                pass
        
        # 获取IO类型
        io_type = device.get('io_type', 'OTHER')
        
        # 从型号中提取通道数
        if '1616' in model:
            return 32  # 16入16出
        
        # 查找型号中的数字，可能表示通道数
        channel_match = re.search(r'(\d+)[ADIO]{1,2}', model)
        if channel_match:
            try:
                return int(channel_match.group(1))
            except (ValueError, IndexError):
                pass
        
        # 使用默认值
        for key, value in self.CHANNEL_DEFAULTS.items():
            if key in io_type:
                return value
        
        return self.CHANNEL_DEFAULTS['未录入']
    
    def _filter_hollysys_devices(self, devices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤和利时PLC产品
        
        Args:
            devices: 设备列表 (可能包含标准字段名或_widget_*字段名)
            
        Returns:
            List[Dict[str, Any]]: 过滤后的和利时产品列表
        """
        hollysys_devices = []
        known_hollysys_keywords = ['和利时', 'HOLLYSYS', 'LK']
        
        # 特殊处理LK117背板（机架）
        lk117_devices = []
        
        for device in devices:
            # 获取字段值，同时考虑标准字段名和原始_widget_*字段名
            model = device.get('model', device.get('_widget_1635777115287', '')).upper()
            brand = device.get('brand', device.get('_widget_1635777115248', '')).upper()
            name = device.get('name', device.get('_widget_1635777115211', '')).upper()
            type_str = device.get('type', name).upper()  # 如果没有type字段，使用name
            desc_str = device.get('description', device.get('_widget_1641439264111', '')).upper()
            ext_params = device.get('ext_params', device.get('_widget_1641439463480', '')).upper()
            quantity = device.get('quantity', device.get('_widget_1635777485580', '1'))
            
            # 合并所有文本字段，用于全文搜索关键字
            all_text = f"{model} {brand} {name} {type_str} {desc_str} {ext_params}"
            
            # 检查是否是LK117背板（机架）
            if 'LK117' in model or any(kw in all_text and '117' in all_text for kw in known_hollysys_keywords):
                # 确保标准化模型名称为LK117
                device['model'] = 'LK117'
                
                # 确保quantity字段存在且有效
                if not quantity or not str(quantity).isdigit():
                    device['quantity'] = '1'
                    logger.warning(f"LK117背板未指定有效数量，默认设为1")
                
                # 记录详细日志，方便排查问题
                logger.info(f"找到LK117背板（机架），原始数量值: {quantity}")
                logger.info(f"设备详情: ID={device.get('id', 'N/A')}, 名称={name}, 品牌={brand}, 型号={model}")
                
                lk117_devices.append(device)
                continue
                
            # 检查是否是和利时产品
            if any(keyword in all_text for keyword in known_hollysys_keywords):
                hollysys_devices.append(device)
                continue
                
            # 检查型号前缀
            if any(model.startswith(prefix) for prefix in self.HOLLYSYS_PREFIXES):
                hollysys_devices.append(device)
                continue
                
            # 检查型号中是否包含LK系列标识
            if 'LK' in model:
                hollysys_devices.append(device)
                continue
        
        # 处理背板数据
        if lk117_devices:
            hollysys_devices.extend(lk117_devices)
            
            # 记录背板的信息
            quantity_list = [device.get('quantity', '1') for device in lk117_devices]
            total_count = sum(int(q) if str(q).isdigit() else 1 for q in quantity_list)
            logger.info(f"找到 {len(lk117_devices)} 条LK117背板记录，数量值: {quantity_list}，总数量: {total_count}")
        
        # 记录过滤结果
        if not hollysys_devices:
            logger.warning(f"未找到和利时设备，原始设备数量: {len(devices)}")
            # 打印前5个设备的品牌和型号，帮助调试
            for i, dev in enumerate(devices[:5]):
                brand = dev.get('brand', dev.get('_widget_1635777115248', '无'))
                model = dev.get('model', dev.get('_widget_1635777115287', '无'))
                logger.debug(f"设备#{i+1}: 品牌={brand}, 型号={model}")
                
            # 打印搜索条件，帮助调试
            logger.debug(f"搜索条件: 和利时前缀={self.HOLLYSYS_PREFIXES}, 关键字={known_hollysys_keywords}")
        else:
            logger.info(f"找到 {len(hollysys_devices)} 个和利时设备（共 {len(devices)} 个设备）")
            
            # 统计找到的LK117背板数量
            lk117_count = sum(1 for dev in hollysys_devices if dev.get('model', '').upper() == 'LK117')
            if lk117_count > 0:
                logger.info(f"其中包含 {lk117_count} 条LK117背板记录")
            
            # 打印前3个找到的和利时设备，帮助确认过滤结果
            for i, dev in enumerate(hollysys_devices[:3]):
                brand = dev.get('brand', dev.get('_widget_1635777115248', '无'))
                model = dev.get('model', dev.get('_widget_1635777115287', '无'))
                quantity = dev.get('quantity', dev.get('_widget_1635777485580', '1'))
                logger.debug(f"和利时设备#{i+1}: 品牌={brand}, 型号={model}, 数量={quantity}")
            
        return hollysys_devices
    
    def get_filtered_modules(self, module_type: str = '全部') -> List[Dict[str, Any]]:
        """
        获取过滤后的模块列表
        
        Args:
            module_type: 模块类型，默认为'全部'
            
        Returns:
            List[Dict[str, Any]]: 过滤后的模块列表
        """
        if not self.modules_data and not self.predefined_modules:
            logger.warning("没有可用的模块数据")
            return []
            
        # 预定义模块优先
        all_modules = []
        if not self.modules_data and self.predefined_modules:
            # 如果没有从设备解析的模块，但有预定义模块
            all_modules = self.predefined_modules
        else:
            # 从实际设备解析的模块
            all_modules = self.modules_data
        
        # 过滤出允许显示的模块类型和特殊允许的模块型号
        filtered_modules = []
        for module in all_modules:
            module_type_value = module.get('type', module.get('io_type', '未录入'))
            module_model = module.get('model', '').upper()
            
            # 检查是否为特殊允许的模块
            if module_model in [m.upper() for m in self.SPECIAL_ALLOWED_MODULES]:
                filtered_modules.append(module)
                continue
                
            # 检查是否为允许的类型
            if module_type_value in self.ALLOWED_MODULE_TYPES:
                filtered_modules.append(module)
                continue
        
        # 如果指定了类型且不是"全部"，进一步过滤
        if module_type != '全部':
            filtered_modules = [m for m in filtered_modules 
                               if m.get('type', m.get('io_type', '')) == module_type]
                               
        logger.debug(f"过滤后的模块: 总计 {len(filtered_modules)} 个")
        return filtered_modules

    def load_available_modules(self, module_type: str = '全部') -> Tuple[List[Dict[str, Any]], bool]:
        """
        加载可用模块
        
        Args:
            module_type: 模块类型，默认为'全部'
            
        Returns:
            Tuple[List[Dict[str, Any]], bool]: (模块列表, 是否有数据)
        """
        try:
            # 如果设备数据为空但预定义模块不为空，使用预定义模块
            if not self.hollysys_filtered_devices and self.predefined_modules:
                if module_type == '全部':
                    modules = self.predefined_modules
                else:
                    modules = [m for m in self.predefined_modules if m.get('type') == module_type]
                    
                logger.info(f"使用预定义模块，找到 {len(modules)} 个 {module_type} 类型模块")
                return modules, len(modules) > 0
            
            # 使用过滤后的设备数据
            modules = self.get_filtered_modules(module_type)
            logger.info(f"从设备数据中找到 {len(modules)} 个 {module_type} 类型模块")
            return modules, len(modules) > 0
            
        except Exception as e:
            logger.error(f"加载模块时出错: {e}", exc_info=True)
            return [], False
    
    def get_module_by_id(self, module_id: int) -> Optional[Dict[str, Any]]:
        """
        通过ID查找模块
        
        Args:
            module_id: 模块ID
            
        Returns:
            Optional[Dict[str, Any]]: 模块信息，未找到时返回None
        """
        for module in self.modules_data:
            if module.get('id') == module_id:
                return module
        
        # 如果在模块数据中未找到，尝试在预定义模块中查找
        if module_id > 0 and module_id <= len(self.predefined_modules):
            return self.predefined_modules[module_id - 1]
            
        return None
    
    def get_module_by_model(self, model: str) -> Optional[Dict[str, Any]]:
        """
        通过型号查找模块
        
        Args:
            model: 模块型号
            
        Returns:
            Optional[Dict[str, Any]]: 模块信息，未找到时返回None
        """
        # 首先在当前数据中查找
        for module in self.modules_data:
            if module.get('model', '').upper() == model.upper():
                return module
        
        # 然后在预定义模块中查找
        for predefined in self.predefined_modules:
            if predefined.get('model', '').upper() == model.upper():
                return predefined
                
        # 如果都未找到，使用plc_modules模块的方法查找
        module_info = get_module_info_by_model(model)
        if module_info:
            return module_info
            
        return None
        
    def save_configuration(self, config) -> bool:
        """
        保存PLC模块配置
        
        Args:
            config: 配置数据，可以是列表格式 [{rack_id, slot_id, model}, ...] 或字典格式 {(rack_id, slot_id): model}
            
        Returns:
            bool: 是否保存成功
        """
        if not config:
            logger.warning("保存配置时接收到空配置数据")
            print("未收到任何PLC模块配置数据")
            return False
            
        # 转换配置格式为统一的字典格式
        config_dict = {}
        
        # 检查配置类型
        if isinstance(config, dict):
            # 如果已经是字典格式，直接使用
            config_dict = config
        elif isinstance(config, list):
            # 如果是列表格式，转换为字典格式
            try:
                for item in config:
                    rack_id = item.get("rack_id", 1)
                    slot_id = item.get("slot_id", 0)
                    model = item.get("model", "未知")
                    config_dict[(rack_id, slot_id)] = model
            except Exception as e:
                logger.error(f"转换配置格式时出错: {e}")
                return False
        else:
            logger.error(f"不支持的配置格式: {type(config)}")
            return False
        
        logger.info(f"接收到PLC模块配置请求: {len(config_dict)} 项")
        
        # 检查是否每个机架都有DP模块
        rack_has_dp = {}
        for (rack_id, slot_id), model in config_dict.items():
            # 记录机架信息
            if rack_id not in rack_has_dp:
                rack_has_dp[rack_id] = False
                
            # 检查是否为DP模块且在槽位1
            module_info = self.get_module_by_model(model)
            if module_info and module_info.get('type') == 'DP' and slot_id == 1:
                rack_has_dp[rack_id] = True
        
        # 检查每个机架是否都有DP模块
        missing_dp_racks = []
        for rack_id, has_dp in rack_has_dp.items():
            if not has_dp:
                missing_dp_racks.append(rack_id)
                
        if missing_dp_racks:
            error_msg = f"以下机架缺少DP模块（必须放在槽位1）: {', '.join(map(str, missing_dp_racks))}"
            logger.warning(error_msg)
            print(f"\n错误: {error_msg}")
            return False
        
        # 记录配置项详情
        for (rack_id, slot_id), model in config_dict.items():
            logger.info(f"机架 {rack_id} 槽位 {slot_id}: {model}")
            
            # 获取模块详细信息
            module_info = self.get_module_by_model(model)
            if module_info:
                logger.info(f"  - 类型: {module_info.get('type', '未知')}")
                logger.info(f"  - 通道数: {module_info.get('channels', '未知')}")
                logger.info(f"  - 描述: {module_info.get('description', '未知')}")
            else:
                logger.warning(f"  - 未找到模块 {model} 的详细信息")
        
        # 记录配置时间
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n-------- PLC模块配置 ({timestamp}) --------")
        print(f"共配置 {len(config_dict)} 个PLC模块，分布在 {len(rack_has_dp)} 个机架")
        
        # 统计每种类型的通道数量
        total_channels = {
            "AI": 0,
            "AO": 0,
            "DI": 0,
            "DO": 0,
            "DP": 0,
            "COM": 0,
            "未录入": 0
        }
        
        # 按机架分别展示配置
        for rack_id in sorted(rack_has_dp.keys()):
            rack_modules = [(r, s, m) for (r, s), m in config_dict.items() if r == rack_id]
            print(f"\n机架 {rack_id} 配置 ({len(rack_modules)} 个模块):")
            
            # 按槽位排序
            rack_modules.sort(key=lambda x: x[1])
            
            for r_id, s_id, model in rack_modules:
                module_info = self.get_module_by_model(model)
                if module_info:
                    module_type = module_info.get("type", "未知")
                    channels = module_info.get("channels", 0)
                    description = module_info.get("description", "")
                    print(f"  槽位 {s_id}: {model} ({module_type}, {channels}通道) - {description}")
                    
                    # 统计通道数
                    if "/" in module_type:
                        types = module_type.split("/")
                        channels_per_type = channels // len(types)
                        for t in types:
                            if t in total_channels:
                                # 只统计IO通道，忽略通信模块
                                if t not in ['DP', 'CP', 'COM']:
                                    total_channels[t] += channels_per_type
                            else:
                                total_channels["未录入"] += channels_per_type
                    else:
                        if module_type in total_channels:
                            # 只统计IO通道，忽略通信模块
                            if module_type not in ['DP', 'CP', 'COM']:
                                total_channels[module_type] += channels
                        else:
                            # 非标准类型且非通信模块，归为未录入
                            if module_type not in ['DP', 'CP', 'COM']:
                                total_channels["未录入"] += channels
                else:
                    print(f"  槽位 {s_id}: {model} (未知类型)")
        
        # 打印通道统计信息
        print("\n通道数统计:")
        total_all = 0
        # 只显示IO通道类型，并按顺序显示
        for io_type in ['AI', 'AO', 'DI', 'DO', '未录入']:
            count = total_channels.get(io_type, 0)
            if count > 0:
                print(f"{io_type} 通道数: {count}")
                total_all += count
        print(f"总通道数: {total_all}")  # 此处应该不包含DP、COM模块的通道
        
        # 保存当前配置
        self.current_configuration = config_dict
        
        # 生成通道位号列表
        all_channel_addresses = self.generate_channel_addresses(config_dict, include_non_io=True)
        
        # 分离IO通道和非IO通道
        io_channels = [addr for addr in all_channel_addresses if addr.get('is_io_channel', False)]
        non_io_channels = [addr for addr in all_channel_addresses if not addr.get('is_io_channel', False)]
        
        # 打印通道统计信息与实际IO通道数比较
        if hasattr(self, 'io_channel_count'):
            if total_all != self.io_channel_count:
                logger.warning(f"通道统计数量 ({total_all}) 与实际IO通道数 ({self.io_channel_count}) 不一致!")
            else:
                logger.info(f"通道统计数量与实际IO通道数一致: {total_all}")
        
        # 打印生成的通道位号列表 - 先显示IO通道，再显示通信模块
        print("\n-------- 通道位号列表 --------")
        print("序号\t模块名称\t模块类型\t通道位号\t类型")
        
        # 先显示所有IO通道
        io_idx = 1
        for addr_info in io_channels:
            print(f"{io_idx}\t{addr_info['model']}\t{addr_info['type']}\t{addr_info['address']}\tIO通道")
            io_idx += 1
        
        # 然后显示通信模块
        if non_io_channels:
            print("\n-------- 通信模块列表 (不计入IO通道) --------")
            for idx, addr_info in enumerate(non_io_channels, 1):
                print(f"{idx}\t{addr_info['model']}\t{addr_info['type']}\t{addr_info['address']}\t通信模块")
        
        print(f"\n总IO通道数: {len(io_channels)}, 非IO通道模块: {len(non_io_channels)}")
        print("注意: 配置数据已记录，实际保存功能尚未实现，在实际项目中应保存到数据库或配置文件中。")
        print("--------------------------------------\n")
        
        # 实际项目中，这里应当实现真正的保存逻辑
        # TODO: 实现配置保存到数据库或配置文件
        
        return True

    def generate_channel_addresses(self, config: Dict[tuple, str], include_non_io: bool = True) -> List[Dict[str, Any]]:
        """
        根据模块配置生成通道位号列表
        
        通道位号格式为: 机架号_槽号_模块类型_通道号
        例如: 1_2_AI_0 表示机架1，槽位2，模块类型AI，通道0
        
        Args:
            config: 配置数据字典，格式为 {(rack_id, slot_id): model}
            include_non_io: 是否包含非IO通道模块(如DP、COM模块)的记录，默认为True
            
        Returns:
            List[Dict[str, Any]]: 通道位号列表，每个元素包含模块信息和通道位号
        """
        channel_addresses = []
        io_channel_count = 0  # 只计算实际IO通道数
        
        # 按机架和槽位排序处理所有模块
        sorted_config = sorted(config.items(), key=lambda x: (x[0][0], x[0][1]))
        
        for (rack_id, slot_id), model in sorted_config:
            # 获取模块信息
            module_info = self.get_module_by_model(model)
            if not module_info:
                logger.warning(f"未找到模块 {model} 的信息，无法生成通道位号")
                continue
                
            module_type = module_info.get('type', '未知')
            channels_count = module_info.get('channels', 0)
            
            # 处理没有通道的模块类型（通信模块）
            if module_type in ['DP', 'CP', 'COM'] or channels_count == 0:
                # 如果要包含非IO模块，则添加一个记录
                if include_non_io:
                    channel_addresses.append({
                        'rack_id': rack_id,
                        'slot_id': slot_id,
                        'model': model,
                        'type': module_type,
                        'channel': 0,
                        'address': f"{rack_id}_{slot_id}_{module_type}_0",
                        'is_io_channel': False  # 标记为非IO通道
                    })
                continue
                
            # 为每个通道生成位号
            for channel_idx in range(channels_count):
                channel_address = f"{rack_id}_{slot_id}_{module_type}_{channel_idx}"
                
                channel_addresses.append({
                    'rack_id': rack_id,
                    'slot_id': slot_id,
                    'model': model,
                    'type': module_type,
                    'channel': channel_idx,
                    'address': channel_address,
                    'is_io_channel': True  # 标记为IO通道
                })
                io_channel_count += 1
                
        # 记录实际IO通道数量
        logger.info(f"生成了 {len(channel_addresses)} 个通道位号记录，其中实际IO通道 {io_channel_count} 个")
        
        # 保存通道位号列表
        self.channel_addresses = channel_addresses
        self.io_channel_count = io_channel_count
        
        return channel_addresses
        
    def get_channel_addresses(self) -> List[Dict[str, Any]]:
        """
        获取当前配置的通道位号列表
        
        Returns:
            List[Dict[str, Any]]: 通道位号列表
        """
        if hasattr(self, 'channel_addresses'):
            return self.channel_addresses
        return [] 