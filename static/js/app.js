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

function getRiskUiState(score, riskLevel) {
    const levelText = (riskLevel || '').toLowerCase();
    if (levelText.includes('critical') || score >= 81) {
        return {
            key: 'critical',
            badge: 'Critical',
            explainer: 'High likelihood of expensive or hard-to-negotiate lease terms. Immediate revisions recommended.',
            gaugeColor: '#ef4444',
            barGradient: 'linear-gradient(90deg, #dc2626 0%, #ef4444 100%)',
            cardGradient: 'linear-gradient(135deg, #7f1d1d 0%, #991b1b 100%)'
        };
    }
    if (score >= 61) {
        return {
            key: 'high',
            badge: 'High',
            explainer: 'Several lease terms may create meaningful financial or legal downside.',
            gaugeColor: '#f97316',
            barGradient: 'linear-gradient(90deg, #ea580c 0%, #f97316 100%)',
            cardGradient: 'linear-gradient(135deg, #9a3412 0%, #c2410c 100%)'
        };
    }
    if (score >= 31) {
        return {
            key: 'moderate',
            badge: 'Moderate',
            explainer: 'Some clauses should be negotiated, but risk may be manageable with targeted edits.',
            gaugeColor: '#f59e0b',
            barGradient: 'linear-gradient(90deg, #d97706 0%, #f59e0b 100%)',
            cardGradient: 'linear-gradient(135deg, #92400e 0%, #a16207 100%)'
        };
    }
    return {
        key: 'low',
        badge: 'Low',
        explainer: 'No major risk patterns detected in the analyzed lease clauses.',
        gaugeColor: '#10b981',
        barGradient: 'linear-gradient(90deg, #059669 0%, #10b981 100%)',
        cardGradient: 'linear-gradient(135deg, #065f46 0%, #047857 100%)'
    };
}

// Display results
function displayResults(data) {
    // Update summary
    document.getElementById('summaryText').textContent = 
        data.contract_summary || 'Contract analysis completed.';

    // Update risk score
    const rawScore = Number(data.overall_risk_score || 0);
    const score = Number.isFinite(rawScore) ? rawScore : 0;
    const riskLevel = data.risk_level || 'Unknown';

    const scoreForDisplay = Number.isInteger(score) ? score.toString() : score.toFixed(1);
    document.getElementById('scoreCircle').textContent = scoreForDisplay;
    document.getElementById('riskLevel').textContent = riskLevel;
    document.getElementById('riskExplainer').textContent = getRiskUiState(score, riskLevel).explainer;
    document.getElementById('redFlagCount').textContent = (data.red_flags || []).length;
    document.getElementById('liabilityCount').textContent = (data.liability_clauses || []).length;

    const uiState = getRiskUiState(score, riskLevel);
    const scoreCard = document.getElementById('riskScoreCard');
    scoreCard.classList.remove('risk-low', 'risk-moderate', 'risk-high', 'risk-critical');
    scoreCard.classList.add(`risk-${uiState.key}`);
    scoreCard.style.background = uiState.cardGradient;

    const riskBadge = document.getElementById('riskBadge');
    riskBadge.textContent = uiState.badge;
    riskBadge.classList.remove('low', 'moderate', 'high', 'critical');
    riskBadge.classList.add(uiState.key);

    const scoreBarFill = document.getElementById('scoreBarFill');
    const gaugeScore = Math.max(0, Math.min(score, 100));
    scoreBarFill.style.width = `${gaugeScore}%`;
    scoreBarFill.style.background = uiState.barGradient;

    const scoreGaugeFill = document.getElementById('scoreGaugeFill');
    const radius = 52;
    const circumference = 2 * Math.PI * radius;
    scoreGaugeFill.style.strokeDasharray = `${circumference}`;
    scoreGaugeFill.style.strokeDashoffset = `${circumference * (1 - gaugeScore / 100)}`;
    scoreGaugeFill.style.stroke = uiState.gaugeColor;

    // Display liability clauses
    const liabilityList = document.getElementById('liabilityList');
    if (data.liability_clauses && data.liability_clauses.length > 0) {
        liabilityList.innerHTML = data.liability_clauses.map(clause => `
            <div class="clause-item ${clause.severity.toLowerCase()}">
                <h4>${clause.risk_type}</h4>
                <span class="severity-badge ${clause.severity.toLowerCase()}">${clause.severity}</span>
                <p><strong>Original clause:</strong></p>
                <p>"${clause.clause_text.substring(0, 200)}${clause.clause_text.length > 200 ? '...' : ''}"</p>
                <p><strong>What this means:</strong> ${clause.reason || clause.plain_english || 'This clause creates a lease obligation.'}</p>
                <p><strong>Resolution:</strong> ${clause.resolution || clause.recommendation || 'Ask for this clause to be narrowed and clarified in writing.'}</p>
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
                <p><strong>Original clause:</strong> ${flag.description}</p>
                <p><strong>What this means:</strong> ${flag.why_problematic || flag.plain_english || ''}</p>
                <p><strong>Resolution:</strong> ${flag.resolution || flag.suggested_fix || ''}</p>
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
