"""RFC 3986 URL normalization and deduplication toolkit (stdlib only)."""

from .dedupe import group_records
from .normalize import normalize_url
from .parser import (
    URIComponents,
    parse_uri_reference,
    remove_dot_segments,
    recompose,
    resolve_reference,
)
from .query import normalize_query, uppercase_pct_encoded
from .report import build_report, write_report

__all__ = [
    "URIComponents",
    "build_report",
    "group_records",
    "normalize_query",
    "normalize_url",
    "parse_uri_reference",
    "remove_dot_segments",
    "recompose",
    "resolve_reference",
    "uppercase_pct_encoded",
    "write_report",
]
