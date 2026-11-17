"""Command line entry point: ``python -m urlnorm.cli``."""

from __future__ import annotations

import argparse

from .report import build_report, write_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize URLs per RFC 3986 and group duplicate records."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSONL/UTF-8 text file of URL references, one per line.",
    )
    parser.add_argument(
        "--base",
        required=True,
        help="Base URL used to resolve relative references.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path of the JSON report to write.",
    )
    args = parser.parse_args(argv)

    with open(args.input, encoding="utf-8") as handle:
        references = handle.read().splitlines()

    report = build_report(references, args.base)
    write_report(report, args.out)

    group_count = len(report["groups"])
    largest_group = max(
        (len(group["records"]) for group in report["groups"]),
        default=0,
    )
    print(
        f"records={report['total_records']} "
        f"groups={group_count} unique={group_count} "
        f"largest_group={largest_group}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
