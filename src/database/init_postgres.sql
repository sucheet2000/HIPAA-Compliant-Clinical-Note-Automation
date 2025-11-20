-- Initialize PostgreSQL database for HIPAA-compliant clinical notes system
-- This script creates all necessary tables for audit logging and transaction tracking

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Audit Log Table - Immutable record of all compliance-relevant events
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    transaction_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    user_id VARCHAR(100),
    ip_address VARCHAR(45),
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index on transaction_id for fast lookups
CREATE INDEX idx_audit_transaction_id ON audit_logs(transaction_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_event_type ON audit_logs(event_type);

-- De-identification Event Log
CREATE TABLE IF NOT EXISTS deidentification_events (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL UNIQUE,
    original_text_length INTEGER,
    masked_text_length INTEGER,
    redaction_counts JSONB,
    validation_safe BOOLEAN,
    validation_report JSONB,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES audit_logs(transaction_id)
);

CREATE INDEX idx_deidentification_transaction ON deidentification_events(transaction_id);

-- Claude API Call Log
CREATE TABLE IF NOT EXISTS claude_api_calls (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL UNIQUE,
    request_tokens INTEGER,
    response_tokens INTEGER,
    total_tokens INTEGER,
    model VARCHAR(50),
    status VARCHAR(20),
    error_message TEXT,
    confidence_score DECIMAL(5, 2),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES audit_logs(transaction_id)
);

CREATE INDEX idx_claude_transaction ON claude_api_calls(transaction_id);

-- FHIR Transformation Log
CREATE TABLE IF NOT EXISTS fhir_transformations (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL UNIQUE,
    input_length INTEGER,
    bundle_length INTEGER,
    resources_created JSONB,
    validation_passed BOOLEAN,
    validation_errors TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES audit_logs(transaction_id)
);

CREATE INDEX idx_fhir_transaction ON fhir_transformations(transaction_id);

-- Clinician Review Log (for Phase 3 UI)
CREATE TABLE IF NOT EXISTS clinician_reviews (
    id SERIAL PRIMARY KEY,
    transaction_id UUID NOT NULL,
    clinician_id VARCHAR(100),
    action VARCHAR(20) NOT NULL,  -- 'approve', 'reject', 'flag_for_escalation'
    notes TEXT,
    review_timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES audit_logs(transaction_id)
);

CREATE INDEX idx_clinician_reviews_transaction ON clinician_reviews(transaction_id);
CREATE INDEX idx_clinician_reviews_timestamp ON clinician_reviews(review_timestamp);

-- Transaction Summary Table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL,  -- 'pending', 'success', 'failure'
    input_length INTEGER,
    output_length INTEGER,
    stages_completed JSONB,
    total_duration_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created ON transactions(created_at);

-- Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO clinicaluser;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO clinicaluser;
