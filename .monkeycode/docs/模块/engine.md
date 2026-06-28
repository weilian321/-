# engine/ 模块

核心业务引擎，负责参数语义匹配、偏离判定、技术得分计算和投标决策推理。

## 结构

```
engine/
├── semantic_matcher.py    # 四级语义匹配策略
├── deviation_judge.py     # 四种参数类型偏离判定
├── score_calculator.py    # 技术得分计算与溯源
└── decision_engine.py     # 三级投标决策推理
```

## 关键文件

| 文件 | 目的 |
|------|------|
| `semantic_matcher.py` | 实现精确/别名/向量/人工四级匹配，支持平台 embedding 和本地 Jaccard fallback |
| `deviation_judge.py` | 数值范围（含运算符/区间解析）、枚举、布尔、功能描述四种类型判定，废标级/扣分级风险分级 |
| `score_calculator.py` | 定量/定性双模式打分，6 种条件操作符（EQ/GT/LT/GTE/LTE/CONTAINS），得分 JSON 溯源，高价值提升项标记 |
| `decision_engine.py` | 三级结论输出（建议/谨慎/不建议投标），优势/风险/建议/竞争四维分析 |

## 依赖

**本模块依赖**: `database.models`, `config.settings`, `reports.deviation_table`

**依赖本模块的**: `orchestrator`, `skill`
