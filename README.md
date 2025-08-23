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
- **Mirror on Start**: Option, beim Start den Projektordner als Snapshot zwangsweise nach GitHub zu spiegeln.
- **Flash‑Meldungen**: Feedback (z. B. „Watcher gestartet“) wird automatisch nach konfigurierbarer Zeit ausgeblendet.

> Kernmodule: `Flask`, `watchdog`, `GitPython`. (Siehe `requirements.txt`).

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
LICENSE
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

| Schlüssel           | Typ      | Standard | Beschreibung |
|---------------------|---------|----------|--------------|
| `project_name`      | str     | ""       | Anzeigename |
| `project_path`      | str     | ""       | Absoluter Pfad zum Projekt |
| `branch`            | str     | "main"   | Zielbranch |
| `remote_url`        | str     | ""       | z. B. `https://github.com/<user>/<repo>.git` |
| `auto_commit`       | bool    | true     | Automatisch commiten |
| `auto_push`         | bool    | true     | Automatisch pushen |
| `batch_window_sec`  | float   | 60       | Sammelfenster (Sekunden) |
| `debounce_ms`       | int     | 600      | Entprellung (ms) |
| `max_backups`       | int     | 10       | Anzahl Backup‑Versionen pro Datei |
| `include_exts`      | list    | \[...]   | erlaubte Dateiendungen (inkl. `Dockerfile`) |
| `exclude_dirs`      | list    | \[...]   | ausgeschlossene Ordner |
| `wip_branch`        | str     | ""       | optionaler Arbeits‑Branch |
| `mirror_on_start`   | bool    | false    | Erzwingt Force‑Push beim Start |
| `flash_duration_sec`| int     | 10       | Sekunden bis Flash‑Meldungen ausgeblendet werden |

> **Hinweis:** `watch_service.py` filtert zusätzlich über `_is_watched_path` (unterhalb des Projekt‑Roots, nicht in `exclude_dirs`). Optional: Regex‑Patterns für Datei‑In-/Exklusion.

---

## 🖥️ UI & Endpunkte

- `/` – Dashboard mit Logs & RAW‑Links.
- `/start` – Watcher starten (+ Cache‑Bereinigung, optional Mirror).
- `/stop` – Watcher stoppen (+ Cache‑Bereinigung).
- `/push` – Manueller Push (nur sinnvoll wenn Auto‑Push aus).
- `/settings` – Projektname, Pfad, Branch, Remote‑URL, Auto‑Commit/Push, Batch/Debounce/Backups, Mirror on Start, Flash‑Timeout.
- `/filters` – `include_exts` & `exclude_dirs` pflegen.
- `/preview` – Liste aktuell beobachteter Dateien.
- `/api/logs` – Letzte Logzeilen als JSON.
- `/api/raw-links` – Aktuelle RAW‑Links als JSON.
- `/choose-folder` – Nativer Ordnerdialog (macOS/AppleScript, Windows/Linux/Tkinter).

---

## 🔄 Wie wird versioniert & gepusht?

1. Events werden entprellt und gesammelt.
2. Nach Ablauf des Batch‑Fensters:
   - Geänderte/gelöschte Dateien werden gestaged (`stage_paths`).
   - Commit (falls `auto_commit=true`).
   - Push (falls `auto_push=true`).
3. Schatten‑Backups werden rotiert (`max_backups`).

**Mirror on Start** überschreibt den Remote‑Branch beim Start mit dem lokalen Stand (Force‑Push mit Lease).

---

## 🧪 Quickstart

1. App starten: `python app.py`
2. Einstellungen vornehmen (`/settings`).
3. `Start` klicken → Änderungen an Dateien erzeugen → Logs prüfen.
4. Manuell pushen, wenn Auto‑Push deaktiviert ist.

---

## 🧱 Packaging (PyInstaller)

```bash
pyinstaller app.py --noconfirm --onedir   --hidden-import flask --hidden-import jinja2   --add-data "templates;templates"   --add-data "static;static"
```

---

## 🔐 Hinweise & Best Practices

- `.gitignore` lokal + Filter in `/filters` kombinierbar.
- Sensible Dateien wie `.env` oder große Binärdateien ausschließen.
- Nur für **Single‑User‑Repos** gedacht, keine Konfliktauflösung eingebaut.
- Sicherstellen, dass `git` im PATH liegt.

---

## 🐞 Troubleshooting

- „Kein Git‑Repo im Projektordner“ → `git init` + Remote konfigurieren.
- „Keine Commits“ → evtl. Dateien durch Filter ausgeschlossen.
- „RAW‑Links leer“ → Remote‑URL prüfen (`https://github.com/...` oder SSH).

---

## 📄 Lizenz

Dieses Projekt steht unter der [MIT‑Lizenz](LICENSE).
