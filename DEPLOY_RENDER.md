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
