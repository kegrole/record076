"""RFC 3986 URI reference parsing and relative-reference resolution.

Implements the component split of RFC 3986 Appendix B together with the
full reference resolution algorithm of RFC 3986 section 5.2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


_URI_REFERENCE_RE = re.compile(
    r"^"
    r"(?:(?P<scheme>[^:/?#]+):)?"
    r"(?://(?P<authority>[^/?#]*))?"
    r"(?P<path>[^?#]*)"
    r"(?:\?(?P<query>[^#]*))?"
    r"(?:#(?P<fragment>.*))?"
    r"$"
)


@dataclass(frozen=True)
class URIComponents:
    """The seven URI components plus an explicit authority-presence flag."""

    scheme: str | None
    has_authority: bool
    userinfo: str | None
    host: str
    port: str | None
    path: str
    query: str | None
    fragment: str | None


def parse_uri_reference(reference: str) -> URIComponents:
    """Split a URI reference into scheme, userinfo, host, port, path, query, fragment."""

    match = _URI_REFERENCE_RE.match(reference)
    if match is None:
        raise ValueError(f"invalid URI reference: {reference!r}")

    scheme = match.group("scheme")
    authority = match.group("authority")
    path = match.group("path") or ""
    query = match.group("query")
    fragment = match.group("fragment")

    has_authority = authority is not None
    userinfo: str | None = None
    host = ""
    port: str | None = None

    if has_authority:
        remainder = authority
        if "@" in remainder:
            userinfo, remainder = remainder.split("@", 1)
        if remainder.startswith("["):
            bracket_end = remainder.find("]")
            if bracket_end == -1:
                raise ValueError(f"unterminated IPv6 literal in authority: {authority!r}")
            host = remainder[: bracket_end + 1]
            tail = remainder[bracket_end + 1 :]
            if tail.startswith(":"):
                port = tail[1:] or None
        elif ":" in remainder:
            host, port_text = remainder.rsplit(":", 1)
            port = port_text or None
        else:
            host = remainder

    return URIComponents(
        scheme=scheme,
        has_authority=has_authority,
        userinfo=userinfo,
        host=host,
        port=port,
        path=path,
        query=query,
        fragment=fragment,
    )


def remove_dot_segments(path: str) -> str:
    """RFC 3986 section 5.2.4: remove "." and ".." segments from a path."""

    input_buffer = path
    output: list[str] = []

    while input_buffer:
        if input_buffer.startswith("../"):
            input_buffer = input_buffer[3:]
        elif input_buffer.startswith("./"):
            input_buffer = input_buffer[2:]
        elif input_buffer.startswith("/./"):
            input_buffer = "/" + input_buffer[3:]
        elif input_buffer == "/.":
            input_buffer = "/"
        elif input_buffer.startswith("/../"):
            input_buffer = "/" + input_buffer[4:]
            if output:
                output.pop()
        elif input_buffer == "/..":
            input_buffer = "/"
            if output:
                output.pop()
        elif input_buffer in (".", ".."):
            input_buffer = ""
        else:
            if input_buffer.startswith("/"):
                next_slash = input_buffer.find("/", 1)
            else:
                next_slash = input_buffer.find("/")
            if next_slash == -1:
                segment, input_buffer = input_buffer, ""
            else:
                segment, input_buffer = input_buffer[:next_slash], input_buffer[next_slash:]
            output.append(segment)

    return "".join(output)


def _merge_path(base: URIComponents, reference_path: str) -> str:
    """RFC 3986 section 5.2.3 merge."""

    if base.has_authority and base.path == "":
        return "/" + reference_path
    last_slash = base.path.rfind("/")
    if last_slash == -1:
        return reference_path
    return base.path[: last_slash + 1] + reference_path


def resolve_reference(base_reference: str, reference: str) -> URIComponents:
    """RFC 3986 section 5.2.2 transform of a reference against a base URI."""

    base = parse_uri_reference(base_reference)
    ref = parse_uri_reference(reference)

    if ref.scheme is not None:
        scheme = ref.scheme
        has_authority = ref.has_authority
        userinfo = ref.userinfo
        host = ref.host
        port = ref.port
        path = remove_dot_segments(ref.path)
        query = ref.query
    elif ref.has_authority:
        scheme = base.scheme
        has_authority = True
        userinfo = ref.userinfo
        host = ref.host
        port = ref.port
        path = remove_dot_segments(ref.path)
        query = ref.query
    else:
        scheme = base.scheme
        has_authority = base.has_authority
        userinfo = base.userinfo
        host = base.host
        port = base.port
        if ref.path == "":
            path = base.path
            query = ref.query if ref.query is not None else base.query
        else:
            if ref.path.startswith("/"):
                path = remove_dot_segments(ref.path)
            else:
                path = remove_dot_segments(_merge_path(base, ref.path))
            query = ref.query

    return URIComponents(
        scheme=scheme,
        has_authority=has_authority,
        userinfo=userinfo,
        host=host,
        port=port,
        path=path,
        query=query,
        fragment=ref.fragment,
    )


def recompose(components: URIComponents, include_fragment: bool = True) -> str:
    """RFC 3986 section 5.3: rebuild a URI reference from its components."""

    result = ""
    if components.scheme is not None:
        result += components.scheme + ":"
    if components.has_authority:
        result += "//"
        if components.userinfo is not None:
            result += components.userinfo + "@"
        result += components.host
        if components.port is not None:
            result += ":" + components.port
    result += components.path
    if components.query is not None:
        result += "?" + components.query
    if include_fragment and components.fragment is not None:
        result += "#" + components.fragment
    return result
