"""
Audit Logging Module for Compliance Tracking
Logs all API calls, de-identification steps, and FHIR transformations
Supports both file-based (legacy) and database-backed (PostgreSQL) logging
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import uuid

# Try to import database module; fall back to file-based if not available
try:
    from .database import get_postgres_connection
    DB_AVAILABLE = True
except (ImportError, Exception):
    DB_AVAILABLE = False


class AuditLogger:
    """Manages compliance audit trails for the clinical scribe system"""

    def __init__(self, log_dir: str = "src/logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.audit_log_file = os.path.join(log_dir, "audit_log.json")
        self.transaction_log_file = os.path.join(log_dir, "transaction_log.json")
        self.ensure_log_files_exist()

    def ensure_log_files_exist(self):
        """Create log files if they don't exist"""
        for log_file in [self.audit_log_file, self.transaction_log_file]:
            if not os.path.exists(log_file):
                with open(log_file, 'w') as f:
                    json.dump([], f, indent=2)

    def log_transaction(
        self,
        transaction_id: Optional[str] = None,
        stage: str = "",
        status: str = "pending",
        input_length: int = 0,
        output_length: int = 0,
        model_used: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a transaction step

        Args:
            transaction_id: Unique identifier for the transaction
            stage: Processing stage (deidentification, llm_processing, fhir_transformation, etc.)
            status: Status of the operation (pending, success, failure)
            input_length: Length of input data
            output_length: Length of output data
            model_used: Name/version of the model used
            metadata: Additional metadata

        Returns:
            transaction_id
        """
        if transaction_id is None:
            transaction_id = str(uuid.uuid4())

        transaction_entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id,
            'stage': stage,
            'status': status,
            'input_length': input_length,
            'output_length': output_length,
            'model_used': model_used,
            'metadata': metadata or {}
        }

        # Append to transaction log
        transactions = self._read_json_log(self.transaction_log_file)
        transactions.append(transaction_entry)
        self._write_json_log(self.transaction_log_file, transactions)

        return transaction_id

    def log_deidentification(
        self,
        transaction_id: str,
        original_length: int,
        masked_length: int,
        redaction_counts: Dict[str, int],
        validation_report: Dict
    ):
        """Log de-identification activity to both JSON (legacy) and PostgreSQL"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id,
            'event_type': 'de_identification',
            'original_length': original_length,
            'masked_length': masked_length,
            'redactions': redaction_counts,
            'validation_safe': validation_report.get('is_safe', False),
            'risks_found': validation_report.get('remaining_phi_risks', [])
        }

        # Log to JSON (legacy support)
        audit_log = self._read_json_log(self.audit_log_file)
        audit_log.append(entry)
        self._write_json_log(self.audit_log_file, audit_log)

        # Log to PostgreSQL if available
        if DB_AVAILABLE:
            try:
                db = get_postgres_connection()
                db.log_audit_event(
                    transaction_id=transaction_id,
                    event_type='de_identification',
                    status='success',
                    details={
                        'original_length': original_length,
                        'masked_length': masked_length,
                        'redaction_counts': redaction_counts,
                        'validation_report': validation_report
                    }
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to log to PostgreSQL: {e}")

    def log_claude_api_call(
        self,
        transaction_id: str,
        prompt_length: int,
        response_length: int,
        model: str,
        max_tokens: int,
        temperature: float,
        status: str = "success",
        error_message: Optional[str] = None
    ):
        """Log Claude API call details to both JSON (legacy) and PostgreSQL"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id,
            'event_type': 'claude_api_call',
            'model': model,
            'prompt_length': prompt_length,
            'response_length': response_length,
            'max_tokens': max_tokens,
            'temperature': temperature,
            'status': status,
            'error_message': error_message
        }

        # Log to JSON (legacy support)
        audit_log = self._read_json_log(self.audit_log_file)
        audit_log.append(entry)
        self._write_json_log(self.audit_log_file, audit_log)

        # Log to PostgreSQL if available
        if DB_AVAILABLE:
            try:
                db = get_postgres_connection()
                db.log_audit_event(
                    transaction_id=transaction_id,
                    event_type='claude_api_call',
                    status=status,
                    details={
                        'model': model,
                        'prompt_length': prompt_length,
                        'response_length': response_length,
                        'max_tokens': max_tokens,
                        'temperature': temperature,
                        'error_message': error_message
                    }
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to log to PostgreSQL: {e}")

    def log_fhir_transformation(
        self,
        transaction_id: str,
        llm_output_length: int,
        fhir_bundle_length: int,
        resources_created: Dict[str, int],
        validation_passed: bool,
        schema_errors: Optional[list] = None
    ):
        """Log FHIR transformation and validation to both JSON (legacy) and PostgreSQL"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id,
            'event_type': 'fhir_transformation',
            'llm_output_length': llm_output_length,
            'fhir_bundle_length': fhir_bundle_length,
            'resources_created': resources_created,
            'validation_passed': validation_passed,
            'schema_errors': schema_errors or []
        }

        # Log to JSON (legacy support)
        audit_log = self._read_json_log(self.audit_log_file)
        audit_log.append(entry)
        self._write_json_log(self.audit_log_file, audit_log)

        # Log to PostgreSQL if available
        if DB_AVAILABLE:
            try:
                db = get_postgres_connection()
                db.log_audit_event(
                    transaction_id=transaction_id,
                    event_type='fhir_transformation',
                    status='success' if validation_passed else 'failure',
                    details={
                        'llm_output_length': llm_output_length,
                        'fhir_bundle_length': fhir_bundle_length,
                        'resources_created': resources_created,
                        'validation_passed': validation_passed,
                        'schema_errors': schema_errors
                    }
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to log to PostgreSQL: {e}")

    def log_confidence_scoring(
        self,
        transaction_id: str,
        overall_confidence: int,
        field_confidences: Dict[str, int],
        low_confidence_fields: list
    ):
        """Log confidence scoring for extracted data to both JSON (legacy) and PostgreSQL"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'transaction_id': transaction_id,
            'event_type': 'confidence_scoring',
            'overall_confidence': overall_confidence,
            'field_confidences': field_confidences,
            'low_confidence_fields': low_confidence_fields,
            'requires_human_review': len(low_confidence_fields) > 0
        }

        # Log to JSON (legacy support)
        audit_log = self._read_json_log(self.audit_log_file)
        audit_log.append(entry)
        self._write_json_log(self.audit_log_file, audit_log)

        # Log to PostgreSQL if available
        if DB_AVAILABLE:
            try:
                db = get_postgres_connection()
                db.log_audit_event(
                    transaction_id=transaction_id,
                    event_type='confidence_scoring',
                    status='success',
                    details={
                        'overall_confidence': overall_confidence,
                        'field_confidences': field_confidences,
                        'low_confidence_fields': low_confidence_fields,
                        'requires_human_review': len(low_confidence_fields) > 0
                    }
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to log to PostgreSQL: {e}")

    def get_transaction_summary(self, transaction_id: str) -> Dict:
        """Get a complete summary of a transaction"""
        audit_log = self._read_json_log(self.audit_log_file)
        transaction_events = [e for e in audit_log if e.get('transaction_id') == transaction_id]

        summary = {
            'transaction_id': transaction_id,
            'total_events': len(transaction_events),
            'events': transaction_events,
            'timeline': [e['timestamp'] for e in transaction_events]
        }

        return summary

    def _read_json_log(self, filepath: str) -> list:
        """Read JSON log file"""
        if not os.path.exists(filepath):
            return []
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def _write_json_log(self, filepath: str, data: list):
        """Write JSON log file"""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def export_audit_report(self, transaction_id: Optional[str] = None) -> str:
        """
        Export audit report as formatted text

        Args:
            transaction_id: If provided, export report for specific transaction

        Returns:
            Formatted audit report string
        """
        # Read from both transaction log and audit log
        audit_log = self._read_json_log(self.audit_log_file)
        transaction_log = self._read_json_log(self.transaction_log_file)

        # Combine both logs
        audit_log.extend(transaction_log)

        if transaction_id:
            audit_log = [e for e in audit_log if e.get('transaction_id') == transaction_id]

        report = "=== AUDIT REPORT ===\n"
        report += f"Generated: {datetime.now().isoformat()}\n"
        report += f"Total Events: {len(audit_log)}\n\n"

        for event in audit_log:
            report += f"Timestamp: {event['timestamp']}\n"
            report += f"Event Type: {event.get('event_type', 'N/A')}\n"
            report += f"Transaction ID: {event.get('transaction_id', 'N/A')}\n"

            if event.get('event_type') == 'de_identification':
                report += f"  - Redactions: {event.get('redactions', {})}\n"
                report += f"  - Validation Safe: {event.get('validation_safe', False)}\n"
            elif event.get('event_type') == 'claude_api_call':
                report += f"  - Model: {event.get('model', 'N/A')}\n"
                report += f"  - Status: {event.get('status', 'N/A')}\n"
            elif event.get('event_type') == 'fhir_transformation':
                report += f"  - Validation Passed: {event.get('validation_passed', False)}\n"
                report += f"  - Resources Created: {event.get('resources_created', {})}\n"
            elif event.get('event_type') == 'confidence_scoring':
                report += f"  - Overall Confidence: {event.get('overall_confidence', 0)}%\n"
                report += f"  - Requires Review: {event.get('requires_human_review', False)}\n"

            report += "\n"

        return report


def create_audit_logger(log_dir: str = "src/logs") -> AuditLogger:
    """Factory function to create an AuditLogger instance"""
    return AuditLogger(log_dir)
