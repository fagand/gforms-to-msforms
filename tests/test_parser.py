from pathlib import Path

from app.converter.models import QuestionType
from app.converter.parser import find_form_html, parse_quiz

FIXTURE_HTML = (Path(__file__).parent / "fixtures" / "sample_quiz.zip")


def _load_html() -> tuple[str, str]:
    import zipfile

    with zipfile.ZipFile(FIXTURE_HTML) as zf:
        files = [(n, zf.read(n)) for n in zf.namelist()]
    return find_form_html(files)


def test_finds_form_html():
    name, html = _load_html()
    assert name.endswith(".html")
    assert "freebirdFormviewerViewFormContent" in html


def test_parses_title_and_all_questions():
    name, html = _load_html()
    quiz = parse_quiz(html, name)
    assert quiz.title == "DR1 Storing Whole Numbers Quiz"
    assert len(quiz.questions) == 13
    assert all(q.question_type == QuestionType.SINGLE_CHOICE for q in quiz.questions)


def test_extracts_correct_answers_and_points():
    name, html = _load_html()
    quiz = parse_quiz(html, name)
    q1 = quiz.questions[0]
    assert q1.text == "What number system do computers use to store data?"
    assert q1.options == ["Decimal", "Hexadecimal", "Binary", "Octal"]
    assert q1.correct_answers == ["Binary"]
    assert q1.points == 1
    assert q1.required is True


def test_no_form_html_raises():
    from app.converter.errors import ConversionError

    import pytest

    with pytest.raises(ConversionError, match="No Google Form HTML found"):
        find_form_html([("readme.txt", b"hello")])
