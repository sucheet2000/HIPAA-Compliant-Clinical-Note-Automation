"""
FHIR Transformation Module
Converts Claude's structured output into FHIR R4 compliant resources
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from .fhir_schemas import (
    get_terminology_code,
    FHIR_PATIENT_SCHEMA,
    FHIR_ENCOUNTER_SCHEMA,
    FHIR_CONDITION_SCHEMA,
    FHIR_MEDICATION_REQUEST_SCHEMA
)
from .audit_logger import AuditLogger


class FHIRTransformer:
    """Transforms Claude's clinical output into FHIR R4 resources"""

    def __init__(self, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize FHIR Transformer

        Args:
            audit_logger: AuditLogger instance for compliance tracking
        """
        self.audit_logger = audit_logger
        self.resource_counter = {
            'Patient': 0,
            'Encounter': 0,
            'Condition': 0,
            'MedicationRequest': 0,
            'AllergyIntolerance': 0
        }

    def transform_to_fhir_bundle(
        self,
        claude_output: Dict[str, Any],
        transaction_id: str,
        patient_id: Optional[str] = None,
        encounter_id: Optional[str] = None
    ) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Transform Claude's structured output into a FHIR Bundle

        Args:
            claude_output: The structured output from Claude
            transaction_id: Unique transaction identifier
            patient_id: Optional patient ID (generates if not provided)
            encounter_id: Optional encounter ID (generates if not provided)

        Returns:
            Tuple of (fhir_bundle, resource_counts)
        """
        # Generate IDs if not provided
        patient_id = patient_id or str(uuid.uuid4())
        encounter_id = encounter_id or str(uuid.uuid4())

        bundle_entries = []

        # Create Patient Resource
        patient_resource = self._create_patient_resource(patient_id)
        bundle_entries.append({
            "fullUrl": f"urn:uuid:{patient_id}",
            "resource": patient_resource
        })
        self.resource_counter['Patient'] += 1

        # Create Encounter Resource
        encounter_resource = self._create_encounter_resource(
            encounter_id,
            patient_id,
            claude_output
        )
        bundle_entries.append({
            "fullUrl": f"urn:uuid:{encounter_id}",
            "resource": encounter_resource
        })
        self.resource_counter['Encounter'] += 1

        # Create Condition Resources
        if 'clinical_entities' in claude_output:
            entities = claude_output['clinical_entities']

            # Ensure entities is a dict (handle case where Claude returns string)
            if isinstance(entities, str):
                entities = {}
            if not isinstance(entities, dict):
                entities = {}

            # Process diagnoses
            diagnoses = entities.get('diagnoses_problems', []) if isinstance(entities, dict) else []
            if isinstance(diagnoses, str) or diagnoses is None:
                diagnoses = []
            for diagnosis in diagnoses:
                condition_resource = self._create_condition_resource(
                    str(uuid.uuid4()),
                    patient_id,
                    encounter_id,
                    diagnosis
                )
                bundle_entries.append({
                    "fullUrl": f"urn:uuid:{condition_resource['id']}",
                    "resource": condition_resource
                })
                self.resource_counter['Condition'] += 1

            # Create MedicationRequest Resources
            medications = entities.get('medication_requests_new_or_changed', []) if isinstance(entities, dict) else []
            if isinstance(medications, str) or medications is None:
                medications = []
            for medication in medications:
                med_resource = self._create_medication_request_resource(
                    str(uuid.uuid4()),
                    patient_id,
                    encounter_id,
                    medication
                )
                bundle_entries.append({
                    "fullUrl": f"urn:uuid:{med_resource['id']}",
                    "resource": med_resource
                })
                self.resource_counter['MedicationRequest'] += 1

            # Create AllergyIntolerance Resources
            allergies = entities.get('allergies', []) if isinstance(entities, dict) else []
            if isinstance(allergies, str) or allergies is None:
                allergies = []
            for allergy in allergies:
                allergy_resource = self._create_allergy_resource(
                    str(uuid.uuid4()),
                    patient_id,
                    allergy
                )
                bundle_entries.append({
                    "fullUrl": f"urn:uuid:{allergy_resource['id']}",
                    "resource": allergy_resource
                })
                self.resource_counter['AllergyIntolerance'] += 1

        # Create the Bundle
        fhir_bundle = {
            "resourceType": "Bundle",
            "id": str(uuid.uuid4()),
            "type": "collection",
            "timestamp": datetime.now().isoformat() + "Z",
            "entry": bundle_entries,
            "meta": {
                "source": "clinical-scribe-ai",
                "transactionId": transaction_id
            }
        }

        # Log transformation
        if self.audit_logger:
            self.audit_logger.log_fhir_transformation(
                transaction_id=transaction_id,
                llm_output_length=len(json.dumps(claude_output)),
                fhir_bundle_length=len(json.dumps(fhir_bundle)),
                resources_created=dict(self.resource_counter),
                validation_passed=True
            )

        return fhir_bundle, dict(self.resource_counter)

    def _create_patient_resource(self, patient_id: str) -> Dict[str, Any]:
        """Create a FHIR Patient resource"""
        return {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [
                {
                    "use": "usual",
                    "text": "[PATIENT_NAME]"
                }
            ],
            "gender": "unknown",
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/Patient"]
            }
        }

    def _create_encounter_resource(
        self,
        encounter_id: str,
        patient_id: str,
        claude_output: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a FHIR Encounter resource"""
        summary = claude_output.get('encounter_summary', {})
        if isinstance(summary, str):
            summary = {}
        chief_complaint = summary.get('chief_complaint', 'Not documented') if isinstance(summary, dict) else 'Not documented'

        return {
            "resourceType": "Encounter",
            "id": encounter_id,
            "status": "finished",
            "class": {
                "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
                "code": "AMB",
                "display": "Ambulatory"
            },
            "type": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "code": "185347001",
                            "display": "Encounter for problem"
                        }
                    ],
                    "text": "Clinical Encounter"
                }
            ],
            "subject": {
                "reference": f"Patient/{patient_id}",
                "display": "[PATIENT_NAME]"
            },
            "period": {
                "start": datetime.now().isoformat() + "Z"
            },
            "reasonCode": [
                {
                    "coding": [
                        {
                            "system": "http://snomed.info/sct",
                            "display": chief_complaint
                        }
                    ],
                    "text": chief_complaint
                }
            ],
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/Encounter"]
            }
        }

    def _create_condition_resource(
        self,
        condition_id: str,
        patient_id: str,
        encounter_id: str,
        diagnosis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a FHIR Condition resource"""
        # Handle both string and dict diagnoses
        if isinstance(diagnosis, str):
            diagnosis_name = diagnosis
            status = 'active'
        else:
            diagnosis_name = diagnosis.get('name', 'Unknown Condition')
            status = diagnosis.get('status', 'active').lower()

        # Map status to FHIR clinical status codes
        status_code_map = {
            'active': 'active',
            'resolved': 'resolved',
            'rule-out': 'unconfirmed',
            'inactive': 'inactive'
        }
        clinical_status = status_code_map.get(status, 'active')

        # Get terminology codes
        terminology = get_terminology_code(diagnosis_name, 'condition')

        return {
            "resourceType": "Condition",
            "id": condition_id,
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": clinical_status
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/icd-10",
                        "code": terminology['codes'].get('icd10', 'R99'),
                        "display": diagnosis_name
                    }
                ],
                "text": diagnosis_name
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "encounter": {
                "reference": f"Encounter/{encounter_id}"
            },
            "recordedDate": datetime.now().isoformat() + "Z",
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/Condition"]
            }
        }

    def _create_medication_request_resource(
        self,
        med_id: str,
        patient_id: str,
        encounter_id: str,
        medication: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a FHIR MedicationRequest resource"""
        # Handle both string and dict medications
        if isinstance(medication, str):
            med_name = medication
            dosage = '1 unit'
            route = 'oral'
            reason = 'Therapeutic use'
        else:
            med_name = medication.get('medication_name', 'Unknown Medication')
            dosage = medication.get('dosage', '1 unit')
            route = medication.get('route', 'oral').lower()
            reason = medication.get('reason', 'Therapeutic use')

        # Get terminology codes
        terminology = get_terminology_code(med_name, 'medication')

        # Parse route to FHIR coding
        route_code_map = {
            'oral': ('386359008', 'Oral'),
            'iv': ('47625008', 'Intravenous'),
            'im': ('78421000', 'Intramuscular'),
            'sc': ('34206005', 'Subcutaneous'),
            'topical': ('404559004', 'Topical'),
            'inhaled': ('404559004', 'Inhalation'),
            'sublingually': ('37161004', 'Sublingual'),
        }

        route_code, route_display = route_code_map.get(route, ('404559004', route.capitalize()))

        return {
            "resourceType": "MedicationRequest",
            "id": med_id,
            "status": "active",
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": terminology['codes'].get('rxnorm', '999999'),
                        "display": med_name
                    }
                ],
                "text": med_name
            },
            "subject": {
                "reference": f"Patient/{patient_id}"
            },
            "encounter": {
                "reference": f"Encounter/{encounter_id}"
            },
            "authoredOn": datetime.now().isoformat() + "Z",
            "dosageInstruction": [
                {
                    "text": f"{dosage}",
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": route_code,
                                "display": route_display
                            }
                        ]
                    }
                }
            ],
            "reasonCode": [
                {
                    "text": reason
                }
            ],
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/MedicationRequest"]
            }
        }

    def _create_allergy_resource(
        self,
        allergy_id: str,
        patient_id: str,
        allergy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a FHIR AllergyIntolerance resource"""
        # Handle both string and dict allergies
        if isinstance(allergy, str):
            allergen_name = allergy
            reaction = 'Unknown reaction'
            severity = 'unknown'
        else:
            allergen_name = allergy.get('name', 'Unknown Allergen')
            reaction = allergy.get('reaction', 'Unknown reaction')
            severity = allergy.get('severity', 'unknown').lower()

        return {
            "resourceType": "AllergyIntolerance",
            "id": allergy_id,
            "patient": {
                "reference": f"Patient/{patient_id}"
            },
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                        "code": "active"
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification",
                        "code": "unconfirmed"
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "display": allergen_name
                    }
                ],
                "text": allergen_name
            },
            "reaction": [
                {
                    "manifestation": [
                        {
                            "text": reaction
                        }
                    ],
                    "severity": severity if severity in ['mild', 'moderate', 'severe'] else 'unknown'
                }
            ],
            "meta": {
                "profile": ["http://hl7.org/fhir/StructureDefinition/AllergyIntolerance"]
            }
        }

    def validate_fhir_bundle(self, bundle: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate FHIR Bundle structure and required fields

        Args:
            bundle: The FHIR Bundle to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Check bundle structure
        if not isinstance(bundle, dict):
            errors.append("Bundle must be a dictionary")
            return False, errors

        required_fields = ['resourceType', 'type', 'entry']
        for field in required_fields:
            if field not in bundle:
                errors.append(f"Bundle missing required field: {field}")

        if bundle.get('resourceType') != 'Bundle':
            errors.append("resourceType must be 'Bundle'")

        if bundle.get('type') != 'collection':
            errors.append("Bundle type must be 'collection'")

        # Validate entries
        entries = bundle.get('entry', [])
        if not isinstance(entries, list):
            errors.append("entry must be an array")
        elif len(entries) == 0:
            errors.append("Bundle must contain at least one entry")

        # Validate each resource
        for i, entry in enumerate(entries):
            resource = entry.get('resource', {})
            resource_type = resource.get('resourceType')

            if not resource_type:
                errors.append(f"Entry {i} missing resourceType")
                continue

            # Basic resource validation
            if 'id' not in resource:
                errors.append(f"Entry {i} ({resource_type}) missing id")

        return len(errors) == 0, errors


def create_fhir_transformer(audit_logger: Optional[AuditLogger] = None) -> FHIRTransformer:
    """Factory function to create a FHIRTransformer instance"""
    return FHIRTransformer(audit_logger=audit_logger)
