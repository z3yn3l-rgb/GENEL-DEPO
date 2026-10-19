#!/usr/bin/env python3
"""
Araba alım planlayıcı.

Aylık gelir, birikim ve kredi koşullarına göre 500-650 bin TL arası bir
araba için kaç ay biriktirmen gerektiğini, kredi taksitlerini ve
bütçene uygun olup olmadığını hesaplar.

Örnek:
    python3 araba_plani.py
    python3 araba_plani.py --gelir 70000 --birikim 150000 --aylik-birikim 20000
    python3 araba_plani.py --faiz 2.8 --fiyat-artisi 1.5

NOT: Kredi faiz oranı ve BDDK taşıt kredisi limitleri sık değişir.
Varsayılan değerleri bankandan güncel bilgiyle kontrol et.
"""

import argparse

# BDDK taşıt kredisi kuralları: (fiyat üst sınırı, kredilendirilebilir oran, en uzun vade/ay)
# Fiyat bu sınıra kadarsa ilgili satır geçerli. Güncel değerleri kontrol et.
KREDI_KADEMELERI = [
    (400_000, 0.70, 48),
    (800_000, 0.50, 36),
    (1_200_000, 0.30, 24),
    (2_000_000, 0.20, 12),
]

KKDF = 0.15  # Kaynak Kullanımını Destekleme Fonu (faiz üzerinden)
BSMV = 0.15  # Banka ve Sigorta Muameleleri Vergisi (faiz üzerinden)


def tl(tutar):
    return f"{tutar:,.0f} TL".replace(",", ".")


def kredi_kosullari(fiyat):
    for ust_sinir, oran, vade in KREDI_KADEMELERI:
        if fiyat <= ust_sinir:
            return oran, vade
    return 0.0, 0


def aylik_taksit(anapara, aylik_faiz_yuzde, vade):
    if anapara <= 0 or vade <= 0:
        return 0.0
    r = aylik_faiz_yuzde / 100 * (1 + KKDF + BSMV)
    if r == 0:
        return anapara / vade
    return anapara * r / (1 - (1 + r) ** -vade)


def biriktirme_suresi(hedef_fn, birikim, aylik_birikim, mevduat_yuzde, max_ay=120):
    """Birikimin hedefe (zamanla artabilen) ulaşacağı ay sayısını döndürür."""
    for ay in range(max_ay + 1):
        if birikim >= hedef_fn(ay):
            return ay, birikim
        birikim = birikim * (1 + mevduat_yuzde / 100) + aylik_birikim
    return None, birikim


def senaryo(fiyat, a):
    oran, max_vade = kredi_kosullari(fiyat)
    vade = min(a.vade, max_vade) if a.vade else max_vade
    artis = a.fiyat_artisi / 100

    def gelecek_fiyat(ay):
        return fiyat * (1 + artis) ** ay

    # 1) Kredili alım: en az peşinatı biriktir, kalanını krediyle öde
    pesinat_ay, _ = biriktirme_suresi(
        lambda ay: gelecek_fiyat(ay) * (1 - oran), a.birikim, a.aylik_birikim, a.mevduat
    )
    if pesinat_ay is not None:
        alis_fiyati = gelecek_fiyat(pesinat_ay)
        kredi = alis_fiyati * oran
        taksit = aylik_taksit(kredi, a.faiz, vade)
        toplam_odeme = alis_fiyati * (1 - oran) + taksit * vade
    else:
        alis_fiyati = kredi = taksit = toplam_odeme = None

    # 2) Peşin alım: tamamını biriktir
    pesin_ay, _ = biriktirme_suresi(gelecek_fiyat, a.birikim, a.aylik_birikim, a.mevduat)

    return {
        "fiyat": fiyat,
        "oran": oran,
        "vade": vade,
        "pesinat_ay": pesinat_ay,
        "alis_fiyati": alis_fiyati,
        "kredi": kredi,
        "taksit": taksit,
        "toplam_odeme": toplam_odeme,
        "pesin_ay": pesin_ay,
        "pesin_fiyat": gelecek_fiyat(pesin_ay) if pesin_ay is not None else None,
    }


def ay_metni(ay):
    if ay is None:
        return "10 yılda bile yetişmiyor"
    if ay == 0:
        return "hemen alabilirsin"
    yil, kalan = divmod(ay, 12)
    parcalar = []
    if yil:
        parcalar.append(f"{yil} yıl")
    if kalan:
        parcalar.append(f"{kalan} ay")
    return " ".join(parcalar)


def main():
    p = argparse.ArgumentParser(description="Araba alım planlayıcı")
    p.add_argument("--gelir", type=float, default=70_000, help="Aylık net gelir (TL)")
    p.add_argument("--birikim", type=float, default=0, help="Şu anki birikim (TL)")
    p.add_argument("--aylik-birikim", type=float, default=None,
                   help="Her ay kenara koyabileceğin tutar (varsayılan: gelirin %%30'u)")
    p.add_argument("--min-fiyat", type=float, default=500_000)
    p.add_argument("--max-fiyat", type=float, default=650_000)
    p.add_argument("--adim", type=float, default=50_000, help="Fiyat aralığı adımı")
    p.add_argument("--faiz", type=float, default=3.0, help="Aylık taşıt kredisi faizi (%%)")
    p.add_argument("--vade", type=int, default=0, help="İstenen vade (ay); 0 = yasal azami")
    p.add_argument("--mevduat", type=float, default=0.0,
                   help="Birikimin aylık getirisi (%%), ör. mevduat faizi")
    p.add_argument("--fiyat-artisi", type=float, default=0.0,
                   help="Araba fiyatlarının aylık artışı (%%), enflasyon etkisi")
    p.add_argument("--isletme", type=float, default=10_000,
                   help="Aylık işletme gideri: yakıt, sigorta, kasko, MTV, bakım (TL)")
    p.add_argument("--max-oran", type=float, default=35,
                   help="Araba için gelirin en fazla yüzde kaçı harcansın (%%)")
    a = p.parse_args()

    if a.aylik_birikim is None:
        a.aylik_birikim = a.gelir * 0.30

    butce_limiti = a.gelir * a.max_oran / 100

    print("=" * 64)
    print(" ARABA ALIM PLANI")
    print("=" * 64)
    print(f" Aylık gelir           : {tl(a.gelir)}")
    print(f" Mevcut birikim        : {tl(a.birikim)}")
    print(f" Aylık biriktirilecek  : {tl(a.aylik_birikim)}")
    print(f" Kredi faizi (aylık)   : %{a.faiz} (+%{(KKDF + BSMV) * 100:.0f} KKDF/BSMV)")
    print(f" İşletme gideri (aylık): {tl(a.isletme)}")
    print(f" Araba bütçe sınırı    : {tl(butce_limiti)}/ay (gelirin %{a.max_oran:.0f}'i)")
    if a.fiyat_artisi:
        print(f" Fiyat artışı (aylık)  : %{a.fiyat_artisi}")
    print()

    en_iyi = None
    fiyat = a.min_fiyat
    while fiyat <= a.max_fiyat + 1e-6:
        s = senaryo(fiyat, a)
        print("-" * 64)
        print(f" {tl(fiyat)} değerinde araba")
        print("-" * 64)

        if s["oran"] == 0:
            print("  Bu fiyatta taşıt kredisi kullanılamıyor.")
        elif s["pesinat_ay"] is None:
            print("  Peşinatı 10 yıl içinde biriktiremiyorsun.")
        else:
            aylik_yuk = s["taksit"] + a.isletme
            yuk_orani = aylik_yuk / a.gelir * 100
            uygun = aylik_yuk <= butce_limiti
            print(f"  [Kredili] Peşinat süresi : {ay_metni(s['pesinat_ay'])}")
            if a.fiyat_artisi and s["pesinat_ay"]:
                print(f"            O zamanki fiyat: {tl(s['alis_fiyati'])}")
            print(f"            Peşinat        : {tl(s['alis_fiyati'] * (1 - s['oran']))}"
                  f" (%{(1 - s['oran']) * 100:.0f})")
            print(f"            Kredi          : {tl(s['kredi'])}, {s['vade']} ay vade")
            print(f"            Aylık taksit   : {tl(s['taksit'])}")
            print(f"            Toplam maliyet : {tl(s['toplam_odeme'])}"
                  f" (faiz yükü {tl(s['toplam_odeme'] - s['alis_fiyati'])})")
            print(f"            Taksit+işletme : {tl(aylik_yuk)} = gelirin %{yuk_orani:.1f}"
                  f"  -> {'UYGUN' if uygun else 'RİSKLİ'}")
            if uygun:
                en_iyi = (fiyat, s)

        print(f"  [Peşin]   Biriktirme süresi: {ay_metni(s['pesin_ay'])}"
              + (f" (o zamanki fiyat {tl(s['pesin_fiyat'])})"
                 if a.fiyat_artisi and s["pesin_ay"] else ""))
        print()
        fiyat += a.adim

    print("=" * 64)
    print(" ÖNERİ")
    print("=" * 64)
    if en_iyi:
        fiyat, s = en_iyi
        print(f" Bütçene uyan en pahalı seçenek: {tl(fiyat)}")
        print(f" {ay_metni(s['pesinat_ay'])} sonra peşinatı tamamlayıp"
              f" {s['vade']} ay boyunca {tl(s['taksit'])} taksit ödersin.")
    else:
        print(" Bu aralıktaki hiçbir seçenek taksit+işletme gideri açısından")
        print(f" gelirinin %{a.max_oran:.0f}'ini aşmadan karşılanamıyor.")
        print(" Daha uzun biriktirip daha büyük peşinat vermeyi, peşin almayı")
        print(" ya da daha uygun fiyatlı bir araç bakmayı düşünebilirsin.")
    print()
    print(" Uyarı: Faiz oranları ve BDDK kredi limitleri değişebilir;")
    print(" kesin rakamlar için bankandan teklif al.")


if __name__ == "__main__":
    main()
