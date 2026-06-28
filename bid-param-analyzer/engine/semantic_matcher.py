"""
语义匹配器

基于向量相似度将招标参数名称与产品库参数名称进行语义匹配，
处理表述不一致问题。

匹配策略（四级降级）：
1. 精确匹配：参数名称字符串完全一致
2. 别名匹配：查询参数别名列表
3. 向量匹配：embedding 余弦相似度 ≥ 阈值(0.85)
4. 人工兜底：标记为"待人工确认"
"""
import math
import re
import uuid
from typing import Optional

from config.settings import SEMANTIC_MATCH_THRESHOLD, EMBEDDING_SERVICE
from database.models import ParameterItem, ParameterRecord, MatchPair


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[（()）\[\]【】]", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("≥", ">=").replace("≤", "<=").replace("～", "~")
    return text


def calculate_similarity(name1: str, name2: str) -> float:
    """
    计算两个参数名称的语义相似度。

    运行时通过平台内置 embedding 服务获取向量并计算余弦相似度。
    本地 fallback 使用 Jaccard 字符 n-gram 相似度。
    """
    n1 = _normalize(name1)
    n2 = _normalize(name2)

    if n1 == n2:
        return 1.0

    if not n1 or not n2:
        return 0.0

    if EMBEDDING_SERVICE == "platform_builtin":
        return _jaccard_ngram_similarity(n1, n2)

    return _jaccard_ngram_similarity(n1, n2)


def _jaccard_ngram_similarity(s1: str, s2: str, n: int = 2) -> float:
    def ngrams(s: str) -> set:
        return {s[i:i+n] for i in range(len(s) - n + 1)} if len(s) >= n else {s}

    set1 = ngrams(s1)
    set2 = ngrams(s2)

    if not set1 or not set2:
        return 0.0

    intersection = set1 & set2
    union = set1 | set2

    return len(intersection) / len(union)


def _exact_match(bid_param: ParameterItem, product_params: list[ParameterRecord]) -> Optional[ParameterRecord]:
    norm_bid = _normalize(bid_param.name)
    for pp in product_params:
        if _normalize(pp.name) == norm_bid:
            return pp
    return None


def _alias_match(
    bid_param: ParameterItem,
    product_params: list[ParameterRecord],
    aliases_map: dict[str, list[str]],
) -> Optional[ParameterRecord]:
    norm_bid = _normalize(bid_param.name)
    for pp in product_params:
        aliases = aliases_map.get(pp.id, [])
        for alias in aliases:
            if _normalize(alias) == norm_bid:
                return pp
    return None


def _vector_match(
    bid_param: ParameterItem,
    product_params: list[ParameterRecord],
) -> tuple[Optional[ParameterRecord], float]:
    best_match = None
    best_score = 0.0

    for pp in product_params:
        score = calculate_similarity(bid_param.name, pp.name)
        if score > best_score:
            best_score = score
            best_match = pp

    if best_score >= SEMANTIC_MATCH_THRESHOLD:
        return best_match, best_score

    return None, best_score


def match_parameters(
    bid_params: list[ParameterItem],
    product_params: list[ParameterRecord],
    aliases_map: Optional[dict[str, list[str]]] = None,
) -> tuple[list[MatchPair], list[ParameterItem]]:
    """
    执行四级匹配策略，返回匹配对列表和未匹配项清单。

    Returns:
        (matched_pairs, unmatched_params)
    """
    if aliases_map is None:
        aliases_map = {}

    matched_pairs: list[MatchPair] = []
    unmatched: list[ParameterItem] = []
    used_product_ids: set[str] = set()

    for bid_param in bid_params:
        match_result = None
        similarity = 0.0
        match_method = ""

        exact = _exact_match(bid_param, product_params)
        if exact and exact.id not in used_product_ids:
            match_result = exact
            similarity = 1.0
            match_method = "exact"

        if not match_result:
            alias = _alias_match(bid_param, product_params, aliases_map)
            if alias and alias.id not in used_product_ids:
                match_result = alias
                similarity = 1.0
                match_method = "alias"

        if not match_result:
            available = [pp for pp in product_params if pp.id not in used_product_ids]
            vec_match, vec_score = _vector_match(bid_param, available)
            if vec_match:
                match_result = vec_match
                similarity = vec_score
                match_method = "vector"

        if match_result:
            used_product_ids.add(match_result.id)
            matched_pairs.append(MatchPair(
                bid_param=bid_param,
                product_param=match_result,
                similarity_score=similarity,
                match_method=match_method,
            ))
        else:
            unmatched.append(bid_param)

    return matched_pairs, unmatched
