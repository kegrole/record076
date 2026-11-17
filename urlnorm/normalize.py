"""Canonical normalization of URI references."""

from __future__ import annotations

from .parser import URIComponents, recompose, resolve_reference
from .query import normalize_query, uppercase_pct_encoded


_DEFAULT_PORTS = {
    "http": "80",
    "https": "443",
}


def normalize_url(reference: str, base: str) -> str:
    """Resolve ``reference`` against ``base`` and return its canonical form.

    The result never carries a fragment, percent-encoded triplets keep their
    bytes (only hex letters are uppercased), literal allowed characters stay
    literal, default ports disappear and the query string is sorted.
    """

    resolved = resolve_reference(base, reference)

    scheme = resolved.scheme.lower() if resolved.scheme is not None else None
    host = resolved.host.lower()

    port = resolved.port
    if port is not None and port.isdigit() and _DEFAULT_PORTS.get(scheme) == port:
        port = None

    path = uppercase_pct_encoded(resolved.path)
    query = normalize_query(resolved.query)

    canonical_components = URIComponents(
        scheme=scheme,
        has_authority=resolved.has_authority,
        userinfo=resolved.userinfo,
        host=host,
        port=port,
        path=path,
        query=query,
        fragment=None,
    )
    return recompose(canonical_components, include_fragment=False)
