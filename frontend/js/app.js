// PRA COREP Reporting Assistant - JavaScript Application

class CorepAssistant {
    constructor() {
        this.apiBase = 'http://localhost:8000';
        this.currentReport = null;
        this.isGenerating = false;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkSystemHealth();
        this.startHealthMonitoring();
    }

    setupEventListeners() {
        // Auto-resize textarea
        const textarea = document.getElementById('query-input');
        if (textarea) {
            textarea.addEventListener('input', () => {
                textarea.style.height = 'auto';
                textarea.style.height = textarea.scrollHeight + 'px';
            });
        }

        // Enter key to submit
        textarea?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                e.preventDefault();
                this.generateReport();
            }
        });
    }

    startHealthMonitoring() {
        // Check health every 30 seconds
        setInterval(() => this.checkSystemHealth(), 30000);
    }

    async checkSystemHealth() {
        try {
            const response = await fetch(`${this.apiBase}/health`);
            const data = await response.json();
            
            this.updateSystemStatus(data);
        } catch (error) {
            console.error('Health check failed:', error);
            this.setSystemOffline();
        }
    }

    updateSystemStatus(data) {
        // Update overall system status
        const systemStatus = document.getElementById('system-status');
        const statusDot = systemStatus?.querySelector('.status-dot');
        const statusText = systemStatus?.querySelector('.status-text');
        
        if (data.status === 'healthy') {
            statusDot?.classList.add('online');
            statusDot?.classList.remove('offline');
            if (statusText) statusText.textContent = 'Online';
        } else {
            statusDot?.classList.add('offline');
            statusDot?.classList.remove('online');
            if (statusText) statusText.textContent = 'Offline';
        }

        // Update individual component statuses
        this.updateComponentStatus('api-status', data.system.initialized ? 'online' : 'offline');
        this.updateComponentStatus('docs-status', data.system.documents_loaded > 0 ? 'online' : 'offline');
        this.updateComponentStatus('groq-status', data.system.groq_connected ? 'online' : 'offline');
        this.updateComponentStatus('validation-status', 'ready');
    }

    updateComponentStatus(elementId, status) {
        const element = document.getElementById(elementId);
        const statusDot = element?.querySelector('.status-dot');
        
        if (statusDot) {
            statusDot.classList.add(status);
            statusDot.classList.remove(status === 'online' ? 'offline' : 'online');
        }
        
        // Update text content
        const statusText = document.getElementById(elementId + '-text');
        if (statusText) {
            statusText.textContent = text;
        }
        
        if (card) {
            card.style.borderLeftColor = isHealthy ? 'var(--success-color)' : 'var(--accent-color)';
        }
    }

    async generateReport() {
        if (this.isGenerating) return;
        
        const query = document.getElementById('query-input').value.trim();
        
        if (!query) {
            this.showNotification('Please enter a reporting scenario', 'warning');
            return;
        }

        this.isGenerating = true;
        this.showLoading(true);
        this.updateLoadingSteps('retrieval', true);

        try {
            const response = await fetch(`${this.apiBase}/generate_corep`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_query: query,
                    k_documents: 3,
                    export_format: 'json'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.updateLoadingSteps('analysis', true);
            
            const data = await response.json();
            this.currentReport = data;
            
            this.updateLoadingSteps('validation', true);
            this.updateLoadingSteps('complete', true);
            
            setTimeout(() => {
                this.displayResults(data);
                this.showLoading(false);
                this.isGenerating = false;
            }, 1000);

        } catch (error) {
            console.error('Error generating report:', error);
            this.showNotification('Failed to generate report. Please check your connection and try again.', 'error');
            this.showLoading(false);
            this.isGenerating = false;
        }
    }

    showLoading(show) {
        const loadingSection = document.getElementById('loading-section');
        const resultsSection = document.getElementById('results-section');
        const generateBtn = document.getElementById('generate-btn');
        
        if (show) {
            loadingSection.style.display = 'block';
            resultsSection.style.display = 'none';
            generateBtn.disabled = true;
            this.resetLoadingSteps();
        } else {
            loadingSection.style.display = 'none';
            generateBtn.disabled = false;
        }
    }

    resetLoadingSteps() {
        const steps = ['retrieval', 'analysis', 'validation', 'complete'];
        steps.forEach(step => this.updateLoadingSteps(step, false));
    }

    updateLoadingSteps(step, active) {
        const stepElement = document.getElementById(`step-${step}`);
        if (stepElement) {
            if (active) {
                stepElement.classList.add('active');
            } else {
                stepElement.classList.remove('active');
            }
        }
    }

    displayResults(data) {
        // Show results section
        const resultsSection = document.getElementById('results-section');
        resultsSection.style.display = 'block';
        resultsSection.classList.add('fade-in');
        
        // Display summary metrics
        this.displaySummaryMetrics(data);
        
        // Display template results
        this.displayTemplateResults(data);
        
        // Display validation results
        this.displayValidationResults(data);
        
        // Display sources
        this.displaySources(data);
        
        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth' });
    }

    displaySummaryMetrics(data) {
        const summary = data.structured_output.summary || {};
        const validation = data.validation_report.validation_summary;
        
        // Update CET1 total
        const cet1Element = document.getElementById('cet1-total');
        if (cet1Element) {
            cet1Element.textContent = this.formatCurrency(summary.total_cet1);
        }
        
        // Update AT1 total
        const at1Element = document.getElementById('at1-total');
        if (at1Element) {
            at1Element.textContent = this.formatCurrency(summary.total_at1);
        }
        
        // Update Tier 2 total
        const tier2Element = document.getElementById('tier2-total');
        if (tier2Element) {
            tier2Element.textContent = this.formatCurrency(summary.total_tier2);
        }
        
        // Update validation status
        const validationElement = document.getElementById('validation-status-badge');
        if (validationElement) {
            validationElement.textContent = validation.status === 'PASS' ? '✅ PASS' : '⚠️ ISSUES';
            validationElement.style.color = validation.status === 'PASS' ? 'var(--success-color)' : 'var(--warning-color)';
        }
    }

    displayTemplateResults(data) {
        const template = data.corep_template;
        const tbody = document.getElementById('template-tbody');
        
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        template.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${row.row_number}</strong></td>
                <td>${row.description}</td>
                <td>${row.formatted_amount}</td>
                <td>-</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Update template info
        const templateDate = document.getElementById('template-date');
        if (templateDate && data.structured_output.reporting_date) {
            templateDate.textContent = data.structured_output.reporting_date;
        }
    }

    displayValidationResults(data) {
        const validation = data.validation_report;
        const summary = validation.validation_summary;
        const flags = validation.validation_flags;
        
        // Update validation summary
        const summaryElement = document.getElementById('validation-summary');
        if (summaryElement) {
            summaryElement.innerHTML = `
                <h4>Validation Summary</h4>
                <div class="validation-summary-grid">
                    <div class="summary-item">
                        <strong>Total Flags:</strong> ${summary.total_flags}
                    </div>
                    <div class="summary-item">
                        <strong>Errors:</strong> <span class="error-count">${summary.errors}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Warnings:</strong> <span class="warning-count">${summary.warnings}</span>
                    </div>
                    <div class="summary-item">
                        <strong>Info:</strong> <span class="info-count">${summary.info}</span>
                    </div>
                </div>
            `;
        }
        
        // Update validation details
        const detailsElement = document.getElementById('validation-details');
        if (detailsElement) {
            detailsElement.innerHTML = '';
            
            ['errors', 'warnings', 'info'].forEach(type => {
                const typeFlags = flags[type] || [];
                if (typeFlags.length > 0) {
                    const section = document.createElement('div');
                    section.innerHTML = `<h5>${type.charAt(0).toUpperCase() + type.slice(1)} (${typeFlags.length})</h5>`;
                    
                    typeFlags.forEach(flag => {
                        const flagDiv = document.createElement('div');
                        flagDiv.className = `validation-flag ${type.slice(0, -1)}`;
                        flagDiv.innerHTML = `
                            <strong>${flag.message}</strong>
                            ${flag.field ? `<br><small>Field: ${flag.field}</small>` : ''}
                            ${flag.suggestion ? `<br><small><em>Suggestion: ${flag.suggestion}</em></small>` : ''}
                        `;
                        section.appendChild(flagDiv);
                    });
                    
                    detailsElement.appendChild(section);
                }
            });
            
            // Add recommendations
            if (validation.recommendations && validation.recommendations.length > 0) {
                const recSection = document.createElement('div');
                recSection.innerHTML = '<h5>Recommendations</h5>';
                
                const recList = document.createElement('ul');
                validation.recommendations.forEach(rec => {
                    const li = document.createElement('li');
                    li.textContent = rec;
                    recList.appendChild(li);
                });
                
                recSection.appendChild(recList);
                detailsElement.appendChild(recSection);
            }
        }
    }

    displaySources(data) {
        const sources = data.retrieved_sources;
        const sourcesList = document.getElementById('sources-list');
        
        if (!sourcesList) return;
        
        sourcesList.innerHTML = '';
        
        sources.forEach((source, index) => {
            const sourceDiv = document.createElement('div');
            sourceDiv.className = 'source-item';
            sourceDiv.innerHTML = `
                <div class="source-header">
                    <h5>${source.source}</h5>
                    <span class="source-score">Score: ${source.score?.toFixed(3) || 'N/A'}</span>
                </div>
                <p>${source.text}</p>
            `;
            sourcesList.appendChild(sourceDiv);
        });
    }

    formatCurrency(amount) {
        if (amount === null || amount === undefined) return 'N/A';
        return new Intl.NumberFormat('en-GB', {
            style: 'currency',
            currency: 'GBP'
        }).format(amount);
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Remove after 3 seconds
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    exportReport(format) {
        if (!this.currentReport) {
            this.showNotification('No report to export', 'warning');
            return;
        }

        // Generate export data
        const exportData = JSON.stringify(this.currentReport, null, 2);
        const blob = new Blob([exportData], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `corep_report_${new Date().toISOString().slice(0,10)}.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showNotification(`Report exported as ${format.toUpperCase()}`, 'success');
    }
}

// Global functions for HTML onclick handlers
function setQuery(text) {
    const textarea = document.getElementById('query-input');
    if (textarea) {
        textarea.value = text;
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }
}

function generateReport() {
    window.corepAssistant.generateReport();
}

function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-pane').forEach(pane => {
        pane.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    const selectedPane = document.getElementById(`${tabName}-tab`);
    if (selectedPane) {
        selectedPane.classList.add('active');
    }
    
    // Add active class to clicked button
    event.target.classList.add('active');
}

function exportReport(format) {
    window.corepAssistant.exportReport(format);
}

function showAbout() {
    alert('PRA COREP Reporting Assistant\n\nVersion 1.0.0\n\nLLM-powered regulatory reporting for UK banks.\nBuilt with Groq API, FastAPI, and modern web technologies.');
}

function showHelp() {
    alert('How to use:\n\n1. Enter your bank\'s capital composition in the text area\n2. Click "Generate COREP Report" or use Ctrl+Enter\n3. Review the generated template and validation results\n4. Export the report in your preferred format\n\nFor support, check the system status indicators above.');
}

// Initialize application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.corepAssistant = new CorepAssistant();
});

// Add notification styles
const notificationStyles = `
    .notification {
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        color: white;
        font-weight: 500;
        z-index: 10000;
        animation: slideInRight 0.3s ease-out;
        max-width: 300px;
    }
    
    .notification.info { background: var(--info-color); }
    .notification.success { background: var(--success-color); }
    .notification.warning { background: var(--warning-color); }
    .notification.error { background: var(--accent-color); }
    
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .validation-summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin-top: 1rem;
    }
    
    .summary-item {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: var(--shadow-sm);
    }
    
    .error-count { color: var(--accent-color); }
    .warning-count { color: var(--warning-color); }
    .info-count { color: var(--info-color); }
`;

// Add styles to head
const styleSheet = document.createElement('style');
styleSheet.textContent = notificationStyles;
document.head.appendChild(styleSheet);
