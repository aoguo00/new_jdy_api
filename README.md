# 深化设计数据查询工具

## 项目简介
用于深化设计数据查询和点表配置的工具，支持项目查询、设备点表配置、PLC配置等功能。

## 主要功能
- 项目和场站信息查询
- 第三方设备点表配置
- PLC系列及模块管理
- 设备模板库管理
- 点表生成和导出

## 项目结构
```
project_root/
├── main.py                  # 程序入口
├── config.ini              # 配置文件
├── data.db                 # SQLite数据库
├── requirements.txt        # 项目依赖
├── core/                   # 核心业务逻辑
│   ├── __init__.py
│   ├── query_area/        # 查询服务 (如简道云API)
│   │   ├── __init__.py
│   │   └── jiandaoyun_api.py
│   ├── project_list_area/ # 项目列表服务与处理
│   │   ├── __init__.py
│   │   ├── project_processor.py
│   │   └── project_service.py
│   ├── device_list_area/  # 设备列表服务与处理
│   │   ├── __init__.py
│   │   ├── device_processor.py
│   │   └── device_service.py
│   ├── io_table/          # IO点表数据处理与导出
│   │   ├── __init__.py
│   │   ├── excel_exporter.py
│   │   ├── get_data.py         # (包含IODataLoader, PLCConfigurationHandler等)
│   │   └── plc_modules.py
│   ├── third_party_config_area/ # 第三方设备配置
│   │   ├── __init__.py
│   │   ├── config_service.py
│   │   ├── template_service.py
│   │   ├── database/        # 数据库服务与DAO
│   │   │   ├── __init__.py
│   │   │   ├── dao.py
│   │   │   ├── database_service.py
│   │   │   └── sql.py
│   │   └── models/          # 数据模型
│   │       ├── __init__.py
│   │       ├── configured_device_models.py
│   │       └── template_models.py
│   └── post_upload_processor/ # IO点表上传后处理
│       ├── __init__.py
│       ├── io_validation/      # IO点表验证
│       │   ├── __init__.py
│       │   └── validator.py
│       ├── hmi_generators/     # HMI点表生成
│       │   ├── __init__.py
│       │   ├── lk_generator/   # 力控
│       │   │   └── __init__.py
│       │   └── yk_generator/   # 亚控
│       │       └── __init__.py
│       └── plc_generators/       # PLC点表生成
│           ├── __init__.py
│           ├── hollysys_generator/ # 和利时
│           │   └── __init__.py
│           └── supcon_generator/   # 中控
│               └── __init__.py
└── ui/                    # 用户界面
    ├── __init__.py
    ├── main_window.py     # 主窗口
    ├── components/        # UI组件
    │   ├── query_area.py
    │   ├── project_list_area.py
    │   ├── device_list_area.py
    │   └── third_party_device_area.py
    └── dialogs/           # 对话框
        ├── __init__.py
        ├── device_point_dialog.py
        ├── error_display_dialog.py
        ├── plc_config_dialog.py
        └── template_manage_dialog.py
```

## 开发环境
- Python 3.7+
- PySide6 6.5.0+
- SQLite3

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置：
- 编辑 `config.ini`，设置简道云API信息和其他配置

3. 运行：
```bash
python main.py
```

## 主要功能说明

### 1. 项目查询
- 支持按项目编号和场站编号查询
- 显示查询结果数量
- 自动获取场站设备清单

### 2. 设备点表配置
- 支持设备模板管理
- 可配置点位属性
- 支持批量生成点表

### 3. PLC配置
- PLC系列和模块管理
- 机架配置
- 模块布局设置

### 4. 数据导出
- 支持Excel格式导出
- 可自定义导出模板
- 支持批量导出

## 配置说明

`config.ini` 主要配置项：
```ini
[Database]
db_path = data.db

[JianDaoYun]
api_base_url = https://api.jiandaoyun.com/api/v5
api_key = YOUR_API_KEY
app_id = YOUR_APP_ID
entry_id = YOUR_ENTRY_ID
```

## 注意事项
- 首次运行会自动创建数据库
- 需要正确配置简道云API信息
- 建议定期备份数据库文件
