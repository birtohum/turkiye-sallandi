/* Türkiye bugün kaç kez sallandı? — tarayıcı tarafı */
(function () {
  "use strict";

  const AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"];
  const AY_KISA = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"];
  const TR_OFSET = 3 * 3600 * 1000; // Türkiye yıl boyu UTC+3
  const sayi = (n) => Number(n).toLocaleString("tr-TR");
  const mag = (m) => Number(m).toFixed(1).replace(".", ",");
  const $ = (id) => document.getElementById(id);

  // Sayılara Türkçe ek: ek(2026, "da") -> "2026'da", ek(1999, "da") -> "1999'da", ek(2023, "da") -> "2023'te"
  const BIR = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"];
  const ON = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"];
  function sonKelime(n) {
    n = Math.abs(Math.round(n));
    if (n === 0) return "sıfır";
    if (n % 10) return BIR[n % 10];
    if (n % 100) return ON[(n % 100) / 10];
    if (n % 1000) return "yüz";
    if (n % 1e6) return "bin";
    return "milyon";
  }
  function ek(n, tip, yazi) {
    const k = sonKelime(n);
    const unlu = [...k].reverse().find((c) => "aeıioöuü".includes(c));
    const ince = "eiöü".includes(unlu);
    const sonHarf = k[k.length - 1];
    const unluBiter = "aeıioöuü".includes(sonHarf);
    const sert = "çfhkpsşt".includes(sonHarf);
    let e;
    if (tip === "da") e = (sert ? "t" : "d") + (ince ? "e" : "a");
    else if (tip === "e") e = (unluBiter ? "y" : "") + (ince ? "e" : "a");
    else { // "i" (belirtme) ve "in" (ilgi)
      const dort = { a: "ı", ı: "ı", e: "i", i: "i", o: "u", u: "u", ö: "ü", ü: "ü" }[unlu];
      e = tip === "i" ? (unluBiter ? "y" : "") + dort : (unluBiter ? "n" : "") + dort + "n";
    }
    return `${yazi != null ? yazi : n}'${e}`;
  }
  // "17:05" -> "17:05'e", "17:00" -> "17:00'ye"
  function saatEk(s, tip) {
    const [sa, dk] = s.split(":").map(Number);
    return ek(dk || sa, tip, s);
  }

  // Türkiye saatine göre bileşenler (tarayıcının saat diliminden bağımsız)
  function trParca(ms) {
    const d = new Date(ms + TR_OFSET);
    return { y: d.getUTCFullYear(), a: d.getUTCMonth(), g: d.getUTCDate(), s: d.getUTCHours(), dk: d.getUTCMinutes() };
  }
  function trGunBasi(ms) {
    const p = trParca(ms);
    return Date.UTC(p.y, p.a, p.g) - TR_OFSET;
  }
  const iki = (n) => String(n).padStart(2, "0");
  function saatYaz(ms) { const p = trParca(ms); return `${iki(p.s)}:${iki(p.dk)}`; }
  function tarihYaz(ms, yilla) {
    const p = trParca(ms);
    return `${p.g} ${AYLAR[p.a]}${yilla ? " " + p.y : ""}`;
  }
  // "2026-05-20T09:00" (Türkiye saati) -> ms
  function yerelMs(s) {
    const [g, z] = s.split("T");
    const [y, a, d] = g.split("-").map(Number);
    const [sa, dk] = (z || "00:00").split(":").map(Number);
    return Date.UTC(y, a - 1, d, sa, dk) - TR_OFSET;
  }
  function olayYaz(o, yilla) {
    if (!o) return "—";
    const ms = yerelMs(o.t);
    return `${mag(o.m)} · ${o.yer} · ${tarihYaz(ms, yilla)} ${saatYaz(ms)}`;
  }

  const durum = { aralik: 7, il: null, caliniyor: null };
  let VERI = {};

  Promise.all(["ozet.json", "son.json", "gecmis.json", "iller.geojson", "komsular.geojson"].map((ad) =>
    fetch(`veri/${ad}`, { cache: "no-cache" }).then((r) => { if (!r.ok) throw new Error(ad); return r.json(); })
  )).then(([ozet, son, gecmis, iller, komsular]) => {
    const A = son.alanlar;
    const olaylar = son.olaylar.map((r) => {
      const o = {}; A.forEach((k, i) => (o[k] = r[i])); o.ms = o.t * 1000; return o;
    });
    VERI = { ozet, son, gecmis, iller, komsular, olaylar, guncelleme: Date.parse(son.guncelleme) };
    VERI.ilAd = {};
    iller.features.forEach((f) => (VERI.ilAd[f.properties.plaka] = f.properties.ad));
    ustKisim();
    sismograf();
    harita();
    ilSecici();
    cizelge();
    merdiven();
    yillar("sayi");
    buyukler();
    dinleKur();
  }).catch((e) => {
    $("bugun-sayi").textContent = "?";
    $("bugun-alt").textContent = "Veri yüklenemedi. Sayfayı biraz sonra yenilemeyi deneyin.";
    console.error(e);
  });

  function yer(o) {
    const ad = VERI.ilAd[o.plaka] || "";
    return o.deniz ? `${ad} açıkları` : ad;
  }

  /* ---------- Üst kısım ---------- */
  function ustKisim() {
    const g = VERI.guncelleme;
    const simdi = Date.now();
    const bugunBas = trGunBasi(simdi);
    const bugun = VERI.olaylar.filter((o) => o.ms >= bugunBas);
    const hafta = VERI.olaylar.filter((o) => o.ms >= g - 7 * 864e5);
    const eski = simdi - g > 12 * 3600e3;
    $("guncelleme").textContent = `son güncelleme ${tarihYaz(g)} ${saatYaz(g)} (Türkiye saati)` + (eski ? " · veri gecikti" : "");

    // Veri gece yarısından önce çekildiyse "bugün" henüz boş olabilir: dürüstçe söyle
    const gunAyni = trGunBasi(g) === bugunBas;
    $("bugun-sayi").textContent = sayi(bugun.length);
    const kucuk = bugun.filter((o) => o.m < 2).length;
    const en = bugun.reduce((a, o) => (!a || o.m > a.m ? o : a), null);
    let metin;
    if (!gunAyni) {
      metin = "Bugünün verisi henüz çekilmedi; birkaç saat içinde güncellenir.";
    } else if (!bugun.length) {
      metin = `Gece yarısından ${saatEk(saatYaz(g), "e")} kadar kayıt yok.`;
    } else {
      metin = `Gece yarısından ${saatEk(saatYaz(g), "e")} kadar. ` +
        (kucuk ? `${sayi(kucuk)} tanesi 2'den küçüktü; onları büyük ihtimalle yalnızca cihazlar fark etti. ` : "") +
        `En büyüğü ${mag(en.m)}, ${yer(en)}, saat ${saatYaz(en.ms)}.`;
    }
    $("bugun-alt").textContent = metin;

    const o = VERI.ozet;
    const not = (liste) => {
      const n3 = liste.filter((x) => x.m >= 3).length;
      return n3 ? `${sayi(n3)} tanesi 3 ve üzeri` : "hiçbiri 3 ve üzeri değil";
    };
    $("s-bugun").textContent = sayi(bugun.length);
    $("s-bugun-not").textContent = bugun.length ? not(bugun) : "";
    $("s-hafta").textContent = sayi(hafta.length);
    $("s-hafta-not").textContent = not(hafta);
    $("s-yil-etiket").textContent = ek(o.yil, "da");
    $("s-yil").textContent = sayi(o.yil_blok.n);
    const y3 = o.yil_blok.siniflar[2] + o.yil_blok.siniflar[3] + o.yil_blok.siniflar[4];
    $("s-yil-not").textContent = `${sayi(y3)} tanesi 3 ve üzeri; geçen yıl aynı tarihe kadar ${sayi(o.gecen_yil_ayni_doneme_kadar)}`;
  }

  /* ---------- Sismograf şeridi (bugün, 24 saat) ---------- */
  function sismograf() {
    const svg = d3.select("#sismo");
    const W = 880, H = 150, orta = H / 2;
    svg.attr("viewBox", `0 0 ${W} ${H}`).attr("preserveAspectRatio", "none");
    const bas = trGunBasi(Date.now());
    const olaylar = VERI.olaylar.filter((o) => o.ms >= bas && o.ms < bas + 864e5);
    const x = (ms) => ((ms - bas) / 864e5) * W;
    const tepe = olaylar.map((o) => ({ x0: x(o.ms), A: Math.min(1, Math.pow(Math.max(o.m, 0.3) / 5.5, 1.6)) * (orta - 6) }));
    const adim = 1;
    const noktalar = [];
    let tohum = 7;
    const gurultu = () => { tohum = (tohum * 9301 + 49297) % 233280; return tohum / 233280 - 0.5; };
    const sonX = Math.min(W, x(VERI.guncelleme));
    for (let px = 0; px <= sonX; px += adim) {
      let y = gurultu() * 1.4;
      for (const t of tepe) {
        const d = px - t.x0;
        if (d >= 0 && d < 40) y += t.A * Math.exp(-d / 7) * Math.sin(d * 1.9);
      }
      noktalar.push([px, orta - y]);
    }
    svg.append("g").selectAll("line").data(d3.range(1, 24)).join("line")
      .attr("class", (h) => "sismo-izgara" + (h % 6 ? "" : " kalin"))
      .attr("x1", (h) => (h / 24) * W).attr("x2", (h) => (h / 24) * W).attr("y1", 0).attr("y2", H);
    svg.append("path").attr("class", "sismo-cizgi").attr("d", d3.line()(noktalar));
    if (sonX < W) svg.append("line").attr("class", "sismo-simdi").attr("x1", sonX).attr("x2", sonX).attr("y1", 6).attr("y2", H - 6).attr("vector-effect", "non-scaling-stroke");
  }

  /* ---------- Harita ---------- */
  let proj, dotKatman, ilKatman, harW, harH;
  const yaricap = (m) => 1.3 + 0.55 * Math.pow(Math.max(m, 0), 1.6);

  function harita() {
    harW = 880; harH = 430;
    const svg = d3.select("#harita").attr("viewBox", `0 0 ${harW} ${harH}`);
    proj = d3.geoMercator().fitExtent([[6, 6], [harW - 6, harH - 6]],
      { type: "MultiPoint", coordinates: [[25.6, 35.7], [44.9, 42.2]] });
    const yol = d3.geoPath(proj);
    svg.append("g").selectAll("path").data(VERI.komsular.features).join("path").attr("class", "komsu").attr("d", yol);
    ilKatman = svg.append("g").selectAll("path").data(VERI.iller.features).join("path")
      .attr("class", "il").attr("d", yol)
      .on("click", (e, f) => ilSec(f.properties.plaka, true));
    ilKatman.append("title").text((f) => f.properties.ad);
    dotKatman = svg.append("g");

    document.querySelectorAll("[data-aralik]").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll("[data-aralik]").forEach((x) => x.classList.toggle("secili", x === b));
      durum.aralik = +b.dataset.aralik;
      noktalariCiz();
    }));
    noktalariCiz();
    lejant();

    // En yakın depremin ipucu (fare/dokunma)
    const ipucu = $("ipucu");
    svg.on("mousemove", (e) => {
      if (!VERI.gorunen || durum.caliniyor) return;
      const [mx, my] = d3.pointer(e);
      let en = null, enD = 14;
      for (const o of VERI.gorunen) {
        const d = Math.hypot(o.px - mx, o.py - my);
        if (d < Math.max(enD, yaricap(o.m) + 2)) { enD = d; en = o; }
      }
      if (!en) { ipucu.hidden = true; return; }
      ipucu.hidden = false;
      ipucu.textContent = `${mag(en.m)} · ${yer(en)} · ${tarihYaz(en.ms)} ${saatYaz(en.ms)}` + (en.derinlik != null ? ` · ${en.derinlik} km derinlik` : "");
      const kutu = svg.node().getBoundingClientRect();
      const olcek = kutu.width / harW;
      ipucu.style.left = Math.min(en.px * olcek + 12, kutu.width - 230) + "px";
      ipucu.style.top = Math.max(en.py * olcek - 40, 4) + "px";
    }).on("mouseleave", () => (ipucu.hidden = true));
  }

  function noktalariCiz(liste) {
    const bitis = VERI.guncelleme;
    const veri = liste || VERI.olaylar.filter((o) => o.ms >= bitis - durum.aralik * 864e5);
    const sirali = veri.slice().sort((a, b) => a.m - b.m);
    sirali.forEach((o) => { const p = proj([o.boylam, o.enlem]); o.px = p[0]; o.py = p[1]; });
    if (!liste) VERI.gorunen = sirali;
    dotKatman.selectAll("circle").data(sirali, (o) => o.t + "_" + o.enlem).join("circle")
      .attr("class", (o) => "dep" + (bitis - o.ms < 864e5 ? " yeni" : ""))
      .attr("cx", (o) => o.px).attr("cy", (o) => o.py).attr("r", (o) => yaricap(o.m));
    if (!liste) {
      const n3 = veri.filter((o) => o.m >= 3).length;
      const ad = { 1: "Son 24 saatte", 7: "Son 7 günde", 30: "Son 30 günde" }[durum.aralik];
      $("harita-not").textContent = `${ad} ${sayi(veri.length)} deprem (${sayi(n3)} tanesi 3 ve üzeri). Koyu turuncu noktalar son 24 saat. Noktanın üstüne gelince ayrıntısı görünür.`;
    }
  }

  function lejant() {
    const l = $("lejant");
    l.innerHTML = "<span>Büyüklük:</span>" + [1, 2, 3, 4, 5].map((m) => {
      const r = yaricap(m);
      return `<span><svg width="${2 * r + 2}" height="${2 * r + 2}"><circle class="dep" cx="${r + 1}" cy="${r + 1}" r="${r}"/></svg>${m}</span>`;
    }).join("");
  }

  /* ---------- Senin ilin ---------- */
  function ilSecici() {
    const sec = $("il-secim");
    const liste = VERI.iller.features.map((f) => f.properties).sort((a, b) => a.ad.localeCompare(b.ad, "tr"));
    sec.innerHTML = liste.map((p) => `<option value="${p.plaka}">${p.ad}</option>`).join("");
    let kayitli = null;
    try { kayitli = +localStorage.getItem("deprem-il"); } catch (e) { /* gizli pencere */ }
    sec.value = String(kayitli && VERI.ilAd[kayitli] ? kayitli : 34);
    sec.addEventListener("change", () => ilSec(+sec.value, false));
    ilSec(+sec.value, false, true);
  }

  function ilSec(plaka, haritadan, ilk) {
    durum.il = plaka;
    $("il-secim").value = String(plaka);
    if (!ilk) { try { localStorage.setItem("deprem-il", String(plaka)); } catch (e) { /* yok say */ } }
    ilKatman.classed("secili-il", (f) => f.properties.plaka === plaka);
    ilKatman.filter((f) => f.properties.plaka === plaka).raise();
    const f = VERI.iller.features.find((x) => x.properties.plaka === plaka);
    const ad = f.properties.ad;
    const oz = VERI.ozet.iller[plaka];
    const gc = VERI.gecmis.iller[plaka];
    const ic30 = VERI.olaylar.filter((o) => o.plaka === plaka);
    const merkez = d3.geoCentroid(f);
    const yakin30 = VERI.olaylar.filter((o) => d3.geoDistance(merkez, [o.boylam, o.enlem]) * 6371 <= 100);
    const yil = VERI.ozet.yil;
    const yakinEn = VERI.gecmis.noktalar.reduce((a, p) =>
      (p[3] > (a ? a[3] : 0) && d3.geoDistance(merkez, [p[2], p[1]]) * 6371 <= 100 ? p : a), null);
    const yakinYaz = yakinEn ? olayYaz({ t: yakinEn[0], m: yakinEn[3], yer: VERI.ilAd[yakinEn[4]] + (yakinEn[5] ? " açıkları" : "") }, true) : "—";
    const sonlar = oz.son.length
      ? `<ul class="il-liste">${oz.son.map((o) => {
          const ms = yerelMs(o.t);
          return `<li><span class="mag">${mag(o.m)}</span><span>${tarihYaz(ms, true)} ${saatYaz(ms)} · ${o.yer}</span></li>`;
        }).join("")}</ul>`
      : "<p>Son bir yılda bu ilin sınırları içinde kayıtlı deprem yok.</p>";
    $("il-kart").innerHTML = `
      <h3>${ad}</h3>
      <div class="il-sayilar">
        <div><span class="n">${sayi(ic30.length)}</span><span class="e">son 30 günde, il sınırları ve kıyı açıkları içinde</span></div>
        <div><span class="n">${sayi(yakin30.length)}</span><span class="e">son 30 günde, il merkezine 100 km'den yakın</span></div>
        <div><span class="n">${sayi(oz.yil)}</span><span class="e">${ek(yil, "da")} il içinde (${sayi(oz.yil_m3)} tanesi 3 ve üzeri)</span></div>
        <div><span class="n">${sayi(gc.m4)}</span><span class="e">1990'dan beri il içinde 4 ve üzeri</span></div>
      </div>
      <p><b>${ek(yil, "in")} en büyüğü:</b> ${olayYaz(oz.en_buyuk_yil, false)}<br>
      <b>1990'dan beri il içinde en büyüğü:</b> ${olayYaz(gc.en_buyuk, true)}<br>
      <b>1990'dan beri il merkezine 100 km'den yakın en büyüğü:</b> ${yakinYaz}</p>
      <p class="kucuk" style="margin-bottom:4px">İl içindeki son depremler:</p>
      ${sonlar}`;
    if (haritadan) $("il-bolum").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /* ---------- Son 365 gün ---------- */
  function cizelge() {
    const veri = VERI.ozet.gunluk.map(([g, n, n3, mx]) => ({ g: yerelMs(g + "T00:00"), gs: g, n, n3, mx }));
    const W = 880, H = 240, m = { s: 10, u: 34, a: 24, sl: 40 };
    const svg = d3.select("#cizelge").attr("viewBox", `0 0 ${W} ${H}`);
    const x = d3.scaleBand().domain(veri.map((d) => d.gs)).range([m.sl, W - m.s]).paddingInner(0.15);
    const enCok = d3.max(veri, (d) => d.n);
    const y = d3.scaleLinear().domain([0, enCok]).nice().range([H - m.a, m.u]);
    svg.append("g").attr("class", "eksen").attr("transform", `translate(${m.sl},0)`)
      .call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.sl - m.s)).tickFormat((v) => sayi(v)))
      .call((g) => g.select(".domain").remove())
      .call((g) => g.selectAll("line").attr("stroke-opacity", 0.5));
    const g = svg.append("g");
    g.selectAll(".cubuk-tum").data(veri).join("rect").attr("class", "cubuk-tum")
      .attr("x", (d) => x(d.gs)).attr("width", x.bandwidth())
      .attr("y", (d) => y(d.n)).attr("height", (d) => y(0) - y(d.n))
      .append("title").text((d) => `${tarihYaz(d.g, true)}: ${sayi(d.n)} deprem, ${sayi(d.n3)} tanesi 3+, en büyüğü ${mag(d.mx)}`);
    g.selectAll(".cubuk-3").data(veri).join("rect").attr("class", "cubuk-3")
      .attr("x", (d) => x(d.gs)).attr("width", x.bandwidth())
      .attr("y", (d) => y(d.n3)).attr("height", (d) => y(0) - y(d.n3)).attr("pointer-events", "none");
    // Ay etiketleri
    const ayBaslari = veri.filter((d) => d.gs.endsWith("-01"));
    svg.append("g").attr("class", "eksen").selectAll("text").data(ayBaslari).join("text")
      .attr("x", (d) => x(d.gs)).attr("y", H - 6)
      .text((d) => { const p = trParca(d.g); return p.a === 0 ? String(p.y) : AY_KISA[p.a]; });
    // En yüksek iki tepe (en az 30 gün arayla)
    const tepeler = [];
    veri.slice().sort((a, b) => b.n - a.n).forEach((d) => {
      if (tepeler.length < 2 && tepeler.every((t) => Math.abs(t.g - d.g) > 30 * 864e5)) tepeler.push(d);
    });
    tepeler.forEach((d) => {
      const xx = x(d.gs) + x.bandwidth() / 2;
      const sag = xx > W * 0.7;
      svg.append("text").attr("class", "etiket-yazi").attr("x", xx + (sag ? -6 : 6)).attr("y", y(d.n) + 4)
        .attr("text-anchor", sag ? "end" : "start")
        .text(`${tarihYaz(d.g, true)}: ${sayi(d.n)} (en büyüğü ${mag(d.mx)})`);
    });
    const ort = d3.median(veri, (d) => d.n);
    $("cizelge-not").textContent = `Sıradan bir günde (ortanca) ${sayi(Math.round(ort))} deprem kaydediliyor. Çubuğun üstüne gelince o günün ayrıntısı görünür.`;
  }

  /* ---------- Büyüklük merdiveni ---------- */
  function merdiven() {
    const d = VERI.ozet.dagilim;
    const sonDolu = d.reduce((a, x, i) => (x.n ? i : a), 0);
    const liste = d.slice(0, sonDolu + 1).filter((x, i) => i > 0 || x.n);
    const enCok = d3.max(liste, (x) => x.n);
    $("merdiven").innerHTML = liste.map((x) => `
      <div class="basamak"><span>${mag(x.m)}–${mag(x.m + 0.4)}</span>
      <span class="cubuk" style="width:${Math.max(0.3, (100 * x.n) / enCok)}%"></span>
      <span class="sayi">${sayi(x.n)}</span></div>`).join("");
    const b1 = d.find((x) => x.m === 1), b4 = d.find((x) => x.m === 4);
    $("merdiven-aciklama").innerHTML = `${VERI.ozet.yil} başından beri kaydedilen depremlerin büyüklüklerine göre dağılımı.
      ${mag(1)}–${mag(1.4)} arasında <b>${sayi(b1.n)}</b>, ${mag(4)}–${mag(4.4)} arasında yalnızca <b>${sayi(b4.n)}</b> deprem var.
      En küçüklerin daha az görünmesi gerçekten az olduklarından değil: o kadar küçük depremlerin hepsini cihazlar yakalayamıyor.`;
  }

  /* ---------- 1990'dan bu yana ---------- */
  function yillar(kip) {
    const G = VERI.gecmis;
    const buYil = VERI.ozet.yil;
    const W = 880, H = 280, m = { s: 10, u: 36, a: 26, sl: 52 };
    const svg = d3.select("#yillar").attr("viewBox", `0 0 ${W} ${H}`);
    svg.selectAll("*").remove();
    const x = d3.scaleBand().domain(G.yillar.map((d) => d.yil)).range([m.sl, W - m.s]).paddingInner(0.2);
    const deger = (d) => (kip === "sayi" ? d.n : d.enerji_m5);
    const y = d3.scaleLinear().domain([0, d3.max(G.yillar, deger)]).nice().range([H - m.a, m.u]);
    svg.append("g").attr("class", "eksen").attr("transform", `translate(${m.sl},0)`)
      .call(d3.axisLeft(y).ticks(4).tickSize(-(W - m.sl - m.s)).tickFormat((v) => sayi(v)))
      .call((g) => g.select(".domain").remove())
      .call((g) => g.selectAll("line").attr("stroke-opacity", 0.5));
    svg.append("g").attr("class", "eksen").selectAll("text").data(G.yillar.filter((d) => d.yil % 5 === 0)).join("text")
      .attr("x", (d) => x(d.yil) + x.bandwidth() / 2).attr("y", H - 8).attr("text-anchor", "middle").text((d) => d.yil);
    svg.append("g").selectAll("rect").data(G.yillar).join("rect")
      .attr("class", (d) => "yil-cubuk" + (d.yil === buYil ? " soluk" : ""))
      .attr("x", (d) => x(d.yil)).attr("width", x.bandwidth())
      .attr("y", (d) => y(deger(d))).attr("height", (d) => Math.max(0, y(0) - y(deger(d))))
      .append("title").text((d) => `${d.yil}${d.yil === buYil ? " (yıl bitmedi)" : ""}: ${sayi(d.n)} deprem (4–4,9: ${d.m4}, 5–5,9: ${d.m5}, 6–6,9: ${d.m6}, 7+: ${d.m7}); enerji ≈ ${sayi(Math.round(d.enerji_m5))} tane 5'lik`);
    const enUst = G.yillar.slice().sort((a, b) => deger(b) - deger(a)).slice(0, 2);
    enUst.forEach((d) => {
      const xx = x(d.yil) + x.bandwidth() / 2;
      const sag = xx > W * 0.7;
      svg.append("text").attr("class", "etiket-yazi").attr("x", sag ? xx + x.bandwidth() / 2 : xx).attr("y", y(deger(d)) - 6)
        .attr("text-anchor", sag ? "end" : "middle").text(`${d.yil}: ${sayi(Math.round(deger(d)))}`);
    });
    document.querySelectorAll("[data-gecmis]").forEach((b) => {
      b.classList.toggle("secili", b.dataset.gecmis === kip);
      b.onclick = () => yillar(b.dataset.gecmis);
    });
    const not = $("yillar-not");
    if (kip === "sayi") {
      not.innerHTML = `Her çubuk bir yıldaki <b>4 ve üzeri</b> deprem sayısı. Büyük bir depremden sonraki aylarda artçılar sayıyı yükseltir (1999, 2011, 2020, 2023).
        ${buYil} çubuğu soluk, çünkü yıl henüz bitmedi.`;
    } else {
      // En büyük yılın enerjisinin ne kadarı tek depremden?
      const y0 = enUst[0];
      const o = G.noktalar.filter((p) => +p[0].slice(0, 4) === y0.yil);
      const enB = o.reduce((a, p) => (p[3] > a ? p[3] : a), 0);
      const pay = Math.round((100 * Math.pow(10, 1.5 * (enB - 5))) / y0.enerji_m5);
      not.innerHTML = `Çubuk, o yıl açığa çıkan toplam enerjiyi “kaç tane 5 büyüklüğündeki deprem” cinsinden gösterir.
        ${ek(y0.yil, "da")} bu sayı yaklaşık <b>${sayi(Math.round(y0.enerji_m5))}</b>; bunun yaklaşık <b>%${ek(pay, "i")}</b> o yılın en büyük tek depreminden (${mag(enB)}) geliyor.
        Logaritmik ölçek yüzünden bir yılın enerjisini neredeyse her zaman birkaç büyük deprem belirler; binlerce küçük deprem toplamda çok az tutar.`;
    }
  }

  function buyukler() {
    const ol = $("buyukler");
    ol.innerHTML = VERI.gecmis.buyukler.slice().reverse().map((o) => {
      const ms = yerelMs(o.t);
      return `<li><span class="mag">${mag(o.m)}</span><span class="tarih">${tarihYaz(ms, true)}</span><span>${o.yer}</span></li>`;
    }).join("");
  }

  /* ---------- Ses: son 7 günü dinle ---------- */
  function dinleKur() {
    const dugme = $("dinle-dugme");
    dugme.addEventListener("click", () => (durum.caliniyor ? durdur() : cal()));
    $("harita-durdur").addEventListener("click", durdur);
  }

  function cal() {
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) { $("dinle-yazi").textContent = "Tarayıcın sesi desteklemiyor"; return; }
    const ctx = new AC();
    const bitis = VERI.guncelleme, bas = bitis - 7 * 864e5;
    const liste = VERI.olaylar.filter((o) => o.ms >= bas).sort((a, b) => a.ms - b.ms);
    const SURE = 20; // saniye
    const ana = ctx.createDynamicsCompressor();
    const ses = ctx.createGain(); ses.gain.value = 0.8;
    ana.connect(ses).connect(ctx.destination);
    const t0 = ctx.currentTime + 0.25;
    liste.forEach((o) => {
      const t = t0 + ((o.ms - bas) / (bitis - bas)) * SURE;
      o.calT = t;
      const m = Math.max(0.2, o.m);
      const frek = 900 * Math.pow(2, -m / 1.3);          // büyük = kalın
      const guc = Math.min(0.9, 0.025 + 0.8 * Math.pow(m / 6, 2.2)); // büyük = yüksek
      const uzun = 0.12 + 0.18 * m;
      const osc = ctx.createOscillator();
      osc.type = m >= 3.5 ? "triangle" : "sine";
      osc.frequency.setValueAtTime(frek * 1.25, t);
      osc.frequency.exponentialRampToValueAtTime(frek, t + 0.05);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(guc, t + 0.008);
      g.gain.exponentialRampToValueAtTime(0.0001, t + uzun);
      osc.connect(g).connect(ana);
      osc.start(t); osc.stop(t + uzun + 0.05);
    });
    durum.caliniyor = { ctx, liste, t0, SURE, bas, bitis };
    const dugme = $("dinle-dugme");
    dugme.setAttribute("aria-pressed", "true");
    dugme.querySelector(".dugme-ikon").textContent = "■";
    $("harita-durdur").hidden = false;
    // Harita: 7 gün görünümüne geç, noktalar sesle birlikte belirsin
    document.querySelectorAll("[data-aralik]").forEach((x) => x.classList.toggle("secili", x.dataset.aralik === "7"));
    durum.aralik = 7;
    noktalariCiz([]);
    $("harita-bolum").scrollIntoView({ behavior: "smooth", block: "start" });
    let sonN = -1;
    const kare = () => {
      const c = durum.caliniyor;
      if (!c) return;
      const simdi = c.ctx.currentTime;
      const n = d3.bisector((o) => o.calT).right(c.liste, simdi);
      if (n !== sonN) {
        sonN = n;
        noktalariCiz(c.liste.slice(0, n));
        dotKatman.selectAll("circle").classed("cal", (o) => simdi - o.calT < 0.35);
        const anMs = c.bas + Math.min(1, Math.max(0, (simdi - c.t0) / c.SURE)) * (c.bitis - c.bas);
        $("dinle-yazi").textContent = `${tarihYaz(anMs)} ${saatYaz(anMs)} · ${sayi(n)}. deprem — durdur`;
        $("harita-not").textContent = `Dinleniyor: ${tarihYaz(anMs)} ${saatYaz(anMs)}, ${sayi(n)} deprem.`;
      }
      if (simdi > c.t0 + c.SURE + 1) { durdur(); return; }
      requestAnimationFrame(kare);
    };
    requestAnimationFrame(kare);
  }

  function durdur() {
    const c = durum.caliniyor;
    durum.caliniyor = null;
    if (c) c.ctx.close();
    const dugme = $("dinle-dugme");
    dugme.setAttribute("aria-pressed", "false");
    dugme.querySelector(".dugme-ikon").textContent = "▶";
    $("harita-durdur").hidden = true;
    $("dinle-yazi").textContent = "Son 7 günü dinle";
    noktalariCiz();
  }
})();
