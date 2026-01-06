/**
 * SCP Foundation Book Generator - Web Interface
 */

// State
let articles = [];
let selectedArticles = new Set();
let pdfInfo = null;
let currentPdfPage = 0;
let totalPdfPages = 0;

// Elements
const elements = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    cacheElements();
    bindEvents();
    loadArticles();
    loadPdfInfo();
});

function cacheElements() {
    elements.statDownloaded = document.getElementById('stat-downloaded');
    elements.statParsed = document.getElementById('stat-parsed');
    elements.statLatex = document.getElementById('stat-latex');
    elements.statPdf = document.getElementById('stat-pdf');

    elements.downloadInput = document.getElementById('download-input');
    elements.searchInput = document.getElementById('search-input');
    elements.articlesContainer = document.getElementById('articles-container');
    elements.articleCount = document.getElementById('article-count');
    elements.selectionActions = document.getElementById('selection-actions');
    elements.selectionCount = document.getElementById('selection-count');
    elements.logContainer = document.getElementById('log-container');

    elements.pdfSection = document.getElementById('pdf-section');
    elements.pdfPages = document.getElementById('pdf-pages');
    elements.pdfSize = document.getElementById('pdf-size');
    elements.pdfModified = document.getElementById('pdf-modified');

    elements.pdfModal = document.getElementById('pdf-modal');
    elements.pdfPreviewImage = document.getElementById('pdf-preview-image');
    elements.pageIndicator = document.getElementById('page-indicator');

    elements.articleModal = document.getElementById('article-modal');
    elements.articleModalTitle = document.getElementById('article-modal-title');
    elements.articleRaw = document.getElementById('article-raw');
    elements.articleParsed = document.getElementById('article-parsed');
    elements.articleLatex = document.getElementById('article-latex');

    elements.filterDownloaded = document.getElementById('filter-downloaded');
    elements.filterNotDownloaded = document.getElementById('filter-not-downloaded');
}

function bindEvents() {
    // Download
    document.getElementById('btn-download').addEventListener('click', handleDownload);
    elements.downloadInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleDownload();
    });

    // Search
    document.getElementById('btn-search').addEventListener('click', handleSearch);
    elements.searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Batch operations
    document.getElementById('btn-parse-all').addEventListener('click', () => parseArticles(true));
    document.getElementById('btn-convert-all').addEventListener('click', () => convertArticles(true));
    document.getElementById('btn-compile').addEventListener('click', compileBook);

    // Selection
    document.getElementById('btn-select-all').addEventListener('click', selectAll);
    document.getElementById('btn-select-none').addEventListener('click', selectNone);
    document.getElementById('btn-parse-selected').addEventListener('click', () => parseArticles(false));
    document.getElementById('btn-convert-selected').addEventListener('click', () => convertArticles(false));

    // PDF
    document.getElementById('btn-pdf-download').addEventListener('click', downloadPdf);
    document.getElementById('btn-pdf-preview').addEventListener('click', openPdfPreview);
    document.getElementById('btn-prev-page').addEventListener('click', () => changePdfPage(-1));
    document.getElementById('btn-next-page').addEventListener('click', () => changePdfPage(1));

    // Modals
    document.getElementById('modal-close').addEventListener('click', closePdfModal);
    document.getElementById('article-modal-close').addEventListener('click', closeArticleModal);

    // Filters
    elements.filterDownloaded.addEventListener('change', renderArticles);
    elements.filterNotDownloaded.addEventListener('change', renderArticles);

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', handleTabClick);
    });

    // Close modals on overlay click
    elements.pdfModal.addEventListener('click', (e) => {
        if (e.target === elements.pdfModal) closePdfModal();
    });
    elements.articleModal.addEventListener('click', (e) => {
        if (e.target === elements.articleModal) closeArticleModal();
    });
}

// API calls
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: { 'Content-Type': 'application/json' },
            ...options
        });
        return await response.json();
    } catch (error) {
        log(`API Error: ${error.message}`, 'error');
        throw error;
    }
}

// Load articles
async function loadArticles() {
    try {
        const data = await apiCall('/api/articles');
        articles = data.articles;
        updateStats(data);
        renderArticles();
        log(`Loaded ${articles.length} articles`, 'info');
    } catch (error) {
        elements.articlesContainer.innerHTML = '<p class="loading">Error loading articles</p>';
    }
}

function updateStats(data) {
    elements.statDownloaded.textContent = data.downloaded;
    elements.statParsed.textContent = data.parsed;
    elements.statLatex.textContent = data.latex_generated;
    elements.statPdf.textContent = data.pdf_compiled;
}

function renderArticles() {
    const showDownloaded = elements.filterDownloaded.checked;
    const showNotDownloaded = elements.filterNotDownloaded.checked;

    const filtered = articles.filter(article => {
        if (article.downloaded && showDownloaded) return true;
        if (!article.downloaded && showNotDownloaded) return true;
        return false;
    });

    elements.articleCount.textContent = `(${filtered.length})`;

    if (filtered.length === 0) {
        elements.articlesContainer.innerHTML = '<p class="loading">No articles match filters</p>';
        return;
    }

    elements.articlesContainer.innerHTML = filtered.map(article => `
        <div class="article-card ${selectedArticles.has(article.number) ? 'selected' : ''}"
             data-scp="${article.number}"
             onclick="toggleArticle('${article.number}', event)">
            <div class="scp-number">SCP-${article.number}</div>
            <div class="status-badges">
                ${article.downloaded ? '<span class="badge badge-downloaded">DL</span>' : ''}
                ${article.parsed ? '<span class="badge badge-parsed">JSON</span>' : ''}
                ${article.latex_generated ? '<span class="badge badge-latex">TEX</span>' : ''}
                ${article.pdf_compiled ? '<span class="badge badge-pdf">PDF</span>' : ''}
            </div>
        </div>
    `).join('');

    updateSelectionUI();
}

function toggleArticle(scpNum, event) {
    // Double-click opens detail
    if (event.detail === 2) {
        openArticleDetail(scpNum);
        return;
    }

    if (selectedArticles.has(scpNum)) {
        selectedArticles.delete(scpNum);
    } else {
        selectedArticles.add(scpNum);
    }
    renderArticles();
}

function updateSelectionUI() {
    const count = selectedArticles.size;
    elements.selectionActions.style.display = count > 0 ? 'flex' : 'none';
    elements.selectionCount.textContent = `${count} selected`;
}

function selectAll() {
    articles.forEach(a => selectedArticles.add(a.number));
    renderArticles();
}

function selectNone() {
    selectedArticles.clear();
    renderArticles();
}

// Download
async function handleDownload() {
    const input = elements.downloadInput.value.trim();
    if (!input) return;

    log(`Downloading: ${input}`, 'info');

    let payload;
    if (input.includes('-')) {
        const [start, end] = input.split('-').map(s => parseInt(s.trim()));
        payload = { start, end };
    } else {
        payload = { scp_numbers: [input] };
    }

    try {
        const result = await apiCall('/api/download', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        log(`Downloaded ${result.successful}/${result.total} articles`,
            result.successful === result.total ? 'success' : 'error');

        result.results.forEach(r => {
            if (r.success) {
                log(`  SCP-${r.scp_number}: OK`, 'success');
            } else {
                log(`  SCP-${r.scp_number}: ${r.error}`, 'error');
            }
        });

        loadArticles();
        elements.downloadInput.value = '';
    } catch (error) {
        log(`Download failed: ${error.message}`, 'error');
    }
}

// Search
async function handleSearch() {
    const query = elements.searchInput.value.trim();
    if (!query) {
        loadArticles();
        return;
    }

    log(`Searching: ${query}`, 'info');

    try {
        const result = await apiCall(`/api/search?q=${encodeURIComponent(query)}`);
        articles = result.results;
        renderArticles();
        log(`Found ${result.count} matching articles`, 'info');
    } catch (error) {
        log(`Search failed: ${error.message}`, 'error');
    }
}

// Parse articles
async function parseArticles(all) {
    const scpNumbers = all ? [] : Array.from(selectedArticles);
    log(`Parsing ${all ? 'all' : scpNumbers.length} articles...`, 'info');

    try {
        const result = await apiCall('/api/parse', {
            method: 'POST',
            body: JSON.stringify(all ? { all: true } : { scp_numbers: scpNumbers })
        });

        log(`Parsed ${result.successful}/${result.total} articles`,
            result.successful === result.total ? 'success' : 'error');

        loadArticles();
    } catch (error) {
        log(`Parse failed: ${error.message}`, 'error');
    }
}

// Convert to LaTeX
async function convertArticles(all) {
    const scpNumbers = all ? [] : Array.from(selectedArticles);
    log(`Converting ${all ? 'all' : scpNumbers.length} articles to LaTeX...`, 'info');

    try {
        const result = await apiCall('/api/convert', {
            method: 'POST',
            body: JSON.stringify(all ? { all: true } : { scp_numbers: scpNumbers })
        });

        log(`Converted ${result.successful}/${result.total} articles`,
            result.successful === result.total ? 'success' : 'error');

        loadArticles();
    } catch (error) {
        log(`Convert failed: ${error.message}`, 'error');
    }
}

// Compile book
async function compileBook() {
    log('Compiling PDF book...', 'info');

    try {
        const result = await apiCall('/api/compile', {
            method: 'POST',
            body: JSON.stringify({})
        });

        if (result.success) {
            log('PDF compiled successfully!', 'success');
            loadPdfInfo();
            loadArticles();
        } else {
            log(`Compile failed: ${result.error}`, 'error');
        }
    } catch (error) {
        log(`Compile failed: ${error.message}`, 'error');
    }
}

// PDF info
async function loadPdfInfo() {
    try {
        const info = await apiCall('/api/pdf/info');
        pdfInfo = info;

        if (info.exists) {
            elements.pdfSection.style.display = 'block';
            elements.pdfPages.textContent = `${info.pages} pages`;
            elements.pdfSize.textContent = formatSize(info.size);
            elements.pdfModified.textContent = new Date(info.modified).toLocaleString();
            totalPdfPages = info.pages;
        } else {
            elements.pdfSection.style.display = 'none';
        }
    } catch (error) {
        elements.pdfSection.style.display = 'none';
    }
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function downloadPdf() {
    window.location.href = '/api/pdf/download';
}

// PDF Preview
async function openPdfPreview() {
    if (!pdfInfo || !pdfInfo.exists) return;

    currentPdfPage = 0;
    elements.pdfModal.classList.add('active');
    loadPdfPage(currentPdfPage);
}

async function loadPdfPage(pageNum) {
    elements.pdfPreviewImage.src = '';
    elements.pdfPreviewImage.alt = 'Loading...';
    elements.pageIndicator.textContent = `Page ${pageNum + 1} of ${totalPdfPages}`;

    try {
        // Generate preview if needed
        await apiCall(`/api/pdf/preview?page=${pageNum}`);
        elements.pdfPreviewImage.src = `/api/pdf/page/${pageNum}?t=${Date.now()}`;
    } catch (error) {
        log(`Failed to load PDF page: ${error.message}`, 'error');
    }
}

function changePdfPage(delta) {
    const newPage = currentPdfPage + delta;
    if (newPage >= 0 && newPage < totalPdfPages) {
        currentPdfPage = newPage;
        loadPdfPage(currentPdfPage);
    }
}

function closePdfModal() {
    elements.pdfModal.classList.remove('active');
}

// Article detail modal
async function openArticleDetail(scpNum) {
    elements.articleModalTitle.textContent = `SCP-${scpNum}`;
    elements.articleRaw.textContent = 'Loading...';
    elements.articleParsed.textContent = 'Loading...';
    elements.articleLatex.textContent = 'Loading...';
    elements.articleModal.classList.add('active');

    try {
        const detail = await apiCall(`/api/article/${scpNum}`);

        elements.articleRaw.textContent = detail.raw_preview || 'Not downloaded';

        if (detail.parsed_content) {
            elements.articleParsed.textContent = JSON.stringify(detail.parsed_content, null, 2);
        } else {
            elements.articleParsed.textContent = 'Not parsed';
        }

        // Load LaTeX
        if (detail.latex_generated) {
            const latex = await apiCall(`/api/latex/${scpNum}`);
            elements.articleLatex.textContent = latex.content || 'Error loading LaTeX';
        } else {
            elements.articleLatex.textContent = 'Not converted';
        }
    } catch (error) {
        elements.articleRaw.textContent = `Error: ${error.message}`;
    }
}

function closeArticleModal() {
    elements.articleModal.classList.remove('active');
}

function handleTabClick(event) {
    const tab = event.target;
    const tabId = tab.dataset.tab;

    // Update active tab
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');

    // Show corresponding content
    document.querySelectorAll('.tab-content').forEach(c => c.style.display = 'none');
    document.getElementById(`tab-${tabId}`).style.display = 'block';
}

// Logging
function log(message, type = 'info') {
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `<span class="log-time">[${time}]</span> ${message}`;
    elements.logContainer.insertBefore(entry, elements.logContainer.firstChild);

    // Keep only last 50 entries
    while (elements.logContainer.children.length > 50) {
        elements.logContainer.removeChild(elements.logContainer.lastChild);
    }
}

// Make toggleArticle available globally
window.toggleArticle = toggleArticle;
