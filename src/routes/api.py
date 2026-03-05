"""
API Routes - RESTful endpoints for clinical notes and reviews
Provides JSON API for frontend and external integrations

HIPAA Note: Every endpoint is protected with @login_required.
Internal exception details are never surfaced to the caller.
"""

import re

from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.note_service import get_note_service
from services.review_service import get_review_service

api_bp = Blueprint('api', __name__, url_prefix='/api')

note_service = get_note_service()
review_service = get_review_service()

# ---------------------------------------------------------------------------
# Input-validation helpers
# ---------------------------------------------------------------------------

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)
_CLINICIAN_ID_RE = re.compile(r'^[\w\-]{1,64}$')

_ALLOWED_ACTIONS = frozenset({'approve', 'reject', 'flag_for_escalation'})


def _valid_transaction_id(tid: str) -> bool:
    """Return True only if *tid* is a well-formed UUID string."""
    return bool(_UUID_RE.match(tid))


# ---------------------------------------------------------------------------
# Notes endpoints
# ---------------------------------------------------------------------------

@api_bp.route('/notes', methods=['GET'])
@login_required
def get_notes():
    """
    Get all processed notes with pagination.

    Query params:
    - limit: notes per page (default 25, max 100)
    - offset: pagination offset (default 0)
    """
    try:
        limit = min(request.args.get('limit', 25, type=int), 100)
        offset = max(request.args.get('offset', 0, type=int), 0)
        result = note_service.get_all_notes(limit=limit, offset=offset)
        return jsonify(result), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve notes'}), 500


@api_bp.route('/notes/flagged', methods=['GET'])
@login_required
def get_flagged_notes():
    """
    Get notes flagged for review (confidence < threshold).

    Query params:
    - confidence: threshold 0-100 (default 85)
    - limit: max results (default 50, max 200)
    """
    try:
        confidence = request.args.get('confidence', 85, type=float)
        limit = min(request.args.get('limit', 50, type=int), 200)
        threshold = confidence / 100

        flagged = note_service.get_flagged_notes(min_confidence=threshold, limit=limit)
        return jsonify({
            'notes': flagged,
            'count': len(flagged),
            'threshold': confidence,
        }), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve flagged notes'}), 500


@api_bp.route('/notes/<transaction_id>', methods=['GET'])
@login_required
def get_note(transaction_id):
    """Get detailed information for a specific note."""
    if not _valid_transaction_id(transaction_id):
        return jsonify({'error': 'Invalid transaction ID format'}), 400

    try:
        note = note_service.get_note_by_id(transaction_id)
        if not note:
            return jsonify({'error': 'Note not found'}), 404

        note['field_confidences'] = note_service.extract_field_confidences(note)
        return jsonify(note), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve note'}), 500


@api_bp.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get dashboard statistics."""
    try:
        stats = note_service.get_statistics()
        return jsonify(stats), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve statistics'}), 500


# ---------------------------------------------------------------------------
# Review endpoints
# ---------------------------------------------------------------------------

@api_bp.route('/notes/<transaction_id>/review', methods=['POST'])
@login_required
def submit_review(transaction_id):
    """
    Submit a clinician review decision.

    JSON body:
    {
        "action": "approve|reject|flag_for_escalation",
        "clinician_id": "user123",
        "notes": "Optional feedback"
    }
    """
    if not _valid_transaction_id(transaction_id):
        return jsonify({'error': 'Invalid transaction ID format'}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'Request body must be valid JSON'}), 400

    action = data.get('action', '').strip()
    if not action:
        return jsonify({'error': 'Missing required field: action'}), 400
    if action not in _ALLOWED_ACTIONS:
        return jsonify({
            'error': f'Invalid action. Allowed values: {sorted(_ALLOWED_ACTIONS)}'
        }), 400

    try:
        clinician_id = data.get('clinician_id', 'system')
        notes = data.get('notes')

        success = review_service.submit_review(
            transaction_id=transaction_id,
            action=action,
            clinician_id=clinician_id,
            notes=notes,
        )

        if success:
            return jsonify({
                'message': 'Review submitted successfully',
                'transaction_id': transaction_id,
                'action': action,
            }), 201
        return jsonify({'error': 'Failed to submit review'}), 400

    except Exception:
        return jsonify({'error': 'Failed to process review'}), 500


@api_bp.route('/notes/<transaction_id>/review-history', methods=['GET'])
@login_required
def get_review_history(transaction_id):
    """Get review history for a specific note."""
    if not _valid_transaction_id(transaction_id):
        return jsonify({'error': 'Invalid transaction ID format'}), 400

    try:
        reviews = review_service.get_review_history(transaction_id)
        return jsonify({
            'transaction_id': transaction_id,
            'reviews': reviews,
            'count': len(reviews),
        }), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve review history'}), 500


@api_bp.route('/reviews/<action>', methods=['GET'])
@login_required
def get_reviews_by_action(action):
    """
    Get all reviews with a specific action.

    Path params:
    - action: 'approve', 'reject', or 'flag_for_escalation'

    Query params:
    - limit: max results (default 50, max 200)
    """
    if action not in _ALLOWED_ACTIONS:
        return jsonify({'error': f'Invalid action: {action}'}), 400

    try:
        limit = min(request.args.get('limit', 50, type=int), 200)
        reviews = review_service.get_reviews_by_action(action, limit=limit)
        return jsonify({'action': action, 'reviews': reviews, 'count': len(reviews)}), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve reviews'}), 500


@api_bp.route('/clinicians/<clinician_id>/stats', methods=['GET'])
@login_required
def get_clinician_stats(clinician_id):
    """Get statistics for a specific clinician."""
    if not _CLINICIAN_ID_RE.match(clinician_id):
        return jsonify({'error': 'Invalid clinician ID format'}), 400

    try:
        stats = review_service.get_clinician_stats(clinician_id)
        return jsonify(stats), 200
    except Exception:
        return jsonify({'error': 'Failed to retrieve clinician stats'}), 500


# ---------------------------------------------------------------------------
# Search & Filter
# ---------------------------------------------------------------------------

@api_bp.route('/search', methods=['GET'])
@login_required
def search_notes():
    """
    Search notes by transaction ID or confidence range.

    Query params:
    - q: transaction_id (must be a valid UUID)
    - min_confidence: 0-100
    - max_confidence: 0-100
    """
    try:
        query = request.args.get('q', '').strip()
        min_conf = max(0.0, min(100.0, request.args.get('min_confidence', 0, type=float)))
        max_conf = max(0.0, min(100.0, request.args.get('max_confidence', 100, type=float)))

        if query:
            # Only allow UUID-format queries to prevent injection
            if not _valid_transaction_id(query):
                return jsonify({'notes': [], 'count': 0}), 200
            note = note_service.get_note_by_id(query)
            if note:
                return jsonify({'notes': [note], 'count': 1}), 200
            return jsonify({'notes': [], 'count': 0}), 200

        all_notes = note_service.get_all_notes(limit=1000)['notes']
        filtered = [
            n for n in all_notes
            if min_conf / 100 <= n.get('confidence_score', 0) <= max_conf / 100
        ]
        return jsonify({'notes': filtered, 'count': len(filtered)}), 200

    except Exception:
        return jsonify({'error': 'Search failed'}), 500
