"""
PROJECT AURELIUS - TEK SEFERLIK CANLI TEST EMRI SCRIPTI
========================================================
Amac: project_aurelius_bot_v17.py icindeki Binance TR CANLI MOD
fonksiyonlarini (binance_serbest_try_bakiyesi, sembol_filtrelerini_getir,
binance_gercek_emir_gonder) kullanarak, TAM BOT DONGUSUNU ACMADAN, TEK ve
KUCUK bir test MARKET ALIM emri gonderip ORDER_ENDPOINT_PATH ile side/type
sayisal kod eslemesinin GERCEKTEN dogru oldugunu izole bir sekilde
dogrulamak.

BU SCRIPT SADECE SIZIN KENDI ORTAMINIZDA (gercek internet erisimi + gercek
API anahtarlariniz ile) ISE YARAR. Bu dosyayi ureten Claude oturumunun ne
Binance TR'ye ag erisimi ne de herhangi bir API anahtariniz vardir - bu
yuzden emri Claude gonderemez, SIZ gondermelisiniz.

GUVENLIK ONLEMLERI:
  1) MAKS_TEST_TUTARI_TRY sinirini (varsayilan 50 TRY) asan hicbir test
     emri GONDERILMEZ - sembolun minNotional'i bu siniri asiyorsa script
     kendini durdurur.
  2) Emri gondermeden ONCE tam bir ozet (sembol/yon/miktar/tahmini tutar/
     kullanilacak endpoint) ekrana basilir.
  3) Gondermeden hemen once terminalde AYNEN "EVET GONDER" yazmanizi ister
     - baska HERHANGI bir girdi (bos Enter dahil) islemi IPTAL eder.
  4) Sadece TEK bir MARKET ALIM emri gonderir; pozisyonu OTOMATIK KAPATMAZ
     - test sonrasi elinizdeki kucuk miktari ne yapacaginiza (satmak/
     tutmak) SIZ karar verirsiniz.
  5) Ham borsa yaniti [BORSA YANITI] etiketiyle terminale basilir - bunu
     kendi Binance TR hesabinizdaki islem gecmisiyle KARSILASTIRIN.

Kullanim (kendi ortaminizda, gercek anahtarlarinizla):
    export BINANCE_TR_API_KEY="..."
    export BINANCE_TR_SECRET_KEY="..."
    export AURELIUS_LIVE_CONFIRM="EVET_GERCEK_PARA_KULLAN"
    python3 test_canli_emir.py PEPETRY

Windows cmd (TIRNAKSIZ - tirnaklar degerin parcasi olur; ayni pencerede calistirin):
    set BINANCE_TR_API_KEY=anahtariniz
    set BINANCE_TR_SECRET_KEY=gizli_anahtariniz
    set AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN
    python test_canli_emir.py PEPETRY
"""
import glob
import importlib.util
import os
import sys

MAKS_TEST_TUTARI_TRY = 50.0  # bu tutarin USTUNDE bir test emrine ASLA izin verilmez

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_DOSYA_YOLU = os.path.join(_SCRIPT_DIR, "project_aurelius_bot_v17.py")


def _bot_dosyasini_bul():
    """
    Bot dosyasini bu scriptin klasorunde arar. Windows ayni adli ikinci
    indirmeyi 'project_aurelius_bot_v17 (1).py' diye kaydeder; tek bir
    boyle aday varsa onu kullanir. Bulamazsa klasordeki .py dosyalarini
    listeleyip neyin yanlis oldugunu soyler.
    """
    if os.path.exists(BOT_DOSYA_YOLU):
        return BOT_DOSYA_YOLU
    adaylar = sorted(glob.glob(os.path.join(_SCRIPT_DIR, "project_aurelius_bot_v17*.py")))
    if len(adaylar) == 1:
        print(f"NOT: '{os.path.basename(adaylar[0])}' kullaniliyor "
              f"(adi tam olarak project_aurelius_bot_v17.py degil).")
        return adaylar[0]

    print(f"HATA: '{_SCRIPT_DIR}' klasorunde project_aurelius_bot_v17.py bulunamadi.")
    if adaylar:
        print("Birden fazla kopya var - GUNCEL olani 'project_aurelius_bot_v17.py' olarak "
              "yeniden adlandirip digerlerini silin:")
        for aday in adaylar:
            print(f"    {os.path.basename(aday)}")
    else:
        py_dosyalari = sorted(f for f in os.listdir(_SCRIPT_DIR) if ".py" in f.lower())
        print(f"Bu klasordeki Python dosyalari: {', '.join(py_dosyalari) or '(hic yok)'}")
        print("Bot dosyasini bu klasore indirin ve adinin tam olarak "
              "'project_aurelius_bot_v17.py' oldugundan emin olun.")
    sys.exit(1)


def _bot_modulunu_yukle():
    bot_dosyasi = _bot_dosyasini_bul()
    spec = importlib.util.spec_from_file_location("aurelius_bot", bot_dosyasi)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) < 2:
        print("Kullanim: python3 test_canli_emir.py SEMBOL   (orn. PEPETRY)")
        sys.exit(1)
    symbol = sys.argv[1].upper()

    m = _bot_modulunu_yukle()

    # Bu script CANLI_MOD bayragindan BAGIMSIZ calisir (dogrudan gercek emir
    # fonksiyonlarini cagirir) ama AYNI guvenlik on kontrolunu (API anahtari
    # + AURELIUS_LIVE_CONFIRM) zorunlu kilar.
    m.CANLI_MOD = True
    if not m.canli_mod_on_kontrol():
        print("\nHATA: guvenlik on kontrolu basarisiz. BINANCE_TR_API_KEY, "
              "BINANCE_TR_SECRET_KEY ve AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN "
              "ortam degiskenlerini kendi ortaminizda tanimlayip tekrar deneyin.")
        sys.exit(1)

    print("\n[1/4] Serbest TRY bakiyesi cekiliyor...")
    try:
        bakiye = m.binance_serbest_try_bakiyesi()
    except Exception as e:
        print(f"HATA: bakiye cekilemedi: {e}")
        sys.exit(1)
    print(f"      Serbest TRY bakiyesi: {bakiye:,.2f} TRY")
    if bakiye <= 0:
        print("HATA: serbest TRY bakiyesi 0 veya negatif - test emri gonderilemez "
              "(bakiye cekme adiminin da dogru calistigini once teyit edin).")
        sys.exit(1)

    print(f"\n[2/4] {symbol} icin LOT_SIZE/minNotional filtreleri ve guncel fiyat cekiliyor...")
    try:
        filtreler = m.sembol_filtrelerini_getir(symbol)
    except Exception as e:
        print(f"HATA: sembol filtreleri alinamadi: {e}")
        sys.exit(1)
    try:
        fiyat = m.get_last_price(symbol)
    except Exception as e:
        print(f"HATA: guncel fiyat alinamadi: {e}")
        sys.exit(1)

    min_notional = filtreler.get("min_notional") or 0.0
    print(f"      step_size={filtreler.get('step_size')}  min_notional={min_notional}  fiyat={fiyat}")

    if min_notional and min_notional > MAKS_TEST_TUTARI_TRY:
        print(f"\nHATA: {symbol} icin minNotional ({min_notional:.2f} TRY) guvenlik sinirini "
              f"({MAKS_TEST_TUTARI_TRY:.2f} TRY) asiyor - GUVENLIK ICIN DURDURULDU. "
              "Daha dusuk minNotional'li baska bir sembol deneyin.")
        sys.exit(1)

    test_tutari = min(MAKS_TEST_TUTARI_TRY, max(min_notional * 1.05, min_notional + 1) if min_notional else 20.0)
    if test_tutari > bakiye:
        print(f"\nHATA: test tutari (~{test_tutari:.2f} TRY) serbest bakiyeden ({bakiye:.2f} TRY) buyuk.")
        sys.exit(1)

    step_size = filtreler.get("step_size")
    ham_miktar = test_tutari / fiyat
    miktar = m.miktari_lot_size_yuvarla(ham_miktar, step_size)
    # LOT_SIZE asagi yuvarlamasi tutari minNotional altina dusurebilir (borsa reddeder).
    if step_size and min_notional and miktar * fiyat < min_notional:
        miktar = m.miktari_lot_size_yuvarla(miktar + step_size, step_size)
    if miktar <= 0:
        print("\nHATA: LOT_SIZE yuvarlamasi sonrasi miktar 0 cikti - test tutari bu sembol icin cok kucuk.")
        sys.exit(1)

    tahmini_tutar = miktar * fiyat
    if tahmini_tutar > MAKS_TEST_TUTARI_TRY or tahmini_tutar > bakiye:
        print(f"\nHATA: LOT_SIZE sonrasi tahmini tutar (~{tahmini_tutar:.2f} TRY) guvenlik sinirini "
              f"veya serbest bakiyeyi asiyor - durduruldu.")
        sys.exit(1)
    if min_notional and tahmini_tutar < min_notional:
        print(f"\nHATA: tahmini tutar (~{tahmini_tutar:.2f} TRY) minNotional ({min_notional}) altinda - "
              "borsa reddeder, durduruldu.")
        sys.exit(1)

    print("\n[3/4] TEST EMRI OZETI")
    print(f"      Sembol      : {symbol}  (Binance TR emir sembolu: {m.binance_tr_islem_sembolu(symbol)})")
    print("      Yon         : BUY (MARKET)")
    print(f"      Miktar      : {miktar}")
    print(f"      Tahmini Tutar: ~{tahmini_tutar:.2f} TRY  (guvenlik sinirinin altinda: {MAKS_TEST_TUTARI_TRY:.2f} TRY)")
    print(f"      Base URL    : {m.BINANCE_TR_PRIVATE_BASE_URL}")
    print(f"      Endpoint    : {m.ORDER_ENDPOINT_PATH}")
    print(f"      side/type   : BUY->{m.ORDER_SIDE_KODU.get('BUY')}  MARKET->{m.ORDER_TIPI_MARKET_KODU}")

    onay = input("\nBu GERCEK PARAYLA gonderilecek bir MARKET ALIM emridir. "
                 "Devam etmek icin AYNEN 'EVET GONDER' yazip Enter'a basin "
                 "(baska HERHANGI bir girdi iptal eder): ")
    if onay.strip() != "EVET GONDER":
        print("\nIptal edildi - hicbir emir gonderilmedi.")
        sys.exit(0)

    print("\n[4/4] Emir gonderiliyor...")
    try:
        sonuc = m.binance_gercek_emir_gonder(symbol, "BUY", miktar)
    except Exception as e:
        print(f"\nHATA: emir gonderilemedi: {e}")
        sys.exit(1)

    print("\n=== SONUC ===")
    print(sonuc)
    print("\nBu sonucu VE yukaridaki [BORSA YANITI] satirini kendi Binance TR "
          "hesabinizdaki islem gecmisiyle karsilastirarak dogrulayin.")


if __name__ == "__main__":
    main()
