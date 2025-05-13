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
│   ├── io_table/          # IO点表数据处理与导出 (旧的模板生成等，部分功能可能被新流程覆盖)
│   │   ├── __init__.py
│   │   ├── excel_exporter.py
│   │   ├── get_data.py         # (包含IODataLoader, PLCConfigurationHandler等)
│   │   └── plc_modules.py
│   ├── third_party_config_area/ # 第三方设备配置 (主要用于UI交互和数据库存储)
│   │   ├── __init__.py
│   │   ├── config_service.py
│   │   ├── template_service.py
│   │   ├── database/        # 数据库服务与DAO
│   │   │   ├── __init__.py
│   │   │   ├── dao.py
│   │   │   ├── database_service.py
│   │   │   └── sql.py
│   │   └── models/          # 数据模型 (用于第三方设备配置的数据库模型)
│   │       ├── __init__.py
│   │       ├── configured_device_models.py
│   │       └── template_models.py
│   └── post_upload_processor/ # IO点表上传后处理 (核心的点表生成流程)
│       ├── __init__.py
│       ├── uploaded_file_processor/ # 统一的Excel文件读取和预处理
│       │   ├── __init__.py
│       │   ├── excel_reader.py     # 核心：读取Excel并转换为 UploadedIOPoint 和 DataFrame
│       │   └── io_data_model.py    # 核心：UploadedIOPoint 数据模型定义
│       ├── io_validation/      # IO点表验证
│       │   ├── __init__.py
│       │   ├── constants.py
│       │   └── validator.py
│       ├── hmi_generators/     # HMI点表生成器
│       │   ├── __init__.py
│       │   ├── lk_generator/   # 力控 (待实现)
│       │   │   ├── __init__.py
│       │   │   └── generator.py
│       │   └── yk_generator/   # 亚控
│       │       ├── __init__.py
│       │       └── generator.py
│       └── plc_generators/       # PLC点表生成器
│           ├── __init__.py
│           ├── hollysys_generator/ # 和利时
│           │   ├── __init__.py
│           │   └── generator.py
│           └── supcon_generator/   # 中控 (待实现)
│               ├── __init__.py
│               └── generator.py
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

## 统一数据源与核心数据流 (IO点表生成)

本项目在处理用户上传的IO点表以生成PLC和HMI点表时，采用了统一的数据源和清晰的数据流：

1.  **文件上传与初步解析**:
    *   用户通过UI (`ui/main_window.py`) 上传Excel格式的IO点表文件。
    *   文件路径传递给 `core.post_upload_processor.uploaded_file_processor.excel_reader.load_workbook_data()` 函数。
    *   `load_workbook_data` 负责：
        *   打开Excel文件。
        *   将指定的"主IO点表"（例如名为 "IO点表" 的sheet）的每一行数据转换为 `core.post_upload_processor.uploaded_file_processor.io_data_model.UploadedIOPoint` 对象实例，形成 `List[UploadedIOPoint]`。
        *   将其余的sheet页作为第三方设备数据，读取为 `pandas.DataFrame` 对象，并与sheet名称一起存为一个元组，形成 `List[Tuple[str, pd.DataFrame]]`。
        *   同时，它会返回一个可选的错误消息字符串，用于在读取过程中发生的严重错误。

2.  **数据校验**:
    *   在 `load_workbook_data` 之前（或作为其一部分，取决于具体实现细节），`core.post_upload_processor.io_validation.validator.validate_io_table()` 会对原始Excel文件内容进行规则校验，确保数据格式和内容符合预设规范。校验失败会阻止后续的数据加载和处理。

3.  **数据暂存**:
    *   成功通过校验并由 `load_workbook_data` 解析后的 `main_io_points: List[UploadedIOPoint]` 和 `third_party_data: List[Tuple[str, pd.DataFrame]]` (以及可能的错误消息) 被返回到 `ui.main_window.py`。
    *   `MainWindow` 将这些解析后的数据存储在其成员变量 `self.loaded_main_io_points` 和 `self.loaded_third_party_data` 中。这些变量构成了后续点表生成的统一数据源。

4.  **点表生成请求**:
    *   用户在UI上选择要生成的PLC类型（如和利时）或HMI类型（如亚控），并触发相应的生成操作。

5.  **数据传递与生成**:
    *   `MainWindow` 将存储的 `self.loaded_main_io_points` 和 `self.loaded_third_party_data` 作为参数，传递给位于 `core.post_upload_processor.plc_generators` 或 `core.post_upload_processor.hmi_generators` 下的对应生成器类的方法（例如 `HollysysGenerator.generate_hollysys_table()` 或 `KingViewGenerator.generate_kingview_files()`）。
    *   各个生成器内部逻辑现在统一使用 `UploadedIOPoint` 对象来访问和处理主IO点数据，并结合传入的第三方DataFrame列表来生成特定格式的点表文件。

通过这种方式，不同类型的点表生成器都依赖于相同结构和类型的输入数据，实现了数据源的统一，简化了后续生成逻辑的开发和维护。

### 关于 `validator.py` 的独立性及其在数据流中的位置

需要特别说明的是，`core/post_upload_processor/io_validation/validator.py` 中的数据校验逻辑，在整个数据处理流程中扮演着一个独立的前置角色：

1.  **`validator.py` 的核心职责**:
    *   `validator.py` 主要负责在用户上传的原始Excel文件数据被加载转换成统一的 `UploadedIOPoint` 对象（以及第三方 `DataFrame`）*之前*，直接对这些原始数据进行校验。
    *   校验的关注点包括：Excel表格中的列名是否存在、单元格值的格式是否正确、是否满足必填项要求、值是否在预定义的允许范围内、以及是否存在跨列数据不一致等问题。
    *   它的主要输入是用户上传文件的路径，输出是一个布尔值（表示校验是否通过）和一条描述校验结果或具体错误的消息字符串。

2.  **数据流中的校验环节**:
    *   在 `ui/main_window.py` 的 `_handle_upload_io_table` 方法（即处理IO点表上传的核心函数）中，程序会**首先**调用 `validate_io_table(file_path)` 来执行数据校验。
    *   **只有当** `validate_io_table` 函数返回 `is_valid = True`（即校验通过），程序才会继续执行后续的 `load_workbook_data(file_path)` 函数调用，进而将Excel数据加载并转换为 `List[UploadedIOPoint]` 和第三方 `DataFrame` 列表。
    *   这种设计意味着 `validator.py` 的校验工作在其自身定义的作用域内完成，它不依赖于 `UploadedIOPoint` 这个后续步骤才会用到的数据模型，也不受数据如何被加载或转换的影响。

3.  **`validator.py` 的内部实现**: 
    *   在其内部，`validator.py` 使用 `pandas.read_excel` 来读取各个sheet页，然后逐行遍历DataFrame数据。
    *   所有具体的校验规则（例如 `HmiDescriptionConsistencyRule`, `RealSetpointUniquenessRule` 等）都是直接操作从DataFrame中取出的单行数据（`pd.Series` 对象）以及一个包含该行上下文的 `ValidationContext` 对象。
    *   这些规则依赖于 `core/post_upload_processor/io_validation/constants.py` 文件中定义的列名常量（如 `C.HMI_NAME_COL`, `C.TP_INPUT_DATA_TYPE_COL` 等）来从原始数据行中准确地提取需要校验的字段值。

**结论**：

对 `excel_reader.py`（负责数据加载和转换）和各个点表生成器的修改，主要是优化了数据在**通过验证之后**如何被统一处理、存储和传递的流程。而 `validator.py` 作为数据进入系统的"第一道关卡"，其基于原始Excel文件内容的校验逻辑，由于其独立性和在数据流中的前置位置，并不会受到这些后续处理流程变化的直接影响。

因此，只要确保以下两点，验证逻辑就能保持其有效性：
*   用户上传的Excel模板文件所使用的**列名**与 `io_validation/constants.py` 中定义的常量保持一致。
*   `validator.py` 中定义的各项**校验规则**（例如，关于HMI名称和描述必须同时填写或为空的规则）仍然符合当前业务需求和期望。
