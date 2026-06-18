"""Standalone CLI for hermes-eldercare."""

from __future__ import annotations

import argparse
import sys

from .installer import apply_profile, doctor_profile


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hermes-eldercare")
    subs = parser.add_subparsers(dest="command")

    init_p = subs.add_parser("init", help="Alias for apply")
    init_p.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    init_p.add_argument("--clone-from", default=None, help="Source Hermes profile to clone config from")
    init_p.add_argument("--guardian-channel", action="append", dest="guardian_channels")

    apply_p = subs.add_parser("apply", help="Create or update the hermes-eldercare profile")
    apply_p.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    apply_p.add_argument("--clone-from", default=None, help="Source Hermes profile to clone config from")
    apply_p.add_argument("--guardian-channel", action="append", dest="guardian_channels")

    doctor_p = subs.add_parser("doctor", help="Check the hermes-eldercare profile")
    doctor_p.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in {"init", "apply"}:
        result = apply_profile(
            dry_run=bool(args.dry_run),
            clone_from=args.clone_from,
            guardian_channels=args.guardian_channels,
        )
        print(result.to_human())
        return 0 if result.ok else 1
    if args.command == "doctor":
        result = doctor_profile()
        print(result.to_json() if args.as_json else result.to_human())
        return 0 if result.ok else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
