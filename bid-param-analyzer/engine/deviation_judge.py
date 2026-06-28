"""
偏离判定器

按参数类型（数值范围、枚举值、布尔型、功能性描述）执行对应的
偏离状态判定逻辑，输出偏离类型和风险等级。
"""
import re
import uuid
from typing import Optional

from database.models import (
    ParameterItem,
    ParameterRecord,
    DeviationResult,
    DeviationType,
    RiskLevel,
    ParamType,
    MatchPair,
)


def _parse_numeric(value: str) -> tuple[Optional[float], str, str]:
    """
    解析数值型参数值，返回 (数值, 运算符, 原始字符串)。

    支持格式: ">=40", "不低于40", "40", "40~100"
    """
    value = value.strip()
    if not value:
        return None, "", value

    op_map = {
        ">=": ">=", "≥": ">=", "不低于": ">=", "不少于": ">=", "不小于": ">=",
        "<=": "<=", "≤": "<=", "不高于": "<=", "不大于": "<=", "不超过": "<=",
        ">": ">", "大于": ">",
        "<": "<", "小于": "<",
        "=": "=", "等于": "=",
    }

    operator = ""
    value_rest = value

    for op_str in sorted(op_map.keys(), key=len, reverse=True):
        if value.startswith(op_str):
            operator = op_map[op_str]
            value_rest = value[len(op_str):].strip()
            break

    match = re.search(r"[\d,.]+", value_rest)
    if match:
        try:
            num_str = match.group().replace(",", "")
            num = float(num_str)
            return num, operator, value
        except ValueError:
            pass

    return None, operator, value


def _parse_numeric_range(value: str) -> tuple[Optional[float], Optional[float]]:
    """
    解析范围值，支持 "40~100", "40-100" 等格式。
    返回 (最小值, 最大值)。
    """
    match = re.match(r"([\d,.]+)\s*[~\-～]\s*([\d,.]+)", value)
    if match:
        try:
            lo = float(match.group(1).replace(",", ""))
            hi = float(match.group(2).replace(",", ""))
            return lo, hi
        except ValueError:
            pass
    return None, None


def _judge_numeric(bid_value: str, product_value: str) -> tuple[str, str]:
    bid_num, bid_op, _ = _parse_numeric(bid_value)
    bid_lo, bid_hi = _parse_numeric_range(bid_value)

    prod_num, _, _ = _parse_numeric(product_value)
    prod_lo, prod_hi = _parse_numeric_range(product_value)

    if bid_num is None and bid_lo is None:
        return DeviationType.UNCONFIRMED.value, "无法解析招标要求数值"

    if prod_num is None and prod_lo is None:
        return DeviationType.UNCONFIRMED.value, "无法解析产品参数数值"

    def check_single_requirement(req_num: float, req_op: str, prod_num: float) -> bool:
        if req_op in (">=", ""):
            return prod_num >= req_num
        elif req_op == ">":
            return prod_num > req_num
        elif req_op == "<=":
            return prod_num <= req_num
        elif req_op == "<":
            return prod_num < req_num
        elif req_op == "=":
            return abs(prod_num - req_num) < 1e-9
        return prod_num >= req_num

    satisfied = False
    if bid_num is not None and bid_op:
        if prod_num is not None:
            satisfied = check_single_requirement(bid_num, bid_op, prod_num)
    elif bid_num is not None:
        if prod_num is not None:
            satisfied = prod_num >= bid_num
    elif bid_lo is not None:
        if prod_lo is not None:
            satisfied = prod_lo >= bid_lo

    if satisfied:
        if prod_num is not None and bid_num is not None and prod_num > bid_num * 1.1:
            return DeviationType.POSITIVE.value, f"产品参数({product_value})优于招标要求({bid_value})"
        return DeviationType.NEUTRAL.value, f"产品参数({product_value})满足招标要求({bid_value})"

    return DeviationType.NEGATIVE.value, f"产品参数({product_value})低于招标要求({bid_value})"


def _judge_enum(bid_value: str, product_value: str) -> tuple[str, str]:
    bid_options = set(re.split(r"[/／、,，;；]", bid_value))
    bid_options = {o.strip() for o in bid_options if o.strip()}

    prod_options = set(re.split(r"[/／、,，;；]", product_value))
    prod_options = {o.strip() for o in prod_options if o.strip()}

    if not bid_options:
        return DeviationType.UNCONFIRMED.value, "招标要求枚举值为空"

    if prod_options.issuperset(bid_options):
        return DeviationType.NEUTRAL.value, f"产品支持所有要求的选项"

    missing = bid_options - prod_options
    if missing:
        return DeviationType.NEGATIVE.value, f"产品缺少以下选项: {', '.join(missing)}"

    return DeviationType.NEUTRAL.value, "产品覆盖所有要求选项"


def _judge_boolean(bid_value: str, product_value: str) -> tuple[str, str]:
    positive_words = {"支持", "是", "有", "具备", "满足", "符合", "true", "yes", "1"}

    bid_lower = bid_value.lower().strip()
    prod_lower = product_value.lower().strip()

    bid_positive = any(w in bid_lower for w in positive_words)
    prod_positive = any(w in prod_lower for w in positive_words)

    if bid_positive and prod_positive:
        return DeviationType.NEUTRAL.value, "产品支持该功能"
    elif not bid_positive and not prod_positive:
        return DeviationType.NEUTRAL.value, "产品与招标要求一致"
    elif bid_positive and not prod_positive:
        return DeviationType.NEGATIVE.value, "产品不支持招标要求的功能"
    else:
        return DeviationType.POSITIVE.value, "产品支持但招标未做要求"


def _judge_functional(bid_value: str, product_value: str) -> tuple[str, str]:
    bid_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", bid_value))
    prod_words = set(re.findall(r"[\u4e00-\u9fff]{2,}", product_value))

    if not bid_words:
        return DeviationType.UNCONFIRMED.value, "无法从功能描述中提取关键词"

    overlap = bid_words & prod_words
    coverage = len(overlap) / len(bid_words) if bid_words else 0

    if coverage >= 0.8:
        return DeviationType.NEUTRAL.value, f"功能关键词覆盖率 {coverage:.0%}"
    elif coverage >= 0.5:
        return DeviationType.UNCONFIRMED.value, f"功能关键词覆盖不足({coverage:.0%})，需人工复核"
    else:
        return DeviationType.UNCONFIRMED.value, f"功能关键词覆盖率过低({coverage:.0%})，无法自动确认"


def judge(bid_param: ParameterItem, product_param: ParameterRecord) -> DeviationResult:
    """
    单条参数偏离判定。

    根据招标参数的 param_type 选择对应的判定逻辑。
    """
    param_type = bid_param.param_type or ParamType.FUNCTIONAL.value

    if param_type == ParamType.NUMERIC.value:
        dev_type, explanation = _judge_numeric(
            bid_param.requirement_value, product_param.nominal_value
        )
    elif param_type == ParamType.ENUM.value:
        dev_type, explanation = _judge_enum(
            bid_param.requirement_value, product_param.nominal_value
        )
    elif param_type == ParamType.BOOLEAN.value:
        dev_type, explanation = _judge_boolean(
            bid_param.requirement_value, product_param.nominal_value
        )
    else:
        dev_type, explanation = _judge_functional(
            bid_param.requirement_value, product_param.nominal_value
        )

    return DeviationResult(
        id=f"dr_{uuid.uuid4().hex[:12]}",
        parsed_param_id=bid_param.id,
        match_param_id=product_param.id,
        deviation_type=dev_type,
        similarity_score=0.0,
        explanation=explanation,
        risk_level=RiskLevel.NONE.value,
        suggestion="",
    )


def classify_risk(deviation: DeviationResult, is_material: bool = False) -> str:
    """
    风险分级：实质性条款负偏离 → 废标级风险
              普通参数负偏离 → 得分扣分项
              其他 → 无风险
    """
    if deviation.deviation_type == DeviationType.NEGATIVE.value:
        if is_material:
            return RiskLevel.DISQUALIFY.value
        return RiskLevel.SCORE_DEDUCTION.value

    if deviation.deviation_type == DeviationType.UNCONFIRMED.value:
        if is_material:
            return RiskLevel.DISQUALIFY.value
        return RiskLevel.NONE.value

    return RiskLevel.NONE.value


def batch_judge(
    matched_pairs: list[MatchPair],
    unmatched_params: list[ParameterItem],
) -> list[DeviationResult]:
    """
    批量判定所有参数对的偏离状态，包含未匹配项的兜底处理。
    """
    results: list[DeviationResult] = []

    for pair in matched_pairs:
        if pair.product_param is None:
            results.append(DeviationResult(
                id=f"dr_{uuid.uuid4().hex[:12]}",
                parsed_param_id=pair.bid_param.id,
                match_param_id="",
                deviation_type=DeviationType.UNCONFIRMED.value,
                similarity_score=pair.similarity_score,
                explanation="未匹配到产品参数",
                risk_level=RiskLevel.NONE.value,
                suggestion="需人工确认",
            ))
        else:
            result = judge(pair.bid_param, pair.product_param)
            result.similarity_score = pair.similarity_score
            result.risk_level = classify_risk(result, pair.bid_param.is_material)
            results.append(result)

    for unmatched in unmatched_params:
        risk = classify_risk(
            DeviationResult(
                id="",
                parsed_param_id=unmatched.id,
                deviation_type=DeviationType.UNCONFIRMED.value,
            ),
            unmatched.is_material,
        )
        results.append(DeviationResult(
            id=f"dr_{uuid.uuid4().hex[:12]}",
            parsed_param_id=unmatched.id,
            match_param_id="",
            deviation_type=DeviationType.UNCONFIRMED.value,
            similarity_score=0.0,
            explanation="未匹配到对应的产品参数",
            risk_level=risk,
            suggestion="请手动映射参数或补充产品数据",
        ))

    return results
