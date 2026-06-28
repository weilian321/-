"""
analysis_report.py 单元测试

覆盖: 报告生成、文件输出验证
"""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from reports.deviation_table import generate_deviation_table
from reports.analysis_report import generate_full_report
from database.models import DeviationResult, DeviationType, RiskLevel, ScoreSummary


def _temp_db_setup():
    import config.settings as s
    s.DATABASE_PATH = os.path.join(tempfile.gettempdir(), "bid_test_report.db")
    s.DATA_DIR = tempfile.gettempdir()
    s.REPORT_OUTPUT_DIR = tempfile.gettempdir()
    from database.migrations import init_db
    init_db()

_temp_db_setup()


class TestDeviationTable:
    def test_generate_table(self):
        deviations = [
            DeviationResult(
                id="dr1", parsed_param_id="p1", match_param_id="m1",
                deviation_type=DeviationType.POSITIVE.value,
                similarity_score=0.95, explanation="性能优于要求",
                risk_level=RiskLevel.NONE.value, suggestion="标注竞争优势",
            ),
            DeviationResult(
                id="dr2", parsed_param_id="p2", match_param_id="m2",
                deviation_type=DeviationType.NEGATIVE.value,
                similarity_score=0.90, explanation="参数不满足要求",
                risk_level=RiskLevel.DISQUALIFY.value, suggestion="需整改",
            ),
        ]
        path = generate_deviation_table(
            deviation_results=deviations,
            param_names={"p1": "吞吐量", "p2": "并发连接数"},
            product_params={"m1": ("10Gbps", "Gbps"), "m2": ("300万", "条")},
            task_id="task_test",
        )
        assert os.path.exists(path)
        assert path.endswith(".docx")


class TestAnalysisReport:
    def test_generate_full_report(self):
        scores = ScoreSummary(
            total_score=75,
            max_possible_score=100,
            score_rate=0.75,
        )
        deviations = [
            DeviationResult(
                id="dr1", parsed_param_id="p1", match_param_id="m1",
                deviation_type=DeviationType.NEUTRAL.value,
                similarity_score=0.95, explanation="满足要求",
                risk_level=RiskLevel.NONE.value, suggestion="",
            ),
        ]
        path = generate_full_report(
            task_id="task_test",
            decision={"conclusion": "谨慎投标", "confidence": "中", "reason": "测试", "score_rate": 0.75},
            advantages=[{"param_id": "p1", "explanation": "性能优势"}],
            risks=[],
            suggestions={"params": [], "evidence": [], "strategy": []},
            competitive={"overall_rating": "中等"},
            score_summary=scores,
            deviation_results=deviations,
            param_names={"p1": "最大吞吐量"},
        )
        assert path.endswith(".docx")
