# 深化设计数据查询工具

## 项目简介

本项目是一个用于深化设计数据查询和点表配置的工具，主要功能包括：
- 查询项目和场站信息
- 配置第三方设备点表
- 生成和导出点表
- 管理设备模板
- PLC系列及模块配置管理

## 项目结构

项目采用模块化设计，将UI和业务逻辑分离，主要结构如下：

```
project_root/
├── main.py                  # 程序入口点
├── requirements.txt         # 项目依赖
├── templates.db            # 模板数据库
├── ui/                     # UI相关代码
│   ├── __init__.py
│   ├── main_window.py      # 主窗口UI
│   └── dialogs/            # 对话框UI组件
│       ├── __init__.py
│       ├── device_point_dialog.py     # 设备点位配置对话框
│       ├── template_manage_dialog.py  # 模板管理对话框
│       ├── module_manager_dialog.py   # PLC模块管理对话框
│       └── plc_config_dialog.py       # PLC配置对话框
└── core/                   # 核心业务逻辑
    ├── __init__.py
    ├── jiandaoyun_api.py  # 简道云API接口
    ├── point_manager.py    # 点位管理
    ├── plc/               # PLC相关
    │   ├── __init__.py
    │   └── hollysys/      # 和利时PLC
    │       ├── __init__.py
    │       └── lk_db.py   # PLC模块数据库操作
    ├── third_device/      # 第三方设备相关
    │   ├── __init__.py
    │   ├── device_manager.py  # 设备管理器
    │   └── device_model.py    # 设备模型
    └── db/                # 数据库操作
        ├── __init__.py
        └── template_db.py # 模板数据库操作
```

## 主要模块说明

### UI模块

- **main_window.py**: 主窗口界面，包含查询条件、项目列表、设备清单和配置区域
- **device_point_dialog.py**: 设备点位配置对话框，用于配置第三方设备的点位
- **template_manage_dialog.py**: 模板管理对话框，用于创建、编辑、删除设备模板
- **module_manager_dialog.py**: PLC模块管理对话框，用于管理不同PLC系列及其模块
- **plc_config_dialog.py**: PLC配置对话框，用于配置PLC机架中的模块布局

### 核心业务逻辑模块

- **jiandaoyun_api.py**: 简道云API接口，负责与简道云平台交互
- **point_manager.py**: 点位管理类，负责点位的生成和预览
- **plc/hollysys/lk_db.py**: PLC模块数据库操作，管理PLC系列和模块信息
- **third_device/device_manager.py**: 设备管理类，负责设备点位的总体管理
- **third_device/device_model.py**: 第三方设备管理类，负责设备点位的管理和导出

### PLC配置功能

#### 1. PLC系列管理
- 支持添加、删除PLC系列
- 每个系列可配置名称和描述
- 系列数据存储在SQLite数据库中

#### 2. 模块管理
- 按系列管理PLC模块
- 支持添加、删除模块
- 模块信息包括：型号、类型(AI/AO/DI/DO)、通道数、描述

#### 3. 机架配置
- 支持配置PLC机架中的模块布局
- 可选择不同的模块类型
- 实时预览配置结果

## 使用方法

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 运行程序：
   ```
   python main.py
   ```

3. 配置第三方设备点表：
   - 点击右侧"第三方设备点表配置"按钮
   - 选择设备模板
   - 输入变量名前缀
   - 点击"保存配置"按钮

4. 生成点表：
   - 输入项目编号和场站编号
   - 点击"生成点表"按钮
   - 在预览窗口中查看点表
   - 点击"导出点表"按钮导出为Excel格式

5. 管理设备模板：
   - 在设备点位配置对话框中点击"管理设备模板"按钮
   - 创建、编辑、复制或删除模板
   - 为模板添加点位

### PLC配置
1. 打开PLC模块管理：
   - 点击"模块管理"按钮
   - 在系列管理区域添加或选择PLC系列
   - 为选定系列添加模块

2. 配置PLC机架：
   - 点击"PLC配置"按钮
   - 选择PLC系列和机架型号
   - 从可用模块列表中选择模块添加到机架
   - 可随时调整模块位置或移除模块

## 开发环境

- Python 3.x
- PySide6 (Qt for Python)

## 依赖库

- PySide6: UI界面库
- openpyxl: 用于Excel文件导出（支持多工作簿）

## 注意事项

- 确保已安装所有依赖库
- 首次运行时会自动创建数据库
- 模板数据存储在本地数据库中，请勿手动修改数据库文件
- 导出点表前请确保已正确配置设备点位
