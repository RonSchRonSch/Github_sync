from __future__ import annotations
import os
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from models.config import ConfigStore
from services.watch_service import WatchService, InMemoryLog

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

CONFIG_PATH = Path.home()/".github_auto_sync"/"config.json"
cfg_store = ConfigStore(CONFIG_PATH)
log = InMemoryLog(maxlen=2000)
watch = WatchService(cfg_store.data, log)

@app.route("/")
def index():
    return render_template("index.html",
                           cfg=cfg_store.data,
                           running=watch.running(),
                           logs=log.dump()[:100])

@app.route("/start", methods=["POST"])
def start_watch():
    if not cfg_store.data.get("project_path"):
        flash("Bitte zuerst einen Projektpfad in den Einstellungen setzen.", "warning")
        return redirect(url_for("settings"))
    try:
        watch.start()
        flash("Watcher gestartet.", "success")
    except Exception as e:
        flash(f"Fehler: {e}", "danger")
    return redirect(url_for("index"))

@app.route("/stop", methods=["POST"])
def stop_watch():
    watch.stop()
    flash("Watcher gestoppt.", "info")
    return redirect(url_for("index"))

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        d = cfg_store.data
        d["project_name"] = request.form.get("project_name","").strip()
        d["project_path"] = request.form.get("project_path","").strip()
        d["branch"] = request.form.get("branch","main").strip()
        d["remote_url"] = request.form.get("remote_url","").strip()
        d["auto_commit"] = bool(request.form.get("auto_commit"))
        d["auto_push"] = bool(request.form.get("auto_push"))
        d["batch_window_sec"] = float(request.form.get("batch_window_sec", "60"))
        d["debounce_ms"] = int(request.form.get("debounce_ms", "600"))
        d["max_backups"] = int(request.form.get("max_backups", "10"))
        d["wip_branch"] = request.form.get("wip_branch","").strip()
        cfg_store.save()
        flash("Einstellungen gespeichert.", "success")
        return redirect(url_for("settings"))
    return render_template("settings.html", cfg=cfg_store.data)

@app.route("/filters", methods=["GET", "POST"])
def filters():
    if request.method == "POST":
        include_exts = request.form.get("include_exts","").strip()
        exclude_dirs = request.form.get("exclude_dirs","").strip()
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
    return jsonify(logs=log.dump()[:200])

@app.get("/pick-folder")
def pick_folder():
    from flask import jsonify
    try:
        # tkinter Import separat try-enclosed, damit fehlende Tk lib sauber gemeldet wird
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as ie:
            return jsonify(ok=False, error=f"tkinter nicht verfügbar: {ie}"), 200

        import os
        from pathlib import Path

        os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")
        root = tk.Tk()
        root.withdraw()
        root.update()
        path = filedialog.askdirectory(title="Projektordner wählen")
        try:
            root.destroy()
        except Exception:
            pass

        if not path:
            return jsonify(ok=False, path="", error="Abgebrochen"), 200

        path = str(Path(path).expanduser().resolve())
        return jsonify(ok=True, path=path), 200

    except Exception as e:
        # niemals HTML, immer JSON -> JS kann es anzeigen
        return jsonify(ok=False, error=f"{type(e).__name__}: {e}"), 200



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)


