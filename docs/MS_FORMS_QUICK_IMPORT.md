# Phase 2 — Microsoft Forms Quick Import Requirements

Researched from Microsoft's official documentation plus Microsoft Q&A / Microsoft
Community Hub threads (Aug 2026). Sources are listed at the bottom. Where sources
disagree or Microsoft has not documented something publicly, this is stated explicitly
rather than guessed — the converter's design choices follow from being honest about
that uncertainty.

## What Quick Import officially supports

Source: [Microsoft Support — Convert a Word or PDF form or quiz to Microsoft Forms](https://support.microsoft.com/en-us/forms/convert-a-word-or-pdf-form-or-quiz-to-microsoft-forms)

- Input: a `.docx` (or PDF) file, **from local disk only** (not OneDrive/SharePoint),
  **max 10 MB**.
- Only **three** content types convert: **titles/subtitles**, **multiple-choice
  questions**, and **open text questions**. Anything else (grids, Likert scales, dates,
  file upload, dropdowns, matching, ranking) is not a supported target type — it either
  gets misread as open text or flagged for manual review after import.
- Guidance for reliable conversion: arrange questions and their options **vertically**,
  keep clear separation between question blocks, **avoid images, figures, tables, and
  complex equations**, use simple text and numbers only.
- After import, Forms shows a review screen with three buckets: missing content,
  uncertain conversions, and unsupported items, each individually resolvable.

## Exact document formatting that reliably parses

No single official "spec" document exists; the pattern below is the intersection of
Microsoft's own guidance and multiple independently-reported working examples
(Microsoft Q&A, Microsoft Community Hub — see sources):

```
1. What is Switzerland's capital?
A. Moscow
B. Washington DC
C. Tokyo
D. Bern

2. Open text question goes here with nothing under it

```

Rules applied by the generator (`app/converter/docx_builder.py`):

- **Question numbering**: plain paragraph, `"<n>. <question text>"`, numerals with a
  period. (Community reports confirm this is what the parser keys off to start a new
  question block — headings are not required and one thread that used Word "Heading 1"
  styling only did so to work around an unrelated problem, not because it's needed.)
- **Choice lettering**: plain paragraphs, `"A. <option text>"`, **capital letters with a
  period**, one option per paragraph, in order. One official Microsoft Q&A thread is
  explicit that **bulleted lists fail to import** ("the format mentioned in the sample
  is mandated and hence we cannot import the old files framed with bulleted choices") —
  so choices are written as plain numbered/lettered paragraphs, never as a Word bullet
  list style.
- **Blank line between question blocks**: an empty paragraph is inserted after each
  question's last option (or after an open-text question with no options) — reported
  as necessary for the parser to reliably detect where one question ends and the next
  begins.
- **No tables, no images, no equations**: the generator never places question content
  in a table and strips inline images from question text (see `docs/ANALYSIS.md` §7).
- **Open text (short/long answer) questions**: emitted as just the numbered question
  line with no lettered options following it, per Microsoft's guidance that this is how
  open text is distinguished from multiple choice during import.
- **Document title**: the Word document's own title becomes the form's title
  ("The Document title gets added as the name of the resultant Form / Quiz" — Microsoft
  Q&A). The generator sets the docx core-properties title *and* puts the quiz title as
  the first paragraph styled as Word's built-in `Title` style, since reports vary on
  which one the importer actually reads — setting both costs nothing and covers either
  behaviour.

## Correct answers and points — the important caveat

This is the one area where sources genuinely conflict, and it matters a lot given the
brief's emphasis on "correct answers and points are essential":

- Microsoft's own official support engineer answer (Microsoft Q&A, "Is there any way to
  import a file of questions with answers instead of answering them manually?"):
  **"This feature is not currently available due to product design limitations."** The
  confirmed, guaranteed workflow is: Quick Import creates the questions and choices,
  then the teacher opens each question in Forms and manually ticks the correct answer
  and sets points via "Add correct answers and point values."
- A separate, more recent Microsoft Community Hub thread reports that appending literal
  lines directly under a question's choices, in this exact form:
  ```
  ANSWER: D
  POINT: 10
  ```
  causes Quick Import to auto-select that choice as correct and set the point value,
  quoting the reporting user directly: *"I couldn't find any public resource that
  mentions the use of ANSWER and POINT but I did test and confirm it worked."* This is
  **not officially documented by Microsoft** and could change or be specific to that
  user's tenant/version.
- Marking a question "required" from the source document is **confirmed not
  possible** (separate Microsoft Community Hub thread, explicit Microsoft response) —
  required must always be toggled manually after import, for every question, every
  time.
- Multi-select ("select all that apply") scoring and per-answer feedback messages are
  likewise confirmed **not settable via import** — always a manual post-import step.

### Design decision

Given the brief's explicit instruction — *"Where multiple formatting approaches are
possible, choose the one most likely to import successfully"* and *"prioritise
conversion accuracy... over visual appearance"* — the generator does **both** of the
following, rather than picking one and hoping:

1. Emits the undocumented-but-tested `ANSWER: <Letter>` / `POINT: <n>` lines under every
   graded question's choices, since it costs nothing if Microsoft ignores it and may
   give a fully-automatic result if it doesn't.
2. **Always** also appends a plain-English, human-readable **Answer Key** section at the
   end of the document (`Question <n>: Correct answer — <text> (<points> point(s))`),
   independent of whether `ANSWER:`/`POINT:` gets parsed. This guarantees that even in
   the worst case (Microsoft only imports questions and choices, exactly as its own
   official support answer says is the guaranteed behaviour), the teacher has everything
   needed to finish the 2-minute manual "tick the correct answer" step per question,
   without needing to go back to Google Classroom.

This is surfaced honestly in the app UI and README: **"Quick Import will reliably
create your questions and choices. Marking correct answers and points automatically is
attempted but not guaranteed by Microsoft — use the Answer Key on the last page of each
document if you need to set them manually."**

## Images

Explicitly advised against by Microsoft's own formatting guidance ("remove figures or
complex equations"; separate community reports of pictures failing to carry through
generally in Forms). The generator never embeds images in the Quick-Import `.docx`. Any
question that referenced an in-question image in the source form is still converted,
with a `[Image omitted — see original Google Form]` note appended to the question text
and a corresponding entry in the batch's error/warning report, so nothing is silently
dropped without the teacher knowing.

## Summary table used by the generator

| Source question type | Quick Import target | Choices written? | Correct answer handling |
|---|---|---|---|
| Radio (single choice) | Multiple choice | Yes, `A.`/`B.`/… | `ANSWER:`/`POINT:` lines + Answer Key entry |
| Checkbox (multi-select) | Multiple choice (single-select on import) | Yes, `A.`/`B.`/… | Answer Key lists all correct options (Quick Import has no multi-answer marking; noted as a required manual step: enable "Multiple answers" + tick all correct choices) |
| Short answer (text) | Open text | No | Answer Key lists accepted answer(s) |
| Long answer (paragraph) | Open text | No | Not graded — omitted from Answer Key |
| Anything else (grid, scale, date, dropdown, file upload, section header) | Open text placeholder carrying the original question text | No | Flagged in the conversion report as "manual review needed" |

## Sources

- [Convert a Word or PDF form or quiz to Microsoft Forms — Microsoft Support](https://support.microsoft.com/en-us/forms/convert-a-word-or-pdf-form-or-quiz-to-microsoft-forms)
- [How to format Word document to have correct formatting for Microsoft Forms — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5496362/how-to-format-word-document-to-have-correct-format)
- [Is there any way to import a file of questions with answers instead of answering them manually? — Microsoft Q&A](https://learn.microsoft.com/en-us/answers/questions/5202143/is-there-any-way-to-import-a-file-of-questions-wit)
- [Ms forms quick import — Microsoft Community Hub](https://techcommunity.microsoft.com/discussions/microsoftforms/ms-forms-quick-import/4150871)
- [MS Forms Quick Import Required question — Microsoft Community Hub](https://techcommunity.microsoft.com/discussions/microsoftforms/ms-forms-quick-import-required-question/4391472)
- [MS Forms "Schnellimport" (Quick import) - formatting — Microsoft Community Hub](https://techcommunity.microsoft.com/discussions/microsoftforms/ms-forms-schnellimportquick-import---formatting/3757433)
- [How to import questions into Microsoft Forms — Jotform Blog](https://www.jotform.com/blog/microsoft-forms-import-questions/)
