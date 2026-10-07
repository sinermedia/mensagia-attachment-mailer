# Mensagia Attachment Mailer

Application to send emails with per-contact personalised attachments using the [Mensagia API](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [Euskera](README.eu.md)

---

## Requirements

- Windows 10/11 (for the executable)
- Or Python 3.11+ (to run from source)

---

## Using the executable (clients without Python)

1. Download the executable from the [releases page](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest) (`mensagia-mailer-gui.exe` for GUI mode, or `mensagia-mailer-console.exe` for console mode)
2. Create a `.env` file in the **same folder** as the `.exe` with your token:

```
MENSAGIA_API_TOKEN=your_api_token_here
```

> You can get your API token at [mensagia.com](https://mensagia.com) → Users.
> If the `.env` file does not exist, the app will ask for the token on startup.

3. Run the `.exe`.

> **Windows SmartScreen warning:** the first time you run the file, Windows may show a security warning. Click **"More info"** and then **"Run anyway"**. This only needs to be done once per downloaded version.

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
5. **Group** — A first page of contact groups is shown. If the group you need is not there, you can filter by name. Groups without contacts are shown but cannot be selected.
6. **Attachment field** — Choose which custom field contains the attachment URL.
7. **Certified** — The user decides whether to certify the sends.
8. **Send** — Contacts with a valid email and attachment URL are filtered, and one email is sent per contact at a rate of 5/minute.

---

## Attachment path in the custom field

The custom field chosen in step 6 can specify each contact's attachment in two ways:

- **Full URL**, starting with `http://` or `https://` (for example, `https://cdn.example.com/docs/invoice_42.pdf`). It is used as is.
- **File name or relative path** (for example, `invoice_42.pdf` or `2026/invoice_42.pdf`). The app prepends a **base URL** to it: with the base `https://cdn.example.com/docs/`, the value `invoice_42.pdf` becomes `https://cdn.example.com/docs/invoice_42.pdf`.

Both forms can be mixed within the same group.

The base URL can be provided in several ways:

- In the `.env` file, with the `MENSAGIA_ATTACHMENT_BASE_URL` variable:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.example.com/docs/
  ```
- In **GUI mode**, in the **Attachment base URL** field on the first screen. If it is set in `.env`, it appears already filled in.
- In **console mode**, the app asks for it only if some contact has a relative path and the variable is not set in `.env`.

> The base URL must always be a **public web address**, never a folder on your computer: Mensagia is the one that downloads the file to attach it to the email. It may end in `/` or not; the app handles both.

---

## ⚠ Note about group contacts

The group is used as a **contact source**, not as a subscription list. The app will send the email to **all contacts that belong to the group**, regardless of whether they are subscribed to it or not.

> The Mensagia API does not provide subscription status information for individual contacts within an agenda. If you want to limit sending to subscribed contacts only, you must manage that segmentation directly in Mensagia before running the application.

---

## ⚠ Important warning about sending

The program **does not send emails immediately**. For each eligible contact it creates an individual send configuration on the Mensagia platform, scheduled to run in a staggered sequence:

- The **first send** is executed between **10 and 20 minutes** after launching the application, to allow time to cancel if an error is detected.
- **Subsequent sends** are spaced **12 seconds** apart (5 per minute).

> **If you need to stop the send once it has started**, closing the app stops new configurations from being created, but those already created will still be sent: you must delete each one individually from the Mensagia portal. There is no global cancel button. You can resume the send later (see [Resuming an interrupted send](#resuming-an-interrupted-send)).
>
> Use **Simulate** mode to review what would be sent without creating any real configurations.

---

## Resuming an interrupted send

If a send is interrupted halfway (the app is closed, the connection drops, the computer shuts down…), the app remembers which contacts have already had their email scheduled.

When you prepare **the same campaign** again (same group, template and attachment field, and **exactly the same subject**), on reaching the summary the app warns that there is an incomplete previous send and asks what to do:

- **Continue**: only the pending contacts are sent to. Their emails are scheduled after those of the previous send, without overlapping them.
- **Don't continue**: the previous send is discarded and the email is sent again to all contacts, including those who already received it.

### Possible duplicates

If the interruption happens right while an email was being scheduled, or if Mensagia does not respond, the app cannot know whether that email was scheduled. In that case it schedules it again, but warns you:

- When resuming, the warning shows the recipient and the date and time to check.
- When finished, it reports whether there is a **possible duplicate** (the email has been scheduled now, but perhaps also before) or an **unconfirmed** send.

The Mensagia API does not allow querying scheduled sends, so this check must be done manually in the portal, deleting the extra scheduled send.

> Progress is saved in the `send_progress.json` file, in the same folder as the `.env` or the `.exe`. When a send finishes without errors, the campaign is removed from the file. Do not delete it while there is a send waiting to be resumed.

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
│       ├── logging/         # Writing of send logs
│       ├── persistence/     # Saving of send progress
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
