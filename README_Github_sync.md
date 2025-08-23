# GitHub Auto Sync (Flask)

Ein leichtgewichtiges **Auto‑Commit/Auto‑Push**‑Tool mit GUI (Flask), das einen lokalen Projektordner überwacht und Änderungen gesammelt nach Git pusht. Zusätzlich legt es rotierende **Schatten‑Backups** im Projekt an und zeigt Live‑Logs sowie RAW‑Links der beobachteten Dateien an.

---

## ✨ Features

- **Datei‑Watcher** mit Debounce und Batch‑Fenster (sammelt Events und committet/pusht gebündelt).
- **Auto‑Commit & Auto‑Push** (abschaltbar) inkl. manuellem Push‑Button.
- **Schatten‑Versionierung**: Rotierende Sicherungen je Datei unter `/.auto_versions/<pfad>.history/`.
- **Filter**: Ein-/Aus­schluss über Dateiendungen und Ordnerlisten; optionale Regex‑Patterns (siehe `watch_service.py`).
- **Konfig‑Speicher**: Persistente JSON‑Config unter `~/.github_auto_sync/config.json`.
- **RAW‑Links**: Erzeugt `raw.githubusercontent.com`‑URLs passend zur konfigurierten `remote_url`+`branch`.
- **UI**: Start/Stopp, Logs, Datei‑Vorschau, Filter & Settings, Ordnerwahl über nativen Dialog.
- **Portables Startverhalten**: Optionales Auto‑Öffnen im gewünschten Browser und fester Fenstergröße (macOS/Windows/Linux).

> Kernmodule: `Flask`, `watchdog`, `GitPython`. (Siehe `requirements.txt`.)

---

## 📦 Projektstruktur (relevant)

```
app.py
models/
  └─ config.py          # DEFAULT_CONFIG & JSON‑ConfigStore (~/.github_auto_sync/config.json)
services/
  ├─ git_service.py     # Repo/Branch/Remote sicherstellen, Stage/Commit/Push
  └─ watch_service.py   # Watchdog‑Handler, Backup‑Rotation, File‑Filter, Log‑Ringpuffer
templates/
  base.html, index.html, settings.html, filters.html, preview.html
static/
  styles.css
requirements.txt
README.md
```

---

## 🚀 Installation

### 1) Umgebung

- **Python 3.10+** empfohlen.
- Abhängigkeiten installieren:
  ```bash
  pip install -r requirements.txt
  # Enthält: Flask>=3.0, GitPython>=3.1, watchdog>=4.0, rich>=13.7
  ```

### 2) Git vorbereitet?
- Ein existierendes Repo im Projektordner ist hilfreich; andernfalls initialisiert die App es automatisch.

---

## ▶️ Starten

```bash
python app.py
```
Standard: `HOST=127.0.0.1`, `PORT=5100`, Browser‑Auto‑Open **aktiv**.

**Umgebungsvariablen** (optional):
```bash
# Port/Host
export APP_HOST=0.0.0.0
export APP_PORT=5100

# Auto‑Open im neuen Fenster steuern
export APP_AUTO_OPEN=true          # true|false
export APP_BROWSER=chrome          # chrome|edge|safari|system
```

Beim ersten Start die **Einstellungen** ausfüllen (`/settings`).

---

## ⚙️ Konfiguration

Die Konfiguration wird in `~/.github_auto_sync/config.json` gespeichert. Ausgangspunkt ist `DEFAULT_CONFIG` aus `models/config.py`:

```json
{
  "project_name": "Mein Projekt",
  "project_path": "",                  // absoluter Pfad zum beobachteten Ordner
  "branch": "main",
  "remote_url": "",                    // z.B. https://github.com/<user>/<repo>.git
  "auto_commit": true,
  "auto_push": true,
  "batch_window_sec": 60,              // Sammelzeitraum für Events (Sek.)
  "debounce_ms": 600,                  // Entprellung pro Datei
  "max_backups": 10,                   // rotierende Sicherungen pro Datei
  "include_exts": [".py",".json",".md",".yml",".yaml",".ini",".toml",".sql",".js",".ts",".html",".css"],
  "exclude_dirs": ["style_check",".git",".idea",".vscode","__pycache__",".venv","venv","node_modules","dist","build",".auto_versions"],
  "wip_branch": ""                     // optionaler Arbeits‑Branch (derzeit rein informativ)
}
```

> **Hinweis:** `watch_service.py` filtert zusätzlich über `_is_watched_path` (unterhalb des Projekt‑Roots, nicht in `exclude_dirs`) und verknüpft dies mit `include_exts`. Optional können **Regex‑Patterns** für Datei‑In-/Exklusion ergänzt werden (siehe dortige Hinweise).

---

## 🖥️ UI & Endpunkte

- `/` – **Dashboard**: Logs (pollbar via `/api/logs`), Datei‑Vorschau inkl. RAW‑Links.
- `/start` (POST) – Watcher starten. Vorab werden Bytecode‑Caches (`__pycache__`, `.pyc/.pyo`) im Projekt entfernt.
- `/stop` (POST) – Watcher stoppen. Danach erneute Cache‑Bereinigung.
- `/push` (POST) – **Manueller Push** des aktuellen Branches (ohne Commit), nützlich wenn `auto_push=false`.
- `/settings` – Projektname, Pfad, Branch, Remote‑URL, Auto‑Commit/Push, Batch/Debounce/Backups konfigurieren.
- `/filters` – `include_exts` & `exclude_dirs` pflegen; Vorschau via `/preview`.
- `/preview` – Liste aktuell beobachteter Dateien (relativ zum Projekt).
- `/api/logs` – JSON: letzte Logzeilen als `text` und `lines[]`.
- `/api/raw-links` – JSON/Text: dynamische **RAW‑Links** zu beobachteten Dateien gemäß `remote_url`+`branch`.
- `/choose-folder` – Nativer Ordnerdialog (macOS via AppleScript; Win/Linux via Tkinter).

---

## 🔄 Wie wird versioniert & gepusht?

- Events werden **entprellt** (`debounce_ms`) und **gebatcht** (`batch_window_sec`).
- Beim Batch:
  1. **Staging** geänderter/gelöschter Pfade (`services/git_service.stage_paths`).
  2. **Commit** (wenn `auto_commit=true` und es Änderungen gibt).
  3. **Push** auf `origin <branch>` (wenn `auto_push=true`).
- Jede erkannte Änderung erzeugt zusätzlich (falls Datei existiert) eine Kopie in  
  `/.auto_versions/<relpath>.history/YYYYmmdd-HHMMSS<suffix>`; nur die **letzten N (`max_backups`)** bleiben erhalten.

---

## 🧪 Quickstart (Beispiel)

1. App starten: `python app.py`
2. In **Settings**:
   - `project_path` auf einen Ordner mit Git‑Repo setzen (oder leer lassen: Repo wird initiiert).
   - `remote_url` auf z. B. `https://github.com/<user>/<repo>.git`
   - `branch` auf `main` (oder eigenen Branch).
   - `auto_commit=true`, `auto_push=true` zum Voll‑Automatik‑Modus.
3. **Start** klicken. Änderungen an z. B. `README.md` vornehmen → Logs beobachten.
4. Optional: `Push` manuell auslösen (wenn Auto‑Push aus ist).

---

## 🧰 CLI/Service‑Betrieb (optional)

### Systemd (Linux)
`/etc/systemd/system/github-auto-sync.service`
```ini
[Unit]
Description=GitHub Auto Sync (Flask)
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=/opt/github_sync
Environment="APP_HOST=0.0.0.0" "APP_PORT=5100" "APP_AUTO_OPEN=false"
ExecStart=/usr/bin/python3 /opt/github_sync/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now github-auto-sync
```

### Windows (PowerShell Autostart)
```powershell
$env:APP_AUTO_OPEN="true"
$env:APP_BROWSER="edge"
python app.py
```

---

## 🧱 Packaging (PyInstaller)

Einfacher One‑Dir‑Build (inkl. Templates/Static):
```bash
pyinstaller app.py --noconfirm --onedir   --hidden-import flask --hidden-import jinja2   --add-data "templates;templates"   --add-data "static;static"
```
> Bei Git‑Operationen wird die lokal installierte **git‑CLI** verwendet (für `/push`) und/oder **GitPython** (für Commit/Status). Stelle sicher, dass `git` im `PATH` liegt.

---

## 🔐 Hinweise & Best Practices

- **Sensible Dateien ausschließen** (z. B. `.env`, Schlüssel, große Binärdateien) via `exclude_dirs` und ggf. zusätzliche regex‑Filter.
- Für **private Repos** mit HTTPS‑Remote sind Git‑Credentials nötig (Credential Manager, PAT). Mit SSH‑Remote muss der Key eingerichtet sein.
- **Konflikte/Rebases** werden nicht automatisch gelöst – das Tool eignet sich für **Ein‑Nutzer‑Flows** bzw. klar getrennte Branches.
- Prüfe Storage‑Budget: `.auto_versions` erzeugt Kopien; `max_backups` entsprechend wählen.

---

## 🐞 Troubleshooting

- **„Kein Git‑Repository im Projektordner“** beim Push → `git init`/Remote setzen oder UI‑Settings prüfen.
- **Nichts wird committet** → Prüfen, ob Dateien durch Filter ausgenommen sind (`include_exts`, `exclude_dirs`) oder keine echten Änderungen (`git status` clean).
- **Watcher startet nicht** → Pfad existiert? Ausreichende Rechte? Python‑Version? Watchdog‑Backend (FS‑Events) verfügbar?
- **RAW‑Links leer** → `remote_url` muss GitHub‑URL sein (`https://github.com/<owner>/<repo>.git` oder `git@github.com:<owner>/<repo>.git`).

---

## 📄 Lizenz

Ohne Angabe – nutze ein passendes Lizenzfile (z. B. MIT), falls gewünscht.

---

## ✍️ Changelog (Kurz)

- **v0.1.0** – Erste lauffähige Version mit Auto‑Commit/Push, Schatten‑Backups, RAW‑Links und UI.
