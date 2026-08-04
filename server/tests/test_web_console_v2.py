from __future__ import annotations

import unittest

from app.web_console import admin_page, login_page, public_page


class WebConsoleV2Tests(unittest.TestCase):
    def test_public_page_renders_complete_dashboard(self) -> None:
        html = public_page()
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('id="metrics"', html)
        self.assertIn('id="lotteries"', html)
        self.assertIn("AI 自动任务", html)
        self.assertIn("toggleTheme", html)

    def test_admin_page_contains_quick_model_switcher(self) -> None:
        html = admin_page()
        for marker in (
            'id="panel-overview"',
            'id="panel-ai"',
            'id="panel-records"',
            'id="panel-security"',
            'id="runBtn"',
            'id="aiAutoEnabled"',
            'id="quickCurrent"',
            'data-quick-model="deepseek-v4-flash"',
            'data-quick-model="deepseek-v4-pro"',
            'id="readQuickModelsBtn"',
            'id="manageDetails"',
            'id="saveAiBtn"',
            'id="recordsList"',
            'class="mobile-nav"',
        ):
            self.assertIn(marker, html)
        self.assertIn("同一个 Key 支持的模型可直接一键切换", html)
        self.assertIn("切换只修改当前接口使用的模型名", html)
        self.assertIn("switchModel", html)
        self.assertIn("运行诊断", html)
        self.assertNotIn("技术详情", html)

    def test_login_page_honors_configuration_state(self) -> None:
        configured = login_page(True)
        unconfigured = login_page(False)
        self.assertIn('id="loginForm"', configured)
        self.assertIn("安全登录云端工作台", configured)
        self.assertIn("disabled", unconfigured)


if __name__ == "__main__":
    unittest.main()
