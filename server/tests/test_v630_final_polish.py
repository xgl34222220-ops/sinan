from __future__ import annotations

import unittest

from app.console_v3 import enhance_console_html


class V680FinalPolishTests(unittest.TestCase):
    def test_console_installs_consolidated_latency_layer(self) -> None:
        html = enhance_console_html("<html><head></head><body></body></html>")
        self.assertIn("Tianji v6.8 consolidated experience layer", html)
        self.assertIn("--v68-card-radius:18px", html)
        self.assertIn("v68-pipeline", html)
        self.assertIn("P50", html)
        self.assertIn("P95", html)
        self.assertIn("font-size:11px", html)


if __name__ == "__main__":
    unittest.main()
