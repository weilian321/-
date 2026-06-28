"""
历史项目管理

保存、检索、恢复投标分析任务的完整上下文快照。
"""
import json
import uuid
from datetime import datetime

from database.migrations import get_connection
from database.models import AnalysisTask


def save_task_snapshot(
    task_id: str,
    status: str,
    bid_file_path: str,
    product_line_id: str,
    version_id: str,
    context: dict,
) -> bool:
    conn = get_connection()
    try:
        existing = conn.execute(
            "SELECT id FROM analysis_tasks WHERE id = ?", (task_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE analysis_tasks SET status = ?, context_snapshot = ?, updated_at = datetime('now') WHERE id = ?",
                (status, json.dumps(context, ensure_ascii=False), task_id),
            )
        else:
            conn.execute(
                "INSERT INTO analysis_tasks (id, status, bid_file_path, product_line_id, version_id, context_snapshot) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (task_id, status, bid_file_path, product_line_id, version_id,
                 json.dumps(context, ensure_ascii=False)),
            )
        conn.commit()
        return True
    finally:
        conn.close()


def list_tasks(
    product_line_id: str = "",
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    conn = get_connection()
    try:
        query = "SELECT id, status, bid_file_path, product_line_id, created_at, updated_at FROM analysis_tasks"
        params = []

        if product_line_id:
            query += " WHERE product_line_id = ?"
            params.append(product_line_id)

        query += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def load_task_context(task_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT context_snapshot FROM analysis_tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["context_snapshot"])
        except (json.JSONDecodeError, TypeError):
            return {}
    finally:
        conn.close()


def delete_task(task_id: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM parsed_parameters WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM deviation_results WHERE parsed_param_id IN "
                     "(SELECT id FROM parsed_parameters WHERE task_id = ?)", (task_id,))
        conn.execute("DELETE FROM score_results WHERE task_id = ?", (task_id,))
        conn.execute("DELETE FROM analysis_tasks WHERE id = ?", (task_id,))
        conn.commit()
        return True
    finally:
        conn.close()
