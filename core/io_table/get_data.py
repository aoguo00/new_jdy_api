"""IO表格数据获取模块"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

# 导入模块定义
from .plc_modules import get_module_info_by_model, get_modules_by_type, get_all_modules, PLC_SERIES, MODULE_TYPE_PREFIXES # 导入PLC_SERIES

logger = logging.getLogger(__name__)

class ModuleInfoProvider:
    """
    模块信息提供者。
    负责从 plc_modules.py 加载和提供预定义的PLC模块信息。
    处理所有预定义模块的缓存和按需检索。
    """
    def __init__(self):
        """构造函数，初始化时加载所有预定义模块。"""
        # 从 plc_modules.py 加载所有模块定义
        self.predefined_modules: List[Dict[str, Any]] = get_all_modules()
        logger.info(f"ModuleInfoProvider initialized with {len(self.predefined_modules)} predefined modules.")

    def get_all_predefined_modules(self) -> List[Dict[str, Any]]:
        """返回所有预定义模块的深拷贝列表，以防止外部直接修改缓存。"""
        return [module.copy() for module in self.predefined_modules]

    def get_predefined_module_by_model(self, model_str: str) -> Optional[Dict[str, Any]]:
        """
        根据精确的模块型号字符串从缓存的预定义模块列表中查找模块。

        Args:
            model_str (str): 要查找的模块型号。

        Returns:
            Optional[Dict[str, Any]]: 如果找到，返回模块信息的拷贝；否则返回None。
        """
        model_upper = model_str.upper()
        for module in self.predefined_modules:
            if module.get("model", "").upper() == model_upper:
                return module.copy()  # 返回副本以确保缓存安全
        return None

    def get_inferred_module_info(self, model_str: str) -> Optional[Dict[str, Any]]:
        """
        使用 plc_modules.get_module_info_by_model 中可能更复杂的推断逻辑获取模块信息。
        当精确的预定义匹配未找到，或者 plc_modules 函数执行的不仅仅是列表查找
        （例如，通过前缀进行类型推断）时，通常使用此方法。

        Args:
            model_str (str): 用于推断的模块型号字符串。

        Returns:
            Optional[Dict[str, Any]]: 推断得到的模块信息，可能为None。
        """
        # plc_get_module_info_by_model 理论上应返回新的字典或可安全修改的字典。
        # 如果它返回 plc_modules 内部字典的引用，这里可能需要深拷贝，
        # 但通常此信息用于只读。
        module_info = get_module_info_by_model(model_str)
        return module_info 

class DeviceDataProcessor:
    """
    设备数据处理器。
    负责处理原始设备数据，包括：
    1. 标准化：将来自不同数据源（如带有 _widget_* 前缀的字段）的原始设备数据转换为统一的内部格式。
    2. 过滤：例如，根据关键字（如品牌）筛选出特定制造商（如和利时）的设备。
    3. 信息补充/丰富化：结合预定义的模块信息，为设备数据补充更详细的属性，如确切的IO类型、通道数、描述等。
    4. IO类型和通道数推断：在信息不足时，尝试根据型号、名称等信息推断模块的IO类型和通道数量。
    """
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
    """IO类型关键字映射，用于从文本描述中推断IO类型。"""
    
    CHANNEL_DEFAULTS = {
        "CPU": 0, 'AI': 8, 'AO': 4, 'DI': 16, 'DO': 16, 'DI/DO': 16,
        'AI/AO': 6, 'DP': 0, 'COM': 0, '未录入': 16
    }
    """不同IO类型的默认通道数，用于信息不完整时的推断。"""

    def __init__(self, module_info_provider: ModuleInfoProvider, hollysys_prefixes: List[str]):
        """
        构造函数。

        Args:
            module_info_provider (ModuleInfoProvider): 模块信息提供者实例，用于获取预定义模块数据。
            hollysys_prefixes (List[str]): 和利时产品型号的已知前缀列表，用于品牌识别。
        """
        self.module_info_provider = module_info_provider
        self.hollysys_prefixes = hollysys_prefixes
        logger.info("DeviceDataProcessor initialized.")

    def process_raw_device_list(self, raw_devices_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        处理原始设备数据列表，将其从包含 _widget_* 字段的格式转换为标准化的内部格式。
        同时会初步推断每个设备的IO类型和通道数。

        Args:
            raw_devices_data (List[Dict[str, Any]]): 从外部（如UI或数据库）获取的原始设备数据列表。

        Returns:
            List[Dict[str, Any]]: 处理和标准化后的设备数据列表。
        """
        processed_data = []
        # 定义原始字段到标准字段的映射关系
        field_mapping = {
            '_widget_1635777115211': 'name', '_widget_1635777115248': 'brand',
            '_widget_1635777115287': 'model', '_widget_1641439264111': 'description',
            '_widget_1635777485580': 'quantity', '_widget_1654703913698': 'unit',
            '_widget_1641439463480': 'ext_params'
        }
        for i, device in enumerate(raw_devices_data):
            try:
                processed_device = {'id': device.get('id', i + 1), 'instance_index': device.get('instance_index', 1)}
                for widget_field, standard_field in field_mapping.items():
                    processed_device[standard_field] = device.get(widget_field, '').strip()
                    # 保留原始的widget字段（如果系统的其他部分需要它们），
                    # 但对于此处理器，标准字段是主要的。
                    # processed_device[widget_field] = device.get(widget_field, '').strip() 
                
                # 如果没有明确的'type'字段，则使用'name'字段作为默认类型
                if 'type' not in processed_device: processed_device['type'] = processed_device.get('name', '')
                # 如果'model'为空但'brand'存在，则尝试使用'brand'作为'model' (某些情况下的兼容处理)
                if not processed_device.get('model') and processed_device.get('brand'):
                    processed_device['model'] = processed_device['brand']
                
                # 推断IO类型和通道数
                processed_device['io_type'] = self._determine_io_type_internal(processed_device)
                processed_device['channels'] = self._determine_channels_internal(processed_device)
                processed_data.append(processed_device)
            except Exception as e:
                logger.warning(f"Error processing raw device data (device #{i+1}, model: {device.get('model', 'N/A')}): {e}", exc_info=True)
        return processed_data

    def _determine_io_type_internal(self, device: Dict[str, Any]) -> str:
        """
        内部辅助方法：根据设备信息推断其IO类型。
        推断顺序：
        1. 明确指定的 'io_type' 字段（如果有效）。
        2. 根据模块型号从预定义模块信息中获取类型。
        3. 基于品牌、型号、名称、描述等文本信息中的关键字进行匹配。
        4. 针对特定型号（如包含'1616'）的硬编码规则。
        
        Args:
            device (Dict[str, Any]): 单个设备的标准化数据。

        Returns:
            str: 推断出的IO类型字符串，如果无法推断则为 '未录入'。
        """
        # 优先使用明确设置且有效的 'io_type'
        explicit_io_type = device.get('io_type')
        if explicit_io_type and explicit_io_type in self.IO_TYPE_MAPPINGS:
            return explicit_io_type
        
        model_str = device.get('model', '').upper() # 使用标准化的 'model' 字段
        
        # 首先尝试从预定义模块信息中获取类型
        if model_str:
            module_definition = self.module_info_provider.get_inferred_module_info(model_str)
            if module_definition and module_definition.get('type', '未录入') != '未录入':
                inferred_type = module_definition['type']
                # 确保推断出的类型是我们已知的IO类型
                if inferred_type in self.IO_TYPE_MAPPINGS: 
                    return inferred_type

        # 如果预定义信息中没有，则回退到基于文本的推断
        brand = device.get('brand', '').upper()
        name = device.get('name', '').upper()
        device_type_field = device.get('type', name).upper() # 设备自身的 'type' 字段或名称
        description = device.get('description', '').upper()
        ext_params = device.get('ext_params', '').upper()
        # 组合所有相关文本内容进行关键字搜索
        all_text_content = f"{model_str} {brand} {name} {device_type_field} {description} {ext_params}"

        # 使用传入的前缀列表检查是否为和利时产品
        is_hollysys_by_prefix = any(model_str.startswith(prefix.upper()) for prefix in self.hollysys_prefixes)
        # 通过品牌或文本内容中的关键字判断是否为和利时产品
        is_hollysys_by_keyword = '和利时' in brand or 'HOLLYSYS' in brand or \
                               '和利时' in all_text_content or 'HOLLYSYS' in all_text_content
        
        if is_hollysys_by_prefix or is_hollysys_by_keyword:
            # 如果是和利时产品，尝试更具体的型号前缀匹配（来自 plc_modules.MODULE_TYPE_PREFIXES）
            for type_key, prefixes_list in MODULE_TYPE_PREFIXES.items():
                if any(model_str.startswith(p.upper()) for p in prefixes_list):
                    if type_key in self.IO_TYPE_MAPPINGS: return type_key # 如果匹配到已知类型，则返回
        
        # 通用关键字匹配
        for io_type, keywords in self.IO_TYPE_MAPPINGS.items():
            if any(keyword.upper() in all_text_content for keyword in keywords):
                return io_type
        
        # 特定遗留规则：如型号中包含'1616'则认为是'DI/DO'
        if '1616' in model_str: return 'DI/DO' 
        return '未录入' # 如果以上都无法匹配，则返回'未录入'

    def _determine_channels_internal(self, device: Dict[str, Any]) -> int:
        """
        内部辅助方法：根据设备信息推断其通道数。
        推断顺序：
        1. 根据模块型号从预定义模块信息中获取通道数。
        2. 使用设备数据中明确指定的 'channels' 字段（如果有效）。
        3. 针对特定型号（如包含'1616'）的硬编码规则。
        4. 从模块型号字符串中通过正则表达式匹配数字（如 "16DI"中的16）。
        5. 根据已推断的IO类型使用预设的默认通道数。

        Args:
            device (Dict[str, Any]): 单个设备的标准化数据，应已包含 'io_type'。

        Returns:
            int: 推断出的通道数量。
        """
        model_str = device.get('model', '').upper()
        
        # 首先尝试从预定义模块信息中获取通道数
        if model_str:
            module_definition = self.module_info_provider.get_inferred_module_info(model_str)
            if module_definition and module_definition.get('channels') is not None:
                return module_definition['channels']
        
        # 如果设备数据中明确提供了 'channels' 字段，且可以转换为整数，则使用它
        if 'channels' in device:
            try: return int(device['channels'])
            except (ValueError, TypeError): pass # 如果转换失败，则忽略并继续后续逻辑
        
        io_type = device.get('io_type', '未录入') # 使用先前推断出的io_type

        # 特定遗留规则：如型号中包含'1616'则认为是32通道
        if '1616' in model_str: return 32 
        
        # 尝试从型号字符串中使用正则表达式提取通道数 (例如, "16DI", "8AO")
        channel_match_in_model = re.search(r'(\d+)[ADIO]{1,2}', model_str) # 简化版正则表达式
        if channel_match_in_model:
            try: return int(channel_match_in_model.group(1))
            except (ValueError, IndexError): pass # 如果提取或转换失败，则忽略
        
        # 如果以上方法都无法确定通道数，则根据IO类型返回默认值
        return self.CHANNEL_DEFAULTS.get(io_type, self.CHANNEL_DEFAULTS['未录入'])

    def filter_hollysys_devices(self, devices: List[Dict[str, Any]], known_hollysys_keywords: List[str]) -> List[Dict[str, Any]]:
        """
        从处理过的设备列表中筛选出和利时（Hollysys）的产品。
        同时会特别处理并标准化 LK117 机架设备。
        
        Args:
            devices (List[Dict[str, Any]]): 已标准化的设备列表。
            known_hollysys_keywords (List[str]): 用于识别和利时产品的关键字列表 (如品牌名)。
                                                这里也会结合初始化时传入的hollysys_prefixes。
            
        Returns:
            List[Dict[str, Any]]: 只包含和利时产品的设备列表，LK117机架会经过特殊处理。
        """
        hollysys_devices = []
        rack_devices_lk117 = [] # 单独存放LK117机架，以便后续统一处理

        for device in devices:
            model_upper = device.get('model', '').upper() # 标准化后的型号
            brand_upper = device.get('brand', '').upper()
            name_upper = device.get('name', '').upper()
            
            # 组合所有相关文本字段用于关键字搜索
            all_text_upper = f"{model_upper} {brand_upper} {name_upper} " \
                             f"{device.get('type', name_upper).upper()} " \
                             f"{device.get('description', '').upper()} " \
                             f"{device.get('ext_params', '').upper()}"

            # 通过关键字或型号前缀判断是否为和利时产品
            is_hollysys_by_keyword = any(keyword.upper() in all_text_upper for keyword in known_hollysys_keywords)
            is_hollysys_by_prefix = any(model_upper.startswith(prefix.upper()) for prefix in self.hollysys_prefixes)

            if is_hollysys_by_keyword or is_hollysys_by_prefix:
                # 如果是和利时产品，再检查是否为LK117机架
                if "LK117" == model_upper: 
                    device['model'] = 'LK117' # 标准化型号名称
                    quantity_str = device.get('quantity', '1')
                    # 确保数量为有效正整数，否则默认为1
                    try:
                        quantity_val = int(quantity_str)
                        if quantity_val < 1: quantity_val = 1
                    except (ValueError, TypeError):
                        quantity_val = 1
                    device['quantity'] = str(quantity_val) # 存回字符串形式，或统一为整数
                    rack_devices_lk117.append(device)
                else:
                    # 其他和利时模块直接添加
                    hollysys_devices.append(device)
        
        # 如果找到了LK117机架，将它们添加到结果列表的末尾（或开头，根据需求）
        if rack_devices_lk117:
            hollysys_devices.extend(rack_devices_lk117) 
            logger.info(f"Identified {len(rack_devices_lk117)} LK117 rack device(s) within Hollysys products.")
        
        logger.info(f"Filtered to {len(hollysys_devices)} Hollysys devices (including racks) from {len(devices)} processed devices.")
        return hollysys_devices

    def enrich_device_data(self, device_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用预定义的模块详细信息来丰富（补充）设备数据列表。
        对于列表中的每个设备，如果能通过其型号找到对应的预定义模块信息，
        则会用预定义信息中的类型、IO类型、通道数、描述以及其他关键结构字段
        （如 sub_channels, power_supply, is_master, slot_required）来更新设备数据。
        
        Args:
            device_data_list (List[Dict[str, Any]]): 经过初步处理和筛选的设备数据列表。
            
        Returns:
            List[Dict[str, Any]]: 信息更丰富的设备数据列表。
        """
        enriched_list = []
        for device in device_data_list:
            enriched_device = device.copy() # 对副本进行操作，不修改原始传入列表中的字典
            model_str = enriched_device.get('model', '')
            
            if model_str:
                # 优先使用精确匹配的预定义模块作为信息来源进行丰富
                module_definition = self.module_info_provider.get_predefined_module_by_model(model_str)
                if not module_definition: # 如果精确匹配未找到，尝试使用推断逻辑获取
                    module_definition = self.module_info_provider.get_inferred_module_info(model_str)

                if module_definition:
                    # 定义需要从预定义模块更新到设备对象中的字段
                    update_fields = {
                        'type': module_definition.get('type'),
                        # 假设预定义模块的'type'字段就是其IO类型，用于统一
                        'io_type': module_definition.get('type'), 
                        'channels': module_definition.get('channels'),
                        # 使用'predefined_description'作为键，以避免覆盖设备本身可能已有的、更具体的描述
                        'predefined_description': module_definition.get('description') 
                    }
                    # 复制其他重要的结构性字段（如果预定义模块中存在这些字段）
                    for key in ['sub_channels', 'power_supply', 'is_master', 'slot_required']:
                        if key in module_definition:
                            update_fields[key] = module_definition[key]
                    
                    # 应用更新
                    enriched_device.update(update_fields)
                    
                    # 如果设备原始描述为空，并且预定义模块有描述，则使用预定义的描述
                    if not enriched_device.get('description') and update_fields.get('predefined_description'):
                        enriched_device['description'] = update_fields['predefined_description']
                    
                    logger.debug(f"Device '{model_str}' enriched. Final type: {enriched_device.get('type')}, "
                                 f"Channels: {enriched_device.get('channels')}, SubChannels: {enriched_device.get('sub_channels')}")
            enriched_list.append(enriched_device)
        return enriched_list

class SystemSetupManager:
    """
    系统设置管理器。
    负责管理PLC的整体系统配置，主要包括：
    1. 系统类型判断：根据是否存在特定CPU模块（如LE5118）来判断系统是 LK 系列还是 LE_CPU 系列。
    2. 机架数量计算：
        - 对于 LE_CPU 系统，通常默认为1个主单元机架。
        - 对于 LK 系统，根据设备数据中LK117背板的数量来计算实际的机架数量，确保至少有1个机架。
    3. 机架数据初始化：为每个计算出的机架创建基础数据结构，包括机架ID、名称、总槽位数、可用槽位数、起始槽位（用户可配置的起始槽位）等。
       可用槽位数和起始槽位会根据系统类型（LK vs LE_CPU）有所不同，例如LK系统槽位1固定给DP，LE系统槽位1通常给CPU。
    """
    DEFAULT_RACK_SLOTS = 11
    """每个标准机架的默认总槽位数。"""

    def __init__(self, default_rack_slots: Optional[int] = None):
        """
        构造函数。
        
        Args:
            default_rack_slots (Optional[int]): 可选参数，用于指定每个机架的默认槽位数。
                                              如果未提供，则使用类定义的 DEFAULT_RACK_SLOTS (11)。
        """
        self.default_slots = default_rack_slots if default_rack_slots is not None else self.DEFAULT_RACK_SLOTS
        self.system_type: str = "LK" # 系统类型，默认为 "LK"
        self.rack_count: int = 0      # PLC系统中的机架数量
        self.racks_data: List[Dict[str, Any]] = [] # 存储每个机架详细信息的列表
        logger.info(f"SystemSetupManager initialized with default_slots: {self.default_slots}.")

    def calculate_system_setup(self, processed_enriched_devices: List[Dict[str, Any]]):
        """
        根据处理和丰富化后的设备列表，计算并确定PLC的系统类型和机架配置。

        Args:
            processed_enriched_devices (List[Dict[str, Any]]): 经过DeviceDataProcessor处理后的设备数据列表。
                                                               此列表应用于已包含准确的模块型号和类型信息。
        """
        self.system_type = "LK" # 每次重新计算前，重置系统类型为默认值 "LK"
        
        # 检查是否存在 LE5118 CPU模块，以确定系统是否为 "LE_CPU" 类型
        le5118_cpus = [m for m in processed_enriched_devices if m.get('model', '').upper() == 'LE5118' and m.get('type') == 'CPU']
        
        if le5118_cpus:
            self.system_type = "LE_CPU"
            self.rack_count = 1 # LE5118 CPU 系统通常只有一个主单元（即一个机架）
            logger.info(f"LE5118 CPU detected. System type set to '{self.system_type}'. Rack count set to {self.rack_count}.")
        else:
            # 对于 LK 或其他非LE_CPU系统，根据 LK117 背板模块的数量来计算实际的机架数量
            lk117_racks = [m for m in processed_enriched_devices if m.get('model', '').upper() == 'LK117']
            calculated_rack_count = 0
            if lk117_racks:
                for rack_module in lk117_racks:
                    try:
                        # LK117模块本身可能在数据中有一个'quantity'字段表示其数量
                        quantity = int(rack_module.get('quantity', '1'))
                        calculated_rack_count += quantity if quantity > 0 else 1 # 确保至少加1
                    except (ValueError, TypeError):
                        calculated_rack_count += 1 # 如果数量无效，则默认为1个
            # 系统至少有1个机架，即使没有明确的LK117模块（例如，如果所有模块都直接列出而没有机架信息）
            self.rack_count = max(1, calculated_rack_count) 
            logger.info(f"System type is '{self.system_type}'. Rack count calculated from LK117s or default: {self.rack_count}.")

        # 基于计算出的机架数量和系统类型，初始化 self.racks_data 列表
        self.racks_data = []
        for i in range(self.rack_count):
            # 判断是否为 LE_CPU 系统的主机架（第一个机架）
            is_le_system_main_rack = (self.system_type == "LE_CPU" and i == 0) 
            
            # 为每个机架创建数据字典
            rack_data = {
                'rack_id': i + 1, # 机架ID，从1开始
                'rack_name': f"机架{i + 1}",
                'total_slots': self.default_slots, # 该机架的总槽位数
                # 可用槽位数和用户起始槽位根据系统类型调整
                # LE_CPU 主机架通常所有槽位都可用（槽位1由用户配置CPU）
                # LK 系统机架槽位1固定给DP模块，所以用户可配置槽位从2开始，可用槽位数相应减少
                'available_slots': self.default_slots if is_le_system_main_rack else self.default_slots -1 , # TODO: LE CPU的available slots也应该是 default_slots? Start slot是1没错
                'start_slot': 1 if is_le_system_main_rack else 2, 
                'modules': [], # 用于存储后续配置到此机架的模块列表（此阶段为空）
                'system_type': self.system_type # 记录该机架所属的系统类型
            }
            self.racks_data.append(rack_data)
        logger.info(f"System setup finalized: {self.rack_count} racks configured for system type '{self.system_type}'.")

    def get_system_type(self) -> str:
        """返回当前PLC系统的类型 (例如 "LK" 或 "LE_CPU")。"""
        return self.system_type

    def get_rack_info_dict(self) -> Dict[str, Any]:
        """
        返回一个包含当前机架配置摘要信息的字典。
        这些信息通常用于UI或其他需要了解整体机架布局的服务。

        Returns:
            Dict[str, Any]: 包含机架数量、每机架槽位数、用户起始槽位、
                            详细机架数据列表以及系统类型等信息的字典。
        """
        return {
            'rack_count': self.rack_count,
            'slots_per_rack': self.default_slots, # UI通常需要知道每个机架有多少槽
            'user_start_slot': 1 if self.system_type == "LE_CPU" else 2, # 用户在UI上看到的第一个可配置槽位号
            'racks': [r.copy() for r in self.racks_data], # 返回机架数据的副本列表
            'system_type': self.system_type
        }

class PLCConfigurationHandler:
    """
    PLC配置处理器。
    负责PLC模块配置的核心逻辑，包括：
    1. 模块放置验证：根据系统类型（LK/LE_CPU）、机架ID、槽位ID和模块型号，验证模块是否可以被放置在指定位置。
       例如，LK系统的槽位1只能放DP模块，LE_CPU系统的槽位1必须是LE5118 CPU等。
    2. 配置保存（模拟）：接收来自UI的配置数据（通常是 {(rack_id, slot_id): model_name} 的字典），
       进行最终验证（如确保LE_CPU系统槽位1已配置CPU），然后打印配置摘要和统计信息到控制台。
       （注意：这里的"保存"是模拟的，实际的持久化存储可能由其他服务完成）。
    3. 通道地址生成：根据有效的模块配置，为每个IO通道生成唯一的地址字符串，并统计总的IO通道数。
       非IO模块（如DP, COM）也会被记录，但不计入IO统计，并可能生成不同的地址格式。

    依赖于 ModuleInfoProvider 来获取模块的详细定义（如类型、通道数、子通道信息等）。
    """
    def __init__(self, module_info_provider: ModuleInfoProvider):
        """
        构造函数。

        Args:
            module_info_provider (ModuleInfoProvider): 模块信息提供者实例，用于在配置处理过程中查询模块属性。
        """
        self.module_info_provider = module_info_provider
        logger.info("PLCConfigurationHandler initialized.")

    def _get_module_details_for_config(self, model_str: str, processed_devices_context: List[Dict[str,Any]]) -> Optional[Dict[str, Any]]:
        """
        内部辅助方法：获取用于配置目的的模块详细信息。
        此方法特别重要，因为它决定了在验证和地址生成时模块属性的来源。
        它按以下优先级顺序查找模块信息：
        1. 当前已处理和丰富化的设备列表 (processed_devices_context)：
           这可以确保使用到运行时特定的信息（如果设备列表已包含这些信息，例如从用户输入或特定项目数据中获取的唯一ID或特殊参数）。
           特别是，这能保证 `sub_channels` 等在 `DeviceDataProcessor.enrich_device_data` 中被正确复制的字段可用。
        2. 预定义模块列表 (通过 self.module_info_provider.get_predefined_module_by_model 精确匹配)。
        3. plc_modules.py 中的推断逻辑 (通过 self.module_info_provider.get_inferred_module_info)。

        Args:
            model_str (str): 要查找的模块型号。
            processed_devices_context (List[Dict[str,Any]]): 当前IODataLoader中已处理和丰富化的设备列表。
                                                            这提供了获取最完整和上下文相关模块信息的途径。

        Returns:
            Optional[Dict[str, Any]]: 模块信息的字典拷贝（如果找到），否则为None。
        """
        model_upper = model_str.upper()
        # 优先级1: 在当前已处理和丰富化的设备上下文中查找
        # 这是最理想的来源，因为它应包含所有通过 enrich_device_data 添加的字段（如 sub_channels）
        if processed_devices_context:
            for device_instance in processed_devices_context:
                if device_instance.get('model', '').upper() == model_upper:
                    # device_instance 应该已经包含了如 'type', 'channels', 'sub_channels' 等所有必要字段
                    return device_instance.copy() # 返回副本以防意外修改
        
        # 优先级2: 从预定义模块列表中精确查找 (通过ModuleInfoProvider)
        module_def = self.module_info_provider.get_predefined_module_by_model(model_str)
        if module_def:
            return module_def # ModuleInfoProvider 应已返回副本

        # 优先级3: 从 plc_modules 的推断逻辑中获取 (通过ModuleInfoProvider)
        module_def_inferred = self.module_info_provider.get_inferred_module_info(model_str)
        if module_def_inferred:
             return module_def_inferred # ModuleInfoProvider 的这个方法也应返回安全数据

        logger.warning(f"Could not retrieve details for module model '{model_str}' during configuration handling.")
        return None


    def validate_module_placement(self, system_type: str, rack_id: int, slot_id: int, module_model: str, processed_devices_context: List[Dict[str,Any]]) -> Dict[str, Any]:
        """
        验证一个模块是否可以被放置在指定的机架和槽位上，基于当前的系统类型。
        
        Args:
            system_type (str): 当前的PLC系统类型 ("LK" 或 "LE_CPU")。
            rack_id (int): 目标机架的ID。
            slot_id (int): 目标槽位的ID。
            module_model (str): 尝试放置的模块的型号。
            processed_devices_context (List[Dict[str,Any]]): 已处理的设备列表，用于获取模块详细信息。
            
        Returns:
            Dict[str, Any]: 包含验证结果的字典，格式如：
                            {'valid': True/False, 'error': '错误信息' (如果valid为False)， 'message': '成功信息' (如果valid为True)}
        """
        module_info = self._get_module_details_for_config(module_model, processed_devices_context)
        if not module_info:
             return {'valid': False, 'error': f"模块 {module_model} 信息未知，无法验证放置。"}
        
        module_type = module_info.get('type', '未录入')

        # LE_CPU 系统规则
        if system_type == "LE_CPU":
            if slot_id == 1: # LE_CPU 系统的槽位1
                # 必须是类型为 'CPU' 且型号为 'LE5118' 的模块
                if not (module_type == 'CPU' and module_model.upper() == 'LE5118'):
                    return {'valid': False, 'error': f"LE系统槽位1只能放置LE5118 CPU模块,尝试放置{module_model}({module_type})"}
            elif module_type == 'CPU': # 如果是CPU模块 (如LE5118)，但尝试放置在非槽位1的位置
                return {'valid': False, 'error': f"CPU模块 {module_model} 只能放置在LE系统的槽位1"}
        
        # LK 系统规则
        elif system_type == "LK": 
            if module_type == 'DP': # 如果是DP模块
                if slot_id != 1: # DP模块必须放置在槽位1
                    return {'valid': False, 'error': f"DP模块 {module_model} 只能放置在LK系统槽位1"}
            elif slot_id == 1: # LK系统的槽位1，但尝试放置的不是DP模块
                return {'valid': False, 'error': f"LK系统槽位1只能放置DP模块,不能放置{module_model}({module_type})"}
        
        # 通用规则：RACK类型的模块（如LK117背板）不能作为可配置模块直接放置到槽位中
        # (这个检查可能更适合在模块选择阶段进行，但在此处作为双重保险)
        if module_type == 'RACK':
            return {'valid': False, 'error': "背板模块 (如LK117) 不能直接添加到配置槽位中"}
            
        return {'valid': True, 'message': f"模块 {module_model} 可以放置在机架 {rack_id} 槽位 {slot_id}"}

    def save_plc_configuration(self, config_dict: Dict[tuple, str], system_type: str, processed_devices_context: List[Dict[str,Any]]) -> Tuple[bool, str]:
        """
        验证并"保存"（实际是打印摘要和统计信息）PLC的配置。

        Args:
            config_dict (Dict[tuple, str]): PLC配置数据，格式为 {(rack_id, slot_id): model_name}。
            system_type (str): 当前PLC系统类型 ("LK" 或 "LE_CPU")。
            processed_devices_context (List[Dict[str,Any]]): 已处理的设备列表，用于获取模块详细信息。

        Returns:
            Tuple[bool, str]: 一个元组，第一个元素表示操作是否成功 (True/False)，
                              第二个元素是相关的消息字符串。
        """
        logger.info(f"Attempting to save PLC configuration: {len(config_dict)} items, System Type: {system_type}")
        
        # --- 配置验证 --- 
        rack_ids_in_config = set(k[0] for k in config_dict.keys()) # 获取配置中涉及的所有机架ID

        # 处理空配置的情况
        if not config_dict: 
            if system_type == "LE_CPU": # LE_CPU 系统不允许完全为空，至少槽位1要有CPU
                msg = "错误: LE_CPU 系统配置为空，槽位1必须配置LE5118 CPU。"
                logger.warning(msg)
                return False, msg
            else: # LK 系统可以接受空配置（虽然通常至少有DP模块）
                logger.info("LK系统配置为空，视为有效。")
                # 继续执行，后续会打印空的配置摘要
        
        # 验证每个已配置机架的槽位1是否符合规则
        for r_id in rack_ids_in_config:
            slot1_model = config_dict.get((r_id, 1)) # 获取该机架槽位1配置的模块型号
            if not slot1_model: # 如果槽位1没有配置模块
                err_detail = "LE5118 CPU" if system_type == "LE_CPU" else "DP模块"
                msg = f"错误: 机架 {r_id} 槽位1必须配置{err_detail}。"
                logger.warning(msg)
                return False, msg
            
            # 获取槽位1模块的详细信息
            slot1_info = self._get_module_details_for_config(slot1_model, processed_devices_context)
            if not slot1_info:
                msg = f"错误: 机架 {r_id} 槽位1配置的模块 {slot1_model} 信息无法获取。"
                logger.warning(msg)
                return False, msg

            slot1_type = slot1_info.get('type')
            # 根据系统类型检查槽位1的模块类型是否正确
            if system_type == "LE_CPU":
                if not (slot1_type == 'CPU' and slot1_model.upper() == 'LE5118'):
                    msg = f"错误: 机架 {r_id} (LE系统) 槽位1必须配置LE5118 CPU, 当前为 {slot1_model}({slot1_type})。"
                    logger.warning(msg)
                    return False, msg
            elif system_type == "LK":
                if slot1_type != 'DP':
                    msg = f"错误: 机架 {r_id} (LK系统) 槽位1必须配置DP模块, 当前为 {slot1_model}({slot1_type})。"
                    logger.warning(msg)
                    return False, msg
        
        # --- 打印配置摘要和统计信息 --- 
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n-------- PLC模块配置 ({timestamp}) --------")
        print(f"共配置 {len(config_dict)} 个PLC模块，分布在 {len(rack_ids_in_config)} 个机架")
        
        # 初始化IO通道统计字典
        summary = {"AI":0, "AO":0, "DI":0, "DO":0, "DP":0, "COM":0, "CPU_count":0, "未录入_IO":0}
        
        # 按机架ID排序遍历已配置的机架
        for r_id in sorted(list(rack_ids_in_config)):
            print(f"\n机架 {r_id} 配置 (系统类型: {system_type}):")
            # 获取该机架的所有模块，并按槽位ID排序
            rack_mods = sorted([(s,m) for (r,s),m in config_dict.items() if r == r_id], key=lambda x: x[0])
            for s_id, model_name in rack_mods:
                m_info = self._get_module_details_for_config(model_name, processed_devices_context)
                if m_info:
                    m_type = m_info.get("type","未知")
                    m_ch_total = m_info.get("channels",0) # 模块自身的总通道数
                    m_desc = m_info.get("description","")
                    print(f"  槽位 {s_id}: {model_name} ({m_type}, {m_ch_total}通道) - {m_desc}")
                    
                    io_counted_for_module = False # 标记该模块的IO是否已被统计
                    # 处理带子通道的CPU模块 (如LE5118)
                    if m_type == "CPU" and "sub_channels" in m_info: 
                        summary["CPU_count"] += 1
                        for sub_t, sub_c in m_info["sub_channels"].items():
                            if sub_t in summary: summary[sub_t] += sub_c
                        io_counted_for_module = True 
                    # 处理带子通道的混合IO模块 (DI/DO, AI/AO)
                    elif m_type in ["DI/DO", "AI/AO"] and "sub_channels" in m_info: 
                        for sub_t, sub_c in m_info["sub_channels"].items():
                            if sub_t in summary: summary[sub_t] += sub_c
                        io_counted_for_module = True
                    # 处理标准的单一类型IO模块 (且不是DP, COM, CPU, RACK等非IO或特殊模块)
                    elif m_type in summary and m_type not in ['DP', 'COM', 'CPU', 'RACK']: 
                        summary[m_type] += m_ch_total
                        io_counted_for_module = True
                    
                    # 如果模块IO未被以上逻辑统计，且模块类型不是已知非IO类型，且通道数大于0，则计入"未录入_IO"
                    if not io_counted_for_module and m_type not in ['DP', 'COM', 'CPU', 'RACK', '未录入'] and m_ch_total > 0:
                        summary["未录入_IO"] += m_ch_total 
                    # 处理没有子通道的CPU模块（仅计数CPU，不计IO）
                    elif m_type == "CPU" and "sub_channels" not in m_info : 
                         summary["CPU_count"] += 1
                else: 
                    # 如果模块信息无法获取
                    print(f"  槽位 {s_id}: {model_name} (未知类型)")
                    # 对完全未知的模块，也尝试增加一个默认的未录入IO通道数
                    summary["未录入_IO"] += DeviceDataProcessor.CHANNEL_DEFAULTS.get('未录入', 0) 
        
        print("\n通道数统计:")
        total_io_channels = sum(summary.get(t, 0) for t in ['AI', 'AO', 'DI', 'DO', '未录入_IO'])
        for ch_type in ['AI', 'AO', 'DI', 'DO']:
            if summary.get(ch_type, 0) > 0: print(f"{ch_type} 通道数: {summary[ch_type]}")
        if summary.get("未录入_IO", 0) > 0: print(f"未录入类型IO通道数: {summary['未录入_IO']}")
        print(f"总IO通道数: {total_io_channels}")
        if summary.get("CPU_count", 0) > 0: print(f"CPU模块数量: {summary['CPU_count']}")
        
        # 打印通道地址列表 (地址由 generate_channel_addresses_list 生成)
        # IODataLoader会在调用此方法成功后，再调用generate_channel_addresses_list来获取并存储地址列表
        generated_addresses, _ = self.generate_channel_addresses_list(config_dict, processed_devices_context, True)
        print_generated_channel_addresses_summary(generated_addresses, total_io_channels)
        
        return True, "配置已验证并模拟保存。"

    def generate_channel_addresses_list(self, config_dict: Dict[tuple, str], processed_devices_context: List[Dict[str,Any]], include_non_io: bool = True) -> Tuple[List[Dict[str, Any]], int]:
        """
        根据给定的PLC模块配置，生成详细的通道地址列表。
        
        Args:
            config_dict (Dict[tuple, str]): PLC配置数据，格式为 {(rack_id, slot_id): model_name}。
            processed_devices_context (List[Dict[str,Any]]): 已处理的设备列表，用于获取模块详细信息，
                                                            特别是 `sub_channels` 等关键信息。
            include_non_io (bool, optional): 是否在结果中包含非IO模块（如DP, COM）的地址记录。
                                             默认为 True。
            
        Returns:
            Tuple[List[Dict[str, Any]], int]: 一个元组，包含：
                - channel_addresses (List[Dict[str, Any]]): 通道地址列表。每个字典包含：
                    'rack_id', 'slot_id', 'model', 'type' (通道类型), 'channel' (通道索引),
                    'address' (生成的地址字符串), 'is_io_channel' (布尔值)。
                - actual_io_channel_count (int): 实际生成的IO通道总数。
        """
        channel_addresses: List[Dict[str, Any]] = [] # 初始化地址列表
        actual_io_channel_count = 0 # 初始化实际IO通道计数器
        if not config_dict: # 如果配置为空，直接返回空列表和0计数
            return [], 0

        # 按机架ID和槽位ID对配置项进行排序，以确保地址生成的顺序性
        sorted_config = sorted(config_dict.items(), key=lambda x: (x[0][0], x[0][1]))
        
        for (rack_id, slot_id), model_name in sorted_config:
            module_info = self._get_module_details_for_config(model_name, processed_devices_context)
            if not module_info: 
                logger.warning(f"Cannot generate addresses for unknown module {model_name} at {rack_id}_{slot_id}")
                continue # 跳过未知模块
            
            module_type = module_info.get('type', '未知')
            module_total_channels = module_info.get('channels', 0) # 模块本身的总通道数
            
            # 判断是否为纯粹的非IO类型模块 (DP, COM)
            is_purely_non_io_type = module_type in ['DP', 'COM'] 
            # 特殊处理CPU模块：如果CPU模块没有定义IO相关的sub_channels，则也视为非IO（仅用于占位和识别）
            is_cpu_without_io_subs = (module_type == 'CPU' and 
                                    not ("sub_channels" in module_info and 
                                         any(st in ['AI','AO','DI','DO'] for st in module_info.get("sub_channels", {}).keys())))

            # 如果是纯非IO模块或无IO子通道的CPU模块
            if is_purely_non_io_type or is_cpu_without_io_subs:
                if include_non_io: # 如果参数要求包含非IO模块的记录
                    channel_addresses.append({
                        'rack_id': rack_id, 'slot_id': slot_id, 'model': model_name, 
                        'type': module_type, 'channel': 0, # 非IO模块通常channel索引为0或无意义
                        'address': f"{rack_id}_{slot_id}_{module_type}_0", # 生成一个代表该模块的地址
                        'is_io_channel': False
                    })
                continue # 处理下一个配置项，不为此类模块生成具体的IO通道地址

            # 处理带有 sub_channels 的模块 (例如带IO的CPU, DI/DO混合模块, AI/AO混合模块)
            if "sub_channels" in module_info and isinstance(module_info["sub_channels"], dict):
                for sub_type, sub_ch_count in module_info["sub_channels"].items():
                    # 只为实际的IO子类型 (AI, AO, DI, DO) 生成地址
                    if sub_type in ['AI', 'AO', 'DI', 'DO']:
                        for i in range(sub_ch_count):
                            addr = f"{rack_id}_{slot_id}_{sub_type}_{i}"
                            channel_addresses.append({
                                'rack_id': rack_id, 'slot_id': slot_id, 'model': model_name, 
                                'type': sub_type, 'channel': i, 'address': addr, 'is_io_channel': True
                            })
                            actual_io_channel_count += 1
            # 处理没有 sub_channels 定义的标准单一类型IO模块 (AI, AO, DI, DO)
            elif module_type in ['AI', 'AO', 'DI', 'DO'] and module_total_channels > 0:
                for i in range(module_total_channels):
                    addr = f"{rack_id}_{slot_id}_{module_type}_{i}"
                    channel_addresses.append({
                        'rack_id': rack_id, 'slot_id': slot_id, 'model': model_name,
                        'type': module_type, 'channel': i, 'address': addr, 'is_io_channel': True
                    })
                    actual_io_channel_count += 1
            # 对于其他类型模块（例如，定义了channels > 0 但没有sub_channels，也不是标准IO类型的模块），
            # 当前逻辑不会为其生成具体的IO地址，除非它们被视为纯非IO模块在上一步处理。
            # 这确保了只有明确定义的IO点才会被计入和分配地址。

        logger.info(f"Generated {len(channel_addresses)} address records in total. Actual IO channels generated: {actual_io_channel_count}.")
        return channel_addresses, actual_io_channel_count

# --- Main IODataLoader Class (Refactored) ---

class IODataLoader:
    """
    IO数据加载和处理的总协调器。
    该类的主要职责是整合其他辅助类 (ModuleInfoProvider, DeviceDataProcessor, SystemSetupManager, PLCConfigurationHandler)
    的功能，对外提供一个统一的接口来处理与PLC IO表相关的各种操作。包括：

    1.  **设备数据设置与处理**: 
        - 接收原始设备列表数据 (通常来自UI或项目文件)。
        - 调用 `DeviceDataProcessor` 进行数据的标准化、和利时产品过滤、以及基于预定义模块信息的丰富化处理。
        - 调用 `SystemSetupManager` 根据处理后的数据重新计算系统配置（类型、机架）。
    2.  **配置信息获取**: 
        - 提供方法 (`get_rack_info`) 让外部（如UI）获取当前计算出的机架配置信息和系统类型。
    3.  **模块加载与查询**: 
        - 提供方法 (`load_available_modules`) 为UI的模块选择穿梭框加载可用的模块列表，会根据模块类型进行过滤，并排除已配置的模块。
        - 提供方法 (`get_module_by_model`) 根据模块型号字符串查询详细的模块信息，查询顺序依次是：当前处理的设备列表、预定义模块、推断逻辑。
    4.  **PLC配置操作**: 
        - 提供模块放置验证接口 (`validate_module_placement`)，供UI在用户尝试放置模块前调用。
        - 提供核心的配置保存接口 (`save_configuration`)，接收UI传递过来的模块配置数据，
          调用 `PLCConfigurationHandler` 进行最终的验证和模拟保存（打印统计和地址）。
          成功后会更新内部存储的当前配置和最后生成的地址列表。
    5.  **通道地址管理**: 
        - 在配置成功保存后，自动调用 `PLCConfigurationHandler` 生成通道地址，并存储结果。
        - 提供方法 (`get_channel_addresses`) 供外部获取最后一次成功生成的通道地址列表。

    通过将不同职责分离到专门的类中，`IODataLoader` 自身保持相对简洁，主要承担协调和流程控制的角色，
    提高了代码的可维护性和扩展性。
    """
    # 允许出现在穿梭框供用户选择的模块类型 (RACK类型已移除，因为它代表机架本身)
    ALLOWED_MODULE_TYPES = ["CPU", 'AI', 'AO', 'DI', 'DO', 'DI/DO', 'AI/AO', 'DP', 'COM'] 
    
    def __init__(self):
        """构造函数，初始化所有辅助类和内部状态变量。"""
        self.module_info_provider = ModuleInfoProvider()
        
        # 从 plc_modules.PLC_SERIES 动态生成和利时产品型号前缀列表
        # 这里假设 PLC_SERIES 已被正确导入并在类级别或实例级别可用
        self.HOLLYSYS_PREFIXES = [
            prefix.upper() for series_data in PLC_SERIES.values() 
            for prefix in series_data.get("prefixes", [])
        ]
        
        # 初始化设备数据处理器，传入模块信息提供者和和利时前缀
        self.device_processor = DeviceDataProcessor(
            module_info_provider=self.module_info_provider,
            hollysys_prefixes=self.HOLLYSYS_PREFIXES
        )
        # 初始化系统设置管理器，使用其内部定义的默认机架槽位数
        self.system_setup_manager = SystemSetupManager(default_rack_slots=SystemSetupManager.DEFAULT_RACK_SLOTS)
        # 初始化PLC配置处理器，传入模块信息提供者
        self.config_handler = PLCConfigurationHandler(module_info_provider=self.module_info_provider)

        # 存储原始的、未处理的设备数据列表
        self.original_devices_data: List[Dict[str, Any]] = []
        # 存储经过处理、筛选和丰富化后的和利时相关设备数据列表
        self.processed_enriched_devices: List[Dict[str, Any]] = [] 
        
        # 当前PLC的配置，格式为 {(rack_id, slot_id): model_name}
        self.current_plc_config: Dict[tuple, str] = {}
        # 最后一次成功生成的通道地址列表
        self.last_generated_addresses: List[Dict[str, Any]] = []
        # 最后一次成功生成的IO通道总数
        self.last_generated_io_count: int = 0

        # 特殊允许的模块列表：这些模块型号会绕过一些常规的类型过滤逻辑，确保它们在穿梭框中可见
        # 例如，所有COM, DI/DO, AI/AO类型的模块，以及特定的CPU型号（如LE5118）和老旧型号（如LK238）
        all_predefined = self.module_info_provider.get_all_predefined_modules()
        self.SPECIAL_ALLOWED_MODULES = list(set(
            [m["model"].upper() for m in all_predefined if m.get("type") in ["COM", "DI/DO", "AI/AO"]] +
            [m["model"].upper() for m in all_predefined if m.get("type") == "CPU" and m.get("model","").upper() == "LE5118"] + 
            ["LK238"] 
        ))
        logger.info(f"IODataLoader initialized. System type: {self.system_setup_manager.get_system_type()}. "
                    f"Found {len(self.HOLLYSYS_PREFIXES)} Hollysys prefixes. "
                    f"{len(self.SPECIAL_ALLOWED_MODULES)} special modules.")

    def set_devices_data(self, devices_data: List[Dict[str, Any]]) -> None:
        """
        设置新的设备数据列表，并触发整个处理流程：
        1. 保存原始数据。
        2. 调用DeviceDataProcessor进行标准化、过滤和丰富化。
        3. 调用SystemSetupManager根据处理后的数据重新计算系统配置（类型、机架）。
        4. 重置任何已存在的PLC配置，因为设备基础已改变。
        
        Args:
            devices_data (List[Dict[str, Any]]): 从外部传入的原始设备数据列表。
        """
        self.original_devices_data = devices_data or [] # 保证列表存在
        logger.info(f"Setting new device data: {len(self.original_devices_data)} raw items.")

        # 1. 标准化原始数据
        processed_list = self.device_processor.process_raw_device_list(self.original_devices_data)
        
        # 定义用于筛选和利时产品的关键字 (可以考虑作为常量或配置)
        known_hollysys_filter_keywords = ['和利时', 'HOLLYSYS'] 
        
        # 2. 筛选出和利时相关设备 (包括机架如LK117)
        hollysys_filtered_list = self.device_processor.filter_hollysys_devices(
            processed_list, 
            # 使用关键字和在初始化时从PLC_SERIES提取的前缀进行联合筛选
            known_hollysys_filter_keywords + self.HOLLYSYS_PREFIXES 
        )
        
        # 3. 丰富化筛选后的设备数据
        self.processed_enriched_devices = self.device_processor.enrich_device_data(hollysys_filtered_list)
        logger.info(f"Processed and enriched data for {len(self.processed_enriched_devices)} Hollysys devices.")
        
        # 4. 根据最新的设备数据重新计算系统设置（机架、系统类型）
        self.system_setup_manager.calculate_system_setup(self.processed_enriched_devices)
        logger.info(f"System setup updated. Current type: {self.system_setup_manager.get_system_type()}")
        
        # 当设备数据重置时，清除当前的PLC配置和已生成的地址信息
        self.current_plc_config = {}
        self.last_generated_addresses = []
        self.last_generated_io_count = 0

    def get_rack_info(self) -> Dict[str, Any]:
        """返回由SystemSetupManager计算和维护的当前机架及系统设置信息。"""
        return self.system_setup_manager.get_rack_info_dict()

    def validate_module_placement(self, rack_id: int, slot_id: int, module_model: str) -> Dict[str, Any]:
        """
        验证指定模块是否可以放置在当前系统配置下的特定机架和槽位。
        实际的验证逻辑委托给 PLCConfigurationHandler。
        
        Args:
            rack_id (int): 目标机架ID。
            slot_id (int): 目标槽位ID。
            module_model (str): 尝试放置的模块型号。
            
        Returns:
            Dict[str, Any]: 验证结果字典 (包含 'valid' 和 'error'/'message')。
        """
        system_type = self.system_setup_manager.get_system_type()
        # 验证时需要传入 processed_enriched_devices 作为上下文，以便_get_module_details_for_config能获取最准确的模块信息
        return self.config_handler.validate_module_placement(system_type, rack_id, slot_id, module_model, self.processed_enriched_devices)

    def load_available_modules(self, module_type_filter: str = '全部') -> Tuple[List[Dict[str, Any]], bool]:
        """
        加载可供用户选择配置到机架上的模块列表（用于UI穿梭框）。
        列表的来源：
        - 如果 `self.processed_enriched_devices` (通过 `set_devices_data` 设置的) 存在，则优先使用此列表作为基础，
          这样可以反映来自实际输入数据中的模块（可能包含特定项目的模块或已处理的属性）。
        - 否则（例如，在未加载任何项目数据，直接打开配置对话框时），回退到使用所有预定义的模块
          (通过 `self.module_info_provider.get_all_predefined_modules()` 获取)。
        
        过滤逻辑：
        1. 模块必须属于 `self.ALLOWED_MODULE_TYPES` 中定义的类型，或者其型号在 `self.SPECIAL_ALLOWED_MODULES` 中。
        2. 应用UI传入的 `module_type_filter` (如 'AI', 'DI', 或 '全部')。
        (注意：已从PLC配置中使用的模块实例应在此方法外部或UI层面进行排除，此方法旨在提供一个总的可用池)
        
        Args:
            module_type_filter (str, optional): UI指定的模块类型过滤器。默认为 '全部'。
            
        Returns:
            Tuple[List[Dict[str, Any]], bool]: 一个元组，包含：
                - available_for_ui (List[Dict[str, Any]]): 符合条件的可用模块列表 (副本)。
                - has_data (bool): 表示列表是否为空的布尔值。
        """
        source_for_shuttle: List[Dict[str, Any]]
        # 判断模块来源：优先使用已处理的设备数据，否则使用所有预定义模块
        if self.processed_enriched_devices:
            source_for_shuttle = self.processed_enriched_devices 
            logger.debug(f"Loading available modules for shuttle from {len(source_for_shuttle)} processed/enriched devices.")
        else:
            source_for_shuttle = self.module_info_provider.get_all_predefined_modules()
            logger.debug(f"Loading available modules for shuttle from {len(source_for_shuttle)} predefined modules (no device data).")

        available_for_ui = []
        for module_candidate in source_for_shuttle:
            m_copy = module_candidate.copy() # 操作副本
            m_type = m_copy.get('type', '未录入') # 使用已丰富化的 'type' 字段
            m_model_upper = m_copy.get('model', '').upper()

            # 判断模块是否被允许：类型在允许列表内，或者型号在特殊允许列表内
            is_allowed_type = m_type in self.ALLOWED_MODULE_TYPES
            is_special_model = m_model_upper in self.SPECIAL_ALLOWED_MODULES
            
            if is_allowed_type or is_special_model:
                # 如果模块被允许，再应用UI的类型过滤器
                if module_type_filter == '全部' or m_type == module_type_filter:
                    available_for_ui.append(m_copy)
        
        logger.info(f"load_available_modules: Filter '{module_type_filter}'. Found {len(available_for_ui)} modules for UI.")
        return available_for_ui, len(available_for_ui) > 0
        
    def get_module_by_model(self, model_str: str) -> Optional[Dict[str, Any]]:
        """
        根据模块型号字符串检索模块的详细信息。
        采用特定的查找顺序以获取最准确和上下文相关的模块数据：
        1.  **当前已处理和丰富化的设备列表 (`self.processed_enriched_devices`)**: 
            这是最高优先级，因为它可能包含特定于当前加载数据的模块实例信息（例如，如果模块信息是从设备清单中动态生成的，
            或者在 `enrich_device_data` 过程中添加了如 `sub_channels` 等关键的运行时属性）。
        2.  **预定义模块列表 (通过 `ModuleInfoProvider.get_predefined_module_by_model`)**: 
            如果上述列表中未找到，则在所有预定义模块中进行精确型号匹配。
        3.  **plc_modules.py 中的推断逻辑 (通过 `ModuleInfoProvider.get_inferred_module_info`)**: 
            作为最后的查找手段，使用 `plc_modules.py` 中可能存在的更复杂的型号推断规则。
        
        Args:
            model_str (str): 要查询的模块型号字符串。
            
        Returns:
            Optional[Dict[str, Any]]: 如果找到模块，则返回其信息的字典拷贝；否则返回 None。
                                      返回拷贝是为了防止外部代码意外修改内部缓存的数据。
        """
        model_upper = model_str.upper()
        
        # 优先级1: 在当前已处理和丰富化的设备数据中查找
        for device in self.processed_enriched_devices:
            if device.get('model', '').upper() == model_upper:
                # 这个设备对象应该已经被 enrich_device_data 完全处理，包含了 sub_channels 等信息
                return device.copy() 

        # 优先级2: 在预定义模块列表中精确查找 (通过 ModuleInfoProvider)
        predefined_match = self.module_info_provider.get_predefined_module_by_model(model_str)
        if predefined_match:
            return predefined_match # ModuleInfoProvider 应确保返回的是副本

        # 优先级3: 回退到 plc_modules.py 的推断逻辑 (通过 ModuleInfoProvider)
        inferred_match = self.module_info_provider.get_inferred_module_info(model_str)
        if inferred_match: 
            # 确保这也是一个副本，以防它来自 plc_modules 中的共享缓存
            return inferred_match.copy() if isinstance(inferred_match, dict) else inferred_match
        
        logger.warning(f"Module model '{model_str}' not found by any lookup method.")
        return None
        
    def save_configuration(self, config_data_from_ui: Any) -> bool:
        """
        保存 (经过验证后) 从UI传递过来的PLC配置数据。
        此方法会协调 `PLCConfigurationHandler` 来执行实际的验证、模拟保存（打印统计和地址），
        并在成功后更新 `self.current_plc_config` 和 `self.last_generated_addresses`。
        
        Args:
            config_data_from_ui (Any): 来自UI的配置数据。可以是两种格式：
                - `Dict[tuple, str]`: 直接是 `{(rack_id, slot_id): model_name}` 的字典。
                - `List[Dict[str, Any]]`: 包含 `{"rack_id", "slot_id", "model"}` 的字典列表，将被转换为上述字典格式。
            
        Returns:
            bool: 配置是否成功保存 (True) 或失败 (False)。
                  失败时，应已通过logger或print输出了错误信息。
        """
        config_dict: Dict[tuple, str] = {}
        # 标准化输入配置数据为 {(rack_id, slot_id): model_name} 字典格式
        if isinstance(config_data_from_ui, dict):
            config_dict = config_data_from_ui
        elif isinstance(config_data_from_ui, list):
            try:
                for item in config_data_from_ui:
                    config_dict[(item["rack_id"], item["slot_id"])] = item["model"]
            except (TypeError, KeyError) as e:
                logger.error(f"Error converting configuration list to dict: {e}", exc_info=True)
                print(f"错误: 转换配置列表时出错 - {e}")
                return False
        else:
            logger.error(f"Unsupported configuration data type provided to save_configuration: {type(config_data_from_ui)}")
            print(f"错误: 不支持的配置数据格式: {type(config_data_from_ui)}")
            return False
        
        current_system_type = self.system_setup_manager.get_system_type()
        
        # 将配置字典和当前系统类型传递给 PLCConfigurationHandler 进行处理
        # 关键：同时传递 self.processed_enriched_devices 作为上下文，
        # 以便 config_handler 内部的 _get_module_details_for_config 能获取到最完整的模块信息（包括sub_channels）
        success, message = self.config_handler.save_plc_configuration(
            config_dict, 
            current_system_type,
            self.processed_enriched_devices 
        )
        
        if success:
            self.current_plc_config = config_dict.copy() # 存储已验证的配置副本
            # 配置成功保存后，立即生成并存储对应的通道地址列表和IO总数
            generated_addrs, io_cnt = self.config_handler.generate_channel_addresses_list(
                self.current_plc_config, 
                self.processed_enriched_devices, # 同样需要上下文 
                True # 通常我们希望包含非IO模块的记录
            )
            self.last_generated_addresses = generated_addrs
            self.last_generated_io_count = io_cnt
            logger.info(f"Configuration saved successfully. {message}")
        else:
            # 如果保存失败，错误信息应已由 PLCConfigurationHandler 或上述转换逻辑打印
            logger.warning(f"Save configuration failed. Reason: {message}")
        return success

    def generate_channel_addresses(self, config_dict_to_process: Dict[tuple, str], include_non_io: bool = True) -> List[Dict[str, Any]]:
        """
        为给定的配置字典生成通道地址列表。
        主要由 `save_configuration` 内部调用，但也可以被外部直接调用以预览地址（不更新实例状态）。
        此方法不更新实例的 `self.last_generated_addresses` 或 `self.last_generated_io_count`。
        
        Args:
            config_dict_to_process (Dict[tuple, str]): 要为其生成地址的PLC配置，
                                                       格式为 `{(rack_id, slot_id): model_name}`。
            include_non_io (bool, optional): 是否在结果中包含非IO模块的记录。默认为True。
            
        Returns:
            List[Dict[str, Any]]: 生成的通道地址列表。
        """
        addrs, _ = self.config_handler.generate_channel_addresses_list(
            config_dict_to_process, 
            self.processed_enriched_devices, # 使用当前已处理的设备作为上下文信息
            include_non_io
        )
        return addrs
        
    def get_channel_addresses(self) -> List[Dict[str, Any]]:
        """返回由最后一次成功的 `save_configuration` 调用所生成的通道地址列表。"""
        return self.last_generated_addresses

# --- 全局辅助函数 --- 

def print_generated_channel_addresses_summary(channel_addresses_list: List[Dict[str, Any]], stat_total_io: int):
    """
    打印生成的通道地址列表的摘要信息到控制台。
    包括IO通道详情、非IO模块列表以及数量统计。
    还会比较从统计模块得到的IO总数与实际生成地址的IO数量，并在不一致时发出警告。

    Args:
        channel_addresses_list (List[Dict[str, Any]]): `PLCConfigurationHandler.generate_channel_addresses_list` 返回的地址列表。
        stat_total_io (int): 从 `PLCConfigurationHandler.save_plc_configuration` 中统计得出的总IO通道数，用于交叉验证。
    """
    # 从地址列表中分离IO通道和非IO通道记录
    io_channels_from_list = [addr for addr in channel_addresses_list if addr.get('is_io_channel', False)]
    non_io_channels_from_list = [addr for addr in channel_addresses_list if not addr.get('is_io_channel', False)]

    actual_io_count_from_list = len(io_channels_from_list)
    # 交叉验证IO总数：比较统计值和实际生成地址的IO数量
    if stat_total_io != actual_io_count_from_list:
        logger.warning(f"Channel statistic from summary ({stat_total_io}) vs "
                       f"actual IO addresses generated ({actual_io_count_from_list}) mismatch!")

    print("\n-------- 通道位号列表 (Generated) --------")
    print("序号\t模块名称\t模块类型\t通道位号\t类型")
    for i, addr_info in enumerate(io_channels_from_list, 1):
        print(f"{i}\t{addr_info['model']}\t{addr_info['type']}\t{addr_info['address']}\tIO通道")
    
    if non_io_channels_from_list:
        print("\n-------- 通信模块列表 (Generated,不计入IO通道) --------")
        for i, addr_info in enumerate(non_io_channels_from_list, 1):
            print(f"{i}\t{addr_info['model']}\t{addr_info['type']}\t{addr_info['address']}\t{addr_info.get('type','模块')}")
    
    print(f"\n总IO通道数 (来自列表生成): {actual_io_count_from_list}, 非IO通道模块: {len(non_io_channels_from_list)}")
    print("注意: 配置数据已记录，实际保存功能尚未实现 (此为地址列表打印)。")
    print("--------------------------------------\n") 