"""
产品参数基准库 CRUD 操作

提供产品线、版本、参数记录的增删改查接口。
"""
import json
import uuid
from typing import Optional

from database.migrations import get_connection
from database.models import (
    ParameterRecord,
    EvidenceIndex,
    ProductLine,
    ProductVersion,
    ParameterAlias,
)


def _row_to_product_line(row) -> ProductLine:
    return ProductLine(
        id=row["id"],
        name=row["name"],
        description=row["description"] or "",
        created_at=row["created_at"] or "",
    )


def _row_to_product_version(row) -> ProductVersion:
    return ProductVersion(
        id=row["id"],
        product_line_id=row["product_line_id"],
        version_name=row["version_name"],
        release_date=row["release_date"] or "",
        is_active=bool(row["is_active"]),
    )


def _row_to_parameter(row) -> ParameterRecord:
    return ParameterRecord(
        id=row["id"],
        version_id=row["version_id"],
        name=row["name"],
        nominal_value=row["nominal_value"] or "",
        acceptable_range=row["acceptable_range"] or "",
        unit=row["unit"] or "",
        deviation_preset=row["deviation_preset"] or "",
        category=row["category"] or "",
    )


def create_product_line(name: str, description: str = "") -> ProductLine:
    conn = get_connection()
    try:
        pl_id = f"pl_{uuid.uuid4().hex[:12]}"
        conn.execute(
            "INSERT INTO product_lines (id, name, description) VALUES (?, ?, ?)",
            (pl_id, name, description),
        )
        conn.commit()
        return ProductLine(id=pl_id, name=name, description=description)
    finally:
        conn.close()


def get_active_params(product_line_id: str) -> list[ParameterRecord]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT pr.* FROM parameter_records pr
            JOIN product_versions pv ON pr.version_id = pv.id
            WHERE pv.product_line_id = ? AND pv.is_active = 1
            """,
            (product_line_id,),
        ).fetchall()
        return [_row_to_parameter(r) for r in rows]
    finally:
        conn.close()
