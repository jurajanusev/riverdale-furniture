# Riverdale Product Finder

Lokálna aplikácia na vyhľadávanie, triedenie a schvaľovanie zariadenia pre projekt Riverdale. Používateľ vyberá **set → miestnosť/zónu → kategóriu → typ položky** a ku každému vyhľadávaniu môže zadať maximálnu cenu, farbu a materiál. Pôvodné postele zostávajú zaradené v **Dom Betty → spálňa / izba → Nábytok → posteľ**.

Set a miestnosť sú iba cieľové zaradenie schválených produktov. Neaplikujú štýlové skóre, nemenia ponuku obchodov a nefiltrujú výsledky podľa estetiky priestoru.

## Inštalácia vo Windows

Vyžaduje Python 3.10 alebo novší. V PowerShelli:

```powershell
cd riverdale-furniture
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Otvorte `http://localhost:5000`. Databáza vznikne automaticky v `data/riverdale.db`.

## Súkromný prístup odkiaľkoľvek

Pre túto aplikáciu je odporúčané ponechať ju na Windows PC, aby fungovala lokálna SQLite databáza aj ručné CAPTCHA overenie v Google Chrome, a sprístupniť ju iba vlastným zariadeniam cez Tailscale Serve.

1. Nainštalujte [Tailscale pre Windows](https://tailscale.com/download/windows) a prihláste tento počítač.
2. Nainštalujte Tailscale rovnakým účtom aj v mobile alebo notebooku.
3. Aktualizujte Python balíky: `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
4. V PowerShelli v priečinku projektu spustite `powershell -ExecutionPolicy Bypass -File .\start_remote.ps1`.
5. Skript vypíše súkromnú HTTPS adresu `https://...ts.net`, ktorá funguje iba pre povolené zariadenia v rovnakom Tailscale účte.

Skript používa Waitress na `127.0.0.1:5000` a Tailscale Serve ako súkromnú HTTPS proxy. Konfigurácia Serve beží na pozadí aj po zatvorení terminálu. Počítač musí zostať zapnutý. Zdieľanie vypnete cez `powershell -ExecutionPolicy Bypass -File .\stop_remote.ps1`.

## Používanie

- Výber obsahuje 14 Riverdale setov, ich miestnosti a 12 hlavných kategórií z projektových podkladov.
- Tlačidlo **Priestory** otvorí menu všetkých setov a miestností. Preklik zachová aktuálnu kategóriu a typ položky.
- **Vyhľadať produkty** spustí šetrné paralelné načítanie podporovaných obchodov. IKEA a JYSK používajú pri kobercoch a komodách priamo verejné kategórie; pri ďalších typoch používajú vyhľadávanie. ASKO, FAVI a Bonami majú vlastné kategórie alebo verejné vyhľadávanie. Pre rakúske obchody sa bežné typy automaticky prekladajú do nemčiny.
- Vyhľadávacie kritériá kopírujú spoločné filtre cieľových obchodov, ktoré aplikácia vie overiť z produktových údajov: minimálna a maximálna cena, dostupnosť, farba, materiál a pri rozmerových kategóriách šírka, hĺbka a výška. Pri posteliach možno zvoliť rozmer lôžka a požadovať rošt alebo matrac v cene či bez nich. Prázdne hodnoty výsledky neobmedzujú.
- Möbelix, XXXLutz, Mömax a Sconto majú pripravené kategórie a vyhľadávacie URL, ale ich ochrana môže automatické načítanie zastaviť CAPTCHA. Panel **Ručne overiť blokovaný obchod** otvorí bežný nainštalovaný Google Chrome s oddeleným trvalým profilom. Po vyriešení CAPTCHA nechajte okno otvorené: pomocník sa pripojí k tej istej živej karte, uloží katalóg a najviac 18 produktových stránok do šesťhodinovej lokálnej cache a okno zavrie automaticky. Až potom spustite vyhľadávanie. Profily a cache zostávajú iba v priečinkoch `data/browser_profiles` a `data/browser_cache`.
- Na Renderi sa viditeľné CAPTCHA okno nedá otvoriť. Spustite preto na Windows počítači `start_collector.ps1`, v otvorenej lokálnej aplikácii vykonajte ručné overenie a zberač odošle získané produkty do cloudovej aplikácie cez chránené API.
- **Pridať produkt manuálne** je určené pre blokované stránky alebo typy bez automatického adaptéra. Povinné sú názov, povolený obchod, cena a priamy URL produktu. Možno vložiť URL fotografie alebo nahrať JPG/PNG/WebP (max. 8 MB).
- Tlačidlá **Schváliť do výberu**, **Možno** a **Vyradiť** ukladajú stav bez obnovy stránky. Schválený produkt sa automaticky zobrazí vo **Výbere miestnosti**, kde sú spolu položky zo všetkých kategórií (napríklad stôl, posteľ aj koberec). Odtiaľ ho možno aj odobrať. Poznámka sa uloží po opustení poľa alebo spolu so zmenou stavu.
- Vo **Výbere miestnosti** možno vytvoriť 30-dňový odkaz pre architekta. Tokenový odkaz zobrazuje iba schválené produkty danej miestnosti; architekt pri nich označí „Páči sa mi“ a jeho voľby sa zobrazia v internom výbere. Každý odkaz možno samostatne zrušiť.
- **Aktualizovať ceny** znovu skontroluje automaticky získané produkty v podporovaných MVP obchodoch. Manuálne produkty sa nemenia automaticky, ak ich obchod nemá adaptér.
- Každý produkt si uchováva set, miestnosť, hlavnú kategóriu a typ položky. Filtre ďalej fungujú pre obchod, krajinu, cenu, farbu, materiál, dostupnosť a stav.

## Export

Menu **Exportovať** exportuje iba schválené produkty:

- Excel `.xlsx` s formátovanou hlavičkou, filtrom, zmrazeným riadkom a URL fotografie,
- UTF-8 CSV pre Google Sheets so všetkými textovými údajmi,
- CSV so stĺpcami pre Canva Bulk Create.

Ak nie je schválený žiadny produkt, export obsahuje iba hlavičku. Excel používa URL fotografie (nevkladá vzdialený obrázok do súboru), aby export nevyžadoval ďalšie sťahovanie z obchodov.

## Testy

```powershell
python -m unittest discover -s tests -v
```

Testy používajú dočasnú SQLite databázu a neposielajú požiadavky na e-shopy.

## Najčastejšie problémy

- **Obchod vráti 0 produktov:** stránka mohla zmeniť HTML, vyžadovať JavaScript, blokovať automatický prístup alebo aktuálne nemá bezpečne overiteľnú zhodu. Pri HTTP 403 aplikácia skúsi obyčajný Chromium cez Playwright a prípadnú uloženú manuálne overenú reláciu. Nepoužíva stealth techniky ani automatické riešenie CAPTCHA. Ak ručné overenie obchod neprijme, použite produktový feed/API alebo manuálny formulár. Ostatné adaptéry pokračujú aj pri chybe jedného obchodu.
- **Fotografia z URL sa nezobrazuje:** obchod môže blokovať vloženie obrázka na inú doménu. Nahrajte fotografiu cez manuálny formulár, ak na to máte oprávnenie.
- **Port 5000 je obsadený:** ukončite druhú aplikáciu používajúcu port alebo dočasne zmeňte `port=5000` na konci `app.py`.
- **PowerShell blokuje aktiváciu prostredia:** použite `Set-ExecutionPolicy -Scope Process Bypass`, potom znova aktivujte `.venv`.
- **Diakritika v CSV:** importujte súbor ako UTF-8. Export obsahuje UTF-8 BOM pre Excel a Google Sheets.

## Štruktúra

`app.py` obsahuje webové routy a exporty, `database.py` SQLite operácie, `models.py` jednotný dátový model, `scrapers/` samostatné adaptéry, `templates/` HTML, `static/` CSS/JS a nahraté obrázky, `exports/` a `data/` lokálne výstupy.
