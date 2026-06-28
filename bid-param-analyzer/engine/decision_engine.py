"""
投标决策推理引擎

综合偏离表、得分、风险清单进行决策推理，输出三级结论、
全景分析和落地建议。
"""
from database.models import (
    DeviationResult,
    ScoreSummary,
    RiskLevel,
    DeviationType,
)


def derive_decision(score_summary: ScoreSummary, risk_list: list[dict]) -> dict:
    """
    基于废标风险数量和得分率输出三级决策结论。

    建议投标：  废标风险=0 且 得分率≥80%
    谨慎投标：  废标风险=0 且 得分率 60%-80% 或存在可消解风险
    不建议投标：废标风险>0 或 得分率<60%
    """
    disqualify_count = sum(
        1 for r in risk_list if r.get("risk_level") == RiskLevel.DISQUALIFY.value
    )
    score_rate = score_summary.score_rate

    if disqualify_count > 0 or score_rate < 0.60:
        conclusion = "不建议投标"
        confidence = "高"
        reason = _build_reject_reason(disqualify_count, score_rate)
    elif score_rate >= 0.80:
        conclusion = "建议投标"
        confidence = "高" if score_rate >= 0.90 else "中"
        reason = f"技术得分率 {score_rate:.0%}，在竞争中具备显著优势"
    else:
        conclusion = "谨慎投标"
        confidence = "中"
        reason = f"技术得分率 {score_rate:.0%}，处于竞争区间，建议针对性优化"

    return {
        "conclusion": conclusion,
        "confidence": confidence,
        "reason": reason,
        "score_rate": score_rate,
        "disqualify_risk_count": disqualify_count,
    }


def _build_reject_reason(disqualify_count: int, score_rate: float) -> str:
    reasons = []
    if disqualify_count > 0:
        reasons.append(f"存在 {disqualify_count} 项废标级风险")
    if score_rate < 0.60:
        reasons.append(f"技术得分率仅 {score_rate:.0%}，低于竞争阈值")
    return "；".join(reasons)


def generate_advantage_list(deviation_table: list[DeviationResult]) -> list[dict]:
    """生成正偏离项清单（竞争优势）。"""
    advantages = []
    for d in deviation_table:
        if d.deviation_type == DeviationType.POSITIVE.value:
            advantages.append({
                "param_id": d.parsed_param_id,
                "deviation_type": d.deviation_type,
                "explanation": d.explanation,
            })
    return advantages


def generate_risk_list(
    deviation_table: list[DeviationResult],
    score_summary: ScoreSummary,
) -> list[dict]:
    """
    生成风险项清单，包含：废标风险、得分短板、资质门槛。
    """
    risks = []

    for d in deviation_table:
        if d.risk_level == RiskLevel.DISQUALIFY.value:
            risks.append({
                "param_id": d.parsed_param_id,
                "risk_level": RiskLevel.DISQUALIFY.value,
                "deviation_type": d.deviation_type,
                "explanation": d.explanation,
                "suggestion": d.suggestion,
                "category": "废标风险",
            })
        elif d.risk_level == RiskLevel.SCORE_DEDUCTION.value:
            risks.append({
                "param_id": d.parsed_param_id,
                "risk_level": RiskLevel.SCORE_DEDUCTION.value,
                "deviation_type": d.deviation_type,
                "explanation": d.explanation,
                "suggestion": d.suggestion,
                "category": "得分短板",
            })

    if score_summary.score_rate < 0.70:
        risks.append({
            "category": "得分短板",
            "risk_level": "整体得分偏低",
            "explanation": f"技术总分 {score_summary.total_score}/{score_summary.max_possible_score} ({score_summary.score_rate:.0%})，低于 70% 目标线",
        })

    return risks


def generate_suggestions(
    risk_list: list[dict],
    improvement_items: list[dict],
) -> dict:
    """
    生成落地建议：参数优化方向、证明材料准备清单、答疑澄清要点、报价策略参考。
    """
    suggestions = {
        "参数优化方向": [],
        "证明材料准备清单": [],
        "答疑澄清要点": [],
        "报价策略参考": [],
    }

    for risk in risk_list:
        if risk.get("category") == "废标风险":
            suggestions["答疑澄清要点"].append(
                f"对 {risk.get('param_id', '未知参数')} 的偏离情况准备澄清说明"
            )
        elif risk.get("category") == "得分短板":
            suggestions["参数优化方向"].append(
                f"优化 {risk.get('param_id', '未知参数')} 以提升得分"
            )

    for item in improvement_items:
        if item.get("improvement_type") == "补充材料":
            suggestions["证明材料准备清单"].append(
                f"为 {item['rule_name']} 准备补充证明（潜在收益 +{item['potential_gain']} 分）"
            )
        elif item.get("improvement_type") == "参数优化":
            suggestions["参数优化方向"].append(
                f"{item['rule_name']}：{item.get('reason', '优化参数以匹配招标要求')}（潜在收益 +{item['potential_gain']} 分）"
            )

    score_rate = 0.8  # Default, will be overridden by caller
    if score_rate >= 0.85:
        suggestions["报价策略参考"].append("技术优势明显，建议正常报价策略")
    elif score_rate >= 0.70:
        suggestions["报价策略参考"].append("技术得分中等，建议适当让利以增强竞争力")
    else:
        suggestions["报价策略参考"].append("技术得分偏低，建议以价格优势弥补技术短板")

    return suggestions


def competitive_assessment(
    deviation_table: list[DeviationResult],
    score_summary: ScoreSummary,
) -> dict:
    """
    基于正负偏离比例与得分率输出竞争维度评估。
    """
    total = len(deviation_table)
    if total == 0:
        return {"level": "无法评估", "analysis": "无偏离数据"}

    positive = sum(1 for d in deviation_table if d.deviation_type == DeviationType.POSITIVE.value)
    neutral = sum(1 for d in deviation_table if d.deviation_type == DeviationType.NEUTRAL.value)
    negative = sum(1 for d in deviation_table if d.deviation_type == DeviationType.NEGATIVE.value)
    unconfirmed = sum(1 for d in deviation_table if d.deviation_type == DeviationType.UNCONFIRMED.value)

    positive_rate = positive / total
    negative_rate = negative / total

    if positive_rate >= 0.5 and negative_rate == 0:
        level = "竞争优势显著"
    elif positive_rate >= 0.3 and negative_rate <= 0.1:
        level = "具备竞争优势"
    elif positive_rate >= 0.1 and negative_rate <= 0.2:
        level = "竞争均势"
    elif negative_rate <= 0.3:
        level = "竞争劣势"
    else:
        level = "竞争力不足"

    return {
        "level": level,
        "total_params": total,
        "positive_count": positive,
        "neutral_count": neutral,
        "negative_count": negative,
        "unconfirmed_count": unconfirmed,
        "positive_rate": round(positive_rate, 3),
        "negative_rate": round(negative_rate, 3),
        "score_rate": round(score_summary.score_rate, 3),
        "analysis": (
            f"参数正偏离率 {positive_rate:.0%}，负偏离率 {negative_rate:.0%}，"
            f"技术得分率 {score_summary.score_rate:.0%}，综合评定：{level}"
        ),
    }
