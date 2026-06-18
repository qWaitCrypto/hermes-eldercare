"""Hermes plugin registration for hermes-eldercare."""

from __future__ import annotations

import argparse
from typing import Any

from .installer import apply_profile, doctor_profile
from .prompts import ELDERCARE_TURN_CONTEXT
from .style import clean_response


def _pre_llm_call(**kwargs: Any) -> dict[str, str] | None:
    platform = str(kwargs.get("platform") or "").lower()
    # Inject on all eldercare-relevant platforms: the older adult channel (weixin),
    # all potential guardian channels (discord, telegram, slack, etc.), and
    # internal runtime platforms (gateway, cli, local). TURN_CONTEXT itself
    # contains the channel-awareness logic that distinguishes elder vs family.
    # Only block platforms that are clearly unrelated to this profile.
    _EXCLUDED = {"teams", "matrix"}
    if platform and platform in _EXCLUDED:
        return None
    return {"context": ELDERCARE_TURN_CONTEXT}


def _transform_llm_output(**kwargs: Any) -> str | None:
    text = kwargs.get("response_text")
    if not isinstance(text, str):
        return None
    cleaned = clean_response(text)
    return cleaned if cleaned != text else None


def _register_cli(subparser: argparse.ArgumentParser) -> None:
    subs = subparser.add_subparsers(dest="eldercare_command")

    apply_p = subs.add_parser("apply", help="Create or update the hermes-eldercare profile")
    apply_p.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")
    apply_p.add_argument("--clone-from", default=None, help="Source Hermes profile to clone config from")
    apply_p.add_argument(
        "--guardian-channel",
        action="append",
        dest="guardian_channels",
        help="Guardian/family gateway channel; can be repeated",
    )
    apply_p.add_argument("--quiet", action="store_true", help="Print only errors")

    doctor_p = subs.add_parser("doctor", help="Check the hermes-eldercare profile")
    doctor_p.add_argument("--json", action="store_true", dest="as_json", help="Print JSON diagnostics")

    subparser.set_defaults(func=_cli_command)


def _cli_command(args: argparse.Namespace) -> int:
    command = getattr(args, "eldercare_command", None)
    if command == "apply":
        result = apply_profile(
            dry_run=bool(getattr(args, "dry_run", False)),
            clone_from=getattr(args, "clone_from", None),
            guardian_channels=getattr(args, "guardian_channels", None),
        )
        if not getattr(args, "quiet", False):
            print(result.to_human())
        return 0 if result.ok else 1
    if command == "doctor":
        result = doctor_profile()
        if getattr(args, "as_json", False):
            print(result.to_json())
        else:
            print(result.to_human())
        return 0 if result.ok else 1
    print("usage: hermes eldercare {apply,doctor}")
    return 2


def register(ctx: Any) -> None:
    """Register eldercare hooks and CLI command with Hermes."""
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
    ctx.register_cli_command(
        name="eldercare",
        help="Configure and diagnose the hermes-eldercare profile",
        setup_fn=_register_cli,
        handler_fn=_cli_command,
        description="Apply or check the Weixin-first eldercare Hermes profile.",
    )
