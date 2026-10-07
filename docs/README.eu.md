# Mensagia Attachment Mailer

[Mensagiaren API](https://api.mensagia.com/docs/v1) erabiliz, kontaktu bakoitzari eranskin pertsonalizatuekin mezu elektronikoak bidaltzeko aplikazioa.

> Bertsioak: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [English](README.en.md)

---

## Eskakizunak

- Windows 10/11 (exekutagarria erabiltzeko)
- Edo Python 3.11+ (iturburu-kodea erabiltzeko)

---

## Exekutagarriaren erabilera (Pythonik gabeko bezeroak)

1. Deskargatu exekutagarria [releases orritik](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) (GUI modurako `mensagia-mailer-gui.exe`, edo kontsola modurako `mensagia-mailer-console.exe`)
2. Sortu `.env` fitxategi bat `.exe`-aren **karpeta berean**, zure tokenarekin:

```
MENSAGIA_API_TOKEN=zure_api_tokena_hemen
```

> Zure API tokena [mensagia.com](https://mensagia.com) → Erabiltzaileak atalean lor dezakezu.
> `.env` fitxategia ez badago, aplikazioak tokena eskatuko dizu abiatzean.

3. Exekutatu `.exe`.

> **Windows SmartScreen oharra:** fitxategia lehen aldiz exekutatzen duzunean, Windowsek segurtasun abisua erakuts dezake. Egin klik **"Informazio gehiago"** eta gero **"Exekutatu hala ere"** aukeretan. Deskargatutako bertsio bakoitzeko behin bakarrik egin behar da.

---

## Iturburu-kodetik erabiltzea

### Instalazioa

```bash
# Biltegia klonatu
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Ingurune birtuala sortu (ez badago)
python -m venv .venv

# Ingurunea aktibatu
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Mendekotasunak instalatu
pip install -r requirements.txt
```

### API tokena konfiguratu

Sortu `.env` fitxategi bat proiektuaren erroan (`.env.example`-ren kopia):

```
MENSAGIA_API_TOKEN=zure_api_tokena_hemen
```

### Modu grafikoan exekutatu

```bash
python main_gui.py
```

### Kontsola moduan exekutatu

```bash
python main.py
```

---

## Bidaltzeko fluxua

1. **API tokena** — `.env`-tik irakurtzen da edo erabiltzaileari eskatzen zaio.
2. **Gaia** — Erabiltzaileak mezu elektronikoaren gaia sartzen du.
3. **Txantiloia** — Eskuragarri dauden email txantiloien zerrenda erakusten da.
4. **Bidaltzailea** — Egiaztatutako bidaltzaile helbideen zerrenda erakusten da.
5. **Taldea** — Agenda-taldeen lehen orria erakusten da. Bilatzen ari zaren taldea agertzen ez bada, izenaren arabera iragaz daiteke. Kontakturik gabeko taldeak erakusten dira, baina ezin dira hautatu.
6. **Eranskin eremua** — Eranskinaren URLa duen eremu pertsonalizatua aukeratzen da.
7. **Ziurtagiria** — Erabiltzaileak bidalketak ziurtatzea erabakitzen du.
8. **Bidalketa** — Email eta eranskin URL balioduna duten kontaktuak iragazten dira, eta minutuko 5eko abiaduran mezu bat bidaltzen da bakoitzari.

---

## Eranskinaren bidea eremu pertsonalizatuan

6. urratsean aukeratutako eremu pertsonalizatuak kontaktu bakoitzaren eranskina bi modutan adieraz dezake:

- **URL osoa**, `http://` edo `https://`-rekin hasten dena (adibidez, `https://cdn.empresa.com/docs/factura_42.pdf`). Dagoen bezala erabiltzen da.
- **Fitxategi-izena edo bide erlatiboa** (adibidez, `factura_42.pdf` edo `2026/factura_42.pdf`). Aplikazioak **oinarrizko URL** bat jartzen dio aurretik: `https://cdn.empresa.com/docs/` oinarriarekin, `factura_42.pdf` balioa `https://cdn.empresa.com/docs/factura_42.pdf` bihurtzen da.

Bi moduak talde berean konbina daitezke.

Oinarrizko URLa hainbat modutan adieraz daiteke:

- `.env` fitxategian, `MENSAGIA_ATTACHMENT_BASE_URL` aldagaiarekin:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- **GUI moduan**, lehen pantailako **Eranskinaren oinarrizko URLa** eremuan. `.env`-n definituta badago, beteta agertzen da.
- **Kontsola moduan**, aplikazioak kontaktuen batek bide erlatiboa badu eta aldagaia `.env`-n ez badago bakarrik eskatzen du.

> Oinarrizko URLak beti **web helbide publiko** bat izan behar du, inoiz ez ordenagailuko karpeta bat: Mensagiak deskargatzen du fitxategia mezuari eransteko. `/`-rekin amai daiteke edo ez; aplikazioak kontuan hartzen du.

---

## ⚠ Oharra taldeko kontaktuei buruz

Taldea **kontaktu-iturri** gisa erabiltzen da, ez harpidetza-zerrenda gisa. Aplikazioak **taldeko kontaktu guztiei** bidaliko die mezua, agenda horretan harpideduta dauden ala ez.

> Mensagiaren APIak ez du kontaktu bakoitzaren harpidetza-egoerari buruzko informaziorik ematen agenda batean. Harpidetutako kontaktuetara soilik bidali nahi baduzu, segmentazio hori Mensagian bertan kudeatu beharko duzu aplikazioa abiarazi aurretik.

---

## ⚠ Oharra bidaltzeari buruz

Programak **ez ditu mezu elektronikoak berehala bidaltzen**. Kontaktu hautagarri bakoitzarentzat banakako bidaltzeko konfigurazio bat sortzen du Mensagia plataforman, modu eskalonatuan exekutatzeko programatuta:

- **Lehen bidalketa** aplikazioa abiarazi eta **10 eta 20 minutu** artean exekutatzen da, erroreren bat antzemanez gero denbora izateko ezeztatzen.
- **Hurrengo bidalketak** **12 segundotan** banatzen dira (minutuko 5).

> **Bidalketa hasita dagoenean gelditu behar baduzu**, aplikazioa ixteak konfigurazio berriak sortzea geldiarazten du, baina dagoeneko sortutakoak bidaliko dira hala ere: Mensagia atarian banaka ezabatu beharko dituzu. Ez dago ezeztatze botoi globalik. Geroago bidalketari berriro ekin ahal izango diozu (ikus [Etendako bidalketa berriro hasi](#etendako-bidalketa-berriro-hasi)).
>
> Erabili **Simulatu** modua konfigurazio errealik sortu gabe zer bidaliko litzatekeen ikusteko.

---

## Etendako bidalketa berriro hasi

Bidalketa bat erdibidean eteten bada (aplikazioa ixten da, konexioa eteten da, ordenagailua itzaltzen da…), aplikazioak gogoratzen du zein kontakturi programatu zaien dagoeneko mezua.

**Kanpaina bera** berriro prestatzean (talde, txantiloi eta eranskin eremu berak, eta **gai bera, hitzez hitz**), laburpenera iristean aplikazioak aurreko bidalketa osatu gabe dagoela ohartarazten du eta zer egin galdetzen du:

- **Jarraitu**: falta diren kontaktuei bakarrik bidaltzen zaie. Haien mezuak aurreko bidalketakoen ondoren programatzen dira, haiekin gainjarri gabe.
- **Ez jarraitu**: aurreko bidalketa baztertu eta kontaktu guztiei bidaltzen zaie berriro, dagoeneko jaso dutenei barne.

### Bikoizketa posibleak

Etenaldia mezu bat programatzen ari zen une berean gertatzen bada, edo Mensagiak erantzuten ez badu, aplikazioak ezin du jakin mezu hori programatuta geratu zen. Kasu horretan berriro programatzen du, baina ohartarazi egiten du:

- Berriro hastean, oharrak hartzailea eta berrikusi beharreko data eta ordua adierazten ditu.
- Amaitzean, **bikoizketa posible** bat dagoen (mezua orain programatu da, baina agian lehen ere bai) edo **berretsi gabeko** bidalketa bat dagoen adierazten du.

Mensagiaren APIak ez du programatutako bidalketak kontsultatzen uzten; beraz, egiaztapen hori eskuz egin behar da atarian, soberan dagoen programazioa ezabatuz.

> Aurrerapena `send_progress.json` fitxategian gordetzen da, `.env` edo `.exe` fitxategiaren karpeta berean. Bidalketa bat errorerik gabe amaitzen denean, kanpaina fitxategitik ezabatzen da. Ez ezabatu fitxategia berriro hasteko zain dagoen bidalketarik dagoen bitartean.

---

## Hautaketen memoria (GUI modua)

Bidalketa edo simulazio bakoitzaren ondoren, aplikazioak aukeratutako
parametroak (txantiloia, bidaltzailea, taldea, eranskin eremua eta
ziurtagiria) `last_selections.json` fitxategi batean gordetzen ditu,
`.env` edo `.exe` fitxategiaren karpeta berean.

Hurrengo exekuzioan, aukera horiek lehenespenez markatuta agertuko dira.

> Memoria hau ezabatzeko, ezabatu `last_selections.json` fitxategia.
> Fitxategia ez badago, aplikazioak normalean funtzionatzen du.

---

## Interfazearen hizkuntzak

Interfazeak sistema eragilearen hizkuntza automatikoki detektatzen du.  
Hizkuntza erabilgarriak: **Español, Català, Galego, Euskera, English**.

---

## Exekutagarria sortu

Garapen-mendekotasunak behar ditu:

```bash
pip install -r requirements-dev.txt
```

Konpilazio scripta exekutatu:

```bash
build.bat
```

`.exe` fitxategiak `dist/` karpetan sortzen dira.

---

## Testak exekutatu

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Proiektuaren egitura

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entitateak eta portuak (interfazeak)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Programazio-logika
│   ├── application/
│   │   └── use_cases/      # Erabilera-kasuak
│   └── infrastructure/
│       ├── api/             # Mensagia API bezeroa eta egokitzaileak
│       ├── config/          # Konfigurazioa kargatzea (.env)
│       ├── logging/         # Bidalketen erregistroa (logak)
│       ├── persistence/     # Bidalketen aurrerapena (send_progress.json)
│       └── ui/
│           ├── console/     # Kontsola interfazea
│           ├── gui/         # Interfaze grafikoa (customtkinter)
│           └── locales/     # Itzulpenak
├── tests/
├── main.py                 # Kontsola sarrera-puntua
├── main_gui.py             # Sarrera-puntu grafikoa
├── build.bat               # .exe-ra konpilatzeko scripta
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
