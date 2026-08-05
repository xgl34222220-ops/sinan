from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from app.bootstrap import app


class BootstrapHealthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_liveness_endpoint_and_security_headers(self) -> None:
        response = self.client.get("/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertTrue(response.headers.get("x-request-id"))

    def test_docs_are_disabled_by_default(self) -> None:
        response = self.client.get("/docs")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
