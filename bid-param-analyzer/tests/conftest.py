"""
pytest 配置 - 确保每个测试使用独立的数据库
"""
import os
import tempfile
import pytest


@pytest.fixture(autouse=True)
def _unique_test_db():
    import importlib
    import config.settings as s
    import database.migrations as mig

    test_nodeid = os.environ.get("PYTEST_CURRENT_TEST", "test")
    safe = test_nodeid.replace("(", "").replace(")", "").replace(":", "_").replace("/", "_").replace(" ", "_")
    import time
    db_name = f"bid_test_{abs(hash(safe))}_{int(time.time() * 1000)}.db"

    # Force-reload settings to avoid cached state
    importlib.reload(s)
    s.DATABASE_PATH = os.path.join(tempfile.gettempdir(), db_name)
    s.DATA_DIR = tempfile.gettempdir()
    s.TEMP_FILE_DIR = os.path.join(tempfile.gettempdir(), f"up_{hash(safe) % 100000}")
    s.REPORT_OUTPUT_DIR = tempfile.gettempdir()
    os.makedirs(s.TEMP_FILE_DIR, exist_ok=True)

    # Force-reload migrations so it picks up the new DATABASE_PATH
    importlib.reload(mig)

    # Remove existing DB to ensure fresh start
    if os.path.exists(s.DATABASE_PATH):
        os.unlink(s.DATABASE_PATH)

    mig.init_db()
