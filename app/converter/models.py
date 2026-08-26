"""Data model for a parsed Google Form quiz.

Kept deliberately small and JSON-serialisable-ish (dataclasses of plain types) since it
is the contract between the parser (app/converter/parser.py) and the docx builder
(app/converter/docx_builder.py). See docs/ANALYSIS.md for how each field is derived
from the source HTML.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"    # Google "radio" -> MS Forms multiple choice
    MULTI_CHOICE = "multi_choice"      # Google "checkbox" -> MS Forms multiple choice
    SHORT_TEXT = "short_text"          # Google short answer -> MS Forms open text
    LONG_TEXT = "long_text"            # Google paragraph -> MS Forms open text
    UNSUPPORTED = "unsupported"        # grid/scale/date/dropdown/etc -> open text placeholder


@dataclass
class Question:
    item_id: str | None
    text: str
    question_type: QuestionType
    required: bool = False
    points: int | None = None
    help_text: str | None = None
    options: list[str] = field(default_factory=list)
    correct_answers: list[str] = field(default_factory=list)
    had_image: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def is_graded(self) -> bool:
        return bool(self.correct_answers) and self.points is not None


@dataclass
class Quiz:
    title: str
    description: str | None = None
    questions: list[Question] = field(default_factory=list)
    source_filename: str | None = None
    warnings: list[str] = field(default_factory=list)
