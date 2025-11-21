"""
Note Service - Database queries for clinical notes
Handles retrieval and filtering of notes from MongoDB and PostgreSQL
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from bson.decimal128 import Decimal128

try:
    from modules.database import get_mongodb_connection, get_postgres_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class NoteService:
    """Service for querying and managing clinical notes"""

    def __init__(self):
        self.mongodb = get_mongodb_connection() if DB_AVAILABLE else None
        self.postgres = get_postgres_connection() if DB_AVAILABLE else None

    def _convert_decimals(self, obj: Any) -> Any:
        """Recursively convert Decimal128 to float"""
        if isinstance(obj, Decimal128):
            return float(obj.to_decimal())
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(i) for i in obj]
        return obj

    def get_all_notes(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """
        Get all processed notes with pagination

        Args:
            limit: Number of notes to return
            offset: Offset for pagination

        Returns:
            Dictionary with notes and metadata
        """
        if not self.mongodb:
            return {'notes': [], 'total': 0, 'limit': limit, 'offset': offset}

        try:
            collection = self.mongodb.db['fhir_bundles']

            # Get total count
            total = collection.count_documents({})

            # Get paginated notes (newest first)
            notes = list(
                collection.find({}, sort=[('created_at', -1)])
                .skip(offset)
                .limit(limit)
            )

            # Convert MongoDB ObjectId to string for JSON serialization
            for note in notes:
                note['_id'] = str(note['_id'])
                if 'created_at' in note:
                    note['created_at'] = note['created_at'].isoformat()
                if 'updated_at' in note:
                    note['updated_at'] = note['updated_at'].isoformat()
            
            # Convert Decimal128 to float
            notes = self._convert_decimals(notes)

            return {
                'notes': notes,
                'total': total,
                'limit': limit,
                'offset': offset,
                'pages': (total + limit - 1) // limit
            }
        except Exception as e:
            print(f"❌ Error fetching notes: {e}")
            return {'notes': [], 'total': 0, 'limit': limit, 'offset': offset, 'error': str(e)}

    def get_flagged_notes(self, min_confidence: float = 0.85, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get notes flagged for review (low confidence)

        Args:
            min_confidence: Minimum confidence threshold (0-1)
            limit: Maximum number of notes to return

        Returns:
            List of flagged notes
        """
        if not self.mongodb:
            return []

        try:
            collection = self.mongodb.db['fhir_bundles']

            # Convert percentage to decimal if needed
            threshold = min_confidence if min_confidence < 1.0 else min_confidence / 100

            flagged = list(
                collection.find(
                    {'confidence_score': {'$lt': threshold}},
                    sort=[('confidence_score', 1), ('created_at', -1)]
                ).limit(limit)
            )

            # Convert ObjectId and dates
            for note in flagged:
                note['_id'] = str(note['_id'])
                if 'created_at' in note:
                    note['created_at'] = note['created_at'].isoformat()

            # Convert Decimal128 to float
            flagged = self._convert_decimals(flagged)

            return flagged
        except Exception as e:
            print(f"❌ Error fetching flagged notes: {e}")
            return []

    def get_note_by_id(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information for a specific note

        Args:
            transaction_id: Transaction ID to retrieve

        Returns:
            Note details with FHIR bundle and metadata
        """
        if not self.mongodb:
            return None

        try:
            bundles_collection = self.mongodb.db['fhir_bundles']
            notes_collection = self.mongodb.db['clinical_notes']
            reviews_collection = self.mongodb.db['clinician_reviews']

            # Get FHIR bundle
            bundle = bundles_collection.find_one({'transaction_id': transaction_id})

            if not bundle:
                return None

            # Get clinical note metadata
            note_meta = notes_collection.find_one({'transaction_id': transaction_id})

            # Get review history
            reviews = list(reviews_collection.find({'transaction_id': transaction_id}))

            # Format response
            result = {
                'transaction_id': transaction_id,
                'confidence_score': bundle.get('confidence_score', 0),
                'validation_status': bundle.get('validation_status', 'unknown'),
                'created_at': bundle.get('created_at').isoformat() if bundle.get('created_at') else None,
                'updated_at': bundle.get('updated_at').isoformat() if bundle.get('updated_at') else None,
                'fhir_bundle': bundle.get('bundle', {}),
                'masked_text': note_meta.get('masked_text', '') if note_meta else '',
                'structured_output': note_meta.get('structured_output', {}) if note_meta else {},
                'review_history': reviews
            }

            return self._convert_decimals(result)
        except Exception as e:
            print(f"❌ Error fetching note {transaction_id}: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get dashboard statistics

        Returns:
            Dictionary with stats
        """
        if not self.mongodb or not self.postgres:
            return self._empty_stats()

        try:
            bundles = self.mongodb.db['fhir_bundles']
            reviews = self.mongodb.db['clinician_reviews']

            # Count total notes
            total_notes = bundles.count_documents({})

            # Count flagged notes (confidence < 0.85)
            flagged_count = bundles.count_documents({'confidence_score': {'$lt': 0.85}})

            # Count reviewed notes
            reviewed_transaction_ids = set(
                doc['transaction_id'] for doc in reviews.find({}, {'transaction_id': 1})
            )
            reviewed_count = len(reviewed_transaction_ids)

            # Get approval rate
            approvals = reviews.count_documents({'action': 'approve'})
            rejections = reviews.count_documents({'action': 'reject'})
            escalations = reviews.count_documents({'action': 'flag_for_escalation'})

            # Average confidence
            pipeline = [
                {
                    '$group': {
                        '_id': None,
                        'avg_confidence': {'$avg': '$confidence_score'},
                        'min_confidence': {'$min': '$confidence_score'},
                        'max_confidence': {'$max': '$confidence_score'}
                    }
                }
            ]
            stats = list(bundles.aggregate(pipeline))
            confidence_stats = self._convert_decimals(stats[0]) if stats else {}

            return {
                'total_notes': total_notes,
                'flagged_count': flagged_count,
                'reviewed_count': reviewed_count,
                'pending_review': flagged_count - reviewed_count,
                'approvals': approvals,
                'rejections': rejections,
                'escalations': escalations,
                'approval_rate': approvals / reviewed_count if reviewed_count > 0 else 0,
                'average_confidence': confidence_stats.get('avg_confidence', 0),
                'min_confidence': confidence_stats.get('min_confidence', 0),
                'max_confidence': confidence_stats.get('max_confidence', 0)
            }
            return self._convert_decimals(stats_result)
        except Exception as e:
            print(f"❌ Error fetching statistics: {e}")
            return self._empty_stats()

    def extract_field_confidences(self, note_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract field-level confidence scores from note

        Args:
            note_data: Note data dictionary

        Returns:
            Dictionary of field confidences
        """
        confidences = {}

        try:
            structured = note_data.get('structured_output', {})

            # Extract confidences from various fields
            if 'encounter_summary' in structured:
                confidences['chief_complaint'] = 90 if structured['encounter_summary'].get('chief_complaint') != 'N/A' else 30

            if 'vital_signs_extracted' in structured:
                vitals = structured['vital_signs_extracted']
                non_na = sum(1 for v in vitals.values() if v and v != 'N/A')
                confidences['vital_signs'] = min(100, (non_na / 5) * 100)

            if 'clinical_entities' in structured:
                entities = structured['clinical_entities']
                confidences['diagnoses'] = 85 if entities.get('diagnoses_problems') else 20
                confidences['medications'] = 85 if entities.get('medication_requests_new_or_changed') else 20
                confidences['allergies'] = 80 if entities.get('allergies') else 20

            return confidences
        except Exception as e:
            print(f"⚠️  Warning: Could not extract field confidences: {e}")
            return {}

    @staticmethod
    def _empty_stats() -> Dict[str, Any]:
        """Return empty statistics dictionary"""
        return {
            'total_notes': 0,
            'flagged_count': 0,
            'reviewed_count': 0,
            'pending_review': 0,
            'approvals': 0,
            'rejections': 0,
            'escalations': 0,
            'approval_rate': 0,
            'average_confidence': 0,
            'min_confidence': 0,
            'max_confidence': 0
        }


# Singleton instance
_note_service = None


def get_note_service() -> NoteService:
    """Get or create note service instance"""
    global _note_service
    if _note_service is None:
        _note_service = NoteService()
    return _note_service
