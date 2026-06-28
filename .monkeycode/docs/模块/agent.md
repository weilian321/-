# Agent 核心中枢层

智能体的核心中枢层，包含自主任务规划、多工具调度、双层记忆、异常处理和结果自校验五大能力。位于 `bid-param-analyzer/agent/`。

## 目录

```
agent/
├── __init__.py           # 统一导出 15 个核心类/数据类
├── planner.py            # 自主任务规划引擎
├── scheduler.py          # 多工具统一调度器
├── memory.py             # 双层记忆系统
├── exception_handler.py  # 异常自主处理器
└── self_validator.py     # 结果自校验器
```

## 模块

### 任务规划引擎 (`planner.py`)

根据用户自然语言输入解析意图，选择对应链路模板，生成有序执行计划。

- **意图解析**: 识别四种链路意图（全流程/资格门槛/性能参数/得分优先）
- **链路模板**: 每种链路预定义了标准执行步骤序列
- **动态调整**: 根据中间结果或异常反馈调整后续步骤
- **关键类**: `AgentPlanner`, `Intent`, `Plan`, `Step`

### 多工具调度器 (`scheduler.py`)

统一管理所有业务工具的注册、调用、容错和日志。

- **工具注册**: 将各业务模块方法注册为可调度工具
- **统一执行**: 按计划依次调用，注入记忆上下文
- **容错机制**: 120s 超时，自动重试 1 次
- **并行调度**: 无依赖步骤支持线程并行
- **关键类**: `ToolScheduler`, `ToolSignature`

### 双层记忆系统 (`memory.py`)

短期会话记忆与长期持久化记忆相结合。

- **SessionMemory**: 当前任务上下文、用户修正、中间结果（内存）
- **LongTermMemory**: 项目历史、修正模式、参数别名、收藏模板（SQLite 4 表）
- **历史搜索**: 按产品线/关键词检索相似历史记录
- **别名建议**: 基于历史修正自动推荐参数别名
- **关键类**: `MemoryManager`, `SessionMemory`, `LongTermMemory`

### 异常自主处理器 (`exception_handler.py`)

检测执行过程中的异常，根据策略矩阵选择处理方式。

- **7 种异常类型**: 参数缺失、语义模糊、估值不符、格式错误、重复冲突、版本冲突、系统异常
- **策略矩阵**: `retry_or_prompt` / `ask_user` / `skip_and_notify` / `ask_user_select` / `retry_or_skip` / `immediate_alert`
- **询问构造**: 基于上下文生成自然语言异常询问
- **高危预警**: 评分决策阶段异常即时告警
- **关键类**: `ExceptionHandler`, `AnomalyType`, `AnomalyResult`

### 结果自校验器 (`self_validator.py`)

对分析结果进行完整性校验，确保输出质量。

- **覆盖率检查**: 招标参数覆盖率 95%+，评分覆盖率 100%+
- **缺漏识别**: 定位未匹配/未评分的参数条目
- **自动补跑**: 触发缺失参数的补充匹配流程
- **关键类**: `SelfValidator`, `ValidationReport`, `MissingItem`

## 公开导出

```python
from agent import (
    AgentPlanner, Intent, Plan, Step,          # 规划
    ToolScheduler, ToolSignature,               # 调度
    MemoryManager, SessionMemory, LongTermMemory, # 记忆
    ExceptionHandler, AnomalyType, AnomalyResult, # 异常
    SelfValidator, ValidationReport, MissingItem, # 校验
)
```
