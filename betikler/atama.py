"""Bir deprem merkez üssünü ile atar.

Kural:
  1. Nokta bir ilin sınırı içindeyse o il (deniz=False).
  2. Değilse ve başka bir ülkenin karası üzerinde değilse, en yakın il KIYI_KM'den
     yakınsa o il, deniz=True ("... açıkları"). Marmara, Ege ve Akdeniz kıyısındaki
     deniz depremleri böylece Türkiye sayımına girer.
  3. Diğer her şey Türkiye dışı (plaka 0).
"""
import json
import math
from pathlib import Path

from shapely import STRtree
from shapely.affinity import affine_transform
from shapely.geometry import Point, shape
from shapely.prepared import prep

KOK = Path(__file__).resolve().parent.parent
SINIR = KOK / "veri" / "sinir"
KIYI_KM = 30.0

# Küçük bir bölgede yeterince doğru eşit uzaklık yaklaşımı (derece -> km)
_KX = 111.32 * math.cos(math.radians(39.0))
_KY = 110.57


def _km(g):
    return affine_transform(g, [_KX, 0, 0, _KY, 0, 0])


class Atayici:
    def __init__(self, sinir=SINIR, kiyi_km=KIYI_KM):
        iller = json.loads((sinir / "iller.geojson").read_text(encoding="utf-8"))["features"]
        self.plakalar = [f["properties"]["plaka"] for f in iller]
        self.geo = [shape(f["geometry"]) for f in iller]
        self.hazir = [prep(g) for g in self.geo]
        self.km = [_km(g) for g in self.geo]
        self.agac = STRtree(self.geo)
        self.agac_km = STRtree(self.km)
        komsu = json.loads((sinir / "komsu_kara.geojson").read_text(encoding="utf-8"))["features"]
        self.komsu = [prep(shape(f["geometry"])) for f in komsu]
        self.komsu_agac = STRtree([shape(f["geometry"]) for f in komsu])
        self.kiyi_km = kiyi_km

    def ata(self, enlem, boylam):
        """(plaka, deniz) döndürür; Türkiye dışı için (0, False)."""
        p = Point(boylam, enlem)
        for i in self.agac.query(p):
            if self.hazir[i].contains(p):
                return self.plakalar[i], False
        for i in self.komsu_agac.query(p):
            if self.komsu[i].contains(p):
                return 0, False
        pk = Point(boylam * _KX, enlem * _KY)
        i = self.agac_km.nearest(pk)
        u = self.km[i].distance(pk)
        if u <= self.kiyi_km:
            # 1 km'den yakınsa sadeleştirme boşluğu / kıyı çizgisi payı: karada say
            return self.plakalar[i], u > 1.0
        return 0, False
