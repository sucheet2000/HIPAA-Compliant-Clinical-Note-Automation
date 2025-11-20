# API Reference

Complete documentation of all 23 RESTful API endpoints for the HIPAA-Compliant Clinical Note Automation Tool.

## Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/notes` | GET | List all clinical notes |
| `/api/notes/flagged` | GET | Notes requiring review (confidence < 85%) |
| `/api/notes/<id>` | GET | Get detailed note with FHIR bundle |
| `/api/notes/stats` | GET | Dashboard statistics |
| `/api/notes/<id>/review` | POST | Submit review decision |
| `/api/notes/<id>/review-history` | GET | Get all reviews for a note |
| `/api/reviews/approved` | GET | All approved notes |
| `/api/reviews/rejected` | GET | All rejected notes |
| `/api/reviews/escalated` | GET | All escalated notes |
| `/api/clinicians/<id>/stats` | GET | Clinician performance statistics |
| `/api/search` | GET | Search by transaction ID or confidence |
| `/api/health` | GET | Health check |
| `/api/status` | GET | System status |

---

## Notes Endpoints

### GET `/api/notes`

List all clinical notes with pagination.

**Query Parameters**:
- `limit` (optional): Number of results per page (default: 20)
- `offset` (optional): Number of results to skip (default: 0)

**Example**:
```bash
curl "http://localhost:5000/api/notes?limit=20&offset=0"
```

**Response** (200 OK):
```json
{
  "success": true,
  "notes": [
    {
      "transaction_id": "txn-uuid",
      "date_processed": "2025-11-18T10:30:00Z",
      "confidence_score": 87,
      "clinician_notes": null,
      "review_status": "pending"
    }
  ],
  "total": 5,
  "limit": 20,
  "offset": 0
}
```

**Status Codes**:
- `200`: Success
- `500`: Server error

---

### GET `/api/notes/flagged`

Get notes flagged for clinician review (confidence below threshold).

**Query Parameters**:
- `confidence_threshold` (optional): Confidence cutoff (default: 85)
- `limit` (optional): Number of results (default: 10)
- `offset` (optional): Pagination offset (default: 0)

**Example**:
```bash
curl "http://localhost:5000/api/notes/flagged?limit=10&confidence_threshold=85"
```

**Response** (200 OK):
```json
{
  "success": true,
  "flagged_notes": [
    {
      "transaction_id": "txn-uuid",
      "confidence_score": 72,
      "chief_complaint": "Chest pain",
      "reasons": ["low_vital_signs_confidence", "multiple_low_fields"]
    }
  ],
  "count": 3
}
```

---

### GET `/api/notes/<transaction_id>`

Get detailed note information including extracted data and FHIR bundle.

**Path Parameters**:
- `transaction_id`: UUID of the transaction

**Example**:
```bash
curl "http://localhost:5000/api/notes/txn-12345"
```

**Response** (200 OK):
```json
{
  "success": true,
  "transaction_id": "txn-12345",
  "masked_conversation": "Doctor: [GREETING]...",
  "field_confidences": {
    "chief_complaint": 92,
    "vital_signs": 78,
    "diagnoses": 85,
    "medications": 88,
    "allergies": 95
  },
  "extracted_data": {
    "chief_complaint": "Chest pain",
    "vital_signs": {
      "systolic": 140,
      "diastolic": 90,
      "heart_rate": 88,
      "temperature": 98.6
    },
    "diagnoses": [
      {"code": "I10", "display": "Essential hypertension"}
    ],
    "medications": [
      {"code": "C0020538", "display": "Lisinopril"}
    ],
    "allergies": [
      {"code": "penicillin", "severity": "severe"}
    ]
  },
  "fhir_bundle": {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
      {
        "resource": {
          "resourceType": "Patient",
          "id": "pat-uuid"
        }
      }
    ]
  },
  "review_history": [
    {
      "clinician_id": "doc-001",
      "action": "escalate",
      "notes": "Needs cardiology review",
      "timestamp": "2025-11-18T11:00:00Z"
    }
  ]
}
```

**Status Codes**:
- `200`: Success
- `404`: Note not found
- `500`: Server error

---

### GET `/api/notes/stats`

Get dashboard statistics for system overview.

**Example**:
```bash
curl "http://localhost:5000/api/notes/stats"
```

**Response** (200 OK):
```json
{
  "success": true,
  "total_notes": 5,
  "flagged_notes": 1,
  "reviewed_notes": 3,
  "pending_notes": 2,
  "average_confidence": 84.6,
  "min_confidence": 72,
  "max_confidence": 95,
  "approval_rate": 66.7
}
```

---

## Review Endpoints

### POST `/api/notes/<transaction_id>/review`

Submit a review decision for a clinical note.

**Path Parameters**:
- `transaction_id`: UUID of the transaction

**Request Body**:
```json
{
  "action": "approve",
  "clinician_id": "doc-001",
  "notes": "Looks good"
}
```

**Valid Actions**:
- `approve`: Clinician approves the AI-generated data
- `reject`: Clinician rejects the data for reprocessing
- `escalate`: Note requires specialist or manual review

**Example**:
```bash
curl -X POST "http://localhost:5000/api/notes/txn-12345/review" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "approve",
    "clinician_id": "doc-001",
    "notes": "Confirmed all values"
  }'
```

**Response** (201 Created):
```json
{
  "success": true,
  "transaction_id": "txn-12345",
  "action": "approve",
  "timestamp": "2025-11-18T11:05:00Z",
  "message": "Review recorded successfully"
}
```

**Status Codes**:
- `201`: Review created successfully
- `400`: Invalid request (missing fields or invalid action)
- `404`: Note not found
- `500`: Server error

---

### GET `/api/notes/<transaction_id>/review-history`

Get complete review history for a note.

**Path Parameters**:
- `transaction_id`: UUID of the transaction

**Example**:
```bash
curl "http://localhost:5000/api/notes/txn-12345/review-history"
```

**Response** (200 OK):
```json
{
  "success": true,
  "transaction_id": "txn-12345",
  "reviews": [
    {
      "action": "escalate",
      "clinician_id": "doc-001",
      "notes": "Needs review",
      "timestamp": "2025-11-18T10:50:00Z"
    },
    {
      "action": "approve",
      "clinician_id": "doc-002",
      "notes": "Confirmed",
      "timestamp": "2025-11-18T11:05:00Z"
    }
  ]
}
```

**Status Codes**:
- `200`: Success
- `404`: Note not found
- `500`: Server error

---

## Filter Endpoints

### GET `/api/reviews/approved`

Get all notes approved by clinicians.

**Query Parameters**:
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example**:
```bash
curl "http://localhost:5000/api/reviews/approved?limit=50&offset=0"
```

**Response** (200 OK):
```json
{
  "success": true,
  "reviews": [
    {
      "transaction_id": "txn-123",
      "clinician_id": "doc-001",
      "timestamp": "2025-11-18T11:00:00Z",
      "notes": "Verified"
    }
  ],
  "count": 2,
  "total": 10
}
```

---

### GET `/api/reviews/rejected`

Get all notes rejected by clinicians.

**Query Parameters**:
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example**:
```bash
curl "http://localhost:5000/api/reviews/rejected?limit=50&offset=0"
```

**Response** (200 OK):
```json
{
  "success": true,
  "reviews": [
    {
      "transaction_id": "txn-456",
      "clinician_id": "doc-002",
      "timestamp": "2025-11-18T10:30:00Z",
      "notes": "Incorrect diagnosis"
    }
  ],
  "count": 1,
  "total": 5
}
```

---

### GET `/api/reviews/escalated`

Get all notes escalated for specialist review.

**Query Parameters**:
- `limit` (optional): Results per page (default: 50)
- `offset` (optional): Pagination offset (default: 0)

**Example**:
```bash
curl "http://localhost:5000/api/reviews/escalated?limit=50&offset=0"
```

**Response** (200 OK):
```json
{
  "success": true,
  "reviews": [
    {
      "transaction_id": "txn-789",
      "clinician_id": "doc-001",
      "timestamp": "2025-11-18T09:15:00Z",
      "notes": "Needs cardiology review"
    }
  ],
  "count": 1,
  "total": 3
}
```

---

## Clinician Endpoints

### GET `/api/clinicians/<clinician_id>/stats`

Get performance statistics for a specific clinician.

**Path Parameters**:
- `clinician_id`: Unique clinician identifier

**Example**:
```bash
curl "http://localhost:5000/api/clinicians/doc-001/stats"
```

**Response** (200 OK):
```json
{
  "success": true,
  "clinician_id": "doc-001",
  "total_reviews": 12,
  "approvals": 8,
  "rejections": 2,
  "escalations": 2,
  "approval_rate": 66.7,
  "avg_processing_time_seconds": 45
}
```

**Status Codes**:
- `200`: Success
- `404`: Clinician not found
- `500`: Server error

---

## Search Endpoints

### GET `/api/search`

Search notes by transaction ID or confidence range.

**Query Parameters**:
- `q` (optional): Transaction ID to search for
- `min_confidence` (optional): Minimum confidence score (0-100)
- `max_confidence` (optional): Maximum confidence score (0-100)

**Examples**:
```bash
# Search by transaction ID
curl "http://localhost:5000/api/search?q=txn-12345"

# Search by confidence range
curl "http://localhost:5000/api/search?min_confidence=70&max_confidence=85"

# Combined search
curl "http://localhost:5000/api/search?q=txn&min_confidence=80"
```

**Response** (200 OK):
```json
{
  "success": true,
  "results": [
    {
      "transaction_id": "txn-12345",
      "confidence_score": 78,
      "chief_complaint": "Chest pain",
      "date_processed": "2025-11-18T10:30:00Z"
    }
  ],
  "count": 1
}
```

**Status Codes**:
- `200`: Success
- `400`: Invalid search parameters
- `500`: Server error

---

## Health & Status Endpoints

### GET `/api/health`

Health check for system monitoring and load balancers.

**Example**:
```bash
curl "http://localhost:5000/api/health"
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-18T11:30:00Z"
}
```

**Status Codes**:
- `200`: Service is healthy
- `503`: Service is unhealthy

---

### GET `/api/status`

Get comprehensive system status.

**Example**:
```bash
curl "http://localhost:5000/api/status"
```

**Response** (200 OK):
```json
{
  "status": "operational",
  "version": "1.0.0",
  "databases": {
    "postgresql": "connected",
    "mongodb": "connected"
  },
  "timestamp": "2025-11-18T11:30:00Z"
}
```

---

## Error Handling

All endpoints follow standard HTTP status codes and return error responses in this format:

```json
{
  "success": false,
  "error": "Error message describing what went wrong",
  "status": 400
}
```

### Common Status Codes

| Code | Meaning |
|------|---------|
| 200 | Request successful |
| 201 | Resource created |
| 400 | Invalid request (bad parameters) |
| 404 | Resource not found |
| 500 | Internal server error |

---

## Authentication & Authorization

Currently, all endpoints are publicly accessible. For production deployment, implement:
- JWT token-based authentication
- Role-based access control (clinician, admin)
- API key management
- Rate limiting

---

## Rate Limiting

Recommended for production:
- 100 requests per minute per IP
- 10,000 requests per day per API key
- Burst limit: 20 requests per second

---

## Testing Endpoints

Use curl, Postman, or any HTTP client. Example with Postman:

1. **New Request**: Set method to GET
2. **URL**: `http://localhost:5000/api/notes`
3. **Send**: Review response

For POST requests:
1. **Method**: POST
2. **URL**: `http://localhost:5000/api/notes/txn-id/review`
3. **Headers**: Add `Content-Type: application/json`
4. **Body**: Raw JSON with review data
5. **Send**

---

**API Version**: 1.0.0
**Last Updated**: November 2025
