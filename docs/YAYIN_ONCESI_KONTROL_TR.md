# Pideci — Pilot ve GitHub Öncesi Kontrol Listesi

> Bu sürüm **yerel pilot** olarak çalışır. "Testlerden geçti" ifadesi canlı ticari kullanıma uygunluk garantisi değildir.

## Kurulum ve görünüm
- [ ] Öne çıkan kartlarda dört fotoğrafın da tamamı masaüstü (1440 px) ve mobil (390 px) görünümde kesilmeden duruyor.
- [ ] Menünün tüm kategori, filtre, sıralama, arama, "Daha fazla", kampanya ve tatlı/içecek alanları çalışıyor.
- [ ] Mobil menü, sepete ekleme, modal, sepet çekmecesi, iletişim formu ve yönetici tablosunda taşma yok.
- [ ] Eksik dört görsel (Bafra Pidesi, Fındık/Kaşarlı Lahmacun, Çıtır Lahmacun Menü) işletmenin gerçek ürününe göre yenilendi.

## Sipariş ve yönetim
- [ ] Site Ayarları: doğru telefon, gerçek adres, çalışma saatleri, teslimat bölgesi, ücret ve minimum sepet girildi.
- [ ] Güncel **gerçek** ürün fiyatları, fotoğrafları, stok ve indirimler doğrulandı.
- [ ] Online sipariş açıldıktan sonra deneme siparişi oluşturuldu; kod ve toplam tutar doğru.
- [ ] Hizmet dışı bölge reddedildi; geçerli bölge kabul edildi.
- [ ] Doğru kod+telefon ile sipariş sorgulama çalışıyor; yanlış telefonla durum gösterilmiyor.
- [ ] Panelde yeni sipariş, durum geçişleri, CSV indirme, mesaj okundu işaretleme, ürün/kategori CRUD ve görsel yükleme tek tek denendi.
- [ ] Gerçek işletmede ekran açık değilken de güvenilir sipariş bildirimi için ek altyapı planlandı (v4'te yalnızca açık panel + tarayıcı izni).
- [ ] Yönetici parolası güçlü; oturum ve başka kullanıcı erişimi test edildi.

## Güvenlik ve dağıtım (gerçek müşteri için zorunlu)
- [ ] HTTPS ve `COOKIE_SECURE=1`, güvenli barındırma, ters vekil, alan adı, sertifika, firewall ve düzenli bakım kuruldu.
- [ ] KVKK aydınlatması, pazarlama izinleri (varsa), çerez ve veri saklama/silme politikaları hukuk kontrolünden geçti.
- [ ] Otomatik düzenli veritabanı + yüklenen medya yedeği ve **geri yükleme** tatbikatı yapıldı.
- [ ] Çoklu worker/sunucu için kalıcı hız sınırlandırma, uygun DB/migration, loglama/izleme, hata alarmı, güvenlik taraması planlandı.
- [ ] Ödeme şekli, teslimat şartları, iptal/iade, mesafeli satış kuralları işletmeye uygun biçimde yayınlandı.
- [ ] Sipariş verileri sunucunun dışında korumasız şekilde dışa aktarılmıyor; CSV/ZIP özel saklanıyor.

## GitHub'a çıkmadan önce
- [ ] `git status --short`, `git diff --check`, `git ls-files` kontrol edildi.
- [ ] `.venv`, `.env`, `data/`, `backups/`, `*.db`, `*-wal`, `*-shm`, API anahtarları ve şifreler izlenmiyor.
- [ ] `README.md`, `README_TR.md`, `README_EN.md`, ekran görüntüleri ve test çıktısı mevcut; örnek kişi verisi kullanılmıyor.
- [ ] Terminalde `python -m pytest -q` ve `node --check web/js/site.js`, `node --check web/js/admin.js` başarılı.
- [ ] Lisans türü proje sahibi tarafından seçildi; lisans eklenmediyse otomatik olarak "açık kaynak" varsayılmadı.
