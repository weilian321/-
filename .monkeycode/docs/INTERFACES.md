# 投标参数智能分析 Skill - 接口文档

本文档描述 Skill 各模块的公开接口与数据模型。

---

## Skill 交互层 (`skill.py`)

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `handle_message(user_input, context)` | user_input: str, context: dict | dict | 解析自然语言指令并路由 |
| `handle_file_upload(file_path, file_type)` | file_path: str, file_type: str | dict | 校验并接收招标文件上传 |
| `get_progress(task_id)` | task_id: str | dict | 查询任务执行进度 |
| `modify_parameter(param_id, edits)` | param_id: str, edits: dict | dict | 修正识别参数条目 |
| `recalculate(task_id)` | task_id: str | dict | 基于修正结果重新比对 |

---

## 任务编排控制器 (`orchestrator.py`)

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `create_task(bid_file_path, product_line)` | bid_file_path: str, product_line: str | str (task_id) | 创建分析任务 |
| `execute_step(task_id, step_name)` | task_id: str, step_name: str | dict | 执行指定步骤 |
| `get_task_state(task_id)` | task_id: str | dict | 获取任务状态与中间结果 |
| `resume_task(task_id)` | task_id: str | dict | 恢复历史任务 |

---

## 文档解析模块

### `doc_parser.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `parse_pdf(file_path)` | file_path: str | ParsedDocument | 解析PDF招标文件 |
| `parse_docx(file_path)` | file_path: str | ParsedDocument | 解析Word招标文件 |
| `detect_scan_type(file_path)` | file_path: str | bool | 判断是否为扫描件 |
| `extract_tables(text)` | text: ParsedDocument | list[TableData] | 提取表格结构 |

### `table_extractor.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `locate_key_sections(full_text)` | full_text: str | list[Section] | 定位关键章节 |
| `extract_parameters(section_text)` | section_text: str | list[ParameterItem] | 提取参数条目 |
| `extract_scoring_rules(rules_section)` | rules_section: str | list[ScoringRule] | 提取评分规则 |
| `detect_star_items(params)` | params: list[ParameterItem] | list[ParameterItem] | 识别*号条款 |

---

## 数据库模块

### `repository.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `create_product_line(name, description)` | name: str, description: str | ProductLine | 新增产品线 |
| `get_active_params(product_line_id)` | product_line_id: str | list[ParameterRecord] | 获取活跃版本参数 |
| `get_version_params(version_id)` | version_id: str | list[ParameterRecord] | 获取指定版本参数 |
| `switch_version(product_line_id, version_id)` | product_line_id: str, version_id: str | bool | 切换活跃版本 |
| `get_version_history(product_line_id)` | product_line_id: str | list[ProductVersion] | 获取版本历史 |
| `import_from_excel(file_path)` | file_path: str | ImportResult | 批量导入Excel |
| `export_to_excel(version_id, output_path)` | version_id: str, output_path: str | str | 导出Excel |
| `update_parameter(param_id, updates)` | param_id: str, updates: dict | ParameterRecord | 更新单条参数 |
| `add_alias(param_id, alias)` | param_id: str, alias: str | bool | 添加参数别名 |

---

## 核心引擎

### `semantic_matcher.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `match_parameters(bid_params, product_params)` | bid_params: list, product_params: list | MatchResult | 全量参数匹配 |
| `calculate_similarity(name1, name2)` | name1: str, name2: str | float | 计算余弦相似度 |
| `add_alias(param_id, alias)` | param_id: str, alias: str | bool | 添加别名 |

### `deviation_judge.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `judge(bid_param, product_param)` | bid_param: ParameterItem, product_param: ParameterRecord | DeviationResult | 单条偏离判定 |
| `batch_judge(matched_pairs)` | matched_pairs: list[MatchPair] | list[DeviationResult] | 批量判定 |
| `classify_risk(deviation_result)` | deviation_result: DeviationResult | RiskLevel | 风险分级 |

### `score_calculator.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `calculate_scoring(scoring_rules, deviation_table)` | scoring_rules: list, deviation_table: list | ScoreSummary | 全量得分计算 |
| `calculate_item_score(rule, deviation)` | rule: ScoringRule, deviation: DeviationResult | float | 单项得分计算 |
| `aggregate_scores(item_scores)` | item_scores: list | ScoreSummary | 得分汇总 |
| `mark_improvement_items(scores, deviation_table)` | scores: list, deviation_table: list | list | 标记提升项 |
| `trace_score(score_id)` | score_id: str | TraceResult | 得分溯源 |

### `decision_engine.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `derive_decision(task_result)` | task_result: TaskResult | DecisionResult | 输出决策结论 |
| `generate_advantage_list(deviation_table)` | deviation_table: list | list | 生成优势清单 |
| `generate_risk_list(deviation_table, scores)` | deviation_table: list, scores: list | RiskReport | 生成风险清单 |
| `generate_suggestions(risk_list, improvement_items)` | risk_list: list, improvement_items: list | Suggestions | 生成落地建议 |
| `competitive_assessment(deviation_table, scores)` | deviation_table: list, scores: list | dict | 竞争维度评估 |

---

## 报告模块

### `reports/analysis_report.py`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `generate_deviation_table(task_id, output_format)` | task_id: str, output_format: str | str | 生成偏离表文件路径 |
| `generate_full_report(task_id, output_format)` | task_id: str, output_format: str | str | 生成完整分析报告路径 |

---

## 核心数据模型

### ParameterItem (招标参数)

```python
@dataclass
class ParameterItem:
    id: str                    # 唯一标识
    name: str                  # 参数名称
    requirement_value: str     # 要求值
    unit: str                  # 单位
    is_material: bool          # 是否为实质性条款
    param_type: ParamType      # 数值/枚举/布尔/功能描述
    source_location: str       # 页码/段落
    parent_id: Optional[str]   # 父级参数ID
    children: list[str]        # 子级参数ID列表
```

### ParameterRecord (产品参数)

```python
@dataclass
class ParameterRecord:
    id: str
    version_id: str
    name: str
    nominal_value: str
    acceptable_range: str
    unit: str
    deviation_preset: str
    category: str
```

### DeviationResult (偏离结果)

```python
@dataclass
class DeviationResult:
    id: str
    parsed_param_id: str
    match_param_id: str
    deviation_type: str       # 正偏离/无偏离/负偏离/无法确认
    similarity_score: float
    explanation: str
    risk_level: str            # 废标级风险/得分扣分项/无风险
    suggestion: str
```

### ScoringRule (评分规则)

```python
@dataclass
class ScoringRule:
    id: str
    name: str
    max_score: float
    rule_type: RuleType        # QUANTITATIVE / QUALITATIVE
    conditions: list[Condition]
    bonus_rules: list[BonusRule]
    penalty_rules: list[PenaltyRule]
```
