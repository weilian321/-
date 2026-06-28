"""
deviation_judge.py 单元测试

覆盖: 数值范围、枚举、布尔、功能描述四种判定及风险分级
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from engine.deviation_judge import (
    judge,
    classify_risk,
    batch_judge,
)
from database.models import (
    ParameterItem,
    ParameterRecord,
    DeviationResult,
    DeviationType,
    RiskLevel,
    ParamType,
    MatchPair,
)


def _make_bid(name, req_value, param_type="数值范围", is_material=False):
    return ParameterItem(
        id=f"bid_{name}",
        name=name,
        requirement_value=req_value,
        param_type=param_type,
        is_material=is_material,
    )


def _make_product(name, nominal_value):
    return ParameterRecord(
        id=f"prod_{name}",
        name=name,
        nominal_value=nominal_value,
        version_id="v1",
    )


class TestNumericJudgment:
    def test_product_meets_requirement(self):
        bid = _make_bid("最大吞吐量", ">=10")
        prod = _make_product("最大吞吐量", "10")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEUTRAL.value

    def test_product_exceeds_requirement(self):
        bid = _make_bid("最大吞吐量", "20")
        prod = _make_product("最大吞吐量", "100")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.POSITIVE.value

    def test_product_falls_short(self):
        bid = _make_bid("最大吞吐量", ">=100")
        prod = _make_product("最大吞吐量", "50")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEGATIVE.value

    def test_unparseable_value(self):
        bid = _make_bid("capacity", "should be big")
        prod = _make_product("capacity", "10")
        result = judge(bid, prod)
        assert result.deviation_type in (
            DeviationType.UNCONFIRMED.value,
            DeviationType.NEUTRAL.value,
        )

    def test_equal_operator(self):
        bid = _make_bid("电压", "=220")
        prod = _make_product("电压", "220")
        result = judge(bid, prod)
        assert result.deviation_type in (
            DeviationType.NEUTRAL.value,
            DeviationType.UNCONFIRMED.value,
        )

    def test_plain_value(self):
        bid = _make_bid("内存", "64")
        prod = _make_product("内存", "128")
        result = judge(bid, prod)
        assert result.deviation_type in (
            DeviationType.NEUTRAL.value,
            DeviationType.POSITIVE.value,
        )


class TestEnumJudgment:
    def test_product_covers_all(self):
        bid = _make_bid("协议", "TCP/UDP/HTTP", param_type="枚举值")
        prod = _make_product("协议", "TCP/UDP/HTTP/HTTPS/FTP")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEUTRAL.value

    def test_product_missing_option(self):
        bid = _make_bid("协议", "TCP/UDP/HTTPS", param_type="枚举值")
        prod = _make_product("协议", "TCP/UDP")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEGATIVE.value

    def test_empty_bid_enum(self):
        bid = _make_bid("协议", "", param_type="枚举值")
        prod = _make_product("协议", "TCP")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.UNCONFIRMED.value


class TestBooleanJudgment:
    def test_both_support(self):
        bid = _make_bid("SNMP支持", "支持", param_type="布尔型")
        prod = _make_product("SNMP支持", "支持")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEUTRAL.value

    def test_product_not_support(self):
        bid = _make_bid("VPN功能", "具备", param_type="布尔型")
        prod = _make_product("VPN功能", "否")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.NEGATIVE.value

    def test_product_extra_support(self):
        bid = _make_bid("冗余电源", "否", param_type="布尔型")
        prod = _make_product("冗余电源", "支持")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.POSITIVE.value


class TestFunctionalJudgment:
    def test_functional_coverage(self):
        bid = _make_bid("审计功能", "支持对网络流量进行深度审计和日志记录", param_type="功能描述")
        prod = _make_product("审计功能", "深度审计日志记录网络流量分析回溯")
        result = judge(bid, prod)
        assert result.deviation_type in (
            DeviationType.NEUTRAL.value,
            DeviationType.UNCONFIRMED.value,
        )

    def test_empty_bid(self):
        bid = _make_bid("描述", "", param_type="功能描述")
        prod = _make_product("描述", "some description")
        result = judge(bid, prod)
        assert result.deviation_type == DeviationType.UNCONFIRMED.value


class TestRiskClassification:
    def test_disqualify_material_negative(self):
        dev = DeviationResult(
            id="dr1", parsed_param_id="p1", match_param_id="m1",
            deviation_type=DeviationType.NEGATIVE.value,
        )
        assert classify_risk(dev, is_material=True) == RiskLevel.DISQUALIFY.value

    def test_score_deduction_normal_negative(self):
        dev = DeviationResult(
            id="dr2", parsed_param_id="p2", match_param_id="m2",
            deviation_type=DeviationType.NEGATIVE.value,
        )
        assert classify_risk(dev, is_material=False) == RiskLevel.SCORE_DEDUCTION.value

    def test_no_risk_neutral(self):
        dev = DeviationResult(
            id="dr3", parsed_param_id="p3", match_param_id="m3",
            deviation_type=DeviationType.NEUTRAL.value,
        )
        assert classify_risk(dev, is_material=False) == RiskLevel.NONE.value

    def test_disqualify_material_unconfirmed(self):
        dev = DeviationResult(
            id="dr4", parsed_param_id="p4", match_param_id="m4",
            deviation_type=DeviationType.UNCONFIRMED.value,
        )
        assert classify_risk(dev, is_material=True) == RiskLevel.DISQUALIFY.value


class TestBatchJudge:
    def test_all_matched(self):
        bid = _make_bid("吞吐量", ">=10")
        prod = _make_product("吞吐量", "12")
        pair = MatchPair(bid_param=bid, product_param=prod, similarity_score=1.0, match_method="exact")
        results = batch_judge([pair], [])
        assert len(results) == 1

    def test_includes_unmatched(self):
        bid = _make_bid("未知参数", "要求", is_material=True)
        results = batch_judge([], [bid])
        assert len(results) == 1
        assert results[0].deviation_type == DeviationType.UNCONFIRMED.value
        assert results[0].risk_level == RiskLevel.DISQUALIFY.value

    def test_null_product_param_in_pair(self):
        bid = _make_bid("A", "req")
        pair = MatchPair(bid_param=bid, product_param=None, similarity_score=0.3, match_method="vector")
        results = batch_judge([pair], [])
        assert len(results) == 1
        assert results[0].deviation_type == DeviationType.UNCONFIRMED.value
