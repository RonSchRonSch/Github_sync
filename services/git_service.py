from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError


# -----------------------------
# Hilfen
# -----------------------------
def _active_branch_name(repo: Repo, fallback: str = "main") -> str:
    """Gibt den aktuellen Branch-Namen zurück, auch wenn HEAD detached ist."""
    try:
        return repo.active_branch.name
    except Exception:
        # detached HEAD oder kein Branch – auf Fallback zurückfallen
        return fallback or "main"


# -----------------------------
# Repo/Remote/Branch
# -----------------------------
def ensure_repo(path: Path) -> Repo:
    try:
        return Repo(path)
    except (InvalidGitRepositoryError, NoSuchPathError):
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        return Repo.init(p)


def ensure_branch(repo: Repo, branch: str) -> None:
    if not branch:
        return
    try:
        repo.git.checkout(branch)
    except GitCommandError:
        repo.git.checkout("-b", branch)


def ensure_remote(repo: Repo, remote_url: Optional[str]) -> None:
    """
    Stellt sicher, dass 'origin' existiert und auf remote_url zeigt.
    Wenn 'origin' existiert, wird die URL gesetzt statt den Remote zu löschen.
    """
    if not remote_url:
        return
    try:
        origin = repo.remotes.origin  # type: ignore[attr-defined]
        # GitPython: set_url setzt Fetch-URL; Push-URL bei Git >=2.7 ebenfalls
        if origin.url != remote_url:
            origin.set_url(remote_url)
    except Exception:
        repo.create_remote("origin", remote_url)


# -----------------------------
# Status/Stage
# -----------------------------
def has_changes(repo: Repo) -> bool:
    # True wenn Working Tree oder Index Änderungen hat
    return bool(repo.git.status("--porcelain").strip())


def stage_paths(repo: Repo, root: Path, add_paths: Iterable[Path], del_paths: Iterable[Path]) -> None:
    add_list = []
    for p in add_paths:
        if p.exists():
            add_list.append(str(Path(p).relative_to(root)))

    if add_list:
        repo.git.add("--", *add_list)

    # Deletions sauber in den Index übernehmen
    for p in del_paths:
        rel = str(Path(p).relative_to(root))
        try:
            # '--cached' meldet die Datei als gelöscht, auch wenn sie bereits fehlt
            repo.git.rm("--cached", "--force", "--", rel)
        except Exception:
            # falls schon als deletion erfasst – ignorieren
            pass


# -----------------------------
# Commit/Push
# -----------------------------
def commit_and_push(repo: Repo, branch: str, message: str, do_commit: bool, do_push: bool) -> None:
    """
    Commit (optional) und Push (optional) mit defensiven Guards.
    Pusht *nur*, wenn do_push=True und 'origin' vorhanden ist.
    """
    # Commit nur wenn gefordert und es Änderungen gibt
    if do_commit and has_changes(repo):
        repo.index.commit(message)

    # Push strikt nur bei Erlaubnis
    if not do_push:
        return

    # Ohne 'origin' gibt es nichts zu pushen
    try:
        origin = repo.remotes.origin  # type: ignore[attr-defined]
    except Exception:
        print("[git] push skipped: no 'origin' remote configured")
        return

    try:
        ref = branch or _active_branch_name(repo)
        origin.push(ref)
        print("[git] push ok")
    except Exception as e:
        print(f"[git] push failed: {e}")
        raise


# -----------------------------
# Spiegelung (Force with lease)
# -----------------------------
def mirror_force_with_lease(
    repo: Repo,
    branch: str,
    remote: str = "origin",
    snapshot_msg: str = "mirror_on_start",
) -> None:
    """
    Spiegelt den *lokalen* Stand auf den Remote-Branch (sicherer Force-Push):
      1) git add -A (tracked + untracked)
      2) Snapshot-Commit, falls nötig
      3) git push --force-with-lease <remote> <branch>:<branch>
    """
    # alles hinzufügen (tracked + untracked)
    repo.git.add(A=True)

    # nur committen, wenn wirklich Änderungen da sind
    if repo.is_dirty(untracked_files=True):
        repo.index.commit(f"auto: {snapshot_msg} @ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # origin ggf. updaten (nicht kritisch, aber hilfreich)
    try:
        repo.git.fetch(remote)
    except Exception:
        pass

    # Ziel-Branch robust bestimmen
    ref = branch or _active_branch_name(repo)

    # sicherer Force-Push (bewahrt Schutz gegen fremde Zwischen-Pushes)
    repo.git.push(remote, f"{ref}:{ref}", "--force-with-lease")
    print(f"[git] mirror_force_with_lease -> {remote}/{ref}")