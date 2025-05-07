"""PLC 管理器模块

负责协调PLC相关的操作，作为UI层和服务层之间的桥梁。
"""
import logging
from typing import List, Optional

# 服务层
from core.services.plc_management_service import PLCManagementService
# 数据模型 (PLCManager 应该返回这些模型给UI层)
from core.models.plc.models import PLCSeriesModel, PLCModuleModel

logger = logging.getLogger(__name__)

class PLCManager:
    """PLC 管理器类"""

    def __init__(self):
        """初始化 PLCManager，并实例化 PLCManagementService。"""
        try:
            self.service = PLCManagementService()
            logger.info("PLCManager 初始化完成，已连接 PLCManagementService")
        except Exception as e:
            logger.error(f"PLCManager 初始化失败: {e}", exc_info=True)
            # 根据应用的错误处理策略，可能需要再次抛出异常
            # 或者让 service 属性为 None，并在后续方法中检查
            self.service = None 
            raise # 倾向于在初始化失败时直接抛出

    def get_all_series(self) -> List[PLCSeriesModel]:
        """获取所有PLC系列。"""
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法获取系列。")
            return []
        try:
            return self.service.get_all_series()
        except Exception as e:
            logger.error(f"PLCManager 获取所有系列失败: {e}", exc_info=True)
            return []

    def add_series(self, name: str, description: Optional[str] = None) -> Optional[PLCSeriesModel]:
        """添加一个新的PLC系列。

        参数:
            name (str): 系列名称。
            description (Optional[str]): 系列描述。

        返回:
            Optional[PLCSeriesModel]: 成功则返回新创建的系列模型，否则返回 None。
                                      如果名称已存在，会引发 ValueError。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法添加系列。")
            return None # 或者可以引发异常
        try:
            return self.service.add_series(name, description)
        except ValueError as ve: # 名称已存在等校验错误
            logger.warning(f"PLCManager 添加系列失败: {ve}")
            raise # 将服务层抛出的 ValueError 继续向上抛给UI层处理
        except Exception as e:
            logger.error(f"PLCManager 添加系列 '{name}' 失败: {e}", exc_info=True)
            return None # 对于其他未知异常，可以选择返回None或也向上抛

    def delete_series(self, series_id: int) -> bool:
        """删除一个PLC系列及其下所有模块。

        参数:
            series_id (int): 要删除的系列ID。

        返回:
            bool: 成功返回 True，失败返回 False。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法删除系列。")
            return False
        try:
            return self.service.delete_series(series_id)
        except Exception as e:
            logger.error(f"PLCManager 删除系列 ID {series_id} 失败: {e}", exc_info=True)
            return False

    def get_modules_by_series(self, series_id: int) -> List[PLCModuleModel]:
        """获取指定系列下的所有模块。

        参数:
            series_id (int): 系列ID。

        返回:
            List[PLCModuleModel]: 模块模型列表。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法获取模块。")
            return []
        try:
            # 注意：这里的方法名和服务层一致 get_modules_by_series_id
            return self.service.get_modules_by_series_id(series_id)
        except Exception as e:
            logger.error(f"PLCManager 获取系列 {series_id} 的模块失败: {e}", exc_info=True)
            return []

    def get_modules_by_series_and_type(self, series_id: int, module_type: str) -> List[PLCModuleModel]:
        """获取指定系列和类型的模块列表。

        参数:
            series_id (int): 系列ID。
            module_type (str): 模块类型 (例如 'AI', 'DI', 'CPU')。

        返回:
            List[PLCModuleModel]: 模块模型列表。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法按类型获取模块。")
            return []
        try:
            return self.service.get_modules_by_series_and_type(series_id, module_type)
        except Exception as e:
            logger.error(f"PLCManager 获取系列 {series_id} 类型 '{module_type}' 的模块失败: {e}", exc_info=True)
            return []

    def add_module_to_series(self, series_id: int, model: str, module_type: str, 
                             channels: int = 0, description: Optional[str] = None) -> Optional[PLCModuleModel]:
        """向指定系列添加一个新模块。

        参数:
            series_id (int): 所属系列ID。
            model (str): 模块型号。
            module_type (str): 模块类型。
            channels (int): 通道数。
            description (Optional[str]): 模块描述。

        返回:
            Optional[PLCModuleModel]: 成功则返回新创建的模块模型，否则返回 None。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法添加模块。")
            return None
        try:
            return self.service.add_module(series_id, model, module_type, channels, description)
        except Exception as e: # 可以更细致地捕获服务层可能抛出的特定异常
            logger.error(f"PLCManager 添加模块 '{model}' 到系列 {series_id} 失败: {e}", exc_info=True)
            return None
            
    def get_module_details(self, series_id: int, model: str) -> Optional[PLCModuleModel]:
        """获取特定模块的详细信息。

        参数:
            series_id (int): 系列ID。
            model (str): 模块型号。
        
        返回:
            Optional[PLCModuleModel]: 模块模型对象或 None。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法获取模块详情。")
            return None
        try:
            return self.service.get_module_info(series_id, model)
        except Exception as e:
            logger.error(f"PLCManager 获取模块 {series_id} - {model} 详情失败: {e}", exc_info=True)
            return None

    def delete_module_from_series(self, series_id: int, model: str) -> bool:
        """从指定系列中删除一个模块。

        参数:
            series_id (int): 系列ID。
            model (str): 要删除的模块型号。

        返回:
            bool: 成功返回 True，失败返回 False。
        """
        if not self.service:
            logger.error("PLCManagementService 未初始化，无法删除模块。")
            return False
        try:
            return self.service.delete_module(series_id, model)
        except Exception as e:
            logger.error(f"PLCManager 删除模块 '{model}' 从系列 {series_id} 失败: {e}", exc_info=True)
            return False

    # 如果有与 PLCBackplaneModel 相关的逻辑，也可以在这里添加相应的方法
    # 例如:
    # def get_all_backplanes(self) -> List[PLCBackplaneModel]: ...
    # def add_backplane(self, model: str, slots: int, ...) -> Optional[PLCBackplaneModel]: ...

    # 可能还需要一些辅助方法，例如根据系列名称获取系列ID等，
    # 不过这些通常应该由服务层提供，或者UI层自己管理从 get_all_series 获取到的数据。 