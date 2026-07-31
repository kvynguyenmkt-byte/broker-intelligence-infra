"""Cưỡng chế mandate bằng test, không bằng lời nhắc (CLAUDE.md mục 1, ADR-002).

Không field nào trong output contract được mang tính khuyến nghị. Đây là cơ chế
cưỡng chế #2: linter chặn tên trường khớp regex.
"""
import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

_SCHEMA_DIR = Path(__file__).resolve().parents[2] / "config" / "schemas"

# Regex y hệt CLAUDE.md mục 1.
_FORBIDDEN = re.compile(
    r"(recommend|suggest|should|advice|best_|optimal|strategy|bid_|budget|draft|proposed)",
    re.IGNORECASE,
)


def _iter_property_names(node, path="$"):
    if isinstance(node, dict):
        props = node.get("properties")
        if isinstance(props, dict):
            for name in props:
                yield name, f"{path}.{name}"
        for key, value in node.items():
            yield from _iter_property_names(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _iter_property_names(item, f"{path}[{i}]")


def _schema_files():
    return sorted(_SCHEMA_DIR.glob("*.json"))


def test_schema_dir_has_files():
    assert _schema_files(), "Không tìm thấy schema nào trong config/schemas."


@pytest.mark.parametrize("schema_path", _schema_files(), ids=lambda p: p.name)
def test_no_recommendation_field_names(schema_path):
    schema = json.loads(schema_path.read_text("utf-8"))
    offenders = [
        loc for name, loc in _iter_property_names(schema) if _FORBIDDEN.search(name)
    ]
    assert not offenders, (
        f"{schema_path.name} có field mang tính khuyến nghị: {offenders}. "
        "Không có chỗ chứa thì không có chỗ bịa (ADR-002)."
    )


@pytest.mark.parametrize("schema_path", _schema_files(), ids=lambda p: p.name)
def test_schema_is_valid_draft202012(schema_path):
    schema = json.loads(schema_path.read_text("utf-8"))
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("schema_path", _schema_files(), ids=lambda p: p.name)
def test_objects_forbid_additional_properties(schema_path):
    """Mọi object schema phải đặt additionalProperties:false (ADR-002)."""
    schema = json.loads(schema_path.read_text("utf-8"))

    def walk(node, path="$"):
        if isinstance(node, dict):
            if node.get("type") == "object" and "properties" in node:
                assert node.get("additionalProperties") is False, (
                    f"{schema_path.name} {path}: object thiếu additionalProperties:false"
                )
            for key, value in node.items():
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, f"{path}[{i}]")

    walk(schema)
