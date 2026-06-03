\
from __future__ import annotations

import argparse
import sys

from .generators import generate_system
from .renderers import render_json, render_mud, render_summary
from .validators import validate_system


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="systemgen",
        description="Generate deterministic stellar systems for Exploration MUD.",
    )
    parser.add_argument("--seed", type=int, required=True, help="Deterministic generation seed.")
    parser.add_argument("--name", type=str, default=None, help="Optional system name.")
    parser.add_argument(
        "--format",
        choices=["summary", "json", "mud"],
        default="summary",
        help="Output format.",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=0.0,
        help="Elapsed days used for MUD contact position rendering.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only run validation and print errors/warnings.",
    )
    parser.add_argument(
        "--compact-json",
        action="store_true",
        help="Emit compact JSON when --format json is used.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    system = generate_system(seed=args.seed, name=args.name)

    if args.validate_only:
        errors, warnings = validate_system(system)
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"Warning: {warning}")
        return 1 if errors else 0

    if args.format == "json":
        print(render_json(system, pretty=not args.compact_json))
    elif args.format == "mud":
        print(render_mud(system, elapsed_days=args.time))
    else:
        print(render_summary(system))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
