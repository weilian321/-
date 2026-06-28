"""
score_calculator.py 单元测试

覆盖: 定量/定性打分、汇总、溯源、高价值项标记
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from engine.score_calculator import (
    calculate_scoring,
    calculate_item_score,
    aggregate_scores,
    mark_improvement_items,
    trace_score,
    _evaluate_condition,
)
from database.models import (
    ScoringRule,
    Condition,
    DeviationResult,
    ScoreResult,
    ScoreSummary,
    DeviationType,
    RuleType,
)


class TestCalculateItemScore:
    def _rule(self, rule_type="quantitative", max_score=10.0, conditions=None):
        return ScoringRule(
            id="rule1",
            name="测试规则",
            max_score=max_score,
            rule_type=rule_type,
            conditions=conditions or [],
        )

    def _dev(self, dev_type=DeviationType.NEUTRAL.value):
        return DeviationResult(
            id="dr1",
            parsed_param_id="p1",
            match_param_id="m1",
            deviation_type=dev_type,
        )

    def test_quantitative_with_conditions_satisfied(self):
        rule = self._rule(max_score=10.0, conditions=[
            Condition(param_name="A", operator="GTE")
        ])
        score = calculate_item_score(rule, self._dev(DeviationType.NEUTRAL.value))
        assert score == 10.0

    def test_quantitative_negative_zero(self):
        rule = self._rule(max_score=5.0, conditions=[
            Condition(param_name="A", operator="EQ")
        ])
        score = calculate_item_score(rule, self._dev(DeviationType.NEGATIVE.value))
        assert score == 0.0

    def test_qualitative_neutral(self):
        rule = self._rule(rule_type="qualitative", max_score=10.0)
        score = calculate_item_score(rule, self._dev(DeviationType.NEUTRAL.value))
        assert score == 8.0

    def test_qualitative_positive(self):
        rule = self._rule(rule_type="qualitative", max_score=10.0)
        score = calculate_item_score(rule, self._dev(DeviationType.POSITIVE.value))
        assert score == 10.0

    def test_qualitative_negative(self):
        rule = self._rule(rule_type="qualitative", max_score=10.0)
        score = calculate_item_score(rule, self._dev(DeviationType.NEGATIVE.value))
        assert score == 2.0

    def test_qualitative_unconfirmed(self):
        rule = self._rule(rule_type="qualitative", max_score=10.0)
        score = calculate_item_score(rule, self._dev(DeviationType.UNCONFIRMED.value))
        assert score == 0.0

    def test_gte_condition_satisfied(self):
        rule = self._rule(max_score=10.0, conditions=[
            Condition(param_name="test", operator="GTE")
        ])
        score = calculate_item_score(rule, self._dev(DeviationType.POSITIVE.value))
        assert score == 10.0

    def test_gt_condition_requires_positive(self):
        rule = self._rule(max_score=10.0, conditions=[
            Condition(param_name="test", operator="GT")
        ])
        score = calculate_item_score(rule, self._dev(DeviationType.NEUTRAL.value))
        assert score == 0.0

    def test_quantitative_no_conditions_zero(self):
        rule = self._rule(max_score=10.0, conditions=[])
        score = calculate_item_score(rule, self._dev(DeviationType.NEUTRAL.value))
        assert score == 0.0

    def test_positive_after_condition_fail(self):
        rule = self._rule(max_score=10.0, conditions=[
            Condition(param_name="test", operator="EQ")
        ])
        score = calculate_item_score(rule, self._dev(DeviationType.POSITIVE.value))
        assert score == 12.0


class TestAggregateScores:
    def test_empty(self):
        summary = aggregate_scores([])
        assert summary.total_score == 0.0
        assert summary.max_possible_score == 0.0

    def test_full_scores(self):
        results = [
            ScoreResult(id="s1", task_id="t1", rule_name="r1", max_score=10.0, actual_score=8.0),
            ScoreResult(id="s2", task_id="t1", rule_name="r2", max_score=5.0, actual_score=5.0),
        ]
        summary = aggregate_scores(results)
        assert summary.total_score == 13.0
        assert summary.max_possible_score == 15.0
        assert 0.86 < summary.score_rate < 0.87


class TestMarkImprovementItems:
    def test_generate_improvement_items(self):
        dev = DeviationResult(
            id="dr1", parsed_param_id="p1", match_param_id="m1",
            deviation_type=DeviationType.NEGATIVE.value,
        )
        scores = [
            ScoreResult(id="s1", task_id="t1", rule_name="r1", max_score=10.0, actual_score=2.0),
            ScoreResult(id="s2", task_id="t1", rule_name="r2", max_score=5.0, actual_score=5.0),
        ]
        items = mark_improvement_items(scores, [dev])
        assert isinstance(items, list)


class TestTraceScore:
    def test_trace_score(self):
        result = ScoreResult(
            id="s1", task_id="t1", rule_name="r1",
            max_score=10.0, actual_score=8.0,
            trace_data='{"reason": "定性打分: 无偏离 8/10"}',
        )
        trace = trace_score(result)
        assert isinstance(trace, dict)


class TestCalculateScoring:
    def test_full_calculation(self):
        rules = [
            ScoringRule(id="r1", name="吞吐量评分", max_score=10.0, rule_type="qualitative"),
            ScoringRule(id="r2", name="并发评分", max_score=5.0, rule_type="qualitative"),
        ]
        deviations = [
            DeviationResult(id="dr1", parsed_param_id="p1", match_param_id="m1", deviation_type=DeviationType.NEUTRAL.value),
            DeviationResult(id="dr2", parsed_param_id="p2", match_param_id="m2", deviation_type=DeviationType.POSITIVE.value),
        ]
        param_map = {"p1": "吞吐量评分", "p2": "并发评分"}
        summary = calculate_scoring(rules, deviations, param_map)
        assert summary.max_possible_score == 15.0
        assert 0 <= summary.score_rate <= 1.0


class TestConditionOperators:
    def _dev(self, dev_type):
        return DeviationResult(
            id="x", parsed_param_id="p", match_param_id="m", deviation_type=dev_type,
        )

    def test_eq_neutral(self):
        cond = Condition(param_name="test", operator="EQ")
        assert _evaluate_condition(cond, self._dev(DeviationType.NEUTRAL.value))

    def test_eq_not_neutral(self):
        cond = Condition(param_name="test", operator="EQ")
        assert not _evaluate_condition(cond, self._dev(DeviationType.POSITIVE.value))

    def test_gt_positive(self):
        cond = Condition(param_name="test", operator="GT")
        assert _evaluate_condition(cond, self._dev(DeviationType.POSITIVE.value))

    def test_gte_neutral_or_positive(self):
        cond = Condition(param_name="test", operator="GTE")
        assert _evaluate_condition(cond, self._dev(DeviationType.NEUTRAL.value))
        assert _evaluate_condition(cond, self._dev(DeviationType.POSITIVE.value))

    def test_contains_neutral_positive(self):
        cond = Condition(param_name="test", operator="CONTAINS")
        assert _evaluate_condition(cond, self._dev(DeviationType.NEUTRAL.value))
        assert not _evaluate_condition(cond, self._dev(DeviationType.NEGATIVE.value))

    def test_empty_param_name_always_true(self):
        cond = Condition(param_name="", operator="LTE")
        assert _evaluate_condition(cond, self._dev(DeviationType.NEGATIVE.value))
