# PLC配置缓存功能说明

## 功能概述

本次更新为PLC硬件配置界面增加了场站配置缓存功能。当用户为某个场站配置好PLC模块并点击"应用配置"后，系统会自动将该场站的配置保存到内存缓存中。当用户再次切换到该场站时，系统会自动从缓存中加载之前的配置，无需重新请求API数据或重新配置。

## 实现细节

### 1. 缓存结构

在 `IODataLoader` 类中新增了缓存相关的属性和方法：

```python
# 场站配置缓存，格式为 {site_name: {
#     'config': {(rack_id, slot_id): model_name},
#     'processed_devices': List[Dict[str, Any]], 
#     'system_info': Dict[str, Any],
#     'addresses': List[Dict[str, Any]],
#     'io_count': int
# }}
self.site_config_cache: Dict[str, Dict[str, Any]] = {}

# 当前场站名称
self.current_site_name: Optional[str] = None
```

### 2. 新增方法

#### IODataLoader 类新增方法：

- `set_current_site(site_name: str)`: 设置当前场站名称
- `has_cached_config_for_site(site_name: str) -> bool`: 检查指定场站是否有缓存配置
- `load_cached_config_for_site(site_name: str) -> bool`: 从缓存加载指定场站的配置
- `save_current_config_to_cache() -> bool`: 将当前配置保存到缓存

#### PLCConfigEmbeddedWidget 类新增方法：

- `_restore_config_from_cache()`: 从IODataLoader的缓存恢复配置到UI

### 3. 工作流程

1. **场站切换时**：
   - 主窗口调用 `_handle_project_selected` 方法
   - 设置IODataLoader的当前场站名称
   - PLCConfigEmbeddedWidget 的 `set_devices_data` 方法检查是否有缓存
   - 如果有缓存，调用 `load_cached_config_for_site` 加载缓存，跳过设备数据处理
   - 如果没有缓存，正常处理设备数据

2. **应用配置时**：
   - 用户点击"应用配置"按钮
   - IODataLoader 的 `save_configuration` 方法保存配置
   - 自动调用 `save_current_config_to_cache` 将配置保存到缓存

3. **清空项目时**：
   - 调用 `clear_current_project_configuration` 方法
   - 清空所有场站的配置缓存

## 使用效果

1. **首次配置**：用户选择场站后，需要手动配置PLC模块，点击"应用配置"保存
2. **再次访问**：切换到其他场站后再切回来，之前的配置会自动恢复，无需重新配置
3. **数据一致性**：缓存包含完整的配置信息，包括模块配置、系统类型、机架信息等

## 注意事项

1. 缓存数据仅保存在内存中，程序重启后会丢失
2. 如果场站的设备数据发生变化，需要手动清除缓存或重新配置
3. 缓存包含完整的配置信息，包括模块配置、IO地址和系统信息

## 模块过滤改进（2024年更新）

### 问题描述
之前的实现中，当选择场站后，穿梭框会显示模块库中的所有模块，而不是只显示场站实际拥有的模块。这是因为系统对所有模块都应用了严格的类型过滤（只允许 AI、AO、DI、DO、DI/DO、AI/AO、COM 类型）。

### 解决方案
1. 新增了 `FILTER_SITE_MODULES_BY_TYPE` 配置项（默认为 `False`）
2. 当使用场站设备数据作为模块源时：
   - 只排除特殊类型的模块（RACK、CPU、DP）
   - 不再严格按照 `ALLOWED_MODULE_TYPES` 过滤
   - 这样可以显示场站中所有实际存在的模块（包括未录入类型的模块）

### 效果
- 选择场站后，穿梭框左侧只显示该场站实际拥有的模块
- 支持显示各种类型的模块，不仅限于标准的 IO 模块
- 特殊模块（如 RACK、CPU、DP）仍然被正确排除，因为它们有特殊的配置规则

## 后续优化建议

1. 可以考虑将缓存持久化到本地文件或数据库
2. 添加缓存过期机制，定期清理旧的缓存数据
3. 提供手动清除指定场站缓存的功能
4. 添加缓存状态的可视化显示，让用户知道当前使用的是缓存数据还是最新数据

## 代码修改摘要

### IODataLoader (core/io_table/get_data.py)
- 新增缓存相关属性：`site_config_cache`, `current_site_name`
- 新增方法：`set_current_site`, `has_cached_config_for_site`, `load_cached_config_for_site`, `save_current_config_to_cache`
- 修改 `save_configuration` 方法：自动保存配置到缓存
- 修改 `clear_current_project_configuration` 方法：清空缓存

### PLCConfigEmbeddedWidget (ui/dialogs/plc_config_dialog.py)
- 新增方法：`_restore_config_from_cache`
- 修改 `set_devices_data` 方法：优先检查缓存，如有缓存则直接恢复

### MainWindow (ui/main_window.py)
- 修改 `_handle_project_selected` 方法：在处理设备数据前设置当前场站名称到IODataLoader

这些修改确保了缓存功能的完整性，提升了用户体验，减少了重复的API请求和数据处理时间。 