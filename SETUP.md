# Web UI Setup & Quickstart

## 🚀 Installation & Running the Web Interface

### Step 1: Install Dependencies

**Option A: Using pip**
```bash
pip install -r requirements.txt
```

**Option B: Using Poetry**
```bash
poetry install
```

### Step 2: Run the Flask Application

```bash
python app.py
```

The application will start on: **http://localhost:5000**

### Step 3: Open in Browser

Open your browser and navigate to:
```
http://localhost:5000
```

---

## 📋 Features

### Upload Documents
- Drag & drop support
- Supported formats: PDF, DOCX, DOC, TXT
- Maximum file size: 50 MB
- Automatic text extraction

### Paste Text
- Direct text input for small contracts
- Minimum text length: 10 characters

### Analysis Results
- **Overall Risk Score** (0-100 scale)
- **Risk Level** categorization (Low/Moderate/High/Critical)
- **Identified Liability Clauses** with severity ratings
- **Red Flags** with explanations and suggestions

---

## 🏗️ Project Structure

```
Contract-Agent/
├── app.py                    # Flask application
├── run_agent.py              # Contract analysis pipeline
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Poetry configuration
│
├── src/contract_agent/       # Core analysis modules
│   ├── __init__.py
│   ├── structuring.py        # Text extraction & segmentation
│   ├── liability_extraction.py
│   ├── red_flag_detection.py
│   ├── risk_scoring.py
│   ├── rules.py
│   └── output.py
│
├── templates/                # HTML templates
│   └── index.html
│
├── static/                   # Frontend assets
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
├── uploads/                  # Temporary uploaded files
│
└── tests/                    # Test suite
    └── test_agents.py
```

---

## 🔧 Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root:

```
FLASK_ENV=development
FLASK_DEBUG=True
MAX_UPLOAD_MB=50
PORT=5000
```

---

## 👥 API Endpoints

### `POST /api/upload`
Uploads and analyzes a document.

**Request:**
```
multipart/form-data: file
```

**Response:**
```json
{
  "contract_summary": "...",
  "overall_risk_score": 72,
  "risk_level": "High",
  "liability_clauses": [...],
  "red_flags": [...]
}
```

### `POST /api/analyze-text`
Analyzes pasted contract text.

**Request:**
```json
{
  "text": "contract content here..."
}
```

**Response:** Same as upload endpoint.

---

## 🐛 Troubleshooting

### Issue: Module not found errors
```bash
pip install --upgrade -r requirements.txt
```

### Issue: Port 5000 already in use
Change the port in `app.py`:
```python
app.run(debug=True, port=5001)
```

### Issue: PDF extraction not working
Install additional system dependencies:
```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils
```

---

## 🚀 Production Deployment

For production, use a WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or deploy to cloud platforms like:
- **Heroku**
- **AWS Elastic Beanstalk**
- **Google Cloud Run**
- **Azure App Service**
- **DigitalOcean App Platform**

---

## 📝 Next Steps

1. Implement full rule engine in `red_flag_detection.py`
2. Add contract template comparison mode
3. Create admin dashboard for batch processing
4. Add export to PDF/Excel functionality
5. Integrate with legal databases
6. Add user authentication & audit logging

---

## 📄 License

This project is proprietary. All rights reserved.
