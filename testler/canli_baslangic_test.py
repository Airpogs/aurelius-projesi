# Calistirmak icin: bash testler/calistir.sh
"""CANLI mod acilis testi: v21 durum dosyasi (ADA pozisyonu) ile v22 baslar, borsa stopu kurar, doner, Ctrl+C."""
import os, sys, json, time
os.environ.update({"AURELIUS_CANLI_MOD": "1", "AURELIUS_LIVE_CONFIRM": "EVET_GERCEK_PARA_KULLAN",
                   "BINANCE_TR_API_KEY": "k" * 64, "BINANCE_TR_SECRET_KEY": "s" * 64})
os.environ.pop("TELEGRAM_BOT_TOKEN", None)
import bot as b
for f in (b.STATE_DOSYASI, b.ISLEM_GUNLUGU_CSV):
    if os.path.exists(f):
        os.remove(f)
MES = []
b.send_telegram = lambda m: MES.append(m)
b.time.sleep = lambda s: None
v21 = {"calisma_modu": "CANLI", "alim_durumu": "ACIK", "kasa_bakiye": 682.5, "kasa_baslangic": 750.0,
       "risk": {"yatirilan_sermaye": 750.0, "zirve_portfoy": 760.0}, "strateji": "TREND",
       "trend": {"son_gun": (int(time.time() * 1000) // 86400000) * 86400000, "son_haftalik": 1},
       "pozisyonlar": {"ADATRY": {"coin_name": "ADA", "starting_try": 68.0, "coin_qty": 120.5,
           "alis_zamani": "2026-10-07T03:06:00", "giris_bilgi": {"tutar": 68.0, "miktar": 120.5, "komisyon": 0.07},
           "grid": [{"price": 0.5643, "has_position": True, "buy_qty": 120.5, "buy_price": 0.5643,
                     "en_yuksek_fiyat": 0.61, "risk_birimi": 0.062, "ilk_stop": 0.5023, "trend_stop": 0.5110}]}}}
json.dump(v21, open(b.STATE_DOSYASI, "w"))
kur = []
b.binance_hesap_bakiyeleri = lambda: {"TRY": {"free": 682.5, "locked": 0.0}, "ADA": {"free": 120.4, "locked": 0.0}}
b.sembol_filtrelerini_getir = lambda s: {"order_types": ["MARKET", "STOP_LOSS_LIMIT"], "step_size": 0.1,
                                         "tick_size": 0.0001, "min_notional": 10}
b.binance_stop_limit_satis_emri = lambda s, q, t, l: kur.append((s, q, t, l)) or "E9"
b.binance_emir_sorgula = lambda e: {"status": 0, "executedQty": 0.0, "executedPrice": 0.0, "tip": 4}
b.get_last_price = lambda s: 0.60
b._gunluk_mumlar = lambda s, bm, n: None
b.orderbook_spread_kontrol = lambda s: (None, None, None)
tur = [0]
def bekle(k):
    tur[0] += 1
    if tur[0] >= 3:
        raise KeyboardInterrupt
b._dongu_beklemesi = bekle
kod = b.run_simulation()
assert kod == b.CIKIS_DUR, kod
assert kur and kur[0][0] == "ADATRY" and abs(kur[0][2] - 0.5110 * 0.99) < 1e-4, kur
veri = json.load(open(b.STATE_DOSYASI))
lvl = veri["pozisyonlar"]["ADATRY"]["grid"][0]
assert lvl["borsa_stop_emir_id"] == "E9" and lvl["trend_stop"] == 0.5110, lvl
assert any("v22 CANLI MODDA baslatildi" in m for m in MES), MES
assert any("borsa stop emri kuruldu" in m for m in MES)
print("CANLI ACILIS OK:", kur, "| mesaj sayisi", len(MES))
