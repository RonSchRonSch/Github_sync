from __future__ import annotations
import hashlib, shutil, threading, time
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import List, Set, Optional, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from .git_service import ensure_repo, ensure_branch, ensure_remote, stage_paths, commit_and_push

BACKUP_DIRNAME = ".auto_versions"

class InMemoryLog:
    def __init__(self, maxlen: int = 2000):
        self._buf = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, msg: str):
        with self._lock:
            ts = datetime.now().strftime("%H:%M:%S")
            self._buf.appendleft(f"[{ts}] {msg}")

    def dump(self) -> List[str]:
        with self._lock:
            return list(self._buf)

def _is_under_git(path: Path) -> bool:
  """True, wenn der Pfad irgendwo unter einem .git/ liegt."""
  parts = Path(path).resolve().parts
  return ".git" in parts

def _display_path(project_root: Path, p: Path) -> str:
  """Aus /Users/.../Test_Vector/src/x.py -> Test_Vector/src/x.py."""
  try:
    rel = p.relative_to(project_root)
  except Exception:
    rel = p
  proj = project_root.name  # letzter Ordnername
  return f"{proj}/{rel.as_posix()}"

def digest(path: Path) -> str:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""

def is_watched_file(root: Path, p: Path, include_exts: List[str], exclude_dirs: List[str]) -> bool:
    if p.is_dir():
        return False
    try:
        rel = p.relative_to(root)
    except Exception:
        return False
    if p.suffix.lower() not in {e.lower() for e in include_exts}:
        return False
    if ".git" in rel.parts:  # Safety net
      return False
    if BACKUP_DIRNAME in rel.parts:
        return False
    for part in rel.parts:
        if part in exclude_dirs:
            return False
    return True

def iter_watch_files(root: Path, include_exts: List[str], exclude_dirs: List[str]):
    for p in Path(root).rglob("*"):
        if p.is_file() and is_watched_file(root, p, include_exts, exclude_dirs):
            yield p

class WatchHandler(FileSystemEventHandler):
    def __init__(self, root: Path, cfg: dict, log: InMemoryLog):
        self.root = Path(root).resolve()
        self.cfg = cfg
        self.log = log
        self.repo = ensure_repo(self.root)
        ensure_branch(self.repo, cfg.get("branch", "main"))
        ensure_remote(self.repo, cfg.get("remote_url"))
        self._changed: Set[Path] = set()
        self._deleted: Set[Path] = set()
        self._last_event: Dict[Path, float] = {}
        self._last_digest: Dict[Path, str] = {}
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

        Path(self.root / BACKUP_DIRNAME).mkdir(exist_ok=True)

    def _debounced(self, p: Path) -> bool:
        now = time.time()
        last = self._last_event.get(p, 0)
        self._last_event[p] = now
        return (now - last) * 1000 < int(self.cfg.get("debounce_ms", 600))

    def _digest_changed(self, p: Path) -> bool:
        d = digest(p) if p.exists() else ""
        if not d:
            return True
        if self._last_digest.get(p) == d:
            return False
        self._last_digest[p] = d
        return True

    def _backup_rotate(self, p: Path):
        try:
            rel = p.relative_to(self.root)
        except Exception:
            return
        vdir = self.root / BACKUP_DIRNAME / rel.with_suffix(rel.suffix + ".history")
        vdir.parent.mkdir(parents=True, exist_ok=True)
        vdir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = vdir / f"{ts}{p.suffix}"
        shutil.copy2(p, dst)
        # rotate
        versions = sorted(vdir.glob(f"*{p.suffix}"))
        max_n = int(self.cfg.get("max_backups", 10))
        excess = len(versions) - max_n
        for i in range(excess):
            try:
                versions[i].unlink()
            except Exception:
                pass

    def _schedule_batch(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(float(self.cfg.get("batch_window_sec", 60)), self._do_batch)
            self._timer.daemon = True
            self._timer.start()

    def _do_batch(self):
        # --- Rauschen durch Editor-Replace glätten ---
        both = self._changed & self._deleted
        if both:
          self._deleted -= both
        # --------------------------------------------
        with self._lock:
            changed = set(self._changed)
            deleted = set(self._deleted)
            self._changed.clear()
            self._deleted.clear()
        try:
            stage_paths(self.repo, self.root, changed, deleted)
            if self.cfg.get("auto_commit", True) or self.cfg.get("auto_push", True):
              proj = self.root.name
              msg = f"{proj}: {len(changed)} updated, {len(deleted)} removed @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
              commit_and_push(self.repo, self.cfg.get("branch", "main"), f"auto: {msg}",
                              self.cfg.get("auto_commit", True), self.cfg.get("auto_push", True))
              self.log.add(f"Commit/Push: {msg}")
        except Exception as e:
            self.log.add(f"Fehler Batch: {e!r}")

    # Events
    def on_modified(self, event):
      if event.is_directory:
        return
      p = Path(event.src_path)
      if not self._is_watched_file(p):
        return
      self._changed.add(p)
      if not p.name.endswith("~"):
        self.log.add(f"Änderung: {_display_path(self.root, p)}")
      self._schedule_batch()

    def on_created(self, event):
      if event.is_directory:
        return
      p = Path(event.src_path)
      if not self._is_watched_file(p):
        return
      self._changed.add(p)
      if not p.name.endswith("~"):
        self.log.add(f"Neu: {_display_path(self.root, p)}")
      self._schedule_batch()

    def on_deleted(self, event):
      if event.is_directory:
        return
      p = Path(event.src_path)
      # Auch gelöschte ignorieren, wenn es Tilde-Dateien waren
      if not self._is_watched_path(p) or p.name.endswith("~"):
        return
      self._deleted.add(p)
      self.log.add(f"Gelöscht: {_display_path(self.root, p)}")
      self._schedule_batch()

    def on_moved(self, event):
      if event.is_directory:
        return
      src = Path(event.src_path)
      dest = Path(event.dest_path)
      # Quelle als gelöscht behandeln (nur loggen, wenn keine Tilde)
      if self._is_watched_path(src) and not src.name.endswith("~"):
        self._deleted.add(src)
        self.log.add(f"Verschoben: {_display_path(self.root, src)} -> {_display_path(self.root, dest)}")
      # Ziel als geändert/neu, wenn es beobachtet wird und keine Tilde
      if dest.exists() and self._is_watched_file(dest) and not dest.name.endswith("~"):
        self._changed.add(dest)
      self._schedule_batch()

    # direkt in der Klasse WatchHandler ergänzen (z.B. nach __init__)
    def _is_watched_path(self, p: Path) -> bool:
      """Pfadbezogene Filter: Projekt-Root, ausgeschlossene Ordner (.git, venv, etc.)."""
      try:
        rel = p.relative_to(self.root)
      except ValueError:
        return False
      # Ordner ausschließen
      for part in rel.parts:
        if part in self.cfg.exclude_dirs:
          return False
      return True

    def _is_watched_file(self, p: Path) -> bool:
      """Dateibezogene Filter: Patterns (inkl/exkl), Tilde, etc."""
      if not self._is_watched_path(p):
        return False
      name = p.name

      # Exclude-Patterns (z.B. .*~$ aus deiner config.py)
      for pat in self.cfg.exclude_file_patterns or []:
        if re.match(pat, name):
          return False

      # Include-Patterns (wenn gesetzt: whiteliste)
      inc = self.cfg.include_file_patterns or []
      if inc:
        return any(re.match(pat, name) for pat in inc)

      return True

class WatchService:
    def __init__(self, cfg: dict, log: InMemoryLog):
        self.cfg = cfg
        self.log = log
        self._observer: Optional[Observer] = None
        self._handler: Optional[WatchHandler] = None

    def start(self):
        if self._observer:
            return
        root = Path(self.cfg["project_path"]).expanduser()
        self._handler = WatchHandler(root=root, cfg=self.cfg, log=self.log)
        self._observer = Observer()
        self._observer.schedule(self._handler, str(root), recursive=True)
        self._observer.start()
        self.log.add("Watcher gestartet")

    def stop(self):
        obs = self._observer
        if obs:
            obs.stop()
            obs.join(timeout=3)
            self._observer = None
            self._handler = None
            self.log.add("Watcher gestoppt")

    def running(self) -> bool:
        return self._observer is not None

    def preview_files(self) -> list[str]:
        root = Path(self.cfg["project_path"]).expanduser()
        return [str(p.relative_to(root)) for p in iter_watch_files(root, self.cfg["include_exts"], self.cfg["exclude_dirs"])]
