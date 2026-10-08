# Mensagia Attachment Mailer

[Mensagiaren API](https://api.mensagia.com/docs/v1) erabiliz, kontaktu bakoitzari eranskin pertsonalizatuekin mezu elektronikoak bidaltzeko aplikazioa.

> Bertsioak: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [English](README.en.md)

---

## Eskakizunak

- Windows 10/11 edo macOS (exekutagarriak erabiltzeko)
- Edo Python 3.11+ (iturburu-kodea erabiltzeko)

---

## Exekutagarriaren erabilera (Pythonik gabeko bezeroak)

Deskargatu zure ordenagailurako bertsioa [releases orritik](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Ordenagailua | GUI modua | Kontsola modua |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Apple Silicon duen Mac-a (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Intel prozesadorea duen Mac-a | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### API tokena

Aplikazioak zure Mensagiako API tokena behar du, [mensagia.com](https://mensagia.com) → Erabiltzaileak atalean lor dezakezuna. Konfiguratuta ez badago, abiatzean eskatuko dizu. Aldi bakoitzean idatzi behar ez izateko, gorde ezazu `.env` fitxategi batean, [aplikazioaren datu-karpetan](#aplikazioaren-fitxategiak):

```
MENSAGIA_API_TOKEN=zure_api_tokena_hemen
```

### Windows

1. Deskargatu `.exe`. Aplikazioak bere fitxategiak karpeta berean gordetzen ditu; beraz, komeni da karpeta propio batean jartzea.
2. Nahi izanez gero, sortu `.env` fitxategia **karpeta berean**.
3. Exekutatu `.exe`.

> **Windows SmartScreen oharra:** fitxategia lehen aldiz exekutatzen duzunean, Windowsek segurtasun abisua erakuts dezake. Egin klik **"Informazio gehiago"** eta gero **"Exekutatu hala ere"** aukeretan. Deskargatutako bertsio bakoitzeko behin bakarrik egin behar da.

### macOS

> macOS ez dago euskaraz: hemen agertzen diren menuen izenak gaztelaniazko bertsiokoak dira.

1. **Aukeratu zure Mac-aren bertsioa.** Ireki Apple menua → **Acerca de este Mac**:
   - **Chip** agertzen bada (Apple M1, M2, M3…), deskargatu `apple-silicon` bertsioa.
   - **Procesador** agertzen bada (Intel…), deskargatu `intel` bertsioa.

   > GitHub Intel duten Mac-etarako konpilatzen duten makinak erretiratzen ari da. Azken bertsioak `intel` fitxategiak ez baditu, deskargatu itzazu haiek dituen bertsio berrienetik, [releases zerrendan](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Egin klik bikoitza `.zip` fitxategian deskonprimitzeko (Safarik automatikoki egin dezake deskargatzean). GUI moduan `mensagia-mailer-gui.app` lortuko duzu, eta **Aplicaciones** karpetara eraman dezakezu.
3. Nahi izanez gero, gorde `.env` fitxategia zure karpeta pertsonaleko **Mensagia Mailer** karpetan. Biak Terminaletik sor ditzakezu:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=zure_api_tokena_hemen" > ~/"Mensagia Mailer/.env"
   ```

   > Finderrek ezkutatu egiten ditu puntu batekin hasten diren fitxategiak, `.env` bezala. Sakatu **Cmd + Maius + .** erakusteko edo ezkutatzeko.

4. Ireki aplikazioa. Lehen aldian, macOSek blokeatu egingo du, Applek sinatu gabe dagoelako (Windowseko SmartScreen oharraren baliokidea da). Baimentzeko:
   - **macOS 15 (Sequoia) edo berriagoa:** oharraren ondoren, ireki **Ajustes del Sistema → Privacidad y seguridad**, jaitsi aplikazioari buruzko mezura arte eta sakatu **Abrir igualmente**. Ireki berriro eta berretsi.
   - **macOS 14 edo zaharragoa:** egin eskuineko klik aplikazioan → **Abrir**, eta berretsi oharrean.
   - **Edozein bertsiotan, Terminaletik:** `xattr -cr` eta ondoren aplikazioaren bidea, adibidez `xattr -cr /Applications/mensagia-mailer-gui.app`.

   Deskargatutako bertsio bakoitzeko behin bakarrik egin behar da.

> Kontsola bertsioa klik bikoitzarekin irekitzen da eta Terminaleko leiho batean exekutatzen da.

---

## Aplikazioaren fitxategiak

Aplikazioak datu-karpeta batean gordetzen ditu bere fitxategiak, eta karpeta hori nola exekutatzen den araberakoa da:

| Exekuzioa | Datu-karpeta |
|---|---|
| Windows (`.exe`) | `.exe` fitxategiaren karpeta bera |
| macOS | `Mensagia Mailer`, zure karpeta pertsonalaren barruan (`~/Mensagia Mailer`) |
| Iturburu-kodea | Proiektuaren erroa |

Karpeta horretan daude:

- `.env`: konfigurazioa (API tokena, hizkuntza, eranskinen oinarrizko URLa…). Zuk sortzen duzu, eta aukerakoa da.
- `logs/`: bidalketa eta simulazio bakoitzaren erregistroa (ikus [Bidalketa bat simulatu](#bidalketa-bat-simulatu)).
- `last_selections.json`: aukeratutako azken aukerak (ikus [Hautaketen memoria](#hautaketen-memoria-gui-modua)).
- `send_progress.json`: bidalketen aurrerapena (ikus [Etendako bidalketa berriro hasi](#etendako-bidalketa-berriro-hasi)).

Aplikazioak karpeta eta fitxategiak behar dituen heinean sortzen ditu.

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

## Bidalketa bat simulatu

**Simulatu** botoiak (kontsola moduan, `Sim` erantzunak) benetako bidalketa baten egiaztapen guztiak egiten ditu (kontaktu egokiak, eranskinen URLak eta deskarga daitezkeen), baina **ez du mezurik programatzen** Mensagian, eta ez du aldatzen [bidalketa berriro hasteko](#etendako-bidalketa-berriro-hasi) gordetako aurrerapena.

Simulazio bakoitzak benetako bidalketa batek bezalako edukia duen loga sortzen du: mezua jasoko luketen kontaktuak eta baztertutakoak, arrazoiarekin. Amaitzean, aplikazioak fitxategiaren bidea erakusten du.

- Logak [aplikazioaren datu-karpetako](#aplikazioaren-fitxategiak) `logs/` karpetan gordetzen dira.
- Simulazioenak `mensagia_simulation_<data_ordua>.log` dira, eta benetako bidalketenak, `mensagia_send_<data_ordua>.log`. Karpeta izenaren arabera ordenatzen baduzu, bereizita geratzen dira.
- Simulazio-log baten lehen lerroa `[SIMULATION] This is a simulation: no email was sent.` da. Bertan, `[SEND_OK]` lerroak bidaliko liratekeen mezuak dira.

Baztertzeko arrazoiak (`reason=`, `[SEND_SKIP]` lerroetan):

- `no_email`: kontaktuak ez du helbide elektronikorik.
- `no_attachment`: eranskinaren eremu pertsonalizatua hutsik dago.
- `already_sent`: kontaktuak kanpaina bereko aurreko bidalketa eten batean jaso zuen mezua.

`[SEND_ERROR]` lerroak eranskina prestatu ezin izan zaien kontaktu egokiak dira (adibidez, oinarrizko URLrik gabeko bide erlatibo bat edo deskargatu ezin den fitxategi bat).

**Taldeko kontakturen bat ere egokia ez denean** (edo denek aurreko bidalketa batean jaso dutenean mezua), ezin da bidali, baina simulatu bai: logari esker jakin daiteke kontaktu bakoitza zergatik baztertu den. Modu grafikoan, **Bidali** botoia desaktibatuta geratzen da; kontsola moduan, aplikazioak simulazioa bakarrik eskaintzen du.

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

> Aurrerapena `send_progress.json` fitxategian gordetzen da, [aplikazioaren datu-karpetan](#aplikazioaren-fitxategiak). Bidalketa bat errorerik gabe amaitzen denean, kanpaina fitxategitik ezabatzen da. Ez ezabatu fitxategia berriro hasteko zain dagoen bidalketarik dagoen bitartean.

---

## Hautaketen memoria (GUI modua)

Bidalketa edo simulazio bakoitzaren ondoren, aplikazioak aukeratutako
parametroak (txantiloia, bidaltzailea, taldea, eranskin eremua eta
ziurtagiria) `last_selections.json` fitxategi batean gordetzen ditu,
[aplikazioaren datu-karpetan](#aplikazioaren-fitxategiak).

Hurrengo exekuzioan, aukera horiek lehenespenez markatuta agertuko dira.

> Memoria hau ezabatzeko, ezabatu `last_selections.json` fitxategia.
> Fitxategia ez badago, aplikazioak normalean funtzionatzen du.

---

## Interfazearen hizkuntzak

Interfazeak sistema eragilearen hizkuntza automatikoki detektatzen du.  
Hizkuntza erabilgarriak: **Español, Català, Galego, Euskera, English**.

---

## Exekutagarriak sortu

Exekutagarriak automatikoki sortzen dira GitHub Actions-ekin (`.github/workflows/build-release.yml`). PyInstallerrek ezin du beste sistema baterako konpilatu; beraz, bertsio bakoitza dagokion sistemako makina batean konpilatzen da: Windows, Apple Silicon duen Mac-a eta Intel duen Mac-a.

- **`vX.Y.Z` tag bat igotzean**, workflow-ak hiru bertsioak konpilatzen ditu eta **release zirriborro** bat sortzen du sei fitxategiak erantsita. Ondoren, oharrak idatzi eta argitaratu egiten da.
- **Eskuz**, **Actions** fitxatik → **Run workflow**, hiru bertsioak konpilatzen ditu releaserik sortu gabe, eta fitxategiak exekuzioan bertan uzten ditu deskargatzeko (**Artifacts** atala).

> Intel duen Mac-erako konpilazioak huts egiten badu GitHubek makina horiek dagoeneko erretiratu dituelako, release zirriborroa sortzen da hala ere, Windows eta Apple Silicon fitxategiekin.

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
│       ├── logging/         # Bidalketen logak idaztea
│       ├── persistence/     # Bidalketen aurrerapena gordetzea
│       └── ui/
│           ├── console/     # Kontsola interfazea
│           ├── gui/         # Interfaze grafikoa (customtkinter)
│           └── locales/     # Itzulpenak
├── tests/
├── main.py                 # Kontsola sarrera-puntua
├── main_gui.py             # Sarrera-puntu grafikoa
├── .github/workflows/      # Exekutagarriak konpilatzea (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
