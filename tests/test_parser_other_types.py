"""The first sample ZIP only contained single-choice (radio) questions. Short-answer
(text) questions with multiple accepted answers were later confirmed against a real
export ("Binary Quick Questions" — see tests/fixtures/short_answer_quiz.zip and
test_short_answer_multiple_accepted_answers below), which caught a real bug: the
class name for each accepted answer was guessed wrong
(...TextCorrectAnswerValue instead of the real ...TextCorrectAnswer), silently
falling back to mashing every accepted answer into one string. The fixtures here now
mirror the *confirmed* structure. Checkbox (multi-select) is still unverified against
a real export — see docs/ANALYSIS.md §10.
"""
import zipfile
from pathlib import Path

from app.converter.models import QuestionType
from app.converter.parser import find_form_html, parse_quiz

SHORT_ANSWER_FIXTURE = Path(__file__).parent / "fixtures" / "short_answer_quiz.zip"

CHECKBOX_HTML = """
<div class="freebirdFormviewerViewFormContent">
<div class="freebirdFormviewerViewHeaderTitle">Checkbox Test Quiz</div>
<div class="freebirdFormviewerViewItemList">
<div class="freebirdFormviewerViewItemsItemItem"
     jscontroller="freebird.formviewer.view.items.checkbox.CheckboxController_"
     data-required="true" data-item-id="1">
  <div class="freebirdFormviewerViewItemsItemItemHeader">
    <div class="freebirdFormviewerViewItemsItemItemTitleContainer">
      <div class="freebirdFormviewerViewItemsItemItemTitle exportItemTitle">
        Select all prime numbers
        <span class="freebirdFormviewerViewItemsItemRequiredAsterisk">*</span>
      </div>
    </div>
    <div class="freebirdFormviewerViewItemsItemScore">2 points</div>
  </div>
  <div class="freebirdFormviewerViewItemsCheckboxChoicesContainer">
    <div role="checkbox" aria-label="2" data-value="2"></div>
    <div role="checkbox" aria-label="3" data-value="3"></div>
    <div role="checkbox" aria-label="4" data-value="4"></div>
    <div role="checkbox" aria-label="5" data-value="5"></div>
  </div>
  <div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBox">
    <div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBoxHeading">Correct answer</div>
    <div class="freebirdFormviewerViewItemsCheckboxCorrectAnswerBox">
      <div role="checkbox" aria-label="2"></div>
      <div role="checkbox" aria-label="3"></div>
      <div role="checkbox" aria-label="5"></div>
    </div>
  </div>
</div>
</div>
</div>
"""

SHORT_TEXT_HTML = """
<div class="freebirdFormviewerViewFormContent">
<div class="freebirdFormviewerViewHeaderTitle">Short Answer Test Quiz</div>
<div class="freebirdFormviewerViewItemList">
<div class="freebirdFormviewerViewItemsItemItem"
     jscontroller="freebird.formviewer.view.items.text.TextController_"
     data-required="false" data-item-id="2">
  <div class="freebirdFormviewerViewItemsItemItemHeader">
    <div class="freebirdFormviewerViewItemsItemItemTitleContainer">
      <div class="freebirdFormviewerViewItemsItemItemTitle exportItemTitle">
        What is the capital of France?
      </div>
    </div>
    <div class="freebirdFormviewerViewItemsItemScore">1 point</div>
  </div>
  <div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBox">
    <div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBoxHeading">Correct answers</div>
    <div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBoxContent">
      <div class="freebirdFormviewerViewItemsTextCorrectAnswerBox">
        <div class="freebirdFormviewerViewItemsTextCorrectAnswer">Paris</div>
      </div>
    </div>
  </div>
</div>
</div>
</div>
"""


def test_checkbox_multi_select_best_effort():
    quiz = parse_quiz(CHECKBOX_HTML, "checkbox_test.html")
    assert len(quiz.questions) == 1
    q = quiz.questions[0]
    assert q.question_type == QuestionType.MULTI_CHOICE
    assert q.options == ["2", "3", "4", "5"]
    assert q.correct_answers == ["2", "3", "5"]
    assert q.points == 2
    assert q.required is True


def test_short_text_best_effort():
    quiz = parse_quiz(SHORT_TEXT_HTML, "short_text_test.html")
    assert len(quiz.questions) == 1
    q = quiz.questions[0]
    assert q.question_type == QuestionType.SHORT_TEXT
    assert q.options == []
    assert q.correct_answers == ["Paris"]
    assert q.points == 1
    assert q.required is False


def test_short_answer_multiple_accepted_answers_real_fixture():
    """Regression test for a real bug: a short-answer question accepting more than
    one exact answer (e.g. "0011 0111" and "00110111" for the same binary value)
    must come back as separate list items, not one mashed-together string."""
    with zipfile.ZipFile(SHORT_ANSWER_FIXTURE) as zf:
        files = [(n, zf.read(n)) for n in zf.namelist()]
    name, html = find_form_html(files)
    quiz = parse_quiz(html, name)

    assert len(quiz.questions) == 16
    assert all(q.question_type == QuestionType.SHORT_TEXT for q in quiz.questions)

    q1 = quiz.questions[0]
    assert q1.text == "55"
    assert q1.options == []
    assert q1.correct_answers == ["0011 0111", "00110111"]
    assert q1.points == 1
