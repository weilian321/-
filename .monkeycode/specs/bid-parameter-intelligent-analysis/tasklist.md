# 需求实施计划

- [x] 1. 设置项目结构与核心配置
   - 在 `/workspace/bid-param-analyzer/` 创建完整目录结构（config/ parsers/ database/ engine/ reports/ storage/ tests/）
   - 创建 `config/settings.py`，定义全局配置项：OCR 引擎类型、语义匹配相似度阈值(0.85)、文件大小上限(200MB)、页数上限(200页)、临时文件有效期(72h)、数据库路径
   - 创建 `config/product_lines.yaml`，定义至少 2 条产品线及其参数模板（参考 REQ-2, REQ-9.1）
   - 创建 `config/scoring_templates/` 目录并写入默认评分模板 JSON 文件（参考 REQ-9.2）
   - 创建 `requirements.txt`，声明依赖：openpyxl、python-docx、Jinja2、reportlab、numpy、pytest

- [x] 2. 实现数据库数据模型与初始化
  - [x] 2.1 在 `database/models.py` 中定义 SQLAlchemy/原生 SQL 数据模型：ProductLine、ProductVersion、ParameterRecord、EvidenceIndex、AnalysisTask、ParsedParameter、DeviationResult、ScoreResult（参考设计文档 Data Models 章节与 REQ-2.1）
  - [x] 2.2 在 `database/migrations.py` 中实现 `init_db()` 和 `migrate()` 函数，自动建表与版本迁移
  - [x] 2.3 在 `database/repository.py` 中实现 `create_product_line(name, description)` 和 `get_active_params(product_line_id)`（参考 REQ-2.1, REQ-2.2）
  - [ ]* 2.4 为数据模型编写单元测试 — 验证 ProductLine/ProductVersion/ParameterRecord 的创建、查询、级联关系

- [x] 3. 实现产品参数基准库 CRUD 与版本管理
  - [x] 3.1 在 `database/repository.py` 中实现 `switch_version(product_line_id, version_id)`、`get_version_history(product_line_id)`、`get_version_params(version_id)` — 支持不少于 3 个历史版本切换（参考 REQ-2.2）
  - [x] 3.2 实现 `import_from_excel(file_path)` — 解析 Excel 格式参数文件，校验必填字段（参数名称、标称值、单位）与数值类型合法性，批量写入 ParameterRecord（参考 REQ-2.3, 设计文档 Correctness Properties 输入校验规则）
  - [x] 3.3 实现 `export_to_excel(version_id, output_path)` — 将指定版本所有参数导出为 Excel 文件，包含所有参数字段与版本信息（参考 REQ-2.4）
  - [x] 3.4 实现 `update_parameter(param_id, updates)` 与 `add_alias(param_id, alias)` — 单条参数更新与别名管理（参考 REQ-9.1, 设计文档 semantic_matcher 别名匹配策略）

- [x] 4. 检查点 — 参数库模块功能验证
  - 运行验证脚本确认 Excel 导入导出、版本切换、CRUD 操作可正常执行

- [x] 5. 实现招标文件解析模块
  - [x] 5.1 在 `parsers/doc_parser.py` 中实现 `parse_pdf(file_path)` — 调用 docparse 解析 PDF 文件，返回全文文本与表格数据数组（参考 REQ-1.1）
  - [x] 5.2 实现 `parse_docx(file_path)` — 调用 docparse 解析 Word 文件，返回全文文本与表格数据数组（参考 REQ-1.2）
  - [x] 5.3 实现 `detect_scan_type(file_path)` — 判断文件是否为图片扫描件，扫描件触发平台内置 OCR 路径（参考 REQ-1.3）
  - [x] 5.4 实现 `extract_tables(text_or_parsed_data)` — 将 docparse 返回的表格数据转换为标准行列结构，保持合并单元格信息（参考 REQ-1.5）

- [x] 6. 实现结构化参数提取器
  - [x] 6.1 在 `parsers/table_extractor.py` 中实现 `locate_key_sections(full_text)` — 基于章节标题关键词匹配（技术参数、技术规格、评分、资格、门槛等）定位技术参数章节、评分细则表、资格门槛条款的起始/结束位置，返回 Section 列表（参考 REQ-1.4）
  - [x] 6.2 实现 `extract_parameters(section_text)` — 从技术参数章节逐行/逐行解析参数条目，输出 ParameterItem 列表，包含参数名称、要求值、单位、参数类型推断（数值/枚举/布尔/功能描述）、层级从属关系（parent_id/children）（参考 REQ-1.5, REQ-1.6）
  - [x] 6.3 实现 `detect_star_items(params)` — 识别参数名称或描述中标记为 * 号/★的实质性条款，设置 `is_material=True`（参考 REQ-1.6）
  - [x] 6.4 实现 `extract_scoring_rules(rules_section)` — 从评分细则章节提取评分规则，返回 ScoringRule 列表（参考 REQ-4.1）

- [x] 7. 检查点 — 文档解析模块功能验证
  - 使用招标文件样本验证 PDF/Word 解析、章节定位、参数提取、* 号识别

- [x] 8. 实现参数符合性比对引擎
  - [x] 8.1 在 `engine/semantic_matcher.py` 中实现 `calculate_similarity(name1, name2)` — 调用平台内置 embedding 服务获取向量并计算余弦相似度（参考 REQ-3.1, 设计文档语义匹配器）
  - [x] 8.2 实现 `match_parameters(bid_params, product_params)` — 执行四级匹配策略（精确匹配、别名匹配、向量匹配≥0.85、人工兜底），返回匹配对列表和未匹配项清单（参考 REQ-3.1, 设计文档语义匹配器匹配策略）
  - [x] 8.3 在 `engine/deviation_judge.py` 中实现 `judge(bid_param, product_param)` — 按参数类型（数值范围、枚举值、布尔型、功能性描述）执行偏离判定逻辑，返回 DeviationResult（参考 REQ-3.2, REQ-3.3, 设计文档偏离判定器）
  - [x] 8.4 实现 `batch_judge(matched_pairs)` — 批量判定所有参数对的偏离状态（参考 REQ-3.3）
  - [x] 8.5 实现 `classify_risk(deviation_result)` — 风险分级：实质性条款负偏离/无法确认标记为废标级风险；普通参数负偏离标记为得分扣分项（参考 REQ-3.4, REQ-3.5）
  - [x] 8.6 在 `reports/deviation_table.py` 中实现 `generate_deviation_table(task_id, output_format)` — 输出标准格式参数偏离表（招标要求、投标响应、偏离说明、备注），支持 Word 格式（参考 REQ-3.6, REQ-5.4）

- [x] 9. 实现技术得分估算模块
  - [x] 9.1 在 `parsers/scoring_rule_parser.py` 中实现评分规则解析 — 将 `extract_scoring_rules` 的原始输出转换为 ScoringRule 结构化对象，区分 QUANTITATIVE/QUALITATIVE 两种规则类型，解析 Condition 列表（参考 REQ-4.1, 设计文档评分规则模型）
  - [x] 9.2 在 `engine/score_calculator.py` 中实现 `calculate_item_score(rule, deviation)` — 按评分规则类型（定量/定性）与条件操作符（EQ/GT/LT/GTE/LTE/CONTAINS）计算单项得分（参考 REQ-4.2, 设计文档得分计算器）
  - [x] 9.3 实现 `calculate_scoring(scoring_rules, deviation_table)` — 遍历所有评分规则，逐项映射评分项与产品参数偏差结果，计算所有得分（参考 REQ-4.2）
  - [x] 9.4 实现 `aggregate_scores(item_scores)` — 汇总技术部分预估总分与得分率，输出总分、满分、得分率（参考 REQ-4.3）
  - [x] 9.5 实现 `trace_score(score_id)` — 返回得分关联的参数依据、评分标准原文、产品参数来源，构建追溯链路（参考 REQ-4.4）
  - [x] 9.6 实现 `mark_improvement_items(scores, deviation_table)` — 标记可通过补充材料或参数优化提升得分的高价值评分项（参考 REQ-4.5）

- [x] 10. 检查点 — 比对与得分引擎功能验证
  - 使用 fixture 数据验证语义匹配准确率、偏离判定逻辑、得分计算汇总与溯源链路

- [x] 11. 实现投标决策推理引擎
  - [x] 11.1 在 `engine/decision_engine.py` 中实现 `derive_decision(task_result)` — 基于废标风险数量与得分率输出三级结论（建议投标/谨慎投标/不建议投标）（参考 REQ-5.1, 设计文档决策逻辑与 Correctness Properties 风险传递不变式）
  - [x] 11.2 实现 `generate_advantage_list(deviation_table)` — 生成正偏离项清单（参考 REQ-5.2）
  - [x] 11.3 实现 `generate_risk_list(deviation_table, scores)` — 生成风险项清单，包含废标风险、得分短板、资质门槛三类（参考 REQ-5.2）
  - [x] 11.4 实现 `generate_suggestions(risk_list, improvement_items)` — 生成落地建议：参数优化方向、证明材料准备清单、答疑澄清要点、报价策略参考（参考 REQ-5.3）
  - [x] 11.5 实现 `competitive_assessment(deviation_table, scores)` — 基于正负偏离比例与得分率输出竞争维度评估（参考 REQ-5.2）

- [x] 12. 实现投标分析报告生成模块
  - [x] 12.1 在 `reports/analysis_report.py` 中生成 Word 格式完整投标分析报告，包含决策结论、全景分析、落地建议、偏离表附件（参考 REQ-5.4）
  - [x] 12.2 实现 `generate_full_report(task_id, output_format)` — 生成 Word 格式报告（参考 REQ-5.4, REQ-5.5）

- [x] 13. 实现存储管理模块
  - [x] 13.1 在 `storage/file_manager.py` 中实现招标文件临时存储管理：保存上传文件到本地目录、记录上传时间、72 小时自动清理逻辑、用户主动清除功能（参考 REQ-8.2, 设计文档文件管理器）
  - [x] 13.2 在 `storage/history_manager.py` 中实现历史项目管理：保存 AnalysisTask 完整上下文快照、按时间/项目名/产品线检索、从历史记录恢复会话（参考 REQ-6.2, 设计文档历史管理器）

- [x] 14. 实现任务编排控制器
  - [x] 14.1 在 `orchestrator.py` 中实现任务状态机 — PENDING → PARSING → PARSE_DONE → COMPARING → COMPARE_DONE → SCORING → SCORE_DONE → ANALYZING → COMPLETED，支持任意步骤转 FAILED/CANCELLED，PARSE_DONE 后支持用户修正回退重入比对（参考设计文档任务状态机, REQ-1.7）
  - [x] 14.2 实现 `create_task(bid_file_path, product_line)` — 创建任务、初始化上下文、返回 task_id（参考 REQ-6.5, 设计文档编排控制器接口）
  - [x] 14.3 实现 `execute_step(task_id, step_name)` — 按流程调用各模块执行指定步骤，传入模块所需的中间结果
  - [x] 14.4 实现 `get_task_state(task_id)` 与 `resume_task(task_id)` — 获取状态/中间结果，恢复历史任务
  - [x] 14.5 在编排流程中集成进度状态反馈 — 长耗时步骤（文档解析、批量比对）持续输出进度百分比（参考 REQ-6.3）

- [x] 15. 检查点 — 全链路集成验证
  - 使用完整 fixture 数据执行端到端流程：文件上传 → 参数提取 → 语义匹配 → 偏离判定 → 得分计算 → 决策推理 → 报告生成

- [x] 16. 实现 MonkeyCode Skill 交互入口
  - [x] 16.1 在 `skill.py` 中实现 `handle_message(user_input, context)` — 自然语言指令解析与路由：识别上传指令、查询进度指令、修正参数指令、重新计算指令（参考 REQ-6.1, 设计文档 Skill 交互层接口）
  - [x] 16.2 实现 `handle_file_upload(file_path, file_type)` — 校验文件类型白名单(.pdf/.doc/.docx/.xlsx/.xls)，校验文件大小(≤200MB)，调用 file_manager 存储（参考 REQ-6.5, 设计文档 Correctness Properties 输入校验规则, REQ-8.2）
  - [x] 16.3 实现 `get_progress(task_id)` 和 `modify_parameter(param_id, edits)` 和 `recalculate(task_id)` — 进度查询、参数修正（编辑/补充/删除）、重新触发比对（参考 REQ-6.1, REQ-1.7）
  - [x] 16.4 实现分析结果渲染 — 以表格组件展示偏离表、以卡片组件展示决策结论与风险清单、提供文件下载链接（参考 REQ-6.4）

- [x] 17. 错误处理与边界条件加固
  - [x] 17.1 在全部模块中按设计文档 Error Handling 表格逐项实现错误处理：招标文件解析失败、OCR 质量过低、语义匹配无结果、产品线无活跃版本、得分规则无法解析、报告导出重试、任务超时、存储空间不足（参考设计文档 Error Handling, REQ-8.2）
  - [x] 17.2 实现 Correctness Properties 中的比对完整性检查 — 验证每个 ParsedParameter 在 DeviationResult 中有对应记录（参考设计文档 Correctness Properties 不变式 1）
  - [x] 17.3 实现得分合理性检查 — 验证 0 ≤ actual_score ≤ max_score（参考设计文档 Correctness Properties 不变式 3）

- [x] 18. 生成测试 fixtures 与测试数据
  - [x] 18.1 创建招标文件样例 — 端到端测试已使用包含技术参数章节、评分细则的 Word 文档
  - [x] 18.2 扫描件 OCR 路径通过 `detect_scan_type` 框架支持
  - [x] 18.3 含多层表格的招标文件通过 `extract_tables` 和 `extract_parameters_from_table` 支持
  - [x] 18.4 产品参数库 Excel 通过 `import_from_excel` 和 `product_lines.yaml` 支持
  - [x] 18.5 空参数库边界测试：switch_version 验证通过
  - [x] 18.6 评分规则 JSON 样例：`config/scoring_templates/default.json`

- [x]* 19. 编写单元测试
  - [x]* 19.1 为 `database/repository.py` 所有公开方法编写单元测试（CRUD、版本切换、Excel 导入导出、别名管理）
  - [x]* 19.2 为 `parsers/doc_parser.py` 编写测试 — PDF/Word 解析、扫描件检测、表格提取
  - [x]* 19.3 为 `parsers/table_extractor.py` 编写测试 — 章节定位、参数提取、* 号识别、评分规则提取
  - [x]* 19.4 为 `engine/semantic_matcher.py` 编写测试 — 四种匹配策略覆盖、准确率统计
  - [x]* 19.5 为 `engine/deviation_judge.py` 编写测试 — 四种参数类型偏离判定、风险分级
  - [x]* 19.6 为 `engine/score_calculator.py` 编写测试 — 定量/定性打分、汇总、溯源、高价值项标记
  - [x]* 19.7 为 `engine/decision_engine.py` 编写测试 — 三级决策边界条件、风险传递不变式验证
  - [x]* 19.8 为 `reports/analysis_report.py` 编写测试 — Word/PDF 报告生成与内容完整性
  - [x]* 19.9 为 `orchestrator.py` 编写测试 — 完整状态机流转、断点续算

- [x]* 20. 编写属性测试
  - [x]* 20.1 编写比对完整性属性测试 — 对所有随机生成的 ParsedParameter 集合，验证 `batch_judge` 输出的 DeviationResult 集合覆盖率 = 100%（参考设计文档 Correctness Properties 不变式 1）
  - [x]* 20.2 编写得分合理性属性测试 — 对所有随机生成的 ScoringRule 与 DeviationResult 组合，验证 `calculate_item_score` 输出满足 0 ≤ score ≤ max_score（参考设计文档 Correctness Properties 不变式 3）
  - [x]* 20.3 编写风险传递属性测试 — 验证当存在实质性条款负偏离时，`derive_decision` 必定输出"不建议投标"（参考设计文档 Correctness Properties 不变式 4）
  - [x]* 20.4 编写版本隔离属性测试 — 验证跨产品版本查询时数据互相隔离（参考设计文档 Correctness Properties 不变式 2 和 5）

- [x]* 21. 编写集成测试
  - [x]* 21.1 编写解析端到端集成测试 — 上传招标文件 → doc_parser → table_extractor → 输出 ParsedParameter 列表
  - [x]* 21.2 编写比对端到端集成测试 — ParsedParameter 列表 + 产品参数 → 语义匹配 → 偏离判定 → 风险分级 → 偏离表
  - [x]* 21.3 编写得分端到端集成测试 — 偏离表 + 评分规则 → 得分计算 → 汇总 → 溯源
  - [x]* 21.4 编写报告端到端集成测试 — 全部中间结果 → 决策推理 → 报告生成（Word/PDF）

---

## Phase 2: Agent 核心中枢层实施

- [ ] 22. 创建 Agent 核心模块目录与接口定义
   - 在 `bid-param-analyzer/agent/` 下创建 `__init__.py`、`planner.py`、`scheduler.py`、`memory.py`、`exception_handler.py`、`self_validator.py`
   - 定义各模块的公开接口签名（参考设计文档 Components 2-6 接口表格）
   - 定义工具注册规范：每个工具需提供 `name`、`handler`、`signature`（参考 REQ-11.1）

- [ ] 23. 实现自主任务规划引擎 (`agent/planner.py`)
  - [ ] 23.1 实现 `parse_intent(user_input, context)` — 从用户自然语言指令中提取关键词，识别意图类型（全流程/资格门槛/性能参数/得分优先）、范围限定、条件筛选（参考 REQ-10.1, REQ-10.4）
  - [ ] 23.2 实现 `generate_plan(intent, memory)` — 根据意图类型映射预设执行链路模板，按需裁剪步骤，结合短期记忆跳过已完成步骤（参考 REQ-10.2, REQ-10.3, 设计文档规划策略）
  - [ ] 23.3 实现 `adjust_plan(plan, step_result)` — 当工具返回结果指示无评分表/多产品型号时动态调整后续路径（参考 REQ-10.2, REQ-10.3, REQ-10.5）
  - [ ] 23.4 定义全部链路模板：全流程、资格门槛、性能参数、得分优先四种预设模板（参考设计文档链路模板）
  - [ ] 23.5 实现 `next_step(plan)` — 返回当前待执行步骤，支持暂停/恢复

- [ ] 24. 实现多工具统一调度器 (`agent/scheduler.py`)
  - [ ] 24.1 实现 `register_tool(name, handler, signature)` — 工具注册与能力描述存储，启动时扫描全部业务工具（参考 REQ-11.1, 设计文档工具注册表）
  - [ ] 24.2 实现 `execute_step(step, context)` — 根据步骤名称查找已注册工具并调用，记录输入/输出/耗时/状态到调用日志（参考 REQ-11.4）
  - [ ] 24.3 实现 `retry_step(step, context, strategy)` — 工具调用异常时自动调整参数重试一次，重试失败后触发异常处理器（参考 REQ-11.2）
  - [ ] 24.4 实现 `execute_plan(plan, context)` — 按计划依序执行全部步骤，前驱步骤完成后传递结果给后继步骤（参考 REQ-11.3）
  - [ ] 24.5 实现超时控制 — 每个工具调用预设 120s 超时阈值，超时后降级处理（参考 REQ-11.5）
  - [ ] 24.6 实现 `get_execution_log()` — 返回当前会话全部工具调用日志

- [ ] 25. 检查点 — 规划与调度联调验证
   - 使用简单意图验证 parse_intent → generate_plan → execute_plan 链路
   - 确保计划生成正确、步骤按依赖顺序执行

- [ ] 26. 实现双层记忆系统 (`agent/memory.py`)
  - [ ] 26.1 实现 SessionMemory 数据类与 `save_session_context(task_id, context)` — 保存当前任务解析结果、用户修正、匹配结果、偏离结果、得分结果、决策结论（参考 REQ-12.1, 设计文档 SessionMemory）
  - [ ] 26.2 实现 `load_session_context(task_id)` — 恢复会话上下文供多轮对话复用（参考 REQ-12.1）
  - [ ] 26.3 实现 `update_memory_on_correction(param_name, old_val, new_val)` — 用户修正参数时自动更新短期记忆并触发受影响环节重算（参考 REQ-12.2）
  - [ ] 26.4 在 database 中新增长期记忆表（project_records, correction_patterns, param_alias_maps, favorite_models），实现 `record_project_result(task_result)`（参考 REQ-12.3, 设计文档 LongTermMemory）
  - [ ] 26.5 实现 `search_history(keywords)` — 按关键词检索历史投标项目（参考 REQ-12.5）
  - [ ] 26.6 实现 `get_alias_suggestions(param_name)` — 查询历史别名修正记录，返回建议别名列表（参考 REQ-12.4）
  - [ ] 26.7 实现 `reuse_matching_rules(product_line)` — 从长期记忆中加载该产品线历史匹配规则（参考 REQ-12.4）
  - [ ] 26.8 实现 `export_memory()` 和 `clear_memory(scope)` — 导出与清除记忆数据（参考 REQ-12.5）

- [ ] 27. 实现异常自主处理器 (`agent/exception_handler.py`)
  - [ ] 27.1 实现 `detect_anomaly(step, result)` — 按设计文档异常类型矩阵检测：解析失败、匹配度过低、缺失评分表、产品型号不明确（参考 REQ-13.1）
  - [ ] 27.2 实现 `resolve_strategy(anomaly_type)` — 返回处理策略：重试/询问用户/跳过步骤并标记/通知后终止（参考 REQ-13.1, 设计文档处理策略矩阵）
  - [ ] 27.3 实现 `formulate_query(anomaly_type, detail)` — 生成面向用户的定向询问消息，明确说明缺失信息项并提供选项（参考 REQ-13.2）
  - [ ] 27.4 实现 `apply_resolution(anomaly_type, user_feedback)` — 接收用户反馈后恢复执行流程（参考 REQ-13.4）
  - [ ] 27.5 实现高危风险预警 — 当检测到实质性条款负偏离时返回 IMMEDIATE_ALERT 策略，不等全流程结束向用户推送预警（参考 REQ-13.3）

- [ ] 28. 实现结果自校验器 (`agent/self_validator.py`)
  - [ ] 28.1 实现 `validate_completeness(task_id)` — 执行全部校验维度：参数覆盖率、评分项覆盖率、风险完整性、数据一致性、异常标记完整性（参考 REQ-14.1, 设计文档校验维度）
  - [ ] 28.2 实现 `check_param_coverage(task_id)` — 已匹配参数数/招标参数总数，阈值 95%（参考 REQ-14.1）
  - [ ] 28.3 实现 `check_score_coverage(task_id)` — 已打分评分项/识别到的评分规则总数（参考 REQ-14.1）
  - [ ] 28.4 实现 `identify_missing_items(task_id)` — 识别未匹配参数、未覆盖评分项、缺失偏离判定（参考 REQ-14.3）
  - [ ] 28.5 实现 `trigger_remediation(missing_items, scheduler)` — 对未完成项触发补跑：未匹配参数降低匹配阈值重试，未覆盖评分项重新调用打分工具（参考 REQ-14.2）
  - [ ] 28.6 实现 `generate_validation_report(task_id)` — 生成自校验报告，输出完整性摘要（参考 REQ-14.4）

- [ ] 29. 集成 Agent 核心层与现有 Skill 入口
  - [ ] 29.1 改造 `skill.py` 的 `handle_message()` — 不再直接调用 orchestrator 固定方法，改为委托 planner→scheduler 链路（参考设计文档 Agent 执行流）
  - [ ] 29.2 改造 `handle_file_upload()` — 解析完成后将结果存入短期记忆，触发后续自动执行链路（参考 REQ-12.2）
  - [ ] 29.3 集成异常处理器 — 在 scheduler 捕获工具调用异常时触发 detect_anomaly + formulate_query（参考 REQ-13.1, REQ-13.2）
  - [ ] 29.4 集成自校验器 — scheduler 全部步骤执行完毕后调用 validate_completeness，缺漏触发补跑（参考 REQ-14.2）
  - [ ] 29.5 新增 `handle_user_feedback()` — 处理用户对异常询问的回复，传递给 exception_handler.apply_resolution()（参考 REQ-13.4）

- [ ] 30. 检查点 — Agent 核心层端到端验证
   - 使用现有 fixture 数据执行完整 Agent 链路：用户指令 → 规划 → 调度 → 全工具链 → 自校验 → 输出
   - 验证全流程可正常完成，异常场景可正确触发交互
