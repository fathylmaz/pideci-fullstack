"""Verify the Windows-safe database backup lifecycle and archive contents."""
from __future__ import annotations

import sqlite3
import zipfile
from pathlib import Path

from scripts import backup_database


def test_backup_includes_sqlite_and_images(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    database = data / "pideci.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE sample (name TEXT)")
        connection.execute("INSERT INTO sample (name) VALUES ('test-product')")
    uploads = data / "uploads"
    uploads.mkdir()
    (uploads / "product.webp").write_bytes(b"RIFFTESTWEBP")
    (uploads / "ignored.txt").write_bytes(b"do-not-archive")
    backups = tmp_path / "backups"

    monkeypatch.setattr(backup_database, "DATABASE", database)
    monkeypatch.setattr(backup_database, "UPLOADS", uploads)
    monkeypatch.setattr(backup_database, "BACKUPS", backups)
    backup_database.main()

    files = list(backups.glob("pideci-yedek-*.zip"))
    assert len(files) == 1
    with zipfile.ZipFile(files[0]) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {"pideci.db", "uploads/product.webp", "INFO.json"}
        snapshot = tmp_path / "restored.db"
        snapshot.write_bytes(archive.read("pideci.db"))
    with sqlite3.connect(snapshot) as restored:
        assert restored.execute("SELECT name FROM sample").fetchone() == ("test-product",)
    # Check that the source DB can still be modified after the backup.
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO sample (name) VALUES ('still-openable')")
