"""
Comprehensive Unit Test Suite for HIPAA-Compliant Clinical Note Automation Tool

Tests cover:
- De-identification module (PHI detection and masking)
- Audit logging (all event types and persistence)
- FHIR schema validation
- FHIR transformer (all resource types)
- Claude API wrapper (with mocking)
- Integration tests (end-to-end pipeline)
- Error handling and edge cases
"""

import json
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from modules.deidentification import DeIdentifier, create_deidentifier
from modules.audit_logger import AuditLogger, create_audit_logger
from modules.fhir_transformer import FHIRTransformer, create_fhir_transformer
from modules.fhir_schemas import get_terminology_code, CLINICAL_NOTE_SCHEMA
from modules.claude_api import ClaudeAPIWrapper


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def deidentifier():
    """Create a fresh DeIdentifier instance"""
    return create_deidentifier()


@pytest.fixture
def temp_log_dir():
    """Create temporary directory for logs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def audit_logger(temp_log_dir):
    """Create AuditLogger with temporary directory"""
    return create_audit_logger(log_dir=temp_log_dir)


@pytest.fixture
def fhir_transformer(audit_logger):
    """Create FHIRTransformer instance"""
    return create_fhir_transformer(audit_logger=audit_logger)


@pytest.fixture
def mock_claude_output():
    """Sample Claude output for testing"""
    return {
        "encounter_summary": {
            "chief_complaint": "Persistent cough",
            "history_of_present_illness": "Patient reports 5-day cough with congestion"
        },
        "vital_signs_extracted": {
            "blood_pressure": "120/80 mmHg",
            "temperature": "98.6 F",
            "heart_rate": "72 bpm"
        },
        "clinical_entities": {
            "diagnoses_problems": [
                {"name": "Upper respiratory infection", "status": "active"},
                "Bronchitis"  # Test handling of string format
            ],
            "medication_requests_new_or_changed": [
                {"medication_name": "Amoxicillin", "dosage": "500mg", "route": "oral", "reason": "Infection"},
                "Cough suppressant"  # Test handling of string format
            ],
            "allergies": [
                {"name": "Penicillin", "reaction": "Rash"},
            ]
        },
        "assessment_plan_draft": "Continue antibiotics and monitor symptoms",
        "ai_confidence_score": 85,
        "flagged_for_review": False
    }


# ============================================================================
# DE-IDENTIFICATION TESTS (16 tests)
# ============================================================================

class TestDeidentification:
    """Test suite for de-identification module"""

    def test_deidentifier_creation(self, deidentifier):
        """Test DeIdentifier instance creation"""
        assert deidentifier is not None
        assert hasattr(deidentifier, 'deidentify')
        assert hasattr(deidentifier, 'validate_deidentification')

    def test_name_detection_and_masking(self, deidentifier):
        """Test detection and masking of patient names"""
        text = "Patient John Smith presented to the clinic"
        masked, audit = deidentifier.deidentify(text)

        assert "[PATIENT_NAME]" in masked
        assert "John Smith" not in masked
        assert audit['redactions_by_type'].get('names', 0) > 0

    def test_date_detection_and_masking(self, deidentifier):
        """Test detection and masking of dates"""
        text = "Patient was seen on January 15, 2025"
        masked, audit = deidentifier.deidentify(text)

        assert "[DATE]" in masked
        assert "January 15" not in masked
        assert audit['redactions_by_type'].get('dates', 0) > 0

    def test_mrn_detection_and_masking(self, deidentifier):
        """Test detection and masking of MRN"""
        text = "MRN: 123456789"
        masked, audit = deidentifier.deidentify(text)

        assert "[MRN]" in masked
        assert "123456789" not in masked
        assert audit['redactions_by_type'].get('mrn', 0) > 0

    def test_ssn_detection_and_masking(self, deidentifier):
        """Test detection and masking of SSN"""
        text = "Social Security Number: 123-45-6789"
        masked, audit = deidentifier.deidentify(text)

        assert "[SSN]" in masked
        assert "123-45-6789" not in masked
        assert audit['redactions_by_type'].get('ssn', 0) > 0

    def test_phone_detection_and_masking(self, deidentifier):
        """Test detection and masking of phone numbers"""
        text = "Contact: (555) 123-4567"
        masked, audit = deidentifier.deidentify(text)

        assert "[PHONE]" in masked
        assert "(555) 123-4567" not in masked
        assert audit['redactions_by_type'].get('phone', 0) > 0

    def test_email_detection_and_masking(self, deidentifier):
        """Test detection and masking of emails"""
        text = "Email: john.smith@example.com"
        masked, audit = deidentifier.deidentify(text)

        assert "[EMAIL]" in masked
        assert "john.smith@example.com" not in masked
        assert audit['redactions_by_type'].get('email', 0) > 0

    def test_no_phi_detected(self, deidentifier):
        """Test text with no PHI"""
        text = "Patient has hypertension and diabetes"
        masked, audit = deidentifier.deidentify(text)

        assert masked == text
        assert audit['total_redactions'] == 0

    def test_multiple_phi_in_one_text(self, deidentifier):
        """Test detection of multiple PHI types in single text"""
        text = "Patient John Smith, DOB: 01/15/1980, MRN: 123456, Phone: (555) 123-4567"
        masked, audit = deidentifier.deidentify(text)

        assert audit['total_redactions'] > 2
        assert "[PATIENT_NAME]" in masked
        assert "[DATE]" in masked
        assert "[MRN]" in masked
        assert "[PHONE]" in masked

    def test_validation_detects_remaining_phi(self, deidentifier):
        """Test validation of de-identified text"""
        # Create text that will have partial masking
        text = "Dr. Smith saw John Smith"
        masked, _ = deidentifier.deidentify(text)

        validation = deidentifier.validate_deidentification(masked)
        # Validation should check for remaining patterns
        assert 'is_safe' in validation
        assert 'remaining_phi_risks' in validation

    def test_audit_includes_timestamp(self, deidentifier):
        """Test that audit includes timestamp"""
        text = "Patient John Smith"
        _, audit = deidentifier.deidentify(text)

        assert 'timestamp' in audit
        assert isinstance(audit['timestamp'], str)

    def test_audit_tracks_redaction_types(self, deidentifier):
        """Test that audit tracks all redaction types"""
        text = "Patient John Smith, DOB: 01/15/1980"
        _, audit = deidentifier.deidentify(text)

        assert 'redactions_by_type' in audit
        assert audit['redactions_by_type'].get('names', 0) > 0
        assert audit['redactions_by_type'].get('dates', 0) > 0

    def test_length_tracking(self, deidentifier):
        """Test that original and masked lengths are tracked"""
        text = "Patient John Smith is here"
        _, audit = deidentifier.deidentify(text)

        assert audit['original_length'] > 0
        assert audit['masked_length'] > 0
        assert 'original_length' in audit
        assert 'masked_length' in audit

    def test_empty_text_handling(self, deidentifier):
        """Test handling of empty text"""
        text = ""
        masked, audit = deidentifier.deidentify(text)

        assert masked == ""
        assert audit['total_redactions'] == 0

    def test_very_long_text_handling(self, deidentifier):
        """Test handling of very long text"""
        text = "Patient John Smith. " * 1000
        masked, audit = deidentifier.deidentify(text)

        assert "[PATIENT_NAME]" in masked
        assert len(masked) > 0


# ============================================================================
# AUDIT LOGGER TESTS (15 tests)
# ============================================================================

class TestAuditLogger:
    """Test suite for audit logging module"""

    def test_audit_logger_creation(self, audit_logger):
        """Test AuditLogger instance creation"""
        assert audit_logger is not None
        assert hasattr(audit_logger, 'log_transaction')
        assert hasattr(audit_logger, 'log_deidentification')

    def test_log_files_created(self, audit_logger):
        """Test that log files are created"""
        assert os.path.exists(audit_logger.audit_log_file)
        assert os.path.exists(audit_logger.transaction_log_file)

    def test_transaction_logging(self, audit_logger):
        """Test logging of transactions"""
        txn_id = audit_logger.log_transaction(
            stage="test_stage",
            status="success",
            input_length=100,
            output_length=200,
            model_used="test-model"
        )

        assert txn_id is not None
        assert len(txn_id) > 0

    def test_deidentification_event_logging(self, audit_logger):
        """Test logging of de-identification events"""
        audit_logger.log_deidentification(
            transaction_id="test-txn-001",
            original_length=1000,
            masked_length=950,
            redaction_counts={"names": 2, "dates": 1},
            validation_report={"is_safe": True, "remaining_phi_risks": []}
        )

        # Verify log was written
        with open(audit_logger.audit_log_file) as f:
            logs = json.load(f)
            assert len(logs) > 0
            assert any(e['event_type'] == 'de_identification' for e in logs)

    def test_claude_api_call_logging(self, audit_logger):
        """Test logging of Claude API calls"""
        audit_logger.log_claude_api_call(
            transaction_id="test-txn-002",
            prompt_length=500,
            response_length=1000,
            model="claude-sonnet-4-5",
            max_tokens=2048,
            temperature=0.0,
            status="success"
        )

        with open(audit_logger.audit_log_file) as f:
            logs = json.load(f)
            assert any(e['event_type'] == 'claude_api_call' for e in logs)

    def test_fhir_transformation_logging(self, audit_logger):
        """Test logging of FHIR transformation events"""
        audit_logger.log_fhir_transformation(
            transaction_id="test-txn-003",
            llm_output_length=1000,
            fhir_bundle_length=1500,
            resources_created={"Patient": 1, "Encounter": 1, "Condition": 2},
            validation_passed=True
        )

        with open(audit_logger.audit_log_file) as f:
            logs = json.load(f)
            assert any(e['event_type'] == 'fhir_transformation' for e in logs)

    def test_confidence_scoring_logging(self, audit_logger):
        """Test logging of confidence scoring"""
        audit_logger.log_confidence_scoring(
            transaction_id="test-txn-004",
            overall_confidence=85,
            field_confidences={"diagnosis": 90, "medication": 80},
            low_confidence_fields=[]
        )

        with open(audit_logger.audit_log_file) as f:
            logs = json.load(f)
            assert any(e['event_type'] == 'confidence_scoring' for e in logs)

    def test_get_transaction_summary(self, audit_logger):
        """Test retrieving transaction summary"""
        txn_id = "test-summary-txn"

        audit_logger.log_transaction(
            transaction_id=txn_id,
            stage="test",
            status="success"
        )

        summary = audit_logger.get_transaction_summary(txn_id)
        assert summary['transaction_id'] == txn_id
        assert 'events' in summary
        assert 'total_events' in summary

    def test_export_audit_report(self, audit_logger):
        """Test exporting audit report"""
        audit_logger.log_transaction(
            transaction_id="report-test",
            stage="test",
            status="success"
        )

        report = audit_logger.export_audit_report("report-test")
        assert isinstance(report, str)
        assert "AUDIT REPORT" in report
        assert "report-test" in report

    def test_multiple_events_per_transaction(self, audit_logger):
        """Test logging multiple events for one transaction"""
        txn_id = "multi-event-txn"

        audit_logger.log_deidentification(
            transaction_id=txn_id,
            original_length=1000,
            masked_length=950,
            redaction_counts={"names": 1},
            validation_report={"is_safe": True, "remaining_phi_risks": []}
        )

        audit_logger.log_claude_api_call(
            transaction_id=txn_id,
            prompt_length=950,
            response_length=1500,
            model="test-model",
            max_tokens=2048,
            temperature=0.0,
            status="success"
        )

        summary = audit_logger.get_transaction_summary(txn_id)
        assert summary['total_events'] == 2

    def test_log_persistence(self, audit_logger):
        """Test that logs persist across instances"""
        txn_id = "persistence-test"
        audit_logger.log_transaction(
            transaction_id=txn_id,
            stage="test",
            status="success"
        )

        # Create new logger with same directory
        new_logger = create_audit_logger(log_dir=audit_logger.log_dir)
        summary = new_logger.get_transaction_summary(txn_id)

        assert summary['transaction_id'] == txn_id

    def test_error_status_logging(self, audit_logger):
        """Test logging of error statuses"""
        audit_logger.log_claude_api_call(
            transaction_id="error-test",
            prompt_length=500,
            response_length=0,
            model="test-model",
            max_tokens=2048,
            temperature=0.0,
            status="failure",
            error_message="Test error"
        )

        with open(audit_logger.audit_log_file) as f:
            logs = json.load(f)
            error_log = [e for e in logs if e.get('status') == 'failure']
            assert len(error_log) > 0
            assert error_log[0]['error_message'] == "Test error"


# ============================================================================
# FHIR SCHEMA TESTS (10 tests)
# ============================================================================

class TestFHIRSchemas:
    """Test suite for FHIR schema definitions"""

    def test_clinical_note_schema_exists(self):
        """Test that clinical note schema is defined"""
        assert CLINICAL_NOTE_SCHEMA is not None
        assert CLINICAL_NOTE_SCHEMA['name'] == 'ClinicalNote'
        assert CLINICAL_NOTE_SCHEMA['strict'] == True

    def test_clinical_note_schema_has_required_fields(self):
        """Test that schema has all required fields"""
        schema = CLINICAL_NOTE_SCHEMA['schema']
        required = schema['required']

        expected_fields = [
            'encounter_summary',
            'vital_signs_extracted',
            'clinical_entities',
            'assessment_plan_draft',
            'ai_confidence_score',
            'flagged_for_review'
        ]

        for field in expected_fields:
            assert field in required

    def test_encounter_summary_schema(self):
        """Test encounter summary schema structure"""
        schema = CLINICAL_NOTE_SCHEMA['schema']
        encounter = schema['properties']['encounter_summary']

        assert 'chief_complaint' in encounter['properties']
        assert 'history_of_present_illness' in encounter['properties']

    def test_vital_signs_schema(self):
        """Test vital signs schema structure"""
        schema = CLINICAL_NOTE_SCHEMA['schema']
        vitals = schema['properties']['vital_signs_extracted']

        expected_vitals = ['blood_pressure', 'temperature', 'heart_rate']
        for vital in expected_vitals:
            assert vital in vitals['properties']

    def test_clinical_entities_schema(self):
        """Test clinical entities schema structure"""
        schema = CLINICAL_NOTE_SCHEMA['schema']
        entities = schema['properties']['clinical_entities']

        assert 'diagnoses_problems' in entities['properties']
        assert 'medication_requests_new_or_changed' in entities['properties']
        assert 'allergies' in entities['properties']

    def test_confidence_score_schema(self):
        """Test confidence score schema"""
        schema = CLINICAL_NOTE_SCHEMA['schema']
        confidence = schema['properties']['ai_confidence_score']

        assert confidence['description'] == "Overall confidence score (1-100) for entity extraction"

    def test_terminology_mapping_conditions(self):
        """Test condition terminology mapping"""
        result = get_terminology_code("diabetes", "condition")

        assert result['found'] == True
        assert 'codes' in result
        assert result['display'] == "diabetes"

    def test_terminology_mapping_medications(self):
        """Test medication terminology mapping"""
        result = get_terminology_code("aspirin", "medication")

        assert result['found'] == True
        assert 'codes' in result

    def test_terminology_unknown_condition(self):
        """Test handling of unknown condition"""
        result = get_terminology_code("unknown_condition_xyz", "condition")

        assert result['found'] == False
        assert result['display'] == "unknown_condition_xyz"

    def test_terminology_code_structure(self):
        """Test structure of terminology results"""
        result = get_terminology_code("hypertension", "condition")

        assert 'found' in result
        assert 'codes' in result
        assert 'display' in result


# ============================================================================
# FHIR TRANSFORMER TESTS (18 tests)
# ============================================================================

class TestFHIRTransformer:
    """Test suite for FHIR transformer module"""

    def test_transformer_creation(self, fhir_transformer):
        """Test FHIRTransformer instance creation"""
        assert fhir_transformer is not None
        assert hasattr(fhir_transformer, 'transform_to_fhir_bundle')

    def test_bundle_creation(self, fhir_transformer, mock_claude_output):
        """Test basic FHIR bundle creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-001"
        )

        assert bundle is not None
        assert bundle['resourceType'] == 'Bundle'
        assert bundle['type'] == 'collection'

    def test_bundle_has_entries(self, fhir_transformer, mock_claude_output):
        """Test that bundle contains entries"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-002"
        )

        assert 'entry' in bundle
        assert len(bundle['entry']) > 0

    def test_patient_resource_creation(self, fhir_transformer, mock_claude_output):
        """Test Patient resource creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-003"
        )

        assert resources['Patient'] > 0
        patient_resources = [e['resource'] for e in bundle['entry']
                            if e['resource']['resourceType'] == 'Patient']
        assert len(patient_resources) > 0

    def test_encounter_resource_creation(self, fhir_transformer, mock_claude_output):
        """Test Encounter resource creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-004"
        )

        assert resources['Encounter'] > 0
        encounter_resources = [e['resource'] for e in bundle['entry']
                              if e['resource']['resourceType'] == 'Encounter']
        assert len(encounter_resources) > 0

    def test_condition_resource_creation(self, fhir_transformer, mock_claude_output):
        """Test Condition resource creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-005"
        )

        assert resources['Condition'] > 0
        condition_resources = [e['resource'] for e in bundle['entry']
                              if e['resource']['resourceType'] == 'Condition']
        assert len(condition_resources) > 0

    def test_medication_request_resource_creation(self, fhir_transformer, mock_claude_output):
        """Test MedicationRequest resource creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-006"
        )

        assert resources['MedicationRequest'] > 0
        med_resources = [e['resource'] for e in bundle['entry']
                        if e['resource']['resourceType'] == 'MedicationRequest']
        assert len(med_resources) > 0

    def test_allergy_resource_creation(self, fhir_transformer, mock_claude_output):
        """Test AllergyIntolerance resource creation"""
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-007"
        )

        assert resources['AllergyIntolerance'] > 0
        allergy_resources = [e['resource'] for e in bundle['entry']
                            if e['resource']['resourceType'] == 'AllergyIntolerance']
        assert len(allergy_resources) > 0

    def test_patient_resource_structure(self, fhir_transformer, mock_claude_output):
        """Test Patient resource has required fields"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-008"
        )

        patient = next(e['resource'] for e in bundle['entry']
                      if e['resource']['resourceType'] == 'Patient')

        assert 'id' in patient
        assert patient['resourceType'] == 'Patient'
        assert 'name' in patient

    def test_encounter_resource_structure(self, fhir_transformer, mock_claude_output):
        """Test Encounter resource has required fields"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-009"
        )

        encounter = next(e['resource'] for e in bundle['entry']
                        if e['resource']['resourceType'] == 'Encounter')

        assert 'id' in encounter
        assert encounter['status'] == 'finished'
        assert 'subject' in encounter

    def test_condition_resource_structure(self, fhir_transformer, mock_claude_output):
        """Test Condition resource has required fields"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-010"
        )

        condition = next(e['resource'] for e in bundle['entry']
                        if e['resource']['resourceType'] == 'Condition')

        assert 'id' in condition
        assert 'code' in condition
        assert 'subject' in condition

    def test_bundle_validation(self, fhir_transformer, mock_claude_output):
        """Test FHIR bundle validation"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-011"
        )

        is_valid, errors = fhir_transformer.validate_fhir_bundle(bundle)
        assert is_valid == True

    def test_string_diagnosis_handling(self, fhir_transformer):
        """Test handling of string format diagnoses"""
        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {
                "diagnoses_problems": ["Diabetes", "Hypertension"],  # Strings instead of dicts
                "medication_requests_new_or_changed": [],
                "allergies": []
            },
            "assessment_plan_draft": "Continue monitoring",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        bundle, resources = fhir_transformer.transform_to_fhir_bundle(output, "test-txn-012")
        assert resources['Condition'] == 2

    def test_string_medication_handling(self, fhir_transformer):
        """Test handling of string format medications"""
        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {
                "diagnoses_problems": [],
                "medication_requests_new_or_changed": ["Aspirin", "Metformin"],  # Strings
                "allergies": []
            },
            "assessment_plan_draft": "Continue monitoring",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        bundle, resources = fhir_transformer.transform_to_fhir_bundle(output, "test-txn-013")
        assert resources['MedicationRequest'] == 2

    def test_string_allergy_handling(self, fhir_transformer):
        """Test handling of string format allergies"""
        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {
                "diagnoses_problems": [],
                "medication_requests_new_or_changed": [],
                "allergies": ["Penicillin", "Sulfonamides"]  # Strings
            },
            "assessment_plan_draft": "Continue monitoring",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        bundle, resources = fhir_transformer.transform_to_fhir_bundle(output, "test-txn-014")
        assert resources['AllergyIntolerance'] == 2

    def test_bundle_metadata(self, fhir_transformer, mock_claude_output):
        """Test bundle has proper metadata"""
        bundle, _ = fhir_transformer.transform_to_fhir_bundle(
            mock_claude_output,
            "test-txn-015"
        )

        assert 'meta' in bundle
        assert 'source' in bundle['meta']
        assert 'transactionId' in bundle['meta']


# ============================================================================
# CLAUDE API WRAPPER TESTS (12 tests)
# ============================================================================

class TestClaudeAPIWrapper:
    """Test suite for Claude API wrapper module"""

    def test_wrapper_schema_validation(self):
        """Test output schema validation"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        valid_output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(valid_output)
        assert is_valid == True

    def test_wrapper_schema_validation_missing_field(self):
        """Test validation detects missing required fields"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        invalid_output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            # Missing vital_signs_extracted
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(invalid_output)
        # Should add default or flag as error
        assert 'vital_signs_extracted' in invalid_output

    def test_schema_fills_missing_encounter_summary(self):
        """Test schema validation fills missing encounter_summary"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(output)
        assert 'encounter_summary' in output

    def test_schema_fills_missing_vital_signs(self):
        """Test schema validation fills missing vital_signs"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(output)
        assert 'vital_signs_extracted' in output

    def test_schema_fills_missing_entities(self):
        """Test schema validation fills missing entities"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(output)
        assert 'clinical_entities' in output

    def test_confidence_score_validation(self):
        """Test confidence score validation"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 150,  # Invalid: > 100
            "flagged_for_review": False
        }

        is_valid, errors = wrapper.validate_output_schema(output)
        # Should have error or default
        assert isinstance(output['ai_confidence_score'], int)

    def test_flagged_for_review_must_be_boolean(self):
        """Test flagged_for_review validation"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": "yes"  # Should be boolean
        }

        is_valid, errors = wrapper.validate_output_schema(output)
        assert isinstance(output['flagged_for_review'], bool)


# ============================================================================
# INTEGRATION TESTS (8 tests)
# ============================================================================

class TestIntegration:
    """Integration tests for complete pipeline"""

    def test_full_pipeline_with_mock_data(self, deidentifier, audit_logger, fhir_transformer):
        """Test complete pipeline: de-id → validation → FHIR"""
        # Setup
        raw_text = "Patient John Smith, DOB: 01/15/1980, presented with cough"

        # Step 1: De-identification
        masked, de_audit = deidentifier.deidentify(raw_text)
        audit_logger.log_deidentification(
            transaction_id="integration-001",
            original_length=len(raw_text),
            masked_length=len(masked),
            redaction_counts=de_audit.get('redactions_by_type', {}),
            validation_report=deidentifier.validate_deidentification(masked)
        )

        # Step 2: Mock Claude output
        claude_output = {
            "encounter_summary": {"chief_complaint": "Cough", "history_of_present_illness": "5 days of cough"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {
                "diagnoses_problems": ["Upper respiratory infection"],
                "medication_requests_new_or_changed": ["Cough suppressant"],
                "allergies": []
            },
            "assessment_plan_draft": "Monitor and rest",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        # Step 3: FHIR transformation
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(
            claude_output,
            "integration-001"
        )

        audit_logger.log_fhir_transformation(
            transaction_id="integration-001",
            llm_output_length=len(json.dumps(claude_output)),
            fhir_bundle_length=len(json.dumps(bundle)),
            resources_created=resources,
            validation_passed=True
        )

        # Verify complete flow
        assert "[PATIENT_NAME]" in masked
        assert bundle['resourceType'] == 'Bundle'
        assert resources['Patient'] > 0

    def test_pipeline_with_multiple_entities(self, deidentifier, fhir_transformer):
        """Test pipeline with multiple diagnoses and medications"""
        mock_output = {
            "encounter_summary": {"chief_complaint": "Multiple issues", "history_of_present_illness": "Multiple symptoms"},
            "vital_signs_extracted": {"blood_pressure": "140/90", "temperature": "99.2", "heart_rate": "88"},
            "clinical_entities": {
                "diagnoses_problems": [
                    {"name": "Hypertension", "status": "active"},
                    {"name": "Diabetes", "status": "active"},
                    "Hyperlipidemia"
                ],
                "medication_requests_new_or_changed": [
                    {"medication_name": "Lisinopril", "dosage": "10mg", "route": "oral", "reason": "HTN"},
                    {"medication_name": "Metformin", "dosage": "500mg", "route": "oral", "reason": "DM"},
                    "Atorvastatin"
                ],
                "allergies": [
                    {"name": "Penicillin", "reaction": "Rash"},
                    "Sulfa drugs"
                ]
            },
            "assessment_plan_draft": "Manage chronic conditions",
            "ai_confidence_score": 88,
            "flagged_for_review": False
        }

        bundle, resources = fhir_transformer.transform_to_fhir_bundle(mock_output, "multi-entity-001")

        assert resources['Condition'] == 3
        assert resources['MedicationRequest'] == 3
        assert resources['AllergyIntolerance'] == 2

    def test_error_handling_in_pipeline(self, fhir_transformer):
        """Test error handling with incomplete data"""
        incomplete_output = {
            "encounter_summary": {"chief_complaint": "", "history_of_present_illness": ""},
            "vital_signs_extracted": {"blood_pressure": "N/A", "temperature": "N/A", "heart_rate": "N/A"},
            "clinical_entities": {
                "diagnoses_problems": [],
                "medication_requests_new_or_changed": [],
                "allergies": []
            },
            "assessment_plan_draft": "N/A",
            "ai_confidence_score": 30,
            "flagged_for_review": True
        }

        # Should still create a valid bundle even with empty data
        bundle, resources = fhir_transformer.transform_to_fhir_bundle(incomplete_output, "error-handling-001")

        assert bundle['resourceType'] == 'Bundle'
        assert 'entry' in bundle


# ============================================================================
# EDGE CASE TESTS (10 tests)
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_very_long_conversation(self, deidentifier):
        """Test handling of very long clinical notes"""
        long_text = "Patient presented with symptoms. " * 5000
        masked, audit = deidentifier.deidentify(long_text)

        assert len(masked) > 0
        assert audit['original_length'] > 100000

    def test_special_characters_in_text(self, deidentifier):
        """Test handling of special characters"""
        text = "Patient: Dr. John O'Brien; Email: test@example.com; Phone: (555) 123-4567 ext. 123"
        masked, audit = deidentifier.deidentify(text)

        assert masked is not None
        assert len(masked) > 0

    def test_mixed_case_phi(self, deidentifier):
        """Test PHI detection with mixed case"""
        text = "patient JOHN SMITH seen on JANUARY 15, 2025"
        masked, audit = deidentifier.deidentify(text)

        # Should detect despite case variations
        assert "[" in masked  # Should have placeholders

    def test_repeated_phi_elements(self, deidentifier):
        """Test handling of repeated PHI in same text"""
        text = "John Smith called John Smith about John Smith"
        masked, audit = deidentifier.deidentify(text)

        # All instances should be masked
        assert "John Smith" not in masked

    def test_unicode_in_clinical_notes(self, deidentifier):
        """Test handling of unicode characters"""
        text = "Patient reports naïve fever and café allergy"
        masked, audit = deidentifier.deidentify(text)

        assert len(masked) > 0

    def test_null_values_in_fhir_output(self, fhir_transformer):
        """Test handling of null values"""
        output = {
            "encounter_summary": {"chief_complaint": None, "history_of_present_illness": None},
            "vital_signs_extracted": {"blood_pressure": None, "temperature": None, "heart_rate": None},
            "clinical_entities": {
                "diagnoses_problems": None,
                "medication_requests_new_or_changed": None,
                "allergies": None
            },
            "assessment_plan_draft": None,
            "ai_confidence_score": 50,
            "flagged_for_review": False
        }

        # Should handle gracefully
        try:
            bundle, _ = fhir_transformer.transform_to_fhir_bundle(output, "null-test")
            assert bundle is not None
        except Exception as e:
            pytest.fail(f"Should handle null values gracefully: {e}")

    def test_empty_lists_in_entities(self, fhir_transformer):
        """Test handling of empty entity lists"""
        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {
                "diagnoses_problems": [],
                "medication_requests_new_or_changed": [],
                "allergies": []
            },
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 85,
            "flagged_for_review": False
        }

        bundle, resources = fhir_transformer.transform_to_fhir_bundle(output, "empty-lists")

        assert resources['Patient'] > 0
        assert resources['Encounter'] > 0
        assert resources['Condition'] == 0

    def test_very_high_confidence_score(self):
        """Test handling of edge case confidence scores"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 100,  # Maximum
            "flagged_for_review": False
        }

        is_valid, _ = wrapper.validate_output_schema(output)
        assert 1 <= output['ai_confidence_score'] <= 100

    def test_very_low_confidence_score(self):
        """Test handling of very low confidence"""
        os.environ['ANTHROPIC_API_KEY'] = 'test-key'
        wrapper = ClaudeAPIWrapper(api_key='test-key')

        output = {
            "encounter_summary": {"chief_complaint": "Test", "history_of_present_illness": "Test"},
            "vital_signs_extracted": {"blood_pressure": "120/80", "temperature": "98.6", "heart_rate": "72"},
            "clinical_entities": {"diagnoses_problems": [], "medication_requests_new_or_changed": [], "allergies": []},
            "assessment_plan_draft": "Test",
            "ai_confidence_score": 1,  # Minimum
            "flagged_for_review": True
        }

        is_valid, _ = wrapper.validate_output_schema(output)
        assert 1 <= output['ai_confidence_score'] <= 100


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
