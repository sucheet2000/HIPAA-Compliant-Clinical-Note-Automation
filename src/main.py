"""
Main Orchestration Script
End-to-end clinical note processing pipeline
Supports both file-based and database-backed storage
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

# Import modules
from modules.deidentification import create_deidentifier
from modules.audit_logger import create_audit_logger
from modules.claude_api import create_claude_api_wrapper
from modules.fhir_transformer import create_fhir_transformer

# Try to import database module; fall back gracefully if not available
try:
    from modules.database import get_mongodb_connection
    DB_AVAILABLE = True
except (ImportError, Exception):
    DB_AVAILABLE = False


class ClinicalNoteProcessor:
    """
    Main orchestrator for the HIPAA-compliant clinical note automation pipeline
    """

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize the clinical note processor

        Args:
            log_dir: Directory for audit logs
        """
        self.deidentifier = create_deidentifier()
        self.audit_logger = create_audit_logger(log_dir)
        self.claude_api = create_claude_api_wrapper(audit_logger=self.audit_logger)
        self.fhir_transformer = create_fhir_transformer(audit_logger=self.audit_logger)

    def process_conversation(
        self,
        raw_conversation: str,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a raw clinical conversation end-to-end

        Args:
            raw_conversation: The unstructured clinical conversation text
            transaction_id: Optional transaction ID (generates if not provided)

        Returns:
            Dictionary with processing results
        """
        # Generate transaction ID if not provided
        transaction_id = transaction_id or str(uuid.uuid4())

        print(f"\n{'='*80}")
        print(f"Processing Transaction: {transaction_id}")
        print(f"{'='*80}\n")

        result = {
            'transaction_id': transaction_id,
            'stages': {},
            'success': False
        }

        try:
            # STAGE 1: De-identification
            print("STAGE 1: De-identification")
            print("-" * 40)
            masked_text, deidentification_audit = self.deidentifier.deidentify(raw_conversation)

            # Validate de-identification
            validation_report = self.deidentifier.validate_deidentification(masked_text)

            self.audit_logger.log_deidentification(
                transaction_id=transaction_id,
                original_length=deidentification_audit['original_length'],
                masked_length=deidentification_audit['masked_length'],
                redaction_counts=deidentification_audit.get('redactions_by_type', {}),
                validation_report=validation_report
            )

            result['stages']['deidentification'] = {
                'status': 'success',
                'redactions': deidentification_audit.get('redactions_by_type', {}),
                'validation_safe': validation_report['is_safe'],
                'phi_risks_found': len(validation_report.get('remaining_phi_risks', []))
            }

            print(f"✓ Redactions applied: {deidentification_audit.get('total_redactions', 0)}")
            print(f"✓ Validation safe: {validation_report['is_safe']}")
            if not validation_report['is_safe']:
                print(f"  WARNING: Remaining PHI risks: {validation_report['remaining_phi_risks']}")
            print(f"✓ Original length: {deidentification_audit['original_length']} chars")
            print(f"✓ Masked length: {deidentification_audit['masked_length']} chars\n")

            # STAGE 2: Claude API Processing
            print("STAGE 2: Claude API Processing")
            print("-" * 40)

            structured_output, raw_response = self.claude_api.process_clinical_conversation(
                masked_conversation=masked_text,
                transaction_id=transaction_id
            )

            # Validate output schema
            is_valid, schema_errors = self.claude_api.validate_output_schema(structured_output)

            if not is_valid:
                raise ValueError(f"Claude output schema validation failed: {schema_errors}")

            result['stages']['claude_processing'] = {
                'status': 'success',
                'confidence_score': structured_output.get('ai_confidence_score', 0),
                'flagged_for_review': structured_output.get('flagged_for_review', False),
                'review_notes': structured_output.get('review_notes', '')
            }

            print(f"✓ Claude processed successfully")
            print(f"✓ Confidence score: {structured_output.get('ai_confidence_score', 0)}/100")
            print(f"✓ Flagged for review: {structured_output.get('flagged_for_review', False)}")
            if structured_output.get('flagged_for_review'):
                print(f"  Review notes: {structured_output.get('review_notes', 'N/A')}\n")
            else:
                print()

            # Log confidence scoring
            field_confidences = self._extract_field_confidences(structured_output)
            low_confidence_fields = [f for f, c in field_confidences.items() if c < 70]

            self.audit_logger.log_confidence_scoring(
                transaction_id=transaction_id,
                overall_confidence=structured_output.get('ai_confidence_score', 0),
                field_confidences=field_confidences,
                low_confidence_fields=low_confidence_fields
            )

            # STAGE 3: FHIR Transformation
            print("STAGE 3: FHIR Transformation")
            print("-" * 40)

            fhir_bundle, resource_counts = self.fhir_transformer.transform_to_fhir_bundle(
                claude_output=structured_output,
                transaction_id=transaction_id
            )

            # Validate FHIR bundle
            is_valid, validation_errors = self.fhir_transformer.validate_fhir_bundle(fhir_bundle)

            if not is_valid:
                print(f"⚠ FHIR validation warnings: {validation_errors}")

            result['stages']['fhir_transformation'] = {
                'status': 'success',
                'resource_counts': resource_counts,
                'bundle_id': fhir_bundle.get('id'),
                'validation_passed': is_valid
            }

            print(f"✓ FHIR Bundle created")
            print(f"✓ Resources created:")
            for resource_type, count in resource_counts.items():
                if count > 0:
                    print(f"  - {resource_type}: {count}")
            print(f"✓ Bundle ID: {fhir_bundle.get('id')}\n")

            # STAGE 4: Generate final output
            print("STAGE 4: Output Generation")
            print("-" * 40)

            result['success'] = True
            result['outputs'] = {
                'masked_conversation': masked_text,
                'structured_clinical_data': structured_output,
                'fhir_bundle': fhir_bundle
            }

            print(f"✓ All stages completed successfully")
            print(f"✓ Transaction ID: {transaction_id}\n")

            return result

        except Exception as e:
            error_msg = f"Processing failed: {str(e)}"
            print(f"✗ Error: {error_msg}\n")

            result['success'] = False
            result['error'] = error_msg

            return result

    def process_batch_conversations(self, conversation_list: list) -> list:
        """
        Process multiple conversations in batch

        Args:
            conversation_list: List of conversation texts

        Returns:
            List of processing results
        """
        results = []
        for i, conversation in enumerate(conversation_list, 1):
            print(f"\n[{i}/{len(conversation_list)}] Processing conversation...")
            result = self.process_conversation(conversation)
            results.append(result)

        return results

    def save_results(self, result: Dict[str, Any], output_dir: str = "output") -> str:
        """
        Save processing results to files and databases

        Args:
            result: The processing result dictionary
            output_dir: Directory to save results

        Returns:
            Path to saved results
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        transaction_id = result['transaction_id']
        result_file = output_path / f"result_{transaction_id}.json"

        # Save JSON file (legacy support)
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)

        print(f"✓ Results saved to: {result_file}")

        # Save FHIR bundle to MongoDB if available
        if DB_AVAILABLE and 'outputs' in result and 'fhir_bundle' in result['outputs']:
            try:
                mongodb = get_mongodb_connection()
                fhir_bundle = result['outputs']['fhir_bundle']
                confidence_score = result['outputs'].get('confidence_score', 0)

                # Save the FHIR bundle
                mongodb.save_fhir_bundle(
                    transaction_id=transaction_id,
                    bundle=fhir_bundle,
                    confidence_score=confidence_score,
                    validation_status='passed' if result['outputs'].get('validation_passed', False) else 'failed'
                )

                # Save clinical note metadata
                mongodb.save_clinical_note(
                    transaction_id=transaction_id,
                    masked_text=result['stages'].get('deidentification', {}).get('masked_text', ''),
                    structured_output=result['outputs'].get('structured_clinical_data', {}),
                    original_text=None  # We don't store original PHI
                )

                print(f"✓ FHIR bundle saved to MongoDB")
            except Exception as e:
                print(f"⚠️  Warning: Failed to save to MongoDB: {e}")

        return str(result_file)

    def generate_audit_report(self, transaction_id: str) -> str:
        """
        Generate audit report for a transaction

        Args:
            transaction_id: The transaction ID

        Returns:
            Formatted audit report
        """
        return self.audit_logger.export_audit_report(transaction_id)

    def _extract_field_confidences(self, structured_output: Dict[str, Any]) -> Dict[str, int]:
        """
        Extract confidence scores from individual fields

        Args:
            structured_output: The Claude structured output

        Returns:
            Dictionary of field confidences
        """
        confidences = {}

        # Chief complaint confidence
        chief_complaint = structured_output.get('encounter_summary', {}).get('chief_complaint', '')
        confidences['chief_complaint'] = 90 if chief_complaint and chief_complaint != 'N/A' else 30

        # Vital signs confidence
        vital_signs = structured_output.get('vital_signs_extracted', {})
        non_na_vitals = sum(1 for v in vital_signs.values() if v and v != 'N/A')
        confidences['vital_signs'] = min(100, (non_na_vitals / 5) * 100)

        # Diagnoses confidence
        diagnoses = structured_output.get('clinical_entities', {}).get('diagnoses_problems', [])
        confidences['diagnoses'] = 85 if diagnoses else 20

        # Medications confidence
        medications = structured_output.get('clinical_entities', {}).get('medication_requests_new_or_changed', [])
        confidences['medications'] = 85 if medications else 20

        # Allergies confidence
        allergies = structured_output.get('clinical_entities', {}).get('allergies', [])
        confidences['allergies'] = 80 if allergies else 50

        # Assessment/Plan confidence
        assessment = structured_output.get('assessment_plan_draft', '')
        confidences['assessment_plan'] = 75 if assessment and assessment != 'N/A' else 30

        return confidences


def load_mock_conversations(filepath: str = "data/mock_conversations.json") -> list:
    """
    Load mock clinical conversations from JSON file

    Args:
        filepath: Path to the mock conversations file

    Returns:
        List of conversation texts
    """
    with open(filepath, 'r') as f:
        data = json.load(f)

    return [conv['conversation'] for conv in data]


def main():
    """Main entry point for the clinical note processor"""

    print("\n" + "="*80)
    print("HIPAA-Compliant Clinical Note Automation Tool")
    print("="*80)

    # Initialize processor
    processor = ClinicalNoteProcessor()

    # Load mock conversations
    try:
        conversations = load_mock_conversations()
        print(f"\nLoaded {len(conversations)} mock clinical conversations")
    except FileNotFoundError:
        print("Error: mock_conversations.json not found")
        sys.exit(1)

    # Process conversations
    results = []
    for i, conversation in enumerate(conversations, 1):  # Process all conversations
        print(f"\n\n{'#'*80}")
        print(f"# CONVERSATION {i}/{len(conversations)}")
        print(f"{'#'*80}")

        result = processor.process_conversation(conversation)
        results.append(result)

        # Save result
        processor.save_results(result)

        # Print audit report
        if result['success']:
            audit_report = processor.generate_audit_report(result['transaction_id'])
            print("\nAUDIT REPORT:")
            print("-" * 40)
            print(audit_report)

    # Summary
    print("\n" + "="*80)
    print("PROCESSING SUMMARY")
    print("="*80)
    successful = sum(1 for r in results if r['success'])
    print(f"Total conversations processed: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
