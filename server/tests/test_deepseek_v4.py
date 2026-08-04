from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ai import (
    AiConnectionResult,
    _deepseek_fast_mode,
    _is_official_deepseek,
    test_connection,
)
from app.runtime_config import RuntimeAiConfig


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class _Client:
    instances: list["_Client"] = []

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.posts: list[dict[str, object]] = []
        self.responses = [
            _Response({"choices": [{"message": {"content": None, "reasoning_content": "thinking"}}]}),
            _Response({"choices": [{"message": {"content": "OK"}}]}),
        ]
        self.__class__.instances.append(self)

    def __enter__(self) -> "_Client":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def post(self, endpoint: str, *, headers: dict[str, str], json: dict[str, object]) -> _Response:
        self.posts.append(json)
        return self.responses.pop(0)


class DeepSeekV4Tests(unittest.TestCase):
    def setUp(self) -> None:
        _Client.instances.clear()
        self.config = RuntimeAiConfig(
            enabled=True,
            endpoint="https://api.deepseek.com/chat/completions",
            model="deepseek-v4-pro",
            api_key="sk-test-key",
            timeout_seconds=120,
            profile_id="deepseek",
            profile_name="DeepSeek",
        )

    def test_detects_official_deepseek(self) -> None:
        self.assertTrue(_is_official_deepseek(self.config))
        compatible = RuntimeAiConfig(
            enabled=True,
            endpoint="https://example.com/v1/chat/completions",
            model="deepseek-v4-pro",
            api_key="key",
            timeout_seconds=120,
        )
        self.assertFalse(_is_official_deepseek(compatible))

    def test_fast_mode_disables_thinking_and_expands_budget(self) -> None:
        body = _deepseek_fast_mode({"model": "deepseek-v4-pro", "max_tokens": 16}, max_tokens=256)
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["max_tokens"], 256)

    @patch("app.ai.discover_models")
    @patch("app.ai.httpx.Client", _Client)
    def test_connection_retries_empty_final_content(self, discover_mock: object) -> None:
        discover_mock.return_value = AiConnectionResult(10, "ok", ["deepseek-v4-pro"])
        result = test_connection(self.config)

        self.assertIn("调用成功", result.message)
        client = _Client.instances[-1]
        self.assertEqual(len(client.posts), 2)
        self.assertEqual(client.posts[0]["thinking"], {"type": "disabled"})
        self.assertEqual(client.posts[0]["max_tokens"], 64)
        self.assertEqual(client.posts[1]["max_tokens"], 256)


if __name__ == "__main__":
    unittest.main()
