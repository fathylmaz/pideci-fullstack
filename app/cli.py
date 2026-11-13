"""Administrator provisioning via the command line; no public registration."""
from __future__ import annotations

import argparse
import getpass
import re

from sqlalchemy import select
from app.database import create_session_factory, seed_database
from app.models import AdminUser
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Pideci yönetici hesabı")
    parser.add_argument("action", choices=["create-admin", "reset-password"])
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,64}", args.username):
        parser.error("Kullanıcı adı 3-64 karakter olmalıdır (harf, rakam, _, -, .).")
    factory = create_session_factory()
    seed_database(factory)
    with factory() as db:
        existing = db.scalar(select(AdminUser).where(AdminUser.username == args.username))
        if args.action == "create-admin" and existing:
            parser.error("Bu kullanıcı zaten var. Şifre için reset-password komutunu kullanın.")
        if args.action == "reset-password" and not existing:
            parser.error("Bu kullanıcı bulunamadı.")
        password = getpass.getpass("Yönetici şifresi (en az 12 karakter): ")
        if len(password) < 12 or len(password) > 128:
            parser.error("Şifre 12-128 karakter olmalıdır.")
        confirm = getpass.getpass("Şifre (tekrar): ")
        if password != confirm:
            parser.error("Şifreler eşleşmiyor.")
        if existing:
            existing.password_hash = hash_password(password)
            from app.models import AdminSession
            from sqlalchemy import delete
            db.execute(delete(AdminSession).where(AdminSession.admin_id == existing.id))
        else:
            db.add(AdminUser(username=args.username, password_hash=hash_password(password)))
        db.commit()
    print(f"Yönetici hesabı hazır: {args.username}")


if __name__ == "__main__":
    main()
