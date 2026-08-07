from __future__ import annotations

import unittest

from app.console_v3 import enhance_console_html


class V630FinalPolishTests(unittest.TestCase):
    def test_console_installs_final_density_tokens(self) -> None:
        html = enhance_console_html("<html><head></head><body></body></html>")
        self.assertIn("Tianji v6.3 final polish", html)
        self.assertIn("--v63-card-radius:18px", html)
        self.assertIn(".v620-latency span", html)
        self.assertIn("font-size:11px", html)


if __name__ == "__main__":
    unittest.main()
