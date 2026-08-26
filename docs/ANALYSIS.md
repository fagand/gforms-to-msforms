# Phase 1 — Analysis of Migrated Google Forms ZIP Files

This document records what was actually found inside the sample ZIP supplied for this
project (`DR1 Storing Whole Numbers Quiz.zip`), produced by a Google Classroom →
migration export. All conversion logic in this project is built around these confirmed
structures, not around generic assumptions about Google Forms exports.

## 1. ZIP contents / folder structure

A single migrated form ZIP contains **three files, flat at the root** (no subfolders):

```
DR1 Storing Whole Numbers Quiz.zip
├── DR1 Storing Whole Numbers Quiz.html   ← the form itself (485 KB, minified)
├── DR1 Storing Whole Numbers Quiz.csv    ← response/submission data (student answers)
└── 1.jpg                                  ← orphaned banner image (see §7)
```

Key points:
- The **HTML file shares the form's title as its filename** (`<Form Title>.html`).
- The **CSV is response data** (one row per submission: timestamp, username/email, then
  one column per question containing that student's answer). It is **not** the form
  definition and contains no correct-answer information. It is not used for conversion.
- Any `.jpg`/`.png` files sitting in the ZIP root are **not necessarily referenced by
  the HTML** — see §7.
- The engine must not assume a fixed filename; it locates the form HTML by *content*
  (see §2), not by name pattern, since a school may rename files or a batch may contain
  many differently-named forms.

## 2. Identifying the form HTML file

The HTML is a static export of Google's own "freebird" form-viewer markup (the same
markup/CSS Google Forms itself renders, minified into a single page: full `<style>`
block copied from `docs/spreadsheets/forms` inline, followed by a static, disabled,
non-interactive `<body>` snapshot of the form — this is the Classroom "export"/"takeout"
view, not the live editable form).

Reliable identification signal: the file is an `.html` file whose content contains the
marker class `freebirdFormviewerViewFormContent` (present in the body wrapper). This is
more robust than matching on filename.

## 3. Form title

```html
<div class="freebirdFormviewerViewHeaderTitle exportFormTitle freebirdCustomFont" ...>
  DR1 Storing Whole Numbers Quiz
</div>
```
`.freebirdFormviewerViewHeaderTitle` holds the plain-text form title. This is also used
as the output `.docx` filename.

## 4. Form description

No description was present in the sample form. The class that Google's stylesheet
defines for this (confirmed present in the shared CSS even though unused here) is
`.freebirdFormviewerViewHeaderDescription`. The parser looks for it and, if present,
places it as an introductory paragraph under the title in the output document.

## 5. Question structure

Each question is one `<div class="freebirdFormviewerViewItemsItemItem">` inside
`.freebirdFormviewerViewItemList`. All 13 questions in the sample use this exact shape:

```html
<div class="freebirdFormviewerViewItemsItemItem"
     jsname="item_"
     jscontroller="freebird.formviewer.view.items.radio.RadioController_"
     data-required="true"
     data-item-id="195096208">
  <div class="freebirdFormviewerViewItemsItemItemHeader">
    <div class="...ItemItemTitleContainer">
      <div class="freebirdFormviewerViewItemsItemItemTitle exportItemTitle" ...>
        <span class="freebirdCustomFont">What number system do computers use to store data? <br></span>
        <span class="freebirdFormviewerViewItemsItemRequiredAsterisk" aria-label="Required question">*</span>
      </div>
    </div>
    <div class="freebirdFormviewerViewItemsItemScore ...ItemHint" ...>1 point</div>
  </div>
  <!-- answer widget for this question type, see §6 -->
</div>
```

Confirmed, reliable extraction points:

| Data | Source |
|---|---|
| Question ID | `data-item-id` attribute on the item div |
| Question type | Substring of the `jscontroller` attribute (`...radio...`, `...checkbox...`, `...text...`, etc.) |
| Question text | `.freebirdFormviewerViewItemsItemItemTitle` text content (with the trailing `*` required-marker span stripped) |
| Required flag | `data-required="true"` attribute — **not** the visual `*`, which is unreliable on its own |
| Points | `.freebirdFormviewerViewItemsItemScore` text, pattern `"<n> point(s)"` |
| Per-question help/description | `.freebirdFormviewerViewItemsItemItemHelpText` (not present in sample; class confirmed in shared CSS) |

Question text can contain inline formatting tags (`<br>`, `<b>…</b>` were both observed,
e.g. *"which **positions** contain a 1?"*). Formatting is flattened to plain text —
Microsoft Forms Quick Import works from plain paragraph text, and preserving rich
inline formatting risks breaking the parser (see `docs/MS_FORMS_QUICK_IMPORT.md`).

## 6. Answer options and correct answers (the critical pattern)

All 13 sample questions are **single-answer multiple choice** (`RadioController_`).
Structure:

```html
<div class="freebirdFormviewerViewItemsRadioChoicesContainer ...">
  <div class="freebirdFormviewerViewItemsRadioOptionContainer">
    <label ...>
      <div id="i5" role="radio" aria-label="Decimal" aria-disabled="true"
           data-value="Decimal" aria-checked="false"> ... </div>
      ...
    </label>
  </div>
  <!-- one such block per option, in display order -->
</div>
<input type="hidden" name="entry.1869934059" disabled>

<div class="freebirdFormviewerViewItemsItemGradingCorrectAnswerBox">
  <div class="...CorrectAnswerBoxHeading">Correct answer</div>
  <div class="...CorrectAnswerBoxContent">
    <div class="freebirdFormviewerViewItemsRadioCorrectAnswerBox">
      <label ...>
        <div role="radio" aria-label="Binary" aria-checked="true" ...> ... </div>
      </label>
    </div>
  </div>
</div>
```

This is the single most important discovery for this project:

- **All answer options are always rendered `aria-checked="false"` / disabled** in the
  main choices list — the option list itself never marks which one is correct.
- **The correct answer is only ever revealed in a separate, sibling block**:
  `.freebirdFormviewerViewItemsItemGradingCorrectAnswerBox`. This wrapper class is
  **generic across question types** (radio/checkbox/text all use the same outer
  `...ItemGradingCorrectAnswerBox` wrapper, with a type-specific inner box —
  `RadioCorrectAnswerBox`, `CheckboxCorrectAnswerBox`, `TextCorrectAnswer` — confirmed
  present together in the shared CSS even though this sample only exercises the radio
  variant).
- Matching a correct answer back to its option is done by **exact text match**
  (`aria-label`/`data-value`), not by position — options are not guaranteed to be
  reordered consistently between the choices list and the correct-answer box, so
  position-based matching is not used.
- If `.freebirdFormviewerViewItemsItemGradingCorrectAnswerBox` is absent for a question,
  the question is treated as **ungraded** (no correct answer to carry through) rather
  than as an error.
- Checkbox (multi-select) questions were not present in this sample, but the shared CSS
  confirms Google uses the same pattern (`freebirdFormviewerViewItemsCheckboxCorrect`,
  `...CheckboxCorrectAnswerBox`) — the parser handles this generically (see
  `docs/MS_FORMS_QUICK_IMPORT.md` / engine design) rather than hard-coding only the
  radio case, but this path has not been verified against a real multi-select export.

## 7. Images

`1.jpg` is present in the ZIP but is **never referenced anywhere in the HTML** — no
`<img src="1.jpg">`, no CSS `background-image`, nothing. Opening it shows it is the
school's own header banner/crest graphic (a "George Watson's College" logo banner),
i.e. **branding artifact left over from the export, unrelated to any quiz question**.

Assumption adopted: images sitting in the ZIP that are not referenced by a relative
`<img src="...">` inside an item's DOM subtree are **decorative/orphaned** and are
**not** included in the output document. Only images referenced from *inside* a
question's markup (class `freebirdFormviewerViewItemsEmbeddedobjectImage`, confirmed in
shared CSS, not exercised in this sample) would be treated as question content — and
even then, they are deliberately **not embedded inline** in the Quick-Import `.docx`
(Microsoft's own guidance says to strip images/figures for reliable import — see
`docs/MS_FORMS_QUICK_IMPORT.md` §Images). Instead the conversion report flags
"question N contained an image that was not carried over."

## 8. Required questions

All 13 questions in the sample are required (`data-required="true"`). Confirmed as the
reliable signal (§5). Microsoft Forms Quick Import has **no way to set "required" from
the source document** (confirmed in Phase 2 research) — this is surfaced to the teacher
as a note, not silently dropped.

## 9. Feedback / per-answer messages

`.freebirdFormviewerViewItemsItemGradingFeedbackBox` exists in the DOM (empty,
`jsname="feedbackBox_"`) but carries no content in this sample — Google only populates
this when the form author added answer-specific feedback text. The parser reads it if
present but Microsoft Forms Quick Import has no import path for per-answer feedback
messages (confirmed in Phase 2), so it is surfaced in the report as "not carried over"
rather than silently discarded when found.

## 10. Variation across forms

Only one form was supplied, so cross-form variation could not be directly observed.
The engine is therefore written defensively (see `app/converter/parser.py`):

- Type dispatch is driven by matching substrings in `jscontroller` (`radio`,
  `checkbox`, `text`) rather than an exhaustive fixed list, so an unrecognised
  `jscontroller` value degrades to a generic "unsupported question" outcome for *that
  question only* instead of aborting the whole file.
- Any question the parser cannot confidently classify is still emitted as an open-text
  question carrying the original question text, with a warning in the conversion
  report — the rest of the form still converts. This matches the brief's instruction
  to prioritise reliability over exhaustive feature coverage.
- The HTML-file-discovery step tolerates a ZIP that contains extra files (images, CSV,
  a `readme`, nested folders) — it scans for *any* `.html` file containing the
  `freebirdFormviewerViewFormContent` marker rather than assuming a single fixed
  filename or flat layout.
