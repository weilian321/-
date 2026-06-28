"""
结构化参数提取器

从招标文件全文中自动定位技术参数章节、评分细则、资格门槛，
并提取结构化参数条目、识别实质性条款、解析评分规则。
"""
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from database.models import (
    ParamType,
    ParameterItem,
    ScoringRule,
    Condition,
    RuleType,
)


@dataclass
class Section:
    name: str
    start: int
    end: int
    section_type: str = ""


SECTION_PATTERNS = {
    "technical_params": [
        r"第.{1,3}[章节].{0,10}(技术参数|技术规格|技术指标|产品参数|产品规格|性能参数)",
        r"(技术参数|技术规格|技术指标|产品参数|产品规格|性能参数).{0,5}(要求|一览表|表|清单)",
        r"(货物|设备|产品).{0,10}(技术|参数|规格).{0,5}(要求|一览)",
        r"(性能|功能|配置).{0,5}(参数|指标|要求)",
        r"(详细|主要).{0,5}(技术|参数).{0,5}(要求|指标|规格)",
    ],
    "scoring_rules": [
        r"第.{1,3}[章节].{0,10}(评分|评审|打分|评价)",
        r"(评分|评审|打分|评价).{0,5}(细则|标准|办法|规则|方案|表)",
        r"(技术|商务).{0,5}(评分|评审).{0,5}(细则|标准|办法)",
        r"(综合|详细).{0,3}(评分|评审|打分).{0,5}(细则|标准|办法)",
        r"(分值|得分|评分).{0,5}(分配|设置|标准|说明)",
    ],
    "qualification": [
        r"第.{1,3}[章节].{0,10}(资格|资质|门槛|准入)",
        r"(资格|资质|门槛|准入).{0,5}(条件|要求|条款|审查)",
        r"(投标人|供应商|报价人).{0,5}(资格|资质|要求)",
        r"(基本|特定|特殊).{0,5}(资格|资质|条件)",
        r"(实质性|星号|\*).{0,5}(条款|要求|响应)",
    ],
}


PARAM_VALUE_PATTERNS = [
    re.compile(r"(?:^|\n)\s*(?:(?:\d+[\.\)、]\s*)|(?:[*\-\•]\s*))(.+?)[：:]\s*(.+?)(?:\n|$)", re.MULTILINE),
    re.compile(r"(?:^|\n)\s*([^：:\n]{2,40}?)[：:]\s*(.+?)(?:\n|$)", re.MULTILINE),
]

NUMERIC_RANGE_PATTERN = re.compile(
    r"([≥≤><]=?|不小于|不低于|不高于|不大于|大于|小于|等于|不低于|不少于|不超过)\s*([\d,.]+)\s*([a-zA-Z%/\u4e00-\u9fff]*)$"
)

ENUM_SEPARATORS = re.compile(r"[/／、,，;；]")

STAR_ITEM_PATTERNS = [
    re.compile(r"(?:^|\s|[（(])\*(?!\s*\d)", re.MULTILINE),
    re.compile(r"[★☆✶✷✹✦✧▪▸►▶◆◇◆❖]"),
    re.compile(r"\(?\*号条款\)?"),
    re.compile(r"(实质性\s*(?:条款|要求|响应))"),
    re.compile(r"(不可\s*偏离\s*(?:条款|项))"),
    re.compile(r"(必须\s*满足\s*(?:的|条款|项))"),
]

SCORE_PATTERNS = [
    re.compile(
        r"([^，。,\.\n]{2,30}?)[：:]\s*[-–]?\s*(\d+)\s*分",
    ),
    re.compile(
        r"([^，。,\.\n]{2,30}?)\s*[（(](-?\d+)\s*分[）)]",
    ),
]


def locate_key_sections(full_text: str) -> list[Section]:
    """
    基于章节标题关键词匹配定位技术参数章节、评分细则表、资格门槛条款。

    返回按原文位置排序的 Section 列表。
    """
    sections: list[Section] = []

    for section_type, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, full_text, re.IGNORECASE):
                sections.append(Section(
                    name=match.group(0),
                    start=match.start(),
                    end=match.end(),
                    section_type=section_type,
                ))

    sections.sort(key=lambda s: s.start)

    merged = _merge_overlapping_sections(sections)
    return merged


def _merge_overlapping_sections(sections: list[Section]) -> list[Section]:
    if not sections:
        return []

    merged: list[Section] = []
    current = sections[0]

    for next_sec in sections[1:]:
        gap = next_sec.start - current.end

        if gap <= 200 and current.section_type == next_sec.section_type:
            current = Section(
                name=f"{current.name} / {next_sec.name}",
                start=current.start,
                end=max(current.end, next_sec.end),
                section_type=current.section_type,
            )
        else:
            merged.append(current)
            current = next_sec

    merged.append(current)
    return merged


def extract_parameters(section_text: str) -> list[ParameterItem]:
    """
    从技术参数章节文本中逐行提取参数条目。

    支持以下格式：
    - 1. 参数名称：要求值
    - * 参数名称：>=数值 单位
    - 参数名称：支持/不支持
    - 表格行格式
    """
    params: list[ParameterItem] = []
    parent_stack: list[ParameterItem] = []

    for pattern in PARAM_VALUE_PATTERNS:
        for match in pattern.finditer(section_text):
            raw_name = match.group(1).strip()
            raw_value = match.group(2).strip() if len(match.groups()) > 1 else ""

            if _is_skip_line(raw_name, raw_value):
                continue

            is_material = _check_star(raw_name)

            name = _clean_param_name(raw_name)
            value, unit = _split_value_unit(raw_value)

            param_type = _infer_param_type(value)
            param = ParameterItem(
                id=f"pp_{uuid.uuid4().hex[:12]}",
                name=name,
                requirement_value=value,
                unit=unit,
                is_material=is_material,
                param_type=param_type,
                source_location=f"offset={match.start()}",
            )
            params.append(param)

    seen_names = set()
    unique_params = []
    for p in params:
        key = (p.name, p.requirement_value)
        if key not in seen_names:
            seen_names.add(key)
            unique_params.append(p)

    return unique_params


def _check_star(raw_text: str) -> bool:
    combined = raw_text
    for pattern in STAR_ITEM_PATTERNS:
        if pattern.search(combined):
            return True
    return False


def _is_skip_line(name: str, value: str) -> bool:
    skip_patterns = [
        r"^(招标|投标|项目|采购|工程|货物|服务|合同|技术|商务|价格).{0,5}(项目|编号|名称|内容|范围|要求|概述)",
        r"^(一|二|三|四|五|六|七|八|九|十)[、.．)]",
        r"^(第.{1,3}[章节条])",
        r"^(备注|说明|注释|注意|注)",
        r"^(附件|附录)",
    ]
    for pat in skip_patterns:
        if re.match(pat, name):
            return True
    return len(name) < 2 or (not value and not name)


def _clean_param_name(raw: str) -> str:
    raw = re.sub(r"^(\d+[\.\)、]\s*)+", "", raw)
    raw = re.sub(r"^[*\-\•★☆]\s*", "", raw)
    raw = re.sub(r"[（(]注[：:].*$", "", raw)
    return raw.strip()


def _split_value_unit(raw_value: str) -> tuple[str, str]:
    if not raw_value:
        return "", ""

    raw_value = raw_value.strip()
    raw_value = re.sub(r"[；;]\s*$", "", raw_value)

    match = NUMERIC_RANGE_PATTERN.search(raw_value)
    if match:
        operator = match.group(1)
        number = match.group(2)
        unit = match.group(3) if match.group(3) else ""
        return f"{operator}{number}", unit

    unit_match = re.search(
        r"([\d,.]+)\s*(Gbps|Mbps|Kbps|bps|GB|MB|KB|TB|PB|GHz|MHz|Hz|ms|s|W|V|A|"
        r"万|千|亿|个|台|套|条|路|层|人|次|元|年|月|日|小时|分钟|秒|%|w|db|dB|"
        r"[a-zA-Z]{1,5})$",
        raw_value,
    )
    if unit_match:
        base_value = raw_value[:unit_match.start()].strip()
        raw_unit = unit_match.group(2)
        return base_value, raw_unit

    return raw_value, ""


def _infer_param_type(value: str) -> str:
    if not value:
        return ParamType.FUNCTIONAL.value

    is_support = re.match(r"^(支持|不支持|是|否|有|无|具备|不具备)$", value)
    if is_support:
        return ParamType.BOOLEAN.value

    has_operator = re.match(r"[≥≤><]=?\d", value)
    if has_operator:
        return ParamType.NUMERIC.value

    has_number = re.search(r"\d+", value)
    if has_number and re.search(r"[\d,.]+", value):
        return ParamType.NUMERIC.value

    enum_count = len(ENUM_SEPARATORS.split(value))
    if enum_count >= 3:
        return ParamType.ENUM.value

    return ParamType.FUNCTIONAL.value


def detect_star_items(params: list[ParameterItem]) -> list[ParameterItem]:
    """
    识别标注为实质性条款（*号/星号/必须满足）的参数。

    在参数名称和原始位置文本中匹配星号标记。
    """
    for param in params:
        combined = f"{param.name} {param.requirement_value} {param.source_location}"
        for pattern in STAR_ITEM_PATTERNS:
            if pattern.search(combined):
                param.is_material = True
                break

    return params


def extract_scoring_rules(rules_section: str) -> list[ScoringRule]:
    """
    从评分细则章节提取结构化的评分规则。

    识别：
    - 定量打分：参数名称：<分数>分
    - 定性打分：分组描述和等级分数
    """
    rules: list[ScoringRule] = []

    for pattern in SCORE_PATTERNS:
        for match in pattern.finditer(rules_section):
            raw_name = match.group(1).strip()
            score_str = match.group(2).strip()

            if _is_skip_line(raw_name, score_str):
                continue

            try:
                score = float(score_str)
            except ValueError:
                continue

            rule_name = _clean_param_name(raw_name)
            rule = ScoringRule(
                id=f"sr_{uuid.uuid4().hex[:12]}",
                name=rule_name,
                max_score=score,
                rule_type=RuleType.QUANTITATIVE.value,
                conditions=[Condition(
                    param_name=rule_name,
                    operator="GTE",
                    target_value="",
                    score=score,
                )],
            )
            rules.append(rule)

    seen_rules = set()
    unique_rules = []
    for r in rules:
        if r.name not in seen_rules:
            seen_rules.add(r.name)
            unique_rules.append(r)

    return unique_rules


def extract_parameters_from_table(table_headers: list[str], table_rows: list[list[str]]) -> list[ParameterItem]:
    """
    从表格数据中提取参数条目。

    自动识别表头映射（参数名称、要求值、单位等常见列名）。
    """
    header_map = _map_table_headers(table_headers)
    if "name" not in header_map:
        return []

    params: list[ParameterItem] = []
    for row in table_rows:
        name = _safe_cell(row, header_map.get("name", -1))
        if not name or _is_skip_line(name, ""):
            continue

        raw_name_cell = name
        name = _clean_param_name(name)
        is_material = _check_star(raw_name_cell)
        value = _safe_cell(row, header_map.get("value", -1))
        unit = _safe_cell(row, header_map.get("unit", -1))

        if value:
            clean_value, clean_unit = _split_value_unit(value)
            if not unit and clean_unit:
                unit = clean_unit
            value = clean_value

        param_type = _infer_param_type(value)
        params.append(ParameterItem(
            id=f"pp_{uuid.uuid4().hex[:12]}",
            name=name,
            requirement_value=value,
            unit=unit,
            is_material=is_material,
            param_type=param_type,
            source_location="table",
        ))

    return params


def _map_table_headers(headers: list[str]) -> dict[str, int]:
    header_map = {}
    name_keywords = ["参数", "名称", "项目", "指标", "性能", "功能", "配置", "规格"]
    value_keywords = ["要求", "指标值", "参数值", "规格", "技术指标", "要求值", "标准"]
    unit_keywords = ["单位"]

    for idx, header in enumerate(headers):
        hl = header.lower().strip()
        if any(k in hl for k in name_keywords if not any(kk in hl for kk in value_keywords)):
            if "name" not in header_map:
                header_map["name"] = idx
        elif any(k in hl for k in value_keywords):
            if "value" not in header_map:
                header_map["value"] = idx
        elif any(k in hl for k in unit_keywords):
            if "unit" not in header_map:
                header_map["unit"] = idx

    if "value" not in header_map and "name" in header_map:
        for idx in range(len(headers)):
            if idx not in header_map.values():
                header_map["value"] = idx
                break

    return header_map


def _safe_cell(row: list[str], idx: int) -> str:
    if idx < 0 or idx >= len(row):
        return ""
    return row[idx].strip()
