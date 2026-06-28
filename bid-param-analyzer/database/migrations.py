"""
数据库初始化与迁移

管理 SQLite 数据库的建表、版本迁移和连接生命周期。
"""
import os
import sqlite3

from config.settings import DATABASE_PATH, DATA_DIR


def get_connection() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA_VERSION = 1

CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS product_lines (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS product_versions (
        id TEXT PRIMARY KEY,
        product_line_id TEXT NOT NULL,
        version_name TEXT NOT NULL,
        release_date TEXT DEFAULT '',
        is_active INTEGER DEFAULT 0,
        FOREIGN KEY (product_line_id) REFERENCES product_lines(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS parameter_records (
        id TEXT PRIMARY KEY,
        version_id TEXT NOT NULL,
        name TEXT NOT NULL,
        nominal_value TEXT DEFAULT '',
        acceptable_range TEXT DEFAULT '',
        unit TEXT DEFAULT '',
        deviation_preset TEXT DEFAULT '',
        category TEXT DEFAULT '',
        FOREIGN KEY (version_id) REFERENCES product_versions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_indices (
        id TEXT PRIMARY KEY,
        parameter_id TEXT NOT NULL,
        doc_title TEXT DEFAULT '',
        doc_path TEXT DEFAULT '',
        page_ref TEXT DEFAULT '',
        FOREIGN KEY (parameter_id) REFERENCES parameter_records(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS parameter_aliases (
        id TEXT PRIMARY KEY,
        parameter_id TEXT NOT NULL,
        alias TEXT NOT NULL,
        FOREIGN KEY (parameter_id) REFERENCES parameter_records(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS analysis_tasks (
        id TEXT PRIMARY KEY,
        status TEXT DEFAULT 'PENDING',
        bid_file_path TEXT DEFAULT '',
        product_line_id TEXT DEFAULT '',
        version_id TEXT DEFAULT '',
        context_snapshot TEXT DEFAULT '{}',
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS parsed_parameters (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        name TEXT NOT NULL,
        requirement_value TEXT DEFAULT '',
        unit TEXT DEFAULT '',
        is_material INTEGER DEFAULT 0,
        param_type TEXT DEFAULT '',
        source_location TEXT DEFAULT '',
        parent_id TEXT DEFAULT '',
        FOREIGN KEY (task_id) REFERENCES analysis_tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS deviation_results (
        id TEXT PRIMARY KEY,
        parsed_param_id TEXT NOT NULL,
        match_param_id TEXT DEFAULT '',
        deviation_type TEXT DEFAULT '无法确认',
        similarity_score REAL DEFAULT 0.0,
        explanation TEXT DEFAULT '',
        risk_level TEXT DEFAULT '无风险',
        suggestion TEXT DEFAULT '',
        FOREIGN KEY (parsed_param_id) REFERENCES parsed_parameters(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS score_results (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        rule_name TEXT DEFAULT '',
        max_score REAL DEFAULT 0.0,
        actual_score REAL DEFAULT 0.0,
        trace_data TEXT DEFAULT '{}',
        FOREIGN KEY (task_id) REFERENCES analysis_tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT DEFAULT (datetime('now'))
    )
    """,
]

INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_product_versions_line ON product_versions(product_line_id)",
    "CREATE INDEX IF NOT EXISTS idx_product_versions_active ON product_versions(is_active)",
    "CREATE INDEX IF NOT EXISTS idx_parameter_records_version ON parameter_records(version_id)",
    "CREATE INDEX IF NOT EXISTS idx_parameter_records_name ON parameter_records(name)",
    "CREATE INDEX IF NOT EXISTS idx_parameter_aliases_param ON parameter_aliases(parameter_id)",
    "CREATE INDEX IF NOT EXISTS idx_parameter_aliases_alias ON parameter_aliases(alias)",
    "CREATE INDEX IF NOT EXISTS idx_analysis_tasks_status ON analysis_tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_parsed_parameters_task ON parsed_parameters(task_id)",
    "CREATE INDEX IF NOT EXISTS idx_deviation_results_param ON deviation_results(parsed_param_id)",
    "CREATE INDEX IF NOT EXISTS idx_score_results_task ON score_results(task_id)",
]


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_connection()
    try:
        for sql in CREATE_TABLES_SQL:
            conn.execute(sql)
        for sql in INDEX_SQL:
            conn.execute(sql)
        existing = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        conn.commit()
    finally:
        conn.close()


def migrate():
    conn = get_connection()
    try:
        current = conn.execute(
            "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
        ).fetchone()
        current_version = current["version"] if current else 0
        if current_version < SCHEMA_VERSION:
            for sql in CREATE_TABLES_SQL:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass
            for sql in INDEX_SQL:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass
            if current_version == 0:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            else:
                conn.execute(
                    "UPDATE schema_version SET version = ?, applied_at = datetime('now')",
                    (SCHEMA_VERSION,),
                )
            conn.commit()
    finally:
        conn.close()
