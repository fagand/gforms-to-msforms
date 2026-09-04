"""FastAPI backend for the Google Forms -> Microsoft Forms Quick Import converter.

Flow (see README.md for the full picture):
  1. POST /api/jobs           - upload 1-20 ZIP files, get a job_id back
  2. GET  /api/jobs/{id}/stream - Server-Sent Events: one "result" event per file as
                                  it's converted, then a "done" event
  3. GET  /api/jobs/{id}/download - a ZIP of every successful .docx

Kept deliberately dependency-light (FastAPI + Starlette's own tools only) per the
brief's "no complex frameworks" instruction.
"""
from __future__ import annotations

import asyncio
import io
import json
import logging
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import jobs
from .converter import convert_zip

logger = logging.getLogger("gforms2msforms")

STATIC_DIR = Path(__file__).parent / "static"  # built locally and committed
SWEEP_INTERVAL_SECONDS = 15 * 60


async def _sweep_loop() -> None:
    while True:
        await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
        try:
            removed = jobs.sweep_expired_jobs()
            if removed:
                logger.info("Swept %d expired job(s)", removed)
        except Exception:  # noqa: BLE001
            logger.exception("Error during job sweep")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_sweep_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Google Forms to Microsoft Forms Converter", lifespan=lifespan)


@app.post("/api/jobs")
async def create_job(files: list[UploadFile] = File(...)):
    if not files:
        raise HTTPException(400, "No files were uploaded.")
    if len(files) > jobs.MAX_FILES_PER_JOB:
        raise HTTPException(400, f"Too many files — the limit is {jobs.MAX_FILES_PER_JOB} per batch.")

    job = jobs.create_job()
    accepted = []

    for upload in files:
        original_name = upload.filename or "upload.zip"
        data = await upload.read()

        if not original_name.lower().endswith(".zip"):
            job.rejected.append((original_name, "Not a .zip file"))
            continue
        if len(data) == 0:
            job.rejected.append((original_name, "File is empty"))
            continue
        if len(data) > jobs.MAX_ZIP_SIZE:
            job.rejected.append((original_name, "File is too large (limit 25MB)"))
            continue
        if data[:2] != b"PK":
            job.rejected.append((original_name, "File is not a valid ZIP archive"))
            continue

        safe_name = jobs.sanitize_filename(original_name)
        disk_path = job.dir / "uploads" / f"{len(job.uploads)}_{safe_name}"
        disk_path.write_bytes(data)
        uploaded = jobs.UploadedFile(original_name=original_name, stored_path=disk_path, size=len(data))
        job.uploads.append(uploaded)
        accepted.append({"name": original_name, "size": len(data)})

    if not job.uploads and not job.rejected:
        jobs.delete_job(job.job_id)
        raise HTTPException(400, "No files were uploaded.")

    return {
        "job_id": job.job_id,
        "accepted": accepted,
        "rejected": [{"name": n, "reason": r} for n, r in job.rejected],
    }


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.get("/api/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found or has expired.")

    async def generator():
        for name, reason in job.rejected:
            yield _sse("result", {"filename": name, "success": False, "error": reason})

        success_count = 0
        failure_count = 0
        used_names: set[str] = set()

        for uploaded in job.uploads:
            yield _sse("start", {"filename": uploaded.original_name})
            data = uploaded.stored_path.read_bytes()
            result = await asyncio.to_thread(convert_zip, uploaded.original_name, data)

            if result.success:
                docx_name = result.docx_filename or "quiz.docx"
                stem, dot, ext = docx_name.rpartition(".")
                counter = 1
                final_name = docx_name
                while final_name in used_names:
                    counter += 1
                    final_name = f"{stem} ({counter}).{ext}" if dot else f"{docx_name} ({counter})"
                used_names.add(final_name)

                out_path = job.dir / "outputs" / final_name
                out_path.write_bytes(result.docx_bytes or b"")

                answer_key_name = None
                if result.answer_key_bytes:
                    ak_name = result.answer_key_filename or "answer_key.docx"
                    ak_stem, ak_dot, ak_ext = ak_name.rpartition(".")
                    ak_counter = 1
                    answer_key_name = ak_name
                    while answer_key_name in used_names:
                        ak_counter += 1
                        answer_key_name = f"{ak_stem} ({ak_counter}).{ak_ext}" if ak_dot else f"{ak_name} ({ak_counter})"
                    used_names.add(answer_key_name)
                    (job.dir / "outputs" / answer_key_name).write_bytes(result.answer_key_bytes)

                success_count += 1
                yield _sse(
                    "result",
                    {
                        "filename": uploaded.original_name,
                        "success": True,
                        "docx_name": final_name,
                        "answer_key_name": answer_key_name,
                        "warnings": result.warnings or [],
                    },
                )
            else:
                failure_count += 1
                yield _sse(
                    "result",
                    {"filename": uploaded.original_name, "success": False, "error": result.error},
                )

        failure_count += len(job.rejected)

        download_url = None
        if success_count > 0:
            zip_path = job.dir / "results.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for docx_file in sorted((job.dir / "outputs").iterdir()):
                    zf.write(docx_file, arcname=docx_file.name)
            job.results_zip = zip_path
            # Relative (no leading slash) so it resolves correctly via the page's
            # <base> tag regardless of whether this app is hosted at a domain root
            # or a sub-path (e.g. behind a reverse proxy or cPanel Passenger app
            # mounted under /something/) — see app/static/index.html.
            download_url = f"api/jobs/{job_id}/download"

        yield _sse(
            "done",
            {
                "success_count": success_count,
                "failure_count": failure_count,
                "download_url": download_url,
            },
        )

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/jobs/{job_id}/download")
async def download_job(job_id: str):
    job = jobs.get_job(job_id)
    if job is None or job.results_zip is None or not job.results_zip.exists():
        raise HTTPException(404, "Nothing to download — the job may have expired.")

    job.consumed = True
    response = FileResponse(
        job.results_zip,
        media_type="application/zip",
        filename="microsoft_forms_quizzes.zip",
    )
    return response


@app.delete("/api/jobs/{job_id}")
async def cleanup_job(job_id: str):
    """Called by the frontend once the user has downloaded their results, so temp
    files don't linger for the full TTL. Safe to call more than once."""
    jobs.delete_job(job_id)
    return {"ok": True}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
