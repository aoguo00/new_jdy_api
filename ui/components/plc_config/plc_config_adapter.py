# -*- coding: utf-8 -*-
"""
PLC配置适配器

将新的AdvancedTransferWidget适配为旧版PLCConfigEmbeddedWidget接口，
确保与现有主窗口代码的无缝兼容。
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QMessageBox
from PySide6.QtCore import Qt, Signal

# 尝试相对导入，失败则使用绝对导入
try:
    from .models import PLCModule, TransferDirection
    from .enhanced_transfer_widget import EnhancedTransferWidget
    from .plc_config_widget import PLCConfigWidget, SystemInfoWidget, RackDisplayWidget
except ImportError:
    # 当直接运行文件或包结构有问题时，使用绝对导入
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent.parent
    sys.path.insert(0, str(project_root))
    
    from ui.components.plc_config.models import PLCModule, TransferDirection
    from ui.components.plc_config.enhanced_transfer_widget import EnhancedTransferWidget
    from ui.components.plc_config.plc_config_widget import PLCConfigWidget, SystemInfoWidget, RackDisplayWidget

logger = logging.getLogger(__name__)


class PLCConfigAdapter(QWidget):
    """
    PLC配置适配器类
    
    这个类作为新旧系统之间的桥梁，提供旧版PLCConfigEmbeddedWidget的接口，
    但内部使用新的现代化组件实现。保持向后兼容性的同时提供新功能。
    """
    
    # 兼容旧版信号 (如果原版有的话)
    configuration_applied = Signal(bool)  # 配置应用信号
    configuration_reset = Signal()        # 配置重置信号
    
    def __init__(self, io_data_loader, devices_data: List[Dict[str, Any]] = None, parent=None):
        """
        初始化适配器
        
        Args:
            io_data_loader: IODataLoader实例
            devices_data: 初始设备数据 (可选)
            parent: 父组件
        """
        super().__init__(parent)
        
        # 验证必需的参数
        if not io_data_loader:
            logger.error("PLCConfigAdapter 初始化错误: IODataLoader 实例未提供")
            self._show_error_ui("IO数据服务不可用，PLC配置功能无法加载")
            return
        
        self.io_data_loader = io_data_loader
        self._setup_ui()
        self._connect_signals()
        
        # 设置初始数据
        if devices_data is not None:
            logger.info(f"PLCConfigAdapter: 收到初始设备数据 {len(devices_data)} 项")
            self.set_devices_data(devices_data)
        else:
            logger.info("PLCConfigAdapter: 未提供初始设备数据，使用空状态初始化")
            self._initialize_empty_state()
    
    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建现代化PLC配置组件
        self.modern_widget = PLCConfigWidget(
            io_data_loader=self.io_data_loader,
            parent=self
        )
        
        layout.addWidget(self.modern_widget)
        
        # 设置最小尺寸 (兼容旧版)
        self.setMinimumSize(1000, 600)
        
        logger.info("PLCConfigAdapter: UI设置完成")
    
    def _show_error_ui(self, error_message: str):
        """显示错误UI"""
        from PySide6.QtWidgets import QLabel
        
        layout = QVBoxLayout(self)
        error_label = QLabel(error_message)
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        layout.addWidget(error_label)
        
        # 标记为错误状态
        self.io_data_loader = None
        self.modern_widget = None
    
    def _connect_signals(self):
        """连接信号"""
        if not hasattr(self, 'modern_widget') or not self.modern_widget:
            return
        
        # 连接现代组件的信号到适配器信号
        self.modern_widget.configurationApplied.connect(self.configuration_applied.emit)
        self.modern_widget.configurationReset.connect(self.configuration_reset.emit)
        
        logger.debug("PLCConfigAdapter: 信号连接完成")
    
    def _initialize_empty_state(self):
        """初始化空状态"""
        if not hasattr(self, 'modern_widget') or not self.modern_widget:
            return
        
        # 显示空状态提示
        self.modern_widget.show_empty_state("请先选择一个项目/场站")
        
        logger.info("PLCConfigAdapter: 空状态初始化完成")
    
    # ========== 兼容旧版接口的方法 ==========
    
    def set_devices_data(self, devices_data: List[Dict[str, Any]]):
        """
        设置设备数据 (兼容旧版接口)
        
        Args:
            devices_data: 设备数据列表
        """
        if not self.io_data_loader or not hasattr(self, 'modern_widget') or not self.modern_widget:
            logger.error("PLCConfigAdapter.set_devices_data: 组件未正确初始化")
            return
        
        logger.info(f"PLCConfigAdapter.set_devices_data: 处理 {len(devices_data)} 个设备")
        
        try:
            # 首先检查缓存
            current_site = getattr(self.io_data_loader, 'current_site_name', None)
            has_cache = current_site and self.io_data_loader.has_cached_config_for_site(current_site)
            
            if has_cache:
                logger.info(f"发现场站 '{current_site}' 有缓存配置，将从缓存恢复配置")
                
                # 从缓存加载配置（不使用force_update，避免清除配置）
                if self.io_data_loader.load_cached_config_for_site(current_site):
                    logger.info(f"成功从缓存恢复场站 '{current_site}' 的配置")
                    
                    # 更新设备数据但不清除配置（使用force_update=False）
                    self.io_data_loader.set_devices_data(devices_data, force_update=False)
                    
                    # 转换最新API数据为模块格式（用于更新可用模块列表）
                    transfer_items = self._convert_devices_to_transfer_items(devices_data)
                    
                    # 更新现代组件的数据源（可用模块列表）
                    self.modern_widget.set_data_source(transfer_items)
                    
                    # 恢复缓存的配置到UI
                    if self._restore_from_cache():
                        logger.info(f"成功恢复场站 '{current_site}' 的完整配置")
                        return
                    else:
                        logger.warning("缓存恢复UI配置失败，将重新处理设备数据")
                else:
                    logger.warning("缓存加载失败，将重新处理设备数据")
            
            # 没有缓存或缓存恢复失败，正常处理设备数据
            logger.info("没有缓存或缓存恢复失败，正常处理设备数据")
            self._process_devices_data(devices_data)
            
        except Exception as e:
            logger.error(f"PLCConfigAdapter.set_devices_data 处理失败: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"处理设备数据失败: {str(e)}")
    
    def _process_devices_data(self, devices_data: List[Dict[str, Any]]):
        """处理设备数据的核心逻辑"""
        # 1. 更新IODataLoader - 强制更新，因为这是来自API的新数据
        self.io_data_loader.set_devices_data(devices_data, force_update=True)
        
        # 2. 转换数据格式
        transfer_items = self._convert_devices_to_transfer_items(devices_data)
        
        # 3. 更新现代组件
        self.modern_widget.set_data_source(transfer_items)
        
        # 4. 从IODataLoader恢复已有配置
        self._restore_existing_config()
        
        logger.info("PLCConfigAdapter: 设备数据处理完成")
    
    def _convert_devices_to_transfer_items(self, devices_data: List[Dict[str, Any]]) -> List[PLCModule]:
        """
        将旧版设备数据转换为TransferItem格式
        
        Args:
            devices_data: 原始设备数据
            
        Returns:
            转换后的PLCModule列表
        """
        transfer_items = []
        
        # 从IODataLoader获取可用模块
        available_modules, has_data = self.io_data_loader.load_available_modules('全部')
        
        if not has_data:
            logger.warning("没有可用的模块数据")
            return transfer_items
        
        # 为每个模块型号维护一个计数器，确保同型号模块有唯一但确定的ID
        model_counters = {}
        
        # 转换格式
        for module in available_modules:
            try:
                model = module.get('model', '未知模块')
                module_type = module.get('type', module.get('io_type', '未知'))
                
                # 生成确定性的unique_id：基于模型名称和序号
                if model not in model_counters:
                    model_counters[model] = 0
                model_counters[model] += 1
                
                # 确定性ID格式：模型名_序号，例如：LK411_1, LK411_2
                unique_id = f"{model}_{model_counters[model]}"
                
                plc_module = PLCModule(
                    key=unique_id,
                    title=model,
                    description=self._build_module_description(module),
                    model=model,
                    module_type=module_type,
                    manufacturer=module.get('manufacturer', '和利时'),
                    channels=module.get('channels', 0),
                    icon=self._get_module_icon(module_type),
                    unique_id=unique_id
                )
                
                transfer_items.append(plc_module)
                
            except Exception as e:
                logger.error(f"转换模块数据失败 {module}: {e}")
                continue
        
        logger.info(f"成功转换 {len(transfer_items)} 个模块为TransferItem格式")
        logger.debug(f"生成的模块ID: {[item.key for item in transfer_items[:5]]}")  # 调试：显示前5个ID
        return transfer_items
    
    def _build_module_description(self, module: Dict[str, Any]) -> str:
        """构建模块描述"""
        model = module.get('model', '未知')
        type_str = module.get('type', module.get('io_type', '未知'))
        channels = module.get('channels', 0)
        
        if channels > 0:
            return f"{model} - {type_str} ({channels}通道)"
        else:
            return f"{model} - {type_str}"
    
    def _get_module_icon(self, module_type: str) -> str:
        """根据模块类型获取图标"""
        icon_map = {
            'CPU': '🖥️',
            'DI': '📥',
            'DO': '📤',
            'AI': '📊',
            'AO': '📈',
            'DI/DO': '🔄',
            'AI/AO': '⚡',
            'COM': '🌐',
            'DP': '🔗',
            'COMM': '🌐'
        }
        return icon_map.get(module_type.upper(), '🔧')
    
    def _restore_existing_config(self):
        """从IODataLoader恢复已有配置"""
        try:
            current_config = self.io_data_loader.get_current_plc_config()
            
            if current_config:
                # 转换配置格式并应用到现代组件
                self._apply_config_to_modern_widget(current_config)
                logger.info(f"恢复了 {len(current_config)} 个模块配置")
            else:
                logger.info("没有现有配置需要恢复")
                
        except Exception as e:
            logger.error(f"恢复配置失败: {e}", exc_info=True)
    
    def _apply_config_to_modern_widget(self, config: Dict[Tuple[int, int], str]):
        """将配置应用到现代组件"""
        if not hasattr(self, 'modern_widget') or not self.modern_widget:
            return
        
        try:
            # 获取系统类型
            rack_info = self.io_data_loader.get_rack_info()
            system_type = rack_info.get('system_type', 'LK')
            
            # 过滤掉系统自动配置的模块，只恢复用户配置的模块
            user_configured_modules = []
            
            for (rack_id, slot_id), model_name in config.items():
                # 跳过系统自动配置的模块
                if system_type == 'LE_CPU' and slot_id == 0:
                    # LE_CPU系统的槽位0是自动配置的LE5118 CPU，跳过
                    logger.debug(f"跳过LE_CPU系统自动配置的槽位0: {model_name}")
                    continue
                elif system_type == 'LK' and slot_id == 1:
                    # LK系统的槽位1是自动配置的PROFIBUS-DP，跳过
                    logger.debug(f"跳过LK系统自动配置的槽位1: {model_name}")
                    continue
                
                # 这是用户配置的模块，需要恢复到穿梭框右侧
                user_configured_modules.append((rack_id, slot_id, model_name))
            
            if user_configured_modules:
                logger.info(f"恢复 {len(user_configured_modules)} 个用户配置的模块到UI")
                # 这里需要现代组件支持配置恢复的接口
                # 暂时记录，等现代组件实现后再补充具体的恢复逻辑
                # 可以通过模拟穿梭框操作来恢复配置
                self._restore_modules_to_transfer_widget(user_configured_modules)
            else:
                logger.info("没有用户配置的模块需要恢复")
                
        except Exception as e:
            logger.error(f"应用配置到现代组件失败: {e}", exc_info=True)
    
    def _restore_modules_to_transfer_widget(self, modules: List[Tuple[int, int, str]]):
        """将模块恢复到穿梭框右侧 - 简化直接匹配版本"""
        try:
            if not hasattr(self.modern_widget, 'transfer_widget'):
                logger.warning("现代组件没有transfer_widget属性")
                return
            
            transfer_widget = self.modern_widget.transfer_widget
            left_items = transfer_widget.get_left_items()
            
            logger.info(f"开始恢复模块配置:")
            logger.info(f"  - 缓存配置: {len(modules)} 个模块")
            logger.info(f"  - 可用模块: {len(left_items)} 个")
            
            # 打印缓存配置详情
            config_models = [model_name for _, _, model_name in modules]
            logger.info(f"  - 缓存配置详情: {config_models}")
            
            # 打印可用模块详情
            available_models = []
            for item in left_items:
                model = getattr(item, 'model', '') or getattr(item, 'title', '')
                available_models.append(f"{model}({item.key})")
            logger.info(f"  - 可用模块详情: {available_models}")
            
            # 简化策略：逐个匹配，一旦匹配成功就移除，避免重复
            modules_to_move = []
            remaining_items = left_items.copy()  # 可用模块的副本
            matched_configs = []
            unmatched_configs = []
            
            for rack_id, slot_id, target_model in modules:
                # 在剩余可用模块中查找匹配的模块
                found_item = None
                for item in remaining_items:
                    item_model = getattr(item, 'model', '') or getattr(item, 'title', '')
                    if item_model == target_model:
                        found_item = item
                        break
                
                if found_item:
                    # 找到匹配项
                    modules_to_move.append(found_item.key)
                    remaining_items.remove(found_item)  # 从可用列表中移除，避免重复匹配
                    matched_configs.append(f"{target_model}@slot_{slot_id}→{found_item.key}")
                    logger.debug(f"✅ 匹配成功: {target_model} → {found_item.key}")
                else:
                    # 未找到匹配项
                    unmatched_configs.append(f"{target_model}@slot_{slot_id}")
                    logger.warning(f"❌ 未找到匹配: {target_model}")
            
            # 输出匹配结果
            logger.info(f"匹配结果统计:")
            logger.info(f"  - 匹配成功: {len(matched_configs)} 个")
            logger.info(f"  - 匹配失败: {len(unmatched_configs)} 个")
            logger.info(f"  - 将移动模块: {modules_to_move}")
            
            if matched_configs:
                logger.info(f"匹配详情: {matched_configs}")
            if unmatched_configs:
                logger.warning(f"未匹配配置: {unmatched_configs}")
            
            # 执行移动操作
            if modules_to_move:
                logger.info(f"执行移动操作: {len(modules_to_move)} 个模块")
                self._move_modules_to_right(transfer_widget, modules_to_move)
                
                # 验证移动结果
                right_items = transfer_widget.get_right_items()
                new_left_items = transfer_widget.get_left_items()
                logger.info(f"移动后状态: 左侧 {len(new_left_items)} 个, 右侧 {len(right_items)} 个")
            else:
                logger.warning("没有可移动的模块")
                
        except Exception as e:
            logger.error(f"恢复模块到穿梭框失败: {e}", exc_info=True)
    
    def _move_modules_to_right(self, transfer_widget, module_keys: List[str]):
        """执行实际的模块移动操作"""
        try:
            # 方法1：通过设置选中状态并调用移动方法
            if hasattr(transfer_widget, '_state') and hasattr(transfer_widget, 'move_to_right'):
                # 设置左侧选中状态
                transfer_widget._state.left_selected = set(module_keys)
                
                # 执行移动到右侧
                transfer_widget.move_to_right()
                
                logger.info(f"成功通过状态管理移动 {len(module_keys)} 个模块到右侧")
                return
            
            # 方法2：通过模拟拖拽操作（备用方案）
            if hasattr(transfer_widget, '_move_items_to_right'):
                transfer_widget._move_items_to_right(module_keys)
                logger.info(f"成功通过拖拽模拟移动 {len(module_keys)} 个模块到右侧")
                return
            
            # 方法3：直接修改内部状态并刷新显示（最后备用方案）
            if hasattr(transfer_widget, '_state') and hasattr(transfer_widget, '_refresh_display'):
                self._direct_move_modules(transfer_widget, module_keys)
                logger.info(f"成功通过直接状态修改移动 {len(module_keys)} 个模块到右侧")
                return
            
            logger.error("无法找到合适的模块移动方法")
            
        except Exception as e:
            logger.error(f"执行模块移动操作失败: {e}", exc_info=True)
    
    def _direct_move_modules(self, transfer_widget, module_keys: List[str]):
        """直接修改状态来移动模块（最后备用方案）"""
        try:
            state = transfer_widget._state
            
            # 找到要移动的模块并从左侧移到右侧
            modules_to_move = []
            for key in module_keys:
                for item in state.left_items:
                    if item.key == key:
                        modules_to_move.append(item)
                        break
            
            # 执行移动
            for item in modules_to_move:
                if item in state.left_items:
                    item.direction = TransferDirection.RIGHT  # 需要导入TransferDirection
                    state.left_items.remove(item)
                    state.right_items.append(item)
            
            # 清除选中状态
            state.left_selected.clear()
            state.right_selected.clear()
            
            # 刷新显示
            transfer_widget._refresh_display()
            
        except Exception as e:
            logger.error(f"直接状态修改失败: {e}", exc_info=True)
    
    def _restore_from_cache(self) -> bool:
        """从缓存恢复配置"""
        try:
            # 获取缓存的系统信息
            rack_info = self.io_data_loader.get_rack_info()
            current_config = self.io_data_loader.get_current_plc_config()
            
            # 更新现代组件
            self.modern_widget.update_system_info(rack_info)
            self._apply_config_to_modern_widget(current_config)
            
            logger.info("成功从缓存恢复配置到现代组件")
            return True
            
        except Exception as e:
            logger.error(f"从缓存恢复配置失败: {e}", exc_info=True)
            return False
    
    def reset_to_initial_state(self):
        """
        重置到初始状态 (兼容旧版接口)
        """
        logger.info("PLCConfigAdapter: 重置到初始状态")
        
        try:
            if hasattr(self, 'modern_widget') and self.modern_widget:
                self.modern_widget.reset_configuration()
            
            if self.io_data_loader and hasattr(self.io_data_loader, 'clear_current_project_configuration'):
                self.io_data_loader.clear_current_project_configuration()
            
            logger.info("PLCConfigAdapter: 成功重置到初始状态")
            
        except Exception as e:
            logger.error(f"PLCConfigAdapter.reset_to_initial_state: 重置失败: {e}", exc_info=True)
    
    def get_current_configuration(self) -> List[Dict[str, Any]]:
        """
        获取当前配置 (兼容旧版接口)
        
        Returns:
            当前配置列表
        """
        if not hasattr(self, 'modern_widget') or not self.modern_widget:
            return []
        
        try:
            # 从现代组件获取配置
            config_data = self.modern_widget.get_current_configuration()
            logger.info(f"获取当前配置: {len(config_data)} 项")
            return config_data
            
        except Exception as e:
            logger.error(f"获取当前配置失败: {e}", exc_info=True)
            return []
    
    def apply_configuration(self) -> bool:
        """
        应用配置 (兼容旧版接口)
        
        Returns:
            应用是否成功
        """
        if not hasattr(self, 'modern_widget') or not self.modern_widget:
            logger.error("PLCConfigAdapter.apply_configuration: 现代组件未初始化")
            return False
        
        try:
            # 调用现代组件的应用配置方法
            success = self.modern_widget.apply_configuration()
            
            if success:
                logger.info("PLCConfigAdapter: 配置应用成功")
                self.configuration_applied.emit(True)
            else:
                logger.warning("PLCConfigAdapter: 配置应用失败")
                self.configuration_applied.emit(False)
            
            return success
            
        except Exception as e:
            logger.error(f"PLCConfigAdapter.apply_configuration: 应用配置失败: {e}", exc_info=True)
            self.configuration_applied.emit(False)
            return False
    
    # ========== 新增的便利方法 ==========
    
    def get_modern_widget(self) -> Optional[PLCConfigWidget]:
        """
        获取内部的现代化组件实例
        
        Returns:
            PLCConfigWidget实例或None
        """
        return getattr(self, 'modern_widget', None)
    
    def is_valid(self) -> bool:
        """
        检查适配器是否处于有效状态
        
        Returns:
            是否有效
        """
        return (
            self.io_data_loader is not None and
            hasattr(self, 'modern_widget') and 
            self.modern_widget is not None
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取配置统计信息
        
        Returns:
            统计信息字典
        """
        if not self.is_valid():
            return {'error': 'Adapter not valid'}
        
        try:
            # 从现代组件获取统计
            return self.modern_widget.get_statistics()
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            return {'error': str(e)} 