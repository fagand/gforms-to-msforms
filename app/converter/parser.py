"""Parses the Google Forms "freebird" export HTML (see docs/ANALYSIS.md) into a Quiz.

The parser is deliberately rule-based against the real DOM structure Google Forms
ships (a stable, long-lived internal naming scheme — "freebirdFormviewerView*" classes
— common to every Google Form export, not something invented for this one form) rather
than against any single sample. Where a question's structure can't be confidently
classified, it degrades to an UNSUPPORTED placeholder for that question only so one
odd question never fails the whole file — see docs/ANALYSIS.md §10.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup
from bs4.element import Tag

from .errors import ConversionError
from .models import Question, QuestionType, Quiz

FORM_MARKER = "freebirdFormviewerViewFormContent"

_POINTS_RE = re.compile(r"(\d+)\s*point")


def find_form_html(files: list[tuple[str, bytes]]) -> tuple[str, str]:
    """Given (filename, bytes) pairs extracted from a ZIP, return the (filename, decoded
    text) of the file that looks like a Google Forms export.

    Raises ConversionError("No Google Form HTML found") if nothing matches.
    """
    candidates = [(name, data) for name, data in files if name.lower().endswith((".html", ".htm"))]
    if not candidates:
        raise ConversionError("No Google Form HTML found")

    for name, data in candidates:
        text = _decode(data)
        if FORM_MARKER in text:
            return name, text

    raise ConversionError("No Google Form HTML found")


def _decode(data: bytes) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def _clean_text(tag: Tag | None) -> str | None:
    if tag is None:
        return None
    text = tag.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _is_descendant(el: Tag, ancestor: Tag) -> bool:
    for parent in el.parents:
        if parent is ancestor:
            return True
    return False


def _extract_title_text(item: Tag) -> str | None:
    title_div = item.select_one(".freebirdFormviewerViewItemsItemItemTitle")
    if title_div is None:
        return None
    title_copy = BeautifulSoup(str(title_div), "lxml")
    for asterisk in title_copy.select(".freebirdFormviewerViewItemsItemRequiredAsterisk"):
        asterisk.decompose()
    text = title_copy.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(" *")
    return text or None


def _extract_points(item: Tag) -> int | None:
    score_div = item.select_one(".freebirdFormviewerViewItemsItemScore")
    text = _clean_text(score_div)
    if not text:
        return None
    match = _POINTS_RE.search(text)
    return int(match.group(1)) if match else None


def _classify(item: Tag) -> QuestionType:
    jsc = item.get("jscontroller") or ""
    jsc = jsc.lower()
    if "radio" in jsc:
        return QuestionType.SINGLE_CHOICE
    if "checkbox" in jsc:
        return QuestionType.MULTI_CHOICE
    if "text" in jsc:
        html = str(item)
        if "freebirdFormviewerViewItemsTextLongText" in html:
            return QuestionType.LONG_TEXT
        return QuestionType.SHORT_TEXT
    return QuestionType.UNSUPPORTED


def _extract_choice_options(item: Tag, correct_box: Tag | None) -> list[str]:
    options: list[str] = []
    seen: set[str] = set()
    for role_el in item.select('[role="radio"], [role="checkbox"]'):
        if correct_box is not None and _is_descendant(role_el, correct_box):
            continue
        label = role_el.get("aria-label")
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        options.append(label)
    return options


def _extract_correct_choice_answers(correct_box: Tag) -> list[str]:
    answers: list[str] = []
    for role_el in correct_box.select('[role="radio"], [role="checkbox"]'):
        label = role_el.get("aria-label")
        if label:
            answers.append(label)
    return answers


def _extract_correct_text_answers(correct_box: Tag) -> list[str]:
    # Confirmed structure (see docs/ANALYSIS.md): one accepted answer per
    # .freebirdFormviewerViewItemsTextCorrectAnswer div, e.g. a short-answer question
    # can accept both "0011 0111" and "00110111" as separate divs here.
    value_tags = correct_box.select(".freebirdFormviewerViewItemsTextCorrectAnswer")
    if value_tags:
        return [t for t in (_clean_text(v) for v in value_tags) if t]
    heading = correct_box.select_one(".freebirdFormviewerViewItemsItemGradingCorrectAnswerBoxHeading")
    if heading is not None:
        heading.decompose()
    text = _clean_text(correct_box)
    return [text] if text else []


def _parse_question(item: Tag) -> Question:
    item_id = item.get("data-item-id")
    required = (item.get("data-required") or "").lower() == "true"
    points = _extract_points(item)
    help_text = _clean_text(item.select_one(".freebirdFormviewerViewItemsItemItemHelpText"))
    has_image = item.select_one("img") is not None

    text = _extract_title_text(item)
    q_type = _classify(item)

    correct_box = item.select_one(".freebirdFormviewerViewItemsItemGradingCorrectAnswerBox")

    options: list[str] = []
    correct_answers: list[str] = []
    warnings: list[str] = []

    if q_type in (QuestionType.SINGLE_CHOICE, QuestionType.MULTI_CHOICE):
        options = _extract_choice_options(item, correct_box)
        if correct_box is not None:
            correct_answers = _extract_correct_choice_answers(correct_box)
        if not options:
            warnings.append("Could not extract answer options for this question; converted to open text.")
            q_type = QuestionType.UNSUPPORTED
    elif q_type in (QuestionType.SHORT_TEXT, QuestionType.LONG_TEXT):
        if correct_box is not None:
            correct_answers = _extract_correct_text_answers(correct_box)
    else:
        warnings.append("Unrecognised question structure; converted to an open text placeholder.")

    if has_image:
        warnings.append("This question contained an image, which was not carried over (see README).")

    if not text:
        text = f"Untitled question ({item_id or 'unknown id'})"
        warnings.append("Question text could not be extracted.")

    return Question(
        item_id=item_id,
        text=text,
        question_type=q_type,
        required=required,
        points=points,
        help_text=help_text,
        options=options,
        correct_answers=correct_answers,
        had_image=has_image,
        warnings=warnings,
    )


def parse_quiz(html: str, source_filename: str) -> Quiz:
    soup = BeautifulSoup(html, "lxml")

    title = _clean_text(soup.select_one(".freebirdFormviewerViewHeaderTitle"))
    description = _clean_text(soup.select_one(".freebirdFormviewerViewHeaderDescription"))

    items = soup.select("div.freebirdFormviewerViewItemsItemItem")

    quiz_warnings: list[str] = []

    if not title:
        fallback = source_filename.rsplit(".", 1)[0]
        title = fallback or "Untitled Quiz"
        quiz_warnings.append("Form title could not be extracted; used the filename instead.")

    if not items:
        raise ConversionError("Unsupported question structure")

    questions: list[Question] = []
    for item in items:
        try:
            question = _parse_question(item)
        except Exception as exc:  # noqa: BLE001 - one bad question must not fail the batch
            questions.append(
                Question(
                    item_id=item.get("data-item-id"),
                    text="Question could not be parsed",
                    question_type=QuestionType.UNSUPPORTED,
                    warnings=[f"Parsing error: {exc}"],
                )
            )
            continue
        questions.append(question)

    if not questions:
        raise ConversionError("Failed to extract answers")

    return Quiz(
        title=title,
        description=description,
        questions=questions,
        source_filename=source_filename,
        warnings=quiz_warnings,
    )
