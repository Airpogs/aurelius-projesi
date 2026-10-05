"""
PROJECT AURELIUS - v21
Binance TR otomatik alim-satim botu
======================================================================
v21 - GUNLUK TREND TAKIBI (VARSAYILAN STRATEJI):
  Gecmis veri testlerinde v19/v20'nin kisa vadeli stratejisi hicbir ayarla kar etmedi (cok fazla kucuk
  islem, masraflar ve oynak coinlerde stop). Gunluk trend takibi ise 3 yillik testte (4 x 270 gun) her
  donemde artida kaldi ('trend 270' komutu). v21 bu stratejiyi canli/simulasyon calismaya ekler:
   - Coinler: BTC, ETH, BNB, SOL, XRP, ADA, AVAX, DOGE, LINK, DOT, TRX, LTC (TRY pariteleri).
   - Gunde bir kez, gunluk mum kapanisindan sonra (TR ~03:05): gunluk kapanis son 50 gunun zirvesini
     kirdiysa, EMA50 ustundeyse ve BTC (USDT) EMA50 ustundeyse alim. En fazla 4 pozisyon, en guclu
     (60 gunluk getirisi en yuksek) once.
   - Stop: giris - 2 x ATR(20, gunluk); her gun zirve - 3 x ATR'ye yukselir, asla inmez. Hedef ve
     kismi kar alma yok - kazanan islem kosar. Gun icinde fiyat stop'a degerse satilir.
   - Islem basina risk AURELIUS_RISK_PCT (varsayilan %1), pozisyon en fazla portfoyun 1/4'u.
   - Acil fren (zirveden %20) gecerli; gunluk limit / mola / coin engeli trend stratejisinde
     uygulanmaz (test edilen kurallarda yoktu).
  Ayarlar: AURELIUS_STRATEJI=KISA (eski strateji), AURELIUS_TREND_KIRILIM (varsayilan 50),
  AURELIUS_TREND_BTC_FILTRE=0 (BTC filtresini kapatir). Acik eski pozisyonlar kendi kurallariyla
  yonetilmeye devam eder. Telegram performans ozeti artik 2 dk'da bir degil, durum bildirimiyle gider.
v20 - RISK KORUMASI, ISLEM GUNLUGU VE GECMIS VERI TESTI:
  1) Islem basina risk: pozisyon, stop olursa kaybin portfoyun en fazla
     AURELIUS_RISK_PCT'si (varsayilan %1) olacagi buyuklukte acilir (eskiden
     neredeyse tum kasa). 0 = kapali (eski davranis).
  2) Gunluk zarar limiti: portfoy gun basindan AURELIUS_GUNLUK_ZARAR_PCT
     (varsayilan %3) duserse o gun yeni alim yok. Art arda AURELIUS_KAYIP_SERISI
     (varsayilan 3) zararli islemden sonra 12 saat mola. Stop olan coine 24
     saat, 7 gunde 2 kez zarar ettiren coine 72 saat girilmez.
  3) Kalici sermaye tabani: acil fren artik her acilista sifirlanmiyor;
     portfoyun ulastigi en yuksek degerden %20 dusus olcer. Rapordaki
     baslangic sermayesi AURELIUS_BASLANGIC_SERMAYE ile verilebilir (yoksa
     v20'nin ilk acilisindaki portfoy). Bot calisirken yatirilan/cekilen TRY
     mutabakatta algilanir, kar/zarar sayilmaz.
  4) Islem gunlugu: her kapanan islem project_aurelius_islem_gunlugu.csv'ye
     (puan, BTC rejimi, R sonucu, cikis sebebi...) yazilir. 'rapor' komutu ve
     Telegram /rapor ozet verir.
  5) Gecmis veri testi: 'backtest [GUN] [SERMAYE] [SEMBOLLER]' v20 kurallarini
     (detayli analiz, R cikislari, risk korumasi, komisyon/kayma) gecmis
     mumlarda calistirir ve rapor verir. Emir gondermez, anahtar gerektirmez.
     'backtest 60 1000 60' gecmisteki bir donemi (60 gun once biten 60 gun) test eder.
     'karsilastir [GUN]' puan barajlarini (55-75) iki ardisik donemde yan yana karsilastirir.
     'strateji [GUN]' farkli kurallari (asiri oynak coinleri atlamak, genis stop, ek filtreler) uc
     ardisik donemde karsilastirir.
     'trend [DONEM_GUN]' farkli bir strateji turunu test eder: buyuk coinlerde gunluk kirilimla
     giris, genis ATR stop ve takip eden stop (4 x 180 gun = son 2 yil).
v19 - DETAYLI ANALIZ VE R TABANLI KAR ALMA:
  GIRIS: Bot bir coine girmeden once onu gunluk, 4 saatlik, 1 saatlik ve 15
  dakikalik mumlarla (her birinde ~200 kapanmis mum) inceler:
   - Zorunlu kurallar: gunluk dusus trendi yok; 4s trend yukari (EMA20>EMA50,
     fiyat EMA50 ustunde) ve guclu (4s ADX>=20, +DI>-DI); 1s ADX>=20 ve 1s'te
     geri cekilme bitmis (MACD guclenen veya fiyat EMA20 ustunde); 1s RSI 38-60, 4s RSI<=72;
     15dk'da asiri yukselis yok; en yakin dirence en az 1.5R alan var; USDT
     paritesinde dusus yok (TRY yukselisi lira kaynakli olmasin); BTC riskli
     degil; BTC zayifken BTC'ye bagli (korelasyon>=0.6) coine girilmez.
   - Puan (0-100): trend 30, ivme (MACD/RSI) 20, hacim (goreceli hacim, OBV,
     alici payi) 20, kar alani 15, BTC 10, USDT trendi 5. Min puan 55
     (AURELIUS_MIN_SKOR ile degistirilebilir). En yuksek puanliya girilir.
  BTC REJIMI: gunluk/4s trend, 4s ADX yonu, son 4s/24s degisim ve oynaklikla
  GUCLU (tam kapasite) / NOTR, ZAYIF (yarim) / RISKLI (yeni alim yok).
  CIKIS (R = giris ile stop arasi): stop destegin alti veya 1.5xATR (%2-6);
  +1R'de 1/3 satilir ve stop basa-basa; +2R'de kalanin yarisi satilir ve stop
  +1R'ye kilitlenir; son kisim zirve-2.5xATR takip eden stopla, ust sinir yok.
  v18 pozisyonlari otomatik aktarilir (1R = eski %4 stop).
  KOMUTLAR: 'analiz SEMBOL' (konsol), /analiz SEMBOL ve /btc (Telegram).
v18 - KESINTI ONLEMLERI (bot kapaliyken pozisyonlar korumasiz kalmasin):
  1) Durum bildirimi: AURELIUS_DURUM_BILDIRIM_SAAT (varsayilan 2, 0=kapali)
     saatte bir Telegram'a portfoy ozeti. AURELIUS_SAGLIK_URL verilirse
     (orn. healthchecks.io ping adresi) 5 dk'da bir "calisiyorum" sinyali;
     sinyal kesilirse (elektrik kesintisi dahil) o servis size haber verir.
  2) Otomatik yeniden baslatma: 'python project_aurelius_bot_v21.py kurulum'
     bu penceredeki ayarlarla baslat.bat (Linux: baslat.sh) olusturur; bot
     coker/baslayamazsa 60 sn sonra yeniden baslar. Istege bagli: Windows
     oturumu acilinca otomatik baslatma. Cikis kodlari: 0 bilincli durdurma,
     1 gecici hata/cokme (yeniden baslat), 2 ayar hatasi.
  3) Bosaltma modu (/bosalt): yeni alim yapilmaz, pozisyonlar kapaninca bot
     durur. Ctrl+C'de acik pozisyon varsa "birak / hepsini sat" sorulur.
  4) Telegram komutlari (sadece TELEGRAM_CHAT_ID'den): /durum /alimdurdur
     /devam /bosalt /hepsinisat (+ /onayla) /yardim. Kapatmak icin
     AURELIUS_TELEGRAM_KOMUT=0. Bot kapaliyken gonderilen komutlar yok sayilir.
  5) Borsada koruyucu stop emri (AURELIUS_BORSA_STOP=1, varsayilan KAPALI):
     her pozisyon icin borsaya STOP_LOSS_LIMIT satis emri konur (tetik: bot
     stop'unun %1 alti), stop yukseldikce emir yukari tasinir, bot satmadan
     once emri iptal eder. Bot/bilgisayar kapaliyken de borsa zarari keser.
     Emir turu RESMI olarak dogrulanmadi - ilk kullanimda [BORSA YANITI]
     satirlarini ve Binance TR'deki acik emirlerinizi kontrol edin.
v17 FIX-2 - TAM KOD INCELEMESI DUZELTMELERI:
  CANLI EMIR GUVENLIGI
  - Emir (POST) istekleri artik otomatik tekrar denenmiyor (zaman asimi/
    5xx sonrasi tekrar, ayni emri iki kez gonderebiliyordu).
  - HTTP 200 + code!=0 donen (reddedilen) emirler artik basari sayilmiyor.
  - /open/v1 emir sembolu 'PEPETRY' -> 'PEPE_TRY' bicimine cevriliyor.
  - SATIS miktari borsadaki gercek serbest bakiyeyle sinirlaniyor (alim
    komisyonu coinden kesildigi icin tam miktar reddediliyor, stop-loss
    mutabakata kadar calismiyordu); tam kapanista satilamayan toz yazilip
    pozisyon kapatiliyor.
  SAHTE ACIL FREN RISKLERI
  - Okunamayan bakiye yaniti artik 0 TRY sayilmiyor (mutabakat kasayi
    sifirlayip tum pozisyonlari tasfiye ettirebiliyordu).
  - Fiyati alinamayan pozisyon 0 TL yerine giris fiyatindan degerleniyor.
  DURUM/KASA
  - Durum dosyasi calisma_modu ile etiketleniyor; SIMULASYON durumu CANLI
    modda yuklenmiyor (yedeklenir). Canli bakiye 0 ise sanal 5.000 TL ile
    emir denenmiyor.
  - Mutabakat tek hesap sorgusu yapiyor, sadece ASAGI senkronize ediyor
    (bot disi coinleri sahiplenmez) ve borsada artik olmayan pozisyonu
    kapatiyor; acik pozisyon sayaci her tick yeniden hesaplaniyor.
  DIGER
  - Grid, pozisyon yokken fiyat banttan cikinca yeniden ortalaniyor (aksi
    halde coin izleme listesinde kaldikca bir daha alinamiyordu).
  - Kritik Telegram uyarilari: istisna metni HTML-kacirilir, cikista kuyruk
    bosaltilir (ACIL FREN / KRITIK HATA mesajlari kayboluyordu).
  - Reddedilen kismi kar alma her tick tekrar denenmiyor; ZAMAN-ASIMI satisi
    basarisizsa stop-loss kontrolu atlanmiyor; coin adi 'TRY' sonekiyle
    dogru ayriliyor.

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
     GERCEK yanit zarfini ({"code":0,"data":{"accountAssets":[...]}};
     yedek olarak "balances"/"assets") destekler. Eski kod dogrudan kok dizinde
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
       degiskenlerini dogrular, /open/v1/account/spot'tan GERCEK serbest
       TRY bakiyesini ceker ve MerkeziKasa ile esitler, evaluate_v9 ve
       acil_tasfiye icindeki her alim/satimda RFC 2104 HMAC-SHA256
       imzali GERCEK MARKET emrini /open/v1/orders'a gonderir.
     - Windows'ta ortam degiskenleri (cmd, TIRNAKSIZ):
           set BINANCE_TR_API_KEY=anahtariniz
           set BINANCE_TR_SECRET_KEY=gizli_anahtariniz
           set AURELIUS_LIVE_CONFIRM=EVET_GERCEK_PARA_KULLAN
           set AURELIUS_CANLI_MOD=1   (dosyada CANLI_MOD'u duzenlemeden acar)
       PowerShell: $env:BINANCE_TR_API_KEY="anahtariniz" (vb.)
       Degiskenler SADECE o terminal penceresinde gecerlidir; botu ayni
       pencereden calistirin.
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
    python project_aurelius_bot_v21.py                          (canli/simulasyon - CANLI_MOD bayragina gore)
    python project_aurelius_bot_v21.py backtest [GUN] [SERMAYE] [SEMBOLLER]  (gecmis veri testi, emir gondermez)
    python project_aurelius_bot_v21.py analiz [SEMBOL]          (detayli analiz raporu, emir gondermez)
    python project_aurelius_bot_v21.py rapor                    (islem gunlugu ozeti)
    python project_aurelius_bot_v21.py karsilastir [GUN]        (puan barajlarini iki donemde karsilastirir)
    python project_aurelius_bot_v21.py strateji [GUN]           (farkli kurallari uc donemde karsilastirir)
    python project_aurelius_bot_v21.py trend [DONEM_GUN]        (gunluk trend takibini 4 donemde test eder)
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
RSI_BEKLEME_KONTROL_ARALIGI_TUR = 2

# CSV kayit dosyalari + v10 STATE dosyasi - script ile ayni klasore yazilir
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ISLEMLER_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_islemler.csv")
PORTFOY_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_portfoy_gecmisi.csv")
STATE_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius_state.json")  # v10
Z_RAPORLARI_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_z_raporlari.csv")  # v11
LOG_DOSYASI = os.path.join(_SCRIPT_DIR, "project_aurelius.log")  # v13
ISLEM_GUNLUGU_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_islem_gunlugu.csv")  # v20
BACKTEST_ISLEMLERI_CSV = os.path.join(_SCRIPT_DIR, "project_aurelius_backtest_islemleri.csv")  # v20

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
# (5) Borsada bekleyen koruyucu stop emri - varsayilan KAPALI, AURELIUS_BORSA_STOP=1 ile
#     acilir. Tetik fiyati botun kendi stop'unun BORSA_STOP_TAMPON_PCT altindadir: bot
#     calisirken once kendi stop'u satar, bot kapaliyken borsadaki emir satar.
BORSA_STOP_AKTIF = _ortam_degiskeni_str_oku("AURELIUS_BORSA_STOP") == "1"
BORSA_STOP_TAMPON_PCT = 0.01
BORSA_STOP_LIMIT_ARALIK_PCT = 0.01      # limit fiyati tetigin bu kadar altinda (dolma sansi icin)
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


# v20 RISK KORUMASI (ayrintilar dosya basindaki v20 notunda)
RISK_PCT = _aralikta(_ortam_sayisi_oku("AURELIUS_RISK_PCT", 1.0), 0.0, 5.0) / 100
GUNLUK_ZARAR_LIMIT_PCT = _aralikta(_ortam_sayisi_oku("AURELIUS_GUNLUK_ZARAR_PCT", 3.0), 0.0, 50.0) / 100
KAYIP_SERISI_LIMIT = int(_aralikta(_ortam_sayisi_oku("AURELIUS_KAYIP_SERISI", 3), 0, 20))
KAYIP_SERISI_MOLA_SAAT = 12.0
COIN_STOP_ENGEL_SAAT = 24.0          # STOP-LOSS ile kapanan coine bu sure girilmez
COIN_TEKRAR_KAYIP_SAYISI = 2         # ayni coinde COIN_TEKRAR_KAYIP_GUN icinde bu kadar zarar ->
COIN_TEKRAR_KAYIP_GUN = 7
COIN_TEKRAR_ENGEL_SAAT = 72.0        # ... coine bu sure girilmez
MIN_POZISYON_TUTARI_TRY = 30.0       # risk hesabi bunun altinda bir tutar verirse bu tutar kullanilir
BASLANGIC_SERMAYE_TRY = max(0.0, _ortam_sayisi_oku("AURELIUS_BASLANGIC_SERMAYE", 0.0))
SERMAYE_HAREKETI_MIN_TRY = 5.0       # mutabakatta bundan (ve portfoyun %1'inden) buyuk TRY farki
SERMAYE_HAREKETI_MIN_ORAN = 0.01     # para yatirma/cekme sayilir
FREN_SIFIRLA = _ortam_degiskeni_str_oku("AURELIUS_FREN_SIFIRLA") == "1"

# v21 STRATEJI SECIMI: TREND (varsayilan, gunluk trend takibi - 3 yillik testte her donemde arti) veya
# KISA (v19/v20 kisa vadeli detayli analiz stratejisi - testlerde kaybettirdi, sadece karsilastirma icin).
STRATEJI = (_ortam_degiskeni_str_oku("AURELIUS_STRATEJI") or "TREND").upper()
TREND_MODU = STRATEJI != "KISA"
TREND_KIRILIM_GUN = int(_aralikta(_ortam_sayisi_oku("AURELIUS_TREND_KIRILIM", 50), 10, 100))
TREND_BTC_FILTRESI = _ortam_degiskeni_str_oku("AURELIUS_TREND_BTC_FILTRE") != "0"
TREND_KONTROL_GECIKME_DK = 5        # gunluk mum 00:00 UTC'de (TR 03:00) kapanir; bu kadar dakika sonra kontrol
TREND_KOVALAMA_ATR = 0.5            # fiyat sinyal kapanisindan 0.5 x ATR'den fazla kactiysa girilmez
TREND_GUNLUK_MUM = 300              # gunluk kontrolde cekilen gecmis (tek istek)
_trend_durumu: dict = {}            # {"son_gun": ms} - durum dosyasina kaydedilir

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
# v20 BOLUM 1: RISK KORUMASI (durum dosyasina kaydedilir, yeniden baslatmada
# sifirlanmaz). Zaman 'simdi' ile verilebilir - gecmis veri testi ayni sinifi kullanir.
# ==========================================================================

def _tarih_oku(deger) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(deger) if deger else None
    except (TypeError, ValueError):
        return None


class RiskKorumasi:
    def __init__(self):
        self.yatirilan_sermaye = 0.0      # raporlardaki "baslangic sermayesi"
        self.zirve_portfoy = 0.0          # acil fren bu degerden olan dususu olcer
        self.gun = ""
        self.gun_baslangic_portfoy = 0.0
        self.ardisik_kayip = 0
        self.mola_bitis: Optional[datetime] = None
        self.coin_engel: dict = {}        # sembol -> engelin bittigi an
        self.coin_kayiplari: dict = {}    # sembol -> son COIN_TEKRAR_KAYIP_GUN gundeki zararli kapanislar
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

    def yeni_alim_engeli(self, portfoy: float, simdi: Optional[datetime] = None) -> Optional[tuple]:
        """Yeni alim yapilmamasi gerekiyorsa (kod, aciklama), yoksa None."""
        simdi = simdi or datetime.now()
        if self.fren_beklemede:
            return ("FREN", f"portfoy kayitli en yuksek degerinden ({self.zirve_portfoy:,.2f} TRY) "
                            f"%{self.zirveden_dusus(portfoy) * 100:.0f} asagida; devam icin /frensifirla")
        if GUNLUK_ZARAR_LIMIT_PCT > 0 and self.gunluk_degisim(portfoy) <= -GUNLUK_ZARAR_LIMIT_PCT:
            return ("GUNLUK", f"gunluk zarar limiti doldu (portfoy bugun %{self.gunluk_degisim(portfoy) * 100:.1f}, "
                              f"limit -%{GUNLUK_ZARAR_LIMIT_PCT * 100:g}); yeni alimlar yarin acilacak")
        if self.mola_bitis is not None and simdi < self.mola_bitis:
            return ("MOLA", f"art arda zararli islemler - yeni alimlara mola "
                            f"({self.mola_bitis.strftime('%d.%m %H:%M')}'e kadar)")
        return None

    def coin_engel_bitisi(self, sembol: str, simdi: Optional[datetime] = None) -> Optional[datetime]:
        bitis = self.coin_engel.get(sembol)
        return bitis if bitis is not None and (simdi or datetime.now()) < bitis else None

    def islem_kapandi(self, sembol: str, net_kar: float, etiket: str,
                      simdi: Optional[datetime] = None) -> list:
        """Tamamen kapanan islemi isler; kullaniciya gosterilecek mesajlari dondurur."""
        simdi = simdi or datetime.now()
        if net_kar >= 0:
            self.ardisik_kayip = 0
            return []
        mesajlar = []
        self.ardisik_kayip += 1
        sinir = simdi - timedelta(days=COIN_TEKRAR_KAYIP_GUN)
        kayiplar = [t for t in self.coin_kayiplari.get(sembol, []) if t > sinir] + [simdi]
        self.coin_kayiplari[sembol] = kayiplar
        engel_saat, sebep = 0.0, ""
        if len(kayiplar) >= COIN_TEKRAR_KAYIP_SAYISI:
            engel_saat, sebep = COIN_TEKRAR_ENGEL_SAAT, f"son {COIN_TEKRAR_KAYIP_GUN} gunde {len(kayiplar)}. zarar"
        elif etiket in ("STOP-LOSS", "BORSA-STOP"):
            engel_saat, sebep = COIN_STOP_ENGEL_SAAT, "stop-loss ile kapandi"
        if engel_saat > 0:
            bitis = simdi + timedelta(hours=engel_saat)
            if bitis > self.coin_engel.get(sembol, simdi):
                self.coin_engel[sembol] = bitis
                mesajlar.append(f"{sembol} {sebep} - {engel_saat:.0f} saat bu coine girilmeyecek.")
        if KAYIP_SERISI_LIMIT > 0 and self.ardisik_kayip >= KAYIP_SERISI_LIMIT:
            self.mola_bitis = simdi + timedelta(hours=KAYIP_SERISI_MOLA_SAAT)
            mesajlar.append(f"Art arda {self.ardisik_kayip} zararli islem - yeni alimlara "
                            f"{KAYIP_SERISI_MOLA_SAAT:.0f} saat mola.")
            self.ardisik_kayip = 0
        return mesajlar

    def sermaye_hareketi(self, fark: float) -> None:
        """Para yatirma (+) / cekme (-): kar-zarar sayilmasin, fren tetiklenmesin."""
        self.yatirilan_sermaye = max(0.0, self.yatirilan_sermaye + fark)
        self.zirve_portfoy = max(0.0, self.zirve_portfoy + fark)
        if self.gun_baslangic_portfoy > 0:
            self.gun_baslangic_portfoy = max(0.0, self.gun_baslangic_portfoy + fark)

    def temizle(self, simdi: Optional[datetime] = None) -> None:
        simdi = simdi or datetime.now()
        self.coin_engel = {s: t for s, t in self.coin_engel.items() if t > simdi}
        sinir = simdi - timedelta(days=COIN_TEKRAR_KAYIP_GUN)
        kayiplar = {s: [t for t in liste if t > sinir] for s, liste in self.coin_kayiplari.items()}
        self.coin_kayiplari = {s: liste for s, liste in kayiplar.items() if liste}

    def durum_satirlari(self, portfoy: float, simdi: Optional[datetime] = None) -> list:
        simdi = simdi or datetime.now()
        satirlar = [f"Risk: islem basina %{RISK_PCT * 100:g} | bugun %{self.gunluk_degisim(portfoy) * 100:+.1f}"
                    + ("" if TREND_MODU else f" (limit -%{GUNLUK_ZARAR_LIMIT_PCT * 100:g})")
                    + f" | zirveden -%{self.zirveden_dusus(portfoy) * 100:.1f} (acil fren %{MAX_DRAWDOWN_PCT * 100:.0f})"]
        engel = self.yeni_alim_engeli(portfoy, simdi)
        if engel and (not TREND_MODU or engel[0] == "FREN"):  # trend modunda sadece acil fren uygulanir
            satirlar.append(f"Yeni alim engeli: {engel[1]}")
        engelli = [] if TREND_MODU else sorted((s, t) for s, t in self.coin_engel.items() if t > simdi)
        if engelli:
            satirlar.append("Engelli coinler: " + ", ".join(f"{s} ({t.strftime('%d.%m %H:%M')})" for s, t in engelli))
        return satirlar

    def to_dict(self) -> dict:
        return {
            "yatirilan_sermaye": self.yatirilan_sermaye,
            "zirve_portfoy": self.zirve_portfoy,
            "gun": self.gun,
            "gun_baslangic_portfoy": self.gun_baslangic_portfoy,
            "ardisik_kayip": self.ardisik_kayip,
            "mola_bitis": self.mola_bitis.isoformat() if self.mola_bitis else None,
            "coin_engel": {s: t.isoformat() for s, t in self.coin_engel.items()},
            "coin_kayiplari": {s: [t.isoformat() for t in liste] for s, liste in self.coin_kayiplari.items()},
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
            obj.ardisik_kayip = int(veri.get("ardisik_kayip") or 0)
        except (TypeError, ValueError):
            pass
        obj.mola_bitis = _tarih_oku(veri.get("mola_bitis"))
        obj.coin_engel = {s: t for s, t in ((s, _tarih_oku(v)) for s, v in (veri.get("coin_engel") or {}).items()) if t}
        obj.coin_kayiplari = {s: [t for t in map(_tarih_oku, liste or []) if t]
                              for s, liste in (veri.get("coin_kayiplari") or {}).items()}
        obj.acil_fren_tetiklendi = bool(veri.get("acil_fren_tetiklendi"))
        obj.fren_beklemede = bool(veri.get("fren_beklemede"))
        return obj


_risk = RiskKorumasi()


def risk_bazli_tutar(portfoy: float, stop_pct: float, ust_sinir: float) -> float:
    """Stop olursa kayip portfoyun RISK_PCT'si olacak pozisyon tutari (ust_sinir'i asmaz)."""
    if RISK_PCT <= 0 or stop_pct <= 0 or portfoy <= 0:
        return ust_sinir
    return min(ust_sinir, max(portfoy * RISK_PCT / stop_pct, MIN_POZISYON_TUTARI_TRY))


# ==========================================================================
# v20 BOLUM 2: ISLEM GUNLUGU (kapanan her islem icin bir satir)
# ==========================================================================
ISLEM_GUNLUGU_ALANLARI = [
    "giris_zamani", "cikis_zamani", "sembol", "kaynak", "giris_fiyati", "cikis_fiyati", "tutar_try",
    "net_kar_try", "net_kar_pct", "r_sonucu", "risk_try", "stop_pct", "sure_saat", "cikis_sebebi",
    "hedef1", "hedef2", "puan", "btc_rejimi", "gunluk_trend", "h4_trend", "rsi_1h", "adx_4h", "goreceli_hacim",
]
GIRIS_ANALIZ_ALANLARI = {"puan": "skor", "btc_rejimi": "btc_rejim", "gunluk_trend": "gunluk_trend",
                         "h4_trend": "h4_trend", "rsi_1h": "rsi_1h", "adx_4h": "adx_4h",
                         "goreceli_hacim": "goreceli_hacim"}


def _sayi(deger) -> Optional[float]:
    if deger is None or deger == "":
        return None
    try:
        return float(deger)
    except (TypeError, ValueError):
        return None


def giris_analiz_ozeti(derin: Optional[dict]) -> dict:
    """Detayli analizden gunluge yazilacak alanlar (analiz yoksa bos)."""
    derin = derin or {}
    if not derin.get("gecti"):
        return {}
    return {alan: derin.get(kaynak) for alan, kaynak in GIRIS_ANALIZ_ALANLARI.items()}


def islem_kaydi_olustur(sembol: str, kaynak: str, giris_zamani: Optional[datetime], cikis_zamani: datetime,
                        giris_fiyati: float, cikis_fiyati: float, tutar: float, net_kar: float,
                        risk_try: float, stop_pct: float, cikis_sebebi: str, hedef1: bool, hedef2: bool,
                        analiz: Optional[dict] = None) -> dict:
    kayit = {
        "giris_zamani": giris_zamani.strftime("%Y-%m-%d %H:%M") if giris_zamani else "",
        "cikis_zamani": cikis_zamani.strftime("%Y-%m-%d %H:%M"),
        "sembol": sembol, "kaynak": kaynak, "giris_fiyati": giris_fiyati, "cikis_fiyati": cikis_fiyati,
        "tutar_try": tutar, "net_kar_try": net_kar,
        "net_kar_pct": net_kar / tutar * 100 if tutar else None,
        "r_sonucu": net_kar / risk_try if risk_try > 0 else None,
        "risk_try": risk_try, "stop_pct": stop_pct * 100 if stop_pct else None,
        "sure_saat": (cikis_zamani - giris_zamani).total_seconds() / 3600 if giris_zamani else None,
        "cikis_sebebi": cikis_sebebi, "hedef1": "E" if hedef1 else "H", "hedef2": "E" if hedef2 else "H",
    }
    for alan in GIRIS_ANALIZ_ALANLARI:
        kayit[alan] = (analiz or {}).get(alan)
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


def _grup_ozeti(baslik: str, kayitlar: list, anahtar, sira: Optional[list] = None) -> str:
    gruplar: dict = {}
    for k in kayitlar:
        gruplar.setdefault(anahtar(k), []).append(k)
    parcalar = []
    for ad in (sira or sorted(gruplar)):
        grup = gruplar.get(ad)
        if not grup:
            continue
        kar = [_sayi(k.get("net_kar_try")) or 0.0 for k in grup]
        rler = [r for r in (_sayi(k.get("r_sonucu")) for k in grup) if r is not None]
        kazanan = sum(1 for x in kar if x > 0)
        parcalar.append(f"{ad}: {len(grup)} islem, %{kazanan / len(grup) * 100:.0f} kazanan, "
                        + (f"{_ortalama(rler):+.2f}R" if rler else f"{sum(kar):+.2f} TL"))
    return f"{baslik}: " + " | ".join(parcalar)


def _puan_grubu(kayit: dict) -> str:
    puan = _sayi(kayit.get("puan"))
    if puan is None:
        return "puansiz"
    return "<60" if puan < 60 else "60-70" if puan < 70 else "70+"


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
        _grup_ozeti("Puana gore", kayitlar, _puan_grubu, ["<60", "60-70", "70+", "puansiz"]),
        _grup_ozeti("BTC rejimine gore", kayitlar, lambda k: k.get("btc_rejimi") or "bilinmiyor",
                    ["GUCLU", "NOTR", "ZAYIF", "BILINMIYOR", "bilinmiyor"]),
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
    """
    Acik pozisyonlari, giris fiyatlarini, trailing-stop icin en yuksek
    gorulen fiyatlari, merkezi kasa bakiyesini VE (v11) X/Z rapor zaman
    damgalari ile donemsel sayaclari JSON dosyasina ATOMIK olarak yazar
    (once .tmp dosyasina yazip os.replace ile degistirir - yazma
    sirasinda bot cokerse bile dosya asla yarim/bozuk kalmaz).
    """
    try:
        veri = {
            "calisma_modu": _aktif_calisma_modu(),
            "alim_durumu": _alim_durumu,  # v18
            "kasa_bakiye": kasa.bakiye,
            "kasa_baslangic": kasa.baslangic,
            "kasa_toplam_komisyon": kasa.toplam_komisyon,
            "kaydedilme_zamani": datetime.now().isoformat(),
            "risk": _risk.to_dict(),  # v20
            "strateji": STRATEJI,  # v21
            "trend": _trend_durumu,
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
                "giris_bilgi": b.giris_bilgi,  # v20
                "acik_islem_pnl": b.acik_islem_pnl,
                "grid": [
                    {
                        "price": lvl.price,
                        "has_position": lvl.has_position,
                        "buy_qty": lvl.buy_qty,
                        "buy_price": lvl.buy_price,
                        "en_yuksek_fiyat": lvl.en_yuksek_fiyat,
                        "kismi_kar_alindi": lvl.kismi_kar_alindi,
                        "borsa_stop_emir_id": lvl.borsa_stop_emir_id,  # v18
                        "borsa_stop_fiyati": lvl.borsa_stop_fiyati,
                        "borsa_stop_miktari": lvl.borsa_stop_miktari,
                        "risk_birimi": lvl.risk_birimi,  # v19
                        "ilk_stop": lvl.ilk_stop,
                        "atr_giris": lvl.atr_giris,
                        "tp1_alindi": lvl.tp1_alindi,
                        "tp2_alindi": lvl.tp2_alindi,
                        "trend_stop": lvl.trend_stop,  # v21
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
    """v10: Kaydedilmis JSON verisinden MerkeziKasa ve CoinBot nesnelerini
    yeniden insa eder - bot kaldigi yerden aynen devam eder."""
    kasa = MerkeziKasa(veri.get("kasa_baslangic", TOPLAM_SANAL_BAKIYE_TRY))
    kasa.bakiye = veri.get("kasa_bakiye", kasa.baslangic)
    kasa.toplam_komisyon = veri.get("kasa_toplam_komisyon", 0.0)

    pozisyonlar = {}
    for sym, p in veri.get("pozisyonlar", {}).items():
        b = CoinBot(
            symbol=sym,
            coin_name=p.get("coin_name", _coin_adi(sym)),
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
        b.giris_bilgi = p.get("giris_bilgi") or {}  # v20
        b.acik_islem_pnl = p.get("acik_islem_pnl", 0.0)
        b.grid = [
            GridLevel(
                price=lvl["price"],
                has_position=lvl["has_position"],
                buy_qty=lvl["buy_qty"],
                buy_price=lvl["buy_price"],
                en_yuksek_fiyat=lvl["en_yuksek_fiyat"],
                kismi_kar_alindi=lvl.get("kismi_kar_alindi", False),
                borsa_stop_emir_id=lvl.get("borsa_stop_emir_id"),  # v18
                borsa_stop_fiyati=lvl.get("borsa_stop_fiyati", 0.0),
                borsa_stop_miktari=lvl.get("borsa_stop_miktari", 0.0),
                risk_birimi=lvl.get("risk_birimi", 0.0),  # v19
                ilk_stop=lvl.get("ilk_stop", 0.0),
                atr_giris=lvl.get("atr_giris", 0.0),
                tp1_alindi=lvl.get("tp1_alindi", False),
                tp2_alindi=lvl.get("tp2_alindi", False),
                trend_stop=lvl.get("trend_stop", 0.0),  # v21
            )
            for lvl in p.get("grid", [])
        ]
        for lvl in b.grid:
            if lvl.has_position and lvl.risk_birimi <= 0 and lvl.buy_price > 0:
                # v19: v18 ve oncesinde acilmis pozisyonu yeni sisteme aktar:
                # eski sabit %4 stop = 1R; kismi kar alindiysa hedef 1 alinmis sayilir.
                lvl.risk_birimi = lvl.buy_price * STOP_LOSS_PCT
                lvl.ilk_stop = lvl.buy_price - lvl.risk_birimi
                lvl.atr_giris = lvl.risk_birimi / R_STOP_ATR_KATSAYI
                lvl.tp1_alindi = lvl.kismi_kar_alindi
                print(f"{CYAN}  {sym}: onceki surumde acilan pozisyon yeni kar alma sistemine aktarildi "
                      f"(1R = %{STOP_LOSS_PCT * 100:.0f}).{RESET}")
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
        "    python project_aurelius_bot_v21.py baglanti",
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
    'python project_aurelius_bot_v21.py baglanti' ile calisir. API anahtari
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
            # Borsada pozisyon fiilen yok (orn. elle satilmis): ic kaydi kapat,
            # yoksa bot var olmayan coini her tick satmaya calisir ve slot
            # sonsuza kadar dolu kalir.
            print(f"{YELLOW}  MUTABAKAT: {bot.symbol} borsada artik yok "
                  f"({bot.coin_qty:.8f} -> {gercek_miktar:.8f}) - ic pozisyon kapatildi.{RESET}")
            logger.warning("Mutabakat: %s borsada yok, ic pozisyon kapatildi (%.8f -> %.8f)",
                           bot.symbol, bot.coin_qty, gercek_miktar)
            bot.coin_qty = 0.0
            bot.alis_zamani = None
            if acik_seviye:
                acik_seviye.has_position = False
                acik_seviye.buy_qty = 0.0
                acik_seviye.borsa_stop_emir_id = None
                acik_seviye.borsa_stop_fiyati = 0.0
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
    olmalidir. Bu fonksiyon partial-fill (kismi gerceklesme) durumunu
    ayrica sorgulamaz - tek seferlik MARKET emri gonderir ve borsanin
    dondurdugu yaniti aynen dondurur (ham yaniti da [BORSA YANITI] ile
    terminale basar - GERCEK PARAYLA ILK EMIRDEN SONRA bu satiri borsa
    arayuzunuzdeki islem gecmisiyle MUTLAKA karsilastirin).
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
    return {"status": durum, "executedQty": miktar, "executedPrice": fiyat}


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
    price: float
    has_position: bool = False
    buy_qty: float = 0.0
    buy_price: float = 0.0
    en_yuksek_fiyat: float = 0.0
    kismi_kar_alindi: bool = False  # v13: kademeli kar alma bu seviyede bir kez yapildi mi
    borsa_stop_emir_id: Optional[str] = None  # v18: borsada bekleyen koruyucu stop emri
    borsa_stop_fiyati: float = 0.0
    borsa_stop_miktari: float = 0.0
    borsa_stop_son_islem: float = 0.0   # kaydedilmez: son kurma/iptal zamani (monotonic)
    borsa_stop_son_sorgu: float = 0.0   # kaydedilmez: son durum sorgusu (monotonic)
    borsa_stop_hata_sayisi: int = 0     # kaydedilmez
    risk_birimi: float = 0.0            # v19: 1R (giris - ilk stop), fiyat cinsinden
    ilk_stop: float = 0.0
    atr_giris: float = 0.0              # giristeki ATR(1s) - takip eden stop mesafesi
    tp1_alindi: bool = False
    tp2_alindi: bool = False
    trend_stop: float = 0.0             # v21: trend pozisyonunun guncel stop'u (0 = trend pozisyonu degil)


def r_stop_hesapla(level: GridLevel) -> tuple:
    """v19: R tabanli stop (asla asagi inmez): ilk stop -> hedef 1 sonrasi
    basa-bas -> takip eden stop (zirve - k x ATR) -> hedef 2 sonrasi +1R kilidi.
    Donus: (stop_seviyesi, etiket). v20: gecmis veri testi de bunu kullanir."""
    b, r = level.buy_price, level.risk_birimi
    stop, etiket = (level.ilk_stop or b - r), "STOP-LOSS"
    if level.tp1_alindi:
        basa_bas = b * (1 + 3 * (KOMISYON_PCT + SLIPAJ_MAKS_PCT))
        if basa_bas > stop:
            stop, etiket = basa_bas, "BREAKEVEN-STOP"
        katsayi = (CHANDELIER_SIKI_ATR_KATSAYI if level.en_yuksek_fiyat >= b + CHANDELIER_SIKI_R * r
                   else CHANDELIER_ATR_KATSAYI)
        takip = level.en_yuksek_fiyat - katsayi * (level.atr_giris or r / R_STOP_ATR_KATSAYI)
        if takip > stop:
            stop, etiket = takip, "TRAILING-STOP"
    if level.tp2_alindi:
        kilit = b + TP2_SONRASI_KILIT_R * r
        if kilit > stop:
            stop, etiket = kilit, "KAR-KILIDI-STOP"
    return stop, etiket


def giris_stop_pct(fiyat: float, derin: Optional[dict], giris_bilgisi: Optional[dict]) -> float:
    """v19/v20: giriste stop mesafesi (oran): analizdeki destek/ATR stop'u, yoksa
    1.5 x ATR tahmini, o da yoksa STOP_LOSS_PCT; %2-6 araligina sikistirilir."""
    derin = derin or {}
    if derin.get("stop_fiyati") and fiyat > 0:
        stop_pct = (fiyat - derin["stop_fiyati"]) / fiyat
    else:
        atr_tahmini = (giris_bilgisi or {}).get("atr14")
        stop_pct = R_STOP_ATR_KATSAYI * atr_tahmini / fiyat if (atr_tahmini and fiyat > 0) else STOP_LOSS_PCT
    return min(max(stop_pct, R_STOP_MIN_PCT), R_STOP_MAKS_PCT)


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
    if tag in ("KAR-AL", "TRAILING-STOP", "KAR-KILIDI-STOP"):
        return COOLDOWN_KAR_DAKIKA
    if tag in ("ZAMAN-ASIMI", "BREAKEVEN-STOP"):
        # v19: basa-bas stopu artik hedef 1 alindiktan SONRA devreye girer
        # (islem toplamda karli) - zarar grubunda degil, notr grupta.
        return COOLDOWN_ZAMAN_ASIMI_DAKIKA
    if tag in ("STOP-LOSS", "ACIL-TASFIYE", "BORSA-STOP", "MANUEL-KAPANIS"):
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


def dinamik_pozisyon_planla(kasa_bakiye: float, toplam_kasa: float, btc_degisim: Optional[float],
                            btc_rejimi: Optional[str] = None):
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

    if btc_rejimi == "RISKLI":
        return 0, 0.0, sniper_modu_aktif  # v19: detayli BTC analizi riskli -> yeni alim yok

    if btc_rejimi in ("GUCLU", "NOTR", "ZAYIF"):
        # v19: detayli BTC rejimi varsa 24s degisim yerine o kullanilir
        izin_verilen = temel_kapasite if btc_rejimi == "GUCLU" else max(1, temel_kapasite // 2)
    elif btc_degisim is None:
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
    en_iyi_anahtar = None
    for sym, bilgi in bilgi_map.items():
        bot = pozisyonlar.get(sym)
        if bot is not None and (bot.has_open_position or bot.cooldown_aktif_mi() or bot.bekliyor):
            continue
        if _risk.coin_engel_bitisi(sym) is not None:
            continue  # v20: stop/tekrarlayan zarar sonrasi bu coine bir sure girilmez
        derin = bilgi.get("derin")
        if derin is not None:
            # v19: detayli analizden GECMEYEN coine asla girilmez; gecenler puana gore
            if not derin.get("gecti"):
                continue
            anahtar = (1, derin.get("skor", 0.0))
        else:
            adx14 = bilgi.get("adx14")
            rsi14 = bilgi.get("rsi14")
            if adx14 is None or rsi14 is None or adx14 < ADX_MIN_ESIK:
                continue
            if not (RSI_KALITE_ALT_ESIK <= rsi14 <= RSI_KALITE_UST_ESIK):
                continue
            anahtar = (0, adx14)
        if en_iyi_anahtar is None or anahtar > en_iyi_anahtar:
            en_iyi_anahtar = anahtar
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
    giris_bilgi: dict = field(default_factory=dict)  # v20: giris zamani/miktari/analiz - islem gunlugu icin
    acik_islem_pnl: float = 0.0                       # v20: acik islemin kismi satislardan gelen net K/Z'si

    def __post_init__(self):
        self.cash_try = self.starting_try

    @property
    def has_open_position(self) -> bool:
        return self.coin_qty > 1e-12

    def guncel_fiyat(self) -> float:
        """Bilinen son fiyat; hic fiyat alinamamissa (yeniden baslatma sonrasi
        ilk tick veya fiyat sorgusu hatasi) acik pozisyonun giris fiyati.
        0 dondurmek pozisyonu sifir degerde gosterir ve sahte bir ACIL FREN
        tasfiyesini tetikleyebilir."""
        fiyat = self.last_real_price or self.last_sim_price
        if fiyat:
            return fiyat
        acik_seviye = next((lvl for lvl in self.grid if lvl.has_position), None)
        return acik_seviye.buy_price if acik_seviye else 0.0

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

        if side == "SELL":
            # Borsa ALIM komisyonunu alinan coinden keser (BNB ile odenmiyorsa);
            # ic kayit komisyon oncesi miktari tuttugu icin tam miktarla satis
            # "yetersiz bakiye" ile reddedilir ve stop-loss mutabakata kadar
            # (6 saate kadar) hic calismaz. Satisi gercek serbest bakiyeyle sinirla.
            try:
                serbest = binance_hesap_bakiyeleri().get(self.coin_name, {}).get("free")
                if serbest is not None and serbest < qty:
                    print(f"{YELLOW}  CANLI SATIS: {self.symbol} miktari borsadaki serbest bakiyeye "
                          f"cekildi ({qty:.8f} -> {serbest:.8f}).{RESET}")
                    qty = serbest
            except Exception as e:
                print(f"{YELLOW}  CANLI SATIS: {self.coin_name} serbest bakiyesi okunamadi ({e}) - "
                      f"ic kayittaki miktarla deneniyor.{RESET}")

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
            # Istisna metni '<urlopen error ...>' gibi '<' icerebilir; kacirilmazsa
            # Telegram HTML ayristirmasi 400 dondurur ve bu kritik uyari hic gitmez.
            send_telegram(f"\u26a0\ufe0f <b>CANLI EMIR BASARISIZ</b>\n{self.symbol} {side} - "
                          f"{html.escape(str(e))}")
            return None

    def _r_stop_hesapla(self, level: "GridLevel") -> tuple:
        return r_stop_hesapla(level)

    def _ratchet_stop_hesapla(self, level: "GridLevel") -> tuple:
        """v14: UC KADEMELI RATCHET STOP hesabini SALT-OKUNUR olarak
        dondurur (islem yapmaz) - hem stop_loss_kontrol() icinde HEM DE
        raporlama/giris karti icin (guncel_stop_seviyesi gostermek icin)
        tekrar kullanilir. Donus: (stop_seviyesi, etiket).
        v19: R bilgisi olan (canli) pozisyonlarda _r_stop_hesapla kullanilir.
        v21: trend pozisyonunda gunluk guncellenen trend_stop."""
        if level.trend_stop > 0:
            return level.trend_stop, ("TRAILING-STOP" if level.trend_stop > level.buy_price else "STOP-LOSS")
        if level.risk_birimi > 0:
            return self._r_stop_hesapla(level)
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
            if level.has_position and level.trend_stop > 0:
                stop, etiket = self._ratchet_stop_hesapla(level)
                return "TREND", stop, etiket  # v21: hedef yok, takip eden stop
            if level.has_position and level.risk_birimi > 0:
                stop, etiket = self._r_stop_hesapla(level)
                if not level.tp1_alindi:
                    return level.buy_price + TP1_R * level.risk_birimi, stop, etiket
                if not level.tp2_alindi:
                    return level.buy_price + TP2_R * level.risk_birimi, stop, etiket
                return "TRAILING", stop, etiket
            if level.has_position:
                stop, etiket = self._ratchet_stop_hesapla(level)
                if etiket == "TRAILING-STOP":
                    return "TRAILING", stop, etiket
                hedef = self._sonraki_kar_hedefi(i)
                return hedef, stop, etiket
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

    def borsa_stopunu_kur(self, level: "GridLevel", zorla: bool = False,
                          durum_kaydet: Optional[object] = None) -> bool:
        """Seviye icin borsada STOP_LOSS_LIMIT satis emri kurar. Basarisizlikta bot
        kendi stop'uyla korumaya devam eder; BORSA_STOP_HATA_BEKLEME_SANIYE sonra
        tekrar denenir."""
        if not (CANLI_MOD and BORSA_STOP_AKTIF) or not level.has_position or level.borsa_stop_emir_id:
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
        print(f"{GREEN}  BORSA STOP kuruldu ({self.symbol}): {_sayi_metni(miktar)} adet, tetik "
              f"{format_fiyat(tetik)} / limit {format_fiyat(limit)} TRY (emir {emir_id}){RESET}")
        if ilk_kurulum:
            send_telegram(f"\U0001F6E1 <b>{self.symbol} borsa stop emri kuruldu</b>\n"
                          f"Tetik: {format_fiyat(tetik)} TRY - bot kapali olsa bile borsa bu fiyatta satar.")
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
                if BORSA_STOP_AKTIF and yeni_kur and not yeni_alim:  # alinan coin hesaba gecsin
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
            if not BORSA_STOP_AKTIF:
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
                        miktar: Optional[float] = None,
                        borsada_gerceklesen: Optional[tuple] = None) -> bool:
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

        v18: borsada_gerceklesen=(miktar, fiyat) verilirse satis borsada ZATEN
        olmustur (koruyucu stop emri doldu): emir gonderilmez, sadece muhasebe yapilir.
        Seviyenin borsada bekleyen stop emri varsa satistan ONCE iptal edilir
        (coinler o emirde kilitliyken satis emri reddedilir).
        """
        tam_kapanis_niyeti = miktar is None
        onceki_level_qty = level.buy_qty
        sell_qty = level.buy_qty if miktar is None else miktar
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
                dogrulanmis_qty = self._canli_emir_dogrula_ve_gonder("SELL", sell_qty, exec_price)
                if dogrulanmis_qty is None:
                    return False  # gercek emir gitmedi - ic durum degismez, sonraki tick'te tekrar denenir
                sell_qty = dogrulanmis_qty

        # CANLI modda tam kapanista satilan miktar LOT_SIZE yuvarlamasi /
        # komisyon kesintisi yuzunden ic kayittan biraz az olabilir. Kalan
        # satilamaz "toz" pozisyonu acik tutarsa bot her tick 0 miktarla satmaya
        # calisir ve slot bosalmaz; tozun maliyeti zarar olarak yazilip seviye kapatilir.
        maliyet_qty = onceki_level_qty if tam_kapanis_niyeti else sell_qty
        brut_proceeds = sell_qty * exec_price
        komisyon = brut_proceeds * KOMISYON_PCT
        net_proceeds = brut_proceeds - komisyon
        cost = maliyet_qty * level.buy_price
        islem_net_pnl = net_proceeds - cost  # v17 MODUL 4: SADECE bu islemden elde edilen net K/Z
        islem_net_pnl_pct = (islem_net_pnl / cost * 100) if cost else 0.0

        self.cash_try += net_proceeds
        self.coin_qty = max(0.0, self.coin_qty - maliyet_qty)
        self.toplam_komisyon += komisyon
        self.realized_pnl += net_proceeds - cost
        level.buy_qty = 0.0 if tam_kapanis_niyeti else max(0.0, level.buy_qty - sell_qty)

        tam_kapanis = tam_kapanis_niyeti or level.buy_qty <= 1e-9
        if tam_kapanis:
            level.has_position = False
            level.buy_qty = 0.0
            level.borsa_stop_emir_id = None  # v18
            level.borsa_stop_fiyati = 0.0
            level.borsa_stop_miktari = 0.0
            level.borsa_stop_hata_sayisi = 0
            if not any(lvl.has_position for lvl in self.grid):
                self.coin_qty = 0.0  # kayan nokta artigi has_open_position'i True birakmasin
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
        if kasa is not None:
            self.acik_islem_pnl += islem_net_pnl  # v20
            if tam_kapanis:
                self._islem_kapanisini_isle(level, exec_price, tag)
        if durum_kaydet is not None:
            durum_kaydet()
        return True

    def _islem_kapanisini_isle(self, level: "GridLevel", cikis_fiyati: float, tag: str) -> None:
        """v20: tamamen kapanan islemi gunluge yazar ve risk korumasina bildirir
        (coin engeli, art arda zarar molasi)."""
        gb = self.giris_bilgi or {}
        simdi = datetime.now()
        toplam = self.acik_islem_pnl - (gb.get("komisyon") or 0.0)  # alim komisyonu da islemin maliyeti
        # v19'dan devralinan pozisyonda giris bilgisi yok: alim tutari starting_try'dan bulunur
        tutar = gb.get("tutar") or self.starting_try or 0.0
        miktar = gb.get("miktar") or (tutar / level.buy_price if level.buy_price else 0.0)
        risk_try = miktar * level.risk_birimi
        kayit = islem_kaydi_olustur(
            self.symbol, _aktif_calisma_modu(), _tarih_oku(gb.get("zaman")), simdi, level.buy_price, cikis_fiyati,
            tutar, toplam, risk_try, level.risk_birimi / level.buy_price if level.buy_price else 0.0, tag,
            level.tp1_alindi, level.tp2_alindi, gb.get("analiz"))
        islem_gunlugune_yaz(kayit)
        if risk_try > 0:
            print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} islem kapandi: {toplam:+,.2f} TRY "
                  f"({kayit['r_sonucu']:+.2f}R)")
        mesajlar = [] if TREND_MODU else _risk.islem_kapandi(self.symbol, toplam, tag, simdi)
        for mesaj in mesajlar:
            print(f"[{ts()}] {YELLOW}RISK KORUMASI: {mesaj}{RESET}")
            if self.bildirim_aktif:
                send_telegram(f"\U0001F6E1 <b>Risk korumasi</b>\n{html.escape(mesaj)}")
        self.acik_islem_pnl = 0.0
        self.giris_bilgi = {}

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

            if kasa is not None and level.trend_stop > 0:
                # v21: trend pozisyonu - kismi kar alma / zaman asimi yok, sadece gunluk yukselen stop
                stop, etiket = self._ratchet_stop_hesapla(level)
                if price <= stop:
                    self._satisi_uygula(level, price, etiket, sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)
                continue

            if kasa is not None and level.risk_birimi > 0:
                self._r_cikis_yonetimi(level, price, sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)
                continue

            # v13: KADEMELI KAR ALMA - pozisyon KISMI_KAR_AL_PCT kara ulastiginda
            # (stop henuz tetiklenmeden) miktarin bir kismi ANINDA satilarak kar
            # erken realize edilir; kalan miktar mevcut breakeven/trailing
            # korumasiyla yoluna devam eder. Sadece CANLI/v9+ modda (kasa
            # verildiginde) aktiftir - backtest/legacy etkilenmez.
            if (kasa is not None and not level.kismi_kar_alindi and KISMI_KAR_AL_ORANI > 0
                    and price >= level.buy_price * (1 + KISMI_KAR_AL_PCT)):
                kismi_qty = level.buy_qty * KISMI_KAR_AL_ORANI
                if kismi_qty > 0:
                    basarili = self._satisi_uygula(level, price, "KISMI-KAR-AL", sim, kasa,
                                                   acik_pozisyon_sayaci, rapor, durum_kaydet, miktar=kismi_qty)
                    if not basarili:
                        # Kismi satis reddedildiyse (orn. yarim pozisyon minNotional
                        # altinda) her tick tekrar denenmesin; tam cikislar etkilenmez.
                        level.kismi_kar_alindi = True
                        print(f"[{ts()}] {YELLOW}{self.symbol} kismi kar alma gerceklestirilemedi - "
                              f"atlandi, pozisyon tam cikis kurallariyla yonetilmeye devam ediyor.{RESET}")

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
                        continue
                    # Zaman asimi satisi basarisizsa asagidaki stop-loss kontrolu
                    # yine calismali; aksi halde stop her tick atlanir.

            # v12/v14: UC KADEMELI RATCHET STOP SISTEMI - artik ortak
            # _ratchet_stop_hesapla() metodundan hesaplanir (raporlama/
            # giris karti ile paylasilan TEK bir kaynak).
            stop_seviyesi, etiket = self._ratchet_stop_hesapla(level)

            if price <= stop_seviyesi:
                self._satisi_uygula(level, price, etiket, sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)

    def _r_cikis_yonetimi(self, level: "GridLevel", price: float, sim: bool, kasa: MerkeziKasa,
                          acik_pozisyon_sayaci: Optional[list], rapor: Optional["RaporlamaDurumu"],
                          durum_kaydet: Optional[object]) -> None:
        """v19 KAR ALMA / ZARAR KESME:
          1) +1R: pozisyonun 1/3'u satilir (KAR-AL-1), stop basa-basa cekilir
          2) +2R: kalanin yarisi satilir (KAR-AL-2), stop +1R'ye kilitlenir
          3) Kalan kisim zirve - 2.5 x ATR takip eden stopla yonetilir (ust sinir yok)
          4) Hedef 1'e hic ulasamayan pozisyon 18 saatte kar < %1 ise kapatilir
          5) Fiyat guncel stop'un altina inerse tamami satilir."""
        b, r = level.buy_price, level.risk_birimi
        if not level.tp1_alindi and price >= b + TP1_R * r:
            if not self._satisi_uygula(level, price, "KAR-AL-1", sim, kasa, acik_pozisyon_sayaci, rapor,
                                       durum_kaydet, miktar=level.buy_qty * TP1_ORAN):
                print(f"[{ts()}] {YELLOW}{self.symbol} hedef 1 satisi gerceklesmedi (orn. tutar cok kucuk) - "
                      f"atlandi; stop yine de basa-basa cekildi.{RESET}")
            level.tp1_alindi = True
            if not level.has_position:
                return
        if level.tp1_alindi and not level.tp2_alindi and price >= b + TP2_R * r:
            if not self._satisi_uygula(level, price, "KAR-AL-2", sim, kasa, acik_pozisyon_sayaci, rapor,
                                       durum_kaydet, miktar=level.buy_qty * TP2_ORAN):
                print(f"[{ts()}] {YELLOW}{self.symbol} hedef 2 satisi gerceklesmedi - atlandi; stop +1R'ye "
                      f"kilitlendi.{RESET}")
            level.tp2_alindi = True
            if not level.has_position:
                return
        if not level.tp1_alindi and self.alis_zamani is not None:
            yas_saat = (datetime.now() - self.alis_zamani).total_seconds() / 3600
            kar_pct = (price - b) / b if b else 0.0
            if yas_saat >= MAKS_POZISYON_OMRU_SAAT and kar_pct < ZAMAN_ASIMI_KAR_ESIGI_PCT:
                if self._satisi_uygula(level, price, "ZAMAN-ASIMI", sim, kasa, acik_pozisyon_sayaci, rapor,
                                       durum_kaydet):
                    print(f"[{ts()}] {YELLOW}\u23F3 {self.symbol} Zaman Asimi Cikisi: "
                          f"{MAKS_POZISYON_OMRU_SAAT:.0f} saatte hedef 1'e ulasamadi, sermaye serbest birakildi.{RESET}")
                    send_telegram(f"\u23F3 <b>{self.symbol} Zaman Asimi Cikisi</b>\n"
                                  f"{MAKS_POZISYON_OMRU_SAAT:.0f} saatte hedef 1'e ulasamadigi icin kapatildi.")
                    return
        stop, etiket = self._r_stop_hesapla(level)
        if price <= stop:
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
                     sniper_modu: bool = False,
                     portfoy_degeri: Optional[float] = None):
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

                # v19: analizden sonra fiyat cok kactiysa veya stop'a dayandiysa girme
                derin = (giris_bilgisi or {}).get("derin") or {}
                if derin.get("gecti") and derin.get("fiyat"):
                    analiz_riski = derin["fiyat"] - derin["stop_fiyati"]
                    erteleme = None
                    if price > derin["fiyat"] + KOVALAMA_MAKS_R * analiz_riski:
                        erteleme = "fiyat analizden sonra hizla yukseldi (kovalanmaz)"
                    elif price - derin["stop_fiyati"] < price * R_STOP_MIN_PCT:
                        erteleme = "fiyat analizdeki stop seviyesine cok yaklasti"
                    if erteleme:
                        if getattr(self, "_son_erteleme", None) != (derin["fiyat"], erteleme):
                            self._son_erteleme = (derin["fiyat"], erteleme)
                            print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} {YELLOW}ALIM ERTELENDI - "
                                  f"{erteleme}; bir sonraki analiz beklenecek.{RESET}")
                        continue

                # v10 BOLUM 3: ALIM'dan hemen once tahta derinligi/spread kontrolu
                spread_pct, en_iyi_bid, en_iyi_ask = orderbook_spread_kontrol(self.symbol)
                if spread_pct is not None and spread_pct > MAX_SPREAD_PCT:
                    print(f"[{ts()}] {MAGENTA}{self.symbol:<9}{RESET} {YELLOW}ALIM IPTAL - "
                          f"spread cok genis (%{spread_pct:.2f} > %{MAX_SPREAD_PCT}), "
                          f"likidite sig kabul edildi (bid={en_iyi_bid}, ask={en_iyi_ask}).{RESET}")
                    continue

                # v20: pozisyon, stop olursa kayip portfoyun RISK_PCT'si olacak buyuklukte
                portfoy = portfoy_degeri if portfoy_degeri is not None else kasa.bakiye
                # (giris fiyati kayma ile biraz yukarida olabilir; stop mesafesi en kotu kaymayla hesaplanir)
                yatirim_tutari = risk_bazli_tutar(portfoy,
                                                  giris_stop_pct(price * (1 + SLIPAJ_MAKS_PCT), derin, giris_bilgisi),
                                                  min(hedef_pozisyon_tutari, kasa.bakiye / (1 + KOMISYON_PCT)))
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
                # v19: R (risk birimi) - analizdeki destek/ATR stop'u, yoksa ATR tahmini
                stop_pct = giris_stop_pct(exec_price, derin, giris_bilgisi)
                level.risk_birimi = exec_price * stop_pct
                level.ilk_stop = exec_price - level.risk_birimi
                level.atr_giris = (derin.get("atr_1h") or (giris_bilgisi or {}).get("atr14")
                                   or level.risk_birimi / R_STOP_ATR_KATSAYI)
                level.tp1_alindi = level.tp2_alindi = level.kismi_kar_alindi = False
                self.alis_zamani = datetime.now()  # v16: zaman bazli bayat pozisyon cikisi icin
                self.giris_bilgi = {"zaman": self.alis_zamani.isoformat(), "miktar": buy_qty,
                                    "tutar": yatirim_tutari, "komisyon": komisyon,
                                    "analiz": giris_analiz_ozeti(derin)}  # v20
                self.acik_islem_pnl = 0.0
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
                # v19: hedef 1 (1/3), hedef 2 (1/3) ve kalan 1/3 icin temkinli +1R
                # varsayimiyla beklenen net kar; zarar ilk stop'tan.
                hedef1_fiyat = exec_price + TP1_R * level.risk_birimi
                hedef_fiyat = exec_price + TP2_R * level.risk_birimi
                stop_fiyat = level.ilk_stop
                satis_brut_tahmini = buy_qty / 3 * (hedef1_fiyat + hedef_fiyat
                                                    + exec_price + TP2_SONRASI_KILIT_R * level.risk_birimi)
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

                gb = dict(giris_bilgisi or {})
                gb.update({k: derin[k] for k in ("ema50", "rsi14", "adx14") if derin.get(k) is not None})
                analiz_ozeti = (f"puan {derin['skor']:.0f}/100 | 4s {derin.get('h4_trend')} | BTC {derin.get('btc_rejim')}"
                                if derin.get("gecti") else None)
                if RISK_PCT > 0 and portfoy > 0:  # v20: stop olursa portfoyun yuzde kaci gider
                    analiz_ozeti = ((analiz_ozeti + " | ") if analiz_ozeti else "") + \
                        f"risk %{yatirim_tutari * stop_pct / portfoy * 100:.1f}"
                kart = giris_karti_olustur(
                    self.symbol, self.coin_name, gb.get("ema50"), gb.get("rsi14"), gb.get("adx14"),
                    buy_qty, exec_price, yatirim_tutari, hedef_fiyat, stop_fiyat,
                    beklenen_net_kar, beklenen_net_kayip, calisma_modu_etiketi,
                    hedef1_fiyat=hedef1_fiyat, analiz_ozeti=analiz_ozeti,
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
                if level.risk_birimi > 0:
                    continue  # v19: R tabanli pozisyonlarin cikislari stop_loss_kontrol'de
                hedef_fiyat_bu_seviye = self._sonraki_kar_hedefi(i)
                if price < hedef_fiyat_bu_seviye:
                    continue
                self._satisi_uygula(level, price, "KAR-AL", sim, kasa, acik_pozisyon_sayaci, rapor, durum_kaydet)

    def trend_girisi(self, fiyat: float, tutar: float, stop_pct: float, kasa: MerkeziKasa,
                     acik_pozisyon_sayaci: list, rapor: Optional["RaporlamaDurumu"], durum_kaydet,
                     portfoy: float, btc_yukari: Optional[bool]) -> bool:
        """v21: trend stratejisi alimi. Stop giristen stop_pct asagida; gunluk kontrolde zirve - 3 x ATR'ye
        kadar yukselir (asla inmez). Kismi kar alma yok. CANLI modda gercek emir; reddedilirse False."""
        exec_price = self._slipajli_fiyat(fiyat, "ALIM")
        buy_qty = tutar / exec_price
        if CANLI_MOD:
            dogrulanmis_qty = self._canli_emir_dogrula_ve_gonder("BUY", buy_qty, exec_price)
            if dogrulanmis_qty is None:
                return False
            buy_qty = dogrulanmis_qty
            tutar = buy_qty * exec_price
        komisyon = tutar * KOMISYON_PCT
        kasa.harca(tutar, komisyon)
        self.starting_try = tutar
        self.cash_try = -komisyon
        self.coin_qty += buy_qty
        self.toplam_komisyon += komisyon
        stop = exec_price * (1 - stop_pct)
        self.grid = [GridLevel(price=exec_price, has_position=True, buy_qty=buy_qty, buy_price=exec_price,
                               en_yuksek_fiyat=exec_price, risk_birimi=exec_price - stop, ilk_stop=stop,
                               atr_giris=exec_price * stop_pct / TREND_ILK_STOP_ATR, trend_stop=stop)]
        self.initialized = True
        self.bekliyor = False
        self.alis_zamani = datetime.now()
        self.giris_bilgi = {"zaman": self.alis_zamani.isoformat(), "miktar": buy_qty, "tutar": tutar,
                            "komisyon": komisyon,
                            "analiz": {"btc_rejimi": ("YUKARI" if btc_yukari else "BILINMIYOR" if btc_yukari is None
                                                      else "ASAGI")}}
        self.acik_islem_pnl = 0.0
        acik_pozisyon_sayaci[0] += 1
        if rapor is not None:
            rapor.islem_kaydet(self.symbol, "ALIM", komisyon, None)
        self.record("ALIM", exec_price, buy_qty, tutar)
        print_trade_line(self.symbol, "ALIM", exec_price, buy_qty, tutar, kasa.bakiye, self.coin_name,
                         False, komisyon=komisyon, telegram_bildir=False)
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
    """v19: hesap adx_di_hesapla()'da; burada sadece ADX dondurulur."""
    return adx_di_hesapla(highs, lows, closes, periyot)[0]


def adx_di_hesapla(highs: list, lows: list, closes: list, periyot: int = 14) -> tuple:
    """
    v19: (ADX, +DI, -DI). +DI > -DI yukari yonlu, tersi asagi yonlu trend.
    v13: ADX (Average Directional Index) - Wilder yontemiyle. Trend
    YONUNU degil GUCUNU olcer; ADX<20 tipik olarak yatay/whipsaw piyasa,
    ADX>25 belirgin trend olarak kabul edilir. RSI/EMA'nin sahte
    kirilimlara (whipsaw) karsi zayif kaldigi durumlar icin ek teyit
    katmanidir.
    """
    n = len(closes)
    if n < periyot * 2 + 1:
        return None, None, None

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
        return None, None, None

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
        return None, None, None

    adx = sum(dx_list[:periyot]) / periyot
    for i in range(periyot, len(dx_list)):
        adx = (adx * (periyot - 1) + dx_list[i]) / periyot

    plus_di = (smoothed_plus_dm / smoothed_tr * 100) if smoothed_tr else 0.0
    minus_di = (smoothed_minus_dm / smoothed_tr * 100) if smoothed_tr else 0.0
    return adx, plus_di, minus_di


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


# ==========================================================================
# v19 BOLUM 1: COK ZAMAN DILIMLI PIYASA VERISI VE GOSTERGE KUTUPHANESI
# ==========================================================================
# Bot bir coine girmeden once onu gunluk / 4 saatlik / 1 saatlik / 15 dakikalik
# mumlarla (her birinde ~200 KAPANMIS mum) inceler. Ayni veri tekrar tekrar
# cekilmesin diye zaman dilimine gore onbellege alinir.
MUM_SAYISI = 200
MUM_ONBELLEK_SANIYE = {"15m": 120, "1h": 300, "4h": 900, "1d": 3600}
_mum_onbellek: dict = {}
_usd_paritesi_yok: set = set()


def mumlari_getir(symbol: str, interval: str, limit: int = MUM_SAYISI) -> Optional[dict]:
    """KAPANMIS mumlari dondurur; son (henuz kapanmamis) mum gostergelere
    katilmaz, sadece 'son_fiyat' icin kullanilir. Anahtarlar: acilis, yuksek,
    dusuk, kapanis, hacim, alici_hacim (piyasa emriyle alim hacmi), son_fiyat.
    Veri yoksa None; ag/HTTP hatasi yukari iletilir."""
    anahtar = (symbol, interval, limit)
    simdi = time.time()
    kayit = _mum_onbellek.get(anahtar)
    if kayit is not None and simdi - kayit[0] < MUM_ONBELLEK_SANIYE.get(interval, 300):
        return kayit[1]
    url = KLINES_URL_TEMPLATE.format(symbol=symbol, interval=interval, limit=limit + 1)
    req = urllib.request.Request(url, headers={"User-Agent": "project-aurelius-bot"})
    data = http_istek_yap(req, timeout=20)
    sonuc = None
    if isinstance(data, list) and len(data) >= 2:
        kapali = data[:-1]

        def sutun(i):
            return [float(m[i]) for m in kapali]

        sonuc = {"acilis": sutun(1), "yuksek": sutun(2), "dusuk": sutun(3), "kapanis": sutun(4),
                 "hacim": sutun(5), "alici_hacim": [float(m[9]) if len(m) > 9 else 0.0 for m in kapali],
                 "son_fiyat": float(data[-1][4])}
    _mum_onbellek[anahtar] = (simdi, sonuc)
    return sonuc


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


def egim_pct(seri: list, geri: int = 5) -> Optional[float]:
    """Serinin son 'geri' adimdaki yuzde degisimi (trendin egimi)."""
    if len(seri) <= geri or not seri[-1 - geri]:
        return None
    return (seri[-1] / seri[-1 - geri] - 1) * 100


def macd_histogram(kapanislar: list) -> Optional[tuple]:
    """MACD(12,26,9) histogrami: (son, bir onceki). Pozitif ve buyuyorsa ivme yukari."""
    e12, e26 = ema_serisi(kapanislar, 12), ema_serisi(kapanislar, 26)
    if not e26:
        return None
    kayma = len(e12) - len(e26)
    macd = [e12[i + kayma] - e26[i] for i in range(len(e26))]
    sinyal = ema_serisi(macd, 9)
    if len(sinyal) < 2:
        return None
    kayma2 = len(macd) - len(sinyal)
    histogram = [macd[i + kayma2] - sinyal[i] for i in range(len(sinyal))]
    return histogram[-1], histogram[-2]


def goreceli_hacim(hacimler: list, pencere: int = 20) -> Optional[float]:
    """Son kapanmis mumun hacmi / onceki 'pencere' mumun ortalama hacmi."""
    if len(hacimler) < pencere + 1:
        return None
    ortalama = sum(hacimler[-pencere - 1:-1]) / pencere
    return hacimler[-1] / ortalama if ortalama > 0 else None


def obv_egimi(kapanislar: list, hacimler: list, pencere: int = 20) -> Optional[float]:
    """Son 'pencere' mumdaki net OBV degisimi, ortalama hacim cinsinden
    (pozitif: yukselen mumlarda daha cok hacim = alim baskisi)."""
    if len(kapanislar) < pencere + 1:
        return None
    obv = 0.0
    for i in range(len(kapanislar) - pencere, len(kapanislar)):
        if kapanislar[i] > kapanislar[i - 1]:
            obv += hacimler[i]
        elif kapanislar[i] < kapanislar[i - 1]:
            obv -= hacimler[i]
    ortalama = sum(hacimler[-pencere:]) / pencere
    return obv / ortalama if ortalama > 0 else None


def alici_orani(hacimler: list, alici_hacimler: list, pencere: int = 6) -> Optional[float]:
    """Son 'pencere' mumda piyasa emriyle ALIM yapanlarin hacim payi (0.5 ustu alici baskin)."""
    toplam = sum(hacimler[-pencere:])
    return sum(alici_hacimler[-pencere:]) / toplam if toplam > 0 else None


def salinim_seviyeleri(yuksek: list, dusuk: list, pencere: int = 3, son: int = 120) -> tuple:
    """Son 'son' mumdaki salinim (pivot) tepe ve dipleri: (direncler, destekler)."""
    n = len(yuksek)
    tepeler, dipler = [], []
    for i in range(max(pencere, n - son), n - pencere):
        if yuksek[i] == max(yuksek[i - pencere:i + pencere + 1]):
            tepeler.append(yuksek[i])
        if dusuk[i] == min(dusuk[i - pencere:i + pencere + 1]):
            dipler.append(dusuk[i])
    return tepeler, dipler


def getiri_korelasyonu(a: list, b: list, pencere: int = 72) -> Optional[float]:
    """Iki fiyat serisinin son 'pencere' mumluk getiri korelasyonu (-1..1)."""
    if min(len(a), len(b)) < pencere + 1:
        return None
    a, b = a[-pencere - 1:], b[-pencere - 1:]
    ra = [a[i] / a[i - 1] - 1 for i in range(1, len(a)) if a[i - 1]]
    rb = [b[i] / b[i - 1] - 1 for i in range(1, len(b)) if b[i - 1]]
    if len(ra) != len(rb) or len(ra) < 10:
        return None
    ma, mb = sum(ra) / len(ra), sum(rb) / len(rb)
    kov = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    va, vb = sum((x - ma) ** 2 for x in ra), sum((y - mb) ** 2 for y in rb)
    return kov / (va * vb) ** 0.5 if va > 0 and vb > 0 else None


def _trend_yonu(kapanislar: list, alt_tolerans: float = 0.0) -> str:
    """EMA20/EMA50 ve kapanisa gore trend yonu: YUKARI / ASAGI / YATAY / BILINMIYOR."""
    if len(kapanislar) < 55:
        return "BILINMIYOR"
    e20, e50, kapanis = ema_hesapla(kapanislar, 20), ema_hesapla(kapanislar, 50), kapanislar[-1]
    if e20 > e50 and kapanis > e50:
        return "YUKARI"
    if e20 < e50 and kapanis < e50 * (1 - alt_tolerans):
        return "ASAGI"
    return "YATAY"


# ==========================================================================
# v19 BOLUM 2: BTC PIYASA REJIMI (detayli)
# ==========================================================================
# Altcoinler cogunlukla BTC'yi takip eder. BTC sadece 24 saatlik degisimle
# degil; gunluk ve 4 saatlik trend, trend gucu/yonu, son 4 ve 24 saatteki
# hareket ve oynaklikla degerlendirilir. USDT paritesi tercih edilir (TRY
# paritesi lira kaybini da icerir), yoksa BTCTRY kullanilir.
BTC_ANALIZ_SEMBOLLERI = ("BTCUSDT", "BTCTRY")
BTC_RISK_4S_DUSUS_PCT = -3.0
BTC_RISK_24S_DUSUS_PCT = -5.0
BTC_RISK_ATR_PCT = 2.5
BTC_REJIM_ONBELLEK_SANIYE = 300
_btc_rejim_onbellek: dict = {"zaman": 0.0, "sonuc": None}


def btc_rejim_analizi(zorla: bool = False) -> dict:
    """BTC rejimi: GUCLU (tam kapasite) / NOTR / ZAYIF (yarim kapasite, BTC'ye
    bagli coinlere girilmez) / RISKLI (yeni alim yok) / BILINMIYOR (veri yok)."""
    simdi = time.time()
    if (not zorla and _btc_rejim_onbellek["sonuc"] is not None
            and simdi - _btc_rejim_onbellek["zaman"] < BTC_REJIM_ONBELLEK_SANIYE):
        return _btc_rejim_onbellek["sonuc"]
    sonuc = {"rejim": "BILINMIYOR", "sembol": None, "notlar": [], "kapanis_1h": []}
    for sembol in BTC_ANALIZ_SEMBOLLERI:
        try:
            h1 = mumlari_getir(sembol, "1h")
            h4 = mumlari_getir(sembol, "4h")
            d1 = mumlari_getir(sembol, "1d")
        except Exception as e:
            sonuc["notlar"].append(f"{sembol} verisi alinamadi: {e}")
            continue
        hesap = btc_rejim_hesapla(sembol, h1, h4, d1)
        if hesap is None:
            sonuc["notlar"].append(f"{sembol} icin yeterli mum yok")
            continue
        sonuc.update(hesap)
        break
    _btc_rejim_onbellek.update(zaman=simdi, sonuc=sonuc)
    return sonuc


def _mumlar_yeterli(h1: Optional[dict], h4: Optional[dict]) -> bool:
    return bool(h1 and h4 and len(h1["kapanis"]) >= 60 and len(h4["kapanis"]) >= 60)


def btc_rejim_hesapla(sembol: str, h1: Optional[dict], h4: Optional[dict], d1: Optional[dict]) -> Optional[dict]:
    """v20: BTC rejimini verilen mumlardan hesaplar (canli bot ve gecmis veri testi
    ayni kurali kullanir). Veri yetersizse None."""
    if not _mumlar_yeterli(h1, h4):
        return None
    k1 = h1["kapanis"]
    fiyat = h1["son_fiyat"]
    degisim_4s = (fiyat / k1[-4] - 1) * 100
    degisim_24s = (fiyat / k1[-24] - 1) * 100
    atr1 = atr_hesapla(h1["yuksek"], h1["dusuk"], k1, 14)
    atr_pct = atr1 / fiyat * 100 if atr1 and fiyat else 0.0
    gunluk = _trend_yonu(d1["kapanis"], alt_tolerans=0.03) if d1 else "BILINMIYOR"
    h4_trend = _trend_yonu(h4["kapanis"])
    adx4, pdi4, mdi4 = adx_di_hesapla(h4["yuksek"], h4["dusuk"], h4["kapanis"], 14)
    rsi1 = rsi_hesapla(k1[-60:], 14)

    if (degisim_4s <= BTC_RISK_4S_DUSUS_PCT or degisim_24s <= BTC_RISK_24S_DUSUS_PCT
            or (atr_pct >= BTC_RISK_ATR_PCT and degisim_4s < 0)):
        rejim = "RISKLI"
    elif h4_trend == "ASAGI" or gunluk == "ASAGI":
        rejim = "ZAYIF"
    elif gunluk == "YUKARI" and h4_trend == "YUKARI" and adx4 is not None and adx4 >= 20 and pdi4 > mdi4:
        rejim = "GUCLU"
    else:
        rejim = "NOTR"
    return {
        "rejim": rejim, "sembol": sembol, "fiyat": fiyat, "degisim_4s": degisim_4s,
        "degisim_24s": degisim_24s, "atr_pct_1h": atr_pct, "gunluk_trend": gunluk,
        "h4_trend": h4_trend, "adx_4h": adx4, "pdi_4h": pdi4, "mdi_4h": mdi4, "rsi_1h": rsi1,
        "kapanis_1h": k1,
    }


def btc_raporu_satirlari(btc: dict) -> list:
    if btc.get("rejim") == "BILINMIYOR" or btc.get("sembol") is None:
        return [f"BTC rejimi: BILINMIYOR ({'; '.join(btc.get('notlar', [])) or 'veri yok'})"]
    adx = btc.get("adx_4h")
    yon = "yukari" if (btc.get("pdi_4h") or 0) > (btc.get("mdi_4h") or 0) else "asagi"
    return [
        f"BTC rejimi: {btc['rejim']} ({btc['sembol']})",
        f"  Gunluk trend: {btc['gunluk_trend']} | 4 saatlik trend: {btc['h4_trend']} | "
        f"4s ADX: {adx:.1f} ({yon})" if adx is not None else
        f"  Gunluk trend: {btc['gunluk_trend']} | 4 saatlik trend: {btc['h4_trend']}",
        f"  Son 4 saat: %{btc['degisim_4s']:+.2f} | Son 24 saat: %{btc['degisim_24s']:+.2f} | "
        f"1s oynaklik (ATR): %{btc['atr_pct_1h']:.2f}"
        + (f" | 1s RSI: {btc['rsi_1h']:.1f}" if btc.get("rsi_1h") is not None else ""),
    ]


# ==========================================================================
# v19 BOLUM 3: COIN DETAYLI ANALIZI (zorunlu kurallar + 100 uzerinden puan)
# ==========================================================================
R_STOP_ATR_KATSAYI = 1.5     # stop: giris - 1.5 x ATR(1s) (veya destegin hemen alti)
R_STOP_MIN_PCT = 0.02
R_STOP_MAKS_PCT = 0.06
MIN_ODA_R = 1.0              # en yakin anlamli dirence kadar en az 1R alan (hedef 1 dirence takilmasin)
# v19 KAR ALMA / ZARAR KESME (R = giris ile ilk stop arasi mesafe = 1 birim risk)
TP1_R, TP1_ORAN = 1.0, 1 / 3          # +1R'de pozisyonun 1/3'u satilir, stop basa-basa cekilir
TP2_R, TP2_ORAN = 2.0, 0.5            # +2R'de KALANIN yarisi satilir, stop +1R'ye kilitlenir
TP2_SONRASI_KILIT_R = 1.0
CHANDELIER_ATR_KATSAYI = 2.5          # kalan kisim: zirve - 2.5 x ATR takip eden stop
CHANDELIER_SIKI_ATR_KATSAYI = 1.5     # zirve +4R'yi gecince takip sikilasir
CHANDELIER_SIKI_R = 4.0
KOVALAMA_MAKS_R = 0.5                 # analizden sonra fiyat +0.5R'den fazla kactiysa alim ertelenir
ANALIZ_MIN_SKOR = _ortam_sayisi_oku("AURELIUS_MIN_SKOR", 55.0)
DERIN_ANALIZ_MAKS = 8        # her taramada detayli incelenen en fazla coin sayisi
STABIL_COINLER = ("USDT", "USDC", "FDUSD", "BUSD", "TUSD", "DAI")


def _usd_trendi(symbol: str) -> tuple:
    """Coinin USDT paritesindeki 4 saatlik trend: (yon, usdt_sembolu). TRY
    paritesindeki yukselis lira kaybindan da gelebilir; gercek hareket USDT'de
    gorulur. Parite yoksa ('BILINMIYOR', None)."""
    if not symbol.endswith("TRY"):
        return "BILINMIYOR", None
    taban = symbol[:-3]
    usd = taban + "USDT"
    if taban in STABIL_COINLER or usd in _usd_paritesi_yok:
        return "BILINMIYOR", None
    try:
        veri = mumlari_getir(usd, "4h", 100)
    except urllib.error.HTTPError:
        _usd_paritesi_yok.add(usd)
        return "BILINMIYOR", None
    except Exception:
        return "BILINMIYOR", None
    if not veri:
        return "BILINMIYOR", None
    return _trend_yonu(veri["kapanis"]), usd


def coin_derin_analiz(symbol: str, btc: Optional[dict] = None) -> dict:
    """Coini gunluk/4s/1s/15dk mumlar, hacim, destek/direnc, USDT paritesi ve BTC
    ile birlikte inceler. Donus: gecti (bool), skor (0-100), sebep (elendiyse),
    stop/hedef fiyatlari ve tum gosterge degerleri. Veri eksikse GIRILMEZ."""
    try:
        h1 = mumlari_getir(symbol, "1h")
        h4 = mumlari_getir(symbol, "4h")
        d1 = mumlari_getir(symbol, "1d")
        m15 = mumlari_getir(symbol, "15m", 100)
    except Exception as e:
        return {"symbol": symbol, "gecti": False, "skor": 0.0, "sebep": f"mum verisi alinamadi ({e})", "puanlar": {}}
    if not _mumlar_yeterli(h1, h4):  # USDT paritesi bosuna sorgulanmasin
        return derin_analiz_hesapla(symbol, h1, h4, d1, m15, btc)
    return derin_analiz_hesapla(symbol, h1, h4, d1, m15, btc, _usd_trendi(symbol))


def derin_analiz_hesapla(symbol: str, h1: Optional[dict], h4: Optional[dict], d1: Optional[dict],
                         m15: Optional[dict], btc: Optional[dict] = None,
                         usd: tuple = ("BILINMIYOR", None)) -> dict:
    """v20: coin_derin_analiz'in hesap kismi - verilen mumlarla calisir, ag kullanmaz
    (canli bot ve gecmis veri testi ayni kurallari kullanir). usd: (yon, usdt_sembolu)."""
    a = {"symbol": symbol, "gecti": False, "skor": 0.0, "sebep": "", "puanlar": {}}
    if not _mumlar_yeterli(h1, h4):
        a["sebep"] = "yeterli mum verisi yok (yeni listelenmis olabilir)"
        return a
    btc = btc or {"rejim": "BILINMIYOR"}

    fiyat = h1["son_fiyat"]
    k1, k4 = h1["kapanis"], h4["kapanis"]
    ema20_1, ema50_1 = ema_hesapla(k1, 20), ema_hesapla(k1, 50)
    rsi1, rsi4 = rsi_hesapla(k1[-80:], 14), rsi_hesapla(k4[-80:], 14)
    adx1, pdi1, mdi1 = adx_di_hesapla(h1["yuksek"], h1["dusuk"], k1, 14)
    atr1 = atr_hesapla(h1["yuksek"], h1["dusuk"], k1, 14)
    macd = macd_histogram(k1)
    ema50_4_egim = egim_pct(ema_serisi(k4, 50), 5)
    adx4, pdi4, mdi4 = adx_di_hesapla(h4["yuksek"], h4["dusuk"], k4, 14)
    gunluk = _trend_yonu(d1["kapanis"], alt_tolerans=0.03) if d1 else "BILINMIYOR"
    h4_trend = _trend_yonu(k4)
    gor_hacim = goreceli_hacim(h1["hacim"], 20)
    obv = obv_egimi(k1, h1["hacim"], 20)
    alici = alici_orani(h1["hacim"], h1["alici_hacim"], 6)
    rsi15 = rsi_hesapla(m15["kapanis"][-60:], 14) if m15 and len(m15["kapanis"]) >= 30 else None
    ema20_15 = ema_hesapla(m15["kapanis"], 20) if m15 and len(m15["kapanis"]) >= 30 else None
    atr15 = (atr_hesapla(m15["yuksek"], m15["dusuk"], m15["kapanis"], 14)
             if m15 and len(m15["kapanis"]) >= 30 else None)
    usd_trend, usd_sembol = usd
    korelasyon = getiri_korelasyonu(k1, btc.get("kapanis_1h") or [], 72)

    # Stop: once destegin hemen alti (%2-6 araliginda ise), yoksa 1.5 x ATR
    # Direnc/destek: 4s salinimlari (~20 gun) + 1s'te genis pencereli son 3 gunun salinimlari
    # (kucuk 1s dalgalanmalari direnc sayilmaz).
    tepeler1, dipler1 = salinim_seviyeleri(h1["yuksek"], h1["dusuk"], 5, 72)
    tepeler4, dipler4 = salinim_seviyeleri(h4["yuksek"], h4["dusuk"], 3, 120)
    atr_stop_pct = min(max(R_STOP_ATR_KATSAYI * (atr1 or 0) / fiyat, R_STOP_MIN_PCT), R_STOP_MAKS_PCT)
    stop_fiyati, stop_kaynagi, destek = fiyat * (1 - atr_stop_pct), "ATR", None
    for d in sorted((d for d in dipler1 + dipler4 if d < fiyat), reverse=True):
        aday = d - 0.25 * (atr1 or 0)
        oran = (fiyat - aday) / fiyat
        if R_STOP_MIN_PCT <= oran <= R_STOP_MAKS_PCT:
            stop_fiyati, stop_kaynagi, destek = aday, "DESTEK", d
            break
    risk = fiyat - stop_fiyati
    direncler = [t for t in tepeler1 + tepeler4 if t > fiyat * 1.003]
    direnc = min(direncler) if direncler else None
    oda_r = (direnc - fiyat) / risk if (direnc and risk > 0) else None

    a.update({
        "fiyat": fiyat, "stop_fiyati": stop_fiyati, "stop_pct": risk / fiyat, "stop_kaynagi": stop_kaynagi,
        "destek": destek, "direnc": direnc, "oda_r": oda_r, "atr_1h": atr1,
        "hedef1": fiyat + TP1_R * risk, "hedef2": fiyat + TP2_R * risk,
        "gunluk_trend": gunluk, "h4_trend": h4_trend, "ema50_4h_egim": ema50_4_egim,
        "rsi_1h": rsi1, "rsi_4h": rsi4, "rsi_15m": rsi15, "adx_1h": adx1, "pdi_1h": pdi1, "mdi_1h": mdi1,
        "adx_4h": adx4, "pdi_4h": pdi4, "mdi_4h": mdi4,
        "macd_hist": macd, "goreceli_hacim": gor_hacim, "obv_egimi": obv, "alici_orani": alici,
        "usd_trend": usd_trend, "usd_sembol": usd_sembol, "btc_korelasyon": korelasyon,
        "btc_rejim": btc.get("rejim", "BILINMIYOR"),
        # eski kartla uyum (giris karti / Telegram)
        "ema50": ema50_1, "rsi14": rsi1, "adx14": adx1,
    })

    # ---- ZORUNLU KURALLAR (biri bile saglanmazsa girilmez) ----
    kurallar = [
        (gunluk == "ASAGI", "gunluk grafikte dusus trendi"),
        (h4_trend != "YUKARI", f"4 saatlik trend yukari degil ({h4_trend})"),
        (adx4 is None or adx4 < ADX_MIN_ESIK, f"4 saatlik trend zayif (ADX {adx4 or 0:.1f} < {ADX_MIN_ESIK})"),
        (pdi4 is not None and mdi4 is not None and pdi4 <= mdi4, "4 saatlik trend yonu asagi (+DI <= -DI)"),
        (adx1 is None or adx1 < ADX_MIN_ESIK, f"1 saatlik trend zayif (ADX {adx1 or 0:.1f} < {ADX_MIN_ESIK})"),
        (not ((macd and macd[0] > macd[1]) or k1[-1] > ema20_1),
         "1 saatlikte geri cekilme suruyor (MACD zayifliyor ve fiyat EMA20 altinda)"),
        (rsi1 is None or not (RSI_KALITE_ALT_ESIK <= rsi1 <= RSI_KALITE_UST_ESIK),
         f"1s RSI uygun aralikta degil ({rsi1 or 0:.1f}, olmasi gereken {RSI_KALITE_ALT_ESIK}-{RSI_KALITE_UST_ESIK})"),
        (rsi4 is not None and rsi4 > 72, f"4 saatlikte asiri alim (RSI {rsi4 or 0:.1f})"),
        (rsi15 is not None and rsi15 > 75, f"son 15 dakikada asiri yukselmis (RSI {rsi15 or 0:.1f})"),
        (ema20_15 is not None and atr15 and fiyat > ema20_15 + 2.5 * atr15, "son 15 dakikada kopmus yukselis - kovalanmaz"),
        (oda_r is not None and oda_r < MIN_ODA_R, f"dirence cok yakin (kar alani {oda_r or 0:.1f}R < {MIN_ODA_R}R)"),
        (usd_trend == "ASAGI", f"{usd_sembol} paritesinde dusus - TRY yukselisi lira kaynakli olabilir"),
        (btc.get("rejim") == "RISKLI", "BTC riskli (sert dusus/oynaklik)"),
        (btc.get("rejim") == "ZAYIF" and korelasyon is not None and korelasyon >= 0.6,
         f"BTC zayif ve coin BTC'ye bagli (korelasyon {korelasyon or 0:.2f})"),
    ]
    for kosul, sebep in kurallar:
        if kosul:
            a["sebep"] = sebep
            return a

    # ---- PUAN (0-100) ----
    p = a["puanlar"]
    p["trend"] = ((10 if gunluk == "YUKARI" else 5 if gunluk == "BILINMIYOR" else 0)
                  + (5 if (ema50_4_egim or 0) > 0 else 0)
                  + min(10.0, max(0.0, (adx4 - 20) * 0.5))
                  + (5 if (pdi1 or 0) > (mdi1 or 0) else 0))
    p["ivme"] = ((5 if macd and macd[0] > 0 else 0) + (5 if macd and macd[0] > macd[1] else 0)
                 + (5 if 45 <= rsi1 <= 60 else 0) + (5 if k1[-1] > ema20_1 else 0))
    p["hacim"] = ((8 if (gor_hacim or 0) >= 1.2 else 4 if (gor_hacim or 0) >= 0.8 else 0)
                  + (6 if (obv or 0) > 0 else 0)
                  + (6 if (alici or 0) >= 0.52 else 3 if (alici or 0) >= 0.48 else 0))
    p["kar_alani"] = (15 if (oda_r is None or oda_r >= 3) else 10 if oda_r >= 2
                      else 7 if oda_r >= 1.5 else 4)
    p["btc"] = {"GUCLU": 10, "NOTR": 6, "BILINMIYOR": 5, "ZAYIF": 3}.get(btc.get("rejim"), 5)
    p["lira"] = 5 if usd_trend == "YUKARI" else 3
    a["skor"] = round(sum(p.values()), 1)
    if a["skor"] < ANALIZ_MIN_SKOR:
        a["sebep"] = f"puan yetersiz ({a['skor']:.0f} < {ANALIZ_MIN_SKOR:.0f})"
        return a
    a["gecti"] = True
    return a


def analiz_raporu_satirlari(a: dict) -> list:
    """Detayli analizin okunur ozeti (konsol, 'analiz' komutu ve Telegram /analiz)."""
    satirlar = [f"{a['symbol']}: " + (f"GIRILEBILIR - puan {a['skor']:.0f}/100" if a.get("gecti")
                                      else f"GIRILMEZ - {a.get('sebep') or 'bilinmiyor'}")]
    if "fiyat" not in a:
        return satirlar
    def s(x, fmt="{:.1f}"):
        return "-" if x is None else fmt.format(x)
    yon = "yukari" if (a.get("pdi_1h") or 0) > (a.get("mdi_1h") or 0) else "asagi"
    macd = a.get("macd_hist")
    satirlar += [
        f"  Fiyat: {format_fiyat(a['fiyat'])} TRY",
        f"  Trend  -> gunluk: {a['gunluk_trend']} | 4s: {a['h4_trend']} (ADX {s(a.get('adx_4h'))}) | "
        f"1s ADX: {s(a.get('adx_1h'))} ({yon})"
        + (f" | USDT paritesi: {a['usd_trend']}" if a.get("usd_sembol") else ""),
        f"  Ivme   -> RSI 1s/4s/15dk: {s(a.get('rsi_1h'))}/{s(a.get('rsi_4h'))}/{s(a.get('rsi_15m'))} | "
        f"MACD: {'pozitif' if macd and macd[0] > 0 else 'negatif'}{', guclenen' if macd and macd[0] > macd[1] else ''}",
        f"  Hacim  -> son saat ortalamanin {s(a.get('goreceli_hacim'), '{:.1f}')} kati | "
        f"OBV: {'alim baskisi' if (a.get('obv_egimi') or 0) > 0 else 'satis baskisi'} | "
        f"alici payi: %{s((a.get('alici_orani') or 0) * 100, '{:.0f}')}",
        f"  Seviye -> destek: {format_fiyat(a['destek']) if a.get('destek') else '-'} | direnc: "
        f"{format_fiyat(a['direnc']) if a.get('direnc') else 'yok (zirve bolgesi)'}"
        + (f" ({a['oda_r']:.1f}R uzakta)" if a.get("oda_r") is not None else ""),
        f"  Plan   -> stop {format_fiyat(a['stop_fiyati'])} (-%{a['stop_pct'] * 100:.1f}, {a['stop_kaynagi']}) | "
        f"hedef1 {format_fiyat(a['hedef1'])} | hedef2 {format_fiyat(a['hedef2'])}",
        f"  BTC    -> rejim {a['btc_rejim']}"
        + (f" | korelasyon {a['btc_korelasyon']:.2f}" if a.get("btc_korelasyon") is not None else ""),
    ]
    if a.get("puanlar"):
        satirlar.append("  Puan   -> " + ", ".join(f"{k}: {v:.0f}" for k, v in a["puanlar"].items()))
    return satirlar


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

    # v19: DETAYLI ANALIZ - BTC rejimi + her hazir aday icin gunluk/4s/1s/15dk,
    # hacim, destek/direnc, USDT paritesi. Sadece buradan GECEN coinlere girilir.
    btc = btc_rejim_analizi()
    print(f"{CYAN}  DETAYLI ANALIZ (gunluk / 4s / 1s / 15dk, hacim, destek-direnc, BTC){RESET}")
    for satir in btc_raporu_satirlari(btc):
        print(f"  {satir}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    analiz_sayisi = 0
    for sym, _, _ in nihai_adaylar:
        if durum_map[sym] == "HAZIR" and analiz_sayisi < DERIN_ANALIZ_MAKS:
            analiz_sayisi += 1
            analiz = coin_derin_analiz(sym, btc)
            time.sleep(API_CALL_SLEEP_SECONDS)
        elif durum_map[sym] == "HAZIR":
            analiz = {"symbol": sym, "gecti": False, "skor": 0.0, "sebep": "bu turda detayli analiz sirasi gelmedi"}
        else:
            analiz = {"symbol": sym, "gecti": False, "skor": 0.0, "sebep": "RSI yuksek, sogumasi bekleniyor"}
        bilgi_map[sym]["derin"] = analiz
        if analiz.get("gecti"):
            print(f"  {sym:<10} {GREEN}GIRILEBILIR{RESET} puan {analiz['skor']:.0f}/100 | stop -%"
                  f"{analiz['stop_pct'] * 100:.1f} | hedef1 +%{analiz['stop_pct'] * 100 * TP1_R:.1f} | "
                  f"hedef2 +%{analiz['stop_pct'] * 100 * TP2_R:.1f}")
        elif "fiyat" in analiz:
            print(f"  {sym:<10} {YELLOW}girilmez{RESET}   {analiz['sebep']}")
    nihai_adaylar.sort(key=lambda x: (bilgi_map[x[0]]["derin"].get("gecti", False),
                                      bilgi_map[x[0]]["derin"].get("skor", 0.0),
                                      adx_map.get(x[0], 0.0)), reverse=True)

    secilenler = nihai_adaylar[:sayisi]

    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}{GREEN}  IZLEME LISTESI ({len(secilenler)} coin - esnek, zorunlu sabit sayi yok):{RESET}")
    for sym, hacim_try, degisim_pct in secilenler:
        derin = bilgi_map[sym].get("derin", {})
        durum_etiketi = ("beklemede (RSI sogusun)" if durum_map[sym] == "BEKLEMEDE"
                         else f"GIRILEBILIR (puan {derin.get('skor', 0):.0f})" if derin.get("gecti")
                         else "izleniyor (analizden gecmedi)")
        print(f"    -> {sym}  (hacim: {hacim_try:,.0f} TRY, 24s degisim: %{degisim_pct:.2f}, durum: {durum_etiketi})")
    print(f"{CYAN}{'-' * 74}{RESET}\n")

    hacim_map = {sym: hacim_try for sym, hacim_try, _ in secilenler}
    secilen_durum_map = {sym: durum_map[sym] for sym, _, _ in secilenler}
    secilen_bilgi_map = {sym: bilgi_map[sym] for sym, _, _ in secilenler}  # v14

    return [s[0] for s in secilenler], hacim_map, secilen_durum_map, secilen_bilgi_map


def print_banner():
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS - v21'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}  BINANCE TR OTOMATIK ALIM-SATIM BOTU  |  {'GUNLUK TREND TAKIBI' if TREND_MODU else 'KISA VADELI ANALIZ'}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    if CANLI_MOD:
        print(f"{RED}{BOLD}  !!! CANLI_MOD = True: BU BOT GERCEK PARA ILE GERCEK EMIR GONDERECEK !!!{RESET}")
    else:
        print(f"{YELLOW}  DRY-RUN (SIMULASYON) modunda. Gercek emir gonderilmiyor.{RESET}")
    print(f"{GRAY}  Calisma modu       : {'CANLI (GERCEK PARA)' if CANLI_MOD else 'SIMULASYON'}{RESET}")
    if TREND_MODU:
        print(f"{CYAN}{BOLD}  Strateji           : TREND - {', '.join(c[:-3] for c in TREND_COINLERI)}{RESET}")
        print(f"{CYAN}                       gunluk kapanis {TREND_KIRILIM_GUN} gunun zirvesini kirinca ve EMA{TREND_EMA} "
              f"ustundeyken alim{' (BTC EMA50 ustundeyse)' if TREND_BTC_FILTRESI else ''};{RESET}")
        print(f"{CYAN}                       stop {TREND_ILK_STOP_ATR:g} x ATR, her gun zirve - {TREND_TAKIP_ATR:g} x ATR'ye "
              f"yukselir; en fazla {TREND_MAKS_POZISYON} pozisyon, islem basina risk %{RISK_PCT * 100:g}{RESET}")
        print(f"{GRAY}                       (eski kisa vadeli strateji icin AURELIUS_STRATEJI=KISA){RESET}")
    print(f"{GRAY}  Sanal/baslangic kasa: {TOPLAM_SANAL_BAKIYE_TRY:,.0f} TRY{RESET}")
    print(f"{GRAY}  Spread filtresi    : max %{MAX_SPREAD_PCT} (ustunde ALIM iptal edilir){RESET}")
    print(f"{GRAY}  Komisyon           : %{KOMISYON_PCT * 100:.2f}{RESET}")
    print(f"{GRAY}  Slipaj araligi     : %{SLIPAJ_MIN_PCT * 100:.2f} - %{SLIPAJ_MAKS_PCT * 100:.2f}{RESET}")
    if not TREND_MODU:  # v21: kisa vadeli stratejinin ayarlari
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
        print(f"{GRAY}  Trend filtresi     : EMA{EMA_PERIYOT}, esik %{TREND_ESIK_PCT * 100:.1f}{RESET}")
        print(f"{GRAY}  RSI giris filtresi : asiri alim>={RSI_ASIRI_ALIM_ESIGI} beklemeye alinir, "
              f"giris icin RSI {RSI_KALITE_ALT_ESIK}-{RSI_KALITE_UST_ESIK}{RESET}")
        print(f"{GRAY}  Detayli analiz     : gunluk/4s/1s/15dk trend, hacim, destek-direnc, USDT paritesi, "
              f"BTC rejimi (min puan {ANALIZ_MIN_SKOR:.0f}){RESET}")
        print(f"{GRAY}  Stop (1R)          : destegin alti veya {R_STOP_ATR_KATSAYI:g} x ATR(1s), "
              f"%{R_STOP_MIN_PCT * 100:.0f}-%{R_STOP_MAKS_PCT * 100:.0f} arasi{RESET}")
        print(f"{GRAY}  Kar alma           : 1/3 +{TP1_R:g}R (stop basa-basa), kalanin yarisi +{TP2_R:g}R "
              f"(stop +{TP2_SONRASI_KILIT_R:g}R), son kisim zirve-{CHANDELIER_ATR_KATSAYI:g}xATR takip{RESET}")
        print(f"{GRAY}  ADX trend filtresi : min {ADX_MIN_ESIK} (altinda whipsaw/yatay piyasa - GIRILMEZ){RESET}")
        print(f"{GRAY}  ATR grid adaptasyonu: dusuk vol ~%2.75 / orta ~%4 / yuksek vol ~%5.25 basamak{RESET}")
        print(f"{GRAY}  Zaman asimi cikisi : {MAKS_POZISYON_OMRU_SAAT:.0f}s+ ve kar<%{ZAMAN_ASIMI_KAR_ESIGI_PCT*100:.0f} ise zorla kapatilir{RESET}")
        print(f"{GRAY}  Dinamik cooldown   : kar={COOLDOWN_KAR_DAKIKA:.0f}dk, zarar={COOLDOWN_ZARAR_DAKIKA:.0f}dk, zaman asimi={COOLDOWN_ZAMAN_ASIMI_DAKIKA:.0f}dk{RESET}")
    if CANLI_MOD:
        print(f"{GRAY}  Bakiye mutabakati  : her ~{MUTABAKAT_ARALIGI_SAAT:.0f} saatte + gunluk X raporunda{RESET}")
    print(f"{GRAY}  Acil fren limiti   : %{MAX_DRAWDOWN_PCT * 100:.0f} (portfoyun en yuksek degerinden; "
          f"yeniden baslatmada sifirlanmaz){RESET}")
    print(f"{GRAY}  Islem basina risk  : "
          f"{f'%{RISK_PCT * 100:g} (stop olursa portfoyun en fazla bu kadari gider)' if RISK_PCT > 0 else 'kapali (tum kasa)'}"
          f"{RESET}")
    if not TREND_MODU:  # trend stratejisinde test edilen kurallar: sadece acil fren
        print(f"{GRAY}  Gunluk zarar limiti: "
              f"{f'%{GUNLUK_ZARAR_LIMIT_PCT * 100:g} (asilirsa o gun yeni alim yok)' if GUNLUK_ZARAR_LIMIT_PCT > 0 else 'kapali'}"
              f"{RESET}")
        print(f"{GRAY}  Kayip korumasi     : "
              + (f"art arda {KAYIP_SERISI_LIMIT} zarar -> {KAYIP_SERISI_MOLA_SAAT:.0f}s mola; " if KAYIP_SERISI_LIMIT else "")
              + f"stop olan coin {COIN_STOP_ENGEL_SAAT:.0f}s, {COIN_TEKRAR_KAYIP_GUN} gunde {COIN_TEKRAR_KAYIP_SAYISI} "
                f"zarar ettiren coin {COIN_TEKRAR_ENGEL_SAAT:.0f}s engelli{RESET}")
    print(f"{GRAY}  Durum dosyasi      : {STATE_DOSYASI}{RESET}")
    print(f"{GRAY}  Telegram bildirimi : {'AKTIF (arka plan kuyrugu)' if (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) else 'kapali (TELEGRAM_BOT_TOKEN/CHAT_ID tanimli degil)'}{RESET}")
    telegram_hazir = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
    print(f"{GRAY}  Telegram komutlari : {'AKTIF (/yardim)' if (telegram_hazir and TELEGRAM_KOMUTLARI_AKTIF) else 'kapali'}{RESET}")
    print(f"{GRAY}  Durum bildirimi    : {f'her {DURUM_BILDIRIM_SAAT:g} saatte bir' if (telegram_hazir and DURUM_BILDIRIM_SAAT > 0) else 'kapali'}{RESET}")
    print(f"{GRAY}  Saglik pingi       : {'AKTIF (her 5 dk)' if SAGLIK_PING_URL else 'kapali (AURELIUS_SAGLIK_URL tanimli degil)'}{RESET}")
    if CANLI_MOD:
        print(f"{GRAY}  Borsa stop emri    : {f'AKTIF (tetik = bot stop-%{BORSA_STOP_TAMPON_PCT*100:g})' if BORSA_STOP_AKTIF else 'kapali (AURELIUS_BORSA_STOP=1 ile acilir)'}{RESET}")
    print(f"{GRAY}  Hata log dosyasi   : {LOG_DOSYASI}{RESET}")
    print(f"{GRAY}  Gunluk X raporu    : her 24 saatte bir (sayac restart'ta sifirlanmaz){RESET}")
    print(f"{GRAY}  Aylik Z raporu     : her 30 gunde bir -> {os.path.basename(Z_RAPORLARI_CSV)}{RESET}")
    print(f"{GRAY}  Islem kaydi        : {ISLEMLER_CSV}{RESET}")
    print(f"{GRAY}  Islem gunlugu      : {ISLEM_GUNLUGU_CSV} ('rapor' komutu / Telegram /rapor){RESET}")
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
                         calisma_modu: str, hedef1_fiyat: Optional[float] = None,
                         analiz_ozeti: Optional[str] = None) -> str:
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
    ] + ([
        satir(f"Hedef 1 (1/3) : {format_fiyat(hedef1_fiyat)} TRY "
              f"({(hedef1_fiyat - exec_price) / exec_price * 100 if exec_price else 0:+.1f}%)"),
        satir(f"Hedef 2 (1/3) : {format_fiyat(hedef_fiyat)} TRY ({hedef_pct:+.1f}%)"),
        satir("Kalan (1/3)   : takip eden stop ile (ust sinir yok)"),
        satir(f"Beklenen Kar  : {beklenen_net_kar:+,.2f} TRY (temkinli)"),
    ] if hedef1_fiyat is not None else [
        satir(f"Hedef Satis   : {format_fiyat(hedef_fiyat)} TRY ({hedef_pct:+.1f}%)"),
        satir(f"Hedef Kar     : {beklenen_net_kar:+,.2f} TRY"),
    ]) + [
        satir(f"Stop-Loss     : {format_fiyat(stop_fiyat)} TRY ({stop_pct:+.1f}%)"),
        satir(f"Maks Risk     : {beklenen_net_kayip:+,.2f} TRY"),
        ic_cizgi(),
        satir(f"Gostergeler   : RSI:{rsi_str} | EMA:{ema_str}"),
        satir(f"Trend Gucu    : ADX:{adx_str} ({_adx_trend_etiketi(adx14)})"),
        satir(f"Mod           : {calisma_modu}"),
    ] + ([satir(f"Analiz        : {analiz_ozeti}")] if analiz_ozeti else []) + [
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
    return f"{saat:.0f}s"


def print_performans_raporu(kasa: MerkeziKasa, pozisyonlar: dict, acik_pozisyon_sayisi: int,
                             izin_verilen_pozisyon: Optional[int] = None, telegram_gonder: bool = True):
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
    print(f"  {'Baslangic Sermayesi':<28}: {kasa.baslangic:>14,.2f} TRY")
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
            fiyat = b.guncel_fiyat()
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

    # v21: RSI beklemesi ve cooldown sadece kisa vadeli stratejide kullanilir
    beklemede_olanlar = [] if TREND_MODU else [b for b in pozisyonlar.values() if b.bekliyor]
    cooldown_olanlar = [] if TREND_MODU else [b for b in pozisyonlar.values()
                                              if not b.has_open_position and b.cooldown_aktif_mi()]
    if beklemede_olanlar:
        print(f"  {YELLOW}RSI asiri alimda bekleyen: {', '.join(b.symbol for b in beklemede_olanlar)}{RESET}")
    if cooldown_olanlar:
        bekleme_str = ", ".join(f"{b.symbol}({b.cooldown_kalan_dakika():.0f}dk)" for b in cooldown_olanlar)
        print(f"  {GRAY}Cooldown'da (yeni alim kilitli): {bekleme_str}{RESET}")

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
    "/analiz SEMBOL - coinin detayli analizi (orn. /analiz PEPETRY)\n"
    "/btc - BTC piyasa rejimi\n"
    "/trend - coinlerin alim sinyaline (50 gunluk zirveye) uzakligi\n"
    "/rapor - son 30 gunun islem ozeti (islem gunlugunden)\n"
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
    ] + ([html.escape(trend_durum_satiri())] if TREND_MODU else []) \
      + [html.escape(satir) for satir in _risk.durum_satirlari(portfoy)]
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
    parcalar = komut.split()
    komut, arguman = parcalar[0], (parcalar[1] if len(parcalar) > 1 else "")
    if komut == "/analiz":
        sembol = arguman.upper()
        if not (sembol.isalnum() and sembol.endswith("TRY") and len(sembol) > 3):
            send_telegram("Kullanim: /analiz SEMBOL (orn. /analiz PEPETRY)")
            return
        btc = btc_rejim_analizi()
        analiz = coin_derin_analiz(sembol, btc)
        send_telegram("<pre>" + html.escape("\n".join(analiz_raporu_satirlari(analiz))) + "</pre>")
        return
    if komut == "/btc":
        send_telegram("<pre>" + html.escape("\n".join(btc_raporu_satirlari(btc_rejim_analizi()))) + "</pre>")
        return
    if komut == "/trend":
        send_telegram("<pre>" + html.escape("\n".join(trend_durumu_satirlari(pozisyonlar))) + "</pre>")
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
        send_telegram("\u23F8 <b>Yeni alimlar durduruldu.</b>\nAcik pozisyonlar stop/kar-al kurallariyla "
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
                      f"(stop/kar-al kurallariyla yonetilmeye devam eder). Tekrar denemek icin /hepsinisat, "
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
                    komut = parcalar[0].split("@")[0].lower()
                    if komut == "/analiz" and len(parcalar) > 1:
                        komut += " " + parcalar[1].upper()
                    _telegram_komut_kuyrugu.put(komut)
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
    print(f"{YELLOW}    [H] Oldugu gibi birak - bot kapaliyken stop/kar-al CALISMAZ (varsayilan){RESET}")
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
    """'python project_aurelius_bot_v21.py kurulum': bu penceredeki ayarlarla, bot
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
    _risk.temizle()
    kasa.baslangic = _risk.yatirilan_sermaye
    pnl = portfoy - kasa.baslangic
    print(f"{CYAN}  Sermaye: baslangic {kasa.baslangic:,.2f} TRY | portfoy {portfoy:,.2f} TRY "
          f"({pnl:+,.2f} TRY) | acil fren: {_risk.zirve_portfoy:,.2f} TRY zirvesinden "
          f"%{MAX_DRAWDOWN_PCT * 100:.0f} dususte{RESET}")
    for satir in _risk.durum_satirlari(portfoy)[1:]:
        print(f"{YELLOW}  {satir}{RESET}")
    print()


def _risk_engeli_bildir(engel: Optional[tuple], onceki_kod: Optional[str]) -> Optional[str]:
    """Yeni alim engeli basladiginda/bittiginde bir kez haber verir."""
    kod = engel[0] if engel else None
    if kod != onceki_kod:
        if engel:
            print(f"[{ts()}] {YELLOW}RISK KORUMASI: yeni alim yok - {engel[1]}{RESET}")
            send_telegram(f"\U0001F6E1 <b>Yeni alimlar durdu</b>\n{html.escape(engel[1])}\n"
                          "Acik pozisyonlar yonetilmeye devam ediyor.")
        elif onceki_kod:
            print(f"[{ts()}] {GREEN}RISK KORUMASI: yeni alimlar tekrar acik.{RESET}")
            send_telegram("\U0001F6E1 Risk korumasi: yeni alimlar tekrar acik.")
    return kod


def run_simulation():
    global _alim_durumu, _risk
    print_banner()

    if CANLI_MOD and not canli_mod_on_kontrol():
        print(f"{RED}Bot baslatilamadi (CANLI_MOD guvenlik kontrolu basarisiz).{RESET}")
        return CIKIS_AYAR_HATASI

    if TREND_MODU:
        # v21: trend modunda tarama yok - sabit buyuk coin listesi, gunde bir kontrol
        semboller, watchlist, hacim_map, durum_map, bilgi_map = list(TREND_COINLERI), [], {}, {}, {}
    else:
        print(f"[{ts()}] Binance TR piyasasi taraniyor, TRY paritesi olan coinler bulunuyor...")
        try:
            semboller = try_paritelerini_bul()
        except Exception as e:
            print(f"{RED}Piyasa taranamadi: {e}{RESET}")
            return CIKIS_YENIDEN_DENE

        if not semboller:
            print(f"{RED}Hicbir TRY paritesi bulunamadi, bot baslatilamiyor.{RESET}")
            return CIKIS_YENIDEN_DENE

        print(f"[{ts()}] Toplam {len(semboller)} TRY paritesi bulundu.\n")

        try:
            watchlist, hacim_map, durum_map, bilgi_map = coin_degerlendir_ve_sec(semboller, MAX_WATCHLIST)
        except Exception as e:
            print(f"{RED}Coin degerlendirmesi yapilamadi: {e}{RESET}")
            return CIKIS_YENIDEN_DENE

        if not watchlist:
            print(f"{YELLOW}  Su an kriterlere uyan hicbir coin yok. Bot %100 nakitte bekleyecek "
                  f"ve periyodik olarak piyasayi yeniden tarayacak.{RESET}\n")

    # v10 BOLUM 1: onceki oturumdan kalici durum var mi kontrol et
    try:
        kayitli_durum = durumu_yukle()
    except CanliDurumKorumasi as e:
        print(f"{RED}{BOLD}  {e}{RESET}")
        return CIKIS_AYAR_HATASI
    risk_kayitli = bool(kayitli_durum and isinstance(kayitli_durum.get("risk"), dict))  # v20
    _risk = RiskKorumasi.from_dict(kayitli_durum.get("risk") if kayitli_durum else None)
    _trend_durumu.clear()
    _trend_durumu.update((kayitli_durum or {}).get("trend") or {})  # v21
    if kayitli_durum and kayitli_durum.get("strateji", "KISA") != STRATEJI:
        print(f"{CYAN}  Strateji degisti ({kayitli_durum.get('strateji', 'KISA')} -> {STRATEJI}): acik pozisyonlar "
              f"acildiklari kurallarla yonetilmeye devam eder, yeni alimlar {STRATEJI} kurallariyla yapilir.{RESET}")
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
        rapor = RaporlamaDurumu(TOPLAM_SANAL_BAKIYE_TRY)  # v11
        if CANLI_MOD:
            print(f"{YELLOW}  Kayitli durum bulunamadi, temiz baslangic (bakiye borsadan cekilecek).{RESET}\n")
        else:
            print(f"{YELLOW}  Kayitli durum bulunamadi, temiz baslangic: {TOPLAM_SANAL_BAKIYE_TRY:,.2f} TRY{RESET}\n")

    # v17 FIX: CANLI MOD ise borsadan gercek bakiyeyi cek ve kasa ile esitle.
    # Cekilen gercek serbest TRY tutari SIFIRDAN BUYUKSE, kasa.baslangic VE
    # kasa.bakiye DOGRUDAN bu tutara esitlenir (onceki oturumdan kayitli
    # durum olsa BILE) - boylece "hep 0.00 TRY" yanilgisindan sonra ilk
    # basarili canli baslangicta kasa GERCEK borsa bakiyesiyle net bir
    # sekilde senkronize olur. Tutar 0 (veya negatif/okunamadi) ise kasa
    # SESSIZCE sifirlanmaz - mevcut/kayitli deger korunur ve acikca uyarilir.
    if CANLI_MOD:
        # v18: Bot kapaliyken borsadaki stop emri dolduysa satisi ONCE kaydet; kasa
        # hemen asagida borsadaki gercek TRY bakiyesine esitlenir (cift sayim olmaz).
        for bot in pozisyonlar.values():
            if any(lvl.has_position and lvl.borsa_stop_emir_id for lvl in bot.grid):
                bot.borsa_stop_bakimi(kasa, acik_pozisyon_sayaci, rapor, None, zorla_sorgu=True, yeni_kur=False)
        onceki_serbest = kasa.bakiye  # v20: bot kapanirken kayitli serbest TRY
        try:
            bakiyeler = binance_hesap_bakiyeleri()
        except Exception as e:
            print(f"{RED}  HATA: Canli bakiye cekilemedi, bot baslatilamiyor: {e}{RESET}")
            return CIKIS_YENIDEN_DENE
        bakiye_ozeti_yazdir(bakiyeler)
        gercek_bakiye = bakiyeler.get("TRY", {}).get("free", 0.0)
        print(f"{GREEN}  CANLI MOD AKTIF - borsadan cekilen serbest TRY bakiyesi: {gercek_bakiye:,.2f} TRY{RESET}\n")
        # v20: kasa.baslangic (sermaye tabani) artik her acilista sifirlanmiyor - bkz. _risk_baslat
        # Bakiye 0 ise kasa ASLA sanal TOPLAM_SANAL_BAKIYE_TRY ile kalmamali, yoksa bot var
        # olmayan parayla gercek emir gondermeye calisir.
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
        send_telegram(f"\U0001F7E2 <b>Project Aurelius CANLI MODDA baslatildi!</b>\nBorsa bakiyesi: {kasa.bakiye:,.2f} TRY"
                      f"\nYeni alimlar: {ALIM_DURUMU_ACIKLAMA[_alim_durumu]}"
                      f"\nBorsa stop emri: {'ACIK' if BORSA_STOP_AKTIF else 'kapali'}"
                      f"\n{trend_durum_satiri() if TREND_MODU else 'Strateji: KISA (detayli analiz)'}"
                      f"\nIslem basina risk: %{RISK_PCT * 100:g}"
                      + ("" if TREND_MODU else f" | gunluk zarar limiti: %{GUNLUK_ZARAR_LIMIT_PCT * 100:g}")
                      + ("\nKomutlar icin /yardim" if TELEGRAM_KOMUTLARI_AKTIF else ""))
    else:
        send_telegram(f"\U0001F9EA Project Aurelius SIMULASYON modunda baslatildi. Bakiye: {kasa.bakiye:,.2f} TRY\n"
                      + (trend_durum_satiri() if TREND_MODU else "Strateji: KISA (detayli analiz)"))
    _risk_baslat(kasa, v9_toplam_portfoy_degeri(kasa, pozisyonlar), risk_kayitli)  # v20
    if TREND_MODU:
        for b in pozisyonlar.values():
            b.bekliyor = False  # eski stratejinin RSI beklemesi trend stratejisinde anlamsiz
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
    _saglik_pingi_gonder()

    real_poll_count = 0
    son_risk_engeli = None  # v20
    son_btc_rejimi = None  # v19
    btc_rejimi = "BILINMIYOR"
    izin_verilen_pozisyon = 0  # v14: guvenli varsayilan (ilk tick'ten once bir kesinti olursa)
    sniper_modu_aktif = False  # v17: guvenli varsayilan
    scan_araligi_tur = max(1, round((SCAN_INTERVAL_MINUTES * 60) / REAL_POLL_INTERVAL_SECONDS))
    varlik_yenileme_araligi_tur = max(1, round((ASSET_REFRESH_HOURS * 3600) / REAL_POLL_INTERVAL_SECONDS))
    mutabakat_araligi_tur = max(1, round((MUTABAKAT_ARALIGI_SAAT * 3600) / REAL_POLL_INTERVAL_SECONDS))  # v16
    if not TREND_MODU:
        print(f"[{ts()}] Firsat taramasi her ~{SCAN_INTERVAL_MINUTES} dk'da bir, "
              f"varlik listesi yenilemesi her ~{ASSET_REFRESH_HOURS} saatte bir yapilacak.\n")

    try:
        while True:
            if TREND_MODU:
                if komut_isleyici is not None:
                    komut_isleyici()
                acik_pozisyon_sayaci[0] = sum(1 for b in pozisyonlar.values() if b.has_open_position)
                izin_verilen_pozisyon = TREND_MAKS_POZISYON
                _trend_turu(kasa, pozisyonlar, acik_pozisyon_sayaci, kaydet, rapor)
            else:
                piyasa_sert_duste = False
                btc_degisim = None
                try:
                    piyasa_sert_duste, btc_degisim = btc_piyasa_durumu()
                    if piyasa_sert_duste:
                        print(f"[{ts()}] {RED}BTC 24s degisim %{btc_degisim:.2f} - piyasa sert dususte, "
                              f"YENI pozisyon aranmiyor (mevcut pozisyonlar yonetilmeye devam ediyor).{RESET}")
                except Exception:
                    pass
                # v19: detayli BTC rejimi (5 dk onbellekli). RISKLI -> yeni alim yok.
                try:
                    btc_rejimi = btc_rejim_analizi().get("rejim", "BILINMIYOR")
                except Exception:
                    btc_rejimi = "BILINMIYOR"
                if btc_rejimi != son_btc_rejimi:
                    if son_btc_rejimi is not None:
                        print(f"[{ts()}] {CYAN}BTC rejimi degisti: {son_btc_rejimi} -> {btc_rejimi}{RESET}")
                        if btc_rejimi == "RISKLI" or son_btc_rejimi == "RISKLI":
                            send_telegram(f"\u26A0\uFE0F <b>BTC rejimi: {son_btc_rejimi} -> {btc_rejimi}</b>\n"
                                          + ("Yeni alim yapilmayacak; acik pozisyonlar yonetilmeye devam ediyor."
                                             if btc_rejimi == "RISKLI" else "Yeni alimlar tekrar degerlendiriliyor."))
                    son_btc_rejimi = btc_rejimi
                if btc_rejimi == "RISKLI":
                    piyasa_sert_duste = True

                # Sayac tick icinde canli guncellenir, ama basarisiz tasfiye / mutabakat
                # ile kapatilan pozisyonlar gibi yollarla kayabilir; her tick gercekten
                # yeniden kur.
                if komut_isleyici is not None:
                    komut_isleyici()
                acik_pozisyon_sayaci[0] = sum(1 for b in pozisyonlar.values() if b.has_open_position)
                guncel_bakiye = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
                izin_verilen_pozisyon, hedef_pozisyon_tutari, sniper_modu_aktif = dinamik_pozisyon_planla(
                    kasa.bakiye, guncel_bakiye, btc_degisim, btc_rejimi
                )  # v17: kasaya gore adaptif Sniper Modu / kademeli portfoy modeli; v19: BTC rejimi
                if _alim_durumu != "ACIK":
                    izin_verilen_pozisyon = 0  # v18: /alimdurdur veya /bosalt - sadece yonetim, yeni alim yok
                _risk.portfoy_guncelle(guncel_bakiye)  # v20: gunluk zarar limiti / kayip molasi
                risk_engeli = _risk.yeni_alim_engeli(guncel_bakiye)
                if risk_engeli:
                    izin_verilen_pozisyon = 0
                son_risk_engeli = _risk_engeli_bildir(risk_engeli, son_risk_engeli)
                en_kaliteli_aday = en_kaliteli_aday_belirle(bilgi_map, pozisyonlar)  # v17 MODUL 1.2

                ilgilenilecek_semboller = sorted(set(pozisyonlar.keys()) | set(watchlist))

                for sym in ilgilenilecek_semboller:
                    if sym not in pozisyonlar:
                        dinamik_width = bilgi_map.get(sym, {}).get("width_pct", VARSAYILAN_WIDTH_PCT)  # v16
                        pozisyonlar[sym] = CoinBot(
                            symbol=sym,
                            coin_name=_coin_adi(sym),
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
                    elif not bot.has_open_position and (fiyat < bot.lower or fiyat > bot.upper):
                        # Grid yalnizca ilk fiyatta kuruluyordu; fiyat bu banttan
                        # ciktiginda evaluate_v9 yeni alimi engelledigi icin coin, izleme
                        # listesinde kaldigi surece KALICI olarak alinamaz hale geliyordu.
                        # Pozisyon yokken grid'i guncel fiyata (ve guncel ATR genisligine)
                        # yeniden ortala.
                        bot.width_pct = bilgi_map.get(sym, {}).get("width_pct", bot.width_pct)
                        bot.setup_grid(fiyat)

                    if piyasa_sert_duste:
                        bot.stop_loss_kontrol(fiyat, sim=False, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                               durum_kaydet=kaydet, rapor=rapor)
                    else:
                        bot.evaluate_v9(fiyat, sim=False, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                                         hedef_pozisyon_tutari=hedef_pozisyon_tutari,
                                         izin_verilen_pozisyon=izin_verilen_pozisyon,
                                         durum_kaydet=kaydet, rapor=rapor, giris_bilgisi=bilgi_map.get(sym),
                                         en_kaliteli_aday=en_kaliteli_aday, sniper_modu=sniper_modu_aktif,
                                         portfoy_degeri=guncel_bakiye)
                    bot.borsa_stop_bakimi(kasa, acik_pozisyon_sayaci, rapor, kaydet)  # v18

                    time.sleep(API_CALL_SLEEP_SECONDS)

            real_poll_count += 1
            rapor.drawdown_guncelle(v9_toplam_portfoy_degeri(kasa, pozisyonlar))  # v11: Z donemi max drawdown takibi
            kaydet()  # her tick sonunda genel bir guvenlik-agi kaydi (bakiye/durum tazeligi)

            # v20: acil fren, portfoyun ulastigi en yuksek degerden olan dususu olcer
            # (referans durum dosyasinda - yeniden baslatmada sifirlanmaz).
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
                print_performans_raporu(kasa, pozisyonlar, 0, izin_verilen_pozisyon=0)
                print(f"{RED}Bot acil fren nedeniyle durduruldu. Elle yeniden baslatirsaniz fren referansi o anki "
                      f"portfoy degerinden baslar.{RESET}")
                return CIKIS_DUR

            if not TREND_MODU and real_poll_count % scan_araligi_tur == 0:
                _risk.temizle()  # v20: suresi dolan coin engelleri
                try:
                    hedef_sayi = MIN_WATCHLIST if piyasa_sert_duste else MAX_WATCHLIST
                    watchlist, hacim_map, durum_map, bilgi_map = coin_degerlendir_ve_sec(semboller, hedef_sayi)
                except Exception as e:
                    print(f"{RED}Firsat taramasi basarisiz, mevcut watchlist ile devam ediliyor: {e}{RESET}")

            if not TREND_MODU and real_poll_count % varlik_yenileme_araligi_tur == 0:
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
                # v21: sadece konsola; Telegram ozeti AURELIUS_DURUM_BILDIRIM_SAAT'te bir gider
                print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0],
                                         izin_verilen_pozisyon=izin_verilen_pozisyon, telegram_gonder=False)

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

            # v18: periyodik "bot calisiyor" bildirimi ve dis saglik pingi
            simdi = time.monotonic()
            if SAGLIK_PING_URL and simdi - son_saglik_pingi >= SAGLIK_PING_ARALIGI_SANIYE:
                son_saglik_pingi = simdi
                _saglik_pingi_gonder()
            if DURUM_BILDIRIM_SAAT > 0 and simdi - son_durum_bildirimi >= DURUM_BILDIRIM_SAAT * 3600:
                son_durum_bildirimi = simdi
                send_telegram("\U0001F493 " + durum_ozeti_metni(kasa, pozisyonlar))

            # v18: bosaltma modu - acik pozisyon kalmadiysa bilincli olarak dur
            if _alim_durumu == "BOSALTMA" and not any(b.has_open_position for b in pozisyonlar.values()):
                _alim_durumu = "ACIK"  # sonraki baslatmada normal islem yapilsin
                print(f"\n{GREEN}{BOLD}  BOSALTMA TAMAMLANDI: acik pozisyon kalmadi, bot durduruluyor.{RESET}\n")
                send_telegram("\U0001F9F9 <b>Bosaltma tamamlandi.</b> Acik pozisyon kalmadi, bot durduruldu. "
                              f"Nakit: {kasa.bakiye:,.2f} TRY")
                return CIKIS_DUR

            # CANLI modda asla simule fiyatla islem yapilmaz (GERCEKCI_MOD kapatilsa bile)
            if GERCEKCI_MOD or CANLI_MOD or TREND_MODU:
                _dongu_beklemesi(komut_isleyici)
            else:
                for _ in range(SUB_TICKS_PER_REAL_POLL):
                    time.sleep(SUB_TICK_SECONDS)
                    guncel_bakiye_sim = v9_toplam_portfoy_degeri(kasa, pozisyonlar)
                    izin_verilen_sim, hedef_sim, sniper_sim = dinamik_pozisyon_planla(
                        kasa.bakiye, guncel_bakiye_sim, btc_degisim, btc_rejimi
                    )
                    if _alim_durumu != "ACIK" or _risk.yeni_alim_engeli(guncel_bakiye_sim):
                        izin_verilen_sim = 0
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
                                             en_kaliteli_aday=en_kaliteli_aday_sim, sniper_modu=sniper_sim,
                                             portfoy_degeri=guncel_bakiye_sim)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}--- Bot durduruldu (Ctrl+C) ---{RESET}\n")
        print_trade_history_table(pozisyonlar.values())
        print_performans_raporu(kasa, pozisyonlar, acik_pozisyon_sayaci[0],
                                 izin_verilen_pozisyon=izin_verilen_pozisyon)
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
# v20 BOLUM 3: GECMIS VERI TESTI (BACKTEST) - canli botla AYNI analiz (derin_analiz_hesapla,
# btc_rejim_hesapla), AYNI R cikislari (r_stop_hesapla) ve AYNI risk korumasi (RiskKorumasi).
# Emir gondermez, API anahtari gerektirmez, Telegram'a yazmaz.
# ==========================================================================
ARALIK_MS = {"15m": 900_000, "1h": 3_600_000, "4h": 14_400_000, "1d": 86_400_000}
ISINMA_MUM = {"15m": 100, "1h": MUM_SAYISI, "4h": MUM_SAYISI, "1d": MUM_SAYISI}
BACKTEST_VARSAYILAN_GUN = 60
BACKTEST_GUN_ARALIGI = (7, 120)
BACKTEST_VARSAYILAN_SERMAYE = 1000.0
BACKTEST_COIN_SAYISI = 15
BACKTEST_SLIPAJ_PCT = (SLIPAJ_MIN_PCT + SLIPAJ_MAKS_PCT) / 2
BACKTEST_MAKS_GERI_GUN = 240
KARSILASTIRMA_BARAJLARI = (55, 60, 65, 70, 75)
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


class _GecmisSeri:
    """Bir zaman dilimindeki gecmis mumlar; t anina kadar KAPANMIS son n mumu verir."""

    def __init__(self, veri: dict, interval: str):
        self.v, self.adim = veri, ARALIK_MS[interval]

    def pencere(self, t: int, n: int, son_fiyat: float) -> Optional[dict]:
        i = bisect.bisect_right(self.v["zaman"], t - self.adim)
        if i < 2:
            return None
        j = max(0, i - n)
        d = {k: self.v[k][j:i] for k in _MUM_ALANLARI}
        d["son_fiyat"] = son_fiyat
        return d


def backtest_simule_et(coin_verileri: dict, btc_verisi: Optional[dict], bas_ms: int, bitis_ms: int,
                       sermaye: float, min_skor: Optional[float] = None,
                       onbellek: Optional[dict] = None, ek_filtre=None) -> dict:
    """coin_verileri: {sembol: {"15m","1h","4h","1d","usd4h": gecmis_mumlari_getir ciktisi (veya None),
    "usd_sembol": str|None}}; btc_verisi: {"sembol", "1h", "4h", "1d"}. Islemler 15 dakikalik mumlarla
    yonetilir, yeni giris kararlari her saat basi (canli bot gibi tek seferde en yuksek puanli coin)."""
    risk = RiskKorumasi()
    nakit = sermaye
    acik: dict = {}
    son_kapanis: dict = {}         # sembol -> (ms, etiket) - cooldown icin
    islemler: list = []
    son_fiyat: dict = {}
    sayac = {"gunluk_limit_gunleri": set(), "mola": 0, "coin_engeli": 0, "acil_fren": False,
             "acik_saat": 0, "toplam_saat": 0, "komisyon": 0.0}
    seri = {s: {k: _GecmisSeri(v[k], k) for k in ("1h", "4h", "1d") if v.get(k)}
            for s, v in coin_verileri.items()}
    usd_seri = {s: _GecmisSeri(v["usd4h"], "4h") for s, v in coin_verileri.items() if v.get("usd4h")}
    idx15 = {s: {z: i for i, z in enumerate(v["15m"]["zaman"])} for s, v in coin_verileri.items() if v.get("15m")}
    m15_seri = {s: _GecmisSeri(v["15m"], "15m") for s, v in coin_verileri.items() if v.get("15m")}
    btc_seri = {k: _GecmisSeri(btc_verisi[k], k) for k in ("1h", "4h", "1d")
                if btc_verisi and btc_verisi.get(k)}
    zirve, en_derin = sermaye, 0.0
    son_engel = None

    def portfoy() -> float:
        return nakit + sum(p["level"].buy_qty * son_fiyat[s] for s, p in acik.items())

    def sat(sembol: str, miktar: float, fiyat: float, etiket: str, t: int, kapat: bool) -> None:
        nonlocal nakit
        p = acik[sembol]
        lv = p["level"]
        miktar = lv.buy_qty if kapat else min(miktar, lv.buy_qty)
        brut = miktar * fiyat * (1 - BACKTEST_SLIPAJ_PCT)
        kom = brut * KOMISYON_PCT
        nakit += brut - kom
        sayac["komisyon"] += kom
        p["pnl"] += brut - kom - miktar * lv.buy_price
        lv.buy_qty -= miktar
        if not kapat and lv.buy_qty > 1e-12:
            return
        del acik[sembol]
        simdi = datetime.fromtimestamp(t / 1000)
        kayit = islem_kaydi_olustur(sembol, "TEST", datetime.fromtimestamp(p["giris_ms"] / 1000), simdi,
                                    lv.buy_price, fiyat, p["tutar"], p["pnl"], p["miktar0"] * lv.risk_birimi,
                                    lv.risk_birimi / lv.buy_price, etiket, lv.tp1_alindi, lv.tp2_alindi,
                                    p["analiz"])
        islemler.append(kayit)
        son_kapanis[sembol] = (t, etiket)
        if etiket != "TEST-SONU":
            onceki_engel = risk.coin_engel.get(sembol)
            onceki_mola = risk.mola_bitis
            risk.islem_kapandi(sembol, p["pnl"], etiket, simdi)
            sayac["coin_engeli"] += risk.coin_engel.get(sembol) != onceki_engel
            sayac["mola"] += risk.mola_bitis != onceki_mola

    def cikislari_isle(sembol: str, i: int, t_kapanis: int) -> None:
        v = coin_verileri[sembol]["15m"]
        acl, yuk, dus, kap = v["acilis"][i], v["yuksek"][i], v["dusuk"][i], v["kapanis"][i]
        lv = acik[sembol]["level"]
        b, r = lv.buy_price, lv.risk_birimi
        stop, etiket = r_stop_hesapla(lv)
        if dus <= stop:  # ayni mumda hem stop hem hedef olabilir: temkinli olarak once stop
            sat(sembol, 0, min(stop, acl), etiket, t_kapanis, True)
            return
        if not lv.tp1_alindi and yuk >= b + TP1_R * r:
            sat(sembol, lv.buy_qty * TP1_ORAN, max(b + TP1_R * r, acl), "KAR-AL-1", t_kapanis, False)
            lv.tp1_alindi = True
        if lv.tp1_alindi and not lv.tp2_alindi and yuk >= b + TP2_R * r:
            sat(sembol, lv.buy_qty * TP2_ORAN, max(b + TP2_R * r, acl), "KAR-AL-2", t_kapanis, False)
            lv.tp2_alindi = True
        lv.en_yuksek_fiyat = max(lv.en_yuksek_fiyat, yuk)
        yas_saat = (t_kapanis - acik[sembol]["giris_ms"]) / 3_600_000
        if (not lv.tp1_alindi and yas_saat >= MAKS_POZISYON_OMRU_SAAT
                and kap < b * (1 + ZAMAN_ASIMI_KAR_ESIGI_PCT)):
            sat(sembol, 0, kap, "ZAMAN-ASIMI", t_kapanis, True)

    def btc_durumu(t: int) -> dict:
        if onbellek is not None and ("BTC", t) in onbellek:
            return onbellek[("BTC", t)]
        sonuc_btc = _btc_durumu_hesapla(t)
        if onbellek is not None:
            onbellek[("BTC", t)] = sonuc_btc
        return sonuc_btc

    def _btc_durumu_hesapla(t: int) -> dict:
        if not btc_seri.get("1h") or not btc_seri.get("4h"):
            return {"rejim": "BILINMIYOR"}
        h1 = btc_seri["1h"].pencere(t, MUM_SAYISI, 0.0)
        if not h1:
            return {"rejim": "BILINMIYOR"}
        h1["son_fiyat"] = h1["kapanis"][-1]
        h4 = btc_seri["4h"].pencere(t, MUM_SAYISI, h1["son_fiyat"])
        d1 = btc_seri["1d"].pencere(t, MUM_SAYISI, h1["son_fiyat"]) if btc_seri.get("1d") else None
        return btc_rejim_hesapla(btc_verisi.get("sembol", "BTC"), h1, h4, d1) or {"rejim": "BILINMIYOR"}

    def analiz(sembol: str, t: int, btc: dict) -> dict:
        # Analiz sadece t anina kadarki veriye bagli; karsilastirmada farkli baraj denemeleri paylasir.
        if onbellek is not None and (sembol, t) in onbellek:
            return onbellek[(sembol, t)]
        a = _analiz_hesapla(sembol, t, btc)
        if onbellek is not None:
            onbellek[(sembol, t)] = a
        return a

    def _analiz_hesapla(sembol: str, t: int, btc: dict) -> dict:
        fiyat = son_fiyat[sembol]
        s = seri[sembol]
        if "1h" not in s or "4h" not in s:
            return {"gecti": False}
        h1, h4 = s["1h"].pencere(t, MUM_SAYISI, fiyat), s["4h"].pencere(t, MUM_SAYISI, fiyat)
        d1 = s["1d"].pencere(t, MUM_SAYISI, fiyat) if "1d" in s else None
        m15 = m15_seri[sembol].pencere(t, 100, fiyat)
        usd = ("BILINMIYOR", None)
        if sembol in usd_seri:
            u4 = usd_seri[sembol].pencere(t, 100, 0.0)
            if u4:
                usd = (_trend_yonu(u4["kapanis"]), coin_verileri[sembol].get("usd_sembol"))
        return derin_analiz_hesapla(sembol, h1, h4, d1, m15, btc, usd)

    t = bas_ms - bas_ms % ARALIK_MS["15m"]
    while t < bitis_ms:
        t_kapanis = t + ARALIK_MS["15m"]
        for sembol, indeks in idx15.items():
            i = indeks.get(t)
            if i is None:
                continue
            son_fiyat[sembol] = coin_verileri[sembol]["15m"]["kapanis"][i]
            if sembol in acik:
                cikislari_isle(sembol, i, t_kapanis)
        t = t_kapanis
        if t % ARALIK_MS["1h"] != 0:
            continue

        # ---- saat basi: risk kontrolleri ve yeni giris karari ----
        simdi = datetime.fromtimestamp(t / 1000)
        deger = portfoy()
        sayac["toplam_saat"] += 1
        sayac["acik_saat"] += bool(acik)
        zirve = max(zirve, deger)
        en_derin = max(en_derin, (zirve - deger) / zirve if zirve > 0 else 0.0)
        risk.portfoy_guncelle(deger, simdi)
        if risk.zirveden_dusus(deger) >= MAX_DRAWDOWN_PCT:
            for sembol in list(acik):
                sat(sembol, 0, son_fiyat[sembol], "ACIL-TASFIYE", t, True)
            sayac["acil_fren"] = True
            break
        if simdi.hour == 0:
            risk.temizle(simdi)
        engel = risk.yeni_alim_engeli(deger, simdi)
        if engel and engel[0] == "GUNLUK":
            sayac["gunluk_limit_gunleri"].add(simdi.strftime("%Y-%m-%d"))
        son_engel = engel[0] if engel else None
        btc = btc_durumu(t)
        izin, hedef_tutar, _ = dinamik_pozisyon_planla(nakit, deger, None, btc.get("rejim"))
        if engel or izin <= len(acik):
            continue
        adaylar = []
        for sembol in seri:
            if sembol in acik or son_fiyat.get(sembol) is None or risk.coin_engel_bitisi(sembol, simdi):
                continue
            kapanis = son_kapanis.get(sembol)
            if kapanis and t - kapanis[0] < _cooldown_suresi_hesapla(kapanis[1]) * 60_000:
                continue
            a = analiz(sembol, t, btc)
            if (a.get("gecti") and (min_skor is None or a.get("skor", 0.0) >= min_skor)
                    and (ek_filtre is None or ek_filtre(a))):
                adaylar.append(a)
        if not adaylar:
            continue
        a = max(adaylar, key=lambda x: x["skor"])
        sembol, fiyat = a["symbol"], son_fiyat[a["symbol"]]
        tutar = risk_bazli_tutar(deger, giris_stop_pct(fiyat * (1 + BACKTEST_SLIPAJ_PCT), a, None),
                                 min(hedef_tutar, nakit / (1 + KOMISYON_PCT)))
        if tutar <= 0 or tutar > nakit:
            continue
        giris = fiyat * (1 + BACKTEST_SLIPAJ_PCT)
        stop_pct = giris_stop_pct(giris, a, None)
        kom = tutar * KOMISYON_PCT
        nakit -= tutar + kom
        sayac["komisyon"] += kom
        miktar = tutar / giris
        lv = GridLevel(price=giris, has_position=True, buy_qty=miktar, buy_price=giris, en_yuksek_fiyat=giris,
                       risk_birimi=giris * stop_pct, ilk_stop=giris * (1 - stop_pct),
                       atr_giris=a.get("atr_1h") or giris * stop_pct / R_STOP_ATR_KATSAYI)
        acik[sembol] = {"level": lv, "giris_ms": t, "tutar": tutar, "miktar0": miktar, "pnl": -kom,
                        "analiz": giris_analiz_ozeti(a)}

    for sembol in list(acik):
        sat(sembol, 0, son_fiyat[sembol], "TEST-SONU", min(t, bitis_ms), True)
    bitis = nakit
    return {"baslangic": sermaye, "bitis": bitis, "islemler": islemler, "en_derin_dusus": en_derin,
            "sayac": sayac, "son_engel": son_engel}


def backtest_coinlerini_sec(sayi: int) -> list:
    """Son 24 saatte en cok islem goren TRY pariteleri (stabil coinler haric)."""
    req = urllib.request.Request(TICKER_24H_URL, headers={"User-Agent": "project-aurelius-bot"})
    veri = http_istek_yap(req, timeout=20)
    adaylar = []
    for d in veri if isinstance(veri, list) else []:
        sembol = d.get("symbol", "")
        if not sembol.endswith("TRY") or sembol[:-3] in STABIL_COINLER:
            continue
        try:
            adaylar.append((float(d.get("quoteVolume") or 0), sembol))
        except (TypeError, ValueError):
            continue
    return [s for _, s in sorted(adaylar, reverse=True)[:sayi] if _ > 0]


def _backtest_verisini_indir(semboller: list, bas_ms: int, bitis_ms: int) -> tuple:
    coin_verileri, toplam = {}, len(semboller)
    for n, sembol in enumerate(semboller, start=1):
        print(f"  [{n}/{toplam}] {sembol} gecmis mumlari indiriliyor...", flush=True)
        v = {}
        try:
            for aralik in ("15m", "1h", "4h", "1d"):
                v[aralik] = gecmis_mumlari_getir(sembol, aralik, bas_ms - ISINMA_MUM[aralik] * ARALIK_MS[aralik],
                                                 bitis_ms)
        except Exception as e:
            print(f"{YELLOW}    {sembol} atlandi (veri alinamadi: {e}){RESET}")
            continue
        if not v.get("15m") or not v.get("1h") or not v.get("4h"):
            print(f"{YELLOW}    {sembol} atlandi (yeterli gecmis yok){RESET}")
            continue
        usd = sembol[:-3] + "USDT"
        try:
            v["usd4h"] = gecmis_mumlari_getir(usd, "4h", bas_ms - 100 * ARALIK_MS["4h"], bitis_ms)
            v["usd_sembol"] = usd if v["usd4h"] else None
        except Exception:
            v["usd4h"], v["usd_sembol"] = None, None
        coin_verileri[sembol] = v
    btc_verisi = None
    for sembol in BTC_ANALIZ_SEMBOLLERI:
        try:
            btc_verisi = {"sembol": sembol, **{a: gecmis_mumlari_getir(sembol, a, bas_ms - ISINMA_MUM[a] * ARALIK_MS[a],
                                                                       bitis_ms) for a in ("1h", "4h", "1d")}}
            if btc_verisi["1h"] and btc_verisi["4h"]:
                break
        except Exception as e:
            print(f"{YELLOW}  {sembol} verisi alinamadi: {e}{RESET}")
        btc_verisi = None
    return coin_verileri, btc_verisi


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


def _piyasa_kiyasi(coin_verileri: dict, btc_verisi: Optional[dict], bas_ms: int, bitis_ms: int) -> str:
    degisimler = [d for d in (_donem_degisimi(v.get("15m"), bas_ms, bitis_ms) for v in coin_verileri.values())
                  if d is not None]
    btc_degisim = _donem_degisimi((btc_verisi or {}).get("1h"), bas_ms, bitis_ms)
    btc_adi = "BTC (USDT)" if (btc_verisi or {}).get("sembol") == "BTCUSDT" else "BTC (TRY)"
    return (f"test edilen coinler ayni donemde ortalama %{_ortalama(degisimler):+.1f}"
            + (f", {btc_adi} %{btc_degisim:+.1f}" if btc_degisim is not None else ""))


def backtest_raporu_satirlari(sonuc: dict, gun: int, coin_verileri: dict, btc_verisi: Optional[dict],
                              bas_ms: int, bitis_ms: Optional[int] = None) -> list:
    bas, bit = sonuc["baslangic"], sonuc["bitis"]
    s = sonuc["sayac"]
    bitis_ms = bitis_ms or bas_ms + gun * ARALIK_MS["1d"]
    satirlar = [
        f"Donem: {gun} gun ({_tarih(bas_ms)} - {_tarih(bitis_ms)}) | {len(coin_verileri)} coin | "
        f"puan baraji {ANALIZ_MIN_SKOR:.0f}",
        f"Sonuc: {bas:,.2f} -> {bit:,.2f} TRY ({bit - bas:+,.2f} TRY, %{(bit / bas - 1) * 100:+.2f})",
        f"En derin dusus: %{sonuc['en_derin_dusus'] * 100:.1f} | odenen komisyon: {s['komisyon']:,.2f} TRY | "
        f"pozisyonda gecen sure: %{s['acik_saat'] / max(1, s['toplam_saat']) * 100:.0f}",
    ] + islem_ozeti_satirlari(sonuc["islemler"]) + [
        "Kiyas: " + _piyasa_kiyasi(coin_verileri, btc_verisi, bas_ms, bitis_ms),
        f"Risk korumasi: gunluk limit {len(s['gunluk_limit_gunleri'])} gun, kayip molasi {s['mola']} kez, "
        f"coin engeli {s['coin_engeli']} kez" + (" | ACIL FREN devreye girdi, test durdu" if s["acil_fren"] else ""),
    ]
    return satirlar


def _backtest_argumanlari(argumanlar: list) -> tuple:
    sayilar, semboller = [], None
    for a in argumanlar:
        try:
            sayilar.append(float(a.replace(",", ".")))
        except ValueError:
            semboller = [x if x.endswith("TRY") else x + "TRY"
                         for x in (p.strip().upper() for p in a.split(",")) if x]
    gun = int(_aralikta(sayilar[0], *BACKTEST_GUN_ARALIGI)) if sayilar else BACKTEST_VARSAYILAN_GUN
    sermaye = sayilar[1] if len(sayilar) > 1 and sayilar[1] > 0 else BACKTEST_VARSAYILAN_SERMAYE
    geri = int(_aralikta(sayilar[2], 0, BACKTEST_MAKS_GERI_GUN)) if len(sayilar) > 2 else 0
    return gun, sermaye, semboller, geri


def backtest_komutu(argumanlar: list) -> int:
    """'backtest [GUN] [SERMAYE] [GERI] [SEMBOLLER]' - orn. 'backtest 90 1000', 'backtest 60 1000 60'
    (60 gun once biten 60 gunluk donem) veya 'backtest 60 1000 PEPETRY,SOLTRY'."""
    gun, sermaye, semboller, geri = _backtest_argumanlari(argumanlar)
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS v21 - GECMIS VERI TESTI'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    bitis_ms = (int(time.time() * 1000) // ARALIK_MS["1h"] * ARALIK_MS["1h"]) - geri * ARALIK_MS["1d"]
    bas_ms = bitis_ms - gun * ARALIK_MS["1d"]
    print(f"  {_tarih(bas_ms)} - {_tarih(bitis_ms)} ({gun} gun), {sermaye:,.0f} TL sanal sermaye, puan baraji "
          f"{ANALIZ_MIN_SKOR:.0f}. Emir gonderilmez; birkac dakika surebilir.\n")
    try:
        semboller = semboller or backtest_coinlerini_sec(BACKTEST_COIN_SAYISI)
    except Exception as e:
        print(f"{RED}Coin listesi alinamadi: {e}{RESET}")
        return CIKIS_DUR
    coin_verileri, btc_verisi = _backtest_verisini_indir(semboller, bas_ms, bitis_ms)
    if not coin_verileri:
        print(f"{RED}Hicbir coin icin gecmis veri alinamadi (internet / Binance TR erisimini kontrol edin).{RESET}")
        return CIKIS_DUR
    print(f"\n  Simulasyon calisiyor ({len(coin_verileri)} coin x {gun * 24} saat)...", flush=True)
    sonuc = backtest_simule_et(coin_verileri, btc_verisi, bas_ms, bitis_ms, sermaye)
    try:
        if os.path.exists(BACKTEST_ISLEMLERI_CSV):
            os.remove(BACKTEST_ISLEMLERI_CSV)
        for kayit in sonuc["islemler"]:
            islem_gunlugune_yaz(kayit, BACKTEST_ISLEMLERI_CSV)
    except OSError as e:
        print(f"{YELLOW}  Islem listesi yazilamadi: {e}{RESET}")
    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}  SONUC{RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    for satir in backtest_raporu_satirlari(sonuc, gun, coin_verileri, btc_verisi, bas_ms, bitis_ms):
        print(f"  {satir}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{GRAY}  Varsayimlar: komisyon %{KOMISYON_PCT * 100:g} + kayma %{BACKTEST_SLIPAJ_PCT * 100:.3g} (her alim/satim), "
          f"15 dk'lik mumlar;\n  ayni mumda hem stop hem hedef varsa once stop sayildi (temkinli); spread/emir reddi "
          f"simule edilmedi;\n  coinler bugunun en hacimli TRY pariteleri (o donemde listede olmayabilirler).{RESET}")
    print(f"{GRAY}  Islemlerin tamami: {BACKTEST_ISLEMLERI_CSV}{RESET}")
    print(f"{YELLOW}  Gecmis sonuc gelecegi garanti etmez.{RESET}\n")
    return CIKIS_DUR


def karsilastir_komutu(argumanlar: list) -> int:
    """'karsilastir [GUN] [SERMAYE] [SEMBOLLER]': puan barajlarini (55-75) iki ARDISIK donemde
    (onceki GUN gun ve son GUN gun) ayni veriyle karsilastirir. Bir ayar ancak iki donemde de
    iyiyse anlamlidir - tek donemde iyi gorunen ayar sans eseri olabilir."""
    global ANALIZ_MIN_SKOR
    gun, sermaye, semboller, _ = _backtest_argumanlari(argumanlar)
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS v21 - PUAN BARAJI KARSILASTIRMASI'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    son_ms = int(time.time() * 1000) // ARALIK_MS["1h"] * ARALIK_MS["1h"]
    orta_ms = son_ms - gun * ARALIK_MS["1d"]
    ilk_ms = orta_ms - gun * ARALIK_MS["1d"]
    donemler = [("Onceki donem", ilk_ms, orta_ms), ("Son donem", orta_ms, son_ms)]
    print(f"  Onceki donem: {_tarih(ilk_ms)} - {_tarih(orta_ms)} | Son donem: {_tarih(orta_ms)} - {_tarih(son_ms)}")
    print(f"  {sermaye:,.0f} TL sanal sermaye, barajlar: {', '.join(map(str, KARSILASTIRMA_BARAJLARI))}. "
          f"Emir gonderilmez; 5-10 dakika surebilir.\n")
    try:
        semboller = semboller or backtest_coinlerini_sec(BACKTEST_COIN_SAYISI)
    except Exception as e:
        print(f"{RED}Coin listesi alinamadi: {e}{RESET}")
        return CIKIS_DUR
    coin_verileri, btc_verisi = _backtest_verisini_indir(semboller, ilk_ms, son_ms)
    if not coin_verileri:
        print(f"{RED}Hicbir coin icin gecmis veri alinamadi (internet / Binance TR erisimini kontrol edin).{RESET}")
        return CIKIS_DUR
    eski_baraj = ANALIZ_MIN_SKOR
    ANALIZ_MIN_SKOR = 0.0  # analiz bir kez yapilir, baraj simulasyonda uygulanir
    sonuclar: dict = {}
    try:
        for ad, bas_ms, bitis_ms in donemler:
            onbellek: dict = {}
            for baraj in KARSILASTIRMA_BARAJLARI:
                print(f"  {ad}, baraj {baraj} hesaplaniyor...", flush=True)
                sonuclar[(ad, baraj)] = backtest_simule_et(coin_verileri, btc_verisi, bas_ms, bitis_ms, sermaye,
                                                           min_skor=baraj, onbellek=onbellek)
    finally:
        ANALIZ_MIN_SKOR = eski_baraj
    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}  SONUC ({len(coin_verileri)} coin, her donem {gun} gun){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    for satir in karsilastirma_satirlari(sonuclar, donemler, coin_verileri, btc_verisi):
        print(f"  {satir}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{GRAY}  R/islem: islem basina ortalama sonuc (1R = stop olursa kaybedilen tutar). Bir baraj ancak IKI\n"
          f"  donemde de artidaysa guvenilir; tek donemde iyi olan sans eseri olabilir.{RESET}")
    print(f"{YELLOW}  Gecmis sonuc gelecegi garanti etmez.{RESET}\n")
    return CIKIS_DUR


def karsilastirma_satirlari(sonuclar: dict, donemler: list, coin_verileri: dict,
                            btc_verisi: Optional[dict]) -> list:
    satirlar = []
    for ad, bas_ms, bitis_ms in donemler:
        satirlar.append(f"{ad} ({_tarih(bas_ms)} - {_tarih(bitis_ms)}): "
                        + _piyasa_kiyasi(coin_verileri, btc_verisi, bas_ms, bitis_ms))
    satirlar.append("")
    baslik = "Baraj | " + " | ".join(f"{ad:<34}" for ad, _, _ in donemler)
    satirlar += [baslik, "      | " + " | ".join(f"{'islem kazanan R/islem    net TL':<34}" for _ in donemler)]
    for baraj in KARSILASTIRMA_BARAJLARI:
        hucreler = []
        for ad, _, _ in donemler:
            s = sonuclar[(ad, baraj)]
            isl = s["islemler"]
            kazanan = sum(1 for k in isl if k["net_kar_try"] > 0)
            rler = [k["r_sonucu"] for k in isl if k.get("r_sonucu") is not None]
            hucreler.append(f"{len(isl):>5} {(kazanan / len(isl) * 100 if isl else 0):>6.0f}% "
                            f"{_ortalama(rler):>+8.2f} {s['bitis'] - s['baslangic']:>+10.2f}")
        satirlar.append(f"{baraj:>5} | " + " | ".join(f"{h:<34}" for h in hucreler))
    return satirlar


# Strateji karsilastirmasi: ayni veriyle, ARDISIK uc donemde farkli kurallar. Bir degisiklik ancak
# her donemde iyilestiriyorsa anlamlidir (tek donemde iyi gorunen sans eseri olabilir).
def _asiri_oynak_degil(a: dict) -> bool:
    """1.5 x ATR(1s) stop'u izin verilen en genis stop'u asiyorsa coin bu stop araligina gore fazla oynak:
    stop %6'ya sikistirilinca normal dalgalanmayla tetikleniyor."""
    return bool(a.get("fiyat")) and (a.get("atr_1h") or 0.0) * R_STOP_ATR_KATSAYI / a["fiyat"] <= R_STOP_MAKS_PCT


STRATEJI_VARYANTLARI = [
    # (ad, gecici ayarlar, ek giris filtresi)
    ("Mevcut (v20)", {}, None),
    ("Asiri oynak coin yok", {}, _asiri_oynak_degil),
    ("Genis stop (2.5xATR, en fazla %10)", {"R_STOP_ATR_KATSAYI": 2.5, "R_STOP_MAKS_PCT": 0.10}, None),
    ("Oynak yok + RSI>=50 + hacim>=0.8", {},
     lambda a: _asiri_oynak_degil(a) and (a.get("rsi_1h") or 0) >= 50 and (a.get("goreceli_hacim") or 0) >= 0.8),
    ("Oynak yok + BTC zayifken girme", {}, lambda a: _asiri_oynak_degil(a) and a.get("btc_rejim") != "ZAYIF"),
]


def strateji_karsilastir(coin_verileri: dict, btc_verisi: Optional[dict], donemler: list, sermaye: float,
                         ilerleme: bool = True) -> dict:
    """{(varyant_adi, donem_adi): simulasyon sonucu}. Ayarlar her varyanttan sonra geri yuklenir."""
    sonuclar: dict = {}
    for ad, ayarlar, filtre in STRATEJI_VARYANTLARI:
        eski = {k: globals()[k] for k in ayarlar}
        globals().update(ayarlar)
        try:
            for donem_adi, bas_ms, bitis_ms in donemler:
                if ilerleme:
                    print(f"  {ad} - {donem_adi} hesaplaniyor...", flush=True)
                # analiz sonucu sadece ayarlara bagli: ayni ayarli varyantlar onbellegi paylasir
                anahtar = (tuple(sorted(ayarlar.items())), donem_adi)
                onbellek = _strateji_onbellegi.setdefault(anahtar, {})
                sonuclar[(ad, donem_adi)] = backtest_simule_et(coin_verileri, btc_verisi, bas_ms, bitis_ms, sermaye,
                                                               onbellek=onbellek, ek_filtre=filtre)
        finally:
            globals().update(eski)
    _strateji_onbellegi.clear()
    return sonuclar


_strateji_onbellegi: dict = {}


def _sonuc_hucresi(s: dict) -> tuple:
    isl = s["islemler"]
    rler = [k["r_sonucu"] for k in isl if k.get("r_sonucu") is not None]
    return len(isl), _ortalama(rler), s["bitis"] - s["baslangic"]


def strateji_satirlari(sonuclar: dict, donemler: list, coin_verileri: dict, btc_verisi: Optional[dict],
                       varyant_adlari: Optional[list] = None, kiyas=None) -> list:
    kiyas = kiyas or (lambda b, e: _piyasa_kiyasi(coin_verileri, btc_verisi, b, e))
    satirlar = [f"{ad} ({_tarih(b)} - {_tarih(e)}): " + kiyas(b, e) for ad, b, e in donemler]
    satirlar.append("")
    genislik = 36
    satirlar.append(f"{'Strateji':<{genislik}}| " + " | ".join(f"{ad:<22}" for ad, _, _ in donemler) + " | TOPLAM")
    satirlar.append(f"{'':<{genislik}}| " + " | ".join(f"{'islem R/islem  net TL':<22}" for _ in donemler)
                    + " | R/islem  net TL")
    for ad in (varyant_adlari or [v[0] for v in STRATEJI_VARYANTLARI]):
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


def strateji_komutu(argumanlar: list) -> int:
    """'strateji [GUN] [SERMAYE] [SEMBOLLER]': STRATEJI_VARYANTLARI'ni ardisik uc donemde (her biri GUN gun,
    varsayilan 60 -> son 180 gun) ayni veriyle karsilastirir."""
    gun, sermaye, semboller, _ = _backtest_argumanlari(argumanlar)
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS v21 - STRATEJI KARSILASTIRMASI'.center(74)}{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 74}{RESET}")
    son_ms = int(time.time() * 1000) // ARALIK_MS["1h"] * ARALIK_MS["1h"]
    sinirlar = [son_ms - k * gun * ARALIK_MS["1d"] for k in (3, 2, 1, 0)]
    donemler = [(f"{i}. donem", sinirlar[i - 1], sinirlar[i]) for i in (1, 2, 3)]
    print(f"  {_tarih(sinirlar[0])} - {_tarih(son_ms)}: uc donem, her biri {gun} gun, {sermaye:,.0f} TL sanal sermaye.")
    print(f"  {len(STRATEJI_VARYANTLARI)} strateji denenecek. Emir gonderilmez; 10-20 dakika surebilir.\n")
    try:
        semboller = semboller or backtest_coinlerini_sec(BACKTEST_COIN_SAYISI)
    except Exception as e:
        print(f"{RED}Coin listesi alinamadi: {e}{RESET}")
        return CIKIS_DUR
    coin_verileri, btc_verisi = _backtest_verisini_indir(semboller, sinirlar[0], son_ms)
    if not coin_verileri:
        print(f"{RED}Hicbir coin icin gecmis veri alinamadi (internet / Binance TR erisimini kontrol edin).{RESET}")
        return CIKIS_DUR
    print()
    sonuclar = strateji_karsilastir(coin_verileri, btc_verisi, donemler, sermaye)
    print(f"\n{CYAN}{'-' * 74}{RESET}")
    print(f"{BOLD}  SONUC ({len(coin_verileri)} coin, puan baraji {ANALIZ_MIN_SKOR:.0f}){RESET}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    for satir in strateji_satirlari(sonuclar, donemler, coin_verileri, btc_verisi):
        print(f"  {satir}")
    print(f"{CYAN}{'-' * 74}{RESET}")
    print(f"{GRAY}  R/islem: islem basina ortalama sonuc (1R = stop olursa kaybedilen tutar). Bir strateji ancak UC\n"
          f"  donemde de artidaysa umut verir; yine de once kucuk tutarla denenmelidir.{RESET}")
    print(f"{YELLOW}  Gecmis sonuc gelecegi garanti etmez.{RESET}\n")
    return CIKIS_DUR


# ==========================================================================
# v20 BOLUM 4: GUNLUK TREND TAKIBI (test). Az sayida buyuk coin; gunluk kapanis son N gunun zirvesini
# kirinca ve fiyat EMA50 ustundeyken girilir; stop 2 x ATR, fiyat yukseldikce zirve - 3 x ATR'ye cekilir.
# Kismi kar alma yok (kazananlar kosar), islem az oldugu icin komisyon/kayma payi kucuk.
# ==========================================================================
TREND_COINLERI = ("BTCTRY", "ETHTRY", "BNBTRY", "SOLTRY", "XRPTRY", "ADATRY", "AVAXTRY", "DOGETRY",
                  "LINKTRY", "DOTTRY", "TRXTRY", "LTCTRY")
TREND_MAKS_POZISYON = 4
TREND_ILK_STOP_ATR = 2.0
TREND_TAKIP_ATR = 3.0
TREND_EMA = 50
TREND_ATR_PERIYOT = 20
TREND_VARYANTLARI = [
    # (ad, kirilim gunu, BTC filtresi, coinler (None = hepsi))
    ("20 gun kirilim + BTC filtresi", 20, True, None),
    ("50 gun kirilim + BTC filtresi", 50, True, None),
    ("20 gun kirilim, BTC filtresi yok", 20, False, None),
    ("20 gun kirilim, sadece BTC + ETH", 20, True, ("BTCTRY", "ETHTRY")),
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
# v21: GUNLUK TREND TAKIBI - CANLI / SIMULASYON CALISMA (AURELIUS_STRATEJI=TREND, varsayilan)
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
        print(f"[{ts()}] {YELLOW}Trend kontrolu: gunluk mumlar alinamadi, sonraki turda tekrar denenecek.{RESET}")
        return False
    btc_yukari = None
    try:
        btc = _gunluk_mumlar("BTCUSDT", bugun, gerekli) or gunluk.get("BTCTRY")
        if btc:
            ema_btc = _ema_hizali(btc["kapanis"], TREND_EMA)[-1]
            btc_yukari = ema_btc is not None and btc["kapanis"][-1] > ema_btc
    except Exception as e:
        logger.warning("Trend: BTC gunluk verisi alinamadi: %s", e)
    satirlar = []

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
                bot = pozisyonlar[s] = CoinBot(symbol=s, coin_name=_coin_adi(s), width_pct=VARSAYILAN_WIDTH_PCT,
                                               grid_count=VARSAYILAN_GRID_SAYISI, starting_try=0.0)
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
    return True


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
        bot.stop_loss_kontrol(fiyat, sim=False, kasa=kasa, acik_pozisyon_sayaci=acik_pozisyon_sayaci,
                              durum_kaydet=kaydet, rapor=rapor)
        bot.borsa_stop_bakimi(kasa, acik_pozisyon_sayaci, rapor, kaydet)
        time.sleep(API_CALL_SLEEP_SECONDS)


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
    print(f"{BOLD}{CYAN}{'PROJECT AURELIUS v21 - GUNLUK TREND TAKIBI TESTI'.center(74)}{RESET}")
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
    for satir in strateji_satirlari(sonuclar, donemler, {}, None, [v[0] for v in TREND_VARYANTLARI],
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


def analiz_komutu(sembol: Optional[str]) -> int:
    """'python project_aurelius_bot_v21.py analiz [SEMBOL]': botun bir coini nasil
    degerlendirdigini gosterir (emir gondermez, anahtar gerektirmez)."""
    print(f"{BOLD}DETAYLI ANALIZ{RESET}")
    btc = btc_rejim_analizi(zorla=True)
    for satir in btc_raporu_satirlari(btc):
        print(f"  {satir}")
    if sembol:
        print()
        for satir in analiz_raporu_satirlari(coin_derin_analiz(sembol, btc)):
            print(f"  {satir}")
    else:
        print(f"\n  Bir coini incelemek icin: python {os.path.basename(__file__)} analiz PEPETRY")
    return CIKIS_DUR


def main():
    komut = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    try:
        if komut == "backtest":
            kod = backtest_komutu(sys.argv[2:])
        elif komut == "rapor":
            kod = rapor_komutu()
        elif komut == "karsilastir":
            kod = karsilastir_komutu(sys.argv[2:])
        elif komut == "strateji":
            kod = strateji_komutu(sys.argv[2:])
        elif komut == "trend":
            kod = trend_komutu(sys.argv[2:])
        elif komut == "baglanti":
            baglanti_testi()
            kod = CIKIS_DUR
        elif komut == "analiz":
            kod = analiz_komutu(sys.argv[2].upper() if len(sys.argv) > 2 else None)
        elif komut == "kurulum":
            kod = baslatici_olustur()
        else:
            kod = run_simulation()
    except KeyboardInterrupt:
        kod = CIKIS_DUR  # baslangic sirasinda Ctrl+C: baslatici yeniden baslatmasin
    # v18: cikis kodu baslaticiya (baslat.bat/.sh) yeniden baslatip baslatmayacagini soyler
    sys.exit(kod if isinstance(kod, int) else CIKIS_DUR)


if __name__ == "__main__":
    main()
