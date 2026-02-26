// Tab switching
document.querySelectorAll('.tab-button').forEach(button => {
    button.addEventListener('click', function() {
        const tabName = this.getAttribute('data-tab');
        switchTab(tabName);
    });
});

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active state from buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

// Drag and drop
const dragDropArea = document.getElementById('dragDropArea');
const fileInput = document.getElementById('fileInput');

dragDropArea.addEventListener('click', () => fileInput.click());

dragDropArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    dragDropArea.classList.add('dragging');
});

dragDropArea.addEventListener('dragleave', () => {
    dragDropArea.classList.remove('dragging');
});

dragDropArea.addEventListener('drop', (e) => {
    e.preventDefault();
    dragDropArea.classList.remove('dragging');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        fileInput.files = files;
        uploadFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        uploadFile(e.target.files[0]);
    }
});

// Upload file
function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    showLoading(true);

    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            displayResults(data);
        }
    })
    .catch(error => {
        showLoading(false);
        alert('Upload failed: ' + error);
    });
}

// Analyze pasted text
function analyzePastedText() {
    const text = document.getElementById('contractText').value.trim();

    if (text.length === 0) {
        alert('Please paste contract text');
        return;
    }

    showLoading(true);

    fetch('/api/analyze-text', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: text })
    })
    .then(response => response.json())
    .then(data => {
        showLoading(false);
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            displayResults(data);
        }
    })
    .catch(error => {
        showLoading(false);
        alert('Analysis failed: ' + error);
    });
}

// Display results
function displayResults(data) {
    // Update summary
    document.getElementById('summaryText').textContent = 
        data.contract_summary || 'Contract analysis completed.';

    // Update risk score
    const score = data.overall_risk_score || 0;
    const riskLevel = data.risk_level || 'Unknown';
    
    document.getElementById('scoreCircle').textContent = score;
    document.getElementById('riskLevel').textContent = riskLevel;

    // Color code the risk level
    const scoreCard = document.querySelector('.risk-score-card');
    if (score >= 81) {
        scoreCard.style.background = 'linear-gradient(135deg, #dc2626 0%, #991b1b 100%)';
    } else if (score >= 61) {
        scoreCard.style.background = 'linear-gradient(135deg, #f97316 0%, #c2410c 100%)';
    } else if (score >= 31) {
        scoreCard.style.background = 'linear-gradient(135deg, #eab308 0%, #a16207 100%)';
    } else {
        scoreCard.style.background = 'linear-gradient(135deg, #10b981 0%, #047857 100%)';
    }

    // Display liability clauses
    const liabilityList = document.getElementById('liabilityList');
    if (data.liability_clauses && data.liability_clauses.length > 0) {
        liabilityList.innerHTML = data.liability_clauses.map(clause => `
            <div class="clause-item ${clause.severity.toLowerCase()}">
                <h4>${clause.risk_type}</h4>
                <span class="severity-badge ${clause.severity.toLowerCase()}">${clause.severity}</span>
                <p><strong>Clause:</strong></p>
                <p>"${clause.clause_text.substring(0, 200)}${clause.clause_text.length > 200 ? '...' : ''}"</p>
                <p><strong>Reason:</strong> ${clause.reason}</p>
                <p><strong>Recommendation:</strong> ${clause.recommendation}</p>
            </div>
        `).join('');
    } else {
        liabilityList.innerHTML = '<div class="empty-state"><p>No significant liability clauses identified.</p></div>';
    }

    // Display red flags
    const redFlagsList = document.getElementById('redFlagsList');
    if (data.red_flags && data.red_flags.length > 0) {
        redFlagsList.innerHTML = data.red_flags.map(flag => `
            <div class="flag-item">
                <h4>🚩 ${flag.category}</h4>
                <p><strong>Description:</strong> ${flag.description}</p>
                <p><strong>Why problematic:</strong> ${flag.why_problematic}</p>
                <p><strong>Suggested fix:</strong> ${flag.suggested_fix}</p>
            </div>
        `).join('');
    } else {
        redFlagsList.innerHTML = '<div class="empty-state"><p>No red flags detected.</p></div>';
    }

    // Show results section
    document.getElementById('resultsSection').style.display = 'block';

    // Scroll to results
    setTimeout(() => {
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
    }, 100);
}

// Reset analysis
function resetAnalysis() {
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('contractText').value = '';
    document.getElementById('fileInput').value = '';
    document.getElementById('dragDropArea').classList.remove('dragging');

    // Switch back to upload tab
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });

    document.getElementById('upload').classList.add('active');
    document.querySelector('[data-tab="upload"]').classList.add('active');
}

// Show/hide loading
function showLoading(show) {
    document.getElementById('loadingSpinner').style.display = show ? 'block' : 'none';
}
