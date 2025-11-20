"""
Web Routes - HTML page routes for the clinical notes review interface
Renders templates for user-facing pages
"""

from flask import Blueprint, render_template, request, redirect, url_for
from services.note_service import get_note_service
from services.review_service import get_review_service

web_bp = Blueprint('web', __name__)

note_service = get_note_service()
review_service = get_review_service()


@web_bp.route('/')
def index():
    """Home page - redirects to dashboard"""
    return redirect(url_for('web.dashboard'))


@web_bp.route('/dashboard')
def dashboard():
    """Dashboard with statistics and overview"""
    try:
        stats = note_service.get_statistics()
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/review-queue')
def review_queue():
    """Review queue - list of notes needing review"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = 25
        offset = (page - 1) * limit

        # Get flagged notes
        flagged = note_service.get_flagged_notes(min_confidence=0.85, limit=100)

        # Pagination
        total = len(flagged)
        pages = (total + limit - 1) // limit
        paginated = flagged[(page-1)*limit:page*limit]

        return render_template(
            'review_queue.html',
            notes=paginated,
            total=total,
            page=page,
            pages=pages,
            limit=limit
        )
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/notes/<transaction_id>')
def note_detail(transaction_id):
    """Detailed view of a specific note"""
    try:
        note = note_service.get_note_by_id(transaction_id)

        if not note:
            return render_template('error.html', error='Note not found'), 404

        # Extract field confidences
        field_confidences = note_service.extract_field_confidences(note)
        note['field_confidences'] = field_confidences

        # Get review history
        reviews = review_service.get_review_history(transaction_id)

        return render_template(
            'note_detail.html',
            note=note,
            reviews=reviews,
            transaction_id=transaction_id
        )
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/notes')
def notes_list():
    """List all processed notes"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = 25
        offset = (page - 1) * limit

        result = note_service.get_all_notes(limit=limit, offset=offset)

        return render_template(
            'notes_list.html',
            notes=result['notes'],
            total=result['total'],
            page=page,
            pages=result['pages'],
            limit=limit
        )
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/approvals')
def approvals():
    """View all approved notes"""
    try:
        approvals = review_service.get_reviews_by_action('approve', limit=100)
        return render_template('approvals.html', reviews=approvals)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/rejections')
def rejections():
    """View all rejected notes"""
    try:
        rejections = review_service.get_reviews_by_action('reject', limit=100)
        return render_template('rejections.html', reviews=rejections)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/escalations')
def escalations():
    """View flagged notes awaiting escalation"""
    try:
        escalations = review_service.get_reviews_by_action('flag_for_escalation', limit=100)
        return render_template('escalations.html', reviews=escalations)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/search')
def search():
    """Search notes by transaction ID or confidence"""
    try:
        query = request.args.get('q', '').strip()
        min_conf = request.args.get('min_confidence', 0, type=float)
        max_conf = request.args.get('max_confidence', 100, type=float)

        results = []

        if query:
            # Search by transaction ID
            note = note_service.get_note_by_id(query)
            if note:
                results = [note]
        elif min_conf or max_conf:
            # Filter by confidence
            all_notes = note_service.get_all_notes(limit=1000)['notes']
            results = [
                n for n in all_notes
                if min_conf/100 <= n.get('confidence_score', 0) <= max_conf/100
            ]

        return render_template(
            'search_results.html',
            results=results,
            query=query,
            min_confidence=min_conf,
            max_confidence=max_conf
        )
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/clinician/<clinician_id>')
def clinician_profile(clinician_id):
    """View clinician profile and statistics"""
    try:
        stats = review_service.get_clinician_stats(clinician_id)
        reviews = review_service.get_review_history(clinician_id)

        return render_template(
            'clinician_profile.html',
            stats=stats,
            reviews=reviews
        )
    except Exception as e:
        return render_template('error.html', error=str(e)), 500


@web_bp.route('/about')
def about():
    """About page with system information"""
    return render_template('about.html')
