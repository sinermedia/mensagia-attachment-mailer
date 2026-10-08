# Mensagia Attachment Mailer

Aplicació per enviar correus electrònics amb adjunts personalitzats per contacte fent servir la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Galego](README.gl.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisits

- Windows 10/11 o macOS (per als executables)
- O Python 3.11+ (per executar des del codi font)

---

## Ús de l'executable (clients sense Python)

Descarrega la versió per al teu ordinador des de la [pàgina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Ordinador | Mode gràfic | Mode consola |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Mac amb Apple Silicon (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Mac amb processador Intel | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### Token API

L'aplicació necessita el teu token API de Mensagia, que pots obtenir a [mensagia.com](https://mensagia.com) → Usuaris. Si no el tens configurat, te'l demanarà en arrencar. Per no haver-lo d'introduir cada vegada, desa'l en un fitxer `.env` a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació):

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

### Windows

1. Descarrega el `.exe`. L'aplicació desa els seus fitxers a la mateixa carpeta, així que convé posar-lo en una carpeta pròpia.
2. Opcionalment, crea el fitxer `.env` en aquesta **mateixa carpeta**.
3. Executa el `.exe`.

> **Avís de Windows SmartScreen:** la primera vegada que executis el fitxer, el Windows pot mostrar un avís de seguretat. Fes clic a **"Més informació"** i després a **"Executa de totes maneres"**. Només cal fer-ho una vegada per cada versió descarregada.

### macOS

1. **Tria la versió del teu Mac.** Obre el menú Apple → **Quant a aquest Mac**:
   - Si hi apareix **Xip** (Apple M1, M2, M3…), descarrega la versió `apple-silicon`.
   - Si hi apareix **Processador** (Intel…), descarrega la versió `intel`.

   > GitHub està retirant les màquines que compilen per a Mac amb Intel. Si l'última versió no inclou els fitxers `intel`, descarrega'ls de la versió més recent que els tingui a la [llista de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Fes doble clic al `.zip` per descomprimir-lo (el Safari ho pot fer automàticament en descarregar-lo). En mode gràfic obtindràs `mensagia-mailer-gui.app`, que pots moure a **Aplicacions**.
3. Opcionalment, desa el fitxer `.env` a la carpeta **Mensagia Mailer** de la teva carpeta personal. Pots crear totes dues coses des del Terminal:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=el_teu_token_api_aqui" > ~/"Mensagia Mailer/.env"
   ```

   > El Finder amaga els fitxers el nom dels quals comença per un punt, com `.env`. Prem **Ordre + Maj + .** per mostrar-los o amagar-los.

4. Obre l'aplicació. La primera vegada, el macOS la bloquejarà perquè no està signada per Apple (és l'equivalent de l'avís de SmartScreen del Windows). Per permetre-la:
   - **macOS 15 (Sequoia) o posterior:** després de l'avís, obre **Configuració del Sistema → Privacitat i seguretat**, baixa fins al missatge sobre l'aplicació i prem **Obre igualment**. Torna-la a obrir i confirma-ho.
   - **macOS 14 o anterior:** fes clic dret sobre l'aplicació → **Obre**, i confirma-ho a l'avís.
   - **En qualsevol versió, des del Terminal:** `xattr -cr` seguit de la ruta de l'aplicació, per exemple `xattr -cr /Applications/mensagia-mailer-gui.app`.

   Només cal fer-ho una vegada per cada versió descarregada.

> La versió de consola s'obre amb doble clic i funciona dins d'una finestra del Terminal.

---

## Fitxers de l'aplicació

L'aplicació desa els seus fitxers en una carpeta de dades, que depèn de com s'executi:

| Execució | Carpeta de dades |
|---|---|
| Windows (`.exe`) | La mateixa carpeta que el `.exe` |
| macOS | `Mensagia Mailer`, dins de la teva carpeta personal (`~/Mensagia Mailer`) |
| Codi font | L'arrel del projecte |

En aquesta carpeta hi ha:

- `.env`: la configuració (token API, idioma, URL base dels adjunts…). El crees tu i és opcional.
- `logs/`: un registre de cada enviament i de cada simulació (vegeu [Simular un enviament](#simular-un-enviament)).
- `last_selections.json`: les últimes opcions triades (vegeu [Memòria de seleccions](#memòria-de-seleccions-mode-gràfic)).
- `send_progress.json`: el progrés dels enviaments (vegeu [Reprendre un enviament interromput](#reprendre-un-enviament-interromput)).

L'aplicació crea la carpeta i els fitxers a mesura que els necessita.

---

## Ús des del codi font

### Instal·lació

```bash
# Clonar el repositori
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Crear entorn virtual (si no existeix)
python -m venv .venv

# Activar l'entorn
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Instal·lar dependències
pip install -r requirements.txt
```

### Configurar el token API

Crea un fitxer `.env` a l'arrel del projecte (còpia de `.env.example`):

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

### Executar mode gràfic

```bash
python main_gui.py
```

### Executar mode consola

```bash
python main.py
```

---

## Flux d'enviament

1. **Token API** — Es llegeix del `.env` o es demana a l'usuari.
2. **Assumpte** — L'usuari introdueix l'assumpte del correu.
3. **Plantilla** — Es mostra la llista de plantilles d'email disponibles.
4. **Remitent** — Es mostra la llista d'adreces d'enviament verificades.
5. **Grup** — Es mostra una primera pàgina de grups de l'agenda. Si el grup buscat no hi apareix, es pot filtrar pel nom. Els grups sense contactes es mostren, però no es poden seleccionar.
6. **Camp adjunt** — Es tria quin camp personalitzat conté la URL de l'adjunt.
7. **Certificat** — L'usuari decideix si certificar els enviaments.
8. **Enviament** — Es filtren els contactes amb email i URL d'adjunt vàlids, i s'envia un correu per cada un a raó de 5/minut.

---

## Ruta de l'adjunt al camp personalitzat

El camp personalitzat triat al pas 6 pot indicar l'adjunt de cada contacte de dues maneres:

- **URL completa**, que comença per `http://` o `https://` (per exemple, `https://cdn.empresa.com/docs/factura_42.pdf`). Es fa servir tal qual.
- **Nom de fitxer o ruta relativa** (per exemple, `factura_42.pdf` o `2026/factura_42.pdf`). L'aplicació hi afegeix al davant una **URL base**: amb la base `https://cdn.empresa.com/docs/`, el valor `factura_42.pdf` es converteix en `https://cdn.empresa.com/docs/factura_42.pdf`.

Les dues formes es poden combinar dins del mateix grup.

La URL base es pot indicar de diverses maneres:

- Al fitxer `.env`, amb la variable `MENSAGIA_ATTACHMENT_BASE_URL`:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.empresa.com/docs/
  ```
- En el **mode gràfic**, al camp **URL base adjunts** de la primera pantalla. Si està definida al `.env`, ja apareix emplenada.
- En el **mode consola**, l'aplicació la demana només si algun contacte té una ruta relativa i la variable no és al `.env`.

> La URL base ha de ser sempre una **adreça web pública**, mai una carpeta de l'ordinador: és Mensagia qui descarrega el fitxer per adjuntar-lo al correu. Pot acabar en `/` o no; l'aplicació ho té en compte.

---

## ⚠ Avís sobre els contactes del grup

El grup s'utilitza com a **font de contactes**, no com a llista de subscripció. L'aplicació enviarà el correu a **tots els contactes que formin part del grup**, hi estiguin subscrits o no.

> La API de Mensagia no proporciona informació sobre l'estat de subscripció de cada contacte en una agenda. Si vols limitar l'enviament als subscrits, hauràs de gestionar aquesta segmentació directament a Mensagia abans de llançar l'aplicació.

---

## ⚠ Avís important sobre l'enviament

El programa **no envia els correus de forma immediata**. Per cada contacte elegible crea una configuració d'enviament individual a la plataforma Mensagia, programada per executar-se de forma escalonada:

- El **primer enviament** s'executa entre **10 i 20 minuts** després de llançar l'aplicació, per donar marge a cancel·lar si es detecta algun error.
- Els **enviaments següents** s'espaiïen **12 segons** entre ells (5 per minut).

> **Si cal aturar l'enviament un cop iniciat**, tancar l'aplicació atura la creació de noves configuracions, però les que ja s'han creat s'enviaran igualment: hauràs d'eliminar-les una per una des del portal de Mensagia. No hi ha cap botó de cancel·lació global. Més endavant podràs reprendre l'enviament (vegeu [Reprendre un enviament interromput](#reprendre-un-enviament-interromput)).
>
> Fes servir el mode **Simular** per revisar què s'enviaria sense crear cap configuració real.

---

## Simular un enviament

El botó **Simular** (en el mode consola, la resposta `Sim`) fa totes les comprovacions d'un enviament real (contactes aptes, URL dels adjunts i que es puguin descarregar), però **no programa cap correu** a Mensagia ni modifica el progrés desat per [reprendre un enviament](#reprendre-un-enviament-interromput).

Cada simulació genera un log amb el mateix contingut que el d'un enviament real: els contactes a qui s'enviaria el correu i els descartats, amb el motiu. En acabar, l'aplicació mostra la ruta del fitxer.

- Els logs es desen a la carpeta `logs/` de la [carpeta de dades de l'aplicació](#fitxers-de-laplicació).
- Els de les simulacions es diuen `mensagia_simulation_<data_hora>.log`, i els dels enviaments reals, `mensagia_send_<data_hora>.log`. Si ordenes la carpeta per nom, queden separats.
- La primera línia d'un log de simulació és `[SIMULATION] This is a simulation: no email was sent.` En aquest log, les línies `[SEND_OK]` són els correus que s'enviarien.

Motius de descart (`reason=` a les línies `[SEND_SKIP]`):

- `no_email`: el contacte no té adreça de correu.
- `no_attachment`: el camp personalitzat de l'adjunt és buit.
- `already_sent`: el contacte ja va rebre el correu en un enviament anterior interromput de la mateixa campanya.

Les línies `[SEND_ERROR]` corresponen a contactes aptes l'adjunt dels quals no s'ha pogut preparar (per exemple, una ruta relativa sense URL base o un fitxer que no es pot descarregar).

Quan **cap contacte del grup és apte** (o tots ja han rebut el correu en un enviament anterior), no es pot enviar, però sí simular: el log permet esbrinar per què s'ha descartat cada contacte. En el mode gràfic, el botó **Enviar** queda desactivat; en el mode consola, l'aplicació només ofereix la simulació.

---

## Reprendre un enviament interromput

Si un enviament s'interromp a mitges (es tanca l'aplicació, es talla la connexió, s'apaga l'ordinador…), l'aplicació recorda a quins contactes ja se'ls ha programat el correu.

En tornar a preparar **la mateixa campanya** (mateix grup, plantilla i camp adjunt, i **exactament el mateix assumpte**), en arribar al resum l'aplicació avisa que hi ha un enviament anterior incomplet i pregunta què cal fer:

- **Continuar**: només s'envia als contactes pendents. Els seus correus es programen a continuació dels de l'enviament anterior, sense solapar-s'hi.
- **No continuar**: es descarta l'enviament anterior i es torna a enviar a tots els contactes, inclosos els que ja l'han rebut.

### Possibles duplicats

Si la interrupció es produeix just mentre es programava un correu, o si Mensagia no arriba a respondre, l'aplicació no pot saber si aquell correu va quedar programat. En aquest cas el torna a programar, però avisa:

- En reprendre, l'avís indica el destinatari i la data i hora a revisar.
- En acabar, indica si hi ha un **possible duplicat** (el correu s'ha programat ara, però potser també abans) o un enviament **no confirmat**.

L'API de Mensagia no permet consultar els enviaments programats, així que aquesta comprovació s'ha de fer a mà al portal, eliminant la programació sobrant.

> El progrés es desa al fitxer `send_progress.json`, a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació). Quan un enviament acaba sense errors, la campanya s'esborra del fitxer. No l'eliminis mentre hi hagi un enviament pendent de reprendre.

---

## Memòria de seleccions (mode gràfic)

Després de cada enviament o simulació, l'aplicació desa els paràmetres escollits
(plantilla, remitent, grup, camp adjunt i certificat) en un fitxer
`last_selections.json`, a la [carpeta de dades de l'aplicació](#fitxers-de-laplicació).

En la propera execució, aquestes opcions quedaran marcades per defecte.

> Per esborrar aquesta memòria, elimina el fitxer `last_selections.json`.
> L'aplicació funciona amb normalitat si el fitxer no existeix.

---

## Idiomes de la interfície

La interfície detecta automàticament l'idioma del sistema operatiu.  
Idiomes disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar els executables

Els executables es generen automàticament amb GitHub Actions (`.github/workflows/build-release.yml`). El PyInstaller no pot compilar per a un altre sistema, així que cada versió es compila en una màquina del sistema corresponent: Windows, Mac amb Apple Silicon i Mac amb Intel.

- **En pujar un tag `vX.Y.Z`**, el workflow compila les tres versions i crea un **esborrany de release** amb els sis fitxers adjunts. Després es redacten les notes i es publica.
- **A mà**, des de la pestanya **Actions** → **Run workflow**, compila les tres versions sense crear cap release i deixa els fitxers per descarregar a la mateixa execució (apartat **Artifacts**).

> Si la compilació per a Mac amb Intel falla perquè GitHub ja ha retirat aquestes màquines, l'esborrany de release es crea igualment amb els fitxers de Windows i d'Apple Silicon.

---

## Executar els tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Estructura del projecte

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entitats i ports (interfícies)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Lògica de calendarització
│   ├── application/
│   │   └── use_cases/      # Casos d'ús
│   └── infrastructure/
│       ├── api/             # Client i adaptadors de la API Mensagia
│       ├── config/          # Càrrega de configuració (.env)
│       ├── logging/         # Escriptura dels logs d'enviament
│       ├── persistence/     # Desament del progrés dels enviaments
│       └── ui/
│           ├── console/     # Interfície de consola
│           ├── gui/         # Interfície gràfica (customtkinter)
│           └── locales/     # Traduccions
├── tests/
├── main.py                 # Punt d'entrada consola
├── main_gui.py             # Punt d'entrada gràfic
├── .github/workflows/      # Compilació dels executables (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
