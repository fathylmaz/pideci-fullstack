# Pideci | Restaurant Ordering & Management

**TR:** Taş fırın restoranları için örnek ürün kataloğu, müşteri sipariş ekranı ve yönetici paneli içeren full-stack uygulama. Mevcut kırmızı-beyaz marka kimliği korunarak geliştirilmiştir.

**EN:** Full-stack restaurant menu, ordering, and administration platform. Preserves the original red-and-white visual identity.

[🇹🇷 Türkçe kullanım rehberi](README_TR.md) · [🇬🇧 English guide](README_EN.md) · [Yayın öncesi kontrol listesi](docs/YAYIN_ONCESI_KONTROL_TR.md)

**Stack:** Python 3.13 · FastAPI · SQLAlchemy · SQLite · HTML/CSS · JavaScript · Pytest · GitHub Actions.

**Current status:** Locally testable pilot software, **not** a production-certified ecommerce service. Sample menu prices, images and content must be reviewed by the real business. Payments are cash on delivery; no online card processing is implemented.

## Running locally

```powershell
cd "C:\VS CODE PROJE\Pideci-Sitesi"
.\KURULUM_WINDOWS.bat   # First time only; creates admin credentials interactively
.\BASLAT_WINDOWS.bat
```

- Customer: http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/admin
- Tests: `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`, then `.\.venv\Scripts\python.exe -m pytest -q`
- Admin default login name: `admin`; **there is no built-in password**.

**Privacy:** Never commit `data/`, `.venv/`, `.env`, `backups/`, customer records, credentials, or unredacted screenshots. The `.gitignore` excludes the most common secrets and runtime data, but inspect `git status` before publishing.

## Core features

- Categories, 45 sample products, local product photos, search, sorting, featured items, promotions and stock status.
- Cart, address/phone order requests, minimum order, delivery fee and optional delivery-zone restriction.
- Order reference and status lookup (reference **plus the ordering phone number**); no customer address exposed via status endpoint.
- Admin sign-in, product/category CRUD, image upload, order workflow, CSV export, customer messages, hero/logo/content editing, social links, and browser notifications while the panel is open.
- Automated API tests, SQLite backup utility, installation/update guides, responsive UI.

## Publishing

This repository is a **portfolio/pilot project**. Production use requires HTTPS, domain/hosting configuration, data-retention and privacy review, backup restore drills, monitoring, security tests, reliable notification delivery and business/consumer-law checks. See the checklist above.

<!-- PIDECI_GALLERY_V1 -->

---

## 📸 Screenshots | Ekran Görüntüleri

### Customer Experience | Müşteri Arayüzü

| Homepage | Product Menu |
|:---:|:---:|
| <img src="docs/screenshots/01-home.png" width="450"> | <img src="docs/screenshots/02-menu.png" width="450"> |

| Featured Products | Shopping Cart |
|:---:|:---:|
| <img src="docs/screenshots/03-featured.png" width="450"> | <img src="docs/screenshots/04-cart.png" width="450"> |

| Checkout | Order Tracking |
|:---:|:---:|
| <img src="docs/screenshots/05-checkout.png" width="450"> | <img src="docs/screenshots/06-tracking.png" width="450"> |

### Admin Dashboard | Yönetici Paneli

| Dashboard | Product Management |
|:---:|:---:|
| <img src="docs/screenshots/07-admin-dashboard.png" width="450"> | <img src="docs/screenshots/08-admin-products.png" width="450"> |

| Product Editor | Order Management |
|:---:|:---:|
| <img src="docs/screenshots/09-admin-product-edit.png" width="450"> | <img src="docs/screenshots/10-admin-orders.png" width="450"> |

**Business Settings | İşletme Ayarları**

<img src="docs/screenshots/11-admin-settings.png" width="700">

### Responsive Design | Mobil Arayüz

| Mobile Homepage | Mobile Menu | Mobile Cart |
|:---:|:---:|:---:|
| <img src="docs/screenshots/12-mobile-home.png" width="250"> | <img src="docs/screenshots/13-mobile-menu.png" width="250"> | <img src="docs/screenshots/14-mobile-cart.png" width="250"> |

<!-- PIDECI_GALLERY_END -->
