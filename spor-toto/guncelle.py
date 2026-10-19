#!/usr/bin/env python3
"""
Sezon içi güncellenen model.

Her haftayı sırayla oynatır: önce o haftanın maçlarını o ana kadarki güç
puanlarıyla tahmin eder, sonra gerçek sonuçla puanları Elo kuralıyla
günceller. Böylece her tahmin yalnızca o haftadan önceki bilgiyle yapılmış
olur (ileriye dönük test). Sonda sonuçları henüz girilmemiş haftalar için
güncel puanlarla maç dosyası (haftaNN_guncel.csv) üretir.

Kullanım:
  python3 guncelle.py            # varsayılan K=30
  python3 guncelle.py --k 20
"""

import argparse
import csv
import os

from bulten import EV_AVANTAJI, KLASOR, bultenleri_oku, guc_oku, olasilik


def sonuclari_oku():
    sonuclar = {}
    with open(os.path.join(KLASOR, "sonuclar.txt"), encoding="utf-8") as f:
        for satir in f:
            if satir.startswith("hafta"):
                ad, s = satir.split(":")
                sonuclar[ad.strip()] = s.strip().upper().replace("0", "X")
    return sonuclar


def guncelle(guc, ev, dep, sonuc, k):
    (g_ev, lig), (g_dep, lig_dep) = guc[ev], guc[dep]
    fark = g_ev + EV_AVANTAJI[lig] - g_dep
    beklenti = 1 / (1 + 10 ** (-fark / 400))
    gercek = {"1": 1.0, "X": 0.5, "2": 0.0}[sonuc]
    degisim = k * (gercek - beklenti)
    guc[ev] = (g_ev + degisim, lig)
    guc[dep] = (g_dep - degisim, lig_dep)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=float, default=30, help="Güncelleme hızı (0 = güncelleme yok)")
    p.add_argument("--sessiz", action="store_true")
    a = p.parse_args()

    guc = guc_oku()
    sonuclar = sonuclari_oku()
    toplam = dogru = 0
    for ad, maclar in bultenleri_oku().items():
        if ad not in sonuclar:
            yol = os.path.join(KLASOR, f"{ad}_guncel.csv")
            with open(yol, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["mac", "ev", "deplasman", "oran1", "oranX", "oran2", "p1", "pX", "p2", "not"])
                for i, (ev, dep) in enumerate(maclar, 1):
                    p1, px, p2 = olasilik(ev, dep, guc)
                    w.writerow([i, ev, dep, "", "", "", f"{p1:.1f}", f"{px:.1f}", f"{p2:.1f}",
                                f"guncel guc {guc[ev][0]:.0f} - {guc[dep][0]:.0f}"])
            if not a.sessiz:
                print(f"{ad}: sonuç yok, {yol} yazıldı")
            continue
        hafta_dogru = 0
        for (ev, dep), sonuc in zip(maclar, sonuclar[ad]):
            olas = olasilik(ev, dep, guc)
            tahmin = "1X2"[olas.index(max(olas))]
            hafta_dogru += tahmin == sonuc
            guncelle(guc, ev, dep, sonuc, a.k)
        toplam += len(maclar)
        dogru += hafta_dogru
        if not a.sessiz:
            print(f"{ad}: {hafta_dogru}/15")
    print(f"K={a.k:g}: toplam {dogru}/{toplam} (%{100 * dogru / toplam:.1f})")

    if not a.sessiz:
        print("\nSüper Lig güncel güç sıralaması:")
        tr = sorted(((g, t) for t, (g, l) in guc.items() if l == "TR"), reverse=True)
        for i, (g, t) in enumerate(tr, 1):
            print(f"  {i:>2}. {t:<15} {g:6.0f}")


if __name__ == "__main__":
    main()
