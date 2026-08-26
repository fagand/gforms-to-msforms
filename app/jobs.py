"""In-memory + on-disk job tracking for a batch conversion.

A "job" is one browser upload of 1-20 ZIP files. Each job gets its own temp directory
(uploads/ and outputs/ subfolders) so batches never collide and cleanup is a single
`shutil.rmtree`. Jobs are swept automatically after completion/download and by a
periodic background sweep as a safety net (see `sweep_expired_jobs`), so nothing is
left behind on the server even if a user closes the tab mid-conversion.
"""
from __future__ import annotations

import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

JOB_TTL_SECONDS = 2 * 60 * 60  # safety-net cleanup for abandoned jobs
MAX_FILES_PER_JOB = 20
MAX_ZIP_SIZE = 25 * 1024 * 1024

_BASE_TMP_DIR = Path(tempfile.gettempdir()) / "gforms2msforms_jobs"
_BASE_TMP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class UploadedFile:
    original_name: str
    stored_path: Path
    size: int


@dataclass
class Job:
    job_id: str
    dir: Path
    uploads: list[UploadedFile] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (name, reason)
    created_at: float = field(default_factory=time.time)
    results_zip: Path | None = None
    consumed: bool = False


_jobs: dict[str, Job] = {}
_lock = Lock()

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9 ._-]+")


def sanitize_filename(name: str) -> str:
    """Strips any path component and unsafe characters — defends against path
    traversal via a crafted upload filename (e.g. "../../etc/passwd.zip")."""
    name = Path(name).name  # drop any directory component
    name = _SAFE_NAME_RE.sub("_", name).strip(" .")
    return name or "upload.zip"


def create_job() -> Job:
    job_id = uuid.uuid4().hex
    job_dir = _BASE_TMP_DIR / job_id
    (job_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (job_dir / "outputs").mkdir(parents=True, exist_ok=True)
    job = Job(job_id=job_id, dir=job_dir)
    with _lock:
        _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Job | None:
    with _lock:
        return _jobs.get(job_id)


def delete_job(job_id: str) -> None:
    with _lock:
        job = _jobs.pop(job_id, None)
    if job is not None:
        shutil.rmtree(job.dir, ignore_errors=True)


def sweep_expired_jobs() -> int:
    """Removes jobs older than JOB_TTL_SECONDS regardless of state. Returns count removed."""
    now = time.time()
    with _lock:
        expired = [jid for jid, j in _jobs.items() if now - j.created_at > JOB_TTL_SECONDS]
    for jid in expired:
        delete_job(jid)
    return len(expired)
