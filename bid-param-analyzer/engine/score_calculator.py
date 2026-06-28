"""
得分计算器

按评分规则计算各评分项得分，汇总技术部分预估总分与得分率，
支持得分溯源和高价值提升项标记。
"""
import uuid

from database.models import (
    ScoringRule,
    Condition,
    DeviationResult,
    ScoreResult,
    ScoreSummary,
    DeviationType,
    RuleType,
)


def calculate_item_score(rule: ScoringRule, deviation: DeviationResult) -> float:
    """
    计算单项评分项得分。

    定量打分：满足条件得满分，否则 0
    定性打分：根据偏离状态分级给分
    """
    if rule.rule_type == RuleType.QUALITATIVE.value:
        return _qualitative_score(rule, deviation)

    if not rule.conditions:
        return 0.0

    satisfied = True
    for cond in rule.conditions:
        if not _evaluate_condition(cond, deviation):
            satisfied = False
            break

    if satisfied:
        return rule.max_score

    if deviation.deviation_type == DeviationType.POSITIVE.value:
        return rule.max_score * 1.2

    return 0.0


def _qualitative_score(rule: ScoringRule, deviation: DeviationResult) -> float:
    mapping = {
        DeviationType.POSITIVE.value: rule.max_score,
        DeviationType.NEUTRAL.value: rule.max_score * 0.8,
        DeviationType.NEGATIVE.value: rule.max_score * 0.2,
        DeviationType.UNCONFIRMED.value: 0.0,
    }
    return mapping.get(deviation.deviation_type, 0.0)


def _evaluate_condition(cond: Condition, deviation: DeviationResult) -> bool:
    if not cond.param_name:
        return True

    if cond.operator == "GTE":
        return deviation.deviation_type in (
            DeviationType.NEUTRAL.value,
            DeviationType.POSITIVE.value,
        )
    elif cond.operator == "GT":
        return deviation.deviation_type == DeviationType.POSITIVE.value
    elif cond.operator == "EQ":
        return deviation.deviation_type == DeviationType.NEUTRAL.value
    elif cond.operator == "CONTAINS":
        return deviation.deviation_type in (
            DeviationType.NEUTRAL.value,
            DeviationType.POSITIVE.value,
        )
    elif cond.operator == "LTE":
        return deviation.deviation_type == DeviationType.NEUTRAL.value

    return True


def calculate_scoring(
    scoring_rules: list[ScoringRule],
    deviation_table: list[DeviationResult],
    param_map: dict[str, str],
) -> ScoreSummary:
    """
    计算所有评分项得分。

    将评分规则逐项映射到偏离表，按规则计分。
    """
    item_scores: list[ScoreResult] = []

    for rule in scoring_rules:
        matched_deviation = _find_matching_deviation(rule, deviation_table, param_map)

        if matched_deviation:
            score = calculate_item_score(rule, matched_deviation)
        else:
            score = 0.0

        item_scores.append(ScoreResult(
            id=f"sr_{uuid.uuid4().hex[:12]}",
            task_id="",
            rule_name=rule.name,
            max_score=rule.max_score,
            actual_score=score,
            trace_data=_build_trace(rule, matched_deviation),
        ))

    return aggregate_scores(item_scores)


def _find_matching_deviation(
    rule: ScoringRule,
    deviation_table: list[DeviationResult],
    param_map: dict[str, str],
) -> DeviationResult | None:
    rule_param_names = set()
    for cond in rule.conditions:
        if cond.param_name:
            rule_param_names.add(cond.param_name)

    for deviation in deviation_table:
        param_name = param_map.get(deviation.parsed_param_id, "")
        if param_name and param_name in rule_param_names:
            return deviation

    if not rule_param_names or rule.name in param_map.values():
        for deviation in deviation_table:
            param_name = param_map.get(deviation.parsed_param_id, "")
            if param_name == rule.name:
                return deviation

    return None


def aggregate_scores(item_scores: list[ScoreResult]) -> ScoreSummary:
    """
    汇总技术部分预估总分与得分率。
    """
    total = sum(s.actual_score for s in item_scores)
    max_possible = sum(s.max_score for s in item_scores)

    score_rate = total / max_possible if max_possible > 0 else 0.0

    return ScoreSummary(
        total_score=total,
        max_possible_score=max_possible,
        score_rate=score_rate,
        item_scores=item_scores,
        improvement_items=[],
    )


def trace_score(score: ScoreResult) -> dict:
    """
    得分溯源：返回评分标准、参数依据链路。
    """
    import json
    try:
        trace = json.loads(score.trace_data)
    except (json.JSONDecodeError, TypeError):
        trace = {}
    return {
        "rule_name": score.rule_name,
        "max_score": score.max_score,
        "actual_score": score.actual_score,
        "score_rate": score.actual_score / score.max_score if score.max_score > 0 else 0,
        "trace": trace,
    }


def mark_improvement_items(
    scores: list[ScoreResult],
    deviation_table: list[DeviationResult],
) -> list[dict]:
    """
    标记可通过补充材料或参数优化提升得分的高价值评分项。

    规则：
    - 得分 < 满分 且偏离状态为无法确认 → 补充材料可提升
    - 得分 = 0 且偏离为负偏离 → 参数优化可提升
    """
    improvement_items: list[dict] = []

    for score in scores:
        if score.actual_score >= score.max_score:
            continue

        improvement_type = ""
        reason = ""

        if score.actual_score == 0:
            improvement_type = "参数优化"
            reason = "当前未得分，建议优化产品参数以匹配招标要求"
        elif score.actual_score < score.max_score:
            improvement_type = "补充材料"
            reason = "得分未满，可通过补充证明材料提升得分"

        gain = score.max_score - score.actual_score
        improvement_items.append({
            "rule_name": score.rule_name,
            "current_score": score.actual_score,
            "max_score": score.max_score,
            "potential_gain": gain,
            "improvement_type": improvement_type,
            "reason": reason,
        })

    improvement_items.sort(key=lambda x: x["potential_gain"], reverse=True)
    return improvement_items


def _build_trace(rule: ScoringRule, deviation: DeviationResult | None) -> str:
    import json
    trace = {
        "rule_name": rule.name,
        "rule_type": rule.rule_type,
        "max_score": rule.max_score,
    }
    if deviation:
        trace["deviation_type"] = deviation.deviation_type
        trace["explanation"] = deviation.explanation
        trace["similarity_score"] = deviation.similarity_score
    else:
        trace["deviation_type"] = "无匹配"
        trace["explanation"] = "未找到对应参数偏离结果"
    return json.dumps(trace, ensure_ascii=False)
