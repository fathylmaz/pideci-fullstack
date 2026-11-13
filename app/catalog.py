"""Representative 2026 demo menu; prices are examples, NOT a real restaurant quote.

Seed is additive and runs once; existing admin changes are not overwritten.
"""
from __future__ import annotations

# name, category, TRY, description, image basename, badge, featured, optional old TRY
CATALOG = [
    ('Kaşarlı Pide', 'Pide', 310, 'Bol kaşar peyniri ve ince, çıtır hamur. Taş fırında kızartılır.', 'pide-kasarli', 'Şefin Seçimi', True, None),
    ('Kıymalı Pide', 'Pide', 340, 'Baharatlarla harmanlanmış dana kıyma, domates ve biber.', 'pide-kiymali', 'Popüler', True, None),
    ('Kuşbaşılı Pide', 'Pide', 395, 'Dana kuşbaşı, taze domates ve yeşil biber.', 'pide-kusbasili', '', True, None),
    ('Kuşbaşılı Kaşarlı Pide', 'Pide', 435, 'Dana kuşbaşı ve eriyen kaşarla ustanın özel yorumu.', 'pide-kusbasili-kasarli', 'Şefin Seçimi', True, None),
    ('Karışık Pide', 'Pide', 450, 'Kıyma, kuşbaşı, sucuk ve kaşarın buluşması.', 'pide-karisik', 'Kampanya', True, 485),
    ('Sucuklu Kaşarlı Pide', 'Pide', 375, 'Baharatlı sucuk ve uzayan kaşar peyniri.', 'pide-sucuklu', '', False, None),
    ('Pastırmalı Kaşarlı Pide', 'Pide', 465, 'Pastırma dilimleri ve bol peynir.', 'pide-pastirmali', 'Yeni', False, None),
    ('Kavurmalı Kaşarlı Pide', 'Pide', 480, 'Yavaş pişmiş dana kavurma ve kaşar.', 'pide-kavurmali', '', False, None),
    ('Yumurtalı Kaşarlı Pide', 'Pide', 325, 'Fırından yeni çıkan pidenin üzerinde yumurta ve kaşar.', 'pide-yumurtali', '', False, None),
    ('Ispanaklı Kaşarlı Pide', 'Pide', 315, 'Ispanak ve kaşar peyniriyle hazırlanan hafif seçenek.', 'pide-ispanakli', 'Vejetaryen', False, None),
    ('Mantarlı Kaşarlı Pide', 'Pide', 350, 'Sote mantar ve kaşarın uyumu.', 'pide-mantarli', 'Vejetaryen', False, None),
    ('Sebzeli Pide', 'Pide', 330, 'Domates, biber, mantar ve mevsim sebzeleriyle hazırlanan pide.', 'pide-sebzeli', 'Vejetaryen', False, None),
    ('Tavuklu Kaşarlı Pide', 'Pide', 355, 'Baharatlı tavuk parçaları ve erimiş kaşar.', 'pide-tavuklu', '', False, None),
    ('Bafra Pidesi', 'Pide', 370, 'Kapalı hamurda nefis kıymalı Bafra usulü pide.', 'pide-bafra', 'Şefin Seçimi', True, None),
    ('Cantık', 'Pide', 185, 'Bursa usulü küçük ve yuvarlak kıymalı pide.', 'pide-cantik', '', False, None),
    ('Lahmacun', 'Lahmacun', 165, 'İncecik, çıtır hamur üzerinde baharatlı kıymalı harç.', 'lahmacun', 'Popüler', True, None),
    ('Acılı Lahmacun', 'Lahmacun', 175, 'Bol kırmızı pul biberli, çıtır lahmacun.', 'lahmacun-acili', 'Acılı', False, None),
    ('Fındık Lahmacun', 'Lahmacun', 110, 'Küçük boy, çıtır lahmacun.', 'lahmacun-findik', '', False, None),
    ('Kaşarlı Lahmacun', 'Lahmacun', 200, 'İnce lahmacuna eriyen kaşar ilavesi.', 'lahmacun-kasarli', 'Yeni', False, None),
    ('Çıtır Lahmacun Menü', 'Lahmacun', 235, 'Çıtır lahmacun, küçük ayran ve yeşillik servisi.', 'lahmacun-menu', 'Kampanya', False, None),
    ('Mercimek Çorbası', 'Çorba', 145, 'Sıcacık, limon ve baharat ile servis.', 'corba-mercimek', '', False, None),
    ('Ezogelin Çorbası', 'Çorba', 155, 'Mercimek, bulgur ve baharatlarla geleneksel tarif.', 'corba-ezogelin', '', False, None),
    ('Tavuk Suyu Çorbası', 'Çorba', 185, 'Ev usulü tavuk suyu ve tel şehriye.', 'corba-tavuk', '', False, None),
    ('İşkembe Çorbası', 'Çorba', 220, 'Sarımsak ve sirkeyle servis edilen klasik lezzet.', 'corba-iskembe', '', False, None),
    ('Künefe', 'Tatlı', 295, 'Tel kadayıf, eriyen peynir ve Antep fıstığıyla sıcacık.', 'tatli-kunefe', 'Tatlı Molası', True, 325),
    ('Sütlaç', 'Tatlı', 220, 'Geleneksel, sütlü ve hafif tatlı.', 'tatli-sutlac', '', False, None),
    ('Fırın Sütlaç', 'Tatlı', 245, 'Üzeri nar gibi kızarmış, fırında sütlaç.', 'tatli-firin-sutlac', '', False, None),
    ('Katmer', 'Tatlı', 325, 'İncecik hamur, kaymak ve Antep fıstığı.', 'tatli-katmer', 'Şefin Seçimi', False, None),
    ('Baklava Porsiyon', 'Tatlı', 285, 'Tereyağlı, çıtır katlar ve Antep fıstığı.', 'tatli-baklava', '', False, None),
    ('Ayran (30 cl)', 'İçecek', 65, 'Yemeklerin yanında serinletici ayran.', 'icecek-ayran', '', False, None),
    ('Büyük Ayran (1 L)', 'İçecek', 145, 'Paylaşmalık bir litrelik ayran.', 'icecek-ayran-buyuk', '', False, None),
    ('Kola (33 cl)', 'İçecek', 90, 'Soğuk kutu kola.', 'icecek-kola', '', False, None),
    ('Fanta (33 cl)', 'İçecek', 90, 'Soğuk portakallı gazlı içecek.', 'icecek-fanta', '', False, None),
    ('Şalgam (30 cl)', 'İçecek', 80, 'Soğuk şalgam suyu.', 'icecek-salgam', '', False, None),
    ('Soda (20 cl)', 'İçecek', 55, 'Doğal maden suyu.', 'icecek-soda', '', False, None),
    ('Su (50 cl)', 'İçecek', 40, 'Ambalajlı içme suyu.', 'icecek-su', '', False, None),
    ('Çay', 'İçecek', 40, 'İnce belli bardakta taze demlenmiş çay.', 'icecek-cay', '', False, None),
    ('Mevsim Salata', 'Yan Ürünler', 170, 'Mevsimin taptaze yeşillikleri ve limon.', 'yan-salata', 'Vejetaryen', False, None),
    ('Çoban Salata', 'Yan Ürünler', 180, 'Domates, salatalık, biber ve maydanoz.', 'yan-coban', '', False, None),
    ('Turşu Tabağı', 'Yan Ürünler', 90, 'Karışık ev usulü turşular.', 'yan-tursu', '', False, None),
    ('Acılı Ezme', 'Yan Ürünler', 120, 'Domates, biber ve isot ile hazırlanan ezme.', 'yan-ezme', 'Acılı', False, None),
    ('Ekstra Kaşar', 'Yan Ürünler', 55, 'Pide için ek kaşar peyniri.', 'yan-kasar', '', False, None),
    ('Ekstra Sucuk', 'Yan Ürünler', 80, 'Pidenize ilave sucuk.', 'yan-sucuk', '', False, None),
    ('Ekstra Ayran Menü', 'Yan Ürünler', 55, 'Siparişe ek 20 cl ayran.', 'yan-ayran', '', False, None),
    ('Ekstra Yumurta', 'Yan Ürünler', 35, 'Pidenize bir adet yumurta.', 'yan-yumurta', '', False, None),
]

DEFAULT_V1_PRICES = {
    'Kuşbaşılı Kaşarlı Pide': 10999,
    'Lahmacun': 4999,
    'Mercimek Çorbası': 5499,
    'Künefe': 8999,
    'Cantık': 4000,
    'Fındık Lahmacun': 2500,
    'Special Pide': 12000,
}
