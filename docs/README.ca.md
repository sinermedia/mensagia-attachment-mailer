# Mensagia Attachment Mailer

Aplicació per enviar correus electrònics amb adjunts personalitzats per contacte fent servir la [API de Mensagia](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Galego](README.gl.md) · [Euskera](README.eu.md) · [English](README.en.md)

---

## Requisits

- Windows 10/11 (per a l'executable)
- O Python 3.11+ (per executar des del codi font)

---

## Ús de l'executable (clients sense Python)

1. Descarrega `mensagia-mailer-gui.exe` (o `mensagia-mailer-console.exe`)
2. Crea un fitxer `.env` a la **mateixa carpeta** que el `.exe` amb el teu token:

```
MENSAGIA_API_TOKEN=el_teu_token_api_aqui
```

> Pots obtenir el teu token API a [app.mensagia.com](https://app.mensagia.com) → Configuració → API.
> Si no existeix el fitxer `.env`, l'aplicació et demanarà el token en arrencar.

3. Executa el `.exe`.

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
5. **Grup** — Es mostra la llista de grups de l'agenda.
6. **Camp adjunt** — Es tria quin camp personalitzat conté la URL de l'adjunt.
7. **Certificat** — L'usuari decideix si certificar els enviaments.
8. **Enviament** — Es filtren els contactes amb email i URL d'adjunt vàlids, i s'envia un correu per cada un a raó de 5/minut.

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
