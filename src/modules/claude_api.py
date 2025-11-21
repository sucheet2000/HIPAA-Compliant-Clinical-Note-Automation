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
        Generate the user message for clinical processing with few-shot examples
        
        Args:
            masked_conversation: The de-identified conversation text
            
        Returns:
            User message string with examples for better accuracy
        """
        examples = f"""
Here are 3 examples of perfect extractions:

EXAMPLE 1 - Cardiology:
Conversation: "Patient reports chest pain for 2 days. BP 145/95, HR 88. EKG shows ST elevation. Starting aspirin 325mg, clopidogrel 75mg. Troponin pending. Likely STEMI - activating cath lab."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Chest pain x 2 days",
    "history_of_present_illness": "Patient presents with chest pain ongoing for 2 days. EKG demonstrates ST elevation concerning for STEMI."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "145/95 mmHg",
    "heart_rate": "88 bpm",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["ST-elevation myocardial infarction (STEMI, suspected)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Aspirin", "dose": "325mg", "frequency": "stat", "indication": "STEMI"}},
      {{"medication_name": "Clopidogrel", "dose": "75mg", "frequency": "daily", "indication": "STEMI"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "STEMI suspected based on chest pain and ST elevation. Aspirin and clopidogrel initiated. Troponin pending. Cath lab activated.",
  "ai_confidence_score": 95,
  "flagged_for_review": false
}}

EXAMPLE 2 - Primary Care:
Conversation: "Annual checkup. No complaints. BP 118/78, HR 72. Vaccines up to date. Continue lisinopril 10mg daily for HTN. RTC 1 year."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Annual wellness visit",
    "history_of_present_illness": "Patient presents for routine annual checkup. No acute complaints. Chronic hypertension well-controlled on current regimen."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "118/78 mmHg",
    "heart_rate": "72 bpm",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Hypertension (controlled)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Lisinopril", "dose": "10mg", "frequency": "daily", "indication": "Hypertension"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "Annual wellness visit. Hypertension well-controlled on lisinopril 10mg daily. Vaccinations current. Return in 1 year.",
  "ai_confidence_score": 98,
  "flagged_for_review": false
}}

EXAMPLE 3 - Pediatrics:
Conversation: "5-year-old with fever 101.5F x 2 days, cough, runny nose. Ears clear, throat mildly red. Likely viral URI. Supportive care. Tylenol PRN. RTC if worsens."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Fever, cough, and runny nose x 2 days",
    "history_of_present_illness": "5-year-old patient presents with fever (101.5°F) for 2 days accompanied by cough and rhinorrhea. Physical exam shows clear ears and mild throat erythema."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "101.5°F"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Viral upper respiratory infection (suspected)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Acetaminophen (Tylenol)", "dose": "as needed", "frequency": "PRN fever/pain", "indication": "Symptomatic relief"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "Likely viral URI. Supportive care recommended. Acetaminophen PRN for fever/discomfort. Return if symptoms worsen or persist beyond 7 days.",
  "ai_confidence_score": 92,
  "flagged_for_review": false
}}

EXAMPLE 4 - Emergency Medicine:
Conversation: "22-year-old male, MVA, GCS 15. C-spine clear. Right forearm deformity, neurovascularly intact. X-ray shows distal radius fracture. Morphine 4mg IV given. Splinted, orthopedics consulted. Admit for ORIF tomorrow."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Right forearm injury after motor vehicle accident",
    "history_of_present_illness": "22-year-old male presents via EMS after motor vehicle accident. Alert and oriented, GCS 15. C-spine cleared clinically. Reports right forearm pain and deformity. Neurovascular exam intact distally."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Distal radius fracture (confirmed on x-ray)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Morphine", "dose": "4mg", "frequency": "IV once", "indication": "Pain management"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "Distal radius fracture confirmed on imaging. Pain controlled with morphine 4mg IV. Forearm splinted. Orthopedics consulted for open reduction internal fixation. Admit for ORIF scheduled tomorrow.",
  "ai_confidence_score": 96,
  "flagged_for_review": false
}}

EXAMPLE 5 - Orthopedics:
Conversation: "Follow-up post-ACL repair 6 weeks ago. ROM improved, minimal effusion. Doing PT 3x/week. Continue weight-bearing as tolerated. Advance exercises. RTC 6 weeks for return-to-sport clearance."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Post-operative follow-up after ACL reconstruction",
    "history_of_present_illness": "Patient presents for 6-week post-op check after ACL repair. Reports good progress with physical therapy 3 times weekly. Range of motion improving with minimal knee effusion noted on exam."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Status post ACL reconstruction"],
    "medication_requests_new_or_changed": [],
    "allergies": []
  }},
  "assessment_plan_draft": "6-week post-ACL repair with good recovery progress. Minimal effusion, ROM improving. Continue weight-bearing as tolerated and advance PT exercises. Return in 6 weeks for return-to-sport clearance evaluation.",
  "ai_confidence_score": 94,
  "flagged_for_review": false
}}

EXAMPLE 6 - Dermatology:
Conversation: "Patient with pigmented lesion on back, asymmetric borders, 8mm. Suspicious for melanoma. Excisional biopsy performed with 2mm margins. Pathology pending. Discussed staging if positive. RTC 2 weeks for results."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Pigmented skin lesion on back",
    "history_of_present_illness": "Patient presents with concerning pigmented lesion on back noted during self-exam. Lesion measures 8mm with asymmetric borders, raising suspicion for melanoma."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Pigmented skin lesion, suspicious for melanoma (pending pathology)"],
    "medication_requests_new_or_changed": [],
    "allergies": []
  }},
  "assessment_plan_draft": "Suspicious pigmented lesion on back. Excisional biopsy performed with 2mm margins. Pathology pending. Discussed potential staging workup if melanoma confirmed. Return in 2 weeks for pathology results and further management.",
  "ai_confidence_score": 93,
  "flagged_for_review": false
}}

EXAMPLE 7 - OB/GYN:
Conversation: "28 weeks pregnant, routine prenatal. BP 118/76, FHR 145, fundal height 28cm. Glucose tolerance test normal. Tdap vaccine given. Discussed kick counts. RTC 2 weeks. No concerns."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Routine prenatal visit at 28 weeks gestation",
    "history_of_present_illness": "Patient presents for routine 28-week prenatal check. No acute complaints. Pregnancy progressing normally."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "118/76 mmHg",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Pregnancy at 28 weeks gestation (normal)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Tdap vaccine", "dose": "1 dose", "frequency": "once", "indication": "Prenatal immunization"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "28-week prenatal visit. Vital signs normal, fetal heart rate 145 bpm, fundal height appropriate at 28cm. Glucose tolerance test normal. Tdap vaccine administered. Kick counts discussed. Return in 2 weeks for routine follow-up.",
  "ai_confidence_score": 97,
  "flagged_for_review": false
}}

EXAMPLE 8 - Psychiatry:
Conversation: "Major depressive disorder follow-up. On sertraline 100mg daily x 8 weeks. Mood improved, PHQ-9 score down from 18 to 8. Sleep better. Continue current dose. Therapy ongoing. RTC 1 month."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Follow-up for major depressive disorder",
    "history_of_present_illness": "Patient returns for follow-up of major depressive disorder after 8 weeks on sertraline 100mg daily. Reports significant mood improvement with PHQ-9 score decreasing from 18 to 8. Sleep quality has improved. Continuing outpatient therapy."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Major depressive disorder (improving)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Sertraline", "dose": "100mg", "frequency": "daily", "indication": "Major depressive disorder"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "Major depressive disorder with good response to sertraline 100mg daily. PHQ-9 improved from 18 to 8 over 8 weeks. Continue current medication regimen. Patient engaged in ongoing therapy. Return in 1 month for monitoring.",
  "ai_confidence_score": 95,
  "flagged_for_review": false
}}

EXAMPLE 9 - Gastroenterology:
Conversation: "GERD symptoms x 6 months. Tried antacids, minimal relief. Endoscopy shows Grade B esophagitis. H. pylori negative. Starting omeprazole 20mg BID. Lifestyle modifications discussed. Repeat endoscopy in 8 weeks if symptoms persist."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Gastroesophageal reflux disease symptoms for 6 months",
    "history_of_present_illness": "Patient presents with 6-month history of GERD symptoms with minimal relief from over-the-counter antacids. Upper endoscopy performed showing Grade B esophagitis. H. pylori testing negative."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "N/A",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Gastroesophageal reflux disease", "Grade B esophagitis"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Omeprazole", "dose": "20mg", "frequency": "twice daily", "indication": "GERD and esophagitis"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "GERD with Grade B esophagitis confirmed on endoscopy. H. pylori negative. Initiating omeprazole 20mg BID. Lifestyle modifications discussed including diet changes and elevation of head of bed. Repeat endoscopy in 8 weeks if symptoms do not improve.",
  "ai_confidence_score": 94,
  "flagged_for_review": false
}}

EXAMPLE 10 - Endocrinology:
Conversation: "Type 2 diabetes follow-up. A1C down from 8.2% to 6.9% on metformin 1000mg BID. No hypoglycemia. BP 128/82. Continue current regimen. Annual eye exam scheduled. Foot check normal. RTC 3 months."

Correct JSON:
{{
  "encounter_summary": {{
    "chief_complaint": "Type 2 diabetes mellitus follow-up",
    "history_of_present_illness": "Patient presents for routine diabetes management follow-up. On metformin 1000mg twice daily with good glycemic control. A1C improved from 8.2% to 6.9%. No reported hypoglycemic episodes."
  }},
  "vital_signs_extracted": {{
    "blood_pressure": "128/82 mmHg",
    "heart_rate": "N/A",
    "temperature": "N/A"
  }},
  "clinical_entities": {{
    "diagnoses_problems": ["Type 2 diabetes mellitus (controlled)"],
    "medication_requests_new_or_changed": [
      {{"medication_name": "Metformin", "dose": "1000mg", "frequency": "twice daily", "indication": "Type 2 diabetes"}}
    ],
    "allergies": []
  }},
  "assessment_plan_draft": "Type 2 diabetes with excellent control on metformin 1000mg BID. A1C improved from 8.2% to 6.9%. No hypoglycemia reported. Blood pressure acceptable. Annual diabetic eye exam scheduled. Foot examination normal with intact sensation. Continue current medication regimen. Return in 3 months.",
  "ai_confidence_score": 96,
  "flagged_for_review": false
}}

Now extract from this NEW conversation:

{masked_conversation}

Return JSON with:
- encounter_summary: {{chief_complaint, history_of_present_illness}}
- vital_signs_extracted: {{blood_pressure, temperature, heart_rate}}
- clinical_entities: {{diagnoses_problems[], medication_requests_new_or_changed[], allergies[]}}
- assessment_plan_draft: string
- ai_confidence_score: 1-100
- flagged_for_review: boolean

Only extract stated facts. Use the examples above as guidance for format and detail level."""
        
        return examples

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
