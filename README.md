# GitHub Auto Sync (Flask)

Ein leichtgewichtiges **Auto‑Commit/Auto‑Push**‑Tool mit GUI (Flask), das einen lokalen Projektordner überwacht und Änderungen gesammelt nach Git pusht. Zusätzlich legt es rotierende **Schatten‑Backups** im Projekt an und zeigt Live‑Logs sowie RAW‑Links der beobachteten Dateien an.

---

## ✨ Features

- **Datei‑Watcher** mit Debounce und Batch‑Fenster (sammelt Events und committet/pusht gebündelt).
- **Auto‑Commit & Auto‑Push** (abschaltbar) inkl. manuellem Push‑Button.
- **Mirror‑on‑Start**: optional beim Start den lokalen Stand als Snapshot committen & pushen (überschreibt Remote).
- **Schatten‑Versionierung**: Rotierende Sicherungen je Datei unter `/.auto_versions/<pfad>.history/`.
- **Filter**: Ein-/Aus­schluss über Dateiendungen und Ordnerlisten; optionale Regex‑Patterns (siehe `watch_service.py`).
- **Konfig‑Speicher**: Persistente JSON‑Config unter `~/.github_auto_sync/config.json`.
- **RAW‑Links**: Erzeugt `raw.githubusercontent.com`‑URLs passend zur konfigurierten `remote_url`+`branch`, live aktualisiert.
- **UI**: Start/Stopp, Logs, Datei‑Vorschau, Filter & Settings, Ordnerwahl über nativen Dialog.
- **Portables Startverhalten**: Optionales Auto‑Öffnen im gewünschten Browser und fester Fenstergröße (macOS/Windows/Linux).

> Kernmodule: `Flask`, `watchdog`, `GitPython`. (Siehe `requirements.txt`.)

---

## 📦 Projektstruktur (relevant)

```
app.py
models/
  └─ config.py          
services/
  ├─ git_service.py     
  └─ watch_service.py   
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

```bash
pip install -r requirements.txt
```

---

## ▶️ Starten

```bash
python app.py
```

Standard: `HOST=127.0.0.1`, `PORT=5100`, Browser‑Auto‑Open **aktiv**.

---

## ⚙️ Konfiguration

Gespeichert in `~/.github_auto_sync/config.json`, basierend auf `models/config.py`:

```json
{
  "project_name": "Mein Projekt",
  "project_path": "",                  
  "branch": "main",
  "remote_url": "",
  "auto_commit": true,
  "auto_push": true,
  "mirror_on_start": false,
  "batch_window_sec": 60,
  "debounce_ms": 600,
  "max_backups": 10,
  "include_exts": ["Dockerfile",".py",".json",".md",".yml",".yaml",".ini",".toml",".sql",".js",".ts",".html",".css"],
  "exclude_dirs": ["style_check",".git",".idea",".vscode","__pycache__",".venv","venv","node_modules","dist","build",".auto_versions"],
  "wip_branch": ""
}
```

---

## 📄 Lizenz

Siehe [LICENSE](LICENSE) (MIT).
