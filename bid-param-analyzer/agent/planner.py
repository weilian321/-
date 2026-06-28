"""
自主任务规划引擎

将用户自然语言指令拆解为工具调用序列，在运行时动态调整执行路径。

参考 REQ-10，设计文档 Components 2。
"""
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Intent:
    """
    解析后的用户意图。

    包含意图类型、范围限定、条件筛选等结构化信息。
    """
    intent_type: str = "full_pipeline"
    keywords: list[str] = field(default_factory=list)
    scope_limit: Optional[str] = None
    extra_conditions: dict[str, Any] = field(default_factory=dict)


@dataclass
class Step:
    """
    执行计划中的单个步骤。
    """
    name: str
    tool_name: str
    depends_on: list[str] = field(default_factory=list)
    args: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"


@dataclass
class Plan:
    """
    任务执行计划，由一系列有序步骤组成。
    """
    steps: list[Step]
    template_name: str = "full_pipeline"
    current_index: int = 0


class AgentPlanner:
    """
    自主任务规划引擎。

    职责：
    1. 解析用户自然语言指令中的意图
    2. 根据意图生成执行计划
    3. 运行时根据中间结果动态调整计划
    """

    TEMPLATES = {
        "full_pipeline": [
            ("parse_doc", "doc_parser"),
            ("extract_params", "table_extractor"),
            ("match_product", "semantic_matcher"),
            ("judge_deviation", "deviation_judge"),
            ("parse_scoring_rules", "scoring_rule_parser"),
            ("calculate_scores", "score_calculator"),
            ("derive_decision", "decision_engine"),
            ("generate_report", "report_generator"),
        ],
        "qualification_only": [
            ("parse_doc", "doc_parser"),
            ("extract_qualifications", "table_extractor"),
            ("judge_qualification", "deviation_judge"),
            ("derive_decision", "decision_engine"),
        ],
        "performance_focus": [
            ("parse_doc", "doc_parser"),
            ("extract_performance_params", "table_extractor"),
            ("match_performance", "semantic_matcher"),
            ("judge_deviation", "deviation_judge"),
            ("parse_scoring_rules", "scoring_rule_parser"),
            ("calculate_scores", "score_calculator"),
            ("mark_improvements", "score_calculator"),
        ],
        "score_priority": [
            ("parse_doc", "doc_parser"),
            ("extract_scoring_table", "table_extractor"),
            ("extract_params", "table_extractor"),
            ("match_product", "semantic_matcher"),
            ("calculate_scores", "score_calculator"),
            ("sensitivity_analysis", "score_calculator"),
            ("derive_decision", "decision_engine"),
        ],
    }

    INTENT_KEYWORDS = {
        "qualification_only": ["资格门槛", "资格条件", "门槛条款", "实质性条件"],
        "performance_focus": ["性能参数", "重点比对性能", "性能优化"],
        "score_priority": ["得分优先", "评分优先", "加分项", "得分分析"],
    }

    def parse_intent(
        self, user_input: str, context: dict[str, Any]
    ) -> Intent:
        """
        从用户自然语言指令中提取关键词，识别意图类型。

        返回 Intent 对象，包含 intent_type（full_pipeline/qualification_only/
        performance_focus/score_priority）、关键词列表和范围限定。
        """
        user_lower = user_input.lower().strip()
        intent = Intent()
        intent.keywords = [k for k in self.INTENT_KEYWORDS.get("full_pipeline", [])
                           if k in user_input]

        for intent_type, keywords in self.INTENT_KEYWORDS.items():
            if any(k in user_input for k in keywords):
                intent.intent_type = intent_type
                intent.keywords = [k for k in keywords if k in user_input]
                break

        return intent

    def generate_plan(
        self, intent: Intent, memory: Optional[Any] = None
    ) -> Plan:
        """
        根据意图类型生成执行计划。

        从预设模板中选择对应的步骤序列，按需裁剪。
        若 memory 非空，跳过已完成步骤。
        """
        template_steps = self.TEMPLATES.get(
            intent.intent_type, self.TEMPLATES["full_pipeline"]
        )

        steps = []
        completed_steps: set[str] = set()

        if memory is not None and hasattr(memory, "completed_steps"):
            completed_steps = set(memory.completed_steps or [])

        for step_name, tool_name in template_steps:
            if step_name in completed_steps:
                continue

            deps = [s.name for s in steps if tool_name in self._get_tool_deps(tool_name)]
            steps.append(Step(
                name=step_name,
                tool_name=tool_name,
                depends_on=deps,
            ))

        return Plan(steps=steps, template_name=intent.intent_type)

    def adjust_plan(
        self, plan: Plan, step_name: str, step_result: dict[str, Any]
    ) -> Plan:
        """
        根据中间步骤的结果动态调整后续执行路径。

        如检测到无评分表 → 移除打分相关步骤，
        检测到多产品型号 → 插入选型确认步骤。
        """
        new_steps = []

        for step in plan.steps:
            if step.status == "completed":
                new_steps.append(step)
                continue

            if step.status != "pending":
                continue

            if "skip_scoring" in step_result and step.tool_name in (
                "scoring_rule_parser", "score_calculator"
            ):
                continue

            new_steps.append(step)

        if "need_model_selection" in step_result:
            select_step = Step(
                name="select_model",
                tool_name="model_selector",
                depends_on=[step_name],
            )
            pos = plan.current_index
            new_steps.insert(pos, select_step)

        return Plan(steps=new_steps, template_name=plan.template_name)

    def next_step(self, plan: Plan) -> Optional[Step]:
        """返回当前待执行步骤。"""
        for step in plan.steps:
            if step.status == "pending":
                return step
        return None

    @staticmethod
    def _get_tool_deps(tool_name: str) -> list[str]:
        """返回指定工具的依赖工具名称列表。"""
        deps_map: dict[str, list[str]] = {
            "table_extractor": ["doc_parser"],
            "scoring_rule_parser": ["doc_parser"],
            "semantic_matcher": ["table_extractor"],
            "deviation_judge": ["semantic_matcher"],
            "score_calculator": ["scoring_rule_parser", "deviation_judge"],
            "decision_engine": ["deviation_judge", "score_calculator"],
            "report_generator": ["deviation_judge", "score_calculator", "decision_engine"],
        }
        return deps_map.get(tool_name, [])
