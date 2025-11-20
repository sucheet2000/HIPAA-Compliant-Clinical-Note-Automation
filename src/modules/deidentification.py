"""
De-identification Module for HIPAA Compliance
Masks Protected Health Information (PHI) before data is sent to LLM
"""

import re
from typing import Dict, List, Tuple
from datetime import datetime


class PHIRedactionList:
    """Defines all PHI categories to be redacted"""

    # Common patterns for PHI detection
    PHI_CATEGORIES = {
        'names': r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )?(?:Smith|Johnson|Williams|Brown|Jones|Garcia|Miller|Davis|Rodriguez|Martinez|Hernandez|Lopez|Gonzalez|Wilson|Anderson|Thomas|Taylor|Moore|Jackson|Martin|Lee|Perez|Thompson|White|Harris|Sanchez|Clark|Ramirez|Lewis|Robinson|Young|Strokes|King|Wright|Long|Chavez))\b',
        'dates': r'\b((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})\b',
        'mrn': r'\b(MRN|Record|ID)[\s:]*(\d{6,10})\b',
        'ssn': r'\b(\d{3}-\d{2}-\d{4})\b',
        'phone': r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
        'email': r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        'address_patterns': r'\b(\d+\s+(?:North|South|East|West|N|S|E|W)\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|Circle|Cir|Trail|Trl))\b',
        'age_specific': r'\b(\d{1,3}(?:\s+)?(?:year|yo|y\.o\.)-old)\b'
    }

    PLACEHOLDER_MAP = {
        'names': '[PATIENT_NAME]',
        'dates': '[DATE]',
        'mrn': '[MRN]',
        'ssn': '[SSN]',
        'phone': '[PHONE]',
        'email': '[EMAIL]',
        'address_patterns': '[ADDRESS]',
        'age_specific': '[AGE]'
    }


class DeIdentifier:
    """Handles de-identification and PHI masking"""

    def __init__(self):
        self.redaction_list = PHIRedactionList()
        self.redaction_audit = []

    def deidentify(self, raw_text: str) -> Tuple[str, Dict]:
        """
        Main de-identification function

        Args:
            raw_text: The raw clinical conversation text

        Returns:
            Tuple of (masked_text, redaction_audit)
        """
        masked_text = raw_text
        audit = {
            'timestamp': datetime.now().isoformat(),
            'original_length': len(raw_text),
            'redactions_by_type': {}
        }

        # Apply each PHI redaction rule
        for phi_type, pattern in self.redaction_list.PHI_CATEGORIES.items():
            matches = re.finditer(pattern, masked_text, re.IGNORECASE)
            redaction_count = 0

            for match in list(matches):
                placeholder = self.redaction_list.PLACEHOLDER_MAP[phi_type]
                masked_text = masked_text[:match.start()] + placeholder + masked_text[match.end():]
                redaction_count += 1

            if redaction_count > 0:
                audit['redactions_by_type'][phi_type] = redaction_count

        audit['masked_length'] = len(masked_text)
        audit['total_redactions'] = sum(audit['redactions_by_type'].values())

        return masked_text, audit

    def redact_names_advanced(self, text: str) -> str:
        """
        Advanced name detection using common clinical context patterns
        """
        # Match titles and names
        patterns = [
            r'\b(Dr\.?\s+[A-Z][a-z]+)',  # Dr. Smith
            r'\b(Mr\.?\s+[A-Z][a-z]+)',  # Mr. Johnson
            r'\b(Ms\.?\s+[A-Z][a-z]+)',  # Ms. Williams
            r'\b(Mrs\.?\s+[A-Z][a-z]+)',  # Mrs. Brown
            r"(patient'?s?\s+name|patient named|i'm\s+[A-Z][a-z]+)",  # "patient named John"
        ]

        for pattern in patterns:
            text = re.sub(pattern, '[PATIENT_NAME]', text, flags=re.IGNORECASE)

        return text

    def validate_deidentification(self, masked_text: str) -> Dict:
        """
        Validate that no PHI remains in the masked text

        Returns a validation report
        """
        validation_report = {
            'is_safe': True,
            'remaining_phi_risks': []
        }

        # Check for common PHI patterns that may have been missed
        checks = {
            'potential_names': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
            'potential_dates': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'potential_numbers': r'\b\d{6,10}\b(?!.*\[)',  # Numbers not in placeholders
        }

        for check_type, pattern in checks.items():
            matches = re.findall(pattern, masked_text)
            if matches:
                validation_report['is_safe'] = False
                validation_report['remaining_phi_risks'].append({
                    'type': check_type,
                    'count': len(matches),
                    'examples': matches[:3]  # First 3 examples
                })

        return validation_report


def create_deidentifier() -> DeIdentifier:
    """Factory function to create a DeIdentifier instance"""
    return DeIdentifier()
