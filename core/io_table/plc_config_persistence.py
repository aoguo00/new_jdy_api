# -*- coding: utf-8 -*-
"""
PLC配置持久化存储模块

用于将每个场站的PLC配置保存到文件，支持：
- 每个场站独立的配置文件
- JSON格式存储
- 自动备份
- 配置恢复
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import shutil

logger = logging.getLogger(__name__)


class PLCConfigPersistence:
    """
    PLC配置持久化存储管理器
    
    将每个场站的PLC配置保存到独立的JSON文件中，
    确保场站间的配置相互独立，支持配置的保存、加载、备份等操作。
    """
    
    def __init__(self, config_dir: str = None):
        """
        初始化持久化管理器
        
        Args:
            config_dir: 配置文件存储目录，默认为db文件夹下的plc_configs文件夹
        """
        # 设置配置文件存储目录
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # 默认存储在db目录下的plc_configs文件夹
            project_root = Path(__file__).parent.parent.parent
            self.config_dir = project_root / "db" / "plc_configs"
        
        # 确保目录存在
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份目录
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"PLCConfigPersistence 初始化完成，配置目录: {self.config_dir}")
    
    def _get_config_filename(self, site_name: str) -> Path:
        """
        获取场站配置文件名
        
        Args:
            site_name: 场站名称
            
        Returns:
            配置文件路径
        """
        # 清理文件名中的非法字符
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in site_name)
        safe_name = safe_name.strip()
        
        return self.config_dir / f"plc_config_{safe_name}.json"
    
    def save_site_config(self, site_name: str, config_data: Dict[str, Any]) -> bool:
        """
        保存场站配置
        
        Args:
            site_name: 场站名称
            config_data: 配置数据，包含：
                - config: PLC模块配置 {(rack_id, slot_id): model_name}
                - system_info: 系统信息
                - processed_devices: 处理后的设备数据
                - addresses: 地址列表
                - io_count: IO通道数
                - rack_configurations: 新增 - 每个机架的独立配置
                
        Returns:
            是否保存成功
        """
        try:
            config_file = self._get_config_filename(site_name)
            
            # 转换配置格式（将tuple键转换为字符串）
            save_data = {
                "site_name": site_name,
                "save_time": datetime.now().isoformat(),
                "version": "1.1",  # 升级版本号以区分新格式
                "config": {},
                "system_info": config_data.get("system_info", {}),
                "io_count": config_data.get("io_count", 0),
                "addresses_count": len(config_data.get("addresses", [])),
                "processed_devices_count": len(config_data.get("processed_devices", []))
            }
            
            # 转换配置字典的键格式
            raw_config = config_data.get("config", {})
            for (rack_id, slot_id), model_name in raw_config.items():
                key = f"{rack_id},{slot_id}"
                save_data["config"][key] = model_name
            
            # 新增：保存机架独立配置（如果存在）
            if "rack_configurations" in config_data:
                rack_configs = {}
                for rack_id, modules in config_data["rack_configurations"].items():
                    # 将模块列表转换为可序列化的格式
                    serializable_modules = []
                    for module in modules:
                        module_data = {
                            "key": module.key if hasattr(module, 'key') else str(module),
                            "title": module.title if hasattr(module, 'title') else str(module),
                            "model": module.model if hasattr(module, 'model') else module.title if hasattr(module, 'title') else str(module),
                            "module_type": module.module_type if hasattr(module, 'module_type') else "未知",
                            "channels": module.channels if hasattr(module, 'channels') else 0,
                            "description": module.description if hasattr(module, 'description') else "",
                            "is_fixed": "🔒" in (module.title if hasattr(module, 'title') else "")
                        }
                        serializable_modules.append(module_data)
                    rack_configs[str(rack_id)] = serializable_modules
                save_data["rack_configurations"] = rack_configs
                logger.info(f"保存机架配置: {len(rack_configs)} 个机架")
            
            # 备份现有文件（如果存在）
            if config_file.exists():
                self._backup_config(site_name, config_file)
            
            # 保存新配置
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功保存场站 '{site_name}' 的PLC配置到: {config_file}")
            logger.info(f"  - 模块数: {len(save_data['config'])}")
            logger.info(f"  - IO通道数: {save_data['io_count']}")
            logger.info(f"  - 地址数: {save_data['addresses_count']}")
            if "rack_configurations" in save_data:
                logger.info(f"  - 机架配置: {len(save_data['rack_configurations'])} 个机架")
            
            # 同时保存完整数据（用于恢复）
            full_data_file = config_file.with_suffix('.full.json')
            with open(full_data_file, 'w', encoding='utf-8') as f:
                # 创建可序列化的完整数据副本
                full_save_data = save_data.copy()
                full_save_data["addresses"] = config_data.get("addresses", [])
                full_save_data["processed_devices"] = config_data.get("processed_devices", [])
                json.dump(full_save_data, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"保存场站 '{site_name}' 配置失败: {e}", exc_info=True)
            return False
    
    def load_site_config(self, site_name: str) -> Optional[Dict[str, Any]]:
        """
        加载场站配置
        
        Args:
            site_name: 场站名称
            
        Returns:
            配置数据或None
        """
        try:
            config_file = self._get_config_filename(site_name)
            
            if not config_file.exists():
                logger.info(f"场站 '{site_name}' 没有保存的配置文件")
                return None
            
            # 优先加载完整数据
            full_data_file = config_file.with_suffix('.full.json')
            if full_data_file.exists():
                with open(full_data_file, 'r', encoding='utf-8') as f:
                    full_data = json.load(f)
                
                # 转换配置键格式（从字符串转回tuple）
                config_dict = {}
                for key_str, model_name in full_data.get("config", {}).items():
                    try:
                        rack_id, slot_id = map(int, key_str.split(','))
                        config_dict[(rack_id, slot_id)] = model_name
                    except:
                        logger.warning(f"跳过无效的配置键: {key_str}")
                        continue
                
                # 构建返回数据
                result = {
                    "config": config_dict,
                    "system_info": full_data.get("system_info", {}),
                    "addresses": full_data.get("addresses", []),
                    "processed_devices": full_data.get("processed_devices", []),
                    "io_count": full_data.get("io_count", 0)
                }
                
                # 新增：加载机架配置（如果存在）
                if "rack_configurations" in full_data:
                    rack_configs = {}
                    for rack_id_str, modules_data in full_data["rack_configurations"].items():
                        rack_id = int(rack_id_str)
                        rack_configs[rack_id] = modules_data  # 保存原始数据，稍后在UI层重建对象
                    result["rack_configurations"] = rack_configs
                    logger.info(f"加载机架配置: {len(rack_configs)} 个机架")
                
                return result
            
            # 如果没有完整数据，加载基本配置
            with open(config_file, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            # 转换配置键格式
            config_dict = {}
            for key_str, model_name in save_data.get("config", {}).items():
                try:
                    rack_id, slot_id = map(int, key_str.split(','))
                    config_dict[(rack_id, slot_id)] = model_name
                except:
                    logger.warning(f"跳过无效的配置键: {key_str}")
                    continue
            
            logger.info(f"成功加载场站 '{site_name}' 的PLC配置")
            logger.info(f"  - 保存时间: {save_data.get('save_time', '未知')}")
            logger.info(f"  - 模块数: {len(config_dict)}")
            logger.info(f"  - IO通道数: {save_data.get('io_count', 0)}")
            
            result = {
                "config": config_dict,
                "system_info": save_data.get("system_info", {}),
                "addresses": [],  # 基本配置不包含地址列表
                "processed_devices": [],  # 基本配置不包含设备列表
                "io_count": save_data.get("io_count", 0)
            }
            
            # 新增：从基本配置加载机架配置（如果存在）
            if "rack_configurations" in save_data:
                rack_configs = {}
                for rack_id_str, modules_data in save_data["rack_configurations"].items():
                    rack_id = int(rack_id_str)
                    rack_configs[rack_id] = modules_data
                result["rack_configurations"] = rack_configs
                logger.info(f"从基本配置加载机架配置: {len(rack_configs)} 个机架")
            
            return result
            
        except Exception as e:
            logger.error(f"加载场站 '{site_name}' 配置失败: {e}", exc_info=True)
            return None
    
    def has_site_config(self, site_name: str) -> bool:
        """
        检查场站是否有保存的配置
        
        Args:
            site_name: 场站名称
            
        Returns:
            是否存在配置文件
        """
        config_file = self._get_config_filename(site_name)
        return config_file.exists()
    
    def delete_site_config(self, site_name: str) -> bool:
        """
        删除指定场站的所有配置文件
        
        Args:
            site_name: 场站名称
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 使用_get_config_filename方法获取正确的文件路径
            config_file = self._get_config_filename(site_name)
            full_config_file = config_file.with_suffix('.full.json')
            
            deleted_files = []
            
            # 删除主配置文件
            if config_file.exists():
                config_file.unlink()
                deleted_files.append(str(config_file))
                logger.info(f"已删除配置文件: {config_file}")
            
            # 删除完整备份文件
            if full_config_file.exists():
                full_config_file.unlink()
                deleted_files.append(str(full_config_file))
                logger.info(f"已删除完整备份文件: {full_config_file}")
            
            # 清理备份目录中相关的备份文件
            backup_dir = self.backup_dir
            if backup_dir.exists():
                # 获取安全的文件名用于匹配备份
                safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in site_name).strip()
                backup_pattern = f"plc_config_{safe_name}_*.json"
                deleted_backups = []
                
                for backup_file in backup_dir.glob(backup_pattern):
                    backup_file.unlink()
                    deleted_backups.append(backup_file.name)
                
                if deleted_backups:
                    logger.info(f"已删除 {len(deleted_backups)} 个备份文件: {deleted_backups}")
            
            if deleted_files:
                logger.info(f"成功删除场站 '{site_name}' 的所有配置文件")
                return True
            else:
                logger.info(f"场站 '{site_name}' 没有找到配置文件，无需删除")
                return True
                
        except Exception as e:
            logger.error(f"删除场站 '{site_name}' 配置文件失败: {e}", exc_info=True)
            return False
    
    def list_saved_sites(self) -> List[str]:
        """
        列出所有已保存配置的场站
        
        Returns:
            场站名称列表
        """
        sites = []
        
        try:
            for config_file in self.config_dir.glob("plc_config_*.json"):
                if not config_file.name.endswith('.full.json'):
                    # 从文件名提取场站名
                    name = config_file.stem.replace("plc_config_", "")
                    sites.append(name)
            
            logger.info(f"找到 {len(sites)} 个已保存配置的场站")
            return sorted(sites)
            
        except Exception as e:
            logger.error(f"列出保存的场站失败: {e}", exc_info=True)
            return []
    
    def _backup_config(self, site_name: str, config_file: Path):
        """
        备份配置文件
        
        Args:
            site_name: 场站名称
            config_file: 配置文件路径
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{config_file.stem}_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_name
            
            shutil.copy2(config_file, backup_path)
            logger.info(f"已备份配置文件到: {backup_path}")
            
            # 保留最近10个备份
            self._cleanup_old_backups(site_name)
            
        except Exception as e:
            logger.error(f"备份配置文件失败: {e}", exc_info=True)
    
    def _cleanup_old_backups(self, site_name: str, keep_count: int = 10):
        """
        清理旧备份文件
        
        Args:
            site_name: 场站名称
            keep_count: 保留的备份数量
        """
        try:
            pattern = f"plc_config_{site_name}_backup_*.json"
            backups = sorted(self.backup_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
            
            # 删除多余的备份
            for backup in backups[keep_count:]:
                backup.unlink()
                logger.debug(f"删除旧备份: {backup}")
                
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}", exc_info=True)
    
    def export_all_configs(self, export_path: str) -> bool:
        """
        导出所有场站配置
        
        Args:
            export_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            all_configs = {}
            
            for site_name in self.list_saved_sites():
                config_data = self.load_site_config(site_name)
                if config_data:
                    # 简化配置数据，只保留关键信息
                    all_configs[site_name] = {
                        "config": {f"{k[0]},{k[1]}": v for k, v in config_data["config"].items()},
                        "system_info": config_data.get("system_info", {}),
                        "io_count": config_data.get("io_count", 0)
                    }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "export_time": datetime.now().isoformat(),
                    "version": "1.0",
                    "site_count": len(all_configs),
                    "sites": all_configs
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功导出 {len(all_configs)} 个场站配置到: {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"导出配置失败: {e}", exc_info=True)
            return False 