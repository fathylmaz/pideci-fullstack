"""Create a transactionally consistent SQLite backup plus uploaded images."""
from __future__ import annotations

import json
from contextlib import closing
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "data" / "pideci.db"
UPLOADS = ROOT / "data" / "uploads"
BACKUPS = ROOT / "backups"


def main() -> None:
    if not DATABASE.is_file():
        raise SystemExit("Veritabanı bulunamadı. Önce uygulamayı kurup başlatın.")
    BACKUPS.mkdir(exist_ok=True)
    name = "pideci-yedek-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".zip"
    destination = BACKUPS / name
    with tempfile.TemporaryDirectory() as temp:
        snapshot = Path(temp) / "pideci.db"
        # sqlite3.Connection used as a context manager does NOT close the
        # connection. On Windows, the open file handle prevents the temporary
        # directory from being removed (WinError 32). `closing` does close it.
        with closing(sqlite3.connect(str(DATABASE))) as source:
            with closing(sqlite3.connect(str(snapshot))) as target:
                source.backup(target)
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, "pideci.db")
            if UPLOADS.is_dir():
                for image in UPLOADS.iterdir():
                    if image.is_file() and image.suffix.lower() == ".webp":
                        archive.write(image, "uploads/" + image.name)
            archive.writestr("INFO.json", json.dumps({"created_at_utc": datetime.now(timezone.utc).isoformat(),
                                                      "format": "Pideci SQLite + uploaded images"}, indent=2))
    print("Yedek oluşturuldu:", destination)
    print("UYARI: Bu dosya müşteri kişisel bilgilerini içerir; güvenli bir konumda saklayın.")


if __name__ == "__main__":
    main()
