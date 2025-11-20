/**
 * Clinical Notes Review UI - Frontend JavaScript
 * Handles API calls, form submissions, and interactivity
 */

// API Base URL (adjust if needed)
const API_BASE = '/api';

/**
 * Fetch helper with error handling
 */
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API call failed: ${endpoint}`, error);
        throw error;
    }
}

/**
 * Format date to readable format
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format confidence score with color coding
 */
function formatConfidence(score) {
    const percentage = (score * 100).toFixed(1);
    let badgeClass = 'bg-success';

    if (score < 0.70) {
        badgeClass = 'bg-danger';
    } else if (score < 0.85) {
        badgeClass = 'bg-warning text-dark';
    }

    return `<span class="badge ${badgeClass}">${percentage}%</span>`;
}

/**
 * Submit a review decision
 */
async function submitReview(transactionId, action, notes = '') {
    try {
        const response = await apiCall(`/notes/${transactionId}/review`, {
            method: 'POST',
            body: JSON.stringify({
                action: action,
                clinician_id: `clinician_${generateId()}`,
                notes: notes
            })
        });

        return response;
    } catch (error) {
        console.error('Review submission failed:', error);
        throw error;
    }
}

/**
 * Generate unique ID
 */
function generateId() {
    return Math.random().toString(36).substr(2, 9);
}

/**
 * Show notification toast
 */
function showNotification(message, type = 'success') {
    const alertClass = `alert-${type}`;
    const html = `
        <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
            <i class="bi bi-check-circle"></i> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const alertContainer = document.querySelector('main .container-fluid');
    if (alertContainer) {
        const alertDiv = document.createElement('div');
        alertDiv.innerHTML = html;
        alertContainer.insertBefore(alertDiv.firstElementChild, alertContainer.firstChild);
    }
}

/**
 * Confirm dialog
 */
function confirmAction(message) {
    return confirm(message);
}

/**
 * Load dashboard statistics
 */
async function loadDashboardStats() {
    try {
        const stats = await apiCall('/stats');
        console.log('Dashboard stats loaded:', stats);
        return stats;
    } catch (error) {
        console.error('Failed to load stats:', error);
        return null;
    }
}

/**
 * Load flagged notes
 */
async function loadFlaggedNotes(confidenceThreshold = 85, limit = 50) {
    try {
        const notes = await apiCall(`/notes/flagged?confidence=${confidenceThreshold}&limit=${limit}`);
        console.log('Flagged notes loaded:', notes);
        return notes;
    } catch (error) {
        console.error('Failed to load flagged notes:', error);
        return { notes: [] };
    }
}

/**
 * Load specific note details
 */
async function loadNoteDetails(transactionId) {
    try {
        const note = await apiCall(`/notes/${transactionId}`);
        console.log('Note details loaded:', note);
        return note;
    } catch (error) {
        console.error('Failed to load note details:', error);
        return null;
    }
}

/**
 * Search notes
 */
async function searchNotes(query) {
    try {
        const results = await apiCall(`/search?q=${encodeURIComponent(query)}`);
        console.log('Search results:', results);
        return results;
    } catch (error) {
        console.error('Search failed:', error);
        return { notes: [] };
    }
}

/**
 * Load review history for a note
 */
async function loadReviewHistory(transactionId) {
    try {
        const history = await apiCall(`/notes/${transactionId}/review-history`);
        console.log('Review history loaded:', history);
        return history;
    } catch (error) {
        console.error('Failed to load review history:', error);
        return { reviews: [] };
    }
}

/**
 * Get clinician statistics
 */
async function getClinicianStats(clinicianId) {
    try {
        const stats = await apiCall(`/clinicians/${clinicianId}/stats`);
        console.log('Clinician stats loaded:', stats);
        return stats;
    } catch (error) {
        console.error('Failed to load clinician stats:', error);
        return null;
    }
}

/**
 * Export data to CSV
 */
function exportToCsv(filename, data) {
    if (!Array.isArray(data) || data.length === 0) {
        alert('No data to export');
        return;
    }

    // Get headers from first object
    const headers = Object.keys(data[0]);
    const csv = [
        headers.join(','),
        ...data.map(row =>
            headers.map(header => {
                const value = row[header];
                // Escape commas and quotes
                if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
                    return `"${value.replace(/"/g, '""')}"`;
                }
                return value;
            }).join(',')
        )
    ].join('\n');

    // Create blob and download
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);

    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Format FHIR bundle for display
 */
function formatFhirBundle(bundle) {
    return JSON.stringify(bundle, null, 2);
}

/**
 * Syntax highlight JSON
 */
function highlightJson(jsonString) {
    return jsonString
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, (match) => {
            var cls = 'number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'key';
                } else {
                    cls = 'string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'boolean';
            } else if (/null/.test(match)) {
                cls = 'null';
            }
            return `<span class="${cls}">${match}</span>`;
        });
}

/**
 * Initialize tooltips (Bootstrap)
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize popovers (Bootstrap)
 */
function initializePopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

/**
 * Document ready handler
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Clinical Notes Review UI initialized');

    // Initialize Bootstrap components
    initializeTooltips();
    initializePopovers();

    // Setup global error handler for alerts
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
    });
});

// Export for use in other scripts
window.clinicalNotesUI = {
    apiCall,
    formatDate,
    formatConfidence,
    submitReview,
    showNotification,
    confirmAction,
    loadDashboardStats,
    loadFlaggedNotes,
    loadNoteDetails,
    searchNotes,
    loadReviewHistory,
    getClinicianStats,
    exportToCsv,
    formatFhirBundle,
    highlightJson
};
