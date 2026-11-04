# Türkiye bugün kaç kez sallandı?

Türkiye'de bugün, son 7 günde ve bu yıl kaydedilen depremleri gösteren statik bir site:
günün sismograf şeridi, il sınırlarıyla harita, "senin ilin" kartı, son 365 günün günlük
sayımı, büyüklük dağılımı ve 1990'dan bu yana 4 ve üzeri depremler. İsteyen son 7 günü
yaklaşık 20 saniyede **dinleyebilir**: her deprem bir ses, büyük deprem daha kalın ve daha
yüksek. Ses kapalı başlar.

Veri GitHub Actions ile 3 saatte bir çekilir, depoya CSV/JSON olarak yazılır ve site
GitHub Pages'e yeniden yayımlanır. **Site tahmin yapmaz.**

## Kaynaklar

| Ne | Kaynak | Kapsam |
|---|---|---|
| Bugün / hafta / yıl, harita, il kartı, günlük çizelge | [EMSC seismicportal FDSN](https://www.seismicportal.eu/fdsnws/event/1/) | 2025-01-01'den bugüne, tüm büyüklükler |
| 1990'dan bu yana | [USGS FDSN event](https://earthquake.usgs.gov/fdsnws/event/1/) | 1990-01-01'den bugüne, M ≥ 4 |
| İl ve ülke sınırları | [Natural Earth](https://www.naturalearthdata.com/) 1:10m (kamu malı) | 81 il |

İkisi de anahtar ya da kayıt istemeyen açık servisler; sorgu kutusu enlem 35–43, boylam 25–45,5.
Kandilli ve AFAD'ın kendi servislerine bağlı değil (yurt dışı IP'lerden, dolayısıyla
GitHub Actions'tan, erişim güvenilir değil). EMSC Türkiye için AFAD ve Kandilli dahil
birçok ağın bildirimini birleştirdiği için sayılar onların listeleriyle birebir aynı olmaz.
2026'da Türkiye'ye düşen EMSC kayıtlarının bildiren kurumu: EMSC 17.067, AFAD 10.789,
KOERI 265.

## Yöntem

1. **Çekme** (`betikler/cek.py`). EMSC ay ay `veri/emsc/YYYY-AA.csv`'ye yazılır. Her
   güncellemede son 10 günün penceresi tamamen yeniden yazılır; EMSC'nin sonradan
   birleştirdiği, sildiği ya da büyüklüğünü düzelttiği olaylar böylece düzelir. USGS
   M4+ listesi her seferinde baştan çekilir (`veri/usgs_m4.csv`, ~5.600 satır);
   USGS'ye ulaşılamazsa eski dosya kullanılır.
2. **İl ataması** (`betikler/atama.py`). Merkez üssü bir ilin sınırı içindeyse o il.
   Değilse ve başka bir ülkenin karası üzerinde değilse, en yakın il 30 km'den yakınsa o
   ilin "açıkları" sayılır (Marmara, Ege ve Akdeniz kıyısındaki deniz depremleri bu
   yüzden sayıma girer). Kalan her şey Türkiye dışıdır ve sitede yer almaz.
   2026 EMSC kayıtlarında: 26.151 karada, 1.946 kıyı açığında, 1.987 Türkiye dışı.
3. **Gün sınırı** Türkiye saatine (UTC+3) göredir. "Bugün" ve "son 7 gün" tarayıcıda,
   son çekilen veriye göre hesaplanır; "bu yıl" son çekimdeki sayıdır.
4. **Enerji** (`log10 E = 1,5 M + 4,8`) "kaç tane 5 büyüklüğündeki deprem" cinsinden
   gösterilir: 6'lık ≈ 32, 7'lik ≈ 1.000 tane 5'lik.
5. **Uzun dönem** yalnızca USGS M ≥ 4 ile yapılır; küçük depremlerin tespiti yıllar
   içinde çok değiştiği için EMSC'nin küçük depremleri uzun dönem karşılaştırmasına girmez.

## 4 Kasım 2026, 18:18 (Türkiye saati) itibarıyla sayılar

- Bugün 64 deprem (52'si 2'den küçük, en büyüğü 2,3, Muğla açıkları), son 7 günde 512
  (6'sı 3 ve üzeri), 2026 başından beri 28.123 (588'i 3 ve üzeri, en büyüğü 5,4,
  Malatya, 20 Mayıs). 2025'te aynı tarihe kadar 35.042 kayıt vardı (Sındırgı depremleri
  sonrası artçılar dahil).
- 2026 büyüklük dağılımı (0,5'lik dilimler): 1,0–1,4 arasında 12.228, 4,0–4,4 arasında 45.
- USGS'de 1990'dan bu yana Türkiye'ye düşen M4+ deprem: 3.290; M6+ : 31.
  Yıllık M4+ sayısının en yüksek olduğu yıllar: 2023 (637), 2011 (226), 1999 (179).
  Açığa çıkan enerjide 2023 yaklaşık 22.000 "tane 5'lik"e denk ve bunun yaklaşık %71'i
  tek bir depremden (7,8) geliyor.

## Sınırlar

- **Tahmin yok.** Günlük sayının artıp azalması büyük bir depremin yaklaştığını göstermez.
- **Tespit değişir.** Küçük depremlerin kaydı istasyon yoğunluğuna bağlıdır; 1'in altındaki
  depremlerin az görünmesi gerçekten az olduklarından değil, hepsi yakalanamadığındandır.
- **Kurum farkları.** EMSC, AFAD, Kandilli ve USGS aynı depremi farklı büyüklükle
  (ML, Mw, mb…) ve birkaç km farklı merkezle verebilir. Uzun dönem bölümündeki büyüklükler
  USGS'nin değeridir; il de USGS'nin merkez üssüne göre atanır. Örneğin 6 Şubat 2023
  04:17 depremi USGS konumuyla Gaziantep sınırına, 23 Nisan 2025 Marmara depremi
  "Tekirdağ açıkları"na düşer; AFAD bunları Pazarcık (Kahramanmaraş) ve Silivri açıkları
  (İstanbul) olarak verir. Bu yüzden il kartında "il merkezine 100 km'den yakın en büyük
  deprem" satırı da var.
- **Sadeleştirilmiş sınırlar.** İl sınırları ~300 m hassasiyetle sadeleştirildi; sınıra
  çok yakın depremler komşu ile düşebilir. Kıbrıs, Ege adaları ve komşu ülkelerin karası
  sayılmaz.
- **Gecikme.** Veri 3 saatte bir çekilir; EMSC kayıtları da depremden birkaç dakika ile
  birkaç saat sonra kesinleşir. Anlık bilgi için AFAD ve Kandilli'yi takip edin.

## Çalıştırma

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows
cd betikler
python cek.py --gecmis    # ilk kurulum: EMSC 2025-01'den bugüne (~23 istek)
python cek.py             # güncelleme: son 10 gün + USGS
python hesapla.py         # site/veri/*.json
cd .. && python -m pytest -q testler
python -m http.server 8823 --directory site
```

`betikler/harita_hazirla.py` il sınırlarını Natural Earth dosyalarından bir kez üretir
(ham dosyalar depoda değil; adresleri betiğin başında).

## Dosyalar

| Yol | İçerik |
|---|---|
| `veri/emsc/*.csv` | EMSC olayları, ay ay (kutunun tamamı, il ataması yapılmamış) |
| `veri/usgs_m4.csv` | USGS M ≥ 4, 1990'dan bugüne |
| `veri/sinir/` | il ataması için sınırlar |
| `site/veri/ozet.json` | sayaçlar, günlük seri, büyüklük dağılımı, il özetleri |
| `site/veri/son.json` | son 30 günün olayları (harita, ses, şerit) |
| `site/veri/gecmis.json` | 1990'dan bu yana yıllık seri, M6+ listesi, M4+ noktalar |

## Lisans

Kod Apache-2.0. EMSC ve USGS verileri kendi kullanım koşullarına tabidir (USGS verisi
kamu malı; EMSC verisi kaynak gösterilerek kullanılıyor). Natural Earth kamu malıdır.
