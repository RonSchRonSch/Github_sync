# GitHub Auto Sync (Flask • Prototype)

MVP zum Testen: Watchdog + GitPython + Backup-Rotation mit Web-GUI.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export FLASK_SECRET_KEY="irgendwas"   # optional
```

## Start

```bash
python app.py
# Browser: http://127.0.0.1:5000
```

## Quickstart

1. Einstellungen öffnen → `Projektpfad` setzen (existierendes lokales Git-Repo oder leeres Verzeichnis)
2. `Branch` und optional `Remote URL` setzen
3. Filter prüfen
4. Dashboard → **Start**

## Features
- Auto-Commit / Auto-Push (abschaltbar)
- Batch-Fenster (z. B. 60s)
- Backup-Rotation `.auto_versions/` (max. N pro Datei)
- Include-/Exclude-Filter editierbar
- Live-Log und Vorschau „Welche Dateien werden beobachtet?“

> Achtung: Für Remote-Push muss das Repo Benutzer/Token-Zugriff haben (Credential Manager / SSH-Agent).
