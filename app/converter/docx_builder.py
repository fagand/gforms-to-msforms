"""Builds a .docx from a Quiz, shaped specifically for Microsoft Forms Quick Import.

See docs/MS_FORMS_QUICK_IMPORT.md for the research this follows. In short:

- Questions are plain paragraphs "<n>. <text>" (numeral + period, no heading style
  required).
- Choices are plain paragraphs "<LETTER>. <text>" (capital letter + period) — never a
  Word bullet-list style, which is reported to fail Quick Import outright.
- A blank paragraph separates each question block.
- No tables, no images, no equations anywhere in the question body.
- An undocumented-but-tested "ANSWER: <Letter>" / "POINT: <n>" pair is emitted under
  single-choice graded questions, since it costs nothing if Microsoft ignores it.
- A human-readable Answer Key is always appended at the end, because Microsoft's own
  official guidance is that pre-set correct answers are not a guaranteed import
  feature — the Answer Key is the reliable fallback for the 2-minute manual step.
- A Conversion Notes section lists anything that needed a judgement call (images
  dropped, unsupported question types, unmatched answers) so nothing is silently lost.
"""
from __future__ import annotations

import re

from docx import Document
from docx.shared import Pt

from .models import Question, QuestionType, Quiz


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _letter(index: int) -> str:
    if 0 <= index < 26:
        return chr(ord("A") + index)
    return str(index + 1)


def _match_option_index(answer: str, options: list[str]) -> int | None:
    target = _normalize(answer)
    for i, option in enumerate(options):
        if _normalize(option) == target:
            return i
    return None


def build_docx(quiz: Quiz) -> Document:
    doc = Document()
    doc.core_properties.title = quiz.title

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)

    doc.add_paragraph(quiz.title, style="Title")
    if quiz.description:
        doc.add_paragraph(quiz.description)
    doc.add_paragraph()

    conversion_notes: list[str] = [f"General: {w}" for w in quiz.warnings]
    answer_key_entries: list[tuple[int, Question]] = []

    for n, question in enumerate(quiz.questions, start=1):
        doc.add_paragraph(f"{n}. {question.text}")

        if question.question_type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE) and question.options:
            for i, option in enumerate(question.options):
                doc.add_paragraph(f"{_letter(i)}. {option}")

            if question.question_type == QuestionType.SINGLE_CHOICE and question.correct_answers:
                match_index = _match_option_index(question.correct_answers[0], question.options)
                if match_index is not None:
                    doc.add_paragraph(f"ANSWER: {_letter(match_index)}")
                    if question.points is not None:
                        doc.add_paragraph(f"POINT: {question.points}")
                else:
                    conversion_notes.append(
                        f"Q{n}: correct answer text did not match any option exactly; "
                        f"automatic answer marking was skipped for this question."
                    )

        doc.add_paragraph()

        if question.correct_answers or question.points is not None or question.required:
            answer_key_entries.append((n, question))

        for w in question.warnings:
            conversion_notes.append(f"Q{n}: {w}")

    if answer_key_entries:
        doc.add_paragraph("Answer Key — For Teacher Reference", style="Heading 1")
        note = doc.add_paragraph()
        note_run = note.add_run(
            "This section is not part of the quiz. Microsoft Forms Quick Import does not "
            "guarantee that correct answers, points, or required settings carry over "
            "automatically — use this list to finish setting them in Microsoft Forms "
            "(select each question, then \"Add correct answers and point values\")."
        )
        note_run.italic = True

        for n, question in answer_key_entries:
            heading = doc.add_paragraph()
            heading.add_run(f"Q{n}: {question.text}").bold = True

            if question.correct_answers:
                label = "Correct answer(s)" if question.question_type != QuestionType.MULTI_CHOICE else "Correct answer(s) (select all)"
                doc.add_paragraph(f"{label}: {'; '.join(question.correct_answers)}")
            else:
                doc.add_paragraph("Correct answer: not graded in the original form.")

            if question.points is not None:
                doc.add_paragraph(f"Points: {question.points}")
            if question.required:
                doc.add_paragraph("Required: Yes (set this manually — Quick Import cannot set it).")
            if question.question_type == QuestionType.MULTI_CHOICE and question.correct_answers:
                doc.add_paragraph(
                    "Note: enable \"Multiple answers\" on this question after import, "
                    "then tick every correct option listed above."
                )
            doc.add_paragraph()

    if conversion_notes:
        doc.add_paragraph("Conversion Notes", style="Heading 1")
        for note_text in conversion_notes:
            p = doc.add_paragraph(style="List Bullet")
            p.add_run(note_text)

    return doc
