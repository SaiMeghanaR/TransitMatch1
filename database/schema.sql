-- ====================================================================
-- DATABASE LAYER: schema.sql
-- File: database/schema.sql
-- Project: TransitMatch (Team BYTEFORCE - CBC006)
-- Problem Statement: PS-3 Public Transport Lost-and-Found Matching
-- ====================================================================

-- 1. Users Table (Role-based access: passenger, staff, admin)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('passenger', 'staff', 'admin')),
    email TEXT,
    phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Items Table (Lost & Found transit reports)
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL CHECK(report_type IN ('lost', 'found')),
    user_id INTEGER,
    reporter_name TEXT NOT NULL,
    reporter_contact TEXT NOT NULL,
    
    -- Structured Item Characteristics
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    color TEXT NOT NULL,
    brand TEXT,
    description TEXT NOT NULL,
    image_url TEXT,
    
    -- Transit Journey Context
    route_vehicle TEXT NOT NULL,       -- e.g., "Metro Purple Line", "BMTC Bus 204"
    start_location TEXT,               -- Boarding / Origin Stop
    destination_location TEXT,         -- Destination Stop
    incident_location TEXT NOT NULL,   -- Coach, Seat, Platform, or Depot
    incident_time TIMESTAMP NOT NULL,  -- Incident Date & Time
    current_depot TEXT,                -- Depot custody storage location
    
    -- Confidential Verification Attributes
    secret_clue TEXT,                  -- Private owner mark (dent, custom sticker, etc.)
    serial_number TEXT,                -- Serial ID, IMEI, or student card number
    
    -- Status Lifecycle
    status TEXT NOT NULL DEFAULT 'REPORTED' CHECK(status IN (
        'REPORTED',
        'POTENTIAL_MATCH',
        'CLAIM_UNDER_VERIFICATION',
        'VERIFIED',
        'HANDED_OVER',
        'CLOSED'
    )),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

-- 3. Match Evaluations Table (Cached match scores & breakdown)
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_item_id INTEGER NOT NULL,
    found_item_id INTEGER NOT NULL,
    confidence_score REAL NOT NULL,    -- 0.0 to 100.0%
    category_score REAL,
    color_score REAL,
    brand_score REAL,
    journey_score REAL,
    nlp_similarity_score REAL,
    status TEXT DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'ACCEPTED', 'REJECTED')),
    reasons_breakdown TEXT,            -- JSON breakdown of scoring points
    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(lost_item_id) REFERENCES items(id) ON DELETE CASCADE,
    FOREIGN KEY(found_item_id) REFERENCES items(id) ON DELETE CASCADE,
    UNIQUE(lost_item_id, found_item_id)
);

-- 4. Claims Table (Secret-clue verification & multiple claimant dispute resolution)
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lost_item_id INTEGER,
    found_item_id INTEGER NOT NULL,
    claimant_name TEXT NOT NULL,
    claimant_contact TEXT NOT NULL,
    
    submitted_secret_clue TEXT NOT NULL,
    supporting_proof_notes TEXT,
    clue_match_status TEXT DEFAULT 'PENDING' CHECK(clue_match_status IN (
        'MATCHED',
        'PARTIAL_MATCH',
        'MISMATCH',
        'PENDING_STAFF'
    )),
    clue_similarity_score REAL DEFAULT 0.0,
    
    is_disputed BOOLEAN DEFAULT 0,
    staff_review_notes TEXT,
    claim_status TEXT DEFAULT 'SUBMITTED' CHECK(claim_status IN (
        'SUBMITTED',
        'IN_REVIEW',
        'APPROVED',
        'REJECTED'
    )),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP,
    FOREIGN KEY(lost_item_id) REFERENCES items(id),
    FOREIGN KEY(found_item_id) REFERENCES items(id)
);

-- 5. Status Audit History (Immutable audit logging)
CREATE TABLE IF NOT EXISTS status_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    remarks TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE
);

-- 6. Incident Patterns & Duplicate Flags
CREATE TABLE IF NOT EXISTS incident_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id INTEGER,
    pattern_type TEXT NOT NULL,        -- 'DUPLICATE_REPORT', 'HIGH_LOSS_ROUTE', 'UNCLAIMED_CLUSTER'
    confidence REAL DEFAULT 0.0,
    description TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(item_id) REFERENCES items(id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_items_report_type ON items(report_type);
CREATE INDEX IF NOT EXISTS idx_items_category ON items(category);
CREATE INDEX IF NOT EXISTS idx_items_route ON items(route_vehicle);
CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_matches_lost ON matches(lost_item_id);
CREATE INDEX IF NOT EXISTS idx_matches_found ON matches(found_item_id);
CREATE INDEX IF NOT EXISTS idx_history_item ON status_history(item_id);
