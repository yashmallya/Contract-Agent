"""Flask web application for Contract Agent UI."""

import os
import json
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import PyPDF2

from run_agent import analyze_contract

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# Create uploads folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_pdf(filepath):
    """Extract text from PDF file."""
    text = []
    try:
        with open(filepath, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text.append(page.extract_text())
        return '\n'.join(text)
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"


def extract_text_from_docx(filepath):
    """Extract text from DOCX file."""
    try:
        from docx import Document
        doc = Document(filepath)
        text = [paragraph.text for paragraph in doc.paragraphs]
        return '\n'.join(text)
    except ImportError:
        return "DOCX support requires python-docx package. Install: pip install python-docx"
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"


def extract_text_from_file(filepath, filetype):
    """Extract text based on file type."""
    if filetype == 'pdf':
        return extract_text_from_pdf(filepath)
    elif filetype in ['docx', 'doc']:
        return extract_text_from_docx(filepath)
    else:  # txt
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()


@app.route('/')
def index():
    """Render the main upload page."""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file upload and analysis."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Use: txt, pdf, docx, doc'}), 400

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Extract text based on file type
        filetype = filename.rsplit('.', 1)[1].lower()
        text = extract_text_from_file(filepath, filetype)

        if text.startswith("Error") or text.startswith("DOCX support"):
            return jsonify({'error': text}), 500

        # Run analysis
        result_json = analyze_contract(text)
        result = json.loads(result_json)

        # Clean up uploaded file
        os.remove(filepath)

        return jsonify(result), 200

    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500


@app.route('/api/analyze-text', methods=['POST'])
def analyze_text():
    """Handle direct text input."""
    data = request.get_json()

    if not data or 'text' not in data:
        return jsonify({'error': 'No text provided'}), 400

    text = data.get('text', '').strip()

    if len(text) < 10:
        return jsonify({'error': 'Contract text too short'}), 400

    try:
        result_json = analyze_contract(text)
        result = json.loads(result_json)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
