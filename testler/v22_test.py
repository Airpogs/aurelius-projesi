# Calistirmak icin: bash testler/calistir.sh
"""v22 testleri (v21.1 testleri v22 API'sine uyarlandi + v22 duzeltmeleri): borsa stop (trend), dogrulama/kapatma, eksik veride tekrar, haftalik ozet, uctan uca trend."""
import importlib, os, sys, time, tempfile, traceback

sonuc = []


def test(ad):
    def sar(f):
        try:
            f()
            sonuc.append((ad, True, ""))
        except Exception:
            sonuc.append((ad, False, traceback.format_exc()))
        return f
    return sar


def yukle(**env):
    for k in ("AURELIUS_BORSA_STOP", "AURELIUS_STRATEJI", "AURELIUS_CANLI_MOD", "TELEGRAM_BOT_TOKEN"):
        os.environ.pop(k, None)
    os.environ.update(env)
    sys.modules.pop("bot", None)
    import bot
    bot.send_telegram = lambda m: MESAJLAR.append(m)
    bot.API_CALL_SLEEP_SECONDS = 0
    bot.time.sleep = lambda s: None
    bot.orderbook_spread_kontrol = lambda s: (None, None, None)  # varsayilan: defter okunamadi
    for f in (bot.ISLEM_GUNLUGU_CSV, bot.STATE_DOSYASI):
        if os.path.exists(f):
            os.remove(f)
    return bot


MESAJLAR = []
GUN = 86_400_000


def gunluk(n, bitis_gun_ms, bas=100.0, egim=0.0, son_sicrama=0.0, oynaklik=0.02):
    """bitis_gun_ms'den onceki n kapanmis gunluk mum (son mum dun)."""
    v = {"zaman": [], "acilis": [], "yuksek": [], "dusuk": [], "kapanis": [], "hacim": [], "alici_hacim": []}
    f = bas
    for i in range(n):
        z = bitis_gun_ms - (n - i) * GUN
        f = f * (1 + egim)
        k = f * (1 + son_sicrama) if i == n - 1 else f
        v["zaman"].append(z); v["acilis"].append(f); v["kapanis"].append(k)
        v["yuksek"].append(max(f, k) * (1 + oynaklik)); v["dusuk"].append(min(f, k) * (1 - oynaklik))
        v["hacim"].append(1000.0); v["alici_hacim"].append(500.0)
    return v


# ---------------------------------------------------------------- ayarlar
@test("A1 borsa stop varsayilan acik")
def _():
    b = yukle()
    assert b.BORSA_STOP_AKTIF


@test("A2 AURELIUS_BORSA_STOP=0 kapatir, =1 acik")
def _():
    b = yukle(AURELIUS_BORSA_STOP="0")
    assert not b.BORSA_STOP_AKTIF
    b = yukle(AURELIUS_BORSA_STOP="1")
    assert b.BORSA_STOP_AKTIF


@test("A3 eski strateji ayari/komutlari yok, AURELIUS_STRATEJI=KISA etkisiz")
def _():
    b = yukle(AURELIUS_STRATEJI="KISA")
    assert b.BORSA_STOP_AKTIF and b.STRATEJI == "TREND"
    for ad in ("TREND_MODU", "evaluate_v9", "coin_derin_analiz", "backtest_komutu", "dinamik_pozisyon_planla"):
        assert not hasattr(b, ad), ad


# ---------------------------------------------------------------- borsa stop
def trend_pozisyonu(b, fiyat=10.0, stop=9.0, qty=7.0):
    bot = b.CoinBot(symbol="ADATRY", coin_name="ADA")
    bot.grid = [b.GridLevel(price=fiyat, has_position=True, buy_qty=qty, buy_price=fiyat, en_yuksek_fiyat=fiyat,
                            risk_birimi=fiyat - stop, ilk_stop=stop, trend_stop=stop)]
    bot.coin_qty = qty
    bot.last_real_price = fiyat
    bot.alis_zamani = b.datetime.now() - b.timedelta(hours=1)
    bot.starting_try = fiyat * qty
    return bot


def canli_hazirla(b, sorgu, iptal=None):
    b.CANLI_MOD = True
    b._trend_durumu.clear()
    cagri = {"kur": [], "sorgu": 0, "iptal": 0}
    b.sembol_filtrelerini_getir = lambda s: {"order_types": ["LIMIT", "MARKET", "STOP_LOSS_LIMIT"],
                                             "step_size": 0.1, "tick_size": 0.0001, "min_notional": 10}
    b.binance_hesap_bakiyeleri = lambda: {"ADA": {"free": 7.0, "locked": 0.0}, "TRY": {"free": 500.0, "locked": 0}}

    def kur(sym, q, tetik, limit):
        cagri["kur"].append((sym, q, tetik, limit))
        return "E1"

    def sorgula(eid):
        cagri["sorgu"] += 1
        return sorgu() if callable(sorgu) else sorgu

    def iptal_et(eid):
        cagri["iptal"] += 1
        return iptal or {"status": 3, "executedQty": 0.0, "executedPrice": 0.0}
    b.binance_stop_limit_satis_emri = kur
    b.binance_emir_sorgula = sorgula
    b.binance_emir_iptal = iptal_et
    return cagri


@test("B1 normal kurulum: tetik stop-%1, trendde limit tetik-%3, emir kaydedilir")
def _():
    b = yukle()
    c = canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4})
    bot = trend_pozisyonu(b)
    MESAJLAR.clear()
    assert bot.borsa_stopunu_kur(bot.grid[0]) is True
    _, q, tetik, limit = c["kur"][0]
    assert abs(tetik - 8.91) < 1e-6, tetik
    assert abs(limit - 8.91 * 0.97) < 1e-3, limit
    assert bot.grid[0].borsa_stop_emir_id == "E1"
    assert not b._trend_durumu.get("borsa_stop_kapali")
    assert any("borsa stop emri kuruldu" in m for m in MESAJLAR)


@test("B2 tip metin olarak STOP_LOSS_LIMIT de kabul")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": "STOP_LOSS_LIMIT"})
    bot = trend_pozisyonu(b)
    assert bot.borsa_stopunu_kur(bot.grid[0]) is True
    assert not b._trend_durumu.get("borsa_stop_kapali")


@test("B3 hemen gerceklesen emir: borsa stop kalici kapanir, satis muhasebeye islenir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 2, "executedQty": 7.0, "executedPrice": 9.95, "tip": 4})
    bot = trend_pozisyonu(b)
    kasa = b.MerkeziKasa(500.0)
    MESAJLAR.clear()
    assert bot.borsa_stopunu_kur(bot.grid[0]) is False
    assert "gerceklesti" in b._trend_durumu["borsa_stop_kapali"]
    assert bot.grid[0].borsa_stop_emir_id == "E1"
    assert any("Borsa stop emri kapatildi" in m for m in MESAJLAR)
    sayac = [1]
    bot.borsa_stop_bakimi(kasa, sayac, None, None)
    assert not bot.has_open_position
    assert sayac[0] == 0
    assert abs(kasa.bakiye - (500 + 7 * 9.95 * (1 - b.KOMISYON_PCT))) < 0.01, kasa.bakiye


@test("B4 yanlis emir turu: emir iptal edilir, borsa stop kapanir, pozisyon acik kalir")
def _():
    b = yukle()
    c = canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": "1"})
    bot = trend_pozisyonu(b)
    assert bot.borsa_stopunu_kur(bot.grid[0]) is False
    assert c["iptal"] == 1
    assert bot.grid[0].borsa_stop_emir_id is None
    assert bot.has_open_position
    assert "emir turunu" in b._trend_durumu["borsa_stop_kapali"]


@test("B5 kapali iken yeni emir kurulmaz, /durum ve haftalik ozet uyarir")
def _():
    b = yukle()
    c = canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4})
    b._trend_durumu["borsa_stop_kapali"] = "test"
    bot = trend_pozisyonu(b)
    kasa = b.MerkeziKasa(500.0)
    assert bot.borsa_stopunu_kur(bot.grid[0]) is False
    bot.borsa_stop_bakimi(kasa, [1], None, None)
    assert c["kur"] == []
    assert "borsa stop emri kapali" in b.durum_ozeti_metni(kasa, {"ADATRY": bot})
    assert "borsa stop emri kapali" in b.haftalik_ozet_metni(kasa, {"ADATRY": bot})


@test("B6 sorgu hatasi dogrulamayi bozmaz (emir kalir)")
def _():
    b = yukle()

    def hata():
        raise RuntimeError("ag")
    canli_hazirla(b, hata)
    bot = trend_pozisyonu(b)
    assert bot.borsa_stopunu_kur(bot.grid[0]) is True
    assert not b._trend_durumu.get("borsa_stop_kapali")


@test("B7 stop yukselince borsadaki emir yukseltilir (trend)")
def _():
    b = yukle()
    c = canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4})
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    bot.last_real_price = 12.0
    assert bot.borsa_stopunu_kur(bot.grid[0])
    bot.grid[0].trend_stop = 10.5
    bot.grid[0].borsa_stop_son_islem = time.monotonic() - 1000
    bot.grid[0].borsa_stop_son_sorgu = time.monotonic()
    bot.borsa_stop_bakimi(b.MerkeziKasa(500.0), [1], None, None)
    assert c["iptal"] == 1 and len(c["kur"]) == 2
    assert abs(c["kur"][1][2] - 10.5 * 0.99) < 1e-6


@test("B8 bot satisi once borsa emrini iptal eder")
def _():
    b = yukle()
    c = canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4})
    bot = trend_pozisyonu(b)
    assert bot.borsa_stopunu_kur(bot.grid[0])
    bot._canli_emir_dogrula_ve_gonder = lambda side, q, p: (q, p)
    kasa = b.MerkeziKasa(500.0)
    bot.stop_loss_kontrol(8.5, sim=False, kasa=kasa, acik_pozisyon_sayaci=[1], durum_kaydet=None, rapor=None)
    assert c["iptal"] == 1
    assert not bot.has_open_position


@test("B9 kapatma bayragi durum dosyasina kaydedilir ve geri yuklenir")
def _():
    b = yukle()
    d = tempfile.mkdtemp()
    b.STATE_DOSYASI = os.path.join(d, "s.json")
    b._trend_durumu.clear()
    b._trend_durumu["borsa_stop_kapali"] = "x"
    b.durumu_kaydet(b.MerkeziKasa(500.0), {})
    veri = b.durumu_yukle()
    assert veri["trend"]["borsa_stop_kapali"] == "x", veri.get("trend")


# ---------------------------------------------------------------- gunluk kontrol, tekrar
def trend_kur(b, veri_fn):
    b.CANLI_MOD = False
    b._trend_durumu.clear()
    b._alim_durumu = "ACIK"
    b._gunluk_mumlar = veri_fn
    b.get_last_price = lambda s: 100.0
    b.orderbook_spread_kontrol = lambda s: (0.05, None, None)  # spread dar, defter fiyati yok
    MESAJLAR.clear()


@test("C1 eksik coin verisi: 2 saat boyunca 10 dk arayla tekrar, sonra eksikle tamamlar")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    cagri = []

    def veri(s, bugun_ms, n):
        cagri.append(s)
        if s == "ETHTRY":
            return None
        return gunluk(n, bugun_ms, egim=0.0)
    trend_kur(b, veri)
    kasa, poz = b.MerkeziKasa(750.0), {}
    t0 = bugun + 10 * 60_000
    assert b.trend_gunluk_kontrol(kasa, poz, [0], lambda: None, None, simdi_ms=t0) is False
    n = len(cagri)
    assert b.trend_gunluk_kontrol(kasa, poz, [0], lambda: None, None, simdi_ms=t0 + 5 * 60_000) is False
    assert len(cagri) == n, "10 dk dolmadan tekrar veri cekildi"
    assert b.trend_gunluk_kontrol(kasa, poz, [0], lambda: None, None, simdi_ms=t0 + 11 * 60_000) is False
    assert len(cagri) > n
    assert not any("Gunluk trend kontrolu" in m for m in MESAJLAR)
    assert b.trend_gunluk_kontrol(kasa, poz, [0], lambda: None, None, simdi_ms=t0 + 125 * 60_000) is True
    assert b._trend_durumu["son_gun"] == bugun
    assert any("Verisi alinamayan: ETH" in m for m in MESAJLAR)


@test("C2 BTC verisi yoksa tekrar denenir")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN

    def veri(s, bugun_ms, n):
        return None if s in ("BTCUSDT", "BTCTRY") else gunluk(n, bugun_ms)
    trend_kur(b, veri)
    assert b.trend_gunluk_kontrol(b.MerkeziKasa(750.0), {}, [0], lambda: None, None,
                                  simdi_ms=bugun + 10 * 60_000) is False


@test("C3 tam veri: ilk denemede tamamlanir, ayni gun tekrar yapilmaz")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    cagri = []

    def veri(s, bugun_ms, n):
        cagri.append(s)
        return gunluk(n, bugun_ms)
    trend_kur(b, veri)
    kasa = b.MerkeziKasa(750.0)
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=bugun + 10 * 60_000) is True
    n = len(cagri)
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=bugun + 60 * 60_000) is False
    assert len(cagri) == n


@test("C4 ertesi gun tekrar sayaci sifirlanir")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    durum = {"eksik": True}

    def veri(s, bugun_ms, n):
        return None if (s == "ETHTRY" and durum["eksik"]) else gunluk(n, bugun_ms)
    trend_kur(b, veri)
    kasa = b.MerkeziKasa(750.0)
    dun = bugun - GUN
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=dun + 10 * 60_000) is False
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=dun + 200 * 60_000) is True
    # yeni gun: ilk denemede eksikse yine tekrar denenmeli (pencere yeni gune gore)
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=bugun + 10 * 60_000) is False


# ---------------------------------------------------------------- uctan uca trend
@test("D1 kirilim sinyalinde alim (risk %1), stop yukseltme, stopta satis ve gunluk")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN

    def veri(s, bugun_ms, n):
        if s == "ADATRY":
            return gunluk(n, bugun_ms, bas=50.0, egim=0.002, son_sicrama=0.03)
        return gunluk(n, bugun_ms, bas=100.0, egim=0.001 if s == "BTCUSDT" else -0.001)
    trend_kur(b, veri)
    son = gunluk(300, bugun, bas=50.0, egim=0.002, son_sicrama=0.03)
    fiyat = son["kapanis"][-1]
    b.get_last_price = lambda s: fiyat
    kasa, poz, sayac = b.MerkeziKasa(750.0), {}, [0]
    assert b.trend_gunluk_kontrol(kasa, poz, sayac, lambda: None, None, simdi_ms=bugun + 10 * 60_000)
    assert "ADATRY" in poz and poz["ADATRY"].has_open_position, MESAJLAR
    lvl = poz["ADATRY"].grid[0]
    risk = lvl.buy_qty * (lvl.buy_price - lvl.trend_stop)
    assert 6.5 < risk < 8.0, risk
    assert sayac[0] == 1
    # ertesi gun daha yuksek: stop yukselir
    poz["ADATRY"].alis_zamani = b.datetime.fromtimestamp((bugun - GUN) / 1000)
    eski = lvl.trend_stop

    def veri2(s, bugun_ms, n):
        if s == "ADATRY":
            v = gunluk(n, bugun_ms, bas=50.0, egim=0.002, son_sicrama=0.03)
            v["yuksek"][-1] = fiyat * 1.3
            v["kapanis"][-1] = fiyat * 1.25
            return v
        return gunluk(n, bugun_ms, bas=100.0, egim=0.001 if s == "BTCUSDT" else -0.001)
    b._gunluk_mumlar = veri2
    assert b.trend_gunluk_kontrol(kasa, poz, sayac, lambda: None, None, simdi_ms=bugun + GUN + 10 * 60_000)
    assert lvl.trend_stop > eski
    # stop'a dusus: satis
    b._trend_turu  # var
    poz["ADATRY"].stop_loss_kontrol(lvl.trend_stop * 0.99, sim=False, kasa=kasa, acik_pozisyon_sayaci=sayac,
                                    durum_kaydet=lambda: None, rapor=None)
    assert not poz["ADATRY"].has_open_position
    assert sayac[0] == 0
    assert os.path.exists(b.ISLEM_GUNLUGU_CSV)
    kay = b.islem_gunlugunu_oku()
    assert len(kay) == 1 and float(kay[0]["net_kar_try"]) > 0, kay


# ---------------------------------------------------------------- haftalik ozet
@test("E1 pazartesi gunluk kontrolden sonra haftalik ozet gelir, sali gelmez")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    pazartesi = bugun - ((time.gmtime(bugun / 1000).tm_wday) * GUN)
    trend_kur(b, lambda s, bm, n: gunluk(n, bm))
    kasa = b.MerkeziKasa(750.0)
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=pazartesi + 10 * 60_000)
    assert any("Haftalik ozet" in m for m in MESAJLAR), MESAJLAR
    assert b._trend_durumu["son_haftalik"] == pazartesi
    MESAJLAR.clear()
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=pazartesi + GUN + 10 * 60_000)
    assert not any("Haftalik ozet" in m for m in MESAJLAR)


@test("E2 pazartesi kacirilirsa 7 gun sonra ilk kontrolde gelir")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    pazartesi = bugun - ((time.gmtime(bugun / 1000).tm_wday) * GUN)
    trend_kur(b, lambda s, bm, n: gunluk(n, bm))
    b._trend_durumu["son_haftalik"] = pazartesi - 7 * GUN
    b._trend_durumu["hafta_portfoy"] = 700.0
    sali = pazartesi + GUN
    kasa = b.MerkeziKasa(750.0)
    assert b.trend_gunluk_kontrol(kasa, {}, [0], lambda: None, None, simdi_ms=sali + 10 * 60_000)
    m = [x for x in MESAJLAR if "Haftalik ozet" in x]
    assert m and "+50.00 TRY" in m[0], m


@test("E3 haftalik ozet icerigi: islemler, acik pozisyon, giris ustu stop")
def _():
    b = yukle()
    g = b.ISLEM_GUNLUGU_CSV
    simdi = b.datetime.now()
    b.islem_gunlugune_yaz({"cikis_zamani": simdi.strftime("%Y-%m-%d %H:%M"), "sembol": "SOLTRY",
                           "net_kar_try": 12.5, "cikis_sebebi": "TRAILING-STOP"}, g)
    bot = trend_pozisyonu(b, fiyat=10.0, stop=10.5)
    bot.last_real_price = 13.0
    kasa = b.MerkeziKasa(700.0)
    kasa.baslangic = 750.0
    metin = b.haftalik_ozet_metni(kasa, {"ADATRY": bot})
    assert "Islem: 1" in metin and "+12.50" in metin, metin
    assert "ADA: %+30.0" in metin, metin
    assert "zarar ihtimali yok" in metin, metin


@test("E4 /hafta komutu ve yardim metni")
def _():
    b = yukle()
    assert "/hafta" in b.TELEGRAM_YARDIM_METNI
    import inspect
    assert '"/hafta"' in inspect.getsource(b)



# ================================================================ v22 duzeltmeleri
def emir_mock(b, yanit, sorgu=None):
    """binance_gercek_emir_gonder ve sorgu mock'u; gonderilen emirleri listeler."""
    giden = []

    def gonder(sym, side, q):
        giden.append((sym, side, q))
        if isinstance(yanit, Exception):
            raise yanit
        return yanit
    b.binance_gercek_emir_gonder = gonder
    if sorgu is not None:
        b.binance_emir_sorgula = lambda eid: sorgu
    return giden


@test("V1 stop teyidi: en iyi alis stop'un ustundeyse (tek islemlik sapma) satilmaz")
def _():
    b = yukle()
    b.CANLI_MOD = False
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    b.orderbook_spread_kontrol = lambda s: (0.1, 9.6, 9.62)
    kasa = b.MerkeziKasa(500.0)
    bot.stop_loss_kontrol(8.0, sim=True, kasa=kasa, acik_pozisyon_sayaci=[1])
    assert bot.has_open_position


@test("V2 stop teyidi: en iyi alis da stop'un altindaysa en iyi alistan satilir")
def _():
    b = yukle()
    b.CANLI_MOD = False
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    b.orderbook_spread_kontrol = lambda s: (0.1, 8.9, 8.92)
    kasa, sayac = b.MerkeziKasa(500.0), [1]
    bot.stop_loss_kontrol(8.95, sim=True, kasa=kasa, acik_pozisyon_sayaci=sayac)
    assert not bot.has_open_position and sayac[0] == 0
    kay = b.islem_gunlugunu_oku()
    assert len(kay) == 1 and kay[0]["cikis_sebebi"] == "STOP-LOSS"
    assert abs(float(kay[0]["cikis_fiyati"]) - 8.9) < 0.05, kay[0]["cikis_fiyati"]


@test("V3 stop teyidi: emir defteri okunamazsa guvenli tarafta kalinip satilir")
def _():
    b = yukle()
    b.CANLI_MOD = False
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    bot.stop_loss_kontrol(8.9, sim=True, kasa=b.MerkeziKasa(500.0), acik_pozisyon_sayaci=[1])
    assert not bot.has_open_position


@test("V4 stop teyidi: fiyat stop ustundeyken emir defterine hic bakilmaz")
def _():
    b = yukle()
    cagri = []
    b.orderbook_spread_kontrol = lambda s: cagri.append(s) or (None, None, None)
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    bot.stop_loss_kontrol(9.5, sim=True, kasa=b.MerkeziKasa(500.0), acik_pozisyon_sayaci=[1])
    assert cagri == [] and bot.has_open_position


@test("V5 gerceklesen fiyat/miktar emir yanitindan okunur (alim)")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4})
    emir_mock(b, {"code": 0, "data": {"orderId": 11, "status": 2, "executedQty": "6.9",
                                      "executedQuoteQty": "70.38"}})
    bot = b.CoinBot(symbol="ADATRY", coin_name="ADA")
    sonuc = bot._canli_emir_dogrula_ve_gonder("BUY", 7.0, 10.0)
    assert sonuc == (6.9, 70.38 / 6.9), sonuc


@test("V6 yanitta dolum yoksa emir bir kez sorgulanir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 2, "executedQty": 6.8, "executedPrice": 10.1, "tip": 2})
    emir_mock(b, {"code": 0, "data": {"orderId": 12}})
    bot = b.CoinBot(symbol="ADATRY", coin_name="ADA")
    assert bot._canli_emir_dogrula_ve_gonder("BUY", 7.0, 10.0) == (6.8, 10.1)


@test("V7 mantiksiz dolum bilgisi (fiyat %20+ farkli / fazla miktar) tahmine doner")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0, "executedQty": 0.0, "executedPrice": 0.0})
    emir_mock(b, {"code": 0, "data": {"orderId": 13, "executedQty": "70", "executedQuoteQty": "7"}})
    bot = b.CoinBot(symbol="ADATRY", coin_name="ADA")
    assert bot._canli_emir_dogrula_ve_gonder("BUY", 7.0, 10.0) == (7.0, 10.0)


@test("V8 canli trend alimi gercek fiyatla kaydedilir, stop gercek fiyattan hesaplanir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    emir_mock(b, {"code": 0, "data": {"orderId": 14, "executedQty": "6.9", "executedQuoteQty": "70.38"}})
    bot = b.CoinBot(symbol="ADATRY", coin_name="ADA")
    kasa, sayac = b.MerkeziKasa(750.0), [0]
    assert bot.trend_girisi(10.0, 70.0, 0.1, kasa, sayac, None, None, 750.0, True)
    lvl = bot.grid[0]
    assert abs(lvl.buy_price - 10.2) < 1e-9 and abs(lvl.trend_stop - 9.18) < 1e-9
    assert abs(kasa.bakiye - (750 - 70.38 * 1.001)) < 1e-6, kasa.bakiye


@test("V9 canli satis gercek fiyatla muhasebeye islenir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    emir_mock(b, {"code": 0, "data": {"orderId": 15, "executedQty": "7", "executedQuoteQty": "62.3"}})
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    kasa = b.MerkeziKasa(500.0)
    bot.stop_loss_kontrol(8.95, sim=False, kasa=kasa, acik_pozisyon_sayaci=[1])
    assert not bot.has_open_position
    assert abs(kasa.bakiye - (500 + 62.3 * 0.999)) < 1e-6, kasa.bakiye


@test("V10 coin borsada yoksa satis emri gonderilmez; kapatilir, gunluge yazilir, nakit esitlenir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    b.binance_hesap_bakiyeleri = lambda: {"ADA": {"free": 0.0, "locked": 0.0}, "TRY": {"free": 566.0, "locked": 0}}
    b.binance_serbest_try_bakiyesi = lambda: 566.0
    giden = emir_mock(b, {"code": 0})
    bot = trend_pozisyonu(b, fiyat=10.0, stop=9.0)
    kasa, sayac = b.MerkeziKasa(500.0), [1]
    MESAJLAR.clear()
    bot.stop_loss_kontrol(8.9, sim=False, kasa=kasa, acik_pozisyon_sayaci=sayac)
    assert giden == [] and not bot.has_open_position and sayac[0] == 0
    assert kasa.bakiye == 566.0
    kay = b.islem_gunlugunu_oku()
    assert len(kay) == 1 and kay[0]["cikis_sebebi"] == "BORSADA-YOK"
    assert sum("borsada bulunamadi" in m for m in MESAJLAR) == 1


@test("V11 coin kilitli emirdeyse (serbest 0, kilitli var) borsada yok sayilmaz")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    b.binance_hesap_bakiyeleri = lambda: {"ADA": {"free": 0.0, "locked": 7.0}, "TRY": {"free": 500.0, "locked": 0}}
    giden = emir_mock(b, {"code": 0})
    bot = trend_pozisyonu(b)
    assert bot._satisi_uygula(bot.grid[0], 8.9, "STOP-LOSS", False, b.MerkeziKasa(500.0), [1], None, None) is False
    assert giden == [] and bot.has_open_position


@test("V12 mutabakatta kaybolan coin gunluge yazilir ve haber verilir")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    b.binance_hesap_bakiyeleri = lambda: {"ADA": {"free": 0.0, "locked": 0.0}, "TRY": {"free": 570.0, "locked": 0}}
    bot = trend_pozisyonu(b)
    kasa = b.MerkeziKasa(500.0)
    MESAJLAR.clear()
    b.mutabakat_yap(kasa, {"ADATRY": bot})
    assert not bot.has_open_position and kasa.bakiye == 570.0
    assert b.islem_gunlugunu_oku()[0]["cikis_sebebi"] == "BORSADA-YOK"
    assert any("borsada bulunamadi" in m for m in MESAJLAR)
    assert b._risk.yatirilan_sermaye == 0.0  # kapanis para yatirma sayilmadi


@test("V13 ayni emir hatasi Telegram'a 30 dk'da en fazla bir kez")
def _():
    b = yukle()
    canli_hazirla(b, {"status": 0})
    emir_mock(b, RuntimeError("Binance TR emri reddetti: code=-1 msg=bakim"))
    zaman = [1000.0]
    b.time.monotonic = lambda: zaman[0]
    bot = trend_pozisyonu(b)
    MESAJLAR.clear()
    for _ in range(10):
        assert bot._canli_emir_dogrula_ve_gonder("SELL", 7.0, 9.0) is None
        zaman[0] += 25
    assert sum("CANLI EMIR BASARISIZ" in m for m in MESAJLAR) == 1
    zaman[0] += 31 * 60
    bot._canli_emir_dogrula_ve_gonder("SELL", 7.0, 9.0)
    assert sum("CANLI EMIR BASARISIZ" in m for m in MESAJLAR) == 2


def dongu_kur(b, tur_fn):
    """run_simulation'i simulasyon modunda ag olmadan calistirir; tur_fn her turda cagrilir."""
    b.CANLI_MOD = False
    sayac = {"tur": 0, "rapor": 0}

    def tur(*a, **k):
        sayac["tur"] += 1
        tur_fn(sayac["tur"])
    b._trend_turu = tur
    b._dongu_beklemesi = lambda k: None
    gercek = b.print_performans_raporu

    def rapor(*a, **k):
        sayac["rapor"] += 1
        return gercek(*a, **k)
    b.print_performans_raporu = rapor
    return sayac


@test("V14 ana dongude beklenmedik hata botu durdurmaz, Telegram'a bir kez haber verilir")
def _():
    b = yukle()

    def tur(n):
        if n <= 3:
            raise ValueError("beklenmedik veri")
        raise KeyboardInterrupt
    sayac = dongu_kur(b, tur)
    MESAJLAR.clear()
    assert b.run_simulation() == b.CIKIS_DUR
    assert sayac["tur"] == 4
    assert sum("Beklenmedik hata" in m for m in MESAJLAR) == 1


@test("V15 art arda 20 turda hata olursa bot durur (baslatici yeniden acar)")
def _():
    b = yukle()

    def tur(n):
        raise ValueError("hep hata")
    sayac = dongu_kur(b, tur)
    try:
        b.run_simulation()
        raise AssertionError("durmaliydi")
    except ValueError:
        pass
    assert sayac["tur"] == b.DONGU_HATA_LIMITI


@test("V16 performans tablosu her turda degil 30 dk'da bir")
def _():
    b = yukle()

    def tur(n):
        if n > 50:
            raise KeyboardInterrupt
    sayac = dongu_kur(b, tur)
    b.run_simulation()
    assert sayac["rapor"] == 2, sayac  # ilk tur + Ctrl+C ozeti


@test("V17 v21 durum dosyasi (ADA trend pozisyonu + borsa stop) kayipsiz yuklenir ve kaydedilir")
def _():
    b = yukle()
    import json
    v21 = {"calisma_modu": "SIMULASYON", "alim_durumu": "ACIK", "kasa_bakiye": 682.5, "kasa_baslangic": 750.0,
           "kasa_toplam_komisyon": 0.07, "risk": {"yatirilan_sermaye": 750.0, "zirve_portfoy": 760.0,
           "coin_engel": {}, "ardisik_kayip": 0}, "strateji": "TREND", "trend": {"son_gun": 123, "son_haftalik": 5},
           "pozisyonlar": {"ADATRY": {"coin_name": "ADA", "width_pct": 0.16, "grid_count": 4, "starting_try": 68.0,
               "cash_try": -0.07, "coin_qty": 120.5, "trade_count": 1, "realized_pnl": 0.0, "toplam_komisyon": 0.07,
               "lower": 0, "upper": 0, "initialized": True, "bekliyor": False, "bekleme_sayaci": 0,
               "son_satis_zamani": None, "alis_zamani": "2026-10-07T03:06:00", "son_cooldown_dakika": 30,
               "giris_bilgi": {"zaman": "2026-10-07T03:06:00", "miktar": 120.5, "tutar": 68.0, "komisyon": 0.07},
               "acik_islem_pnl": 0.0, "grid": [{"price": 0.5643, "has_position": True, "buy_qty": 120.5,
               "buy_price": 0.5643, "en_yuksek_fiyat": 0.61, "kismi_kar_alindi": False, "borsa_stop_emir_id": "777",
               "borsa_stop_fiyati": 0.50, "borsa_stop_miktari": 120.4, "risk_birimi": 0.062, "ilk_stop": 0.5023,
               "atr_giris": 0.031, "tp1_alindi": False, "tp2_alindi": False, "trend_stop": 0.5110}]},
               "ETHTRY": {"coin_name": "ETH", "coin_qty": 0.0, "grid": []}},
           "raporlama": {}}
    kasa, poz, acik = b.durumdan_kasa_ve_pozisyonlar_olustur(v21)
    assert acik == 1 and list(poz) == ["ADATRY"]
    lvl = poz["ADATRY"].grid[0]
    assert lvl.trend_stop == 0.5110 and lvl.borsa_stop_emir_id == "777" and lvl.en_yuksek_fiyat == 0.61
    assert poz["ADATRY"].giris_bilgi["tutar"] == 68.0
    b.STATE_DOSYASI = os.path.join(tempfile.mkdtemp(), "s.json")
    b._trend_durumu.update(v21["trend"])
    b.durumu_kaydet(kasa, poz)
    veri = b.durumu_yukle()
    kasa2, poz2, _ = b.durumdan_kasa_ve_pozisyonlar_olustur(veri)
    assert poz2["ADATRY"].grid[0] == lvl and kasa2.bakiye == 682.5
    assert veri["trend"]["son_haftalik"] == 5


@test("V18 eski stratejiden kalan pozisyon trend kurallarina aktarilir")
def _():
    b = yukle()
    eski = {"pozisyonlar": {"PEPETRY": {"coin_name": "PEPE", "coin_qty": 1000.0, "starting_try": 100.0,
            "grid": [{"price": 1, "has_position": False, "buy_qty": 0, "buy_price": 0, "en_yuksek_fiyat": 0},
                     {"price": 0.1, "has_position": True, "buy_qty": 1000.0, "buy_price": 0.1,
                      "en_yuksek_fiyat": 0.11, "risk_birimi": 0.003, "ilk_stop": 0.097, "tp1_alindi": True}]}}}
    _, poz, acik = b.durumdan_kasa_ve_pozisyonlar_olustur(eski)
    assert acik == 1 and len(poz["PEPETRY"].grid) == 1
    lvl = poz["PEPETRY"].grid[0]
    assert lvl.trend_stop == 0.097
    eski2 = {"pozisyonlar": {"X": {"coin_qty": 5.0, "grid": [{"price": 2, "has_position": True, "buy_qty": 5.0,
                                                            "buy_price": 2.0, "en_yuksek_fiyat": 2.0}]}}}
    _, poz2, _ = b.durumdan_kasa_ve_pozisyonlar_olustur(eski2)
    assert abs(poz2["X"].grid[0].trend_stop - 2.0 * 0.96) < 1e-12


@test("V19 kaldirilan komutlar acik bir mesajla cikar (kod 2)")
def _():
    b = yukle()
    for k in ("backtest", "analiz", "karsilastir", "strateji"):
        sys.argv = ["bot.py", k]
        try:
            b.main()
        except SystemExit as e:
            assert e.code == b.CIKIS_AYAR_HATASI, (k, e.code)


@test("V20 /btc yeni BTC filtresi ciktisi; /analiz yardimda yok")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN
    b._gunluk_mumlar = lambda s, bm, n: gunluk(n, bm, bas=60000, egim=0.002)
    satirlar = b.btc_durum_satirlari()
    assert any("EMA50 USTUNDE" in x for x in satirlar), satirlar
    MESAJLAR.clear()
    b.telegram_komutunu_uygula("/btc", b.MerkeziKasa(1), {}, lambda: None, None, [0], {})
    assert MESAJLAR and "BTC filtresi" in MESAJLAR[0]
    assert "/analiz" not in b.TELEGRAM_YARDIM_METNI and "/btc" in b.TELEGRAM_YARDIM_METNI
    MESAJLAR.clear()
    b.telegram_komutunu_uygula("/analiz", b.MerkeziKasa(1), {}, lambda: None, None, [0], {})
    assert "Bilinmeyen komut" in MESAJLAR[0]


@test("V21 'trend' testi ve 'rapor' komutu calisir (sentetik veri)")
def _():
    b = yukle()
    son = (int(time.time() * 1000) // GUN) * GUN
    b.gecmis_mumlari_getir = lambda s, i, bas, bit: gunluk(int((bit - bas) // GUN), bit, bas=100,
                                                            egim=0.003 if s != "DOGETRY" else -0.001,
                                                            oynaklik=0.03)
    assert b.trend_komutu(["90", "1000"]) == b.CIKIS_DUR
    assert b.rapor_komutu() == b.CIKIS_DUR


@test("V22 Ctrl+C sorusu borsa stopundan bahsediyor (eski 'stop calismaz' yazisi yok)")
def _():
    b = yukle()
    import inspect
    kaynak = inspect.getsource(b._kapanista_pozisyon_sorusu)
    assert "borsa stop" in kaynak and "CALISMAZ" not in kaynak


@test("V23 uctan uca simulasyon: sinyal -> alim -> stop yukselme -> stopta satis -> gunluk/ozet")
def _():
    b = yukle()
    bugun = (int(time.time() * 1000) // GUN) * GUN

    def veri(s, bugun_ms, n):
        if s == "SOLTRY":
            return gunluk(n, bugun_ms, bas=50.0, egim=0.002, son_sicrama=0.03)
        return gunluk(n, bugun_ms, bas=100.0, egim=0.001 if s == "BTCUSDT" else -0.001)
    trend_kur(b, veri)
    fiyat = gunluk(300, bugun, bas=50.0, egim=0.002, son_sicrama=0.03)["kapanis"][-1]
    b.get_last_price = lambda s: fiyat
    kasa, poz, sayac = b.MerkeziKasa(750.0), {}, [0]
    b._trend_turu(kasa, poz, sayac, lambda: None, None)
    assert "SOLTRY" in poz and poz["SOLTRY"].has_open_position, MESAJLAR
    assert any("TREND ALIMI: SOLTRY" in m for m in MESAJLAR)
    b.get_last_price = lambda s: poz["SOLTRY"].grid[0].trend_stop * 0.99
    b._trend_turu(kasa, poz, sayac, lambda: None, None)
    assert not poz["SOLTRY"].has_open_position and sayac[0] == 0
    metin = b.haftalik_ozet_metni(kasa, poz)
    assert "Islem: 1" in metin


if __name__ == "__main__":
    for ad, ok, hata in sonuc:
        print(("GECTI " if ok else "KALDI ") + ad)
        if not ok:
            print(hata)
    print(f"\n{sum(1 for _, ok, _ in sonuc if ok)}/{len(sonuc)} gecti")
