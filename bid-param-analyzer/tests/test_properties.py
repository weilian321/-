"""
Correctness Properties 属性测试 (任务 20)

验证设计文档中定义的 Correctness Properties 不变式。
"""
import os
import sys
import random
import string
import uuid
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from engine.deviation_judge import batch_judge
from engine.score_calculator import calculate_item_score
from engine.decision_engine import derive_decision
from database.models import (
    ParameterItem,
    ParameterRecord,
    DeviationResult,
    ScoreSummary,
    ScoringRule,
    DeviationType,
    RiskLevel,
    MatchPair,
)


def _random_param():
    name = "".join(random.choices(string.ascii_letters, k=6))
    return ParameterItem(
        id=f"rp_{random.randint(0, 99999)}",
        name=name,
        requirement_value=str(random.randint(1, 100)),
        param_type="数值范围",
        is_material=random.choice([True, False]),
    )


def _random_product():
    name = "".join(random.choices(string.ascii_letters, k=6))
    return ParameterRecord(
        id=f"rpr_{random.randint(0, 99999)}",
        name=name,
        nominal_value=str(random.randint(1, 100)),
        version_id="v1",
    )


def _random_deviation(dev_type=None):
    return DeviationResult(
        id=f"rd_{random.randint(0, 99999)}",
        parsed_param_id=f"p{random.randint(0, 99)}",
        match_param_id=f"m{random.randint(0, 99)}",
        deviation_type=dev_type or random.choice([
            DeviationType.POSITIVE.value,
            DeviationType.NEUTRAL.value,
            DeviationType.NEGATIVE.value,
            DeviationType.UNCONFIRMED.value,
        ]),
    )


def _random_rule(max_score=None):
    return ScoringRule(
        id=f"rr_{random.randint(0, 99999)}",
        name="random_rule",
        max_score=max_score or random.uniform(1, 100),
        rule_type=random.choice(["quantitative", "qualitative"]),
    )


class TestPropertyComparisonCoverage:
    def test_coverage_10_params(self):
        for _ in range(10):
            bid = [_random_param() for _ in range(5)]
            prod = [_random_product() for _ in range(3)]
            pairs = [
                MatchPair(
                    bid_param=bid[i % len(bid)],
                    product_param=random.choice(prod),
                    similarity_score=random.uniform(0, 1),
                    match_method=random.choice(["exact", "vector"]),
                )
                for i in range(len(bid))
            ]
            results = batch_judge(pairs, [])
            assert len(results) >= len(bid)

    def test_unmatched_coverage(self):
        for _ in range(10):
            bid = [_random_param() for _ in range(3)]
            results = batch_judge([], bid)
            assert len(results) == len(bid)


class TestPropertyScoreBounds:
    def test_score_bounds(self):
        for _ in range(50):
            rule = _random_rule()
            dev = _random_deviation()
            score = calculate_item_score(rule, dev)
            assert 0.0 <= score


class TestPropertyRiskPropagation:
    def test_material_negative_leads_to_reject(self):
        for _ in range(20):
            risk_list = [
                {"risk_level": RiskLevel.DISQUALIFY.value}
                for _ in range(random.randint(1, 3))
            ]
            summary = ScoreSummary(
                total_score=random.uniform(50, 100),
                max_possible_score=100,
                score_rate=random.uniform(0.5, 0.99),
            )
            decision = derive_decision(summary, risk_list)
            assert decision["conclusion"] == "不建议投标"


class TestPropertyVersionIsolation:
    def test_version_isolation(self):
        from database.migrations import get_connection
        import database.repository as repo
        pl = repo.create_product_line("PL-ISO", "version isolation test")
        v1 = repo.create_product_version(pl.id, "V1")
        v2 = repo.create_product_version(pl.id, "V2")

        conn = get_connection()
        import uuid
        for vid, name in [(v1.id, "参数A"), (v1.id, "参数B"), (v2.id, "参数C")]:
            pid = f"par_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO parameter_records (id, version_id, name, nominal_value) VALUES (?, ?, ?, ?)",
                (pid, vid, name, "100"),
            )
        conn.commit()
        conn.close()

        import database.repository as repo
        pl = repo.create_product_line("PL-ISO", "version isolation test")
        v1 = repo.create_product_version(pl.id, "V1")
        v2 = repo.create_product_version(pl.id, "V2")

        conn = get_connection()
        for vid, name in [(v1.id, "参数A"), (v1.id, "参数B"), (v2.id, "参数C")]:
            pid = f"par_{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO parameter_records (id, version_id, name, nominal_value) VALUES (?, ?, ?, ?)",
                (pid, vid, name, "100"),
            )
        conn.commit()
        conn.close()

        p1 = repo.get_version_params(v1.id)
        p2 = repo.get_version_params(v2.id)
        assert len(p1) == 2
        assert len(p2) == 1
        names_v1 = {p.name for p in p1}
        names_v2 = {p.name for p in p2}
        assert names_v1.isdisjoint(names_v2), "version data not isolated"
