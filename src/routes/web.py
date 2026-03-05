"""
Web Routes - HTML page routes for the clinical notes review interface
Renders templates for user-facing pages

Internal exception details are logged server-side but never forwarded
to templates, preventing accidental information disclosure.
"""

import logging

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from services.note_service import get_note_service
from services.review_service import get_review_service

logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__)

note_service = get_note_service()
review_service = get_review_service()

_GENERIC_ERROR = 'An unexpected error occurred. Please try again.'


@web_bp.route('/')
def index():
    """Home page — redirects to dashboard."""
    return redirect(url_for('web.dashboard'))


@web_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard with statistics and overview."""
    try:
        stats = note_service.get_statistics()
        return render_template('dashboard.html', stats=stats)
    except Exception as exc:
        logger.error('Dashboard error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/review-queue')
@login_required
def review_queue():
    """Review queue — list of notes needing review."""
    try:
        page = max(request.args.get('page', 1, type=int), 1)
        limit = 25
        flagged = note_service.get_flagged_notes(min_confidence=0.85, limit=100)

        total = len(flagged)
        pages = max((total + limit - 1) // limit, 1)
        paginated = flagged[(page - 1) * limit: page * limit]

        return render_template(
            'review_queue.html',
            notes=paginated,
            total=total,
            page=page,
            pages=pages,
            limit=limit,
        )
    except Exception as exc:
        logger.error('Review queue error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/notes/<transaction_id>')
@login_required
def note_detail(transaction_id):
    """Detailed view of a specific note."""
    # Basic UUID format check before hitting the database
    import re
    if not re.match(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        transaction_id,
        re.IGNORECASE,
    ):
        return render_template('error.html', error='Invalid note ID'), 400

    try:
        note = note_service.get_note_by_id(transaction_id)
        if not note:
            return render_template('error.html', error='Note not found'), 404

        note['field_confidences'] = note_service.extract_field_confidences(note)
        reviews = review_service.get_review_history(transaction_id)

        return render_template(
            'note_detail.html',
            note=note,
            reviews=reviews,
            transaction_id=transaction_id,
        )
    except Exception as exc:
        logger.error('Note detail error for %s: %s', transaction_id, exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/notes')
@login_required
def notes_list():
    """List all processed notes."""
    try:
        page = max(request.args.get('page', 1, type=int), 1)
        limit = 25
        offset = (page - 1) * limit
        result = note_service.get_all_notes(limit=limit, offset=offset)

        return render_template(
            'notes_list.html',
            notes=result['notes'],
            total=result['total'],
            page=page,
            pages=result['pages'],
            limit=limit,
        )
    except Exception as exc:
        logger.error('Notes list error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/approvals')
@login_required
def approvals():
    """View all approved notes."""
    try:
        reviews = review_service.get_reviews_by_action('approve', limit=100)
        return render_template('approvals.html', reviews=reviews)
    except Exception as exc:
        logger.error('Approvals error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/rejections')
@login_required
def rejections():
    """View all rejected notes."""
    try:
        reviews = review_service.get_reviews_by_action('reject', limit=100)
        return render_template('rejections.html', reviews=reviews)
    except Exception as exc:
        logger.error('Rejections error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/escalations')
@login_required
def escalations():
    """View notes flagged for escalation."""
    try:
        reviews = review_service.get_reviews_by_action('flag_for_escalation', limit=100)
        return render_template('escalations.html', reviews=reviews)
    except Exception as exc:
        logger.error('Escalations error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/search')
@login_required
def search():
    """Search notes by transaction ID or confidence range."""
    try:
        query = request.args.get('q', '').strip()
        min_conf = max(0.0, min(100.0, request.args.get('min_confidence', 0, type=float)))
        max_conf = max(0.0, min(100.0, request.args.get('max_confidence', 100, type=float)))

        results = []

        if query:
            note = note_service.get_note_by_id(query)
            if note:
                results = [note]
        elif min_conf or max_conf < 100:
            all_notes = note_service.get_all_notes(limit=1000)['notes']
            results = [
                n for n in all_notes
                if min_conf / 100 <= n.get('confidence_score', 0) <= max_conf / 100
            ]

        return render_template(
            'search_results.html',
            results=results,
            query=query,
            min_confidence=min_conf,
            max_confidence=max_conf,
        )
    except Exception as exc:
        logger.error('Search error: %s', exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/clinician/<clinician_id>')
@login_required
def clinician_profile(clinician_id):
    """View clinician profile and statistics."""
    import re as _re
    if not _re.match(r'^[\w\-]{1,64}$', clinician_id):
        return render_template('error.html', error='Invalid clinician ID'), 400

    try:
        stats = review_service.get_clinician_stats(clinician_id)
        reviews = review_service.get_review_history(clinician_id)
        return render_template('clinician_profile.html', stats=stats, reviews=reviews)
    except Exception as exc:
        logger.error('Clinician profile error for %s: %s', clinician_id, exc, exc_info=True)
        return render_template('error.html', error=_GENERIC_ERROR), 500


@web_bp.route('/about')
def about():
    """About page with system information."""
    return render_template('about.html')
