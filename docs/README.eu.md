# Mensagia Attachment Mailer

[Mensagiaren API](https://api.mensagia.com/docs/v1) erabiliz, kontaktu bakoitzari eranskin pertsonalizatuekin mezu elektronikoak bidaltzeko aplikazioa.

> Bertsioak: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [English](README.en.md)

---

## Eskakizunak

- Windows 10/11 (exekutagarria erabiltzeko)
- Edo Python 3.11+ (iturburu-kodea erabiltzeko)

---

## Exekutagarriaren erabilera (Pythonik gabeko bezeroak)

1. Deskargatu `mensagia-mailer-gui.exe` (edo `mensagia-mailer-console.exe`)
2. Sortu `.env` fitxategi bat `.exe`-aren **karpeta berean**, zure tokenarekin:

```
MENSAGIA_API_TOKEN=zure_api_tokena_hemen
```

> Zure API tokena [mensagia.com](https://mensagia.com) → Erabiltzaileak atalean lor dezakezu.
> `.env` fitxategia ez badago, aplikazioak tokena eskatuko dizu abiatzean.

3. Exekutatu `.exe`.

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
5. **Taldea** — Agenda-taldeen zerrenda erakusten da.
6. **Eranskin eremua** — Eranskinaren URLa duen eremu pertsonalizatua aukeratzen da.
7. **Ziurtagiria** — Erabiltzaileak bidalketak ziurtatzea erabakitzen du.
8. **Bidalketa** — Email eta eranskin URL balioduna duten kontaktuak iragazten dira, eta minutuko 5eko abiaduran mezu bat bidaltzen da bakoitzari.

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
