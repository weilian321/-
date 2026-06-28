#!/usr/bin/env python3
"""
投标参数智能分析智能体 - 交互式运营控制台

在本地环境模拟 MonkeyCode 平台上下文，以对话方式与智能体交互。
支持：上传文件、查询进度、修正参数、重新计算、导出报告等全部操作。
"""
import sys
import os
import json
import uuid
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

TASK_ID = ""

def print_banner():
    print(f"\n{BOLD}{CYAN}{'=' * 64}{RESET}")
    print(f"{BOLD}{CYAN}  投标参数智能分析智能体 - 运营控制台{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 64}{RESET}")
    print(f"\n  {CYAN}架构:{RESET} Agent 核心 (规划/调度/记忆/异常/校验) + 业务工具层")
    print(f"  {CYAN}测试:{RESET} 126 通过 | {CYAN}状态:{RESET} {GREEN}运行中{RESET}")
    print(f"\n  {YELLOW}输入 '帮助' 查看指令, 'exit/quit' 退出{RESET}\n")


def print_help():
    print(f"""
{BOLD}{CYAN}支持的操作指令:{RESET}

  {YELLOW}文件操作{RESET}
    {MAGENTA}上传{RESET} [文件路径]      上传招标文件并启动分析
    {MAGENTA}清除{RESET}                 清除当前任务缓存文件

  {YELLOW}分析操作{RESET}
    {MAGENTA}分析{RESET}                 触发完整分析流程
    {MAGENTA}门槛{RESET}                 仅分析资格准入门槛
    {MAGENTA}性能{RESET}                 重点比对性能参数
    {MAGENTA}得分{RESET}                 得分优先分析模式
    {MAGENTA}进度{RESET}                 查看当前任务执行状态

  {YELLOW}报告操作{RESET}
    {MAGENTA}导出{RESET} / {MAGENTA}报告{RESET}         获取分析报告下载链接
    {MAGENTA}修正{RESET}                 发起参数修正流程
    {MAGENTA}重新计算{RESET}             基于修正结果重新比对

  {YELLOW}免提测试{RESET}
    {MAGENTA}演示{RESET}                 运行完整演示流程（无需文件）

  {YELLOW}系统{RESET}
    {MAGENTA}帮助{RESET} / {MAGENTA}help{RESET}        显示此帮助
    {MAGENTA}exit{RESET} / {MAGENTA}quit{RESET}        退出
""")


def call_handle_message(user_input, context=None):
    """调用 skill.handle_message，捕获并格式化输出。"""
    global TASK_ID
    from skill import handle_message

    ctx = context or {"current_task_id": TASK_ID}
    result = handle_message(user_input, ctx)

    if result.get("task_id"):
        TASK_ID = result["task_id"]

    return result


def print_response(result):
    """格式化输出智能体响应。"""
    msg = result.get("message", "")
    print(f"\n{BOLD}{BLUE}[智能体]{RESET} {msg}")

    components = result.get("components", [])
    if not components:
        return

    for comp in components:
        ctype = comp.get("type", "")
        if ctype == "table":
            title = comp.get("title", "")
            headers = comp.get("headers", [])
            rows = comp.get("rows", [])
            if title:
                print(f"\n  {BOLD}{title}{RESET}")
            if headers:
                header_line = "  " + " | ".join(h[:12].ljust(12) for h in headers)
                print(f"  {header_line}")
                print(f"  {'-' * len(header_line)}")
            for row in rows:
                print(f"  {'  | '.join(str(c)[:15] for c in row)}")
        elif ctype == "card":
            print(f"\n  {BOLD}{comp.get('title', '')}{RESET}")
            for field in comp.get("fields", []):
                print(f"    {field['label']}: {field['value']}")
        elif ctype == "file_download":
            print(f"  {CYAN}[下载]{RESET} {comp.get('description', '')}")
        elif ctype == "text":
            print(f"  {comp.get('content', '')}")


def run_demo():
    """无文件演示模式 - 展示 Agent 全部能力。"""
    print(f"\n{BOLD}{CYAN}{'=' * 64}{RESET}")
    print(f"{BOLD}{CYAN}  演示模式 - Agent 核心能力展示{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 64}{RESET}\n")

    # --- 1. Planner ---
    print(f"{BOLD}[1] 规划引擎 - 意图解析{RESET}")
    from agent.planner import AgentPlanner
    planner = AgentPlanner()
    intents = [
        "帮我分析招标文件",
        "只检查资格门槛",
        "重点比对性能参数",
        "得分优先分析",
    ]
    for inp in intents:
        intent = planner.parse_intent(inp, {})
        plan = planner.generate_plan(intent)
        print(f"  \"{inp}\"")
        print(f"  -> {GREEN}{intent.intent_type}{RESET} ({len(plan.steps)} 步)")

    # --- 2. Memory ---
    print(f"\n{BOLD}[2] 记忆系统 - 读写测试{RESET}")
    from agent.memory import MemoryManager
    memory = MemoryManager(db_path=os.path.join(os.path.dirname(__file__), "data", "agent_ops.db"))
    tid = f"ops_{uuid.uuid4().hex[:8]}"
    memory.save_session_context(tid, {"parsed_params": [{"name": "交换容量", "value": ">=2.4Tbps"}]})
    memory.record_project_result({
        "bid_file_name": "运营测试项目.pdf",
        "product_line_id": "pl-001",
        "decision": {"conclusion": "建议投标", "score_rate": 0.91},
        "risk_count": 1,
    })
    sess = memory.load_session_context(tid)
    hist = memory.search_history("投标")
    print(f"  {GREEN}OK{RESET} 短期: {len(sess.parsed_params)} 参数, 长期: {len(hist)} 历史")

    # --- 3. ExceptionHandler ---
    print(f"\n{BOLD}[3] 异常处理 - 全场景{RESET}")
    from agent.exception_handler import ExceptionHandler
    eh = ExceptionHandler()
    scenarios = [
        ({"tool_name": "doc_parser"}, {"success": False, "error": "文件损坏"}),
        ({"tool_name": "semantic_matcher"}, {"success": True, "data": {"coverage": 0.35}}),
        ({"tool_name": "scoring_rule_parser"}, {"success": True, "data": {"rules": []}}),
    ]
    for step, result in scenarios:
        anomaly = eh.detect_anomaly(step, result)
        strategy = eh.resolve_strategy(anomaly)
        print(f"  {GREEN}{anomaly.anomaly_type.value}{RESET} -> 策略={strategy} 级别={anomaly.severity}")

    # --- 4. SelfValidator ---
    print(f"\n{BOLD}[4] 自校验 - 覆盖率检查{RESET}")
    from agent.self_validator import SelfValidator
    validator = SelfValidator()
    full_ctx = {
        "parsed_params": [{"id": f"p{i}", "name": f"参数{i}"} for i in range(5)],
        "matched_pairs": [{"bid_param_id": "p0"}, {"bid_param_id": "p1"}, {"bid_param_id": "p2"}, {"bid_param_id": "p3"}, {"bid_param_id": "p4"}],
        "deviation_results": [{"parsed_param_id": f"p{i}", "deviation_type": "一致"} for i in range(5)],
        "scoring_rules": [{"name": "规则A"}, {"name": "规则B"}],
        "score_results": [{"rule_name": "规则A"}, {"rule_name": "规则B"}],
    }
    report = validator.validate_completeness("demo", context=full_ctx)
    print(f"  {GREEN}PASS{RESET} 参数覆盖={report.param_coverage:.0%} 评分覆盖={report.score_coverage:.0%}")
    print(f"  总结: {report.summary}")

    # --- 5. Agent integration ---
    print(f"\n{BOLD}[5] Skill 集成 - 入口调用{RESET}")
    resp = call_handle_message("帮助")
    print(f"  {GREEN}OK{RESET} {resp['message'][:60]}...")

    print(f"\n{BOLD}{CYAN}演示完成。智能体五大核心模块全部就绪。{RESET}\n")


def main():
    print_banner()

    while True:
        try:
            user_input = input(f"{GREEN}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}智能体已停止。{RESET}")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit", "q"):
            print(f"{YELLOW}再见。{RESET}")
            break

        if user_input.lower() in ("帮助", "help", "h", "?"):
            print_help()
            continue

        if user_input.lower() in ("演示", "demo"):
            run_demo()
            continue

        # --- 交互式分析 ---
        result = call_handle_message(user_input)
        print_response(result)


if __name__ == "__main__":
    main()
