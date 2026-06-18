# hermes-eldercare

`hermes-eldercare` is a Weixin-first eldercare profile and plugin for Hermes.

Hermes remains the runtime agent. This project adds a dedicated `hermes-eldercare`
profile, Chinese senior-friendly prompt policy, quiet Weixin display defaults,
and a small setup/diagnostic CLI.

## What It Does

- Uses Hermes' existing Weixin gateway for the older adult chat channel.
- Creates or updates a dedicated `hermes-eldercare` Hermes profile.
- Defaults the assistant to Chinese, short answers, and low technical detail.
- Guides reminder creation through Hermes' existing `cronjob` / cron support.
- Prompts the assistant to handle safety, medical, fraud, banking, and verification-code risks conservatively.
- Keeps normal chats private by default; guardian/family notification is only for high-risk situations or explicit user intent.
- Keeps Weixin quiet: no streaming, no tool-progress chatter, no runtime footer.

## Install For Development

Recommended for development:

```bash
pip install -e .
```

Use either pip installation or Hermes' directory-plugin install flow, not both.
Using both can register the hooks twice.

Preview profile/config changes:

```bash
hermes-eldercare apply --dry-run
```

Apply the profile/config:

```bash
hermes-eldercare apply
```

Enable the plugin and run Hermes with the eldercare profile:

```bash
hermes plugins enable hermes-eldercare
hermes -p hermes-eldercare gateway setup
```

Choose Weixin in `gateway setup`, scan the QR code, and confirm login in
Weixin. Hermes saves the Weixin credentials automatically; do not edit
`WEIXIN_TOKEN` or `WEIXIN_ACCOUNT_ID` by hand.

After Weixin is connected:

```bash
hermes -p hermes-eldercare gateway run
```

`apply` writes real profile/config files by default. It only targets the
`hermes-eldercare` profile.

## Commands

```bash
hermes-eldercare apply       # create/update the profile
hermes-eldercare doctor      # check profile, Weixin config, and guardian channels
hermes-eldercare init        # alias for apply
```

When loaded as a Hermes plugin, equivalent commands are available under:

```bash
hermes eldercare apply
hermes eldercare doctor
```

## Defaults

| Setting | Default |
| --- | --- |
| Plugin name | `hermes-eldercare` |
| Profile name | `hermes-eldercare` |
| Older adult channel | Weixin |
| Guardian channels | configured non-Weixin gateway channels |
| Language | Chinese |
| Reminders | Hermes `cronjob` / cron |
| Slash commands | not used for the product mode |

## Notes

This project does not implement a new Weixin adapter. Hermes already provides
Weixin support. `hermes-eldercare` configures and constrains Hermes for this
use case.

Voice input, dialect recognition, medical diagnosis, banking/payment workflows,
and a guardian dashboard are out of scope for the first version.

## Test

Requires Python 3.10+.

```bash
python3.10 -m py_compile __init__.py hermes_eldercare/*.py tests/test_eldercare_installer.py
PYTHONPATH=. python3.10 tests/test_eldercare_installer.py
```
