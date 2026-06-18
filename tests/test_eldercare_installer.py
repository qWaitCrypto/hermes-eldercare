from __future__ import annotations

import os
import unittest
from pathlib import Path

import yaml

from hermes_eldercare.installer import apply_profile, doctor_profile
from hermes_eldercare.plugin import _pre_llm_call, _transform_llm_output
from hermes_eldercare.style import clean_response


class EldercareInstallerTests(unittest.TestCase):
    def setUp(self):
        self._old_home = os.environ.get("HOME")
        self._old_hermes_home = os.environ.get("HERMES_HOME")

    def tearDown(self):
        tmp = getattr(self, "tmp", None)
        if tmp is not None:
            tmp.cleanup()
        if self._old_home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._old_home
        if self._old_hermes_home is None:
            os.environ.pop("HERMES_HOME", None)
        else:
            os.environ["HERMES_HOME"] = self._old_hermes_home

    def _use_tmp_home(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        os.environ["HOME"] = str(root)
        os.environ.pop("HERMES_HOME", None)
        return root

    def test_clean_response_removes_ai_preface(self):
        self.assertEqual(clean_response("作为AI语言模型，我可以帮您。"), "我可以帮您。")

    def test_hooks_return_expected_shapes(self):
        ctx = _pre_llm_call(platform="weixin")
        self.assertIsInstance(ctx, dict)
        self.assertIn("Chinese", ctx["context"])
        self.assertIsNone(_pre_llm_call(platform="discord"))
        self.assertEqual(_transform_llm_output(response_text="作为AI语言模型，我可以帮您。"), "我可以帮您。")

    def test_apply_profile_writes_profile_config(self):
        tmp_path = self._use_tmp_home()
        default_home = tmp_path / ".hermes"
        default_home.mkdir()
        (default_home / "config.yaml").write_text(
            yaml.safe_dump({"model": {"provider": "test", "default": "model"}}),
            encoding="utf-8",
        )
        (default_home / ".env").write_text("OPENAI_API_KEY=test\n", encoding="utf-8")

        result = apply_profile(guardian_channels=["telegram"])

        self.assertTrue(result.changed)
        profile = default_home / "profiles" / "hermes-eldercare"
        config = yaml.safe_load((profile / "config.yaml").read_text(encoding="utf-8"))
        self.assertEqual(config["plugins"]["enabled"], ["hermes-eldercare"])
        self.assertEqual(config["display"]["language"], "zh")
        self.assertTrue(config["platforms"]["weixin"]["enabled"])
        self.assertEqual(config["platforms"]["weixin"]["extra"]["user_allowed_commands"], [])
        self.assertEqual(config["eldercare"]["guardian_channels"], ["telegram"])
        self.assertIn("中文助手", (profile / "SOUL.md").read_text(encoding="utf-8"))
        self.assertIn("gateway setup", result.to_human())
        self.assertIn("微信尚未连接", result.to_human())

    def test_apply_profile_dry_run_does_not_write(self):
        tmp_path = self._use_tmp_home()

        result = apply_profile(dry_run=True)

        self.assertTrue(result.ok)
        self.assertIn("Would create Hermes profile", result.to_human())
        self.assertFalse((tmp_path / ".hermes" / "profiles" / "hermes-eldercare").exists())

    def test_doctor_reports_missing_profile(self):
        self._use_tmp_home()

        result = doctor_profile()

        self.assertFalse(result.ok)
        self.assertIn("does not exist", result.to_human())


if __name__ == "__main__":
    unittest.main()
