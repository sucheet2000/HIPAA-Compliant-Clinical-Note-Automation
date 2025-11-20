"""
FHIR Schema Definitions
Defines the JSON schema structure for Claude API structured outputs
and FHIR resource creation
"""

# Clinical Note Schema - Output from Claude
CLINICAL_NOTE_SCHEMA = {
    "name": "ClinicalNote",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "encounter_summary": {
                "type": "object",
                "properties": {
                    "chief_complaint": {
                        "type": "string",
                        "description": "A single, concise sentence describing the main reason for visit"
                    },
                    "history_of_present_illness": {
                        "type": "string",
                        "description": "3-4 sentences summarizing the patient's clinical story"
                    }
                },
                "required": ["chief_complaint", "history_of_present_illness"]
            },
            "vital_signs_extracted": {
                "type": "object",
                "properties": {
                    "blood_pressure": {
                        "type": "string",
                        "description": "e.g., '120/80 mmHg' or 'N/A'"
                    },
                    "temperature": {
                        "type": "string",
                        "description": "e.g., '37.0 C' or 'N/A'"
                    },
                    "heart_rate": {
                        "type": "string",
                        "description": "e.g., '72 bpm' or 'N/A'"
                    },
                    "respiratory_rate": {
                        "type": "string",
                        "description": "e.g., '16 breaths/min' or 'N/A'"
                    },
                    "oxygen_saturation": {
                        "type": "string",
                        "description": "e.g., '98% RA' or 'N/A'"
                    }
                },
                "required": ["blood_pressure", "temperature", "heart_rate"]
            },
            "clinical_entities": {
                "type": "object",
                "properties": {
                    "diagnoses_problems": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "status": {
                                    "type": "string",
                                    "enum": ["active", "resolved", "rule-out"]
                                },
                                "confidence": {
                                    "type": "string",
                                    "enum": ["high", "medium", "low"]
                                }
                            },
                            "required": ["name", "status"]
                        }
                    },
                    "medication_requests_new_or_changed": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "medication_name": {"type": "string"},
                                "dosage": {
                                    "type": "string",
                                    "description": "e.g., '10mg daily'"
                                },
                                "route": {
                                    "type": "string",
                                    "description": "e.g., 'oral', 'IV', 'topical'"
                                },
                                "reason": {"type": "string"},
                                "frequency": {
                                    "type": "string",
                                    "description": "e.g., 'twice daily', 'as needed'"
                                }
                            },
                            "required": ["medication_name", "dosage", "route"]
                        }
                    },
                    "allergies": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Drug or substance name"
                                },
                                "reaction": {
                                    "type": "string",
                                    "description": "Type of allergic reaction"
                                },
                                "severity": {
                                    "type": "string",
                                    "enum": ["mild", "moderate", "severe"]
                                }
                            },
                            "required": ["name", "reaction"]
                        }
                    }
                },
                "required": ["diagnoses_problems", "medication_requests_new_or_changed", "allergies"]
            },
            "assessment_plan_draft": {
                "type": "string",
                "description": "Draft of physician's Assessment and Plan section"
            },
            "ai_confidence_score": {
                "type": "integer",
                "description": "Overall confidence score (1-100) for entity extraction"
            },
            "flagged_for_review": {
                "type": "boolean",
                "description": "Whether output should be reviewed by human clinician"
            },
            "review_notes": {
                "type": "string",
                "description": "Notes on why flagged for review if applicable"
            }
        },
        "required": [
            "encounter_summary",
            "vital_signs_extracted",
            "clinical_entities",
            "assessment_plan_draft",
            "ai_confidence_score",
            "flagged_for_review"
        ]
    }
}


# FHIR R4 Resource Schemas for Bundle Creation

FHIR_PATIENT_SCHEMA = {
    "resourceType": "Patient",
    "properties": {
        "id": {"type": "string"},
        "name": {
            "type": "array",
            "items": {
                "properties": {
                    "use": {"type": "string"},
                    "text": {"type": "string"}
                }
            }
        },
        "gender": {
            "type": "string",
            "enum": ["male", "female", "other", "unknown"]
        },
        "birthDate": {"type": "string", "format": "date"}
    }
}

FHIR_ENCOUNTER_SCHEMA = {
    "resourceType": "Encounter",
    "properties": {
        "id": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["planned", "arrived", "triaged", "in-progress", "on-leave", "finished", "cancelled"]
        },
        "class": {
            "type": "object",
            "properties": {
                "system": {"type": "string"},
                "code": {"type": "string"},
                "display": {"type": "string"}
            }
        },
        "type": {
            "type": "array",
            "items": {
                "properties": {
                    "coding": {
                        "type": "array",
                        "items": {
                            "properties": {
                                "system": {"type": "string"},
                                "code": {"type": "string"},
                                "display": {"type": "string"}
                            }
                        }
                    }
                }
            }
        },
        "subject": {
            "properties": {
                "reference": {"type": "string"}
            }
        },
        "period": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"}
            }
        },
        "reasonCode": {
            "type": "array",
            "items": {
                "properties": {
                    "coding": {
                        "type": "array",
                        "items": {
                            "properties": {
                                "system": {"type": "string"},
                                "code": {"type": "string"},
                                "display": {"type": "string"}
                            }
                        }
                    },
                    "text": {"type": "string"}
                }
            }
        }
    }
}

FHIR_CONDITION_SCHEMA = {
    "resourceType": "Condition",
    "properties": {
        "id": {"type": "string"},
        "clinicalStatus": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "properties": {
                            "system": {"type": "string"},
                            "code": {
                                "type": "string",
                                "enum": ["active", "recurrence", "relapse", "inactive", "remission", "resolved"]
                            }
                        }
                    }
                }
            }
        },
        "code": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"}
                        }
                    }
                },
                "text": {"type": "string"}
            }
        },
        "subject": {
            "properties": {
                "reference": {"type": "string"}
            }
        },
        "encounter": {
            "properties": {
                "reference": {"type": "string"}
            }
        },
        "onsetDateTime": {"type": "string", "format": "date-time"},
        "recordedDate": {"type": "string", "format": "date-time"}
    }
}

FHIR_MEDICATION_REQUEST_SCHEMA = {
    "resourceType": "MedicationRequest",
    "properties": {
        "id": {"type": "string"},
        "status": {
            "type": "string",
            "enum": ["active", "on-hold", "cancelled", "completed", "entered-in-error", "draft", "unknown"]
        },
        "intent": {
            "type": "string",
            "enum": ["proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"]
        },
        "medicationCodeableConcept": {
            "type": "object",
            "properties": {
                "coding": {
                    "type": "array",
                    "items": {
                        "properties": {
                            "system": {"type": "string"},
                            "code": {"type": "string"},
                            "display": {"type": "string"}
                        }
                    }
                },
                "text": {"type": "string"}
            }
        },
        "subject": {
            "properties": {
                "reference": {"type": "string"}
            }
        },
        "encounter": {
            "properties": {
                "reference": {"type": "string"}
            }
        },
        "authoredOn": {"type": "string", "format": "date-time"},
        "dosageInstruction": {
            "type": "array",
            "items": {
                "properties": {
                    "text": {"type": "string"},
                    "timing": {
                        "properties": {
                            "repeat": {
                                "properties": {
                                    "frequency": {"type": "integer"},
                                    "period": {"type": "number"},
                                    "periodUnit": {"type": "string"}
                                }
                            }
                        }
                    },
                    "route": {
                        "properties": {
                            "coding": {
                                "type": "array",
                                "items": {
                                    "properties": {
                                        "system": {"type": "string"},
                                        "code": {"type": "string"},
                                        "display": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "doseAndRate": {
                        "type": "array",
                        "items": {
                            "properties": {
                                "doseQuantity": {
                                    "properties": {
                                        "value": {"type": "number"},
                                        "unit": {"type": "string"},
                                        "system": {"type": "string"},
                                        "code": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "reasonCode": {
            "type": "array",
            "items": {
                "properties": {
                    "coding": {
                        "type": "array",
                        "items": {
                            "properties": {
                                "system": {"type": "string"},
                                "code": {"type": "string"},
                                "display": {"type": "string"}
                            }
                        }
                    },
                    "text": {"type": "string"}
                }
            }
        }
    }
}

FHIR_BUNDLE_SCHEMA = {
    "resourceType": "Bundle",
    "type": "collection",
    "properties": {
        "id": {"type": "string"},
        "timestamp": {"type": "string", "format": "date-time"},
        "entry": {
            "type": "array",
            "items": {
                "properties": {
                    "fullUrl": {"type": "string"},
                    "resource": {"type": "object"}
                }
            }
        }
    }
}

# Terminology mapping for common conditions and medications
CONDITION_CODE_MAP = {
    "high blood pressure": {"icd10": "I10", "snomed": "59621000"},
    "hypertension": {"icd10": "I10", "snomed": "59621000"},
    "diabetes": {"icd10": "E11.9", "snomed": "44054006"},
    "type 2 diabetes": {"icd10": "E11.9", "snomed": "44054006"},
    "heart failure": {"icd10": "I50", "snomed": "84114007"},
    "pneumonia": {"icd10": "J18.9", "snomed": "233604007"},
    "upper respiratory infection": {"icd10": "J06.9", "snomed": "54150009"},
    "anxiety": {"icd10": "F41.9", "snomed": "48694002"},
    "headache": {"icd10": "R51.9", "snomed": "25064002"},
    "chest pain": {"icd10": "R07.9", "snomed": "29650007"},
    "cough": {"icd10": "R05.9", "snomed": "13645005"},
    "fatigue": {"icd10": "R53.83", "snomed": "84216000"},
    "shortness of breath": {"icd10": "R06.02", "snomed": "25064002"},
    "neuropathy": {"icd10": "G89.29", "snomed": "386033004"},
    "edema": {"icd10": "R60.9", "snomed": "267038008"},
}

MEDICATION_CODE_MAP = {
    "aspirin": {"rxnorm": "1191", "snomed": "387458008"},
    "metformin": {"rxnorm": "6809", "snomed": "372567009"},
    "lisinopril": {"rxnorm": "21600", "snomed": "386876001"},
    "amlodipine": {"rxnorm": "17767", "snomed": "386929003"},
    "atorvastatin": {"rxnorm": "83367", "snomed": "412263009"},
    "sertraline": {"rxnorm": "36437", "snomed": "372588000"},
    "albuterol": {"rxnorm": "435", "snomed": "372897005"},
    "hydrochlorothiazide": {"rxnorm": "5487", "snomed": "366333007"},
    "atenolol": {"rxnorm": "733", "snomed": "372495000"},
    "acetaminophen": {"rxnorm": "161", "snomed": "372348007"},
    "ibuprofen": {"rxnorm": "5640", "snomed": "373025003"},
    "amoxicillin": {"rxnorm": "2230", "snomed": "372687004"},
    "glipizide": {"rxnorm": "4821", "snomed": "386228008"},
    "insulin": {"rxnorm": "5856", "snomed": "325072002"},
}

def get_terminology_code(term_name: str, term_type: str = "condition") -> dict:
    """
    Get terminology codes for a clinical term

    Args:
        term_name: The clinical term (e.g., "diabetes")
        term_type: Either "condition" or "medication"

    Returns:
        Dictionary with terminology codes
    """
    term_lower = term_name.lower().strip()

    if term_type == "condition":
        code_map = CONDITION_CODE_MAP
        default_system = "http://hl7.org/fhir/sid/icd-10"
    else:
        code_map = MEDICATION_CODE_MAP
        default_system = "http://www.nlm.nih.gov/research/umls/rxnorm"

    if term_lower in code_map:
        codes = code_map[term_lower]
        return {
            "found": True,
            "codes": codes,
            "display": term_name
        }

    # Return a generic unknown entry
    return {
        "found": False,
        "codes": {},
        "display": term_name
    }
