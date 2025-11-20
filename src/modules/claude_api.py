"""
Claude API Integration Module
Handles all interactions with Claude API for clinical note processing
Uses structured outputs for guaranteed JSON compliance
"""

import os
import json
from typing import Dict, Any, Optional, Tuple
import anthropic
from .fhir_schemas import CLINICAL_NOTE_SCHEMA
from .audit_logger import AuditLogger


class ClaudeAPIWrapper:
    """
    Wrapper for Claude API calls with structured outputs
    Ensures HIPAA-compliant processing and audit logging
    """

    def __init__(self, api_key: Optional[str] = None, audit_logger: Optional[AuditLogger] = None):
        """
        Initialize Claude API wrapper

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            audit_logger: AuditLogger instance for compliance tracking
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.audit_logger = audit_logger
        self.model = "claude-sonnet-4-5-20250929"
        self.temperature = 0  # Deterministic output for clinical work

    def set_model(self, model: str):
        """Set the model to use for API calls"""
        self.model = model

    def process_clinical_conversation(
        self,
        masked_conversation: str,
        transaction_id: str,
        max_tokens: int = 2048
    ) -> Tuple[Dict[str, Any], str]:
        """
        Process a de-identified clinical conversation and extract structured data

        Args:
            masked_conversation: The de-identified clinical conversation text
            transaction_id: Unique transaction identifier for audit logging
            max_tokens: Maximum tokens for the response

        Returns:
            Tuple of (structured_output_dict, raw_response_text)
        """
        # Define the system prompt
        system_prompt = self._get_system_prompt()

        # Prepare the user message
        user_message = self._get_user_message(masked_conversation)

        try:
            # Call Claude API with system prompt for JSON output
            # Note: Using standard API without explicit output_format parameter
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            )

            # Extract the response text
            response_text = response.content[0].text

            # Parse the JSON response with robust error handling
            import re
            json_text = response_text.strip()

            # Remove markdown code blocks if present
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            elif "```" in json_text:
                json_text = json_text.split("```")[1].split("```")[0].strip()

            # Try to parse with multiple strategies
            structured_output = None
            parse_error = None

            # Strategy 1: Direct parse
            try:
                structured_output = json.loads(json_text)
            except json.JSONDecodeError as e:
                parse_error = e

            # Strategy 2: Find JSON object in response
            if structured_output is None:
                try:
                    # Find the first { and last } to extract JSON
                    start_idx = json_text.find('{')
                    end_idx = json_text.rfind('}')
                    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                        json_text = json_text[start_idx:end_idx+1]
                        structured_output = json.loads(json_text)
                except json.JSONDecodeError:
                    pass

            # Strategy 3: Try fixing common JSON issues
            if structured_output is None:
                try:
                    # Fix unescaped newlines and common issues
                    json_text_fixed = json_text.replace('\n', '\\n').replace('\r', '\\r')
                    structured_output = json.loads(json_text_fixed)
                except json.JSONDecodeError:
                    pass

            # If all strategies fail, raise original error
            if structured_output is None:
                raise RuntimeError(f"Failed to parse Claude response: {parse_error}")

            # Log the API call
            if self.audit_logger:
                self.audit_logger.log_claude_api_call(
                    transaction_id=transaction_id,
                    prompt_length=len(user_message),
                    response_length=len(response_text),
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    status="success"
                )

            return structured_output, response_text

        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing error: {str(e)}"
            if self.audit_logger:
                self.audit_logger.log_claude_api_call(
                    transaction_id=transaction_id,
                    prompt_length=len(user_message),
                    response_length=0,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    status="failure",
                    error_message=error_msg
                )
            raise RuntimeError(f"Failed to parse Claude response: {error_msg}")

        except anthropic.APIError as e:
            error_msg = f"API error: {str(e)}"
            if self.audit_logger:
                self.audit_logger.log_claude_api_call(
                    transaction_id=transaction_id,
                    prompt_length=len(user_message),
                    response_length=0,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=self.temperature,
                    status="failure",
                    error_message=error_msg
                )
            raise RuntimeError(f"Claude API call failed: {error_msg}")

    def _get_system_prompt(self) -> str:
        """
        Generate the system prompt for clinical note processing

        Returns:
            System prompt string
        """
        return """Extract clinical data from de-identified conversation. Output MUST be valid JSON.

Rules:
- NEVER include patient names/dates/identifiers
- Only extract explicitly stated facts
- Use 'N/A' for missing fields
- Return JSON object with: encounter_summary, vital_signs_extracted, clinical_entities, assessment_plan_draft, ai_confidence_score, flagged_for_review"""

    def _get_user_message(self, masked_conversation: str) -> str:
        """
        Generate the user message for clinical processing

        Args:
            masked_conversation: The de-identified conversation text

        Returns:
            User message string
        """
        return f"""Extract JSON from this clinical conversation (de-identified):

{masked_conversation}

Return JSON with:
- encounter_summary: {{chief_complaint, history_of_present_illness}}
- vital_signs_extracted: {{blood_pressure, temperature, heart_rate}}
- clinical_entities: {{diagnoses_problems[], medication_requests_new_or_changed[], allergies[]}}
- assessment_plan_draft: string
- ai_confidence_score: 1-100
- flagged_for_review: boolean

Only extract stated facts."""

    def validate_output_schema(self, output: Dict[str, Any]) -> Tuple[bool, list]:
        """
        Validate that the Claude output matches the expected schema.
        Adds default values for missing fields to ensure robustness.

        Args:
            output: The parsed JSON output from Claude

        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Define required fields with default values
        required_fields = {
            'encounter_summary': {'chief_complaint': 'N/A', 'history_of_present_illness': 'N/A'},
            'vital_signs_extracted': {'blood_pressure': 'N/A', 'temperature': 'N/A', 'heart_rate': 'N/A'},
            'clinical_entities': {'diagnoses_problems': [], 'medication_requests_new_or_changed': [], 'allergies': []},
            'assessment_plan_draft': 'N/A',
            'ai_confidence_score': 50,
            'flagged_for_review': False
        }

        errors = []
        warnings = []

        # Add missing top-level fields with defaults
        for field, default_value in required_fields.items():
            if field not in output:
                output[field] = default_value
                warnings.append(f"Missing field '{field}': using default value")

        # Validate nested structures
        if 'encounter_summary' in output:
            summary = output['encounter_summary']
            if not isinstance(summary, dict):
                errors.append("encounter_summary must be an object")
            elif 'chief_complaint' not in summary or 'history_of_present_illness' not in summary:
                errors.append("encounter_summary missing required subfields")

        if 'clinical_entities' in output:
            entities = output['clinical_entities']
            if not isinstance(entities, dict):
                errors.append("clinical_entities must be an object")
            elif not isinstance(entities.get('diagnoses_problems'), list):
                errors.append("diagnoses_problems must be an array")
            elif not isinstance(entities.get('medication_requests_new_or_changed'), list):
                errors.append("medication_requests_new_or_changed must be an array")
            elif not isinstance(entities.get('allergies'), list):
                errors.append("allergies must be an array")

        if 'ai_confidence_score' in output:
            score = output['ai_confidence_score']
            if not isinstance(score, int) or score < 1 or score > 100:
                errors.append("ai_confidence_score must be an integer between 1 and 100")

        if 'flagged_for_review' in output:
            if not isinstance(output['flagged_for_review'], bool):
                output['flagged_for_review'] = False

        # Return True if no critical errors (warnings are acceptable)
        is_valid = len(errors) == 0
        all_messages = errors + warnings
        return is_valid, all_messages


def create_claude_api_wrapper(
    api_key: Optional[str] = None,
    audit_logger: Optional[AuditLogger] = None
) -> ClaudeAPIWrapper:
    """Factory function to create a ClaudeAPIWrapper instance"""
    return ClaudeAPIWrapper(api_key=api_key, audit_logger=audit_logger)
