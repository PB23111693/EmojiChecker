"""文本归一化。"""

from __future__ import annotations

import unicodedata


def normalize_class_name(value: str) -> str:
    """统一班级名的全角半角与空白，避免同一班级在统计中分裂为多个取值。

    班级仍是课堂上的自由文本字段，不引入独立实体；归一化只保证录入差异
    不会造成查询与聚合口径分裂。调用方需保证输入非空。
    """
    normalized = unicodedata.normalize("NFKC", value)
    return " ".join(normalized.split())
