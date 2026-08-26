"""The one supplied sample ZIP only contained single-choice (radio) questions.
Checkbox (multi-select) and text questions are handled generically by the parser
(same role-based / correct-answer-box extraction, see app/converter/parser.py), but
that code path was never exercised against a real export. These tests build minimal
synthetic fragments that mirror the *documented* Google Forms DOM conventions (see
docs/ANALYSIS.md §10) to check the generic extraction logic actually works, and to
flag clearly if it doesn't — rather than shipping an untested assumption silently.
"""
from app.converter.models import QuestionType
from app.converter.parser import parse_quiz

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
    <div class="freebirdFormviewerViewItemsTextCorrectAnswer">
      <span class="freebirdFormviewerViewItemsTextCorrectAnswerValue">Paris</span>
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
