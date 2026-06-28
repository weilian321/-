"""
异常自主处理器

在工具调用失败或结果不满足预期时，自主判断处理策略并主动与用户交互。

参考 REQ-13，设计文档 Components 5。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AnomalyType(str, Enum):
    """异常类型枚举。"""
    PARSE_FAILURE = "parse_failure"
    LOW_MATCH_RATE = "low_match_rate"
    MISSING_SCORING_RULES = "missing_scoring_rules"
    AMBIGUOUS_MODEL = "ambiguous_model"
    TOOL_TIMEOUT = "tool_timeout"
    HIGH_RISK_ALERT = "high_risk_alert"
    UNKNOWN = "unknown"


@dataclass
class AnomalyResult:
    """异常检测结果。"""
    anomaly_type: AnomalyType
    severity: str = "warning"
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    suggested_strategy: str = ""
    user_query: Optional[str] = None
    user_options: list[str] = field(default_factory=list)


class ExceptionHandler:
    """
    异常自主处理器。

    职责：
    1. 检测工具返回结果中的异常
    2. 按异常类型返回处理策略
    3. 生成面向用户的定向询问
    4. 处理用户反馈并恢复执行
    """

    STRATEGY_MAP = {
        AnomalyType.PARSE_FAILURE: "retry_or_prompt",
        AnomalyType.LOW_MATCH_RATE: "ask_user",
        AnomalyType.MISSING_SCORING_RULES: "skip_and_notify",
        AnomalyType.AMBIGUOUS_MODEL: "ask_user_select",
        AnomalyType.TOOL_TIMEOUT: "retry_or_skip",
        AnomalyType.HIGH_RISK_ALERT: "immediate_alert",
        AnomalyType.UNKNOWN: "notify_user",
    }

    SEVERITY_MAP = {
        AnomalyType.PARSE_FAILURE: "error",
        AnomalyType.LOW_MATCH_RATE: "warning",
        AnomalyType.MISSING_SCORING_RULES: "info",
        AnomalyType.AMBIGUOUS_MODEL: "warning",
        AnomalyType.TOOL_TIMEOUT: "error",
        AnomalyType.HIGH_RISK_ALERT: "critical",
        AnomalyType.UNKNOWN: "warning",
    }

    def detect_anomaly(
        self, step: dict[str, Any], result: dict[str, Any]
    ) -> AnomalyResult:
        """
        检测是否触发异常条件并返回异常结果。

        参数:
            step: 当前步骤信息 {"name": str, "tool_name": str}
            result: 步骤执行结果 {"success": bool, "data": Any, "error": str}
        """
        tool_name = step.get("tool_name", "")

        if not result.get("success", False):
            return self._build_anomaly(
                AnomalyType.PARSE_FAILURE,
                message=f"工具 [{tool_name}] 执行失败",
                detail={"error": result.get("error", ""), "step": step},
                user_query=f"工具 [{tool_name}] 执行失败：{result.get('error', '')}。是否重试？",
                user_options=["重试", "跳过此步骤", "终止分析"],
            )

        data = result.get("data", {})

        if tool_name == "semantic_matcher":
            if isinstance(data, dict):
                coverage = data.get("coverage", 1.0)
                if coverage < 0.6:
                    return self._build_anomaly(
                        AnomalyType.LOW_MATCH_RATE,
                        message=f"参数匹配覆盖率仅 {coverage:.0%}，低于 60%",
                        detail={"coverage": coverage},
                        user_query=f"参数匹配覆盖率仅 {coverage:.0%}，部分参数未能自动匹配。是否需要手动映射？",
                        user_options=["查看未匹配清单", "跳过，使用当前结果", "手动映射"],
                    )

        if tool_name in ("scoring_rule_parser",):
            if isinstance(data, dict) and not data.get("rules"):
                return self._build_anomaly(
                    AnomalyType.MISSING_SCORING_RULES,
                    message="未检测到评分细则",
                    detail={},
                    user_query="未从招标文件中检测到评分细则，将跳过得分计算环节。是否继续？",
                    user_options=["继续，跳过得分计算", "手动输入评分规则"],
                )

        if tool_name == "semantic_matcher" and isinstance(data, dict):
            models = data.get("candidate_models", [])
            if len(models) > 1:
                return self._build_anomaly(
                    AnomalyType.AMBIGUOUS_MODEL,
                    message=f"检测到 {len(models)} 个匹配产品型号",
                    detail={"candidates": models},
                    user_query=f"检测到 {len(models)} 个匹配的产品型号，请选择：",
                    user_options=[str(m.get("name", "")) for m in models[:5]],
                )

        return AnomalyResult(
            anomaly_type=AnomalyType.UNKNOWN,
            severity="info",
            message="正常",
        )

    def resolve_strategy(self, anomaly: AnomalyResult) -> str:
        """返回对应异常类型的处理策略。"""
        return self.STRATEGY_MAP.get(
            anomaly.anomaly_type, "notify_user"
        )

    def formulate_query(
        self, anomaly: AnomalyResult
    ) -> dict[str, Any]:
        """
        生成面向用户的定向询问消息，返回可渲染的对话组件。

        返回:
            {"message": str, "options": list[str], "severity": str}
        """
        return {
            "message": anomaly.user_query or anomaly.message,
            "options": anomaly.user_options,
            "severity": anomaly.severity,
            "anomaly_type": anomaly.anomaly_type.value,
        }

    def apply_resolution(
        self, anomaly: AnomalyResult, user_feedback: str
    ) -> dict[str, Any]:
        """
        根据用户反馈生成恢复执行指令。

        参数:
            anomaly: 原始异常结果
            user_feedback: 用户回复的文本

        返回:
            {"action": str, "params": dict}
        """
        feedback_lower = user_feedback.lower().strip()

        if feedback_lower in ("重试", "retry", "是", "yes"):
            return {"action": "retry", "params": {}}

        if "跳过" in feedback_lower or "skip" in feedback_lower:
            return {"action": "skip", "params": {}}

        if "终止" in feedback_lower or "取消" in feedback_lower or "cancel" in feedback_lower:
            return {"action": "abort", "params": {}}

        if anomaly.anomaly_type == AnomalyType.LOW_MATCH_RATE:
            return {"action": "continue_with_manual", "params": {"feedback": user_feedback}}

        if anomaly.anomaly_type == AnomalyType.AMBIGUOUS_MODEL:
            return {"action": "select_model", "params": {"selection": user_feedback}}

        return {"action": "continue", "params": {"feedback": user_feedback}}

    def check_high_risk(self, deviation_results: list[Any]) -> Optional[AnomalyResult]:
        """
        检查偏离结果中是否存在实质性条款负偏离等高危风险。

        返回高危风险预警 AnomalyResult，无风险返回 None。
        """
        for result in deviation_results:
            is_material = getattr(result, "is_material", False)
            deviation = getattr(result, "deviation_type", "")
            if is_material and deviation in ("负偏离", "negative", "无法确认", "unconfirmed"):
                return self._build_anomaly(
                    AnomalyType.HIGH_RISK_ALERT,
                    message="发现实质性条款负偏离，存在废标风险",
                    detail={
                        "param_name": getattr(result, "param_name", ""),
                        "deviation_type": deviation,
                    },
                )
        return None

    def _build_anomaly(
        self,
        anomaly_type: AnomalyType,
        message: str = "",
        detail: Optional[dict] = None,
        user_query: Optional[str] = None,
        user_options: Optional[list[str]] = None,
    ) -> AnomalyResult:
        strategy = self.STRATEGY_MAP.get(anomaly_type, "notify_user")
        severity = self.SEVERITY_MAP.get(anomaly_type, "warning")
        return AnomalyResult(
            anomaly_type=anomaly_type,
            severity=severity,
            message=message,
            detail=detail or {},
            suggested_strategy=strategy,
            user_query=user_query or message,
            user_options=user_options or [],
        )
