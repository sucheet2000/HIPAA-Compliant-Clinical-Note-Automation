"""
Claude API Integration Module
Handles all interactions with Claude API for clinical note processing
Uses structured outputs for guaranteed JSON compliance
"""

import json
import logging
import os
import re
from typing import Any, Dict, Optional, Tuple

import anthropic

from .fhir_schemas import CLINICAL_NOTE_SCHEMA
from .audit_logger import AuditLogger

logger = logging.getLogger(__name__)


class ClaudeAPIWrapper:
    """
    Wrapper for Claude API calls with structured outputs.
    Ensures HIPAA-compliant processing and audit logging.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        """
        Initialise Claude API wrapper.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var).
            audit_logger: AuditLogger instance for compliance tracking.
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError('ANTHROPIC_API_KEY environment variable is not set')

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.audit_logger = audit_logger
        self.model = os.getenv('CLAUDE_MODEL', 'claude-sonnet-4-5-20250929')
        self.temperature = 0  # Deterministic output for clinical work

    def set_model(self, model: str) -> None:
        """Override the model used for API calls."""
        self.model = model

    # ------------------------------------------------------------------
    # Core processing
    # ------------------------------------------------------------------

    def process_clinical_conversation(
        self,
        masked_conversation: str,
        transaction_id: str,
        max_tokens: int = 2048,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Process a de-identified clinical conversation and extract structured data.

        Args:
            masked_conversation: The de-identified clinical conversation text.
            transaction_id: Unique transaction identifier for audit logging.
            max_tokens: Maximum tokens for the response.

        Returns:
            Tuple of (structured_output_dict, raw_response_text).
        """
        system_prompt = self._get_system_prompt()
        user_message = self._get_user_message(masked_conversation)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[{'role': 'user', 'content': user_message}],
            )

            response_text = response.content[0].text
            structured_output = self._parse_json_response(response_text)

            if self.audit_logger:
                self.audit_logger.log_claude_api_call(
                    transaction_id=transaction_id,
                    prompt_length=len(user_message),
                    response_length=len(response_text),
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    status='success',
                )

            return structured_output, response_text

        except (json.JSONDecodeError, RuntimeError) as exc:
            error_msg = f'JSON parsing error: {exc}'
            logger.error('Failed to parse Claude response for tx %s: %s', transaction_id, exc)
            self._log_failure(transaction_id, len(user_message), max_tokens, error_msg)
            raise RuntimeError(f'Failed to parse Claude response: {error_msg}') from exc

        except anthropic.APIError as exc:
            error_msg = f'API error: {exc}'
            logger.error('Claude API error for tx %s: %s', transaction_id, exc)
            self._log_failure(transaction_id, len(user_message), max_tokens, error_msg)
            raise RuntimeError(f'Claude API call failed: {error_msg}') from exc

    # ------------------------------------------------------------------
    # Schema validation
    # ------------------------------------------------------------------

    def validate_output_schema(
        self, output: Dict[str, Any]
    ) -> Tuple[bool, list]:
        """
        Validate that the Claude output matches the expected schema.
        Adds default values for missing fields to ensure robustness.

        Args:
            output: The parsed JSON output from Claude.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        required_fields = {
            'encounter_summary': {
                'chief_complaint': 'N/A',
                'history_of_present_illness': 'N/A',
            },
            'vital_signs_extracted': {
                'blood_pressure': 'N/A',
                'temperature': 'N/A',
                'heart_rate': 'N/A',
            },
            'clinical_entities': {
                'diagnoses_problems': [],
                'medication_requests_new_or_changed': [],
                'allergies': [],
            },
            'assessment_plan_draft': 'N/A',
            'ai_confidence_score': 50,
            'flagged_for_review': False,
        }

        errors: list = []
        warnings: list = []

        # Fill missing top-level fields with defaults
        for field, default_value in required_fields.items():
            if field not in output:
                output[field] = default_value
                warnings.append(f"Missing field '{field}': using default value")

        # Validate nested structures
        summary = output.get('encounter_summary')
        if not isinstance(summary, dict):
            errors.append('encounter_summary must be an object')
        elif 'chief_complaint' not in summary or 'history_of_present_illness' not in summary:
            errors.append('encounter_summary missing required subfields')

        entities = output.get('clinical_entities')
        if not isinstance(entities, dict):
            errors.append('clinical_entities must be an object')
        else:
            for list_field in (
                'diagnoses_problems',
                'medication_requests_new_or_changed',
                'allergies',
            ):
                if not isinstance(entities.get(list_field), list):
                    errors.append(f'{list_field} must be an array')

        score = output.get('ai_confidence_score')
        if not isinstance(score, (int, float)) or not (1 <= score <= 100):
            errors.append('ai_confidence_score must be a number between 1 and 100')

        if not isinstance(output.get('flagged_for_review'), bool):
            output['flagged_for_review'] = False

        is_valid = len(errors) == 0
        return is_valid, errors + warnings

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _get_system_prompt(self) -> str:
        return (
            'Extract clinical data from de-identified conversation. '
            'Output MUST be valid JSON.\n\n'
            'Rules:\n'
            '- NEVER include patient names, dates, or identifiers\n'
            '- Only extract explicitly stated facts\n'
            "- Use 'N/A' for missing fields\n"
            '- Return a JSON object with: encounter_summary, vital_signs_extracted, '
            'clinical_entities, assessment_plan_draft, ai_confidence_score, flagged_for_review'
        )

    def _get_user_message(self, masked_conversation: str) -> str:
        return (
            'Extract JSON from this clinical conversation (de-identified):\n\n'
            f'{masked_conversation}\n\n'
            'Return JSON with:\n'
            '- encounter_summary: {chief_complaint, history_of_present_illness}\n'
            '- vital_signs_extracted: {blood_pressure, temperature, heart_rate}\n'
            '- clinical_entities: {diagnoses_problems[], medication_requests_new_or_changed[], allergies[]}\n'
            '- assessment_plan_draft: string\n'
            '- ai_confidence_score: 1-100\n'
            '- flagged_for_review: boolean\n\n'
            'Only extract stated facts.'
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(response_text: str) -> Dict[str, Any]:
        """
        Parse a JSON response from Claude using multiple fallback strategies.

        Args:
            response_text: Raw text returned by the model.

        Returns:
            Parsed JSON dict.

        Raises:
            RuntimeError: If all parsing strategies fail.
        """
        json_text = response_text.strip()

        # Strip markdown code fences if present
        if '```json' in json_text:
            json_text = json_text.split('```json')[1].split('```')[0].strip()
        elif '```' in json_text:
            json_text = json_text.split('```')[1].split('```')[0].strip()

        last_error: Optional[Exception] = None

        # Strategy 1: direct parse
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as exc:
            last_error = exc

        # Strategy 2: extract first {...} block
        start = json_text.find('{')
        end = json_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(json_text[start: end + 1])
            except json.JSONDecodeError as exc:
                last_error = exc

        # Strategy 3: escape bare newlines / carriage returns
        try:
            fixed = json_text.replace('\n', '\\n').replace('\r', '\\r')
            return json.loads(fixed)
        except json.JSONDecodeError as exc:
            last_error = exc

        raise RuntimeError(
            f'Could not parse Claude response as JSON: {last_error}'
        )

    def _log_failure(
        self,
        transaction_id: str,
        prompt_length: int,
        max_tokens: int,
        error_message: str,
    ) -> None:
        if self.audit_logger:
            self.audit_logger.log_claude_api_call(
                transaction_id=transaction_id,
                prompt_length=prompt_length,
                response_length=0,
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                status='failure',
                error_message=error_message,
            )


def create_claude_api_wrapper(
    api_key: Optional[str] = None,
    audit_logger: Optional[AuditLogger] = None,
) -> ClaudeAPIWrapper:
    """Factory function to create a ClaudeAPIWrapper instance."""
    return ClaudeAPIWrapper(api_key=api_key, audit_logger=audit_logger)
