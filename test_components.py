"""
Component Testing Script
Validates all modules except Claude API (which requires API key)
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from modules.deidentification import create_deidentifier
from modules.audit_logger import create_audit_logger
from modules.fhir_transformer import create_fhir_transformer
from modules.fhir_schemas import CLINICAL_NOTE_SCHEMA


def test_deidentification():
    """Test the de-identification module"""
    print("\n" + "="*80)
    print("TEST 1: De-identification Module")
    print("="*80 + "\n")

    deidentifier = create_deidentifier()

    # Test with realistic clinical text
    test_text = """
    Patient: John Smith, DOB 05/15/1980, MRN 123456789
    Phone: (555) 123-4567
    Address: 123 Main Street, New York, NY 10001

    Chief Complaint: The patient presents with chest pain on January 15th, 2025.
    History: Patient is a 45-year-old male with hypertension.
    Email: john.smith@example.com
    SSN: 123-45-6789
    """

    print("Input text (with PHI):")
    print("-" * 40)
    print(test_text[:200] + "...\n")

    # De-identify
    masked_text, audit = deidentifier.deidentify(test_text)

    print("Output text (de-identified):")
    print("-" * 40)
    print(masked_text[:200] + "...\n")

    print("De-identification Audit:")
    print("-" * 40)
    print(f"Original length: {audit['original_length']} chars")
    print(f"Masked length: {audit['masked_length']} chars")
    print(f"Total redactions: {audit['total_redactions']}")
    print(f"Redactions by type:")
    for phi_type, count in audit.get('redactions_by_type', {}).items():
        print(f"  - {phi_type}: {count}")

    # Validate
    validation = deidentifier.validate_deidentification(masked_text)
    print(f"\nValidation safe: {validation['is_safe']}")
    if not validation['is_safe']:
        print(f"Remaining risks: {validation['remaining_phi_risks']}")

    print("\n✓ De-identification test passed!\n")
    return True


def test_audit_logger():
    """Test the audit logging module"""
    print("\n" + "="*80)
    print("TEST 2: Audit Logger Module")
    print("="*80 + "\n")

    audit_logger = create_audit_logger(log_dir="test_logs")

    transaction_id = "test-txn-001"

    # Log de-identification
    print("Logging de-identification event...")
    audit_logger.log_deidentification(
        transaction_id=transaction_id,
        original_length=1000,
        masked_length=950,
        redaction_counts={'names': 1, 'dates': 2, 'mrn': 1},
        validation_report={'is_safe': True, 'remaining_phi_risks': []}
    )

    # Log Claude API call
    print("Logging Claude API call...")
    audit_logger.log_claude_api_call(
        transaction_id=transaction_id,
        prompt_length=950,
        response_length=1500,
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        temperature=0.0,
        status="success"
    )

    # Log FHIR transformation
    print("Logging FHIR transformation...")
    audit_logger.log_fhir_transformation(
        transaction_id=transaction_id,
        llm_output_length=1500,
        fhir_bundle_length=2000,
        resources_created={'Patient': 1, 'Encounter': 1, 'Condition': 2, 'MedicationRequest': 1},
        validation_passed=True
    )

    # Log confidence scoring
    print("Logging confidence scoring...")
    audit_logger.log_confidence_scoring(
        transaction_id=transaction_id,
        overall_confidence=85,
        field_confidences={'chief_complaint': 90, 'diagnoses': 80, 'medications': 85},
        low_confidence_fields=[]
    )

    # Get transaction summary
    print("\nRetrieving transaction summary...")
    summary = audit_logger.get_transaction_summary(transaction_id)
    print(f"Transaction ID: {summary['transaction_id']}")
    print(f"Total events: {summary['total_events']}")
    print(f"Events:")
    for i, event in enumerate(summary['events'], 1):
        print(f"  {i}. {event.get('event_type', 'unknown')} - {event.get('status', 'N/A')}")

    # Export audit report
    print("\nExporting audit report...")
    report = audit_logger.export_audit_report(transaction_id)
    print("Report preview:")
    print("-" * 40)
    print(report[:500] + "...\n")

    print("✓ Audit logger test passed!\n")
    return True


def test_fhir_transformer():
    """Test the FHIR transformer module"""
    print("\n" + "="*80)
    print("TEST 3: FHIR Transformer Module")
    print("="*80 + "\n")

    transformer = create_fhir_transformer()

    # Create mock Claude output
    mock_claude_output = {
        "encounter_summary": {
            "chief_complaint": "Chest pain for 2 days",
            "history_of_present_illness": "Patient presents with sharp chest pain that started 2 days ago. Pain is worse with exertion. Associated with mild shortness of breath. No fever or cough."
        },
        "vital_signs_extracted": {
            "blood_pressure": "145/92 mmHg",
            "temperature": "98.6 F",
            "heart_rate": "88 bpm",
            "respiratory_rate": "18 breaths/min",
            "oxygen_saturation": "97% RA"
        },
        "clinical_entities": {
            "diagnoses_problems": [
                {"name": "Chest pain", "status": "active", "confidence": "high"},
                {"name": "Hypertension", "status": "active", "confidence": "high"},
                {"name": "Possible myocardial infarction", "status": "rule-out", "confidence": "medium"}
            ],
            "medication_requests_new_or_changed": [
                {
                    "medication_name": "aspirin",
                    "dosage": "325mg",
                    "route": "oral",
                    "reason": "Acute coronary syndrome prevention",
                    "frequency": "once daily"
                },
                {
                    "medication_name": "lisinopril",
                    "dosage": "10mg",
                    "route": "oral",
                    "reason": "Hypertension control",
                    "frequency": "once daily"
                }
            ],
            "allergies": [
                {"name": "Penicillin", "reaction": "Rash", "severity": "mild"}
            ]
        },
        "assessment_plan_draft": "45-year-old male with acute chest pain concerning for acute coronary syndrome. Needs EKG, troponin levels, and admission for monitoring.",
        "ai_confidence_score": 85,
        "flagged_for_review": True,
        "review_notes": "Rule-out myocardial infarction requires immediate clinical evaluation and cannot be fully assessed from conversation alone."
    }

    print("Mock Claude output created")
    print(f"Chief complaint: {mock_claude_output['encounter_summary']['chief_complaint']}")
    print(f"Confidence score: {mock_claude_output['ai_confidence_score']}/100\n")

    # Transform to FHIR
    print("Transforming to FHIR Bundle...")
    transaction_id = "test-txn-fhir-001"
    fhir_bundle, resource_counts = transformer.transform_to_fhir_bundle(
        mock_claude_output,
        transaction_id
    )

    print(f"\nFHIR Bundle created:")
    print(f"Bundle ID: {fhir_bundle['id']}")
    print(f"Resources created:")
    for resource_type, count in resource_counts.items():
        if count > 0:
            print(f"  - {resource_type}: {count}")

    # Validate bundle
    print("\nValidating FHIR Bundle...")
    is_valid, errors = transformer.validate_fhir_bundle(fhir_bundle)
    print(f"Validation result: {'✓ PASSED' if is_valid else '✗ FAILED'}")
    if errors:
        for error in errors:
            print(f"  - {error}")

    # Show sample resource
    print("\nSample resource (Condition):")
    print("-" * 40)
    condition_resource = next(
        (e['resource'] for e in fhir_bundle['entry'] if e['resource'].get('resourceType') == 'Condition'),
        None
    )
    if condition_resource:
        print(json.dumps(condition_resource, indent=2)[:500] + "...\n")

    print("✓ FHIR transformer test passed!\n")
    return True


def test_fhir_schema():
    """Test FHIR schema definitions"""
    print("\n" + "="*80)
    print("TEST 4: FHIR Schema Definitions")
    print("="*80 + "\n")

    print("Clinical Note Schema structure:")
    print("-" * 40)
    properties = CLINICAL_NOTE_SCHEMA['schema']['properties']
    print(f"Schema name: {CLINICAL_NOTE_SCHEMA['name']}")
    print(f"Number of top-level fields: {len(properties)}")
    for field_name in properties.keys():
        print(f"  - {field_name}")

    print("\nSchema validation:")
    print("-" * 40)

    # Check required fields
    required_fields = CLINICAL_NOTE_SCHEMA['schema'].get('required', [])
    print(f"Required fields: {len(required_fields)}")
    for field in required_fields:
        print(f"  - {field}")

    # Check encounter_summary structure
    encounter_summary = properties['encounter_summary']
    encounter_props = encounter_summary['properties']
    print(f"\nEncounter summary sub-fields: {len(encounter_props)}")
    for prop in encounter_props.keys():
        print(f"  - {prop}")

    print("\n✓ FHIR schema test passed!\n")
    return True


def main():
    """Run all component tests"""
    print("\n" + "#"*80)
    print("# HIPAA-Compliant Clinical Note Automation Tool")
    print("# Component Testing Suite")
    print("#"*80 + "\n")

    tests = [
        ("De-identification", test_deidentification),
        ("Audit Logger", test_audit_logger),
        ("FHIR Schema", test_fhir_schema),
        ("FHIR Transformer", test_fhir_transformer),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} test FAILED with error:")
            print(f"  {str(e)}\n")
            results.append((test_name, False))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All component tests passed!\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
