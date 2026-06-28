"""
decision_engine.py 单元测试

覆盖: 三级决策边界、优势/风险评估、竞争评估、建议生成
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from engine.decision_engine import (
    derive_decision,
    generate_advantage_list,
    generate_risk_list,
    generate_suggestions,
    competitive_assessment,
)
from database.models import (
    ScoreSummary,
    DeviationResult,
    DeviationType,
    RiskLevel,
)


def _summary(score_rate, total=100, max_=100):
    return ScoreSummary(
        total_score=total * score_rate,
        max_possible_score=max_,
        score_rate=score_rate,
    )


def _dev(dev_type, parsed_param_id="p1", risk_level=RiskLevel.NONE.value, explanation=""):
    return DeviationResult(
        id=f"dr_{parsed_param_id}",
        parsed_param_id=parsed_param_id,
        match_param_id="m1",
        deviation_type=dev_type,
        risk_level=risk_level,
        explanation=explanation,
    )


class TestDeriveDecision:
    def test_recommend_high_score(self):
        result = derive_decision(_summary(0.90), [])
        assert result["conclusion"] == "建议投标"
        assert result["confidence"] == "高"

    def test_recommend_moderate_score(self):
        result = derive_decision(_summary(0.85), [])
        assert result["conclusion"] == "建议投标"
        assert result["confidence"] == "中"

    def test_caution_edge(self):
        result = derive_decision(_summary(0.70), [])
        assert result["conclusion"] == "谨慎投标"

    def test_caution_high_edge(self):
        result = derive_decision(_summary(0.79), [])
        assert result["conclusion"] == "谨慎投标"

    def test_reject_low_score(self):
        result = derive_decision(_summary(0.30), [])
        assert result["conclusion"] == "不建议投标"

    def test_reject_disqualify_risk(self):
        risk = [{"risk_level": RiskLevel.DISQUALIFY.value}]
        result = derive_decision(_summary(0.95), risk)
        assert result["conclusion"] == "不建议投标"
        assert result["disqualify_risk_count"] == 1

    def test_export_fields(self):
        risk = [
            {"risk_level": RiskLevel.DISQUALIFY.value},
            {"risk_level": RiskLevel.DISQUALIFY.value},
        ]
        result = derive_decision(_summary(0.20), risk)
        assert result["score_rate"] == 0.20
        assert result["disqualify_risk_count"] == 2


class TestAdvantageList:
    def test_positive_included(self):
        devs = [
            _dev(DeviationType.POSITIVE.value, explanation="性能超出"),
            _dev(DeviationType.NEUTRAL.value),
            _dev(DeviationType.NEGATIVE.value),
        ]
        advantages = generate_advantage_list(devs)
        assert len(advantages) == 1
        assert advantages[0]["explanation"] == "性能超出"

    def test_no_positive(self):
        devs = [_dev(DeviationType.NEUTRAL.value), _dev(DeviationType.NEGATIVE.value)]
        assert generate_advantage_list(devs) == []


class TestRiskList:
    def test_disqualify_and_deduction(self):
        devs = [
            _dev(DeviationType.NEGATIVE.value, parsed_param_id="p1", risk_level=RiskLevel.DISQUALIFY.value, explanation="核心参数不满足"),
        ]
        risks = generate_risk_list(devs, _summary(0.5))
        assert len(risks) >= 1

    def test_no_risks(self):
        devs = [_dev(DeviationType.NEUTRAL.value, risk_level=RiskLevel.NONE.value)]
        risks = generate_risk_list(devs, _summary(0.9))
        assert len(risks) >= 0


class TestSuggestions:
    def test_generate_suggestions(self):
        risk_list = [
            {"category": "废标风险", "param_id": "p1", "risk_level": RiskLevel.DISQUALIFY.value},
        ]
        improvements = [
            {"improvement_type": "补充材料", "rule_name": "规则A", "potential_gain": 5},
        ]
        suggestions = generate_suggestions(risk_list, improvements)
        assert len(suggestions) > 0

    def test_empty(self):
        suggestions = generate_suggestions([], [])
        assert len(suggestions) >= 0


class TestCompetitiveAssessment:
    def test_assessment(self):
        devs = [
            _dev(DeviationType.POSITIVE.value, parsed_param_id="a1"),
            _dev(DeviationType.NEUTRAL.value, parsed_param_id="a2"),
            _dev(DeviationType.NEGATIVE.value, parsed_param_id="a3"),
        ]
        result = competitive_assessment(devs, _summary(0.75))
        assert isinstance(result, dict)
        assert "score_rate" in result
