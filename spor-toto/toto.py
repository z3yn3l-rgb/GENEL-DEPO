#!/usr/bin/env python3
"""
Spor Toto kupon asistanı.

Komutlar:
  kupon   Haftanın maç dosyasından, kolon bütçesine göre 15 bilme ihtimalini
          en yükseğe çıkaran kuponu (tek/çift/üçlü seçimleri) hesaplar.
  sonuc   Hafta bitince gerçek sonuçları girip kuponun kaç tuttuğunu kaydeder.
  rapor   Geçmiş haftalardan gerçek isabet oranını ve tahminlerin ne kadar
          güvenilir olduğunu gösterir.

Örnek:
  python3 toto.py kupon ornek_hafta.csv --kolon 256 --kolon-fiyati 5
  python3 toto.py sonuc ornek_hafta.csv 1X21102X1112012 --kolon 256
  python3 toto.py rapor

Maç dosyası (CSV) sütunları:
  mac, ev, deplasman, oran1, oranX, oran2  -> iddaa oranları (zorunlu)
  p1, pX, p2  -> isteğe bağlı, senin/Claude'un yüzde olarak düzeltilmiş tahmini.
                 Doluysa oranların yerine bunlar kullanılır.
  not         -> sakatlık, kadro, motivasyon gibi notlar

NOT: Hiçbir hesap 15 bilmeyi garanti etmez. Bu araç tahminlerini en iyi
şekilde kupona dökmek ve gerçek başarını ölçmek içindir.
"""

import argparse
import csv
import math
import os
from datetime import date

SONUCLAR = ("1", "X", "2")
GECMIS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gecmis.csv")


def sayi(deger):
    deger = (deger or "").strip().replace(",", ".")
    return float(deger) if deger else None


def maclari_oku(yol):
    maclar = []
    with open(yol, encoding="utf-8") as f:
        for satir in csv.DictReader(f):
            elle = [sayi(satir.get(k)) for k in ("p1", "pX", "p2")]
            if all(p is not None for p in elle):
                ham = elle
                kaynak = "elle"
            else:
                oranlar = [sayi(satir.get(k)) for k in ("oran1", "oranX", "oran2")]
                if any(o is None or o <= 1 for o in oranlar):
                    raise SystemExit(f"{satir.get('mac')}. maçta oran ya da p1/pX/p2 eksik.")
                ham = [1 / o for o in oranlar]  # bahis şirketi marjı aşağıda temizleniyor
                kaynak = "oran"
            toplam = sum(ham)
            maclar.append({
                "mac": satir.get("mac", str(len(maclar) + 1)).strip(),
                "ad": f"{satir.get('ev', '').strip()} - {satir.get('deplasman', '').strip()}",
                "olasilik": [p / toplam for p in ham],
                "kaynak": kaynak,
                "not": (satir.get("not") or "").strip(),
            })
    if len(maclar) != 15:
        print(f"Uyarı: dosyada {len(maclar)} maç var, Spor Toto 15 maçtır.")
    return maclar


def secenekler(olasilik):
    """Bir maç için tek, çift ve üçlü seçim seçenekleri (en olası sonuçlardan başlayarak)."""
    sirali = sorted(range(3), key=lambda i: -olasilik[i])
    return [
        ("".join(SONUCLAR[i] for i in sorted(sirali[:k])), k, sum(olasilik[i] for i in sirali[:k]))
        for k in (1, 2, 3)
    ]


def kupon_olustur(maclar, butce):
    """Kolon sayısı bütçeyi aşmadan, 15'in de tutma ihtimalini en yükseğe çıkarır (DP)."""
    durumlar = {1: (0.0, [])}  # kolon sayısı -> (log ihtimal, seçimler)
    for mac in maclar:
        yeni = {}
        for kolon, (puan, secim) in durumlar.items():
            for etiket, k, q in secenekler(mac["olasilik"]):
                yk = kolon * k
                if yk > butce or q <= 0:
                    continue
                yp = puan + math.log(q)
                if yk not in yeni or yp > yeni[yk][0]:
                    yeni[yk] = (yp, secim + [(etiket, q)])
        durumlar = yeni
    kolon, (puan, secim) = max(durumlar.items(), key=lambda d: d[1][0])
    return kolon, secim


def dagilim(qlar):
    """Tutan maç sayısının dağılımı (her maç bağımsız)."""
    d = [1.0]
    for q in qlar:
        yeni = [0.0] * (len(d) + 1)
        for i, p in enumerate(d):
            yeni[i] += p * (1 - q)
            yeni[i + 1] += p * q
        d = yeni
    return d


def kupon_komutu(a):
    maclar = maclari_oku(a.dosya)
    kolon, secim = kupon_olustur(maclar, a.kolon)
    print("=" * 72)
    print(f" KUPON  ({kolon} kolon" + (f", {kolon * a.kolon_fiyati:,.2f} TL" if a.kolon_fiyati else "") + ")")
    print("=" * 72)
    for mac, (etiket, q) in zip(maclar, secim):
        olas = " ".join(f"{s}:%{p * 100:4.1f}" for s, p in zip(SONUCLAR, mac["olasilik"]))
        isaret = "*" if mac["kaynak"] == "elle" else " "
        print(f" {mac['mac']:>2}. {mac['ad'][:30]:<30} [{etiket:^3}] %{q * 100:5.1f}  {olas}{isaret}")
        if mac["not"]:
            print(f"      not: {mac['not']}")
    print(" (* = oran yerine elle girilmiş tahmin)")

    d = dagilim([q for _, q in secim])
    n = len(secim)
    print()
    for hedef in range(n, max(n - 4, 0) - 1, -1):
        p = sum(d[hedef:])
        bir = f"~{1 / p:,.0f} haftada 1" if p > 0 else "-"
        print(f"  En az {hedef:>2} bilme ihtimali: %{p * 100:7.3f}   ({bir})")
    print()
    print(" Bu ihtimaller girdiğin olasılıklar doğruysa geçerlidir. Gerçek başarını")
    print(" görmek için hafta bitince 'sonuc' komutunu, birkaç hafta sonra 'rapor'u çalıştır.")


def sonuc_komutu(a):
    maclar = maclari_oku(a.dosya)
    sonuclar = a.sonuclar.upper().replace("0", "X")
    if len(sonuclar) != len(maclar) or any(s not in SONUCLAR for s in sonuclar):
        raise SystemExit(f"Sonuçlar {len(maclar)} karakter olmalı ve yalnızca 1, X(ya da 0), 2 içermeli.")
    _, secim = kupon_olustur(maclar, a.kolon)

    yeni_dosya = not os.path.exists(GECMIS)
    tutan = 0
    with open(GECMIS, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni_dosya:
            w.writerow(["tarih", "hafta", "mac", "secim", "secim_olasiligi", "favori",
                        "favori_olasiligi", "sonuc", "tuttu"])
        for mac, (etiket, q), sonuc in zip(maclar, secim, sonuclar):
            fav_i = max(range(3), key=lambda i: mac["olasilik"][i])
            tuttu = sonuc in etiket
            tutan += tuttu
            w.writerow([date.today().isoformat(), os.path.basename(a.dosya), mac["mac"], etiket,
                        f"{q:.4f}", SONUCLAR[fav_i], f"{mac['olasilik'][fav_i]:.4f}", sonuc, int(tuttu)])
    print(f"Kuponun en iyi kolonu {tutan}/{len(maclar)} bildi. Kaydedildi: {GECMIS}")


def rapor_komutu(_):
    if not os.path.exists(GECMIS):
        raise SystemExit("Henüz kayıt yok. Önce 'sonuc' komutuyla bir hafta kaydet.")
    with open(GECMIS, encoding="utf-8") as f:
        satirlar = list(csv.DictReader(f))

    haftalar = {}
    for s in satirlar:
        haftalar.setdefault((s["tarih"], s["hafta"]), []).append(s)

    print("=" * 60)
    print(" GEÇMİŞ RAPORU")
    print("=" * 60)
    for (tarih, hafta), ss in haftalar.items():
        kupon = sum(int(s["tuttu"]) for s in ss)
        tek = sum(s["favori"] == s["sonuc"] for s in ss)
        print(f" {tarih} {hafta:<25} kupon: {kupon:>2}/{len(ss)}   tek kolon (favoriler): {tek:>2}/{len(ss)}")

    n = len(satirlar)
    isabet = sum(s["favori"] == s["sonuc"] for s in satirlar) / n
    beklenen = sum(float(s["favori_olasiligi"]) for s in satirlar) / n
    print()
    print(f" Toplam {n} maç, {len(haftalar)} hafta")
    print(f" Gerçek tek tahmin isabeti : %{isabet * 100:.1f}")
    print(f" Tahminlerin beklediği     : %{beklenen * 100:.1f}")
    print(f" Bu isabetle tek kolonda 15: ~{1 / isabet ** 15:,.0f} haftada 1" if isabet else "")

    print()
    print(" Güvenilirlik (tahmin edilen olasılık -> gerçekleşen):")
    for alt, ust in ((0, .4), (.4, .5), (.5, .6), (.6, .7), (.7, 1.01)):
        grup = [s for s in satirlar if alt <= float(s["favori_olasiligi"]) < ust]
        if grup:
            g = sum(s["favori"] == s["sonuc"] for s in grup) / len(grup)
            print(f"   %{alt * 100:3.0f}-%{min(ust, 1) * 100:3.0f}: {len(grup):>3} maç, gerçekleşen %{g * 100:5.1f}")
    print()
    if len(haftalar) < 10:
        print(" Not: 10 haftadan az veri var, sonuçlar henüz güvenilir değil.")
    if isabet <= beklenen:
        print(" Elle girilen bilgiler şimdilik oranların ötesinde bir avantaj göstermiyor.")
    else:
        print(" Gerçek isabetin oranların beklediğinden yüksek; veri arttıkça bunu takip et.")


def main():
    p = argparse.ArgumentParser(description="Spor Toto kupon asistanı")
    alt = p.add_subparsers(dest="komut", required=True)

    k = alt.add_parser("kupon", help="Haftanın kuponunu oluştur")
    k.add_argument("dosya")
    k.add_argument("--kolon", type=int, default=1, help="En fazla kolon sayısı (bütçe)")
    k.add_argument("--kolon-fiyati", type=float, default=None, help="Bir kolonun fiyatı (TL)")
    k.set_defaults(f=kupon_komutu)

    s = alt.add_parser("sonuc", help="Gerçek sonuçları kaydet")
    s.add_argument("dosya")
    s.add_argument("sonuclar", help="Ör. 1X21102X1112012 (X yerine 0 da yazılabilir)")
    s.add_argument("--kolon", type=int, default=1, help="Kuponu oluştururken kullandığın kolon sayısı")
    s.set_defaults(f=sonuc_komutu)

    r = alt.add_parser("rapor", help="Geçmiş başarıyı göster")
    r.set_defaults(f=rapor_komutu)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
