"""Profile installer for hermes-eldercare."""

from __future__ import annotations

import copy
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .constants import (
    DEFAULT_GUARDIAN_CHANNELS,
    PLUGIN_NAME,
    PROFILE_NAME,
    WEIXIN_PLATFORM,
)
from .prompts import ELDERCARE_SOUL_MD


@dataclass
class OperationResult:
    ok: bool = True
    changed: bool = False
    messages: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)

    def add(self, message: str) -> None:
        self.messages.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def fail(self, message: str) -> None:
        self.ok = False
        self.errors.append(message)

    def to_human(self) -> str:
        lines: list[str] = []
        lines.extend(self.messages)
        lines.extend(f"WARNING: {msg}" for msg in self.warnings)
        lines.extend(f"ERROR: {msg}" for msg in self.errors)
        return "\n".join(lines) if lines else ("ok" if self.ok else "failed")

    def to_json(self) -> str:
        return json.dumps(
            {
                "ok": self.ok,
                "changed": self.changed,
                "messages": self.messages,
                "warnings": self.warnings,
                "errors": self.errors,
                "data": self.data,
            },
            ensure_ascii=False,
            indent=2,
        )


def apply_profile(
    *,
    dry_run: bool = False,
    clone_from: str | None = None,
    guardian_channels: list[str] | None = None,
) -> OperationResult:
    result = OperationResult(data={"profile": PROFILE_NAME, "dry_run": dry_run})
    profile_dir = _profile_dir(PROFILE_NAME)
    result.data["profile_dir"] = str(profile_dir)

    if not profile_dir.exists():
        if dry_run:
            result.add(f"Would create Hermes profile '{PROFILE_NAME}' by cloning current/default config.")
        else:
            created = _create_profile(PROFILE_NAME, clone_from=clone_from)
            result.changed = True
            result.add(f"Created Hermes profile '{PROFILE_NAME}' at {created}.")
    else:
        result.add(f"Hermes profile '{PROFILE_NAME}' already exists at {profile_dir}.")

    if not dry_run:
        profile_dir.mkdir(parents=True, exist_ok=True)

    channels = _normalize_channels(guardian_channels)
    config_path = profile_dir / "config.yaml"
    config = _read_yaml(config_path)
    desired = _apply_eldercare_config(config, guardian_channels=channels)
    if desired != config:
        if dry_run:
            result.add(f"Would update {config_path}.")
        else:
            _backup_file(config_path)
            _write_yaml(config_path, desired)
            result.changed = True
            result.add(f"Updated {config_path}.")
    else:
        result.add(f"{config_path} already matches eldercare defaults.")

    soul_path = profile_dir / "SOUL.md"
    current_soul = _read_text(soul_path)
    if current_soul != ELDERCARE_SOUL_MD:
        if dry_run:
            result.add(f"Would write {soul_path}.")
        else:
            _backup_file(soul_path)
            soul_path.write_text(ELDERCARE_SOUL_MD, encoding="utf-8")
            result.changed = True
            result.add(f"Wrote {soul_path}.")
    else:
        result.add(f"{soul_path} already matches eldercare SOUL.md.")

    if dry_run and not profile_dir.exists():
        result.warn("Weixin credentials and guardian channels were not checked because the profile does not exist yet.")
    else:
        doctor = _diagnose(profile_dir, desired)
        result.warnings.extend(doctor.warnings)
        result.errors.extend(doctor.errors)
        result.ok = result.ok and doctor.ok
        result.data.update(doctor.data)
    if dry_run and result.ok:
        result.add("Dry run complete; no files were written.")
    elif result.ok:
        result.add(f"Next: hermes -p {PROFILE_NAME} gateway run")
    return result


def doctor_profile() -> OperationResult:
    profile_dir = _profile_dir(PROFILE_NAME)
    config = _read_yaml(profile_dir / "config.yaml")
    result = _diagnose(profile_dir, config)
    result.data["profile"] = PROFILE_NAME
    result.data["profile_dir"] = str(profile_dir)
    if result.ok:
        result.add(f"Profile '{PROFILE_NAME}' is configured enough to try gateway startup.")
    return result


def _create_profile(name: str, *, clone_from: str | None) -> Path:
    try:
        from hermes_cli.profiles import create_profile

        return create_profile(
            name,
            clone_from=clone_from,
            clone_config=True,
            no_alias=True,
            description="Weixin-first Chinese eldercare assistant profile.",
        )
    except ImportError:
        profile_dir = _profile_dir(name)
        profile_dir.mkdir(parents=True, exist_ok=True)
        for subdir in ("memories", "sessions", "skills", "logs", "plans", "workspace", "cron", "home"):
            (profile_dir / subdir).mkdir(parents=True, exist_ok=True)
        source = _default_hermes_home() if clone_from in {None, "default"} else _profile_dir(clone_from)
        for filename in ("config.yaml", ".env"):
            src = source / filename
            if src.exists():
                shutil.copy2(src, profile_dir / filename)
        return profile_dir


def _apply_eldercare_config(config: dict[str, Any], *, guardian_channels: tuple[str, ...]) -> dict[str, Any]:
    cfg = copy.deepcopy(config) if isinstance(config, dict) else {}

    plugins = cfg.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        plugins = {}
        cfg["plugins"] = plugins
    enabled = plugins.setdefault("enabled", [])
    if not isinstance(enabled, list):
        enabled = []
        plugins["enabled"] = enabled
    if PLUGIN_NAME not in enabled:
        enabled.append(PLUGIN_NAME)
    disabled = plugins.get("disabled")
    if isinstance(disabled, list) and PLUGIN_NAME in disabled:
        plugins["disabled"] = [item for item in disabled if item != PLUGIN_NAME]

    cfg["platform_toolsets"] = _merged_platform_toolsets(cfg.get("platform_toolsets"))

    display = cfg.setdefault("display", {})
    if not isinstance(display, dict):
        display = {}
        cfg["display"] = display
    display["language"] = "zh"
    display["runtime_footer"] = {"enabled": False}
    platforms_display = display.setdefault("platforms", {})
    if not isinstance(platforms_display, dict):
        platforms_display = {}
        display["platforms"] = platforms_display
    platforms_display[WEIXIN_PLATFORM] = {
        "tool_progress": "off",
        "streaming": False,
        "interim_assistant_messages": False,
        "long_running_notifications": False,
        "busy_ack_detail": False,
    }

    approvals = cfg.setdefault("approvals", {})
    if not isinstance(approvals, dict):
        approvals = {}
        cfg["approvals"] = approvals
    approvals.setdefault("mode", "smart")
    approvals.setdefault("cron_mode", "approve")

    platforms = cfg.setdefault("platforms", {})
    if not isinstance(platforms, dict):
        platforms = {}
        cfg["platforms"] = platforms
    weixin = platforms.setdefault(WEIXIN_PLATFORM, {})
    if not isinstance(weixin, dict):
        weixin = {}
        platforms[WEIXIN_PLATFORM] = weixin
    weixin["enabled"] = True
    extra = weixin.setdefault("extra", {})
    if not isinstance(extra, dict):
        extra = {}
        weixin["extra"] = extra
    extra.setdefault("dm_policy", "open")
    extra.setdefault("group_policy", "disabled")
    # Gating cannot remove Hermes' hard-coded /help and /whoami floor, but this
    # avoids exposing any additional commands to ordinary eldercare users.
    extra.setdefault("allow_admin_from", ["__operator_only__"])
    extra["user_allowed_commands"] = []
    extra.setdefault("group_allow_admin_from", ["__operator_only__"])
    extra["group_user_allowed_commands"] = []
    extra.setdefault("split_multiline_messages", False)
    extra.setdefault("text_batch_delay_seconds", 3.0)

    eldercare = cfg.setdefault("eldercare", {})
    if not isinstance(eldercare, dict):
        eldercare = {}
        cfg["eldercare"] = eldercare
    eldercare["older_adult_channel"] = WEIXIN_PLATFORM
    eldercare["guardian_channels"] = list(guardian_channels)
    eldercare["default_language"] = "zh"
    eldercare["slash_commands"] = "disabled_except_hermes_help_whoami_floor"
    eldercare["risk_policy"] = "prompt"
    eldercare["reminders"] = "hermes_cronjob"
    return cfg


def _merged_platform_toolsets(raw: Any) -> dict[str, Any]:
    toolsets = copy.deepcopy(raw) if isinstance(raw, dict) else {}
    toolsets[WEIXIN_PLATFORM] = ["web", "cronjob", "memory", "session_search", "clarify"]
    return toolsets


def _diagnose(profile_dir: Path, config: dict[str, Any]) -> OperationResult:
    result = OperationResult(data={"profile_exists": profile_dir.is_dir()})
    if not profile_dir.is_dir():
        result.fail(f"Profile '{PROFILE_NAME}' does not exist at {profile_dir}. Run apply first.")
        return result

    platforms = config.get("platforms", {}) if isinstance(config, dict) else {}
    weixin = platforms.get(WEIXIN_PLATFORM, {}) if isinstance(platforms, dict) else {}
    if not isinstance(weixin, dict) or not weixin.get("enabled"):
        result.fail("Weixin platform is not enabled in the eldercare profile.")
    extra = weixin.get("extra", {}) if isinstance(weixin, dict) else {}
    token = weixin.get("token") if isinstance(weixin, dict) else None
    account_id = extra.get("account_id") if isinstance(extra, dict) else None
    if not token and not os.getenv("WEIXIN_TOKEN"):
        result.fail("Weixin token is missing. Run Hermes Weixin setup or set WEIXIN_TOKEN / platforms.weixin.token.")
    if not account_id and not os.getenv("WEIXIN_ACCOUNT_ID"):
        result.fail("Weixin account_id is missing. Run Hermes Weixin setup or set WEIXIN_ACCOUNT_ID / platforms.weixin.extra.account_id.")

    try:
        from gateway.platforms.weixin import check_weixin_requirements

        if not check_weixin_requirements():
            result.fail("Weixin Python requirements are missing: aiohttp and cryptography are required.")
    except Exception as exc:
        result.warn(f"Could not check Weixin runtime requirements: {exc}")

    eldercare = config.get("eldercare", {}) if isinstance(config, dict) else {}
    channels = eldercare.get("guardian_channels", DEFAULT_GUARDIAN_CHANNELS) if isinstance(eldercare, dict) else DEFAULT_GUARDIAN_CHANNELS
    configured_guardians = []
    if isinstance(platforms, dict):
        for channel in channels:
            block = platforms.get(channel)
            if isinstance(block, dict) and block.get("enabled"):
                configured_guardians.append(channel)
    result.data["guardian_channels_enabled"] = configured_guardians
    if not configured_guardians:
        result.warn("No non-Weixin guardian channel is enabled yet.")

    if not (profile_dir / "SOUL.md").is_file():
        result.fail("SOUL.md is missing from the eldercare profile.")
    return result


def _normalize_channels(channels: list[str] | None) -> tuple[str, ...]:
    raw = channels or list(DEFAULT_GUARDIAN_CHANNELS)
    normalized: list[str] = []
    for item in raw:
        value = str(item).strip().lower()
        if value and value != WEIXIN_PLATFORM and value not in normalized:
            normalized.append(value)
    return tuple(normalized or DEFAULT_GUARDIAN_CHANNELS)


def _profile_dir(name: str | None) -> Path:
    if not name or name == "default":
        return _default_hermes_home()
    try:
        from hermes_cli.profiles import get_profile_dir

        return get_profile_dir(name)
    except ImportError:
        return _default_hermes_home() / "profiles" / name


def _default_hermes_home() -> Path:
    try:
        from hermes_cli.profiles import _get_default_hermes_home

        return _get_default_hermes_home()
    except ImportError:
        return Path(os.getenv("HERMES_HOME") or Path.home() / ".hermes")


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _backup_file(path: Path) -> None:
    if not path.exists():
        return
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.name}.eldercare.{stamp}.bak")
    shutil.copy2(path, backup)
