# Coding Rat Vault

Coding Rat Vault is the start of a new local-first password manager built around
Rory's Coding Rat / Rat Mode identity: dark, focused, technical, and cleanly
usable. The current build is a PyQt5 desktop prototype with the login portal and
post-login dashboard shell in place.

The repository is public. Do not commit real vault databases, exported backups,
environment files, private keys, API tokens, certificates, or personal secrets.

## Current Status

This is an early UI foundation, not a production password manager yet.

- Branded PyQt5 login portal.
- Post-login dashboard shell.
- Local Coding Rat visual assets.
- Unlock and create-vault modes.
- Dummy account for local UI testing.
- Dashboard navigation, vault overview, empty-state table, quick actions, and
  security posture panels.
- Dedicated Vault view with searchable session credentials and a detail pane.
- Folder tree navigation for jumping between vault lanes.
- Add Entry workflow that creates in-memory session credentials.
- No real encrypted vault persistence yet.
- No real user credentials are stored by this prototype.

## Dummy Account

Use the `Fill Demo` button on the login screen, or enter:

```text
Access ID: rat@vault.local
Passphrase: ratmode-demo-2026
```

This credential is intentionally public demo data. It only unlocks the local UI
prototype and does not protect or expose any real vault contents.

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

The app currently depends on PyQt5.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

## Project Layout

```text
app/
  main.py                 PyQt5 app, login portal, dashboard shell
assets/
  coding-rat-reference.png
  coding-rat-wallpaper.png
requirements.txt
run.sh
```

## Prototype Workflow

1. Log in with the dummy account.
2. Click `Vault` in the sidebar to browse demo credentials.
3. Use the folder chips or folder tree to jump between vault lanes.
4. Click `Add Entry` or `Add Credential` to open the credential form.
5. Save an entry to add it to the current in-memory session.
6. Search or select rows in the Vault view to inspect details.

Entries created in this prototype are not written to disk yet.

## Public Repo Safety

The `.gitignore` is set up to keep local runtime data out of source control:

- SQLite databases and vault files.
- `.env` files.
- private keys and certificates.
- logs, exports, backups, and generated build folders.
- virtual environments and Python caches.

Before committing future work, run:

```bash
git status --short
rg -n --hidden -S "(PRIVATE KEY|AWS_SECRET|AKIA|github_pat_|ghp_|sk-|token|secret|api[_-]?key)" . -g '!assets/**'
```

## Product Direction

The target product is a calm, polished, local-first desktop vault:

- Master password setup and verification.
- SQLite-backed encrypted vault.
- Strong key derivation and authenticated encryption.
- Password generator.
- Searchable credential list.
- Folders or workspaces.
- Secure clipboard handling.
- Import/export with encrypted backups.
- Security health checks.
- Optional breach checks.
- Clear lock/unlock and session state.

## Design Direction

Coding Rat Vault should feel more restrained and mature than a novelty cyberpunk
tool. The brand language is black, graphite, wet asphalt, and controlled hot
magenta accents. The interface should prioritize clarity, density, and repeated
daily use over decorative clutter.
