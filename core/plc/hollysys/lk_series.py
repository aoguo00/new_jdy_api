"""和利时LK系列PLC模块"""
from typing import List, Dict, Optional
from .lk_db import LKModuleManager

class LKRack:
    """LK系列机架"""
    def __init__(self, backplane_model: str):
        self.module_manager = LKModuleManager()
        self.backplane_info = self.module_manager.get_backplane_info(backplane_model)
        
        if not self.backplane_info:
            raise ValueError(f"未知的背板型号: {backplane_model}")
            
        self.model = self.backplane_info['model']
        self.total_slots = self.backplane_info['slots']
        self.description = self.backplane_info['description']
        
        # 槽位分配，0表示未使用，其他值为模块型号
        self.slots = [''] * self.total_slots
        # 槽位1预留给DP通讯模块
        self.slots[0] = 'DP'

    def get_available_slots(self) -> List[int]:
        """获取可用的槽位号列表"""
        return [i + 1 for i, module in enumerate(self.slots) if not module]

    def assign_module(self, slot: int, module_model: str) -> bool:
        """
        分配模块到指定槽位
        :param slot: 槽位号（1-based）
        :param module_model: 模块型号
        :return: 是否分配成功
        """
        if slot < 1 or slot > self.total_slots:
            raise ValueError(f"无效的槽位号: {slot}")
            
        if self.slots[slot - 1]:
            return False
            
        module_info = self.module_manager.get_module_info(module_model)
        if not module_info:
            raise ValueError(f"未知的模块型号: {module_model}")
            
        self.slots[slot - 1] = module_model
        return True

    def get_slot_info(self) -> List[Dict]:
        """获取所有槽位信息"""
        slot_info = []
        for i, module_model in enumerate(self.slots):
            if not module_model:
                continue
                
            info = {
                'slot': i + 1,
                'model': module_model
            }
            
            if module_model != 'DP':
                module_info = self.module_manager.get_module_info(module_model)
                info.update({
                    'type': module_info['module_type'],
                    'channels': module_info['channels'],
                    'description': module_info['description']
                })
            else:
                info.update({
                    'type': 'DP',
                    'description': 'DP通讯模块'
                })
                
            slot_info.append(info)
            
        return slot_info

class LKSeries:
    """LK系列PLC管理器"""
    def __init__(self):
        self.module_manager = LKModuleManager()
        self.racks: List[LKRack] = []
        
    def add_rack(self, backplane_model: str) -> LKRack:
        """
        添加机架
        :param backplane_model: 背板型号
        :return: 机架实例
        """
        rack = LKRack(backplane_model)
        self.racks.append(rack)
        return rack
    
    def get_module_list(self, module_type: Optional[str] = None) -> List[Dict]:
        """
        获取模块列表
        :param module_type: 模块类型（可选）
        :return: 模块信息列表
        """
        if module_type:
            return self.module_manager.get_modules_by_type(module_type)
            
        # 获取所有类型的模块
        all_modules = []
        for module_type in ['AI', 'AO', 'DI', 'DO']:
            modules = self.module_manager.get_modules_by_type(module_type)
            all_modules.extend(modules)
        return all_modules
    
    def assign_modules(self, modules: List[Dict]) -> List[Dict]:
        """
        分配模块到机架
        :param modules: 模块列表，每个模块包含型号和数量
        :return: 分配结果
        """
        current_rack = None
        assignments = []
        
        for module in modules:
            model = module['model']
            count = module.get('count', 1)
            
            for _ in range(count):
                # 如果没有机架或当前机架已满，创建新机架
                if not current_rack or not current_rack.get_available_slots():
                    current_rack = self.add_rack('LK117')
                
                # 获取第一个可用槽位
                available_slots = current_rack.get_available_slots()
                if not available_slots:
                    continue
                    
                slot = available_slots[0]
                if current_rack.assign_module(slot, model):
                    assignments.append({
                        'rack_index': len(self.racks) - 1,
                        'slot': slot,
                        'model': model
                    })
                
        return assignments 