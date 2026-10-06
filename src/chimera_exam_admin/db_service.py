"""Application-level database access layer.

This keeps the NiceGUI UI code focused on rendering and interaction while the
SQLite access stays in the database layer module.
"""

from __future__ import annotations

from pathlib import Path

from .server_db import ChimeraServerDB


def create_database(db_path: str | Path, *, test_on_start: bool = False, clean_start: bool = False) -> ChimeraServerDB:
    """Create a connected database instance for the app."""
    return ChimeraServerDB(db_path, test_on_start=test_on_start, clean_start=clean_start)
