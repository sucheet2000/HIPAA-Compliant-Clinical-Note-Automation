# Quick Reference Guide

## Installation (One-Time Setup)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key (pick one method)
export ANTHROPIC_API_KEY="sk-ant-..."          # Terminal
# OR edit .env file with your key

# 3. Verify setup
python test_components.py  # Should pass all tests
```

## Common Tasks

### Run Demo (Process 3 Sample Conversations)
```bash
cd src
python main.py
```
**Output**: Files in `output/` and `src/logs/`

### Test All Components (No API Key Needed)
```bash
python test_components.py
```
**Output**: ✓ All 4 tests passed

### Process Single Conversation (Programmatic)
```python
from src.main import ClinicalNoteProcessor

processor = ClinicalNoteProcessor()
result = processor.process_conversation("Doctor: ... Patient: ...")

# Check result
print(f"Success: {result['success']}")
print(f"Confidence: {result['stages']['claude_processing']['confidence_score']}")

# Save to file
processor.save_results(result)
```

### Process Multiple Conversations
```python
from src.main import ClinicalNoteProcessor
import json

processor = ClinicalNoteProcessor()

# Load conversations
with open('conversations.json') as f:
    convs = json.load(f)

# Process all
for i, conv in enumerate(convs):
    print(f"Processing {i+1}/{len(convs)}...")
    result = processor.process_conversation(conv['text'])
    processor.save_results(result)
```

### View Audit Logs
```bash
# View complete audit log
cat src/logs/audit_log.json | python -m json.tool

# Or programmatically
from src.modules.audit_logger import create_audit_logger

logger = create_audit_logger()
report = logger.export_audit_report()
print(report)
```

### De-identify Text Manually
```python
from src.modules.deidentification import create_deidentifier

deidentifier = create_deidentifier()
masked_text, audit = deidentifier.deidentify(
    "Patient John Smith, DOB 05/15/1980..."
)

print(f"Original: 334 chars")
print(f"Masked: {audit['masked_length']} chars")
print(f"Redactions: {audit['redactions_by_type']}")
```

### Transform Claude Output to FHIR
```python
from src.modules.fhir_transformer import create_fhir_transformer

transformer = create_fhir_transformer()

claude_output = {
    "encounter_summary": {...},
    "vital_signs_extracted": {...},
    "clinical_entities": {...},
    # ... etc
}

fhir_bundle, resources = transformer.transform_to_fhir_bundle(
    claude_output,
    transaction_id="txn-001"
)

print(f"Created resources: {resources}")
```

## File Locations

| Type | Location | Purpose |
|------|----------|---------|
| Processing Results | `output/result_*.json` | Complete output with all stages |
| Audit Logs | `src/logs/audit_log.json` | Compliance audit trail |
| Transaction Log | `src/logs/transaction_log.json` | Transaction summaries |
| Mock Data | `src/data/mock_conversations.json` | Sample conversations |
| Code | `src/modules/` | Implementation |

## Output Files Explained

### result_<transaction_id>.json
```json
{
  "transaction_id": "uuid-...",
  "success": true,
  "stages": {
    "deidentification": {
      "status": "success",
      "redactions": {"names": 1, "dates": 2},
      "validation_safe": true
    },
    "claude_processing": {
      "status": "success",
      "confidence_score": 85,
      "flagged_for_review": false
    },
    "fhir_transformation": {
      "status": "success",
      "resource_counts": {
        "Patient": 1,
        "Encounter": 1,
        "Condition": 2,
        "MedicationRequest": 1,
        "AllergyIntolerance": 1
      }
    }
  },
  "outputs": {
    "masked_conversation": "...",
    "structured_clinical_data": {...},
    "fhir_bundle": {...}
  }
}
```

### audit_log.json
Array of audit events:
```json
[
  {
    "timestamp": "2025-11-18T...",
    "transaction_id": "uuid-...",
    "event_type": "de_identification",
    "redactions": {...},
    "validation_safe": true
  },
  {
    "event_type": "claude_api_call",
    "model": "claude-sonnet-4-5-20250929",
    "status": "success"
  },
  ...
]
```

## Configuration

### Environment Variables
```bash
ANTHROPIC_API_KEY=sk-ant-...        # Required
CLAUDE_MODEL=claude-sonnet-...      # Optional (default: claude-sonnet-4-5-20250929)
LOG_DIR=src/logs                    # Optional (default: src/logs)
OUTPUT_DIR=output                   # Optional (default: output)
```

### .env File
```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx
CLAUDE_MODEL=claude-sonnet-4-5-20250929
LOG_DIR=src/logs
OUTPUT_DIR=output
```

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ANTHROPIC_API_KEY not set` | Missing API key | `export ANTHROPIC_API_KEY="sk-..."` |
| `ModuleNotFoundError: anthropic` | Dependencies missing | `pip install -r requirements.txt` |
| `FileNotFoundError: mock_conversations.json` | Wrong directory | `cd src && python main.py` |
| `json.JSONDecodeError` | Claude response invalid | Check API key, try again |
| `Permission denied` | File permissions | `chmod +x *.py` |

## Key Concepts

### De-identification
Converts PHI (names, dates, MRN) to placeholders (`[PATIENT_NAME]`) before processing.

### Structured Outputs
Claude API feature guaranteeing valid JSON matching a specific schema.

### FHIR Bundle
Collection of healthcare resources (Patient, Encounter, Condition, etc.) linked together.

### Confidence Score
1-100 rating of how confident Claude is in the extracted data (80+ = good).

### Audit Trail
Complete log of every processing step for compliance verification.

## Data Flow

```
Raw Conversation (unstructured)
    ↓
De-identification (masks PHI)
    ↓
Claude Processing (structured JSON)
    ↓
FHIR Transformation (healthcare standard)
    ↓
Audit Logging (compliance trail)
    ↓
Output Files (JSON results)
```

## Testing

### Validate Setup
```bash
python test_components.py
```
Expected: All 4 tests pass ✓

### Test with Sample Data
```bash
cd src
python main.py
```
Expected: Processes 3 conversations, creates output files

### Debug Single Conversation
```python
from src.main import ClinicalNoteProcessor
import json

processor = ClinicalNoteProcessor()
result = processor.process_conversation("your text here")
print(json.dumps(result, indent=2, default=str))
```

## Performance Notes

- **Per conversation**: 2-6 seconds (depends on Claude API latency)
- **Cost per conversation**: ~$0.01 USD
- **Batch processing**: Easy to scale to 100+ conversations
- **Peak performance**: 10 conversations/minute (sequential)

## Tips & Tricks

### Process Faster
```python
# Set higher temperature for variety (not recommended for medical)
wrapper.temperature = 0.3
```

### Custom De-identification
```python
# Add custom pattern
from src.modules.deidentification import PHIRedactionList

PHIRedactionList.PHI_CATEGORIES['custom'] = r'your-regex'
PHIRedactionList.PLACEHOLDER_MAP['custom'] = '[CUSTOM]'
```

### Extend FHIR Resources
```python
# Add new resource type to schemas
FHIR_OBSERVATION_SCHEMA = {
    "resourceType": "Observation",
    "properties": {...}
}
```

### Change Claude Model
```python
processor.claude_api.set_model("claude-opus-4-1-20250805")
```

### Save Raw Response
```python
result = processor.process_conversation(conv)
structured = result['outputs']['structured_clinical_data']
raw_fhir = result['outputs']['fhir_bundle']

# Process further if needed
```

## Troubleshooting

### Nothing happens when I run the script
- Check you're in correct directory: `cd src`
- Check Python version: `python --version` (need 3.9+)
- Check dependencies: `pip list | grep anthropic`

### API returns errors
- Verify API key: `echo $ANTHROPIC_API_KEY`
- Check account at https://console.anthropic.com/account/keys
- Verify API key format: starts with `sk-ant-`
- Check rate limits: max 50 requests/minute

### Output files not created
- Check output directory exists: `mkdir -p output`
- Check permissions: `ls -la output/`
- Check error message in console

### Tests fail
- Run `python test_components.py` with full output
- Check Python version: `python --version`
- Reinstall dependencies: `pip install -r requirements.txt`

## Getting Help

1. **Check Documentation**
   - Full guide: [README.md](README.md)
   - Setup help: [SETUP.md](SETUP.md)
   - Project details: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

2. **Review Code**
   - Main script: `src/main.py`
   - Module docstrings
   - Test suite: `test_components.py`

3. **Check Logs**
   - Audit trail: `src/logs/audit_log.json`
   - Output: `output/result_*.json`
   - Errors in console output

4. **External Resources**
   - Claude API docs: https://docs.anthropic.com/
   - FHIR docs: https://www.hl7.org/fhir/R4/
   - HIPAA info: https://www.hhs.gov/hipaa/

## Summary

**Setup**: `pip install -r requirements.txt && export ANTHROPIC_API_KEY="..."`

**Test**: `python test_components.py`

**Run**: `cd src && python main.py`

**Process**: Use `ClinicalNoteProcessor` class in code

**View Results**: Check `output/` and `src/logs/`

---

For detailed information, see [README.md](README.md) and [SETUP.md](SETUP.md).
