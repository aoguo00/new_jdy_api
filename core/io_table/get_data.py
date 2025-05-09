"""IO表格数据获取模块"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

# 导入模块定义
from .plc_modules import get_module_info_by_model, get_modules_by_type, get_all_modules, PLC_SERIES # 导入PLC_SERIES

logger = logging.getLogger(__name__)

class IODataLoader:
    """IO数据加载器，负责获取和处理PLC IO配置数据"""
    
    # 和利时PLC产品前缀列表，用于过滤 (从plc_modules动态生成)
    HOLLYSYS_PREFIXES = [prefix for series in PLC_SERIES.values() for prefix in series["prefixes"]]
    
    # IO类型映射
    IO_TYPE_MAPPINGS = {
        "CPU": ["CPU", "中央处理单元"],
        'AI': ['AI', '模拟量输入', 'ANALOG INPUT'],
        'AO': ['AO', '模拟量输出', 'ANALOG OUTPUT'],
        'DI': ['DI', '数字量输入', '开关量输入', 'DIGITAL INPUT'],
        'DO': ['DO', '数字量输出', '开关量输出', 'DIGITAL OUTPUT'],
        'DI/DO': ['DI/DO', '数字量输入输出', '数字量混合'],
        'AI/AO': ['AI/AO', '模拟量输入输出', '模拟量混合'],
        'DP': ['DP', 'PROFIBUS', 'PROFIBUS-DP'],
        'COM': ['COM', '通讯']
    }
    
    # 通道数默认映射
    CHANNEL_DEFAULTS = {
        "CPU": 0,
        'AI': 8,
        'AO': 4,
        'DI': 16,
        'DO': 16,
        'DI/DO': 16, 
        'AI/AO': 6, # 混合模块的默认总通道数
        'DP': 0,
        'COM': 0, 
        '未录入': 16 # 对于完全未知的类型，给一个通用猜测值
    }
    
    # 允许在穿梭框中显示的模块类型
    ALLOWED_MODULE_TYPES = ["CPU", 'AI', 'AO', 'DI', 'DO', 'DI/DO', 'AI/AO', 'DP', 'COM'] # 添加CPU类型
    
    # 特殊允许的模块型号 (即使类型不在ALLOWED_MODULE_TYPES中也会显示)
    # 动态生成，包含所有预定义模块中的COM类型以及其他特殊型号
    SPECIAL_ALLOWED_MODULES = list(set(
        [m["model"] for m in get_all_modules() if m["type"] == "COM"] + 
        [m["model"] for m in get_all_modules() if m["type"] == "DI/DO"] + 
        [m["model"] for m in get_all_modules() if m["type"] == "AI/AO"] + # 允许AI/AO模块
        ["LK238"] # 保留对旧特殊模块的兼容
    ))
    # 确保唯一性
    SPECIAL_ALLOWED_MODULES = list(set(SPECIAL_ALLOWED_MODULES))

    # 每个机架的槽位数 (LE系列可能没有传统机架，这里主要为LK系列服务)
    DEFAULT_RACK_SLOTS = 11
    
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
        self.system_type = "LK" # 默认为LK系统, 可为 "LE_CPU"
        
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
        """计算机架数量并初始化机架数据，同时判断系统类型（LK或LE_CPU）"""
        self.system_type = "LK" # 默认是LK系统
        cpu_modules = [m for m in self.modules_data if m.get('type') == 'CPU']
        
        if any(m.get('model', '').upper() == 'LE5118' for m in cpu_modules):
            self.system_type = "LE_CPU" 
            logger.info("检测到LE5118 CPU，系统类型设置为 LE_CPU")
            # 对于LE_CPU系统，机架数量由LE5118（或其他CPU模块）决定，通常为1个主机构架。
            # 扩展功能板不计为独立机架，而是属于这个CPU控制的系统。
            self.rack_count = 1 # LE5118系统视为一个集成机架
        else:
            # LK系统或其他非特定CPU系统，机架数量通过LK117背板计算
            rack_modules = [m for m in self.modules_data if 'LK117' in m.get('model', '').upper()]                
            rack_count_lk = 0
            if rack_modules:
                for rack_module in rack_modules:
                    try:
                        quantity_str = rack_module.get('quantity', rack_module.get('_widget_1635777485580', '1'))
                        rack_count_lk += int(quantity_str) if quantity_str and quantity_str.isdigit() else 1
                    except (ValueError, TypeError): rack_count_lk += 1
            self.rack_count = max(1, rack_count_lk) # 至少1个机架
            logger.info(f"LK或通用系统，通过LK117计算得到机架数量: {self.rack_count}")

        self.racks_data = []
        for i in range(self.rack_count):
            rack_data = {
                'rack_id': i + 1,
                'rack_name': f"机架{i + 1}",
                'total_slots': self.DEFAULT_RACK_SLOTS,
                 # 对于LE_CPU系统，槽位1由用户放置CPU；对于LK，槽位1固定DP
                'available_slots': self.DEFAULT_RACK_SLOTS if self.system_type == "LE_CPU" else self.DEFAULT_RACK_SLOTS -1,
                'start_slot': 1 if self.system_type == "LE_CPU" else 2, 
                'modules': [],
                'system_type': self.system_type # 把系统类型也加入机架数据
            }
            self.racks_data.append(rack_data)
        logger.info(f"系统配置: 类型={self.system_type}, 共 {self.rack_count} 个机架，每个机架 {self.DEFAULT_RACK_SLOTS} 个槽位 (逻辑定义)")

    def get_rack_info(self) -> Dict[str, Any]:
        """
        获取机架配置信息
        
        Returns:
            Dict[str, Any]: 机架配置信息
        """
        return {
            'rack_count': self.rack_count,
            'slots_per_rack': self.DEFAULT_RACK_SLOTS,
            'user_start_slot': 1 if self.system_type == "LE_CPU" else 2,
            'racks': self.racks_data,
            'system_type': self.system_type # 暴露系统类型
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
        module_info = get_module_info_by_model(module_model)
        module_type = module_info.get('type')

        # 获取当前机架的系统类型 (应该从self.racks_data获取对应rack_id的system_type)
        # 为简化，我们暂时假设所有机架共享self.system_type，但在多机架混合系统中可能需要更细致处理
        current_rack_system_type = self.system_type 
        # rack_data = next((r for r in self.racks_data if r['rack_id'] == rack_id), None)
        # if rack_data: current_rack_system_type = rack_data.get('system_type', self.system_type)

        if current_rack_system_type == "LE_CPU":
            if slot_id == 1:
                if module_type != 'CPU' or module_model.upper() != 'LE5118': #槽位1必须是LE5118 CPU
                    return {'valid': False, 'error': f"LE系统槽位1只能放置LE5118 CPU模块"}
            elif module_type == 'CPU': # CPU模块不能放在其他槽位
                 return {'valid': False, 'error': f"LE5118 CPU模块只能放置在槽位1"}
        elif current_rack_system_type == "LK": # LK系统逻辑
            if module_type == 'DP':
                if slot_id != 1:
                    return {'valid': False, 'error': f"DP模块 {module_model} 只能放置在LK系统槽位1"}
            elif slot_id == 1: # LK系统槽位1只能放DP
                return {'valid': False, 'error': f"LK系统槽位1只能放置DP模块，不能放置 {module_model}"}
        
        # 通用检查：背板模块不能直接添加
        if module_type == 'RACK':
            return {'valid': False, 'error': "背板模块不能直接添加到配置中"}
            
        return {'valid': True, 'message': f"模块 {module_model} 可以放置在机架 {rack_id} 槽位 {slot_id}"}

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
                
            # 查找预定义的模块信息 (从 plc_modules.py)
            module_info = get_module_info_by_model(model) # This is plc_modules.get_module_info_by_model
            if module_info:
                # 构建要更新的字典
                update_dict = {
                    'type': module_info.get('type'), # 使用 .get() 以增加稳健性
                    'io_type': module_info.get('type'), # io_type 通常与 type 相同
                    'channels': module_info.get('channels'),
                    'predefined_description': module_info.get('description')
                }
                
                # 如果预定义信息中有 sub_channels，复制过来
                if 'sub_channels' in module_info:
                    update_dict['sub_channels'] = module_info['sub_channels']
                
                # 如果预定义信息中有 power_supply，复制过来
                if 'power_supply' in module_info:
                    update_dict['power_supply'] = module_info['power_supply']
                
                # 其他可能需要从预定义模块复制的关键信息可以在此添加
                # 例如 is_master, slot_required等，如果它们对于运行时行为重要的话
                if 'is_master' in module_info:
                    update_dict['is_master'] = module_info['is_master']
                if 'slot_required' in module_info:
                    update_dict['slot_required'] = module_info['slot_required']

                # 使用预定义信息更新设备数据
                device.update(update_dict)
                
                # 如果设备原来没有描述，或描述为空，使用预定义描述
                if not device.get('description') and module_info.get('description'):
                    device['description'] = module_info['description']
                    
                logger.debug(f"设备 {model} 已使用预定义模块信息进行丰富: 类型={module_info.get('type')}, 通道={module_info.get('channels')}, 子通道={module_info.get('sub_channels')}")

    def _determine_io_type(self, device: Dict[str, Any]) -> str:
        """
        根据设备信息确定IO类型
        """
        # 如果已有io_type字段且有效，则直接使用
        if device.get('io_type') and device['io_type'] in self.IO_TYPE_MAPPINGS:
            return device['io_type']
        
        model = device.get('model', device.get('_widget_1635777115287', '')).upper()
        if model:
            module_info = get_module_info_by_model(model) 
            if module_info and module_info['type'] != "未录入":
                return module_info['type']
        
        brand = device.get('brand', device.get('_widget_1635777115248', '')).upper()
        name = device.get('name', device.get('_widget_1635777115211', '')).upper()
        device_type_str = device.get('type', name).upper()
        description = device.get('description', device.get('_widget_1641439264111', '')).upper()
        ext_params = device.get('ext_params', device.get('_widget_1641439463480', '')).upper()
        all_text = f"{model} {brand} {name} {device_type_str} {description} {ext_params}"
        
        is_hollysys = False
        if '和利时' in brand or 'HOLLYSYS' in brand or any(keyword in all_text for keyword in ['和利时', 'HOLLYSYS']):
            is_hollysys = True
        elif any(model.startswith(prefix) for prefix in self.HOLLYSYS_PREFIXES):
            is_hollysys = True
            
        if is_hollysys:
            # 模块定义文件中的前缀判断优先 (MODULE_TYPE_PREFIXES from plc_modules)
            for type_key, prefixes_list in MODULE_TYPE_PREFIXES.items(): 
                if any(model.startswith(p) for p in prefixes_list):
                    return type_key
            # 再次检查文本关键字
            for io_type_key, keywords in self.IO_TYPE_MAPPINGS.items():
                for keyword in keywords:
                    if keyword.upper() in all_text:
                        return io_type_key
        
        for io_type_key, keywords in self.IO_TYPE_MAPPINGS.items(): # 通用逻辑
            for keyword in keywords:
                if keyword.upper() in all_text:
                    return io_type_key
        
        if '1616' in model: return 'DI/DO'
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
        过滤和利时PLC产品 (包括LK和LE系列)
        """
        hollysys_devices = []
        # known_hollysys_keywords现在可以从HOLLYSYS_PREFIXES和品牌名生成
        known_hollysys_keywords = ['和利时', 'HOLLYSYS'] + self.HOLLYSYS_PREFIXES
        
        rack_devices = [] # 用于存放背板/机架类设备

        for device in devices:
            model_upper = device.get('model', device.get('_widget_1635777115287', '')).upper()
            brand_upper = device.get('brand', device.get('_widget_1635777115248', '')).upper()
            name_upper = device.get('name', device.get('_widget_1635777115211', '')).upper()
            
            all_text_upper = f"{model_upper} {brand_upper} {name_upper} {device.get('type', name_upper).upper()} {device.get('description', '').upper()} {device.get('ext_params', '').upper()}"

            is_hollysys_device = False
            if any(keyword.upper() in all_text_upper for keyword in known_hollysys_keywords):
                is_hollysys_device = True
            elif any(model_upper.startswith(prefix.upper()) for prefix in self.HOLLYSYS_PREFIXES):
                 is_hollysys_device = True

            if is_hollysys_device:
                # 检查是否为背板 (如LK117), LE系列可能没有类似的可计数背板
                if "LK117" in model_upper: # 当前只显式处理LK117作为机架计数依据
                    device['model'] = 'LK117' # 标准化
                    quantity = device.get('quantity', device.get('_widget_1635777485580', '1'))
                    if not quantity or not str(quantity).isdigit(): device['quantity'] = '1'
                    rack_devices.append(device)
                    logger.info(f"找到LK117背板: {model_upper}, 数量: {device['quantity']}")
                else:
                    hollysys_devices.append(device)
        
        if rack_devices:
            hollysys_devices.extend(rack_devices)
            logger.info(f"共找到 {len(rack_devices)} 条LK117背板记录.")

        logger.info(f"过滤后得到 {len(hollysys_devices)} 个和利时设备 (含背板). 原始设备数: {len(devices)}")
        return hollysys_devices
    
    def get_filtered_modules(self, module_type: str = '全部') -> List[Dict[str, Any]]:
        """
        获取过滤后的模块列表
        
        Args:
            module_type: 模块类型，默认为'全部'
            
        Returns:
            List[Dict[str, Any]]: 过滤后的模块列表
        """
        if not self.modules_data:
            logger.warning("没有可用的模块数据")
            return []
        
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
            # 如果没有设备数据，直接返回空列表
            if not self.hollysys_filtered_devices:
                logger.info("没有可用的设备数据，返回空列表")
                return [], False
            
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
        
        rack_ids_with_config = set(k[0] for k in config_dict.keys())
        if not rack_ids_with_config and self.system_type == "LE_CPU":
             logger.warning("LE_CPU系统配置为空，但槽位1必须配置LE5118 CPU。")
             print("错误: LE5118 CPU必须配置在槽位1。")
             return False
        elif not rack_ids_with_config and self.system_type == "LK":
             logger.info("LK系统配置为空，跳过槽位1模块检查。")
        else: 
            for r_id in rack_ids_with_config:
                slot1_module_model = config_dict.get((r_id, 1))
                if not slot1_module_model:
                    error_msg_detail = "LE5118 CPU" if self.system_type == "LE_CPU" else "DP模块"
                    logger.warning(f"机架 {r_id} 槽位1未配置{error_msg_detail}。")
                    print(f"错误: 机架 {r_id} 槽位1必须配置{error_msg_detail}。")
                    return False
                slot1_module_info = self.get_module_by_model(slot1_module_model)
                if not slot1_module_info:
                    logger.warning(f"机架 {r_id} 槽位1配置的模块 {slot1_module_model} 未知。")
                    print(f"错误: 机架 {r_id} 槽位1配置的模块 {slot1_module_model} 信息无法获取。")
                    return False
                slot1_type = slot1_module_info.get('type')
                if self.system_type == "LE_CPU":
                    if slot1_type != 'CPU' or slot1_module_model.upper() != 'LE5118':
                        logger.warning(f"机架 {r_id} (LE系统) 槽位1配置错误，应为LE5118 CPU，实际为 {slot1_module_model} ({slot1_type})。")
                        print(f"错误: 机架 {r_id} (LE系统) 槽位1必须配置LE5118 CPU。")
                        return False
                elif self.system_type == "LK":
                    if slot1_type != 'DP':
                        logger.warning(f"机架 {r_id} (LK系统) 槽位1配置错误，应为DP模块，实际为 {slot1_module_model} ({slot1_type})。")
                        print(f"错误: 机架 {r_id} (LK系统) 槽位1必须配置DP模块。")
                        return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n-------- PLC模块配置 ({timestamp}) --------")
        print(f"共配置 {len(config_dict)} 个PLC模块，分布在 {len(rack_ids_with_config)} 个机架")

        summary = {"AI":0, "AO":0, "DI":0, "DO":0, "DP":0, "COM":0, "CPU_count":0, "未录入_IO":0}

        for r_id in sorted(list(rack_ids_with_config)):
            print(f"\n机架 {r_id} 配置 (系统类型: {self.system_type}):")
            rack_mods = sorted([(s,m) for (r,s),m in config_dict.items() if r == r_id], key=lambda x: x[0])
            for s_id, model_name in rack_mods:
                m_info = self.get_module_by_model(model_name)
                if m_info:
                    m_type, m_ch, m_desc = m_info.get("type","未知"), m_info.get("channels",0), m_info.get("description","")
                    print(f"  槽位 {s_id}: {model_name} ({m_type}, {m_ch}通道) - {m_desc}")
                    
                    is_io_counted_for_this_module = False
                    # 检查模块是否为CPU且有sub_channels (例如LE5118的自带IO)
                    if m_type == "CPU" and "sub_channels" in m_info:
                        summary["CPU_count"] += 1
                        for sub_t, sub_c in m_info["sub_channels"].items():
                            if sub_t in summary: 
                                summary[sub_t] += sub_c
                                is_io_counted_for_this_module = True
                            # else: # sub_t (like 'DI', 'DO' from CPU) should always be in summary
                            #     summary["未录入_IO"] += sub_c 
                    # 处理其他混合IO模块 (AI/AO, DI/DO)
                    elif m_type in ["DI/DO", "AI/AO"] and "sub_channels" in m_info:
                        for sub_t, sub_c in m_info["sub_channels"].items():
                            if sub_t in summary: 
                                summary[sub_t] += sub_c
                                is_io_counted_for_this_module = True
                    # 处理标准单类型IO模块
                    elif m_type in summary and m_type not in ['DP', 'CP', 'COM', 'CPU', 'RACK']:
                        summary[m_type] += m_ch
                        is_io_counted_for_this_module = True
                    
                    # 处理其他非明确IO、非通信/DP/CPU/RACK的模块的通道数
                    if not is_io_counted_for_this_module and m_type not in ['DP', 'CP', 'COM', 'CPU', 'RACK', '未录入']:
                        summary["未录入_IO"] += m_ch
                    elif m_type == "CPU" and "sub_channels" not in m_info: # 无自带IO的CPU（如果有这种）
                        summary["CPU_count"] += 1
                else: 
                    print(f"  槽位 {s_id}: {model_name} (未知类型)")
                    summary["未录入_IO"] += self.CHANNEL_DEFAULTS.get('未录入', 16)

        print("\n通道数统计:")
        total_io = 0
        main_io_types = ['AI', 'AO', 'DI', 'DO']
        for ch_t in main_io_types: 
            count = summary.get(ch_t,0) 
            if count > 0: print(f"{ch_t} 通道数: {count}"); total_io+=count
        if summary["未录入_IO"] > 0: print(f"未录入类型IO通道数: {summary['未录入_IO']}"); total_io += summary["未录入_IO"]
        print(f"总IO通道数: {total_io}")
        if summary["CPU_count"] > 0: print(f"CPU模块数量: {summary['CPU_count']}")

        self.current_configuration = config_dict
        all_addrs = self.generate_channel_addresses(config_dict, True)
        io_ch_addrs = [a for a in all_addrs if a.get('is_io_channel', False)]
        non_io_addrs = [a for a in all_addrs if not a.get('is_io_channel', False)]
        if hasattr(self, 'io_channel_count') and total_io != self.io_channel_count:
            logger.warning(f"统计通道数({total_io})与生成地址IO数({self.io_channel_count})不一致!")
        print("\n-------- 通道位号列表 --------")
        print("序号\t模块名称\t模块类型\t通道位号\t类型")
        for i,addr in enumerate(io_ch_addrs,1): print(f"{i}\t{addr['model']}\t{addr['type']}\t{addr['address']}\tIO通道")
        if non_io_addrs: 
            print("\n-------- 通信模块列表 (不计入IO通道) --------")
            for idx, addr_info in enumerate(non_io_addrs, 1): print(f"{idx}\t{addr_info['model']}\t{addr_info['type']}\t{addr_info['address']}\t{addr_info.get('type','模块')}")
        print(f"\n总IO通道数: {len(io_ch_addrs)}, 非IO通道模块: {len(non_io_addrs)}")
        print("注意: 配置数据已记录，实际保存功能尚未实现...")
        print("--------------------------------------\n")
        return True

    def generate_channel_addresses(self, config: Dict[tuple, str], include_non_io: bool = True) -> List[Dict[str, Any]]:
        channel_addresses = []
        io_channel_count = 0
        if not config: self.channel_addresses = []; self.io_channel_count = 0; return []

        sorted_config = sorted(config.items(), key=lambda x: (x[0][0], x[0][1]))
        
        for (rack_id, slot_id), model in sorted_config:
            module_info = self.get_module_by_model(model)
            if not module_info: continue
                
            module_type = module_info.get('type', '未知')
            channels_count = module_info.get('channels', 0) # 这是总通道数
            
            is_non_io_module_type = module_type in ['DP', 'CP', 'COM', 'RACK']
            # 对于CPU，如果它有sub_channels，则它包含IO；如果没有，则它本身不产生IO地址（除非特殊规则）
            has_io_sub_channels = "sub_channels" in module_info and any(st in ['AI','AO','DI','DO'] for st in module_info["sub_channels"].keys())
            
            # 如果是纯粹的非IO模块类型 (DP, COM, RACK) 且没有IO子通道
            # 或者模块类型是CPU但没有IO子通道，且总通道数为0
            if (is_non_io_module_type and not has_io_sub_channels) or \
               (module_type == 'CPU' and not has_io_sub_channels and channels_count == 0):
                if include_non_io: 
                    channel_addresses.append({'rack_id': rack_id, 'slot_id': slot_id, 'model': model, 'type': module_type, 'channel': 0, 'address': f"{rack_id}_{slot_id}_{module_type}_0", 'is_io_channel': False})
                continue 
            
            # 处理带sub_channels的模块 (包括CPU的自带IO, DI/DO, AI/AO)
            if "sub_channels" in module_info:
                for sub_type, sub_ch_count in module_info["sub_channels"].items():
                    if sub_type in ['AI', 'AO', 'DI', 'DO']: # 只为IO子类型生成地址
                        for i in range(sub_ch_count):
                            # 地址格式中，对于CPU自带IO，使用 sub_type (DI/DO)
                            # 对于扩展板上的混合模块，也使用 sub_type
                            addr = f"{rack_id}_{slot_id}_{sub_type}_{i}"
                            channel_addresses.append({'rack_id': rack_id, 'slot_id': slot_id, 'model': model, 'type': sub_type, 'channel': i, 'address': addr, 'is_io_channel': True})
                            io_channel_count +=1
                    # else: #如果sub_channels里有非IO类型，比如COM, DP等，这里可以特殊处理或忽略
                    #    pass 
            # 处理没有sub_channels但有总通道数的标准IO模块 (AI, AO, DI, DO)
            elif module_type in ['AI', 'AO', 'DI', 'DO'] and channels_count > 0:
                for channel_idx in range(channels_count):
                    addr_module_type = module_type 
                    channel_address = f"{rack_id}_{slot_id}_{addr_module_type}_{channel_idx}"
                    channel_addresses.append({'rack_id': rack_id, 'slot_id': slot_id, 'model': model, 'type': addr_module_type, 'channel': channel_idx, 'address': channel_address, 'is_io_channel': True})
                    io_channel_count += 1
            # 对于没有sub_channels的CPU模块且channels_count > 0的情况（如果存在这种CPU）
            # 或者其他未明确处理但被认为是IO的模块，如果需要，可以在这里添加逻辑
            # else: logger.debug(f"模块 {model} 类型 {module_type} 有 {channels_count} 通道但未生成IO地址")

        logger.info(f"生成了 {len(channel_addresses)} 个通道位号记录，其中实际IO通道 {io_channel_count} 个")
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