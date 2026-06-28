# database/ 模块

SQLite 数据库层，管理产品参数基准库的持久化存储和任务数据。

## 结构

```
database/
├── models.py         # 14 个 dataclass + 5 个枚举
├── migrations.py     # 10 张表 + 10 个索引 + 版本管理
└── repository.py     # 12 个 CRUD 方法
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `models.py` | 定义 ProductLine、ProductVersion、ParameterRecord、EvidenceIndex、AnalysisTask、ParsedParameter、DeviationResult、ScoreResult 等核心实体及 ParamType/DeviationType/RiskLevel/RuleType/TaskStatus 枚举 |
| `migrations.py` | `init_db()` 和 `migrate()` 管理 10 张业务表 + schema_version 版本表 |
| `repository.py` | 完整 CRUD：产品线/版本管理、Excel 导入导出（含字段校验）、参数更新、别名管理 |

## 依赖

**本模块依赖**: `config.settings`, Python stdlib `sqlite3`

**依赖本模块的**: `engine.semantic_matcher`, `storage.history_manager`, `orchestrator`
