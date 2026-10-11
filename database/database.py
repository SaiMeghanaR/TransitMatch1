"""
DATABASE LAYER: database.py
File: database/database.py
Project: TransitMatch (Team BYTEFORCE - CBC006)
Domain: Software & Web Development
Problem Statement: PS-3 Public Transport Lost-and-Found Matching
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

DB_FILE = os.path.join(os.path.dirname(__file__), "transitmatch.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")

def get_db_connection():
    """Create a database connection with dict-like row access."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    """Initialize database tables using schema.sql."""
    with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    with get_db_connection() as conn:
        conn.executescript(schema_sql)
        conn.commit()

def mask_private_string(val):
    """Mask string for privacy-preserving public display."""
    if not val:
        return "Not Disclosed"
    val = str(val).strip()
    if len(val) <= 4:
        return "*** [Protected]"
    return val[:2] + "****" + val[-2:]

def add_item(data):
    """Insert a new lost or found report."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO items (
                report_type, user_id, reporter_name, reporter_contact,
                title, category, color, brand, description, image_url,
                route_vehicle, start_location, destination_location,
                incident_location, incident_time, current_depot,
                secret_clue, serial_number, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('report_type', 'lost'),
            data.get('user_id', 1),
            data.get('reporter_name', 'Anonymous Passenger'),
            data.get('reporter_contact', 'N/A'),
            data.get('title', 'Unknown Item'),
            data.get('category', 'General'),
            data.get('color', 'Unknown'),
            data.get('brand', 'Unknown'),
            data.get('description', ''),
            data.get('image_url', ''),
            data.get('route_vehicle', 'General Transit'),
            data.get('start_location', ''),
            data.get('destination_location', ''),
            data.get('incident_location', 'In Transit'),
            data.get('incident_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('current_depot', 'Pending Custody' if data.get('report_type') == 'found' else 'N/A'),
            data.get('secret_clue', ''),
            data.get('serial_number', ''),
            'REPORTED'
        ))
        item_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO status_history (item_id, previous_status, new_status, changed_by, actor_role, remarks)
            VALUES (?, NULL, 'REPORTED', ?, ?, ?)
        """, (
            item_id,
            data.get('reporter_name', 'System'),
            'passenger' if data.get('report_type') == 'lost' else 'staff',
            f"Initial {data.get('report_type', 'lost').upper()} report submitted into TransitMatch system."
        ))
        conn.commit()
        return item_id

def get_items(report_type=None, search_query=None, category=None, privacy_mode=True):
    """Retrieve items with optional privacy masking."""
    query = "SELECT * FROM items WHERE 1=1"
    params = []
    
    if report_type:
        query += " AND report_type = ?"
        params.append(report_type)
        
    if category and category != 'All':
        query += " AND category = ?"
        params.append(category)
        
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ? OR route_vehicle LIKE ? OR color LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])
        
    query += " ORDER BY id DESC"
    
    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
        items = []
        for row in rows:
            d = dict(row)
            if privacy_mode:
                d['secret_clue'] = "🔒 Hidden for Ownership Verification" if d.get('secret_clue') else "None Provided"
                d['serial_number'] = mask_private_string(d.get('serial_number')) if d.get('serial_number') else "None"
                d['reporter_contact'] = mask_private_string(d.get('reporter_contact'))
            items.append(d)
        return items

def get_item_by_id(item_id, privacy_mode=False):
    """Fetch a single item by ID."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        if privacy_mode:
            d['secret_clue'] = "🔒 Hidden for Ownership Verification" if d.get('secret_clue') else "None Provided"
            d['serial_number'] = mask_private_string(d.get('serial_number'))
            d['reporter_contact'] = mask_private_string(d.get('reporter_contact'))
        return d

def update_item_status(item_id, new_status, changed_by="Transit Staff", actor_role="staff", remarks=""):
    """Update item status with immutable audit logging."""
    with get_db_connection() as conn:
        curr = conn.execute("SELECT status FROM items WHERE id = ?", (item_id,)).fetchone()
        if not curr:
            return False
        prev_status = curr['status']
        
        conn.execute("""
            UPDATE items 
            SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_status, item_id))
        
        conn.execute("""
            INSERT INTO status_history (item_id, previous_status, new_status, changed_by, actor_role, remarks)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (item_id, prev_status, new_status, changed_by, actor_role, remarks))
        
        conn.commit()
        return True

def delete_item(item_id):
    """Delete an item report and related claim/match logs if found or canceled."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM matches WHERE lost_item_id = ? OR found_item_id = ?", (item_id, item_id))
        conn.execute("DELETE FROM claims WHERE lost_item_id = ? OR found_item_id = ?", (item_id, item_id))
        conn.execute("DELETE FROM status_history WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM incident_patterns WHERE item_id = ?", (item_id,))
        cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
        conn.commit()
        return cursor.rowcount > 0

def clear_all_items():
    """Wipe all item reports, claims, matches, and logs for a completely fresh registry."""
    with get_db_connection() as conn:
        conn.execute("DELETE FROM matches")
        conn.execute("DELETE FROM claims")
        conn.execute("DELETE FROM status_history")
        conn.execute("DELETE FROM incident_patterns")
        conn.execute("DELETE FROM items")
        conn.commit()
        return True

def create_claim(data):
    """Submit an ownership claim with secret clue verification."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO claims (
                lost_item_id, found_item_id, claimant_name, claimant_contact,
                submitted_secret_clue, supporting_proof_notes, clue_match_status,
                clue_similarity_score, is_disputed, staff_review_notes, claim_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('lost_item_id'),
            data.get('found_item_id'),
            data.get('claimant_name', 'Claimant'),
            data.get('claimant_contact', 'N/A'),
            data.get('submitted_secret_clue', ''),
            data.get('supporting_proof_notes', ''),
            data.get('clue_match_status', 'PENDING'),
            data.get('clue_similarity_score', 0.0),
            data.get('is_disputed', 0),
            data.get('staff_review_notes', ''),
            data.get('claim_status', 'SUBMITTED')
        ))
        claim_id = cursor.lastrowid
        
        conn.execute("""
            UPDATE items SET status = 'CLAIM_UNDER_VERIFICATION' WHERE id = ?
        """, (data.get('found_item_id'),))
        
        conn.execute("""
            INSERT INTO status_history (item_id, previous_status, new_status, changed_by, actor_role, remarks)
            VALUES (?, 'POTENTIAL_MATCH', 'CLAIM_UNDER_VERIFICATION', ?, 'passenger', ?)
        """, (
            data.get('found_item_id'),
            data.get('claimant_name', 'Passenger'),
            f"Ownership claim #{claim_id} lodged. Secret clue validation score: {data.get('clue_similarity_score', 0)}%"
        ))
        
        conn.commit()
        return claim_id

def get_claims_for_found_item(found_item_id):
    """Get all competing claims for a specific found item."""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM claims WHERE found_item_id = ? ORDER BY clue_similarity_score DESC, id ASC
        """, (found_item_id,)).fetchall()
        return [dict(r) for r in rows]

def get_status_history(item_id):
    """Get full audit history for an item."""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM status_history WHERE item_id = ? ORDER BY id ASC
        """, (item_id,)).fetchall()
        return [dict(r) for r in rows]

def save_match_record(lost_id, found_id, score, cat_score, col_score, br_score, jrn_score, nlp_score, breakdown_list):
    """Save or update matching score evaluation."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO matches (
                lost_item_id, found_item_id, confidence_score,
                category_score, color_score, brand_score,
                journey_score, nlp_similarity_score, reasons_breakdown
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(lost_item_id, found_item_id) DO UPDATE SET
                confidence_score = excluded.confidence_score,
                category_score = excluded.category_score,
                color_score = excluded.color_score,
                brand_score = excluded.brand_score,
                journey_score = excluded.journey_score,
                nlp_similarity_score = excluded.nlp_similarity_score,
                reasons_breakdown = excluded.reasons_breakdown,
                evaluated_at = CURRENT_TIMESTAMP
        """, (
            lost_id, found_id, score,
            cat_score, col_score, br_score,
            jrn_score, nlp_score, json.dumps(breakdown_list)
        ))
        conn.commit()

def record_incident_pattern(item_id, pattern_type, confidence, description):
    """Record an automated incident or duplicate pattern."""
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO incident_patterns (item_id, pattern_type, confidence, description)
            VALUES (?, ?, ?, ?)
        """, (item_id, pattern_type, confidence, description))
        conn.commit()

def get_incident_patterns():
    """Retrieve recent incident pattern flags."""
    with get_db_connection() as conn:
        rows = conn.execute("""
            SELECT p.*, i.title, i.route_vehicle, i.category, i.report_type
            FROM incident_patterns p
            LEFT JOIN items i ON p.item_id = i.id
            ORDER BY p.id DESC LIMIT 20
        """).fetchall()
        return [dict(r) for r in rows]

def get_dashboard_analytics():
    """Compute comprehensive dashboard KPIs, funnel metrics, and distributions."""
    with get_db_connection() as conn:
        total_items = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        lost_count = conn.execute("SELECT COUNT(*) FROM items WHERE report_type = 'lost'").fetchone()[0]
        found_count = conn.execute("SELECT COUNT(*) FROM items WHERE report_type = 'found'").fetchone()[0]
        
        status_rows = conn.execute("SELECT status, COUNT(*) as count FROM items GROUP BY status").fetchall()
        status_map = {row['status']: row['count'] for row in status_rows}
        
        verified_count = status_map.get('VERIFIED', 0)
        handed_over_count = status_map.get('HANDED_OVER', 0)
        potential_matches = status_map.get('POTENTIAL_MATCH', 0)
        claims_pending = status_map.get('CLAIM_UNDER_VERIFICATION', 0)
        
        resolved = verified_count + handed_over_count
        recovery_rate = round((resolved / max(1, lost_count)) * 100, 1)
        
        cat_rows = conn.execute("SELECT category, COUNT(*) as count FROM items GROUP BY category ORDER BY count DESC").fetchall()
        categories = [{"category": r["category"], "count": r["count"]} for r in cat_rows]
        
        route_rows = conn.execute("SELECT route_vehicle, COUNT(*) as count FROM items GROUP BY route_vehicle ORDER BY count DESC LIMIT 5").fetchall()
        routes = [{"route": r["route_vehicle"], "count": r["count"]} for r in route_rows]
        
        matches_count = conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0]
        claims_count = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        patterns_count = conn.execute("SELECT COUNT(*) FROM incident_patterns").fetchone()[0]
        
        recent_history = conn.execute("""
            SELECT h.*, i.title, i.route_vehicle
            FROM status_history h
            JOIN items i ON h.item_id = i.id
            ORDER BY h.id DESC LIMIT 8
        """).fetchall()
        
        return {
            "total_items": total_items,
            "lost_count": lost_count,
            "found_count": found_count,
            "verified_count": verified_count,
            "handed_over_count": handed_over_count,
            "potential_matches": potential_matches,
            "claims_pending": claims_pending,
            "recovery_rate": recovery_rate,
            "matches_evaluated": matches_count,
            "claims_lodged": claims_count,
            "patterns_count": patterns_count,
            "status_map": status_map,
            "categories": categories,
            "routes": routes,
            "recent_activities": [dict(r) for r in recent_history]
        }


def seed_demo_data():
    """Seed comprehensive realistic data matching CBC 2.0 slide examples."""
    init_db()
    with get_db_connection() as conn:
        count = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        if count > 0:
            return {"message": "Database already populated", "count": count}
    
    now = datetime.now()
    t1 = (now - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M')
    t2 = (now - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M')
    t3 = (now - timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')
    t4 = (now - timedelta(hours=6)).strftime('%Y-%m-%d %H:%M')
    t5 = (now - timedelta(days=1)).strftime('%Y-%m-%d %H:%M')

    # Seed Users
    with get_db_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO users (username, full_name, role, email, phone) VALUES ('passenger1', 'Rahul Sharma', 'passenger', 'rahul@example.com', '+91 9876543210')")
        conn.execute("INSERT OR IGNORE INTO users (username, full_name, role, email, phone) VALUES ('staff1', 'Officer Suresh Kumar', 'staff', 'suresh.transit@metro.org', '+91 9444123456')")
        conn.commit()

    # 1. Lost "Blue Bottle"
    add_item({
        'report_type': 'lost',
        'reporter_name': 'Rahul Sharma',
        'reporter_contact': '+91 9876543210',
        'title': 'Blue Bottle',
        'category': 'Personal Accessories',
        'color': 'Blue',
        'brand': 'Milton',
        'description': 'Left my blue insulated water bottle under seat 14. Has a slight scratch at the bottom.',
        'route_vehicle': 'Metro Purple Line',
        'start_location': 'MG Road Station',
        'destination_location': 'Indiranagar',
        'incident_location': 'Metro Coach C3, Seat 14',
        'incident_time': t1,
        'secret_clue': 'Scratch on base ring and an astronaut cartoon sticker near cap',
        'serial_number': 'N/A'
    })

    # 2. Found "Dark-Blue Metal Bottle"
    add_item({
        'report_type': 'found',
        'reporter_name': 'Depot Officer Suresh',
        'reporter_contact': '+91 9444123456',
        'title': 'Dark-Blue Metal Bottle',
        'category': 'Personal Accessories',
        'color': 'Dark Blue',
        'brand': 'Milton Thermosteel',
        'description': 'Dark-blue metallic thermos bottle recovered by sweep crew at terminus depot.',
        'route_vehicle': 'Metro Purple Line',
        'start_location': 'MG Road Station',
        'destination_location': 'Baiyappanahalli Terminal',
        'incident_location': 'Coach C3 floor',
        'incident_time': t2,
        'current_depot': 'Baiyappanahalli Metro Lost & Found Office (Depot Locker #12)',
        'secret_clue': 'Astronaut sticker on upper ring, dented base ring',
        'serial_number': 'N/A'
    })

    # 3. Lost Wallet
    lost_wallet_id = add_item({
        'report_type': 'lost',
        'reporter_name': 'Amit Verma',
        'reporter_contact': '+91 9777123987',
        'title': 'Brown Leather Wallet',
        'category': 'Wallets & Bags',
        'color': 'Brown',
        'brand': 'WildHorn',
        'description': 'Brown leather bifold wallet with cards and college ID slip inside.',
        'route_vehicle': 'BMTC Bus Route 204',
        'start_location': 'Majestic Bus Stand',
        'destination_location': 'Electronic City',
        'incident_location': 'Bus 204 Upper Deck Rear',
        'incident_time': t3,
        'secret_clue': 'BITM College student library card #BITM-2024-889 in hidden fold',
        'serial_number': 'ID# BITM-2024-889'
    })

    # 4. Found Wallet
    add_item({
        'report_type': 'found',
        'reporter_name': 'Conductor Ramesh',
        'reporter_contact': '+91 9555112233',
        'title': 'Found Men Leather Wallet (Tan Brown)',
        'category': 'Wallets & Bags',
        'color': 'Brown',
        'brand': 'WildHorn Genuine Leather',
        'description': 'Found brown men wallet with some cash and student identification cards.',
        'route_vehicle': 'BMTC Bus Route 204',
        'start_location': 'Majestic Bus Stand',
        'destination_location': 'Electronic City Depot',
        'incident_location': 'Seat 28 Bus 204',
        'incident_time': t4,
        'current_depot': 'Electronic City Depot Lost & Found Counter #3',
        'secret_clue': 'Student library card from BITM College inside fold',
        'serial_number': 'Protected Student ID'
    })

    # 5. Express Train Laptop Bag
    found_laptop_id = add_item({
        'report_type': 'found',
        'reporter_name': 'RPF Inspector Khan',
        'reporter_contact': '+91 9333998877',
        'title': 'Black Dell Backpack with Laptop',
        'category': 'Electronics',
        'color': 'Black',
        'brand': 'Dell',
        'description': 'Padded black laptop backpack containing 15-inch Dell laptop and charging cable.',
        'route_vehicle': 'Express Train 126',
        'start_location': 'Hubballi Junction',
        'destination_location': 'Ballari Central Station',
        'incident_location': 'Coach B2 Berth 45',
        'incident_time': t5,
        'current_depot': 'Ballari Junction RPF Custody Room',
        'secret_clue': 'Silver HP pendrive attached to interior zipper tag',
        'serial_number': 'DELL-SN-7890-XX'
    })

    # 6. Duplicate Edge Case
    lost_dup_id = add_item({
        'report_type': 'lost',
        'reporter_name': 'Amit Brother (Anil Verma)',
        'reporter_contact': '+91 9777999888',
        'title': 'Lost Brown Leather Wallet Wildhorn',
        'category': 'Wallets & Bags',
        'color': 'Brown',
        'brand': 'WildHorn',
        'description': 'My brother lost his brown leather wallet on Bus 204 towards Electronic City.',
        'route_vehicle': 'BMTC Bus Route 204',
        'start_location': 'Majestic Bus Stand',
        'destination_location': 'Electronic City',
        'incident_location': 'Bus 204',
        'incident_time': t3,
        'secret_clue': 'Contains BITM college card',
        'serial_number': 'BITM-2024-889'
    })

    record_incident_pattern(
        lost_dup_id,
        'DUPLICATE_REPORT',
        92.5,
        f"Cross-report duplicate detected: Report #{lost_dup_id} matches Lost Report #{lost_wallet_id} on Bus Route 204 with 92.5% similarity."
    )
    record_incident_pattern(
        found_laptop_id,
        'HIGH_VALUE_ELECTRONICS',
        88.0,
        "High-value unattended electronic property registered in Ballari Station RPF custody requiring Level-2 verification."
    )

    return {"message": "Demo scenario seeded successfully", "items_count": 6}

if __name__ == '__main__':
    init_db()
    seed_demo_data()
    print("Database ready.")
