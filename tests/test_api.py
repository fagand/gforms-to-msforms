from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

FIXTURE_ZIP = Path(__file__).parent / "fixtures" / "sample_quiz.zip"

client = TestClient(app)


def test_upload_convert_download_flow():
    with open(FIXTURE_ZIP, "rb") as f:
        resp = client.post(
            "/api/jobs",
            files={"files": ("DR1 Storing Whole Numbers Quiz.zip", f, "application/zip")},
        )
    assert resp.status_code == 200
    body = resp.json()
    job_id = body["job_id"]
    assert len(body["accepted"]) == 1
    assert body["rejected"] == []

    with client.stream("GET", f"/api/jobs/{job_id}/stream") as stream_resp:
        events = "".join(stream_resp.iter_text())
    assert "event: result" in events
    assert '"success": true' in events
    assert "event: done" in events
    assert "download_url" in events

    dl = client.get(f"/api/jobs/{job_id}/download")
    assert dl.status_code == 200
    assert dl.headers["content-type"] == "application/zip"

    cleanup = client.delete(f"/api/jobs/{job_id}")
    assert cleanup.status_code == 200

    dl_after_cleanup = client.get(f"/api/jobs/{job_id}/download")
    assert dl_after_cleanup.status_code == 404


def test_rejects_non_zip_upload():
    resp = client.post(
        "/api/jobs",
        files={"files": ("notes.txt", b"hello world", "text/plain")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["accepted"] == []
    assert body["rejected"][0]["name"] == "notes.txt"


def test_rejects_too_many_files():
    files = [("files", (f"f{i}.zip", b"PK\x03\x04", "application/zip")) for i in range(21)]
    resp = client.post("/api/jobs", files=files)
    assert resp.status_code == 400


def test_unknown_job_returns_404():
    resp = client.get("/api/jobs/does-not-exist/stream")
    assert resp.status_code == 404
