"""
semantic_matcher.py 单元测试

覆盖: 精确匹配、别名匹配、向量匹配、未匹配项、空输入
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from engine.semantic_matcher import (
    match_parameters,
    calculate_similarity,
    _normalize,
)
from database.models import ParameterItem, ParameterRecord, MatchPair


def _param_item(name: str, **kw) -> ParameterItem:
    return ParameterItem(id=f"pi_{name}", name=name, **kw)


def _param_record(name: str, **kw) -> ParameterRecord:
    return ParameterRecord(id=f"pr_{name}", name=name, version_id="v1", **kw)


class TestNormalize:
    def test_lower_and_strip(self):
        assert _normalize("  Throughput  ") == "throughput"

    def test_remove_parens(self):
        assert _normalize("CPU(核心数)") == "cpu核心数"

    def test_replace_symbols(self):
        assert ">=" in _normalize("≥40")


class TestCalculateSimilarity:
    def test_identical(self):
        assert calculate_similarity("吞吐量", "吞吐量") == 1.0

    def test_different(self):
        s = calculate_similarity("最大吞吐量", "保修期限")
        assert s < 0.5

    def test_similar(self):
        s = calculate_similarity("最大吞吐量", "吞吐量")
        assert 0.3 <= s <= 1.0

    def test_empty_strings(self):
        assert calculate_similarity("", "anything") == 0.0
        assert calculate_similarity("anything", "") == 0.0

    def test_single_char(self):
        assert 0.0 <= calculate_similarity("a", "b") <= 1.0


class TestMatchParameters:
    def test_exact_match(self):
        bid = [_param_item("最大吞吐量")]
        prod = [_param_record("最大吞吐量", nominal_value="10Gbps")]
        pairs, unmatched = match_parameters(bid, prod)
        assert len(pairs) == 1
        assert len(unmatched) == 0
        assert pairs[0].match_method == "exact"

    def test_alias_match(self):
        bid = [_param_item("吞吐量")]
        prod = [_param_record("最大吞吐量", nominal_value="10Gbps")]
        aliases = {prod[0].id: ["吞吐量", "Throughput"]}
        pairs, unmatched = match_parameters(bid, prod, aliases)
        assert len(pairs) == 1
        assert pairs[0].match_method == "alias"

    def test_vector_match_threshold(self):
        bid = [_param_item("最大吞吐量")]
        prod = [_param_record("网络吞吐量", nominal_value="10Gbps")]
        pairs, unmatched = match_parameters(bid, prod)
        assert len(pairs) + len(unmatched) == len(bid)

    def test_unmatched_single(self):
        bid = [_param_item("完全不同的参数")]
        prod = [_param_record("最大吞吐量")]
        pairs, unmatched = match_parameters(bid, prod)
        assert len(pairs) == 0
        assert len(unmatched) == 1

    def test_multiple_bid_params(self):
        bid = [
            _param_item("最大吞吐量"),
            _param_item("并发连接数"),
        ]
        prod = [
            _param_record("最大吞吐量"),
            _param_record("并发连接数"),
        ]
        pairs, unmatched = match_parameters(bid, prod)
        assert len(pairs) == 2
        assert len(unmatched) == 0

    def test_product_param_used_once(self):
        bid = [
            _param_item("最大吞吐量"),
            _param_item("吞吐量"),
        ]
        prod = [
            _param_record("最大吞吐量"),
        ]
        aliases = {prod[0].id: ["吞吐量"]}
        pairs, unmatched = match_parameters(bid, prod, aliases)
        assert len(pairs) == 1
        assert len(unmatched) == 1

    def test_empty_bid(self):
        pairs, unmatched = match_parameters([], [_param_record("A")])
        assert pairs == []
        assert unmatched == []

    def test_empty_product(self):
        bid = [_param_item("A")]
        pairs, unmatched = match_parameters(bid, [])
        assert len(pairs) == 0
        assert len(unmatched) == 1
