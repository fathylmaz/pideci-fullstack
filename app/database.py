from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, Category, Product, Setting
from app.catalog import CATALOG, DEFAULT_V1_PRICES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SETTINGS = {
    "business_name": "Pideci",
    "hero_title": "DAYANILMAZ LEZZET ŞİMDİ KAPINDA",
    "hero_text": "Dilediğin lezzeti sepetine ekle, siparişini ver ve fırından çıktığı gibi kapına gelsin.",
    "hero_image_url": "/images/hero-v2.webp",
    "logo_url": "/images/logo.png",
    "about_title": "Bafra Pidesinin Tarihçesini Biliyor musunuz?",
    "about_text": "Bafra pidesi, Karadeniz'in köklü fırıncılık geleneğinden gelen sevilen bir lezzettir. Ustalıkla hazırlanan hamur ve iç malzeme, taş fırında bir araya gelir.",
    "about_image_url": "/images/pide-atolyesi.webp",
    "phone": "",
    "address": "",
    "opening_hours": "Çalışma saatleri için bizi arayın.",
    "instagram_url": "",
    "facebook_url": "",
    "delivery_areas": "",  # One neighborhood/district per line; empty means no zone restriction.
    "delivery_fee_cents": "0",
    "min_order_cents": "0",
    "ordering_enabled": "false",
}


def create_session_factory(db_url: str | None = None):
    db_url = db_url or os.environ.get("DATABASE_URL") or f"sqlite:///{ROOT / 'data' / 'pideci.db'}"
    if db_url.startswith("sqlite:///") and ":memory:" not in db_url:
        Path(db_url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False, "timeout": 20} if db_url.startswith("sqlite") else {},
        pool_pre_ping=True,
    )
    if db_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(connection, _record):
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=20000")
            cursor.close()
    # Simple, non-destructive SQLite migration for existing v1 installations.
    if db_url.startswith("sqlite"):
        with engine.begin() as conn:
            tables = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")).all()
            if tables:
                cols = {row[1] for row in conn.execute(text("PRAGMA table_info(products)"))}
                if "badge" not in cols:
                    conn.execute(text("ALTER TABLE products ADD COLUMN badge VARCHAR(24) NOT NULL DEFAULT ''"))
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def seed_database(factory):
    with factory() as db:
        for key, value in DEFAULT_SETTINGS.items():
            if db.get(Setting, key) is None:
                db.add(Setting(key=key, value=value))
        if not db.scalars(select(Category).limit(1)).first():
            categories = [
                Category(name="Pide", position=1),
                Category(name="Lahmacun", position=2),
                Category(name="Çorba", position=3),
                Category(name="Tatlı", position=4),
            ]
            db.add_all(categories)
            db.flush()
            examples = [
                ("Kuşbaşılı Kaşarlı Pide", categories[0], 10999, 11999, "/images/kuşbaşilikaşarli.png", True, ""),
                ("Lahmacun", categories[1], 4999, 5499, "/images/lahmacun.webp", True, ""),
                ("Mercimek Çorbası", categories[2], 5499, 5999, "/images/çorba.png", True, ""),
                ("Künefe", categories[3], 8999, 9999, "/images/künefe.png", True, ""),
                ("Cantık", categories[0], 4000, None, "/images/cantik.png", False, "200 gr"),
                ("Fındık Lahmacun", categories[1], 2500, None, "/images/findiklahmacun.png", False, "110 gr"),
                ("Special Pide", categories[0], 12000, None, "/images/kasarli.webp", False, "250 gr"),
            ]
            for pos, (name, category, price, old_price, photo, featured, serving) in enumerate(examples, 1):
                db.add(Product(name=name, category_id=category.id, price_cents=price,
                               old_price_cents=old_price, image_url=photo,
                               is_featured=featured, serving_info=serving, position=pos))
        # Import once: NEVER reset the catalog/price/image after an admin edits it.
        if db.get(Setting, "catalog_v2_seeded") is None:
            categories_by_name = {c.name: c for c in db.scalars(select(Category)).all()}
            for index, name in enumerate(("Pide", "Lahmacun", "Çorba", "Tatlı", "İçecek", "Yan Ürünler"), 1):
                if name not in categories_by_name:
                    cat = Category(name=name, position=index)
                    db.add(cat)
                    db.flush()
                    categories_by_name[name] = cat
            existing = {p.name: p for p in db.scalars(select(Product)).all()}
            # Original sample 'Special Pide' is explicitly a placeholder product.
            demo = existing.get("Special Pide")
            if demo and demo.price_cents == 12000 and "Kaşarlı Pide" not in existing:
                demo.name = "Kaşarlı Pide"
                existing[demo.name] = demo
            for position, (name, category_name, price, description, image, badge, featured, old_price) in enumerate(CATALOG, 1):
                url = f"/images/v2/{image}.webp"
                price_cents = price * 100
                old_cents = old_price * 100 if old_price else None
                item = existing.get(name)
                if item is None:
                    item = Product(name=name, category_id=categories_by_name[category_name].id,
                                   price_cents=price_cents, old_price_cents=old_cents,
                                   description=description, image_url=url, badge=badge,
                                   is_featured=featured, position=position)
                    db.add(item)
                elif name in DEFAULT_V1_PRICES or (name == "Kaşarlı Pide" and item is demo):
                    old_default = DEFAULT_V1_PRICES.get(name, 12000)
                    # Never replace business-defined prices or uploaded imagery.
                    if item.price_cents == old_default:
                        item.price_cents = price_cents
                        item.old_price_cents = old_cents
                    if item.image_url.startswith("/images/"):
                        item.image_url = url
                    if not item.description:
                        item.description = description
                    item.badge = badge
                    item.is_featured = featured
                    item.position = position
            hero_setting = db.get(Setting, "hero_image_url")
            if hero_setting and hero_setting.value in {"/images/arkaplan1.webp", "/images/arkaplan1.jpg"}:
                hero_setting.value = "/images/hero-v2.webp"
            about_setting = db.get(Setting, "about_image_url")
            if about_setting and about_setting.value == "/images/bafra.jpg":
                about_setting.value = "/images/pide-atolyesi.webp"
            db.add(Setting(key="catalog_v2_seeded", value="true"))
        db.commit()


def setting_values(db: Session) -> dict[str, str]:
    return {x.key: x.value for x in db.scalars(select(Setting)).all()}
