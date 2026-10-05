import sqlite3
import tempfile
import unittest
from pathlib import Path

from chimera_exam_admin.server_db import chimera_server_db
from chimera_exam_admin.utils import matches_pdf_filter


class AdminPdfTrackingTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_directory.name) / "legacy.db"
        connection = sqlite3.connect(self.db_path)
        connection.execute(
            """CREATE TABLE sessions (
                id INTEGER PRIMARY KEY,
                uid TEXT NOT NULL,
                username TEXT NOT NULL,
                set_name TEXT NOT NULL,
                set_type TEXT NOT NULL,
                device_name TEXT NOT NULL,
                start_dt TEXT NOT NULL,
                finalised INTEGER NOT NULL
            )"""
        )
        connection.execute(
            """INSERT INTO sessions
               (uid, username, set_name, set_type, device_name, start_dt, finalised)
               VALUES ('session-1', 'candidate', 'set', 'RR', 'device',
                       '2026-09-28T14:00:00', 0)"""
        )
        connection.commit()
        connection.close()
        self.database = chimera_server_db(
            self.db_path, test_on_start=False, clean_start=False
        )

    def tearDown(self):
        self.database.connection.close()
        self.temp_directory.cleanup()

    def test_legacy_database_is_migrated_and_status_is_exposed(self):
        columns = {
            row[1]: row
            for row in self.database.connection.execute("PRAGMA table_info(sessions)")
        }
        self.assertEqual(columns["pdf"][3], 1)
        self.assertEqual(columns["pdf"][4], "0")
        self.assertIn("pdf_dt", columns)
        self.assertEqual(columns["pdf_dt"][2], "TIMESTAMP")
        self.assertEqual(columns["pdf_dt"][3], 0)
        self.assertIn("final_dt", columns)
        self.assertEqual(columns["final_dt"][2], "TIMESTAMP")
        self.assertEqual(columns["final_dt"][3], 0)

        session = self.database.query_all_sessions()[0]
        self.assertIsNone(session["final_dt"])
        self.assertFalse(session["pdf"])
        self.assertIsNone(session["pdf_dt"])

        self.database.mark_pdf_created("session-1", "2026-09-28T14:30:00")
        session = self.database.get_session_by_uid("session-1")
        self.assertTrue(session.pdf)
        self.assertEqual(session.pdf_dt, "2026-09-28T14:30:00")

    def test_tracking_fields_are_editable(self):
        self.database.update_session_tracking(
            "session-1",
            "2026-09-28T14:15:00",
            True,
            "2026-09-28T14:30:00",
        )

        session = self.database.get_session_by_uid("session-1")
        self.assertEqual(session.final_dt, "2026-09-28T14:15:00")
        self.assertTrue(session.pdf)
        self.assertEqual(session.pdf_dt, "2026-09-28T14:30:00")

    def test_pdf_filter_matches_yes_no_and_all(self):
        created = {"pdf": True}
        missing = {"pdf": False}

        self.assertTrue(matches_pdf_filter(created, "yes"))
        self.assertFalse(matches_pdf_filter(missing, "yes"))
        self.assertFalse(matches_pdf_filter(created, "no"))
        self.assertTrue(matches_pdf_filter(missing, "no"))
        self.assertTrue(matches_pdf_filter(created, "all"))
        self.assertTrue(matches_pdf_filter(missing, "all"))


if __name__ == "__main__":
    unittest.main()
