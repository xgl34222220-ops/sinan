from __future__ import annotations

import unittest

from app.records_ui import enhance_admin_html
from app.web_console import admin_page


class RecordsUiTests(unittest.TestCase):
    def test_archive_workspace_is_injected(self) -> None:
        html = enhance_admin_html(admin_page())
        for marker in (
            "workspace.id='recordsV2'",
            'data-source="ai"',
            'data-source="native"',
            'data-source="all"',
            'data-status="pending"',
            'id="recordsLotteryFilter"',
            '云端 AI 档案',
            '本机云端档案',
            '查看分析说明',
        ):
            self.assertIn(marker, html)

    def test_archive_workspace_hides_legacy_list(self) -> None:
        html = enhance_admin_html(admin_page())
        self.assertIn('legacy-records-card', html)
        self.assertIn('/admin/api/state', html)
        self.assertEqual(html.count('</body>'), 1)


if __name__ == "__main__":
    unittest.main()
