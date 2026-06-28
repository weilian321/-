# reports/ 模块

投标分析报告生成，输出 Word 格式的参数偏离表和完整的投标分析报告。

## 结构

```
reports/
├── deviation_table.py    # 参数偏离表生成 (Word)
└── analysis_report.py    # 投标分析报告生成 (Word)
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `deviation_table.py` | 生成 6 列标准偏离表（序号/招标要求/投标响应/偏离说明/偏离状态/备注），废标红/负偏离黄/正偏离绿背景色高亮 |
| `analysis_report.py` | 生成 6 章完整报告（决策结论/得分概览/竞争评估/优势项/风险清单/落地建议），含偏离结果附表 |

## 依赖

**本模块依赖**: `config.settings`, `database.models`, `python-docx`

**依赖本模块的**: `orchestrator`, `engine.decision_engine`
