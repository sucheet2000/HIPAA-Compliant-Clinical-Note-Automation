# Phase 2: Running Locally on Your Machine

Since Docker isn't available in this development sandbox, here are the complete instructions to run Phase 2 on your local machine.

## Prerequisites

Before starting, ensure you have:

- ✅ Docker Desktop installed ([download here](https://www.docker.com/products/docker-desktop))
- ✅ Your Anthropic API key
- ✅ This project cloned/saved to your machine

## Step-by-Step: Run Phase 2 (5 minutes)

### 1. Navigate to Project Directory

```bash
cd /Users/sucheetboppana/HIPAA-Compliant\ Clinical\ Note\ Automation\ Tool
```

### 2. Set Up Environment Variables

```bash
# Copy the environment template
cp .env.example .env

# Edit .env and replace YOUR_API_KEY
# Option A: Edit the file directly
nano .env  # or use your favorite editor

# Option B: Set as environment variable (one-time)
export ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 3. Build Docker Images and Start Services

```bash
# Build and start all three services (this takes 2-3 minutes on first run)
docker-compose up --build

# Or run in background (no logs visible)
docker-compose up -d --build
```

**First-time build includes:**
- Python 3.9 slim base image (~150MB)
- PostgreSQL 15 Alpine (~100MB)
- MongoDB 7 (~300MB)
- Python dependencies installation

### 4. Verify Services are Running

**In a new terminal:**

```bash
cd /Users/sucheetboppana/HIPAA-Compliant\ Clinical\ Note\ Automation\ Tool

docker-compose ps
```

You should see:

```
NAME                      COMMAND                  STATE            PORTS
clinical_notes_app        python src/main.py       running          0.0.0.0:5000->5000/tcp
clinical_notes_mongodb    mongod --auth            healthy (1/1)    0.0.0.0:27017->27017/tcp
clinical_notes_postgres   postgres                 healthy (1/1)    0.0.0.0:5432->5432/tcp
```

### 5. Monitor Application Logs

```bash
# View all logs
docker-compose logs -f

# View just the app
docker-compose logs -f app

# View just PostgreSQL
docker-compose logs -f postgres

# View just MongoDB
docker-compose logs -f mongodb
```

The app will automatically:
1. ✅ Process all 8 mock clinical conversations
2. ✅ De-identify each conversation
3. ✅ Send to Claude API for extraction
4. ✅ Transform to FHIR bundles
5. ✅ Save to both PostgreSQL and MongoDB
6. ✅ Generate audit logs

**Expected output:**
```
Processing Transaction: <uuid>
  ✓ De-identification complete
  ✓ Claude API processed (confidence: 92%)
  ✓ FHIR bundle created (58 resources)
  ✓ Results saved to: output/result_<uuid>.json
  ✓ FHIR bundle saved to MongoDB
```

### 6. Verify Data in Databases

#### PostgreSQL (Audit Logs)

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U clinicaluser -d clinical_notes_audit

# Inside psql prompt (postgres=#), try these queries:
SELECT COUNT(*) FROM audit_logs;
SELECT transaction_id, event_type, status FROM audit_logs LIMIT 5;
SELECT * FROM deidentification_events;
SELECT * FROM claude_api_calls;
SELECT * FROM fhir_transformations;

# Exit psql
\q
```

#### MongoDB (FHIR Bundles)

```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh -u clinicaluser -p secure_password_change_me

# Inside mongosh prompt (>), try these:
use clinical_notes_fhir
db.fhir_bundles.count()
db.fhir_bundles.find().limit(1).pretty()
db.clinical_notes.find().limit(1).pretty()

# Exit mongosh
exit
```

### 7. View Output Files

```bash
# FHIR bundles (JSON format)
ls -la output/

# Audit logs (JSON format, legacy)
cat src/logs/audit_log.json | python -m json.tool | less

# Result files
cat output/result_*.json | python -m json.tool
```

---

## What's Happening (Data Flow)

```
1. Raw Conversations (src/data/mock_conversations.json)
           ↓
2. De-identification Module
   - Masks: names, dates, SSN, phone, etc.
   - Logs to: src/logs/audit_log.json + PostgreSQL
           ↓
3. Claude API Wrapper
   - Extracts: diagnoses, medications, allergies, vital signs
   - Logs to: src/logs/audit_log.json + PostgreSQL
           ↓
4. FHIR Transformer
   - Converts to FHIR R4 resources
   - Creates: Patient, Encounter, Condition, Medication, Allergy
   - Logs to: src/logs/audit_log.json + PostgreSQL
           ↓
5. Persistence (Dual Storage)
   - JSON files → output/result_*.json
   - PostgreSQL → All audit tables
   - MongoDB → fhir_bundles collection
           ↓
6. Output Available In:
   - output/ directory
   - PostgreSQL audit_logs table
   - MongoDB fhir_bundles collection
```

---

## Troubleshooting Phase 2

### Problem: "docker: command not found"

**Solution**: Install Docker Desktop
- Download from https://www.docker.com/products/docker-desktop
- After installation, restart your terminal

### Problem: "Connection refused" to databases

**Solution**: Services need more time to start
```bash
# Wait 30 seconds and check again
docker-compose ps

# Check service logs for errors
docker-compose logs postgres
docker-compose logs mongodb
```

### Problem: "Authentication failed" for MongoDB

**Make sure you're using the correct password:**
```bash
docker-compose exec mongodb mongosh -u clinicaluser -p secure_password_change_me
```

The password is: `secure_password_change_me` (change for production!)

### Problem: API key not working

```bash
# Verify your API key is set
echo $ANTHROPIC_API_KEY

# If empty, set it:
export ANTHROPIC_API_KEY=sk-ant-xxx...

# Then restart the app
docker-compose restart app

# View logs to confirm it's working
docker-compose logs -f app
```

### Problem: "Database is empty" after restart

**Don't use the `-v` flag when stopping:**
```bash
docker-compose down     # Good - keeps data
docker-compose down -v  # Bad - deletes all data!
```

---

## Testing Phase 2

### Run Unit Tests with Databases

```bash
# Option 1: Run tests in the container
docker-compose exec app pytest test_full_suite.py -v

# Option 2: Run with coverage
docker-compose exec app pytest test_full_suite.py -v --cov=src
```

**Expected:** All 72 tests pass ✅

### Manual Testing

```bash
# Process a single conversation
docker-compose exec app python -c "
from src.main import ClinicalNoteProcessor
processor = ClinicalNoteProcessor()
result = processor.process_conversation('Patient reports fever and cough for 3 days.')
print(result)
"
```

---

## Monitoring Services

### Check System Resources

```bash
# View CPU/memory usage
docker stats

# Ctrl+C to exit
```

### View Service Logs in Real-Time

```bash
# All services
docker-compose logs -f --tail=100

# Just errors
docker-compose logs -f app | grep -i error
```

---

## Stopping Services

```bash
# Graceful shutdown (keeps data)
docker-compose down

# Stop but keep containers running
docker-compose stop

# Resume running containers
docker-compose start

# Full cleanup (deletes all data!)
docker-compose down -v
```

---

## Next Steps After Phase 2 Works

Once you confirm all services are running and data is being stored:

1. ✅ Verify PostgreSQL has audit logs
2. ✅ Verify MongoDB has FHIR bundles
3. ✅ Run the test suite (should all pass)
4. ✅ Check output files are being created

Then you're ready for **Phase 3: Human-in-the-Loop Web UI** 🎨

---

## Performance Expectations

On a typical machine:

- **Startup time**: 30-60 seconds (services initialization)
- **Per-conversation processing**: 5-15 seconds (Claude API call)
- **8 conversations total**: 1-2 minutes
- **Database write time**: <1 second per record

---

## Security Notes for Phase 2

⚠️ **IMPORTANT: Change Default Credentials Before Production**

In `docker-compose.yml`, these are defaults:
```yaml
POSTGRES_PASSWORD: secure_password_change_me
MONGO_INITDB_ROOT_PASSWORD: secure_password_change_me
```

For production:
1. Generate random passwords
2. Store in AWS Secrets Manager
3. Use separate credentials for each environment
4. Enable TLS/SSL for all connections
5. Set up automated backups

---

## Docker Compose Cheat Sheet

```bash
# Start services
docker-compose up -d --build

# Stop services
docker-compose down

# View status
docker-compose ps

# View logs
docker-compose logs -f

# Run a command in container
docker-compose exec app python script.py

# Access PostgreSQL shell
docker-compose exec postgres psql -U clinicaluser -d clinical_notes_audit

# Access MongoDB shell
docker-compose exec mongodb mongosh -u clinicaluser -p secure_password_change_me

# Remove everything (destructive!)
docker-compose down -v
```

---

## Success Checklist ✅

After running Phase 2, verify:

- [ ] Docker containers started successfully
- [ ] PostgreSQL is healthy
- [ ] MongoDB is healthy
- [ ] App processed all 8 conversations
- [ ] output/ directory has JSON files
- [ ] PostgreSQL has audit_logs records
- [ ] MongoDB has fhir_bundles
- [ ] src/logs/audit_log.json has entries
- [ ] No major errors in logs
- [ ] Test suite passes (all 72 tests)

---

## Ready to Run Phase 2?

Execute this in your terminal:

```bash
cd /Users/sucheetboppana/HIPAA-Compliant\ Clinical\ Note\ Automation\ Tool
export ANTHROPIC_API_KEY=your_key_here
docker-compose up --build
```

You're all set! Let me know when Phase 2 is running successfully, and we'll move on to Phase 3. 🚀
