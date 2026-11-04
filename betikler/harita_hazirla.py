"""Bir kez çalıştırılır: Natural Earth 1:10m sınırlarından il ve komşu kara dosyalarını üretir.

  python harita_hazirla.py ne_10m_admin_1_states_provinces.geojson ne_10m_admin_0_countries.geojson

Kaynak: https://github.com/nvkelso/natural-earth-vector (kamu malı).
Çıktılar:
  veri/sinir/iller.geojson        il ataması için (sadeleştirme ~300 m)
  veri/sinir/komsu_kara.geojson   Türkiye dışındaki karalar (kıyı açığı kuralı için)
  site/veri/iller.geojson         harita çizimi için (sadeleştirme ~1 km)
  site/veri/komsular.geojson      harita arka planı için komşu ülkeler
"""
import json
import sys
from pathlib import Path

from shapely.geometry import MultiPolygon, box, mapping, shape
from shapely.geometry.polygon import orient

from iller import IL_ADLARI

KOK = Path(__file__).resolve().parent.parent
KUTU = box(22.0, 33.0, 48.0, 44.5)  # komşu karalar için kesme kutusu


def _yuvarla(o, n):
    if isinstance(o, float):
        return round(o, n)
    if isinstance(o, (list, tuple)):
        return [_yuvarla(x, n) for x in o]
    return o


def _d3(g):
    # d3-geo dış halkayı saat yönünde bekler
    if g.geom_type == "MultiPolygon":
        return MultiPolygon([orient(q, -1.0) for q in g.geoms])
    return orient(g, -1.0)


def _yaz(yol, ozellikler, n):
    yol.parent.mkdir(parents=True, exist_ok=True)
    feats = []
    for props, g in ozellikler:
        geo = mapping(_d3(g))
        feats.append({"type": "Feature", "properties": props,
                      "geometry": {"type": geo["type"], "coordinates": _yuvarla(geo["coordinates"], n)}})
    yol.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{yol} ({yol.stat().st_size // 1024} KB)")


def main(adm1, adm0):
    d = json.loads(Path(adm1).read_text(encoding="utf-8"))
    iller = []
    for f in d["features"]:
        p = f["properties"]
        if p.get("adm0_a3") != "TUR":
            continue
        plaka = int(p["iso_3166_2"].split("-")[1])
        iller.append((plaka, shape(f["geometry"])))
    assert len(iller) == 81, len(iller)
    iller.sort()
    _yaz(KOK / "veri" / "sinir" / "iller.geojson",
         [({"plaka": k, "ad": IL_ADLARI[k]}, g.simplify(0.003, preserve_topology=True)) for k, g in iller], 4)
    _yaz(KOK / "site" / "veri" / "iller.geojson",
         [({"plaka": k, "ad": IL_ADLARI[k]}, g.simplify(0.012, preserve_topology=True)) for k, g in iller], 3)

    d0 = json.loads(Path(adm0).read_text(encoding="utf-8"))
    komsu = []
    for f in d0["features"]:
        p = f["properties"]
        if p.get("ADM0_A3") == "TUR":
            continue
        g = shape(f["geometry"])
        if not g.intersects(KUTU):
            continue
        g = g.intersection(KUTU)
        if g.is_empty or g.geom_type not in ("Polygon", "MultiPolygon"):
            continue
        komsu.append((p.get("ADM0_A3"), g))
    _yaz(KOK / "veri" / "sinir" / "komsu_kara.geojson",
         [({"ulke": u}, g.simplify(0.003, preserve_topology=True)) for u, g in komsu], 4)
    _yaz(KOK / "site" / "veri" / "komsular.geojson",
         [({"ulke": u}, g.simplify(0.02, preserve_topology=True)) for u, g in komsu
          if g.area > 0.002], 2)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
