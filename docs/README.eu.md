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

## Bertsio berriaren abisua

Abiaraztean, aplikazioak egiaztatzen du [releases orrian](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) bertsio berriagorik argitaratu den. Baldin badago, abisu txiki bat erakusten du bertsio berriaren zenbakiarekin eta deskargatzeko estekarekin:

- **Modu grafikoa:** lehen pantailaren behealdean (tokenarena). Egin klik estekan deskarga-orria irekitzeko.
- **Kontsola modua:** lerro bat gaia eskatu aurretik.

Aplikazioak abisatu besterik ez du egiten: ez du ezer deskargatzen ez instalatzen. Eguneratzeko, deskargatu bertsio berria [Exekutagarriaren erabilera](#exekutagarriaren-erabilera-pythonik-gabeko-bezeroak) atalean azaltzen den bezala, eta ordeztu aurrekoa. Windowsen, jarri `.exe` berria karpeta berean, [datu-karpetako](#aplikazioaren-fitxategiak) fitxategiak gordetzeko.

Konexiorik ez badago edo GitHubek 3 segundotan erantzuten ez badu, ez da ezer erakusten eta aplikazioak normal funtzionatzen du.

Egiaztapena desaktibatzeko, gehitu lerro hau `.env` fitxategiari:

```
MENSAGIA_CHECK_UPDATES=false
```

> Iturburu-kodetik, aplikazioak ez daki bere bertsio-zenbakia eta ez du ezer egiaztatzen. Abisua probatzeko, gehitu `.env` fitxategiari argitaratutako azkena baino bertsio zaharragoa, adibidez `MENSAGIA_APP_VERSION=v1.3.0`. Exekutagarriek ez diote aldagai honi kasurik egiten.

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
2. **Gaia, hasiera-ordua eta jatorria** — Erabiltzaileak mezu elektronikoaren gaia sartzen du, mezuak noiz bidaliko diren aukeratzen du: orain, data eta ordu jakin batean edo kontaktu bakoitzaren egunean (ikus [Hasiera-ordua programatu](#hasiera-ordua-programatu)) eta hartzaileak nondik datozen: **agendako talde** batetik edo **fitxategi** batetik (ikus [Fitxategi bateko hartzaileei bidali](#fitxategi-bateko-hartzaileei-bidali)).
3. **Txantiloia** — Eskuragarri dauden email txantiloien zerrenda erakusten da.
4. **Bidaltzailea** — Egiaztatutako bidaltzaile helbideen zerrenda erakusten da.
5. **Taldea edo fitxategia**:
   - Agendarekin, taldeen lehen orria erakusten da. Bilatzen ari zaren taldea agertzen ez bada, izenaren arabera iragaz daiteke. Kontakturik gabeko taldeak erakusten dira, baina ezin dira hautatu.
   - Fitxategi batekin, fitxategia aukeratzen da eta, hainbat orri dituen Excel bat bada, orria.
6. **Eranskin eremua edo zutabeak**:
   - Agendarekin, eranskinaren URLa duen eremu pertsonalizatua aukeratzen da. Mezuak kontaktu bakoitzaren egunean bidaltzen badira, ondoren data duen eremua eta haren formatua aukeratzen dira.
   - Fitxategi batekin, helbide elektronikoa zein zutabetan dagoen eta eranskina zeinetan dagoen aukeratzen da. Mezuak kontaktu bakoitzaren egunean bidaltzen badira, data duen zutabea eta haren formatua ere bai.
7. **Ziurtagiria** — Erabiltzaileak bidalketak ziurtatzea erabakitzen du.
8. **Bidalketa** — Helbide baliozkorik edo eranskinik ez duten hartzaileak baztertzen dira, eta minutuko 5eko abiaduran mezu bat bidaltzen zaio bakoitzari.

---

## Eranskinaren bidea eremu pertsonalizatuan

6. urratsean aukeratutako eremu pertsonalizatuak (edo eranskinaren zutabeak, hartzaileak fitxategi batetik badatoz) kontaktu bakoitzaren eranskina bi modutan adieraz dezake:

- **URL osoa**, `http://` edo `https://`-rekin hasten dena (adibidez, `https://cdn.empresa.com/docs/factura_42.pdf`). Dagoen bezala erabiltzen da.
- **Fitxategi-izena edo bide erlatiboa** (adibidez, `factura_42.pdf` edo `2026/factura_42.pdf`). Aplikazioak **oinarrizko URL** bat jartzen dio aurretik: `https://cdn.empresa.com/docs/` oinarriarekin, `factura_42.pdf` balioa `https://cdn.empresa.com/docs/factura_42.pdf` bihurtzen da.

Bi moduak talde edo fitxategi berean konbina daitezke.

Oinarrizko URLa hainbat modutan adieraz daiteke:

- `.env` fitxategian, `MENSAGIA_ATTACHMENT_BASE_URL` aldagaiarekin:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- **GUI moduan**, lehen pantailako **Eranskinaren oinarrizko URLa** eremuan. `.env`-n definituta badago, beteta agertzen da.
- **Kontsola moduan**, aplikazioak kontaktuen batek bide erlatiboa badu eta aldagaia `.env`-n ez badago bakarrik eskatzen du.

> Oinarrizko URLak beti **web helbide publiko** bat izan behar du, inoiz ez ordenagailuko karpeta bat: Mensagiak deskargatzen du fitxategia mezuari eransteko. `/`-rekin amai daiteke edo ez; aplikazioak kontuan hartzen du.

---

## Fitxategi bateko hartzaileei bidali

Agendako talde batez gain, hartzaileak **Excel (`.xlsx`)** edo **CSV (`.csv`)** fitxategi batetik atera daitezke. Fitxategiko errenkada bakoitza mezu bat da; beraz, helbide berak hainbat mezu jaso ditzake eranskin desberdinekin bidalketa berean (adibidez, bere bezero batzuen dokumentazioa jasotzen duen agentzia batek). Hartzaileek ez dute Mensagiako agendan egon behar.

### Nolakoa izan behar du fitxategiak

- **Lehen errenkada goiburua da**, eta derrigorrezkoa da: zutabe bakoitzaren izena du.
- Zutabeen izenak, ordena eta kopurua libreak dira. Bidalketa prestatzean, helbide elektronikoa zein zutabetan dagoen eta eranskina zeinetan dagoen aukeratzen da; gainerakoak ez dira kontuan hartzen.
- Erabat hutsik dauden errenkadak eta zutabeak ez dira kontuan hartzen.
- Excelak hainbat orri baditu, zein erabili aukeratzen da. Bat bakarrik badu, ez da galdetzen.
- CSVetan, bereizlea (`;` edo `,`) eta kodeketa (UTF-8 edo Windowsena) automatikoki hautematen dira.

Adibidea:

| Bezeroa | Helbidea | Eranskina |
|---|---|---|
| A bezeroa | agentzia@adibidea.com | fakturak/bezeroa_a.pdf |
| B bezeroa | agentzia@adibidea.com | fakturak/bezeroa_b.pdf |
| C bezeroa | info@bezeroac.com | https://cdn.empresa.com/docs/c.pdf |

Aplikazioak ez du jarraitzen uzten baldin eta:

- fitxategia hutsik badago edo goiburua baino ez badu;
- zutaberen batek datuak baditu baina goiburuan izenik ez badu;
- izen bereko bi zutabe badaude (maiuskulak bereizi gabe);
- lehen errenkadako gelaxkaren batek `@` badu: ziurrenik fitxategiak ez du goibururik.

### Errenkada bakoitzeko helbidea eta eranskina

- **Helbide elektronikoa**: hasierako eta amaierako zuriuneak kentzen dira. Helbide bakar bat izan behar du: `@` bakar bat; `@`-ren aurretik, azentu gabeko letrak, zenbakiak eta `. _ % + -` bakarrik; ondoren, azentu gabeko letrak, zenbakiak, `-` eta gutxienez puntu bat. Helbide bat baino gehiago dituen gelaxka ez da baliozkoa.
- **Eranskina**: eremu pertsonalizatuan bezala, URL oso bat edo oinarrizko URLarekiko bide erlatibo bat (ikus [Eranskinaren bidea](#eranskinaren-bidea-eremu-pertsonalizatuan)). Zenbakiak hamartarrik gabe irakurtzen dira (`1234`, ez `1234.0`).

Errenkada hauek baztertu egiten dira, eta [logak](#bidalketa-bat-simulatu) arrazoia adierazten du:

- helbiderik gabekoak (`no_email`) edo helbide baliogabea dutenak (`invalid_email`);
- eranskinik gabekoak (`no_attachment`);
- aurreko errenkada baten helbide bera (maiuskulak bereizi gabe) eta eranskin bera dutenak (`duplicate_row`): lehena bakarrik bidaltzen da. Mezuak kontaktu bakoitzaren egunean bidaltzen badira, datak ere bat etorri behar du. Fitxategi-izen bat eta oinarrizko URLarekin lortzen den URL osoa eranskin bera dira.

Logean, errenkada bakoitza Excelek erakusten duen zenbakiarekin (goiburua 1. errenkada da), helbidearekin eta eranskinarekin identifikatzen da. Adibidez:

```
[SEND_SKIP]  row=14 to=agentzia@adibidea.com attachment=fakturak/bezeroa_a.pdf reason=duplicate_row
```

### Fitxategiko aldaketak

Fitxategia berriro irakurtzen da laburpenera iristean eta bidalketa hastean; beraz, bitartean gordetako aldaketak erabiltzen dira. Fitxategia ezin bada erabili (adibidez, aukeratutako zutabe baten izena aldatu delako), aplikazioak hala adierazten du eta ez du ezer bidaltzen.

[Etendako bidalketa berriro hasteko](#etendako-bidalketa-berriro-hasi), fitxategia duen bidalketa bat **fitxategiaren izenaren** (karpetarik gabe), orriaren, aukeratutako zutabeen, txantiloiaren, gaiaren eta hasiera-orduaren moduaren arabera identifikatzen da. Horregatik:

- Fitxategia beste karpeta batera eraman daiteke, errenkadak zuzendu, errenkada berriak gehitu edo haien ordena aldatu. Berriro hastean, falta ziren errenkadak bakarrik bidaltzen dira, errenkada bakoitza bere helbidearen eta eranskinaren bidez ezagutzen baita.
- Fitxategiaren izena, orria edo zutaberen bat aldatzen bada, bidalketa berritzat hartzen da.

> Kontsola moduan, fitxategiaren bidea idatzi edo itsatsi egiten da. Windowsen «Kopiatu bide gisa» aukerak gehitzen dituen komatxoak onartzen dira.

---

## ⚠ Oharra taldeko kontaktuei buruz

Taldea **kontaktu-iturri** gisa erabiltzen da, ez harpidetza-zerrenda gisa. Aplikazioak **taldeko kontaktu guztiei** bidaliko die mezua, agenda horretan harpideduta dauden ala ez.

> Mensagiaren APIak ez du kontaktu bakoitzaren harpidetza-egoerari buruzko informaziorik ematen agenda batean. Harpidetutako kontaktuetara soilik bidali nahi baduzu, segmentazio hori Mensagian bertan kudeatu beharko duzu aplikazioa abiarazi aurretik.

---

## ⚠ Oharra bidaltzeari buruz

Programak **ez ditu mezu elektronikoak berehala bidaltzen**. Kontaktu hautagarri bakoitzarentzat banakako bidaltzeko konfigurazio bat sortzen du Mensagia plataforman, modu eskalonatuan exekutatzeko programatuta:

- **Lehen bidalketa** bidalketa abiarazi eta **10 eta 20 minutu** artean exekutatzen da, erroreren bat antzemanez gero denbora izateko ezeztatzen, edo aukeratutako data eta orduan (ikus [Hasiera-ordua programatu](#hasiera-ordua-programatu)).
- **Hurrengo bidalketak** **12 segundotan** banatzen dira (minutuko 5).

> **Bidalketa hasita dagoenean gelditu behar baduzu**, aplikazioa ixteak konfigurazio berriak sortzea geldiarazten du, baina dagoeneko sortutakoak bidaliko dira hala ere: Mensagia atarian banaka ezabatu beharko dituzu. Ez dago ezeztatze botoi globalik. Geroago bidalketari berriro ekin ahal izango diozu (ikus [Etendako bidalketa berriro hasi](#etendako-bidalketa-berriro-hasi)).
>
> Erabili **Simulatu** modua konfigurazio errealik sortu gabe zer bidaliko litzatekeen ikusteko.

---

## Hasiera-ordua programatu

Gaiaren orrian (kontsola moduan, gaiaren ondoren) mezuak noiz bidaliko diren aukeratzen da:

- **Orain**: bidalketa hasi eta 10-20 minutu barru.
- **Data eta ordu jakin batean**: lehen mezua adierazitako data eta orduan bidaltzen da, eta hurrengoak 12 segundoro. Bidalketek gauerdia gaindi dezakete.
- **Kontaktu bakoitzaren eguna, ordu jakin batean**: mezu bakoitza kontaktuaren datuetan adierazitako egunean bidaltzen da, aukeratutako orduan (ikus [Mezu bakoitza kontaktuaren egunean bidali](#mezu-bakoitza-kontaktuaren-egunean-bidali)).

Data eta ordua beti `ee/hh/uuuu` eta `oo:mm` ordenan idazten dira, hizkuntza edozein dela ere. Modu grafikoan zati bakoitzak bere eremua du, eta kurtsorea bakarrik pasatzen da hurrengora eremu bat betetzean. Kontsola moduan ohiko beste forma batzuk ere onartzen dira (`8/10/26`, `8-10-2026`, `9h30`, `9`…), eta Sartu tekla sakatuta kortxete artean proposatutako balioa onartzen da.

Mugak:

- **Gutxieneko tartea: 10 minutu.** Hurrengo orrira igarotzean, data eta orduak uneko ordua baino gutxienez 10 minutu geroago izan behar du.
- **Atzeratze automatikoa.** Gainerako urratsak betetzen diren bitartean aukeratutako orduak 10 minutuko tartea galtzen badu, bidalketa hastean automatikoki atzeratzen da tarte hori betetzen duen lehen ordura, «Orain» aukerarekin bezala. Aplikazioak ez du ohartarazten, baina bidalketaren logak aukeratutako ordua (`start_at`) eta lehen mezuarena (`first_slot`) adierazten ditu. Mezuak ez dira inoiz aukeratutako ordua baino lehenago bidaltzen.
- **Gehienez 6 aste lehenago**, bidalketa prestatzen den unetik.
- Simulazioak ez du ordua egiaztatzen, datuak bakarrik.

> ⚠ **Ordu-eremua.** Ordua ordu-eremurik gabe bidaltzen zaio Mensagiari, eta Mensagiak tokenari lotutako **Mensagiako erabiltzailean konfiguratutako «Ordu-eremua»** erabiliz interpretatzen du. Egiaztatu aplikazioa exekutatzen duen ordenagailuarenarekin bat datorrela: bestela, mezuak aukeratutakoaz bestelako ordu batean bidaliko dira.

Aplikazioak gaurko data proposatzen du eta, ordu gisa, modu grafikoan aukeratutako azkena edo, bat ere ez badago, «Orain» aukerari legokiokeena.

[Etendako bidalketa bat berriro hasteko](#etendako-bidalketa-berriro-hasi) aukera berak errepikatu behar dira, hasiera-orduaren modua barne: modua aldatzen bada, bidalketa berritzat hartzen da. Aldiz, data edo ordua aldatzeak ez du bidalketa berririk sortzen: berriro hastean, mezuak programatutako azkenaren ondoren jarraitzen dute, eta ordu berria une horrek 10 minutuko tartea ez badu bakarrik erabiltzen da.

---

## Mezu bakoitza kontaktuaren egunean bidali

**Kontaktu bakoitzaren eguna, ordu jakin batean** aukerarekin, hartzaile bakoitzak bere datuetan adierazitako egunean jasotzen du mezua: eremu pertsonalizatu batean (agenda) edo zutabe batean (fitxategia). Ordua bakarrik aukeratzen da, eta egun guztietarako bera da.

- Agendarekin, eranskinaren eremuaren ondoren data duen eremua aukeratzen da. Ezin da eranskinarena izan.
- Fitxategi batekin, zutabeen orrian data duen zutabea ere aukeratzen da. Ezin da beste bietako bat izan.

Egun bakoitza aukeratutako orduan hasten da, eta 12 segundo gehitzen ditu **egun bereko** aurreko mezu bakoitzeko. Adibidez, 09:00ekin, 15/10eko hiru mezu 09:00:00etan, 09:00:12etan eta 09:00:24etan bidaltzen dira, eta 16/10eko bat, 09:00:00etan.

| Kontaktuaren data | Zer gertatzen da |
|---|---|
| Etorkizuneko egun bat | Egun horretako aukeratutako orduan bidaltzen da |
| Gaur | Aukeratutako orduan, gutxienez 10 minutu falta badira; bestela, «Orain» aukeran bezala (10 eta 20 minutu geroago) |
| Iragandako egun bat | Baztertu egiten da (`past_send_date`) |
| 6 aste baino urrunago | Baztertu egiten da (`send_date_too_far`) |
| Hutsik | Baztertu egiten da (`no_send_date`) |
| Beste formatu batean | Baztertu egiten da (`invalid_send_date`) |
| Orduarekin | Baztertu egiten da (`send_date_has_time`) |

Adibidez, 10:07an eta 10:00ko orduarekin, gaurko kontaktuak 10:20:00etan, 10:20:12etan… bidaltzen dira, eta hurrengo egunetakoak, beren eguneko 10:00:00etan, 10:00:12etan…

- Egun bateko mezuek gauerdia gaindi dezakete. Hurrengo eguna ez da mugitzen, nahiz eta denbora batez minutuko mezu gehiago bidali.
- Egunak ordenan programatzen dira, hurbilenetik urrunenera.

### Dataren formatua

Mensagiak ez du bere data-eremuen formatua adierazten; beraz, aukeratu egin behar da: `ee/hh/uuuu`, `ee-hh-uuuu`, `uuuu/hh/ee` edo `uuuu-hh-ee`.

Ordenak eta bereizleak aukeratutako formatuarekin bat etorri behar dute, baina zeroak aukerakoak dira eta urteak 2 zifra izan ditzake: `ee/hh/uuuu` formatuarekin, `3/4/26` 2026ko apirilaren 3a da. Orduarekin datorren data bat (`15/10/2026 10:00`) baztertu egiten da.

Fitxategi batean, formatua testu gisa idatzitako datei bakarrik aplikatzen zaie (CSV batean, edo gelaxka testu formatuan duen Excel batean). Excelek data gisa ezagutzen dituen gelaxkak zuzenean irakurtzen dira; 00:00 ez den ordu bat badute, baztertu egiten dira.

### Aurretiko laburpena

Bidali aurretik, laburpenak hau erakusten du:

- egun bakoitzeko errenkada bat duen taula, mezu kopuruarekin eta lehenaren eta azkenaren gutxi gorabeherako orduarekin;
- baztertutakoak, arrazoiaren arabera taldekatuta (bakoitzaren xehetasuna logean dago);
- fitxategi batekin, helbide berera eranskin bera data desberdinetan bidaliko duten errenkadak. Guztiak bidaltzen dira; bat soberan badago, Mensagiako atarian ezaba daiteke.

Orduak gutxi gorabeherakoak dira: mezu bakoitzaren behin betiko ordua programatzean kalkulatzen da.

### Berriro hasi

Egun bakoitza bere aldetik hasten da berriro: egun horretan programatutako azken mezuaren ondoren jarraitzen du edo, bat ere ez bazuen, aukeratutako orduan (gaur, gutxienez 10 minutu falta badira bakarrik). Dagoeneko igaro diren egunetako kontaktu pendienteak baztertu egiten dira. Dataren eremua edo zutabea bidalketaren parte dira: aldatzen badira, bidalketa berria da.

---

## Bidalketa bat simulatu

**Simulatu** botoiak (kontsola moduan, `Sim` erantzunak) benetako bidalketa baten egiaztapen guztiak egiten ditu (kontaktu egokiak, eranskinen URLak eta deskarga daitezkeen), baina **ez du mezurik programatzen** Mensagian, eta ez du aldatzen [bidalketa berriro hasteko](#etendako-bidalketa-berriro-hasi) gordetako aurrerapena.

Simulazio bakoitzak benetako bidalketa batek bezalako edukia duen loga sortzen du: mezua jasoko luketen kontaktuak eta baztertutakoak, arrazoiarekin. Amaitzean, aplikazioak fitxategiaren bidea erakusten du.

- Logak [aplikazioaren datu-karpetako](#aplikazioaren-fitxategiak) `logs/` karpetan gordetzen dira.
- Simulazioenak `mensagia_simulation_<data_ordua>.log` dira, eta benetako bidalketenak, `mensagia_send_<data_ordua>.log`. Karpeta izenaren arabera ordenatzen baduzu, bereizita geratzen dira.
- Simulazio-log baten lehen lerroa `[SIMULATION] This is a simulation: no email was sent.` da. Bertan, `[SEND_OK]` lerroak bidaliko liratekeen mezuak dira.

Baztertzeko arrazoiak (`reason=`, `[SEND_SKIP]` lerroetan):

- `no_email`: kontaktuak edo errenkadak ez du helbide elektronikorik.
- `invalid_email`: errenkadako helbide elektronikoa ez da baliozkoa (fitxategi batekin bakarrik).
- `no_attachment`: eranskinaren eremu pertsonalizatua edo zutabea hutsik dago.
- `duplicate_row`: errenkadak aurreko errenkada baten helbidea eta eranskina errepikatzen ditu (fitxategi batekin bakarrik).
- `already_sent`: hartzaileak kanpaina bereko aurreko bidalketa eten batean jaso zuen mezua.
- `no_send_date`, `invalid_send_date` eta `send_date_has_time`: kontaktuaren data hutsik dago, ez du aukeratutako formatua edo ordua du (ikus [Mezu bakoitza kontaktuaren egunean bidali](#mezu-bakoitza-kontaktuaren-egunean-bidali)).
- `past_send_date` eta `send_date_too_far`: kontaktuaren data igaro da edo 6 aste baino urrunago dago.

`[SEND_OK]` lerroek mezu bakoitza zein data eta ordutarako programatu den ere adierazten dute (`start_date`), Mensagiako atarian aurkitzeko. Aurretiko laburpenak baztertutakoak arrazoiaren arabera taldekatuta erakusten ditu.

`[SEND_ERROR]` lerroak eranskina prestatu ezin izan zaien kontaktu egokiak dira (adibidez, oinarrizko URLrik gabeko bide erlatibo bat edo deskargatu ezin den fitxategi bat).

**Taldeko kontakturen bat edo fitxategiko errenkadaren bat ere egokia ez denean** (edo denek aurreko bidalketa batean jaso dutenean mezua), ezin da bidali, baina simulatu bai: logari esker jakin daiteke bakoitza zergatik baztertu den. Modu grafikoan, **Bidali** botoia desaktibatuta geratzen da; kontsola moduan, aplikazioak simulazioa bakarrik eskaintzen du. Gainera, simulazio baten ondoren, modu grafikoak mezuren bat bidaliko balitz bakarrik eskaintzen du **Bidali** botoia (adibidez, ez du eskaintzen eranskinik deskargatu ezin bada).

---

## Etendako bidalketa berriro hasi

Bidalketa bat erdibidean eteten bada (aplikazioa ixten da, konexioa eteten da, ordenagailua itzaltzen da…), aplikazioak gogoratzen du zein kontakturi programatu zaien dagoeneko mezua.

**Kanpaina bera** berriro prestatzean (talde bera —edo fitxategi, orri eta helbide-zutabe berak—, txantiloi, eranskin eremu edo zutabe eta hasiera-ordu modu berak —eta, mezuak kontaktu bakoitzaren egunean bidaltzen badira, dataren eremu edo zutabe bera—, eta **gai bera, hitzez hitz**), laburpenera iristean aplikazioak aurreko bidalketa osatu gabe dagoela ohartarazten du eta zer egin galdetzen du:

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
parametroak (hartzaileen jatorria, txantiloia, bidaltzailea, taldea, eranskin eremua, azken fitxategiaren karpeta,
helbidearen eta eranskinaren zutabeak, dataren eremua edo zutabea eta haren formatua, ziurtagiria, eta hasiera-orduaren modua eta ordua) `last_selections.json` fitxategi batean gordetzen ditu,
[aplikazioaren datu-karpetan](#aplikazioaren-fitxategiak).

Hurrengo exekuzioan, aukera horiek lehenespenez markatuta agertuko dira. Zutabeak fitxategi berriak
izen horiek dituzten zutabeak baditu bakarrik markatzen dira. Fitxategia eta orria ez dira gogoratzen:
fitxategi-hautatzailea azkena erabilitakoaren karpetan irekitzen da.

> Memoria hau ezabatzeko, ezabatu `last_selections.json` fitxategia.
> Fitxategia ez badago, aplikazioak normalean funtzionatzen du.

---

## Interfazearen hizkuntzak

Interfazeak sistema eragilearen hizkuntza automatikoki detektatzen du.  
Hizkuntza erabilgarriak: **Español, Català, Galego, Euskera, English**.

---

## Exekutagarriak sortu

Exekutagarriak automatikoki sortzen dira GitHub Actions-ekin (`.github/workflows/build-release.yml`). PyInstallerrek ezin du beste sistema baterako konpilatu; beraz, bertsio bakoitza dagokion sistemako makina batean konpilatzen da: Windows, Apple Silicon duen Mac-a eta Intel duen Mac-a.

- **`vX.Y.Z` tag bat igotzean**, workflow-ak hiru bertsioak konpilatzen ditu eta **release zirriborro** bat sortzen du sei fitxategiak erantsita. Ondoren, oharrak idatzi eta argitaratu egiten da. Exekutagarriek tag-aren bertsio-zenbakia daramate, [bertsio berriaren abisuak](#bertsio-berriaren-abisua) erabiltzen duena.
- **Eskuz**, **Actions** fitxatik → **Run workflow**, hiru bertsioak konpilatzen ditu releaserik sortu gabe, eta fitxategiak exekuzioan bertan uzten ditu deskargatzeko (**Artifacts** atala). Exekutagarri hauek `dev` bertsioa dute eta ez dute bertsio berriez abisatzen.

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
│       ├── files/           # Excel eta CSV fitxategiak irakurtzea
│       ├── logging/         # Bidalketen logak idaztea
│       ├── persistence/     # Bidalketen aurrerapena gordetzea
│       ├── recipients/      # Hartzaileen jatorriak (agenda edo fitxategia)
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
