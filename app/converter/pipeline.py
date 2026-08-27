"""Orchestrates: uploaded ZIP bytes -> validated extraction -> parse -> docx bytes.

Isolated per file so a batch of up to 20 ZIPs keeps going even if one is malformed,
per the brief's error-handling requirement.
"""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass

from .docx_builder import build_answer_key_docx, build_quiz_docx
from .errors import ConversionError
from .parser import find_form_html, parse_quiz

MAX_ZIP_SIZE = 25 * 1024 * 1024  # 25MB per ZIP — generous for a form's HTML/CSV/images
MAX_MEMBER_SIZE = 25 * 1024 * 1024
MAX_MEMBERS = 200


@dataclass
class ConversionResult:
    original_filename: str
    success: bool
    docx_filename: str | None = None
    docx_bytes: bytes | None = None
    answer_key_filename: str | None = None
    answer_key_bytes: bytes | None = None
    error: str | None = None
    warnings: list[str] | None = None


def _safe_extract_all(data: bytes) -> list[tuple[str, bytes]]:
    """Safely reads every regular file out of a ZIP's bytes, guarding against
    zip-slip path traversal and zip-bomb style abuse. Never writes to disk — the whole
    batch is handled in memory, since a school's batch of quiz forms is small.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ConversionError("File is not a valid ZIP archive") from exc

    infos = zf.infolist()
    if len(infos) > MAX_MEMBERS:
        raise ConversionError("ZIP contains too many files")

    out: list[tuple[str, bytes]] = []
    for info in infos:
        if info.is_dir():
            continue
        name = info.filename
        # zip-slip guard: reject absolute paths, drive letters, and any ".." segment
        normalized = name.replace("\\", "/")
        if normalized.startswith("/") or ":" in normalized or ".." in normalized.split("/"):
            raise ConversionError("ZIP contains unsafe file paths")
        if info.file_size > MAX_MEMBER_SIZE:
            raise ConversionError("ZIP contains a file that is too large")
        # keep just the base filename — folder structure inside the ZIP isn't needed
        # (see docs/ANALYSIS.md: forms are flat, three files at the root)
        base_name = normalized.rsplit("/", 1)[-1]
        if not base_name:
            continue
        out.append((base_name, zf.read(info)))
    return out


def convert_zip(original_filename: str, data: bytes) -> ConversionResult:
    try:
        if len(data) > MAX_ZIP_SIZE:
            raise ConversionError("ZIP file is too large (limit 25MB)")

        files = _safe_extract_all(data)
        html_name, html_text = find_form_html(files)
        quiz = parse_quiz(html_text, html_name)

        quiz_doc, conversion_notes = build_quiz_docx(quiz)
        buf = io.BytesIO()
        quiz_doc.save(buf)
        docx_filename = _safe_docx_filename(quiz.title, original_filename)

        answer_key_filename = None
        answer_key_bytes = None
        answer_key_doc = build_answer_key_docx(quiz, conversion_notes)
        if answer_key_doc is not None:
            ak_buf = io.BytesIO()
            answer_key_doc.save(ak_buf)
            answer_key_filename = _safe_docx_filename(f"{quiz.title} - Answer Key", original_filename)
            answer_key_bytes = ak_buf.getvalue()

        all_warnings = list(quiz.warnings)
        for q in quiz.questions:
            all_warnings.extend(q.warnings)

        return ConversionResult(
            original_filename=original_filename,
            success=True,
            docx_filename=docx_filename,
            docx_bytes=buf.getvalue(),
            answer_key_filename=answer_key_filename,
            answer_key_bytes=answer_key_bytes,
            warnings=all_warnings,
        )
    except ConversionError as exc:
        return ConversionResult(original_filename=original_filename, success=False, error=exc.message)
    except Exception as exc:  # noqa: BLE001 - never let one bad file crash the batch
        return ConversionResult(
            original_filename=original_filename,
            success=False,
            error=f"Unexpected error while converting this file: {exc}",
        )


_UNSAFE_FILENAME_CHARS = '<>:"/\\|?*'


def _safe_docx_filename(title: str, fallback: str) -> str:
    name = title or fallback.rsplit(".", 1)[0]
    for ch in _UNSAFE_FILENAME_CHARS:
        name = name.replace(ch, "")
    name = name.strip().strip(".")
    if not name:
        name = "quiz"
    return f"{name[:150]}.docx"
