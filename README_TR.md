# Pideci Sitesi — Full-stack Restoran Yönetimi (v4.0)

**Durum:** Yerel pilot / portföy projesi. Canlı ticari kullanıma geçmeden önce [yayın öncesi kontrol listesindeki](docs/YAYIN_ONCESI_KONTROL_TR.md) işlerin tamamlanması gerekir.

Orijinal kırmızı, beyaz ve siyah Pideci Sitesi tasarımının üzerine **FastAPI, SQLAlchemy ve SQLite** ile geliştirilmiş müşteri sitesi ve işletme yönetici panelidir.

[English](README_EN.md) · [Ana sayfa](README.md) · [Değişiklikler](CHANGELOG.md)

## İşlevler

**Müşteri:** 45 örnek ürün / 6 kategori, arama-sıralama-filtre, öne çıkanlar, kampanyalar, tatlı/içecek vitrini, sepet, adet kontrolü, sunucu tabanlı fiyat, teslimat ve minimum sepet tutarı, isteğe bağlı teslimat bölgesi kısıtı, ad/telefon/adres ile kapıda nakit sipariş, sipariş kodu ve durum sorgulama, iletişim formu, çalışma saatleri/adres/telefon ve Instagram/Facebook bağlantıları.

**Yönetici:** 12+ karakterlik kurulum parolası ile giriş, ürün oluşturma/düzenleme/arşivleme, görsel yükleme, kategori, stok, kampanya ve rozet, fiyat/indirim ve öne çıkarma, sipariş durumu yönetimi (yeni→onaylandı→hazırlanıyor→yolda→teslim), CSV, mesajlar, pano, işletme/hero/logo/hakkımızda/teslimat ayarları. Tarayıcı açık ve panel görünürken yeni siparişler için kontrol ve isteğe bağlı tarayıcı bildirimi.

**Önemli:** Tarayıcı bildirimi, ekran kapalıyken garantili push/SMS/WhatsApp bildirimi değildir. Çalışma saatleri bilgilendirme metnidir; otomatik saat dışı sipariş durdurma henüz yoktur. Online kart ile ödeme yoktur.

## Windows'ta kurulum

Proje konumu: `C:\VS CODE PROJE\Pideci-Sitesi`

```powershell
cd "C:\VS CODE PROJE\Pideci-Sitesi"
.\KURULUM_WINDOWS.bat  # Yalnızca ilk kurulumda
.\BASLAT_WINDOWS.bat
```

Müşteri: http://127.0.0.1:8000 · Yönetici: http://127.0.0.1:8000/admin

Kurulumda kullanıcı adı `admin` için kendi şifrenizi (en az 12 karakter) oluşturursunuz. **Hazır şifre yoktur.** Var olan kurulum için ilk kurulumu tekrarlamayın; v4 paketindeki güvenli güncelleme yönergelerini uygulayın.

## İşletmeyi hazırlama

Yönetici panelinde **Site Ayarları** bölümünden işletme adı, telefon, adres, çalışma saatleri, Instagram/Facebook, teslimat bölgesi (her satır bir semt/mahalle), minimum sipariş, teslimat ücreti ve sipariş alımı açma/kapama kontrolünü yapın. Teslimat bölgelerini boş bırakırsanız sistem bölge kısıtı uygulamaz. Bölge eklerseniz müşteri sipariş formunda birini seçer; sunucu da doğrular.

**Örnek fiyatlar gerçek restoran fiyatları değildir.** İşletme tarafından doğrulanmalıdır. Siparişler yalnızca işletmeye talep olarak iletilir ve otomatik kabul edilmiş sayılmaz.

## Test

```powershell
.\TEST_ET_WINDOWS.bat
```

Veya:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
node --check web\js\site.js
node --check web\js\admin.js
```

Testler geçici veritabanı kullanır. GitHub Actions `.github/workflows/ci.yml` üzerinden çalışır.

## Veri ve gizlilik

- Veritabanı: `data/pideci.db`; yönetici yüklemeleri: `data/uploads/*.webp`.
- Veritabanı + medyayı yedekleme: `.\.venv\Scripts\python.exe scripts\backup_database.py`.
- Yedek müşteri telefon ve adresleri içerir. Kimseyle açık paylaşmayın, GitHub'a göndermeyin.
- `.gitignore` içinde `.venv/`, `data/`, `backups/`, `.env` ve tipik veritabanı/gizli dosyalar hariç tutulur.
- Mevcut yönetici şifresi, siparişler, fiyatlar ve özel yüklenmiş görseller güncellemede değişmez.

## Proje yapısı

- `app/`: Python/FastAPI uygulaması, güvenlik, veri modelleri
- `web/index.html`, `web/js/site.js`, `web/styles/`: müşteri sitesi
- `web/admin.html`, `web/js/admin.js`: yönetici paneli
- `web/images/`: uygulama görselleri; `data/uploads/`: işletmenin kendi fotoğrafları
- `tests/`: API, iş kuralları ve yükseltme testleri
- `scripts/`: yedekleme
- `docs/`: kontrol listeleri ve tasarım/örnek fiyat notları

## Yayından önce

HTTPS/TLS + güvenli çerez, KVKK ve çerez metinleri, veri saklama/silme, sipariş bildirimlerinin sürekli çalışması, yedek geri yükleme tatbikatı, dış servisler, çoklu sunucu ve üretim veritabanı/migration, performans ve güvenlik testleri tamamlanmalıdır.
