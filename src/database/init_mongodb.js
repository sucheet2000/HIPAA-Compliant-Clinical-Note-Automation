// Initialize MongoDB database for FHIR bundle storage
// This script creates collections and indexes for the clinical notes system

db = db.getSiblingDB('clinical_notes_fhir');

// Create FHIR Bundles collection
db.createCollection('fhir_bundles', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['transaction_id', 'bundle', 'created_at'],
            properties: {
                _id: { bsonType: 'objectId' },
                transaction_id: { bsonType: 'string', description: 'Unique transaction identifier' },
                bundle: { bsonType: 'object', description: 'FHIR Bundle resource' },
                confidence_score: { bsonType: 'decimal', description: 'Overall confidence score' },
                validation_status: {
                    bsonType: 'string',
                    enum: ['passed', 'failed', 'partial'],
                    description: 'FHIR validation status'
                },
                created_at: { bsonType: 'date', description: 'Creation timestamp' },
                updated_at: { bsonType: 'date', description: 'Last update timestamp' }
            }
        }
    }
});

// Create indexes for fast lookup
db.fhir_bundles.createIndex({ transaction_id: 1 }, { unique: true });
db.fhir_bundles.createIndex({ created_at: 1 });
db.fhir_bundles.createIndex({ 'bundle.type': 1 });
db.fhir_bundles.createIndex({ confidence_score: 1 });

// Create Clinical Notes collection (for future reference to original notes)
db.createCollection('clinical_notes', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['transaction_id', 'created_at'],
            properties: {
                _id: { bsonType: 'objectId' },
                transaction_id: { bsonType: 'string', description: 'Unique transaction identifier' },
                original_text: { bsonType: 'string', description: 'Original clinical note (optional)' },
                masked_text: { bsonType: 'string', description: 'De-identified clinical note' },
                structured_output: { bsonType: 'object', description: 'Claude extracted data' },
                created_at: { bsonType: 'date', description: 'Creation timestamp' }
            }
        }
    }
});

db.clinical_notes.createIndex({ transaction_id: 1 }, { unique: true });
db.clinical_notes.createIndex({ created_at: 1 });

// Create Clinician Reviews collection (for Phase 3)
db.createCollection('clinician_reviews', {
    validator: {
        $jsonSchema: {
            bsonType: 'object',
            required: ['transaction_id', 'action', 'reviewed_at'],
            properties: {
                _id: { bsonType: 'objectId' },
                transaction_id: { bsonType: 'string', description: 'Reference to transaction' },
                clinician_id: { bsonType: 'string', description: 'Clinician who performed review' },
                action: {
                    bsonType: 'string',
                    enum: ['approve', 'reject', 'flag_for_escalation'],
                    description: 'Review action taken'
                },
                notes: { bsonType: 'string', description: 'Clinician notes on review' },
                reviewed_at: { bsonType: 'date', description: 'Timestamp of review' }
            }
        }
    }
});

db.clinician_reviews.createIndex({ transaction_id: 1 });
db.clinician_reviews.createIndex({ reviewed_at: 1 });
db.clinician_reviews.createIndex({ clinician_id: 1 });

// Grant appropriate permissions to clinicaluser
db.createUser({
    user: 'clinicaluser',
    pwd: 'secure_password_change_me',
    roles: [
        { role: 'readWrite', db: 'clinical_notes_fhir' }
    ]
});

print('✅ MongoDB initialization complete');
