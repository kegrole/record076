"""JSON report construction for URL deduplication."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable

from .dedupe import group_records


def build_report(references: Iterable[str], base: str) -> dict[str, object]:
    references = list(references)
    groups = group_records(references, base)
    return {
        "groups": groups,
        "total_records": len(references),
    }


def write_report(report: dict[str, object], out_path: str) -> None:
    parent = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
