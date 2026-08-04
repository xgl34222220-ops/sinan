from __future__ import annotations

import unittest

from app.web_console import admin_page, login_page, public_page


class WebConsoleRenderTests(unittest.TestCase):
    def test_public_page_renders(self) -> None:
        value = public_page()
        self.assertIn("天机云端", value)
        self.assertIn("/v1/public/overview", value)

    def test_login_pages_render(self) -> None:
        configured = login_page(True)
        unconfigured = login_page(False)
        self.assertIn("进入控制台", configured)
        self.assertIn("disabled", unconfigured)

    def test_admin_page_renders(self) -> None:
        value = admin_page()
        self.assertIn("天机控制台", value)
        self.assertIn("/admin/api/ai", value)
        self.assertIn("/admin/api/state", value)


if __name__ == "__main__":
    unittest.main()
