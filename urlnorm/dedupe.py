"""Group input records by their normalized canonical URL."""

from __future__ import annotations

from collections.abc import Iterable

from .normalize import normalize_url


def group_records(references: Iterable[str], base: str) -> list[dict[str, object]]:
    """Return canonical groups ordered by the smallest input line number."""

    groups: dict[str, list[int]] = {}
    for line_number, reference in enumerate(references, start=1):
        canonical = normalize_url(reference, base)
        groups.setdefault(canonical, []).append(line_number)

    result = [
        {"canonical": canonical, "records": records}
        for canonical, records in groups.items()
    ]
    result.sort(key=lambda group: group["records"][0])
    return result
