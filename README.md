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
├── main.py                  # GUI程序入口，初始化并运行PySide6应用和主窗口
├── config.ini              # 应用程序配置文件 (如数据库路径, API密钥等)
├── data.db                 # SQLite数据库文件 (如果使用，具体路径可能在config.ini中定义)
├── requirements.txt        # Python项目依赖包列表
├── README.md               # 项目说明文件 (本文档)
├── core/                   # 核心业务逻辑层，与UI分离
│   ├── __init__.py
│   ├── query_area/         # 与外部数据源(如简道云)API交互的模块
│   │   ├── __init__.py
│   │   └── jiandaoyun_api.py # 封装简道云API的调用逻辑，用于获取项目、设备等信息
│   ├── project_list_area/  # 项目列表相关的业务逻辑处理
│   │   ├── __init__.py
│   │   ├── project_processor.py # (可能用于)处理从API获取的项目原始数据，转换为内部使用格式
│   │   └── project_service.py   # 项目服务，提供获取和格式化项目数据的功能给UI层
│   ├── device_list_area/   # 设备列表相关的业务逻辑处理
│   │   ├── __init__.py
│   │   ├── device_processor.py  # (可能用于)处理从API获取的设备原始数据
│   │   └── device_service.py    # 设备服务，提供获取和格式化特定场站设备数据的功能
│   ├── io_table/           # 旧的或辅助的IO点表数据处理与导出逻辑 (部分功能可能已被新流程取代)
│   │   ├── __init__.py
│   │   ├── excel_exporter.py    # (可能用于)将数据导出为特定Excel模板格式
│   │   ├── get_data.py          # (可能包含)如IODataLoader, PLCConfigurationHandler等，用于处理PLC配置和生成点表模板
│   │   └── plc_modules.py       # (可能包含)PLC模块相关的定义或数据
│   ├── third_party_config_area/ # 第三方设备配置管理，包括模板和已配置设备
│   │   ├── __init__.py
│   │   ├── config_service.py    # 管理已配置的第三方设备实例的服务
│   │   ├── template_service.py  # 管理第三方设备点表模板的服务
│   │   ├── database/            # 数据库交互层 (SQLite)
│   │   │   ├── __init__.py
│   │   │   ├── dao.py           # 数据访问对象 (DAO)，封装SQL操作，如TemplateDAO, ConfiguredDeviceDAO
│   │   │   ├── database_service.py # 数据库服务的核心，提供连接和事务管理 (可能是单例)
│   │   │   └── sql.py           # (可能包含)SQL语句定义
│   │   └── models/              # Pydantic或dataclass等数据模型，用于第三方设备配置的数据库记录
│   │       ├── __init__.py
│   │       ├── configured_device_models.py # 已配置设备的数据模型
│   │       └── template_models.py          # 设备模板的数据模型
│   └── post_upload_processor/ # 用户上传IO点表后的核心处理流程，包含校验、解析和生成
│       ├── __init__.py
│       ├── uploaded_file_processor/ # 统一的Excel文件读取和标准化模块
│       │   ├── __init__.py
│       │   ├── excel_reader.py     # 核心：读取用户上传的Excel，并将所有sheet数据转换为统一的 `UploadedIOPoint` 对象列表，输出为 `Dict[str, List[UploadedIOPoint]]` 结构
│       │   └── io_data_model.py    # 核心：定义 `UploadedIOPoint` 标准化数据模型
│       ├── intermediate_point_processor.py # (建议或已创建) 负责根据主IO点派生中间点位（如报警、设定点），输入和输出均为 `Dict[str, List[UploadedIOPoint]]`
│       ├── io_validation/          # IO点表文件内容校验模块
│       │   ├── __init__.py
│       │   ├── constants.py        # 校验规则中使用的常量 (如预期的列名)
│       │   └── validator.py        # 对上传的Excel文件进行规则校验，确保数据符合预设规范
│       ├── hmi_generators/         # HMI点表生成器，将标准化的IO点数据转换为特定HMI格式
│       │   ├── __init__.py
│       │   ├── base_generator.py   # (建议或已创建) 生成器的抽象基类 (ABC)，定义统一的 `generate` 接口
│       │   ├── lk_generator/       # 力控HMI点表生成器
│       │   │   ├── __init__.py
│       │   │   └── generator.py    # 实现力控 `Basic.xls` 点表生成逻辑
│       │   └── yk_generator/       # 亚控HMI点表生成器
│       │       ├── __init__.py
│       │       ├── kingview_format_config.py # (建议或已创建) 亚控输出格式的配置 (表头、默认值等)
│       │       └── generator.py    # 实现亚控IO Server和数据词典文件的生成逻辑
│       └── plc_generators/           # PLC点表生成器，将标准化的IO点数据转换为特定PLC格式
│           ├── __init__.py
│           ├── base_generator.py   # (可能与HMI生成器共用或类似) 生成器的抽象基类
│           ├── hollysys_generator/   # 和利时PLC点表生成器
│           │   ├── __init__.py
│           │   └── generator.py      # 实现和利时PLC点表 `.xls` 文件生成逻辑
│           └── supcon_generator/     # 中控PLC点表生成器 (待实现或规划中)
│               ├── __init__.py
│               └── generator.py
└── ui/                    # 用户界面 (PySide6)
    ├── __init__.py
    ├── main_window.py     # 主窗口类，组织UI布局，处理用户交互和信号，调用core层服务
    ├── components/        # 可重用的UI组件
    │   ├── __init__.py
    │   ├── query_area.py           # 查询条件输入区域UI
    │   ├── project_list_area.py    # 项目列表显示区域UI
    │   ├── device_list_area.py     # 设备列表显示区域UI
    │   └── third_party_device_area.py # 第三方设备配置界面UI
    └── dialogs/           # 应用程序中使用的各种对话框
        ├── __init__.py
        ├── device_point_dialog.py  # (可能用于)单个设备点位详细配置的对话框
        ├── error_display_dialog.py # 通用的错误信息显示对话框
        ├── plc_config_dialog.py    # PLC硬件配置对话框
        └── template_manage_dialog.py # 第三方设备模板管理对话框
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

本项目在处理用户上传的IO点表以生成PLC和HMI点表时，采用了统一的数据源和清晰的数据流，确保了模块间的解耦和可维护性。

1.  **文件上传与校验**:
    *   用户通过UI (`ui/main_window.py`) 上传Excel格式的IO点表文件。
    *   在进行任何数据解析之前，程序首先调用 `core.post_upload_processor.io_validation.validator.validate_io_table(file_path)` 对原始Excel文件内容进行规则校验。此校验基于预定义的列名和规则（定义在 `core/post_upload_processor/io_validation/constants.py`），确保数据格式和内容符合规范。
    *   校验失败会阻止后续的数据加载和处理，并向用户提示错误信息。

2.  **统一数据解析与标准化 (`excel_reader.py`)**:
    *   只有当原始Excel文件通过校验后，文件路径才会传递给 `core.post_upload_processor.uploaded_file_processor.excel_reader.load_workbook_data()` 函数。
    *   `excel_reader.py` 的核心职责是：
        *   打开Excel文件。
        *   **解析所有工作表**：无论是被指定为主IO点表的工作表（通常名为 "IO点表"），还是其他被视为第三方设备数据的工作表。
        *   **统一数据模型转换**：将所有工作表中的每一有效行数据都转换为标准化的内部数据模型 `core.post_upload_processor.uploaded_file_processor.io_data_model.UploadedIOPoint` 对象实例。
        *   **标记数据来源**：每个 `UploadedIOPoint` 对象会通过其 `source_sheet_name` (原始工作表名) 和 `source_type` (例如 "main_io", "third_party", "intermediate_from_main") 属性来记录其来源。
        *   **处理预留点**：在解析主IO工作表时，如果点位的HMI变量名为空但通道位号和PLC地址不为空，会自动生成预留点HMI名称（如 "YLDW\[通道位号]"）和描述。
        *   **（可选/分离的）中间点派生**：
            *   **当前（或分离后）**：基于主IO工作表中的点位（`source_type="main_io"`），系统会根据预定义的规则（例如，在 `core/post_upload_processor/intermediate_point_processor.py` 中定义的 `INTERMEDIATE_POINT_DEFINITIONS`）派生出相关的中间点位（如AI点的报警、设定点等）。
            *   这些派生出的中间点同样是 `UploadedIOPoint` 对象，其 `source_type` 会被标记为 "intermediate_from_main"，并继承或生成相应的HMI名称和描述。此步骤确保了所有相关的点位信息都以统一的格式存在。
    *   `load_workbook_data` 函数最终返回一个核心数据结构：`Dict[str, List[UploadedIOPoint]]`。这是一个字典，键是原始Excel中的工作表名称，值是对应工作表中所有点位（包括直接解析的点和后续派生的中间点）的 `UploadedIOPoint` 对象列表。同时，它也可能返回一个错误消息字符串。

3.  **数据暂存**:
    *   成功由 `load_workbook_data` 解析并（如果适用）经过中间点派生处理后的 `Dict[str, List[UploadedIOPoint]]` 数据被返回到 `ui/main_window.py`。
    *   `MainWindow` 将这个字典存储在其成员变量 `self.loaded_io_data_by_sheet` 中。此变量构成了所有后续点表生成的统一、标准化数据源。

4.  **点表生成请求**:
    *   用户在UI上选择要生成的PLC类型（如和利时）或HMI类型（如亚控、力控），并触发相应的生成操作。

5.  **统一接口调用与生成**:
    *   `MainWindow` 根据用户的选择，从一个策略映射中获取相应的点表生成器实例（例如 `HollysysGenerator`, `KingViewGenerator`, `LikongGenerator` 的实例）。
    *   所有生成器都实现了统一的接口（例如，一个 `PointTableGenerator` 抽象基类，定义了 `generate` 方法）。
    *   `MainWindow` 调用选定生成器的 `generate` 方法，并将统一的 `self.loaded_io_data_by_sheet: Dict[str, List[UploadedIOPoint]]` 数据以及输出目录等选项作为参数传递。
    *   各个生成器内部逻辑：
        *   接收 `Dict[str, List[UploadedIOPoint]]`。
        *   根据自身需求处理这些数据（例如，亚控生成器可能会在内部将所有工作表的点位列表合并成一个扁平列表进行处理，而和利时或力控生成器可能会为原始字典中的每个工作表条目生成对应的目标文件结构或Sheet页）。
        *   将标准化的 `UploadedIOPoint` 数据转换为特定HMI或PLC系统所需的点表文件格式并保存。

通过这种方式，数据校验、解析、标准化、中间点派生（可选的独立步骤）以及最终的格式生成等各个环节职责清晰，模块间依赖于定义良好的数据结构 (`UploadedIOPoint`, `Dict[str, List[UploadedIOPoint]]`) 和接口 (`PointTableGenerator`)，从而提高了系统的可维护性和可扩展性。

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
