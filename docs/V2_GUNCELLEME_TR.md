# Pideci v2.0 — Veri kaybetmeden güncelleme kılavuzu

## 1. Eski sunucuyu durdurun

`BASLAT_WINDOWS.bat` çalışan terminalde **Ctrl+C** tuşlarına basın. Uygulamayı kapatmadan güncelleme yapmayın.

## 2. PowerShell'de aşağıdaki satırları çalıştırın

ZIP'in `C:\Users\<kullanıcı>\Downloads\Pideci_FullStack_v2.zip` konumuna indiğini varsayar.

```powershell
$hedef = "C:\VS CODE PROJE\Pideci-Sitesi"
Set-Location $hedef
.\.venv\Scripts\python.exe scripts\backup_database.py
if ($LASTEXITCODE -ne 0) { throw "Yedek alınamadı; güncelleme durduruldu." }
Expand-Archive -LiteralPath "$HOME\Downloads\Pideci_FullStack_v2.zip" -DestinationPath $hedef -Force
.\.venv\Scripts\python.exe -m app.main
if ($LASTEXITCODE -ne 0) { throw "Uygulama başlatma kontrolü başarısız." }
.\BASLAT_WINDOWS.bat
```

**Önemli:** Paket içinde `data/`, `.venv/`, `backups/` ve `.env` **yoktur**. Kullanıcı şifreleri, sipariş geçmişi, mevcut yüklemeler ve işletme ayarları bu nedenle silinmez.

> Not: `python -m app.main` uygulamayı başlangıç aşamasından geçirerek veri tabanı yükseltmesini çalıştırır; web sunucusu başlatmaz. Son satır başlatır.

## 3. İlk açılıştan sonra kontrol

- Müşteri sayfası: `http://127.0.0.1:8000/`
- Yönetici paneli: `http://127.0.0.1:8000/admin`
- Yönetim panelinden daha önce oluşturulan kullanıcı adı ve şifreyle giriş yapın.
- Ürün Yönetimi'nde **45 demo ürünü** ve **6 kategoriyi** kontrol edin. İşletmenin daha önce eklediği özel ürünler varsa sayı 42'den yüksek olabilir.
- Örnek fiyatlar **canlı satış fiyatı değildir**. İşletmenin gerçek ürün ve fiyatlarını gözden geçirin.
- Site Ayarları, siparişler ve görsel yüklemelerini kontrol edin. İşletme bilgileri girilmediyse online sipariş kapalı kalır.

## 4. Güncellemenin veri politikası

- Veritabanında `products.badge` sütunu **yalnızca yoksa eklenir**.
- `catalog_v2_seeded` işaretçisi olmadığı zaman demo katalog **bir kere** eklenir.
- v1'in örnek 7 ürününden birebir eşleşenlerde, **yalnızca varsayılan v1 fiyatı hâlâ duruyorsa** v2 örnek fiyatı uygulanır. İşletmenin değiştirdiği fiyatlar korunur.
- Yüklenmiş (`/uploads/`) görsellerin yerini yeni görseller **almaz**. Başlangıçtaki örnek görseller güncellenir.
- V2 ilk ekleme gerçekleştikten sonraki başlatmalarda fiyat ve katalog değiştirilmez.
- Örnek görsellerin bazıları fotoğraf, bazıları özel hazırlanmış ürün illüstrasyonudur. Ticari işletme kendi gerçek ürün fotoğraflarını yönetim panelinden yüklemelidir.

## 5. Geri dönüş / yedekten geri yükleme

`backups/` altındaki son yedek ZIP içinde `pideci.db` ve varsa `uploads/` bulunur. Sunucu kapalıyken geri yüklenir; mevcut veritabanını ezmeden önce ayrıca kopyasını alın. Uygulama kodu v1'e geri alınacaksa veritabanı da v1 yedeğinden geri alınmalıdır.

## 6. Canlı ticari kullanıma geçmeden önce

Bu proje yerel pilot sürümdür. Üretim için HTTPS/domain, güvenli deploy, erişim kayıtları, merkezi yedekleme/geri yükleme tatbikatı, KVKK ve işletmeye özel metinler, gerçek teslimat kapsamı, bildirim entegrasyonu, sipariş kabul prosedürü, yoğunluk/stres testleri, görsel/ürün doğrulaması, çalışma saatleri/teslimat kuralları ve gerekiyorsa ödeme entegrasyonu gerekir.
