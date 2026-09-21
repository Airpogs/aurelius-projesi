"""
PROJECT AURELIUS - v17
Binance TR AKILLI SECIM Grid Trading Bot - PIYASA ADAPTIF MOTOR VE OTONOM SERMAYE DONGUSU
======================================================================
v17 FIX - BINANCE TR CANLI MOD API ENTEGRASYON DUZELTMESI (bakiye hep
0.00 TRY donuyordu / "Invalid API-key" / "tuple object has no attribute
'encode'"):

  1) BASE_URL + ACCOUNT_ENDPOINT_PATH duzeltildi: "https://www.binancetr.com"
     + "/open-api/v3/account" (Binance Global stili, YANLIS) yerine
     kullanicidan teyitli "https://www.binance.tr" + "/open/v1/account/spot"
     kullaniliyor.
  1b) ORDER_ENDPOINT_PATH ARASTIRILDI VE GUNCELLENDI: "/open-api/v3/order"
     (Binance Global stili, kesinlikle yanlis) yerine "/open/v1/orders"
     (POST) kullaniliyor - bu yol, Binance TR'yi hedefleyen bagimsiz/acik
     kaynakli bir topluluk kutuphanesinin (github.com/futuristicexchanger/
     BinanceTrApi) incelenmesiyle bulundu; kutuphanenin hesap/bakiye yolu
     kullanicinin CANLI ortamda ZATEN dogruladigi yolla birebir ayni oldugu
     icin guven duzeyi yuksek kabul edildi. AYRICA bu kaynaga gore Binance
     TR "side"/"type" alanlarini "BUY"/"MARKET" METIN olarak degil SAYISAL
     KOD olarak bekliyor - binance_gercek_emir_gonder() artik ORDER_SIDE_
     KODU/ORDER_TIPI_MARKET_KODU ile bu donusumu yapiyor. YINE DE BU RESMI
     BINANCE TR DOKUMANTASYONU DEGILDIR - canli_mod_on_kontrol() her CANLI
     baslangicta ilk emri KUCUK bir tutarla test edip [BORSA YANITI]
     satirini borsa arayuzuyle karsilastirmanizi hatirlatir.
  2) API anahtarlari artik _ortam_degiskeni_str_oku() ile okunuyor - ortam
     degiskeni yanlislikla tuple/list olursa (orn. tanim satirinin sonunda
     unutulan bir virgul) ANINDA, net bir Turkce hata ile durur; artik
     HMAC imzalama sirasinda "tuple object has no attribute 'encode'" gibi
     anlasilmasi zor bir hatayla GEC ortaya cikmaz. _binance_imzali_sorgu()
     ve binance_signed_request() de anahtarlarin str oldugunu ayrica dogrular.
  3) binance_signed_request() artik try/except ile HATA YAKALAMALI: HTTP
     hatasi (orn. 401 Invalid API-key) veya beklenmeyen bir istisna olursa
     borsanin dondurdugu HAM YANIT govdesi hem konsola basiliyor hem de
     logger.error ile project_aurelius.log dosyasina kalici olarak
     yaziliyor - "Invalid API-key" gibi hatalarin gercek nedeni artik
     kaybolmuyor.
  4) YENI _binance_tr_bakiye_listesini_cikar() yardimcisi: Binance TR'nin
     GERCEK yanit zarfini ({"code":0,"data":{"balances":[...]}} VEYA
     {"data":{"assets":[...]}}) destekler. Eski kod dogrudan kok dizinde
     "balances" aradigi icin liste HEP BOS donuyor, cuzdanda serbest TRY
     olsa bile bakiye SESSIZCE 0.00 TRY basiliyordu. binance_serbest_try_
     bakiyesi() VE mutabakat_yap() artik bu ortak yardimciyi kullaniyor;
     "code" alani hata donerse veya format hic taniniyorsa ham yanit
     loglanip 0.0/bos sonuc dondurulur (sessiz yanlis pozitif yerine
     log dosyasinda GORUNUR bir iz birakilir).

======================================================================
v17 farki - 4 KRITIK MODUL (v9-v16'nin state/Telegram/X-Z raporlama/
Ratchet Trailing-Stop/Zaman Asimi/Sonuca Dayali Cooldown/ATR bazli
dinamik aralik mimarisi DEGISTIRILMEDI):

  1) KASAYA GORE ADAPTIF SERMAYE VE SNIPER MODU:
     - dinamik_pozisyon_planla() TAMAMEN YENIDEN kurgulandi. Sabit
       "kasa // 2500" formulu yerine ACIK butce esikleri kullanilir:
         < 1.500 TL           -> SNIPER MODU: KESINLIKLE 1 pozisyon,
                                  sermaye ASLA bolunmez, hedef_pozisyon_
                                  tutari DOGRUDAN serbest kasaya esitlenir.
         1.500 - 3.500 TL     -> en fazla 2 pozisyon
         3.500 - 7.500 TL     -> en fazla 3 pozisyon
         7.500 - 15.000 TL    -> en fazla 4 pozisyon
         >= 15.000 TL         -> en fazla 6 pozisyon (tavan)
     - BTC rejimi DEGISMEDI (sert duste 0/tam nakit, notr/kararsizda
       yari kapasite - taban 1, guclu yukseliste tam kapasite) ama artik
       yukaridaki kademe uzerine uygulanir.
     - YENI KALITE FILTRESI: bos pozisyon hakki olsa dahi, ADX>=20 VE
       RSI 38-60 kriterlerini birlikte karsilayan (ve henuz yatirilmamis/
       cooldown'da olmayan) adaylar arasindan SADECE en yuksek ADX'e
       sahip olana girilir (en_kaliteli_aday_belirle()). Kriteri
       karsilayan aday yoksa sermaye NAKITTE bekletilir - orta kaliteli
       coinlere "slot bos diye" giris YAPILMAZ.
     - TABAN_POZISYON_TUTARI: 1.500 TL -> 300 TL (kucuk kasalarda daha
       esnek tek-aday odaklanmasi icin); 500-1.000 TL sermaye artik
       Sniper Modu sayesinde otomatik olarak tek bir güçlü adaya gider.

  2) DUSUK FIYATLI COINLER ICIN DINAMIK BASAMAK HASSASIYETI:
     - YENI format_fiyat() yardimcisi: fiyat<0.001 ise 8, 0.001<=fiyat<1
       ise 6, fiyat>=1 ise 4 ondalik basamak kullanir. PEPETRY/SHIBTRY
       gibi mikro paritelerde artik "0.0002" yerine "0.00021350" gibi
       gercek deger gorunur.
     - Performans raporu tablosu, giris karti, satis/alis bildirimleri
       ve islem gecmisi tablosu bu fonksiyonu kullanacak sekilde
       guncellendi. Tum tetikleme/karsilastirma mantigi HALA saf float
       degerler uzerinden calisir (gosterim katmani ayri tutuldu).

  3) SEFFAF VE ZENGIN TELEGRAM GIRIS KARTI:
     - giris_karti_olustur() YENIDEN tasarlandi: Sembol, Giris Fiyati,
       Yatirilan (TL) ve Alinan Miktar (Adet), yuzdesel Hedef Satis/
       Stop-Loss ile birlikte beklenen +TL/-TL, RSI(14)/EMA(50)/ADX(14)
       gostergeleri ve Calisma Modu (Sniper Modu / Portfoy Modu (X/Y))
       tek bir monospace <pre> kartinda gosterilir.
     - Kart hem konsola (baslik: "[YENI POZISYON ACILDI]") hem Telegram'a
       (parse_mode="HTML", arka plan kuyrugu uzerinden) gonderilir.

  4) KAR/ZARAR MUHASEBESI VE GOSTERIM OPTIMIZASYONU (ISLEM BAZLI K/Z):
     - Satis aninda ana para + kar zaten MerkeziKasa.bakiye'ye ekleniyordu
       (bileşik getiri v14'ten beri mevcuttu); v17'de EK OLARAK satis
       bildirimi artik ilk gunden beri biriken kumulatif getiri yerine
       SADECE o islemden elde edilen net TL/% kari ve satis sonrasi
       GUNCEL serbest kasa bakiyesini gosterir (orn. "Bu Islemden Net
       Kar: +37.88 TRY (+%1.86) | Yeni Guncel Kasa: 5.308,22 TRY").
     - Bu, TUM kapanis yollarindan (KAR-AL/TRAILING-STOP/STOP-LOSS/
       BREAKEVEN-STOP/ZAMAN-ASIMI/ACIL-TASFIYE/KISMI-KAR-AL) gecen ortak
       _satisi_uygula() metoduna eklendigi icin HER SATIS turunde tutarli
       calisir. Performans raporundaki "Guncel Bakiye" (serbest nakit +
       acik pozisyon piyasa degeri) ve acik pozisyon K/Z sutunu (SADECE
       o an acik olan pozisyonun anlik K/Z'si) DEGISMEDI - zaten dogru
       calisiyordu.

======================================================================
v16 farki - 4 KRITIK MODUL (v9-v15'in state/Telegram/X-Z raporlama/
dinamik sermaye/grid-disi-satis mimarisi DEGISTIRILMEDI):

  1) ZAMAN BAZLI BAYAT POZISYON CIKISI:
     - CoinBot'a 'alis_zamani' (datetime) alani eklendi, state JSON'a
       kalici kaydediliyor.
     - MAKS_POZISYON_OMRU_SAAT (18s) asilmis VE guncel kar
       ZAMAN_ASIMI_KAR_ESIGI_PCT (%1) altindaysa, pozisyon "ZAMAN-ASIMI"
       etiketiyle piyasa fiyatindan kapatilir, sermaye kasaya doner.
     - Konsol+Telegram'a ozel bir bildirim gecilir.

  2) SONUCA DAYALI DINAMIK COOLDOWN:
     - Sabit COOLDOWN_MINUTES yerine, kapanis SEBEBINE gore degisen
       sure: KAR-AL/TRAILING-STOP -> 15dk, ZAMAN-ASIMI -> 45dk,
       STOP-LOSS/BREAKEVEN-STOP/ACIL-TASFIYE -> 90dk (zarar/notr kabul
       edilir - bkz. teslim mesaji icin BREAKEVEN-STOP siniflandirma
       gerekcesi).
     - Tum SATIS yollari artik ortak _satisi_uygula() metodundan geciyor
       - bu METOD, ilgili kapanis etiketine gore dogru cooldown suresini
       otomatik uygular (tag->sure esleme tek bir yerden yonetilir).

  3) ATR TABANLI DINAMIK GRID/KAR ARALIGI:
     - 14 periyotluk ATR (Wilder), coin_degerlendir_ve_sec sirasinda
       (ekstra API cagrisi olmadan, ayni OHLC veri uzerinden) hesaplanir.
     - ATR/Fiyat oranina gore coin basina width_pct DINAMIK belirlenir:
       dusuk volatilite -> ~%2.75 basamak, orta -> ~%4 (eski varsayilan),
       yuksek volatilite -> ~%5.25 basamak.
     - Giris karti ve hedef/stop hesaplari otomatik olarak bu dinamik
       basamaga gore uretilir (STOP_LOSS_PCT/TRAILING sabitleri
       DEGISMEDI - sadece kar hedefi/grid genisligi volatiliteye gore
       olcekleniyor).

  4) CANLI MOD BAKIYE MUTABAKATI:
     - mutabakat_yap(): CANLI_MOD=True iken her ~6 saatte bir VE Gunluk
       X Raporu aninda /open-api/v3/account sorgulanip GERCEK serbest
       TRY bakiyesi ve acik coin miktarlari ic degiskenlerle SESSIZCE
       (sadece log/print ile) senkronize edilir. SIMULASYON modunda
       guvenle atlanir.

  5) TABLO/GORSEL IYILESTIRME:
     - Acik pozisyonlar tablosuna "Yas" kolonu eklendi (orn. "45dk", "19s").
     - Hedef<Stop tutarsizligi v15'te zaten cozulmustu (Trailing aktifken
       "TRAILING" etiketi) - v16'da DEGISTIRILMEDI, korundu.

======================================================================
v15 farki - GRID KAPSAMI DISI SATIS + RAPORLAMA DUZELTMESI
(v9-v14'un state/Telegram/X-Z raporlama/dinamik sermaye mimarisi DEGISTIRILMEDI):

  1) GRID BANDI DISINA CIKAN POZISYONLARIN KAPANAMAMASI - DUZELTILDI:
     KOK NEDEN: evaluate_v9() icinde 'price < self.lower or price >
     self.upper: return' erken cikisi, fiyat gridin USTUNE ciktiginda
     (orn. HEITRY %30 yukseldiginde) KAR-AL kontrolunu de bypass
     ediyordu - pozisyon sadece Trailing-Stop'a mahkum kaliyordu.
     COZUM: Bu erken "return" KALDIRILDI. Aralik kontrolu artik SADECE
     yeni ALIM dalinda uygulaniyor; SATIS/KAR-AL kontrolu fiyat
     araligindan BAGIMSIZ, HER ZAMAN calisir.

  2) DINAMIK KAR HEDEFI + 'HEDEF < STOP' RAPORLAMA TUTARSIZLIGI - DUZELTILDI:
     - YENI: _sonraki_kar_hedefi() metodu - pozisyon gridin en ust
       seviyesindeyse (bir sonraki sabit grid basamagi yoksa) hedefi
       DINAMIK olarak bir basamak daha ileriye tasir (giris fiyati
       uzerinden). Boylece fiyat gridin tepesini asmis olsa bile KAR-AL
       her zaman ulasilabilir bir hedefe sahiptir.
     - acik_hedef_ve_stop(): Trailing-Stop AKTIVE olduysa artik sabit
       bir sayisal hedef DEGIL, "TRAILING" ETIKETI dondurur - cikis
       artik trailing tarafindan yonetildigi icin sabit bir hedef
       gostermek yaniltici olurdu (eski 'Hedef 7.04 < Stop 8.64'
       tutarsizligi boylece ortadan kalkti).

  3) KISMI KAR ALMA SONRASI KALAN POZISYON - DOGRULANDI:
     Madde 1/2 duzeltmesiyle birlikte, kismi kar alma sonrasi kalan
     miktar (level.buy_qty) hedef fiyata ulasildiginda ARTIK HER ZAMAN
     TAMAMEN satiliyor (fiyat grid disina cikmis olsa bile) - ayri bir
     kod degisikligi gerekmedi, ayni duzeltme bunu da kapsiyor. Test
       edilerek dogrulandi (bkz. teslim mesaji).

  4) DINAMIK KAPASITE GORSEL TUTARLILIGI - DUZELTILDI:
     Acik pozisyon sayisi izin verilen kapasiteyi asiyorsa (piyasa
     kosullari kapasiteyi daralttiginda), performans raporunda VE
     Telegram ozetinde "X / Y (Kapasite Daraldi - Yeni Alim Yok)"
     seklinde ACIK bir durum notu gosterilir. Mevcut acik pozisyonlar
     ASLA panik ile kapatilmaz - sadece YENI alim durur (zaten v14'te
     de boyleydi, sadece raporlama netlestirildi).

======================================================================
v14 farki - DINAMIK SERMAYE OLCEKLEME + SEFFAF GIRIS KARTLARI
(v9-v13'un state/Telegram/X-Z raporlama/borsa entegrasyonu DEGISMEDI):

  1) DINAMIK POZISYON MODELI - sabit MAX_OPEN_POSITIONS KALDIRILDI:
     Her tick'te GUNCEL toplam kasaya (kasa.bakiye + acik pozisyonlarin
     piyasa degeri) ve BTC'nin 24s gucune gore YENIDEN hesaplanir:
       a) Taban butce: tek pozisyon TABAN_POZISYON_TUTARI (1.500 TL)
          altina inmesin (mumkunse pozisyon sayisi azaltilarak saglanir).
       b) Kasa kapasitesi: kasa_kapasitesi = max(1, min(6, toplam_kasa//2500))
       c) BTC 24s carpani: >+%1.5 ise tam kapasite; yatay/notr ise yari
          kapasite; sert dususte (BTC_DUSUS_ESIGI_PCT) ise 0 (%100 nakit).
       d) hedef_pozisyon_tutari = kasa.bakiye / izin_verilen_pozisyon
     Boylece 1.000 TL'den 100.000 TL'ye kadar HER kasa buyuklugunde ayni
     mantik otonom olarak dogru sayida, dogru buyuklukte pozisyon acar.

  2) SEFFAF GIRIS KARTI (konsol ASCII kutusu + Telegram):
     Her ALIM'da GIRIS GEREKCESI (EMA50/RSI14/24s hacim), ALIS DETAYI
     (miktar/fiyat/tutar) ve HEDEFLER (hedef satis+beklenen net kar,
     stop-loss+beklenen net kayip, trailing aktivasyon fiyati) iceren
     bir kart hem konsola hem Telegram'a (<pre> blogu ile) gonderilir.
     Periyodik performans raporundaki acik pozisyonlar tablosuna da
     Hedef/Stop kolonlari eklendi.

  3) RISK/ODUL ASIMETRISI: v12'de zaten cozuldu, v14'te DEGISTIRILMEDI
     (STOP_LOSS_PCT=%4, TRAILING_AKTIVASYON_PCT=%3.5, grid basamagi ~%4).

======================================================================
v13 farki - DAYANIKLILIK VE PORTFOY VERIMLILIGI (v9-v12 cekirdegi DEGISMEDI):

  ONEMLI DUZELTME: Mevcut kod tabaninda asyncio veya python-telegram-bot
  KULLANILMIYOR (sadece urllib ile senkron istek atiliyor). Telegram'in
  sessiz kalmasinin gercek nedeni asyncio/thread catismasi degil,
  send_telegram()'in "except Exception: pass" ile HER hatayi (Connection
  reset dahil) hicbir iz birakmadan yutmasiydi.

  1) TELEGRAM DAYANIKLILIGI:
     - send_telegram() artik ANA DONGUYU HICBIR ZAMAN BLOKE ETMEYEN bir
       arka plan thread'i + queue.Queue kuyrugu uzerinden calisir. Mesaj
       kuyruga anlik eklenir (non-blocking), ayri bir worker thread
       exponential backoff (2sn->8sn, 3 deneme) ile gonderir.
     - Basarisiz denemeler artik SESSIZCE yutulmuyor: logging modulu ile
       'project_aurelius.log' dosyasina WARNING/ERROR olarak yaziliyor.

  2) ESNEK PORTFOY + KADEMELI KAR ALMA:
     - MAX_OPEN_POSITIONS: 2 -> 4 (sermaye 4 parcaya bolunebiliyor,
       kilitlenme azaltildi).
     - YENI: KISMI_KAR_AL_PCT (%2) esigine ulasan pozisyonun
       KISMI_KAR_AL_ORANI (%50) kadari ANINDA realize edilir; kalan
       miktar mevcut breakeven/trailing korumasiyla yoluna devam eder.
       Boylece kar sadece kagit uzerinde kalmiyor, kismen kasaya doner.
     - NOT: Kasitli olarak "acik bir kar pozisyonunu zorla kapatip yerine
       yeni aday alma" YAPILMADI - bu, kazanan islemleri erken kesmek
       anlamina gelir ve saglam risk/odul prensipleriyle CELISIR. Bunun
       yerine capital efficiency sorunu daha fazla slot + kademeli kar
       alma ile cozuldu.

  3) TREND GUCU TEYIDI (WHIPSAW FILTRESI):
     - YENI: ADX (Average Directional Index, 14 periyot, Wilder yontemi)
       hesaplaniyor. ADX < ADX_MIN_ESIK (20) ise piyasa yatay/whipsaw
       kabul edilir ve o coin'e GIRILMEZ (ELENDI_ZAYIF_TREND).
     - Izleme listesi artik ADX gucune gore siralaniyor - bos slot
       aciliginda en guclu trendli aday once denenir.

  4) FORMATLAMA DUZELTMESI:
     - Tum tablo f-string'lerine (acik pozisyonlar, islem gecmisi)
       alanlar arasina ACIK BOSLUK ayiraclari eklendi - genislik
       dolgusuna guvenmek yerine garanti ayrisma saglaniyor.

  5) AG DAYANIKLILIGI:
     - Genel API cagrilari zaten v10'dan beri http_istek_yap() ile
       exponential backoff kullaniyordu (429/5xx/ConnectionResetError
       dahil OSError turevleri). v13'te Telegram da ayni desene EKLENDI
       (madde 1).

======================================================================
v12 farki - RISK/ODUL ASIMETRISI DUZELTMESI (v9/v10/v11 cekirdegi DEGISMEDI):

  SORUN TESPITI (v11'de): Sabit stop-loss %8 iken grid basamak mesafesi
  ~%1.5'ti; komisyon+slipaj sonrasi net kar islem basina ~%1.1 eklerken
  tek bir stop-loss kasadan %8 goturuyordu (1 zarari telafi icin 6-7
  karli islem gerekiyordu). Trailing-stop da pozisyon daha %1-2 kardayken
  tetiklenip komisyon zarariyla kapaniyordu.

  COZUM - UC KADEMELI, BIRBIRINI RATCHET (SADECE YUKARI KILITLEYEN) STOP SISTEMI:

  1) RISK/ODUL YENIDEN YAPILANDIRILDI:
     - STOP_LOSS_PCT: %8 -> %4 (taban risk yariya indi).
     - Grid basamagi genisletildi: VARSAYILAN_WIDTH_PCT=0.16 +
       VARSAYILAN_GRID_SAYISI=4 -> basamak basina ~%4 mesafe, komisyon+
       slipaj sonrasi net ~%3.5-3.7 kar hedefi.

  2) KADEMELI, AKTIVASYON ESIKLI TRAILING-STOP:
     - TRAILING_AKTIVASYON_PCT=%3.5: fiyat (tepe nokta uzerinden) giris
       fiyatinin en az %3.5 UZERINE cikmadan trailing-stop DEVREYE
       GIRMEZ - erken stop-out'lar engellendi.
     - Aktive olduktan sonra tepeden %1.8 (TRAILING_STOP_PCT) geri
       cekilme kari kilitler.

  3) BASA-BAS (BREAKEVEN) KORUMASI:
     - Pozisyon (tepe noktada) %2.5 kara ulastigi an (BREAKEVEN_
       AKTIVASYON_PCT), stop seviyesi giris fiyati + komisyon tamponuna
       CEKILIR - o noktadan sonra pozisyon ASLA net zararla kapanamaz.

  Uc kademe de RATCHET mantigiyla birlesir: her tick'te uc olasi stop
  seviyesi (sabit stop-loss, basa-bas, trailing) hesaplanir ve HANGISI
  aktifse VE en yuksekse (en korumaci) o kullanilir - stop seviyesi asla
  geriye/asagi gitmez.

======================================================================
v11 farki - X/Z RAPORLAMA (v9/v10'un cekirdegi DEGISTIRILMEDI):

  6) GUNLUK X RAPORU (her 24 saatte bir):
     - Sayac SIFIRLANMAZ, geride kalan son 24 saatin operasyonel ara
       bilancosu cikarilir: toplam portfoy, gunluk realize K/Z (TRY ve
       %), alim/satim sayisi, win rate, 24 saatlik komisyon, acik
       pozisyonlarin anlik durumu. Konsola tablo olarak basilir VE
       Telegram'a gonderilir. Rapor sonrasi SADECE 24 saatlik sayaclar
       sifirlanir (aylik/Z sayaclari etkilenmez).

  7) AYLIK Z RAPORU (her 30 gunde bir):
     - 30 gunluk kumulatif donem KAPATILIR: donem basi/sonu sermaye, net
       K/Z, maksimum cekilme (donem boyunca sureklilikle takip edilen
       drawdown), toplam komisyon faturasi, en cok kazandiran/
       kaybettiren coin, toplam islem adedi. 'project_aurelius_
       z_raporlari.csv' dosyasina kalici satir olarak eklenir ve
       Telegram'a oncelikli bildirim olarak gonderilir. Rapor sonrasi
       yeni bir 30 gunluk donem baslatilir (sayaclar sifirlanir).

  8) ZAMANLAYICI VE DAYANIKLILIK:
     - Zamanlama kontrolu ana dongu icinde datetime farklariyla yapilir
       (schedule/celery gibi ek kutuphane KULLANILMAZ).
     - X/Z rapor zaman damgalari ve donemsel sayaclar 'project_aurelius_
       state.json' icine kaydedilir - bot yeniden baslatildiginda 24
       saatlik/30 gunluk sayaclar SIFIRLANMAZ, kaldigi yerden devam eder.

======================================================================
v10 farki - BES KRITIK KATMAN (v9'un risk/strateji cekirdegi DEGISTIRILMEDI):

  1) KALICI DURUM YONETIMI (State Persistence - JSON):
     - 'project_aurelius_state.json' dosyasi acik pozisyonlari, giris
       fiyatlarini, trailing-stop icin en yuksek gorulen fiyatlari ve
       merkezi kasa bakiyesini kalici tutar.
     - Her ALIM/SATIM ve her tick sonunda dosya guncellenir (atomic
       yazma: once .tmp dosyasina yazilir, sonra os.replace ile
       degistirilir - yarim/bozuk dosya riski yok).
     - Acilista dosya varsa okunur ve kaldigi yerden devam edilir;
       yoksa TOPLAM_SANAL_BAKIYE_TRY (5.000 TL) ile temiz baslar.

  2) TELEGRAM BILDIRIM ENTEGRASYONU:
     - send_telegram(mesaj) fonksiyonu os.getenv("TELEGRAM_BOT_TOKEN") ve
       os.getenv("TELEGRAM_CHAT_ID") okur. Ikisi de tanimliysa ALIM,
       SATIM (Kar-Al/Stop-Loss/Trailing-Stop/Acil-Tasfiye), Acil Fren ve
       periyodik ozet raporlarinda mesaj gonderir. Tanimli degilse veya
       herhangi bir hata olursa SESSIZCE gecer, botu asla durdurmaz.

  3) TAHTA DERINLIGI & SPREAD FILTRESI:
     - Her ALIM'dan hemen once orderbook (/api/v3/depth, limit=5)
       sorgulanir. En iyi alis/satis arasindaki spread MAX_SPREAD_PCT
       (%0.5) ustundeyse emir GONDERILMEZ, "likidite sig" olarak
       loglanir - kayma/slipaj tuzagina karsi koruma.

  4) CIFT CALISMA MODU - CANLI (LIVE) & DRY-RUN (SIMULATION):
     - CANLI_MOD=False (varsayilan): 5.000 TL sanal kasa ile tam
       simulasyon, v9 ile ayni.
     - CANLI_MOD=True: BINANCE_TR_API_KEY / BINANCE_TR_SECRET_KEY ortam
       degiskenlerini dogrular, /open-api/v3/account'tan GERCEK serbest
       TRY bakiyesini ceker ve MerkeziKasa ile esitler, evaluate_v9 ve
       acil_tasfiye icindeki her alim/satimda RFC 2104 HMAC-SHA256
       imzali GERCEK MARKET emrini /open-api/v3/order'a gonderir.
       LOT_SIZE (stepSize) yuvarlamasi ve minNotional kontrolu emirden
       ONCE yapilir; kontrolu gecemeyen ya da borsa tarafindan
       reddedilen emirler ic durumu GUNCELLEMEZ (ic muhasebe ile gercek
       borsa durumu arasinda sapma onlenir).
     - EK GUVENLIK KILIDI: CANLI_MOD=True olsa BILE, ortam degiskeni
       olarak AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN tanimli
       degilse bot CANLI baslamaz. Bu, kod icindeki tek bir bayragin
       yanlislikla True birakilmasina karsi bilincli EK bir korumadir.

  5) DAYANIKLILIK VE HATA YAKALAMA:
     - Tum HTTP cagrilari http_istek_yap() uzerinden gecer: ag kopmasi
       veya HTTP 429/5xx durumunda exponential backoff ile (2sn, 4sn,
       8sn... max 60sn, en fazla 5 deneme) otomatik tekrar dener. Bot
       COKMEZ, sadece bekler ve devam eder.

Mevcut strateji cekirdegi (EMA50 trend filtresi, RSI14 giris filtresi,
trailing-stop/stop-loss, cooldown+mutex, merkezi kasa, grid araligi/
adimi, backtest fonksiyonu, CSV loglama formati) v9-v13 ile ayni
mantikla calisir - v14'te SADECE pozisyon SAYISI/BUYUKLUGU sabit
degil, dinamik (bkz. yukarida BOLUM 1).

Dis agir kutuphane KULLANILMADI: sadece urllib, hmac, hashlib, json,
time, os, decimal (standart kutuphane).

=============================================================================
ONEMLI - CANLI MOD HAKKINDA LUTFEN DIKKATLE OKUYUN:
=============================================================================
Bu script CANLI_MOD=True yapildiginda GERCEK PARA ile GERCEK BORSA EMRI
gonderir. Bu bir yatirim tavsiyesi degildir ve KESIN KAR GARANTISI
VERMEZ - kripto para piyasalari yuksek risklidir, sermayenizin tamamini
kaybedebilirsiniz. Binance TR'nin GERCEK ozel (imzali) API yol yapisi
(/open-api/v3/account, /open-api/v3/order) resmi olarak genis capli
indekslenmis bir dokumantasyona sahip degildir; bu kod sizin belirttiginiz
yol yapisini temel alir ancak CANLI_MOD=True ile calistirmadan once bu
adresleri MUTLAKA kendi guncel Binance TR API dokumantasyonunuzdan/API
saglayicinizdan DOGRULAYIN ve KUCUK TUTARLARLA once test edin. Bu kod
partial-fill (kismi gerceklesme) durumlarini veya emir durumu sorgulamasini
YAPMAZ; her emir tek seferde MARKET emri olarak gonderilir ve sonucu
dogrudan API yanitindan okunur.

Kullanim:
    python project_aurelius_bot_v17.py                          (canli/simulasyon - CANLI_MOD bayragina gore)
    python project_aurelius_bot_v17.py backtest SEMBOL GUN [SERMAYE]  (backtest - her zaman simulasyon)
"""

import time
import random
import urllib.request
import urllib.parse
import urllib.error
import hmac
import hashlib
import json
import csv
import os
import sys
import logging
import threading
import queue
from decimal import Decimal, ROUND_DOWN
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

# ----------------------------------------------------------------------
# AYARLAR
# ----------------------------------------------------------------------
# Coinleri elle listelemiyoruz. Bot acilista Binance TR'nin exchangeInfo
# uc noktasindan TRY ile islem goren TUM aktif pariteleri ceker ve
# kriterleri karsilayanlari (esnek sayida) izlemeye alir.

TOPLAM_SANAL_BAKIYE_TRY = 5_000        # v10: 5.000 TL'ye guncellendi
TABAN_POZISYON_TUTARI = 300.0          # v17: 1.500 -> 300 TL (kucuk kasalarda esnek tek-aday odaklanmasi)

# v17 MODUL 1: Kasaya gore ADAPTIF sermaye kademeleri (dinamik_pozisyon_planla).
# Toplam kasa (serbest nakit + acik pozisyonlarin guncel piyasa degeri) bu
# esiklere gore SNIPER MODU'na veya kademeli portfoy kapasitesine tabidir.
SNIPER_MODU_ESIGI_TRY = 1500.0         # bu esigin ALTINDA -> Sniper Modu, KESINLIKLE 1 pozisyon
KADEME_2_ESIGI_TRY = 3500.0            # 1.500 - 3.500 TL -> en fazla 2 pozisyon
KADEME_3_ESIGI_TRY = 7500.0            # 3.500 - 7.500 TL -> en fazla 3 pozisyon
KADEME_4_ESIGI_TRY = 15000.0           # 7.500 - 15.000 TL -> en fazla 4 pozisyon
KASA_KAPASITESI_TAVAN = 6              # >= 15.000 TL -> en fazla 6 pozisyon (tavan sinir)
BTC_GUCLU_YUKSELIS_PCT = 1.5           # v14: BTC 24s bu esigin ustundeyse tam kapasite kullanilir

# v17 MODUL 1.2: Kalite onceligi - bos slot olsa dahi SADECE bu araligi VE
# ADX_MIN_ESIK'i birlikte karsilayan en yuksek ADX'li adaya girilir.
RSI_KALITE_ALT_ESIK = 38
RSI_KALITE_UST_ESIK = 60

MIN_WATCHLIST = 1
MAX_WATCHLIST = 8
COOLDOWN_MINUTES = 30
SCAN_INTERVAL_MINUTES = 5
ASSET_REFRESH_HOURS = 4
API_CALL_SLEEP_SECONDS = 0.5
BTC_DUSUS_ESIGI_PCT = -5.0

# Risk yonetimi ayarlari - v12: +EV (pozitif beklenti) icin yeniden yapilandirildi
STOP_LOSS_PCT = 0.04                   # v12: %8 -> %4 (taban risk yariya indirildi)
TRAILING_AKTIVASYON_PCT = 0.035        # v12: fiyat (tepe) giristen %3.5 uzaklasmadan trailing DEVREYE GIRMEZ
TRAILING_STOP_PCT = 0.018              # v12: aktive olduktan sonra tepeden %1.8 geri cekilme kari kilitler
BREAKEVEN_AKTIVASYON_PCT = 0.025       # v12: pozisyon (tepe) %2.5 kara ulasinca stop basa-basa cekilir
MAX_DRAWDOWN_PCT = 0.20
TRAILING_STOP_AKTIF = True

# v13: Kademeli kar alma (pozisyonun bir kismini erken realize et)
KISMI_KAR_AL_PCT = 0.02                # %2 karda pozisyonun bir kismi ANINDA realize edilir
KISMI_KAR_AL_ORANI = 0.5               # realize edilecek oran (0.5 = pozisyonun yarisi satilir)

# v13: ADX (trend gucu) filtresi - whipsaw/yatay piyasa korumasi
ADX_PERIYOT = 14
ADX_MIN_ESIK = 20                      # ADX bu esigin altindaysa piyasa yatay/whipsaw kabul edilir, GIRILMEZ

# v16 BOLUM 1: Zaman bazli bayat pozisyon cikisi
MAKS_POZISYON_OMRU_SAAT = 18.0         # bu sureyi asan VE kari yetersiz pozisyonlar zorla kapatilir
ZAMAN_ASIMI_KAR_ESIGI_PCT = 0.01       # %1 - bu esigin altindaki kar "yetersiz" sayilir

# v16 BOLUM 2: Sonuca dayali dinamik cooldown (dakika)
COOLDOWN_KAR_DAKIKA = 15.0             # KAR-AL / TRAILING-STOP ile kapanista
COOLDOWN_ZARAR_DAKIKA = 90.0           # STOP-LOSS / BREAKEVEN-STOP / ACIL-TASFIYE ile kapanista
COOLDOWN_ZAMAN_ASIMI_DAKIKA = 45.0     # ZAMAN-ASIMI ile kapanista

# v16 BOLUM 3: ATR tabanli dinamik grid genisligi (volatilite adaptasyonu)
ATR_PERIYOT = 14
ATR_DUSUK_VOLATILITE_ORAN = 0.015      # ATR/fiyat bu oranin ALTINDAYSA dusuk volatilite (BTC/ETH tarzi)
ATR_YUKSEK_VOLATILITE_ORAN = 0.035     # ATR/fiyat bu oranin USTUNDEYSE yuksek volatilite (hareketli altcoin)
WIDTH_PCT_DUSUK_VOL = 0.11             # ~%2.75 basamak (hizli kar al / hizli devir)
WIDTH_PCT_ORTA_VOL = 0.16              # ~%4 basamak (eski sabit varsayilan)
WIDTH_PCT_YUKSEK_VOL = 0.21            # ~%5.25 basamak (buyuk dalgalari yakala)

# v16 BOLUM 4: Canli mod bakiye mutabakati
MUTABAKAT_ARALIGI_SAAT = 6.0

# Trend filtresi ayarlari (EMA50 tabanli) - DEGISTIRILMEDI
EMA_PERIYOT = 50
TREND_ESIK_PCT = 0.02
KLINE_INTERVAL_TREND = "1h"
KLINE_LIMIT_TREND = 60

# RSI giris filtresi ayarlari - DEGISTIRILMEDI
RSI_PERIYOT = 14
RSI_ASIRI_ALIM_ESIGI = 60
RSI_GIRIS_UST_ESIGI = 50
RSI_BEKLEME_KONTROL_ARALIGI_TUR = 2

# CSV kayit dosyalari + v10 STATE dosyasi - script ile ayni klasore yazilir
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ISLEMLER_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_islemler.csv")
PORTFOY_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_portfoy_gecmisi.csv")
STATE_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius_state.json")  # v10
Z_RAPORLARI_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_z_raporlari.csv")  # v11
LOG_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius.log")  # v13

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

VARSAYILAN_WIDTH_PCT = 0.16            # v12: %12 -> %16 (basamak basina ~%4 mesafe icin)
VARSAYILAN_GRID_SAYISI = 4             # v12: 8 -> 4 (0.16/4 = %4 basamak - net ~%3.5-3.7 kar hedefi)

# Eleme kriterleri (24 saatlik istatistiklere gore) - DEGISTIRILMEDI
MIN_HACIM_TRY = 500_000
MIN_HAREKETLILIK_PCT = 0.5
MAX_HAREKETLILIK_PCT = 20.0
YON_FILTRESI_MIN_DEGISIM_PCT = -8.0

# Genel/public piyasa verisi uc noktalari (fiyat, kline, ticker, orderbook, exchangeInfo)
EXCHANGE_INFO_URL = "https://api.binance.me/api/v3/exchangeInfo"
TICKER_24H_URL = "https://api.binance.me/api/v3/ticker/24hr"
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
    return str(deger).strip()


# v17 FIX - Ortam degiskenlerinden okunan kimlikler. Artik _ortam_degiskeni_str_oku()
# ile okunuyor - anahtarlar HER ZAMAN temiz birer str, asla tuple/list olamaz
# (bkz. yukaridaki fonksiyon dokumantasyonu).
TELEGRAM_BOT_TOKEN = _ortam_degiskeni_str_oku("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = _ortam_degiskeni_str_oku("TELEGRAM_CHAT_ID")
BINANCE_TR_API_KEY = _ortam_degiskeni_str_oku("BINANCE_TR_API_KEY")
BINANCE_TR_SECRET_KEY = _ortam_degiskeni_str_oku("BINANCE_TR_SECRET_KEY")

REAL_POLL_INTERVAL_SECONDS = 25
SUB_TICK_SECONDS = 2
SUB_TICKS_PER_REAL_POLL = REAL_POLL_INTERVAL_SECONDS // SUB_TICK_SECONDS
MICRO_WIGGLE_PCT = 0.0015
SUMMARY_EVERY_N_REAL_POLLS = 3

# Gercekcilik ayarlari
GERCEKCI_MOD = True
KOMISYON_PCT = 0.0010
SLIPAJ_MIN_PCT = 0.0005
SLIPAJ_MAKS_PCT = 0.0020

GUVENLI_MARJ_KATSAYISI = 2.0

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
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            son_hata = e
            if e.code == 429 or e.code >= 500:
                print(f"{YELLOW}  HTTP {e.code} alindi ({deneme}/{max_deneme}), "
                      f"{gecikme:.1f}sn sonra tekrar denenecek...{RESET}")
                time.sleep(gecikme)
                gecikme = min(gecikme * 2, BACKOFF_MAX_SANIYE)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            son_hata = e
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
    """
    Acik pozisyonlari, giris fiyatlarini, trailing-stop icin en yuksek
    gorulen fiyatlari, merkezi kasa bakiyesini VE (v11) X/Z rapor zaman
    damgalari ile donemsel sayaclari JSON dosyasina ATOMIK olarak yazar
    (once .tmp dosyasina yazip os.replace ile degistirir - yazma
    sirasinda bot cokerse bile dosya asla yarim/bozuk kalmaz).
    """
    try:
        veri = {
            "kasa_bakiye": kasa.bakiye,
            "kasa_baslangic": kasa.baslangic,
            "kasa_toplam_komisyon": kasa.toplam_komisyon,
            "kaydedilme_zamani": datetime.now().isoformat(),
            "pozisyonlar": {},
        }
        if rapor is not None:
            veri["raporlama"] = rapor.to_dict()  # v11
        for sym, b in pozisyonlar.items():
            veri["pozisyonlar"][sym] = {
                "coin_name": b.coin_name,
                "width_pct": b.width_pct,
                "grid_count": b.grid_count,
                "starting_try": b.starting_try,
                "cash_try": b.cash_try,
                "coin_qty": b.coin_qty,
                "trade_count": b.trade_count,
                "realized_pnl": b.realized_pnl,
                "toplam_komisyon": b.toplam_komisyon,
                "lower": b.lower,
                "upper": b.upper,
                "initialized": b.initialized,
                "bekliyor": b.bekliyor,
                "bekleme_sayaci": b.bekleme_sayaci,
                "son_satis_zamani": b.son_satis_zamani.isoformat() if b.son_satis_zamani else None,
                "alis_zamani": b.alis_zamani.isoformat() if b.alis_zamani else None,  # v16
                "son_cooldown_dakika": b.son_cooldown_dakika,  # v16
                "grid": [
                    {
                        "price": lvl.price,
                        "has_position": lvl.has_position,
                        "buy_qty": lvl.buy_qty,
                        "buy_price": lvl.buy_price,
                        "en_yuksek_fiyat": lvl.en_yuksek_fiyat,
                        "kismi_kar_alindi": lvl.kismi_kar_alindi,
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


def durumu_yukle() -> Optional[dict]:
    """v10: STATE_DOSYASI varsa okur ve dondurur. Yoksa veya bozuksa
    None doner (bu durumda temiz baslangic yapilir)."""
    if not os.path.exists(STATE_DOSYASI):
        return None
    try:
        with open(STATE_DOSYASI, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"{RED}  (Durum dosyasi okunamadi, temiz baslangic yapilacak: {e}){RESET}")
        return None


def durumdan_kasa_ve_pozisyonlar_olustur(veri: dict):
    """v10: Kaydedilmis JSON verisinden MerkeziKasa ve CoinBot nesnelerini
    yeniden insa eder - bot kaldigi yerden aynen devam eder."""
    kasa = MerkeziKasa(veri.get("kasa_baslangic", TOPLAM_SANAL_BAKIYE_TRY))
    kasa.bakiye = veri.get("kasa_bakiye", kasa.baslangic)
    kasa.toplam_komisyon = veri.get("kasa_toplam_komisyon", 0.0)

    pozisyonlar = {}
    for sym, p in veri.get("pozisyonlar", {}).items():
        b = CoinBot(
            symbol=sym,
            coin_name=p.get("coin_name", sym.replace("TRY", "")),
            width_pct=p.get("width_pct", VARSAYILAN_WIDTH_PCT),
            grid_count=p.get("grid_count", VARSAYILAN_GRID_SAYISI),
            starting_try=p.get("starting_try", 0.0),
            tek_pozisyon_modu=True,
            bekliyor=p.get("bekliyor", False),
            bekleme_sayaci=p.get("bekleme_sayaci", 0),
        )
        b.cash_try = p.get("cash_try", b.starting_try)
        b.coin_qty = p.get("coin_qty", 0.0)
        b.trade_count = p.get("trade_count", 0)
        b.realized_pnl = p.get("realized_pnl", 0.0)
        b.toplam_komisyon = p.get("toplam_komisyon", 0.0)
        b.lower = p.get("lower", 0.0)
        b.upper = p.get("upper", 0.0)
        b.initialized = p.get("initialized", False)
        son_satis = p.get("son_satis_zamani")
        b.son_satis_zamani = datetime.fromisoformat(son_satis) if son_satis else None
        alis = p.get("alis_zamani")  # v16
        b.alis_zamani = datetime.fromisoformat(alis) if alis else None
        b.son_cooldown_dakika = p.get("son_cooldown_dakika", COOLDOWN_MINUTES)  # v16
        b.grid = [
            GridLevel(
                price=lvl["price"],
                has_position=lvl["has_position"],
                buy_qty=lvl["buy_qty"],
                buy_price=lvl["buy_price"],
                en_yuksek_fiyat=lvl["en_yuksek_fiyat"],
                kismi_kar_alindi=lvl.get("kismi_kar_alindi", False),
            )
            for lvl in p.get("grid", [])
        ]
        pozisyonlar[sym] = b

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

        return http_istek_yap(req, timeout=15)

    except urllib.error.HTTPError as e:
        try:
            ham_govde = e.read().decode("utf-8", errors="replace")
        except Exception:
            ham_govde = "(govde okunamadi)"
        print(f"{RED}  BINANCE TR IMZALI ISTEK HATASI ({method} {path}): "
              f"HTTP {e.code} -> {ham_govde}{RESET}")
        logger.error("Binance TR imzali istek HTTP hatasi (%s %s): kod=%s ham_govde=%s",
                     method, path, e.code, ham_govde)
        raise
    except Exception as e:
        print(f"{RED}  BINANCE TR IMZALI ISTEK BEKLENMEYEN HATA ({method} {path}): {e}{RESET}")
        logger.error("Binance TR imzali istek beklenmeyen hata (%s %s): %s", method, path, e)
        raise


def _binance_tr_bakiye_listesini_cikar(veri) -> list:
    """
    v17 FIX: Binance TR'nin /open/v1/account/spot yaniti Binance Global'den
    FARKLI bir "zarf" (envelope) kullanir - bakiye listesi yanitin KOK
    dizininde DEGIL, "data" sozlugu altinda gelir:
        {"code": 0, "data": {"balances": [...]}}   VEYA
        {"code": 0, "data": {"assets":   [...]}}
    Eski kod dogrudan veri.get("balances", []) aradigi icin liste HER ZAMAN
    bos donuyor ve cuzdanda serbest TRY olsa bile bakiye SESSIZCE 0.00 TRY
    basiliyordu. Bu fonksiyon HER IKI bilinen sekli de destekler; ayrica:
      - "code" alani 0'dan FARKLIYSA (API seviyesinde hata donmus demektir,
        orn. yetkisiz istek) HAM YANITI loglar ve bos liste dondurur.
      - Beklenmeyen/tanimadigi bir format gelirse (borsa API'sini
        degistirmis olabilir) HAM YANITI loglar ve bos liste dondurur -
        boylece sorun "hep 0.00 TRY" yerine log dosyasinda GORUNUR olur.
    """
    if not isinstance(veri, dict):
        logger.error("Binance TR hesap yaniti beklenmeyen tip (%s): %r", type(veri).__name__, veri)
        return []

    kod = veri.get("code")
    if kod not in (0, None):
        mesaj = veri.get("msg") or veri.get("message") or "(mesaj yok)"
        print(f"{RED}  BINANCE TR HESAP SORGUSU API HATASI DONDURDU: code={kod} msg={mesaj}{RESET}")
        logger.error("Binance TR hesap sorgusu API hatasi: code=%s msg=%s ham_yanit=%r", kod, mesaj, veri)
        return []

    data = veri.get("data")
    if isinstance(data, dict):
        if isinstance(data.get("balances"), list):
            return data["balances"]
        if isinstance(data.get("assets"), list):
            return data["assets"]

    # Geriye donuk uyumluluk: bazi eski/alternatif yanitlarda liste
    # dogrudan kok dizinde olabilir.
    if isinstance(veri.get("balances"), list):
        return veri["balances"]

    print(f"{RED}  BINANCE TR HESAP YANITI BEKLENMEYEN FORMATTA - ham yanit log dosyasina yazildi.{RESET}")
    logger.error("Binance TR hesap yanitinda 'data.balances'/'data.assets' bulunamadi - ham yanit: %r", veri)
    return []


def binance_serbest_try_bakiyesi() -> float:
    """
    v17 FIX: /open/v1/account/spot uzerinden GERCEK serbest TRY bakiyesini
    ceker. Bakiye listesi artik _binance_tr_bakiye_listesini_cikar() ile,
    Binance TR'nin gercek "data.balances"/"data.assets" zarfina uygun
    sekilde okunuyor (eskiden kok dizinde aranip HEP bos donuyordu, bu
    yuzden TRY bakiyesi cuzdanda para olsa bile hep 0.00 TRY basiliyordu).
    Alan adi olarak once "asset" (Binance-stili), yoksa "coin"/"currency"
    denenir; miktar icin once "free", yoksa "available" denenir - borsanin
    tam alan adlandirmasi teyit edilene kadar esneklik icin.
    """
    veri = binance_signed_request("GET", ACCOUNT_ENDPOINT_PATH)
    # v17 FIX: ham borsa yanitini HER ZAMAN terminale bas - olasi API hata
    # kodlarini (orn. code=-2015 Invalid API-key) gozle GORMEK icin. Bu,
    # logger.error ile 'project_aurelius.log' dosyasina yazilan kayda EKtir,
    # onun yerine gecmez.
    print(f"{GRAY}[BORSA YANITI]: {veri!r}{RESET}")
    for bakiye in _binance_tr_bakiye_listesini_cikar(veri):
        if not isinstance(bakiye, dict):
            continue
        asset_adi = bakiye.get("asset") or bakiye.get("coin") or bakiye.get("currency")
        if asset_adi != "TRY":
            continue
        serbest = bakiye.get("free")
        if serbest is None:
            serbest = bakiye.get("available", 0.0)
        try:
            return float(serbest)
        except (TypeError, ValueError):
            logger.error("Binance TR TRY bakiyesi sayiya cevrilemedi, ham kayit: %r", bakiye)
            return 0.0

    logger.warning("Binance TR hesap yanitinda TRY varligi bulunamadi - ham yanit: %r", veri)
    return 0.0


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
        gercek_bakiye = binance_serbest_try_bakiyesi()
        eski_bakiye = kasa.bakiye
        fark = gercek_bakiye - eski_bakiye
        kasa.bakiye = gercek_bakiye
        if abs(fark) > 0.01:
            print(f"{CYAN}  MUTABAKAT: Kasa bakiyesi borsa ile senkronize edildi "
                  f"({eski_bakiye:,.2f} -> {gercek_bakiye:,.2f} TRY, fark: {fark:+,.2f}){RESET}")
            logger.warning("Mutabakat: kasa bakiyesi %.2f -> %.2f (fark %.2f)", eski_bakiye, gercek_bakiye, fark)

        hesap = binance_signed_request("GET", ACCOUNT_ENDPOINT_PATH)
        print(f"{GRAY}[BORSA YANITI]: {hesap!r}{RESET}")  # v17 FIX: ham yaniti gozle gor
        # v17 FIX: ayni "data.balances"/"data.assets" zarfi burada da
        # kullaniliyor - eskiden hesap.get("balances", []) hep bos donup
        # coin miktari mutabakati SESSIZCE hicbir sey yapmiyordu.
        borsa_bakiyeleri = {
            (b.get("asset") or b.get("coin") or b.get("currency")):
                float(b.get("free") or b.get("available") or 0) + float(b.get("locked") or b.get("frozen") or 0)
            for b in _binance_tr_bakiye_listesini_cikar(hesap)
            if isinstance(b, dict)
        }
        for bot in pozisyonlar.values():
            if not bot.has_open_position:
                continue
            gercek_miktar = borsa_bakiyeleri.get(bot.coin_name)
            if gercek_miktar is None:
                continue
            fark_miktar = abs(gercek_miktar - bot.coin_qty)
            esik = max(1e-8, bot.coin_qty * 0.001)  # binde 1'den fazla sapma varsa senkronize et
            if fark_miktar > esik:
                print(f"{CYAN}  MUTABAKAT: {bot.symbol} miktari senkronize edildi "
                      f"({bot.coin_qty:.8f} -> {gercek_miktar:.8f}){RESET}")
                logger.warning("Mutabakat: %s miktari %.8f -> %.8f", bot.symbol, bot.coin_qty, gercek_miktar)
                bot.coin_qty = gercek_miktar
                acik_seviye = next((lvl for lvl in bot.grid if lvl.has_position), None)
                if acik_seviye:
                    acik_seviye.buy_qty = gercek_miktar
    except Exception as e:
        print(f"{RED}  MUTABAKAT basarisiz (bir sonraki denemede tekrar denenecek): {e}{RESET}")
        logger.error("Mutabakat basarisiz: %s", e)


_sembol_filtre_onbellek: dict = {}


def sembol_filtrelerini_getir(symbol: str) -> dict:
    """v10: LOT_SIZE (stepSize) ve MIN_NOTIONAL degerlerini exchangeInfo
    uzerinden ceker ve onbellege alir (her emirde tekrar cekmemek icin)."""
    if symbol in _sembol_filtre_onbellek:
        return _sembol_filtre_onbellek[symbol]

    req = urllib.request.Request(EXCHANGE_INFO_URL, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=20)

    sonuc = {"step_size": None, "min_notional": None}
    for s in data.get("symbols", []):
        if s.get("symbol") == symbol:
            for f in s.get("filters", []):
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
    miktar = Decimal(str(qty))
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
    olmalidir. Bu fonksiyon partial-fill (kismi gerceklesme) durumunu
    ayrica sorgulamaz - tek seferlik MARKET emri gonderir ve borsanin
    dondurdugu yaniti aynen dondurur (ham yaniti da [BORSA YANITI] ile
    terminale basar - GERCEK PARAYLA ILK EMIRDEN SONRA bu satiri borsa
    arayuzunuzdeki islem gecmisiyle MUTLAKA karsilastirin).
    """
    params = {
        "symbol": symbol,
        "side": ORDER_SIDE_KODU.get(side, side),
        "type": ORDER_TIPI_MARKET_KODU,
        "quantity": f"{quantity:.8f}".rstrip("0").rstrip("."),
    }
    sonuc = binance_signed_request("POST", ORDER_ENDPOINT_PATH, params)
    print(f"{GRAY}[BORSA YANITI]: {sonuc!r}{RESET}")
    return sonuc


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

    if os.getenv("AURELIUS_LIVE_CONFIRM", "") != "EVET_GERCEK_PARA_KULLAN":
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
    price: float
    has_position: bool = False
    buy_qty: float = 0.0
    buy_price: float = 0.0
    en_yuksek_fiyat: float = 0.0
    kismi_kar_alindi: bool = False  # v13: kademeli kar alma bu seviyede bir kez yapildi mi


def _cooldown_suresi_hesapla(tag: str) -> float:
    """
    v16 BOLUM 2: Islem SONUCUNA (kapanis etiketine) gore dinamik cooldown
    suresi (dakika) dondurur.
      - KAR-AL / TRAILING-STOP  -> 15 dk (guclu trendi erken yeniden yakala)
      - ZAMAN-ASIMI             -> 45 dk
      - STOP-LOSS / BREAKEVEN-STOP / ACIL-TASFIYE -> 90 dk

    NOT (tasarim karari): BREAKEVEN-STOP, kullanicinin spesifik olarak
    belirtmedigi bir kategori. Teknik olarak kucuk bir NET KAR ile
    kapanir (v12'nin komisyon+slipaj tamponu sayesinde), ancak pozisyonun
    guclu bir trend GOSTEREMEDIGINI (sadece basa-basa zar zor ulasabildigini)
    ifade eder - bu yuzden "zarar/notr" grubuna (90dk) dahil edildi, "kar"
    grubuna (15dk) DEGIL. ACIL-TASFIYE de (portfoy capinda acil fren)
    aynı temkinli gruba alindi.
    """
    if tag in ("KAR-AL", "TRAILING-STOP"):
        return COOLDOWN_KAR_DAKIKA
    if tag == "ZAMAN-ASIMI":
        return COOLDOWN_ZAMAN_ASIMI_DAKIKA
    if tag in ("STOP-LOSS", "BREAKEVEN-STOP", "ACIL-TASFIYE"):
        return COOLDOWN_ZARAR_DAKIKA
    return COOLDOWN_MINUTES  # bilinmeyen etiket icin guvenli varsayilan


def kademe_kapasitesi_hesapla(toplam_kasa: float) -> int:
    """
    v17 MODUL 1: Toplam kasa (serbest nakit + acik pozisyonlarin guncel
    piyasa degeri) buyuklugune gore, BTC rejiminden BAGIMSIZ TABAN pozisyon
    kapasitesini dondurur:
      < 1.500 TL           -> 1  (Sniper Modu - sermaye ASLA bolunmez)
      1.500 - 3.500 TL     -> 2
      3.500 - 7.500 TL     -> 3
      7.500 - 15.000 TL    -> 4
      >= 15.000 TL         -> 6  (tavan)
    """
    if toplam_kasa < SNIPER_MODU_ESIGI_TRY:
        return 1
    if toplam_kasa < KADEME_2_ESIGI_TRY:
        return 2
    if toplam_kasa < KADEME_3_ESIGI_TRY:
        return 3
    if toplam_kasa < KADEME_4_ESIGI_TRY:
        return 4
    return KASA_KAPASITESI_TAVAN


def dinamik_pozisyon_planla(kasa_bakiye: float, toplam_kasa: float, btc_degisim: Optional[float]):
    """
    v17 MODUL 1: KASAYA GORE ADAPTIF SERMAYE VE SNIPER MODU. Her tick'te
    GUNCEL toplam kasaya (serbest nakit + acik pozisyonlarin piyasa
    degeri) ve BTC'nin 24 saatlik gucune gore kac pozisyon acilabilecegini
    VE pozisyon basina ne kadar sermaye ayrilacagini YENIDEN hesaplar.

    - Toplam kasa 1.500 TL ALTINDAYSA (Sniper Modu): izin verilen pozisyon
      KESINLIKLE 1'dir (BTC sert dususu haric - o zaman 0), sermaye asla
      2+ parcaya bolunmez; hedef_pozisyon_tutari DOGRUDAN serbest kasaya
      (kasa_bakiye) esitlenir - boylece 500-1.000 TL gibi kucuk sermayeler
      tek bir guclu adaya tam kapasiteyle yonlendirilir, minNotional
      takilmalari/parcali emir reddi engellenir.
    - Toplam kasa >= 1.500 TL ise kademeli portfoy kapasitesi (bkz.
      kademe_kapasitesi_hesapla) ve klasik BTC 24s carpani (sert duste 0,
      notr/kararsizda yari kapasite - taban 1, guclu yukseliste tam
      kapasite) birlikte uygulanir.

    Donus: (izin_verilen_pozisyon: int, hedef_pozisyon_tutari: float,
            sniper_modu_aktif: bool)
    """
    if toplam_kasa <= 0 or kasa_bakiye <= 0:
        return 0, 0.0, False

    sniper_modu_aktif = toplam_kasa < SNIPER_MODU_ESIGI_TRY
    temel_kapasite = kademe_kapasitesi_hesapla(toplam_kasa)

    if btc_degisim is not None and btc_degisim <= BTC_DUSUS_ESIGI_PCT:
        # v17: BTC sert dususteyse KASA NE OLURSA OLSUN %100 nakit koruma
        return 0, 0.0, sniper_modu_aktif

    if btc_degisim is None:
        izin_verilen = max(1, temel_kapasite // 2)  # veri yok - temkinli/savunma modu
    elif btc_degisim > BTC_GUCLU_YUKSELIS_PCT:
        izin_verilen = temel_kapasite  # BTC guclu yukseliste -> tam kapasite
    else:
        izin_verilen = max(1, temel_kapasite // 2)  # BTC notr/kararsiz -> savunma modu, taban 1

    if sniper_modu_aktif:
        izin_verilen = min(izin_verilen, 1)  # v17: Sniper Modu'nda KESINLIKLE tek pozisyon

    if izin_verilen <= 0:
        return 0, 0.0, sniper_modu_aktif

    if sniper_modu_aktif:
        # v17: Sniper Modu - sermaye bolunmez, tum serbest kasa TEK adaya gider
        return 1, kasa_bakiye, True

    hedef_pozisyon_tutari = kasa_bakiye / izin_verilen

    # v14/v17: TABAN BUTCE KURALI - pozisyon TABAN_POZISYON_TUTARI altina
    # inmesin. Mumkunse (kasa yeterince buyukse) pozisyon sayisini
    # azaltarak bunu sagliyoruz; kasa zaten tabanin altindaysa (kucuk
    # sermaye edge-case'i) elimizdeki nakit ile yetiniyoruz.
    if hedef_pozisyon_tutari < TABAN_POZISYON_TUTARI and kasa_bakiye >= TABAN_POZISYON_TUTARI:
        izin_verilen = max(1, int(kasa_bakiye // TABAN_POZISYON_TUTARI))
        hedef_pozisyon_tutari = kasa_bakiye / izin_verilen

    return izin_verilen, hedef_pozisyon_tutari, False


def en_kaliteli_aday_belirle(bilgi_map: dict, pozisyonlar: dict) -> Optional[str]:
    """
    v17 MODUL 1.2: KALITE ONCELIGI. Bos pozisyon hakki olsa dahi, taranan
    listede ADX_MIN_ESIK VE [RSI_KALITE_ALT_ESIK, RSI_KALITE_UST_ESIK]
    kriterlerini BIRLIKTE karsilayan VE su an yatirilmamis/cooldown'da
    olmayan/RSI-beklemede olmayan adaylar arasindan SADECE en yuksek
    ADX'e (trend/kalite skoru) sahip olanin sembolunu dondurur. Kriteri
    tam karsilayan uygun aday yoksa None doner - bu durumda cagiran taraf
    (evaluate_v9) YENI ALIM yapmaz, sermaye nakitte bekletilir.
    """
    en_iyi_sym: Optional[str] = None
    en_iyi_adx = -1.0
    for sym, bilgi in bilgi_map.items():
        adx14 = bilgi.get("adx14")
        rsi14 = bilgi.get("rsi14")
        if adx14 is None or rsi14 is None:
            continue
        if adx14 < ADX_MIN_ESIK:
            continue
        if not (RSI_KALITE_ALT_ESIK <= rsi14 <= RSI_KALITE_UST_ESIK):
            continue
        bot = pozisyonlar.get(sym)
        if bot is not None and (bot.has_open_position or bot.cooldown_aktif_mi() or bot.bekliyor):
            continue
        if adx14 > en_iyi_adx:
            en_iyi_adx = adx14
            en_iyi_sym = sym
    return en_iyi_sym


class MerkeziKasa:
    """
    Tum acik pozisyonlar arasinda PAYLASILAN tek bir nakit havuzu. Her
    yeni pozisyon GUNCEL toplam bakiye / MAX_OPEN_POSITIONS kadar
    sermaye ile acilir. v10'da CANLI_MOD=True ise bu bakiye borsadan
    cekilen GERCEK serbest TRY bakiyesiyle senkronize edilir.
    """

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


@dataclass
class CoinBot:
    symbol: str
    coin_name: str
    width_pct: float
    grid_count: int
    starting_try: float
    cash_try: float = 0.0
    coin_qty: float = 0.0
    trade_count: int = 0
    realized_pnl: float = 0.0
    toplam_komisyon: float = 0.0
    history: list = field(default_factory=list)
    grid: list = field(default_factory=list)
    last_real_price: float = 0.0
    last_sim_price: float = 0.0
    lower: float = 0.0
    upper: float = 0.0
    initialized: bool = False
    bekliyor: bool = False
    bekleme_sayaci: int = 0
    tek_pozisyon_modu: bool = True
    son_satis_zamani: Optional[datetime] = None
    bu_turda_islem_yapildi: bool = False
    bildirim_aktif: bool = True   # v10: False ise Telegram bildirimi gonderilmez (backtest icin)
    alis_zamani: Optional[datetime] = None      # v16: zaman bazli bayat pozisyon cikisi icin
    son_cooldown_dakika: float = COOLDOWN_MINUTES  # v16: son kapanisin SONUCUNA gore belirlenen dinamik sure

    def __post_init__(self):
        self.cash_try = self.starting_try

    @property
    def has_open_position(self) -> bool:
        return self.coin_qty > 1e-12

    def cooldown_aktif_mi(self) -> bool:
        if self.son_satis_zamani is None:
            return False
        gecen_saniye = (datetime.now() - self.son_satis_zamani).total_seconds()
        return gecen_saniye < self.son_cooldown_dakika * 60

    def cooldown_kalan_dakika(self) -> float:
        if self.son_satis_zamani is None:
            return 0.0
        gecen_saniye = (datetime.now() - self.son_satis_zamani).total_seconds()
        kalan = self.son_cooldown_dakika * 60 - gecen_saniye
        return max(0.0, kalan / 60)

    def _satis_sonrasi_kilitle(self, tag: str = "STOP-LOSS") -> None:
        """v16: Cooldown suresi artik SABIT degil, kapanis SEBEBINE (tag)
        gore dinamik belirlenir - bkz. _cooldown_suresi_hesapla()."""
        self.son_satis_zamani = datetime.now()
        self.bu_turda_islem_yapildi = True
        self.son_cooldown_dakika = _cooldown_suresi_hesapla(tag)

    def setup_grid(self, center_price: float):
        self.lower = center_price * (1 - self.width_pct / 2)
        self.upper = center_price * (1 + self.width_pct / 2)
        step = (self.upper - self.lower) / self.grid_count
        self.grid = [GridLevel(price=self.lower + i * step) for i in range(self.grid_count + 1)]
        self.last_sim_price = center_price
        self.initialized = True

        adim_pct = step / center_price
        tahmini_yuvarlak_tur_maliyet = 2 * KOMISYON_PCT + (SLIPAJ_MIN_PCT + SLIPAJ_MAKS_PCT)
        guvenli_mi = adim_pct >= tahmini_yuvarlak_tur_maliyet * GUVENLI_MARJ_KATSAYISI

        print(
            f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} izleme araligi kuruldu -> "
            f"{format_fiyat(self.lower)} - {format_fiyat(self.upper)} TRY ({self.grid_count} seviye, "
            f"adim: %{adim_pct*100:.2f}, merkez: {format_fiyat(center_price)} TRY)"
        )
        if not guvenli_mi:
            print(f"{RED}    UYARI: Grid adimi (%{adim_pct*100:.2f}) tahmini islem maliyetine "
                  f"(%{tahmini_yuvarlak_tur_maliyet*100:.2f}) gore COK DAR.{RESET}")

    @property
    def qty_per_grid_try(self) -> float:
        """Yalnizca LEGACY (tek_pozisyon_modu=False, backtest) yolunda kullanilir."""
        return self.starting_try / self.grid_count

    def record(self, side, price, qty, amount):
        self.trade_count += 1
        self.history.append((ts(), side, price, qty, amount))

    def next_sim_price(self) -> float:
        drift = random.uniform(-MICRO_WIGGLE_PCT, MICRO_WIGGLE_PCT)
        candidate = self.last_sim_price * (1 + drift)
        pull = (self.last_real_price - candidate) * 0.15
        candidate += pull
        self.last_sim_price = candidate
        return candidate

    @staticmethod
    def _slipajli_fiyat(price: float, side: str) -> float:
        slip = random.uniform(SLIPAJ_MIN_PCT, SLIPAJ_MAKS_PCT)
        if side == "ALIM":
            return price * (1 + slip)
        else:
            return price * (1 - slip)

    def _canli_emir_dogrula_ve_gonder(self, side: str, qty: float, exec_price: float) -> Optional[float]:
        """
        v10: CANLI_MOD=True iken cagrilir. LOT_SIZE (stepSize) yuvarlamasi
        ve minNotional kontrolu yapar, ardindan GERCEK emri gonderir.
        Basarili olursa (yuvarlanmis) miktari, basarisiz/uygunsuz olursa
        None doner. CAGIRAN TARAF None DONDUGUNDE IC DURUMU
        GUNCELLEMEMELIDIR - cunku gercek borsa emri gitmemis demektir.
        """
        try:
            filtreler = sembol_filtrelerini_getir(self.symbol)
        except Exception as e:
            print(f"{RED}  CANLI EMIR IPTAL: sembol filtreleri alinamadi ({self.symbol}): {e}{RESET}")
            return None

        yuvarlanmis_qty = miktari_lot_size_yuvarla(qty, filtreler.get("step_size"))
        if yuvarlanmis_qty <= 0:
            print(f"{RED}  CANLI EMIR IPTAL: LOT_SIZE yuvarlamasi sonrasi miktar 0 ({self.symbol}).{RESET}")
            return None

        min_notional = filtreler.get("min_notional")
        tahmini_notional = yuvarlanmis_qty * exec_price
        if min_notional and tahmini_notional < min_notional:
            print(f"{RED}  CANLI EMIR IPTAL: Tutar minNotional altinda "
                  f"({tahmini_notional:.2f} < {min_notional}) - {self.symbol}.{RESET}")
            return None

        try:
            emir_sonucu = binance_gercek_emir_gonder(self.symbol, side, yuvarlanmis_qty)
            print(f"{GREEN}  CANLI EMIR GONDERILDI ({side} {self.symbol}): {emir_sonucu}{RESET}")
            return yuvarlanmis_qty
        except Exception as e:
            print(f"{RED}  CANLI EMIR BASARISIZ ({side} {self.symbol}): {e}{RESET}")
            send_telegram(f"\u26a0\ufe0f <b>CANLI EMIR BASARISIZ</b>\n{self.symbol} {side} - {e}")
            return None

    def _ratchet_stop_hesapla(self, level: "GridLevel") -> tuple:
        """v14: UC KADEMELI RATCHET STOP hesabini SALT-OKUNUR olarak
        dondurur (islem yapmaz) - hem stop_loss_kontrol() icinde HEM DE
        raporlama/giris karti icin (guncel_stop_seviyesi gostermek icin)
        tekrar kullanilir. Donus: (stop_seviyesi, etiket)."""
        peak = level.en_yuksek_fiyat
        buy_price = level.buy_price

        stop_seviyesi = buy_price * (1 - STOP_LOSS_PCT)
        etiket = "STOP-LOSS"

        if peak >= buy_price * (1 + BREAKEVEN_AKTIVASYON_PCT):
            komisyon_ve_slipaj_tamponu = 3 * (KOMISYON_PCT + SLIPAJ_MAKS_PCT)
            breakeven_seviyesi = buy_price * (1 + komisyon_ve_slipaj_tamponu)
            if breakeven_seviyesi > stop_seviyesi:
                stop_seviyesi = breakeven_seviyesi
                etiket = "BREAKEVEN-STOP"

        if TRAILING_STOP_AKTIF and peak >= buy_price * (1 + TRAILING_AKTIVASYON_PCT):
            trailing_seviyesi = peak * (1 - TRAILING_STOP_PCT)
            if trailing_seviyesi > stop_seviyesi:
                stop_seviyesi = trailing_seviyesi
                etiket = "TRAILING-STOP"

        return stop_seviyesi, etiket

    def _sonraki_kar_hedefi(self, level_index: int) -> float:
        """v15: level_index'teki pozisyonun kar-al hedefini dondurur. Grid
        icinde bir sonraki seviye varsa onu kullanir; YOKSA (fiyat gridin
        tepesini asmis/asacak durumdaysa) DINAMIK olarak bir basamak daha
        ilerideki fiyati hesaplar - boylece fiyat grid sinirini asip
        'sicramis' olsa bile pozisyon HER ZAMAN gercekci, ulasilabilir bir
        kar hedefine sahip olur (v15 BOLUM 1/2 duzeltmesi)."""
        if level_index + 1 < len(self.grid):
            return self.grid[level_index + 1].price
        basamak_pct = self.width_pct / self.grid_count
        return self.grid[level_index].buy_price * (1 + basamak_pct)

    def acik_hedef_ve_stop(self) -> tuple:
        """v15: Su an acik olan seviye icin (hedef_fiyat, stop_fiyat, etiket)
        dondurur - periyodik raporlarda gostermek icin. Acik pozisyon
        yoksa (None, None, None) doner. TRAILING-STOP aktifse hedef
        artik sabit bir grid basamagi degil, trailing tarafindan
        yonetildigi icin hedef alaninda "TRAILING" ETIKETI dondurulur
        (v14'teki 'Hedef < Stop' tutarsizligini onlemek icin - trailing
        aktifken zaten cikis o mekanizma tarafindan yonetilir)."""
        for i, level in enumerate(self.grid):
            if level.has_position:
                stop, etiket = self._ratchet_stop_hesapla(level)
                if etiket == "TRAILING-STOP":
                    return "TRAILING", stop, etiket
                hedef = self._sonraki_kar_hedefi(i)
                return hedef, stop, etiket
        return None, None, None

    def _satisi_uygula(self, level: "GridLevel", price: float, tag: str, sim: bool,
                        kasa: Optional[MerkeziKasa], acik_pozisyon_sayaci: Optional[list],
                        rapor: Optional["RaporlamaDurumu"], durum_kaydet: Optional[object],
                        miktar: Optional[float] = None) -> bool:
        """
        v16: TUM SATIS/KAPANIS yollari (STOP-LOSS, BREAKEVEN-STOP,
        TRAILING-STOP, KAR-AL, ZAMAN-ASIMI, ACIL-TASFIYE, KISMI-KAR-AL)
        icin TEK, ORTAK muhasebe/log/telegram/state-kaydet/dinamik-
        cooldown rutinidir - kod tekrarini onler ve dinamik cooldown'un
        (BOLUM 2) HER kapanis yolunda tutarli uygulanmasini saglar.

        miktar verilmezse TUM level.buy_qty satilir (pozisyon TAM kapanir
        - cooldown/mutex tetiklenir, alis_zamani temizlenir, acik pozisyon
        sayaci dusurulur). miktar verilirse SADECE o kadari satilir
        (kismi kar alma - pozisyon ACIK KALIR, cooldown/mutex/alis_zamani
        DOKUNULMAZ).

        kasa=None ise (LEGACY/backtest yolu) sadece bu CoinBot'un kendi
        cash_try/coin_qty muhasebesi yapilir - merkezi kasa, cooldown ve
        acik_pozisyon_sayaci hic etkilenmez (v9 oncesi davranisla ayni).

        Basarili olursa True, CANLI_MOD'da gercek emir basarisiz olursa
        False doner (bu durumda HICBIR ic durum degismez).
        """
        sell_qty = level.buy_qty if miktar is None else miktar
        if sell_qty <= 0:
            return False

        exec_price = self._slipajli_fiyat(price, "SATIM")
        if CANLI_MOD and kasa is not None:
            dogrulanmis_qty = self._canli_emir_dogrula_ve_gonder("SELL", sell_qty, exec_price)
            if dogrulanmis_qty is None:
                return False  # gercek emir gitmedi - ic durum degismez, sonraki tick'te tekrar denenir
            sell_qty = dogrulanmis_qty

        brut_proceeds = sell_qty * exec_price
        komisyon = brut_proceeds * KOMISYON_PCT
        net_proceeds = brut_proceeds - komisyon
        cost = sell_qty * level.buy_price
        islem_net_pnl = net_proceeds - cost  # v17 MODUL 4: SADECE bu islemden elde edilen net K/Z
        islem_net_pnl_pct = (islem_net_pnl / cost * 100) if cost else 0.0

        self.cash_try += net_proceeds
        self.coin_qty = max(0.0, self.coin_qty - sell_qty)
        self.toplam_komisyon += komisyon
        self.realized_pnl += net_proceeds - cost
        level.buy_qty = max(0.0, level.buy_qty - sell_qty)

        tam_kapanis = level.buy_qty <= 1e-9
        if tam_kapanis:
            level.has_position = False
            level.buy_qty = 0.0
            self.alis_zamani = None  # v16
            if kasa is not None:
                kasa.yatir(net_proceeds, komisyon)
                self._satis_sonrasi_kilitle(tag)  # v16: dinamik cooldown, tag'e gore
                if acik_pozisyon_sayaci is not None and acik_pozisyon_sayaci[0] > 0:
                    acik_pozisyon_sayaci[0] -= 1
        else:
            level.kismi_kar_alindi = True
            if kasa is not None:
                kasa.yatir(net_proceeds, komisyon)

        if rapor is not None:
            rapor.islem_kaydet(self.symbol, "SATIM", komisyon, net_proceeds - cost)
        self.record("SATIM", exec_price, sell_qty, net_proceeds)
        # v17 MODUL 4: Satis bildirimi artik ilk gunden beri biriken kumulatif
        # getiri yerine SADECE bu islemden elde edilen net K/Z'yi ve satis
        # sonrasi GUNCEL serbest kasa bakiyesini gosterir.
        print_trade_line(self.symbol, "SATIM", exec_price, sell_qty, net_proceeds, self.cash_try,
                          self.coin_name, sim, tag=tag, komisyon=komisyon,
                          telegram_bildir=self.bildirim_aktif,
                          net_pnl=islem_net_pnl, net_pnl_pct=islem_net_pnl_pct,
                          guncel_kasa=(kasa.bakiye if kasa is not None else None))
        if durum_kaydet is not None:
            durum_kaydet()
        return True

    def stop_loss_kontrol(self, price: float, sim: bool, kasa: Optional[MerkeziKasa] = None,
                           acik_pozisyon_sayaci: Optional[list] = None,
                           durum_kaydet: Optional[object] = None,
                           rapor: Optional["RaporlamaDurumu"] = None):
        """
        Acik pozisyonlari kontrol eder (SABIT STOP-LOSS + TRAILING STOP +
        v16: ZAMAN BAZLI BAYAT POZISYON CIKISI). v10'da EK OLARAK:
        CANLI_MOD=True ise satistan once GERCEK SATIM emri gonderilir
        (basarisizsa pozisyon ACIK KALIR, ic durum guncellenmez); basarili
        her satistan sonra durum_kaydet() cagirilirsa JSON dosyasi
        guncellenir. v11'de EK OLARAK: rapor verilirse basarili her satis
        X/Z donemsel sayaclarina islenir (islem_kaydet).
        """
        for level in self.grid:
            if not level.has_position:
                continue

            if price > level.en_yuksek_fiyat:
                level.en_yuksek_fiyat = price

            # v13: KADEMELI KAR ALMA - pozisyon KISMI_KAR_AL_PCT kara ulastiginda
            # (stop henuz tetiklenmeden) miktarin bir kismi ANINDA satilarak kar
            # erken realize edilir; kalan miktar mevcut breakeven/trailing
            # korumasiyla yoluna devam eder. Sadece CANLI/v9+ modda (kasa
            # verildiginde) aktiftir - backtest/legacy etkilenmez.
            if (kasa is not None and not level.kismi_kar_alindi and KISMI_KAR_AL_ORANI > 0
                    and price >= level.buy_price * (1 + KISMI_KAR_AL_PCT)):
                kismi_qty = level.buy_qty * KISMI_KAR_AL_ORANI
                if kismi_qty > 0:
                    self._satisi_uygula(level, price, "KISMI-KAR-AL", sim, kasa,
                                         acik_pozisyon_sayaci, rapor, durum_kaydet, miktar=kismi_qty)

            if not level.has_position:
                continue  # kismi kar alma pozisyonu tam kapatmis olamaz, ama guvenlik icin kontrol

            # v16 BOLUM 1: ZAMAN BAZLI BAYAT POZISYON CIKISI - pozisyon
            # MAKS_POZISYON_OMRU_SAAT'ten uzun suredir aciksa VE guncel
            # kari ZAMAN_ASIMI_KAR_ESIGI_PCT altindaysa (negatif dahil),
            # bot artik hedefi beklemez, piyasa fiyatindan kapatir.
            if kasa is not None and self.alis_zamani is not None:
                yas_saat = (datetime.now() - self.alis_zamani).total_seconds() / 3600
                guncel_kar_pct = (price - level.buy_price) / level.buy_price if level.buy_price else 0.0
                if yas_saat >= MAKS_POZISYON_OMRU_SAAT and guncel_kar_pct < ZAMAN_ASIMI_KAR_ESIGI_PCT:
                    if self._satisi_uygula(level, price, "ZAMAN-ASIMI", sim, kasa,
                                            acik_pozisyon_sayaci, rapor, durum_kaydet):
                        mesaj = (f"\u23F3 <b>{self.symbol} Zaman Asimi Cikisi</b>\n"
                                 f"{MAKS_POZISYON_OMRU_SAAT:.0f} saattir yatay seyrettigi icin "
                                 f"sermaye serbest birakildi.")
                        print(f"[{ts()}] {YELLOW}\u23F3 {self.symbol} Zaman Asimi Cikisi: "
                              f"{MAKS_POZISYON_OMRU_SAAT:.0f} saattir yatay seyrettigi icin "
                              f"sermaye serbest birakildi.{RESET}")
                        send_telegram(mesaj)
                    continue  # bu seviye kapandi (veya emir basarisiz oldu) - ratchet kontrolu gereksiz

            # v12/v14: UC KADEMELI RATCHET STOP SISTEMI - artik ortak
            # _ratchet_stop_hesapla() metodundan hesaplanir (raporlama/
            # giris karti ile paylasilan TEK bir kaynak).
            stop_seviyesi, etiket = self._ratchet_stop_hesapla(level)

            if price <= stop_seviyesi:
                self._satisi_uygula(level, price, etiket, sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)

    # ------------------------------------------------------------
    # LEGACY (v8/v9) DEGERLENDIRME - SADECE BACKTEST icin (tek_pozisyon_modu=False)
    # ------------------------------------------------------------
    def evaluate(self, price: float, sim: bool):
        """v8/v9 ile BIREBIR AYNI - coklu-seviye grid dolumu. Sadece backtest_calistir() tarafindan kullanilir."""
        self.stop_loss_kontrol(price, sim)

        if price < self.lower or price > self.upper:
            return
        qty_per_grid_try = self.qty_per_grid_try
        for i, level in enumerate(self.grid):
            if not level.has_position and price <= level.price and self.cash_try >= qty_per_grid_try:
                exec_price = self._slipajli_fiyat(price, "ALIM")
                buy_qty = qty_per_grid_try / exec_price
                komisyon = qty_per_grid_try * KOMISYON_PCT
                self.cash_try -= (qty_per_grid_try + komisyon)
                self.coin_qty += buy_qty
                self.toplam_komisyon += komisyon
                level.has_position = True
                level.buy_qty = buy_qty
                level.buy_price = exec_price
                level.en_yuksek_fiyat = exec_price
                self.record("ALIM", exec_price, buy_qty, qty_per_grid_try)
                print_trade_line(self.symbol, "ALIM", exec_price, buy_qty, qty_per_grid_try, self.cash_try,
                                  self.coin_name, sim, komisyon=komisyon, telegram_bildir=self.bildirim_aktif)

            elif level.has_position and i + 1 < len(self.grid) and price >= self.grid[i + 1].price:
                exec_price = self._slipajli_fiyat(price, "SATIM")
                sell_qty = level.buy_qty
                brut_proceeds = sell_qty * exec_price
                komisyon = brut_proceeds * KOMISYON_PCT
                net_proceeds = brut_proceeds - komisyon
                cost = sell_qty * level.buy_price
                self.cash_try += net_proceeds
                self.coin_qty -= sell_qty
                self.toplam_komisyon += komisyon
                self.realized_pnl += net_proceeds - cost
                level.has_position = False
                level.buy_qty = 0.0
                self.record("SATIM", exec_price, sell_qty, net_proceeds)
                print_trade_line(self.symbol, "SATIM", exec_price, sell_qty, net_proceeds, self.cash_try,
                                  self.coin_name, sim, komisyon=komisyon, telegram_bildir=self.bildirim_aktif)

    def opening_fill(self, current_price: float):
        """Sadece backtest_calistir() tarafindan kullanilir (v8/v9 ile ayni)."""
        for level in self.grid:
            if level.price <= current_price and self.cash_try >= self.qty_per_grid_try:
                exec_price = self._slipajli_fiyat(current_price, "ALIM")
                buy_qty = self.qty_per_grid_try / exec_price
                komisyon = self.qty_per_grid_try * KOMISYON_PCT
                self.cash_try -= (self.qty_per_grid_try + komisyon)
                self.coin_qty += buy_qty
                self.toplam_komisyon += komisyon
                level.has_position = True
                level.buy_qty = buy_qty
                level.buy_price = exec_price
                level.en_yuksek_fiyat = exec_price
                self.record("ALIM", exec_price, buy_qty, self.qty_per_grid_try)
                print_trade_line(self.symbol, "ALIM", exec_price, buy_qty, self.qty_per_grid_try, self.cash_try,
                                  self.coin_name, sim=False, tag="ACILIS", komisyon=komisyon,
                                  telegram_bildir=self.bildirim_aktif)

    def tasfiye_et(self, current_price: float) -> float:
        """Sadece backtest_calistir() tarafindan kullanilir (v8/v9 ile ayni)."""
        if self.coin_qty > 0:
            exec_price = self._slipajli_fiyat(current_price, "SATIM")
            brut_proceeds = self.coin_qty * exec_price
            komisyon = brut_proceeds * KOMISYON_PCT
            net_proceeds = brut_proceeds - komisyon
            self.cash_try += net_proceeds
            self.toplam_komisyon += komisyon
            self.record("SATIM", exec_price, self.coin_qty, net_proceeds)
            print_trade_line(self.symbol, "SATIM", exec_price, self.coin_qty, net_proceeds, self.cash_try,
                              self.coin_name, sim=False, tag="TASFIYE", komisyon=komisyon,
                              telegram_bildir=self.bildirim_aktif)
            self.coin_qty = 0.0
        return self.cash_try

    # ------------------------------------------------------------
    # CANLI MOD DEGERLENDIRMESI - TEK ACIK POZISYON + MERKEZI KASA (v9 cekirdegi + v10 katmanlari)
    # ------------------------------------------------------------
    def evaluate_v9(self, price: float, sim: bool, kasa: MerkeziKasa,
                     acik_pozisyon_sayaci: list, hedef_pozisyon_tutari: float,
                     izin_verilen_pozisyon: int,
                     durum_kaydet: Optional[object] = None,
                     rapor: Optional["RaporlamaDurumu"] = None,
                     giris_bilgisi: Optional[dict] = None,
                     en_kaliteli_aday: Optional[str] = None,
                     sniper_modu: bool = False):
        """
        COIN BASINA TEK ACIK POZISYON kuralini uygular: tek pozisyon,
        cooldown, mutex. v14'te MAX_OPEN_POSITIONS SABITI KALDIRILDI -
        artik her tick'te run_simulation tarafindan dinamik_pozisyon_planla()
        ile hesaplanan izin_verilen_pozisyon/hedef_pozisyon_tutari
        parametre olarak gecirilir (sermaye buyuklugunden bagimsiz otonom
        model). v17 MODUL 1.2: en_kaliteli_aday verilmisse (bkz.
        en_kaliteli_aday_belirle), bos pozisyon hakki olsa dahi SADECE bu
        sembol icin YENI ALIM denenir - kalite kriterini karsilamayan orta
        seviye adaylara "slot bos diye" giris YAPILMAZ. ALIM'dan hemen
        once orderbook spread kontrolu yapilir. CANLI_MOD=True ise
        ALIM/SATIM GERCEK borsa emri olarak gonderilir. Basarili her
        ALIM'da giris_bilgisi (varsa EMA50/RSI14/ADX14/hacim) ve
        sniper_modu/izin_verilen_pozisyon'dan turetilen Calisma Modu
        etiketiyle seffaf, zengin bir GIRIS KARTI konsola ve Telegram'a
        gonderilir.
        """
        self.stop_loss_kontrol(price, sim, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                durum_kaydet=durum_kaydet, rapor=rapor)

        # v15 BOLUM 1 DUZELTMESI: Fiyat self.upper/self.lower araligi
        # DISINA cikmis olsa bile SATIS/KAR-AL kontrolu ASLA bypass
        # edilmez. Bu bayrak SADECE asagidaki YENI ALIM dalinda kullanilir;
        # eskiden burada erken "return" vardi ve bu, fiyat grid tavanini
        # asan (orn. %30 yukselen) pozisyonlarin kar-al ile kapanmasini
        # tamamen engelliyordu.
        fiyat_aralik_disinda = price < self.lower or price > self.upper

        for i, level in enumerate(self.grid):
            if not level.has_position and price <= level.price:
                if fiyat_aralik_disinda:
                    continue  # v15: aralik disinda SADECE yeni alim engellenir
                if self.has_open_position:
                    continue
                if self.bu_turda_islem_yapildi:
                    continue
                if self.cooldown_aktif_mi():
                    continue
                if izin_verilen_pozisyon <= 0 or acik_pozisyon_sayaci[0] >= izin_verilen_pozisyon:
                    continue

                # v17 MODUL 1.2: KALITE ONCELIGI - bos slot olsa dahi SADECE
                # ADX>=20 ve RSI 38-60 kriterlerini birlikte karsilayan en
                # yuksek ADX'li aday icin YENI ALIM denenir; kriteri tam
                # karsilamayan orta seviye adaylara giris YAPILMAZ.
                if en_kaliteli_aday is None or self.symbol != en_kaliteli_aday:
                    continue

                # v10 BOLUM 3: ALIM'dan hemen once tahta derinligi/spread kontrolu
                spread_pct, en_iyi_bid, en_iyi_ask = orderbook_spread_kontrol(self.symbol)
                if spread_pct is not None and spread_pct > MAX_SPREAD_PCT:
                    print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} {YELLOW}ALIM IPTAL - "
                          f"spread cok genis (%{spread_pct:.2f} > %{MAX_SPREAD_PCT}), "
                          f"likidite sig kabul edildi (bid={en_iyi_bid}, ask={en_iyi_ask}).{RESET}")
                    continue

                yatirim_tutari = min(hedef_pozisyon_tutari, kasa.bakiye / (1 + KOMISYON_PCT))
                if yatirim_tutari <= 0:
                    continue

                exec_price = self._slipajli_fiyat(price, "ALIM")
                buy_qty = yatirim_tutari / exec_price

                if CANLI_MOD:
                    dogrulanmis_qty = self._canli_emir_dogrula_ve_gonder("BUY", buy_qty, exec_price)
                    if dogrulanmis_qty is None:
                        continue  # gercek emir gitmedi, ic durum guncellenmez
                    buy_qty = dogrulanmis_qty
                    yatirim_tutari = buy_qty * exec_price  # yuvarlama sonrasi gercek tutar

                komisyon = yatirim_tutari * KOMISYON_PCT
                kasa.harca(yatirim_tutari, komisyon)
                self.starting_try = yatirim_tutari
                self.cash_try = -komisyon
                self.coin_qty += buy_qty
                self.toplam_komisyon += komisyon
                level.has_position = True
                level.buy_qty = buy_qty
                level.buy_price = exec_price
                level.en_yuksek_fiyat = exec_price
                self.alis_zamani = datetime.now()  # v16: zaman bazli bayat pozisyon cikisi icin
                self.bu_turda_islem_yapildi = True
                acik_pozisyon_sayaci[0] += 1
                if rapor is not None:
                    rapor.islem_kaydet(self.symbol, "ALIM", komisyon, None)
                self.record("ALIM", exec_price, buy_qty, yatirim_tutari)
                print_trade_line(self.symbol, "ALIM", exec_price, buy_qty, yatirim_tutari,
                                  self.cash_try, self.coin_name, sim, komisyon=komisyon,
                                  telegram_bildir=self.bildirim_aktif)

                # v14/v17: SEFFAF GIRIS KARTI - hedef satis (bir sonraki grid
                # seviyesi) ve stop-loss (taban) fiyatlarini, beklenen net
                # kar/kayip TL ile birlikte gosterir.
                hedef_fiyat = self._sonraki_kar_hedefi(i)
                stop_fiyat = exec_price * (1 - STOP_LOSS_PCT)
                satis_brut_tahmini = buy_qty * hedef_fiyat
                satis_kom_tahmini = satis_brut_tahmini * KOMISYON_PCT
                beklenen_net_kar = (satis_brut_tahmini - satis_kom_tahmini) - yatirim_tutari
                stop_brut_tahmini = buy_qty * stop_fiyat
                stop_kom_tahmini = stop_brut_tahmini * KOMISYON_PCT
                beklenen_net_kayip = (stop_brut_tahmini - stop_kom_tahmini) - yatirim_tutari

                # v17 MODUL 3: Calisma Modu etiketi - Sniper Modu (kasa <
                # SNIPER_MODU_ESIGI_TRY) veya Portfoy Modu (guncel acik/izin
                # verilen pozisyon sayisi).
                calisma_modu_etiketi = (
                    "Sniper Modu" if sniper_modu
                    else f"Portfoy Modu ({acik_pozisyon_sayaci[0]}/{izin_verilen_pozisyon})"
                )

                gb = giris_bilgisi or {}
                kart = giris_karti_olustur(
                    self.symbol, self.coin_name, gb.get("ema50"), gb.get("rsi14"), gb.get("adx14"),
                    buy_qty, exec_price, yatirim_tutari, hedef_fiyat, stop_fiyat,
                    beklenen_net_kar, beklenen_net_kayip, calisma_modu_etiketi,
                )
                print(f"{GREEN}{BOLD}\U0001F7E2 [YENI POZISYON ACILDI]{RESET}")
                print(f"{CYAN}{kart}{RESET}\n")
                if self.bildirim_aktif:
                    giris_karti_telegram_gonder(kart, self.symbol)

                if durum_kaydet is not None:
                    durum_kaydet()

            elif level.has_position:
                # v15/v16: hedef artik SADECE sabit grid[i+1] degil -
                # _sonraki_kar_hedefi() ile hesaplanir. Boylece fiyat
                # gridin tepesini asmis olsa bile (HEITRY ornegindeki gibi
                # %30 yukselis) pozisyon gercekci bir hedefe ulasinca
                # KAR-AL ile kapanabilir. v16: satis muhasebesi artik
                # ortak _satisi_uygula() metodundan geciyor (dinamik
                # cooldown otomatik uygulanir).
                hedef_fiyat_bu_seviye = self._sonraki_kar_hedefi(i)
                if price < hedef_fiyat_bu_seviye:
                    continue
                self._satisi_uygula(level, price, "KAR-AL", sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)

    def acil_tasfiye(self, current_price: float, kasa: MerkeziKasa,
                      durum_kaydet: Optional[object] = None,
                      rapor: Optional["RaporlamaDurumu"] = None) -> None:
        """ACIL FREN (max drawdown) durumunda acik pozisyonu kasaya geri
        satarak kapatir. v10: CANLI_MOD=True ise GERCEK SATIM emri
        gonderir; basarisiz olursa pozisyon ACIK KALIR ve Telegram'a
        acil uyari gonderilir (manuel mudahale gerekebilir). v11: rapor
        verilirse X/Z donemsel sayaclarina islenir. v16: muhasebe artik
        ortak _satisi_uygula() metodundan geciyor."""
        acik_seviye = next((lvl for lvl in self.grid if lvl.has_position), None)
        if not acik_seviye or self.coin_qty <= 0:
            return
        basarili = self._satisi_uygula(acik_seviye, current_price, "ACIL-TASFIYE", False, kasa,
                                        None, rapor, durum_kaydet)
        if not basarili:
            print(f"{RED}  ACIL TASFIYE BASARISIZ: {self.symbol} gercek emir gonderilemedi - "
                  f"pozisyon ACIK KALDI, MANUEL MUDAHALE GEREKEBILIR.{RESET}")
            send_telegram(f"\U0001F6A8 <b>ACIL TASFIYE BASARISIZ</b>\n{self.symbol} - "
                          f"pozisyon acik kaldi, manuel mudahale gerekebilir!")


def get_last_price(symbol: str) -> float:
    url = PRICE_URL_TEMPLATE.format(symbol=symbol)
    req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=FIYAT_TIMEOUT_SANIYE, max_deneme=FIYAT_MAX_DENEME)
    return float(data[0]["price"])


def klines_kapanislarini_getir(symbol: str, interval: str = "1h", limit: int = 60) -> list:
    url = KLINES_URL_TEMPLATE.format(symbol=symbol, interval=interval, limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=20)
    return [float(mum[4]) for mum in data]


def klines_ohlc_getir(symbol: str, interval: str = "1h", limit: int = 60):
    """v13: ADX hesabi icin high/low/close serilerini birlikte ceker."""
    url = KLINES_URL_TEMPLATE.format(symbol=symbol, interval=interval, limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=20)
    highs = [float(mum[2]) for mum in data]
    lows = [float(mum[3]) for mum in data]
    closes = [float(mum[4]) for mum in data]
    return highs, lows, closes


def ema_hesapla(kapanislar: list, periyot: int):
    if len(kapanislar) < periyot:
        return None
    k = 2 / (periyot + 1)
    ema = sum(kapanislar[:periyot]) / periyot
    for fiyat in kapanislar[periyot:]:
        ema = fiyat * k + ema * (1 - k)
    return ema


def rsi_hesapla(kapanislar: list, periyot: int = 14):
    if len(kapanislar) < periyot + 1:
        return None
    kazanclar, kayiplar = [], []
    for i in range(1, len(kapanislar)):
        fark = kapanislar[i] - kapanislar[i - 1]
        kazanclar.append(max(fark, 0.0))
        kayiplar.append(max(-fark, 0.0))

    ort_kazanc = sum(kazanclar[:periyot]) / periyot
    ort_kayip = sum(kayiplar[:periyot]) / periyot
    for i in range(periyot, len(kazanclar)):
        ort_kazanc = (ort_kazanc * (periyot - 1) + kazanclar[i]) / periyot
        ort_kayip = (ort_kayip * (periyot - 1) + kayiplar[i]) / periyot

    if ort_kayip == 0:
        return 100.0
    rs = ort_kazanc / ort_kayip
    return 100 - (100 / (1 + rs))


def adx_hesapla(highs: list, lows: list, closes: list, periyot: int = 14):
    """
    v13: ADX (Average Directional Index) - Wilder yontemiyle. Trend
    YONUNU degil GUCUNU olcer; ADX<20 tipik olarak yatay/whipsaw piyasa,
    ADX>25 belirgin trend olarak kabul edilir. RSI/EMA'nin sahte
    kirilimlara (whipsaw) karsi zayif kaldigi durumlar icin ek teyit
    katmanidir.
    """
    n = len(closes)
    if n < periyot * 2 + 1:
        return None

    tr_list, plus_dm_list, minus_dm_list = [], [], []
    for i in range(1, n):
        yuksek_fark = highs[i] - highs[i - 1]
        dusuk_fark = lows[i - 1] - lows[i]
        plus_dm = yuksek_fark if (yuksek_fark > dusuk_fark and yuksek_fark > 0) else 0.0
        minus_dm = dusuk_fark if (dusuk_fark > yuksek_fark and dusuk_fark > 0) else 0.0
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)
        plus_dm_list.append(plus_dm)
        minus_dm_list.append(minus_dm)

    if len(tr_list) < periyot * 2:
        return None

    smoothed_tr = sum(tr_list[:periyot])
    smoothed_plus_dm = sum(plus_dm_list[:periyot])
    smoothed_minus_dm = sum(minus_dm_list[:periyot])

    def _dx(s_tr, s_plus, s_minus):
        plus_di = (s_plus / s_tr * 100) if s_tr else 0.0
        minus_di = (s_minus / s_tr * 100) if s_tr else 0.0
        toplam = plus_di + minus_di
        return (abs(plus_di - minus_di) / toplam * 100) if toplam else 0.0

    dx_list = [_dx(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm)]

    for i in range(periyot, len(tr_list)):
        smoothed_tr = smoothed_tr - (smoothed_tr / periyot) + tr_list[i]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / periyot) + plus_dm_list[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / periyot) + minus_dm_list[i]
        dx_list.append(_dx(smoothed_tr, smoothed_plus_dm, smoothed_minus_dm))

    if len(dx_list) < periyot:
        return None

    adx = sum(dx_list[:periyot]) / periyot
    for i in range(periyot, len(dx_list)):
        adx = (adx * (periyot - 1) + dx_list[i]) / periyot

    return adx


def atr_hesapla(highs: list, lows: list, closes: list, periyot: int = 14):
    """
    v16 BOLUM 3: ATR (Average True Range) - Wilder yontemiyle. Fiyattan
    BAGIMSIZ (mutlak TRY cinsinden) volatilite olcusudur; ATR/son_fiyat
    orani coin'in "ne kadar oynak" oldugunu gosterir ve grid genisligini
    (width_pct) buna gore dinamik olcekler.
    """
    n = len(closes)
    if n < periyot + 1:
        return None

    tr_list = []
    for i in range(1, n):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1]))
        tr_list.append(tr)

    if len(tr_list) < periyot:
        return None

    atr = sum(tr_list[:periyot]) / periyot
    for i in range(periyot, len(tr_list)):
        atr = (atr * (periyot - 1) + tr_list[i]) / periyot

    return atr


def atr_bazli_width_pct(atr: Optional[float], son_fiyat: float) -> float:
    """
    v16 BOLUM 3: ATR/fiyat oranina gore coin basina grid genisligini
    (width_pct) belirler:
      - Dusuk volatilite (BTC/ETH tarzi)  -> ~%2.75 basamak (hizli devir)
      - Orta volatilite                   -> ~%4 basamak (eski sabit varsayilan)
      - Yuksek volatilite (hareketli alt) -> ~%5.25 basamak (buyuk dalga)
    ATR hesaplanamadiysa (yetersiz veri) guvenli varsayilana doner.
    """
    if atr is None or son_fiyat <= 0:
        return VARSAYILAN_WIDTH_PCT
    atr_orani = atr / son_fiyat
    if atr_orani < ATR_DUSUK_VOLATILITE_ORAN:
        return WIDTH_PCT_DUSUK_VOL
    if atr_orani > ATR_YUKSEK_VOLATILITE_ORAN:
        return WIDTH_PCT_YUKSEK_VOL
    return WIDTH_PCT_ORTA_VOL


def trend_ve_rsi_durumu(symbol: str):
    try:
        highs, lows, kapanislar = klines_ohlc_getir(symbol, KLINE_INTERVAL_TREND, KLINE_LIMIT_TREND)
    except Exception:
        return "HAZIR", None, None, None, None, None

    if len(kapanislar) < EMA_PERIYOT + 1:
        return "HAZIR", None, None, None, None, kapanislar[-1] if kapanislar else None

    son_fiyat = kapanislar[-1]
    ema50 = ema_hesapla(kapanislar[-(EMA_PERIYOT + 10):], EMA_PERIYOT)
    rsi14 = rsi_hesapla(kapanislar[-(RSI_PERIYOT + 20):], RSI_PERIYOT)
    adx14 = adx_hesapla(highs, lows, kapanislar, ADX_PERIYOT)  # v13
    atr14 = atr_hesapla(highs, lows, kapanislar, ATR_PERIYOT)  # v16

    if ema50 is not None and son_fiyat < ema50 * (1 - TREND_ESIK_PCT):
        return "ELENDI_TREND", ema50, rsi14, adx14, atr14, son_fiyat

    # v13: ADX whipsaw/yatay piyasa filtresi - trend YOK sayilan piyasaya girilmez
    if adx14 is not None and adx14 < ADX_MIN_ESIK:
        return "ELENDI_ZAYIF_TREND", ema50, rsi14, adx14, atr14, son_fiyat

    if rsi14 is not None and rsi14 >= RSI_ASIRI_ALIM_ESIGI:
        return "BEKLEMEDE", ema50, rsi14, adx14, atr14, son_fiyat

    return "HAZIR", ema50, rsi14, adx14, atr14, son_fiyat


def btc_piyasa_durumu():
    url = TICKER_24H_URL + "?symbol=BTCTRY"
    req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=15)
    degisim = float(data.get("priceChangePercent", 0))
    return degisim <= BTC_DUSUS_ESIGI_PCT, degisim


def try_paritelerini_bul() -> list:
    req = urllib.request.Request(EXCHANGE_INFO_URL, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=25)

    semboller = []
    for s in data.get("symbols", []):
        if s.get("quoteAsset") == "TRY" and s.get("status") == "TRADING":
            semboller.append(s["symbol"])

    return sorted(set(semboller))


def coin_degerlendir_ve_sec(semboller: list, sayisi: int):
    """
    24 saatlik hacim/degisim + EMA50/RSI14 trend filtresine gore coinleri
    elemeye tabi tutar. 'sayisi' bir TAVAN (esnek) - kriterleri
    karsilayan kac coin varsa o kadari dondurulur, ZORUNLU sabit sayi yok.
    Donus: (secilen_semboller_listesi, {sembol: hacim_try}, {sembol: durum})
    """
    req = urllib.request.Request(TICKER_24H_URL, headers={"User-Agent": "grid-bot-sim"})
    tum_veriler = http_istek_yap(req, timeout=25)

    veri_map = {d["symbol"]: d for d in tum_veriler if d.get("symbol") in semboller}

    adaylar = []
    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{CYAN}  COIN DEGERLENDIRMESI (24 saatlik veriye gore){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")

    for sym in semboller:
        d = veri_map.get(sym)
        if not d:
            continue
        try:
            hacim_try = float(d.get("quoteVolume", 0))
            ham_degisim_pct = float(d.get("priceChangePercent", 0))
            degisim_pct = abs(ham_degisim_pct)
        except (TypeError, ValueError):
            continue

        if hacim_try < MIN_HACIM_TRY:
            continue
        if degisim_pct < MIN_HAREKETLILIK_PCT:
            continue
        if degisim_pct > MAX_HAREKETLILIK_PCT:
            continue
        if ham_degisim_pct < YON_FILTRESI_MIN_DEGISIM_PCT:
            continue

        print(f"  {sym:<10} {GREEN}aday{RESET}   (hacim: {hacim_try:>14,.0f} TRY, degisim: %{ham_degisim_pct:+.2f})")
        adaylar.append((sym, hacim_try, degisim_pct))

    if not adaylar:
        print(f"{RED}  Hicbir coin kriterlere uymadi - %100 nakitte beklenecek.{RESET}")
        return [], {}, {}, {}

    adaylar.sort(key=lambda x: x[1], reverse=True)
    on_adaylar = adaylar[: sayisi * 2] if len(adaylar) > sayisi * 2 else adaylar

    print(f"{CYAN}  EMA{EMA_PERIYOT}/RSI{RSI_PERIYOT} TREND KONTROLU ({len(on_adaylar)} on-aday){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")

    nihai_adaylar = []
    durum_map = {}
    adx_map = {}   # v13
    bilgi_map = {}  # v14: giris karti icin EMA50/RSI14/hacim onbellegi
    for sym, hacim_try, degisim_pct in on_adaylar:
        try:
            durum, ema50, rsi14, adx14, atr14, son_fiyat = trend_ve_rsi_durumu(sym)
        except Exception as e:
            print(f"  {sym:<10} {RED}trend/RSI/ADX hesaplanamadi ({e}) - temkinli HAZIR sayildi{RESET}")
            durum, ema50, rsi14, adx14, atr14, son_fiyat = "HAZIR", None, None, None, None, None
        time.sleep(API_CALL_SLEEP_SECONDS)  # Binance TR rate-limitine takilmamak icin guvenli bekleme

        ema_str = format_fiyat(ema50) if ema50 is not None else "N/A"
        rsi_str = f"{rsi14:.1f}" if rsi14 is not None else "N/A"
        adx_str = f"{adx14:.1f}" if adx14 is not None else "N/A"

        if durum == "ELENDI_TREND":
            print(f"  {sym:<10} {RED}elendi{RESET} (dusus trendinde: fiyat EMA{EMA_PERIYOT}={ema_str} altinda)")
            continue
        elif durum == "ELENDI_ZAYIF_TREND":
            print(f"  {sym:<10} {RED}elendi{RESET} (zayif trend/whipsaw: ADX={adx_str} < {ADX_MIN_ESIK})")
            continue
        elif durum == "BEKLEMEDE":
            print(f"  {sym:<10} {YELLOW}beklemede{RESET} (RSI={rsi_str} >= {RSI_ASIRI_ALIM_ESIGI}, ADX={adx_str})")
        else:
            print(f"  {sym:<10} {GREEN}hazir{RESET}   (EMA{EMA_PERIYOT}={ema_str}, RSI={rsi_str}, ADX={adx_str})")

        durum_map[sym] = durum
        adx_map[sym] = adx14 if adx14 is not None else 0.0
        bilgi_map[sym] = {
            "ema50": ema50, "rsi14": rsi14, "hacim_try": hacim_try, "adx14": adx14,
            "atr14": atr14, "width_pct": atr_bazli_width_pct(atr14, son_fiyat if son_fiyat else 0.0),
        }  # v14/v16
        nihai_adaylar.append((sym, hacim_try, degisim_pct))

    if not nihai_adaylar:
        print(f"{RED}  Trend filtresinden gecen coin kalmadi - %100 nakitte beklenecek.{RESET}")
        return [], {}, {}, {}

    # v13: kalan adaylar arasindan en GUCLU TRENDE (yuksek ADX) sahip olanlar
    # once alinir - bos bir pozisyon slotu aciginda tarama listesindeki en
    # guclu aday oncelikli denenir.
    nihai_adaylar.sort(key=lambda x: adx_map.get(x[0], 0.0), reverse=True)

    secilenler = nihai_adaylar[:sayisi]

    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}{GREEN}  IZLEME LISTESI ({len(secilenler)} coin - esnek, zorunlu sabit sayi yok):{RESET}")
    for sym, hacim_try, degisim_pct in secilenler:
        durum_etiketi = "beklemede (RSI sogusun)" if durum_map[sym] == "BEKLEMEDE" else "hazir"
        print(f"    -> {sym}  (hacim: {hacim_try:,.0f} TRY, 24s degisim: %{degisim_pct:.2f}, durum: {durum_etiketi})")
    print(f"{CYAN}{'-' * 74}{RESET}\n")

    hacim_map = {sym: hacim_try for sym, hacim_try, _ in secilenler}
    secilen_durum_map = {sym: durum_map[sym] for sym, _, _ in secilenler}
    secilen_bilgi_map = {sym: bilgi_map[sym] for sym, _, _ in secilenler}  # v14

    return [s[0] for s in secilenler], hacim_map, secilen_durum_map, secilen_bilgi_map


def print_banner():
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS - v17'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}  BINANCE TR AKILLI SECIM GRID BOT  |  PIYASA ADAPTIF MOTOR{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    if CANLI_MOD:
        print(f"{RED}{BOLD}  !!! CANLI_MOD = True: BU BOT GERCEK PARA ILE GERCEK EMIR GONDERECEK !!!{RESET}")
    else:
        print(f"{YELLOW}  DRY-RUN (SIMULASYON) modunda. Gercek emir gonderilmiyor.{RESET}")
    print(f"{GRAY}  Calisma modu       : {'CANLI (GERCEK PARA)' if CANLI_MOD else 'SIMULASYON'}{RESET}")
    print(f"{GRAY}  Sanal/baslangic kasa: {TOPLAM_SANAL_BAKIYE_TRY:,.0f} TRY{RESET}")
    print(f"{GRAY}  Pozisyon modeli    : < {SNIPER_MODU_ESIGI_TRY:,.0f} TRY -> SNIPER MODU (kesinlikle 1 pozisyon),{RESET}")
    print(f"{GRAY}                       {SNIPER_MODU_ESIGI_TRY:,.0f}-{KADEME_2_ESIGI_TRY:,.0f}:2 / "
          f"{KADEME_2_ESIGI_TRY:,.0f}-{KADEME_3_ESIGI_TRY:,.0f}:3 / {KADEME_3_ESIGI_TRY:,.0f}-{KADEME_4_ESIGI_TRY:,.0f}:4 / "
          f">={KADEME_4_ESIGI_TRY:,.0f}:{KASA_KAPASITESI_TAVAN} (tavan){RESET}")
    print(f"{GRAY}                       taban pozisyon {TABAN_POZISYON_TUTARI:,.0f} TRY, "
          f"BTC 24s gucune gore tam/yari/sifir kapasite{RESET}")
    print(f"{GRAY}  Kalite onceligi    : ADX>={ADX_MIN_ESIK} VE RSI {RSI_KALITE_ALT_ESIK}-{RSI_KALITE_UST_ESIK} - "
          f"bos slotta bile sadece en yuksek ADX'li aday alinir{RESET}")
    print(f"{GRAY}  Cooldown           : {COOLDOWN_MINUTES} dk (satistan sonra yeniden alim kilidi){RESET}")
    print(f"{GRAY}  Izleme listesi     : esnek, {MIN_WATCHLIST}-{MAX_WATCHLIST} coin arasi{RESET}")
    print(f"{GRAY}  Firsat taramasi    : her ~{SCAN_INTERVAL_MINUTES} dk{RESET}")
    print(f"{GRAY}  Varlik yenileme    : her ~{ASSET_REFRESH_HOURS} saat{RESET}")
    print(f"{GRAY}  BTC dusus esigi    : %{BTC_DUSUS_ESIGI_PCT:.0f}{RESET}")
    print(f"{GRAY}  Spread filtresi    : max %{MAX_SPREAD_PCT} (ustunde ALIM iptal edilir){RESET}")
    print(f"{GRAY}  Komisyon           : %{KOMISYON_PCT * 100:.2f}{RESET}")
    print(f"{GRAY}  Slipaj araligi     : %{SLIPAJ_MIN_PCT * 100:.2f} - %{SLIPAJ_MAKS_PCT * 100:.2f}{RESET}")
    print(f"{GRAY}  Trend filtresi     : EMA{EMA_PERIYOT}, esik %{TREND_ESIK_PCT * 100:.1f}{RESET}")
    print(f"{GRAY}  RSI giris filtresi : asiri alim>={RSI_ASIRI_ALIM_ESIGI}, giris esigi<={RSI_GIRIS_UST_ESIGI}{RESET}")
    print(f"{GRAY}  Sabit stop-loss    : %{STOP_LOSS_PCT * 100:.0f} (taban){RESET}")
    print(f"{GRAY}  Basa-bas aktivasyon: %{BREAKEVEN_AKTIVASYON_PCT * 100:.1f} kardan sonra stop=basabas{RESET}")
    print(f"{GRAY}  Trailing aktivasyon: %{TRAILING_AKTIVASYON_PCT * 100:.1f} kardan sonra devreye girer{RESET}")
    print(f"{GRAY}  Trailing mesafesi  : tepeden %{TRAILING_STOP_PCT * 100:.1f} geri cekilme{RESET}")
    print(f"{GRAY}  Kismi kar alma     : %{KISMI_KAR_AL_PCT * 100:.0f} karda pozisyonun %{KISMI_KAR_AL_ORANI * 100:.0f}'i realize edilir{RESET}")
    print(f"{GRAY}  ADX trend filtresi : min {ADX_MIN_ESIK} (altinda whipsaw/yatay piyasa - GIRILMEZ){RESET}")
    print(f"{GRAY}  ATR grid adaptasyonu: dusuk vol ~%2.75 / orta ~%4 / yuksek vol ~%5.25 basamak{RESET}")
    print(f"{GRAY}  Zaman asimi cikisi : {MAKS_POZISYON_OMRU_SAAT:.0f}s+ ve kar<%{ZAMAN_ASIMI_KAR_ESIGI_PCT*100:.0f} ise zorla kapatilir{RESET}")
    print(f"{GRAY}  Dinamik cooldown   : kar={COOLDOWN_KAR_DAKIKA:.0f}dk, zarar={COOLDOWN_ZARAR_DAKIKA:.0f}dk, zaman asimi={COOLDOWN_ZAMAN_ASIMI_DAKIKA:.0f}dk{RESET}")
    if CANLI_MOD:
        print(f"{GRAY}  Bakiye mutabakati  : her ~{MUTABAKAT_ARALIGI_SAAT:.0f} saatte + gunluk X raporunda{RESET}")
    print(f"{GRAY}  Acil fren limiti   : %{MAX_DRAWDOWN_PCT * 100:.0f}{RESET}")
    print(f"{GRAY}  Durum dosyasi      : {STATE_DOSYASI}{RESET}")
    print(f"{GRAY}  Telegram bildirimi : {'AKTIF (arka plan kuyrugu)' if (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) else 'kapali (TELEGRAM_BOT_TOKEN/CHAT_ID tanimli degil)'}{RESET}")
    print(f"{GRAY}  Hata log dosyasi   : {LOG_DOSYASI}{RESET}")
    print(f"{GRAY}  Gunluk X raporu    : her 24 saatte bir (sayac restart'ta sifirlanmaz){RESET}")
    print(f"{GRAY}  Aylik Z raporu     : her 30 gunde bir -> {os.path.basename(Z_RAPORLARI_CSV)}{RESET}")
    print(f"{GRAY}  Islem kaydi        : {ISLEMLER_CSV}{RESET}")
    print(f"{GRAY}  Portfoy kaydi      : {PORTFOY_CSV}{RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}\n")


GIRIS_KARTI_GENISLIK = 72  # v14


def _adx_trend_etiketi(adx: Optional[float]) -> str:
    """v17: ADX gucune gore kisa, okunabilir bir trend etiketi dondurur."""
    if adx is None:
        return "N/A"
    if adx >= 40:
        return "Cok Guclu Trend"
    if adx >= 25:
        return "Guclu Trend"
    if adx >= ADX_MIN_ESIK:
        return "Orta Trend"
    return "Zayif Trend"


def giris_karti_olustur(symbol: str, coin_name: str, ema50, rsi14, adx14,
                         adet: float, exec_price: float, yatirilan_tl: float,
                         hedef_fiyat: float, stop_fiyat: float,
                         beklenen_net_kar: float, beklenen_net_kayip: float,
                         calisma_modu: str) -> str:
    """
    v17 MODUL 3: Her ALIM icin ZENGIN, monospace bir ASCII kart uretir
    (konsol ve Telegram <pre> blogunda AYNI metin kullanilir). Sembol/Giris
    Fiyati (format_fiyat ile - mikro pariteler icin gercek hassasiyet),
    Yatirilan TL ve Alinan Miktar (adet), yuzdesel Hedef Satis/Stop-Loss ile
    beklenen +TL/-TL, RSI(14)/EMA(50)/ADX(14) gostergeleri ve Calisma Modu
    (Sniper Modu / Portfoy Modu (X/Y)) tek bir kartta gosterilir.
    """
    W = GIRIS_KARTI_GENISLIK

    def satir(s: str) -> str:
        return f"│ {s:<{W - 4}} │"

    def ic_cizgi() -> str:
        return f"├{'─' * (W - 2)}┤"

    hedef_pct = ((hedef_fiyat - exec_price) / exec_price * 100) if exec_price else 0.0
    stop_pct = ((stop_fiyat - exec_price) / exec_price * 100) if exec_price else 0.0

    ema_str = format_fiyat(ema50) if ema50 is not None else "N/A"
    rsi_str = f"{rsi14:.1f}" if rsi14 is not None else "N/A"
    adx_str = f"{adx14:.1f}" if adx14 is not None else "N/A"

    satirlar = [
        f"┌{'─' * (W - 2)}┐",
        satir(f"Sembol        : {symbol}"),
        satir(f"Giris Fiyati  : {format_fiyat(exec_price)} TRY"),
        satir(f"Yatirilan     : {yatirilan_tl:,.2f} TRY"),
        satir(f"Alinan Miktar : {adet:,.2f} {coin_name}"),
        ic_cizgi(),
        satir(f"Hedef Satis   : {format_fiyat(hedef_fiyat)} TRY ({hedef_pct:+.1f}%)"),
        satir(f"Hedef Kar     : {beklenen_net_kar:+,.2f} TRY"),
        satir(f"Stop-Loss     : {format_fiyat(stop_fiyat)} TRY ({stop_pct:+.1f}%)"),
        satir(f"Maks Risk     : {beklenen_net_kayip:+,.2f} TRY"),
        ic_cizgi(),
        satir(f"Gostergeler   : RSI:{rsi_str} | EMA:{ema_str}"),
        satir(f"Trend Gucu    : ADX:{adx_str} ({_adx_trend_etiketi(adx14)})"),
        satir(f"Mod           : {calisma_modu}"),
        f"└{'─' * (W - 2)}┘",
    ]
    return "\n".join(satirlar)


def giris_karti_telegram_gonder(kart_metni: str, symbol: str) -> None:
    """v17 MODUL 3: Giris kartini Telegram'a <pre> (monospace) blogu icinde,
    parse_mode="HTML" standardiyla arka plan worker thread kuyruguna
    (send_telegram -> _telegram_kuyrugu.put_nowait) iletir."""
    mesaj = f"\U0001F7E2 <b>[YENI POZISYON ACILDI] {symbol}</b>\n<pre>{kart_metni}</pre>"
    send_telegram(mesaj)


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
            fiyat = bot.last_real_price or bot.last_sim_price
            toplam += bot.coin_qty * fiyat
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
    return f"{saat:.0f}s"


def print_performans_raporu(kasa: MerkeziKasa, pozisyonlar: dict, acik_pozisyon_sayisi: int,
                             izin_verilen_pozisyon: Optional[int] = None):
    """Baslangic/Guncel Bakiye, Net K/Z (TRY ve %), toplam komisyon, acik
    pozisyonlar (v14: hedef satis + stop fiyatlariyla birlikte) ve bekleyen
    K/Z durumlarini temiz bir tabloda basar; ek olarak ozet bir Telegram
    mesaji da gonderir."""
    guncel_bakiye = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
    pnl = guncel_bakiye - kasa.baslangic
    pnl_pct = (pnl / kasa.baslangic) * 100 if kasa.baslangic else 0
    pnl_renk = GREEN if pnl >= 0 else RED
    limit_str = str(izin_verilen_pozisyon) if izin_verilen_pozisyon is not None else "?"

    print(f"{CYAN}{BOLD}{'=' * 70}{RESET}")
    print(f"{CYAN}{BOLD}  PERFORMANS RAPORU - {ts()}{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 70}{RESET}")
    print(f"  {'Baslangic Bakiyesi':<28}: {kasa.baslangic:>14,.2f} TRY")
    print(f"  {'Guncel Bakiye':<28}: {guncel_bakiye:>14,.2f} TRY")
    print(f"  {'Net Kar/Zarar':<28}: {pnl_renk}{pnl:>+14,.2f} TRY  ({pnl_pct:+.2f}%){RESET}")
    print(f"  {'Toplam Odenen Komisyon':<28}: {kasa.toplam_komisyon:>14,.2f} TRY")
    izin_verilen_sayi = izin_verilen_pozisyon if izin_verilen_pozisyon is not None else 0
    kapasite_notu = " (Kapasite Daraldi - Yeni Alim Yok)" if acik_pozisyon_sayisi > izin_verilen_sayi else ""
    print(f"  {'Acik Pozisyon Sayisi':<28}: {acik_pozisyon_sayisi} / {limit_str}{kapasite_notu}")
    print(f"{CYAN}{'-' * 70}{RESET}")

    acik_olanlar = [b for b in pozisyonlar.values() if b.has_open_position]
    if acik_olanlar:
        print(f"  {BOLD}Acik Pozisyonlar:{RESET}")
        print(f"  {'Sembol':<9} {'Yas':>6} {'Miktar':>12} {'Giris':>12} {'Guncel':>12} {'Hedef':>12} {'Stop':>12} "
              f"{'K/Z(TRY)':>10} {'K/Z%':>7}")
        for b in acik_olanlar:
            fiyat = b.last_real_price or b.last_sim_price
            deger = b.coin_qty * fiyat
            acik_seviye = next((lvl for lvl in b.grid if lvl.has_position), None)
            giris_fiyati = acik_seviye.buy_price if acik_seviye else 0.0
            maliyet = b.coin_qty * giris_fiyati
            kz = deger - maliyet  # v17: SADECE su an acik olan pozisyonun anlik K/Z'si (MODUL 4.2)
            kz_pct = (kz / maliyet * 100) if maliyet else 0
            renk = GREEN if kz >= 0 else RED
            hedef, stop, _ = b.acik_hedef_ve_stop()  # v14
            # v17 MODUL 2: mikro paritelerde ('0.0002' yerine gercek deger) dinamik hassasiyet
            hedef_str = "N/A" if hedef is None else (hedef if isinstance(hedef, str) else format_fiyat(hedef))
            stop_str = format_fiyat(stop) if stop is not None else "N/A"
            yas_str = _yas_formatla(b.alis_zamani)  # v16
            print(f"  {b.symbol:<9} {yas_str:>6} {b.coin_qty:>12.6f} {format_fiyat(giris_fiyati):>12} "
                  f"{format_fiyat(fiyat):>12} {hedef_str:>12} {stop_str:>12} "
                  f"{renk}{kz:>+10,.2f}{RESET} {renk}{kz_pct:>+6.2f}%{RESET}")
    else:
        print(f"  {YELLOW}Su an acik pozisyon yok - nakitte bekleniyor.{RESET}")

    beklemede_olanlar = [b for b in pozisyonlar.values() if b.bekliyor]
    cooldown_olanlar = [b for b in pozisyonlar.values() if not b.has_open_position and b.cooldown_aktif_mi()]
    if beklemede_olanlar:
        print(f"  {YELLOW}RSI asiri alimda bekleyen: {', '.join(b.symbol for b in beklemede_olanlar)}{RESET}")
    if cooldown_olanlar:
        bekleme_str = ", ".join(f"{b.symbol}({b.cooldown_kalan_dakika():.0f}dk)" for b in cooldown_olanlar)
        print(f"  {GRAY}Cooldown'da (yeni alim kilitli): {bekleme_str}{RESET}")

    print(f"{YELLOW}  Hatirlatma: {'CANLI MOD - GERCEK PARA.' if CANLI_MOD else 'Bu bir SIMULASYON.'}{RESET}")
    csv_portfoy_yaz(guncel_bakiye, kasa.baslangic, pnl, pnl_pct, acik_pozisyon_sayisi)
    print(f"{CYAN}{'=' * 70}{RESET}\n")

    ozet_emoji = "\U0001F4C8" if pnl >= 0 else "\U0001F4C9"
    send_telegram(
        f"{ozet_emoji} <b>Performans Ozeti</b>\n"
        f"Bakiye: {guncel_bakiye:,.2f} TRY\n"
        f"Net K/Z: {pnl:+,.2f} TRY ({pnl_pct:+.2f}%)\n"
        f"Acik Pozisyon: {acik_pozisyon_sayisi}/{limit_str}{kapasite_notu}\n"
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
            fiyat = b.last_real_price or b.last_sim_price
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

def run_simulation():
    print_banner()

    if CANLI_MOD and not canli_mod_on_kontrol():
        print(f"{RED}Bot baslatilamadi (CANLI_MOD guvenlik kontrolu basarisiz).{RESET}")
        return

    print(f"[{ts()}] Binance TR piyasasi taraniyor, TRY paritesi olan coinler bulunuyor...")
    try:
        semboller = try_paritelerini_bul()
    except Exception as e:
        print(f"{RED}Piyasa taranamadi: {e}{RESET}")
        return

    if not semboller:
        print(f"{RED}Hicbir TRY paritesi bulunamadi, bot baslatilamiyor.{RESET}")
        return

    print(f"[{ts()}] Toplam {len(semboller)} TRY paritesi bulundu.\n")

    try:
        watchlist, hacim_map, durum_map, bilgi_map = coin_degerlendir_ve_sec(semboller, MAX_WATCHLIST)
    except Exception as e:
        print(f"{RED}Coin degerlendirmesi yapilamadi: {e}{RESET}")
        return

    if not watchlist:
        print(f"{YELLOW}  Su an kriterlere uyan hicbir coin yok. Bot %100 nakitte bekleyecek "
              f"ve periyodik olarak piyasayi yeniden tarayacak.{RESET}\n")

    # v10 BOLUM 1: onceki oturumdan kalici durum var mi kontrol et
    kayitli_durum = durumu_yukle()
    if kayitli_durum:
        kasa, pozisyonlar, acik_baslangic_sayisi = durumdan_kasa_ve_pozisyonlar_olustur(kayitli_durum)
        acik_pozisyon_sayaci = [acik_baslangic_sayisi]
        rapor_verisi = kayitli_durum.get("raporlama")  # v11
        rapor = RaporlamaDurumu.from_dict(rapor_verisi, kasa.bakiye) if rapor_verisi else RaporlamaDurumu(kasa.bakiye)
        print(f"{GREEN}  Onceki oturumdan durum yuklendi: bakiye={kasa.bakiye:,.2f} TRY, "
              f"acik pozisyon={acik_baslangic_sayisi}, kaydedilme zamani="
              f"{kayitli_durum.get('kaydedilme_zamani', '?')}{RESET}")
        print(f"{GREEN}  X raporu son: {rapor.son_x_raporu_zamani.strftime('%d.%m.%Y %H:%M')} | "
              f"Z raporu son: {rapor.son_z_raporu_zamani.strftime('%d.%m.%Y %H:%M')}{RESET}\n")
    else:
        kasa = MerkeziKasa(TOPLAM_SANAL_BAKIYE_TRY)
        pozisyonlar: dict = {}
        acik_pozisyon_sayaci = [0]
        rapor = RaporlamaDurumu(TOPLAM_SANAL_BAKIYE_TRY)  # v11
        print(f"{YELLOW}  Kayitli durum bulunamadi, temiz baslangic: {TOPLAM_SANAL_BAKIYE_TRY:,.2f} TRY{RESET}\n")

    # v17 FIX: CANLI MOD ise borsadan gercek bakiyeyi cek ve kasa ile esitle.
    # Cekilen gercek serbest TRY tutari SIFIRDAN BUYUKSE, kasa.baslangic VE
    # kasa.bakiye DOGRUDAN bu tutara esitlenir (onceki oturumdan kayitli
    # durum olsa BILE) - boylece "hep 0.00 TRY" yanilgisindan sonra ilk
    # basarili canli baslangicta kasa GERCEK borsa bakiyesiyle net bir
    # sekilde senkronize olur. Tutar 0 (veya negatif/okunamadi) ise kasa
    # SESSIZCE sifirlanmaz - mevcut/kayitli deger korunur ve acikca uyarilir.
    if CANLI_MOD:
        try:
            gercek_bakiye = binance_serbest_try_bakiyesi()
            print(f"{GREEN}  CANLI MOD AKTIF - borsadan cekilen serbest TRY bakiyesi: {gercek_bakiye:,.2f} TRY{RESET}\n")
            if gercek_bakiye > 0:
                kasa.baslangic = gercek_bakiye
                kasa.bakiye = gercek_bakiye
            else:
                print(f"{YELLOW}  UYARI: Borsadan cekilen serbest TRY bakiyesi 0 (veya gecersiz) - "
                      f"kasa.baslangic/kasa.bakiye GUNCELLENMEDI, mevcut/kayitli deger korundu. "
                      f"[BORSA YANITI] satirini kontrol edin.{RESET}")
        except Exception as e:
            print(f"{RED}  HATA: Canli bakiye cekilemedi, bot baslatilamiyor: {e}{RESET}")
            return
        send_telegram(f"\U0001F7E2 <b>Project Aurelius CANLI MODDA baslatildi!</b>\nBorsa bakiyesi: {kasa.bakiye:,.2f} TRY")
    else:
        send_telegram(f"\U0001F9EA Project Aurelius SIMULASYON modunda baslatildi. Bakiye: {kasa.bakiye:,.2f} TRY")

    def kaydet():
        durumu_kaydet(kasa, pozisyonlar, rapor)

    real_poll_count = 0
    izin_verilen_pozisyon = 0  # v14: guvenli varsayilan (ilk tick'ten once bir kesinti olursa)
    sniper_modu_aktif = False  # v17: guvenli varsayilan
    scan_araligi_tur = max(1, round((SCAN_INTERVAL_MINUTES * 60) / REAL_POLL_INTERVAL_SECONDS))
    varlik_yenileme_araligi_tur = max(1, round((ASSET_REFRESH_HOURS * 3600) / REAL_POLL_INTERVAL_SECONDS))
    mutabakat_araligi_tur = max(1, round((MUTABAKAT_ARALIGI_SAAT * 3600) / REAL_POLL_INTERVAL_SECONDS))  # v16
    print(f"[{ts()}] Firsat taramasi her ~{SCAN_INTERVAL_MINUTES} dk'da bir, "
          f"varlik listesi yenilemesi her ~{ASSET_REFRESH_HOURS} saatte bir yapilacak.\n")

    try:
        while True:
            piyasa_sert_duste = False
            btc_degisim = None
            try:
                piyasa_sert_duste, btc_degisim = btc_piyasa_durumu()
                if piyasa_sert_duste:
                    print(f"[{ts()}] {RED}BTC 24s degisim %{btc_degisim:.2f} - piyasa sert dususte, "
                          f"YENI pozisyon aranmiyor (mevcut pozisyonlar yonetilmeye devam ediyor).{RESET}")
            except Exception:
                pass

            guncel_bakiye = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
            izin_verilen_pozisyon, hedef_pozisyon_tutari, sniper_modu_aktif = dinamik_pozisyon_planla(
                kasa.bakiye, guncel_bakiye, btc_degisim
            )  # v17: kasaya gore adaptif Sniper Modu / kademeli portfoy modeli
            en_kaliteli_aday = en_kaliteli_aday_belirle(bilgi_map, pozisyonlar)  # v17 MODUL 1.2

            ilgilenilecek_semboller = sorted(set(pozisyonlar.keys()) | set(watchlist))

            for sym in ilgilenilecek_semboller:
                if sym not in pozisyonlar:
                    dinamik_width = bilgi_map.get(sym, {}).get("width_pct", VARSAYILAN_WIDTH_PCT)  # v16
                    pozisyonlar[sym] = CoinBot(
                        symbol=sym,
                        coin_name=sym.replace("TRY", ""),
                        width_pct=dinamik_width,
                        grid_count=VARSAYILAN_GRID_SAYISI,
                        starting_try=0.0,
                        tek_pozisyon_modu=True,
                        bekliyor=(durum_map.get(sym) == "BEKLEMEDE"),
                    )
                bot = pozisyonlar[sym]

                try:
                    fiyat = get_last_price(sym)
                except Exception as e:
                    print(f"[{ts()}] {MAGENTA}{sym:<9}{RESET} {RED}gercek fiyat alinamadi: {e}{RESET}")
                    continue
                bot.last_real_price = fiyat
                bot.bu_turda_islem_yapildi = False

                if bot.bekliyor:
                    bot.bekleme_sayaci += 1
                    if bot.bekleme_sayaci % RSI_BEKLEME_KONTROL_ARALIGI_TUR == 0:
                        try:
                            durum, _, rsi14, _, _, _ = trend_ve_rsi_durumu(sym)
                        except Exception:
                            durum, rsi14 = "BEKLEMEDE", None
                        rsi_str = f"{rsi14:.1f}" if rsi14 is not None else "N/A"
                        if durum == "HAZIR":
                            print(f"[{ts()}] {MAGENTA}{sym:<9}{RESET} {GREEN}RSI sogudu (RSI={rsi_str}) - degerlendirmeye alindi.{RESET}")
                            bot.bekliyor = False
                        else:
                            print(f"[{ts()}] {MAGENTA}{sym:<9}{RESET} {YELLOW}hala beklemede (RSI={rsi_str}).{RESET}")
                    time.sleep(API_CALL_SLEEP_SECONDS)
                    continue

                if not bot.initialized:
                    bot.setup_grid(fiyat)

                if piyasa_sert_duste:
                    bot.stop_loss_kontrol(fiyat, sim=False, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                           durum_kaydet=kaydet, rapor=rapor)
                else:
                    bot.evaluate_v9(fiyat, sim=False, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                     hedef_pozisyon_tutari=hedef_pozisyon_tutari,
                                     izin_verilen_pozisyon=izin_verilen_pozisyon,
                                     durum_kaydet=kaydet, rapor=rapor, giris_bilgisi=bilgi_map.get(sym),
                                     en_kaliteli_aday=en_kaliteli_aday, sniper_modu=sniper_modu_aktif)

                time.sleep(API_CALL_SLEEP_SECONDS)

            real_poll_count += 1
            rapor.drawdown_guncelle(v9_toplam_portfoy_degeri(kasa, pozisyonlar))  # v11: Z donemi max drawdown takibi
            kaydet()  # her tick sonunda genel bir guvenlik-agi kaydi (bakiye/durum tazeligi)

            if kasa.baslangic > 0:
                guncel_kontrol = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
                kayip_pct = (kasa.baslangic - guncel_kontrol) / kasa.baslangic
                if kayip_pct >= MAX_DRAWDOWN_PCT:
                    print(f"\n{RED}{BOLD}{'!' * 74}{RESET}")
                    print(f"{RED}{BOLD}  ACIL FREN: Portfoy baslangictan %{kayip_pct*100:.2f} kaybetti "
                          f"(limit: %{MAX_DRAWDOWN_PCT*100:.0f}). TUM ACIK POZISYONLAR TASFIYE EDILIYOR.{RESET}")
                    print(f"{RED}{BOLD}{'!' * 74}{RESET}\n")
                    send_telegram(f"\U0001F6A8\U0001F6A8 <b>ACIL FREN DEVREYE GIRDI</b> \U0001F6A8\U0001F6A8\n"
                                  f"Portfoy %{kayip_pct*100:.2f} kayipta (limit %{MAX_DRAWDOWN_PCT*100:.0f}). "
                                  f"Tum pozisyonlar tasfiye ediliyor.")
                    for bot in pozisyonlar.values():
                        if bot.has_open_position:
                            fiyat = bot.last_real_price or bot.last_sim_price
                            bot.acil_tasfiye(fiyat, kasa, durum_kaydet=kaydet, rapor=rapor)
                    acik_pozisyon_sayaci[0] = 0
                    print_trade_history_table(pozisyonlar.values())
                    print_performans_raporu(kasa, pozisyonlar, 0, izin_verilen_pozisyon=0)
                    print(f"{RED}Bot acil fren nedeniyle durduruldu. Ayarlardan MAX_DRAWDOWN_PCT degistirilebilir.{RESET}")
                    return

            if real_poll_count % scan_araligi_tur == 0:
                try:
                    hedef_sayi = MIN_WATCHLIST if piyasa_sert_duste else MAX_WATCHLIST
                    watchlist, hacim_map, durum_map, bilgi_map = coin_degerlendir_ve_sec(semboller, hedef_sayi)
                except Exception as e:
                    print(f"{RED}Firsat taramasi basarisiz, mevcut watchlist ile devam ediliyor: {e}{RESET}")

            if real_poll_count % varlik_yenileme_araligi_tur == 0:
                print(f"\n{CYAN}{BOLD}{'*' * 74}{RESET}")
                print(f"{CYAN}{BOLD}  OTONOM VARLIK YENILEME - {ts()}{RESET}")
                print(f"{CYAN}{BOLD}{'*' * 74}{RESET}")
                try:
                    semboller = try_paritelerini_bul()
                    watchlist, hacim_map, durum_map, bilgi_map = coin_degerlendir_ve_sec(semboller, MAX_WATCHLIST)
                    for sym in list(pozisyonlar.keys()):
                        eski = pozisyonlar[sym]
                        if (not eski.has_open_position and sym not in watchlist
                                and not eski.cooldown_aktif_mi() and not eski.bekliyor):
                            del pozisyonlar[sym]
                    print(f"{CYAN}  Guncel izleme listesi: {', '.join(watchlist) if watchlist else '(bos - %100 nakit)'}{RESET}")
                except Exception as e:
                    print(f"{RED}Varlik yenileme basarisiz, mevcut liste ile devam ediliyor: {e}{RESET}")
                print(f"{CYAN}{BOLD}{'*' * 74}{RESET}\n")

            if real_poll_count % SUMMARY_EVERY_N_REAL_POLLS == 0:
                print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0],
                                         izin_verilen_pozisyon=izin_verilen_pozisyon)

            # v16 BOLUM 4: CANLI MOD bakiye mutabakati - periyodik (her ~6 saat)
            if real_poll_count % mutabakat_araligi_tur == 0:
                mutabakat_yap(kasa, pozisyonlar)

            # v11 BOLUM 6/7: X (gunluk) / Z (aylik) rapor zamanlamasi - ana dongude
            # datetime farkiyla kontrol edilir, ekstra zamanlayici kutuphane kullanilmaz.
            if rapor.x_suresi_doldu_mu():
                mutabakat_yap(kasa, pozisyonlar)  # v16: X raporu aninda da mutabakat yapilir
                x_raporu_olustur_ve_gonder(kasa, pozisyonlar, rapor)
                kaydet()
            if rapor.z_suresi_doldu_mu():
                z_raporu_olustur_ve_gonder(kasa, pozisyonlar, rapor)
                kaydet()

            if GERCEKCI_MOD:
                time.sleep(REAL_POLL_INTERVAL_SECONDS)
            else:
                for _ in range(SUB_TICKS_PER_REAL_POLL):
                    time.sleep(SUB_TICK_SECONDS)
                    guncel_bakiye_sim = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
                    izin_verilen_sim, hedef_sim, sniper_sim = dinamik_pozisyon_planla(
                        kasa.bakiye, guncel_bakiye_sim, btc_degisim
                    )
                    en_kaliteli_aday_sim = en_kaliteli_aday_belirle(bilgi_map, pozisyonlar)  # v17 MODUL 1.2
                    for bot in pozisyonlar.values():
                        if not bot.initialized or bot.bekliyor:
                            continue
                        sim_price = bot.next_sim_price()
                        if piyasa_sert_duste:
                            bot.stop_loss_kontrol(sim_price, sim=True, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                                   durum_kaydet=kaydet, rapor=rapor)
                        else:
                            bot.evaluate_v9(sim_price, sim=True, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                             hedef_pozisyon_tutari=hedef_sim, izin_verilen_pozisyon=izin_verilen_sim,
                                             durum_kaydet=kaydet, rapor=rapor, giris_bilgisi=bilgi_map.get(bot.symbol),
                                             en_kaliteli_aday=en_kaliteli_aday_sim, sniper_modu=sniper_sim)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}--- Simulasyon durduruldu (Ctrl+C) ---{RESET}\n")
        print_trade_history_table(pozisyonlar.values())
        print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0],
                                 izin_verilen_pozisyon=izin_verilen_pozisyon)
        send_telegram(f"\U0001F6D1 Project Aurelius durduruldu (Ctrl+C). Guncel bakiye: "
                      f"{v9_toplam_portfoy_degeri(kasa, pozisyonlar):,.2f} TRY")
        print(f"{YELLOW}Hatirlatma: {'Bu CANLI bir oturumdu.' if CANLI_MOD else 'Bu bir simulasyondu.'}{RESET}")
    except Exception as e:
        print(f"\n{RED}{BOLD}KRITIK HATA: {e}{RESET}\n")
        send_telegram(f"\U0001F6A8 Project Aurelius KRITIK HATA ile durdu: {e}")
        raise
    finally:
        durumu_kaydet(kasa, pozisyonlar, rapor)
        print(f"{GRAY}  Durum kaydedildi: {STATE_DOSYASI}{RESET}")


# ==========================================================================
# BACKTEST MODU - v8/v9 ile AYNI (tek_pozisyon_modu=False, coklu-seviye grid)
# ==========================================================================

def gecmis_fiyatlari_getir(symbol: str, gun: int) -> list:
    limit = min(gun * 24, 1000)
    url = KLINES_URL_TEMPLATE.format(symbol=symbol, interval="1h", limit=limit)
    req = urllib.request.Request(url, headers={"User-Agent": "grid-bot-sim"})
    data = http_istek_yap(req, timeout=30)
    return [float(mum[4]) for mum in data]


def backtest_calistir(symbol: str, gun: int, sermaye: float = None):
    sermaye = sermaye if sermaye is not None else TOPLAM_SANAL_BAKIYE_TRY

    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS - BACKTEST MODU (v17)'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"  Sembol: {symbol}   |   Test edilen sure: son {gun} gun (1 saatlik mumlarla)   |   Sermaye: {sermaye:,.2f} TRY\n")
    print(f"{YELLOW}  NOT: Backtest, ORIJINAL coklu-seviye grid davranisini kullanir "
          f"(tek_pozisyon_modu=False) - MAX_OPEN_POSITIONS/cooldown/CANLI_MOD burada gecerli "
          f"degildir, bu mod SADECE grid parametrelerinin TARIHSEL kalitesini test eder "
          f"(her zaman simulasyon, Telegram bildirimi gondermez).{RESET}\n")

    try:
        fiyatlar = gecmis_fiyatlari_getir(symbol, gun)
    except Exception as e:
        print(f"{RED}Gecmis veri alinamadi: {e}{RESET}")
        return

    if len(fiyatlar) < 10:
        print(f"{RED}Yeterli gecmis veri bulunamadi ({len(fiyatlar)} mum).{RESET}")
        return

    print(f"  {len(fiyatlar)} adet kapanis fiyati bulundu. Ilk fiyat: {fiyatlar[0]:,.4f} TRY, "
          f"son fiyat: {fiyatlar[-1]:,.4f} TRY\n")

    bot = CoinBot(
        symbol=symbol,
        coin_name=symbol.replace("TRY", ""),
        width_pct=VARSAYILAN_WIDTH_PCT,
        grid_count=VARSAYILAN_GRID_SAYISI,
        starting_try=sermaye,
        tek_pozisyon_modu=False,
        bildirim_aktif=False,  # v10: backtest Telegram'a spam atmaz
    )
    bot.setup_grid(fiyatlar[0])
    bot.opening_fill(fiyatlar[0])

    en_yuksek_portfoy = sermaye
    en_derin_dusus_pct = 0.0

    for fiyat in fiyatlar[1:]:
        bot.last_real_price = fiyat
        bot.stop_loss_kontrol(fiyat, sim=False)
        bot.evaluate(fiyat, sim=False)

        anlik_portfoy = bot.cash_try + bot.coin_qty * fiyat
        if anlik_portfoy > en_yuksek_portfoy:
            en_yuksek_portfoy = anlik_portfoy
        dusus_pct = (en_yuksek_portfoy - anlik_portfoy) / en_yuksek_portfoy if en_yuksek_portfoy > 0 else 0
        if dusus_pct > en_derin_dusus_pct:
            en_derin_dusus_pct = dusus_pct

    son_fiyat = fiyatlar[-1]
    bot.tasfiye_et(son_fiyat)

    portfoy = bot.cash_try
    pnl = portfoy - sermaye
    pnl_pct = (pnl / sermaye) * 100
    pnl_color = GREEN if pnl >= 0 else RED

    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}  BACKTEST SONUCU{RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"  Baslangic sermayesi : {sermaye:,.2f} TRY")
    print(f"  Bitis sermayesi     : {portfoy:,.2f} TRY")
    print(f"  Kar/Zarar           : {pnl_color}{pnl:+,.2f} TRY ({pnl_pct:+.2f}%){RESET}")
    print(f"  Toplam islem sayisi : {bot.trade_count} adet (alim+satim)")
    print(f"  Odenen toplam komisyon: {bot.toplam_komisyon:,.2f} TRY")
    print(f"  En derin dusus (max drawdown): %{en_derin_dusus_pct * 100:.2f}")
    print(f"{CYAN}{'=' * 74}{RESET}\n")
    print(f"{YELLOW}  Not: Bu bir GECMIS VERIYLE simulasyondur, gelecekteki performansi garanti etmez.{RESET}")


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "backtest":
        symbol = sys.argv[2].upper() if len(sys.argv) > 2 else "BTCTRY"
        gun = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        sermaye = float(sys.argv[4]) if len(sys.argv) > 4 else None
        backtest_calistir(symbol, gun, sermaye)
    else:
        run_simulation()


if __name__ == "__main__":
    main()
