# Matchi-avbokningsbot

Bevakar utvalda anläggningar på [matchi.se](https://www.matchi.se) och skickar ett Telegram-meddelande när en tid blir ledig (t.ex. vid avbokning). Körs var 10:e minut via Windows Aktivitetsschemaläggaren.

> GitHub Actions fungerar inte: Matchi svarar `403 Forbidden` på anrop från datacenter-IP:er. Boten måste köras från ett vanligt hemnät.

## Så funkar det
1. Hämtar lediga tider via Matchis `/book/listSlots` för varje anläggning i `config.yaml`, `days_ahead` dagar framåt.
2. Filtrerar på tidsfönster (veckodagar + tider; en tid måste ligga helt inom fönstret).
3. Jämför med `state.json` från förra körningen. Nya lediga tider skickas till Telegram med bokningslänk.
4. Sparar ny `state.json` lokalt.

Första körningen, och varje ny dag som kommer in i fönstret, räknas som baslinje och ger inga notiser. Vid fel (t.ex. om Matchi ändrar sin HTML) skickas en varning max en gång per dygn.

## Setup
1. **Telegram-bot:** skriv `/newbot` till [@BotFather](https://t.me/BotFather) och spara token. Skicka sedan ett meddelande till boten och hämta ditt chat_id från `https://api.telegram.org/bot<TOKEN>/getUpdates` (`message.chat.id`).
2. **`.env`** i projektroten (ignoreras av git):
   ```
   TELEGRAM_BOT_TOKEN=...
   TELEGRAM_CHAT_ID=...
   ```
3. **`config.yaml`:** anläggningar (slug från URL:en), sport-id (`&sport=` på anläggningssidan; tennis = 1, padel = 5) och tidsfönster.
4. **Installera:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\pip install -r requirements-dev.txt
   .venv\Scripts\python run.py        # testkörning, skriver till konsolen
   ```
5. **Schemalägg** (PowerShell):
   ```powershell
   $root = (Get-Location).Path
   $action = New-ScheduledTaskAction -Execute "$root\.venv\Scripts\pythonw.exe" -Argument "`"$root\run.py`"" -WorkingDirectory $root
   $trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 10)
   $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 8)
   Register-ScheduledTask -TaskName "Matchi-bot" -Action $action -Trigger $trigger -Settings $settings
   ```
   Boten körs bara när datorn är på och inte sover.

## Drift
- Logg: `logs/bot.log`
- Pausa / starta: `Disable-ScheduledTask Matchi-bot` / `Enable-ScheduledTask Matchi-bot`
- Ta bort: `Unregister-ScheduledTask Matchi-bot`
- Tester: `.venv\Scripts\python -m pytest`

## Hänsyn
Matchis `robots.txt` avråder från automatiska anrop mot bokningssidorna. Boten är gjord för eget bruk: få anläggningar, låg frekvens, 1 s paus mellan anrop, tydlig User-Agent och ingen automatisk bokning. Höj inte frekvensen kraftigt.
