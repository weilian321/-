"""
双层记忆系统

管理短期会话上下文与长期业务知识，支持上下文复用与经验累积。

参考 REQ-12，设计文档 Components 4。
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SessionMemory:
    """短期会话记忆（内存字典，会话期间存活）。"""
    task_id: str = ""
    parsed_params: list[Any] = field(default_factory=list)
    user_corrections: dict[str, dict[str, Any]] = field(default_factory=dict)
    matched_pairs: list[Any] = field(default_factory=list)
    deviation_results: list[Any] = field(default_factory=list)
    score_results: list[Any] = field(default_factory=list)
    decision: Optional[Any] = None
    pending_queries: list[str] = field(default_factory=list)
    completed_steps: list[str] = field(default_factory=list)


@dataclass
class LongTermMemory:
    """长期业务记忆（SQLite 表，持久化保存）。"""
    project_history: list[dict[str, Any]] = field(default_factory=list)
    correction_patterns: dict[str, Any] = field(default_factory=dict)
    param_alias_map: dict[str, list[str]] = field(default_factory=dict)
    favorite_models: list[dict[str, Any]] = field(default_factory=list)
    rule_templates: list[dict[str, Any]] = field(default_factory=list)


class MemoryManager:
    """
    双层记忆系统管理器。

    职责：
    1. 管理短期会话上下文的读写
    2. 管理长期业务记忆的持久化
    3. 用户修正时同步更新双层记忆
    4. 支持历史项目搜索与复用
    """

    def __init__(self, db_path: Optional[str] = None):
        self._session: dict[str, SessionMemory] = {}
        self._db_path = db_path
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        """确保长期记忆表存在。"""
        if not self._db_path:
            return
        try:
            from database.migrations import get_connection
            conn = get_connection()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS project_records (
                    id TEXT PRIMARY KEY,
                    bid_file_name TEXT,
                    product_line_id TEXT,
                    decision_conclusion TEXT,
                    score_rate REAL,
                    risk_count INTEGER,
                    result_snapshot TEXT,
                    analyzed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS correction_patterns (
                    id TEXT PRIMARY KEY,
                    original_name TEXT,
                    corrected_name TEXT,
                    frequency INTEGER DEFAULT 1,
                    last_used TEXT
                );
                CREATE TABLE IF NOT EXISTS param_alias_maps (
                    id TEXT PRIMARY KEY,
                    param_name TEXT,
                    alias TEXT,
                    usage_count INTEGER DEFAULT 1,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS favorite_models (
                    id TEXT PRIMARY KEY,
                    product_line_id TEXT,
                    model_name TEXT,
                    use_count INTEGER DEFAULT 1,
                    last_selected TEXT
                );
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    def save_session_context(
        self, task_id: str, context: dict[str, Any]
    ) -> None:
        """保存当前任务上下文到短期记忆。"""
        memory = self._session.get(task_id, SessionMemory(task_id=task_id))

        if "parsed_params" in context:
            memory.parsed_params = context["parsed_params"]
        if "matched_pairs" in context:
            memory.matched_pairs = context["matched_pairs"]
        if "deviation_results" in context:
            memory.deviation_results = context["deviation_results"]
        if "score_results" in context:
            memory.score_results = context["score_results"]
        if "decision" in context:
            memory.decision = context["decision"]
        if "completed_step" in context:
            step = context["completed_step"]
            if step not in memory.completed_steps:
                memory.completed_steps.append(step)

        self._session[task_id] = memory

    def load_session_context(self, task_id: str) -> Optional[SessionMemory]:
        """恢复会话上下文。"""
        return self._session.get(task_id)

    def update_memory_on_correction(
        self, task_id: str, param_name: str, old_val: Any, new_val: Any
    ) -> None:
        """用户修正参数时同步更新双层记忆。"""
        memory = self._session.get(task_id)
        if memory is None:
            memory = SessionMemory(task_id=task_id)
            self._session[task_id] = memory

        memory.user_corrections[param_name] = {
            "old_value": old_val,
            "new_value": new_val,
        }

        self._record_correction_pattern(param_name, str(old_val), str(new_val))

    def _record_correction_pattern(
        self, original_name: str, old_val: str, new_val: str
    ) -> None:
        """记录到长期记忆的纠正模式表。"""
        if not self._db_path:
            return
        try:
            from database.migrations import get_connection
            import uuid
            conn = get_connection()
            existing = conn.execute(
                "SELECT id, frequency FROM correction_patterns "
                "WHERE original_name = ? AND corrected_name = ?",
                (original_name, new_val),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE correction_patterns SET frequency = frequency + 1, "
                    "last_used = datetime('now') WHERE id = ?",
                    (existing["id"],),
                )
            else:
                cid = f"cp_{uuid.uuid4().hex[:12]}"
                conn.execute(
                    "INSERT INTO correction_patterns (id, original_name, "
                    "corrected_name, frequency, last_used) VALUES (?, ?, ?, 1, datetime('now'))",
                    (cid, original_name, new_val),
                )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def record_project_result(self, task_result: dict[str, Any]) -> None:
        """持久化本次分析摘要到长期记忆。"""
        if not self._db_path:
            return
        try:
            from database.migrations import get_connection
            import uuid
            conn = get_connection()
            pid = f"pr_{uuid.uuid4().hex[:12]}"
            decision = task_result.get("decision", {})
            conn.execute(
                "INSERT INTO project_records (id, bid_file_name, product_line_id, "
                "decision_conclusion, score_rate, risk_count, result_snapshot, analyzed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                (
                    pid,
                    task_result.get("bid_file_name", ""),
                    task_result.get("product_line_id", ""),
                    str(decision.get("conclusion", "")),
                    decision.get("score_rate", 0.0),
                    task_result.get("risk_count", 0),
                    json.dumps(task_result, ensure_ascii=False, default=str),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def search_history(self, keywords: str) -> list[dict[str, Any]]:
        """按关键词检索历史投标项目。"""
        if not self._db_path:
            return []
        try:
            from database.migrations import get_connection
            conn = get_connection()
            like_kw = f"%{keywords}%"
            rows = conn.execute(
                "SELECT * FROM project_records WHERE "
                "bid_file_name LIKE ? OR decision_conclusion LIKE ? "
                "ORDER BY analyzed_at DESC LIMIT 20",
                (like_kw, like_kw),
            ).fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def get_alias_suggestions(self, param_name: str) -> list[str]:
        """查询历史别名建议。"""
        if not self._db_path:
            return []
        try:
            from database.migrations import get_connection
            conn = get_connection()
            rows = conn.execute(
                "SELECT alias FROM param_alias_maps WHERE param_name = ? "
                "ORDER BY usage_count DESC LIMIT 5",
                (param_name,),
            ).fetchall()
            conn.close()
            return [r["alias"] for r in rows]
        except Exception:
            return []

    def reuse_matching_rules(
        self, product_line_id: str
    ) -> list[dict[str, Any]]:
        """加载该产品线历史匹配规则。"""
        if not self._db_path:
            return []
        try:
            from database.migrations import get_connection
            conn = get_connection()
            rows = conn.execute(
                "SELECT param_name, alias FROM param_alias_maps "
                "WHERE param_name IN (SELECT name FROM parameter_records "
                "WHERE version_id IN (SELECT id FROM product_versions "
                "WHERE product_line_id = ?)) ORDER BY usage_count DESC",
                (product_line_id,),
            ).fetchall()
            conn.close()
            return [{"param_name": r["param_name"], "alias": r["alias"]} for r in rows]
        except Exception:
            return []

    def export_memory(self) -> dict[str, Any]:
        """导出记忆数据（短期 + 长期）。"""
        return {
            "session_count": len(self._session),
            "sessions": {
                tid: {
                    "parsed_params": len(m.parsed_params),
                    "matched_pairs": len(m.matched_pairs),
                    "completed_steps": m.completed_steps,
                }
                for tid, m in self._session.items()
            },
        }

    def clear_memory(self, scope: str = "session") -> int:
        """清除指定范围的记忆。

        参数:
            scope: "session" | "task:{task_id}" | "long_term"

        返回: 清除的记忆条目数
        """
        if scope.startswith("task:"):
            task_id = scope.split(":", 1)[1]
            if task_id in self._session:
                del self._session[task_id]
                return 1
            return 0
        if scope == "session":
            count = len(self._session)
            self._session.clear()
            return count
        return 0
