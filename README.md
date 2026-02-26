# Contract-Agent

Production-grade contract intelligence with a multi-agent risk engine.

## Overview

- **Document Structuring Agent** – parses text, extracts parties and builds
  obligation graph.
- **Liability Extraction Agent** – identifies clauses related to liabilities.
- **Red Flag Detection Agent** – applies explicit rules, handles asymmetry,
  illusory caps, indemnity depth, financial stacking, survival amplification,
  and more.
- **Risk Scoring Agent** – cluster-based scoring with dynamic multipliers.

## Running locally

1. Create & activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start the web UI:
   ```bash
   ./venv/bin/python app.py
   ```
4. Open `http://localhost:5000` in a browser.

## API Endpoints

- `POST /api/upload` – multipart form field `file` with contract document
  (txt/pdf/docx). Returns JSON analysis.
- `POST /api/analyze-text` – JSON `{ "text": "..." }`.

## Gemini Reasoning Layer (No Fallback)

The app uses Gemini for final reasoning output and plain-language resolutions.
No deterministic fallback is used if Gemini is unavailable.

Set these environment variables:

```bash
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.5-flash
GEMINI_THINKING_BUDGET=1024
GEMINI_MAX_TEXT_CHARS=30000
```

If `GEMINI_API_KEY` is missing/invalid or Gemini fails, analysis now returns
an explicit error (shown in the UI) and does not fall back.

## Deployment on Vercel

Set required environment variables first:

```bash
vercel env add GEMINI_API_KEY production
vercel env add GEMINI_MODEL production
vercel env add GEMINI_THINKING_BUDGET production
vercel env add GEMINI_MAX_TEXT_CHARS production
```

Suggested values:
- `GEMINI_MODEL`: `gemini-2.5-flash`
- `GEMINI_THINKING_BUDGET`: `1024`
- `GEMINI_MAX_TEXT_CHARS`: `30000`

Then deploy:

```bash
vercel --prod
```

Vercel routes all traffic to `api/index.py`, which imports the Flask app from
`app.py`.

Troubleshoot by running `vercel dev` locally and examining the function
logs; common errors include missing packages or exceeding the size limit.

## Sample contract

A sample under `samples/test_contract.txt` shows the kinds of clauses the
engine flags.

## Testing

```bash
./venv/bin/python -m pytest -q
```

The test suite includes a basic flow that verifies the analysis pipeline.

## Further work

- Improve party extraction and asymmetry computation.
- Add downloadable JSON/CSV export in UI.
- Extend rule engine with templates and negotiation suggestions.

---

© 2026 Contract-Agent
