# storage/ 模块

文件临时存储与历史任务管理，保障数据安全与可追溯性。

## 结构

```
storage/
├── file_manager.py       # 招标文件临时存储
└── history_manager.py    # 历史任务快照管理
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `file_manager.py` | `save_uploaded_file` 按任务ID组织存储，`cleanup_expired_files` 72小时 TTL 自动清理，`clear_task_files` 用户主动清除 |
| `history_manager.py` | `save_task_snapshot` JSON 上下文快照持久化，`list_tasks` 按产品线/时间检索，`load_task_context` 恢复会话，`delete_task` 级联清理 |

## 依赖

**本模块依赖**: `config.settings`, `database.migrations`, `database.models`

**依赖本模块的**: `orchestrator`, `skill`
