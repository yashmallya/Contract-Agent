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

## Deployment on Vercel

Add a `vercel.json` file (already included) with the Python build settings.
Use the Vercel CLI to deploy:

```bash
vercel --prod
```

Vercel will treat `app.py` as a serverless function. Ensure `requirements.txt`
lists all dependencies.

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
