"""
任务编排控制器

协调各模块按流程顺序执行，管理任务生命周期。

状态机：
PENDING → PARSING → PARSE_DONE → COMPARING → COMPARE_DONE
  → SCORING → SCORE_DONE → ANALYZING → COMPLETED
"""
import uuid
from typing import Optional

from config.settings import REPORT_OUTPUT_DIR
from database.models import TaskStatus, ParameterItem, ParameterRecord
from database.repository import get_active_params, get_aliases
from parsers.doc_parser import parse_document, extract_tables, ParsedDocument
from parsers.table_extractor import (
    locate_key_sections,
    extract_parameters,
    extract_parameters_from_table,
    extract_scoring_rules,
    detect_star_items,
)
from parsers.scoring_rule_parser import parse_scoring_rules
from engine.semantic_matcher import match_parameters
from engine.deviation_judge import batch_judge
from engine.score_calculator import calculate_scoring, mark_improvement_items
from engine.decision_engine import (
    derive_decision,
    generate_advantage_list,
    generate_risk_list,
    generate_suggestions,
    competitive_assessment,
)
from reports.deviation_table import generate_deviation_table
from reports.analysis_report import generate_full_report
from storage.file_manager import save_uploaded_file
from storage.history_manager import save_task_snapshot, load_task_context


class Orchestrator:
    def __init__(self):
        self._tasks: dict[str, dict] = {}

    def create_task(self, bid_file_path: str, product_line_id: str) -> str:
        task_id = f"task_{uuid.uuid4().hex[:12]}"

        saved_path = save_uploaded_file(bid_file_path, task_id)

        self._tasks[task_id] = {
            "status": TaskStatus.PENDING.value,
            "bid_file_path": saved_path,
            "product_line_id": product_line_id,
            "version_id": "",
            "result": {},
        }
        return task_id

    def execute_step(self, task_id: str, step_name: str) -> dict:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        if step_name == "parse":
            return self._do_parse(task_id, task)
        elif step_name == "compare":
            return self._do_compare(task_id, task)
        elif step_name == "score":
            return self._do_score(task_id, task)
        elif step_name == "analyze":
            return self._do_analyze(task_id, task)
        else:
            raise ValueError(f"未知步骤: {step_name}")

    def execute_all(self, task_id: str) -> dict:
        result = self.execute_step(task_id, "parse")
        if result.get("status") == TaskStatus.PARSE_DONE.value:
            result = self.execute_step(task_id, "compare")
        if result.get("status") == TaskStatus.COMPARE_DONE.value:
            result = self.execute_step(task_id, "score")
        if result.get("status") == TaskStatus.SCORE_DONE.value:
            result = self.execute_step(task_id, "analyze")
        return result

    def _do_parse(self, task_id: str, task: dict) -> dict:
        task["status"] = TaskStatus.PARSING.value
        bid_path = task["bid_file_path"]

        parsed_doc = parse_document(bid_path)
        tables = extract_tables(parsed_doc)

        sections = locate_key_sections(parsed_doc.full_text)
        all_params: list[ParameterItem] = []

        tech_sections = [s for s in sections if s.section_type == "technical_params"]
        if tech_sections:
            for sec in tech_sections:
                section_text = parsed_doc.full_text[sec.start:sec.end + 3000]
                params = extract_parameters(section_text)
                all_params.extend(params)

        for table in tables:
            table_params = extract_parameters_from_table(table.headers, table.rows)
            all_params.extend(table_params)

        detect_star_items(all_params)

        scoring_rules = []
        scoring_sections = [s for s in sections if s.section_type == "scoring_rules"]
        if scoring_sections:
            for sec in scoring_sections:
                section_text = parsed_doc.full_text[sec.start:sec.end + 3000]
                raw_rules = extract_scoring_rules(section_text)
                scoring_rules.extend(parse_scoring_rules(raw_rules))

        seen = {}
        unique_params = []
        for p in all_params:
            key = (p.name, p.requirement_value)
            if key not in seen:
                seen[key] = True
                unique_params.append(p)

        task["result"]["parsed_params"] = unique_params
        task["result"]["scoring_rules"] = scoring_rules
        task["result"]["sections"] = sections
        task["result"]["tables"] = tables
        task["status"] = TaskStatus.PARSE_DONE.value

        return {
            "status": task["status"],
            "param_count": len(unique_params),
            "scoring_rule_count": len(scoring_rules),
            "section_count": len(sections),
            "table_count": len(tables),
            "parsed_params": unique_params,
            "scoring_rules": scoring_rules,
        }

    def _do_compare(self, task_id: str, task: dict) -> dict:
        task["status"] = TaskStatus.COMPARING.value
        product_line_id = task["product_line_id"]

        product_params = get_active_params(product_line_id)
        aliases_map = {}
        for pp in product_params:
            aliases_map[pp.id] = get_aliases(pp.id)

        parsed_params = task["result"].get("parsed_params", [])

        matched, unmatched = match_parameters(parsed_params, product_params, aliases_map)
        deviation_results = batch_judge(matched, unmatched)

        param_names = {p.id: p.name for p in parsed_params}
        prod_params = {p.id: (p.name, p.nominal_value) for p in product_params}

        deviation_table_path = generate_deviation_table(
            deviation_results, param_names, prod_params, task_id=task_id
        )

        task["result"]["deviation_results"] = deviation_results
        task["result"]["matched_count"] = len(matched)
        task["result"]["unmatched_count"] = len(unmatched)
        task["result"]["param_names"] = param_names
        task["result"]["product_params"] = product_params
        task["status"] = TaskStatus.COMPARE_DONE.value

        return {
            "status": task["status"],
            "matched_count": len(matched),
            "unmatched_count": len(unmatched),
            "deviation_results": deviation_results,
            "deviation_table_path": deviation_table_path,
        }

    def _do_score(self, task_id: str, task: dict) -> dict:
        task["status"] = TaskStatus.SCORING.value

        scoring_rules = task["result"].get("scoring_rules", [])
        deviation_results = task["result"].get("deviation_results", [])
        param_names = task["result"].get("param_names", {})

        score_summary = calculate_scoring(scoring_rules, deviation_results, param_names)
        improvement_items = mark_improvement_items(
            score_summary.item_scores, deviation_results
        )

        task["result"]["score_summary"] = score_summary
        task["result"]["improvement_items"] = improvement_items
        task["status"] = TaskStatus.SCORE_DONE.value

        return {
            "status": task["status"],
            "total_score": score_summary.total_score,
            "max_score": score_summary.max_possible_score,
            "score_rate": score_summary.score_rate,
            "improvement_items": improvement_items,
        }

    def _do_analyze(self, task_id: str, task: dict) -> dict:
        task["status"] = TaskStatus.ANALYZING.value

        deviation_results = task["result"].get("deviation_results", [])
        score_summary = task["result"].get("score_summary")
        improvement_items = task["result"].get("improvement_items", [])
        param_names = task["result"].get("param_names", {})

        advantages = generate_advantage_list(deviation_results)
        risks = generate_risk_list(deviation_results, score_summary)
        suggestions = generate_suggestions(risks, improvement_items)
        competitive = competitive_assessment(deviation_results, score_summary)
        decision = derive_decision(score_summary, risks)

        report_path = generate_full_report(
            task_id=task_id,
            decision=decision,
            advantages=advantages,
            risks=risks,
            suggestions=suggestions,
            competitive=competitive,
            score_summary=score_summary,
            deviation_results=deviation_results,
            param_names=param_names,
        )

        task["result"]["decision"] = decision
        task["result"]["advantages"] = advantages
        task["result"]["risks"] = risks
        task["result"]["suggestions"] = suggestions
        task["result"]["competitive"] = competitive
        task["result"]["report_path"] = report_path
        task["status"] = TaskStatus.COMPLETED.value

        return {
            "status": task["status"],
            "decision": decision,
            "advantages_count": len(advantages),
            "risk_count": len(risks),
            "report_path": report_path,
        }

    def get_task_state(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if not task:
            return {"status": "NOT_FOUND"}
        return {
            "task_id": task_id,
            "status": task["status"],
            "product_line_id": task.get("product_line_id", ""),
        }

    def modify_parameter(self, task_id: str, param_id: str, edits: dict) -> dict:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        params = task["result"].get("parsed_params", [])
        for p in params:
            if p.id == param_id:
                for key, value in edits.items():
                    if hasattr(p, key):
                        setattr(p, key, value)
                task["status"] = TaskStatus.PARSE_DONE.value
                return {"status": "updated", "param_id": param_id}

        raise ValueError(f"参数不存在: {param_id}")

    def recalculate(self, task_id: str) -> dict:
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        self.execute_step(task_id, "compare")
        self.execute_step(task_id, "score")
        return self.execute_step(task_id, "analyze")

    def resume_task(self, task_id: str) -> bool:
        context = load_task_context(task_id)
        if context is None:
            return False

        self._tasks[task_id] = {
            "status": context.get("status", TaskStatus.PENDING.value),
            "bid_file_path": context.get("bid_file_path", ""),
            "product_line_id": context.get("product_line_id", ""),
            "version_id": context.get("version_id", ""),
            "result": context.get("result", {}),
        }
        return True
