#!/usr/bin/env python3
"""
Bültenleri ve takım güç puanlarını (guc.csv) kullanarak her hafta için
toto.py'nin okuyabileceği maç dosyası (haftaNN.csv) üretir.

Olasılıklar Elo mantığıyla hesaplanır: ev sahibine lige göre avantaj puanı
eklenir, güç farkından galibiyet beklentisi, beklentiye göre de beraberlik
payı çıkarılır. Yeni bilgi (sakatlık, transfer, hoca değişikliği) gelince
guc.csv'deki puanı değiştirip bu scripti tekrar çalıştırmak yeterli.

Kullanım:
  python3 bulten.py
"""

import csv
import os

KLASOR = os.path.dirname(os.path.abspath(__file__))
EV_AVANTAJI = {"TR": 70, "EN": 60, "ES": 60, "DE": 60, "FR": 60, "IT": 60, "MILLI": 90}


def guc_oku():
    with open(os.path.join(KLASOR, "guc.csv"), encoding="utf-8") as f:
        return {s["takim"]: (float(s["guc"]), s["lig"]) for s in csv.DictReader(f)}


def olasilik(ev, dep, guc):
    (g_ev, lig), (g_dep, _) = guc[ev], guc[dep]
    fark = g_ev + EV_AVANTAJI[lig] - g_dep
    beklenti = 1 / (1 + 10 ** (-fark / 400))
    beraberlik = max(0.12, 0.29 - 0.35 * abs(beklenti - 0.5))
    p1 = max(0.03, beklenti - beraberlik / 2)
    p2 = max(0.03, 1 - beklenti - beraberlik / 2)
    toplam = p1 + beraberlik + p2
    return [p / toplam * 100 for p in (p1, beraberlik, p2)]


def bultenleri_oku():
    haftalar, ad = {}, None
    with open(os.path.join(KLASOR, "bultenler.txt"), encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if not satir or satir.startswith("#"):
                continue
            if satir.startswith("["):
                ad = satir[1:satir.index("]")]
                haftalar[ad] = []
            else:
                ev, dep = (t.strip() for t in satir.split(" - "))
                haftalar[ad].append((ev, dep))
    return haftalar


def main():
    guc = guc_oku()
    for ad, maclar in bultenleri_oku().items():
        eksik = {t for m in maclar for t in m if t not in guc}
        if eksik:
            raise SystemExit(f"{ad}: guc.csv'de olmayan takım(lar): {', '.join(sorted(eksik))}")
        yol = os.path.join(KLASOR, f"{ad}.csv")
        with open(yol, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["mac", "ev", "deplasman", "oran1", "oranX", "oran2", "p1", "pX", "p2", "not"])
            for i, (ev, dep) in enumerate(maclar, 1):
                p1, px, p2 = olasilik(ev, dep, guc)
                w.writerow([i, ev, dep, "", "", "", f"{p1:.1f}", f"{px:.1f}", f"{p2:.1f}", ""])
        print(f"{yol} yazıldı ({len(maclar)} maç)")


if __name__ == "__main__":
    main()
