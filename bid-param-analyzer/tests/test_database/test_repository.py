"""
repository.py 单元测试

覆盖: CRUD、版本切换、Excel 导入导出、别名管理
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from database.migrations import get_connection
import database.repository as repo


def _list_product_lines():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM product_lines").fetchall()
        return [repo._row_to_product_line(r) for r in rows]
    finally:
        conn.close()


def _get_active_version(product_line_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM product_versions WHERE product_line_id = ? AND is_active = 1",
            (product_line_id,),
        ).fetchone()
        if row:
            return repo._row_to_product_version(row)
        return None
    finally:
        conn.close()


def _insert_parameter(version_id, name, nominal_value, unit="", category=""):
    conn = get_connection()
    import uuid
    pid = f"par_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO parameter_records (id, version_id, name, nominal_value, unit, category) VALUES (?, ?, ?, ?, ?, ?)",
        (pid, version_id, name, nominal_value, unit, category),
    )
    conn.commit()
    conn.close()
    return pid


class TestCreateProductLine:
    def test_create(self):
        pl = repo.create_product_line("网络安全产品", "下一代防火墙")
        assert pl.id.startswith("pl_")
        assert pl.name == "网络安全产品"
        assert len(_list_product_lines()) == 1

    def test_create_second(self):
        repo.create_product_line("PL-A")
        repo.create_product_line("PL-B")
        assert len(_list_product_lines()) >= 2


class TestVersionManagement:
    def test_create_and_switch(self):
        pl = repo.create_product_line("PL-V", "描述")
        v1 = repo.create_product_version(pl.id, "V1.0", "2025-01-01")
        v2 = repo.create_product_version(pl.id, "V2.0", "2025-06-01")

        assert v1.id.startswith("v_")
        assert not v1.is_active

        assert repo.switch_version(pl.id, v1.id)
        ver = _get_active_version(pl.id)
        assert ver is not None
        assert ver.id == v1.id

        assert repo.switch_version(pl.id, v2.id)
        ver2 = _get_active_version(pl.id)
        assert ver2.id == v2.id

    def test_version_history(self):
        pl = repo.create_product_line("PL-HIST")
        v1 = repo.create_product_version(pl.id, "V1", "2025-01-01")
        v2 = repo.create_product_version(pl.id, "V2", "2025-03-01")
        history = repo.get_version_history(pl.id)
        assert len(history) >= 2

    def test_active_version_none(self):
        pl = repo.create_product_line("PL-NONE")
        assert _get_active_version(pl.id) is None

    def test_switch_nonexistent(self):
        pl = repo.create_product_line("PL-NX")
        assert repo.switch_version(pl.id, "nonexistent_id") is True

    def test_empty_params(self):
        pl = repo.create_product_line("PL-EMP")
        v = repo.create_product_version(pl.id, "V1")
        assert repo.get_version_params(v.id) == []


class TestParameterCRUD:
    def test_insert_and_get(self):
        pl = repo.create_product_line("PL-CRUD")
        v = repo.create_product_version(pl.id, "V1")
        repo.switch_version(pl.id, v.id)

        pid = _insert_parameter(v.id, "最大吞吐量", "10Gbps", unit="Gbps", category="性能")
        assert pid.startswith("par_")

        params = repo.get_version_params(v.id)
        assert len(params) == 1
        assert params[0].name == "最大吞吐量"

    def test_insert_id_format(self):
        pl = repo.create_product_line("PL-ID")
        v = repo.create_product_version(pl.id, "V1")
        pid = _insert_parameter(v.id, "并发连接数", "500万")
        assert pid.startswith("par_")

    def test_update(self):
        pl = repo.create_product_line("PL-UP")
        v = repo.create_product_version(pl.id, "V1")
        pid = _insert_parameter(v.id, "并发连接数", "500万")

        result = repo.update_parameter(pid, {"nominal_value": "600万", "unit": "条"})
        assert result is not None
        assert result.nominal_value == "600万"

    def test_update_nonexistent(self):
        assert repo.update_parameter("nonexistent", {"nominal_value": "test"}) is None


class TestAliasManagement:
    def test_add_and_get(self):
        pl = repo.create_product_line("PL-AL")
        v = repo.create_product_version(pl.id, "V1")
        pid = _insert_parameter(v.id, "最大吞吐量", "10Gbps")

        assert repo.add_alias(pid, "吞吐量")
        assert repo.add_alias(pid, "Throughput")

        aliases = repo.get_aliases(pid)
        assert "吞吐量" in aliases
        assert "Throughput" in aliases

    def test_empty_aliases(self):
        assert repo.get_aliases("nonexistent") == []

    def test_delete(self):
        pl = repo.create_product_line("PL-DA")
        v = repo.create_product_version(pl.id, "V1")
        pid = _insert_parameter(v.id, "最大吞吐量", "10Gbps")

        repo.add_alias(pid, "别名1")
        assert repo.delete_alias(pid, "别名1")
        assert "别名1" not in repo.get_aliases(pid)


class TestExcelIO:
    def test_export(self, tmp_path):
        pl = repo.create_product_line("PL-EXP")
        v = repo.create_product_version(pl.id, "V1")
        _insert_parameter(v.id, "最大吞吐量", "10Gbps", unit="Gbps")
        _insert_parameter(v.id, "并发连接数", "500万", unit="条")

        output = os.path.join(tmp_path, "params.xlsx")
        path = repo.export_to_excel(v.id, output)
        assert os.path.exists(path)

    def test_import(self, tmp_path):
        import openpyxl
        pl = repo.create_product_line("PL-IMP")
        v = repo.create_product_version(pl.id, "V1")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["参数名称", "标称值", "单位", "类别"])
        ws.append(["最大吞吐量", "10Gbps", "Gbps", "性能"])
        ws.append(["并发连接数", "500万", "条", "性能"])
        file_path = os.path.join(tmp_path, "import_test.xlsx")
        wb.save(file_path)

        result = repo.import_from_excel(file_path, version_id=v.id)
        assert result.get("imported", 0) >= 2
