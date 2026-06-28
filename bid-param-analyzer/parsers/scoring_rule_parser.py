"""
评分规则解析器

将 table_extractor 提取的原始评分规则转换为结构化的 ScoringRule 对象，
支持定量（QUANTITATIVE）和定性（QUALITATIVE）两种规则类型。
"""
import json
import os

from database.models import ScoringRule, Condition, RuleType
from config.settings import REPORT_TEMPLATE_DIR as SCORING_TEMPLATES_DIR

# 使用 config/scoring_templates/ 目录
from config.settings import BASE_DIR
SCORING_TEMPLATES_DIR = os.path.join(BASE_DIR, "config", "scoring_templates")


def parse_scoring_rules(raw_rules: list[ScoringRule]) -> list[ScoringRule]:
    """
    将原始提取的评分规则规范化为标准 ScoringRule 对象。

    对每个规则进行类型推断和条件标准化。
    """
    parsed: list[ScoringRule] = []

    for rule in raw_rules:
        conditions = []
        for cond in rule.conditions:
            conditions.append(Condition(
                param_name=cond.param_name or rule.name,
                operator=cond.operator or "GTE",
                target_value=cond.target_value or "",
                score=cond.score if cond.score > 0 else rule.max_score,
            ))

        parsed.append(ScoringRule(
            id=rule.id,
            name=rule.name,
            max_score=rule.max_score,
            rule_type=_infer_rule_type(rule),
            conditions=conditions,
            bonus_rules=rule.bonus_rules,
            penalty_rules=rule.penalty_rules,
        ))

    return parsed


def _infer_rule_type(rule: ScoringRule) -> str:
    if rule.rule_type == RuleType.QUALITATIVE.value:
        return RuleType.QUALITATIVE.value
    name_lower = rule.name.lower()
    qualitative_keywords = ["综合", "整体", "方案", "服务", "培训", "售后", "实施"]
    if any(k in name_lower for k in qualitative_keywords):
        return RuleType.QUALITATIVE.value
    return RuleType.QUANTITATIVE.value


def load_template(template_name: str) -> dict:
    """
    加载评分模板。
    """
    template_path = os.path.join(SCORING_TEMPLATES_DIR, f"{template_name}.json")
    if not os.path.exists(template_path):
        template_path = os.path.join(SCORING_TEMPLATES_DIR, "default.json")
    with open(template_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_templates() -> dict[str, dict]:
    """
    加载所有可用评分模板。
    """
    templates = {}
    if not os.path.isdir(SCORING_TEMPLATES_DIR):
        return templates
    for filename in os.listdir(SCORING_TEMPLATES_DIR):
        if filename.endswith(".json"):
            name = filename[:-5]
            try:
                with open(os.path.join(SCORING_TEMPLATES_DIR, filename), "r", encoding="utf-8") as f:
                    templates[name] = json.load(f)
            except Exception:
                pass
    return templates


def apply_template(
    template: dict,
    matched_params: list[str],
    deviation_results: dict,
) -> list[ScoringRule]:
    """
    将评分模板应用于匹配到的参数和偏离结果，生成具体评分规则。
    """
    rules: list[ScoringRule] = []
    rule_type = template.get("rule_type", RuleType.QUANTITATIVE.value)

    if rule_type == RuleType.QUALITATIVE.value:
        score_per_item = template.get("score_per_item", 1)
        for param_name in matched_params:
            rules.append(ScoringRule(
                id=f"sr_{param_name}",
                name=param_name,
                max_score=float(score_per_item),
                rule_type=RuleType.QUALITATIVE.value,
                conditions=[Condition(
                    param_name=param_name,
                    operator="EQ",
                    target_value="无偏离",
                    score=float(score_per_item),
                )],
            ))
    else:
        if "dimensions" in template:
            for dim_name, weight in template.get("dimensions", {}).items():
                dim_score = weight * 100
                rules.append(ScoringRule(
                    id=f"sr_{dim_name}",
                    name=dim_name,
                    max_score=dim_score,
                    rule_type=RuleType.QUANTITATIVE.value,
                    conditions=[Condition(
                        param_name=dim_name,
                        operator="GTE",
                        target_value="",
                        score=dim_score,
                    )],
                ))
        elif "ranking" in template:
            top_score = template["ranking"].get("top_score", 5)
            for param_name in matched_params:
                rules.append(ScoringRule(
                    id=f"sr_{param_name}",
                    name=param_name,
                    max_score=float(top_score),
                    rule_type=RuleType.QUANTITATIVE.value,
                    conditions=[Condition(
                        param_name=param_name,
                        operator="GTE",
                        target_value="",
                        score=float(top_score),
                    )],
                ))

    return rules
