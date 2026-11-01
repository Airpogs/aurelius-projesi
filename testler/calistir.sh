#!/usr/bin/env bash
# Aurelius v22 testleri. Bot dosyasini gecici bir klasore 'bot.py' olarak kopyalayip calistirir.
# Borsaya emir gondermez, internet gerektirmez (borsa yanitlari taklit edilir).
set -e
BURASI="$(cd "$(dirname "$0")" && pwd)"
D="$(mktemp -d)"
cp "$BURASI/../project_aurelius_bot_v22.py" "$D/bot.py"
cp "$BURASI/v22_test.py" "$BURASI/canli_baslangic_test.py" "$D/"
cd "$D"
env -u AURELIUS_CANLI_MOD -u TELEGRAM_BOT_TOKEN python3 v22_test.py > sonuc.txt 2>&1 || true
grep -E '^(GECTI|KALDI)' sonuc.txt
tail -1 sonuc.txt
env -u TELEGRAM_BOT_TOKEN python3 canli_baslangic_test.py 2>&1 | tail -1
rm -rf "$D"
