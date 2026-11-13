from __future__ import annotations

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select

from app.main import create_app
from app.models import AdminUser
from app.security import hash_password


@pytest.fixture
def client(tmp_path):
    app = create_app(db_url=f"sqlite:///{tmp_path / 'test.db'}", upload_dir=tmp_path / "uploads")
    with app.state.factory() as db:
        db.add(AdminUser(username="admin", password_hash=hash_password("a-long-test-password123")))
        db.commit()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_client(client):
    response = client.post("/api/admin/login", json={"username": "admin", "password": "a-long-test-password123"})
    assert response.status_code == 200, response.text
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    return client


def valid_product(**overrides):
    product = {"name": "Yeni Kaşarlı Pide", "category_id": 1, "description": "Taş fırından",
               "price_cents": 15850, "old_price_cents": 16900,
               "image_url": "/images/cantik.png", "serving_info": "260 gr",
               "position": 3, "is_active": True, "in_stock": True, "is_featured": True}
    product.update(overrides)
    return product


def activate_ordering(c):
    settings = c.get("/api/admin/settings").json()
    settings.update(phone="0555 555 55 55", address="Merkez Mahallesi Ornek Sokak No 1 Tokat", ordering_enabled=True)
    response = c.put("/api/admin/settings", json=settings)
    assert response.status_code == 200, response.text


def valid_order(product_id=1):
    return {"customer_name": "Ayşe Yılmaz", "phone": "0555 555 55 55",
            "address": "Merkez Mahallesi, Örnek Sokak No: 12 Tokat",
            "items": [{"product_id": product_id, "quantity": 2}], "note": "Az acılı"}


def test_public_pages_and_seed(client):
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}
    products = client.get("/api/public/products").json()
    assert len(products) == 45
    assert products[0]["price_cents"] == 31000
    assert len(client.get("/api/public/categories").json()) == 6
    assert client.get("/api/public/settings").json()["ordering_enabled"] is False
    for product in products:
        if product["image_url"]:
            assert client.get(product["image_url"]).status_code == 200
    assert client.get("/api/public/settings").json()["hero_title"] == "DAYANILMAZ LEZZET ŞİMDİ KAPINDA"


def test_admin_session_and_csrf(client, admin_client):
    assert client.get("/api/admin/me").status_code == 200
    admin_client.headers.pop("X-CSRF-Token")
    assert admin_client.post("/api/admin/products", json=valid_product()).status_code == 403
    me = admin_client.get("/api/admin/me").json()
    admin_client.headers["X-CSRF-Token"] = me["csrf_token"]
    assert admin_client.post("/api/admin/logout").status_code == 200
    assert client.get("/api/admin/me").status_code == 401


def test_wrong_login_and_unauthorized(client):
    assert client.get("/api/admin/products").status_code == 401
    assert client.post("/api/admin/login", json={"username": "admin", "password": "wrong"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "admin", "password": "a-long-test-password123"}, headers={"Origin":"https://evil.example"}).status_code == 403


def test_product_crud_and_archive(admin_client):
    c = admin_client
    created = c.post("/api/admin/products", json=valid_product())
    assert created.status_code == 201, created.text
    product_id = created.json()["id"]
    assert len(c.get("/api/public/products").json()) == 46
    update = c.put(f"/api/admin/products/{product_id}", json=valid_product(price_cents=17375, old_price_cents=19000, in_stock=False))
    assert update.status_code == 200, update.text
    assert update.json()["price_cents"] == 17375
    assert not update.json()["in_stock"]
    assert c.delete(f"/api/admin/products/{product_id}").status_code == 200
    assert len(c.get("/api/public/products").json()) == 45
    assert any(p["id"] == product_id and not p["is_active"] for p in c.get("/api/admin/products").json())
    assert c.post("/api/admin/products", json=valid_product(image_url="https://external.site/malicious.jpg")).status_code == 422
    assert c.post("/api/admin/products", json=valid_product(badge="<script>evil</script>")).status_code == 422


def test_order_uses_server_prices_and_status(admin_client):
    c = admin_client
    activate_ordering(c)
    supplied = {**valid_order(), "total_cents": 1, "items": [{"product_id": 1, "quantity": 2, "price_cents": 1}]}
    response = c.post("/api/public/orders", json=supplied)
    assert response.status_code == 201, response.text
    assert response.json()["total_cents"] == 2 * 43500
    orders = c.get("/api/admin/orders").json()
    assert len(orders) == 1
    assert orders[0]["items"][0]["unit_price_cents"] == 43500
    id_ = orders[0]["id"]
    assert c.patch(f"/api/admin/orders/{id_}", json={"status": "delivered"}).status_code == 409
    for status in ["confirmed", "preparing", "on_the_way", "delivered"]:
        r = c.patch(f"/api/admin/orders/{id_}", json={"status": status})
        assert r.status_code == 200, r.text
    assert c.patch(f"/api/admin/orders/{id_}", json={"status": "new"}).status_code == 409
    assert c.get("/api/admin/dashboard").json()["delivered_revenue_cents"] == 2 * 43500


def test_order_rejects_out_of_stock_and_disabled(admin_client):
    c = admin_client
    activate_ordering(c)
    product = c.get("/api/admin/products").json()[0]
    c.put(f"/api/admin/products/{product['id']}", json={**product, "in_stock": False})
    assert c.post("/api/public/orders", json=valid_order(product["id"])).status_code == 409
    settings = c.get("/api/admin/settings").json()
    settings.update(ordering_enabled=False)
    assert c.put("/api/admin/settings", json=settings).status_code == 200
    assert c.post("/api/public/orders", json=valid_order(2)).status_code == 409


def test_delivery_and_minimum_applied_on_server(admin_client):
    c = admin_client
    activate_ordering(c)
    settings = c.get("/api/admin/settings").json()
    settings.update(delivery_fee_cents=1750, min_order_cents=90000)
    c.put("/api/admin/settings", json=settings)
    assert c.post("/api/public/orders", json=valid_order()).status_code == 422
    payload = valid_order()
    payload["items"][0]["quantity"] = 3
    response = c.post("/api/public/orders", json=payload)
    assert response.status_code == 201, response.text
    assert response.json()["total_cents"] == 43500 * 3 + 1750


def test_category_management(admin_client):
    c = admin_client
    created = c.post("/api/admin/categories", json={"name": "İçecekler", "position": 8, "is_active": True})
    assert created.status_code == 201
    new_id = created.json()["id"]
    assert c.post("/api/admin/categories", json={"name": "İçecekler", "position": 9}).status_code == 409
    assert c.put(f"/api/admin/categories/{new_id}", json={"name": "Soğuk İçecekler", "position": 7, "is_active": True}).status_code == 200
    assert c.delete("/api/admin/categories/1").status_code == 409
    assert c.delete(f"/api/admin/categories/{new_id}").status_code == 200


def test_contact_message_flow(admin_client):
    c = admin_client
    assert c.post("/api/public/messages", json={"name": "Zeynep", "email": "zeynep@example.com",
                                                 "message": "Menünüz hakkında bir sorum var.", "phone": ""}).status_code == 201
    messages = c.get("/api/admin/messages").json()
    assert len(messages) == 1
    assert not messages[0]["is_read"]
    assert c.patch(f"/api/admin/messages/{messages[0]['id']}", json={"is_read": True}).status_code == 200
    assert c.get("/api/admin/dashboard").json()["unread_messages"] == 0


def test_valid_image_upload_and_rejected_fake_image(admin_client):
    c = admin_client
    buffer = BytesIO()
    Image.new("RGB", (50, 50), "red").save(buffer, format="PNG")
    response = c.post("/api/admin/uploads", files={"file": ("test.png", buffer.getvalue(), "image/png")})
    assert response.status_code == 201, response.text
    image_url = response.json()["url"]
    assert image_url.endswith(".webp")
    assert c.get(image_url).status_code == 200
    fake = c.post("/api/admin/uploads", files={"file": ("fake.png", b"not-an-image", "image/png")})
    assert fake.status_code == 422
    invalid = c.post("/api/admin/uploads", files={"file": ("file.txt", b"hello", "text/plain")})
    assert invalid.status_code == 422


def test_settings_validation(admin_client):
    c = admin_client
    settings = c.get("/api/admin/settings").json()
    settings["ordering_enabled"] = True
    assert c.put("/api/admin/settings", json=settings).status_code == 422
    settings = c.get("/api/admin/settings").json()
    settings.update(business_name="Fırın Ustası", hero_title="Yeni Lezzet", phone="0555 555 55 55", address="Ornek Mahallesi Tokat", ordering_enabled=True)
    assert c.put("/api/admin/settings", json=settings).status_code == 200
    assert c.get("/api/public/settings").json()["business_name"] == "Fırın Ustası"
    settings["instagram_url"] = "javascript:alert(1)"
    assert c.put("/api/admin/settings", json=settings).status_code == 422


def test_order_csv_export_is_admin_only_and_safe(admin_client):
    c = admin_client
    activate_ordering(c)
    payload = valid_order()
    payload["note"] = "=HYPERLINK(\"bad\")"
    assert c.post("/api/public/orders", json=payload).status_code == 201
    export = c.get("/api/admin/orders/export")
    assert export.status_code == 200
    assert "pideci-siparisler.csv" in export.headers["content-disposition"]
    assert "'=HYPERLINK" in export.text


def test_new_categories_badges_and_campaigns(admin_client):
    c = admin_client
    categories = {x["name"] for x in c.get("/api/public/categories").json()}
    assert {"Pide", "Lahmacun", "Çorba", "Tatlı", "İçecek", "Yan Ürünler"} <= categories
    products = c.get("/api/public/products").json()
    assert all(p["badge"] in {"", "Yeni", "Popüler", "Şefin Seçimi", "Kampanya", "Acılı", "Vejetaryen", "Tatlı Molası"} for p in products)
    assert any(p["old_price_cents"] and p["old_price_cents"] > p["price_cents"] for p in products)
    assert len({p["image_url"] for p in products}) == 45
    first = c.get("/api/admin/products").json()[0]
    response = c.put(f"/api/admin/products/{first['id']}", json={**first, "badge": "Yeni", "old_price_cents": None})
    assert response.status_code == 200, response.text
    assert response.json()["badge"] == "Yeni"


def test_v2_seed_is_idempotent_and_preserves_admin_customizations(tmp_path):
    from app.database import seed_database
    dbfile = tmp_path / "persist.db"
    app = create_app(db_url=f"sqlite:///{dbfile}", upload_dir=tmp_path / "uploads")
    with app.state.factory() as db:
        from app.models import Product
        first = db.scalars(select(Product)).first()
        first_id = first.id
        first.price_cents = 98765
        first.image_url = "/uploads/owner-image.webp"
        db.commit()
    seed_database(app.state.factory)
    with app.state.factory() as db:
        from app.models import Product, Setting
        products = db.scalars(select(Product)).all()
        assert len(products) == 45
        first = db.get(Product, first_id)
        assert first.price_cents == 98765
        assert first.image_url == "/uploads/owner-image.webp"
        assert db.get(Setting, "catalog_v2_seeded").value == "true"


def test_upgrade_from_v1_schema_preserves_custom_item(tmp_path):
    import sqlite3
    from app.models import Product
    dbfile = tmp_path / "old_schema.db"
    with sqlite3.connect(dbfile) as conn:
        conn.executescript("""
        CREATE TABLE categories (
            id INTEGER NOT NULL PRIMARY KEY, name VARCHAR(60) NOT NULL UNIQUE,
            position INTEGER NOT NULL, is_active BOOLEAN NOT NULL
        );
        CREATE TABLE products (
            id INTEGER NOT NULL PRIMARY KEY, category_id INTEGER NOT NULL,
            name VARCHAR(120) NOT NULL, description TEXT NOT NULL,
            image_url VARCHAR(400) NOT NULL, price_cents INTEGER NOT NULL,
            old_price_cents INTEGER, serving_info VARCHAR(120) NOT NULL,
            is_active BOOLEAN NOT NULL, in_stock BOOLEAN NOT NULL,
            is_featured BOOLEAN NOT NULL, position INTEGER NOT NULL,
            created_at DATETIME, updated_at DATETIME,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
        INSERT INTO categories VALUES(1, 'Pide', 1, 1);
        INSERT INTO products VALUES(1, 1, 'Özel İşletme Pidesi', 'Kendi tarifimiz', '/uploads/ozel.webp',
             99999, NULL, '', 1, 1, 0, 1, NULL, NULL);
        """)
    app = create_app(db_url=f"sqlite:///{dbfile}", upload_dir=tmp_path / "uploads")
    with app.state.factory() as db:
        item = db.get(Product, 1)
        assert item.name == "Özel İşletme Pidesi"
        assert item.price_cents == 99999
        assert item.image_url == "/uploads/ozel.webp"
        assert item.badge == ""
        assert len(db.scalars(select(Product)).all()) == 46


def test_delivery_areas_are_enforced_and_saved_without_schema_change(admin_client):
    c = admin_client
    activate_ordering(c)
    settings = c.get('/api/admin/settings').json()
    settings['delivery_areas'] = 'Merkez\nYeni Mahalle'
    settings['facebook_url'] = 'https://www.facebook.com/example'
    saved = c.put('/api/admin/settings', json=settings)
    assert saved.status_code == 200, saved.text
    public = c.get('/api/public/settings').json()
    assert public['delivery_areas'] == 'Merkez\nYeni Mahalle'
    assert public['facebook_url'] == 'https://www.facebook.com/example'
    assert c.post('/api/public/orders', json=valid_order()).status_code == 422
    bad = {**valid_order(), 'delivery_area': 'Başka Semt'}
    assert c.post('/api/public/orders', json=bad).status_code == 422
    valid = {**valid_order(), 'delivery_area': 'merkez'}
    order = c.post('/api/public/orders', json=valid)
    assert order.status_code == 201, order.text
    assert c.get('/api/admin/orders').json()[0]['address'].startswith('Merkez — ')
    assert c.put('/api/admin/settings', json={**settings, 'delivery_areas': 'Merkez\nmerkez'}).status_code == 422
    assert c.put('/api/admin/settings', json={**settings, 'facebook_url': 'https://evil.example/foo'}).status_code == 422


def test_order_status_requires_matching_phone_and_exposes_no_customer_data(admin_client):
    c = admin_client
    activate_ordering(c)
    order = c.post('/api/public/orders', json=valid_order())
    assert order.status_code == 201
    code = order.json()['code']
    status = c.get('/api/public/orders/status', params={'code': code, 'phone': '0555 555 55 55'})
    assert status.status_code == 200
    assert status.json()['status'] == 'new'
    assert set(status.json()) == {'code', 'status', 'total_cents', 'created_at'}
    assert c.get('/api/public/orders/status', params={'code': code, 'phone': '0544 333 22 11'}).status_code == 404
    assert c.get('/api/public/orders/status', params={'code': 'invalid', 'phone': '0555 555 55 55'}).status_code == 422
    admin_order_id = c.get('/api/admin/orders').json()[0]['id']
    assert c.patch(f'/api/admin/orders/{admin_order_id}', json={'status': 'confirmed'}).status_code == 200
    assert c.get('/api/public/orders/status', params={'code': code, 'phone': '05555555555'}).json()['status'] == 'confirmed'


def test_new_ui_files_and_featured_image_framing(client):
    css = client.get('/styles/site.css').text
    html = client.get('/').text
    admin_html = client.get('/admin').text
    assert 'featured-photo img' in css
    assert 'object-fit:contain !important' in css
    assert 'delivery-area-select' in html
    assert 'receipt-dialog' in html
    assert 'status-form' in html
    assert 'delivery_areas' in admin_html
    assert 'notifications-enable' in admin_html
