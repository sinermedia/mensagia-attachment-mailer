# Mensagia Attachment Mailer

Application to send emails with per-contact personalised attachments using the [Mensagia API](https://api.mensagia.com/docs/v1).

> Versions: [Español](../README.md) · [Català](README.ca.md) · [Galego](README.gl.md) · [Euskera](README.eu.md)

---

## Requirements

- Windows 10/11 or macOS (for the executables)
- Or Python 3.11+ (to run from source)

---

## Using the executable (clients without Python)

Download the version for your computer from the [releases page](https://github.com/sinermedia/mensagia-attachment-mailer/releases/latest):

| Computer | GUI mode | Console mode |
|---|---|---|
| Windows | `mensagia-mailer-gui-windows.exe` | `mensagia-mailer-console-windows.exe` |
| Mac with Apple Silicon (M1, M2…) | `mensagia-mailer-gui-macos-apple-silicon.zip` | `mensagia-mailer-console-macos-apple-silicon.zip` |
| Mac with an Intel processor | `mensagia-mailer-gui-macos-intel.zip` | `mensagia-mailer-console-macos-intel.zip` |

### API token

The app needs your Mensagia API token, which you can get at [mensagia.com](https://mensagia.com) → Users. If it is not configured, the app asks for it on startup. To avoid typing it every time, save it in a `.env` file in the [app data folder](#app-files):

```
MENSAGIA_API_TOKEN=your_api_token_here
```

### Windows

1. Download the `.exe`. The app stores its files in the same folder, so it is best to put it in a folder of its own.
2. Optionally, create the `.env` file in that **same folder**.
3. Run the `.exe`.

> **Windows SmartScreen warning:** the first time you run the file, Windows may show a security warning. Click **"More info"** and then **"Run anyway"**. This only needs to be done once per downloaded version.

### macOS

1. **Choose the version for your Mac.** Open the Apple menu → **About This Mac**:
   - If it shows **Chip** (Apple M1, M2, M3…), download the `apple-silicon` version.
   - If it shows **Processor** (Intel…), download the `intel` version.

   > GitHub is retiring the machines that build for Intel Macs. If the latest version does not include the `intel` files, download them from the most recent version that has them in the [list of releases](https://github.com/sinermedia/mensagia-attachment-mailer/releases).

2. Double-click the `.zip` to unzip it (Safari may do this automatically when downloading). In GUI mode you get `mensagia-mailer-gui.app`, which you can move to **Applications**.
3. Optionally, save the `.env` file in the **Mensagia Mailer** folder of your home folder. You can create both from Terminal:

   ```
   mkdir -p ~/"Mensagia Mailer"
   echo "MENSAGIA_API_TOKEN=your_api_token_here" > ~/"Mensagia Mailer/.env"
   ```

   > Finder hides files whose name starts with a dot, such as `.env`. Press **Cmd + Shift + .** to show or hide them.

4. Open the app. The first time, macOS blocks it because it is not signed by Apple (the equivalent of the SmartScreen warning on Windows). To allow it:
   - **macOS 15 (Sequoia) or later:** after the warning, open **System Settings → Privacy & Security**, scroll down to the message about the app and click **Open Anyway**. Open it again and confirm.
   - **macOS 14 or earlier:** right-click the app → **Open**, and confirm in the warning.
   - **On any version, from Terminal:** `xattr -cr` followed by the path to the app, for example `xattr -cr /Applications/mensagia-mailer-gui.app`.

   This only needs to be done once per downloaded version.

> The console version opens with a double-click and runs inside a Terminal window.

---

## App files

The app stores its files in a data folder, which depends on how it runs:

| Running | Data folder |
|---|---|
| Windows (`.exe`) | The same folder as the `.exe` |
| macOS | `Mensagia Mailer`, inside your home folder (`~/Mensagia Mailer`) |
| Source code | The project root |

That folder holds:

- `.env`: the configuration (API token, language, attachment base URL…). You create it, and it is optional.
- `logs/`: a log of each send and each simulation (see [Simulating a send](#simulating-a-send)).
- `last_selections.json`: the last options chosen (see [Selection memory](#selection-memory-gui-mode)).
- `send_progress.json`: the progress of sends (see [Resuming an interrupted send](#resuming-an-interrupted-send)).

The app creates the folder and the files as it needs them.

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
2. **Subject, start time and source** — The user enters the email subject, chooses when the first email goes out (see [Scheduling the start time](#scheduling-the-start-time)) and where the recipients come from: an **agenda group** or a **file** (see [Sending to the recipients of a file](#sending-to-the-recipients-of-a-file)).
3. **Template** — The list of available email templates is shown.
4. **Sender** — The list of verified sender addresses is shown.
5. **Group or file**:
   - With the agenda, a first page of contact groups is shown. If the group you need is not there, you can filter by name. Groups without contacts are shown but cannot be selected.
   - With a file, choose the file and, if it is an Excel file with several sheets, the sheet.
6. **Attachment field or columns**:
   - With the agenda, choose which custom field contains the attachment URL.
   - With a file, choose which column contains the email and which one the attachment.
7. **Certified** — The user decides whether to certify the sends.
8. **Send** — Recipients without a valid email or without an attachment are left out, and one email is sent to each of the others at a rate of 5/minute.

---

## Attachment path in the custom field

The custom field chosen in step 6 (or the attachment column, if the recipients come from a file) can specify each contact's attachment in two ways:

- **Full URL**, starting with `http://` or `https://` (for example, `https://cdn.example.com/docs/invoice_42.pdf`). It is used as is.
- **File name or relative path** (for example, `invoice_42.pdf` or `2026/invoice_42.pdf`). The app prepends a **base URL** to it: with the base `https://cdn.example.com/docs/`, the value `invoice_42.pdf` becomes `https://cdn.example.com/docs/invoice_42.pdf`.

Both forms can be mixed within the same group or file.

The base URL can be provided in several ways:

- In the `.env` file, with the `MENSAGIA_ATTACHMENT_BASE_URL` variable:
  ```
  MENSAGIA_ATTACHMENT_BASE_URL=https://cdn.example.com/docs/
  ```
- In **GUI mode**, in the **Attachment base URL** field on the first screen. If it is set in `.env`, it appears already filled in.
- In **console mode**, the app asks for it only if some contact has a relative path and the variable is not set in `.env`.

> The base URL must always be a **public web address**, never a folder on your computer: Mensagia is the one that downloads the file to attach it to the email. It may end in `/` or not; the app handles both.

---

## Sending to the recipients of a file

Besides an agenda group, the recipients can come from an **Excel (`.xlsx`)** or **CSV (`.csv`)** file. Each row of the file is one email, so the same address can receive several emails with different attachments in the same send (for example, an agency that receives the documents of several of its clients). Recipients do not need to be in the Mensagia agenda.

### What the file must look like

- **The first row is the header** and it is required: it holds the name of each column.
- Column names, order and number are free. When preparing the send you choose which column holds the email and which one the attachment; the others are ignored.
- Completely empty rows and columns are ignored.
- If the Excel file has several sheets, you choose which one to use. If it has only one, you are not asked.
- In CSV files, the separator (`;` or `,`) and the encoding (UTF-8 or the Windows one) are detected automatically.

Example:

| Client | Email | Attachment |
|---|---|---|
| Client A | agency@example.com | invoices/client_a.pdf |
| Client B | agency@example.com | invoices/client_b.pdf |
| Client C | info@clientc.com | https://cdn.company.com/docs/c.pdf |

The app does not let you continue if:

- the file is empty or only has the header;
- a column has data but no name in the header;
- two columns have the same name (ignoring case);
- a cell of the first row contains `@`: the file probably has no header.

### Email and attachment of each row

- **Email**: spaces at the start and end are removed. It must hold a single address: a single `@`; before the `@`, only unaccented letters, digits and `. _ % + -`; after it, unaccented letters, digits, `-` and at least one dot. A cell with several addresses is not valid.
- **Attachment**: as in the custom field, a full URL or a path relative to the base URL (see [Attachment path](#attachment-path-in-the-custom-field)). Numbers are read without decimals (`1234`, not `1234.0`).

These rows are left out, and the [log](#simulating-a-send) gives the reason:

- without an email (`no_email`) or with an invalid one (`invalid_email`);
- without an attachment (`no_attachment`);
- with the same email (ignoring case) and the same attachment as an earlier row (`duplicate_row`): only the first one is sent.

In the log, each row is identified by its number as Excel shows it (the header is row 1), its email and its attachment. For example:

```
[SEND_SKIP]  row=14 to=agency@example.com attachment=invoices/client_a.pdf reason=duplicate_row
```

### Changes to the file

The file is read again when reaching the summary and when the send starts, so changes saved in the meantime are used. If the file can no longer be used (for example, because a chosen column was renamed), the app says so and sends nothing.

To [resume an interrupted send](#resuming-an-interrupted-send), a send from a file is identified by the **file name** (without its folder), the sheet, the chosen columns, the template, the subject and the start mode. Therefore:

- You can move the file to another folder, fix rows, add new rows or change their order. When resuming, only the missing rows are sent, because each row is recognised by its email and its attachment.
- If you rename the file, or change the sheet or any of the columns, it is treated as a new send.

> In console mode, the file path is typed or pasted. The quotes added by Windows' "Copy as path" option are accepted.

---

## ⚠ Note about group contacts

The group is used as a **contact source**, not as a subscription list. The app will send the email to **all contacts that belong to the group**, regardless of whether they are subscribed to it or not.

> The Mensagia API does not provide subscription status information for individual contacts within an agenda. If you want to limit sending to subscribed contacts only, you must manage that segmentation directly in Mensagia before running the application.

---

## ⚠ Important warning about sending

The program **does not send emails immediately**. For each eligible contact it creates an individual send configuration on the Mensagia platform, scheduled to run in a staggered sequence:

- The **first send** is executed between **10 and 20 minutes** after starting the send, to allow time to cancel if an error is detected, or at the chosen date and time (see [Scheduling the start time](#scheduling-the-start-time)).
- **Subsequent sends** are spaced **12 seconds** apart (5 per minute).

> **If you need to stop the send once it has started**, closing the app stops new configurations from being created, but those already created will still be sent: you must delete each one individually from the Mensagia portal. There is no global cancel button. You can resume the send later (see [Resuming an interrupted send](#resuming-an-interrupted-send)).
>
> Use **Simulate** mode to review what would be sent without creating any real configurations.

---

## Scheduling the start time

On the subject page (in console mode, right after the subject) you choose when the first email goes out:

- **Now**: 10 to 20 minutes after the send starts.
- **On a specific date and time**: the first email goes out at the date and time given, and the next ones every 12 seconds. Sends may run past midnight.

The date and time are always typed in the order `dd/mm/yyyy` and `hh:mm`, whatever the language. In GUI mode there is one field per part, and the cursor moves to the next one when a field is complete. In console mode other common forms are also accepted (`8/10/26`, `8-10-2026`, `9h30`, `9`…), and Enter accepts the value proposed between brackets.

Limits:

- **10-minute minimum lead.** When moving on to the next page, the date and time must be at least 10 minutes after the current time.
- **Automatic postponement.** If, while the other steps are completed, the chosen time no longer has 10 minutes of lead, it is automatically postponed when the send starts to the first time that has it, as with the "Now" option. The app gives no warning, but the send log shows the chosen time (`start_at`) and the time of the first email (`first_slot`). Emails never go out before the chosen time.
- **At most 6 weeks ahead** of the moment the send is prepared.
- The simulation does not check the time, only the data.

> ⚠ **Time zone.** The time is sent to Mensagia without a time zone, and Mensagia reads it in the **"Time zone" set on the Mensagia user** linked to the token. Check that it matches the time zone of the computer running the app: otherwise the emails will go out at a different time than the one chosen.

The app proposes today's date and, as the time, the last one chosen in GUI mode or, if there is none, the one the "Now" option would give.

To [resume an interrupted send](#resuming-an-interrupted-send) you must repeat exactly the same options, including the start mode: changing the mode makes it a new send. Changing the date or time, on the other hand, does not create a new send: when resuming, emails continue after the last one scheduled, and the new time is only used if that moment no longer has 10 minutes of lead.

---

## Simulating a send

The **Simulate** button (in console mode, the answer `Sim`) runs every check of a real send (eligible contacts, attachment URLs and whether they can be downloaded), but **schedules no email** in Mensagia and leaves the progress saved for [resuming a send](#resuming-an-interrupted-send) untouched.

Each simulation writes a log with the same content as a real send: the contacts that would receive the email and the ones left out, with the reason. When it finishes, the app shows the path of the file.

- Logs are saved in the `logs/` folder of the [app data folder](#app-files).
- Simulation logs are named `mensagia_simulation_<date_time>.log`, and real send logs, `mensagia_send_<date_time>.log`. Sorting the folder by name keeps them apart.
- The first line of a simulation log is `[SIMULATION] This is a simulation: no email was sent.` In it, the `[SEND_OK]` lines are the emails that would be sent.

Skip reasons (`reason=` in the `[SEND_SKIP]` lines):

- `no_email`: the contact or row has no email address.
- `invalid_email`: the email address of the row is not valid (only with a file).
- `no_attachment`: the attachment custom field or column is empty.
- `duplicate_row`: the row repeats the email and the attachment of an earlier row (only with a file).
- `already_sent`: the recipient already received the email in a previous, interrupted send of the same campaign.

The `[SEND_ERROR]` lines are eligible contacts whose attachment could not be prepared (for example, a relative path without a base URL, or a file that cannot be downloaded).

When **no contact in the group or row of the file is eligible** (or all of them already received the email in a previous send), sending is not possible but simulating is: the log shows why each one was left out. In GUI mode the **Send** button stays disabled; in console mode the app only offers the simulation. Also, after a simulation, GUI mode only offers the **Send** button if some email would be sent (for example, it is not offered when no attachment can be downloaded).

---

## Resuming an interrupted send

If a send is interrupted halfway (the app is closed, the connection drops, the computer shuts down…), the app remembers which contacts have already had their email scheduled.

When you prepare **the same campaign** again (same group —or same file, sheet and email column—, template, attachment field or column and start mode, and **exactly the same subject**), on reaching the summary the app warns that there is an incomplete previous send and asks what to do:

- **Continue**: only the pending contacts are sent to. Their emails are scheduled after those of the previous send, without overlapping them.
- **Don't continue**: the previous send is discarded and the email is sent again to all contacts, including those who already received it.

### Possible duplicates

If the interruption happens right while an email was being scheduled, or if Mensagia does not respond, the app cannot know whether that email was scheduled. In that case it schedules it again, but warns you:

- When resuming, the warning shows the recipient and the date and time to check.
- When finished, it reports whether there is a **possible duplicate** (the email has been scheduled now, but perhaps also before) or an **unconfirmed** send.

The Mensagia API does not allow querying scheduled sends, so this check must be done manually in the portal, deleting the extra scheduled send.

> Progress is saved in the `send_progress.json` file, in the [app data folder](#app-files). When a send finishes without errors, the campaign is removed from the file. Do not delete it while there is a send waiting to be resumed.

---

## Selection memory (GUI mode)

After each send or simulation, the app saves the chosen parameters
(recipient source, template, sender, group, attachment field, folder of the last file,
email and attachment columns, certified, and the start mode and time) to a file
`last_selections.json`, in the [app data folder](#app-files).

On the next run, those options will be pre-selected by default. The columns are only selected if
the new file has columns with those names. The file and the sheet are not remembered: the file
picker opens in the folder of the last one used.

> To clear this memory, delete the `last_selections.json` file.
> The app works normally if the file does not exist.

---

## Interface languages

The interface automatically detects the operating system language.  
Available languages: **Español, Català, Galego, Euskera, English**.

---

## Building the executables

The executables are built automatically with GitHub Actions (`.github/workflows/build-release.yml`). PyInstaller cannot build for another system, so each version is built on a machine of the matching system: Windows, Mac with Apple Silicon and Mac with Intel.

- **When a `vX.Y.Z` tag is pushed**, the workflow builds the three versions and creates a **draft release** with the six files attached. The notes are then written and the release is published.
- **Manually**, from the **Actions** tab → **Run workflow**, it builds the three versions without creating any release and leaves the files to download in the run itself (**Artifacts** section).

> If the Intel Mac build fails because GitHub has already retired those machines, the draft release is still created with the Windows and Apple Silicon files.

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
│       ├── files/           # Reading of Excel and CSV files
│       ├── logging/         # Writing of send logs
│       ├── persistence/     # Saving of send progress
│       ├── recipients/      # Recipient sources (agenda or file)
│       └── ui/
│           ├── console/     # Console interface
│           ├── gui/         # Graphical interface (customtkinter)
│           └── locales/     # Translations
├── tests/
├── main.py                 # Console entry point
├── main_gui.py             # GUI entry point
├── .github/workflows/      # Executable builds (GitHub Actions)
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```
