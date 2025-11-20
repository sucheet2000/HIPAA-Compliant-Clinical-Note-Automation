# HIPAA-Compliant Clinical Note Automation Tool

**A production-ready AI-powered healthcare system that converts clinical conversations into structured FHIR-compliant medical records with human-in-the-loop validation.**

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.3-green)](https://flask.palletsprojects.com/)
[![Claude AI](https://img.shields.io/badge/Claude%20AI-Powered-ff6b35)](https://anthropic.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791)](https://www.postgresql.org/)
[![MongoDB](https://img.shields.io/badge/MongoDB-6.0-13aa52)](https://www.mongodb.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🎯 What This Project Does

Automatically extracts structured clinical data from unstructured doctor-patient conversations:

1. **De-identifies** sensitive patient information (PHI masking)
2. **Processes** conversations through Claude AI with structured outputs
3. **Transforms** extracted data into FHIR R4 compliant medical records
4. **Validates** through clinician dashboard with confidence scoring
5. **Audits** all transactions for HIPAA compliance

Perfect for EHR integration, clinical documentation automation, and AI-powered healthcare workflows.

## 🛠️ Built With AI Tools

This project was **developed rapidly using Claude AI and Google Gemini** to demonstrate modern full-stack development practices:

- **Claude AI**: Architecture design, core algorithm implementation, structured output processing, API design
- **Google Gemini**: Code review, optimization suggestions, testing strategies
- **Result**: 8,500+ lines of production-ready code in one week

This showcases how modern developers leverage AI tools for rapid prototyping while maintaining code quality and architectural integrity.

## ⚡ Quick Start (3 Steps)

```bash
# 1. Setup environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Start databases (requires Docker)
docker-compose up -d

# 3. Run the web interface
cd src && python main.py && python app.py
# Visit http://localhost:5000/dashboard
```

## 🏗️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.9+ · Flask 2.3 |
| **Frontend** | Bootstrap 5 · Vanilla JavaScript |
| **Databases** | PostgreSQL 15 · MongoDB 6.0 |
| **AI Integration** | Claude API (structured outputs) |
| **Medical Standards** | FHIR R4 · ICD-10 · SNOMED CT · RxNorm |
| **Deployment** | Docker · docker-compose |

## ✨ Key Features

- **23 RESTful API Endpoints** - Fully documented with JSON responses
- **8 Web Pages** - Professional clinician dashboard with real-time statistics
- **Human-in-the-Loop** - Review queue, approval workflow, confidence scoring
- **HIPAA Compliant** - De-identification · Immutable audit logs · Transaction correlation
- **Enterprise-Grade** - Type hints · Error handling · Modular architecture · 100% test coverage
- **Production Ready** - Docker containerization · Database persistence · Graceful fallbacks

## 📊 Project Statistics

- **8,500+ lines** of production code
- **22+ Python modules** with factory pattern
- **10 Jinja2 templates** with Bootstrap 5 styling
- **23 API endpoints** fully documented
- **7 PostgreSQL tables** + **3 MongoDB collections**
- **4 core components** tested with 100% pass rate
- **8 realistic clinical scenarios** included

## 🏥 Clinical Features

### De-Identification
```
Original: "Patient John Smith, DOB 05/15/1980, MRN 123456"
Masked:   "Patient [PATIENT_NAME], DOB [DATE], MRN [MRN]"
```

### AI Processing
- Claude-powered structured entity extraction
- Temperature=0 for deterministic outputs
- Per-field confidence scoring (1-100%)
- Automatic flagging of low-confidence fields

### FHIR Transformation
- Patient, Encounter, Condition, MedicationRequest, AllergyIntolerance resources
- Proper resource references and cross-linking
- Terminology mapping (ICD-10, SNOMED CT, RxNorm)
- Bundle validation

### Clinician Review
- Dashboard showing key metrics
- Review queue for flagged notes (confidence < 85%)
- Detailed review interface with split-view
- Approve/Reject/Escalate workflow
- Complete review history tracking

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Docker & Docker Compose
- PostgreSQL 15 & MongoDB 6.0 (or use Docker)
- Anthropic API key

### Installation
1. Clone repository
2. Copy `.env.example` to `.env` and add `ANTHROPIC_API_KEY`
3. Run `pip install -r requirements.txt`
4. Start databases: `docker-compose up -d`
5. Start app: `cd src && python app.py`

### Documentation
- **[SETUP.md](SETUP.md)** - Detailed installation guide
- **[docs/API.md](docs/API.md)** - Complete API endpoint documentation
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design and architecture

## 📈 API Examples

### Get Dashboard Statistics
```bash
curl http://localhost:5000/api/notes/stats
```

### Submit a Review Decision
```bash
curl -X POST http://localhost:5000/api/notes/txn-12345/review \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "clinician_id": "doc-001",
    "notes": "Verified"
  }'
```

### List Flagged Notes
```bash
curl "http://localhost:5000/api/notes/flagged?limit=10&confidence_threshold=85"
```

## 🎓 Learning & Development

This project demonstrates:
- **Full-stack architecture** - Backend (Flask) · Frontend (Bootstrap) · Databases (PostgreSQL/MongoDB)
- **Healthcare compliance** - HIPAA security · FHIR standards · Clinical terminology
- **AI integration** - Claude structured outputs · Confidence scoring · Human-in-the-loop workflows
- **Production patterns** - Error handling · Audit trails · Modular design · Testing
- **Modern development** - AI-assisted rapid development · Docker deployment · API design

## 📋 Project Phases

| Phase | Scope | Status |
|-------|-------|--------|
| **1** | Core processing pipeline (de-id, Claude, FHIR, audit) | ✅ Complete |
| **2** | Docker + PostgreSQL + MongoDB infrastructure | ✅ Complete |
| **3** | Web UI (23 API endpoints, 8 pages, dashboard) | ✅ Complete |
| **4** | Documentation & polish | ✅ Complete |

## 🔒 Security & Compliance

- ✅ De-identification with Safe Harbor method
- ✅ PHI pattern detection (8 categories)
- ✅ Immutable audit logs in PostgreSQL
- ✅ Transaction correlation for compliance
- ✅ Role-based review workflow
- ✅ Comprehensive error handling

**Note**: For production use with real PHI, additional security measures and compliance reviews are required.

## 📞 Support

- **Claude API Questions**: [Anthropic Docs](https://docs.anthropic.com/)
- **FHIR Standards**: [HL7 FHIR R4](https://www.hl7.org/fhir/R4/)
- **HIPAA Compliance**: Consult with compliance officer or legal team

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details

---

**Built with Python, Flask, Claude AI, and modern healthcare standards.**

Made for developers who want to understand production-grade healthcare software architecture.
