# Nasadenie Riverdale 24/7 na Render

Projekt obsahuje `render.yaml` pre platenú webovú službu v regióne Frankfurt
s 1 GB trvalým diskom. Disk uchová SQLite databázu, nahrané fotografie aj
exporty pri reštarte alebo novom nasadení.

1. Nahrajte projekt do súkromného GitHub repozitára.
2. Na Renderi zvoľte **New → Blueprint** a pripojte repozitár.
3. Pri vytváraní nastavte tajnú premennú `RIVERDALE_ADMIN_PASSWORD` na vlastné
   silné heslo. `RIVERDALE_SECRET` sa vygeneruje automaticky.
4. Po nasadení dostanete verejnú HTTPS adresu `*.onrender.com`.

Správa aplikácie je v cloude chránená heslom. Odkazy `/architect/<token>`
ostávajú architektovi dostupné bez hesla; sú náhodné, časovo obmedzené a
odvolateľné.

Render nedokáže otvoriť lokálny Google Chrome na ručné potvrdenie CAPTCHA.
Obchody bez CAPTCHA je možné vyhľadávať priamo v cloude. Blokované obchody treba
overiť lokálne alebo neskôr doplniť synchronizáciu lokálneho zberača s cloudom.

## Lokálny CAPTCHA zberač

Na Windows spustite `start_collector.ps1`. Skript si bezpečne vypýta heslo
cloudovej Riverdale aplikácie iba pre aktuálne spustenie, otvorí lokálnu aplikáciu
na `http://127.0.0.1:5000` a heslo nezapíše do konfiguračného súboru.

V lokálnej aplikácii vyberte priestor, miestnosť, kategóriu a typ produktu. V
paneli ručného overenia kliknite na blokovaný obchod a dokončite CAPTCHA v
otvorenom Chrome. Pomocník uloží produktové stránky, spracuje ich a cez HTTPS
odošle maximálne 18 výsledkov do cloudovej aplikácie. Stav pri obchode zobrazí
počet nájdených a synchronizovaných produktov.

Spustenie:

```powershell
powershell -ExecutionPolicy Bypass -File .\start_collector.ps1
```
