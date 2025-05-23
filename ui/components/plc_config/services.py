# -*- coding: utf-8 -*-
"""
PLC配置服务层

提供缓存管理、数据持久化、配置同步等业务服务
实现与现有IODataLoader系统的集成和兼容
"""

from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import json
import pickle
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import PLCModule, TransferDirection
    from .utils import calculate_rack_requirements, validate_transfer_item_data
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import PLCModule, TransferDirection
    from ui.components.plc_config.utils import calculate_rack_requirements, validate_transfer_item_data


class CacheService(QObject):
    """
    缓存服务
    管理PLC配置的内存缓存和持久化缓存
    与现有IODataLoader的缓存系统集成
    """
    
    # 缓存信号
    cacheUpdated = Signal(str, dict)    # 缓存更新 (site_name, config_data)
    cacheCleared = Signal(str)          # 缓存清除 (site_name)
    cacheError = Signal(str, str)       # 缓存错误 (operation, error_msg)
    
    def __init__(self, io_data_loader=None, parent=None):
        super().__init__(parent)
        self.io_data_loader = io_data_loader
        
        # 内存缓存
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        
        # 缓存配置
        self.cache_config = {
            'max_sites': 10,
            'auto_save': True,
            'compression': True,
            'encryption': False
        }
        
        # 定时保存计时器
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save_to_disk)
        self.auto_save_timer.start(30000)  # 30秒自动保存一次
    
    def set_io_data_loader(self, io_data_loader):
        """设置IODataLoader实例"""
        self.io_data_loader = io_data_loader
    
    def save_site_configuration(self, site_name: str, modules: List[PLCModule], 
                               system_info: Dict[str, Any] = None) -> bool:
        """
        保存场站配置到缓存
        
        Args:
            site_name: 场站名称
            modules: 已配置的模块列表
            system_info: 系统信息
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if not site_name:
                raise ValueError("场站名称不能为空")
            
            # 构建缓存数据
            cache_data = {
                'modules': [module.to_dict() for module in modules],
                'system_info': system_info or {},
                'statistics': calculate_rack_requirements([m.to_dict() for m in modules]),
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
            
            # 验证数据完整性
            if not self._validate_cache_data(cache_data):
                raise ValueError("缓存数据验证失败")
            
            # 保存到内存缓存
            self.memory_cache[site_name] = cache_data
            
            # 限制缓存大小
            self._limit_cache_size()
            
            # 同步到IODataLoader缓存
            if self.io_data_loader:
                self._sync_to_io_data_loader(site_name, modules)
            
            # 发送缓存更新信号
            self.cacheUpdated.emit(site_name, cache_data)
            
            print(f"✅ 场站 '{site_name}' 配置已保存到缓存")
            return True
            
        except Exception as e:
            error_msg = f"保存场站配置失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.cacheError.emit("save_configuration", error_msg)
            return False
    
    def load_site_configuration(self, site_name: str) -> Optional[Dict[str, Any]]:
        """
        从缓存加载场站配置
        
        Args:
            site_name: 场站名称
            
        Returns:
            Optional[Dict]: 配置数据，如果不存在则返回None
        """
        try:
            # 先尝试从内存缓存加载
            if site_name in self.memory_cache:
                cache_data = self.memory_cache[site_name]
                print(f"✅ 从内存缓存加载场站 '{site_name}' 配置")
                return cache_data
            
            # 尝试从IODataLoader缓存加载
            if self.io_data_loader and hasattr(self.io_data_loader, 'has_cached_config_for_site'):
                if self.io_data_loader.has_cached_config_for_site(site_name):
                    if self.io_data_loader.load_cached_config_for_site(site_name):
                        # 从IODataLoader重建缓存数据
                        plc_config = self.io_data_loader.get_current_plc_config()
                        modules = self._convert_plc_config_to_modules(plc_config)
                        
                        cache_data = {
                            'modules': [module.to_dict() for module in modules],
                            'system_info': self.io_data_loader.get_rack_info(),
                            'statistics': calculate_rack_requirements([m.to_dict() for m in modules]),
                            'timestamp': datetime.now().isoformat(),
                            'version': '1.0.0',
                            'source': 'io_data_loader'
                        }
                        
                        # 保存到内存缓存
                        self.memory_cache[site_name] = cache_data
                        
                        print(f"✅ 从IODataLoader缓存加载场站 '{site_name}' 配置")
                        return cache_data
            
            print(f"⚠️ 场站 '{site_name}' 的配置缓存不存在")
            return None
            
        except Exception as e:
            error_msg = f"加载场站配置失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.cacheError.emit("load_configuration", error_msg)
            return None
    
    def has_site_cache(self, site_name: str) -> bool:
        """
        检查场站是否有缓存配置
        
        Args:
            site_name: 场站名称
            
        Returns:
            bool: 是否存在缓存
        """
        # 检查内存缓存
        if site_name in self.memory_cache:
            return True
        
        # 检查IODataLoader缓存
        if self.io_data_loader and hasattr(self.io_data_loader, 'has_cached_config_for_site'):
            return self.io_data_loader.has_cached_config_for_site(site_name)
        
        return False
    
    def clear_site_cache(self, site_name: str) -> bool:
        """
        清除场站缓存
        
        Args:
            site_name: 场站名称
            
        Returns:
            bool: 是否清除成功
        """
        try:
            # 清除内存缓存
            if site_name in self.memory_cache:
                del self.memory_cache[site_name]
            
            # 清除IODataLoader缓存
            if self.io_data_loader and hasattr(self.io_data_loader, 'clear_site_cache'):
                self.io_data_loader.clear_site_cache(site_name)
            
            self.cacheCleared.emit(site_name)
            print(f"✅ 场站 '{site_name}' 缓存已清除")
            return True
            
        except Exception as e:
            error_msg = f"清除场站缓存失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.cacheError.emit("clear_cache", error_msg)
            return False
    
    def clear_all_cache(self) -> bool:
        """清除所有缓存"""
        try:
            # 清除内存缓存
            self.memory_cache.clear()
            
            # 清除IODataLoader缓存
            if self.io_data_loader and hasattr(self.io_data_loader, 'clear_all_site_cache'):
                self.io_data_loader.clear_all_site_cache()
            
            print("✅ 所有缓存已清除")
            return True
            
        except Exception as e:
            error_msg = f"清除所有缓存失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.cacheError.emit("clear_all_cache", error_msg)
            return False
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取缓存信息"""
        return {
            'sites_count': len(self.memory_cache),
            'sites': list(self.memory_cache.keys()),
            'config': self.cache_config.copy(),
            'io_data_loader_available': self.io_data_loader is not None
        }
    
    def _validate_cache_data(self, cache_data: Dict[str, Any]) -> bool:
        """验证缓存数据完整性"""
        required_fields = ['modules', 'system_info', 'statistics', 'timestamp']
        
        for field in required_fields:
            if field not in cache_data:
                return False
        
        # 验证模块数据
        for module_data in cache_data['modules']:
            if not validate_transfer_item_data(module_data):
                return False
        
        return True
    
    def _limit_cache_size(self):
        """限制缓存大小"""
        max_sites = self.cache_config['max_sites']
        
        if len(self.memory_cache) > max_sites:
            # 删除最旧的缓存项
            sorted_items = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].get('timestamp', ''),
                reverse=False
            )
            
            while len(self.memory_cache) > max_sites:
                site_name = sorted_items.pop(0)[0]
                del self.memory_cache[site_name]
                print(f"⚠️ 缓存已满，删除最旧的场站缓存: {site_name}")
    
    def _sync_to_io_data_loader(self, site_name: str, modules: List[PLCModule]):
        """同步到IODataLoader缓存"""
        try:
            if not self.io_data_loader:
                return
            
            # 设置当前场站
            if hasattr(self.io_data_loader, 'set_current_site'):
                self.io_data_loader.set_current_site(site_name)
            
            # 构建配置字典
            config_dict = {}
            for module in modules:
                if module.is_placed():
                    config_dict[(module.rack_id, module.slot_id)] = module.model
            
            # 保存到IODataLoader
            if hasattr(self.io_data_loader, 'save_current_config_to_cache'):
                # 先设置当前配置
                if hasattr(self.io_data_loader, 'current_plc_config'):
                    self.io_data_loader.current_plc_config = config_dict
                
                # 保存到缓存
                self.io_data_loader.save_current_config_to_cache()
            
        except Exception as e:
            print(f"⚠️ 同步到IODataLoader失败: {e}")
    
    def _convert_plc_config_to_modules(self, plc_config: Dict) -> List[PLCModule]:
        """将PLC配置转换为模块列表"""
        modules = []
        
        for (rack_id, slot_id), model_name in plc_config.items():
            # 从IODataLoader获取模块信息
            if self.io_data_loader and hasattr(self.io_data_loader, 'get_module_by_model'):
                module_info = self.io_data_loader.get_module_by_model(model_name)
                if module_info:
                    module = PLCModule.from_legacy_dict(module_info)
                    module.rack_id = rack_id
                    module.slot_id = slot_id
                    modules.append(module)
        
        return modules
    
    def _auto_save_to_disk(self):
        """自动保存到磁盘（如果启用）"""
        if not self.cache_config['auto_save'] or not self.memory_cache:
            return
        
        try:
            # 这里可以实现磁盘持久化逻辑
            # 暂时只打印日志
            print(f"🔄 自动保存缓存: {len(self.memory_cache)} 个场站")
        except Exception as e:
            print(f"❌ 自动保存失败: {e}")


class ConfigurationService(QObject):
    """
    配置服务
    处理配置的导入、导出、版本管理和同步
    """
    
    # 配置服务信号
    configImported = Signal(str, dict)      # 配置导入成功
    configExported = Signal(str, str)       # 配置导出成功 (site_name, file_path)
    configSynced = Signal(str)              # 配置同步成功
    serviceError = Signal(str, str)         # 服务错误
    
    def __init__(self, cache_service: CacheService = None, parent=None):
        super().__init__(parent)
        self.cache_service = cache_service
        self.supported_formats = ['json', 'pickle', 'xml']
    
    def export_configuration(self, site_name: str, file_path: str, 
                           format_type: str = 'json') -> bool:
        """
        导出配置到文件
        
        Args:
            site_name: 场站名称
            file_path: 文件路径
            format_type: 文件格式 ('json', 'pickle', 'xml')
            
        Returns:
            bool: 是否导出成功
        """
        try:
            if format_type not in self.supported_formats:
                raise ValueError(f"不支持的格式: {format_type}")
            
            # 从缓存获取配置
            if not self.cache_service:
                raise ValueError("缓存服务不可用")
            
            config_data = self.cache_service.load_site_configuration(site_name)
            if not config_data:
                raise ValueError(f"场站 '{site_name}' 的配置不存在")
            
            # 根据格式导出
            if format_type == 'json':
                self._export_to_json(config_data, file_path)
            elif format_type == 'pickle':
                self._export_to_pickle(config_data, file_path)
            elif format_type == 'xml':
                self._export_to_xml(config_data, file_path)
            
            self.configExported.emit(site_name, file_path)
            print(f"✅ 配置已导出: {file_path}")
            return True
            
        except Exception as e:
            error_msg = f"导出配置失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.serviceError.emit("export_configuration", error_msg)
            return False
    
    def import_configuration(self, site_name: str, file_path: str) -> bool:
        """
        从文件导入配置
        
        Args:
            site_name: 场站名称
            file_path: 文件路径
            
        Returns:
            bool: 是否导入成功
        """
        try:
            if not Path(file_path).exists():
                raise ValueError(f"文件不存在: {file_path}")
            
            # 根据文件扩展名确定格式
            suffix = Path(file_path).suffix.lower()
            if suffix == '.json':
                config_data = self._import_from_json(file_path)
            elif suffix == '.pkl' or suffix == '.pickle':
                config_data = self._import_from_pickle(file_path)
            elif suffix == '.xml':
                config_data = self._import_from_xml(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {suffix}")
            
            # 验证导入的数据
            if not self.cache_service._validate_cache_data(config_data):
                raise ValueError("导入的配置数据格式不正确")
            
            # 重建模块列表
            modules = []
            for module_data in config_data['modules']:
                module = PLCModule.from_dict(module_data)
                modules.append(module)
            
            # 保存到缓存
            if self.cache_service:
                self.cache_service.save_site_configuration(
                    site_name, modules, config_data.get('system_info', {})
                )
            
            self.configImported.emit(site_name, config_data)
            print(f"✅ 配置已导入: {site_name}")
            return True
            
        except Exception as e:
            error_msg = f"导入配置失败: {str(e)}"
            print(f"❌ {error_msg}")
            self.serviceError.emit("import_configuration", error_msg)
            return False
    
    def _export_to_json(self, config_data: Dict[str, Any], file_path: str):
        """导出为JSON格式"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
    
    def _export_to_pickle(self, config_data: Dict[str, Any], file_path: str):
        """导出为Pickle格式"""
        with open(file_path, 'wb') as f:
            pickle.dump(config_data, f)
    
    def _export_to_xml(self, config_data: Dict[str, Any], file_path: str):
        """导出为XML格式"""
        # 简单的XML导出实现
        import xml.etree.ElementTree as ET
        
        root = ET.Element("PLCConfiguration")
        
        # 添加基本信息
        info = ET.SubElement(root, "Info")
        ET.SubElement(info, "Timestamp").text = config_data.get('timestamp', '')
        ET.SubElement(info, "Version").text = config_data.get('version', '')
        
        # 添加模块信息
        modules_elem = ET.SubElement(root, "Modules")
        for module_data in config_data['modules']:
            module_elem = ET.SubElement(modules_elem, "Module")
            for key, value in module_data.items():
                ET.SubElement(module_elem, key).text = str(value)
        
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    
    def _import_from_json(self, file_path: str) -> Dict[str, Any]:
        """从JSON格式导入"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _import_from_pickle(self, file_path: str) -> Dict[str, Any]:
        """从Pickle格式导入"""
        with open(file_path, 'rb') as f:
            return pickle.load(f)
    
    def _import_from_xml(self, file_path: str) -> Dict[str, Any]:
        """从XML格式导入"""
        import xml.etree.ElementTree as ET
        
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        config_data = {
            'modules': [],
            'system_info': {},
            'statistics': {},
            'timestamp': '',
            'version': ''
        }
        
        # 解析基本信息
        info_elem = root.find('Info')
        if info_elem is not None:
            config_data['timestamp'] = info_elem.findtext('Timestamp', '')
            config_data['version'] = info_elem.findtext('Version', '')
        
        # 解析模块信息
        modules_elem = root.find('Modules')
        if modules_elem is not None:
            for module_elem in modules_elem.findall('Module'):
                module_data = {}
                for child in module_elem:
                    module_data[child.tag] = child.text
                config_data['modules'].append(module_data)
        
        return config_data


class SyncService(QObject):
    """
    同步服务
    负责与现有IODataLoader系统的数据同步
    """
    
    syncCompleted = Signal(str, bool)  # 同步完成 (operation, success)
    
    def __init__(self, cache_service: CacheService = None, parent=None):
        super().__init__(parent)
        self.cache_service = cache_service
    
    def sync_from_io_data_loader(self, site_name: str) -> bool:
        """从IODataLoader同步配置"""
        try:
            if not self.cache_service or not self.cache_service.io_data_loader:
                return False
            
            # 加载IODataLoader中的配置
            io_loader = self.cache_service.io_data_loader
            if hasattr(io_loader, 'load_cached_config_for_site'):
                if io_loader.load_cached_config_for_site(site_name):
                    # 获取配置并转换为新格式
                    plc_config = io_loader.get_current_plc_config()
                    modules = self.cache_service._convert_plc_config_to_modules(plc_config)
                    
                    # 保存到新缓存
                    system_info = io_loader.get_rack_info() if hasattr(io_loader, 'get_rack_info') else {}
                    self.cache_service.save_site_configuration(site_name, modules, system_info)
                    
                    self.syncCompleted.emit("sync_from_io_data_loader", True)
                    return True
            
            return False
            
        except Exception as e:
            print(f"❌ 从IODataLoader同步失败: {e}")
            self.syncCompleted.emit("sync_from_io_data_loader", False)
            return False
    
    def sync_to_io_data_loader(self, site_name: str) -> bool:
        """同步配置到IODataLoader"""
        try:
            if not self.cache_service:
                return False
            
            # 从缓存加载配置
            config_data = self.cache_service.load_site_configuration(site_name)
            if not config_data:
                return False
            
            # 重建模块列表并同步
            modules = [PLCModule.from_dict(m) for m in config_data['modules']]
            self.cache_service._sync_to_io_data_loader(site_name, modules)
            
            self.syncCompleted.emit("sync_to_io_data_loader", True)
            return True
            
        except Exception as e:
            print(f"❌ 同步到IODataLoader失败: {e}")
            self.syncCompleted.emit("sync_to_io_data_loader", False)
            return False 