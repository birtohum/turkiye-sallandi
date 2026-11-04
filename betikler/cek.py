"""Deprem kataloglarını çeker ve veri/ altına CSV olarak yazar.

  python cek.py              # güncelleme: EMSC son 10 gün + USGS M4+ 1990'dan bugüne
  python cek.py --gecmis     # ilk kurulum: EMSC 2025-01'den bugüne, ay ay

Kaynaklar (ikisi de anahtar istemeyen FDSN event servisi):
  EMSC  https://www.seismicportal.eu/fdsnws/event/1/query   (tüm büyüklükler)
  USGS  https://earthquake.usgs.gov/fdsnws/event/1/query    (uzun dönem, M>=4)
"""
import csv
import io
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "veri"
EMSC_KLASOR = VERI / "emsc"
USGS_DOSYA = VERI / "usgs_m4.csv"

# Türkiye ve çevresi; il ataması hesapla.py'de yapılır
KUTU = dict(minlat=35.0, maxlat=43.0, minlon=25.0, maxlon=45.5)
EMSC_BASLANGIC = datetime(2025, 1, 1, tzinfo=timezone.utc)
USGS_BASLANGIC = "1990-01-01"
UA = {"User-Agent": "turkiye-sallandi/1.0 (+https://github.com/birtohum/turkiye-sallandi)"}

EMSC_ALANLAR = ["id", "zaman", "enlem", "boylam", "derinlik", "buyukluk", "tur", "kurum", "bolge"]
USGS_ALANLAR = ["id", "zaman", "enlem", "boylam", "derinlik", "buyukluk", "tur", "yer"]


def _iso(t):
    return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _get(url, params, deneme=4):
    for i in range(deneme):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=120)
            if r.status_code == 204:  # FDSN: sonuç yok
                return None
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if i == deneme - 1:
                raise
            print(f"  yeniden deneniyor ({e})", file=sys.stderr)
            time.sleep(10 * (i + 1))


def emsc_cek(bas, son):
    """[bas, son) aralığındaki EMSC olaylarını satır sözlükleri olarak döndürür."""
    p = dict(format="json", starttime=_iso(bas), endtime=_iso(son), limit=50000, **KUTU)
    r = _get("https://www.seismicportal.eu/fdsnws/event/1/query", p)
    if r is None:
        return []
    satirlar = []
    for f in r.json()["features"]:
        q = f["properties"]
        if q.get("mag") is None:
            continue
        z = datetime.fromisoformat(q["time"].replace("Z", "+00:00"))
        if not (bas <= z < son):  # servis gün sınırlarını gevşek yorumlayabiliyor
            continue
        satirlar.append({
            "id": q["unid"], "zaman": z.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-5] + "Z",
            "enlem": q["lat"], "boylam": q["lon"], "derinlik": q.get("depth"),
            "buyukluk": q["mag"], "tur": q.get("magtype") or "", "kurum": q.get("auth") or "",
            "bolge": q.get("flynn_region") or "",
        })
    return satirlar


def _ay_dosyasi(yil, ay):
    return EMSC_KLASOR / f"{yil:04d}-{ay:02d}.csv"


def _oku(yol):
    if not yol.exists():
        return []
    with yol.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _yaz(yol, satirlar, alanlar):
    yol.parent.mkdir(parents=True, exist_ok=True)
    satirlar = sorted(satirlar, key=lambda s: (s["zaman"], s["id"]))
    tampon = io.StringIO()
    w = csv.DictWriter(tampon, fieldnames=alanlar, lineterminator="\n")
    w.writeheader()
    w.writerows(satirlar)
    yol.write_text(tampon.getvalue(), encoding="utf-8")


def ay_basi(t):
    return t.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def sonraki_ay(t):
    return (t.replace(day=28) + timedelta(days=4)).replace(day=1)


def emsc_birlestir(eski, yeni, bas, son):
    """Pencere [bas, son) içindeki eski kayıtları yenileriyle değiştirir (EMSC olayları
    birleştirir/siler; pencere içini tamamen yeniden yazmak bunu doğru yansıtır)."""
    b, s = _iso(bas), _iso(son)
    kalan = [r for r in eski if not (b <= r["zaman"][:19] < s)]
    gorulen = {r["id"] for r in kalan}
    return kalan + [r for r in yeni if r["id"] not in gorulen]


def emsc_guncelle(bas, son):
    t = ay_basi(bas)
    toplam = 0
    while t < son:
        ay_son = min(sonraki_ay(t), son)
        pb = max(t, bas)
        yeni = emsc_cek(pb, ay_son)
        yol = _ay_dosyasi(t.year, t.month)
        satirlar = emsc_birlestir(_oku(yol), yeni, pb, ay_son)
        _yaz(yol, satirlar, EMSC_ALANLAR)
        toplam += len(yeni)
        print(f"EMSC {t:%Y-%m}: {len(yeni)} olay çekildi, dosyada {len(satirlar)}")
        t = sonraki_ay(t)
        time.sleep(2)
    return toplam


def usgs_guncelle():
    p = dict(format="csv", starttime=USGS_BASLANGIC, minmagnitude=4, orderby="time-asc",
             minlatitude=KUTU["minlat"], maxlatitude=KUTU["maxlat"],
             minlongitude=KUTU["minlon"], maxlongitude=KUTU["maxlon"], eventtype="earthquake")
    r = _get("https://earthquake.usgs.gov/fdsnws/event/1/query", p)
    satirlar = []
    for q in csv.DictReader(io.StringIO(r.text)):
        satirlar.append({
            "id": q["id"], "zaman": q["time"],
            "enlem": q["latitude"], "boylam": q["longitude"], "derinlik": q["depth"],
            "buyukluk": q["mag"], "tur": q["magType"], "yer": q["place"],
        })
    if len(satirlar) < 3000:  # beklenen ~5000; eksik yanıtı diske yazma
        raise RuntimeError(f"USGS beklenenden az satır döndürdü: {len(satirlar)}")
    _yaz(USGS_DOSYA, satirlar, USGS_ALANLAR)
    print(f"USGS M4+: {len(satirlar)} olay")


def main(argv):
    simdi = datetime.now(timezone.utc).replace(microsecond=0)
    bas = EMSC_BASLANGIC if "--gecmis" in argv else simdi - timedelta(days=10)
    emsc_guncelle(bas, simdi + timedelta(minutes=1))
    try:
        usgs_guncelle()
    except Exception as e:  # uzun dönem dosyası eskisiyle kalır; günlük sayımlar etkilenmez
        if not USGS_DOSYA.exists():
            raise
        print(f"UYARI: USGS güncellenemedi, eski dosya kullanılıyor ({e})", file=sys.stderr)
    (VERI / "cekim.json").write_text(json.dumps({"zaman": _iso(simdi) + "Z"}), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
