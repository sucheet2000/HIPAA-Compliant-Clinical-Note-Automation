# Setup Guide - HIPAA-Compliant Clinical Note Automation Tool

## Quick Start (3 Minutes)

### 1. Install Dependencies
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your ANTHROPIC_API_KEY
# Get your key from: https://console.anthropic.com
```

### 3. Start Services (Requires Docker)
```bash
# Start PostgreSQL and MongoDB
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Run the Application
```bash
# Seed database with mock clinical data
cd src
python main.py

# Start Flask web server
python app.py

# Visit http://localhost:5000/dashboard
```

## System Requirements

- **Python**: 3.9 or higher
- **Docker**: For database services (PostgreSQL 15, MongoDB 6.0)
- **RAM**: Minimum 2GB recommended
- **Storage**: 1GB for databases and logs
- **API Key**: Anthropic Claude API key

## Environment Variables

Create a `.env` file with:

```env
# Required: Your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Model selection (default: claude-sonnet-4-5-20250929)
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Optional: Temperature (default: 0 for deterministic output)
CLAUDE_TEMPERATURE=0

# Database URLs (auto-configured by docker-compose)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/clinical_notes
MONGODB_URL=mongodb://localhost:27017/clinical_notes

# Flask configuration
FLASK_ENV=development
FLASK_DEBUG=True
```

## Troubleshooting

### Port Already in Use
```bash
# Flask uses port 5000
# PostgreSQL uses port 5432
# MongoDB uses port 27017

# To use different port:
python -c "from app import create_app; create_app().run(port=5001)"
```

### Database Connection Errors
```bash
# Verify containers are running
docker-compose ps

# View container logs
docker-compose logs postgres
docker-compose logs mongodb

# Restart services
docker-compose restart
```

### "Module not found: anthropic"
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### ANTHROPIC_API_KEY Not Set
```bash
# Method 1: Export as environment variable
export ANTHROPIC_API_KEY="your-key-here"

# Method 2: Add to .env file
# Edit .env and add: ANTHROPIC_API_KEY=sk-ant-...

# Method 3: Verify it's set
echo $ANTHROPIC_API_KEY
```

## Running Tests

```bash
# Run component tests
python test_components.py

# Expected output: All tests should pass ✓
```

## File Structure

```
.
├── src/
│   ├── main.py                 # Main orchestration
│   ├── app.py                  # Flask application
│   ├── modules/                # Core processing modules
│   ├── routes/                 # API and web routes
│   ├── services/               # Database query layer
│   ├── templates/              # Jinja2 HTML templates
│   ├── static/                 # CSS and JavaScript
│   ├── data/                   # Mock clinical conversations
│   └── database/               # Database initialization scripts
├── requirements.txt            # Python dependencies
├── docker-compose.yml         # Multi-service orchestration
├── Dockerfile                 # Flask app container
└── .env.example              # Environment template
```

## Next Steps

1. **Explore the Dashboard**: Visit http://localhost:5000/dashboard
2. **Review Mock Data**: Check `src/data/mock_conversations.json`
3. **Test API Endpoints**: Use curl or Postman
4. **Read Full Documentation**: Check repository for detailed guides

## Getting Help

- **API Documentation**: See inline code comments and docstrings
- **FHIR Standards**: https://www.hl7.org/fhir/R4/
- **Claude API**: https://docs.anthropic.com/
- **Docker Help**: https://docs.docker.com/

## Production Deployment

For production use with real PHI:

1. Set up proper database backups
2. Enable HTTPS/TLS for all connections
3. Implement authentication and authorization
4. Complete HIPAA risk assessment
5. Obtain Business Associate Agreement with Anthropic
6. Enable comprehensive audit logging
7. Implement rate limiting and monitoring

---

**For more detailed information, see the main README.md**
