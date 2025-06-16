# 工控系统点表管理软件V1.0

## 🚀 项目简介

工控系统点表管理软件V1.0 是一个专为工业自动化项目深化设计阶段开发的综合性数据管理平台。该工具集成了项目数据查询、PLC硬件配置、第三方设备管理、IO点表生成等核心功能，大幅提升了工程师的工作效率。

## ✨ 主要特性

### 🔍 数据查询与管理
- **项目信息查询**：支持按项目编号和场站编号快速检索项目信息
- **设备清单管理**：自动获取和展示场站设备清单，支持筛选和排序
- **数据源集成**：与简道云API深度集成，实现实时数据同步

### ⚙️ PLC硬件配置
- **现代化配置界面**：采用穿梭框设计的直观配置界面
- **多系列支持**：完整支持和利时LK/LE系列PLC模块
- **智能配置验证**：自动检测系统类型，智能验证模块配置合法性
- **配置持久化**：自动保存配置到数据库，支持场站间配置切换

### 🔧 第三方设备管理
- **设备模板库**：支持创建和管理第三方设备点表模板
- **批量配置**：基于模板快速配置设备实例
- **灵活扩展**：支持自定义设备类型和点位属性

### 📊 点表生成与导出
- **多格式支持**：
  - PLC点表：和利时PLC（含安全型）、中控PLC
  - HMI点表：亚控组态、力控组态
  - FAT测试点表：自动生成功能测试清单
- **统一数据流**：基于标准化数据模型的统一处理流程
- **智能派生**：自动生成报警、设定点等衍生点位

## 🏗️ 技术架构

### 架构设计原则
- **分层架构**：UI层、业务逻辑层、数据访问层清晰分离
- **模块化设计**：功能模块独立，支持灵活组合和扩展
- **统一数据模型**：基于`UploadedIOPoint`的标准化数据流

### 核心技术栈
- **界面框架**：PySide6 (Qt6)
- **数据库**：SQLite3
- **数据处理**：Pandas, openpyxl
- **架构模式**：MVC + 服务层模式

## 📁 项目结构

```
工控系统点表管理软件V1.0/
├── main.py                    # 应用程序主入口
├── config.ini                # 全局配置文件
├── migrate_plc_configs.py     # 配置迁移工具
├── requirements.txt          # Python依赖列表
├── db/                       # 数据库和配置存储
│   ├── data.db              # SQLite数据库
│   ├── plc_modules.json     # PLC模块定义
│   └── plc_configs/         # PLC配置文件存储
│       ├── plc_config_*.json      # 场站配置文件
│       └── backups/               # 自动备份
├── core/                     # 核心业务逻辑层
│   ├── query_area/          # 数据查询服务
│   │   └── jiandaoyun_api.py      # 简道云API集成
│   ├── project_list_area/   # 项目管理服务
│   │   └── project_service.py    # 项目数据处理
│   ├── device_list_area/    # 设备管理服务
│   │   └── device_service.py     # 设备数据处理
│   ├── io_table/           # IO数据处理核心
│   │   ├── get_data.py           # 数据加载器和处理器
│   │   ├── plc_config_persistence.py  # 配置持久化
│   │   └── excel_exporter.py    # Excel导出功能
│   ├── third_party_config_area/  # 第三方设备配置
│   │   ├── template_service.py   # 模板管理服务
│   │   ├── config_service.py     # 配置管理服务
│   │   ├── database/             # 数据访问层
│   │   │   ├── database_service.py
│   │   │   └── dao.py           # 数据访问对象
│   │   └── models/              # 数据模型
│   │       ├── template_models.py
│   │       └── configured_device_models.py
│   └── post_upload_processor/   # 文件处理流水线
│       ├── uploaded_file_processor/   # 文件解析
│       │   ├── excel_reader.py       # Excel统一读取器
│       │   └── io_data_model.py      # 标准数据模型
│       ├── io_validation/           # 数据校验
│       │   ├── validator.py         # 校验引擎
│       │   └── constants.py         # 校验规则常量
│       ├── plc_generators/          # PLC点表生成器
│       │   └── hollysys_generator/
│       │       ├── generator.py     # 标准和利时生成器
│       │       └── safety_generator.py  # 安全型生成器
│       ├── hmi_generators/          # HMI点表生成器
│       │   ├── yk_generator/        # 亚控生成器
│       │   └── lk_generator/        # 力控生成器
│       └── fat_generators/          # FAT点表生成器
└── ui/                      # 用户界面层
    ├── main_window.py       # 主窗口
    ├── components/          # UI组件
    │   ├── query_area.py           # 查询区域
    │   ├── project_list_area.py    # 项目列表
    │   ├── device_list_area.py     # 设备列表
    │   ├── third_party_device_area.py  # 第三方设备配置
    │   └── plc_config/            # 现代化PLC配置组件
    │       ├── plc_config_widget.py     # 主配置界面
    │       ├── plc_config_adapter.py    # 兼容性适配器
    │       ├── enhanced_transfer_widget.py  # 高级穿梭框
    │       ├── rack_widget.py           # 机架显示组件
    │       └── models.py               # 数据模型
    └── dialogs/            # 对话框
        ├── plc_config_dialog.py      # PLC配置对话框
        ├── template_manage_dialog.py  # 模板管理对话框
        ├── device_point_dialog.py    # 设备点位配置
        └── error_display_dialog.py   # 错误显示对话框
```

## 🚀 快速开始

### 环境要求
- Python 3.7 或更高版本
- Windows 10+ (推荐) / Linux / macOS
- 4GB+ RAM
- 500MB+ 磁盘空间

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd new_jdy_api
```

2. **创建虚拟环境**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS  
source .venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置应用**
```bash
# 复制配置模板并编辑
cp config.ini.example config.ini
# 编辑config.ini，填入简道云API信息
```

5. **运行应用**
```bash
python main.py
```

## ⚙️ 配置说明

### config.ini 配置项

```ini
[DATABASE]
db_path = db/data.db

[JIANDAOYUN]
api_base_url = https://api.jiandaoyun.com/api/v5
api_key = YOUR_API_KEY
app_id = YOUR_APP_ID
entry_id = YOUR_ENTRY_ID

[UI]
use_modern_plc_config = true
show_comparison_mode = false

[LOGGING]
level = INFO
log_file = app.log
```

### 简道云API配置
1. 登录简道云管理后台
2. 获取API密钥和应用信息
3. 填入config.ini对应字段

## 📖 使用指南

### 1. 项目数据查询
1. 在查询区域输入项目编号
2. 点击"查询"按钮获取项目列表
3. 选择具体场站获取设备清单

### 2. PLC硬件配置
1. 切换到"PLC硬件配置"选项卡
2. 使用穿梭框选择和配置模块
3. 系统自动验证配置合法性
4. 点击"应用配置"保存配置

### 3. 第三方设备配置
1. 进入"第三方设备配置"选项卡
2. 创建或选择设备模板
3. 配置设备实例和点位属性
4. 保存配置供后续点表生成使用

### 4. 点表生成流程
1. 上传IO点表Excel文件
2. 系统自动校验文件格式
3. 选择目标格式（PLC/HMI/FAT）
4. 生成并下载对应点表文件

## 🔧 开发指南

### 代码贡献
1. Fork项目
2. 创建功能分支
3. 提交更改
4. 创建Pull Request

### 开发环境设置
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
python -m pytest tests/

# 代码格式检查
black . --check
flake8 .
```

### 架构扩展
- **新增PLC支持**：继承`BaseGenerator`类
- **新增HMI支持**：实现标准生成器接口
- **新增数据源**：扩展API服务层

## 🔄 最新更新

### v2.1.0 (当前版本)
- ✅ 修复应用配置按钮状态问题
- ✅ 配置文件迁移到db目录统一管理
- ✅ 修正机架槽位显示逻辑（显示可用槽位数）
- ✅ 实现现代化PLC配置界面
- ✅ 增强配置持久化和缓存机制
- ✅ 完善键盘快捷键支持（Ctrl+A全选、Enter移动）

### 计划功能
- 🔄 中控PLC点表生成器完善
- 🔄 配置导入导出功能
- 🔄 批量项目处理功能
- 🔄 Web界面支持

## ⚠️ 注意事项

### 重要提醒
- 📁 配置文件现存储在`db/plc_configs/`目录
- 🔧 如有旧配置文件，请运行`python migrate_plc_configs.py`进行迁移
- 💾 建议定期备份`db/`目录
- 🔑 妥善保管简道云API密钥

### 故障排除
- **配置按钮灰色**：请先添加模块配置
- **文件校验失败**：检查Excel文件格式和列名
- **API连接失败**：确认网络连接和API配置

## 📞 技术支持

- 📧 邮箱：[技术支持邮箱]
- 🐛 Issue：[GitHub Issues]
- 📖 文档：[在线文档地址]

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

**开发团队** | 致力于提升工业自动化工程效率 🚀

## 更新日志

### 2025-05-23 修复打包后PLC配置保存问题
- **问题描述**：打包成exe后，PLC配置无法保存，看不到生成的配置目录和文件
- **问题原因**：`PLCConfigPersistence`类使用`__file__`计算路径，在打包环境中会指向临时解压目录
- **解决方案**：
  - 在`plc_config_persistence.py`中添加了`get_app_base_path()`函数
  - 该函数能够正确识别程序是否被打包，并返回正确的基准路径
  - 打包后配置文件将保存在exe所在目录下的`db/plc_configs/`文件夹中
- **影响范围**：此修改确保了PLC配置在开发环境和打包环境中都能正确保存和加载