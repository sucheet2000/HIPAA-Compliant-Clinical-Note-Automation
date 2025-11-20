"""
API Routes - RESTful endpoints for clinical notes and reviews
Provides JSON API for frontend and external integrations
"""

from flask import Blueprint, request, jsonify
from services.note_service import get_note_service
from services.review_service import get_review_service

api_bp = Blueprint('api', __name__, url_prefix='/api')

note_service = get_note_service()
review_service = get_review_service()


# =====================
# Notes Endpoints
# =====================

@api_bp.route('/notes', methods=['GET'])
def get_notes():
    """
    Get all processed notes with pagination

    Query params:
    - limit: Number of notes per page (default: 25)
    - offset: Pagination offset (default: 0)
    """
    try:
        limit = request.args.get('limit', 25, type=int)
        offset = request.args.get('offset', 0, type=int)

        # Validate parameters
        limit = min(limit, 100)  # Max 100 per page
        offset = max(offset, 0)

        result = note_service.get_all_notes(limit=limit, offset=offset)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/notes/flagged', methods=['GET'])
def get_flagged_notes():
    """
    Get notes flagged for review (confidence < threshold)

    Query params:
    - confidence: Minimum confidence threshold (0-100, default: 85)
    - limit: Maximum results (default: 50)
    """
    try:
        confidence = request.args.get('confidence', 85, type=float)
        limit = request.args.get('limit', 50, type=int)

        # Convert percentage to decimal
        threshold = confidence / 100

        flagged = note_service.get_flagged_notes(min_confidence=threshold, limit=limit)
        return jsonify({
            'notes': flagged,
            'count': len(flagged),
            'threshold': confidence
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/notes/<transaction_id>', methods=['GET'])
def get_note(transaction_id):
    """
    Get detailed information for a specific note

    Path params:
    - transaction_id: Transaction ID to retrieve
    """
    try:
        note = note_service.get_note_by_id(transaction_id)

        if not note:
            return jsonify({'error': 'Note not found'}), 404

        # Extract field confidences
        field_confidences = note_service.extract_field_confidences(note)
        note['field_confidences'] = field_confidences

        return jsonify(note), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """
    Get dashboard statistics
    """
    try:
        stats = note_service.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================
# Review Endpoints
# =====================

@api_bp.route('/notes/<transaction_id>/review', methods=['POST'])
def submit_review(transaction_id):
    """
    Submit a clinician review decision

    JSON body:
    {
        "action": "approve|reject|flag_for_escalation",
        "clinician_id": "user123",
        "notes": "Optional feedback"
    }
    """
    try:
        data = request.get_json()

        if not data or 'action' not in data:
            return jsonify({'error': 'Missing required field: action'}), 400

        action = data.get('action')
        clinician_id = data.get('clinician_id', 'system')
        notes = data.get('notes')

        success = review_service.submit_review(
            transaction_id=transaction_id,
            action=action,
            clinician_id=clinician_id,
            notes=notes
        )

        if success:
            return jsonify({
                'message': 'Review submitted successfully',
                'transaction_id': transaction_id,
                'action': action
            }), 201
        else:
            return jsonify({'error': 'Failed to submit review'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/notes/<transaction_id>/review-history', methods=['GET'])
def get_review_history(transaction_id):
    """
    Get review history for a specific note
    """
    try:
        reviews = review_service.get_review_history(transaction_id)
        return jsonify({
            'transaction_id': transaction_id,
            'reviews': reviews,
            'count': len(reviews)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/reviews/<action>', methods=['GET'])
def get_reviews_by_action(action):
    """
    Get all reviews with a specific action

    Path params:
    - action: 'approve', 'reject', or 'flag_for_escalation'

    Query params:
    - limit: Maximum results (default: 50)
    """
    try:
        limit = request.args.get('limit', 50, type=int)

        if action not in ['approve', 'reject', 'flag_for_escalation']:
            return jsonify({'error': f'Invalid action: {action}'}), 400

        reviews = review_service.get_reviews_by_action(action, limit=limit)
        return jsonify({
            'action': action,
            'reviews': reviews,
            'count': len(reviews)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/clinicians/<clinician_id>/stats', methods=['GET'])
def get_clinician_stats(clinician_id):
    """
    Get statistics for a specific clinician
    """
    try:
        stats = review_service.get_clinician_stats(clinician_id)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================
# Search & Filter
# =====================

@api_bp.route('/search', methods=['GET'])
def search_notes():
    """
    Search notes by transaction ID or confidence range

    Query params:
    - q: Search query (transaction_id)
    - min_confidence: Minimum confidence (0-100)
    - max_confidence: Maximum confidence (0-100)
    """
    try:
        query = request.args.get('q', '').strip()
        min_conf = request.args.get('min_confidence', 0, type=float)
        max_conf = request.args.get('max_confidence', 100, type=float)

        if query:
            # Search by transaction ID
            note = note_service.get_note_by_id(query)
            if note:
                return jsonify({'notes': [note], 'count': 1}), 200
            else:
                return jsonify({'notes': [], 'count': 0}), 200

        # Filter by confidence range
        all_notes = note_service.get_all_notes(limit=1000)['notes']
        filtered = [
            n for n in all_notes
            if min_conf/100 <= n.get('confidence_score', 0) <= max_conf/100
        ]
        return jsonify({'notes': filtered, 'count': len(filtered)}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
