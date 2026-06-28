"""
数据模型定义

使用 dataclass 定义核心业务实体，SQLite 表结构在 migrations.py 中管理。
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ParamType(str, Enum):
    NUMERIC = "数值范围"
    ENUM = "枚举值"
    BOOLEAN = "布尔型"
    FUNCTIONAL = "功能描述"


class DeviationType(str, Enum):
    POSITIVE = "正偏离"
    NEUTRAL = "无偏离"
    NEGATIVE = "负偏离"
    UNCONFIRMED = "无法确认"


class RiskLevel(str, Enum):
    DISQUALIFY = "废标级风险"
    SCORE_DEDUCTION = "得分扣分项"
    NONE = "无风险"


class RuleType(str, Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PARSING = "PARSING"
    PARSE_DONE = "PARSE_DONE"
    COMPARING = "COMPARING"
    COMPARE_DONE = "COMPARE_DONE"
    SCORING = "SCORING"
    SCORE_DONE = "SCORE_DONE"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ProductLine:
    id: str
    name: str
    description: str = ""
    created_at: str = ""


@dataclass
class ProductVersion:
    id: str
    product_line_id: str
    version_name: str
    release_date: str = ""
    is_active: bool = False


@dataclass
class ParameterRecord:
    id: str
    version_id: str
    name: str
    nominal_value: str = ""
    acceptable_range: str = ""
    unit: str = ""
    deviation_preset: str = ""
    category: str = ""


@dataclass
class EvidenceIndex:
    id: str
    parameter_id: str
    doc_title: str = ""
    doc_path: str = ""
    page_ref: str = ""


@dataclass
class ParameterAlias:
    id: str
    parameter_id: str
    alias: str


@dataclass
class AnalysisTask:
    id: str
    status: str = TaskStatus.PENDING.value
    bid_file_path: str = ""
    product_line_id: str = ""
    version_id: str = ""
    context_snapshot: str = "{}"
    created_at: str = ""
    updated_at: str = ""


@dataclass
class ParsedParameter:
    id: str
    task_id: str
    name: str
    requirement_value: str = ""
    unit: str = ""
    is_material: bool = False
    param_type: str = ""
    source_location: str = ""
    parent_id: str = ""


@dataclass
class DeviationResult:
    id: str
    parsed_param_id: str
    match_param_id: str = ""
    deviation_type: str = DeviationType.UNCONFIRMED.value
    similarity_score: float = 0.0
    explanation: str = ""
    risk_level: str = RiskLevel.NONE.value
    suggestion: str = ""


@dataclass
class ScoreResult:
    id: str
    task_id: str
    rule_name: str = ""
    max_score: float = 0.0
    actual_score: float = 0.0
    trace_data: str = "{}"


@dataclass
class ScoringRule:
    id: str
    name: str = ""
    max_score: float = 0.0
    rule_type: str = RuleType.QUANTITATIVE.value
    conditions: list = field(default_factory=list)
    bonus_rules: list = field(default_factory=list)
    penalty_rules: list = field(default_factory=list)


@dataclass
class Condition:
    param_name: str = ""
    operator: str = "EQ"
    target_value: str = ""
    score: float = 0.0


@dataclass
class ParameterItem:
    id: str
    name: str
    requirement_value: str = ""
    unit: str = ""
    is_material: bool = False
    param_type: str = ""
    source_location: str = ""
    parent_id: Optional[str] = None
    children: list = field(default_factory=list)


@dataclass
class MatchPair:
    bid_param: ParameterItem
    product_param: Optional[ParameterRecord]
    similarity_score: float = 0.0
    match_method: str = ""


@dataclass
class ScoreSummary:
    total_score: float = 0.0
    max_possible_score: float = 0.0
    score_rate: float = 0.0
    item_scores: list = field(default_factory=list)
    improvement_items: list = field(default_factory=list)
