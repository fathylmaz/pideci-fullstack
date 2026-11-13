# Canlı Restoran Sistemi için Üretim Öncesi Kontrol Listesi

**v1 yerel pilot çalışır; bu listenin tamamı uygulanmadan canlı müşteri verisiyle kullanmayın.**

## Zorunlu canlıya alma işleri

- [ ] Alan adı, HTTPS/TLS, reverse proxy (örn. Caddy veya Nginx) ve HSTS yapılandırması.
- [ ] `COOKIE_SECURE=1`, servis hesabı ile yönetim, güçlü benzersiz yönetici parolası, gerektiğinde MFA.
- [ ] Gerçek işletme iletişim bilgileri, çalışma saatleri, teslimat kapsama alanı, menü ve fiyatlar doğrulandı.
- [ ] Sipariş alımında işletme kapalı/açık saat kontrolü, hizmet dışı bölgeler ve anlık stok senaryoları belirlendi.
- [ ] Yeni siparişler için personel bildirim çözümü (panel ekranı + ses / e-posta / SMS / yazıcı) ve kesinti prosedürü.
- [ ] Yasal satış, iade, teslimat, mesafeli satış ve kapıda ödeme bilgilendirmeleri hukuki incelemeden geçti.
- [ ] KVKK: aydınlatma metni, veri işleme hukuki dayanakları, saklama/silme ve ilgili kişi talepleri süreçleri.
- [ ] İletişim formunun anti-spam/CAPTCHA/rate limit altyapısı kalıcı paylaşımlı depolamaya taşındı.
- [ ] Roller (işletme sahibi, mutfak, kasa), erişim kaydı, rol bazlı yetkilendirme ve uygun admin kimlik doğrulama.
- [ ] Düzenli şifreli veritabanı + yükleme yedeği; ayrı lokasyonda saklama, geri yükleme tatbikatı.
- [ ] PostgreSQL'e geçiş ve Alembic migration, API testleri, yük/performans testleri, güvenlik testi.
- [ ] Hata günlükleri, alarm, uygulama izleme, uptime ve hizmet seviyesi hedefi.
- [ ] Gerçek müşteriyle uçtan uca sipariş kabulü / iptali / teslimat ve arıza senaryoları doğrulandı.
- [ ] Fiyatlandırmada vergi, kampanya, fiş/fatura ve ödeme entegrasyonları işletmenin gereksinimine göre tamamlandı.

## v1 sınırları

Bu sürüm: **tek işletme**, **tek yönetici rolü**, **kapıda nakit**, **yerel SQLite**, **sunucu içinde yapılan basit hız sınırlaması** ve **25 saniyelik panel yenileme** esaslıdır. Teslimat rotası, online kart tahsilatı, otomatik SMS/e-posta, çoklu şube, canlı konum, otomatik fiş/fatura ve üretim için tam gözlemlenebilirlik **henüz bulunmuyor**.

## Önerilen uygulama aşamaları

1. **v1.1:** Sipariş bildirimi, sipariş kabul/iptal bildirimi, açık/kapalı saatleri, teslimat bölgeleri.
2. **v1.2:** Mutfak ekranı, yazıcı, müşteri sipariş durum sorgusu, kupon ve kampanyalar.
3. **v2.0:** PostgreSQL + migration, rol tabanlı yönetim, üretim dağıtımı, KVKK süreçleri, izleme/yedek.
4. **v2.1:** İşletme talebine göre ödeme sağlayıcısı ve muhasebe/fiş entegrasyonu.
