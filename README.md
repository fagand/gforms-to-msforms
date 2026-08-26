# Google Forms → Microsoft Forms Converter

A small, self-hosted web app for school staff migrating quizzes from Google Forms
(via Google Classroom's export/"takeout" ZIP) to Microsoft Forms. Upload up to 20
migrated Google Forms ZIP files, and the app converts each one into a `.docx` file
shaped specifically for **Microsoft Forms Quick Import**, then bundles all the
results into a single downloadable ZIP.

Built with **FastAPI** (Python) on the backend and plain **HTML/CSS/JavaScript** on
the frontend — no build step, no frontend framework, easy to read and host.

## Why this exists / how it works

Google Classroom's Forms migration tool exports each form as a ZIP containing the
form's own HTML (Google's internal "freebird" form-viewer markup) plus a CSV of
student responses. That HTML is a static, disabled snapshot of the form that — for
quiz forms — **also reveals each question's correct answer** in a hidden "Correct
answer" box for anyone who inspects the markup. This app parses that structure
directly (see [`docs/ANALYSIS.md`](docs/ANALYSIS.md) for exactly what was found and
how) and regenerates it as a Word document written in the format Microsoft Forms'
Quick Import feature expects (see [`docs/MS_FORMS_QUICK_IMPORT.md`](docs/MS_FORMS_QUICK_IMPORT.md)
for that research).

**Important, honest caveat:** Microsoft's own support documentation confirms Quick
Import does **not guarantee** that pre-defined correct answers, point values, or
"required" flags carry over automatically — the only 100%-guaranteed workflow is
Quick Import creating your questions and choices, then a teacher manually ticking the
correct answer per question in Microsoft Forms. This app tries an undocumented (but
independently reported-working) `ANSWER:`/`POINT:` marker convention to automate that
step, **and** always appends a plain-English **Answer Key** page to every generated
document, so the manual step (if needed) takes seconds per question instead of
requiring you to go back to the original Google Form.

## Features

- Drag-and-drop upload of up to 20 ZIP files at once
- Live, per-file progress with no page reload (Server-Sent Events)
- Partial-failure handling — one bad ZIP never blocks the rest of the batch
- A single "Download All Documents" ZIP of every successful conversion
- Every generated `.docx` includes an Answer Key + Conversion Notes page so nothing
  is silently lost (dropped images, unsupported question types, etc. are all listed)
- No data retained: uploads and generated files live in a per-batch temp folder that
  is deleted as soon as you download, and swept automatically after 2 hours regardless

## Supported question types

| Google Forms question type | Converts to |
|---|---|
| Multiple choice (single answer) | Microsoft Forms multiple choice, with an attempted automatic correct-answer + points marking, plus an Answer Key entry |
| Checkboxes (multiple answers) | Microsoft Forms multiple choice (choices only — Quick Import has no way to mark a question multi-select on import); Answer Key lists every correct option and reminds you to flip on "Multiple answers" |
| Short answer | Microsoft Forms open text; Answer Key lists the accepted answer(s) |
| Paragraph (long answer) | Microsoft Forms open text (ungraded) |
| Anything else (grid, scale, date, dropdown, file upload, section headers) | Converted to an open-text placeholder carrying the original question text, and flagged in that document's Conversion Notes for manual review |

Images referenced inside a question are **not** embedded in the output document —
Microsoft's own guidance says to strip images for reliable Quick Import — the
question is still converted, with a note added to the Conversion Notes section.
Images that just happen to be sitting in the ZIP without being referenced by the form
(e.g. a school's banner/logo left over from the export) are ignored entirely.

## Project layout

```
gforms-to-msforms/
├── app/
│   ├── main.py              # FastAPI app: upload / SSE progress / download endpoints
│   ├── jobs.py               # per-batch temp-folder + cleanup bookkeeping
│   ├── converter/
│   │   ├── models.py          # Quiz / Question dataclasses
│   │   ├── parser.py          # Google Forms HTML -> Quiz (see docs/ANALYSIS.md)
│   │   ├── docx_builder.py    # Quiz -> Quick-Import-shaped .docx
│   │   ├── pipeline.py        # ZIP bytes -> docx bytes, with per-file error isolation
│   │   └── errors.py
│   └── static/                # the single-page frontend (HTML/CSS/JS, no build step)
├── docs/
│   ├── ANALYSIS.md            # Phase 1: what's actually inside a migrated ZIP
│   └── MS_FORMS_QUICK_IMPORT.md  # Phase 2: Quick Import format research
├── deploy/
│   ├── nginx.conf              # reverse proxy config (SSE-aware)
│   └── gforms2msforms.service  # systemd unit
├── examples/
│   └── input_zip_example/      # a real (student-data-free) sample input ZIP
├── tests/
├── passenger_wsgi.py            # entry point for cPanel/Passenger shared hosting
└── requirements.txt
```

## Installation (local / development)

Requires Python 3.11+.

```bash
git clone <this-repo> gforms-to-msforms
cd gforms-to-msforms
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8811
```

Then open http://127.0.0.1:8811 in a browser.

To run the test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

## Deploying on a standard Linux server (production)

This assumes a Debian/Ubuntu-family server with Python 3.11+, Nginx, and systemd —
adjust package manager commands for other distros.

1. **Create a dedicated user and install the app:**

   ```bash
   sudo useradd --system --home /opt/gforms2msforms --shell /usr/sbin/nologin gforms2msforms
   sudo mkdir -p /opt/gforms2msforms
   sudo git clone <this-repo> /opt/gforms2msforms
   cd /opt/gforms2msforms
   sudo python3 -m venv .venv
   sudo .venv/bin/pip install -r requirements.txt
   sudo chown -R gforms2msforms:gforms2msforms /opt/gforms2msforms
   ```

2. **Install and start the systemd service:**

   ```bash
   sudo cp deploy/gforms2msforms.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now gforms2msforms
   sudo systemctl status gforms2msforms
   ```

3. **Configure Nginx as a reverse proxy:**

   ```bash
   sudo cp deploy/nginx.conf /etc/nginx/sites-available/gforms2msforms
   # edit server_name in that file to match your hostname
   sudo ln -s /etc/nginx/sites-available/gforms2msforms /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```

   The Nginx config disables proxy buffering — this is required for the live
   progress updates to actually stream to the browser instead of arriving all at
   once at the end.

4. **(Recommended) Enable HTTPS**, e.g. with Certbot:

   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d forms.example.school.uk
   ```

5. Visit `https://forms.example.school.uk` and confirm the upload/convert/download
   flow works end to end with a real migrated ZIP.

### Updating

```bash
cd /opt/gforms2msforms
sudo -u gforms2msforms git pull
sudo -u gforms2msforms .venv/bin/pip install -r requirements.txt
sudo systemctl restart gforms2msforms
```

## Deploying on cPanel shared hosting

Shared cPanel hosting doesn't give you root, systemd, or a real Nginx/Apache config
to edit, so the guide above doesn't apply. Instead, use cPanel's **"Setup Python
App"** feature (Software section — sometimes called "Application Manager"; it's
built on Phusion Passenger, and is what most hosts use for Python apps).

If your cPanel doesn't have that icon at all, your host doesn't support running a
persistent Python app of any kind on that plan — check with your host, or ask about
switching to a plan/product that includes it.

**One thing to know going in:** Passenger's classic mode runs Python apps as WSGI,
but this app is built on FastAPI, which speaks ASGI. `passenger_wsgi.py` (included
in the repo) bridges the two automatically — you don't need to change any app code.
The live progress feature (Server-Sent Events) still works through that bridge, but
whether it *streams live* in the browser rather than jumping to 100% at the end also
depends on your specific host's Apache/Passenger setup, which varies host to host —
conversions succeed correctly either way, so test it after deploying and treat it as
a cosmetic detail, not a blocker.

1. **cPanel → Software → Setup Python App → Create Application**
   - **Python version**: pick the highest 3.11+ available.
   - **Application root**: e.g. `gforms2msforms` (this becomes a folder in your home directory).
   - **Application URL**: the domain or subdomain you want it on, e.g. `forms.yourschool.uk`.
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
   - Click **Create**.

2. **Upload the code** into the application root cPanel just created. Easiest via
   Git if your host's cPanel has "Git Version Control" (point it at this repo and
   the same application root); otherwise upload a ZIP of the project via File
   Manager and extract it there, or `scp`/SFTP it up if your host gives you SSH.

3. **Install dependencies.** The "Setup Python App" page gives you a command to
   enter its virtualenv, something like:

   ```bash
   source /home/<cpanel-username>/virtualenv/gforms2msforms/3.11/bin/activate
   cd /home/<cpanel-username>/gforms2msforms
   pip install -r requirements.txt
   ```

   Run that (via cPanel's Terminal app if you have one enabled, or over SSH if your
   host provides it).

4. **Restart the app** — back on the Setup Python App page, click **Restart**.

5. Visit the domain/subdomain you configured and confirm the upload/convert/download
   flow works with a real migrated ZIP.

### Updating

Pull or re-upload the changed files into the application root, then re-run
`pip install -r requirements.txt` in the app's virtualenv if `requirements.txt`
changed, and click **Restart** on the Setup Python App page.

### If it doesn't work at all

- **500 error / blank page**: check the "Errors" / log file link on the Setup
  Python App page — it shows the Python traceback.
- **No "Setup Python App" option**: your hosting plan doesn't support persistent
  Python apps; ask your host, or consider a small VPS instead (see the Linux
  deployment guide above) — a VPS costing a few pounds a month gives you full
  control and is the more common route for self-hosted school tools like this one.
- **Uploads fail or time out**: some cPanel/Apache configs cap request body size or
  execution time lower than this app's own limits — ask your host to raise
  `LimitRequestBody` / any Passenger request timeout for this application if you
  hit this with larger batches.

## Security notes

- Only `.zip` files are accepted; every upload is checked by extension, magic bytes,
  and size before extraction.
- ZIP extraction guards against path-traversal ("zip-slip") entries and rejects
  archives with unsafe paths, oversized members, or too many members.
- Every batch gets its own temp folder (never written into the app's own
  directories); it's deleted immediately after download, and a background sweep
  removes any batch older than 2 hours regardless (e.g. if a browser tab is closed
  mid-conversion).
- Uploaded filenames are sanitized before ever touching the filesystem.
- No student response data (the CSV inside a migrated ZIP) is used or retained by
  this app — only the form's own question/answer structure is read.

## Known limitations (by design — see docs/MS_FORMS_QUICK_IMPORT.md)

- Microsoft Forms Quick Import does not guarantee automatic correct-answer, points,
  or required-question import — use each document's Answer Key page as the fallback.
- Multi-select ("choose all that apply") questions always need a manual step in
  Microsoft Forms after import to enable "Multiple answers" and tick every correct
  option.
- Grids, scales, dates, dropdowns, and file-upload questions are not question types
  Quick Import itself supports — they're carried over as an open-text placeholder so
  no content is lost, but they'll need to be rebuilt as their real type manually.
- Images are intentionally not embedded in the output document (Microsoft's own
  guidance for reliable Quick Import).
