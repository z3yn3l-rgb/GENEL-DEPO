#!/usr/bin/env python3
"""
Ağırlıklı tahmin modeli ve geçmiş haftalar üzerinde ileriye dönük test.

Her maçın olasılığı üç kaynağın ağırlıklı ortalamasıdır:
  %50  Bu sezonun geçmiş sonuçları: sadece o haftadan ÖNCEKİ sonuçlardan
       öğrenilen Elo puanları (tüm takımlar eşit puanla başlar).
  %40  Claude'un kendi bilgisi: sezon öncesi güç puanları (guc.csv).
  %10  Oyuncu tercih yüzdeleri (haftaNN_tercih.csv varsa). Yoksa bu pay
       diğer iki kaynağa oranlarına göre dağıtılır.

Tek kolon seçimi: en olası sonuç; ama ev sahibi ve deplasman olasılıkları
birbirine yakınsa (fark < --x-esigi puan) beraberlik (X) yazılır.

Kullanım:
  python3 agirlikli.py
  python3 agirlikli.py --x-esigi 8
"""

import argparse
import csv
import os

from bulten import KLASOR, bultenleri_oku, guc_oku, olasilik
from guncelle import guncelle, sonuclari_oku

AGIRLIK = {"sonuc": 0.50, "bilgi": 0.40, "tercih": 0.10}
BASLANGIC = 1600


def tercih_oku(ad):
    yol = os.path.join(KLASOR, f"{ad}_tercih.csv")
    if not os.path.exists(yol):
        return None
    with open(yol, encoding="utf-8") as f:
        return [[float(s[k]) for k in ("p1", "pX", "p2")] for s in csv.DictReader(f)]


def birlestir(kaynaklar):
    """kaynaklar: {ad: olasılık listesi ya da None}. Eksik kaynağın payı dağıtılır."""
    mevcut = {k: v for k, v in kaynaklar.items() if v is not None}
    toplam_agirlik = sum(AGIRLIK[k] for k in mevcut)
    return [sum(AGIRLIK[k] * v[i] for k, v in mevcut.items()) / toplam_agirlik for i in range(3)]


def sec(p, esik):
    if abs(p[0] - p[2]) < esik:
        return "X"
    return "1X2"[p.index(max(p))]


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--x-esigi", type=float, default=8)
    a.add_argument("--k", type=float, default=40)
    a = a.parse_args()

    bilgi = guc_oku()
    sezon = {t: (BASLANGIC, lig) for t, (_, lig) in bilgi.items()}
    sonuclar = sonuclari_oku()
    satirlar = []

    print(f"{'Hafta':<8}{'Tahmin':<18}{'Gerçek':<18}{'Doğru':>6}")
    toplam = dogru = 0
    for ad, maclar in bultenleri_oku().items():
        tercih = tercih_oku(ad)
        tahmin = ""
        for i, (ev, dep) in enumerate(maclar):
            p = birlestir({
                "sonuc": olasilik(ev, dep, sezon),
                "bilgi": olasilik(ev, dep, bilgi),
                "tercih": tercih[i] if tercih else None,
            })
            tahmin += sec(p, a.x_esigi)
            satirlar.append((ad, i + 1, ev, dep, p, tahmin[-1]))
        gercek = sonuclar.get(ad)
        if gercek:
            oynanan = sum(g in "1X2" for g in gercek)  # "-" = henüz oynanmadı
            d = sum(t == g for t, g in zip(tahmin, gercek))
            toplam += oynanan
            dogru += d
            print(f"{ad:<8}{tahmin:<18}{gercek:<18}{d:>4}/{oynanan}")
            for (ev, dep), s in zip(maclar, gercek):  # tahminden SONRA öğren
                if s in "1X2":
                    guncelle(sezon, ev, dep, s, a.k)
        else:
            print(f"{ad:<8}{tahmin:<18}{'(sonuç yok)':<18}")
    print(f"\nToplam: {dogru}/{toplam}  (%{100 * dogru / toplam:.1f}),"
          f" haftalık ortalama {15 * dogru / toplam:.1f} doğru")

    with open(os.path.join(KLASOR, "agirlikli_tahminler.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["hafta", "mac", "ev", "deplasman", "p1", "pX", "p2", "tahmin"])
        for ad, i, ev, dep, p, t in satirlar:
            w.writerow([ad, i, ev, dep, *(f"{x:.1f}" for x in p), t])


if __name__ == "__main__":
    main()
