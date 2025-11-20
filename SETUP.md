# Setup Guide - HIPAA-Compliant Clinical Note Automation Tool

## Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Anthropic API Key
1. Visit https://console.anthropic.com/account/keys
2. Create a new API key
3. Copy the key

### 3. Configure Environment
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Run Component Tests (No API Key Required)
```bash
python test_components.py
```

Expected output: All 4 tests pass ✓

### 5. Process Clinical Conversations (Requires API Key)
```bash
cd src
python main.py
```

This will:
- Process first 3 mock clinical conversations
- Generate output files in `output/` directory
- Create audit logs in `src/logs/` directory

## Detailed Installation

### System Requirements
- **Python**: 3.9 or higher
- **pip**: Latest version recommended
- **Memory**: 1GB minimum (for concurrent processing)
- **Disk**: 100MB for logs and output

### Step-by-Step Setup

#### 1. Clone or Download Project
```bash
# If you have git
git clone <repository-url>
cd "HIPAA-Compliant Clinical Note Automation Tool"

# Or if downloaded as ZIP
unzip project.zip
cd "HIPAA-Compliant Clinical Note Automation Tool"
```

#### 2. Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verify installation:
```bash
python -c "import anthropic; print(f'✓ Anthropic SDK {anthropic.__version__}')"
python -c "import fhir.resources; print('✓ FHIR Resources installed')"
```

#### 4. Set Up API Key

**Option A: Environment Variable**
```bash
export ANTHROPIC_API_KEY="sk-ant-xxx"  # macOS/Linux
set ANTHROPIC_API_KEY=sk-ant-xxx       # Windows
```

**Option B: .env File**
```bash
cp .env.example .env
# Edit .env with your text editor
# ANTHROPIC_API_KEY=sk-ant-xxx
```

**Option C: Programmatically**
```python
import os
os.environ['ANTHROPIC_API_KEY'] = 'sk-ant-xxx'
```

### Verify Setup
```bash
# Test all components (no API key required)
python test_components.py

# Should output:
# ✓ De-identification: PASSED
# ✓ Audit Logger: PASSED
# ✓ FHIR Schema: PASSED
# ✓ FHIR Transformer: PASSED
# 🎉 All component tests passed!
```

## Project Structure After Setup

```
HIPAA-Compliant Clinical Note Automation Tool/
├── src/
│   ├── main.py                      # Main entry point
│   ├── modules/
│   │   ├── deidentification.py      # PHI masking
│   │   ├── audit_logger.py          # Compliance logging
│   │   ├── claude_api.py            # Claude integration
│   │   ├── fhir_transformer.py      # FHIR conversion
│   │   └── fhir_schemas.py          # Schema definitions
│   ├── data/
│   │   └── mock_conversations.json  # Test conversations
│   └── logs/                        # Generated audit logs
├── output/                          # Generated output files
├── test_components.py               # Component tests
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── README.md                        # Full documentation
└── SETUP.md                         # This file
```

## Running the Tool

### Test Mode (No API Key Needed)
```bash
# Validate all components
python test_components.py
```

### Demo Mode (Requires API Key)
```bash
cd src
python main.py
```

This processes 3 sample conversations and shows:
- De-identification process
- Claude API processing with confidence scores
- FHIR transformation results
- Complete audit logs

### Processing Custom Conversations

**Python Script:**
```python
from src.main import ClinicalNoteProcessor

processor = ClinicalNoteProcessor()

conversation = """
Doctor: Good afternoon. What brings you in today?
Patient: I've had a persistent headache for 3 days.
...
"""

result = processor.process_conversation(conversation)
if result['success']:
    processor.save_results(result)
    print(f"Processed: {result['transaction_id']}")
```

**From JSON File:**
```python
import json
from src.main import ClinicalNoteProcessor

processor = ClinicalNoteProcessor()

# Load conversations
with open('my_conversations.json') as f:
    data = json.load(f)

# Process each
for conv in data:
    result = processor.process_conversation(conv['text'])
    processor.save_results(result)
```

## Environment Configuration

### Required Variables
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for processing)

### Optional Variables
- `CLAUDE_MODEL`: Override default model (default: `claude-sonnet-4-5-20250929`)
- `LOG_DIR`: Audit logs directory (default: `src/logs`)
- `OUTPUT_DIR`: Results directory (default: `output`)

### .env File Example
```env
# Required
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx

# Optional
CLAUDE_MODEL=claude-sonnet-4-5-20250929
LOG_DIR=src/logs
OUTPUT_DIR=output
AUDIT_LOG_FILE=src/logs/audit_log.json
TRANSACTION_LOG_FILE=src/logs/transaction_log.json
```

## Troubleshooting

### "ANTHROPIC_API_KEY not set"
**Problem**: API key not found
**Solutions**:
1. Check .env file exists and has correct key
2. Run: `echo $ANTHROPIC_API_KEY` (should show your key)
3. Ensure no spaces around `=` in .env file

### "ModuleNotFoundError: No module named 'anthropic'"
**Problem**: Dependencies not installed
**Solutions**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install anthropic
```

### "FileNotFoundError: mock_conversations.json"
**Problem**: Running from wrong directory
**Solutions**:
```bash
# Correct way
cd src
python main.py

# Or run from root with full path
python src/main.py
```

### "Permission denied" on macOS/Linux
**Problem**: Script not executable
**Solutions**:
```bash
chmod +x src/main.py
chmod +x test_components.py
```

### Claude API returns error
**Problem**: API key invalid or rate limited
**Solutions**:
1. Verify API key: https://console.anthropic.com/account/keys
2. Check account balance/credits
3. Review rate limits: max 50 requests/minute
4. Wait 30 seconds and retry

### FHIR validation fails
**Problem**: Schema mismatch
**Solutions**:
1. Check Claude response format matches schema
2. Review FHIR schema in `fhir_schemas.py`
3. Check audit logs for details
4. Run test suite: `python test_components.py`

## Development & Testing

### Run Component Tests
```bash
python test_components.py

# Expected: All 4 tests pass
```

### Run with Verbose Output
```bash
cd src
python main.py
# Shows detailed output for each stage
```

### Debug a Single Conversation
```python
from src.main import ClinicalNoteProcessor
import json

processor = ClinicalNoteProcessor()

conversation = "Doctor: ... Patient: ..."
result = processor.process_conversation(conversation)

print(json.dumps(result, indent=2, default=str))
```

### Access Audit Logs
```bash
# View recent logs
cat src/logs/audit_log.json | python -m json.tool

# Or programmatically
from src.modules.audit_logger import create_audit_logger
logger = create_audit_logger()
report = logger.export_audit_report()
print(report)
```

## Advanced Configuration

### Custom Claude Model
```python
from src.modules.claude_api import create_claude_api_wrapper

wrapper = create_claude_api_wrapper()
wrapper.set_model("claude-opus-4-1-20250805")
```

### Custom Log Directory
```python
from src.modules.audit_logger import create_audit_logger

logger = create_audit_logger(log_dir="/path/to/logs")
```

### Custom De-identification Patterns
Edit `src/modules/deidentification.py`:
```python
PHI_CATEGORIES = {
    'custom_pattern': r'your-regex-here',
    ...
}
```

### Batch Processing
```python
from src.main import ClinicalNoteProcessor

processor = ClinicalNoteProcessor()

conversations = [conv1, conv2, conv3, ...]
results = processor.process_batch_conversations(conversations)

for result in results:
    if result['success']:
        print(f"✓ {result['transaction_id']}")
    else:
        print(f"✗ {result['error']}")
```

## Performance Tuning

### Optimize API Calls
- Process in parallel (requires async refactoring)
- Batch multiple conversations
- Cache terminology lookups
- Use connection pooling

### Optimize Logging
- Compress old logs periodically
- Implement log rotation
- Archive audit logs to cold storage

### Optimize FHIR Conversion
- Use database instead of JSON files
- Implement resource caching
- Pre-compile terminology maps

## Production Deployment

### Minimum Requirements
- Python 3.9+
- 2GB RAM
- 100GB disk for logs
- Network access to Anthropic API

### Recommended Setup
```
Application Server
  ├── Python 3.11+
  ├── Virtual Environment
  ├── Gunicorn/ASGI server
  └── Process manager (systemd/supervisor)

Database
  ├── PostgreSQL for transaction logs
  └── MongoDB for FHIR documents

Security
  ├── API rate limiting
  ├── TLS encryption
  ├── VPC isolated network
  └── Role-based access control
```

### Example systemd Service
```ini
[Unit]
Description=Clinical Note Automation
After=network.target

[Service]
User=appuser
WorkingDirectory=/opt/clinical-scribe
Environment="PATH=/opt/clinical-scribe/venv/bin"
Environment="ANTHROPIC_API_KEY=..."
ExecStart=/opt/clinical-scribe/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Getting Help

### Documentation
- Full documentation: See [README.md](README.md)
- Component details: See docstrings in source files
- FHIR standards: https://www.hl7.org/fhir/R4/

### Community & Support
- Claude API docs: https://docs.anthropic.com/
- FHIR forums: https://chat.fhir.org/
- GitHub issues: Report bugs and request features

### Debugging
1. Check `src/logs/audit_log.json` for error details
2. Review output JSON in `output/` directory
3. Run `test_components.py` to validate setup
4. Check environment variables: `env | grep ANTHROPIC`

---

**Version**: 1.0.0
**Last Updated**: November 2025
