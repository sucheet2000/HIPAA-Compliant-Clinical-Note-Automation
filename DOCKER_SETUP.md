# Docker Setup Guide

This guide explains how to run the HIPAA-Compliant Clinical Note Automation Tool in Docker with PostgreSQL and MongoDB.

## Prerequisites

- Docker Desktop installed ([https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop))
- Docker Compose (included with Docker Desktop)
- An Anthropic API key

## Quick Start (5 minutes)

### 1. Clone and Setup

```bash
cd /Users/sucheetboppana/HIPAA-Compliant\ Clinical\ Note\ Automation\ Tool

# Copy the environment file
cp .env.example .env

# Edit .env and add your Anthropic API key
# (or set it as an environment variable: export ANTHROPIC_API_KEY=your_key_here)
```

### 2. Start Docker Services

```bash
# Start PostgreSQL, MongoDB, and the Python app
docker-compose up --build

# Run in background
docker-compose up -d --build
```

The first build may take 2-3 minutes as Docker downloads base images and installs dependencies.

### 3. Verify Services are Running

```bash
# Check container status
docker-compose ps

# You should see:
# - clinical_notes_postgres   (healthy)
# - clinical_notes_mongodb    (healthy)
# - clinical_notes_app        (running)
```

### 4. View Logs

```bash
# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f mongodb
```

## Architecture Overview

```
┌─────────────────────────────────────────┐
│        Docker Network (clinical_network) │
├─────────────────────────────────────────┤
│                                          │
│  ┌──────────────┐   ┌───────────────┐   │
│  │   Python App │   │  Flask UI     │   │
│  │   :5000      │   │  :5000 (Phase 3) │
│  └──────┬───────┘   └──────┬────────┘   │
│         │                  │            │
│         ├──────────────────┼────────────┤
│         │                  │            │
│  ┌──────▼──────┐    ┌──────▼────────┐   │
│  │ PostgreSQL  │    │   MongoDB      │   │
│  │ :5432       │    │   :27017       │   │
│  │ (Audit Logs)│    │ (FHIR Bundles) │   │
│  └─────────────┘    └────────────────┘   │
│                                          │
└─────────────────────────────────────────┘
```

## Database Access

### PostgreSQL (Audit Logs)

```bash
# Connect to PostgreSQL from command line
docker-compose exec postgres psql -U clinicaluser -d clinical_notes_audit

# Example queries
SELECT * FROM audit_logs;
SELECT * FROM deidentification_events;
SELECT * FROM claude_api_calls;
SELECT * FROM fhir_transformations;
```

### MongoDB (FHIR Bundles)

```bash
# Connect to MongoDB
docker-compose exec mongodb mongosh -u clinicaluser -p secure_password_change_me

# Example queries (in mongosh)
use clinical_notes_fhir
db.fhir_bundles.find().pretty()
db.clinical_notes.find().pretty()
db.clinician_reviews.find().pretty()
```

## Data Persistence

Data is stored in Docker volumes:

- **PostgreSQL data**: `postgres_data` volume
- **MongoDB data**: `mongodb_data` volume

To remove all data (⚠️ destructive):

```bash
docker-compose down -v
```

To keep data while stopping services:

```bash
docker-compose down
docker-compose up
```

## Running the Application

### Option 1: Via Docker Compose (Recommended)

```bash
# Start all services and run the application
docker-compose up

# The app will process the mock clinical conversations and save results to:
# - PostgreSQL: audit logs
# - MongoDB: FHIR bundles
# - src/logs/: JSON audit logs (legacy)
# - output/: FHIR bundle files
```

### Option 2: Manually in the Container

```bash
# Start services only (no app)
docker-compose up -d postgres mongodb

# Run app in the container
docker-compose run --rm app python src/main.py

# Or execute a shell
docker-compose run --rm app bash
```

## Testing

```bash
# Run pytest inside the container
docker-compose run --rm app pytest test_full_suite.py -v

# Run with coverage
docker-compose run --rm app pytest test_full_suite.py --cov=src --cov-report=html
```

## Troubleshooting

### "Connection refused" errors

**Issue**: App can't connect to PostgreSQL or MongoDB

```
psycopg2.OperationalError: could not connect to server
pymongo.errors.ServerSelectionTimeoutError
```

**Solution**:
```bash
# Check if services are healthy
docker-compose ps

# View service logs
docker-compose logs postgres
docker-compose logs mongodb

# Wait longer for services to be ready
docker-compose up

# If persistent, remove and restart
docker-compose down -v
docker-compose up --build
```

### Database is empty / data not persisting

**Issue**: After restarting, data is gone

**Cause**: Volumes were deleted (you ran `docker-compose down -v`)

**Solution**:
```bash
# Don't use the -v flag (removes volumes)
docker-compose down  # Good - keeps data
docker-compose down -v  # Bad - destroys data
```

### API key not working

**Issue**: `anthropic.AuthenticationError`

**Solution**:
```bash
# Make sure your API key is set
export ANTHROPIC_API_KEY=your_actual_key_here

# Or update .env file
echo "ANTHROPIC_API_KEY=your_actual_key_here" > .env

# Restart the app
docker-compose restart app
```

### Docker build errors

**Issue**: `ERROR: docker buildkit not available`

**Solution**:
```bash
# Build without buildkit
DOCKER_BUILDKIT=0 docker-compose up --build
```

## Next Steps

Once Docker is running:

1. **Phase 3**: Build the human-in-the-loop web UI (Flask)
2. **Monitor Databases**: Use PostgreSQL and MongoDB clients to inspect logged data
3. **Customize**: Modify database schemas in `src/database/init_*.sql`/`.js`
4. **Deploy**: Push images to Docker Hub or deploy to Kubernetes

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove all data
docker-compose down -v

# Clean up unused Docker resources
docker system prune
```

## Production Considerations

For a production deployment:

1. **Change default passwords** in `docker-compose.yml` and `.env`
2. **Use secrets management** (AWS Secrets Manager, Vault, etc.)
3. **Enable TLS/SSL** for all connections
4. **Set up automated backups** for PostgreSQL and MongoDB
5. **Configure proper resource limits** (CPU, memory)
6. **Use a reverse proxy** (nginx) for the Flask app
7. **Set up monitoring** (Prometheus, Grafana)
8. **Use orchestration** (Kubernetes, Docker Swarm)
