"""Pideci full-stack HTTP API and static customer/admin interfaces.

Prices are integer kuruş; the server is the only authority for order totals.
"""

import io
import csv
import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, Response as PlainResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import DEFAULT_SETTINGS, ROOT, create_session_factory, seed_database, setting_values
from app.models import (
    AdminSession, AdminUser, AuditLog, Category, ContactMessage, Order, OrderItem,
    Product, Setting, utcnow,
)
from app.security import check_password, token_hash

SESSION_COOKIE = "pideci_admin_session"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_UPLOAD_PIXELS = 12_000_000
PHONE_PATTERN = re.compile(r"^[+0-9][0-9 ()-]{8,22}$")
ORDER_TRANSITIONS = {
    "new": {"confirmed", "cancelled"},
    "confirmed": {"preparing", "cancelled"},
    "preparing": {"on_the_way", "cancelled"},
    "on_the_way": {"delivered", "cancelled"},
    "delivered": set(),
    "cancelled": set(),
}


class ProductPayload(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category_id: int = Field(gt=0)
    description: str = Field(default="", max_length=1000)
    image_url: str = Field(default="", max_length=400)
    price_cents: int = Field(ge=1, le=50_000_000)
    old_price_cents: int | None = Field(default=None, ge=1, le=50_000_000)
    serving_info: str = Field(default="", max_length=120)
    badge: str = Field(default="", max_length=24)
    is_active: bool = True
    in_stock: bool = True
    is_featured: bool = False
    position: int = Field(default=0, ge=0, le=100_000)

    @model_validator(mode="after")
    def validate_old_price(self):
        if self.old_price_cents is not None and self.old_price_cents <= self.price_cents:
            raise ValueError("Eski fiyat, satış fiyatından yüksek olmalıdır")
        return self

    @field_validator("badge")
    @classmethod
    def validate_badge(cls, value):
        if value not in {"", "Yeni", "Popüler", "Şefin Seçimi", "Kampanya", "Acılı", "Vejetaryen", "Tatlı Molası"}:
            raise ValueError("Bilinmeyen ürün etiketi")
        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        if not value.strip():
            raise ValueError("Ürün adı boş olamaz")
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value):
        if value and not (value.startswith("/uploads/") or value.startswith("/images/")):
            raise ValueError("Görsel yalnızca uygulamaya yüklenen dosyalardan seçilebilir")
        if ".." in value or "?" in value or "#" in value:
            raise ValueError("Geçersiz görsel yolu")
        return value


class CategoryPayload(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    position: int = Field(default=0, ge=0, le=100_000)
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Kategori adı en az 2 harf olmalıdır")
        return value


class OrderLinePayload(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=30)


class OrderPayload(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=24)
    address: str = Field(min_length=10, max_length=500)
    delivery_area: str = Field(default="", max_length=80)
    note: str = Field(default="", max_length=500)
    items: list[OrderLinePayload] = Field(min_length=1, max_length=30)

    @field_validator("customer_name", "address")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Boş değer kabul edilmez")
        return value.strip()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value):
        if not PHONE_PATTERN.fullmatch(value.strip()):
            raise ValueError("Geçerli bir telefon numarası girin")
        return value.strip()


class ContactPayload(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=160)
    phone: str = Field(default="", max_length=24)
    message: str = Field(min_length=10, max_length=2000)

    @field_validator("name", "message")
    @classmethod
    def meaningful_contact_text(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("İçerik boş olamaz")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Geçerli bir e-posta adresi girin")
        return value


class LoginPayload(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class OrderStatusPayload(BaseModel):
    status: str


class MessageStatusPayload(BaseModel):
    is_read: bool


class SettingsPayload(BaseModel):
    business_name: str = Field(min_length=2, max_length=100)
    hero_title: str = Field(min_length=2, max_length=160)
    hero_text: str = Field(min_length=2, max_length=500)
    hero_image_url: str = Field(max_length=400)
    logo_url: str = Field(max_length=400)
    about_title: str = Field(max_length=160)
    about_text: str = Field(max_length=1000)
    about_image_url: str = Field(max_length=400)
    phone: str = Field(max_length=30)
    address: str = Field(max_length=400)
    opening_hours: str = Field(max_length=200)
    instagram_url: str = Field(max_length=300)
    facebook_url: str = Field(default="", max_length=300)
    delivery_areas: str = Field(default="", max_length=900)
    delivery_fee_cents: int = Field(ge=0, le=10_000_000)
    min_order_cents: int = Field(ge=0, le=10_000_000)
    ordering_enabled: bool

    @field_validator("hero_image_url", "logo_url", "about_image_url")
    @classmethod
    def valid_local_image(cls, value):
        return ProductPayload.validate_image_url(value)

    @field_validator("instagram_url", "facebook_url")
    @classmethod
    def valid_social(cls, value, info):
        value = value.strip()
        if value:
            parsed = urlparse(value)
            allowed = ({"instagram.com", "www.instagram.com"} if info.field_name == "instagram_url"
                       else {"facebook.com", "www.facebook.com", "m.facebook.com"})
            if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username or parsed.password:
                raise ValueError("Güvenilir bir HTTPS sosyal medya adresi girin")
        return value

    @field_validator("delivery_areas")
    @classmethod
    def valid_areas(cls, value):
        areas = [a.strip() for a in value.replace(",", "\n").splitlines() if a.strip()]
        if len(areas) > 40 or any(len(a) > 80 for a in areas):
            raise ValueError("En fazla 40 teslimat bölgesi ve bölge başına 80 karakter girin")
        if len({a.casefold() for a in areas}) != len(areas):
            raise ValueError("Teslimat bölgeleri tekrar etmemeli")
        return "\n".join(areas)


def parse_delivery_areas(value: str) -> list[str]:
    return [a.strip() for a in value.replace(",", "\n").splitlines() if a.strip()]


def product_dict(product: Product) -> dict:
    return {
        "id": product.id, "name": product.name, "description": product.description,
        "image_url": product.image_url, "category_id": product.category_id,
        "category": product.category.name, "price_cents": product.price_cents,
        "old_price_cents": product.old_price_cents, "serving_info": product.serving_info,
        "badge": product.badge,
        "is_active": product.is_active, "in_stock": product.in_stock,
        "is_featured": product.is_featured, "position": product.position,
    }


def category_dict(category: Category) -> dict:
    return {"id": category.id, "name": category.name, "position": category.position,
            "is_active": category.is_active}


def order_dict(order: Order) -> dict:
    return {
        "id": order.id, "code": order.code, "customer_name": order.customer_name,
        "phone": order.phone, "address": order.address, "note": order.note,
        "status": order.status, "payment_method": order.payment_method,
        "subtotal_cents": order.subtotal_cents, "delivery_fee_cents": order.delivery_fee_cents,
        "total_cents": order.total_cents, "created_at": order.created_at.isoformat() + "Z",
        "items": [{"product_id": item.product_id, "name": item.product_name,
                   "quantity": item.quantity, "unit_price_cents": item.unit_price_cents,
                   "line_total_cents": item.line_total_cents} for item in order.items],
    }


def create_app(db_url: str | None = None, upload_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Pideci Sitesi API", docs_url=None, redoc_url=None)
    app.state.factory = create_session_factory(db_url)
    seed_database(app.state.factory)
    uploads = Path(upload_dir) if upload_dir else ROOT / "data" / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    app.state.uploads = uploads
    app.state.login_attempts = defaultdict(deque)
    app.state.public_attempts = defaultdict(deque)

    def get_db(request: Request):
        with request.app.state.factory() as db:
            yield db

    Db = Annotated[Session, Depends(get_db)]

    def guard_rate(request: Request, key: str, limit: int, window: int):
        # In-process throttle is suitable locally; use a shared store behind multiple workers.
        ip = request.client.host if request.client else "unknown"
        bucket = (key, ip)
        store = app.state.login_attempts if key == "login" else app.state.public_attempts
        q = store[bucket]
        now = time.monotonic()
        while q and q[0] < now - window:
            q.popleft()
        if len(q) >= limit:
            raise HTTPException(status_code=429, detail="Çok fazla deneme. Daha sonra tekrar deneyin.")
        q.append(now)

    def get_session(request: Request, db: Db) -> tuple[AdminSession, AdminUser]:
        cookie = request.cookies.get(SESSION_COOKIE)
        if not cookie:
            raise HTTPException(status_code=401, detail="Yönetici girişi gerekli")
        session = db.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash(cookie)))
        if not session or session.expires_at <= utcnow():
            raise HTTPException(status_code=401, detail="Oturum süresi doldu")
        admin = db.get(AdminUser, session.admin_id)
        if admin is None:
            raise HTTPException(status_code=401, detail="Yönetici bulunamadı")
        return session, admin

    Admin = Annotated[tuple[AdminSession, AdminUser], Depends(get_session)]

    def csrf_admin(request: Request, admin: Admin,
                   x_csrf_token: Annotated[str | None, Header()] = None):
        if not x_csrf_token or not secrets.compare_digest(x_csrf_token, admin[0].csrf_token):
            raise HTTPException(status_code=403, detail="Güvenlik doğrulaması başarısız")
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(status_code=403, detail="Güvenilmeyen istek kaynağı")
        return admin[1]

    MutatingAdmin = Annotated[AdminUser, Depends(csrf_admin)]

    def audit(db: Session, admin: AdminUser, action: str, target: str, target_id: str | int):
        db.add(AuditLog(admin_id=admin.id, action=action, target=target, target_id=str(target_id)))

    @app.middleware("http")
    async def response_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith("/api/admin"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/public/settings")
    def public_settings(db: Db):
        settings = setting_values(db)
        return {k: (int(v) if k.endswith("_cents") else v == "true" if k == "ordering_enabled" else v)
                for k, v in settings.items() if k in DEFAULT_SETTINGS}

    @app.get("/api/public/categories")
    def public_categories(db: Db):
        cats = db.scalars(select(Category).where(Category.is_active.is_(True))
                          .order_by(Category.position, Category.id)).all()
        return [category_dict(c) for c in cats]

    @app.get("/api/public/products")
    def public_products(db: Db):
        products = db.scalars(select(Product).join(Category)
                              .where(Product.is_active.is_(True), Category.is_active.is_(True))
                              .options(joinedload(Product.category))
                              .order_by(Product.position, Product.id)).all()
        return [product_dict(x) for x in products]

    @app.post("/api/public/orders", status_code=201)
    def create_order(payload: OrderPayload, request: Request, db: Db):
        guard_rate(request, "orders", 15, 900)
        settings = setting_values(db)
        if settings.get("ordering_enabled") != "true" or not settings.get("phone") or not settings.get("address"):
            raise HTTPException(status_code=409, detail="Şu anda internetten sipariş alınmıyor")
        areas = parse_delivery_areas(settings.get("delivery_areas", ""))
        selected_area = payload.delivery_area.strip()
        if areas:
            canonical = next((area for area in areas if area.casefold() == selected_area.casefold()), None)
            if canonical is None:
                raise HTTPException(status_code=422, detail="Lütfen hizmet verilen bir teslimat bölgesi seçin")
            selected_area = canonical
        quantities = {}
        for item in payload.items:
            quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
            if quantities[item.product_id] > 30:
                raise HTTPException(status_code=422, detail="Bir üründen en fazla 30 adet sipariş edilebilir")
        if sum(quantities.values()) > 60:
            raise HTTPException(status_code=422, detail="Sipariş miktarı sınırı aşıldı")
        rows = db.scalars(select(Product).join(Category).where(
            Product.id.in_(quantities), Product.is_active.is_(True),
            Product.in_stock.is_(True), Category.is_active.is_(True),
        )).all()
        if len(rows) != len(quantities):
            raise HTTPException(status_code=409, detail="Sepetteki bir ürün artık satışta değil")
        subtotal = sum(p.price_cents * quantities[p.id] for p in rows)
        minimum = int(settings.get("min_order_cents", "0"))
        if subtotal < minimum:
            raise HTTPException(status_code=422, detail="Minimum sipariş tutarına ulaşılmadı")
        delivery = int(settings.get("delivery_fee_cents", "0"))
        address = f"{selected_area} — {payload.address}" if selected_area else payload.address
        order = Order(code="PD-" + secrets.token_hex(5).upper(), customer_name=payload.customer_name,
                      phone=payload.phone, address=address, note=payload.note,
                      subtotal_cents=subtotal, delivery_fee_cents=delivery,
                      total_cents=subtotal + delivery)
        db.add(order)
        db.flush()
        for product in rows:
            count = quantities[product.id]
            db.add(OrderItem(order_id=order.id, product_id=product.id,
                             product_name=product.name, unit_price_cents=product.price_cents,
                             quantity=count, line_total_cents=product.price_cents * count))
        db.commit()
        return {"code": order.code, "total_cents": order.total_cents,
                "message": "Siparişiniz alındı. İşletme siparişinizi değerlendirecek."}

    @app.get("/api/public/orders/status")
    def public_order_status(code: str, phone: str, request: Request, db: Db):
        guard_rate(request, "order_status", 15, 900)
        code = code.strip().upper()
        phone_digits = re.sub(r"\D", "", phone)
        if not re.fullmatch(r"PD-[0-9A-F]{10}", code) or not (10 <= len(phone_digits) <= 15):
            raise HTTPException(status_code=422, detail="Sipariş kodu veya telefon geçersiz")
        order = db.scalar(select(Order).where(Order.code == code))
        if not order or re.sub(r"\D", "", order.phone) != phone_digits:
            raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
        return {"code": order.code, "status": order.status,
                "total_cents": order.total_cents, "created_at": order.created_at.isoformat() + "Z"}

    @app.post("/api/public/messages", status_code=201)
    def create_message(payload: ContactPayload, request: Request, db: Db):
        guard_rate(request, "messages", 6, 900)
        db.add(ContactMessage(name=payload.name.strip(), email=payload.email,
                              phone=payload.phone.strip(), message=payload.message.strip()))
        db.commit()
        return {"message": "Mesajınız alındı"}

    @app.post("/api/admin/login")
    def login(payload: LoginPayload, response: Response, request: Request, db: Db):
        guard_rate(request, "login", 8, 900)
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            raise HTTPException(status_code=403, detail="Güvenilmeyen istek kaynağı")
        admin = db.scalar(select(AdminUser).where(AdminUser.username == payload.username))
        if not admin or not check_password(payload.password, admin.password_hash):
            raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı")
        # Prevent session fixation; issue a fresh opaque cookie for each login.
        token = secrets.token_urlsafe(48)
        csrf = secrets.token_urlsafe(32)
        db.add(AdminSession(admin_id=admin.id, token_hash=token_hash(token), csrf_token=csrf,
                            expires_at=utcnow() + timedelta(hours=12)))
        db.commit()
        response.set_cookie(key=SESSION_COOKIE, value=token, httponly=True,
                            secure=os.environ.get("COOKIE_SECURE") == "1",
                            samesite="strict", path="/", max_age=12 * 3600)
        return {"username": admin.username, "csrf_token": csrf}

    @app.get("/api/admin/me")
    def admin_me(admin: Admin):
        return {"username": admin[1].username, "csrf_token": admin[0].csrf_token}

    @app.post("/api/admin/logout")
    def admin_logout(response: Response, admin: MutatingAdmin, request: Request, db: Db):
        cookie = request.cookies.get(SESSION_COOKIE)
        if cookie:
            session = db.scalar(select(AdminSession).where(AdminSession.token_hash == token_hash(cookie)))
            if session:
                db.delete(session)
                db.commit()
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"success": True}

    @app.get("/api/admin/dashboard")
    def dashboard(admin: Admin, db: Db):
        active_products = db.scalar(select(func.count()).select_from(Product).where(Product.is_active.is_(True)))
        new_orders = db.scalar(select(func.count()).select_from(Order).where(Order.status == "new"))
        unread = db.scalar(select(func.count()).select_from(ContactMessage).where(ContactMessage.is_read.is_(False)))
        delivered_total = db.scalar(select(func.coalesce(func.sum(Order.total_cents), 0)).where(Order.status == "delivered"))
        recent = db.scalars(select(Order).options(selectinload(Order.items))
                            .order_by(Order.created_at.desc(), Order.id.desc()).limit(6)).all()
        return {"active_products": active_products, "new_orders": new_orders,
                "unread_messages": unread, "delivered_revenue_cents": delivered_total,
                "recent_orders": [order_dict(o) for o in recent]}

    @app.get("/api/admin/products")
    def admin_products(admin: Admin, db: Db):
        rows = db.scalars(select(Product).options(joinedload(Product.category))
                          .order_by(Product.position, Product.id)).all()
        return [product_dict(p) for p in rows]

    @app.post("/api/admin/products", status_code=201)
    def add_product(payload: ProductPayload, admin: MutatingAdmin, db: Db):
        if not db.get(Category, payload.category_id):
            raise HTTPException(status_code=422, detail="Kategori bulunamadı")
        product = Product(**payload.model_dump())
        db.add(product)
        db.flush()
        audit(db, admin, "create", "product", product.id)
        db.commit()
        db.refresh(product)
        return product_dict(product)

    @app.put("/api/admin/products/{product_id}")
    def update_product(product_id: int, payload: ProductPayload, admin: MutatingAdmin, db: Db):
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        if not db.get(Category, payload.category_id):
            raise HTTPException(status_code=422, detail="Kategori bulunamadı")
        for key, value in payload.model_dump().items():
            setattr(product, key, value)
        audit(db, admin, "update", "product", product.id)
        db.commit()
        db.refresh(product)
        return product_dict(product)

    @app.delete("/api/admin/products/{product_id}")
    def archive_product(product_id: int, admin: MutatingAdmin, db: Db):
        product = db.get(Product, product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Ürün bulunamadı")
        product.is_active = False  # Preserve order history: never hard-delete sold products.
        audit(db, admin, "archive", "product", product.id)
        db.commit()
        return {"success": True}

    @app.get("/api/admin/categories")
    def admin_categories(admin: Admin, db: Db):
        cats = db.scalars(select(Category).order_by(Category.position, Category.id)).all()
        return [category_dict(c) for c in cats]

    @app.post("/api/admin/categories", status_code=201)
    def add_category(payload: CategoryPayload, admin: MutatingAdmin, db: Db):
        category = Category(**payload.model_dump())
        db.add(category)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Bu kategori zaten var") from None
        audit(db, admin, "create", "category", category.id)
        db.commit()
        return category_dict(category)

    @app.put("/api/admin/categories/{category_id}")
    def update_category(category_id: int, payload: CategoryPayload, admin: MutatingAdmin, db: Db):
        category = db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        for key, value in payload.model_dump().items():
            setattr(category, key, value)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="Bu kategori zaten var") from None
        audit(db, admin, "update", "category", category.id)
        db.commit()
        return category_dict(category)

    @app.delete("/api/admin/categories/{category_id}")
    def delete_category(category_id: int, admin: MutatingAdmin, db: Db):
        category = db.get(Category, category_id)
        if not category:
            raise HTTPException(status_code=404, detail="Kategori bulunamadı")
        if db.scalar(select(func.count()).select_from(Product).where(Product.category_id == category_id)):
            raise HTTPException(status_code=409, detail="Bu kategoride ürün var. Kategoriyi pasifleştirebilirsiniz.")
        db.delete(category)
        audit(db, admin, "delete", "category", category.id)
        db.commit()
        return {"success": True}

    @app.post("/api/admin/uploads", status_code=201)
    async def upload_image(admin: MutatingAdmin, db: Db, file: UploadFile = File(...)):
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(status_code=422, detail="JPG, PNG veya WEBP yükleyebilirsiniz")
        data = await file.read(MAX_UPLOAD_BYTES + 1)
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Görsel 5 MB'dan büyük olamaz")
        try:
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(status_code=422, detail="Desteklenmeyen görsel biçimi")
                if original.width * original.height > MAX_UPLOAD_PIXELS:
                    raise HTTPException(status_code=413, detail="Görsel çözünürlüğü çok yüksek")
                original.verify()
            with Image.open(io.BytesIO(data)) as original:
                image = ImageOps.exif_transpose(original)
                image.thumbnail((2000, 2000))
                if image.mode not in {"RGB", "RGBA"}:
                    image = image.convert("RGBA" if "transparency" in image.info else "RGB")
                filename = secrets.token_hex(16) + ".webp"
                path = app.state.uploads / filename
                image.save(path, format="WEBP", quality=86, method=5)
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise HTTPException(status_code=422, detail="Görsel dosyası geçersiz") from None
        audit(db, admin, "upload", "image", filename)
        db.commit()
        return {"url": "/uploads/" + filename}

    @app.get("/api/admin/orders")
    def admin_orders(admin: Admin, db: Db):
        orders = db.scalars(select(Order).options(selectinload(Order.items))
                            .order_by(Order.created_at.desc(), Order.id.desc()).limit(300)).all()
        return [order_dict(o) for o in orders]

    @app.get("/api/admin/orders/export")
    def export_orders_csv(admin: Admin, db: Db):
        """UTF-8 Excel-ready export. Strip formula prefixes from untrusted cells."""
        rows = db.scalars(select(Order).options(selectinload(Order.items))
                          .order_by(Order.created_at.desc(), Order.id.desc())).all()
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["Sipariş Kodu", "Tarih (UTC)", "Durum", "Müşteri", "Telefon",
                         "Adres", "Not", "Ürünler", "Ara Toplam (Kuruş)",
                         "Teslimat (Kuruş)", "Toplam (Kuruş)"])
        def safe(value):
            text = str(value or "")
            return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text
        for order in rows:
            products = "; ".join(f"{item.quantity}x {item.product_name}" for item in order.items)
            writer.writerow([safe(order.code), order.created_at.isoformat(), safe(order.status),
                             safe(order.customer_name), safe(order.phone), safe(order.address),
                             safe(order.note), safe(products), order.subtotal_cents,
                             order.delivery_fee_cents, order.total_cents])
        return PlainResponse(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=pideci-siparisler.csv"})

    @app.patch("/api/admin/orders/{order_id}")
    def update_order_status(order_id: int, payload: OrderStatusPayload, admin: MutatingAdmin, db: Db):
        order = db.get(Order, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Sipariş bulunamadı")
        if payload.status not in ORDER_TRANSITIONS.get(order.status, set()):
            raise HTTPException(status_code=409, detail="Bu sipariş durumu geçişine izin verilmiyor")
        order.status = payload.status
        audit(db, admin, "status:" + payload.status, "order", order.id)
        db.commit()
        return {"success": True, "status": order.status}

    @app.get("/api/admin/messages")
    def admin_messages(admin: Admin, db: Db):
        messages = db.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc(),
                                                               ContactMessage.id.desc()).limit(300)).all()
        return [{"id": m.id, "name": m.name, "email": m.email, "phone": m.phone,
                 "message": m.message, "is_read": m.is_read,
                 "created_at": m.created_at.isoformat() + "Z"} for m in messages]

    @app.patch("/api/admin/messages/{message_id}")
    def mark_message(message_id: int, payload: MessageStatusPayload, admin: MutatingAdmin, db: Db):
        message = db.get(ContactMessage, message_id)
        if not message:
            raise HTTPException(status_code=404, detail="Mesaj bulunamadı")
        message.is_read = payload.is_read
        audit(db, admin, "mark_read" if payload.is_read else "mark_unread", "message", message.id)
        db.commit()
        return {"success": True}

    @app.get("/api/admin/settings")
    def admin_settings(admin: Admin, db: Db):
        values = setting_values(db)
        return {k: (int(v) if k.endswith("_cents") else v == "true" if k == "ordering_enabled" else v)
                for k, v in values.items() if k in DEFAULT_SETTINGS}

    @app.put("/api/admin/settings")
    def update_settings(payload: SettingsPayload, admin: MutatingAdmin, db: Db):
        if payload.ordering_enabled and (not payload.phone.strip() or not payload.address.strip()):
            raise HTTPException(status_code=422, detail="Siparişi açmadan önce işletme telefonu ve adresini girin")
        for key, value in payload.model_dump().items():
            item = db.get(Setting, key)
            if item is None:
                item = Setting(key=key, value="")
                db.add(item)
            item.value = str(value).lower() if isinstance(value, bool) else str(value)
        audit(db, admin, "update", "settings", "site")
        db.commit()
        return {"success": True}

    web = ROOT / "web"
    app.mount("/images", StaticFiles(directory=web / "images"), name="images")
    app.mount("/styles", StaticFiles(directory=web / "styles"), name="styles")
    app.mount("/js", StaticFiles(directory=web / "js"), name="js")
    app.mount("/uploads", StaticFiles(directory=uploads), name="uploads")

    @app.get("/admin")
    @app.get("/admin/")
    def admin_page():
        return FileResponse(web / "admin.html", headers={"Cache-Control": "no-store"})

    @app.get("/")
    def homepage():
        return FileResponse(web / "index.html")

    return app


app = create_app()
