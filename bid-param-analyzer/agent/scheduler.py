"""
多工具统一调度器

按任务规划引擎生成的执行计划，统一纳管并调度所有业务工具的调用。

参考 REQ-11，设计文档 Components 3。
"""
import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass
class ToolSignature:
    """工具注册签名，描述工具的能力与参数规范。"""
    name: str
    description: str
    handler: Callable
    param_schema: dict[str, Any] = field(default_factory=dict)
    timeout: float = 120.0


@dataclass
class ExecutionLog:
    """单次工具调用日志。"""
    tool_name: str
    step_name: str
    input: dict[str, Any]
    output: Any
    duration_ms: float
    status: str
    error: Optional[str] = None
    retry_count: int = 0


class ToolScheduler:
    """
    多工具统一调度器。

    职责：
    1. 注册发现所有可用工具
    2. 按计划依序/并行执行步骤
    3. 失败自动重试与超时控制
    4. 维护调用日志
    """

    DEFAULT_TIMEOUT = 120.0  # 秒
    MAX_RETRIES = 1

    def __init__(self):
        self._tools: dict[str, ToolSignature] = {}
        self._logs: list[ExecutionLog] = []
        self._exception_handler: Optional[Any] = None

    def set_exception_handler(self, handler: Any) -> None:
        self._exception_handler = handler

    def register_tool(
        self, name: str, handler: Callable, signature: dict[str, Any]
    ) -> None:
        """
        注册一个业务工具到调度器。

        参数:
            name: 工具唯一名称，如 doc_parser
            handler: 工具处理函数
            signature: 工具参数描述，如 {"file_path": "str", "task_id": "str"}
        """
        self._tools[name] = ToolSignature(
            name=name,
            description=signature.get("description", ""),
            handler=handler,
            param_schema=signature.get("params", {}),
            timeout=signature.get("timeout", self.DEFAULT_TIMEOUT),
        )

    def execute_step(
        self, step_name: str, tool_name: str, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        执行单个计划步骤。

        参数:
            step_name: 步骤名称
            tool_name: 要调用的工具名称
            context: 执行上下文（包含前序步骤的输出）

        返回:
            {"success": bool, "data": Any, "error": str | None}
        """
        if tool_name not in self._tools:
            return {
                "success": False,
                "data": None,
                "error": f"工具 [{tool_name}] 未注册",
            }

        tool = self._tools[tool_name]
        start_time = time.time()
        error = None

        try:
            result = self._call_with_timeout(tool.handler, context, tool.timeout)
            duration_ms = (time.time() - start_time) * 1000

            log = ExecutionLog(
                tool_name=tool_name,
                step_name=step_name,
                input=context,
                output=result,
                duration_ms=duration_ms,
                status="success",
            )
            self._logs.append(log)

            return {"success": True, "data": result, "error": None}

        except TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error = f"工具 [{tool_name}] 执行超时（>{tool.timeout}s）"
            log = ExecutionLog(
                tool_name=tool_name,
                step_name=step_name,
                input=context,
                output=None,
                duration_ms=duration_ms,
                status="timeout",
                error=error,
            )
            self._logs.append(log)

            if self._exception_handler:
                self._exception_handler.detect_anomaly(
                    step={"name": step_name, "tool_name": tool_name},
                    result={"success": False, "error": error},
                )

            return {"success": False, "data": None, "error": error}

        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            error = str(exc)
            log = ExecutionLog(
                tool_name=tool_name,
                step_name=step_name,
                input=context,
                output=None,
                duration_ms=duration_ms,
                status="failed",
                error=error,
            )
            self._logs.append(log)
            return {"success": False, "data": None, "error": error}

    def retry_step(
        self, step_name: str, tool_name: str, context: dict[str, Any],
        strategy: str = "default"
    ) -> dict[str, Any]:
        """
        以指定策略重试失败步骤。

        参数:
            step_name: 步骤名称
            tool_name: 工具名称
            context: 执行上下文
            strategy: retry/degrade/skip 策略
        """
        for attempt in range(self.MAX_RETRIES):
            result = self.execute_step(step_name, tool_name, context)
            if result["success"]:
                result["retry_attempt"] = attempt + 1
                return result

        if strategy == "skip":
            return {
                "success": True,
                "data": {"skipped": True, "reason": "重试均失败，已跳过"},
                "error": None,
            }

        if self._exception_handler:
            anomaly = self._exception_handler.detect_anomaly(
                step={"name": step_name, "tool_name": tool_name},
                result={"success": False, "error": "重试耗尽"},
            )
            return {
                "success": False,
                "data": None,
                "error": "重试均失败",
                "anomaly": anomaly,
            }

        return {"success": False, "data": None, "error": "重试均失败"}

    def execute_plan(
        self, plan: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        按计划依序执行全部步骤。

        前驱步骤完成后将输出合并到 context 中传递给后继步骤。
        """
        results: dict[str, Any] = {}
        step_outputs: dict[str, Any] = {}

        for step in plan.steps:
            if step.status == "completed":
                continue

            step_context = {**context, **step_outputs}

            for dep in step.depends_on:
                if dep in step_outputs:
                    step_context[dep] = step_outputs[dep]

            result = self.execute_step(
                step.name, step.tool_name, step_context
            )

            if not result["success"]:
                retry_result = self.retry_step(
                    step.name, step.tool_name, step_context
                )
                if not retry_result.get("success"):
                    results[step.name] = retry_result
                    step.status = "failed"
                    if retry_result.get("anomaly"):
                        results["_anomaly"] = retry_result["anomaly"]
                    return results
                result = retry_result

            step.status = "completed"
            step_outputs[step.name] = result.get("data")
            results[step.name] = result

        return results

    def get_execution_log(self) -> list[dict[str, Any]]:
        """返回当前会话全部工具调用日志。"""
        return [
            {
                "tool": log.tool_name,
                "step": log.step_name,
                "duration_ms": log.duration_ms,
                "status": log.status,
                "error": log.error,
            }
            for log in self._logs
        ]

    def list_tools(self) -> list[str]:
        """返回已注册的工具名称列表。"""
        return list(self._tools.keys())

    def _call_with_timeout(
        self, handler: Callable, context: dict[str, Any], timeout: float
    ) -> Any:
        """在超时限制内同步调用工具处理函数。"""
        result_container: list[Any] = []
        error_container: list[Optional[Exception]] = [None]

        def _target() -> None:
            try:
                result_container.append(handler(context))
            except Exception as exc:
                error_container[0] = exc

        thread = threading.Thread(target=_target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)

        if thread.is_alive():
            raise TimeoutError(f"工具调用超时（>{timeout}s）")

        if error_container[0] is not None:
            raise error_container[0]

        return result_container[0] if result_container else None
