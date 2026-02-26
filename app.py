"""Flask web application for Contract Agent UI."""

import json
import os
import tempfile
from pathlib import Path
from typing import Callable

import PyPDF2
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from run_agent import analyze_contract

MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx", "doc"}
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_UPLOAD_DIR = Path(tempfile.gettempdir()) / "contract-agent-uploads"

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE_BYTES
app.config["UPLOAD_FOLDER"] = os.environ.get("UPLOAD_FOLDER", str(DEFAULT_UPLOAD_DIR))
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)


def _json_error(message: str, status_code: int):
    return jsonify({"error": message}), status_code


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from PDF file."""
    text = []
    try:
        with open(filepath, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text.append(page.extract_text())
        return "\n".join(text)
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_docx(filepath: str) -> str:
    """Extract text from DOCX file."""
    try:
        from docx import Document

        doc = Document(filepath)
        text = [paragraph.text for paragraph in doc.paragraphs]
        return "\n".join(text)
    except ImportError:
        return "DOCX support requires python-docx package. Install: pip install python-docx"
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"


def extract_text_from_file(filepath: str, filetype: str) -> str:
    """Extract text based on file type."""
    extractors: dict[str, Callable[[str], str]] = {
        "pdf": extract_text_from_pdf,
        "docx": extract_text_from_docx,
        "doc": extract_text_from_docx,
    }
    if filetype in extractors:
        return extractors[filetype](filepath)

    with open(filepath, "r", encoding="utf-8", errors="ignore") as text_file:
        return text_file.read()


def _analyze_text_to_json(text: str) -> dict:
    result_json = analyze_contract(text)
    return json.loads(result_json)


@app.route("/")
def index():
    """Render the main upload page."""
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload_file():
    """Handle file upload and analysis."""
    if "file" not in request.files:
        return _json_error("No file provided", 400)

    file = request.files["file"]
    if file.filename == "":
        return _json_error("No file selected", 400)
    if not allowed_file(file.filename):
        return _json_error("File type not allowed. Use: txt, pdf, docx, doc", 400)

    filepath = ""
    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        filetype = filename.rsplit(".", 1)[1].lower()
        text = extract_text_from_file(filepath, filetype)
        if text.startswith("Error") or text.startswith("DOCX support"):
            return _json_error(text, 500)

        return jsonify(_analyze_text_to_json(text)), 200
    except Exception as e:
        return _json_error(f"Processing failed: {str(e)}", 500)
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)


@app.route("/api/analyze-text", methods=["POST"])
def analyze_text():
    """Handle direct text input."""
    data = request.get_json()
    if not data or "text" not in data:
        return _json_error("No text provided", 400)

    text = data.get("text", "").strip()
    if len(text) < 10:
        return _json_error("Contract text too short", 400)

    try:
        return jsonify(_analyze_text_to_json(text)), 200
    except Exception as e:
        return _json_error(f"Analysis failed: {str(e)}", 500)


if __name__ == "__main__":
    debug_flag = os.environ.get("FLASK_DEBUG", "False").lower() in ("1", "true", "yes")
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=debug_flag, port=port)
