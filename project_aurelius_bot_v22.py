"""
PROJECT AURELIUS - v22
Binance TR otomatik alim-satim botu - GUNLUK TREND TAKIBI
======================================================================
STRATEJI (3 yillik gecmis veri testinde her donemde artida kaldi - 'trend' komutu):
  - Coinler: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOGE, LINK, DOT, TRX, LTC (TRY pariteleri).
  - Gunde bir kez, gunluk mum kapanisindan sonra (TR ~03:05): gunluk kapanis son 50 gunun zirvesini
    kirdiysa, EMA50 ustundeyse ve BTC (USDT) EMA50 ustundeyse alim. En fazla 4 pozisyon; birden fazla
    sinyal varsa 60 gunluk getirisi en yuksek olan once.
  - Pozisyon buyuklugu: stop olursa kayip portfoyun AURELIUS_RISK_PCT'si (varsayilan %1) olacak kadar;
    tek pozisyon en fazla portfoyun 1/4'u.
  - Stop: giris - 2 x ATR(20, gunluk); her gun zirve - 3 x ATR'ye yukselir, asla inmez. Hedef ve kismi
    kar alma yok - kazanan islem kosar. Gun icinde fiyat stop'a inerse (emir defteriyle teyitli) satilir.
  - Borsa stop emri (varsayilan ACIK, AURELIUS_BORSA_STOP=0 kapatir): her pozisyon icin Binance TR'ye
    STOP_LOSS_LIMIT satis emri konur (tetik bot stop'unun %1 alti, limit tetigin %3 alti); bot veya
    bilgisayar kapaliyken de zarar borsada kesilir. Emir turu resmi dokumanla dogrulanmadigi icin her
    kurulumdan sonra emir sorgulanir; terslik varsa ozellik kalici kapanir ve Telegram'a uyari gider.
  - Acil fren: portfoy ulastigi en yuksek degerden %20 duserse tum pozisyonlar satilir ve bot durur.

v22 (kod incelemesi - ayrinti: rapor/v22_inceleme_raporu.html):
  - Stop, tek bir islemin fiyatiyla degil emir defterindeki en iyi alis fiyatiyla teyit edilip satilir.
  - Emirden sonra gerceklesen miktar ve ortalama fiyat borsadan okunur (giris fiyati, stop ve K/Z gercek).
  - Elle satilan (borsada olmayan) coin hemen kapatilir, gunluge yazilir, bir kez haber verilir.
  - Ayni emir hatasi Telegram'a en fazla 30 dk'da bir gelir; tek turdaki beklenmedik hata botu durdurmaz.
  - Performans tablosu / portfoy kaydi 30 dk'da bir. Eski kisa vadeli strateji ve grid kodlari kaldirildi
    (v21'den beri kapaliydi); onceki surumden kalan acik pozisyon varsa trend kurallarina aktarilir.
  Durum dosyasi ve islem gunlugu v21 ile ayni bicimde: v21'den v22'ye gecis kayipsizdir.

Gecmis surumlerin ozeti: v10 canli mod/durum dosyasi/Telegram, v11 gunluk-aylik rapor, v13 Telegram
kuyrugu, v17 Binance TR API duzeltmeleri, v18 kesinti onlemleri (baslatici, /komutlar, borsa stop),
v20 islem basina risk/acil fren tabani/islem gunlugu, v21 gunluk trend takibi, v21.1 borsa stop varsayilan
acik + haftalik ozet.

ONEMLI: AURELIUS_CANLI_MOD=1 ve AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN ile GERCEK PARA ile GERCEK
emir gonderir. Yatirim tavsiyesi degildir, kar garantisi yoktur; kripto piyasalari yuksek risklidir.
Binance TR'nin ozel API'si icin resmi genis dokuman yoktur; emir yollari topluluk kaynaklarindan alindi
ve canli hesapta (alim-satim) dogrulandi. API anahtarinda PARA CEKME izni KAPALI olmalidir.

Ortam degiskenleri: BINANCE_TR_API_KEY, BINANCE_TR_SECRET_KEY, AURELIUS_CANLI_MOD=1,
AURELIUS_LIVE_CONFIRM, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID; istege bagli AURELIUS_RISK_PCT,
AURELIUS_TREND_KIRILIM (50), AURELIUS_TREND_BTC_FILTRE=0, AURELIUS_BORSA_STOP=0,
AURELIUS_DURUM_BILDIRIM_SAAT (2), AURELIUS_SAGLIK_URL, AURELIUS_TELEGRAM_KOMUT=0,
AURELIUS_BASLANGIC_SERMAYE, AURELIUS_FREN_SIFIRLA=1.

Kullanim:
    python project_aurelius_bot_v22.py                   (canli/simulasyon calisma)
    python project_aurelius_bot_v22.py trend [GUN] [TL]  (gunluk trend takibini 4 donemde test eder)
    python project_aurelius_bot_v22.py rapor             (islem gunlugu ozeti)
    python project_aurelius_bot_v22.py baglanti          (Binance TR baglanti teshisi)
    python project_aurelius_bot_v22.py kurulum           (otomatik yeniden baslatan baslat.sh/.bat)
Telegram: /durum /trend /btc /hafta /rapor /alimdurdur /devam /bosalt /hepsinisat /frensifirla /yardim
"""

import time
import random
import html
import urllib.request
import urllib.parse
import urllib.error
import hmac
import hashlib
import json
import socket
import ssl
import csv
import os
import sys
import logging
import threading
import queue
import bisect
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

# ----------------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------------
TOPLAM_SANAL_BAKIYE_TRY = 5_000        # sadece SIMULASYON modunda baslangic kasasi
API_CALL_SLEEP_SECONDS = 0.5
MAX_DRAWDOWN_PCT = 0.20                # acil fren: portfoyun en yuksek degerinden bu kadar dusus
MUTABAKAT_ARALIGI_SAAT = 6.0           # canli modda borsa bakiyesiyle esitleme araligi
ESKI_SURUM_STOP_PCT = 0.04             # v21 oncesinden kalan (trend disi) pozisyonun aktarimdaki stop'u

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ISLEMLER_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_islemler.csv")
PORTFOY_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_portfoy_gecmisi.csv")
STATE_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius_state.json")  # v10
Z_RAPORLARI_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_z_raporlari.csv")  # v11
LOG_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius.log")  # v13
ISLEM_GUNLUGU_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_islem_gunlugu.csv")  # v20

# v13: Telegram/ag hatalarinin artik SESSIZCE kaybolmamasi icin kalici log dosyasi.
# Konsoldaki renkli print() ciktisi degismedi - bu, ONA EK, persistent bir kayittir.
logging.basicConfig(
    filename=LOG_DOSYASI,
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    encoding="utf-8",
)
logger = logging.getLogger("aurelius")

# v11 - X (gunluk) / Z (aylik) raporlama periyotlari
X_RAPOR_PERIYODU = timedelta(hours=24)
Z_RAPOR_PERIYODU = timedelta(days=30)

# Genel/public piyasa verisi uc noktalari (fiyat, kline, ticker, orderbook, exchangeInfo)
EXCHANGE_INFO_URL = "https://api.binance.me/api/v3/exchangeInfo"
KLINES_URL_TEMPLATE = "https://api.binance.me/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
PRICE_URL_TEMPLATE = "https://api.binance.me/api/v3/trades?symbol={symbol}&limit=1"
DEPTH_URL_TEMPLATE = "https://api.binance.me/api/v3/depth?symbol={symbol}&limit={limit}"  # v10

# v17 FIX - CANLI MOD icin OZEL/IMZALI uc noktalar.
# BASE_URL ve ACCOUNT_ENDPOINT_PATH, Binance TR'nin resmi acik API yapisina
# (https://www.binance.tr + /open/v1/account/spot) gore DUZELTILDI - eski
# "binancetr.com" / "/open-api/v3/account" (Binance Global stili) adresler
# Binance TR icin YANLISTI ve bakiyenin hep 0.00 TRY donmesine yol aciyordu.
#
# !!! ONEMLI - ORDER_ENDPOINT_PATH KAYNAK NOTU: Binance TR'nin ozel API'si
# icin resmi, genis capli indekslenmis bir dokumantasyon YOKTUR. Asagidaki
# "/open/v1/orders" yolu, Binance TR'yi hedefleyen BAGIMSIZ/ACIK KAYNAKLI bir
# topluluk kutuphanesinin incelenmesiyle bulundu
# (github.com/futuristicexchanger/BinanceTrApi, BinanceTrService.py +
# constants.json) - bu kutuphanenin hesap/bakiye yolu ("/open/v1/account/spot")
# SIZIN CANLI ORTAMDA ZATEN DOGRULADIGINIZ yol ile BIREBIR AYNI oldugu icin
# guvenilirligi ARTMIS kabul edildi, ANCAK bu RESMI Binance TR dokumantasyonu
# DEGILDIR ve emir uc noktasi bizzat SIZIN TARAFINIZDAN test edilmedi.
# AYRICA ONEMLI: bu kaynaga gore Binance TR, "side"/"type" alanlarini
# Binance Global gibi "BUY"/"MARKET" METIN olarak DEGIL, SAYISAL KOD olarak
# bekliyor (bkz. ORDER_SIDE_KODU/ORDER_TIPI_MARKET_KODU asagida ve
# binance_gercek_emir_gonder()). GERCEK PARAYLA ILK EMIRDEN ONCE MUTLAKA
# en kucuk (minNotional'a yakin) bir tutarla TEK bir test emri gonderip
# konsoldaki [BORSA YANITI] satirini borsa arayuzunuzdeki islem gecmisiyle
# KARSILASTIRARAK dogrulayin. canli_mod_on_kontrol() bu konuda ayrica bir
# uyari basar.
BINANCE_TR_PRIVATE_BASE_URL = "https://www.binance.tr"
ACCOUNT_ENDPOINT_PATH = "/open/v1/account/spot"
ORDER_ENDPOINT_PATH = "/open/v1/orders"  # v17 FIX: bkz. yukaridaki KAYNAK NOTU - RESMI DOGRULAMA hala YOK
RECV_WINDOW_MS = 5000

# v17 FIX: Binance TR'nin emir API'si (yukaridaki kaynak notuna gore)
# side/type alanlarini metin degil SAYISAL KOD olarak bekliyor gibi
# gorunuyor. Bu esleme SADECE BUY/SELL MARKET emirleri icin (botun kullandigi
# tek emir turu) - Binance Global stili "BUY"/"SELL"/"MARKET" sabitlerini
# bu kodlara cevirir.
ORDER_SIDE_KODU = {"BUY": "0", "SELL": "1"}
ORDER_TIPI_MARKET_KODU = "2"
# v18: Borsada bekleyen koruyucu stop emri icin (AURELIUS_BORSA_STOP=1). Kaynak:
# ayni /open/v1 API ailesini kullanan ccxt (Tokocrypto) ve topluluk kutuphanesi -
# RESMI Binance TR dokumani DEGIL; ilk kullanimda [BORSA YANITI] satirlarini kontrol edin.
ORDER_TIPI_STOP_LOSS_LIMIT_KODU = "4"
ORDER_CANCEL_ENDPOINT_PATH = "/open/v1/orders/cancel"
ORDER_DETAIL_ENDPOINT_PATH = "/open/v1/orders/detail"
EMIR_DURUMLARI = {-2: "ISLENIYOR", 0: "YENI", 1: "KISMEN-DOLDU", 2: "DOLDU", 3: "IPTAL",
                  4: "IPTAL-BEKLIYOR", 5: "REDDEDILDI", 6: "SURESI-DOLDU"}


def _coin_adi(symbol: str) -> str:
    """'PEPETRY' -> 'PEPE'. str.replace("TRY", "") adinda TRY gecen
    varliklari bozar (orn. 'SENTRYTRY' -> 'SEN'); sadece sondaki TRY atilir."""
    return symbol[:-3] if symbol.endswith("TRY") else symbol


def binance_tr_islem_sembolu(symbol: str) -> str:
    """Genel piyasa verisi (api/v3) 'PEPETRY' bicimini kullanir; Binance TR'nin
    ozel /open/v1 uc noktalari ise 'PEPE_TRY' bicimini bekler (bkz.
    ORDER_ENDPOINT_PATH KAYNAK NOTU - ayni kutuphanenin README ornegi:
    postNewLimitOrder("USDT_TRY", ...))."""
    if "_" in symbol or not symbol.endswith("TRY"):
        return symbol
    return f"{symbol[:-3]}_TRY"

# v10 - Tahta derinligi / spread filtresi
ORDERBOOK_DEPTH_LIMIT = 5
MAX_SPREAD_PCT = 0.5   # bu esikten genis spreadli coinlerde ALIM iptal edilir

# v10 - Canli/Dry-Run mod anahtari (VARSAYILAN: False - guvenli)
CANLI_MOD = False

def _ortam_degiskeni_str_oku(isim: str, varsayilan: str = "") -> str:
    """
    v17 FIX: Ortam degiskenini HER ZAMAN temiz, tek bir str olarak okur.
    os.getenv() zaten bir str (veya None) dondurur, ancak bu sarmalayici
    iki yaygin hata sinifina karsi savunma saglar:
      1) Tanim satirinin sonunda unutulan bir virgul (orn.
         'BINANCE_TR_API_KEY = os.getenv("X", ""),' ) degiskeni SESSIZCE
         bir tuple'a cevirir - sonrasinda .encode() cagrildiginda
         "tuple object has no attribute 'encode'" hatasi COK GEC, HMAC
         imzalama asamasinda ortaya cikar. Burada erkenden yakalanir.
      2) .env dosyalarindan/terminal kopyala-yapistirdan gelen bastaki/
         sondaki bosluk veya satir sonu karakteri ("API_KEY=abc123\\n" gibi)
         Binance TR'nin "Invalid API-key" hatasina yol acabilir - .strip()
         ile temizlenir.
      3) Windows cmd'de 'set BINANCE_TR_API_KEY="abc123"' yazildiginda
         tirnak isaretleri DEGERIN PARCASI olur ('"abc123"') ve borsa
         anahtari tanimaz (code=3700 Invalid API-key). Anahtarlar, secret,
         token ve chat id hicbir zaman tirnakla baslayip bitmedigi icin
         bastaki/sondaki tirnaklar da temizlenir.
    """
    deger = os.getenv(isim, varsayilan)
    if isinstance(deger, (tuple, list)):
        # Yanlislikla tuple/list haline gelmisse (bkz. yukaridaki 1. hata),
        # ilk elemani almak yerine acikca HATA vererek sorunun gizli kalan
        # bir "tuple object has no attribute 'encode'" istisnasina donusmesini
        # ONLE - erken ve anlasilir bir hata mesaji ile durdur.
        raise TypeError(
            f"{isim} ortam degiskeni bir str degil, {type(deger).__name__} olarak okundu "
            f"({deger!r}). Tanim satirinda fazladan bir virgul olup olmadigini kontrol edin."
        )
    if deger is None:
        deger = varsayilan
    return str(deger).strip().strip("\"'").strip()


# v17 FIX - Ortam degiskenlerinden okunan kimlikler. Artik _ortam_degiskeni_str_oku()
# ile okunuyor - anahtarlar HER ZAMAN temiz birer str, asla tuple/list olamaz
# (bkz. yukaridaki fonksiyon dokumantasyonu).
TELEGRAM_BOT_TOKEN = _ortam_degiskeni_str_oku("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _ortam_degiskeni_str_oku("TELEGRAM_CHAT_ID")
BINANCE_TR_API_KEY = _ortam_degiskeni_str_oku("BINANCE_TR_API_KEY")
BINANCE_TR_SECRET_KEY = _ortam_degiskeni_str_oku("BINANCE_TR_SECRET_KEY")

# Canli modu dosyayi duzenlemeden acmak icin: AURELIUS_CANLI_MOD=1. Her yeni
# indirmede CANLI_MOD yukarida yine False gelir; bu degisken o adimi gereksiz
# kilar. Ek guvenlik onayi (AURELIUS_LIVE_CONFIRM) yine AYRICA zorunludur.
if _ortam_degiskeni_str_oku("AURELIUS_CANLI_MOD") == "1":
    CANLI_MOD = True


def _ortam_sayisi_oku(isim: str, varsayilan: float) -> float:
    deger = _ortam_degiskeni_str_oku(isim)
    if not deger:
        return varsayilan
    try:
        return float(deger.replace(",", "."))
    except ValueError:
        print(f"{isim} sayi olarak okunamadi ({deger!r}); varsayilan {varsayilan} kullaniliyor.")
        return varsayilan


# v18 KESINTI ONLEMLERI
# (1) Periyodik "bot calisiyor" durum bildirimi (saat, 0 = kapali) ve istege bagli dis
#     saglik pingi (orn. healthchecks.io ping adresi): bot durursa (elektrik kesintisi
#     dahil) o servis size haber verir.
DURUM_BILDIRIM_SAAT = _ortam_sayisi_oku("AURELIUS_DURUM_BILDIRIM_SAAT", 2.0)
SAGLIK_PING_URL = _ortam_degiskeni_str_oku("AURELIUS_SAGLIK_URL")
SAGLIK_PING_ARALIGI_SANIYE = 300
# (4) Telegram komutlari - SADECE TELEGRAM_CHAT_ID'den gelenler kabul edilir.
#     Kapatmak icin AURELIUS_TELEGRAM_KOMUT=0.
TELEGRAM_KOMUTLARI_AKTIF = _ortam_degiskeni_str_oku("AURELIUS_TELEGRAM_KOMUT") != "0"
HEPSINI_SAT_ONAY_SANIYE = 60
# (5) Borsada bekleyen koruyucu stop emri - varsayilan ACIK, AURELIUS_BORSA_STOP=0 ile kapanir.
#     Trend pozisyonlari gunlerce acik kalir; bot/bilgisayar kapaliyken de korunmalari gerekir.
#     Tetik fiyati botun kendi stop'unun BORSA_STOP_TAMPON_PCT altindadir: bot calisirken once kendi
#     stop'u satar, bot kapaliyken borsadaki emir satar.
BORSA_STOP_AKTIF = _ortam_degiskeni_str_oku("AURELIUS_BORSA_STOP") != "0"
BORSA_STOP_TAMPON_PCT = 0.01
BORSA_STOP_LIMIT_ARALIK_PCT = 0.03      # limit fiyati tetigin bu kadar altinda (hizli dususte de dolsun)
BORSA_STOP_GUNCELLEME_ESIGI_PCT = 0.01  # bot stop'u bu kadar yukselince borsadaki emir yukseltilir
BORSA_STOP_GUNCELLEME_MIN_SANIYE = 300
BORSA_STOP_SORGU_SANIYE = 120
BORSA_STOP_HATA_BEKLEME_SANIYE = 120
# (2) Cikis kodlari - 'kurulum' ile olusturulan baslatici bunlara gore davranir.
CIKIS_DUR = 0            # bilincli durdurma (Ctrl+C, bosaltma bitti, ACIL FREN): yeniden baslatma
CIKIS_YENIDEN_DENE = 1   # gecici sorun (ag, bakiye okunamadi) veya cokme: yeniden baslat
CIKIS_AYAR_HATASI = 2    # eksik anahtar / mod uyusmazligi: yeniden baslatmak ise yaramaz
# (3)/(4) Yeni alim durumu - durum dosyasina kaydedilir, yeniden baslatmada korunur.
ALIM_DURUMU_ACIKLAMA = {
    "ACIK": "ACIK",
    "DURDURULDU": "DURDURULDU (acik pozisyonlar yonetilmeye devam ediyor)",
    "BOSALTMA": "BOSALTMA (yeni alim yok; pozisyonlar kapaninca bot duracak)",
}
_alim_durumu = "ACIK"


def _aralikta(deger: float, alt: float, ust: float) -> float:
    return min(max(deger, alt), ust)


# v20 RISK: islem basina risk ve kalici sermaye tabani / acil fren referansi
RISK_PCT = _aralikta(_ortam_sayisi_oku("AURELIUS_RISK_PCT", 1.0), 0.0, 5.0) / 100
MIN_POZISYON_TUTARI_TRY = 30.0       # bundan kucuk alim yapilmaz
BASLANGIC_SERMAYE_TRY = max(0.0, _ortam_sayisi_oku("AURELIUS_BASLANGIC_SERMAYE", 0.0))
SERMAYE_HAREKETI_MIN_TRY = 5.0       # mutabakatta bundan (ve portfoyun %1'inden) buyuk TRY farki
SERMAYE_HAREKETI_MIN_ORAN = 0.01     # para yatirma/cekme sayilir
FREN_SIFIRLA = _ortam_degiskeni_str_oku("AURELIUS_FREN_SIFIRLA") == "1"

# GUNLUK TREND TAKIBI ayarlari (kurallar 'trend' testindekiyle ayni)
STRATEJI = "TREND"  # durum dosyasina yazilir
TREND_COINLERI = ("BTCTRY", "ETHTRY", "BNBTRY", "SOLTRY", "XRPTRY", "ADATRY", "AVAXTRY", "DOGETRY",
                  "LINKTRY", "DOTTRY", "TRXTRY", "LTCTRY")
TREND_MAKS_POZISYON = 4
TREND_ILK_STOP_ATR = 2.0            # ilk stop: giris - 2 x ATR
TREND_TAKIP_ATR = 3.0               # takip eden stop: zirve - 3 x ATR
TREND_EMA = 50
TREND_ATR_PERIYOT = 20
TREND_KIRILIM_GUN = int(_aralikta(_ortam_sayisi_oku("AURELIUS_TREND_KIRILIM", 50), 10, 100))
TREND_BTC_FILTRESI = _ortam_degiskeni_str_oku("AURELIUS_TREND_BTC_FILTRE") != "0"
TREND_KONTROL_GECIKME_DK = 5        # gunluk mum 00:00 UTC'de (TR 03:00) kapanir; bu kadar dakika sonra kontrol
TREND_KOVALAMA_ATR = 0.5            # fiyat sinyal kapanisindan 0.5 x ATR'den fazla kactiysa girilmez
TREND_GUNLUK_MUM = 300              # gunluk kontrolde cekilen gecmis (tek istek)
_trend_durumu: dict = {}            # {"son_gun": ms} - durum dosyasina kaydedilir
TREND_VERI_TEKRAR_SAAT = 2          # eksik veride gunluk kontrol bu sure boyunca tekrar denenir
TREND_VERI_TEKRAR_DK = 10
STOP_TEYIT_TAMPON_PCT = 0.002      # v22: en iyi alis stop'un bu kadar ustundeyse tek islemlik sapma sayilir

REAL_POLL_INTERVAL_SECONDS = 25
PERFORMANS_RAPORU_DK = 30           # v22: konsol performans tablosu / portfoy kaydi araligi
EMIR_HATA_BILDIRIM_DK = 30          # v22: ayni coinin emir hatasi Telegram'a en fazla bu aralikla
DONGU_HATA_BILDIRIM_DK = 60         # v22: ana donguedeki beklenmedik hata Telegram'a en fazla bu aralikla
DONGU_HATA_LIMITI = 20              # v22: art arda bu kadar turda hata olursa bot durur (baslatici acar)

# Gercekcilik ayarlari (simulasyon ve tahmin)
KOMISYON_PCT = 0.0010
SLIPAJ_MIN_PCT = 0.0005
SLIPAJ_MAKS_PCT = 0.0020

FIYAT_TIMEOUT_SANIYE = 20
FIYAT_MAX_DENEME = 3

# v10 - Genel amacli exponential backoff ayarlari (BOLUM 5)
BACKOFF_BASLANGIC_SANIYE = 2.0
BACKOFF_MAX_SANIYE = 60.0
BACKOFF_MAX_DENEME = 5

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def format_fiyat(fiyat: Optional[float]) -> str:
    """
    v17 MODUL 2: Dusuk fiyatli coinler (orn. PEPETRY, SHIBTRY gibi birim
    fiyati 1 TL'nin cok altinda olan mikro pariteler) icin DINAMIK basamak
    hassasiyeti. Sabit ':.4f' formati bu coinlerde "0.0002" gibi sabit ve
    anlamsiz bir deger basiyordu; bu fonksiyon SADECE GOSTERIM katmaninda
    kullanilir - tetikleme/karsilastirma mantigi HER ZAMAN saf float
    degerler uzerinden calisir, burada uretilen string asla geri
    donusturulup karsilastirilmaz.
      fiyat < 0.001        -> 8 ondalik basamak
      0.001 <= fiyat < 1.0 -> 6 ondalik basamak
      fiyat >= 1.0         -> 4 ondalik basamak (binlik ayiracli)
    """
    if fiyat is None:
        return "N/A"
    fiyat = float(fiyat)
    if fiyat < 0.001:
        return f"{fiyat:.8f}"
    if fiyat < 1.0:
        return f"{fiyat:.6f}"
    return f"{fiyat:,.4f}"


def csv_islem_yaz(symbol, side, price, qty, amount, komisyon, kaynak, tag=""):
    """Her ALIM/SATIM islemini CSV dosyasina ekler (kalici kayit)."""
    dosya_var = os.path.exists(ISLEMLER_CSV)
    try:
        with open(ISLEMLER_CSV, "a", newline="", encoding="utf-8") as f:
            yazici = csv.writer(f)
            if not dosya_var:
                yazici.writerow(["tarih_saat", "sembol", "yon", "fiyat_try", "miktar", "tutar_try", "komisyon_try", "kaynak", "etiket"])
            yazici.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), symbol, side, f"{price:.8f}", f"{qty:.8f}", f"{amount:.2f}", f"{komisyon:.2f}", kaynak, tag])
    except Exception as e:
        print(f"{RED}  (CSV islem kaydi yazilamadi: {e}){RESET}")


def csv_portfoy_yaz(toplam_portfoy, toplam_baslangic, pnl, pnl_pct, acik_pozisyon_sayisi):
    """Belirli araliklarla toplam portfoy anlik goruntusunu CSV'ye ekler."""
    dosya_var = os.path.exists(PORTFOY_CSV)
    try:
        with open(PORTFOY_CSV, "a", newline="", encoding="utf-8") as f:
            yazici = csv.writer(f)
            if not dosya_var:
                yazici.writerow(["tarih_saat", "toplam_portfoy_try", "baslangic_try", "kar_zarar_try", "kar_zarar_pct", "acik_pozisyon_sayisi"])
            yazici.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"{toplam_portfoy:.2f}", f"{toplam_baslangic:.2f}", f"{pnl:.2f}", f"{pnl_pct:.2f}", acik_pozisyon_sayisi])
    except Exception as e:
        print(f"{RED}  (CSV portfoy kaydi yazilamadi: {e}){RESET}")


def z_csv_yaz(baslangic_tarihi, bitis_tarihi, ay_basi, ay_sonu, pnl, pnl_pct, max_dd_pct, komisyon,
              en_iyi_sym, en_iyi_pnl, en_kotu_sym, en_kotu_pnl, toplam_islem):
    """v11: Her AYLIK Z RAPORU'nu kalici olarak project_aurelius_z_raporlari.csv
    dosyasina bir satir olarak ekler."""
    dosya_var = os.path.exists(Z_RAPORLARI_CSV)
    try:
        with open(Z_RAPORLARI_CSV, "a", newline="", encoding="utf-8") as f:
            yazici = csv.writer(f)
            if not dosya_var:
                yazici.writerow([
                    "kaydedilme_zamani", "donem_baslangic", "donem_bitis", "ay_basi_bakiye_try",
                    "ay_sonu_bakiye_try", "net_pnl_try", "net_pnl_pct", "max_drawdown_pct",
                    "toplam_komisyon_try", "en_iyi_coin", "en_iyi_coin_pnl_try", "en_kotu_coin",
                    "en_kotu_coin_pnl_try", "toplam_islem_adedi",
                ])
            yazici.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"), baslangic_tarihi, bitis_tarihi,
                f"{ay_basi:.2f}", f"{ay_sonu:.2f}", f"{pnl:.2f}", f"{pnl_pct:.2f}",
                f"{max_dd_pct * 100:.2f}", f"{komisyon:.2f}", en_iyi_sym, f"{en_iyi_pnl:.2f}",
                en_kotu_sym, f"{en_kotu_pnl:.2f}", toplam_islem,
            ])
    except Exception as e:
        print(f"{RED}  (Z raporu CSV'ye yazilamadi: {e}){RESET}")


class RaporlamaDurumu:
    """
    v11: Gunluk (X) ve Aylik (Z) donemsel raporlama icin biriken
    istatistikleri tutar. State JSON'a kaydedilir/yuklenir - bot yeniden
    baslatildiginda 24 saatlik/30 gunluk sayaclar SIFIRLANMAZ.

    X (gunluk) sayaclari: sadece bir X raporu gonderildikten sonra
    sifirlanir. Z (aylik) sayaclari: sadece bir Z raporu gonderildikten
    sonra sifirlanir. Ikisi birbirinden BAGIMSIZ calisir.
    """

    def __init__(self, baslangic_bakiye: float):
        self.son_z_raporu_zamani = datetime.now()
        self.x_sifirla(baslangic_bakiye)
        self.z_sifirla(baslangic_bakiye)

    def x_sifirla(self, donem_baslangic_portfoy: float) -> None:
        self.son_x_raporu_zamani = datetime.now()
        self.x_alim_sayisi = 0
        self.x_satim_sayisi = 0
        self.x_kazanan = 0
        self.x_kaybeden = 0
        self.x_komisyon = 0.0
        self.x_realized_pnl = 0.0
        self.x_donem_baslangic_portfoy = donem_baslangic_portfoy

    def z_sifirla(self, yeni_donem_baslangic_bakiye: float) -> None:
        self.z_ay_basi_bakiye = yeni_donem_baslangic_bakiye
        self.z_toplam_komisyon = 0.0
        self.z_toplam_islem = 0
        self.z_en_yuksek_portfoy = yeni_donem_baslangic_bakiye
        self.z_en_derin_dusus_pct = 0.0
        self.z_coin_pnl: dict = {}

    def islem_kaydet(self, symbol: str, side: str, komisyon: float, realized_pnl: Optional[float]) -> None:
        """Her basarili ALIM/SATIM'dan sonra cagirilir; hem X hem Z
        sayaclarini gunceller."""
        self.x_komisyon += komisyon
        self.z_toplam_komisyon += komisyon
        self.z_toplam_islem += 1
        if side == "ALIM":
            self.x_alim_sayisi += 1
        else:
            self.x_satim_sayisi += 1
            if realized_pnl is not None:
                self.x_realized_pnl += realized_pnl
                self.z_coin_pnl[symbol] = self.z_coin_pnl.get(symbol, 0.0) + realized_pnl
                if realized_pnl > 0:
                    self.x_kazanan += 1
                elif realized_pnl < 0:
                    self.x_kaybeden += 1

    def drawdown_guncelle(self, guncel_portfoy: float) -> None:
        """Her tick'te cagirilir - Z donemi icin surekli max drawdown takibi."""
        if guncel_portfoy > self.z_en_yuksek_portfoy:
            self.z_en_yuksek_portfoy = guncel_portfoy
        if self.z_en_yuksek_portfoy > 0:
            dusus = (self.z_en_yuksek_portfoy - guncel_portfoy) / self.z_en_yuksek_portfoy
            if dusus > self.z_en_derin_dusus_pct:
                self.z_en_derin_dusus_pct = dusus

    def x_suresi_doldu_mu(self) -> bool:
        return (datetime.now() - self.son_x_raporu_zamani) >= X_RAPOR_PERIYODU

    def z_suresi_doldu_mu(self) -> bool:
        return (datetime.now() - self.son_z_raporu_zamani) >= Z_RAPOR_PERIYODU

    def to_dict(self) -> dict:
        return {
            "son_x_raporu_zamani": self.son_x_raporu_zamani.isoformat(),
            "son_z_raporu_zamani": self.son_z_raporu_zamani.isoformat(),
            "x_alim_sayisi": self.x_alim_sayisi,
            "x_satim_sayisi": self.x_satim_sayisi,
            "x_kazanan": self.x_kazanan,
            "x_kaybeden": self.x_kaybeden,
            "x_komisyon": self.x_komisyon,
            "x_realized_pnl": self.x_realized_pnl,
            "x_donem_baslangic_portfoy": self.x_donem_baslangic_portfoy,
            "z_ay_basi_bakiye": self.z_ay_basi_bakiye,
            "z_toplam_komisyon": self.z_toplam_komisyon,
            "z_toplam_islem": self.z_toplam_islem,
            "z_en_yuksek_portfoy": self.z_en_yuksek_portfoy,
            "z_en_derin_dusus_pct": self.z_en_derin_dusus_pct,
            "z_coin_pnl": self.z_coin_pnl,
        }

    @classmethod
    def from_dict(cls, veri: dict, varsayilan_bakiye: float) -> "RaporlamaDurumu":
        obj = cls.__new__(cls)
        obj.son_x_raporu_zamani = (
            datetime.fromisoformat(veri["son_x_raporu_zamani"]) if veri.get("son_x_raporu_zamani") else datetime.now()
        )
        obj.son_z_raporu_zamani = (
            datetime.fromisoformat(veri["son_z_raporu_zamani"]) if veri.get("son_z_raporu_zamani") else datetime.now()
        )
        obj.x_alim_sayisi = veri.get("x_alim_sayisi", 0)
        obj.x_satim_sayisi = veri.get("x_satim_sayisi", 0)
        obj.x_kazanan = veri.get("x_kazanan", 0)
        obj.x_kaybeden = veri.get("x_kaybeden", 0)
        obj.x_komisyon = veri.get("x_komisyon", 0.0)
        obj.x_realized_pnl = veri.get("x_realized_pnl", 0.0)
        obj.x_donem_baslangic_portfoy = veri.get("x_donem_baslangic_portfoy", varsayilan_bakiye)
        obj.z_ay_basi_bakiye = veri.get("z_ay_basi_bakiye", varsayilan_bakiye)
        obj.z_toplam_komisyon = veri.get("z_toplam_komisyon", 0.0)
        obj.z_toplam_islem = veri.get("z_toplam_islem", 0)
        obj.z_en_yuksek_portfoy = veri.get("z_en_yuksek_portfoy", varsayilan_bakiye)
        obj.z_en_derin_dusus_pct = veri.get("z_en_derin_dusus_pct", 0.0)
        obj.z_coin_pnl = veri.get("z_coin_pnl", {})
        return obj


# ==========================================================================
# RISK KORUMASI: sermaye tabani ve acil fren referansi (durum dosyasina kaydedilir,
# yeniden baslatmada sifirlanmaz). Trend stratejisinde test edilen tek koruma acil frendir.
# ==========================================================================

class RiskKorumasi:
    def __init__(self):
        self.yatirilan_sermaye = 0.0      # raporlardaki "baslangic sermayesi"
        self.zirve_portfoy = 0.0          # acil fren bu degerden olan dususu olcer
        self.gun = ""
        self.gun_baslangic_portfoy = 0.0
        self.acil_fren_tetiklendi = False
        # Acilista portfoy zaten zirveden fren limitinden fazla asagidaysa (dusus bot kapaliyken
        # olmus): otomatik satis yapilmaz, yeni alimlar /frensifirla'ya kadar durur.
        self.fren_beklemede = False

    def fren_sifirla(self, portfoy: float) -> None:
        self.zirve_portfoy = portfoy
        self.fren_beklemede = False
        self.acil_fren_tetiklendi = False

    def portfoy_guncelle(self, portfoy: float, simdi: Optional[datetime] = None) -> None:
        gun = (simdi or datetime.now()).strftime("%Y-%m-%d")
        if gun != self.gun or self.gun_baslangic_portfoy <= 0:
            self.gun, self.gun_baslangic_portfoy = gun, portfoy
        if portfoy > self.zirve_portfoy:
            self.zirve_portfoy = portfoy

    def zirveden_dusus(self, portfoy: float) -> float:
        if self.zirve_portfoy <= 0:
            return 0.0
        return max(0.0, (self.zirve_portfoy - portfoy) / self.zirve_portfoy)

    def gunluk_degisim(self, portfoy: float) -> float:
        return portfoy / self.gun_baslangic_portfoy - 1 if self.gun_baslangic_portfoy > 0 else 0.0

    def sermaye_hareketi(self, fark: float) -> None:
        """Para yatirma (+) / cekme (-): kar-zarar sayilmasin, fren tetiklenmesin."""
        self.yatirilan_sermaye = max(0.0, self.yatirilan_sermaye + fark)
        self.zirve_portfoy = max(0.0, self.zirve_portfoy + fark)
        if self.gun_baslangic_portfoy > 0:
            self.gun_baslangic_portfoy = max(0.0, self.gun_baslangic_portfoy + fark)

    def durum_satirlari(self, portfoy: float) -> list:
        satirlar = [f"Risk: islem basina %{RISK_PCT * 100:g} | bugun %{self.gunluk_degisim(portfoy) * 100:+.1f}"
                    f" | zirveden -%{self.zirveden_dusus(portfoy) * 100:.1f} (acil fren %{MAX_DRAWDOWN_PCT * 100:.0f})"]
        if self.fren_beklemede:
            satirlar.append(f"Yeni alim engeli: portfoy kayitli en yuksek degerinden ({self.zirve_portfoy:,.2f} TRY) "
                            f"%{self.zirveden_dusus(portfoy) * 100:.0f} asagida; devam icin /frensifirla")
        return satirlar

    def to_dict(self) -> dict:
        return {
            "yatirilan_sermaye": self.yatirilan_sermaye,
            "zirve_portfoy": self.zirve_portfoy,
            "gun": self.gun,
            "gun_baslangic_portfoy": self.gun_baslangic_portfoy,
            "acil_fren_tetiklendi": self.acil_fren_tetiklendi,
            "fren_beklemede": self.fren_beklemede,
        }

    @classmethod
    def from_dict(cls, veri: Optional[dict]) -> "RiskKorumasi":
        obj = cls()
        if not isinstance(veri, dict):
            return obj
        try:
            obj.yatirilan_sermaye = float(veri.get("yatirilan_sermaye") or 0.0)
            obj.zirve_portfoy = float(veri.get("zirve_portfoy") or 0.0)
            obj.gun = str(veri.get("gun") or "")
            obj.gun_baslangic_portfoy = float(veri.get("gun_baslangic_portfoy") or 0.0)
        except (TypeError, ValueError):
            pass
        obj.acil_fren_tetiklendi = bool(veri.get("acil_fren_tetiklendi"))
        obj.fren_beklemede = bool(veri.get("fren_beklemede"))
        return obj


_risk = RiskKorumasi()


# ==========================================================================
# ISLEM GUNLUGU (kapanan her islem icin bir satir). Sutunlar v20/v21 ile ayni kalir
# (eski dosyaya eklenen satirlar kaymasin); eski stratejinin analiz sutunlari bos yazilir.
# ==========================================================================
ISLEM_GUNLUGU_ALANLARI = [
    "giris_zamani", "cikis_zamani", "sembol", "kaynak", "giris_fiyati", "cikis_fiyati", "tutar_try",
    "net_kar_try", "net_kar_pct", "r_sonucu", "risk_try", "stop_pct", "sure_saat", "cikis_sebebi",
    "hedef1", "hedef2", "puan", "btc_rejimi", "gunluk_trend", "h4_trend", "rsi_1h", "adx_4h", "goreceli_hacim",
]


def _tarih_oku(deger) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(deger) if deger else None
    except (TypeError, ValueError):
        return None


def _sayi(deger) -> Optional[float]:
    if deger is None or deger == "":
        return None
    try:
        return float(deger)
    except (TypeError, ValueError):
        return None


def islem_kaydi_olustur(sembol: str, kaynak: str, giris_zamani: Optional[datetime], cikis_zamani: datetime,
                        giris_fiyati: float, cikis_fiyati: float, tutar: float, net_kar: float,
                        risk_try: float, stop_pct: float, cikis_sebebi: str,
                        btc_rejimi: Optional[str] = None) -> dict:
    kayit = {
        "giris_zamani": giris_zamani.strftime("%Y-%m-%d %H:%M") if giris_zamani else "",
        "cikis_zamani": cikis_zamani.strftime("%Y-%m-%d %H:%M"),
        "sembol": sembol, "kaynak": kaynak, "giris_fiyati": giris_fiyati, "cikis_fiyati": cikis_fiyati,
        "tutar_try": tutar, "net_kar_try": net_kar,
        "net_kar_pct": net_kar / tutar * 100 if tutar else None,
        "r_sonucu": net_kar / risk_try if risk_try > 0 else None,
        "risk_try": risk_try, "stop_pct": stop_pct * 100 if stop_pct else None,
        "sure_saat": (cikis_zamani - giris_zamani).total_seconds() / 3600 if giris_zamani else None,
        "cikis_sebebi": cikis_sebebi, "hedef1": "H", "hedef2": "H", "btc_rejimi": btc_rejimi,
    }
    return kayit


def _gunluk_degeri(deger) -> str:
    if deger is None:
        return ""
    if isinstance(deger, float):
        return f"{deger:.8g}" if abs(deger) < 1 else f"{deger:.4f}".rstrip("0").rstrip(".")
    return str(deger)


def islem_gunlugune_yaz(kayit: dict, dosya: str = ISLEM_GUNLUGU_CSV) -> None:
    dosya_var = os.path.exists(dosya)
    try:
        with open(dosya, "a", newline="", encoding="utf-8") as f:
            yazici = csv.writer(f)
            if not dosya_var:
                yazici.writerow(ISLEM_GUNLUGU_ALANLARI)
            yazici.writerow([_gunluk_degeri(kayit.get(alan)) for alan in ISLEM_GUNLUGU_ALANLARI])
    except Exception as e:
        print(f"{RED}  (Islem gunlugu yazilamadi: {e}){RESET}")


def islem_gunlugunu_oku(dosya: str = ISLEM_GUNLUGU_CSV, gun: Optional[int] = None) -> list:
    if not os.path.exists(dosya):
        return []
    try:
        with open(dosya, newline="", encoding="utf-8") as f:
            kayitlar = list(csv.DictReader(f))
    except Exception as e:
        print(f"{RED}  (Islem gunlugu okunamadi: {e}){RESET}")
        return []
    if gun:
        sinir = (datetime.now() - timedelta(days=gun)).strftime("%Y-%m-%d %H:%M")
        kayitlar = [k for k in kayitlar if (k.get("cikis_zamani") or "") >= sinir]
    return kayitlar


def _ortalama(degerler: list) -> float:
    return sum(degerler) / len(degerler) if degerler else 0.0


def islem_ozeti_satirlari(kayitlar: list) -> list:
    """Islem gunlugu / gecmis veri testi icin ortak ozet."""
    if not kayitlar:
        return ["Henuz kapanmis islem yok."]
    kar = [_sayi(k.get("net_kar_try")) or 0.0 for k in kayitlar]
    kazanc, kayip = [x for x in kar if x > 0], [x for x in kar if x <= 0]
    rler = [r for r in (_sayi(k.get("r_sonucu")) for k in kayitlar) if r is not None]
    cikislar: dict = {}
    for k, x in zip(kayitlar, kar):
        sebep = k.get("cikis_sebebi") or "?"
        adet, toplam = cikislar.get(sebep, (0, 0.0))
        cikislar[sebep] = (adet + 1, toplam + x)
    return [
        f"Islem: {len(kar)} | kazanan {len(kazanc)} (%{len(kazanc) / len(kar) * 100:.0f}) | net {sum(kar):+,.2f} TL",
        f"Ortalama: kazanc {_ortalama(kazanc):+.2f} TL / kayip {_ortalama(kayip):+.2f} TL"
        + (f" | islem basina {_ortalama(rler):+.2f}R" if rler else ""),
        "Cikislar: " + ", ".join(f"{s} {a} ({t:+.2f} TL)"
                                 for s, (a, t) in sorted(cikislar.items(), key=lambda kv: kv[1][1])),
    ]


# ==========================================================================
# v10 BOLUM 5: GENEL HTTP ISTEK KATMANI - EXPONENTIAL BACKOFF
# ==========================================================================

def http_istek_yap(req: urllib.request.Request, timeout: float = 15, max_deneme: int = BACKOFF_MAX_DENEME):
    """
    v10: Ag kopmalari veya borsa HTTP 429 (rate-limit) / 5xx (sunucu
    hatasi) durumlarinda exponential backoff ile (2sn, 4sn, 8sn... en
    fazla BACKOFF_MAX_SANIYE) otomatik olarak yeniden dener - BOT COKMEZ.
    4xx istemci hatalari (orn. 400 gecersiz parametre, 401 yetkisiz)
    tekrar denemekle duzelmeyecegi icin ANINDA firlatilir.
    """
    gecikme = BACKOFF_BASLANGIC_SANIYE
    son_hata = None
    for deneme in range(1, max_deneme + 1):
        son_deneme = deneme >= max_deneme
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            son_hata = e
            if (e.code == 429 or e.code >= 500) and not son_deneme:
                print(f"{YELLOW}  HTTP {e.code} alindi ({deneme}/{max_deneme}), "
                      f"{gecikme:.1f}sn sonra tekrar denenecek...{RESET}")
                time.sleep(gecikme)
                gecikme = min(gecikme * 2, BACKOFF_MAX_SANIYE)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            son_hata = e
            if son_deneme:
                break
            print(f"{YELLOW}  Ag hatasi ({e}) ({deneme}/{max_deneme}), "
                  f"{gecikme:.1f}sn sonra tekrar denenecek...{RESET}")
            time.sleep(gecikme)
            gecikme = min(gecikme * 2, BACKOFF_MAX_SANIYE)
            continue
    raise son_hata


# ==========================================================================
# v10 BOLUM 2: TELEGRAM BILDIRIM ENTEGRASYONU
# ==========================================================================

def send_telegram(mesaj: str) -> None:
    """
    v13: TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID ortam degiskenleri
    tanimliysa mesaji kuyruga ekler ve HEMEN doner (ANA DONGUYU ASLA
    BLOKE ETMEZ). Ayri bir arka plan thread'i (_telegram_worker) mesaji
    exponential backoff ile gonderir; basarisiz denemeler artik
    SESSIZCE yutulmuyor, 'project_aurelius.log' dosyasina WARNING/ERROR
    olarak yaziliyor.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    _telegram_worker_baslat()
    try:
        _telegram_kuyrugu.put_nowait(mesaj)
    except Exception as e:
        logger.warning("Telegram kuyruguna eklenemedi: %s", e)


_telegram_kuyrugu: "queue.Queue[str]" = queue.Queue()
_telegram_thread_baslatildi = False
_telegram_thread_lock = threading.Lock()

TELEGRAM_MAX_DENEME = 3
TELEGRAM_BACKOFF_BASLANGIC = 2.0


def _telegram_gonder_gercek(mesaj: str) -> None:
    """Tek bir mesaji gercekten HTTP ile gonderir; exponential backoff ile
    en fazla TELEGRAM_MAX_DENEME kez dener. Son denemede de basarisiz
    olursa logger.error ile kaydeder (sessizce yutmaz)."""
    gecikme = TELEGRAM_BACKOFF_BASLANGIC
    for deneme in range(1, TELEGRAM_MAX_DENEME + 1):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": TELEGRAM_CHAT_ID,
                "text": mesaj,
                "parse_mode": "HTML",
            }).encode("utf-8")
            req = urllib.request.Request(url, data=data, headers={"User-Agent": "grid-bot-sim"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
            return  # basarili
        except Exception as e:
            logger.warning("Telegram gonderim denemesi %d/%d basarisiz: %s", deneme, TELEGRAM_MAX_DENEME, e)
            if deneme < TELEGRAM_MAX_DENEME:
                time.sleep(gecikme)
                gecikme *= 2
    logger.error("Telegram mesaji %d denemeden sonra gonderilemedi, vazgecildi: %.60s...",
                 TELEGRAM_MAX_DENEME, mesaj)


def _telegram_worker() -> None:
    """Arka plan thread'i: kuyruktaki mesajlari sirayla, ana donguyu
    ETKILEMEDEN gonderir. daemon=True oldugu icin ana program kapaninca
    otomatik sonlanir."""
    while True:
        mesaj = _telegram_kuyrugu.get()
        try:
            _telegram_gonder_gercek(mesaj)
        except Exception as e:  # noqa: BLE001 - worker thread ASLA olmemeli
            logger.error("Telegram worker beklenmeyen hata: %s", e)
        finally:
            _telegram_kuyrugu.task_done()


def telegram_kuyrugunu_bosalt(zaman_asimi_saniye: float = 20.0) -> None:
    """Worker thread daemon oldugu icin program kapaninca kuyruktaki mesajlar
    atilir; ACIL FREN / KRITIK HATA / Ctrl+C uyarilari tam da cikistan hemen
    once kuyruga eklenir. Cikmadan once kuyrugun bosalmasini (en fazla
    zaman_asimi_saniye) bekler."""
    if not _telegram_thread_baslatildi:
        return
    bitis = time.time() + zaman_asimi_saniye
    while _telegram_kuyrugu.unfinished_tasks and time.time() < bitis:
        time.sleep(0.2)
    if _telegram_kuyrugu.unfinished_tasks:
        logger.warning("Cikista %d Telegram mesaji gonderilemeden kaldi.", _telegram_kuyrugu.unfinished_tasks)


def _telegram_worker_baslat() -> None:
    global _telegram_thread_baslatildi
    with _telegram_thread_lock:
        if _telegram_thread_baslatildi:
            return
        t = threading.Thread(target=_telegram_worker, daemon=True, name="telegram-worker")
        t.start()
        _telegram_thread_baslatildi = True


# ==========================================================================
# v10 BOLUM 1: KALICI DURUM YONETIMI (STATE PERSISTENCE)
# ==========================================================================

def durumu_kaydet(kasa: "MerkeziKasa", pozisyonlar: dict, rapor: "RaporlamaDurumu" = None) -> None:
    """Acik pozisyonlari, kasayi, risk/trend durumunu ve rapor sayaclarini JSON dosyasina ATOMIK
    olarak yazar (once .tmp dosyasina yazip os.replace ile degistirir - yazma sirasinda bot
    cokerse bile dosya asla yarim/bozuk kalmaz). Bicim v21 ile uyumludur."""
    try:
        veri = {
            "calisma_modu": _aktif_calisma_modu(),
            "alim_durumu": _alim_durumu,
            "kasa_bakiye": kasa.bakiye,
            "kasa_baslangic": kasa.baslangic,
            "kasa_toplam_komisyon": kasa.toplam_komisyon,
            "kaydedilme_zamani": datetime.now().isoformat(),
            "risk": _risk.to_dict(),
            "strateji": STRATEJI,
            "trend": _trend_durumu,
            "pozisyonlar": {},
        }
        if rapor is not None:
            veri["raporlama"] = rapor.to_dict()
        for sym, b in pozisyonlar.items():
            if not b.has_open_position:
                continue  # v22: kapanmis pozisyonun saklanacak bir durumu yok
            veri["pozisyonlar"][sym] = {
                "coin_name": b.coin_name,
                "starting_try": b.starting_try,
                "cash_try": b.cash_try,
                "coin_qty": b.coin_qty,
                "trade_count": b.trade_count,
                "realized_pnl": b.realized_pnl,
                "toplam_komisyon": b.toplam_komisyon,
                "alis_zamani": b.alis_zamani.isoformat() if b.alis_zamani else None,
                "giris_bilgi": b.giris_bilgi,
                "acik_islem_pnl": b.acik_islem_pnl,
                "grid": [
                    {
                        "price": lvl.price,
                        "has_position": lvl.has_position,
                        "buy_qty": lvl.buy_qty,
                        "buy_price": lvl.buy_price,
                        "en_yuksek_fiyat": lvl.en_yuksek_fiyat,
                        "borsa_stop_emir_id": lvl.borsa_stop_emir_id,
                        "borsa_stop_fiyati": lvl.borsa_stop_fiyati,
                        "borsa_stop_miktari": lvl.borsa_stop_miktari,
                        "risk_birimi": lvl.risk_birimi,
                        "ilk_stop": lvl.ilk_stop,
                        "trend_stop": lvl.trend_stop,
                    }
                    for lvl in b.grid
                ],
            }
        gecici = STATE_DOSYASI + ".tmp"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(veri, f, ensure_ascii=False, indent=2)
        os.replace(gecici, STATE_DOSYASI)
    except Exception as e:
        print(f"{RED}  (Durum kaydedilemedi: {e}){RESET}")


def _aktif_calisma_modu() -> str:
    return "CANLI" if CANLI_MOD else "SIMULASYON"


class CanliDurumKorumasi(Exception):
    """CANLI modda kaydedilmis durum dosyasi varken bot SIMULASYON modunda
    baslatildi. Dosya kenara alinirsa sonraki canli baslatmada acik gercek
    pozisyonlar unutulur (stop-loss/kar-al yonetimi olmadan kalir); bu yuzden
    bot hic baslatilmaz ve dosyaya dokunulmaz."""


def durumu_yukle() -> Optional[dict]:
    """v10: STATE_DOSYASI varsa okur ve dondurur. Yoksa veya bozuksa
    None doner (bu durumda temiz baslangic yapilir).

    v17 FIX: Dosya baska bir calisma modunda kaydedilmisse (orn. SIMULASYON
    durumu varken CANLI_MOD=True ile baslatildi) YUKLENMEZ: aksi halde sanal
    pozisyonlar ve sanal kasa GERCEK para ile islem yapan bota tasinir ve bot
    sahip olmadigi coinleri satmaya calisir. Eski dosya silinmez, yedeklenir.
    "calisma_modu" alani olmayan eski dosyalar SIMULASYON kabul edilir (onceki
    surumlerde canli mod hic basarili emir gonderemiyordu)."""
    if not os.path.exists(STATE_DOSYASI):
        return None
    try:
        with open(STATE_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except Exception as e:
        print(f"{RED}  (Durum dosyasi okunamadi, temiz baslangic yapilacak: {e}){RESET}")
        return None

    kayitli_mod = veri.get("calisma_modu", "SIMULASYON")
    aktif_mod = _aktif_calisma_modu()
    if kayitli_mod == "CANLI" and aktif_mod != "CANLI":
        acik = sum(1 for p in veri.get("pozisyonlar", {}).values()
                   if any(l.get("has_position") for l in p.get("grid", [])))
        raise CanliDurumKorumasi(
            f"HATA: Bu klasordeki durum dosyasi CANLI modda kaydedilmis ({acik} acik gercek pozisyon), "
            f"ama bot su an {aktif_mod} modunda baslatildi.\n"
            "  Canli kaydi korumak icin bot BASLATILMADI, dosyaya dokunulmadi.\n"
            "  Canli devam etmek icin 'set AURELIUS_CANLI_MOD=1' satirini (ve diger set satirlarini)\n"
            "  yazip tekrar baslatin. Simulasyon denemek istiyorsaniz botu BASKA bir klasorde calistirin.")
    if kayitli_mod != aktif_mod:
        yedek = f"{STATE_DOSYASI}.{kayitli_mod.lower()}.yedek"
        if os.path.exists(yedek):  # onceki bir yedegin uzerine asla yazma
            yedek = f"{yedek}.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            os.replace(STATE_DOSYASI, yedek)
            yedek_notu = f"eski dosya '{os.path.basename(yedek)}' olarak yedeklendi"
        except OSError as e:
            yedek_notu = f"yedeklenemedi ({e}) - ilk kayitta uzerine yazilacak"
        print(f"{YELLOW}  Durum dosyasi {kayitli_mod} modunda kaydedilmis; {aktif_mod} modunda "
              f"KULLANILMIYOR, temiz baslangic yapiliyor ({yedek_notu}).{RESET}")
        logger.warning("Durum dosyasi modu uyusmuyor (%s != %s): %s", kayitli_mod, aktif_mod, yedek_notu)
        return None
    return veri


def durumdan_kasa_ve_pozisyonlar_olustur(veri: dict):
    """Kaydedilmis JSON verisinden MerkeziKasa ve CoinBot nesnelerini yeniden kurar - bot kaldigi
    yerden devam eder. v22: v21 oncesi stratejilerden kalan (trend_stop'u olmayan) acik pozisyon
    trend kurallarina aktarilir: stop eski stop seviyesi, sonra her gun zirve - 3 x ATR'ye yukselir."""
    kasa = MerkeziKasa(veri.get("kasa_baslangic", TOPLAM_SANAL_BAKIYE_TRY))
    kasa.bakiye = veri.get("kasa_bakiye", kasa.baslangic)
    kasa.toplam_komisyon = veri.get("kasa_toplam_komisyon", 0.0)

    pozisyonlar = {}
    for sym, p in veri.get("pozisyonlar", {}).items():
        b = CoinBot(symbol=sym, coin_name=p.get("coin_name", _coin_adi(sym)), starting_try=p.get("starting_try", 0.0))
        b.cash_try = p.get("cash_try", b.starting_try)
        b.coin_qty = p.get("coin_qty", 0.0)
        b.trade_count = p.get("trade_count", 0)
        b.realized_pnl = p.get("realized_pnl", 0.0)
        b.toplam_komisyon = p.get("toplam_komisyon", 0.0)
        b.alis_zamani = _tarih_oku(p.get("alis_zamani"))
        b.giris_bilgi = p.get("giris_bilgi") or {}
        b.acik_islem_pnl = p.get("acik_islem_pnl", 0.0)
        b.grid = [
            GridLevel(
                price=lvl.get("price", 0.0),
                has_position=lvl.get("has_position", False),
                buy_qty=lvl.get("buy_qty", 0.0),
                buy_price=lvl.get("buy_price", 0.0),
                en_yuksek_fiyat=lvl.get("en_yuksek_fiyat", 0.0),
                borsa_stop_emir_id=lvl.get("borsa_stop_emir_id"),
                borsa_stop_fiyati=lvl.get("borsa_stop_fiyati", 0.0),
                borsa_stop_miktari=lvl.get("borsa_stop_miktari", 0.0),
                risk_birimi=lvl.get("risk_birimi", 0.0),
                ilk_stop=lvl.get("ilk_stop", 0.0),
                trend_stop=lvl.get("trend_stop", 0.0),
            )
            for lvl in p.get("grid", [])
        ]
        b.grid = [lvl for lvl in b.grid if lvl.has_position]  # bos grid seviyeleri eski stratejiden kalma
        for lvl in b.grid:
            if lvl.trend_stop <= 0 and lvl.buy_price > 0:
                lvl.ilk_stop = lvl.ilk_stop or lvl.buy_price * (1 - ESKI_SURUM_STOP_PCT)
                lvl.risk_birimi = lvl.risk_birimi or (lvl.buy_price - lvl.ilk_stop)
                lvl.trend_stop = lvl.ilk_stop
                lvl.en_yuksek_fiyat = lvl.en_yuksek_fiyat or lvl.buy_price
                print(f"{CYAN}  {sym}: onceki stratejiden kalan pozisyon trend kurallarina aktarildi "
                      f"(stop {format_fiyat(lvl.trend_stop)} TRY, her gun yukseltilir).{RESET}")
        if b.has_open_position and b.grid:
            pozisyonlar[sym] = b
        elif b.has_open_position:
            print(f"{RED}  UYARI: {sym} kaydinda {b.coin_qty:.8f} coin var ama acik pozisyon bilgisi yok - bot bu "
                  f"coini YONETMEYECEK. Binance TR'de kontrol edin.{RESET}")
            logger.warning("%s durum kaydinda pozisyon bilgisi yok (coin_qty=%.8f), yonetilmiyor", sym, b.coin_qty)

    acik_sayisi = sum(1 for b in pozisyonlar.values() if b.has_open_position)
    return kasa, pozisyonlar, acik_sayisi


# ==========================================================================
# v10 BOLUM 4: CANLI MOD - BINANCE TR IMZALI (SIGNED) ISTEKLER
# ==========================================================================

def _binance_imzali_sorgu(params: dict) -> str:
    """
    RFC 2104 HMAC-SHA256 imzali query string olusturur. v17 FIX: imzalama
    oncesi BINANCE_TR_SECRET_KEY'in gercekten bir str oldugu KONTROL EDILIR -
    aksi halde ".encode()" cagrisi "tuple/NoneType object has no attribute
    'encode'" gibi anlasilmasi zor bir hatayla derinlerde patlar; burada
    net, Turkce bir hata mesajiyla ERKENDEN durdurulur.
    """
    if not isinstance(BINANCE_TR_SECRET_KEY, str) or not BINANCE_TR_SECRET_KEY:
        raise TypeError(
            "BINANCE_TR_SECRET_KEY tanimli/gecerli bir str degil - imza olusturulamaz. "
            "BINANCE_TR_SECRET_KEY ortam degiskenini kontrol edin."
        )
    params = dict(params)
    params["timestamp"] = int(time.time() * 1000)
    params.setdefault("recvWindow", RECV_WINDOW_MS)
    query = urllib.parse.urlencode(params)
    imza = hmac.new(BINANCE_TR_SECRET_KEY.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{query}&signature={imza}"


def _anahtar_maskele(anahtar: str) -> str:
    """API key'in sadece ilk/son 4 karakterini gosterir (panelle karsilastirma icin)."""
    if len(anahtar) <= 12:
        return "*" * len(anahtar)
    return f"{anahtar[:4]}...{anahtar[-4:]}"


def _supheli_karakter_var(deger: str) -> bool:
    """Bosluk, tirnak, gorunmez ya da ASCII disi karakter (kopyala-yapistir artigi)."""
    return any(c.isspace() or c in "\"'`" or not c.isprintable() or ord(c) > 127 for c in deger)


def api_anahtari_teshis_raporu() -> None:
    """
    CANLI baslangicta borsaya gidecek kimliklerin MASKELI ozetini basar:
    API key'in ilk/son 4 karakteri + uzunlugu, secret'in SADECE uzunlugu
    (tek bir karakteri bile yazdirilmaz). Binance TR panelindeki anahtarla
    karsilastirarak yanlis/eski/eksik kopyalanmis anahtar hemen fark edilir.
    """
    print(f"{CYAN}  API KEY    : {_anahtar_maskele(BINANCE_TR_API_KEY)}  "
          f"({len(BINANCE_TR_API_KEY)} karakter){RESET}")
    print(f"{CYAN}  SECRET KEY : (gizli)  ({len(BINANCE_TR_SECRET_KEY)} karakter){RESET}")
    for isim, deger in (("BINANCE_TR_API_KEY", BINANCE_TR_API_KEY),
                        ("BINANCE_TR_SECRET_KEY", BINANCE_TR_SECRET_KEY)):
        if _supheli_karakter_var(deger):
            print(f"{YELLOW}  UYARI: {isim} bosluk/tirnak/gorunmez karakter iceriyor - "
                  f"kopyalarken fazladan karakter gelmis olabilir.{RESET}")
    if BINANCE_TR_API_KEY and BINANCE_TR_API_KEY == BINANCE_TR_SECRET_KEY:
        print(f"{YELLOW}  UYARI: API KEY ile SECRET KEY AYNI - biri yanlis kopyalanmis.{RESET}")


def _borsa_hata_ipucu(kod, mesaj) -> None:
    """
    Binance TR'nin kimlik dogrulama hatalarinda (code/msg) neyin yanlis
    oldugunu ve nasil duzeltilecegini Turkce olarak basar. Taninmayan
    hatalarda hicbir sey yapmaz.
    """
    metin = str(mesaj or "").lower()
    if kod == 3700 or "api-key" in metin:
        satirlar = [
            "NEDEN: Binance TR istekteki API anahtarini TANIMADI (imza veya saat hatasi degil -",
            "       anahtarin KENDISI reddedildi). Kontrol listesi:",
            " 1) Anahtar Binance TR'de mi olusturuldu (www.binance.tr -> Profil -> API Yonetimi)?",
            "    Binance Global (binance.com) anahtarlari Binance TR'de GECMEZ.",
            " 2) Yukarida basilan 'API KEY' ilk/son 4 karakteri ve uzunlugu paneldeki anahtarla ayni mi?",
            "    Degilse anahtar eksik/yanlis kopyalanmis ya da eski bir deger okunuyor",
            "    (orn. daha once 'setx' ile kalici kaydedilmis eski anahtar).",
            " 3) API KEY ile SECRET KEY yer degistirmis olabilir mi?",
            " 4) Anahtar panelde hala AKTIF mi (silinmis / onayi tamamlanmamis olabilir)?",
            " 5) Anahtara IP kisitlamasi koyduysaniz, su anki IP adresiniz listede mi?",
            " 6) Windows cmd'de TIRNAKSIZ ve botla AYNI pencerede tanimlayin:",
            "      set BINANCE_TR_API_KEY=anahtariniz",
            "      set BINANCE_TR_SECRET_KEY=gizli_anahtariniz",
            " Emin degilseniz: panelde YENI bir anahtar olusturup (Okuma + Spot Islem izni)",
            " iki degeri de yeniden kopyalayin.",
        ]
    elif "signature" in metin:
        satirlar = [
            "NEDEN: API KEY tanindi ama IMZA gecersiz - SECRET KEY yanlis/eksik kopyalanmis",
            "       ya da baska bir anahtarin secret'i. Paneldeki anahtarin secret'ini tekrar",
            "       tanimlayin (secret sadece olusturma aninda gosterilir; kaybettiyseniz",
            "       yeni anahtar olusturun).",
        ]
    elif "timestamp" in metin or "recvwindow" in metin:
        satirlar = [
            "NEDEN: Bilgisayarinizin saati borsa saatinden fazla sapmis. Windows: Ayarlar ->",
            "       Saat ve dil -> Tarih ve saat -> 'Simdi esitle' ve botu yeniden baslatin.",
        ]
    else:
        return
    for satir in satirlar:
        print(f"{YELLOW}  {satir}{RESET}")


def _python_proxy_ayarlari() -> dict:
    """Python'un (urllib) http/https isteklerinde kullanacagi proxy (ortam degiskeni veya Windows ayari)."""
    return {k: v for k, v in urllib.request.getproxies().items() if k in ("http", "https")}


def _ag_hatasi_ipucu(hata: Exception) -> None:
    """
    Borsaya hic ulasilamadiginda (SSL/baglanti hatasi) olasi nedenleri ve
    Python'un kullandigi proxy ayarini Turkce olarak basar.
    """
    metin = str(hata)
    if "WRONG_VERSION_NUMBER" in metin or "SSL" in metin:
        satirlar = [
            "NEDEN: Sifreli (TLS) baglanti kurulamadi - bilgisayariniz ile borsa arasindaki bir",
            "       sey (VPN, antivirusun 'HTTPS/SSL tarama' ozelligi, proxy veya ag filtresi)",
            "       sifreli yanit yerine duz metin dondurdu. Kod/API anahtari ile ilgili DEGIL.",
        ]
    else:
        satirlar = ["NEDEN: Borsaya baglanti kurulamadi (internet, DNS, VPN veya guvenlik duvari)."]
    proxyler = _python_proxy_ayarlari()
    satirlar += [
        f"Python'un kullandigi proxy: {proxyler or 'yok'}",
        "Ne yapmali: VPN'i kapatip/acip, antivirusun HTTPS taramasini gecici kapatip veya",
        "baska bir aga (orn. telefon hotspot) gecip tekrar deneyin. Ayrintili teshis icin:",
        "    python project_aurelius_bot_v22.py baglanti",
    ]
    if proxyler:
        satirlar.append("Proxy'yi bu pencerede devre disi birakmak icin:  set NO_PROXY=*")
    for satir in satirlar:
        print(f"{YELLOW}  {satir}{RESET}")


def _tls_ilk_yaniti_al(host: str, port: int) -> bytes:
    """
    Gercek bir TLS ClientHello gonderip karsidan gelen ILK baytlari ham
    olarak dondurur. Normal bir sunucu TLS kaydiyla (0x16/0x15) yanit
    verir; araya giren bir filtre/proxy ise genellikle duz bir HTTP
    yaniti (orn. erisim engeli sayfasina yonlendirme) dondurur.
    """
    giden = ssl.MemoryBIO()
    tls = ssl.create_default_context().wrap_bio(ssl.MemoryBIO(), giden, server_hostname=host)
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        pass
    with socket.create_connection((host, port), timeout=10) as ham_soket:
        ham_soket.sendall(giden.read())
        try:
            return ham_soket.recv(400)
        except ConnectionResetError:
            return b""


def _ham_yanit_ozeti(ham: bytes) -> str:
    """_tls_ilk_yaniti_al() sonucunu okunur bir satira cevirir."""
    if not ham:
        return "BOS: baglanti hemen kapatildi"
    if ham[:1] == b"\x16":
        return "TLS el sikisma yaniti (normal)"
    if ham[:1] == b"\x15":
        return f"TLS uyari (alert) kaydi: {ham[:7].hex(' ')}"
    return f"TLS DISI YANIT: {ham[:300]!r}"


def baglanti_testi() -> None:
    """
    'python project_aurelius_bot_v22.py baglanti' ile calisir. API anahtari
    GEREKTIRMEZ, emir GONDERMEZ. Binance TR'ye giden yolu adim adim test
    eder (DNS -> TLS el sikisma -> ozel API sunucusu -> piyasa verisi
    sunucusu) ve sorunun nerede oldugunu gosterir.
    """
    adres = urllib.parse.urlparse(BINANCE_TR_PRIVATE_BASE_URL)
    host, port = adres.hostname, adres.port or 443
    proxyler = _python_proxy_ayarlari()
    print(f"{BOLD}BAGLANTI TESTI - {host}{RESET}")
    print(f"  Python {sys.version.split()[0]} | {ssl.OPENSSL_VERSION}")
    print(f"  Python'un kullandigi proxy: {proxyler or 'yok'}")

    try:
        ipler = sorted({a[4][0] for a in socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)})
        print(f"{GREEN}  [1] DNS OK: {host} -> {', '.join(ipler)}{RESET}")
    except Exception as e:
        print(f"{RED}  [1] DNS HATASI: {e} - internet baglantinizi / DNS ayarinizi kontrol edin.{RESET}")
        return

    # [2] Dogrudan TLS el sikisma - sorun aralikli olabildigi icin birkac kez denenir.
    deneme_sayisi = 5
    basarili, hatalar, tls_bilgi, sertifika_hatasi = 0, [], "", None
    for _ in range(deneme_sayisi):
        try:
            with socket.create_connection((host, port), timeout=10) as ham_soket:
                with ssl.create_default_context().wrap_socket(ham_soket, server_hostname=host) as tls:
                    veren = dict(alan[0] for alan in tls.getpeercert().get("issuer", ()))
                    tls_bilgi = (f"{tls.version()}, sertifikayi veren: "
                                 f"{veren.get('organizationName', '?')} / {veren.get('commonName', '?')}")
                    basarili += 1
        except ssl.SSLCertVerificationError as e:
            sertifika_hatasi = e
            break
        except Exception as e:
            hatalar.append(str(e))

    if sertifika_hatasi is not None:
        print(f"{RED}  [2] SERTIFIKA DOGRULANAMADI: {sertifika_hatasi}{RESET}")
        print(f"{YELLOW}      Baglanti Binance TR'nin degil BASKA bir sertifikayla kuruluyor - antivirus "
              f"(HTTPS tarama) veya bir ag cihazi trafigi araya girip inceliyor olabilir.{RESET}")
    else:
        renk = GREEN if basarili == deneme_sayisi else (YELLOW if basarili else RED)
        print(f"{renk}  [2] TLS el sikisma: {deneme_sayisi} denemeden {basarili} basarili"
              f"{f' ({tls_bilgi})' if tls_bilgi else ''}{RESET}")
        for hata in dict.fromkeys(hatalar):
            print(f"{RED}      Hata ({hatalar.count(hata)} kez): {hata}{RESET}")

    tls_disi_yanit = False
    if hatalar:
        ornekler = []
        for _ in range(deneme_sayisi):
            try:
                ornekler.append(_ham_yanit_ozeti(_tls_ilk_yaniti_al(host, port)))
            except Exception as e:
                ornekler.append(f"(alinamadi: {e})")
        print(f"{YELLOW}      TLS istegine karsi gelen ilk yanitlar ({deneme_sayisi} deneme):{RESET}")
        for ornek in dict.fromkeys(ornekler):
            print(f"{YELLOW}        - {ornekler.count(ornek)} kez: {ornek}{RESET}")
        tls_disi_yanit = any(o.startswith(("TLS DISI", "BOS")) for o in ornekler)

    sonuclar = {}
    for anahtar, etiket, url in (
            ("ozel", "[3] Ozel API sunucusu", f"{BINANCE_TR_PRIVATE_BASE_URL}/open/v1/common/time"),
            ("piyasa", "[4] Piyasa verisi sunucusu", "https://api.binance.me/api/v3/time")):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "project-aurelius-bot"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                print(f"{GREEN}  {etiket} OK: HTTP {resp.status} {resp.read(150)!r}{RESET}")
            sonuclar[anahtar] = True
        except urllib.error.HTTPError as e:
            print(f"{GREEN}  {etiket} ULASILDI (HTTP {e.code}) - baglanti calisiyor.{RESET}")
            sonuclar[anahtar] = True
        except Exception as e:
            print(f"{RED}  {etiket} HATASI: {e}{RESET}")
            sonuclar[anahtar] = False

    print()
    if not hatalar and sertifika_hatasi is None and all(sonuclar.values()):
        print(f"{GREEN}{BOLD}  SONUC: Baglanti sorunsuz.{RESET}")
    elif (hatalar or not sonuclar["ozel"]) and sonuclar["piyasa"]:
        for satir in (
            f"SONUC: Internete cikabiliyorsunuz (piyasa sunucusu OK), ama {host} baglantilarina",
            "aradaki bir sistem mudahale ediyor" + (" (sifreli yanit yerine baska bir yanit geliyor)."
                                                    if tls_disi_yanit else "."),
            "Bu, botun veya API anahtarinin sorunu DEGIL. Olasi kaynaklar:",
            " - bagli oldugunuz agin guvenlik duvari / icerik filtresi (yurt, is yeri, okul, site agi)",
            " - internet saglayicinizin 'Guvenli Internet' filtresi veya modemdeki ebeveyn denetimi",
            " - bilgisayardaki guvenlik yazilimi (web koruma / ebeveyn denetimi)",
            "Kaynagi ayirt etmek icin ayni testi baska bir baglantiyla (orn. telefonun mobil verisi) deneyin.",
        ):
            print(f"{YELLOW}{BOLD}  {satir}{RESET}")
    print("\n  Bu ekranin goruntusunu paylasabilirsiniz (API anahtari icermez).")


def binance_signed_request(method: str, path: str, params: Optional[dict] = None):
    """
    v17 FIX: CANLI MOD icin RFC 2104 HMAC-SHA256 imzali istek gonderir.
    X-MBX-APIKEY header'i ile birlikte Binance TR'nin ozel (orn.
    /open/v1/account/spot GET) uc noktalarina istek atar.

    HATA YAKALAMALI: HTTP hatasi (orn. 401 "Invalid API-key, IP, or
    permissions for action.") veya baglanti/parse sorunu olursa, borsanin
    donduğu HAM YANIT GOVDESI (varsa) hem konsola basilir hem de
    logger.error ile 'project_aurelius.log' dosyasina KALICI olarak
    yazilir - boylece "Invalid API-key" gibi hatalarin GERCEK nedeni
    (yanlis IP kisitlamasi, eksik izin, suresi gecmis anahtar, saat
    senkron sorunu vb.) korunur ve kaybolmaz. Hata bu fonksiyonda
    YUTULMAZ - tekrar firlatilir; cagiran taraf (binance_serbest_try_
    bakiyesi -> mutabakat_yap / run_simulation baslangici) KENDI
    try/except'inde yakalar, bot COKMEZ.
    """
    if not isinstance(BINANCE_TR_API_KEY, str) or not BINANCE_TR_API_KEY:
        hata = TypeError(
            "BINANCE_TR_API_KEY tanimli/gecerli bir str degil - istek gonderilemez. "
            "BINANCE_TR_API_KEY ortam degiskenini kontrol edin."
        )
        logger.error("Binance TR imzali istek iptal: %s", hata)
        raise hata

    try:
        query_signed = _binance_imzali_sorgu(params or {})
        headers = {"X-MBX-APIKEY": BINANCE_TR_API_KEY, "User-Agent": "project-aurelius-bot"}

        if method == "GET":
            url = f"{BINANCE_TR_PRIVATE_BASE_URL}{path}?{query_signed}"
            req = urllib.request.Request(url, headers=headers, method="GET")
        else:
            url = f"{BINANCE_TR_PRIVATE_BASE_URL}{path}"
            req = urllib.request.Request(url, data=query_signed.encode("utf-8"), headers=headers, method=method)

        # Emir (POST) istekleri idempotent degildir: zaman asimi/5xx sonrasi
        # otomatik tekrar, borsaya ulasmis bir emri IKINCI kez gonderebilir.
        max_deneme = BACKOFF_MAX_DENEME if method == "GET" else 1
        return http_istek_yap(req, timeout=15, max_deneme=max_deneme)

    except urllib.error.HTTPError as e:
        try:
            ham_govde = e.read().decode("utf-8", errors="replace")
        except Exception:
            ham_govde = "(govde okunamadi)"
        print(f"{RED}  BINANCE TR IMZALI ISTEK HATASI ({method} {path}): "
              f"HTTP {e.code} -> {ham_govde}{RESET}")
        logger.error("Binance TR imzali istek HTTP hatasi (%s %s): kod=%s ham_govde=%s",
                     method, path, e.code, ham_govde)
        _borsa_hata_ipucu(None, ham_govde)
        raise
    except Exception as e:
        print(f"{RED}  BINANCE TR IMZALI ISTEK BEKLENMEYEN HATA ({method} {path}): {e}{RESET}")
        logger.error("Binance TR imzali istek beklenmeyen hata (%s %s): %s", method, path, e)
        if isinstance(e, (urllib.error.URLError, OSError)):
            _ag_hatasi_ipucu(e)
        raise


def _binance_tr_bakiye_listesini_cikar(veri) -> Optional[list]:
    """
    v17 FIX: Binance TR'nin /open/v1/account/spot yaniti Binance Global'den
    FARKLI bir "zarf" (envelope) kullanir - bakiye listesi yanitin KOK
    dizininde DEGIL, "data" sozlugu altinda "accountAssets" anahtariyla gelir:
        {"code": 0, "msg": "Success", "data": {"canTrade": 1, ...,
         "accountAssets": [{"asset": "TRY", "free": "0", "locked": "0"}, ...]}}
    (Kaynak: ayni /open/v1 API ailesini kullanan Tokocrypto icin ccxt'nin
    fetch_balance uygulamasi - Binance TR resmi dokumani degil.) Farkli bir
    surum ihtimaline karsi "balances"/"assets" de yedek olarak denenir.
    "code" 0'dan farkliysa (API hatasi) veya format taninmiyorsa ham yaniti
    loglar ve None dondurur. None, "bakiye 0" ile KARISTIRILMAMALIDIR:
    cagiran taraf okunamayan bir yaniti asla sifir bakiye gibi kullanmamali.
    """
    if not isinstance(veri, dict):
        logger.error("Binance TR hesap yaniti beklenmeyen tip (%s): %r", type(veri).__name__, veri)
        return None

    kod = veri.get("code")
    if kod not in (0, None):
        mesaj = veri.get("msg") or veri.get("message") or "(mesaj yok)"
        print(f"{RED}  BINANCE TR HESAP SORGUSU API HATASI DONDURDU: code={kod} msg={mesaj}{RESET}")
        logger.error("Binance TR hesap sorgusu API hatasi: code=%s msg=%s ham_yanit=%r", kod, mesaj, veri)
        _borsa_hata_ipucu(kod, mesaj)
        return None

    data = veri.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("accountAssets"), list):
            return data["accountAssets"]
        if isinstance(data.get("balances"), list):
            return data["balances"]
        if isinstance(data.get("assets"), list):
            return data["assets"]

    # Geriye donuk uyumluluk: bazi eski/alternatif yanitlarda liste
    # dogrudan kok dizinde olabilir.
    if isinstance(veri.get("balances"), list):
        return veri["balances"]

    print(f"{RED}  BINANCE TR HESAP YANITI BEKLENMEYEN FORMATTA - ham yanit log dosyasina yazildi.{RESET}")
    logger.error("Binance TR hesap yanitinda 'data.accountAssets' bulunamadi - ham yanit: %r", veri)
    return None


def binance_hesap_bakiyeleri() -> dict:
    """
    /open/v1/account/spot yanitini {varlik: {"free": float, "locked": float}}
    sozlugune cevirir. Ham yaniti [BORSA YANITI] onekiyle terminale basar.
    Yanit okunamazsa (API hatasi, beklenmeyen format, sayiya cevrilemeyen
    miktar) RuntimeError FIRLATIR - asla sessizce bos/sifir dondurmez.
    Alan adi icin "asset" yoksa "coin"/"currency"; miktar icin "free" yoksa
    "available", kilitli icin "locked" yoksa "frozen" denenir.
    """
    veri = binance_signed_request("GET", ACCOUNT_ENDPOINT_PATH)
    print(f"{GRAY}[BORSA YANITI]: {veri!r}{RESET}")
    liste = _binance_tr_bakiye_listesini_cikar(veri)
    if liste is None:
        raise RuntimeError("Binance TR hesap yaniti okunamadi (API hatasi veya beklenmeyen format) "
                           "- [BORSA YANITI] satirina bakin.")

    bakiyeler = {}
    for kayit in liste:
        if not isinstance(kayit, dict):
            continue
        varlik = kayit.get("asset") or kayit.get("coin") or kayit.get("currency")
        if not varlik:
            continue
        serbest = kayit.get("free")
        if serbest is None:
            serbest = kayit.get("available")
        kilitli = kayit.get("locked")
        if kilitli is None:
            kilitli = kayit.get("frozen")
        try:
            bakiyeler[varlik] = {"free": float(serbest or 0), "locked": float(kilitli or 0)}
        except (TypeError, ValueError):
            logger.error("Binance TR bakiye kaydi sayiya cevrilemedi, ham kayit: %r", kayit)
            raise RuntimeError(f"Binance TR {varlik} bakiyesi sayiya cevrilemedi: {kayit!r}")
    return bakiyeler


def bakiye_ozeti_yazdir(bakiyeler: dict) -> None:
    """
    Borsadaki SIFIRDAN FARKLI varliklari (serbest/kilitli) okunakli bir
    tablo olarak basar. Bot SADECE serbest TRY ile alim yapar; bu ozet,
    "bakiye 0 gorunuyor" durumunda paranin nerede oldugunu (acik emirde
    kilitli TRY, USDT/coin olarak duran bakiye) hemen gosterir.
    """
    dolu = {v: b for v, b in bakiyeler.items() if b["free"] > 0 or b["locked"] > 0}
    print(f"{CYAN}  BORSADAKI VARLIKLARINIZ ({len(dolu)} adet sifirdan farkli):{RESET}")
    for varlik, b in sorted(dolu.items(), key=lambda x: (x[0] != "TRY", x[0]))[:20]:
        print(f"{CYAN}    {varlik:<8} serbest: {b['free']:>18,.8f}   kilitli: {b['locked']:>18,.8f}{RESET}")
    if len(dolu) > 20:
        print(f"{CYAN}    ... ve {len(dolu) - 20} varlik daha{RESET}")

    try_kaydi = bakiyeler.get("TRY", {"free": 0.0, "locked": 0.0})
    if try_kaydi["free"] > 0:
        return
    if try_kaydi["locked"] > 0:
        print(f"{YELLOW}  NOT: {try_kaydi['locked']:,.2f} TRY acik emirlerde KILITLI - bot sadece SERBEST TRY "
              f"kullanir. Binance TR'de acik emirleri iptal ederseniz serbest bakiyeye doner.{RESET}")
    diger = [v for v in dolu if v != "TRY"]
    if diger:
        print(f"{YELLOW}  NOT: Bakiyeniz TRY disinda varliklarda ({', '.join(diger[:8])}"
              f"{'...' if len(diger) > 8 else ''}). Bot alimlari SADECE serbest TRY ile yapar - "
              f"kullanmak istediginiz tutari Binance TR'de TRY'ye cevirin.{RESET}")
    elif not dolu:
        print(f"{YELLOW}  NOT: Hesapta hic bakiye gorunmuyor. Para Binance TR SPOT cuzdaninda mi? "
              f"(API anahtari dogru HESABA mi ait?){RESET}")


def binance_serbest_try_bakiyesi() -> float:
    """
    v17 FIX: /open/v1/account/spot uzerinden GERCEK serbest TRY bakiyesini
    ceker ("data.accountAssets" zarfi - bkz. binance_hesap_
    bakiyeleri). Yanit okunamazsa RuntimeError firlatir; boylece bir API
    hatasi "0.00 TRY" gibi gorunup kasayi sifirlamaz (mutabakat sonrasi
    sahte ACIL FREN tetiklemesine yol acabiliyordu). Yanit gecerli ama TRY
    kaydi yoksa gercekten 0 kabul edilir.
    """
    bakiyeler = binance_hesap_bakiyeleri()
    try_kaydi = bakiyeler.get("TRY")
    if try_kaydi is None:
        logger.warning("Binance TR hesap yanitinda TRY varligi bulunamadi - 0 kabul edildi.")
        return 0.0
    return try_kaydi["free"]


def mutabakat_yap(kasa: "MerkeziKasa", pozisyonlar: dict) -> None:
    """
    v16 BOLUM 4: CANLI MOD BAKIYE MUTABAKATI. Borsa emirlerindeki stepSize
    yuvarlamalari ve komisyon kesintileri zamanla ic kasa ile GERCEK borsa
    bakiyesi arasinda kurus sapmalarina yol acabilir. Bu fonksiyon
    ACCOUNT_ENDPOINT_PATH'ten (v17 FIX: /open/v1/account/spot) GERCEK serbest TRY bakiyesini VE acik
    pozisyonlarin coin miktarlarini okuyup ic degiskenleri SESSIZCE
    (kullaniciya ekstra gurultu yapmadan, sadece log/print ile) senkronize
    eder. SIMULASYON modunda (CANLI_MOD=False) GUVENLE ATLANIR - hicbir
    API cagrisi yapmaz.
    """
    if not CANLI_MOD:
        return
    try:
        bakiyeler = binance_hesap_bakiyeleri()
    except Exception as e:
        # Okunamayan bir yanit ASLA kasayi sifirlamamali: kasa.bakiye=0 olursa
        # portfoy degeri duser ve ACIL FREN tum pozisyonlari tasfiye edebilir.
        print(f"{RED}  MUTABAKAT basarisiz, kasa DEGISTIRILMEDI (bir sonraki denemede "
              f"tekrar denenecek): {e}{RESET}")
        logger.error("Mutabakat basarisiz: %s", e)
        return

    gercek_bakiye = bakiyeler.get("TRY", {}).get("free", 0.0)
    eski_bakiye = kasa.bakiye
    fark = gercek_bakiye - eski_bakiye
    kasa.bakiye = gercek_bakiye
    if abs(fark) > 0.01:
        print(f"{CYAN}  MUTABAKAT: Kasa bakiyesi borsa ile senkronize edildi "
              f"({eski_bakiye:,.2f} -> {gercek_bakiye:,.2f} TRY, fark: {fark:+,.2f}){RESET}")
        logger.warning("Mutabakat: kasa bakiyesi %.2f -> %.2f (fark %.2f)", eski_bakiye, gercek_bakiye, fark)

    acik_once = sum(1 for b in pozisyonlar.values() if b.has_open_position)
    _mutabakat_pozisyonlari(bakiyeler, pozisyonlar)
    kapanan = acik_once - sum(1 for b in pozisyonlar.values() if b.has_open_position)
    # v20: pozisyon kapanmadan TRY bakiyesi belirgin degistiyse bu bot disi para yatirma/cekmedir:
    # kar/zarar sayilmaz, acil fren referansi ve sermaye tabani ayni miktarda kaydirilir.
    if kapanan == 0 and _sermaye_hareketi_mi(fark, v9_toplam_portfoy_degeri(kasa, pozisyonlar)):
        _risk.sermaye_hareketi(fark)
        print(f"{CYAN}  MUTABAKAT: TRY bakiyesi bot disinda {fark:+,.2f} TRY degisti - para "
              f"{'yatirma' if fark > 0 else 'cekme'} olarak kaydedildi (kar/zarar sayilmadi).{RESET}")
        logger.warning("Mutabakat: sermaye hareketi %.2f TRY", fark)


def _mutabakat_pozisyonlari(bakiyeler: dict, pozisyonlar: dict) -> None:
    for bot in pozisyonlar.values():
        if not bot.has_open_position:
            continue
        kayit = bakiyeler.get(bot.coin_name)
        if kayit is None:
            continue
        gercek_miktar = kayit["free"] + kayit["locked"]
        acik_seviye = next((lvl for lvl in bot.grid if lvl.has_position), None)

        if gercek_miktar <= bot.coin_qty * 0.01:
            # Borsada pozisyon fiilen yok (orn. elle satilmis): ic kaydi kapat, yoksa bot var olmayan coini
            # her turda satmaya calisir. v22: islem gunluge yazilir ve kullaniciya haber verilir.
            if acik_seviye:
                bot.borsada_yok_kapat(acik_seviye, bot.guncel_fiyat(), None, None, None, None,
                                      f"mutabakatta {bot.coin_name} miktari {gercek_miktar:.8f} (bot kaydi "
                                      f"{bot.coin_qty:.8f})", kasayi_esitle=False)
            else:
                bot.coin_qty = 0.0
                bot.alis_zamani = None
            continue

        # Sadece ASAGI senkronize et: borsadaki fazlalik kullanicinin bot
        # disi varligi olabilir; bot, kendi almadigi coini asla satmamali.
        esik = max(1e-8, bot.coin_qty * 0.001)  # binde 1'den fazla eksik varsa senkronize et
        if bot.coin_qty - gercek_miktar > esik:
            print(f"{CYAN}  MUTABAKAT: {bot.symbol} miktari senkronize edildi "
                  f"({bot.coin_qty:.8f} -> {gercek_miktar:.8f}){RESET}")
            logger.warning("Mutabakat: %s miktari %.8f -> %.8f", bot.symbol, bot.coin_qty, gercek_miktar)
            bot.coin_qty = gercek_miktar
            if acik_seviye:
                acik_seviye.buy_qty = gercek_miktar


_sembol_filtre_onbellek: dict = {}


def sembol_filtrelerini_getir(symbol: str) -> dict:
    """v10: LOT_SIZE (stepSize) ve MIN_NOTIONAL degerlerini exchangeInfo
    uzerinden ceker ve onbellege alir (her emirde tekrar cekmemek icin)."""
    if symbol in _sembol_filtre_onbellek:
        return _sembol_filtre_onbellek[symbol]

    req = urllib.request.Request(EXCHANGE_INFO_URL, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=20)

    sonuc = {"step_size": None, "min_notional": None, "tick_size": None, "order_types": None}
    for s in data.get("symbols", []):
        if s.get("symbol") == symbol:
            sonuc["order_types"] = s.get("orderTypes")
            for f in s.get("filters", []):
                if f.get("filterType") == "PRICE_FILTER":
                    sonuc["tick_size"] = float(f.get("tickSize", 0)) or None
                if f.get("filterType") == "LOT_SIZE":
                    sonuc["step_size"] = float(f.get("stepSize", 0))
                if f.get("filterType") in ("MIN_NOTIONAL", "NOTIONAL"):
                    sonuc["min_notional"] = float(f.get("minNotional") or f.get("notional") or 0)
            break

    _sembol_filtre_onbellek[symbol] = sonuc
    return sonuc


def miktari_lot_size_yuvarla(qty: float, step_size: Optional[float]) -> float:
    """v10: Miktari LOT_SIZE filtresinin stepSize basamagina ASAGI
    yuvarlar (Decimal ile - kayan nokta hatalarindan kacinmak icin).
    Borsa kurallarina uymayan miktarda emir REDDEDILMESIN diye."""
    if not step_size or step_size <= 0:
        return qty
    adim = Decimal(str(step_size))
    # round(..., 12): 96*0.99 = 95.03999999999999 gibi kayan nokta artiklari bir
    # basamak fazla asagi yuvarlanmasin (gercek deger 95.04).
    miktar = Decimal(str(round(qty, 12)))
    birim_sayisi = (miktar / adim).to_integral_value(rounding=ROUND_DOWN)
    return float(birim_sayisi * adim)


def binance_gercek_emir_gonder(symbol: str, side: str, quantity: float) -> dict:
    """
    ORDER_ENDPOINT_PATH (v17 FIX: /open/v1/orders, POST) uc noktasina
    GERCEK MARKET emri gonderir (HMAC-SHA256 imzali).

    !!! KAYNAK/GUVEN NOTU: Bu yol VE asagidaki side/type SAYISAL KOD
    eslemesi, Binance TR'yi hedefleyen bagimsiz bir topluluk kutuphanesinin
    incelenmesiyle bulundu (bkz. ORDER_ENDPOINT_PATH tanimindaki uzun
    yorum). Hesap/bakiye yolu SIZIN CANLI ortamda dogruladiginiz yolla
    BIREBIR ayni oldugu icin guven duzeyi yuksek, ama RESMI Binance TR
    dokumantasyonu ile teyit edilmedi. side: 'BUY' veya 'SELL' (Binance
    Global stili metin) - ORDER_SIDE_KODU ile SAYISAL KODA ("0"/"1")
    cevrilir; type sabit olarak ORDER_TIPI_MARKET_KODU ("2") gonderilir.
    LOT_SIZE/minNotional kontrolu cagiran taraf
    (CoinBot._canli_emir_dogrula_ve_gonder) tarafindan ONCEDEN yapilmis
    olmalidir. Tek seferlik MARKET emri gonderir ve borsanin yanitini aynen
    dondurur (ham yaniti [BORSA YANITI] ile terminale basar); gerceklesen
    miktar/fiyat emir_dolum_bilgisi() ile okunur.
    """
    params = {
        "symbol": binance_tr_islem_sembolu(symbol),
        "side": ORDER_SIDE_KODU.get(side, side),
        "type": ORDER_TIPI_MARKET_KODU,
        "quantity": f"{quantity:.8f}".rstrip("0").rstrip("."),
    }
    sonuc = binance_signed_request("POST", ORDER_ENDPOINT_PATH, params)
    print(f"{GRAY}[BORSA YANITI]: {sonuc!r}{RESET}")
    # Binance TR reddedilen emirleri de HTTP 200 + {"code": <sifirdan farkli>}
    # ile dondurebilir; bunu basari sayarsak ic muhasebe var olmayan bir
    # pozisyon/satis kaydeder.
    if isinstance(sonuc, dict) and sonuc.get("code") not in (0, None):
        mesaj = sonuc.get("msg") or sonuc.get("message") or "(mesaj yok)"
        raise RuntimeError(f"Binance TR emri reddetti: code={sonuc.get('code')} msg={mesaj}")
    return sonuc


def _sayi_metni(deger: float) -> str:
    """Emir parametresi icin bilimsel gosterimsiz sayi (1e-05 yerine 0.00001)."""
    return f"{deger:.8f}".rstrip("0").rstrip(".") or "0"


def fiyati_tick_yuvarla(fiyat: float, tick_size: Optional[float]) -> float:
    """Fiyati PRICE_FILTER tickSize basamagina ASAGI yuvarlar."""
    if not tick_size or tick_size <= 0:
        return fiyat
    adim = Decimal(str(tick_size))
    return float((Decimal(str(round(fiyat, 12))) / adim).to_integral_value(rounding=ROUND_DOWN) * adim)


def _binance_emir_yaniti(sonuc, islem: str, yazdir: bool = True) -> dict:
    """Emir/iptal/sorgu yanitini dogrular ve 'data' kismini dondurur. code != 0 ise
    (HTTP 200 olsa bile) RuntimeError firlatir."""
    if yazdir:
        print(f"{GRAY}[BORSA YANITI]: {sonuc!r}{RESET}")
    if not isinstance(sonuc, dict):
        raise RuntimeError(f"Binance TR {islem} yaniti beklenmeyen formatta: {sonuc!r}")
    if sonuc.get("code") not in (0, None):
        mesaj = sonuc.get("msg") or sonuc.get("message") or "(mesaj yok)"
        raise RuntimeError(f"Binance TR {islem} reddetti: code={sonuc.get('code')} msg={mesaj}")
    data = sonuc.get("data", sonuc)
    if isinstance(data, dict) and isinstance(data.get("list"), list):
        data = data["list"][0] if data["list"] else {}
    return data if isinstance(data, dict) else {}


def _emir_bilgisi(data: dict) -> dict:
    """Emir kaydindan durum, gerceklesen miktar ve ortalama fiyati cikarir."""
    def sayi(anahtar: str) -> float:
        try:
            return float(data.get(anahtar) or 0)
        except (TypeError, ValueError):
            return 0.0
    try:
        durum = int(data.get("status"))
    except (TypeError, ValueError):
        durum = None
    miktar, tutar = sayi("executedQty"), sayi("executedQuoteQty")
    fiyat = tutar / miktar if (miktar and tutar) else (sayi("avgPrice") or sayi("executedPrice"))
    return {"status": durum, "executedQty": miktar, "executedPrice": fiyat, "tip": data.get("type")}


def emir_dolum_bilgisi(sonuc) -> tuple:
    """v22: market emri yanitindan - yoksa emri bir kez sorgulayarak - gerceklesen (miktar, ortalama
    fiyat). Okunamazsa (None, None): cagiran taraf tahmini degerlerle devam eder."""
    data = sonuc.get("data") if isinstance(sonuc, dict) else None
    if isinstance(data, dict) and isinstance(data.get("list"), list):
        data = data["list"][0] if data["list"] else None
    emir_id = None
    if isinstance(data, dict):
        bilgi = _emir_bilgisi(data)
        if bilgi["executedQty"] > 0 and bilgi["executedPrice"] > 0:
            return bilgi["executedQty"], bilgi["executedPrice"]
        emir_id = data.get("orderId")
    if emir_id in (None, "", 0):
        return None, None
    time.sleep(1.0)
    try:
        bilgi = binance_emir_sorgula(str(emir_id))
    except Exception as e:
        logger.warning("Emir %s sorgulanamadi, tahmini fiyat kullanildi: %s", emir_id, e)
        return None, None
    if bilgi["executedQty"] > 0 and bilgi["executedPrice"] > 0:
        return bilgi["executedQty"], bilgi["executedPrice"]
    return None, None



def binance_stop_limit_satis_emri(symbol: str, quantity: float, stop_fiyati: float,
                                  limit_fiyati: float) -> str:
    """Borsada bekleyen STOP_LOSS_LIMIT SATIS emri kurar, emir numarasini dondurur.
    Fiyat stop_fiyati'na inince borsa, limit_fiyati'ndan (veya daha iyisinden) satar."""
    params = {
        "symbol": binance_tr_islem_sembolu(symbol),
        "side": ORDER_SIDE_KODU["SELL"],
        "type": ORDER_TIPI_STOP_LOSS_LIMIT_KODU,
        "quantity": _sayi_metni(quantity),
        "price": _sayi_metni(limit_fiyati),
        "stopPrice": _sayi_metni(stop_fiyati),
    }
    try:
        data = _binance_emir_yaniti(binance_signed_request("POST", ORDER_ENDPOINT_PATH, params), "stop emrini")
    except RuntimeError as e:
        if "timeinforce" not in str(e).lower():
            raise
        params["timeInForce"] = "1"  # GTC - borsa bu alani zorunlu tutuyorsa bir kez daha dene
        data = _binance_emir_yaniti(binance_signed_request("POST", ORDER_ENDPOINT_PATH, params), "stop emrini")
    emir_id = data.get("orderId")
    if emir_id in (None, "", 0):
        raise RuntimeError(f"Binance TR stop emri yanitinda emir numarasi (orderId) yok: {data!r}")
    return str(emir_id)


def _borsa_stop_kullanilabilir() -> bool:
    """Borsa stop emri kurulabilir/yukseltilebilir mi (v21.1: dogrulama hatasinda kalici kapanir)."""
    return CANLI_MOD and BORSA_STOP_AKTIF and not _trend_durumu.get("borsa_stop_kapali")


def binance_emir_iptal(emir_id: str) -> dict:
    """Bekleyen bir emri iptal eder; emir bilgisini (_emir_bilgisi) dondurur."""
    sonuc = binance_signed_request("POST", ORDER_CANCEL_ENDPOINT_PATH, {"orderId": emir_id})
    if isinstance(sonuc, dict) and sonuc.get("code") == 3219:  # "Already cancelled"
        print(f"{GRAY}[BORSA YANITI]: {sonuc!r}{RESET}")
        return {"status": 3, "executedQty": 0.0, "executedPrice": 0.0}
    return _emir_bilgisi(_binance_emir_yaniti(sonuc, "emir iptalini"))


def binance_emir_sorgula(emir_id: str) -> dict:
    """Emrin guncel durumunu sorgular (once /orders/detail, olmazsa /orders?orderId=)."""
    try:
        data = _binance_emir_yaniti(binance_signed_request("GET", ORDER_DETAIL_ENDPOINT_PATH,
                                                           {"orderId": emir_id}), "emir sorgusunu", yazdir=False)
    except Exception as ilk_hata:
        try:
            data = _binance_emir_yaniti(binance_signed_request("GET", ORDER_ENDPOINT_PATH,
                                                               {"orderId": emir_id}), "emir sorgusunu", yazdir=False)
        except Exception:
            raise ilk_hata
    return _emir_bilgisi(data)


def canli_mod_on_kontrol() -> bool:
    """v17 FIX: CANLI_MOD=True ile baslatilmadan once gerekli TUM guvenlik
    kontrollerini yapar. Herhangi biri eksikse bot CANLI baslamaz."""
    if not CANLI_MOD:
        return True

    hata_var = False

    # v17 FIX: API anahtarlarinin gercekten str oldugunu ACIKCA dogrula -
    # eger bir kod degisikligi _ortam_degiskeni_str_oku()'yu atlayip
    # BINANCE_TR_API_KEY/SECRET_KEY'i tekrar dogrudan os.getenv(...), ile
    # (sondaki virgulle) tanimlarsa, bu deger tuple olur ve daha sonra
    # HMAC imzalama sirasinda anlasilmasi zor bir "tuple object has no
    # attribute 'encode'" hatasi verir. Burada erken ve ACIK bir hata ile
    # yakalanir.
    if not isinstance(BINANCE_TR_API_KEY, str) or not isinstance(BINANCE_TR_SECRET_KEY, str):
        print(f"{RED}  HATA: BINANCE_TR_API_KEY/BINANCE_TR_SECRET_KEY str degil "
              f"({type(BINANCE_TR_API_KEY).__name__}/{type(BINANCE_TR_SECRET_KEY).__name__}). "
              f"Ortam degiskeni tanimini kontrol edin (fazladan virgul olabilir).{RESET}")
        hata_var = True
    elif not BINANCE_TR_API_KEY or not BINANCE_TR_SECRET_KEY:
        print(f"{RED}  HATA: CANLI_MOD=True ama BINANCE_TR_API_KEY / BINANCE_TR_SECRET_KEY "
              f"ortam degiskenleri tanimli degil.{RESET}")
        hata_var = True
    else:
        api_anahtari_teshis_raporu()

    if _ortam_degiskeni_str_oku("AURELIUS_LIVE_CONFIRM") != "EVET_GERCEK_PARA_KULLAN":
        print(f"{RED}  HATA: CANLI_MOD=True icin ek bir guvenlik onayi gerekiyor.{RESET}")
        print(f"{RED}  Ortam degiskeni olarak AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN "
              f"tanimlamadan bot GERCEK PARA ile baslamaz. Bu, kod icindeki tek bir "
              f"bayragin yanlislikla True birakilmasina karsi BILINCLI EK bir korumadir.{RESET}")
        hata_var = True

    # v17 FIX: ORDER_ENDPOINT_PATH ("/open/v1/orders") ve side/type sayisal
    # kod eslemesi bagimsiz bir topluluk kaynagindan geldi (bkz. dosyanin
    # ustundeki ORDER_ENDPOINT_PATH tanimindaki KAYNAK NOTU) - hesap/bakiye
    # yoluyla ayni aile oldugu icin guven duzeyi YUKSEK, ama RESMI Binance TR
    # dokumantasyonuyla TEYIT EDILMEDI. Bu SADECE bir uyaridir, botu DURDURMAZ.
    print(f"{YELLOW}  UYARI: ORDER_ENDPOINT_PATH ({ORDER_ENDPOINT_PATH}) ve side/type "
          f"sayisal kod eslemesi RESMI olarak dogrulanmadi (bagimsiz kaynaktan alindi - "
          f"bkz. kod ici yorum). ILK GERCEK EMRI MUTLAKA en kucuk tutarla gonderip "
          f"[BORSA YANITI] satirini borsa arayuzunuzdeki islem gecmisiyle karsilastirin.{RESET}")
    logger.warning("ORDER_ENDPOINT_PATH (%s) ve side/type kod eslemesi resmi olarak "
                   "dogrulanmadi - ilk CANLI emirden once kucuk tutarla teyit edin.",
                   ORDER_ENDPOINT_PATH)

    return not hata_var


# ==========================================================================
# v10 BOLUM 3: TAHTA DERINLIGI & SPREAD FILTRESI
# ==========================================================================

def orderbook_spread_kontrol(symbol: str):
    """
    v10: En iyi alis (bid) ve en iyi satis (ask) fiyatlarini ceker,
    aralarindaki spread yuzdesini hesaplar.
    Donus: (spread_pct, en_iyi_bid, en_iyi_ask) - hata durumunda
    (None, None, None) doner (bu durumda cagiran taraf, veri
    alinamadigi icin islemi TEMKINLI sekilde engellemez, sadece
    kontrolu atlar - ag sorunlarinin islem firsatini gereksiz yere
    kacirmasini onlemek icindir; asil koruma basarili bir sorguda
    genis spread tespit edildiginde devreye girer).
    """
    try:
        url = DEPTH_URL_TEMPLATE.format(symbol=symbol, limit=ORDERBOOK_DEPTH_LIMIT)
        req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
        data = http_istek_yap(req, timeout=10, max_deneme=2)
        en_iyi_bid = float(data["bids"][0][0])
        en_iyi_ask = float(data["asks"][0][0])
        orta_fiyat = (en_iyi_bid + en_iyi_ask) / 2
        spread_pct = ((en_iyi_ask - en_iyi_bid) / orta_fiyat) * 100 if orta_fiyat > 0 else None
        return spread_pct, en_iyi_bid, en_iyi_ask
    except Exception:
        return None, None, None


@dataclass
class GridLevel:
    """Acik pozisyonun kaydi (adi v10 grid yapisindan kalma; durum dosyasi uyumu icin korunuyor)."""
    price: float
    has_position: bool = False
    buy_qty: float = 0.0
    buy_price: float = 0.0
    en_yuksek_fiyat: float = 0.0
    borsa_stop_emir_id: Optional[str] = None  # borsada bekleyen koruyucu stop emri
    borsa_stop_fiyati: float = 0.0
    borsa_stop_miktari: float = 0.0
    borsa_stop_son_islem: float = 0.0   # kaydedilmez: son kurma/iptal zamani (monotonic)
    borsa_stop_son_sorgu: float = 0.0   # kaydedilmez: son durum sorgusu (monotonic)
    borsa_stop_hata_sayisi: int = 0     # kaydedilmez
    risk_birimi: float = 0.0            # 1R (giris - ilk stop), fiyat cinsinden - islem gunlugundeki R sonucu
    ilk_stop: float = 0.0
    trend_stop: float = 0.0             # guncel stop: gunluk kontrolde zirve - 3 x ATR'ye yukselir, asla inmez


class MerkeziKasa:
    """Tum acik pozisyonlarin paylastigi tek nakit havuzu. CANLI_MOD'da borsadaki gercek serbest
    TRY bakiyesiyle esitlenir."""

    def __init__(self, baslangic: float):
        self.baslangic = baslangic
        self.bakiye = baslangic
        self.toplam_komisyon = 0.0

    def harca(self, tutar: float, komisyon: float) -> None:
        self.bakiye -= (tutar + komisyon)
        self.toplam_komisyon += komisyon

    def yatir(self, tutar: float, komisyon: float) -> None:
        self.bakiye += tutar
        self.toplam_komisyon += komisyon


class CoinBorsadaYok(Exception):
    """v22: satilmak istenen coin borsada yok (orn. elle satilmis)."""


@dataclass
class CoinBot:
    symbol: str
    coin_name: str
    starting_try: float = 0.0           # acik pozisyonun alim tutari
    cash_try: float = 0.0
    coin_qty: float = 0.0
    trade_count: int = 0
    realized_pnl: float = 0.0
    toplam_komisyon: float = 0.0
    history: list = field(default_factory=list)
    grid: list = field(default_factory=list)   # en fazla bir acik GridLevel
    last_real_price: float = 0.0
    bildirim_aktif: bool = True
    alis_zamani: Optional[datetime] = None
    giris_bilgi: dict = field(default_factory=dict)  # giris zamani/miktari/tutari - islem gunlugu icin
    acik_islem_pnl: float = 0.0
    emir_hata_bildirimi: dict = field(default_factory=dict)  # v22: (yon) -> son Telegram zamani (kaydedilmez)
    son_teyitsiz_stop: float = 0.0                           # v22: ayni uyari tekrar basilmasin (kaydedilmez)

    def __post_init__(self):
        self.cash_try = self.starting_try

    @property
    def has_open_position(self) -> bool:
        return self.coin_qty > 1e-12

    def guncel_fiyat(self) -> float:
        """Bilinen son fiyat; hic fiyat alinamamissa (yeniden baslatma sonrasi ilk tur veya fiyat
        sorgusu hatasi) acik pozisyonun giris fiyati. 0 dondurmek pozisyonu sifir degerde gosterir ve
        sahte bir ACIL FREN tasfiyesini tetikleyebilir."""
        if self.last_real_price:
            return self.last_real_price
        acik_seviye = next((lvl for lvl in self.grid if lvl.has_position), None)
        return acik_seviye.buy_price if acik_seviye else 0.0

    def record(self, side, price, qty, amount):
        self.trade_count += 1
        self.history.append((ts(), side, price, qty, amount))

    @staticmethod
    def _slipajli_fiyat(price: float, side: str) -> float:
        """Emir oncesi tahmini gerceklesme fiyati (simulasyon ve gercek fiyat okunamadiginda)."""
        slip = random.uniform(SLIPAJ_MIN_PCT, SLIPAJ_MAKS_PCT)
        return price * (1 + slip) if side == "ALIM" else price * (1 - slip)

    def _emir_hatasi_bildir(self, side: str, metin: str) -> None:
        """v22: ayni coinin ayni yondeki emir hatasi Telegram'a en fazla EMIR_HATA_BILDIRIM_DK'da bir gider
        (borsa bir emri surekli reddederse her turda mesaj yagmasin)."""
        simdi = time.monotonic()
        if simdi - self.emir_hata_bildirimi.get(side, -1e9) >= EMIR_HATA_BILDIRIM_DK * 60:
            self.emir_hata_bildirimi[side] = simdi
            send_telegram(f"\u26a0\ufe0f <b>CANLI EMIR BASARISIZ</b>\n{self.symbol} {side} - {html.escape(metin)}"
                          f"\n(bot denemeye devam ediyor; bu uyari en fazla {EMIR_HATA_BILDIRIM_DK} dk'da bir gelir)")

    def _canli_emir_dogrula_ve_gonder(self, side: str, qty: float, exec_price: float) -> Optional[tuple]:
        """CANLI_MOD'da cagrilir: LOT_SIZE yuvarlamasi ve minNotional kontrolu, ardindan GERCEK market emri.
        Basariliysa (gerceklesen miktar, gerceklesen ortalama fiyat) - v22: borsadan okunur, okunamazsa
        yuvarlanmis miktar ve tahmini fiyat. Basarisiz/uygunsuzsa None: CAGIRAN TARAF IC DURUMU
        GUNCELLEMEMELI (gercek emir gitmemistir). SATIS'ta coin borsada yoksa CoinBorsadaYok firlatir."""
        try:
            filtreler = sembol_filtrelerini_getir(self.symbol)
        except Exception as e:
            print(f"{RED}  CANLI EMIR IPTAL: sembol filtreleri alinamadi ({self.symbol}): {e}{RESET}")
            return None

        if side == "SELL":
            # Borsa ALIM komisyonunu alinan coinden keser; ic kayittaki tam miktarla satis "yetersiz
            # bakiye" ile reddedilir. Satisi gercek serbest bakiyeyle sinirla.
            try:
                kayit = binance_hesap_bakiyeleri().get(self.coin_name)
            except Exception as e:
                kayit = None
                print(f"{YELLOW}  CANLI SATIS: {self.coin_name} bakiyesi okunamadi ({e}) - ic kayittaki "
                      f"miktarla deneniyor.{RESET}")
            if kayit is not None:
                if kayit["free"] + kayit["locked"] <= qty * 0.01:
                    raise CoinBorsadaYok(f"{self.coin_name} borsada yok (serbest {kayit['free']:.8f}, "
                                         f"kilitli {kayit['locked']:.8f})")
                if kayit["free"] < qty:
                    print(f"{YELLOW}  CANLI SATIS: {self.symbol} miktari borsadaki serbest bakiyeye cekildi "
                          f"({qty:.8f} -> {kayit['free']:.8f}).{RESET}")
                    qty = kayit["free"]

        yuvarlanmis_qty = miktari_lot_size_yuvarla(qty, filtreler.get("step_size"))
        if yuvarlanmis_qty <= 0:
            print(f"{RED}  CANLI EMIR IPTAL: LOT_SIZE yuvarlamasi sonrasi miktar 0 ({self.symbol}).{RESET}")
            return None
        min_notional = filtreler.get("min_notional")
        tahmini_notional = yuvarlanmis_qty * exec_price
        if min_notional and tahmini_notional < min_notional:
            print(f"{RED}  CANLI EMIR IPTAL: Tutar minNotional altinda "
                  f"({tahmini_notional:.2f} < {min_notional}) - {self.symbol}.{RESET}")
            self._emir_hatasi_bildir(side, f"tutar borsanin alt sinirinin altinda ({tahmini_notional:.2f} < "
                                           f"{min_notional} TRY)")
            return None

        try:
            emir_sonucu = binance_gercek_emir_gonder(self.symbol, side, yuvarlanmis_qty)
        except Exception as e:
            print(f"{RED}  CANLI EMIR BASARISIZ ({side} {self.symbol}): {e}{RESET}")
            self._emir_hatasi_bildir(side, str(e))
            return None
        print(f"{GREEN}  CANLI EMIR GONDERILDI ({side} {self.symbol}): {emir_sonucu}{RESET}")
        self.emir_hata_bildirimi.pop(side, None)
        miktar, fiyat = emir_dolum_bilgisi(emir_sonucu)
        # Borsanin bildirdigi deger mantiksizsa (birim/alan farki) tahmine don
        if not miktar or not (0 < miktar <= yuvarlanmis_qty * 1.001):
            miktar = yuvarlanmis_qty
        if not fiyat or abs(fiyat / exec_price - 1) > 0.2:
            fiyat = exec_price
        else:
            print(f"{GRAY}  Gerceklesen: {_sayi_metni(miktar)} {self.coin_name} x {format_fiyat(fiyat)} TRY{RESET}")
        return miktar, fiyat

    def _ratchet_stop_hesapla(self, level: "GridLevel") -> tuple:
        """Guncel stop (salt okunur): (stop_seviyesi, etiket). Stop giris fiyatinin ustune ciktiysa
        TRAILING-STOP, degilse STOP-LOSS."""
        stop = level.trend_stop if level.trend_stop > 0 else level.buy_price * (1 - ESKI_SURUM_STOP_PCT)
        return stop, ("TRAILING-STOP" if stop > level.buy_price else "STOP-LOSS")

    def acik_hedef_ve_stop(self) -> tuple:
        """Acik pozisyon icin (hedef, stop, etiket) - raporlarda gosterim icin. Trend stratejisinde sabit
        hedef yoktur ("TREND"). Acik pozisyon yoksa (None, None, None)."""
        for level in self.grid:
            if level.has_position:
                stop, etiket = self._ratchet_stop_hesapla(level)
                return "TREND", stop, etiket
        return None, None, None

    # ------------------------------------------------------------
    # v18: BORSADA BEKLEYEN KORUYUCU STOP EMRI (AURELIUS_BORSA_STOP=1)
    # ------------------------------------------------------------
    def _borsa_koruma_fiyatlari(self, level: "GridLevel") -> tuple:
        """(tetik, limit): tetik botun guncel ratchet stop'unun BORSA_STOP_TAMPON_PCT
        altinda - bot calisirken once kendi stop'u devreye girer."""
        stop, _ = self._ratchet_stop_hesapla(level)
        tetik = stop * (1 - BORSA_STOP_TAMPON_PCT)
        return tetik, tetik * (1 - BORSA_STOP_LIMIT_ARALIK_PCT)

    def _borsa_stop_dogrula(self, emir_id: str) -> Optional[str]:
        """v21.1: emir turu kodu resmi dokumanla dogrulanmadi. Yeni kurulan emir hemen gerceklestiyse
        ya da borsa baska bir emir turu bildiriyorsa sorunu dondurur (yanlis tur pozisyonu erken satar)."""
        time.sleep(1.0)
        try:
            bilgi = binance_emir_sorgula(emir_id)
        except Exception as e:
            logger.warning("Borsa stop dogrulama sorgusu yapilamadi (%s): %s", self.symbol, e)
            return None  # periyodik sorgu devam eder
        tip = str(bilgi.get("tip") if bilgi.get("tip") is not None else "").strip().upper()
        if bilgi.get("status") in (1, 2) or bilgi.get("executedQty"):
            return "kurulan emir fiyat stop'a inmeden hemen gerceklesti"
        if tip and tip not in ("4", "STOP_LOSS_LIMIT"):
            return f"borsa emir turunu '{tip}' olarak bildirdi (beklenen STOP_LOSS_LIMIT)"
        return None

    def borsa_stopunu_kur(self, level: "GridLevel", zorla: bool = False,
                          durum_kaydet: Optional[object] = None) -> bool:
        """Seviye icin borsada STOP_LOSS_LIMIT satis emri kurar. Basarisizlikta bot
        kendi stop'uyla korumaya devam eder; BORSA_STOP_HATA_BEKLEME_SANIYE sonra
        tekrar denenir."""
        if not _borsa_stop_kullanilabilir() or not level.has_position or level.borsa_stop_emir_id:
            return False
        simdi = time.monotonic()
        if (not zorla and level.borsa_stop_hata_sayisi
                and simdi - level.borsa_stop_son_islem < BORSA_STOP_HATA_BEKLEME_SANIYE):
            return False
        level.borsa_stop_son_islem = simdi
        ilk_kurulum = level.borsa_stop_fiyati <= 0
        coin_yok = False
        try:
            filtreler = sembol_filtrelerini_getir(self.symbol)
            tipler = filtreler.get("order_types")
            if tipler and "STOP_LOSS_LIMIT" not in tipler:
                raise RuntimeError(f"bu sembolde STOP_LOSS_LIMIT emri desteklenmiyor ({', '.join(tipler)})")
            kayit = binance_hesap_bakiyeleri().get(self.coin_name, {})
            serbest, kilitli = kayit.get("free", 0.0), kayit.get("locked", 0.0)
            if serbest + kilitli <= level.buy_qty * 0.01:
                coin_yok = True
                raise RuntimeError("coin borsada yok (elle satilmis olabilir) - mutabakatta kapatilacak")
            miktar = miktari_lot_size_yuvarla(min(level.buy_qty, serbest), filtreler.get("step_size"))
            tetik, limit = self._borsa_koruma_fiyatlari(level)
            tetik = fiyati_tick_yuvarla(tetik, filtreler.get("tick_size"))
            limit = fiyati_tick_yuvarla(limit, filtreler.get("tick_size"))
            guncel = self.guncel_fiyat()
            if guncel and tetik >= guncel * 0.998:
                raise RuntimeError(f"tetik ({format_fiyat(tetik)}) guncel fiyata ({format_fiyat(guncel)}) "
                                   f"cok yakin - botun kendi stop'u devrede")
            if miktar <= 0 or limit <= 0:
                raise RuntimeError(f"miktar/fiyat gecersiz (miktar={miktar}, serbest={serbest}, kilitli={kilitli})")
            min_notional = filtreler.get("min_notional")
            if min_notional and miktar * limit < min_notional:
                raise RuntimeError(f"emir tutari minNotional altinda ({miktar * limit:.2f} < {min_notional})")
            emir_id = binance_stop_limit_satis_emri(self.symbol, miktar, tetik, limit)
        except Exception as e:
            level.borsa_stop_hata_sayisi += 1
            print(f"{YELLOW}  BORSA STOP kurulamadi ({self.symbol}): {e} - bot calistigi surece "
                  f"kendi stop'u gecerli.{RESET}")
            logger.warning("Borsa stop kurulamadi (%s): %s", self.symbol, e)
            if level.borsa_stop_hata_sayisi == 3 and not coin_yok:
                send_telegram(f"\u26a0\ufe0f <b>{self.symbol} borsa stop emri kurulamiyor</b>\n"
                              f"{html.escape(str(e))}\nBot calistigi surece kendi stop'u gecerli; "
                              f"bot kapanirsa bu pozisyon korumasiz kalir.")
            return False
        level.borsa_stop_emir_id = emir_id
        level.borsa_stop_fiyati = tetik
        level.borsa_stop_miktari = miktar
        level.borsa_stop_hata_sayisi = 0
        level.borsa_stop_son_sorgu = simdi
        sorun = self._borsa_stop_dogrula(emir_id)
        if sorun:
            _trend_durumu["borsa_stop_kapali"] = sorun  # durum dosyasina kaydedilir: yeniden baslatmada da kapali
            print(f"{RED}{BOLD}  BORSA STOP KAPATILDI ({self.symbol}): {sorun}. Bot kendi stop'uyla korumaya "
                  f"devam ediyor.{RESET}")
            logger.error("Borsa stop kapatildi (%s): %s", self.symbol, sorun)
            if "gerceklesti" in sorun:
                level.borsa_stop_son_sorgu = 0.0  # satis borsada oldu: bir sonraki bakimda muhasebeye islenir
            else:
                durum, _ = self.borsa_stopunu_iptal_et(level)
                if durum == "DOLDU":
                    level.borsa_stop_emir_id = emir_id
                    level.borsa_stop_son_sorgu = 0.0
            send_telegram(f"\u26a0\ufe0f <b>Borsa stop emri kapatildi</b> ({self.symbol})\n{html.escape(sorun)}.\n"
                          f"Pozisyonlar botun kendi stop'uyla korunmaya devam ediyor; bot kapaliyken koruma yok. "
                          f"Binance TR'de acik emirlerinizi kontrol edin ve bu mesaji Claude'a iletin.")
            if durum_kaydet is not None:
                durum_kaydet()
            return False
        print(f"{GREEN}  BORSA STOP kuruldu ({self.symbol}): {_sayi_metni(miktar)} adet, tetik "
              f"{format_fiyat(tetik)} / limit {format_fiyat(limit)} TRY (emir {emir_id}){RESET}")
        if ilk_kurulum:
            send_telegram(f"\U0001F6E1 <b>{self.symbol} borsa stop emri kuruldu</b>\n"
                          f"Tetik: {format_fiyat(tetik)} TRY - bot kapali olsa bile borsa bu fiyatta satar.\n"
                          f"Binance TR'de Emirler > Acik emirler bolumunde gorebilirsiniz.")
        if durum_kaydet is not None:
            durum_kaydet()  # emir numarasi kaybolmasin (yetim emir coinleri kilitli tutar)
        return True

    def borsa_stopunu_iptal_et(self, level: "GridLevel") -> tuple:
        """Seviyenin borsa stop emrini iptal eder. Donus (durum, bilgi):
        'YOK' emir yok, 'IPTAL' iptal edildi/zaten aktif degil, 'DOLDU' emir zaten
        gerceklesmis (cagiran taraf satisi kaydetmeli), 'HATA' iptal edilemedi."""
        emir_id = level.borsa_stop_emir_id
        if not emir_id:
            return "YOK", None
        level.borsa_stop_son_islem = time.monotonic()
        try:
            bilgi = binance_emir_iptal(emir_id)
        except Exception as e:
            try:
                bilgi = binance_emir_sorgula(emir_id)
            except Exception as e2:
                print(f"{RED}  BORSA STOP iptal edilemedi ve durumu okunamadi ({self.symbol}, emir "
                      f"{emir_id}): {e} / {e2}{RESET}")
                return "HATA", None
            if bilgi["status"] == 2:
                level.borsa_stop_emir_id = None
                return "DOLDU", bilgi
            if bilgi["status"] in (3, 5, 6):
                level.borsa_stop_emir_id = None
                return "IPTAL", bilgi
            print(f"{RED}  BORSA STOP iptal edilemedi ({self.symbol}, emir {emir_id}, durum "
                  f"{EMIR_DURUMLARI.get(bilgi['status'], bilgi['status'])}): {e}{RESET}")
            return "HATA", bilgi
        level.borsa_stop_emir_id = None
        if bilgi.get("status") == 2:
            return "DOLDU", bilgi
        if bilgi.get("executedQty"):
            print(f"{YELLOW}  BORSA STOP iptalinden once {_sayi_metni(bilgi['executedQty'])} adet "
                  f"gerceklesmisti ({self.symbol}) - miktar mutabakatta duzelir.{RESET}")
        print(f"{GRAY}  BORSA STOP iptal edildi ({self.symbol}, emir {emir_id}).{RESET}")
        return "IPTAL", bilgi

    def _borsa_stop_dolumunu_isle(self, level: "GridLevel", bilgi: Optional[dict],
                                  kasa: Optional[MerkeziKasa], acik_pozisyon_sayaci: Optional[list],
                                  rapor: Optional["RaporlamaDurumu"], durum_kaydet: Optional[object]) -> bool:
        """Borsada gerceklesmis stop emrini (ek emir gondermeden) ic muhasebeye isler."""
        bilgi = bilgi or {}
        miktar = bilgi.get("executedQty") or level.borsa_stop_miktari or level.buy_qty
        fiyat = bilgi.get("executedPrice") or level.borsa_stop_fiyati or self.guncel_fiyat()
        print(f"{YELLOW}{BOLD}  BORSA STOP GERCEKLESTI ({self.symbol}): {_sayi_metni(miktar)} adet "
              f"~{format_fiyat(fiyat)} TRY{RESET}")
        send_telegram(f"\U0001F6E1 <b>{self.symbol} borsa stop emri gerceklesti</b>\n"
                      f"{_sayi_metni(miktar)} adet ~{format_fiyat(fiyat)} TRY'den satildi.")
        return self._satisi_uygula(level, fiyat, "BORSA-STOP", False, kasa, acik_pozisyon_sayaci,
                                   rapor, durum_kaydet, borsada_gerceklesen=(miktar, fiyat))

    def borsa_stop_bakimi(self, kasa: Optional[MerkeziKasa], acik_pozisyon_sayaci: Optional[list] = None,
                          rapor: Optional["RaporlamaDurumu"] = None, durum_kaydet: Optional[object] = None,
                          zorla_sorgu: bool = False, yeni_kur: bool = True) -> None:
        """Her tick'te cagrilir: eksik emri kurar, emrin durumunu periyodik sorgular
        (doldu -> kaydet, iptal/red -> yeniden kur) ve bot stop'u yukseldikce
        borsadaki emri yukari tasir (asla asagi indirmez)."""
        if not CANLI_MOD or kasa is None:
            return
        for level in self.grid:
            if not level.has_position:
                continue
            simdi = time.monotonic()
            if not level.borsa_stop_emir_id:
                yeni_alim = (self.alis_zamani is not None
                             and (datetime.now() - self.alis_zamani).total_seconds() < 20)
                if _borsa_stop_kullanilabilir() and yeni_kur and not yeni_alim:  # alinan coin hesaba gecsin
                    self.borsa_stopunu_kur(level, durum_kaydet=durum_kaydet)
                continue
            if zorla_sorgu or simdi - level.borsa_stop_son_sorgu >= BORSA_STOP_SORGU_SANIYE:
                level.borsa_stop_son_sorgu = simdi
                try:
                    bilgi = binance_emir_sorgula(level.borsa_stop_emir_id)
                except Exception as e:
                    print(f"{YELLOW}  BORSA STOP durumu okunamadi ({self.symbol}): {e}{RESET}")
                    continue
                if bilgi["status"] == 2:
                    level.borsa_stop_emir_id = None
                    self._borsa_stop_dolumunu_isle(level, bilgi, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)
                    continue
                if bilgi["status"] in (3, 5, 6):
                    print(f"{YELLOW}  BORSA STOP emri artik aktif degil ({self.symbol}, durum "
                          f"{EMIR_DURUMLARI.get(bilgi['status'])}) - yeniden kurulacak.{RESET}")
                    level.borsa_stop_emir_id = None
                    continue
            if not _borsa_stop_kullanilabilir():
                continue
            tetik, _ = self._borsa_koruma_fiyatlari(level)
            if (tetik > level.borsa_stop_fiyati * (1 + BORSA_STOP_GUNCELLEME_ESIGI_PCT)
                    and simdi - level.borsa_stop_son_islem >= BORSA_STOP_GUNCELLEME_MIN_SANIYE):
                durum, bilgi = self.borsa_stopunu_iptal_et(level)
                if durum == "DOLDU":
                    self._borsa_stop_dolumunu_isle(level, bilgi, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)
                elif durum == "IPTAL":
                    time.sleep(1.0)  # kilitli coinler serbest bakiyeye gecsin
                    self.borsa_stopunu_kur(level, zorla=True, durum_kaydet=durum_kaydet)

    def _satisi_uygula(self, level: "GridLevel", price: float, tag: str, sim: bool,
                       kasa: Optional[MerkeziKasa], acik_pozisyon_sayaci: Optional[list],
                       rapor: Optional["RaporlamaDurumu"], durum_kaydet: Optional[object],
                       borsada_gerceklesen: Optional[tuple] = None) -> bool:
        """TUM kapanis yollari (stop, borsa stop, acil tasfiye, elle kapanis) icin ortak satis/muhasebe/
        log/Telegram/kayit rutini; pozisyonun tamami kapanir. CANLI_MOD'da gercek emir basarisizsa False
        doner ve HICBIR ic durum degismez (sonraki turda tekrar denenir).
        borsada_gerceklesen=(miktar, fiyat): satis borsada ZATEN olmus (koruyucu stop emri doldu) - emir
        gonderilmez, sadece muhasebe yapilir. Borsada bekleyen stop emri varsa satistan ONCE iptal edilir
        (coinler o emirde kilitliyken satis emri reddedilir)."""
        sell_qty = level.buy_qty
        if sell_qty <= 0:
            return False

        if borsada_gerceklesen is not None:
            sell_qty = borsada_gerceklesen[0] or sell_qty
            exec_price = borsada_gerceklesen[1] or price
        else:
            exec_price = self._slipajli_fiyat(price, "SATIM")
            if CANLI_MOD and kasa is not None:
                if level.borsa_stop_emir_id:
                    durum, bilgi = self.borsa_stopunu_iptal_et(level)
                    if durum == "DOLDU":
                        return self._borsa_stop_dolumunu_isle(level, bilgi, kasa, acik_pozisyon_sayaci,
                                                              rapor, durum_kaydet)
                    if durum == "HATA":
                        print(f"{RED}  SATIS ERTELENDI ({self.symbol} {tag}): borsadaki stop emri iptal "
                              f"edilemedi, sonraki turda tekrar denenecek.{RESET}")
                        return False
                    time.sleep(1.0)  # kilitli coinler serbest bakiyeye gecsin
                try:
                    dolum = self._canli_emir_dogrula_ve_gonder("SELL", sell_qty, exec_price)
                except CoinBorsadaYok as e:
                    return self.borsada_yok_kapat(level, price, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet,
                                                  str(e))
                if dolum is None:
                    return False  # gercek emir gitmedi - ic durum degismez, sonraki turda tekrar denenir
                sell_qty, exec_price = dolum

        # CANLI modda satilan miktar LOT_SIZE yuvarlamasi / komisyon kesintisi yuzunden ic kayittan biraz
        # az olabilir; kalan satilamaz "toz"un maliyeti zarar olarak yazilir ve pozisyon kapatilir.
        brut_proceeds = sell_qty * exec_price
        komisyon = brut_proceeds * KOMISYON_PCT
        net_proceeds = brut_proceeds - komisyon
        cost = level.buy_qty * level.buy_price
        islem_net_pnl = net_proceeds - cost
        islem_net_pnl_pct = (islem_net_pnl / cost * 100) if cost else 0.0

        self.cash_try += net_proceeds
        self.toplam_komisyon += komisyon
        self.realized_pnl += islem_net_pnl
        self._pozisyonu_kapat(level)
        if kasa is not None:
            kasa.yatir(net_proceeds, komisyon)
            if acik_pozisyon_sayaci is not None and acik_pozisyon_sayaci[0] > 0:
                acik_pozisyon_sayaci[0] -= 1
        if rapor is not None:
            rapor.islem_kaydet(self.symbol, "SATIM", komisyon, islem_net_pnl)
        self.record("SATIM", exec_price, sell_qty, net_proceeds)
        print_trade_line(self.symbol, "SATIM", exec_price, sell_qty, net_proceeds, self.cash_try,
                         self.coin_name, sim, tag=tag, komisyon=komisyon,
                         telegram_bildir=self.bildirim_aktif,
                         net_pnl=islem_net_pnl, net_pnl_pct=islem_net_pnl_pct,
                         guncel_kasa=(kasa.bakiye if kasa is not None else None))
        self.acik_islem_pnl += islem_net_pnl
        self._islem_kapanisini_isle(level, exec_price, tag)
        if durum_kaydet is not None:
            durum_kaydet()
        return True

    def _pozisyonu_kapat(self, level: "GridLevel") -> None:
        level.has_position = False
        level.buy_qty = 0.0
        level.borsa_stop_emir_id = None
        level.borsa_stop_fiyati = 0.0
        level.borsa_stop_miktari = 0.0
        level.borsa_stop_hata_sayisi = 0
        if not any(lvl.has_position for lvl in self.grid):
            self.coin_qty = 0.0
            self.alis_zamani = None

    def borsada_yok_kapat(self, level: "GridLevel", fiyat: float, kasa: Optional[MerkeziKasa],
                          acik_pozisyon_sayaci: Optional[list], rapor: Optional["RaporlamaDurumu"],
                          durum_kaydet: Optional[object], sebep: str, kasayi_esitle: bool = True) -> bool:
        """v22: coin borsada yok (elle ya da baska bir yerden satilmis). Bot artik var olmayan coini
        satmaya calismaz: pozisyon ic kayitta kapatilir, sonuc guncel fiyattan TAHMINI olarak gunluge
        yazilir, nakit borsadaki gercek TRY bakiyesine esitlenir ve kullaniciya bir kez haber verilir."""
        tahmini_net = level.buy_qty * fiyat * (1 - KOMISYON_PCT)
        pnl = tahmini_net - level.buy_qty * level.buy_price
        self._pozisyonu_kapat(level)
        if kasa is not None and kasayi_esitle:
            try:
                kasa.bakiye = binance_serbest_try_bakiyesi() if CANLI_MOD else kasa.bakiye + tahmini_net
            except Exception as e:
                print(f"{YELLOW}  TRY bakiyesi okunamadi ({e}); kasa bir sonraki mutabakatta esitlenecek.{RESET}")
        if acik_pozisyon_sayaci is not None and acik_pozisyon_sayaci[0] > 0:
            acik_pozisyon_sayaci[0] -= 1
        if rapor is not None:
            rapor.islem_kaydet(self.symbol, "SATIM", 0.0, pnl)
        self.acik_islem_pnl += pnl
        self._islem_kapanisini_isle(level, fiyat, "BORSADA-YOK")
        print(f"{YELLOW}{BOLD}  {self.symbol}: {sebep} - pozisyon bot kaydinda kapatildi.{RESET}")
        logger.warning("%s borsada yok, pozisyon kapatildi: %s", self.symbol, sebep)
        send_telegram(f"\u2139\ufe0f <b>{self.symbol} borsada bulunamadi</b>\n{html.escape(sebep)}.\n"
                      f"Coin elle satilmis olabilir; bot bu pozisyonu kapatti ve artik yonetmiyor. "
                      f"Tahmini sonuc {pnl:+,.2f} TRY (gercek sonucu Binance TR islem gecmisinizde gorebilirsiniz).")
        if durum_kaydet is not None:
            durum_kaydet()
        return True

    def _islem_kapanisini_isle(self, level: "GridLevel", cikis_fiyati: float, tag: str) -> None:
        """Tamamen kapanan islemi islem gunlugune yazar."""
        gb = self.giris_bilgi or {}
        simdi = datetime.now()
        toplam = self.acik_islem_pnl - (gb.get("komisyon") or 0.0)  # alim komisyonu da islemin maliyeti
        tutar = gb.get("tutar") or self.starting_try or 0.0
        miktar = gb.get("miktar") or (tutar / level.buy_price if level.buy_price else 0.0)
        risk_try = miktar * level.risk_birimi
        kayit = islem_kaydi_olustur(
            self.symbol, _aktif_calisma_modu(), _tarih_oku(gb.get("zaman")), simdi, level.buy_price, cikis_fiyati,
            tutar, toplam, risk_try, level.risk_birimi / level.buy_price if level.buy_price else 0.0, tag,
            (gb.get("analiz") or {}).get("btc_rejimi"))
        islem_gunlugune_yaz(kayit)
        if risk_try > 0:
            print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} islem kapandi: {toplam:+,.2f} TRY "
                  f"({kayit['r_sonucu']:+.2f}R)")
        self.acik_islem_pnl = 0.0
        self.giris_bilgi = {}

    def stop_loss_kontrol(self, price: float, sim: bool, kasa: Optional[MerkeziKasa] = None,
                          acik_pozisyon_sayaci: Optional[list] = None,
                          durum_kaydet: Optional[object] = None,
                          rapor: Optional["RaporlamaDurumu"] = None) -> None:
        """Her turda: zirveyi gunceller; fiyat stop'a indiyse satar. v22: fiyat tek bir islemden okunur;
        ince TRY paritelerinde tek bir sapkin islem sahte stop tetiklemesin diye satmadan once emir
        defterindeki en iyi alis teyit edilir (defter okunamazsa guvenli tarafta kalinip satilir)."""
        for level in self.grid:
            if not level.has_position:
                continue
            if price > level.en_yuksek_fiyat:
                level.en_yuksek_fiyat = price
            stop, etiket = self._ratchet_stop_hesapla(level)
            if price > stop:
                continue
            _, en_iyi_bid, _ = orderbook_spread_kontrol(self.symbol)
            if en_iyi_bid is not None and en_iyi_bid > stop * (1 + STOP_TEYIT_TAMPON_PCT):
                if self.son_teyitsiz_stop != stop:
                    self.son_teyitsiz_stop = stop
                    print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} {YELLOW}son islem fiyati "
                          f"({format_fiyat(price)}) stop'un altinda ama en iyi alis {format_fiyat(en_iyi_bid)} - "
                          f"tek islemlik sapma sayildi, satilmadi.{RESET}")
                continue
            self._satisi_uygula(level, en_iyi_bid or price, etiket, sim, kasa, acik_pozisyon_sayaci, rapor,
                                durum_kaydet)

    def trend_girisi(self, fiyat: float, tutar: float, stop_pct: float, kasa: MerkeziKasa,
                     acik_pozisyon_sayaci: list, rapor: Optional["RaporlamaDurumu"], durum_kaydet,
                     portfoy: float, btc_yukari: Optional[bool]) -> bool:
        """Trend alimi. Stop giristen stop_pct asagida; gunluk kontrolde zirve - 3 x ATR'ye kadar yukselir
        (asla inmez). Kismi kar alma yok. CANLI modda gercek emir (v22: gerceklesen fiyat/miktar borsadan
        okunur); reddedilirse False."""
        exec_price = self._slipajli_fiyat(fiyat, "ALIM")
        buy_qty = tutar / exec_price
        if CANLI_MOD:
            dolum = self._canli_emir_dogrula_ve_gonder("BUY", buy_qty, exec_price)
            if dolum is None:
                return False
            buy_qty, exec_price = dolum
            tutar = buy_qty * exec_price
        komisyon = tutar * KOMISYON_PCT
        kasa.harca(tutar, komisyon)
        self.starting_try = tutar
        self.cash_try = -komisyon
        self.coin_qty = buy_qty
        self.toplam_komisyon += komisyon
        stop = exec_price * (1 - stop_pct)
        self.grid = [GridLevel(price=exec_price, has_position=True, buy_qty=buy_qty, buy_price=exec_price,
                               en_yuksek_fiyat=exec_price, risk_birimi=exec_price - stop, ilk_stop=stop,
                               trend_stop=stop)]
        self.alis_zamani = datetime.now()
        self.giris_bilgi = {"zaman": self.alis_zamani.isoformat(), "miktar": buy_qty, "tutar": tutar,
                            "komisyon": komisyon,
                            "analiz": {"btc_rejimi": ("YUKARI" if btc_yukari else "BILINMIYOR" if btc_yukari is None
                                                      else "ASAGI")}}
        self.acik_islem_pnl = 0.0
        self.son_teyitsiz_stop = 0.0
        acik_pozisyon_sayaci[0] += 1
        if rapor is not None:
            rapor.islem_kaydet(self.symbol, "ALIM", komisyon, None)
        self.record("ALIM", exec_price, buy_qty, tutar)
        print_trade_line(self.symbol, "ALIM", exec_price, buy_qty, tutar, kasa.bakiye, self.coin_name,
                         not CANLI_MOD, komisyon=komisyon, telegram_bildir=False)
        risk_try = buy_qty * (exec_price - stop)
        mesaj = (f"\U0001F7E2 <b>TREND ALIMI: {self.symbol}</b>\n"
                 f"Fiyat: {format_fiyat(exec_price)} TRY | Tutar: {tutar:,.2f} TRY\n"
                 f"Stop: {format_fiyat(stop)} TRY (-%{stop_pct * 100:.1f}) | stop olursa ~{risk_try:,.2f} TRY "
                 f"(portfoyun %{risk_try / portfoy * 100 if portfoy else 0:.1f}'i)\n"
                 f"Sinyal: {TREND_KIRILIM_GUN} gunluk zirve kirildi"
                 + (", BTC yukselis trendinde" if btc_yukari else "") + "\n"
                 "Hedef yok: fiyat yukseldikce stop her gun yukari tasinir.")
        print(f"{GREEN}{BOLD}\U0001F7E2 [TREND POZISYONU ACILDI]{RESET} {self.symbol}: stop {format_fiyat(stop)} "
              f"(-%{stop_pct * 100:.1f}), risk ~{risk_try:,.2f} TRY")
        if self.bildirim_aktif:
            send_telegram(mesaj)
        if durum_kaydet is not None:
            durum_kaydet()
        return True

    def acil_tasfiye(self, current_price: float, kasa: MerkeziKasa,
                     durum_kaydet: Optional[object] = None,
                     rapor: Optional["RaporlamaDurumu"] = None) -> None:
        """ACIL FREN durumunda acik pozisyonu satar. CANLI_MOD'da gercek satis; basarisizsa pozisyon
        acik kalir ve Telegram'a acil uyari gider (elle mudahale gerekebilir)."""
        acik_seviye = next((lvl for lvl in self.grid if lvl.has_position), None)
        if not acik_seviye or self.coin_qty <= 0:
            return
        basarili = self._satisi_uygula(acik_seviye, current_price, "ACIL-TASFIYE", not CANLI_MOD, kasa,
                                       None, rapor, durum_kaydet)
        if not basarili:
            print(f"{RED}  ACIL TASFIYE BASARISIZ: {self.symbol} gercek emir gonderilemedi - "
                  f"pozisyon ACIK KALDI, MANUEL MUDAHALE GEREKEBILIR.{RESET}")
            send_telegram(f"\U0001F6A8 <b>ACIL TASFIYE BASARISIZ</b>\n{self.symbol} - "
                          f"pozisyon acik kaldi, manuel mudahale gerekebilir!")



def get_last_price(symbol: str) -> float:
    """Son islem fiyati (stop teyidi icin emir defterine ayrica bakilir - bkz. stop_loss_kontrol)."""
    url = PRICE_URL_TEMPLATE.format(symbol=symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "project-aurelius-bot"})
    data = http_istek_yap(req, timeout=FIYAT_TIMEOUT_SANIYE, max_deneme=FIYAT_MAX_DENEME)
    return float(data[0]["price"])


def ema_serisi(degerler: list, periyot: int) -> list:
    """EMA serisi (ilk deger ilk 'periyot' degerin ortalamasi)."""
    if len(degerler) < periyot:
        return []
    k = 2 / (periyot + 1)
    ema = sum(degerler[:periyot]) / periyot
    seri = [ema]
    for deger in degerler[periyot:]:
        ema = deger * k + ema * (1 - k)
        seri.append(ema)
    return seri



def print_banner():
    telegram_hazir = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS - v22'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}  BINANCE TR OTOMATIK ALIM-SATIM BOTU  |  GUNLUK TREND TAKIBI{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    if CANLI_MOD:
        print(f"{RED}{BOLD}  !!! CANLI_MOD = True: BU BOT GERCEK PARA ILE GERCEK EMIR GONDERECEK !!!{RESET}")
    else:
        print(f"{YELLOW}  DRY-RUN (SIMULASYON) modunda. Gercek emir gonderilmiyor.{RESET}")
    print(f"{GRAY}  Calisma modu       : {'CANLI (GERCEK PARA)' if CANLI_MOD else 'SIMULASYON'}{RESET}")
    print(f"{CYAN}{BOLD}  Strateji           : TREND - {', '.join(c[:-3] for c in TREND_COINLERI)}{RESET}")
    print(f"{CYAN}                       gunluk kapanis {TREND_KIRILIM_GUN} gunun zirvesini kirinca ve EMA{TREND_EMA} "
          f"ustundeyken alim{' (BTC EMA50 ustundeyse)' if TREND_BTC_FILTRESI else ''};{RESET}")
    print(f"{CYAN}                       stop {TREND_ILK_STOP_ATR:g} x ATR, her gun zirve - {TREND_TAKIP_ATR:g} x ATR'ye "
          f"yukselir; en fazla {TREND_MAKS_POZISYON} pozisyon, islem basina risk %{RISK_PCT * 100:g}{RESET}")
    if not CANLI_MOD:
        print(f"{GRAY}  Sanal/baslangic kasa: {TOPLAM_SANAL_BAKIYE_TRY:,.0f} TRY{RESET}")
    print(f"{GRAY}  Spread filtresi    : max %{MAX_SPREAD_PCT} (ustunde ALIM iptal edilir){RESET}")
    print(f"{GRAY}  Komisyon           : %{KOMISYON_PCT * 100:.2f}{RESET}")
    if CANLI_MOD:
        print(f"{GRAY}  Bakiye mutabakati  : her ~{MUTABAKAT_ARALIGI_SAAT:.0f} saatte + gunluk X raporunda{RESET}")
        print(f"{GRAY}  Borsa stop emri    : "
              f"{f'AKTIF (tetik = bot stop-%{BORSA_STOP_TAMPON_PCT * 100:g})' if BORSA_STOP_AKTIF else 'kapali (AURELIUS_BORSA_STOP=0)'}"
              f"{RESET}")
    print(f"{GRAY}  Acil fren limiti   : %{MAX_DRAWDOWN_PCT * 100:.0f} (portfoyun en yuksek degerinden; "
          f"yeniden baslatmada sifirlanmaz){RESET}")
    print(f"{GRAY}  Durum dosyasi      : {STATE_DOSYASI}{RESET}")
    print(f"{GRAY}  Telegram bildirimi : {'AKTIF (arka plan kuyrugu)' if telegram_hazir else 'kapali (TELEGRAM_BOT_TOKEN/CHAT_ID tanimli degil)'}{RESET}")
    print(f"{GRAY}  Telegram komutlari : {'AKTIF (/yardim)' if (telegram_hazir and TELEGRAM_KOMUTLARI_AKTIF) else 'kapali'}{RESET}")
    print(f"{GRAY}  Durum bildirimi    : {f'her {DURUM_BILDIRIM_SAAT:g} saatte bir' if (telegram_hazir and DURUM_BILDIRIM_SAAT > 0) else 'kapali'}{RESET}")
    print(f"{GRAY}  Saglik pingi       : {'AKTIF (her 5 dk)' if SAGLIK_PING_URL else 'kapali (AURELIUS_SAGLIK_URL tanimli degil)'}{RESET}")
    print(f"{GRAY}  Hata log dosyasi   : {LOG_DOSYASI}{RESET}")
    print(f"{GRAY}  Raporlar           : gunluk X (24 saat), aylik Z (30 gun), haftalik ozet (pazartesi){RESET}")
    print(f"{GRAY}  Islem gunlugu      : {ISLEM_GUNLUGU_CSV} ('rapor' komutu / Telegram /rapor){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}\n")



def print_trade_line(symbol, side, price, qty, amount, cash_after, coin_name, sim, tag="", komisyon=0.0,
                      telegram_bildir=True, net_pnl: Optional[float] = None,
                      net_pnl_pct: Optional[float] = None, guncel_kasa: Optional[float] = None):
    """
    v17: fiyat gosterimi artik format_fiyat() ile DINAMIK basamak
    hassasiyeti kullanir (MODUL 2). SATIM'da net_pnl verilmisse (v9/CANLI
    yolundaki her kapanis _satisi_uygula uzerinden buraya net_pnl/
    net_pnl_pct/guncel_kasa iletir), kumulatif getiri yerine SADECE bu
    islemden elde edilen net K/Z ve satis sonrasi guncel serbest kasa
    bakiyesi gosterilir (MODUL 4). Legacy/backtest SATIM yolunda (kasa
    yok, net_pnl=None) eski genel bicim korunur.
    """
    color = GREEN if side == "ALIM" else RED
    baslik = "ALIM" if side == "ALIM" else "SATIM"
    kaynak = "Simule" if sim else "Gercek"
    etiket_notu = f" ({tag})" if tag else ""

    print(f"{color}{BOLD}[{ts()}] {symbol} {baslik}{etiket_notu}{RESET}")
    print(f"   {qty:.6f} {coin_name}  x  {format_fiyat(price)} TRY  =  {amount:,.2f} TRY")
    if side == "SATIM" and net_pnl is not None:
        pnl_renk = GREEN if net_pnl >= 0 else RED
        pnl_pct_str = f"{net_pnl_pct:+.2f}%" if net_pnl_pct is not None else "N/A"
        print(f"   {pnl_renk}Bu Islemden Net K/Z: {net_pnl:+,.2f} TRY ({pnl_pct_str}){RESET}")
        if guncel_kasa is not None:
            print(f"   Yeni Guncel Kasa: {guncel_kasa:,.2f} TRY")
    print(f"   Kalan Nakit: {cash_after:,.2f} TRY   |   Komisyon: {komisyon:,.2f} TRY   |   Kaynak: {kaynak}\n")
    csv_islem_yaz(symbol, side, price, qty, amount, komisyon, kaynak, tag)

    if telegram_bildir:
        if side == "SATIM" and net_pnl is not None:
            # v17 MODUL 4: ISLEM BAZLI net K/Z bildirimi - "Bu Islemden Net
            # Kar/Zarar" (+TL ve +%) ve satis sonrasi Yeni Guncel Kasa.
            emoji = "\U0001F4B0" if net_pnl >= 0 else "\U0001F53B"
            pnl_pct_str = f"{net_pnl_pct:+.2f}%" if net_pnl_pct is not None else "N/A"
            kasa_satiri = f"\nYeni Guncel Kasa: {guncel_kasa:,.2f} TRY" if guncel_kasa is not None else ""
            mesaj = (
                f"{emoji} <b>[SATIS TAMAMLANDI] {symbol}{etiket_notu}</b>\n"
                f"Bu Islemden Net Kar: {net_pnl:+,.2f} TRY ({pnl_pct_str}){kasa_satiri}"
            )
        else:
            emoji = "\U0001F7E2" if side == "ALIM" else "\U0001F534"
            baslik_tg = f"{baslik} ({tag})" if tag else baslik
            mesaj = (
                f"{emoji} <b>{symbol} {baslik_tg}</b>\n"
                f"{qty:.6f} {coin_name} @ {format_fiyat(price)} TRY\n"
                f"Tutar: {amount:,.2f} TRY | Komisyon: {komisyon:,.2f} TRY\n"
                f"Kaynak: {kaynak}"
            )
        send_telegram(mesaj)


def v9_toplam_portfoy_degeri(kasa: MerkeziKasa, pozisyonlar: dict) -> float:
    """Merkezi kasadaki serbest nakit + tum acik pozisyonlarin guncel piyasa degeri."""
    toplam = kasa.bakiye
    for bot in pozisyonlar.values():
        if bot.has_open_position:
            toplam += bot.coin_qty * bot.guncel_fiyat()
    return toplam


def _yas_formatla(alis_zamani: Optional[datetime]) -> str:
    """v16: Pozisyonun ne kadar suredir acik oldugunu kisa bir metinle
    gosterir (orn. '45dk', '19s'). alis_zamani yoksa 'N/A' doner."""
    if alis_zamani is None:
        return "N/A"
    saniye = (datetime.now() - alis_zamani).total_seconds()
    saat = saniye / 3600
    if saat < 1:
        return f"{max(0, int(saniye / 60))}dk"
    if saat >= 48:
        return f"{saat / 24:.0f}g"  # trend pozisyonlari gunlerce acik kalir
    return f"{saat:.0f}s"


def print_performans_raporu(kasa: MerkeziKasa, pozisyonlar: dict, acik_pozisyon_sayisi: int,
                            telegram_gonder: bool = True):
    """Baslangic/guncel bakiye, net K/Z, komisyon ve acik pozisyonlari (giris, guncel fiyat, stop) konsola
    tablo olarak basar, portfoy kaydina bir satir ekler; istenirse Telegram'a kisa ozet gonderir."""
    guncel_bakiye = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    pnl = guncel_bakiye - kasa.baslangic
    pnl_pct = (pnl / kasa.baslangic) * 100 if kasa.baslangic else 0
    pnl_renk = GREEN if pnl >= 0 else RED

    print(f"{CYAN}{BOLD}{'=' * 70}{RESET}")
    print(f"{CYAN}{BOLD}  PERFORMANS RAPORU - {ts()}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 70}{RESET}")
    print(f"  {'Baslangic Sermayesi':<28}: {kasa.baslangic:>14,.2f} TRY")
    print(f"  {'Guncel Bakiye':<28}: {guncel_bakiye:>14,.2f} TRY")
    print(f"  {'Net Kar/Zarar':<28}: {pnl_renk}{pnl:>+14,.2f} TRY  ({pnl_pct:+.2f}%){RESET}")
    print(f"  {'Toplam Odenen Komisyon':<28}: {kasa.toplam_komisyon:>14,.2f} TRY")
    print(f"  {'Acik Pozisyon Sayisi':<28}: {acik_pozisyon_sayisi} / {TREND_MAKS_POZISYON}")
    print(f"{CYAN}{'-' * 70}{RESET}")

    acik_olanlar = [b for b in pozisyonlar.values() if b.has_open_position]
    if acik_olanlar:
        print(f"  {BOLD}Acik Pozisyonlar:{RESET}")
        print(f"  {'Sembol':<9} {'Yas':>6} {'Miktar':>12} {'Giris':>12} {'Guncel':>12} {'Stop':>12} "
              f"{'K/Z(TRY)':>10} {'K/Z%':>7}")
        for b in acik_olanlar:
            fiyat = b.guncel_fiyat()
            deger = b.coin_qty * fiyat
            acik_seviye = next((lvl for lvl in b.grid if lvl.has_position), None)
            giris_fiyati = acik_seviye.buy_price if acik_seviye else 0.0
            maliyet = b.coin_qty * giris_fiyati
            kz = deger - maliyet  # su an acik olan pozisyonun anlik K/Z'si
            kz_pct = (kz / maliyet * 100) if maliyet else 0
            renk = GREEN if kz >= 0 else RED
            _, stop, _ = b.acik_hedef_ve_stop()
            stop_str = format_fiyat(stop) if stop is not None else "N/A"
            print(f"  {b.symbol:<9} {_yas_formatla(b.alis_zamani):>6} {b.coin_qty:>12.6f} "
                  f"{format_fiyat(giris_fiyati):>12} {format_fiyat(fiyat):>12} {stop_str:>12} "
                  f"{renk}{kz:>+10,.2f}{RESET} {renk}{kz_pct:>+6.2f}%{RESET}")
    else:
        print(f"  {YELLOW}Su an acik pozisyon yok - nakitte bekleniyor.{RESET}")

    print(f"{YELLOW}  Hatirlatma: {'CANLI MOD - GERCEK PARA.' if CANLI_MOD else 'Bu bir SIMULASYON.'}{RESET}")
    csv_portfoy_yaz(guncel_bakiye, kasa.baslangic, pnl, pnl_pct, acik_pozisyon_sayisi)
    print(f"{CYAN}{'=' * 70}{RESET}\n")

    if not telegram_gonder:
        return
    ozet_emoji = "\U0001F4C8" if pnl >= 0 else "\U0001F4C9"
    send_telegram(
        f"{ozet_emoji} <b>Performans Ozeti</b>\n"
        f"Bakiye: {guncel_bakiye:,.2f} TRY\n"
        f"Net K/Z: {pnl:+,.2f} TRY ({pnl_pct:+.2f}%)\n"
        f"Acik Pozisyon: {acik_pozisyon_sayisi}/{TREND_MAKS_POZISYON}\n"
        f"Mod: {'CANLI' if CANLI_MOD else 'SIMULASYON'}"
    )


# ==========================================================================
# v11 BOLUM 6/7: GUNLUK X RAPORU VE AYLIK Z RAPORU
# ==========================================================================

def x_raporu_olustur_ve_gonder(kasa: MerkeziKasa, pozisyonlar: dict, rapor: RaporlamaDurumu) -> None:
    """
    v11: Son 24 saatin operasyonel ara bilancosunu cikarir. Sayac
    SIFIRLANMAZ - donem sonunda bir "karne" alinir, ardindan SADECE
    24 saatlik sayaclar bir sonraki donem icin sifirlanir (Z/aylik
    sayaclar etkilenmez).
    """
    guncel_portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    gunluk_pnl = rapor.x_realized_pnl
    baz = rapor.x_donem_baslangic_portfoy
    gunluk_pnl_pct = (gunluk_pnl / baz * 100) if baz else 0.0

    karar_verilen_islem = rapor.x_kazanan + rapor.x_kaybeden
    win_rate = (rapor.x_kazanan / karar_verilen_islem * 100) if karar_verilen_islem else 0.0

    acik_olanlar = [b for b in pozisyonlar.values() if b.has_open_position]
    if acik_olanlar:
        satirlar = []
        for b in acik_olanlar:
            fiyat = b.guncel_fiyat()
            acik_seviye = next((lvl for lvl in b.grid if lvl.has_position), None)
            giris = acik_seviye.buy_price if acik_seviye else 0.0
            kz_pct = ((fiyat - giris) / giris * 100) if giris else 0.0
            satirlar.append(f"{b.symbol} ({kz_pct:+.2f}%)")
        acik_pozisyon_str = ", ".join(satirlar)
    else:
        acik_pozisyon_str = "Yok (nakitte)"

    pnl_renk = GREEN if gunluk_pnl >= 0 else RED
    tarih_str = datetime.now().strftime("%d.%m.%Y %H:%M")

    print(f"\n{CYAN}{BOLD}{'#' * 74}{RESET}")
    print(f"{CYAN}{BOLD}  GUNLUK X RAPORU - {tarih_str}{RESET}")
    print(f"{CYAN}{BOLD}{'#' * 74}{RESET}")
    print(f"  {'Toplam Portfoy':<28}: {guncel_portfoy:>14,.2f} TRY")
    print(f"  {'Gunluk Realize K/Z':<28}: {pnl_renk}{gunluk_pnl:>+14,.2f} TRY  ({gunluk_pnl_pct:+.2f}%){RESET}")
    print(f"  {'Gunluk Islem Sayisi':<28}: {rapor.x_alim_sayisi} ALIM / {rapor.x_satim_sayisi} SATIM")
    print(f"  {'Basari Orani (Win Rate)':<28}: %{win_rate:.1f}  ({rapor.x_kazanan} kazanan / {rapor.x_kaybeden} kaybeden)")
    print(f"  {'Odenen Komisyon (24s)':<28}: {rapor.x_komisyon:,.2f} TRY")
    print(f"  {'Acik Pozisyonlar':<28}: {acik_pozisyon_str}")
    print(f"{CYAN}{BOLD}{'#' * 74}{RESET}\n")

    mesaj = (
        f"\U0001F4CA <b>PROJECT AURELIUS - GUNLUK X RAPORU</b> \U0001F4CA\n"
        f"\U0001F4C5 Tarih/Saat: {tarih_str}\n"
        f"\U0001F4B0 Toplam Portfoy: {guncel_portfoy:,.2f} TRY\n"
        f"\U0001F4B5 Gunluk Realize K/Z: {gunluk_pnl:+,.2f} TRY ({gunluk_pnl_pct:+.2f}%)\n"
        f"\U0001F4C8 Gunluk Islem Sayisi: {rapor.x_alim_sayisi} ALIM / {rapor.x_satim_sayisi} SATIM\n"
        f"\U0001F3AF Basari Orani (Win Rate): %{win_rate:.1f}\n"
        f"\U0001F4B8 Odenen Komisyon (24s): {rapor.x_komisyon:,.2f} TRY\n"
        f"\U0001F50D Acik Pozisyonlar: {acik_pozisyon_str}"
    )
    send_telegram(mesaj)

    rapor.x_sifirla(guncel_portfoy)  # yeni 24 saatlik donem basliyor


def z_raporu_olustur_ve_gonder(kasa: MerkeziKasa, pozisyonlar: dict, rapor: RaporlamaDurumu) -> None:
    """
    v11: 30 gunluk kumulatif donemi KAPATIR, kesin mali bilanco cikarir,
    CSV'ye kalici olarak ekler ve Telegram'a oncelikli bildirim olarak
    gonderir. Rapor sonrasi yeni bir 30 gunluk donem baslatilir.
    """
    guncel_portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    ay_basi = rapor.z_ay_basi_bakiye
    aylik_pnl = guncel_portfoy - ay_basi
    aylik_pnl_pct = (aylik_pnl / ay_basi * 100) if ay_basi else 0.0

    if rapor.z_coin_pnl:
        en_iyi_sym, en_iyi_pnl = max(rapor.z_coin_pnl.items(), key=lambda kv: kv[1])
        en_kotu_sym, en_kotu_pnl = min(rapor.z_coin_pnl.items(), key=lambda kv: kv[1])
    else:
        en_iyi_sym, en_iyi_pnl = "-", 0.0
        en_kotu_sym, en_kotu_pnl = "-", 0.0

    baslangic_tarihi = rapor.son_z_raporu_zamani.strftime("%d.%m.%Y")
    bitis_tarihi = datetime.now().strftime("%d.%m.%Y")
    en_iyi_str = f"{en_iyi_sym} (+{en_iyi_pnl:,.2f} TRY)" if en_iyi_pnl > 0 else "-"
    en_kotu_str = f"{en_kotu_sym} ({en_kotu_pnl:,.2f} TRY)" if en_kotu_pnl < 0 else "-"

    pnl_renk = GREEN if aylik_pnl >= 0 else RED

    print(f"\n{MAGENTA}{BOLD}{'=' * 74}{RESET}")
    print(f"{MAGENTA}{BOLD}  AYLIK Z RAPORU (DONEM KAPANISI) - {ts()}{RESET}")
    print(f"{MAGENTA}{BOLD}{'=' * 74}{RESET}")
    print(f"  {'Donem':<28}: {baslangic_tarihi} - {bitis_tarihi}")
    print(f"  {'Donem Basi Sermaye':<28}: {ay_basi:>14,.2f} TRY")
    print(f"  {'Donem Sonu Sermaye':<28}: {guncel_portfoy:>14,.2f} TRY")
    print(f"  {'Net K/Z':<28}: {pnl_renk}{aylik_pnl:>+14,.2f} TRY  ({aylik_pnl_pct:+.2f}%){RESET}")
    print(f"  {'Maksimum Cekilme':<28}: %{rapor.z_en_derin_dusus_pct * 100:.2f}")
    print(f"  {'Toplam Komisyon Faturasi':<28}: {rapor.z_toplam_komisyon:,.2f} TRY")
    print(f"  {'En Cok Kazandiran Coin':<28}: {en_iyi_str}")
    print(f"  {'En Cok Kaybettiren Coin':<28}: {en_kotu_str}")
    print(f"  {'Toplam Islem Adedi':<28}: {rapor.z_toplam_islem}")
    print(f"{MAGENTA}{BOLD}{'=' * 74}{RESET}\n")

    z_csv_yaz(baslangic_tarihi, bitis_tarihi, ay_basi, guncel_portfoy, aylik_pnl, aylik_pnl_pct,
              rapor.z_en_derin_dusus_pct, rapor.z_toplam_komisyon, en_iyi_sym, en_iyi_pnl,
              en_kotu_sym, en_kotu_pnl, rapor.z_toplam_islem)

    mesaj = (
        f"\U0001F3C6 <b>PROJECT AURELIUS - AYLIK Z RAPORU (DONEM KAPANISI)</b> \U0001F3C6\n"
        f"\U0001F4C5 Donem: {baslangic_tarihi} - {bitis_tarihi}\n"
        f"\U0001F3E6 Donem Basi Sermaye: {ay_basi:,.2f} TRY\n"
        f"\U0001F3E6 Donem Sonu Sermaye: {guncel_portfoy:,.2f} TRY\n"
        f"\U0001F680 Net K/Z: {aylik_pnl:+,.2f} TRY ({aylik_pnl_pct:+.2f}%)\n"
        f"\U0001F4C9 Maksimum Cekilme: %{rapor.z_en_derin_dusus_pct * 100:.2f}\n"
        f"\U0001F9FE Toplam Komisyon Faturasi: {rapor.z_toplam_komisyon:,.2f} TRY\n"
        f"\U0001F947 En Cok Kazandiran Coin: {en_iyi_str}\n"
        f"\u26A0\uFE0F En Cok Kaybettiren Coin: {en_kotu_str}\n"
        f"\U0001F4CA Toplam Islem Adedi: {rapor.z_toplam_islem}"
    )
    send_telegram(mesaj)

    rapor.son_z_raporu_zamani = datetime.now()
    rapor.z_sifirla(guncel_portfoy)  # yeni 30 gunluk donem basliyor


def print_trade_history_table(pozisyonlar):
    print(f"\n{BOLD}{'ZAMAN':<10} {'COIN':<10} {'YON':<6} {'FIYAT (TRY)':>14} {'MIKTAR':>14} {'TUTAR (TRY)':>14}{RESET}")
    print("-" * 80)
    all_trades = []
    for b in pozisyonlar:
        for t, side, price, qty, amount in b.history:
            all_trades.append((t, b.symbol, side, price, qty, amount))
    all_trades.sort(key=lambda x: x[0])
    if not all_trades:
        print("Henuz islem yapilmadi.")
    for t, symbol, side, price, qty, amount in all_trades:
        color = GREEN if side == "ALIM" else RED
        print(f"{t:<10} {symbol:<10} {color}{side:<6}{RESET} {format_fiyat(price):>14} {qty:>14.6f} {amount:>14,.2f}")
    print("-" * 80)


# ==========================================================================
# CANLI/SIMULASYON CALISTIRMA (v10)
# ==========================================================================

# ==========================================================================
# v18 KESINTI ONLEMLERI: durum bildirimi, saglik pingi, Telegram komutlari,
# bosaltma modu, kapanis sorusu, baslatici kurulumu
# ==========================================================================

TELEGRAM_YARDIM_METNI = (
    "<b>Project Aurelius komutlari</b>\n"
    "/durum - portfoy ve acik pozisyonlar\n"
    "/alimdurdur - yeni alimlari durdur (acik pozisyonlar yonetilmeye devam eder)\n"
    "/devam - yeni alimlari yeniden ac\n"
    "/bosalt - yeni alim yapma; acik pozisyonlar kapaninca botu durdur\n"
    "/hepsinisat - tum pozisyonlari piyasa fiyatindan sat (onay ister)\n"
    "/btc - BTC trend filtresi (EMA50'ye gore)\n"
    "/trend - coinlerin alim sinyaline (50 gunluk zirveye) uzakligi\n"
    "/rapor - son 30 gunun islem ozeti (islem gunlugunden)\n"
    "/hafta - haftalik ozet (her pazartesi kendiliginden de gelir)\n"
    "/frensifirla - acil fren referansini bugunku portfoy degerine cek\n"
    "/yardim - bu liste"
)


def durum_ozeti_metni(kasa: "MerkeziKasa", pozisyonlar: dict) -> str:
    """/durum komutu ve periyodik durum bildirimi icin kisa HTML ozet."""
    portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    pnl = portfoy - kasa.baslangic
    satirlar = [
        f"<b>Project Aurelius</b> ({_aktif_calisma_modu()}) - {datetime.now().strftime('%d.%m %H:%M')}",
        f"Portfoy: {portfoy:,.2f} TRY | Nakit: {kasa.bakiye:,.2f} TRY",
        f"Baslangic: {kasa.baslangic:,.2f} TRY | toplam K/Z: {pnl:+,.2f} TRY"
        + (f" (%{pnl / kasa.baslangic * 100:+.1f})" if kasa.baslangic else ""),
        f"Yeni alimlar: {ALIM_DURUMU_ACIKLAMA.get(_alim_durumu, _alim_durumu)}",
        html.escape(trend_durum_satiri()),
    ] + [html.escape(satir) for satir in _risk.durum_satirlari(portfoy)]
    if CANLI_MOD and BORSA_STOP_AKTIF and _trend_durumu.get("borsa_stop_kapali"):
        satirlar.append("UYARI: borsa stop emri kapali - " + html.escape(str(_trend_durumu["borsa_stop_kapali"])))
    acik = [b for b in pozisyonlar.values() if b.has_open_position]
    if not acik:
        satirlar.append("Acik pozisyon yok.")
    for b in acik:
        seviye = next((lvl for lvl in b.grid if lvl.has_position), None)
        if seviye is None:
            continue
        fiyat = b.guncel_fiyat()
        kar_pct = (fiyat / seviye.buy_price - 1) * 100 if seviye.buy_price else 0.0
        stop, _ = b._ratchet_stop_hesapla(seviye)
        koruma = (f", borsa stop {format_fiyat(seviye.borsa_stop_fiyati)}"
                  if seviye.borsa_stop_emir_id else "")
        satirlar.append(f"- {b.symbol}: {format_fiyat(fiyat)} TRY ({kar_pct:+.2f}%), "
                        f"stop {format_fiyat(stop)}{koruma}, {_yas_formatla(b.alis_zamani)}")
    return "\n".join(satirlar)


def tum_pozisyonlari_kapat(pozisyonlar: dict, kasa: "MerkeziKasa", durum_kaydet, rapor,
                           acik_pozisyon_sayaci: Optional[list], tag: str = "MANUEL-KAPANIS") -> tuple:
    """Tum acik pozisyonlari guncel fiyattan satar. Donus: (satilan_sayi, satilamayan_semboller)."""
    satilan, kalan = 0, []
    for bot in pozisyonlar.values():
        if not bot.has_open_position:
            continue
        try:
            fiyat = get_last_price(bot.symbol)
            bot.last_real_price = fiyat
        except Exception:
            fiyat = bot.guncel_fiyat()
        basarili = True
        for seviye in bot.grid:
            if seviye.has_position:
                basarili = bot._satisi_uygula(seviye, fiyat, tag, False, kasa, acik_pozisyon_sayaci,
                                              rapor, durum_kaydet) and basarili
        if basarili and not bot.has_open_position:
            satilan += 1
        else:
            kalan.append(bot.symbol)
    if acik_pozisyon_sayaci is not None:
        acik_pozisyon_sayaci[0] = sum(1 for b in pozisyonlar.values() if b.has_open_position)
    return satilan, kalan


def telegram_komutunu_uygula(komut: str, kasa: "MerkeziKasa", pozisyonlar: dict, durum_kaydet, rapor,
                             acik_pozisyon_sayaci: Optional[list], kontrol: dict) -> None:
    """Ana thread'de calisir (alim-satim ile ayni thread - yaris durumu olmaz)."""
    global _alim_durumu
    komut = (komut.split() or [""])[0]
    if komut == "/btc":
        send_telegram("<pre>" + html.escape("\n".join(btc_durum_satirlari())) + "</pre>")
        return
    if komut == "/trend":
        send_telegram("<pre>" + html.escape("\n".join(trend_durumu_satirlari(pozisyonlar))) + "</pre>")
        return
    if komut == "/hafta":
        send_telegram(haftalik_ozet_metni(kasa, pozisyonlar))
        return
    if komut == "/frensifirla":
        portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
        _risk.fren_sifirla(portfoy)
        durum_kaydet()
        send_telegram(f"\U0001F6E1 Acil fren referansi {portfoy:,.2f} TRY'ye cekildi; bu degerden "
                      f"%{MAX_DRAWDOWN_PCT * 100:.0f} dususte fren tekrar devreye girer.")
        return
    if komut == "/rapor":
        satirlar = ["Son 30 gun (islem gunlugu):"] + islem_ozeti_satirlari(islem_gunlugunu_oku(gun=30))
        send_telegram("<pre>" + html.escape("\n".join(satirlar)) + "</pre>")
        return
    if komut == "/durum":
        send_telegram(durum_ozeti_metni(kasa, pozisyonlar))
    elif komut == "/alimdurdur":
        _alim_durumu = "DURDURULDU"
        durum_kaydet()
        send_telegram("\u23F8 <b>Yeni alimlar durduruldu.</b>\nAcik pozisyonlar stoplariyla "
                      "yonetilmeye devam ediyor. Tekrar acmak icin /devam")
    elif komut == "/devam":
        _alim_durumu = "ACIK"
        durum_kaydet()
        send_telegram("\u25B6\uFE0F <b>Yeni alimlar acildi.</b>")
    elif komut == "/bosalt":
        _alim_durumu = "BOSALTMA"
        durum_kaydet()
        acik = sum(1 for b in pozisyonlar.values() if b.has_open_position)
        send_telegram(f"\U0001F9F9 <b>Bosaltma modu acildi.</b>\nYeni alim yapilmayacak; {acik} acik pozisyon "
                      f"kendi kurallariyla kapaninca bot duracak. Iptal icin /devam")
    elif komut == "/hepsinisat":
        acik = sum(1 for b in pozisyonlar.values() if b.has_open_position)
        if not acik:
            send_telegram("Acik pozisyon yok, satilacak bir sey yok.")
            return
        kontrol["hepsini_sat_bitis"] = time.monotonic() + HEPSINI_SAT_ONAY_SANIYE
        send_telegram(f"\u26a0\ufe0f <b>{acik} acik pozisyonun TAMAMI piyasa fiyatindan satilacak.</b>\n"
                      f"Onaylamak icin {HEPSINI_SAT_ONAY_SANIYE} saniye icinde /onayla gonderin.")
    elif komut == "/onayla":
        if time.monotonic() > kontrol.get("hepsini_sat_bitis", 0.0):
            send_telegram("Onaylanacak bir islem yok (once /hepsinisat gonderin; onay suresi "
                          f"{HEPSINI_SAT_ONAY_SANIYE} sn).")
            return
        kontrol["hepsini_sat_bitis"] = 0.0
        _alim_durumu = "DURDURULDU"  # satistan hemen sonra yeniden alim yapilmasin
        satilan, kalan = tum_pozisyonlari_kapat(pozisyonlar, kasa, durum_kaydet, rapor,
                                                acik_pozisyon_sayaci, "MANUEL-KAPANIS")
        durum_kaydet()
        mesaj = (f"\u2705 <b>{satilan} pozisyon satildi.</b>\nYeni alimlar DURDURULDU "
                 f"(acmak icin /devam).")
        if kalan:
            mesaj += (f"\n\u26a0\ufe0f Satilamayan: {html.escape(', '.join(kalan))} - bu pozisyon acik kaldi "
                      f"(stopuyla yonetilmeye devam eder). Tekrar denemek icin /hepsinisat, "
                      f"ya da Binance TR'den kontrol edin.")
        send_telegram(mesaj)
    elif komut in ("/yardim", "/help", "/start"):
        send_telegram(TELEGRAM_YARDIM_METNI)
    else:
        send_telegram(f"Bilinmeyen komut: {html.escape(komut)}\n\n{TELEGRAM_YARDIM_METNI}")


_telegram_komut_kuyrugu: "queue.Queue[str]" = queue.Queue()
_telegram_dinleyici_baslatildi = False


def _telegram_guncellemeleri_al(offset: Optional[int], bekleme_saniye: int) -> list:
    parametreler = {"timeout": bekleme_saniye, "allowed_updates": '["message"]'}
    if offset is not None:
        parametreler["offset"] = offset
    url = (f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?"
           f"{urllib.parse.urlencode(parametreler)}")
    req = urllib.request.Request(url, headers={"User-Agent": "project-aurelius-bot"})
    with urllib.request.urlopen(req, timeout=bekleme_saniye + 15) as resp:
        veri = json.loads(resp.read().decode())
    return veri.get("result", []) if isinstance(veri, dict) and veri.get("ok") else []


def _telegram_komut_dinleyici() -> None:
    """Arka plan thread'i: sadece komutlari kuyruga ekler, islem YAPMAZ. Bot
    kapaliyken gonderilmis eski mesajlar (orn. unutulmus bir /hepsinisat) atlanir."""
    offset = None
    while offset is None:
        try:
            eski = _telegram_guncellemeleri_al(-1, 0)
            offset = eski[-1]["update_id"] + 1 if eski else 0
        except Exception as e:
            logger.warning("Telegram komut dinleyici baslatilamadi, tekrar denenecek: %s", e)
            time.sleep(15)
    while True:
        try:
            for guncelleme in _telegram_guncellemeleri_al(offset, 25):
                offset = guncelleme["update_id"] + 1
                mesaj = guncelleme.get("message") or {}
                if str(mesaj.get("chat", {}).get("id")) != str(TELEGRAM_CHAT_ID):
                    logger.warning("Yetkisiz sohbetten gelen Telegram mesaji yok sayildi: %s",
                                   mesaj.get("chat", {}).get("id"))
                    continue
                metin = (mesaj.get("text") or "").strip()
                if metin.startswith("/"):
                    parcalar = metin.split()
                    _telegram_komut_kuyrugu.put(parcalar[0].split("@")[0].lower())
        except Exception as e:
            logger.warning("Telegram komutlari alinamadi: %s", e)
            time.sleep(10)


def telegram_komut_dinleyicisini_baslat() -> bool:
    global _telegram_dinleyici_baslatildi
    if not (TELEGRAM_KOMUTLARI_AKTIF and TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        return False
    if not _telegram_dinleyici_baslatildi:
        threading.Thread(target=_telegram_komut_dinleyici, daemon=True, name="telegram-komut").start()
        _telegram_dinleyici_baslatildi = True
    return True


def bekleyen_telegram_komutlari() -> list:
    komutlar = []
    while True:
        try:
            komutlar.append(_telegram_komut_kuyrugu.get_nowait())
        except queue.Empty:
            return komutlar


def _saglik_pingi_gonder(ek: str = "", bekle: bool = False) -> None:
    """Dis saglik servisine (AURELIUS_SAGLIK_URL) 'hala calisiyorum' sinyali gonderir.
    Sinyal kesilirse servis size haber verir (bilgisayar kapansa bile)."""
    if not SAGLIK_PING_URL:
        return

    def gonder():
        try:
            req = urllib.request.Request(SAGLIK_PING_URL.rstrip("/") + ek,
                                         headers={"User-Agent": "project-aurelius-bot"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as e:
            logger.warning("Saglik pingi gonderilemedi: %s", e)

    if bekle:
        gonder()
    else:
        threading.Thread(target=gonder, daemon=True, name="saglik-pingi").start()


def _dongu_beklemesi(komut_isleyici) -> None:
    """Turlar arasi bekleme. Telegram komutlari aciksa bekleme boyunca her saniye
    komutlara bakilir (yanit ~1 sn icinde gelir)."""
    if komut_isleyici is None:
        time.sleep(REAL_POLL_INTERVAL_SECONDS)
        return
    bitis = time.monotonic() + REAL_POLL_INTERVAL_SECONDS
    while True:
        komut_isleyici()
        kalan = bitis - time.monotonic()
        if kalan <= 0:
            return
        time.sleep(min(1.0, kalan))


def _kapanista_pozisyon_sorusu() -> str:
    """Ctrl+C sonrasi acik pozisyonlar icin secim ister. Etkilesimli konsol yoksa
    veya cevap alinamazsa guvenli varsayilan 'H' (oldugu gibi birak)."""
    try:
        if sys.stdin is None or not sys.stdin.isatty():
            return "H"
    except Exception:
        return "H"
    print(f"{YELLOW}{BOLD}  Acik pozisyonlar ne yapilsin?{RESET}")
    print(f"{YELLOW}    [H] Oldugu gibi birak (varsayilan) - borsa stop emri olan pozisyonlar bot kapaliyken de "
          f"korunur; olmayanlarin stop'u bot acilinca calisir{RESET}")
    print(f"{YELLOW}    [S] Hepsini SIMDI piyasa fiyatindan sat{RESET}")
    try:
        cevap = input("  Seciminiz (H/S) ve Enter: ")
    except (KeyboardInterrupt, EOFError):
        print()
        return "H"
    return "S" if cevap.strip().upper() in ("S", "SAT") else "H"


def _bat_degeri(deger: str) -> str:
    return deger.replace("%", "%%").replace('"', "")


def baslatici_olustur() -> int:
    """'python project_aurelius_bot_v22.py kurulum': bu penceredeki ayarlarla, bot
    cokerse/koparsa 60 sn sonra kendini yeniden baslatan baslatici dosyayi olusturur
    ve (Windows'ta, istege bagli) oturum acilinca otomatik baslatir."""
    gerekli = ["BINANCE_TR_API_KEY", "BINANCE_TR_SECRET_KEY", "AURELIUS_LIVE_CONFIRM", "AURELIUS_CANLI_MOD"]
    istege_bagli = ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "AURELIUS_SAGLIK_URL",
                    "AURELIUS_DURUM_BILDIRIM_SAAT", "AURELIUS_TELEGRAM_KOMUT", "AURELIUS_BORSA_STOP"]
    eksik = [isim for isim in gerekli if not _ortam_degiskeni_str_oku(isim)]
    if eksik:
        print(f"{RED}  HATA: Once bu pencerede su degiskenleri tanimlayin: {', '.join(eksik)}{RESET}")
        return CIKIS_AYAR_HATASI
    degerler = [(isim, _ortam_degiskeni_str_oku(isim)) for isim in gerekli + istege_bagli
                if _ortam_degiskeni_str_oku(isim)]
    betik = os.path.abspath(__file__)
    python = sys.executable or "python"

    if os.name == "nt":
        dosya = os.path.join(_SCRIPT_DIR, "baslat.bat")
        satirlar = ["@echo off", "title Project Aurelius", f'cd /d "{_SCRIPT_DIR}"']
        satirlar += [f'set "{isim}={_bat_degeri(deger)}"' for isim, deger in degerler]
        satirlar += [
            ":dongu",
            f'"{python}" "{betik}"',
            "set KOD=%ERRORLEVEL%",
            f'if "%KOD%"=="{CIKIS_DUR}" goto son',
            f'if "%KOD%"=="{CIKIS_AYAR_HATASI}" goto son',
            "echo.",
            "echo [%date% %time%] Bot beklenmedik sekilde kapandi (kod %KOD%). 60 sn sonra yeniden "
            "baslatilacak - iptal icin Ctrl+C.",
            "timeout /t 60 /nobreak >nul",
            "goto dongu",
            ":son",
            "echo.",
            "echo Bot durdu (kod %KOD%), yeniden baslatilmayacak.",
            "pause",
        ]
    else:
        dosya = os.path.join(_SCRIPT_DIR, "baslat.sh")
        satirlar = ["#!/usr/bin/env bash", f"cd '{_SCRIPT_DIR}'"]
        satirlar += [f"export {isim}='" + deger.replace("'", "'\\''") + "'" for isim, deger in degerler]
        satirlar += [
            "while true; do",
            f"  '{python}' '{betik}'",
            "  KOD=$?",
            f"  if [ $KOD -eq {CIKIS_DUR} ] || [ $KOD -eq {CIKIS_AYAR_HATASI} ]; then",
            "    echo \"Bot durdu (kod $KOD), yeniden baslatilmayacak.\"; break",
            "  fi",
            "  echo \"Bot beklenmedik sekilde kapandi (kod $KOD). 60 sn sonra yeniden baslatilacak (iptal: Ctrl+C).\"",
            "  sleep 60",
            "done",
        ]
    with open(dosya, "w", encoding="utf-8", newline="\r\n" if os.name == "nt" else "\n") as f:
        f.write("\n".join(satirlar) + "\n")
    if os.name != "nt":
        os.chmod(dosya, 0o700)
    print(f"{GREEN}  Baslatici olusturuldu: {dosya}{RESET}")
    print(f"{GRAY}  Icine yazilan ayarlar: {', '.join(isim for isim, _ in degerler)}{RESET}")
    print(f"{YELLOW}  UYARI: Bu dosya API anahtarlarinizi icerir - kimseyle paylasmayin.{RESET}")
    print(f"{GRAY}  Bot cokerse veya internet/bakiye sorunuyla baslayamazsa 60 sn sonra kendini yeniden "
          f"baslatir; Ctrl+C, bosaltma veya ACIL FREN ile durunca yeniden baslatmaz.{RESET}")

    if os.name == "nt" and os.environ.get("APPDATA"):
        try:
            cevap = input("  Windows oturumu acilinca bot otomatik baslasin mi? (E/H): ")
        except (KeyboardInterrupt, EOFError):
            cevap = "H"
        baslangic = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu",
                                 "Programs", "Startup", "Aurelius_otomatik_baslat.bat")
        if cevap.strip().upper() in ("E", "EVET"):
            with open(baslangic, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(f'@echo off\nstart "Project Aurelius" "{dosya}"\n')
            print(f"{GREEN}  Otomatik baslatma eklendi: {baslangic}{RESET}")
            print(f"{GRAY}  Kaldirmak icin bu dosyayi silin. Elektrik kesintisinden sonra bilgisayarin "
                  f"acilip oturumun acilmasi gerekir.{RESET}")
        elif os.path.exists(baslangic):
            print(f"{GRAY}  Onceden eklenmis otomatik baslatma duruyor: {baslangic}{RESET}")
    print(f"{CYAN}  Botu baslatmak icin: {os.path.basename(dosya)} dosyasini calistirin.{RESET}")
    return CIKIS_DUR


def _sermaye_hareketi_mi(fark: float, portfoy: float) -> bool:
    return abs(fark) >= max(SERMAYE_HAREKETI_MIN_TRY, portfoy * SERMAYE_HAREKETI_MIN_ORAN)


def _risk_baslat(kasa: "MerkeziKasa", portfoy: float, risk_kayitli: bool) -> None:
    """v20: sermaye tabani ve acil fren referansi - her acilista SIFIRLANMAZ."""
    if not risk_kayitli or _risk.yatirilan_sermaye <= 0:
        _risk.yatirilan_sermaye = portfoy if CANLI_MOD else (kasa.baslangic or portfoy)
        _risk.zirve_portfoy = portfoy
        print(f"{CYAN}  Sermaye takibi basladi: {portfoy:,.2f} TRY (bundan sonra yeniden baslatmada "
              f"sifirlanmaz).{RESET}")
    if BASLANGIC_SERMAYE_TRY > 0:
        _risk.yatirilan_sermaye = BASLANGIC_SERMAYE_TRY
    if _risk.acil_fren_tetiklendi or FREN_SIFIRLA:
        _risk.fren_sifirla(portfoy)
        print(f"{YELLOW}  {'Acil frenden sonra elle yeniden baslatildi' if not FREN_SIFIRLA else 'AURELIUS_FREN_SIFIRLA=1'}"
              f": fren referansi {portfoy:,.2f} TRY'ye cekildi.{RESET}")
    if _risk.zirve_portfoy <= 0:
        _risk.zirve_portfoy = portfoy
    if not _risk.fren_beklemede and _risk.zirveden_dusus(portfoy) >= MAX_DRAWDOWN_PCT:
        # Dusus bot kapaliyken olmus (fiyat hareketi, elle islem, para cekme...): acilir acilmaz her seyi
        # piyasa fiyatindan satmak yerine yeni alimlar durdurulur ve kullaniciya sorulur.
        _risk.fren_beklemede = True
        mesaj = (f"Portfoy ({portfoy:,.2f} TRY) kayitli en yuksek degerinden ({_risk.zirve_portfoy:,.2f} TRY) "
                 f"%{_risk.zirveden_dusus(portfoy) * 100:.1f} asagida - dusus bot kapaliyken olmus. Acil fren "
                 f"satis YAPMADI; yeni alimlar durduruldu, acik pozisyonlar stoplariyla yonetiliyor.")
        print(f"{RED}{BOLD}  {mesaj}{RESET}")
        print(f"{YELLOW}  Devam etmek icin Telegram'dan /frensifirla gonderin (veya AURELIUS_FREN_SIFIRLA=1 ile "
              f"baslatin); hepsini satmak icin /hepsinisat.{RESET}")
        send_telegram(f"\U0001F6A8 <b>Acil fren beklemede</b>\n{html.escape(mesaj)}\n"
                      "Devam: /frensifirla | Hepsini sat: /hepsinisat")
    _risk.portfoy_guncelle(portfoy)
    kasa.baslangic = _risk.yatirilan_sermaye
    pnl = portfoy - kasa.baslangic
    print(f"{CYAN}  Sermaye: baslangic {kasa.baslangic:,.2f} TRY | portfoy {portfoy:,.2f} TRY "
          f"({pnl:+,.2f} TRY) | acil fren: {_risk.zirve_portfoy:,.2f} TRY zirvesinden "
          f"%{MAX_DRAWDOWN_PCT * 100:.0f} dususte{RESET}")
    for satir in _risk.durum_satirlari(portfoy)[1:]:
        print(f"{YELLOW}  {satir}{RESET}")
    print()


def run_simulation():
    global _alim_durumu, _risk
    print_banner()

    if CANLI_MOD and not canli_mod_on_kontrol():
        print(f"{RED}Bot baslatilamadi (CANLI_MOD guvenlik kontrolu basarisiz).{RESET}")
        return CIKIS_AYAR_HATASI

    # Onceki oturumdan kalici durum var mi?
    try:
        kayitli_durum = durumu_yukle()
    except CanliDurumKorumasi as e:
        print(f"{RED}{BOLD}  {e}{RESET}")
        return CIKIS_AYAR_HATASI
    risk_kayitli = bool(kayitli_durum and isinstance(kayitli_durum.get("risk"), dict))
    _risk = RiskKorumasi.from_dict(kayitli_durum.get("risk") if kayitli_durum else None)
    _trend_durumu.clear()
    _trend_durumu.update((kayitli_durum or {}).get("trend") or {})
    if kayitli_durum:
        kasa, pozisyonlar, acik_baslangic_sayisi = durumdan_kasa_ve_pozisyonlar_olustur(kayitli_durum)
        acik_pozisyon_sayaci = [acik_baslangic_sayisi]
        rapor_verisi = kayitli_durum.get("raporlama")
        rapor = RaporlamaDurumu.from_dict(rapor_verisi, kasa.bakiye) if rapor_verisi else RaporlamaDurumu(kasa.bakiye)
        print(f"{GREEN}  Onceki oturumdan durum yuklendi: bakiye={kasa.bakiye:,.2f} TRY, "
              f"acik pozisyon={acik_baslangic_sayisi}, kaydedilme zamani="
              f"{kayitli_durum.get('kaydedilme_zamani', '?')}{RESET}")
        print(f"{GREEN}  X raporu son: {rapor.son_x_raporu_zamani.strftime('%d.%m.%Y %H:%M')} | "
              f"Z raporu son: {rapor.son_z_raporu_zamani.strftime('%d.%m.%Y %H:%M')}{RESET}\n")
        _alim_durumu = kayitli_durum.get("alim_durumu", "ACIK")
        if _alim_durumu not in ALIM_DURUMU_ACIKLAMA:
            _alim_durumu = "ACIK"
        if _alim_durumu != "ACIK":
            print(f"{YELLOW}  Yeni alimlar: {ALIM_DURUMU_ACIKLAMA[_alim_durumu]} - Telegram'dan /devam ile "
                  f"acabilirsiniz.{RESET}\n")
    else:
        kasa = MerkeziKasa(TOPLAM_SANAL_BAKIYE_TRY)
        pozisyonlar: dict = {}
        acik_pozisyon_sayaci = [0]
        rapor = RaporlamaDurumu(TOPLAM_SANAL_BAKIYE_TRY)
        if CANLI_MOD:
            print(f"{YELLOW}  Kayitli durum bulunamadi, temiz baslangic (bakiye borsadan cekilecek).{RESET}\n")
        else:
            print(f"{YELLOW}  Kayitli durum bulunamadi, temiz baslangic: {TOPLAM_SANAL_BAKIYE_TRY:,.2f} TRY{RESET}\n")

    # CANLI MOD: kasa borsadaki gercek serbest TRY bakiyesine esitlenir (bakiye 0 ise yeni alim yapilmaz;
    # okunamazsa bot baslamaz - sanal bakiyeyle gercek emir denenmesin).
    if CANLI_MOD:
        # Bot kapaliyken borsadaki stop emri dolduysa satisi ONCE kaydet; kasa hemen asagida borsadaki
        # gercek TRY bakiyesine esitlenir (cift sayim olmaz).
        for bot in pozisyonlar.values():
            if any(lvl.has_position and lvl.borsa_stop_emir_id for lvl in bot.grid):
                bot.borsa_stop_bakimi(kasa, acik_pozisyon_sayaci, rapor, None, zorla_sorgu=True, yeni_kur=False)
        onceki_serbest = kasa.bakiye
        try:
            bakiyeler = binance_hesap_bakiyeleri()
        except Exception as e:
            print(f"{RED}  HATA: Canli bakiye cekilemedi, bot baslatilamiyor: {e}{RESET}")
            return CIKIS_YENIDEN_DENE
        bakiye_ozeti_yazdir(bakiyeler)
        gercek_bakiye = bakiyeler.get("TRY", {}).get("free", 0.0)
        print(f"{GREEN}  CANLI MOD AKTIF - borsadan cekilen serbest TRY bakiyesi: {gercek_bakiye:,.2f} TRY{RESET}\n")
        kasa.bakiye = max(0.0, gercek_bakiye)
        if gercek_bakiye <= 0:
            print(f"{YELLOW}  UYARI: Borsadaki serbest TRY bakiyesi 0 - yeni alim yapilmayacak "
                  f"(acik pozisyonlar yonetilmeye devam eder).{RESET}")
        kapanan = 0
        if not kayitli_durum:
            rapor = RaporlamaDurumu(kasa.bakiye)  # X/Z tabanlari sanal degil gercek bakiyeden baslasin
        elif any(b.has_open_position for b in pozisyonlar.values()):
            acik_once = sum(1 for b in pozisyonlar.values() if b.has_open_position)
            mutabakat_yap(kasa, pozisyonlar)  # bot kapaliyken elle satilan/degisen pozisyonlari hemen yakala
            kapanan = acik_once - sum(1 for b in pozisyonlar.values() if b.has_open_position)
        fark = kasa.bakiye - onceki_serbest
        if risk_kayitli and kapanan == 0 and _sermaye_hareketi_mi(fark, v9_toplam_portfoy_degeri(kasa, pozisyonlar)):
            _risk.sermaye_hareketi(fark)
            print(f"{CYAN}  Bot kapaliyken TRY bakiyesi {fark:+,.2f} TRY degismis: para "
                  f"{'yatirma' if fark > 0 else 'cekme'} olarak kaydedildi (kar/zarar sayilmadi).{RESET}")
        send_telegram(f"\U0001F7E2 <b>Project Aurelius v22 CANLI MODDA baslatildi!</b>\n"
                      f"Borsa bakiyesi: {kasa.bakiye:,.2f} TRY"
                      f"\nYeni alimlar: {ALIM_DURUMU_ACIKLAMA[_alim_durumu]}"
                      f"\nBorsa stop emri: {'ACIK' if _borsa_stop_kullanilabilir() else 'kapali'}"
                      f"\n{trend_durum_satiri()}"
                      f"\nIslem basina risk: %{RISK_PCT * 100:g}"
                      + ("\nKomutlar icin /yardim" if TELEGRAM_KOMUTLARI_AKTIF else ""))
    else:
        send_telegram(f"\U0001F9EA Project Aurelius v22 SIMULASYON modunda baslatildi. Bakiye: {kasa.bakiye:,.2f} TRY\n"
                      + trend_durum_satiri())
    _risk_baslat(kasa, v9_toplam_portfoy_degeri(kasa, pozisyonlar), risk_kayitli)
    print(f"{CYAN}  {trend_durum_satiri()}{RESET}")
    print(f"{GRAY}  Gunluk kontrol her gun TR saatiyle ~03:{TREND_KONTROL_GECIKME_DK:02d}'te (gunluk mum "
          f"kapanisindan sonra); bot o saatte kapaliysa acilinca yapilir.{RESET}\n")

    def kaydet():
        durumu_kaydet(kasa, pozisyonlar, rapor)

    komut_kontrol: dict = {}

    def komutlari_isle():
        for komut in bekleyen_telegram_komutlari():
            print(f"[{ts()}] {CYAN}Telegram komutu: {komut}{RESET}")
            try:
                telegram_komutunu_uygula(komut, kasa, pozisyonlar, kaydet, rapor, acik_pozisyon_sayaci,
                                         komut_kontrol)
            except Exception as e:
                logger.error("Telegram komutu islenemedi (%s): %s", komut, e)
                send_telegram(f"Komut islenemedi ({html.escape(komut)}): {html.escape(str(e))}")

    komut_isleyici = komutlari_isle if telegram_komut_dinleyicisini_baslat() else None
    son_durum_bildirimi = time.monotonic()
    son_saglik_pingi = time.monotonic()
    son_performans_raporu = 0.0
    son_mutabakat = time.monotonic()
    ardisik_hata, son_hata_bildirimi = 0, -1e9
    _saglik_pingi_gonder()

    try:
        while True:
            try:
                if komut_isleyici is not None:
                    komut_isleyici()
                acik_pozisyon_sayaci[0] = sum(1 for b in pozisyonlar.values() if b.has_open_position)
                _trend_turu(kasa, pozisyonlar, acik_pozisyon_sayaci, kaydet, rapor)
                rapor.drawdown_guncelle(v9_toplam_portfoy_degeri(kasa, pozisyonlar))  # Z donemi en derin dusus
                kaydet()  # her tur sonunda genel bir guvenlik-agi kaydi

                # Acil fren: portfoyun ulastigi en yuksek degerden olan dusus (referans durum dosyasinda)
                guncel_kontrol = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
                _risk.portfoy_guncelle(guncel_kontrol)
                kayip_pct = _risk.zirveden_dusus(guncel_kontrol)
                if kayip_pct >= MAX_DRAWDOWN_PCT and not _risk.fren_beklemede:
                    print(f"\n{RED}{BOLD}{'!' * 74}{RESET}")
                    print(f"{RED}{BOLD}  ACIL FREN: Portfoy en yuksek degerinden ({_risk.zirve_portfoy:,.2f} TRY) "
                          f"%{kayip_pct*100:.2f} dustu (limit: %{MAX_DRAWDOWN_PCT*100:.0f}). "
                          f"TUM ACIK POZISYONLAR TASFIYE EDILIYOR.{RESET}")
                    print(f"{RED}{BOLD}{'!' * 74}{RESET}\n")
                    send_telegram(f"\U0001F6A8\U0001F6A8 <b>ACIL FREN DEVREYE GIRDI</b> \U0001F6A8\U0001F6A8\n"
                                  f"Portfoy en yuksek degerinden ({_risk.zirve_portfoy:,.2f} TRY) %{kayip_pct*100:.2f} "
                                  f"dustu (limit %{MAX_DRAWDOWN_PCT*100:.0f}). Tum pozisyonlar tasfiye ediliyor ve bot "
                                  f"duruyor.")
                    _risk.acil_fren_tetiklendi = True
                    for bot in pozisyonlar.values():
                        if bot.has_open_position:
                            bot.acil_tasfiye(bot.guncel_fiyat(), kasa, durum_kaydet=kaydet, rapor=rapor)
                    acik_pozisyon_sayaci[0] = sum(1 for b in pozisyonlar.values() if b.has_open_position)
                    print_trade_history_table(pozisyonlar.values())
                    print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0])
                    print(f"{RED}Bot acil fren nedeniyle durduruldu. Elle yeniden baslatirsaniz fren referansi o "
                          f"anki portfoy degerinden baslar.{RESET}")
                    return CIKIS_DUR

                simdi = time.monotonic()
                if simdi - son_performans_raporu >= PERFORMANS_RAPORU_DK * 60:
                    son_performans_raporu = simdi  # sadece konsol + portfoy kaydi; Telegram durum bildirimiyle
                    print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0], telegram_gonder=False)

                # CANLI mod bakiye mutabakati (her ~6 saat ve gunluk X raporunda)
                if simdi - son_mutabakat >= MUTABAKAT_ARALIGI_SAAT * 3600:
                    son_mutabakat = simdi
                    mutabakat_yap(kasa, pozisyonlar)
                if rapor.x_suresi_doldu_mu():
                    mutabakat_yap(kasa, pozisyonlar)
                    x_raporu_olustur_ve_gonder(kasa, pozisyonlar, rapor)
                    kaydet()
                if rapor.z_suresi_doldu_mu():
                    z_raporu_olustur_ve_gonder(kasa, pozisyonlar, rapor)
                    kaydet()

                # Periyodik "bot calisiyor" bildirimi ve dis saglik pingi
                if SAGLIK_PING_URL and simdi - son_saglik_pingi >= SAGLIK_PING_ARALIGI_SANIYE:
                    son_saglik_pingi = simdi
                    _saglik_pingi_gonder()
                if DURUM_BILDIRIM_SAAT > 0 and simdi - son_durum_bildirimi >= DURUM_BILDIRIM_SAAT * 3600:
                    son_durum_bildirimi = simdi
                    send_telegram("\U0001F493 " + durum_ozeti_metni(kasa, pozisyonlar))

                # Bosaltma modu: acik pozisyon kalmadiysa bilincli olarak dur
                if _alim_durumu == "BOSALTMA" and not any(b.has_open_position for b in pozisyonlar.values()):
                    _alim_durumu = "ACIK"  # sonraki baslatmada normal islem yapilsin
                    print(f"\n{GREEN}{BOLD}  BOSALTMA TAMAMLANDI: acik pozisyon kalmadi, bot durduruluyor.{RESET}\n")
                    send_telegram("\U0001F9F9 <b>Bosaltma tamamlandi.</b> Acik pozisyon kalmadi, bot durduruldu. "
                                  f"Nakit: {kasa.bakiye:,.2f} TRY")
                    return CIKIS_DUR
                ardisik_hata = 0
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                # v22: tek turdaki beklenmedik hata botu durdurmaz; art arda cok hata olursa durur
                # (baslatici yeniden acar).
                ardisik_hata += 1
                print(f"[{ts()}] {RED}BEKLENMEDIK HATA (tur atlandi, {ardisik_hata}/{DONGU_HATA_LIMITI}): {e}{RESET}")
                logger.exception("Ana dongude beklenmedik hata")
                if ardisik_hata >= DONGU_HATA_LIMITI:
                    raise
                if time.monotonic() - son_hata_bildirimi >= DONGU_HATA_BILDIRIM_DK * 60:
                    son_hata_bildirimi = time.monotonic()
                    send_telegram(f"\u26a0\ufe0f <b>Beklenmedik hata</b> (bot calismaya devam ediyor): "
                                  f"{html.escape(str(e))}")
            _dongu_beklemesi(komut_isleyici)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}--- Bot durduruldu (Ctrl+C) ---{RESET}\n")
        print_trade_history_table(pozisyonlar.values())
        print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0])
        acik_botlar = [b for b in pozisyonlar.values() if b.has_open_position]
        if CANLI_MOD and acik_botlar:
            korunan = [b.symbol for b in acik_botlar if any(l.borsa_stop_emir_id for l in b.grid)]
            if korunan:
                print(f"{GRAY}  Borsa stop emri olanlar bot kapaliyken de korunur: {', '.join(korunan)}{RESET}")
            if _kapanista_pozisyon_sorusu() == "S":
                satilan, kalan = tum_pozisyonlari_kapat(pozisyonlar, kasa, None, rapor,
                                                        acik_pozisyon_sayaci, "MANUEL-KAPANIS")
                print(f"{GREEN}  {satilan} pozisyon satildi.{RESET}" + (
                    f" {RED}Satilamayan: {', '.join(kalan)} - Binance TR'de kontrol edin!{RESET}" if kalan else ""))
            else:
                print(f"{YELLOW}  Pozisyonlar oldugu gibi birakildi; bot tekrar baslatilinca yonetmeye devam eder.{RESET}")
        send_telegram(f"\U0001F6D1 Project Aurelius durduruldu (Ctrl+C). Guncel bakiye: "
                      f"{v9_toplam_portfoy_degeri(kasa, pozisyonlar):,.2f} TRY"
                      + (f"\nAcik pozisyon: {sum(1 for b in pozisyonlar.values() if b.has_open_position)}"
                         if CANLI_MOD else ""))
        print(f"{YELLOW}Hatirlatma: {'Bu CANLI bir oturumdu.' if CANLI_MOD else 'Bu bir simulasyondu.'}{RESET}")
        return CIKIS_DUR
    except Exception as e:
        print(f"\n{RED}{BOLD}KRITIK HATA: {e}{RESET}\n")
        send_telegram(f"\U0001F6A8 Project Aurelius KRITIK HATA ile durdu: {html.escape(str(e))}")
        _saglik_pingi_gonder("/fail", bekle=True)
        raise
    finally:
        durumu_kaydet(kasa, pozisyonlar, rapor)
        print(f"{GRAY}  Durum kaydedildi: {STATE_DOSYASI}{RESET}")
        telegram_kuyrugunu_bosalt()


# ==========================================================================
# GECMIS MUM VERISI ve 'trend' testinin yardimcilari. Emir gondermez, API anahtari gerektirmez.
# ==========================================================================
ARALIK_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
BACKTEST_VARSAYILAN_SERMAYE = 1000.0
BACKTEST_SLIPAJ_PCT = (SLIPAJ_MIN_PCT + SLIPAJ_MAKS_PCT) / 2
_MUM_ALANLARI = ("acilis", "yuksek", "dusuk", "kapanis", "hacim", "alici_hacim")


def gecmis_mumlari_getir(symbol: str, interval: str, baslangic_ms: int, bitis_ms: int) -> Optional[dict]:
    """[baslangic_ms, bitis_ms) arasinda KAPANMIS mumlari sayfa sayfa ceker. 'zaman' = acilis (ms)."""
    adim = ARALIK_MS[interval]
    veri = {"zaman": [], **{k: [] for k in _MUM_ALANLARI}}
    bas = baslangic_ms
    while bas < bitis_ms:
        url = (KLINES_URL_TEMPLATE.format(symbol=symbol, interval=interval, limit=1000)
               + f"&startTime={bas}&endTime={bitis_ms - 1}")
        parca = http_istek_yap(urllib.request.Request(url, headers={"User-Agent": "project-aurelius-bot"}),
                               timeout=30)
        if not isinstance(parca, list) or not parca:
            break
        for m in parca:
            acilis = int(m[0])
            if acilis + adim > bitis_ms or (veri["zaman"] and acilis <= veri["zaman"][-1]):
                continue
            veri["zaman"].append(acilis)
            for i, k in enumerate(("acilis", "yuksek", "dusuk", "kapanis", "hacim"), start=1):
                veri[k].append(float(m[i]))
            veri["alici_hacim"].append(float(m[9]) if len(m) > 9 else 0.0)
        if len(parca) < 1000:
            break
        bas = int(parca[-1][0]) + adim
        time.sleep(0.1)
    return veri if veri["zaman"] else None


def _donem_degisimi(veri: Optional[dict], bas_ms: int, bitis_ms: Optional[int] = None) -> Optional[float]:
    """Test donemi basindan sonuna kapanis fiyati degisimi (%)."""
    if not veri or not veri.get("zaman"):
        return None
    i = bisect.bisect_left(veri["zaman"], bas_ms)
    j = len(veri["zaman"]) - 1 if bitis_ms is None else bisect.bisect_left(veri["zaman"], bitis_ms) - 1
    if i >= len(veri["zaman"]) or j <= i or not veri["kapanis"][i]:
        return None
    return (veri["kapanis"][j] / veri["kapanis"][i] - 1) * 100


def _tarih(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%d.%m.%Y")


def _sonuc_hucresi(s: dict) -> tuple:
    isl = s["islemler"]
    rler = [k["r_sonucu"] for k in isl if k.get("r_sonucu") is not None]
    return len(isl), _ortalama(rler), s["bitis"] - s["baslangic"]


def strateji_satirlari(sonuclar: dict, donemler: list, varyant_adlari: list, kiyas) -> list:
    """Varyant x donem sonuc tablosu (islem sayisi, islem basina R, net TL)."""
    satirlar = [f"{ad} ({_tarih(b)} - {_tarih(e)}): " + kiyas(b, e) for ad, b, e in donemler]
    satirlar.append("")
    genislik = 36
    satirlar.append(f"{'Strateji':<{genislik}}| " + " | ".join(f"{ad:<22}" for ad, _, _ in donemler) + " | TOPLAM")
    satirlar.append(f"{'':<{genislik}}| " + " | ".join(f"{'islem R/islem  net TL':<22}" for _ in donemler)
                    + " | R/islem  net TL")
    for ad in varyant_adlari:
        hucreler, toplam_islem, toplam_r, toplam_tl, hep_arti = [], 0, 0.0, 0.0, True
        for donem_adi, _, _ in donemler:
            n, r, tl = _sonuc_hucresi(sonuclar[(ad, donem_adi)])
            hucreler.append(f"{n:>5} {r:>+7.2f} {tl:>+8.1f}")
            toplam_islem += n
            toplam_r += r * n
            toplam_tl += tl
            hep_arti = hep_arti and n > 0 and r > 0
        isaret = "  <- her donemde arti" if hep_arti else ""
        satirlar.append(f"{ad:<{genislik}}| " + " | ".join(f"{h:<22}" for h in hucreler)
                        + f" | {toplam_r / max(1, toplam_islem):>+7.2f} {toplam_tl:>+8.1f}{isaret}")
    return satirlar


# ==========================================================================
# GUNLUK TREND TAKIBI - kurallar ('trend' testi ve canli calisma AYNI fonksiyonlari kullanir). Az sayida
# buyuk coin; gunluk kapanis son N gunun zirvesini kirinca ve fiyat EMA50 ustundeyken girilir; stop
# 2 x ATR, fiyat yukseldikce zirve - 3 x ATR'ye cekilir. Kismi kar alma yok (kazananlar kosar).
# ==========================================================================
TREND_VARYANTLARI = [
    # (ad, kirilim gunu, BTC filtresi, coinler (None = hepsi)) - ilk satir canli ayar
    (f"{TREND_KIRILIM_GUN} gun kirilim + BTC (canli ayar)", TREND_KIRILIM_GUN, True, None),
    ("20 gun kirilim + BTC filtresi", 20, True, None),
    ("50 gun kirilim, BTC filtresi yok", 50, False, None),
    ("20 gun kirilim, BTC filtresi yok", 20, False, None),
]


def _ema_hizali(degerler: list, periyot: int) -> list:
    """degerler ile ayni uzunlukta EMA; yeterli veri olmayan basta None."""
    seri = ema_serisi(degerler, periyot)
    return [None] * (len(degerler) - len(seri)) + seri


def _atr_serisi(yuksek: list, dusuk: list, kapanis: list, periyot: int) -> list:
    """Wilder ATR, kapanis ile ayni uzunlukta (basta None)."""
    atr, sonuc = None, [None] * len(kapanis)
    trler = []
    for i in range(1, len(kapanis)):
        tr = max(yuksek[i] - dusuk[i], abs(yuksek[i] - kapanis[i - 1]), abs(dusuk[i] - kapanis[i - 1]))
        if atr is None:
            trler.append(tr)
            if len(trler) == periyot:
                atr = sum(trler) / periyot
        else:
            atr = (atr * (periyot - 1) + tr) / periyot
        sonuc[i] = atr
    return sonuc


def trend_sinyali(v: dict, i: int, kirilim: int, ema: list, atr: list) -> Optional[tuple]:
    """i. gunun kapanisinda kirilim sinyali (test ve canli ayni kural): kapanis onceki 'kirilim' gunun en
    yuksegini asti ve EMA50 ustunde. Donus: (60 gunluk getiri - siralama icin, kapanis, ATR) veya None."""
    if i < kirilim or i >= len(v["kapanis"]):
        return None
    a, e, kap = atr[i], ema[i], v["kapanis"][i]
    if a and e and kap > e and kap > max(v["yuksek"][i - kirilim:i]):
        return kap / v["kapanis"][max(0, i - 60)] - 1, kap, a
    return None


def trend_simule_et(coin_gunluk: dict, btc_gunluk: Optional[dict], bas_ms: int, bitis_ms: int, sermaye: float,
                    kirilim: int = 20, btc_filtresi: bool = True, coinler: Optional[tuple] = None) -> dict:
    """Gunluk mumlarla trend takibi simulasyonu. Kararlar gun kapanisinda (o gune kadarki veriyle),
    stoplar ertesi gunden itibaren gecerli. Donus backtest_simule_et ile ayni bicimde."""
    gun_ms = ARALIK_MS["1d"]
    hazir = {}
    for s, v in coin_gunluk.items():
        if (coinler and s not in coinler) or not v or len(v["zaman"]) < max(TREND_EMA, kirilim) + 2:
            continue
        hazir[s] = {"v": v, "idx": {z: i for i, z in enumerate(v["zaman"])},
                    "ema": _ema_hizali(v["kapanis"], TREND_EMA),
                    "atr": _atr_serisi(v["yuksek"], v["dusuk"], v["kapanis"], TREND_ATR_PERIYOT)}
    btc_yukari = {}
    if btc_gunluk and btc_gunluk.get("zaman"):
        e = _ema_hizali(btc_gunluk["kapanis"], TREND_EMA)
        btc_yukari = {z: e[i] is not None and btc_gunluk["kapanis"][i] > e[i]
                      for i, z in enumerate(btc_gunluk["zaman"])}
    nakit, acik, islemler, son_fiyat = sermaye, {}, [], {}
    zirve, en_derin = sermaye, 0.0
    sayac = {"komisyon": 0.0, "acil_fren": False, "acik_gun": 0, "toplam_gun": 0}

    def sat(s: str, fiyat: float, etiket: str, t_ms: int) -> None:
        nonlocal nakit
        p = acik.pop(s)
        brut = p["miktar"] * fiyat * (1 - BACKTEST_SLIPAJ_PCT)
        kom = brut * KOMISYON_PCT
        nakit += brut - kom
        sayac["komisyon"] += kom
        pnl = brut - kom - p["tutar"] - p["kom"]
        islemler.append(islem_kaydi_olustur(
            s, "TEST", datetime.fromtimestamp(p["giris_ms"] / 1000), datetime.fromtimestamp(t_ms / 1000),
            p["giris"], fiyat, p["tutar"], pnl, p["miktar"] * (p["giris"] - p["ilk_stop"]),
            (p["giris"] - p["ilk_stop"]) / p["giris"], etiket, False, False, {}))

    t = bas_ms - bas_ms % gun_ms
    while t + gun_ms <= bitis_ms:
        kapanis_ms = t + gun_ms
        # 1) acik pozisyonlar: gunun dusugu stop'a degdiyse cik, degmediyse takip eden stop'u yukselt
        for s in list(acik):
            i = hazir[s]["idx"].get(t)
            if i is None:
                continue
            v, p = hazir[s]["v"], acik[s]
            son_fiyat[s] = v["kapanis"][i]
            if v["dusuk"][i] <= p["stop"]:
                sat(s, min(p["stop"], v["acilis"][i]),
                    "TRAILING-STOP" if p["stop"] > p["giris"] else "STOP-LOSS", kapanis_ms)
                continue
            p["zirve"] = max(p["zirve"], v["yuksek"][i])
            atr = hazir[s]["atr"][i]
            if atr:
                p["stop"] = max(p["stop"], p["zirve"] - TREND_TAKIP_ATR * atr)
        for s, h in hazir.items():
            i = h["idx"].get(t)
            if i is not None:
                son_fiyat[s] = h["v"]["kapanis"][i]
        # 2) portfoy ve acil fren
        deger = nakit + sum(p["miktar"] * son_fiyat[s] for s, p in acik.items())
        sayac["toplam_gun"] += 1
        sayac["acik_gun"] += bool(acik)
        zirve = max(zirve, deger)
        en_derin = max(en_derin, (zirve - deger) / zirve if zirve > 0 else 0.0)
        if zirve > 0 and (zirve - deger) / zirve >= MAX_DRAWDOWN_PCT:
            for s in list(acik):
                sat(s, son_fiyat[s], "ACIL-TASFIYE", kapanis_ms)
            sayac["acil_fren"] = True
            break
        # 3) yeni girisler (gun kapanisinda)
        bos = TREND_MAKS_POZISYON - len(acik)
        if bos > 0 and (not btc_filtresi or btc_yukari.get(t, False)):
            adaylar = []
            for s, h in hazir.items():
                i = h["idx"].get(t)
                if s in acik or i is None or i < kirilim:
                    continue
                sinyal = trend_sinyali(h["v"], i, kirilim, h["ema"], h["atr"])
                if sinyal:
                    adaylar.append((sinyal[0], s, sinyal[1], sinyal[2]))
            for _, s, kap, atr in sorted(adaylar, reverse=True)[:bos]:
                giris = kap * (1 + BACKTEST_SLIPAJ_PCT)
                stop = giris - TREND_ILK_STOP_ATR * atr
                stop_pct = (giris - stop) / giris
                if not (0 < stop_pct < 0.5):
                    continue
                risk_tutari = deger * RISK_PCT / stop_pct if RISK_PCT > 0 else deger
                tutar = min(risk_tutari, deger / TREND_MAKS_POZISYON, nakit / (1 + KOMISYON_PCT))
                if tutar < MIN_POZISYON_TUTARI_TRY:
                    continue
                kom = tutar * KOMISYON_PCT
                nakit -= tutar + kom
                sayac["komisyon"] += kom
                acik[s] = {"giris": giris, "miktar": tutar / giris, "tutar": tutar, "kom": kom, "stop": stop,
                           "ilk_stop": stop, "zirve": giris, "giris_ms": kapanis_ms}
        t += gun_ms
    for s in list(acik):
        sat(s, son_fiyat[s], "TEST-SONU", min(t, bitis_ms))
    return {"baslangic": sermaye, "bitis": nakit, "islemler": islemler, "en_derin_dusus": en_derin,
            "sayac": sayac}


# ==========================================================================
# GUNLUK TREND TAKIBI - CANLI / SIMULASYON CALISMA
# Gunluk mum kapanisindan (00:00 UTC = TR 03:00) sonra GUNDE BIR KEZ: acik trend pozisyonlarinin stop'u
# yukseltilir, sinyal veren coinlere (en fazla TREND_MAKS_POZISYON) islem basina RISK_PCT riskle girilir.
# Gun icinde her turda sadece stop kontrol edilir. Kurallar 'trend' testindekiyle ayni (trend_sinyali).
# ==========================================================================
def _gunluk_mumlar(sembol: str, bugun_ms: int, gun: int) -> Optional[dict]:
    """Bugune kadar KAPANMIS son 'gun' gunluk mum; son mum dun kapanmis olmali (yoksa None)."""
    v = gecmis_mumlari_getir(sembol, "1d", bugun_ms - gun * ARALIK_MS["1d"], bugun_ms)
    if not v or v["zaman"][-1] != bugun_ms - ARALIK_MS["1d"]:
        return None
    return v


def trend_gunluk_kontrol(kasa: "MerkeziKasa", pozisyonlar: dict, acik_pozisyon_sayaci: list,
                         durum_kaydet, rapor, simdi_ms: Optional[int] = None) -> bool:
    """Gunluk kontrolu (gunde bir kez) yapar. Yapildiysa True; zamani gelmediyse/veri yoksa False
    (sonraki turda tekrar denenir)."""
    gun_ms = ARALIK_MS["1d"]
    simdi_ms = simdi_ms or int(time.time() * 1000)
    bugun = simdi_ms // gun_ms * gun_ms
    if _trend_durumu.get("son_gun") == bugun or simdi_ms - bugun < TREND_KONTROL_GECIKME_DK * 60_000:
        return False
    # v21.1: eksik veride (borsa/ag sorunu) gun hemen "yapildi" sayilmaz; 10 dk arayla tekrar denenir
    if simdi_ms - _trend_durumu.get("son_deneme_ms", 0) < TREND_VERI_TEKRAR_DK * 60_000:
        return False
    if _trend_durumu.get("ilk_deneme_ms", 0) < bugun:
        _trend_durumu["ilk_deneme_ms"] = simdi_ms
    tekrar_suresi_var = simdi_ms - _trend_durumu["ilk_deneme_ms"] < TREND_VERI_TEKRAR_SAAT * 3_600_000
    gerekli = TREND_GUNLUK_MUM  # ATR/EMA testteki gibi uzun gecmisle hesaplansin
    acik_trend = [s for s, b in pozisyonlar.items()
                  if b.has_open_position and any(l.has_position and l.trend_stop > 0 for l in b.grid)]
    gunluk = {}
    for s in dict.fromkeys(list(TREND_COINLERI) + acik_trend):
        try:
            v = _gunluk_mumlar(s, bugun, gerekli)
        except Exception as e:
            logger.warning("Trend: %s gunluk mumlari alinamadi: %s", s, e)
            continue
        if v:
            gunluk[s] = v
        time.sleep(API_CALL_SLEEP_SECONDS)
    if not gunluk:
        _trend_durumu["son_deneme_ms"] = simdi_ms
        print(f"[{ts()}] {YELLOW}Trend kontrolu: gunluk mumlar alinamadi, {TREND_VERI_TEKRAR_DK} dk sonra "
              f"tekrar denenecek.{RESET}")
        return False
    btc_yukari = None
    try:
        btc = _gunluk_mumlar("BTCUSDT", bugun, gerekli) or gunluk.get("BTCTRY")
        if btc:
            ema_btc = _ema_hizali(btc["kapanis"], TREND_EMA)[-1]
            btc_yukari = ema_btc is not None and btc["kapanis"][-1] > ema_btc
    except Exception as e:
        logger.warning("Trend: BTC gunluk verisi alinamadi: %s", e)
    eksik = [s[:-3] for s in dict.fromkeys(list(TREND_COINLERI) + acik_trend) if s not in gunluk]
    if TREND_BTC_FILTRESI and btc_yukari is None:
        eksik.append("BTC filtresi")
    satirlar = []
    if eksik:
        if tekrar_suresi_var:
            _trend_durumu["son_deneme_ms"] = simdi_ms
            print(f"[{ts()}] {YELLOW}Trend kontrolu: {', '.join(eksik)} verisi alinamadi, {TREND_VERI_TEKRAR_DK} dk "
                  f"sonra tekrar denenecek.{RESET}")
            return False
        satirlar.append(f"Verisi alinamayan: {', '.join(eksik)} (bugun bunlar icin islem yapilmadi)")

    # 1) acik trend pozisyonlarinin stop'unu yukselt (zirve - 3 x ATR; asla asagi inmez)
    for s in acik_trend:
        v, bot = gunluk.get(s), pozisyonlar[s]
        if not v:
            continue
        atr = _atr_serisi(v["yuksek"], v["dusuk"], v["kapanis"], TREND_ATR_PERIYOT)[-1]
        giris_ms = bot.alis_zamani.timestamp() * 1000 if bot.alis_zamani else 0
        for lvl in bot.grid:
            if not (lvl.has_position and lvl.trend_stop > 0):
                continue
            lvl.en_yuksek_fiyat = max([lvl.en_yuksek_fiyat] + [y for z, y in zip(v["zaman"], v["yuksek"])
                                                               if z + gun_ms > giris_ms])
            eski = lvl.trend_stop
            if atr:
                lvl.trend_stop = max(lvl.trend_stop, lvl.en_yuksek_fiyat - TREND_TAKIP_ATR * atr)
            fiyat = bot.guncel_fiyat()
            satirlar.append(f"{s}: stop {format_fiyat(lvl.trend_stop)}"
                            + (" (yukseltildi)" if lvl.trend_stop > eski else "")
                            + (f", su an %{(fiyat / lvl.buy_price - 1) * 100:+.1f}" if fiyat and lvl.buy_price else ""))

    # 2) yeni girisler
    acik_sayi = sum(1 for b in pozisyonlar.values() if b.has_open_position)
    bos = TREND_MAKS_POZISYON - acik_sayi
    engel = None
    if _alim_durumu != "ACIK":
        engel = f"yeni alimlar {ALIM_DURUMU_ACIKLAMA.get(_alim_durumu, _alim_durumu)}"
    elif _risk.fren_beklemede:
        engel = "acil fren beklemede (/frensifirla)"
    elif TREND_BTC_FILTRESI and not btc_yukari:
        engel = "BTC gunluk trendi asagi (EMA50 altinda)" if btc_yukari is False else "BTC verisi alinamadi"
    elif bos <= 0:
        engel = f"pozisyon siniri dolu ({TREND_MAKS_POZISYON})"
    alinanlar = []
    if not engel:
        adaylar = []
        for s, v in gunluk.items():
            if s not in TREND_COINLERI or (s in pozisyonlar and pozisyonlar[s].has_open_position):
                continue
            sinyal = trend_sinyali(v, len(v["kapanis"]) - 1, TREND_KIRILIM_GUN, _ema_hizali(v["kapanis"], TREND_EMA),
                                   _atr_serisi(v["yuksek"], v["dusuk"], v["kapanis"], TREND_ATR_PERIYOT))
            if sinyal:
                adaylar.append((sinyal[0], s, sinyal[1], sinyal[2]))
        portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
        for _, s, kapanis, atr in sorted(adaylar, reverse=True)[:bos]:
            try:
                fiyat = get_last_price(s)
            except Exception as e:
                satirlar.append(f"{s}: sinyal var ama fiyat alinamadi ({e})")
                continue
            if fiyat > kapanis + TREND_KOVALAMA_ATR * atr:
                satirlar.append(f"{s}: sinyal var ama fiyat kapanistan cok uzaklasti, kovalanmadi")
                continue
            spread_pct, _, _ = orderbook_spread_kontrol(s)
            if spread_pct is not None and spread_pct > MAX_SPREAD_PCT:
                satirlar.append(f"{s}: sinyal var ama spread genis (%{spread_pct:.2f}), alinmadi")
                continue
            stop_pct = TREND_ILK_STOP_ATR * atr / fiyat
            if not (0 < stop_pct < 0.5):
                continue
            risk_tutari = portfoy * RISK_PCT / stop_pct if RISK_PCT > 0 else portfoy
            tutar = min(risk_tutari, portfoy / TREND_MAKS_POZISYON, kasa.bakiye / (1 + KOMISYON_PCT))
            if tutar < MIN_POZISYON_TUTARI_TRY:
                satirlar.append(f"{s}: sinyal var ama ayrilabilecek tutar cok kucuk ({tutar:,.2f} TRY)")
                continue
            bot = pozisyonlar.get(s)
            if bot is None:
                bot = pozisyonlar[s] = CoinBot(symbol=s, coin_name=_coin_adi(s))
            if bot.trend_girisi(fiyat, tutar, stop_pct, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet,
                                portfoy, btc_yukari):
                alinanlar.append(s)
        if not adaylar:
            satirlar.append(f"Yeni sinyal yok ({TREND_KIRILIM_GUN} gunluk zirveyi kiran coin yok).")
    yakin = [y for y in trend_yakinlik(gunluk) if y[0] not in pozisyonlar or not pozisyonlar[y[0]].has_open_position]
    if yakin and not alinanlar:
        satirlar.append("Zirveye en yakin: " + ", ".join(f"{s[:-3]} %{max(0.0, u):.1f}" for s, _, _, u, _ in yakin[:3])
                        + " (ayrinti: /trend)")
    _trend_durumu["son_gun"] = bugun
    _trend_durumu["son_kontrol"] = datetime.now().isoformat(timespec="minutes")
    _trend_durumu["btc_yukari"] = btc_yukari
    durum_kaydet()
    baslik = (f"BTC: {'yukselis trendinde (EMA50 ustu)' if btc_yukari else 'EMA50 altinda' if btc_yukari is False else 'bilinmiyor'}"
              + (f" | yeni alim yok: {engel}" if engel else "")
              + (f" | alinan: {', '.join(alinanlar)}" if alinanlar else ""))
    print(f"[{ts()}] {CYAN}GUNLUK TREND KONTROLU - {baslik}{RESET}")
    for satir in satirlar:
        print(f"    {satir}")
    send_telegram("\U0001F4C5 <b>Gunluk trend kontrolu</b>\n" + html.escape(baslik)
                  + "".join(f"\n- {html.escape(x)}" for x in satirlar))
    son_haftalik = _trend_durumu.get("son_haftalik", 0)
    if son_haftalik != bugun and (time.gmtime(bugun / 1000).tm_wday == 0
                                  or (son_haftalik and bugun - son_haftalik >= 7 * gun_ms)):
        send_telegram(haftalik_ozet_metni(kasa, pozisyonlar))
        _trend_durumu["son_haftalik"] = bugun
        _trend_durumu["hafta_portfoy"] = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
        durum_kaydet()
    return True


def haftalik_ozet_metni(kasa: "MerkeziKasa", pozisyonlar: dict) -> str:
    """v21.1: her pazartesi (gunluk kontrolden sonra) ve /hafta ile gonderilen haftalik ozet."""
    portfoy = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    onceki = _trend_durumu.get("hafta_portfoy")
    satirlar = [f"Portfoy: {portfoy:,.2f} TRY | Nakit: {kasa.bakiye:,.2f} TRY"]
    if onceki:
        satirlar.append(f"Son ozetten bu yana: {portfoy - onceki:+,.2f} TRY (%{(portfoy / onceki - 1) * 100:+.1f})")
    if kasa.baslangic:
        satirlar.append(f"Baslangictan bu yana ({kasa.baslangic:,.2f} TRY): {portfoy - kasa.baslangic:+,.2f} TRY "
                        f"(%{(portfoy / kasa.baslangic - 1) * 100:+.1f})")
    kayitlar = islem_gunlugunu_oku(gun=7)
    satirlar.append("")
    satirlar += (["Son 7 gun:"] + islem_ozeti_satirlari(kayitlar)[:3]) if kayitlar else ["Son 7 gunde kapanan islem yok."]
    acik = [b for b in pozisyonlar.values() if b.has_open_position]
    satirlar.append("")
    satirlar.append(f"Acik pozisyon: {len(acik)}" + ("" if acik else " (sinyal bekleniyor, /trend)"))
    for b in acik:
        seviye = next((lvl for lvl in b.grid if lvl.has_position), None)
        if seviye is None or not seviye.buy_price:
            continue
        fiyat = b.guncel_fiyat()
        stop, _ = b._ratchet_stop_hesapla(seviye)
        satirlar.append(f"- {b.symbol[:-3]}: %{(fiyat / seviye.buy_price - 1) * 100:+.1f}, stop {format_fiyat(stop)}"
                        + (" (giris ustunde, zarar ihtimali yok)" if stop > seviye.buy_price * (1 + 2 * KOMISYON_PCT)
                           else f" (stop olursa %{(stop / seviye.buy_price - 1) * 100:+.1f})")
                        + (", borsada stop emri var" if seviye.borsa_stop_emir_id else ""))
    if BORSA_STOP_AKTIF and _trend_durumu.get("borsa_stop_kapali"):
        satirlar.append(f"UYARI: borsa stop emri kapali ({_trend_durumu['borsa_stop_kapali']})")
    return "\U0001F4CA <b>Haftalik ozet</b>\n<pre>" + html.escape("\n".join(satirlar)) + "</pre>"


def trend_yakinlik(gunluk: dict, fiyatlar: Optional[dict] = None) -> list:
    """Her coin icin alim sinyaline uzaklik: (sembol, zirve_seviyesi, fiyat, uzaklik_pct, ema50_ustu).
    Sinyal icin bir sonraki gunluk kapanis son TREND_KIRILIM_GUN gunun en yuksegini gecmeli. Yakindan uzaga."""
    sonuc = []
    for s, v in gunluk.items():
        if s not in TREND_COINLERI or not v or len(v["kapanis"]) < max(TREND_EMA, TREND_KIRILIM_GUN) + 1:
            continue
        seviye = max(v["yuksek"][-TREND_KIRILIM_GUN:])
        ema = _ema_hizali(v["kapanis"], TREND_EMA)[-1]
        fiyat = (fiyatlar or {}).get(s) or v["kapanis"][-1]
        sonuc.append((s, seviye, fiyat, (seviye / fiyat - 1) * 100, ema is not None and fiyat > ema))
    return sorted(sonuc, key=lambda x: x[3])


def trend_durumu_satirlari(pozisyonlar: Optional[dict] = None) -> list:
    """/trend: BTC filtresi ve her coinin 50 gunluk zirveye (alim sinyaline) uzakligi."""
    gun_ms = ARALIK_MS["1d"]
    bugun = int(time.time() * 1000) // gun_ms * gun_ms
    gunluk, fiyatlar = {}, {}
    for s in TREND_COINLERI:
        try:
            v = _gunluk_mumlar(s, bugun, TREND_GUNLUK_MUM)
            if v:
                gunluk[s] = v
                fiyatlar[s] = get_last_price(s)
        except Exception as e:
            logger.warning("/trend: %s verisi alinamadi: %s", s, e)
    btc_yukari = None
    try:
        btc = _gunluk_mumlar("BTCUSDT", bugun, TREND_GUNLUK_MUM)
        if btc:
            ema_btc = _ema_hizali(btc["kapanis"], TREND_EMA)[-1]
            btc_yukari = ema_btc is not None and btc["kapanis"][-1] > ema_btc
    except Exception as e:
        logger.warning("/trend: BTC verisi alinamadi: %s", e)
    satirlar = [
        "BTC filtresi: " + ("EMA50 ustunde - alim serbest" if btc_yukari else
                            "EMA50 altinda - yeni alim yok" if btc_yukari is False else "veri alinamadi"),
        f"Alim sarti: gunluk kapanis son {TREND_KIRILIM_GUN} gunun zirvesini gecmeli (kontrol her gun ~03:05)",
        "",
    ]
    for s, seviye, fiyat, uzaklik, ema_ustu in trend_yakinlik(gunluk, fiyatlar):
        coin = s[:-3]
        bot = (pozisyonlar or {}).get(s)
        if bot is not None and bot.has_open_position:
            _, stop, _ = bot.acik_hedef_ve_stop()
            satirlar.append(f"{coin:<5} POZISYONDA, stop {format_fiyat(stop)}")
        elif uzaklik <= 0:
            satirlar.append(f"{coin:<5} zirvenin %{-uzaklik:.1f} USTUNDE - kapanis boyle kalirsa sinyal"
                            + ("" if ema_ustu else " (ama EMA50 altinda)"))
        else:
            satirlar.append(f"{coin:<5} zirveye %{uzaklik:.1f} kaldi ({format_fiyat(seviye)} TRY)"
                            + ("" if ema_ustu else ", EMA50 altinda"))
    if not gunluk:
        satirlar.append("Coin verileri alinamadi, biraz sonra tekrar deneyin.")
    return satirlar


def _trend_turu(kasa: "MerkeziKasa", pozisyonlar: dict, acik_pozisyon_sayaci: list, kaydet, rapor) -> None:
    """Trend modunda bir tur: gerekiyorsa gunluk kontrol, sonra acik pozisyonlarin stop kontrolu."""
    try:
        trend_gunluk_kontrol(kasa, pozisyonlar, acik_pozisyon_sayaci, kaydet, rapor)
    except Exception as e:
        print(f"[{ts()}] {RED}Gunluk trend kontrolu yapilamadi (sonraki turda tekrar): {e}{RESET}")
        logger.error("Gunluk trend kontrolu hatasi: %s", e)
    for sym, bot in list(pozisyonlar.items()):
        if not bot.has_open_position:
            continue
        try:
            fiyat = get_last_price(sym)
        except Exception as e:
            print(f"[{ts()}] {MAGENTA}{sym:<9}{RESET} {RED}gercek fiyat alinamadi: {e}{RESET}")
            continue
        bot.last_real_price = fiyat
        try:  # v22: bir pozisyondaki beklenmedik hata digerlerinin stop kontrolunu engellemesin
            bot.stop_loss_kontrol(fiyat, sim=not CANLI_MOD, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                  durum_kaydet=kaydet, rapor=rapor)
            bot.borsa_stop_bakimi(kasa, acik_pozisyon_sayaci, rapor, kaydet)
        except Exception as e:
            print(f"[{ts()}] {MAGENTA}{sym:<9}{RESET} {RED}pozisyon kontrolunde hata: {e}{RESET}")
            logger.exception("%s pozisyon kontrolunde hata", sym)
        time.sleep(API_CALL_SLEEP_SECONDS)


def btc_durum_satirlari() -> list:
    """/btc: BTC (USDT) gunluk kapanisi EMA50'ye gore - yeni alimlarin on sarti (BTC filtresi)."""
    gun_ms = ARALIK_MS["1d"]
    bugun = int(time.time() * 1000) // gun_ms * gun_ms
    try:
        v = _gunluk_mumlar("BTCUSDT", bugun, TREND_GUNLUK_MUM)
    except Exception as e:
        return [f"BTC verisi alinamadi: {e}"]
    if not v:
        return ["BTC verisi alinamadi, biraz sonra tekrar deneyin."]
    ema = _ema_hizali(v["kapanis"], TREND_EMA)[-1]
    kapanis = v["kapanis"][-1]
    if ema is None:
        return ["BTC EMA50 hesaplanamadi (yetersiz veri)."]
    fark = (kapanis / ema - 1) * 100
    satirlar = [f"BTC (USDT) dunku gunluk kapanis: {kapanis:,.0f} | EMA{TREND_EMA}: {ema:,.0f} ({fark:+.1f}%)",
                "BTC filtresi: " + ("EMA50 USTUNDE - yeni alimlar serbest" if kapanis > ema
                                    else "EMA50 ALTINDA - yeni alim yapilmaz (acik pozisyonlar stoplariyla devam)")]
    if not TREND_BTC_FILTRESI:
        satirlar.append("(BTC filtresi AURELIUS_TREND_BTC_FILTRE=0 ile kapali - alimlari etkilemiyor)")
    satirlar.append("Coinlerin alim sinyaline uzakligi icin /trend")
    return satirlar


def trend_durum_satiri() -> str:
    btc = _trend_durumu.get("btc_yukari")
    return (f"Strateji: TREND ({TREND_KIRILIM_GUN} gun kirilim"
            + (", BTC filtresi" if TREND_BTC_FILTRESI else "") + f", en fazla {TREND_MAKS_POZISYON} pozisyon)"
            + f" | son gunluk kontrol: {(_trend_durumu.get('son_kontrol') or 'henuz yok').replace('T', ' ')}"
            + (f" | BTC {'yukari' if btc else 'asagi'}" if btc is not None else ""))


def trend_kiyasi(coin_gunluk: dict, bas_ms: int, bitis_ms: int) -> str:
    """Ayni donemde al-tut: BTC ve tum coinler esit agirlikli."""
    btc = _donem_degisimi(coin_gunluk.get("BTCTRY"), bas_ms, bitis_ms)
    hepsi = [d for d in (_donem_degisimi(v, bas_ms, bitis_ms) for v in coin_gunluk.values()) if d is not None]
    return ((f"BTC al-tut %{btc:+.1f}, " if btc is not None else "")
            + f"coinlerin hepsini al-tut %{_ortalama(hepsi):+.1f}")


def trend_komutu(argumanlar: list) -> int:
    """'trend [DONEM_GUN] [SERMAYE]': gunluk trend takibini ardisik 4 donemde (varsayilan 4 x 180 gun = 2 yil)
    TREND_VARYANTLARI ile test eder."""
    sayilar = []
    for a in argumanlar:
        try:
            sayilar.append(float(a.replace(",", ".")))
        except ValueError:
            pass
    donem_gun = int(_aralikta(sayilar[0], 60, 365)) if sayilar else 180
    sermaye = sayilar[1] if len(sayilar) > 1 and sayilar[1] > 0 else BACKTEST_VARSAYILAN_SERMAYE
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS v22 - GUNLUK TREND TAKIBI TESTI'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    gun_ms = ARALIK_MS["1d"]
    son_ms = int(time.time() * 1000) // gun_ms * gun_ms
    sinirlar = [son_ms - k * donem_gun * gun_ms for k in (4, 3, 2, 1, 0)]
    donemler = [(f"{i}. donem", sinirlar[i - 1], sinirlar[i]) for i in (1, 2, 3, 4)]
    print(f"  {_tarih(sinirlar[0])} - {_tarih(son_ms)}: 4 donem x {donem_gun} gun, {sermaye:,.0f} TL sanal sermaye, "
          f"islem basina risk %{RISK_PCT * 100:g}, en fazla {TREND_MAKS_POZISYON} pozisyon.")
    print(f"  Coinler: {', '.join(c[:-3] for c in TREND_COINLERI)}. Emir gonderilmez.\n")
    isinma = (max(TREND_EMA, 50) + 30) * gun_ms
    coin_gunluk = {}
    for n, s in enumerate(TREND_COINLERI, start=1):
        print(f"  [{n}/{len(TREND_COINLERI)}] {s} gunluk mumlari indiriliyor...", flush=True)
        try:
            v = gecmis_mumlari_getir(s, "1d", sinirlar[0] - isinma, son_ms)
        except Exception as e:
            print(f"{YELLOW}    {s} atlandi ({e}){RESET}")
            continue
        if v:
            coin_gunluk[s] = v
    try:
        btc_gunluk = gecmis_mumlari_getir("BTCUSDT", "1d", sinirlar[0] - isinma, son_ms)
    except Exception:
        btc_gunluk = coin_gunluk.get("BTCTRY")
    if not coin_gunluk:
        print(f"{RED}Hicbir coin icin gecmis veri alinamadi (internet / Binance TR erisimini kontrol edin).{RESET}")
        return CIKIS_DUR
    sonuclar = {}
    for ad, kirilim, btc_filtresi, coinler in TREND_VARYANTLARI:
        for donem_adi, b, e in donemler:
            sonuclar[(ad, donem_adi)] = trend_simule_et(coin_gunluk, btc_gunluk, b, e, sermaye, kirilim,
                                                        btc_filtresi, coinler)
    tum = {ad: trend_simule_et(coin_gunluk, btc_gunluk, sinirlar[0], son_ms, sermaye, k, f, c)
           for ad, k, f, c in TREND_VARYANTLARI}
    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}  SONUC ({len(coin_gunluk)} coin){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    for satir in strateji_satirlari(sonuclar, donemler, [v[0] for v in TREND_VARYANTLARI],
                                    lambda b, e: trend_kiyasi(coin_gunluk, b, e)):
        print(f"  {satir}")
    print()
    print(f"  Tum {4 * donem_gun} gun boyunca kesintisiz ({sermaye:,.0f} TL ile):  "
          + trend_kiyasi(coin_gunluk, sinirlar[0], son_ms))
    for ad, _, _, _ in TREND_VARYANTLARI:
        s = tum[ad]
        print(f"    {ad:<36}: {s['bitis']:>10,.2f} TL ({(s['bitis'] / sermaye - 1) * 100:+.1f}%), "
              f"en derin dusus %{s['en_derin_dusus'] * 100:.1f}, {len(s['islemler'])} islem"
              + (" - ACIL FREN" if s["sayac"]["acil_fren"] else ""))
    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{GRAY}  Varsayimlar: gunluk mumlar; giris gun kapanisinda, stop ertesi gunden itibaren; komisyon "
          f"%{KOMISYON_PCT * 100:g} + kayma %{BACKTEST_SLIPAJ_PCT * 100:.3g} her alim/satimda.{RESET}")
    print(f"{GRAY}  Al-tut kiyasi risk sinirsizdir (tum para coinde); bot ise islem basina %{RISK_PCT * 100:g} risk "
          f"alir, dususu cok daha kucuk olmalidir.{RESET}")
    print(f"{YELLOW}  Gecmis sonuc gelecegi garanti etmez.{RESET}\n")
    return CIKIS_DUR


def rapor_komutu() -> int:
    """'rapor': islem gunlugunun tum zamanlar ve son 30 gun ozeti."""
    tumu = islem_gunlugunu_oku()
    print(f"{BOLD}ISLEM GUNLUGU OZETI{RESET} ({ISLEM_GUNLUGU_CSV})\n")
    for baslik, kayitlar in (("Tum zamanlar", tumu), ("Son 30 gun", islem_gunlugunu_oku(gun=30))):
        print(f"{BOLD}{baslik}{RESET}")
        for satir in islem_ozeti_satirlari(kayitlar):
            print(f"  {satir}")
        print()
    return CIKIS_DUR


def main():
    komut = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    try:
        if komut == "rapor":
            kod = rapor_komutu()
        elif komut == "trend":
            kod = trend_komutu(sys.argv[2:])
        elif komut == "baglanti":
            baglanti_testi()
            kod = CIKIS_DUR
        elif komut == "kurulum":
            kod = baslatici_olustur()
        elif komut in ("backtest", "karsilastir", "strateji", "analiz"):
            print(f"'{komut}' komutu v22'de kaldirildi (eski kisa vadeli stratejiye aitti). Stratejiyi test "
                  f"etmek icin: python {os.path.basename(__file__)} trend 270")
            kod = CIKIS_AYAR_HATASI
        else:
            kod = run_simulation()
    except KeyboardInterrupt:
        kod = CIKIS_DUR  # baslangic sirasinda Ctrl+C: baslatici yeniden baslatmasin
    # v18: cikis kodu baslaticiya (baslat.bat/.sh) yeniden baslatip baslatmayacagini soyler
    sys.exit(kod if isinstance(kod, int) else CIKIS_DUR)


if __name__ == "__main__":
    main()
