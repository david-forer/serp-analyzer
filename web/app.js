// Wait for pywebview API to be ready
let apiReady = false;

window.addEventListener('pywebviewready', function() {
    apiReady = true;
    console.log('PyWebView API ready');
});

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active from all tabs and panes
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        // Add active to clicked tab and corresponding pane
        tab.classList.add('active');
        const paneId = tab.dataset.tab;
        document.getElementById(paneId).classList.add('active');
    });
});

// Enter key to submit
document.getElementById('query').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        runAnalysis();
    }
});

async function runAnalysis() {
    const query = document.getElementById('query').value.trim();
    if (!query) {
        showError('Please enter a search query');
        return;
    }

    const numResults = parseInt(document.getElementById('numResults').value);
    const detectIntent = document.getElementById('detectIntent').checked;
    const classify = document.getElementById('classify').checked;
    const strategy = document.getElementById('strategy').checked;

    // Show loading, hide results and error
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('error').classList.add('hidden');
    document.getElementById('analyzeBtn').disabled = true;

    try {
        // Call Python API
        const result = await window.pywebview.api.analyze(
            query, numResults, detectIntent, classify, strategy
        );

        if (result.error) {
            showError(result.error);
        } else {
            displayResults(result);
        }
    } catch (err) {
        showError('Analysis failed: ' + err.message);
    } finally {
        document.getElementById('loading').classList.add('hidden');
        document.getElementById('analyzeBtn').disabled = false;
    }
}

function showError(message) {
    const errorEl = document.getElementById('error');
    errorEl.textContent = message;
    errorEl.classList.remove('hidden');
}

function displayResults(data) {
    // Show results section
    document.getElementById('results').classList.remove('hidden');

    // Overview stats
    document.getElementById('stat-query').textContent = data.query || '-';
    document.getElementById('stat-results').textContent = data.total_results || '-';

    // Dominant type
    const dominantType = data.classification_summary
        ? Object.entries(data.classification_summary).sort((a, b) => b[1] - a[1])[0]?.[0] || '-'
        : '-';
    document.getElementById('stat-dominant').textContent = dominantType;

    // Content format
    const contentType = data.content_strategy?.recommendation?.content_type || '-';
    document.getElementById('stat-format').textContent = contentType;

    // Distribution chart
    displayDistribution(data.classification_summary);

    // Intent
    displayIntent(data.intent);

    // Strategy
    displayStrategy(data.content_strategy);

    // SERP results
    displaySerpResults(data.results);
}

function displayDistribution(summary) {
    const container = document.getElementById('distribution');
    if (!summary || Object.keys(summary).length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted)">No classification data</p>';
        return;
    }

    const total = Object.values(summary).reduce((a, b) => a + b, 0);
    const sorted = Object.entries(summary).sort((a, b) => b[1] - a[1]);

    let html = '<h4 style="margin-bottom: 16px; color: var(--text-muted);">Result Type Distribution</h4>';

    sorted.forEach(([type, count]) => {
        const pct = (count / total * 100).toFixed(1);
        html += `
            <div class="dist-bar">
                <span class="dist-label">${type}</span>
                <div class="dist-bar-container">
                    <div class="dist-bar-fill" style="width: ${pct}%"></div>
                </div>
                <span class="dist-count">${count} (${pct}%)</span>
            </div>
        `;
    });

    container.innerHTML = html;
}

function displayIntent(intent) {
    if (!intent) {
        document.getElementById('intent-description').textContent = 'Intent detection was skipped';
        document.getElementById('intent-type').textContent = '-';
        document.getElementById('intent-confidence').textContent = '';
        document.getElementById('intent-signals').innerHTML = '';
        document.getElementById('intent-reasoning').textContent = '-';
        return;
    }

    document.getElementById('intent-description').textContent = intent.user_intent || '-';
    document.getElementById('intent-type').textContent = intent.intent_type || '-';
    document.getElementById('intent-confidence').textContent =
        intent.confidence ? `${(intent.confidence * 100).toFixed(0)}% confidence` : '';

    // Signals
    const signalsContainer = document.getElementById('intent-signals');
    if (intent.key_signals && intent.key_signals.length > 0) {
        signalsContainer.innerHTML = intent.key_signals
            .map(s => `<span class="signal">${s}</span>`)
            .join('');
    } else {
        signalsContainer.innerHTML = '';
    }

    document.getElementById('intent-reasoning').textContent = intent.reasoning || '-';
}

function displayStrategy(strategy) {
    if (!strategy || !strategy.recommendation) {
        document.getElementById('strategy-type').textContent = 'Strategy analysis was skipped';
        document.getElementById('strategy-format').textContent = '';
        document.getElementById('strategy-angle').textContent = '-';
        document.getElementById('strategy-elements').innerHTML = '';
        document.getElementById('strategy-reasoning').innerHTML = '';
        return;
    }

    const rec = strategy.recommendation;

    document.getElementById('strategy-type').textContent = rec.content_type || '-';
    document.getElementById('strategy-format').textContent = rec.format || '';
    document.getElementById('strategy-angle').textContent = rec.angle || '-';

    // Required elements
    const elementsContainer = document.getElementById('strategy-elements');
    if (rec.required_elements && rec.required_elements.length > 0) {
        elementsContainer.innerHTML = rec.required_elements
            .map(e => `<li>${e}</li>`)
            .join('');
    } else {
        elementsContainer.innerHTML = '<li>No specific elements identified</li>';
    }

    // Reasoning
    const reasoningContainer = document.getElementById('strategy-reasoning');
    if (rec.reasoning && rec.reasoning.length > 0) {
        reasoningContainer.innerHTML = rec.reasoning
            .map(r => `<li>${r}</li>`)
            .join('');
    } else {
        reasoningContainer.innerHTML = '<li>No reasoning provided</li>';
    }
}

function displaySerpResults(results) {
    const container = document.getElementById('serp-results');

    if (!results || results.length === 0) {
        container.innerHTML = '<p style="color: var(--text-muted)">No results to display</p>';
        return;
    }

    container.innerHTML = results.map(r => `
        <div class="serp-item">
            <span class="serp-position">${r.position}</span>
            <div class="serp-title">${escapeHtml(r.title)}</div>
            <div class="serp-url">${escapeHtml(r.url)}</div>
            <div class="serp-snippet">${escapeHtml(r.snippet)}</div>
            ${r.classification ? `<span class="serp-classification">${r.classification.category}</span>` : ''}
        </div>
    `).join('');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Export functions
async function exportJson() {
    await doExport('json');
}

async function exportCsv() {
    await doExport('csv');
}

async function exportAll() {
    await doExport('all');
}

async function doExport(type) {
    const statusEl = document.getElementById('export-status');
    statusEl.textContent = 'Exporting...';
    statusEl.className = 'export-status';

    try {
        let result;
        if (type === 'json') {
            result = await window.pywebview.api.export_json();
        } else if (type === 'csv') {
            result = await window.pywebview.api.export_csv();
        } else {
            result = await window.pywebview.api.export_all();
        }

        if (result.error) {
            statusEl.textContent = 'Error: ' + result.error;
            statusEl.className = 'export-status error';
        } else {
            const path = result.path || (result.paths ? Object.values(result.paths).join(', ') : 'Unknown');
            statusEl.textContent = 'Exported to: ' + path;
            statusEl.className = 'export-status success';
        }
    } catch (err) {
        statusEl.textContent = 'Export failed: ' + err.message;
        statusEl.className = 'export-status error';
    }
}
