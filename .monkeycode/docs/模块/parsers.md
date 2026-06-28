# parsers/ 模块

招标文件解析与结构化信息提取，将原始文档内容转化为可供引擎处理的结构化数据。

## 结构

```
parsers/
├── doc_parser.py             # PDF/Word/扫描件解析适配层
├── table_extractor.py        # 结构化参数提取器
└── scoring_rule_parser.py    # 评分规则规范化
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `doc_parser.py` | 提供 `parse_pdf`/`parse_docx`/`parse_document` 统一入口，运行时委托 MonkCode docparse 与 OCR |
| `table_extractor.py` | 15 种招标章节模式匹配定位三类区域，参数逐行提取含类型推断，* 号/★实质性条款检测，评分规则原始提取，表格行列自动映射 |
| `scoring_rule_parser.py` | 将原始评分规则转换为 ScoringRule 对象，支持加载和应用评分模板 |

## 依赖

**本模块依赖**: `config.settings`, `database.models`

**依赖本模块的**: `orchestrator`
