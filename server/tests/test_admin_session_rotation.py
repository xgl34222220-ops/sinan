from __future__ import annotations

import os
import unittest

from app.admin_auth import change_admin_password, create_session, verify_session
from app.config import settings


class AdminSessionRotationTests(unittest.TestCase):
    def tearDown(self) -> None:
        try:
            os.remove(os.path.join(settings.data_dir, "admin-password.hash"))
        except FileNotFoundError:
            pass

    def test_password_change_invalidates_existing_sessions(self) -> None:
        change_admin_password("first-password-123")
        session = create_session()
        self.assertTrue(verify_session(session))
        change_admin_password("second-password-456")
        self.assertFalse(verify_session(session))


if __name__ == "__main__":
    unittest.main()
