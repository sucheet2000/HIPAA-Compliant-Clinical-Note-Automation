"""
Review Service - Manages clinician reviews and decisions
Handles approval, rejection, and escalation of clinical notes
"""

from typing import Dict, Any, Optional
from datetime import datetime

try:
    from modules.database import get_mongodb_connection, get_postgres_connection
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False


class ReviewService:
    """Service for managing clinician reviews"""

    def __init__(self):
        self.mongodb = get_mongodb_connection() if DB_AVAILABLE else None
        self.postgres = get_postgres_connection() if DB_AVAILABLE else None

    def submit_review(
        self,
        transaction_id: str,
        action: str,
        clinician_id: str = "system",
        notes: Optional[str] = None
    ) -> bool:
        """
        Submit a clinician review decision

        Args:
            transaction_id: Transaction ID being reviewed
            action: 'approve', 'reject', or 'flag_for_escalation'
            clinician_id: ID of clinician making the decision
            notes: Optional notes/feedback from clinician

        Returns:
            True if successful, False otherwise
        """
        if action not in ['approve', 'reject', 'flag_for_escalation']:
            print(f"❌ Invalid action: {action}")
            return False

        try:
            # Save to MongoDB
            if self.mongodb:
                self.mongodb.save_clinician_review(
                    transaction_id=transaction_id,
                    clinician_id=clinician_id,
                    action=action,
                    notes=notes
                )

            # Save to PostgreSQL audit log
            if self.postgres:
                self.postgres.log_audit_event(
                    transaction_id=transaction_id,
                    event_type='clinician_review',
                    status='success',
                    details={
                        'action': action,
                        'clinician_id': clinician_id,
                        'notes': notes,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )

            print(f"✓ Review submitted: {transaction_id} → {action}")
            return True

        except Exception as e:
            print(f"❌ Error submitting review: {e}")
            return False

    def get_review_history(self, transaction_id: str) -> list:
        """
        Get all reviews for a specific note

        Args:
            transaction_id: Transaction ID

        Returns:
            List of reviews
        """
        if not self.mongodb:
            return []

        try:
            collection = self.mongodb.db['clinician_reviews']
            reviews = list(collection.find({'transaction_id': transaction_id}))

            # Format for response
            for review in reviews:
                review['_id'] = str(review['_id'])
                if 'reviewed_at' in review:
                    review['reviewed_at'] = review['reviewed_at'].isoformat()

            return reviews
        except Exception as e:
            print(f"❌ Error fetching review history: {e}")
            return []

    def get_clinician_stats(self, clinician_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific clinician

        Args:
            clinician_id: ID of clinician

        Returns:
            Dictionary with stats
        """
        if not self.mongodb:
            return self._empty_clinician_stats()

        try:
            collection = self.mongodb.db['clinician_reviews']

            # Count actions by this clinician
            approvals = collection.count_documents(
                {'clinician_id': clinician_id, 'action': 'approve'}
            )
            rejections = collection.count_documents(
                {'clinician_id': clinician_id, 'action': 'reject'}
            )
            escalations = collection.count_documents(
                {'clinician_id': clinician_id, 'action': 'flag_for_escalation'}
            )

            total = approvals + rejections + escalations

            return {
                'clinician_id': clinician_id,
                'total_reviews': total,
                'approvals': approvals,
                'rejections': rejections,
                'escalations': escalations,
                'approval_rate': approvals / total if total > 0 else 0
            }
        except Exception as e:
            print(f"❌ Error fetching clinician stats: {e}")
            return self._empty_clinician_stats()

    def get_reviews_by_action(self, action: str, limit: int = 50) -> list:
        """
        Get all reviews with a specific action

        Args:
            action: 'approve', 'reject', or 'flag_for_escalation'
            limit: Maximum results to return

        Returns:
            List of reviews
        """
        if not self.mongodb:
            return []

        try:
            collection = self.mongodb.db['clinician_reviews']
            reviews = list(
                collection.find({'action': action}, sort=[('reviewed_at', -1)]).limit(limit)
            )

            for review in reviews:
                review['_id'] = str(review['_id'])
                if 'reviewed_at' in review:
                    review['reviewed_at'] = review['reviewed_at'].isoformat()

            return reviews
        except Exception as e:
            print(f"❌ Error fetching reviews: {e}")
            return []

    @staticmethod
    def _empty_clinician_stats() -> Dict[str, Any]:
        """Return empty clinician stats"""
        return {
            'clinician_id': '',
            'total_reviews': 0,
            'approvals': 0,
            'rejections': 0,
            'escalations': 0,
            'approval_rate': 0
        }


# Singleton instance
_review_service = None


def get_review_service() -> ReviewService:
    """Get or create review service instance"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
