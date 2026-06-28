"""
MonkeyCode Agent 交互入口

智能体核心中枢集成：自主任务规划、多工具调度、双层记忆、
异常主动处理和结果自校验。
"""
import json
import os
from typing import Any

from orchestrator import Orchestrator
from storage.file_manager import cleanup_expired_files, clear_task_files
from agent.planner import AgentPlanner
from agent.scheduler import ToolScheduler
from agent.memory import MemoryManager
from agent.exception_handler import ExceptionHandler
from agent.self_validator import SelfValidator


_orchestrator = Orchestrator()
_planner = AgentPlanner()
_scheduler = ToolScheduler()
_memory = MemoryManager()
_exception_handler = ExceptionHandler()
_validator = SelfValidator()

_pending_anomaly: dict[str, Any] = {}


def handle_message(user_input: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    处理用户自然语言指令。

    支持指令：
    - "上传"/"分析" → 触发招标文件上传引导
    - "进度"/"状态" → 查询任务进度
    - "修正"/"修改参数" → 修正参数条目
    - "重新计算"/"重算" → 重新触发比对
    - "导出"/"报告"/"下载" → 获取报告下载链接
    - "清除"/"删除" → 清除任务文件
    - 对异常询问的回复 → 自动识别并传递给异常处理器
    """
    user_lower = user_input.lower().strip()

    task_id = context.get("current_task_id", "")

    if task_id and task_id in _pending_anomaly:
        return _handle_user_feedback(user_input, context)

    if any(k in user_lower for k in ["上传", "分析", "开始分析"]):
        intent = _planner.parse_intent(user_input, context)
        plan = _planner.generate_plan(intent, _memory.load_session_context(task_id) if task_id else None)
        context["_agent_intent"] = intent.intent_type
        context["_agent_plan"] = [s.name for s in plan.steps]
        return _prompt_upload(context)

    if any(k in user_lower for k in ["进度", "状态"]):
        return _get_progress(context)

    if any(k in user_lower for k in ["修正", "修改参数", "编辑参数"]):
        return _prompt_modify(context)

    if any(k in user_lower for k in ["重新计算", "重算", "重新比对"]):
        return _recalculate(context)

    if any(k in user_lower for k in ["导出", "报告", "下载"]):
        return _download_report(context)

    if any(k in user_lower for k in ["清除", "删除"]):
        return _clear_files(context)

    if any(k in user_lower for k in ["帮助", "help", "说明"]):
        return _show_help()

    return {
        "message": (
            "您好，我是投标参数智能分析智能体。请提供以下信息开始分析：\n"
            "1. 上传招标文件（支持 PDF/Word 格式）\n"
            "2. 选择产品线进行参数比对\n\n"
            "您也可以输入"帮助"查看完整指令列表。"
        ),
        "components": [],
    }


def _handle_user_feedback(user_input: str, context: dict) -> dict:
    """处理用户对异常询问的回复。"""
    task_id = context.get("current_task_id", "")
    anomaly_info = _pending_anomaly.pop(task_id, None)
    if not anomaly_info:
        return _prompt_upload(context)

    anomaly = anomaly_info.get("anomaly")
    if anomaly is None:
        return _prompt_upload(context)

    action = _exception_handler.apply_resolution(anomaly, user_input)

    action_map = {
        "retry": "正在重试上次失败的步骤...",
        "skip": "已跳过该步骤，继续执行后续分析。",
        "abort": "分析已终止。如需重新开始，请上传新的招标文件。",
        "select_model": "已选择产品型号，继续执行分析。",
        "continue_with_manual": "已记录您的反馈，将在报告中标记为人工确认项。",
        "continue": "已收到反馈，继续执行分析。",
    }
    msg = action_map.get(action["action"], "已收到反馈，继续执行分析。")

    return {"message": msg, "components": [], "task_id": task_id}


def handle_file_upload(file_path: str, file_type: str, context: dict) -> dict:
    """
    处理招标文件上传，校验类型与大小，启动智能体分析任务。
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in (".pdf", ".doc", ".docx"):
        return {"message": f"不支持的文件类型: {ext}，仅支持 PDF/Word 格式", "components": []}

    task_id = _orchestrator.create_task(file_path, "")
    context["current_task_id"] = task_id

    _memory.save_session_context(task_id, {"bid_file_path": file_path})

    try:
        result = _orchestrator.execute_step(task_id, "parse")
        context["current_task_id"] = task_id

        param_count = result.get("param_count", 0)
        rule_count = result.get("scoring_rule_count", 0)
        params = result.get("parsed_params", [])

        _memory.save_session_context(task_id, {
            "parsed_params": params,
            "completed_step": "parse",
        })

        param_table = {
            "type": "table",
            "title": f"识别参数列表（共 {param_count} 项）",
            "headers": ["参数名称", "要求值", "单位", "类型", "实质性条款"],
            "rows": [
                [
                    p.name if hasattr(p, "name") else p.get("name", ""),
                    p.requirement_value if hasattr(p, "requirement_value") else p.get("requirement_value", ""),
                    p.unit if hasattr(p, "unit") else p.get("unit", ""),
                    p.param_type if hasattr(p, "param_type") else p.get("param_type", ""),
                    "是" if (p.is_material if hasattr(p, "is_material") else p.get("is_material", False)) else "否",
                ]
                for p in params[:20]
            ],
        }

        components = [param_table] if params else []

        if param_count > 20:
            components.append({"type": "text", "content": f"... 共 {param_count} 项参数，仅展示前 20 项"})

        intent_type = context.get("_agent_intent", "full_pipeline")

        return {
            "message": (
                f"招标文件解析完成（智能体模式: {intent_type}）：\n"
                f"- 提取技术参数 {param_count} 项\n"
                f"- 识别评分规则 {rule_count} 项\n\n"
                f"请确认参数是否准确，如需修正请告知。确认后请选择产品线以继续比对。"
            ),
            "components": components,
            "task_id": task_id,
        }
    except Exception as e:
        anomaly = _exception_handler.detect_anomaly(
            {"name": "parse", "tool_name": "doc_parser"},
            {"success": False, "error": str(e)},
        )
        if anomaly.severity == "error":
            _pending_anomaly[task_id] = {"anomaly": anomaly}
            query = _exception_handler.formulate_query(anomaly)
            return {
                "message": query["message"],
                "components": [{"type": "text", "content": " | ".join(query["options"])}],
                "task_id": task_id,
            }
        return {"message": f"解析失败: {e}", "components": []}


def _get_progress(context: dict) -> dict:
    task_id = context.get("current_task_id", "")
    if not task_id:
        return {"message": "当前没有进行中的分析任务，请先上传招标文件。", "components": []}

    state = _orchestrator.get_task_state(task_id)
    status_descriptions = {
        "PENDING": "等待开始",
        "PARSING": "正在解析招标文件...",
        "PARSE_DONE": "招标文件解析完成，等待确认",
        "COMPARING": "正在执行参数比对...",
        "COMPARE_DONE": "参数比对完成",
        "SCORING": "正在计算技术得分...",
        "SCORE_DONE": "技术得分计算完成",
        "ANALYZING": "正在生成投标分析报告...",
        "COMPLETED": "分析完成",
        "FAILED": "任务失败",
    }

    desc = status_descriptions.get(state["status"], state["status"])
    return {
        "message": f"任务 {task_id} 当前状态：{desc}",
        "components": [],
        "task_id": task_id,
    }


def _prompt_modify(context: dict) -> dict:
    task_id = context.get("current_task_id", "")
    if not task_id:
        return {"message": "当前没有进行中的任务。", "components": []}

    return {
        "message": "请告知需要修正的参数名称及新值。例如："修正 防火墙吞吐量 的 要求值 为 >=50 Gbps"",
        "components": [],
    }


def _recalculate(context: dict) -> dict:
    task_id = context.get("current_task_id", "")
    if not task_id:
        return {"message": "当前没有进行中的任务。", "components": []}

    try:
        result = _orchestrator.recalculate(task_id)

        _memory.update_memory_on_correction(
            task_id, "_recalculate", "_prev", "_new"
        )

        validation = _validator.generate_validation_report(task_id)
        if not validation["complete"]:
            context["_validation"] = validation

        return _format_analysis_result(result)
    except Exception as e:
        return {"message": f"重新计算失败: {e}", "components": []}


def _download_report(context: dict) -> dict:
    task_id = context.get("current_task_id", "")
    if not task_id:
        return {"message": "当前没有分析报告。请先执行分析任务。", "components": []}

    state = _orchestrator.get_task_state(task_id)
    if state["status"] not in ("COMPLETED",):
        return {"message": f"分析尚未完成，当前状态: {state['status']}", "components": []}

    return {
        "message": "分析报告已生成，请通过以下链接下载。",
        "components": [
            {
                "type": "file_download",
                "title": "下载投标分析报告",
                "file_type": "docx",
                "description": "包含决策结论、得分概览、风险清单和落地建议的完整报告",
            }
        ],
    }


def _clear_files(context: dict) -> dict:
    task_id = context.get("current_task_id", "")
    if task_id:
        clear_task_files(task_id)
    cleaned = cleanup_expired_files()
    return {
        "message": f"临时文件已清除（清理过期任务 {cleaned} 个）。",
        "components": [],
    }


def _format_analysis_result(result: dict) -> dict:
    decision = result.get("decision", {})
    conclusion = decision.get("conclusion", "未知")
    score_rate = decision.get("score_rate", 0)
    reason = decision.get("reason", "")

    card = {
        "type": "card",
        "title": f"投标决策：{conclusion}",
        "fields": [
            {"label": "技术得分率", "value": f"{score_rate:.1%}"},
            {"label": "竞争优势项", "value": str(result.get("advantages_count", 0))},
            {"label": "风险项", "value": str(result.get("risk_count", 0))},
        ],
    }

    return {
        "message": f"分析完成。决策结论：{conclusion}（{reason}）",
        "components": [card],
    }


def _show_help() -> dict:
    return {
        "message": (
            "**投标参数智能分析智能体** 支持以下操作：\n\n"
            "- 上传招标文件（输入"分析"或直接发送文件）\n"
            "- 自定义分析范围（如"只分析资格门槛项"）\n"
            "- 查询进度（输入"进度"）\n"
            "- 修正参数（输入"修正"）\n"
            "- 重新计算（输入"重新计算"）\n"
            "- 下载报告（输入"导出"或"报告"）\n"
            "- 清除文件（输入"清除"）\n"
            "- 查看帮助（输入"帮助"）"
        ),
        "components": [],
    }
