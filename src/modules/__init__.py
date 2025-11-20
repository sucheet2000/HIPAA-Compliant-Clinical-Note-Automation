"""
HIPAA-Compliant Clinical Note Automation Tool Modules
"""

from .deidentification import create_deidentifier, DeIdentifier, PHIRedactionList
from .audit_logger import create_audit_logger, AuditLogger
from .claude_api import create_claude_api_wrapper, ClaudeAPIWrapper
from .fhir_transformer import create_fhir_transformer, FHIRTransformer
from .fhir_schemas import (
    CLINICAL_NOTE_SCHEMA,
    FHIR_PATIENT_SCHEMA,
    FHIR_ENCOUNTER_SCHEMA,
    FHIR_CONDITION_SCHEMA,
    FHIR_MEDICATION_REQUEST_SCHEMA,
    FHIR_BUNDLE_SCHEMA,
    get_terminology_code
)

__all__ = [
    'create_deidentifier',
    'DeIdentifier',
    'PHIRedactionList',
    'create_audit_logger',
    'AuditLogger',
    'create_claude_api_wrapper',
    'ClaudeAPIWrapper',
    'create_fhir_transformer',
    'FHIRTransformer',
    'CLINICAL_NOTE_SCHEMA',
    'FHIR_PATIENT_SCHEMA',
    'FHIR_ENCOUNTER_SCHEMA',
    'FHIR_CONDITION_SCHEMA',
    'FHIR_MEDICATION_REQUEST_SCHEMA',
    'FHIR_BUNDLE_SCHEMA',
    'get_terminology_code'
]
