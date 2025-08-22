from __future__ import annotations
from pathlib import Path
from typing import Iterable, Optional
from git import Repo, GitCommandError, InvalidGitRepositoryError, NoSuchPathError

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
    if not remote_url:
        return
    try:
        origin = repo.remotes.origin
        if origin.url != remote_url:
            repo.delete_remote(origin)
            repo.create_remote("origin", remote_url)
    except Exception:
        repo.create_remote("origin", remote_url)

def has_changes(repo: Repo) -> bool:
    return bool(repo.git.status("--porcelain").strip())

def stage_paths(repo: Repo, root: Path, add_paths: Iterable[Path], del_paths: Iterable[Path]) -> None:
    add_list = []
    for p in add_paths:
        if p.exists():
            add_list.append(str(Path(p).relative_to(root)))
    if add_list:
        repo.git.add("--", *add_list)
    for p in del_paths:
        rel = str(Path(p).relative_to(root))
        try:
            repo.git.rm("--cached", "--force", "--", rel)
        except Exception:
            pass


def commit_and_push(repo: Repo, branch: str, message: str, do_commit: bool, do_push: bool) -> None:
  """
  Commit (optional) und Push (optional) mit sichtbarem Feedback.
  """
  if do_commit and has_changes(repo):
    repo.index.commit(message)

  if do_push:
    try:
      # branch bevorzugen; sonst aktiven Branch verwenden
      ref = branch or repo.active_branch.name
      repo.remotes.origin.push(ref)
      print("[git] push ok")  # sichtbar im Flask/Terminal-Log
    except Exception as e:
      print(f"[git] push failed: {e}")
      raise