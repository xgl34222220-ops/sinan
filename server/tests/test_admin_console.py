from __future__ import annotations

from dataclasses import replace
import os
import tempfile
import unittest

from app import admin_auth, runtime_config


class AdminAuthTests(unittest.TestCase):
    def test_password_hash_round_trip(self) -> None:
        encoded = admin_auth.hash_password("correct-horse-42")
        self.assertTrue(admin_auth.verify_password_hash("correct-horse-42", encoded))
        self.assertFalse(admin_auth.verify_password_hash("wrong-password", encoded))

    def test_session_round_trip(self) -> None:
        token = admin_auth.create_session()
        self.assertTrue(admin_auth.verify_session(token))
        self.assertFalse(admin_auth.verify_session(token + "x"))


class RuntimeConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_settings = runtime_config.settings
        runtime_config.settings = replace(
            self.original_settings,
            database_path=os.path.join(self.temp_dir.name, "tianji.db"),
            ai_endpoint="https://env.example/v1/chat/completions",
            ai_model="env-model",
            ai_api_key="env-key",
        )

    def tearDown(self) -> None:
        runtime_config.settings = self.original_settings
        self.temp_dir.cleanup()

    def test_runtime_config_overrides_environment_and_keeps_key(self) -> None:
        saved = runtime_config.save_ai_config(
            enabled=True,
            endpoint="https://api.example.com/v1/chat/completions/",
            model="model-a",
            api_key="secret-a",
            timeout_seconds=90,
        )
        self.assertEqual(saved.endpoint, "https://api.example.com/v1/chat/completions")
        self.assertTrue(saved.complete)

        updated = runtime_config.save_ai_config(
            enabled=True,
            endpoint="https://api.example.com/v1/chat/completions",
            model="model-b",
            api_key=None,
            timeout_seconds=120,
        )
        self.assertEqual(updated.model, "model-b")
        self.assertEqual(updated.api_key, "secret-a")
        self.assertEqual(runtime_config.load_ai_config().api_key, "secret-a")

    def test_rejects_non_https_endpoint(self) -> None:
        with self.assertRaises(ValueError):
            runtime_config.save_ai_config(
                enabled=True,
                endpoint="http://example.com/v1/chat/completions",
                model="model-a",
                api_key="secret",
                timeout_seconds=120,
            )

    def test_multiple_profiles_can_be_saved_switched_and_disabled(self) -> None:
        runtime_config.settings = replace(
            runtime_config.settings,
            ai_endpoint="",
            ai_model="",
            ai_api_key="",
        )
        runtime_config.clear_runtime_ai_config()

        first = runtime_config.save_ai_profile(
            profile_id=None,
            name="主力模型",
            endpoint="https://one.example/v1/chat/completions",
            model="model-one",
            api_key="key-one",
            timeout_seconds=90,
            activate=True,
        )
        second = runtime_config.save_ai_profile(
            profile_id=None,
            name="备用模型",
            endpoint="https://two.example/v1/responses",
            model="model-two",
            api_key="key-two",
            timeout_seconds=120,
            activate=False,
        )

        registry = runtime_config.load_ai_registry()
        self.assertEqual(len(registry.profiles), 2)
        self.assertEqual(registry.active_profile_id, first.profile_id)

        runtime_config.activate_ai_profile(second.profile_id)
        runtime_config.set_ai_auto_predict(True)
        active = runtime_config.load_ai_config()
        self.assertEqual(active.model, "model-two")
        self.assertTrue(active.complete)

        runtime_config.set_ai_auto_predict(False)
        self.assertFalse(runtime_config.load_ai_config().complete)
        self.assertTrue(runtime_config.load_ai_config().ready)

        remaining = runtime_config.delete_ai_profile(second.profile_id)
        self.assertEqual(len(remaining.profiles), 1)
        self.assertEqual(remaining.active_profile_id, first.profile_id)


if __name__ == "__main__":
    unittest.main()
