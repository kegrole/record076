"""Query string normalization: pct-encoded casing and stable parameter sorting."""

from __future__ import annotations

import re


_PCT_ENCODED_RE = re.compile(r"%[0-9A-Fa-f]{2}")


def uppercase_pct_encoded(text: str) -> str:
    """Uppercase the hex digits of every pct-encoded triplet without decoding it."""

    return _PCT_ENCODED_RE.sub(lambda match: match.group(0).upper(), text)


def normalize_query(query: str | None) -> str | None:
    """Sort query parameters by (name, value) with a stable sort.

    A bare parameter (no "=") is treated as an empty value and rendered as
    "name=".  An empty but present query string is preserved as "".
    """

    if query is None:
        return None

    query = uppercase_pct_encoded(query)
    if query == "":
        return ""

    pairs: list[tuple[str, str]] = []
    for raw_parameter in query.split("&"):
        if "=" in raw_parameter:
            name, value = raw_parameter.split("=", 1)
        else:
            name, value = raw_parameter, ""
        pairs.append((name, value))

    pairs.sort(key=lambda item: (item[0], item[1]))
    return "&".join(f"{name}={value}" for name, value in pairs)
