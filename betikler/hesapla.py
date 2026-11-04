"""veri/ altındaki katalogları ile atar ve site/veri/*.json dosyalarını üretir."""
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from atama import Atayici
from iller import IL_ADLARI

KOK = Path(__file__).resolve().parent.parent
VERI = KOK / "veri"
CIKTI = KOK / "site" / "veri"
TR = timezone(timedelta(hours=3))  # Türkiye 2016'dan beri yıl boyu UTC+3
SON_GUN = 30          # haritaya ve sese giden pencere
GUNLUK_GUN = 365      # zaman çizelgesi


def zaman(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def kutu(m):
    """Büyüklük sınıfı: 0:<2, 1:2–2.9, 2:3–3.9, 3:4–4.9, 4:5+"""
    if m < 2:
        return 0
    return min(int(m), 5) - 1


SINIF_ADLARI = ["2'den küçük", "2–2,9", "3–3,9", "4–4,9", "5 ve üzeri"]


def m5_esdegeri(m):
    """Açığa çıkan enerjiyi 'kaç tane M5' cinsinden verir (log10 E = 1,5 M + 4,8)."""
    return 10 ** (1.5 * (m - 5.0))


def yer_adi(plaka, deniz):
    ad = IL_ADLARI[plaka]
    return f"{ad} açıkları" if deniz else ad


def oku_emsc(atayici):
    olaylar = []
    for yol in sorted((VERI / "emsc").glob("*.csv")):
        with yol.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if not r["buyukluk"]:
                    continue
                lat, lon = float(r["enlem"]), float(r["boylam"])
                plaka, deniz = atayici.ata(lat, lon)
                if not plaka:
                    continue
                olaylar.append({
                    "t": zaman(r["zaman"]), "enlem": lat, "boylam": lon,
                    "derinlik": float(r["derinlik"]) if r["derinlik"] else None,
                    "m": round(float(r["buyukluk"]), 1), "plaka": plaka, "deniz": deniz,
                    "kurum": r["kurum"],
                })
    olaylar.sort(key=lambda o: o["t"])
    return olaylar


def oku_usgs(atayici):
    olaylar = []
    with (VERI / "usgs_m4.csv").open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["enlem"]), float(r["boylam"])
            plaka, deniz = atayici.ata(lat, lon)
            if not plaka or not r["buyukluk"]:
                continue
            olaylar.append({"t": zaman(r["zaman"]), "enlem": lat, "boylam": lon,
                            "m": round(float(r["buyukluk"]), 1), "tur": r["tur"],
                            "plaka": plaka, "deniz": deniz})
    olaylar.sort(key=lambda o: o["t"])
    return olaylar


def kisa(o):
    return {"t": o["t"].astimezone(TR).strftime("%Y-%m-%dT%H:%M"), "m": o["m"],
            "yer": yer_adi(o["plaka"], o["deniz"])}


def ozet_hesapla(emsc, simdi):
    yerel = simdi.astimezone(TR)
    yil_bas = datetime(yerel.year, 1, 1, tzinfo=TR)
    gecen_bas = datetime(yerel.year - 1, 1, 1, tzinfo=TR)
    gecen_ayni = (yerel - timedelta(days=1) if (yerel.month, yerel.day) == (2, 29) else yerel).replace(year=yerel.year - 1)
    bugun_bas = yerel.replace(hour=0, minute=0, second=0, microsecond=0)
    hafta_bas = simdi - timedelta(days=7)

    yil = [o for o in emsc if o["t"] >= yil_bas]
    gecen = [o for o in emsc if gecen_bas <= o["t"] < gecen_ayni]
    bugun = [o for o in emsc if o["t"] >= bugun_bas]
    hafta = [o for o in emsc if o["t"] >= hafta_bas]

    def blok(liste):
        s = Counter(kutu(o["m"]) for o in liste)
        en = max(liste, key=lambda o: (o["m"], o["t"]), default=None)
        return {"n": len(liste), "siniflar": [s.get(i, 0) for i in range(5)],
                "en_buyuk": kisa(en) if en else None}

    # Büyüklük dağılımı (yıl başından beri, 0,5'lik dilimler)
    dagilim = Counter(min(int(o["m"] * 2) / 2, 6.5) for o in yil if o["m"] >= 0)
    dagilim_liste = [{"m": k, "n": dagilim.get(k, 0)} for k in [x / 2 for x in range(0, 14)]]

    # Günlük sayım (son 365 gün, Türkiye takvim günü)
    gunler = defaultdict(lambda: [0, 0, 0.0])
    ilk_gun = (bugun_bas - timedelta(days=GUNLUK_GUN - 1)).date()
    for o in emsc:
        g = o["t"].astimezone(TR).date()
        if g < ilk_gun:
            continue
        k = gunler[g]
        k[0] += 1
        k[1] += o["m"] >= 3
        k[2] = max(k[2], o["m"])
    gunluk = []
    for i in range(GUNLUK_GUN):
        g = ilk_gun + timedelta(days=i)
        n, n3, mx = gunler.get(g, [0, 0, 0.0])
        gunluk.append([g.isoformat(), n, n3, mx])

    # İller (yıl başından beri)
    il_yil = defaultdict(list)
    for o in yil:
        il_yil[o["plaka"]].append(o)
    son365 = simdi - timedelta(days=365)
    il_son = defaultdict(list)
    for o in emsc:
        if o["t"] >= son365:
            il_son[o["plaka"]].append(o)
    iller = {}
    for p in IL_ADLARI:
        liste = il_yil.get(p, [])
        en = max(liste, key=lambda o: (o["m"], o["t"]), default=None)
        sonlar = il_son.get(p, [])
        iller[str(p)] = {
            "yil": len(liste), "yil_m3": sum(o["m"] >= 3 for o in liste),
            "en_buyuk_yil": kisa(en) if en else None,
            "son365": len(sonlar),
            "son": [kisa(o) for o in reversed(sonlar[-5:])],
        }

    kurumlar = Counter(o["kurum"] for o in yil)
    return {
        "yil": yerel.year,
        "bugun": blok(bugun), "hafta": blok(hafta), "yil_blok": blok(yil),
        "gecen_yil_ayni_doneme_kadar": len(gecen),
        "siniflar": SINIF_ADLARI,
        "dagilim": dagilim_liste,
        "gunluk": gunluk,
        "iller": iller,
        "kurumlar": kurumlar.most_common(6),
    }


def son_olaylar(emsc, simdi):
    bas = simdi - timedelta(days=SON_GUN)
    return {
        "alanlar": ["t", "enlem", "boylam", "derinlik", "m", "plaka", "deniz"],
        "olaylar": [[int(o["t"].timestamp()), round(o["enlem"], 3), round(o["boylam"], 3),
                     round(o["derinlik"]) if o["derinlik"] is not None else None,
                     o["m"], o["plaka"], int(o["deniz"])] for o in emsc if o["t"] >= bas],
    }


def gecmis_hesapla(usgs, simdi):
    son_yil = simdi.astimezone(TR).year
    yillar = []
    for y in range(1990, son_yil + 1):
        liste = [o for o in usgs if o["t"].astimezone(TR).year == y]
        s = Counter(min(int(o["m"]), 7) for o in liste)
        yillar.append({
            "yil": y, "n": len(liste),
            "m4": s.get(4, 0), "m5": s.get(5, 0), "m6": s.get(6, 0), "m7": s.get(7, 0),
            "enerji_m5": round(sum(m5_esdegeri(o["m"]) for o in liste), 1),
        })
    buyukler = [dict(kisa(o), tur=o["tur"]) for o in usgs if o["m"] >= 6]
    il_m4 = Counter(o["plaka"] for o in usgs)
    il_en = {}
    for o in usgs:
        k = str(o["plaka"])
        if k not in il_en or o["m"] > il_en[k]["m"]:
            il_en[k] = kisa(o)
    return {
        "yillar": yillar, "buyukler": buyukler,
        "iller": {str(p): {"m4": il_m4.get(p, 0), "en_buyuk": il_en.get(str(p))} for p in IL_ADLARI},
        "noktalar": [[o["t"].astimezone(TR).strftime("%Y-%m-%dT%H:%M"), round(o["enlem"], 2),
                      round(o["boylam"], 2), o["m"], o["plaka"], int(o["deniz"])] for o in usgs],
        "toplam": len(usgs),
    }


def yaz(ad, veri):
    CIKTI.mkdir(parents=True, exist_ok=True)
    yol = CIKTI / ad
    yol.write_text(json.dumps(veri, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{ad}: {yol.stat().st_size // 1024} KB")


def main():
    cekim = json.loads((VERI / "cekim.json").read_text(encoding="utf-8"))["zaman"]
    simdi = zaman(cekim)
    a = Atayici()
    emsc = oku_emsc(a)
    usgs = oku_usgs(a)
    ozet = ozet_hesapla(emsc, simdi)
    ozet["guncelleme"] = cekim
    yaz("ozet.json", ozet)
    yaz("son.json", dict(son_olaylar(emsc, simdi), guncelleme=cekim))
    yaz("gecmis.json", gecmis_hesapla(usgs, simdi))
    b, h, y = ozet["bugun"], ozet["hafta"], ozet["yil_blok"]
    print(f"Bugün {b['n']}, son 7 gün {h['n']}, {ozet['yil']} başından beri {y['n']} "
          f"(geçen yıl aynı döneme kadar {ozet['gecen_yil_ayni_doneme_kadar']}); "
          f"EMSC Türkiye olayı {len(emsc)}, USGS M4+ Türkiye {len(usgs)}")


if __name__ == "__main__":
    main()
