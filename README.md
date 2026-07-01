# Coding Rat Vault

Coding Rat Vault is a local-first desktop password manager built around Rory's
Coding Rat / Rat Mode identity: dark, focused, technical, and cleanly usable.
The current build is a PyQt5 application with a real encrypted SQLite vault,
modular backend services, and Rat Mode visual direction.

The repository is public. Do not commit real vault databases, exported backups,
environment files, private keys, API tokens, certificates, or personal secrets.

## Current Status

This is now a functional encrypted-vault foundation, not just a UI prototype.

- Branded PyQt5 login portal and unlocked dashboard.
- Create/unlock flow for a local encrypted vault.
- SQLite-backed encrypted storage outside the public repo by default.
- AES-256-GCM with PBKDF2-SHA256 key derivation.
- Versioned ciphertext envelopes with authenticated data per field.
- Encrypted service, account, username, password, URL, notes, and custom fields.
- Folder and entry-type tables based on the Kitty Cyber Vault feature set.
- Add/edit/delete workflows that persist encrypted records.
- Custom-field editor UI with encrypted key-value fields.
- Folder manager with add, rename, and delete flows.
- Searchable vault list, folder map, credential detail view, and copy actions.
- Secure clipboard helper that clears copied values after 30 seconds if unchanged.
- Password generator screen.
- Security posture screen with activity log and async HIBP k-anonymity breach checks.
- Password health dashboard for weak, reused, and incomplete records.
- Settings screen with import, export, restore, folder, travel, preferences, and
  self-destruct controls.
- Encrypted Rat `.ratvault` exports with passphrase confirmation.
- Backup restore UI that replaces local records from a selected backup.
- Travel Mode with full encrypted backup creation, travel-safe record retention,
  and backup restore.
- Preferences for auto-lock, clipboard clear timing, and username masking.
- Optional failed-unlock self-destruct controls plus manual typed confirmation.
- Import support for Rat `.ratvault` and `.rattravel`, CSV, JSON, folders of
  supported files, and Kitty V1 `.cvbak` files when the old backup passphrase is
  provided.

## Local Vault Storage

By default, runtime data is stored outside this repository:

```text
~/.local/share/coding-rat-vault/rat-mode.vault.sqlite3
```

Environment overrides:

```bash
RAT_VAULT_DB_PATH=/path/to/vault.sqlite3
RAT_VAULT_HOME=/path/to/private/runtime-dir
```

The `.gitignore` also blocks local database, vault, backup, export, key,
certificate, log, and environment files if runtime data is ever placed under the
repo during development.

## Demo Account

Use `Fill Demo`, or enter:

```text
Access ID: rat@vault.local
Passphrase: ratmode-demo-2026
```

The demo account opens an isolated demo database at:

```text
~/.local/share/coding-rat-vault/rat-mode-demo.vault.sqlite3
```

These credentials are public dummy data for UI and workflow testing. They do not
unlock the private default vault.

## Run

From the project root:

```bash
./run.sh
```

or:

```bash
python3 -m app.main
```

## Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

## Project Layout

```text
app/
  main.py                         PyQt5 shell and Rat Mode UI composition
  core/
    crypto.py                     PBKDF2 + AES-GCM vault crypto
    database.py                   SQLite schema and encrypted CRUD
    import_export.py              Rat/CSV/JSON/Kitty import and export helpers
    models.py                     Shared credential models
    paths.py                      Private runtime path handling
    security/
      breach.py                   HIBP k-anonymity password checks
  gui/
    controllers/
      vault_controller.py         App-facing vault session controller
    widgets/
      clipboard.py                Secure clipboard helper
assets/
  coding-rat-reference.png
  coding-rat-wallpaper.png
requirements.txt
run.sh
```

## Workflow

1. Launch the app.
2. Select `Create`.
3. Choose an access ID and master passphrase.
4. Add credentials from the Vault or Overview screens.
5. Use Settings to import, restore, export encrypted backups, configure Travel
   Mode, and tune local security preferences.
6. Lock the vault when finished.

For a quick UI pass, click `Fill Demo` on the login screen and unlock the
isolated demo vault.

## Public Repo Safety

Before committing future work, run:

```bash
git status --short
rg -n --hidden -S "(PRIVATE KEY|AWS_SECRET|AKIA|github_pat_|ghp_|sk-|token|secret|api[_-]?key)" . -g '!assets/**'
```

## Product Direction

The next build slices should keep Rat Mode's restrained interface while deepening
the password-manager surface:

- Master password rotation with full re-encryption tests.
- Auto-lock based on global input events.
- Optional migration assistant for previous Kitty vault databases.
- Per-entry breach and rotation history.
- Tray and single-instance behavior.
