# Matchi-avbokningsbot

Bevakar utvalda anläggningar på [matchi.se](https://www.matchi.se) och skickar ett Telegram-meddelande när en tid blir ledig (t.ex. vid avbokning). Körs gratis på GitHub Actions var 10:e minut.

## Så funkar det
1. Hämtar lediga tider via Matchis `/book/listSlots` för varje anläggning i `config.yaml`, `days_ahead` dagar framåt.
2. Filtrerar på veckodagar och tidsfönster.
3. Jämför med `state.json` från förra körningen. Tider som är nya sedan dess skickas till Telegram med en direkt bokningslänk.
4. Sparar ny `state.json` (workflowen committar den tillbaka till repot).

Första körningen, och varje ny dag som kommer in i fönstret, räknas som baslinje och ger inga notiser.

## Setup
1. **Skapa en Telegram-bot:** skriv till [@BotFather](https://t.me/BotFather), kör `/newbot` och spara token.
2. **Hämta ditt chat_id:** skicka valfritt meddelande till din nya bot och öppna `https://api.telegram.org/bot<TOKEN>/getUpdates`. Värdet finns under `message.chat.id`.
3. **Redigera `config.yaml`** med dina anläggningar (slug från URL:en, sport-id från `&sport=` på anläggningssidan; padel = 5).
4. **Skapa ett GitHub-repo och pusha.** Gör repot **publikt**: privata repon har bara 2000 gratis Actions-minuter per månad, vilket inte räcker för en körning var 10:e minut. (Vill du ha det privat, sätt cron till `*/30`.)
5. **Lägg in secrets** under *Settings → Secrets and variables → Actions*: `TELEGRAM_BOT_TOKEN` och `TELEGRAM_CHAT_ID`.
6. **Kör workflowen manuellt** en gång (*Actions → Check Matchi → Run workflow*) för att skapa baslinjen.

Obs: GitHub kan försena schemalagda körningar med några minuter, och schemat pausas automatiskt i repon utan aktivitet på 60 dagar.

## Lokalt
```sh
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt   # Windows
.venv/Scripts/python -m pytest
PYTHONPATH=src .venv/Scripts/python -m matchi_bot    # utan token skrivs meddelandet bara ut
```

## Hänsyn
Matchis `robots.txt` avråder från automatiska anrop mot bokningssidorna. Boten är gjord för eget bruk: få anläggningar, låg frekvens, 1 s paus mellan anrop, tydlig User-Agent och ingen automatisk bokning. Höj inte frekvensen kraftigt.
