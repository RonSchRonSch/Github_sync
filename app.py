from __future__ import annotations
import os, sys, subprocess
import re
import atexit
import shutil
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models.config import ConfigStore
from services.watch_service import WatchService, InMemoryLog


def _purge_pycache(root_path: str):
    """
    Löscht rekursiv __pycache__-Ordner und .pyc/.pyo Dateien unterhalb von root_path.
    Macht nichts kaputt – nur kompilierten Bytecode weg.
    """
    root_path = os.path.expanduser(root_path)
    for dirpath, dirnames, filenames in os.walk(root_path):
        # __pycache__-Ordner sammeln
        if "__pycache__" in dirnames:
            d = os.path.join(dirpath, "__pycache__")
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        # einzelne .pyc/.pyo löschen (falls außerhalb der __pycache__)
        for fn in filenames:
            if fn.endswith((".pyc", ".pyo")):
                fp = os.path.join(dirpath, fn)
                try:
                    os.remove(fp)
                except Exception:
                    pass


def _safe_cleanup_before_start(cfg, log):
    """
    Wird VOR dem Start des Watchers aufgerufen:
    - Bytecode-Caches im Projekt löschen
    """
    proj = cfg.get("project_path")
    if proj:
        _purge_pycache(proj)
        log.add("Cache bereinigt (vor Start)")


def _raw_url_for(rel_path: str, cfg: dict) -> str:
    """
    Baut eine raw.githubusercontent.com-URL aus remote_url + branch + relativem Pfad.
    Unterstützt https und ssh Remote-Formate.
    """
    remote = (cfg.get("remote_url") or "").strip()
    branch = (cfg.get("branch") or "main").strip()

    # https-Variante: https://github.com/<user>/<repo>.git
    m = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", remote)
    if not m:
        # ssh-Variante: git@github.com:<user>/<repo>.git
        m = re.match(r"^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", remote)

    if not m:
        return rel_path  # Fallback: lieber den relativen Pfad zeigen als gar nichts

    user, repo = m.group(1), m.group(2)
    # raw‑Basis
    base = f"https://raw.githubusercontent.com/{user}/{repo}/{branch}"
    # rel_path sauber anhängen
    rel_path = rel_path.lstrip("/")

    return f"{base}/{rel_path}"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

CONFIG_PATH = Path.home() / ".github_auto_sync" / "config.json"
cfg_store = ConfigStore(CONFIG_PATH)
log = InMemoryLog(maxlen=2000)
watch = WatchService(cfg_store.data, log)

# Beim Prozessende sicher stoppen (verhindert „hängende“ Watchdog-Threads)
atexit.register(lambda: watch.stop() if watch and watch.running() else None)


@app.route("/")
def index():
    # Logs wie gehabt
    lines = log.dump()[:100]

    # Vorschau-Dateien + RAW-URLs erzeugen
    try:
        files = watch.preview_files() if watch.running() else []
    except Exception:
        files = []

    raw_urls = []
    for rel in files:
        raw_urls.append(_raw_url_for(rel, cfg_store.data))

    return render_template(
        "index.html",
        cfg=cfg_store.data,
        running=watch.running(),
        logs=list(lines),
        preview_files=files,
        preview_raw_urls=raw_urls,
    )


@app.route("/start", methods=["POST"])
def start_watch():
    if not cfg_store.data.get("project_path"):
        flash("Bitte zuerst einen Projektpfad in den Einstellungen setzen.", "warning")
        return redirect(url_for("settings"))
    try:
        # NEU: vor dem Start Caches bereinigen
        _safe_cleanup_before_start(cfg_store.data, log)
        watch.start()
        flash("Watcher gestartet.", "success")
    except Exception as e:
        flash(f"Fehler: {e}", "danger")
    return redirect(url_for("index"))


@app.route("/stop", methods=["POST"])
def stop_watch():
    watch.stop()
    # NEU: nach dem Stop Caches im Projekt entfernen
    proj = cfg_store.data.get("project_path")
    if proj:
        _purge_pycache(proj)
        log.add("Cache bereinigt (nach Stop)")
    flash("Watcher gestoppt.", "info")
    return redirect(url_for("index"))


@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        d = cfg_store.data
        d["project_name"] = request.form.get("project_name", "").strip()
        d["project_path"] = request.form.get("project_path", "").strip()
        d["branch"] = request.form.get("branch", "main").strip()
        d["remote_url"] = request.form.get("remote_url", "").strip()
        d["auto_commit"] = bool(request.form.get("auto_commit"))
        d["auto_push"] = bool(request.form.get("auto_push"))
        d["batch_window_sec"] = float(request.form.get("batch_window_sec", "60"))
        d["debounce_ms"] = int(request.form.get("debounce_ms", "600"))
        d["max_backups"] = int(request.form.get("max_backups", "10"))
        d["wip_branch"] = request.form.get("wip_branch", "").strip()
        cfg_store.save()
        flash("Einstellungen gespeichert.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", cfg=cfg_store.data)


@app.route("/filters", methods=["GET", "POST"])
def filters():
    if request.method == "POST":
        include_exts = request.form.get("include_exts", "").strip()
        exclude_dirs = request.form.get("exclude_dirs", "").strip()
        cfg_store.data["include_exts"] = [e.strip() for e in include_exts.split(",") if e.strip()]
        cfg_store.data["exclude_dirs"] = [e.strip() for e in exclude_dirs.split(",") if e.strip()]
        cfg_store.save()
        flash("Filter gespeichert.", "success")
        return redirect(url_for("filters"))
    return render_template("filters.html", cfg=cfg_store.data)


@app.route("/preview")
def preview():
    try:
        files = watch.preview_files()
        return render_template("preview.html", files=files, cfg=cfg_store.data)
    except Exception as e:
        flash(f"Fehler bei Vorschau: {e}", "danger")
        return redirect(url_for("filters"))


@app.route("/api/logs")
def api_logs():
    try:
        lines = list(log.dump()[:500])
    except Exception:
        lines = []
    return jsonify(text="\n".join(lines), lines=lines)


# --- NEU: dynamische RAW-Link-Liste ---
def _raw_base_from_remote(remote_url: str, branch: str) -> str:
    """
    Baut die raw.githubusercontent.com-Basis aus einer GitHub-Remote-URL.
    Unterstützt https://github.com/<owner>/<repo>.git
    """
    try:
        # Beispiel: https://github.com/RonSchRonSch/PyCharm_auto.git
        if "github.com" in remote_url:
            tail = remote_url.split("github.com/", 1)[1]
            tail = tail.removesuffix(".git")
            owner, repo = tail.split("/", 1)
            return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}"
    except Exception:
        pass
    return ""  # unbekanntes Remote-Format -> leere Basis

@app.route("/api/raw-links")
def api_raw_links():
    """
    Gibt die aktuelle RAW-Liste zurück (Text + Array), damit das Frontend
    sie wie die Logs pollen und live anzeigen kann.
    """
    try:
        files = watch.preview_files()  # relative Pfade
        branch = cfg_store.data.get("branch", "main")
        remote = cfg_store.data.get("remote_url", "")
        base = _raw_base_from_remote(remote, branch)
        lines = [(f"{base}/{p}" if base else p) for p in files]
        text = "\n".join(lines)
        return jsonify(ok=True, text=text, lines=lines)
    except Exception as e:
        return jsonify(ok=False, error=str(e), text="", lines=[])


@app.get("/choose-folder")
def choose_folder():
    """
    Öffnet den nativen Ordnerdialog abhängig vom OS:
      - macOS: AppleScript (osascript)
      - Windows/Linux: Tkinter askdirectory
    Gibt JSON {ok: bool, path?: str, error?: str} zurück.
    """
    try:
        # macOS: nativer Dialog
        if sys.platform.startswith("darwin"):
            script = (
                'try\n'
                '  set theFolder to POSIX path of (choose folder with prompt "Projektordner wählen")\n'
                '  return theFolder\n'
                'on error number -128\n'
                '  return "__USER_CANCELLED__"\n'
                'end try'
            )
            out = subprocess.check_output(["osascript", "-e", script], text=True).strip()
            if out == "__USER_CANCELLED__" or not out:
                return jsonify(ok=False, error="cancelled"), 400
            path = out.rstrip("/")
        else:
            # Windows/Linux (+ macOS Fallback): Tkinter
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.update()
                path = filedialog.askdirectory(title="Projektordner wählen")
                try:
                    root.destroy()
                except Exception:
                    pass
                if not path:
                    return jsonify(ok=False, error="cancelled"), 400
            except Exception as e:
                return jsonify(ok=False, error=f"tkinter_failed: {e}"), 500

        # Sicherheit: existiert der Ordner wirklich?
        if not os.path.isdir(path):
            return jsonify(ok=False, error="not_a_directory", path=path), 400

        return jsonify(ok=True, path=str(Path(path).expanduser().resolve())), 200

    except subprocess.CalledProcessError:
        return jsonify(ok=False, error="osascript_failed"), 500
    except Exception as e:
        return jsonify(ok=False, error=f"unexpected: {e}"), 500


if __name__ == "__main__":
    # Kein Auto-Reload (use_reloader=False), damit Ports/Threads nicht „kleben“ bleiben.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)