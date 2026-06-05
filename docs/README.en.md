# Mensagia Attachment Mailer

Application to send emails with per-contact personalised attachments using the [Mensagia API](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [Euskera](README.eu.md)

---

## Requirements

- Windows 10/11 (for the executable)
- Or Python 3.11+ (to run from source)

---

## Using the executable (clients without Python)

1. Download `mensagia-mailer-gui.exe` (or `mensagia-mailer-console.exe`)
2. Create a `.env` file in the **same folder** as the `.exe` with your token:

```
MENSAGIA_API_TOKEN=your_api_token_here
```

> You can get your API token at [mensagia.com](https://mensagia.com) → Users.
> If the `.env` file does not exist, the app will ask for the token on startup.

3. Run the `.exe`.

---

## Running from source

### Installation

```bash
# Clone the repository
git clone https://github.com/sinermedia/mensagia-attachment-mailer.git
cd mensagia-attachment-mailer

# Create virtual environment (if it doesn't exist)
python -m venv .venv

# Activate the environment
.venv\Scripts\activate     # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### Configure the API token

Create a `.env` file at the project root (copy of `.env.example`):

```
MENSAGIA_API_TOKEN=your_api_token_here
```

### Run in GUI mode

```bash
python main_gui.py
```

### Run in console mode

```bash
python main.py
```

---

## Sending flow

1. **API token** — Read from `.env` or prompted from the user.
2. **Subject** — The user enters the email subject.
3. **Template** — The list of available email templates is shown.
4. **Sender** — The list of verified sender addresses is shown.
5. **Group** — The list of contact groups is shown.
6. **Attachment field** — Choose which custom field contains the attachment URL.
7. **Certified** — The user decides whether to certify the sends.
8. **Send** — Contacts with a valid email and attachment URL are filtered, and one email is sent per contact at a rate of 5/minute.

---

## ⚠ Note about group contacts

The group is used as a **contact source**, not as a subscription list. The app will send the email to **all contacts that belong to the group**, regardless of whether they are subscribed to it or not.

> The Mensagia API does not provide subscription status information for individual contacts within an agenda. If you want to limit sending to subscribed contacts only, you must manage that segmentation directly in Mensagia before running the application.

---

## ⚠ Important warning about sending

The program **does not send emails immediately**. For each eligible contact it creates an individual send configuration on the Mensagia platform, scheduled to run in a staggered sequence:

- The **first send** is executed between **10 and 20 minutes** after launching the application, to allow time to cancel if an error is detected.
- **Subsequent sends** are spaced **12 seconds** apart (5 per minute).

> **If you need to stop the send once it has started**, you must delete each send configuration individually from the Mensagia portal. There is no global cancel button.
>
> Use **Simulate** mode to review what would be sent without creating any real configurations.

---

## Selection memory (GUI mode)

After each send or simulation, the app saves the chosen parameters
(template, sender, group, attachment field and certified) to a file
`last_selections.json`, in the same folder as the `.env` or the `.exe`.

On the next run, those options will be pre-selected by default.

> To clear this memory, delete the `last_selections.json` file.
> The app works normally if the file does not exist.

---

## Interface languages

The interface automatically detects the operating system language.  
Available languages: **Español, Català, Galego, Euskera, English**.

---

## Building the executable

Requires the development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the build script:

```bash
build.bat
```

The `.exe` files are generated in the `dist/` folder.

---

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

---

## Project structure

```
mensagia-attachment-mailer/
├── src/
│   ├── domain/              # Entities and ports (interfaces)
│   │   ├── entities/
│   │   ├── ports/
│   │   └── scheduling.py   # Scheduling logic
│   ├── application/
│   │   └── use_cases/      # Use cases
│   └── infrastructure/
│       ├── api/             # Mensagia API client and adapters
│       ├── config/          # Configuration loading (.env)
│       └── ui/
│           ├── console/     # Console interface
│           ├── gui/         # Graphical interface (customtkinter)
│           └── locales/     # Translations
├── tests/
├── main.py                 # Console entry point
├── main_gui.py             # GUI entry point
├── build.bat               # Build script to .exe
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
