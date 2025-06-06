# 设计院文档自动填写IO点表功能开发计划

## 功能概述
开发一个完整的工作流程，让用户能够通过设计院Word文档自动填写IO点表模板的灰色高亮部分，实现从文档解析到通道分配再到模板自动填写的端到端解决方案。

## 核心需求重新定义
1. **文档解析**：解析设计院Word文档，提取仪表位号、描述、信号类型等信息
2. **通道分配界面**：提供交互界面让用户手动分配每个点位到具体PLC通道
3. **模板自动填写**：根据通道分配结果，自动填写IO点表模板的灰色部分
4. **数据管理**：支持分配方案的保存、加载和管理

## 用户工作流程
```
1. 拖拽Word文档 → 解析点位数据
2. 进入通道分配界面 → 人工分配每个点位到具体通道
3. 保存分配方案
4. 生成IO点表时选择使用分配方案 → 自动填写灰色部分
```

## 技术架构

### 1. 文档解析模块 (`core/document_parser/`) ✅ 已完成
- **word_parser.py**: Word文档解析器
- **smart_header_detector.py**: 智能表头检测器
- **data_enhancer.py**: 数据增强处理器

### 2. 通道分配模块 (`core/channel_assignment/`) 🆕 新增
- **assignment_manager.py**: 分配方案管理器
- **channel_provider.py**: 可用通道提供器
- **assignment_validator.py**: 分配结果验证器

### 3. 数据存储模块 (`core/data_storage/`) 🆕 新增
- **parsed_data_dao.py**: 解析数据访问对象
- **assignment_dao.py**: 分配方案访问对象
- **data_models.py**: 数据模型定义

### 4. 用户界面模块 (`ui/components/`)
- **document_import_widget.py**: 文档导入界面 ✅ 已完成
- **channel_assignment_widget.py**: 通道分配界面 🆕 新增
- **assignment_preview_widget.py**: 分配预览组件 🆕 新增

### 5. IO点表集成模块 (`core/io_table/`)
- **excel_exporter.py**: 修改现有导出器，支持自动填写 🔄 需修改
- **template_filler.py**: 模板自动填写器 🆕 新增

## 开发阶段

### 第一阶段：文档解析功能 ✅ 已完成
**目标**：实现Word文档解析和数据提取
- [x] Word文档解析器
- [x] 智能表头检测
- [x] 数据增强和标准化

### 第二阶段：数据存储和管理 🎯 当前阶段
**目标**：建立解析数据的持久化存储
- [ ] 设计数据模型和数据库表结构
- [ ] 实现解析数据的CRUD操作
- [ ] 建立分配方案的存储机制

**交付物**：
- 解析数据持久化存储
- 分配方案管理功能
- 数据查询和检索接口

### 第三阶段：通道分配界面 🎯 核心功能
**目标**：创建交互式通道分配界面
- [ ] 设计通道分配UI布局
- [ ] 实现拖拽分配功能
- [ ] 添加智能分配辅助
- [ ] 实现分配结果验证

**界面设计**：
```
┌─────────────────┬─────────────────┬─────────────────┐
│   解析的点位    │    分配操作     │   可用通道      │
├─────────────────┼─────────────────┼─────────────────┤
│ □ PT-1102       │                 │ □ AI-01         │
│   压力检测      │   [分配] →      │ □ AI-02         │
│   AI类型        │                 │ □ AI-03         │
├─────────────────┤                 ├─────────────────┤
│ □ TT-1101       │                 │ □ DI-01         │
│   温度检测      │   [分配] →      │ □ DI-02         │
│   AI类型        │                 │ □ DI-03         │
└─────────────────┴─────────────────┴─────────────────┘
```

**交付物**：
- 完整的通道分配界面
- 拖拽分配功能
- 分配冲突检测和提醒

### 第四阶段：IO点表集成 🎯 最终目标
**目标**：修改现有IO点表导出功能，支持自动填写
- [ ] 修改PLCSheetExporter类
- [ ] 实现从分配数据自动填写灰色字段
- [ ] 在IO点表界面添加"使用分配数据"选项

**自动填写的字段**：
- **通道位号**：根据分配结果填写（如AI-01）
- **变量名称（HMI）**：使用解析的instrument_tag
- **变量描述**：使用解析的description
- **单位**：使用解析的units
- **量程低限/高限**：从解析的data_range提取
- **供电类型**：从解析的power_supply推断
- **线制**：从信号类型推断

**交付物**：
- 修改后的IO点表导出功能
- 自动填写灰色字段的逻辑
- 完整的端到端工作流程

### 第五阶段：功能完善和优化
**目标**：完善用户体验和系统稳定性
- [ ] 添加批量分配功能
- [ ] 实现分配模板和规则
- [ ] 优化界面交互体验
- [ ] 添加数据导入导出功能

## 关键技术实现

### 1. 通道分配算法
```python
class ChannelAssignmentManager:
    def assign_channel(self, point_data, channel_id):
        """分配点位到指定通道"""
        
    def auto_assign_by_type(self, points, start_channel):
        """按类型自动分配通道"""
        
    def validate_assignment(self, assignment):
        """验证分配结果的合法性"""
```

### 2. 模板自动填写
```python
class TemplateFiller:
    def fill_from_assignment(self, assignment_data):
        """根据分配数据填写模板"""
        
    def extract_range_values(self, data_range):
        """从数据范围提取低限高限"""
        
    def infer_power_type(self, power_supply):
        """推断供电类型"""
```

### 3. 数据持久化
```python
class ParsedDataDAO:
    def save_parsed_data(self, project_id, parsed_points):
        """保存解析数据"""
        
    def get_parsed_data(self, project_id):
        """获取解析数据"""

class AssignmentDAO:
    def save_assignment(self, assignment_scheme):
        """保存分配方案"""
        
    def load_assignment(self, scheme_id):
        """加载分配方案"""
```

## 数据模型设计

### 解析数据模型
```python
@dataclass
class ParsedPoint:
    id: str
    project_id: str
    instrument_tag: str
    description: str
    signal_type: str
    io_type: str
    units: str
    data_range: str
    power_supply: str
    created_at: datetime
```

### 分配方案模型
```python
@dataclass
class ChannelAssignment:
    id: str
    project_id: str
    scheme_name: str
    assignments: List[PointChannelMapping]
    created_at: datetime

@dataclass
class PointChannelMapping:
    point_id: str
    channel_id: str
    channel_type: str  # AI, DI, AO, DO
    assigned_at: datetime
```

## 成功标准

### 功能标准
- [ ] 支持100+点位的通道分配操作
- [ ] 自动填写准确率达到95%以上
- [ ] 完整的数据管理和方案保存功能

### 性能标准
- [ ] 通道分配界面响应时间<1秒
- [ ] 模板自动填写时间<10秒
- [ ] 支持多个项目并发操作

### 用户体验标准
- [ ] 直观的拖拽分配界面
- [ ] 清晰的分配进度和状态提示
- [ ] 完善的错误处理和撤销功能

## 风险评估和缓解

### 高风险
- **通道冲突**：多个点位分配到同一通道
  - 缓解：实时冲突检测和提醒
- **数据一致性**：分配数据与实际硬件不符
  - 缓解：严格的数据验证和用户确认

### 中风险
- **界面复杂性**：通道分配界面可能过于复杂
  - 缓解：分步骤引导和智能默认值
- **性能问题**：大量点位的分配操作可能较慢
  - 缓解：分页加载和异步处理

## 后续优化方向

### 短期优化
- 智能分配算法优化
- 分配模板和规则引擎
- 批量操作功能增强

### 长期规划
- AI辅助的智能分配建议
- 与硬件配置的实时同步
- 分配方案的版本控制和协作
