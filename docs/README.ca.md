# Mensagia Attachment Mailer

Aplicació per enviar correus electrònics amb adjunts personalitzats per contacte fent servir la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Galego](README.gl.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisits

- Windows 10/11 (per a l'executable)
- O Python 3.11+ (per executar des del codi font)

---

## Ús de l'executable (clients sense Python)

1. Descarrega l'executable des de la [pàgina de releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) (`mensagia-mailer-gui.exe` per al mode gràfic, o `mensagia-mailer-console.exe` per al mode consola)
2. Crea un fitxer `.env` a la **mateixa carpeta** que el `.exe` amb el teu token:

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

> Pots obtenir el teu token API a [mensagia.com](https://mensagia.com) → Usuaris.
> Si no existeix el fitxer `.env`, l'aplicació et demanarà el token en arrencar.

3. Executa el `.exe`.

> **Avís de Windows SmartScreen:** la primera vegada que executis el fitxer, el Windows pot mostrar un avís de seguretat. Fes clic a **"Més informació"** i després a **"Executa de totes maneres"**. Només cal fer-ho una vegada per cada versió descarregada.

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

> El progrés es desa al fitxer `send_progress.json`, a la mateixa carpeta que el `.env` o l'`.exe`. Quan un enviament acaba sense errors, la campanya s'esborra del fitxer. No l'eliminis mentre hi hagi un enviament pendent de reprendre.

---

## Memòria de seleccions (mode gràfic)

Després de cada enviament o simulació, l'aplicació desa els paràmetres escollits
(plantilla, remitent, grup, camp adjunt i certificat) en un fitxer
`last_selections.json`, a la mateixa carpeta que el `.env` o el `.exe`.

En la propera execució, aquestes opcions quedaran marcades per defecte.

> Per esborrar aquesta memòria, elimina el fitxer `last_selections.json`.
> L'aplicació funciona amb normalitat si el fitxer no existeix.

---

## Idiomes de la interfície

La interfície detecta automàticament l'idioma del sistema operatiu.  
Idiomes disponibles: **Español, Català, Galego, Euskera, English**.

---

## Generar l'executable

Requereix les dependències de desenvolupament:

```bash
pip install -r requirements-dev.txt
```

Executa l'script de compilació:

```bash
build.bat
```

Els fitxers `.exe` es generen a la carpeta `dist/`.

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
│       ├── logging/         # Registre d'enviaments (logs)
│       ├── persistence/     # Progrés dels enviaments (send_progress.json)
│       └── ui/
│           ├── console/     # Interfície de consola
│           ├── gui/         # Interfície gràfica (customtkinter)
│           └── locales/     # Traduccions
├── tests/
├── main.py                 # Punt d'entrada consola
├── main_gui.py             # Punt d'entrada gràfic
├── build.bat               # Script de compilació a .exe
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
