"""Acceptance tests for the urlnorm package.

The eleven numbered test classes map one-to-one onto the eleven judgment
criteria in the task specification.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from urlnorm import (
    build_report,
    group_records,
    normalize_query,
    normalize_url,
    parse_uri_reference,
)
from urlnorm.parser import remove_dot_segments, resolve_reference


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_PATH = REPO_ROOT / "demo" / "urls.jsonl"
BASE = "https://example.com/dir/page.html"


def load_demo() -> list[str]:
    return DEMO_PATH.read_text(encoding="utf-8").splitlines()


class Criterion01DemoFixtureTests(unittest.TestCase):
    def test_demo_contains_exactly_the_seven_specified_records(self) -> None:
        expected = [
            "https://Example.COM:443/a/../b?z=1&y=2#frag",
            "/b?y=2&z=1",
            "https://example.com:443/a/../b?y=2&z=1",
            "https://user:pw@example.com/a%2Fb?y=2&z=1",
            "https://user:pw@example.com:443/a%2Fb?y=2&z=1",
            "https://example.com/b/?z=&y=2",
            "https://EXAMPLE.com:443/b/?y=2&z",
        ]
        self.assertEqual(load_demo(), expected)
        self.assertEqual(len(load_demo()), 7)


class Criterion02FirstGroupCanonicalTests(unittest.TestCase):
    def test_records_1_2_3_share_one_canonical_form(self) -> None:
        records = load_demo()
        canonical = [normalize_url(record, BASE) for record in records[:3]]
        self.assertEqual(len(set(canonical)), 1)
        self.assertEqual(
            canonical[0],
            "https://example.com/b?y=2&z=1",
        )


class Criterion03RelativeResolutionTests(unittest.TestCase):
    def test_relative_path_uses_rfc523_merge_not_string_concatenation(self) -> None:
        self.assertEqual(
            normalize_url("/b?y=2&z=1", BASE),
            "https://example.com/b?y=2&z=1",
        )


class Criterion04UserinfoAndPct2fTests(unittest.TestCase):
    def test_userinfo_preserved_and_encoded_slash_kept_encoded(self) -> None:
        records = load_demo()
        canonical = [normalize_url(record, BASE) for record in records[3:5]]
        self.assertEqual(len(set(canonical)), 1)
        self.assertEqual(
            canonical[0],
            "https://user:pw@example.com/a%2Fb?y=2&z=1",
        )
        self.assertNotIn("/a/b", canonical[0])


class Criterion05TrailingSlashAndEmptyValueTests(unittest.TestCase):
    def test_trailing_slash_kept_and_bare_key_rendered_as_key_equals(self) -> None:
        records = load_demo()
        canonical = [normalize_url(record, BASE) for record in records[5:7]]
        self.assertEqual(len(set(canonical)), 1)
        self.assertEqual(
            canonical[0],
            "https://example.com/b/?y=2&z=",
        )
        self.assertNotEqual(
            canonical[0],
            normalize_url(records[0], BASE),
        )


class Criterion06FragmentStrippingTests(unittest.TestCase):
    def test_fragment_is_removed_and_hash_never_appears(self) -> None:
        records = load_demo()
        first = normalize_url(records[0], BASE)
        third = normalize_url(records[2], BASE)
        self.assertNotIn("#", first)
        self.assertEqual(first, third)


class Criterion07GroupingTests(unittest.TestCase):
    def test_three_groups_with_sizes_3_2_2_in_first_record_order(self) -> None:
        groups = group_records(load_demo(), BASE)
        sizes = [len(group["records"]) for group in groups]
        self.assertEqual(sizes, [3, 2, 2])
        self.assertEqual(sum(sizes), 7)
        minimums = [group["records"][0] for group in groups]
        self.assertEqual(minimums, sorted(minimums))
        self.assertEqual(
            [group["records"] for group in groups],
            [[1, 2, 3], [4, 5], [6, 7]],
        )


class Criterion08ReportSchemaTests(unittest.TestCase):
    def test_report_has_required_top_level_and_group_fields(self) -> None:
        report = build_report(load_demo(), BASE)
        self.assertEqual(set(report), {"groups", "total_records"})
        self.assertEqual(report["total_records"], 7)
        self.assertEqual(len(report["groups"]), 3)
        for group in report["groups"]:
            self.assertEqual(set(group), {"canonical", "records"})
            records = group["records"]
            self.assertEqual(records, sorted(records))
            self.assertTrue(all(isinstance(index, int) and index >= 1 for index in records))

    def test_report_json_roundtrip_matches_in_memory_report(self, tmp_path=None) -> None:
        from urlnorm import write_report

        out_path = REPO_ROOT / "out" / "report_test.json"
        report = build_report(load_demo(), BASE)
        write_report(report, str(out_path))
        try:
            loaded = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded, report)
        finally:
            out_path.unlink()


class Criterion09IdempotencyTests(unittest.TestCase):
    def test_every_canonical_url_is_a_fixed_point(self) -> None:
        groups = group_records(load_demo(), BASE)
        self.assertEqual(len(groups), 3)
        for group in groups:
            canonical = group["canonical"]
            self.assertEqual(normalize_url(canonical, BASE), canonical)


class Criterion10CharacterSetAndPortTests(unittest.TestCase):
    def test_literal_path_characters_remain_unencoded(self) -> None:
        literal_path = "/~!$&'()*+,;=:@"
        self.assertEqual(
            normalize_url("https://example.com" + literal_path, BASE),
            "https://example.com" + literal_path,
        )

    def test_lowercase_pct_encoded_hex_is_uppercased_without_decoding(self) -> None:
        self.assertEqual(
            normalize_url("https://example.com/a%2fb%3ac", BASE),
            "https://example.com/a%2Fb%3Ac",
        )

    def test_encoded_slash_is_not_a_path_separator(self) -> None:
        self.assertEqual(
            normalize_url("https://example.com/a%2f..%2fb", BASE),
            "https://example.com/a%2F..%2Fb",
        )

    def test_literal_slash_and_question_mark_in_query_are_kept(self) -> None:
        self.assertEqual(
            normalize_url("https://example.com/x?q=a/b?c", BASE),
            "https://example.com/x?q=a/b?c",
        )

    def test_default_ports_removed_and_other_ports_kept(self) -> None:
        self.assertEqual(
            normalize_url("http://example.com:80/x", BASE),
            "http://example.com/x",
        )
        self.assertEqual(
            normalize_url("http://example.com:8080/x", BASE),
            "http://example.com:8080/x",
        )
        self.assertEqual(
            normalize_url("https://example.com:443/x", BASE),
            "https://example.com/x",
        )


class Criterion11ReferenceResolutionCombinationTests(unittest.TestCase):
    def test_rfc522_resolution_cases_and_their_idempotency(self) -> None:
        cases = [
            ("", "https://example.com/dir/page.html"),
            ("?y=1", "https://example.com/dir/page.html?y=1"),
            ("#frag", "https://example.com/dir/page.html"),
            ("../g", "https://example.com/g"),
            ("//other.org/x", "https://other.org/x"),
        ]
        for reference, expected in cases:
            with self.subTest(reference=reference):
                canonical = normalize_url(reference, BASE)
                self.assertEqual(canonical, expected)
                self.assertEqual(normalize_url(canonical, BASE), canonical)


class ExtraNormalizationTests(unittest.TestCase):
    def test_parser_exposes_all_seven_components(self) -> None:
        components = parse_uri_reference(
            "https://user:pw@host.example:8080/p%2fa?x=1#frag"
        )
        self.assertEqual(components.scheme, "https")
        self.assertTrue(components.has_authority)
        self.assertEqual(components.userinfo, "user:pw")
        self.assertEqual(components.host, "host.example")
        self.assertEqual(components.port, "8080")
        self.assertEqual(components.path, "/p%2fa")
        self.assertEqual(components.query, "x=1")
        self.assertEqual(components.fragment, "frag")

    def test_ipv6_literal_keeps_brackets_and_only_changes_case(self) -> None:
        self.assertEqual(
            normalize_url("https://[2001:DB8::1]:443/x", BASE),
            "https://[2001:db8::1]/x",
        )
        self.assertEqual(
            normalize_url("https://[2001:DB8::1]:8080/x", BASE),
            "https://[2001:db8::1]:8080/x",
        )

    def test_consecutive_and_trailing_slashes_are_preserved(self) -> None:
        self.assertEqual(
            normalize_url("https://example.com/a//b/", BASE),
            "https://example.com/a//b/",
        )

    def test_remove_dot_segments_follows_rfc_524_examples(self) -> None:
        self.assertEqual(remove_dot_segments("/a/b/c/./../../g"), "/a/g")
        self.assertEqual(remove_dot_segments("mid/content=5/../6"), "mid/6")

    def test_query_sort_is_stable_and_keeps_repeated_values(self) -> None:
        self.assertEqual(normalize_query("b=2&a=1&a=0"), "a=0&a=1&b=2")
        self.assertEqual(normalize_query("a=1&b=0&a=1"), "a=1&a=1&b=0")
        self.assertEqual(normalize_query("z"), "z=")
        self.assertIsNone(normalize_query(None))
        self.assertEqual(normalize_query(""), "")

    def test_userinfo_is_kept_verbatim_without_decoding_or_recasing(self) -> None:
        self.assertEqual(
            normalize_url("https://us%2fer:pw@example.com/x", BASE),
            "https://us%2fer:pw@example.com/x",
        )
        self.assertEqual(
            normalize_url("https://us%2Fer:pw@example.com/x", BASE),
            "https://us%2Fer:pw@example.com/x",
        )

    def test_network_relative_reference_keeps_base_scheme(self) -> None:
        components = resolve_reference(BASE, "//other.org/p?a=1")
        self.assertEqual(components.scheme, "https")
        self.assertEqual(components.host, "other.org")
        self.assertEqual(components.path, "/p")


if __name__ == "__main__":
    unittest.main()
