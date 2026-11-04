"""Paylaşım görseli (1200×630): günün sayısı ve sismograf çizgisi -> site/og.png"""
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

KOK = Path(__file__).resolve().parent.parent
YT = Path(__file__).resolve().parent / "yazitipi"
TR = timezone(timedelta(hours=3))
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

KAGIT, KARA, MUREKKEP, MUREKKEP2, CIZGI, VURGU = "#f4efe4", "#fbf8f1", "#1f2933", "#52606d", "#cfc6b3", "#b4532a"


def yazi(dosya, boy, eksenler):
    f = ImageFont.truetype(str(YT / dosya), boy)
    f.set_variation_by_axes(eksenler)
    return f


def sayi(n):
    return f"{n:,}".replace(",", ".")


def main():
    ozet = json.loads((KOK / "site" / "veri" / "ozet.json").read_text(encoding="utf-8"))
    son = json.loads((KOK / "site" / "veri" / "son.json").read_text(encoding="utf-8"))
    g = datetime.fromisoformat(ozet["guncelleme"].replace("Z", "+00:00")).astimezone(TR)
    bas = g.replace(hour=0, minute=0, second=0, microsecond=0)
    i_t, i_m = son["alanlar"].index("t"), son["alanlar"].index("m")
    bugun = [(r[i_t], r[i_m]) for r in son["olaylar"] if r[i_t] >= bas.timestamp()]
    n = len(bugun)

    W, H = 1200, 630
    im = Image.new("RGB", (W, H), KAGIT)
    d = ImageDraw.Draw(im)
    baslik = yazi("Fraunces.ttf", 96, [144, 700, 0, 0])
    kucuk = yazi("Figtree.ttf", 28, [500])
    alt = yazi("Figtree.ttf", 24, [400])

    d.text((72, 64), f"Sismograf defteri · {g.day} {AYLAR[g.month - 1]} {g.year}, {g:%H:%M}", font=kucuk, fill=MUREKKEP2)
    # "Türkiye bugün 64" / "kez sallandı."
    x, y = 72, 118
    d.text((x, y), "Türkiye bugün ", font=baslik, fill=MUREKKEP)
    x += d.textlength("Türkiye bugün ", font=baslik)
    d.text((x, y), sayi(n), font=baslik, fill=VURGU)
    d.text((72, y + 110), "kez sallandı.", font=baslik, fill=MUREKKEP)

    # Sismograf şeridi (gece yarısından son güncellemeye)
    sx0, sx1, sy0, sy1 = 72, W - 72, 400, 540
    d.rounded_rectangle((sx0, sy0, sx1, sy1), radius=14, fill=KARA, outline=CIZGI, width=2)
    for h in range(1, 24):
        xx = sx0 + (sx1 - sx0) * h / 24
        d.line((xx, sy0 + 2, xx, sy1 - 2), fill=CIZGI if h % 6 else "#b9af9b", width=1)
    orta = (sy0 + sy1) / 2
    gen = sx1 - sx0
    tepe = [(sx0 + gen * (t - bas.timestamp()) / 86400, min(1, (max(m, 0.3) / 5.5) ** 1.6) * 62) for t, m in bugun]
    son_x = sx0 + gen * min(1, (g - bas).total_seconds() / 86400)
    nok, tohum = [], 7
    xx = sx0
    while xx <= son_x:
        tohum = (tohum * 9301 + 49297) % 233280
        yy = (tohum / 233280 - 0.5) * 1.6
        for x0, a in tepe:
            dd = xx - x0
            if 0 <= dd < 48:
                yy += a * math.exp(-dd / 8.5) * math.sin(dd * 1.6)
        nok.append((xx, orta - yy))
        xx += 1
    if len(nok) > 1:
        d.line(nok, fill=MUREKKEP, width=2, joint="curve")
        d.ellipse((son_x - 8, orta - 8, son_x + 8, orta + 8), fill=VURGU)

    d.text((72, 562), "EMSC kataloğu · Türkiye ve kıyı açıkları · tahmin yapmaz", font=alt, fill=MUREKKEP2)
    sag = "birtohum.github.io/turkiye-sallandi"
    d.text((W - 72 - d.textlength(sag, font=alt), 562), sag, font=alt, fill=MUREKKEP2)
    hedef = KOK / "site" / "og.png"
    im.save(hedef, optimize=True)
    print(f"og.png: bugün {n}, {hedef.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
