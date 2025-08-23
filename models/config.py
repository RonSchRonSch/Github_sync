from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG: Dict[str, Any] = {
    "project_name": "Mein Projekt",
    "project_path": "",
    "branch": "main",
    "remote_url": "",
    "auto_commit": True,
    "auto_push": True,
    "batch_window_sec": 60,
    "debounce_ms": 600,
    "max_backups": 10,
    "include_exts": [".py", ".json", ".md", ".yml", ".yaml", ".ini", ".toml", ".sql", ".js", ".ts", ".html", ".css"],
    "exclude_dirs": ["style_check", ".git", ".idea", ".vscode", "__pycache__", ".venv", "venv", "node_modules", "dist", "build", ".auto_versions"],
    "wip_branch": "",
}

class ConfigStore:
    def __init__(self, path: Path):
        self.path = path
        self._cfg = DEFAULT_CONFIG.copy()
        self.load()

    @property
    def data(self) -> Dict[str, Any]:
        return self._cfg

    def load(self) -> None:
        if self.path.exists():
            try:
                self._cfg.update(json.loads(self.path.read_text(encoding="utf-8")))
            except Exception:
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._cfg, indent=2, ensure_ascii=False), encoding="utf-8")
