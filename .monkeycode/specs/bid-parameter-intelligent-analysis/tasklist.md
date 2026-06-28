# 需求实施计划

- [x] 1. 设置项目结构与核心配置
   - 在 `/workspace/bid-param-analyzer/` 创建完整目录结构（config/ parsers/ database/ engine/ reports/ storage/ tests/）
   - 创建 `config/settings.py`，定义全局配置项：OCR 引擎类型、语义匹配相似度阈值(0.85)、文件大小上限(200MB)、页数上限(200页)、临时文件有效期(72h)、数据库路径
   - 创建 `config/product_lines.yaml`，定义至少 2 条产品线及其参数模板（参考 REQ-2, REQ-9.1）
   - 创建 `config/scoring_templates/` 目录并写入默认评分模板 JSON 文件（参考 REQ-9.2）
   - 创建 `requirements.txt`，声明依赖：openpyxl、python-docx、Jinja2、reportlab、numpy、pytest

- [ ] 2. 实现数据库数据模型与初始化
  - [ ] 2.1 在 `database/models.py` 中定义 SQLAlchemy/原生 SQL 数据模型：ProductLine、ProductVersion、ParameterRecord、EvidenceIndex、AnalysisTask、ParsedParameter、DeviationResult、ScoreResult（参考设计文档 Data Models 章节与 REQ-2.1）
  - [ ] 2.2 在 `database/migrations.py` 中实现 `init_db()` 和 `migrate()` 函数，自动建表与版本迁移
  - [ ] 2.3 在 `database/repository.py` 中实现 `create_product_line(name, description)` 和 `get_active_params(product_line_id)`（参考 REQ-2.1, REQ-2.2）
  - [ ]* 2.4 为数据模型编写单元测试 — 验证 ProductLine/ProductVersion/ParameterRecord 的创建、查询、级联关系

- [ ] 3. 实现产品参数基准库 CRUD 与版本管理
  - [ ] 3.1 在 `database/repository.py` 中实现 `switch_version(product_line_id, version_id)`、`get_version_history(product_line_id)`、`get_version_params(version_id)` — 支持不少于 3 个历史版本切换（参考 REQ-2.2）
  - [ ] 3.2 实现 `import_from_excel(file_path)` — 解析 Excel 格式参数文件，校验必填字段（参数名称、标称值、单位）与数值类型合法性，批量写入 ParameterRecord（参考 REQ-2.3, 设计文档 Correctness Properties 输入校验规则）
  - [ ] 3.3 实现 `export_to_excel(version_id, output_path)` — 将指定版本所有参数导出为 Excel 文件，包含所有参数字段与版本信息（参考 REQ-2.4）
  - [ ] 3.4 实现 `update_parameter(param_id, updates)` 与 `add_alias(param_id, alias)` — 单条参数更新与别名管理（参考 REQ-9.1, 设计文档 semantic_matcher 别名匹配策略）

- [ ] 4. 检查点 — 参数库模块功能验证
  - 运行 `python -c "from database.repository import *; import tempfile; ..."` 验证 Excel 导入导出、版本切换、CRUD 操作可正常执行

- [ ] 5. 实现招标文件解析模块
  - [ ] 5.1 在 `parsers/doc_parser.py` 中实现 `parse_pdf(file_path)` — 调用 docparse 解析 PDF 文件，返回全文文本与表格数据数组（参考 REQ-1.1）
  - [ ] 5.2 实现 `parse_docx(file_path)` — 调用 docparse 解析 Word 文件，返回全文文本与表格数据数组（参考 REQ-1.2）
  - [ ] 5.3 实现 `detect_scan_type(file_path)` — 判断文件是否为图片扫描件，扫描件触发平台内置 OCR 路径（参考 REQ-1.3）
  - [ ] 5.4 实现 `extract_tables(text_or_parsed_data)` — 将 docparse 返回的表格数据转换为标准行列结构，保持合并单元格信息（参考 REQ-1.5）

- [ ] 6. 实现结构化参数提取器
  - [ ] 6.1 在 `parsers/table_extractor.py` 中实现 `locate_key_sections(full_text)` — 基于章节标题关键词匹配（技术参数、技术规格、评分、资格、门槛等）定位技术参数章节、评分细则表、资格门槛条款的起始/结束位置，返回 Section 列表（参考 REQ-1.4）
  - [ ] 6.2 实现 `extract_parameters(section_text)` — 从技术参数章节逐行/逐行解析参数条目，输出 ParameterItem 列表，包含参数名称、要求值、单位、参数类型推断（数值/枚举/布尔/功能描述）、层级从属关系（parent_id/children）（参考 REQ-1.5, REQ-1.6）
  - [ ] 6.3 实现 `detect_star_items(params)` — 识别参数名称或描述中标记为 * 号/★的实质性条款，设置 `is_material=True`（参考 REQ-1.6）
  - [ ] 6.4 实现 `extract_scoring_rules(rules_section)` — 从评分细则章节提取评分规则，返回 ScoringRule 列表（参考 REQ-4.1）

- [ ] 7. 检查点 — 文档解析模块功能验证
  - 使用 `tests/fixtures/bid_docs/` 下的样本文件验证 PDF/Word 解析、章节定位、参数提取、* 号识别

- [ ] 8. 实现参数符合性比对引擎
  - [ ] 8.1 在 `engine/semantic_matcher.py` 中实现 `calculate_similarity(name1, name2)` — 调用平台内置 embedding 服务获取向量并计算余弦相似度（参考 REQ-3.1, 设计文档语义匹配器）
  - [ ] 8.2 实现 `match_parameters(bid_params, product_params)` — 执行四级匹配策略（精确匹配、别名匹配、向量匹配≥0.85、人工兜底），返回匹配对列表和未匹配项清单（参考 REQ-3.1, 设计文档语义匹配器匹配策略）
  - [ ] 8.3 在 `engine/deviation_judge.py` 中实现 `judge(bid_param, product_param)` — 按参数类型（数值范围、枚举值、布尔型、功能性描述）执行偏离判定逻辑，返回 DeviationResult（参考 REQ-3.2, REQ-3.3, 设计文档偏离判定器）
  - [ ] 8.4 实现 `batch_judge(matched_pairs)` — 批量判定所有参数对的偏离状态（参考 REQ-3.3）
  - [ ] 8.5 实现 `classify_risk(deviation_result)` — 风险分级：实质性条款负偏离/无法确认标记为废标级风险；普通参数负偏离标记为得分扣分项（参考 REQ-3.4, REQ-3.5）
  - [ ] 8.6 在 `reports/deviation_table.py` 中实现 `generate_deviation_table(task_id, output_format)` — 输出标准格式参数偏离表（招标要求、投标响应、偏离说明、备注），支持 Word 格式（参考 REQ-3.6, REQ-5.4）

- [ ] 9. 实现技术得分估算模块
  - [ ] 9.1 在 `parsers/scoring_rule_parser.py` 中实现评分规则解析 — 将 `extract_scoring_rules` 的原始输出转换为 ScoringRule 结构化对象，区分 QUANTITATIVE/QUALITATIVE 两种规则类型，解析 Condition 列表（参考 REQ-4.1, 设计文档评分规则模型）
  - [ ] 9.2 在 `engine/score_calculator.py` 中实现 `calculate_item_score(rule, deviation)` — 按评分规则类型（定量/定性）与条件操作符（EQ/GT/LT/GTE/LTE/CONTAINS）计算单项得分（参考 REQ-4.2, 设计文档得分计算器）
  - [ ] 9.3 实现 `calculate_scoring(scoring_rules, deviation_table)` — 遍历所有评分规则，逐项映射评分项与产品参数偏差结果，计算所有得分（参考 REQ-4.2）
  - [ ] 9.4 实现 `aggregate_scores(item_scores)` — 汇总技术部分预估总分与得分率，输出总分、满分、得分率（参考 REQ-4.3）
  - [ ] 9.5 实现 `trace_score(score_id)` — 返回得分关联的参数依据、评分标准原文、产品参数来源，构建追溯链路（参考 REQ-4.4）
  - [ ] 9.6 实现 `mark_improvement_items(scores, deviation_table)` — 标记可通过补充材料或参数优化提升得分的高价值评分项（参考 REQ-4.5）

- [ ] 10. 检查点 — 比对与得分引擎功能验证
  - 使用 fixture 数据验证语义匹配准确率、偏离判定逻辑、得分计算汇总与溯源链路

- [ ] 11. 实现投标决策推理引擎
  - [ ] 11.1 在 `engine/decision_engine.py` 中实现 `derive_decision(task_result)` — 基于废标风险数量与得分率输出三级结论（建议投标/谨慎投标/不建议投标）（参考 REQ-5.1, 设计文档决策逻辑与 Correctness Properties 风险传递不变式）
  - [ ] 11.2 实现 `generate_advantage_list(deviation_table)` — 生成正偏离项清单（参考 REQ-5.2）
  - [ ] 11.3 实现 `generate_risk_list(deviation_table, scores)` — 生成风险项清单，包含废标风险、得分短板、资质门槛三类（参考 REQ-5.2）
  - [ ] 11.4 实现 `generate_suggestions(risk_list, improvement_items)` — 生成落地建议：参数优化方向、证明材料准备清单、答疑澄清要点、报价策略参考（参考 REQ-5.3）
  - [ ] 11.5 实现 `competitive_assessment(deviation_table, scores)` — 基于正负偏离比例与得分率输出竞争维度评估（参考 REQ-5.2）

- [ ] 12. 实现投标分析报告生成模块
  - [ ] 12.1 在 `reports/analysis_report.py` 中创建 Jinja2 模板 `templates/analysis_report.docx.j2` — 完整投标分析报告模板，包含决策结论、全景分析、落地建议、偏离表附件（参考 REQ-5.4）
  - [ ] 12.2 实现 `generate_full_report(task_id, output_format)` — 渲染模板生成 Word 格式报告、借助 reportlab 生成 PDF 格式报告（参考 REQ-5.4, REQ-5.5）

- [ ] 13. 实现存储管理模块
  - [ ] 13.1 在 `storage/file_manager.py` 中实现招标文件临时存储管理：保存上传文件到本地目录、记录上传时间、72 小时自动清理逻辑、用户主动清除功能（参考 REQ-8.2, 设计文档文件管理器）
  - [ ] 13.2 在 `storage/history_manager.py` 中实现历史项目管理：保存 AnalysisTask 完整上下文快照、按时间/项目名/产品线检索、从历史记录恢复会话（参考 REQ-6.2, 设计文档历史管理器）

- [ ] 14. 实现任务编排控制器
  - [ ] 14.1 在 `orchestrator.py` 中实现任务状态机 — PENDING → PARSING → PARSE_DONE → COMPARING → COMPARE_DONE → SCORING → SCORE_DONE → ANALYZING → COMPLETED，支持任意步骤转 FAILED/CANCELLED，PARSE_DONE 后支持用户修正回退重入比对（参考设计文档任务状态机, REQ-1.7）
  - [ ] 14.2 实现 `create_task(bid_file_path, product_line)` — 创建任务、初始化上下文、返回 task_id（参考 REQ-6.5, 设计文档编排控制器接口）
  - [ ] 14.3 实现 `execute_step(task_id, step_name)` — 按流程调用各模块执行指定步骤，传入模块所需的中间结果
  - [ ] 14.4 实现 `get_task_state(task_id)` 与 `resume_task(task_id)` — 获取状态/中间结果，恢复历史任务
  - [ ] 14.5 在编排流程中集成进度状态反馈 — 长耗时步骤（文档解析、批量比对）持续输出进度百分比（参考 REQ-6.3）

- [ ] 15. 检查点 — 全链路集成验证
  - 使用完整 fixture 数据执行端到端流程：文件上传 → 参数提取 → 语义匹配 → 偏离判定 → 得分计算 → 决策推理 → 报告生成

- [ ] 16. 实现 MonkeyCode Skill 交互入口
  - [ ] 16.1 在 `skill.py` 中实现 `handle_message(user_input, context)` — 自然语言指令解析与路由：识别上传指令、查询进度指令、修正参数指令、重新计算指令（参考 REQ-6.1, 设计文档 Skill 交互层接口）
  - [ ] 16.2 实现 `handle_file_upload(file_path, file_type)` — 校验文件类型白名单(.pdf/.doc/.docx/.xlsx/.xls)，校验文件大小(≤200MB)，调用 file_manager 存储（参考 REQ-6.5, 设计文档 Correctness Properties 输入校验规则, REQ-8.2）
  - [ ] 16.3 实现 `get_progress(task_id)` 和 `modify_parameter(param_id, edits)` 和 `recalculate(task_id)` — 进度查询、参数修正（编辑/补充/删除）、重新触发比对（参考 REQ-6.1, REQ-1.7）
  - [ ] 16.4 实现分析结果渲染 — 以表格组件展示偏离表、以卡片组件展示决策结论与风险清单、提供文件下载链接（参考 REQ-6.4）

- [ ] 17. 错误处理与边界条件加固
  - [ ] 17.1 在全部模块中按设计文档 Error Handling 表格逐项实现错误处理：招标文件解析失败、OCR 质量过低、语义匹配无结果、产品线无活跃版本、得分规则无法解析、报告导出重试、任务超时、存储空间不足（参考设计文档 Error Handling, REQ-8.2）
  - [ ] 17.2 实现 Correctness Properties 中的比对完整性检查 — 验证每个 ParsedParameter 在 DeviationResult 中有对应记录（参考设计文档 Correctness Properties 不变式 1）
  - [ ] 17.3 实现得分合理性检查 — 验证 0 ≤ actual_score ≤ max_score（参考设计文档 Correctness Properties 不变式 3）

- [ ] 18. 生成测试 fixtures 与测试数据
  - [ ] 18.1 创建 `tests/fixtures/bid_docs/standard.pdf` 和 `standard.docx` — 包含技术参数章节（含 * 号条款）、评分细则表、资格门槛条款的标准招标文件样例
  - [ ] 18.2 创建 `tests/fixtures/bid_docs/scanned.pdf` — 图片扫描件招标文件样例，用于 OCR 路径测试
  - [ ] 18.3 创建 `tests/fixtures/bid_docs/complex_table.docx` — 含多层嵌套表格的招标文件，验证表格解析与层级保留
  - [ ] 18.4 创建 `tests/fixtures/product_db/product_line_a.xlsx` — 完整产品参数库（≥20 条参数，覆盖四种参数类型），含多版本数据
  - [ ] 18.5 创建 `tests/fixtures/product_db/product_line_b_empty.xlsx` — 空参数库边界测试用例
  - [ ] 18.6 创建 `tests/fixtures/scoring_rules/` 下的评分规则 JSON 样例

- [ ]* 19. 编写单元测试
  - [ ]* 19.1 为 `database/repository.py` 所有公开方法编写单元测试（CRUD、版本切换、Excel 导入导出、别名管理）
  - [ ]* 19.2 为 `parsers/doc_parser.py` 编写测试 — PDF/Word 解析、扫描件检测、表格提取
  - [ ]* 19.3 为 `parsers/table_extractor.py` 编写测试 — 章节定位、参数提取、* 号识别、评分规则提取
  - [ ]* 19.4 为 `engine/semantic_matcher.py` 编写测试 — 四种匹配策略覆盖、准确率统计
  - [ ]* 19.5 为 `engine/deviation_judge.py` 编写测试 — 四种参数类型偏离判定、风险分级
  - [ ]* 19.6 为 `engine/score_calculator.py` 编写测试 — 定量/定性打分、汇总、溯源、高价值项标记
  - [ ]* 19.7 为 `engine/decision_engine.py` 编写测试 — 三级决策边界条件、风险传递不变式验证
  - [ ]* 19.8 为 `reports/analysis_report.py` 编写测试 — Word/PDF 报告生成与内容完整性
  - [ ]* 19.9 为 `orchestrator.py` 编写测试 — 完整状态机流转、断点续算

- [ ]* 20. 编写属性测试
  - [ ]* 20.1 编写比对完整性属性测试 — 对所有随机生成的 ParsedParameter 集合，验证 `batch_judge` 输出的 DeviationResult 集合覆盖率 = 100%（参考设计文档 Correctness Properties 不变式 1）
  - [ ]* 20.2 编写得分合理性属性测试 — 对所有随机生成的 ScoringRule 与 DeviationResult 组合，验证 `calculate_item_score` 输出满足 0 ≤ score ≤ max_score（参考设计文档 Correctness Properties 不变式 3）
  - [ ]* 20.3 编写风险传递属性测试 — 验证当存在实质性条款负偏离时，`derive_decision` 必定输出"不建议投标"（参考设计文档 Correctness Properties 不变式 4）
  - [ ]* 20.4 编写版本隔离属性测试 — 验证跨产品版本查询时数据互相隔离（参考设计文档 Correctness Properties 不变式 2 和 5）

- [ ]* 21. 编写集成测试
  - [ ]* 21.1 编写解析端到端集成测试 — 上传招标文件 → doc_parser → table_extractor → 输出 ParsedParameter 列表
  - [ ]* 21.2 编写比对端到端集成测试 — ParsedParameter 列表 + 产品参数 → 语义匹配 → 偏离判定 → 风险分级 → 偏离表
  - [ ]* 21.3 编写得分端到端集成测试 — 偏离表 + 评分规则 → 得分计算 → 汇总 → 溯源
  - [ ]* 21.4 编写报告端到端集成测试 — 全部中间结果 → 决策推理 → 报告生成（Word/PDF）
