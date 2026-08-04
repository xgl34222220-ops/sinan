from __future__ import annotations

import unittest

from app.web_console import admin_page, login_page, public_page


class WebConsoleV2Tests(unittest.TestCase):
    def test_public_page_renders_complete_dashboard(self) -> None:
        html = public_page()
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('id="metrics"', html)
        self.assertIn('id="lotteries"', html)
        self.assertIn("AI 任务", html)
        self.assertIn("toggleTheme", html)
        self.assertNotIn("__SERVER__", html)
        self.assertNotIn("__STYLE__", html)

    def test_admin_page_contains_all_operable_sections(self) -> None:
        html = admin_page()
        for marker in (
            'id="panel-overview"',
            'id="panel-ai"',
            'id="panel-records"',
            'id="panel-security"',
            'id="runBtn"',
            'id="saveAiBtn"',
            'id="testAiBtn"',
            'id="recordsList"',
            'class="mobile-nav"',
        ):
            self.assertIn(marker, html)
        self.assertIn("技术详情", html)
        self.assertIn("真实调用测试", html)
        self.assertNotIn("__TITLE__", html)

    def test_login_page_honors_configuration_state(self) -> None:
        configured = login_page(True)
        unconfigured = login_page(False)
        self.assertIn('id="loginForm"', configured)
        self.assertIn("安全登录到云端管理面板", configured)
        self.assertIn("disabled", unconfigured)


if __name__ == "__main__":
    unittest.main()
