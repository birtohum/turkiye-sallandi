import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "betikler"))

from atama import Atayici  # noqa: E402
from cek import emsc_birlestir, sonraki_ay  # noqa: E402
from hesapla import TR, kutu, m5_esdegeri, ozet_hesapla  # noqa: E402


@pytest.fixture(scope="module")
def a():
    return Atayici()


@pytest.mark.parametrize("enlem,boylam,plaka,deniz", [
    (39.92, 32.85, 6, False),    # Ankara, Kızılay
    (41.01, 28.98, 34, False),   # İstanbul, Eminönü
    (37.07, 37.38, 27, False),   # Gaziantep merkez
    (38.50, 43.38, 65, False),   # Van merkez
    (37.90, 26.79, 35, True),    # 30 Ekim 2020 Samos–İzmir depremi, denizde
])
def test_il_atama(a, enlem, boylam, plaka, deniz):
    assert a.ata(enlem, boylam) == (plaka, deniz)


def test_marmara_ortasi_turkiye_sayilir(a):
    plaka, deniz = a.ata(40.80, 28.00)
    assert plaka in (34, 59, 77, 16, 10) and deniz


@pytest.mark.parametrize("enlem,boylam", [
    (37.98, 23.73),   # Atina
    (39.20, 26.30),   # Midilli adası (Yunanistan karası, kıyımıza 30 km'den yakın)
    (36.20, 36.95),   # Halep, Suriye
    (43.00, 34.00),   # Karadeniz ortası
    (35.17, 33.36),   # Lefkoşa (Kıbrıs, Türkiye ili değil)
])
def test_turkiye_disi(a, enlem, boylam):
    assert a.ata(enlem, boylam) == (0, False)


def test_kutu():
    assert [kutu(m) for m in (0.4, 1.9, 2.0, 3.5, 4.9, 5.0, 7.8)] == [0, 0, 1, 2, 3, 4, 4]


def test_enerji_logaritmik():
    assert m5_esdegeri(5.0) == pytest.approx(1.0)
    assert m5_esdegeri(6.0) == pytest.approx(31.62, rel=1e-3)
    assert m5_esdegeri(7.0) == pytest.approx(1000.0, rel=1e-6)


def test_sonraki_ay():
    t = datetime(2025, 12, 1, tzinfo=timezone.utc)
    assert sonraki_ay(t) == datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_emsc_birlestir_pencereyi_yeniler():
    bas = datetime(2026, 11, 1, tzinfo=timezone.utc)
    son = datetime(2026, 11, 3, tzinfo=timezone.utc)
    eski = [
        {"id": "a", "zaman": "2026-10-31T23:59:00.0Z"},   # pencere dışı: kalır
        {"id": "b", "zaman": "2026-11-01T05:00:00.0Z"},   # pencere içi, EMSC sildi: gider
        {"id": "c", "zaman": "2026-11-02T05:00:00.0Z"},   # pencere içi, güncellendi
    ]
    yeni = [{"id": "c", "zaman": "2026-11-02T05:00:01.0Z"}, {"id": "d", "zaman": "2026-11-02T06:00:00.0Z"}]
    sonuc = emsc_birlestir(eski, yeni, bas, son)
    assert sorted(r["id"] for r in sonuc) == ["a", "c", "d"]
    assert [r for r in sonuc if r["id"] == "c"][0]["zaman"].endswith("01.0Z")


def _olay(t, m, plaka=6):
    return {"t": t, "enlem": 39.9, "boylam": 32.8, "derinlik": 7.0, "m": m, "plaka": plaka,
            "deniz": False, "kurum": "AFAD"}


def test_bugun_turkiye_saatine_gore():
    simdi = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)          # 15:00 TR
    olaylar = [
        _olay(datetime(2026, 11, 3, 20, 59, tzinfo=timezone.utc), 1.0),  # 23:59 TR, dün
        _olay(datetime(2026, 11, 3, 21, 1, tzinfo=timezone.utc), 2.5),   # 00:01 TR, bugün
        _olay(datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc), 4.2),
        _olay(datetime(2025, 11, 4, 9, 0, tzinfo=timezone.utc), 3.0),    # geçen yıl, aynı tarihten önce
        _olay(datetime(2025, 11, 5, 9, 0, tzinfo=timezone.utc), 3.0),    # geçen yıl, sonra
    ]
    o = ozet_hesapla(olaylar, simdi)
    assert o["bugun"]["n"] == 2
    assert o["bugun"]["siniflar"] == [0, 1, 0, 1, 0]
    assert o["bugun"]["en_buyuk"]["m"] == 4.2
    assert o["bugun"]["en_buyuk"]["t"] == "2026-11-04T14:00"
    assert o["yil_blok"]["n"] == 3
    assert o["gecen_yil_ayni_doneme_kadar"] == 1
    assert o["iller"]["6"]["yil"] == 3 and o["iller"]["6"]["yil_m3"] == 1
    assert o["gunluk"][-1][0] == "2026-11-04" and o["gunluk"][-1][1] == 2
    assert len(o["gunluk"]) == 365
