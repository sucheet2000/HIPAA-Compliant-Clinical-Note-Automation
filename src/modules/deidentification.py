"""
De-identification Module for HIPAA Compliance
Masks Protected Health Information (PHI) before data is sent to LLM
"""

import re
from typing import Dict, List, Tuple
from datetime import datetime


class PHIRedactionList:
    """Defines all PHI categories to be redacted."""

    PHI_CATEGORIES = {
        'names': (
            r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )?(?:Smith|Johnson|Williams|Brown|Jones|Garcia|'
            r'Miller|Davis|Rodriguez|Martinez|Hernandez|Lopez|Gonzalez|Wilson|Anderson|Thomas|'
            r'Taylor|Moore|Jackson|Martin|Lee|Perez|Thompson|White|Harris|Sanchez|Clark|Ramirez|'
            r'Lewis|Robinson|Young|Strokes|King|Wright|Long|Chavez))\b'
        ),
        'dates': (
            r'\b((?:January|February|March|April|May|June|July|August|September|October|November|'
            r'December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}'
            r'(?:st|nd|rd|th)?(?:\s+\d{4})?|\d{1,2}/\d{1,2}/\d{2,4})\b'
        ),
        'mrn': r'\b(MRN|Record|ID)[\s:]*(\d{6,10})\b',
        'ssn': r'\b(\d{3}-\d{2}-\d{4})\b',
        'phone': r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})',
        'email': r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        'address_patterns': (
            r'\b(\d+\s+(?:North|South|East|West|N|S|E|W)\s+[A-Za-z\s]+'
            r'(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Boulevard|Blvd|Court|Ct|'
            r'Circle|Cir|Trail|Trl))\b'
        ),
        'age_specific': r'\b(\d{1,3}(?:\s+)?(?:year|yo|y\.o\.)-old)\b',
    }

    # Title-prefixed name patterns applied before the main PHI sweep
    TITLE_NAME_PATTERNS: List[str] = [
        r'\bDr\.?\s+[A-Z][a-z]+\b',
        r'\bMr\.?\s+[A-Z][a-z]+\b',
        r'\bMs\.?\s+[A-Z][a-z]+\b',
        r'\bMrs\.?\s+[A-Z][a-z]+\b',
        r"patient(?:'s)?\s+name\s+is\s+[A-Z][a-z]+",
        r'patient named\s+[A-Z][a-z]+',
        r"i'?m\s+[A-Z][a-z]+\b",
    ]

    PLACEHOLDER_MAP = {
        'names': '[PATIENT_NAME]',
        'dates': '[DATE]',
        'mrn': '[MRN]',
        'ssn': '[SSN]',
        'phone': '[PHONE]',
        'email': '[EMAIL]',
        'address_patterns': '[ADDRESS]',
        'age_specific': '[AGE]',
    }


class DeIdentifier:
    """Handles de-identification and PHI masking."""

    def __init__(self):
        self.redaction_list = PHIRedactionList()
        # Pre-compile all patterns once at construction time
        self._compiled: Dict[str, re.Pattern] = {
            phi_type: re.compile(pattern, re.IGNORECASE)
            for phi_type, pattern in self.redaction_list.PHI_CATEGORIES.items()
        }
        self._compiled_title_names: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE)
            for p in self.redaction_list.TITLE_NAME_PATTERNS
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def deidentify(self, raw_text: str) -> Tuple[str, Dict]:
        """
        Main de-identification function.

        Uses re.sub for every substitution to avoid the stale-index bug
        that occurs when text is sliced inside a match-iteration loop
        (where replacing one match shifts the offsets of all subsequent
        matches that were found on the original string).

        Args:
            raw_text: The raw clinical conversation text.

        Returns:
            Tuple of (masked_text, redaction_audit)
        """
        masked_text = raw_text
        audit: Dict = {
            'timestamp': datetime.now().isoformat(),
            'original_length': len(raw_text),
            'redactions_by_type': {},
        }

        # Pass 1 — title-based names (Dr./Mr./Ms./Mrs. + clinical context phrases)
        masked_text, title_count = self._redact_title_names(masked_text)
        if title_count:
            audit['redactions_by_type']['title_names'] = title_count

        # Pass 2 — all PHI category patterns
        for phi_type, compiled_pattern in self._compiled.items():
            placeholder = self.redaction_list.PLACEHOLDER_MAP[phi_type]
            masked_text, count = self._sub_count(compiled_pattern, placeholder, masked_text)
            if count > 0:
                audit['redactions_by_type'][phi_type] = count

        audit['masked_length'] = len(masked_text)
        audit['total_redactions'] = sum(audit['redactions_by_type'].values())
        return masked_text, audit

    def validate_deidentification(self, masked_text: str) -> Dict:
        """
        Validate that no obvious PHI remains in the masked text.

        Returns:
            Dict with 'is_safe' bool and 'remaining_phi_risks' list.
        """
        validation_report: Dict = {
            'is_safe': True,
            'remaining_phi_risks': [],
        }

        checks = {
            'potential_names': re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),
            'potential_dates': re.compile(r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
            # Long digit sequences that are NOT inside a placeholder bracket
            'potential_numbers': re.compile(r'(?<!\[)\b\d{6,10}\b(?!\])'),
        }

        for check_type, pattern in checks.items():
            matches = pattern.findall(masked_text)
            if matches:
                validation_report['is_safe'] = False
                validation_report['remaining_phi_risks'].append({
                    'type': check_type,
                    'count': len(matches),
                    'examples': matches[:3],
                })

        return validation_report

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _redact_title_names(self, text: str) -> Tuple[str, int]:
        """Apply title-name patterns and return (new_text, count)."""
        total = 0
        for pattern in self._compiled_title_names:
            text, n = self._sub_count(pattern, '[PATIENT_NAME]', text)
            total += n
        return text, total

    @staticmethod
    def _sub_count(
        pattern: re.Pattern, replacement: str, text: str
    ) -> Tuple[str, int]:
        """
        Apply *pattern* with re.sub and return (new_text, substitution_count).

        Key fix: re.sub processes all matches on the *original* string in a
        single pass, so offsets are always correct — unlike the previous
        approach of mutating the string inside a re.finditer loop.
        """
        count = 0

        def _replacer(_match):
            nonlocal count
            count += 1
            return replacement

        new_text = pattern.sub(_replacer, text)
        return new_text, count


def create_deidentifier() -> DeIdentifier:
    """Factory function to create a DeIdentifier instance."""
    return DeIdentifier()
