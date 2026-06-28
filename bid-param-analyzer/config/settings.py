"""
全局配置模块

定义投标参数智能分析 Skill 的所有可配置参数。
"""
import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 文档解析配置 ---
OCR_ENGINE = "platform_builtin"
DOCPARSE_ENABLED = True
SUPPORTED_FILE_TYPES = [".pdf", ".doc", ".docx"]
MAX_FILE_SIZE_MB = 200
MAX_PAGE_COUNT = 200
PARSE_TIMEOUT_PDF_SECONDS = 30
PARSE_TIMEOUT_DOCX_SECONDS = 15

# --- 语义匹配配置 ---
SEMANTIC_MATCH_THRESHOLD = 0.85
EMBEDDING_SERVICE = "platform_builtin"

# --- 评分与决策配置 ---
SCORE_RECOMMEND_THRESHOLD = 0.80
SCORE_CAUTION_THRESHOLD = 0.60
SCORE_REJECT_THRESHOLD_BELOW = 0.60

# --- 数据库配置 ---
DATABASE_PATH = os.path.join(BASE_DIR, "data", "param_base.db")
DATA_DIR = os.path.join(BASE_DIR, "data")

# --- 存储配置 ---
TEMP_FILE_DIR = os.path.join(BASE_DIR, "data", "temp_uploads")
TEMP_FILE_TTL_HOURS = 72

# --- 报告配置 ---
REPORT_TEMPLATE_DIR = os.path.join(BASE_DIR, "reports", "templates")
REPORT_OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")

# --- 参数库 Excel 导入配置 ---
EXCEL_REQUIRED_FIELDS = ["参数名称", "标称值", "单位"]
EXCEL_FIELD_MAPPING = {
    "参数名称": "name",
    "标称值": "nominal_value",
    "可满足范围": "acceptable_range",
    "单位": "unit",
    "偏离类型预设": "deviation_preset",
    "类别": "category",
    "证明材料标题": "evidence_title",
    "证明材料路径": "evidence_path",
    "证明材料页码": "evidence_page_ref",
}

# --- 评分规则配置 ---
SCORING_RULE_TYPE = {
    "QUANTITATIVE": "quantitative",
    "QUALITATIVE": "qualitative",
}

CONDITION_OPERATORS = ["EQ", "GT", "LT", "GTE", "LTE", "CONTAINS"]

DEVIATION_TYPES = {
    "POSITIVE": "正偏离",
    "NEUTRAL": "无偏离",
    "NEGATIVE": "负偏离",
    "UNCONFIRMED": "无法确认",
}

RISK_LEVELS = {
    "DISQUALIFY": "废标级风险",
    "SCORE_DEDUCTION": "得分扣分项",
    "NONE": "无风险",
}
