# -*- coding: utf-8 -*-
"""
PLC配置控制器

负责协调UI组件和业务逻辑，实现MVC模式中的Controller层
提供数据流管理、状态同步和事件处理
"""

from typing import List, Dict, Any, Optional, Callable
from PySide6.QtCore import QObject, Signal

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import PLCModule, TransferDirection, TransferListState
    from .utils import calculate_rack_requirements, ModuleType, batch_convert_legacy_modules
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import PLCModule, TransferDirection, TransferListState
    from ui.components.plc_config.utils import calculate_rack_requirements, ModuleType, batch_convert_legacy_modules


class PLCConfigController(QObject):
    """
    PLC配置控制器
    
    协调穿梭框、机架显示、系统信息等组件
    管理配置状态和数据流
    """
    
    # 控制器信号
    configurationChanged = Signal(dict)     # 配置发生变化
    statisticsUpdated = Signal(dict)        # 统计信息更新
    validationFailed = Signal(str)          # 验证失败
    operationCompleted = Signal(str, bool)  # 操作完成 (操作名, 是否成功)
    
    def __init__(self, io_data_loader=None, parent=None):
        super().__init__(parent)
        self.io_data_loader = io_data_loader
        self.current_modules: List[PLCModule] = []
        self.current_configuration: Dict[str, Any] = {}
        self.validation_callbacks: List[Callable] = []
        
        # 状态追踪
        self.is_loading = False
        self.has_unsaved_changes = False
    
    def set_io_data_loader(self, io_data_loader):
        """设置IODataLoader实例"""
        self.io_data_loader = io_data_loader
    
    def load_modules_from_legacy_data(self, legacy_modules: List[Dict[str, Any]]) -> List[PLCModule]:
        """
        从现有系统数据格式加载模块
        
        Args:
            legacy_modules: 现有系统的模块数据列表
            
        Returns:
            List[PLCModule]: 转换后的PLC模块列表
        """
        self.is_loading = True
        
        try:
            # 批量转换现有数据格式
            converted_data = batch_convert_legacy_modules(legacy_modules)
            
            # 创建PLCModule实例
            plc_modules = []
            for module_data in converted_data:
                try:
                    plc_module = PLCModule.from_dict(module_data)
                    plc_modules.append(plc_module)
                except Exception as e:
                    print(f"⚠️ 加载模块失败: {module_data.get('model', 'unknown')}, 错误: {e}")
            
            self.current_modules = plc_modules
            self.has_unsaved_changes = False
            
            print(f"✅ 成功加载 {len(plc_modules)} 个模块")
            return plc_modules
            
        except Exception as e:
            print(f"❌ 加载模块数据失败: {e}")
            return []
        finally:
            self.is_loading = False
    
    def handle_transfer_change(self, transfer_data: Dict[str, Any]) -> bool:
        """
        处理穿梭框传输变化
        
        Args:
            transfer_data: 传输变化数据
            
        Returns:
            bool: 是否处理成功
        """
        try:
            from_side = transfer_data.get('from', '')
            to_side = transfer_data.get('to', '')
            moved_keys = transfer_data.get('list', [])
            
            print(f"📋 处理传输: {len(moved_keys)} 个模块从 {from_side} 到 {to_side}")
            
            # 标记为有未保存的变化
            self.has_unsaved_changes = True
            
            # 发送配置变化信号
            self.configurationChanged.emit({
                'type': 'transfer',
                'from': from_side,
                'to': to_side,
                'items': moved_keys,
                'has_unsaved_changes': self.has_unsaved_changes
            })
            
            return True
            
        except Exception as e:
            print(f"❌ 处理传输变化失败: {e}")
            self.validationFailed.emit(f"传输处理失败: {str(e)}")
            return False
    
    def handle_selection_change(self, selection_data: Dict[str, Any]):
        """
        处理选择变化
        
        Args:
            selection_data: 选择变化数据
        """
        direction = selection_data.get('direction', '')
        selected_count = len(selection_data.get('list', []))
        
        print(f"📌 选择变化: {direction}侧选中 {selected_count} 项")
        
        # 可以在这里添加选择验证逻辑
        # 例如：检查CPU模块只能选择一个等
    
    def validate_configuration(self, selected_modules: List[PLCModule]) -> tuple[bool, str]:
        """
        验证配置有效性
        
        Args:
            selected_modules: 已选择的模块列表
            
        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        try:
            # 1. 检查是否有CPU模块
            cpu_modules = [m for m in selected_modules if m.module_type.upper() == 'CPU']
            if len(cpu_modules) == 0:
                return False, "配置中必须包含至少一个CPU模块"
            elif len(cpu_modules) > 1:
                return False, "配置中只能包含一个CPU模块"
            
            # 2. 检查模块兼容性
            for module in selected_modules:
                if not self._is_module_compatible(module):
                    return False, f"模块 {module.model} 与当前系统不兼容"
            
            # 3. 检查机架容量
            stats = calculate_rack_requirements([m.to_dict() for m in selected_modules])
            if stats.get('required_racks', 0) > 4:  # 假设最多支持4个机架
                return False, "所需机架数量超过系统支持的最大值(4个)"
            
            # 4. 执行自定义验证回调
            for validator in self.validation_callbacks:
                is_valid, error_msg = validator(selected_modules)
                if not is_valid:
                    return False, error_msg
            
            return True, ""
            
        except Exception as e:
            return False, f"验证过程中发生错误: {str(e)}"
    
    def _is_module_compatible(self, module: PLCModule) -> bool:
        """检查模块兼容性"""
        # 这里可以添加具体的兼容性检查逻辑
        # 例如：检查模块系列、制造商等
        return module.manufacturer == "和利时" and module.series == "LK"
    
    def add_validation_callback(self, callback: Callable[[List[PLCModule]], tuple[bool, str]]):
        """添加自定义验证回调"""
        self.validation_callbacks.append(callback)
    
    def apply_configuration(self, selected_modules: List[PLCModule]) -> bool:
        """
        应用配置
        
        Args:
            selected_modules: 已选择的模块列表
            
        Returns:
            bool: 是否应用成功
        """
        try:
            # 1. 验证配置
            is_valid, error_msg = self.validate_configuration(selected_modules)
            if not is_valid:
                self.validationFailed.emit(error_msg)
                return False
            
            # 2. 自动分配机架位置
            self._auto_assign_rack_positions(selected_modules)
            
            # 3. 保存到IODataLoader
            if self.io_data_loader and hasattr(self.io_data_loader, 'save_configuration'):
                config_dict = {}
                for module in selected_modules:
                    if module.is_placed():
                        config_dict[(module.rack_id, module.slot_id)] = module.model
                
                success = self.io_data_loader.save_configuration(config_dict)
                if success:
                    self.has_unsaved_changes = False
                    self.operationCompleted.emit("apply_configuration", True)
                    print("✅ 配置应用成功")
                    return True
                else:
                    self.operationCompleted.emit("apply_configuration", False)
                    print("❌ 配置保存失败")
                    return False
            else:
                print("⚠️ IODataLoader不可用，无法保存配置")
                return False
                
        except Exception as e:
            print(f"❌ 应用配置失败: {e}")
            self.operationCompleted.emit("apply_configuration", False)
            return False
    
    def _auto_assign_rack_positions(self, modules: List[PLCModule]):
        """自动分配机架位置"""
        rack_id = 1
        slot_id = 0
        
        # 先分配CPU模块到槽位0
        cpu_modules = [m for m in modules if m.module_type.upper() == 'CPU']
        for cpu_module in cpu_modules:
            cpu_module.rack_id = rack_id
            cpu_module.slot_id = 0
        
        # 然后分配其他模块
        slot_id = 1  # 从槽位1开始
        for module in modules:
            if module.module_type.upper() != 'CPU' and not module.is_placed():
                module.rack_id = rack_id
                module.slot_id = slot_id
                slot_id += 1
                
                # 如果槽位满了，换下一个机架
                if slot_id >= 16:
                    rack_id += 1
                    slot_id = 1  # 新机架从槽位1开始（槽位0留给CPU）
    
    def update_statistics(self, selected_modules: List[PLCModule]):
        """
        更新统计信息
        
        Args:
            selected_modules: 已选择的模块列表
        """
        try:
            stats = calculate_rack_requirements([m.to_dict() for m in selected_modules])
            
            # 添加额外的统计信息
            stats.update({
                'has_cpu': any(m.module_type.upper() == 'CPU' for m in selected_modules),
                'module_types': list(set(m.module_type for m in selected_modules)),
                'total_channels': sum(m.channels for m in selected_modules if m.channels > 0),
                'configuration_valid': self.validate_configuration(selected_modules)[0]
            })
            
            self.statisticsUpdated.emit(stats)
            
        except Exception as e:
            print(f"❌ 更新统计信息失败: {e}")
    
    def reset_configuration(self) -> bool:
        """
        重置配置
        
        Returns:
            bool: 是否重置成功
        """
        try:
            self.has_unsaved_changes = False
            self.current_configuration = {}
            
            # 清除IODataLoader中的配置
            if self.io_data_loader and hasattr(self.io_data_loader, 'clear_current_project_configuration'):
                self.io_data_loader.clear_current_project_configuration()
            
            self.operationCompleted.emit("reset_configuration", True)
            print("✅ 配置重置成功")
            return True
            
        except Exception as e:
            print(f"❌ 重置配置失败: {e}")
            self.operationCompleted.emit("reset_configuration", False)
            return False
    
    def get_current_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            'is_loading': self.is_loading,
            'has_unsaved_changes': self.has_unsaved_changes,
            'modules_count': len(self.current_modules),
            'io_data_loader_available': self.io_data_loader is not None
        }


class ModuleFilterController(QObject):
    """
    模块过滤控制器
    负责模块的搜索、过滤和分类逻辑
    """
    
    # 过滤信号
    filterChanged = Signal(dict)  # 过滤条件变化
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = {
            'type': '全部',
            'search_text': '',
            'manufacturer': '全部',
            'series': '全部'
        }
    
    def set_type_filter(self, module_type: str):
        """设置模块类型过滤"""
        self.current_filter['type'] = module_type
        self._emit_filter_change()
    
    def set_search_filter(self, search_text: str):
        """设置搜索过滤"""
        self.current_filter['search_text'] = search_text.strip()
        self._emit_filter_change()
    
    def set_manufacturer_filter(self, manufacturer: str):
        """设置制造商过滤"""
        self.current_filter['manufacturer'] = manufacturer
        self._emit_filter_change()
    
    def clear_filters(self):
        """清空所有过滤条件"""
        self.current_filter = {
            'type': '全部',
            'search_text': '',
            'manufacturer': '全部',
            'series': '全部'
        }
        self._emit_filter_change()
    
    def filter_modules(self, modules: List[PLCModule]) -> List[PLCModule]:
        """
        应用过滤条件
        
        Args:
            modules: 原始模块列表
            
        Returns:
            List[PLCModule]: 过滤后的模块列表
        """
        filtered = modules.copy()
        
        # 类型过滤
        if self.current_filter['type'] != '全部':
            filtered = [m for m in filtered if m.module_type.upper() == self.current_filter['type'].upper()]
        
        # 搜索文本过滤
        if self.current_filter['search_text']:
            search_text = self.current_filter['search_text'].lower()
            filtered = [m for m in filtered if 
                       search_text in m.title.lower() or 
                       search_text in m.model.lower() or 
                       search_text in m.description.lower()]
        
        # 制造商过滤
        if self.current_filter['manufacturer'] != '全部':
            filtered = [m for m in filtered if m.manufacturer == self.current_filter['manufacturer']]
        
        return filtered
    
    def _emit_filter_change(self):
        """发送过滤条件变化信号"""
        self.filterChanged.emit(self.current_filter.copy()) 