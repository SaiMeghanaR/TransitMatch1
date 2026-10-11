"""
BACKEND LAYER: app.py
File: backend/app.py
Project: TransitMatch (Team BYTEFORCE - CBC006)
College: Ballari Institute of Technology and Management
Domain: Software & Web Development
Problem Statement: PS-3 Public Transport Lost-and-Found Matching

Flask Server, REST API & Intelligence Engine:
- Serves Frontend from ../frontend/
- Database operations via ../database/database.py
- Multi-attribute matching (Category, Color, Brand, Journey, Time, TF-IDF NLP)
- Secret clue verification algorithm
- Cross-report duplicate & pattern detection
- Item status management, verified handover, and item deletion
"""

import os
import sys
import math
import re
from datetime import datetime
from collections import Counter
from flask import Flask, send_from_directory, request, jsonify

# Setup paths to connect separate folders
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')
DATABASE_DIR = os.path.join(BASE_DIR, 'database')

if DATABASE_DIR not in sys.path:
    sys.path.insert(0, DATABASE_DIR)

import database

# -------------------------------------------------------------
# INTELLIGENT MATCHING & NLP ENGINE (BUILT-IN)
# -------------------------------------------------------------
STOPWORDS = {
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your',
    'he', 'him', 'his', 'she', 'her', 'it', 'its', 'they', 'them', 'their',
    'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or',
    'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about',
    'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again',
    'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all'
}

COLOR_SYNONYMS = {
    'blue': {'blue', 'dark-blue', 'dark blue', 'navy', 'navy-blue', 'sky-blue', 'cyan', 'azure', 'indigo'},
    'black': {'black', 'charcoal', 'jet-black', 'matte-black', 'dark'},
    'brown': {'brown', 'tan', 'leather', 'coffee', 'chocolate', 'camel', 'khaki'},
    'red': {'red', 'maroon', 'crimson', 'burgundy', 'scarlet'},
    'silver': {'silver', 'grey', 'gray', 'metallic', 'chrome', 'steel', 'metal'},
    'white': {'white', 'cream', 'ivory', 'off-white'},
    'green': {'green', 'olive', 'emerald', 'mint', 'lime'}
}

def tokenize(text):
    if not text:
        return []
    words = re.findall(r'[a-zA-Z0-9]+', text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]

class SimpleTFIDF:
    def __init__(self, documents):
        self.documents = [tokenize(doc) for doc in documents]
        self.doc_count = len(self.documents)
        self.vocab = set(w for doc in self.documents for w in doc)
        self.idf = {}
        for term in self.vocab:
            df = sum(1 for doc in self.documents if term in doc)
            self.idf[term] = math.log((self.doc_count + 1) / (df + 1)) + 1.0

    def vectorize(self, text):
        tokens = tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        total_tokens = len(tokens)
        vector = {}
        for term, count in tf.items():
            if term in self.idf:
                vector[term] = (count / total_tokens) * self.idf[term]
            else:
                vector[term] = (count / total_tokens) * 1.0
        return vector

    @staticmethod
    def cosine_similarity(vec1, vec2):
        if not vec1 or not vec2:
            return 0.0
        dot_product = sum(vec1.get(t, 0.0) * vec2.get(t, 0.0) for t in set(vec1.keys()) & set(vec2.keys()))
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot_product / (norm1 * norm2)

def color_similarity(c1, c2):
    if not c1 or not c2:
        return 0.0
    c1, c2 = c1.lower().strip(), c2.lower().strip()
    if c1 == c2:
        return 1.0
    if c1 in c2 or c2 in c1:
        return 0.85
    for cluster in COLOR_SYNONYMS.values():
        if c1 in cluster and c2 in cluster:
            return 0.90
    return 0.0

def brand_similarity(b1, b2):
    if not b1 or not b2:
        return 0.3
    b1, b2 = b1.lower().strip(), b2.lower().strip()
    if b1 == b2:
        return 1.0
    if b1 in b2 or b2 in b1:
        return 0.85
    t1, t2 = set(tokenize(b1)), set(tokenize(b2))
    if t1 and t2 and (t1 & t2):
        return 0.75
    return 0.0

def journey_similarity(lost, found):
    score = 0.0
    factors = []
    r1 = (lost.get('route_vehicle') or '').strip().lower()
    r2 = (found.get('route_vehicle') or '').strip().lower()
    
    if r1 and r2:
        if r1 == r2:
            score += 0.55
            factors.append("Identical Transit Route/Vehicle")
        elif r1 in r2 or r2 in r1:
            score += 0.45
            factors.append("Transit Route Line Matched")
        else:
            toks1, toks2 = set(tokenize(r1)), set(tokenize(r2))
            if toks1 & toks2:
                score += 0.30
                factors.append("Shared Route Identifier")

    stops1 = f"{lost.get('start_location','')} {lost.get('destination_location','')} {lost.get('incident_location','')}".lower()
    stops2 = f"{found.get('start_location','')} {found.get('destination_location','')} {found.get('incident_location','')} {found.get('current_depot','')}".lower()
    common_stops = set(tokenize(stops1)) & set(tokenize(stops2))
    if common_stops:
        overlap_ratio = min(1.0, len(common_stops) / 2.0)
        score += 0.45 * overlap_ratio
        factors.append(f"Station/Depot alignment ({', '.join(list(common_stops)[:2])})")
        
    return min(1.0, score), factors

def time_proximity_score(t1_str, t2_str):
    if not t1_str or not t2_str:
        return 0.5, "Estimated timeframe"
    formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%dT%H:%M']
    dt1, dt2 = None, None
    for fmt in formats:
        try:
            dt1 = datetime.strptime(str(t1_str).split('.')[0], fmt)
            break
        except Exception:
            pass
    for fmt in formats:
        try:
            dt2 = datetime.strptime(str(t2_str).split('.')[0], fmt)
            break
        except Exception:
            pass
            
    if not dt1 or not dt2:
        return 0.6, "Timeframe approximate"
        
    diff_hours = abs((dt1 - dt2).total_seconds()) / 3600.0
    if diff_hours <= 6:
        return 1.0, f"Same day incident ({int(diff_hours)}h gap)"
    elif diff_hours <= 24:
        return 0.85, f"Within 24 hours ({int(diff_hours)}h gap)"
    elif diff_hours <= 72:
        return 0.60, f"Within 3 days ({int(diff_hours/24)}d gap)"
    elif diff_hours <= 168:
        return 0.35, "Within 1 week"
    else:
        return 0.15, "Over 1 week difference"

def calculate_match(lost_item, found_item, tfidf_engine=None):
    breakdown = []
    
    # Category (25%)
    cat_lost = (lost_item.get('category') or '').lower().strip()
    cat_found = (found_item.get('category') or '').lower().strip()
    cat_score = 1.0 if (cat_lost == cat_found and cat_lost) else 0.0
    breakdown.append({
        "factor": "Category Match", "weight": 25, "earned": cat_score * 25.0,
        "note": f"Both '{lost_item.get('category')}'" if cat_score else f"Mismatch ({cat_lost} vs {cat_found})"
    })
    
    # Color (15%)
    col_score = color_similarity(lost_item.get('color'), found_item.get('color'))
    col_earned = round(col_score * 15.0, 1)
    breakdown.append({
        "factor": "Color Affinity", "weight": 15, "earned": col_earned,
        "note": f"'{lost_item.get('color')}' vs '{found_item.get('color')}' ({int(col_score*100)}% match)"
    })
    
    # Brand (15%)
    br_score = brand_similarity(lost_item.get('brand'), found_item.get('brand'))
    br_earned = round(br_score * 15.0, 1)
    breakdown.append({
        "factor": "Brand Compatibility", "weight": 15, "earned": br_earned,
        "note": f"'{lost_item.get('brand') or 'N/A'}' vs '{found_item.get('brand') or 'N/A'}'"
    })
    
    # Journey & Route (20%)
    jrn_score, jrn_factors = journey_similarity(lost_item, found_item)
    jrn_earned = round(jrn_score * 20.0, 1)
    breakdown.append({
        "factor": "Transit Route & Journey", "weight": 20, "earned": jrn_earned,
        "note": ", ".join(jrn_factors) if jrn_factors else "Route mismatch"
    })
    
    # Time Proximity (10%)
    time_score, time_note = time_proximity_score(lost_item.get('incident_time'), found_item.get('incident_time'))
    time_earned = round(time_score * 10.0, 1)
    breakdown.append({
        "factor": "Temporal Window", "weight": 10, "earned": time_earned, "note": time_note
    })
    
    # TF-IDF NLP Text Similarity (15%)
    doc1 = f"{lost_item.get('title','')} {lost_item.get('description','')}"
    doc2 = f"{found_item.get('title','')} {found_item.get('description','')}"
    if tfidf_engine:
        nlp_score = tfidf_engine.cosine_similarity(tfidf_engine.vectorize(doc1), tfidf_engine.vectorize(doc2))
    else:
        t1, t2 = set(tokenize(doc1)), set(tokenize(doc2))
        nlp_score = len(t1 & t2) / max(1, len(t1 | t2))
    nlp_earned = round(nlp_score * 15.0, 1)
    breakdown.append({
        "factor": "NLP Description Similarity (TF-IDF)", "weight": 15, "earned": nlp_earned,
        "note": f"{int(nlp_score * 100)}% descriptive text similarity"
    })
    
    total_score = round(cat_score * 25.0 + col_earned + br_earned + jrn_earned + time_earned + nlp_earned, 1)
    total_score = max(0.0, min(100.0, total_score))
    
    tier = "HIGH_CONFIDENCE_MATCH" if total_score >= 75.0 else ("PROBABLE_MATCH" if total_score >= 50.0 else "WEAK_MATCH")
    badge = "High Probability Match" if total_score >= 75.0 else ("Probable Candidate" if total_score >= 50.0 else "Low / Partial Match")
    
    return {
        "confidence_score": total_score, "tier": tier, "badge": badge,
        "category_score": cat_score, "color_score": col_score, "brand_score": br_score,
        "journey_score": jrn_score, "time_score": time_score, "nlp_similarity_score": nlp_score,
        "breakdown": breakdown
    }

def verify_secret_clue(actual_secret_clue, claimant_provided_clue):
    if not actual_secret_clue or not claimant_provided_clue:
        return {"status": "INSUFFICIENT_EVIDENCE", "score": 0.0, "message": "Secret clue detail missing.", "requires_staff_review": True}
        
    act_tokens = set(tokenize(actual_secret_clue))
    claim_tokens = set(tokenize(claimant_provided_clue))
    if not act_tokens or not claim_tokens:
        return {"status": "MISMATCH", "score": 0.0, "message": "Could not verify tokens.", "requires_staff_review": True}
        
    common = act_tokens & claim_tokens
    recall = len(common) / len(act_tokens)
    precision = len(common) / len(claim_tokens)
    score = round((0.7 * recall + 0.3 * precision) * 100.0, 1)
    
    if score >= 60.0 or len(common) >= 2:
        return {"status": "MATCHED", "score": max(75.0, score), "message": f"Ownership verified! {len(common)} private identifiers matched.", "requires_staff_review": False}
    elif score >= 30.0 or len(common) >= 1:
        return {"status": "PARTIAL_MATCH", "score": score, "message": "Partial secret clue match. Staff manual check advised.", "requires_staff_review": True}
    else:
        return {"status": "MISMATCH", "score": score, "message": "Provided details do not match custody records.", "requires_staff_review": True}

def analyze_incident_patterns(items_list):
    patterns = []
    lost_items = [i for i in items_list if i.get('report_type') == 'lost']
    for i in range(len(lost_items)):
        for j in range(i + 1, len(lost_items)):
            a, b = lost_items[i], lost_items[j]
            if a.get('category') == b.get('category') and a.get('route_vehicle') == b.get('route_vehicle'):
                ta = set(tokenize(f"{a.get('title','')} {a.get('description','')}"))
                tb = set(tokenize(f"{b.get('title','')} {b.get('description','')}"))
                if ta and tb:
                    overlap = len(ta & tb) / min(len(ta), len(tb))
                    if overlap >= 0.5:
                        patterns.append({
                            "type": "DUPLICATE_REPORT", "confidence": round(overlap * 100, 1),
                            "item_id": a.get('id'), "related_id": b.get('id'), "route": a.get('route_vehicle'),
                            "description": f"Reports #{a.get('id')} and #{b.get('id')} may refer to the same lost {a.get('category')} on {a.get('route_vehicle')}."
                        })
    route_counter = Counter(i.get('route_vehicle') for i in items_list if i.get('route_vehicle'))
    for route, count in route_counter.items():
        if count >= 3:
            patterns.append({
                "type": "HIGH_LOSS_ROUTE", "confidence": 90.0, "item_id": None, "route": route,
                "description": f"Transit Route '{route}' has {count} active incidents logged. Flagged for transit security."
            })
    return patterns

FAQ_KB = {
    'en': {
        'greeting': "Hello! I am TransitMatch AI Assistant. I help you report lost belongings, match found items across buses & trains, and verify ownership.",
        'how_to_report': "Click 'Report Lost Item', provide your transit route, date/time, and a 'Secret Clue' (hidden mark/sticker) so only you can claim it!",
        'how_to_claim': "Find your item in the registry, click 'Claim Item', and submit your Secret Clue to prove ownership.",
        'depot': "Found items are stored in station depots within 12 hours. Check the custody depot location on the item card.",
        'fallback': "I can help you report lost belongings, check found items across buses & trains, or verify ownership."
    },
    'hi': {
        'greeting': "नमस्ते! मैं ट्रांजिटमैच एआई सहायक हूँ। खोए या मिले सामान की रिपोर्टिंग और सत्यापन में आपकी मदद कर सकता हूँ।",
        'how_to_report': "'Report Lost Item' पर क्लिक करें, रूट और समय भरें, और अपना गुप्त निशान (सीक्रेट क्लू) दर्ज करें।",
        'how_to_claim': "सामान का दावा करने के लिए: 'Claim Item' दबाएं और अपना सीक्रेट क्लू दर्ज करें।",
        'depot': "मिला हुआ सामान संबंधित स्टेशन डिपो या लॉस्ट एंड फाउंड काउंटर पर सुरक्षित जमा रहता है।",
        'fallback': "कृपया बताएं कि आपका सामान किस बस या मेट्रो रूट पर खोया था।"
    },
    'kn': {
        'greeting': "ನಮಸ್ಕಾರ! ನಾನು ಟ್ರಾನ್ಸಿಟ್‌ಮ್ಯಾಚ್ ಎಐ ಸಹಾಯಕ. ಬಸ್ ಮತ್ತು ಮೆಟ್ರೋದಲ್ಲಿ ಕಳೆದುಹೋದ ವಸ್ತುಗಳನ್ನು ಪತ್ತೆಹಚ್ಚಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.",
        'how_to_report': "'Report Lost Item' ಕ್ಲಿಕ್ ಮಾಡಿ, ನಿಮ್ಮ ಬಸ್/ಮೆಟ್ರೋ ಮಾರ್ಗ ಮತ್ತು ರಹಸ್ಯ ಗುರುತನ್ನು (Secret Clue) ನಮೂದಿಸಿ.",
        'how_to_claim': "ಪತ್ತೆಯಾದ ವಸ್ತುವನ್ನು ಪಡೆಯಲು 'Claim Item' ಒತ್ತಿ ರಹಸ್ಯ ವಿವರಗಳನ್ನು ನೀಡಿ.",
        'depot': "ದೊರೆತ ವಸ್ತುಗಳನ್ನು ನಿಲ್ದಾಣದ ಲಾಸ್ಟ್ & ಫೌಂಡ್ ಕೌಂಟರ್‌ನಲ್ಲಿ ಸುರಕ್ಷಿತವಾಗಿ ಇರಿಸಲಾಗುತ್ತದೆ.",
        'fallback': "ನಿಮ್ಮ ಕಳೆದುಹೋದ ವಸ್ತು ಅಥವಾ ಪ್ರಯಾಣದ ವಿವರಗಳನ್ನು ಹಂಚಿಕೊಳ್ಳಿ."
    }
}

def get_chatbot_response(message, language='en'):
    msg_lower = (message or '').lower().strip()
    kb = FAQ_KB.get(language, FAQ_KB['en'])
    if any(w in msg_lower for w in ['hi', 'hello', 'hey', 'start', 'namaste', 'namaskara']):
        return kb['greeting']
    elif any(w in msg_lower for w in ['how to report', 'lost item', 'report', 'lost my']):
        return kb['how_to_report']
    elif any(w in msg_lower for w in ['claim', 'verify', 'ownership', 'secret clue', 'clue']):
        return kb['how_to_claim']
    elif any(w in msg_lower for w in ['depot', 'office', 'where is', 'pickup']):
        return kb['depot']
    return f"{kb['fallback']} (Use the top tabs to lodge reports or check match rankings)."

# -------------------------------------------------------------
# FLASK APPLICATION & ROUTER
# -------------------------------------------------------------
app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path='',
    template_folder=FRONTEND_DIR,
)

with app.app_context():
    database.init_db()

@app.route('/')
def home():
    """Serves the frontend/index.html web page."""
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/api/auth/login', methods=['POST'])
def login_api():
    """Secure role authentication: validates Staff Passcode or Admin Master Key."""
    data = request.get_json() or {}
    role = data.get('role', 'passenger').lower()
    passcode = data.get('passcode', '').strip()
    
    if role == 'staff':
        if passcode in ['staff123', 'STAFF101', 'STAFF2024']:
            return jsonify({
                "success": True,
                "role": "staff",
                "name": "Officer Suresh Kumar",
                "title": "Depot Custody Officer",
                "depot": "Central Terminal Depot",
                "message": "Staff badge verified. Depot custody operations unlocked."
            })
        return jsonify({"success": False, "error": "Invalid Staff Passcode. (Default: staff123)"}), 401
        
    elif role == 'admin':
        if passcode in ['admin123', 'ADMIN2024']:
            return jsonify({
                "success": True,
                "role": "admin",
                "name": "Transit Authority Supervisor",
                "title": "System Administrator",
                "message": "Admin Master Key verified. Executive controls unlocked."
            })
        return jsonify({"success": False, "error": "Invalid Admin Key. (Default: admin123)"}), 401
        
    return jsonify({"success": True, "role": "passenger", "name": "Commuter", "message": "Passenger mode active."})

@app.route('/api/admin/clear-all', methods=['POST'])
def clear_all_items_api():
    """Wipes all item records, claims, and history for a fresh registry."""
    database.clear_all_items()
    return jsonify({"success": True, "message": "All item reports and logs wiped clean."})


@app.route('/api/items', methods=['GET'])
def get_items_api():
    report_type = request.args.get('type')
    search_q = request.args.get('q')
    category = request.args.get('category')
    user_role = request.args.get('role', 'passenger').lower()
    
    privacy_mode = False if user_role in ['staff', 'admin'] else True
    items = database.get_items(report_type, search_q, category, privacy_mode)
    return jsonify({"success": True, "count": len(items), "items": items})

@app.route('/api/items/<int:item_id>', methods=['GET'])
def get_item_detail_api(item_id):
    user_role = request.args.get('role', 'passenger').lower()
    privacy_mode = False if user_role in ['staff', 'admin'] else True
    item = database.get_item_by_id(item_id, privacy_mode)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404
    return jsonify({"success": True, "item": item})

@app.route('/api/items/lost', methods=['POST'])
def report_lost_item():
    data = request.get_json() or {}
    if not data.get('title') or not data.get('category') or not data.get('route_vehicle'):
        return jsonify({"success": False, "error": "Title, Category, and Route/Vehicle are required."}), 400
    data['report_type'] = 'lost'
    item_id = database.add_item(data)
    
    all_items = database.get_items(privacy_mode=False)
    for p in analyze_incident_patterns(all_items):
        if p.get('item_id') == item_id or p.get('related_id') == item_id:
            database.record_incident_pattern(item_id, p['type'], p['confidence'], p['description'])
            
    return jsonify({"success": True, "message": f"Lost item report lodged (ID: #{item_id}).", "item_id": item_id}), 201

@app.route('/api/items/found', methods=['POST'])
def report_found_item():
    data = request.get_json() or {}
    if not data.get('title') or not data.get('category') or not data.get('route_vehicle'):
        return jsonify({"success": False, "error": "Title, Category, and Route/Vehicle are required."}), 400
    data['report_type'] = 'found'
    item_id = database.add_item(data)
    return jsonify({"success": True, "message": f"Found item registered in custody (ID: #{item_id}).", "item_id": item_id}), 201

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def delete_item_api(item_id):
    """Delete an item report (e.g. if resolved, found, or cancelled)."""
    success = database.delete_item(item_id)
    if not success:
        return jsonify({"success": False, "error": "Item not found or already removed."}), 404
    return jsonify({"success": True, "message": f"Report #{item_id} deleted successfully."})

@app.route('/api/matches/<int:item_id>', methods=['GET'])
def get_item_matches(item_id):
    target = database.get_item_by_id(item_id, privacy_mode=False)
    if not target:
        return jsonify({"success": False, "error": "Target item not found"}), 404
        
    candidate_type = 'found' if target['report_type'] == 'lost' else 'lost'
    candidates = database.get_items(report_type=candidate_type, privacy_mode=False)
    if not candidates:
        return jsonify({"success": True, "target": target, "matches": [], "message": f"No {candidate_type} items in registry."})
        
    all_texts = [f"{c.get('title','')} {c.get('description','')}" for c in candidates]
    all_texts.append(f"{target.get('title','')} {target.get('description','')}")
    tfidf = SimpleTFIDF(all_texts)
    
    results = []
    for cand in candidates:
        lost_obj = target if target['report_type'] == 'lost' else cand
        found_obj = cand if target['report_type'] == 'lost' else target
        
        match_result = calculate_match(lost_obj, found_obj, tfidf_engine=tfidf)
        database.save_match_record(
            lost_obj['id'], found_obj['id'],
            match_result['confidence_score'], match_result['category_score'],
            match_result['color_score'], match_result['brand_score'],
            match_result['journey_score'], match_result['nlp_similarity_score'],
            match_result['breakdown']
        )
        masked = dict(cand)
        masked['secret_clue'] = "🔒 Hidden for Ownership Verification"
        results.append({"candidate": masked, "match_evaluation": match_result})
        
    results.sort(key=lambda x: x['match_evaluation']['confidence_score'], reverse=True)
    if results and results[0]['match_evaluation']['confidence_score'] >= 60.0 and target['status'] == 'REPORTED':
        database.update_item_status(
            item_id, 'POTENTIAL_MATCH', changed_by="TransitMatch AI Engine",
            actor_role="admin", remarks=f"High-confidence candidate #{results[0]['candidate']['id']} identified ({results[0]['match_evaluation']['confidence_score']}%)."
        )
    return jsonify({"success": True, "target": target, "match_count": len(results), "matches": results})

@app.route('/api/claims/verify', methods=['POST'])
def verify_claim_api():
    data = request.get_json() or {}
    found_item_id = data.get('found_item_id')
    claimant_clue = data.get('secret_clue', '')
    claimant_name = data.get('claimant_name', 'Claimant')
    claimant_contact = data.get('claimant_contact', 'N/A')
    lost_item_id = data.get('lost_item_id')
    
    found_item = database.get_item_by_id(found_item_id, privacy_mode=False)
    if not found_item:
        return jsonify({"success": False, "error": "Found item not found."}), 404
        
    verification = verify_secret_clue(found_item.get('secret_clue', ''), claimant_clue)
    claim_id = database.create_claim({
        'lost_item_id': lost_item_id, 'found_item_id': found_item_id,
        'claimant_name': claimant_name, 'claimant_contact': claimant_contact,
        'submitted_secret_clue': claimant_clue,
        'supporting_proof_notes': data.get('supporting_proof_notes', ''),
        'clue_match_status': verification['status'], 'clue_similarity_score': verification['score'],
        'claim_status': 'APPROVED' if verification['status'] == 'MATCHED' else 'IN_REVIEW'
    })
    
    if verification['status'] == 'MATCHED':
        database.update_item_status(
            found_item_id, 'VERIFIED', changed_by="AI Ownership Verifier",
            actor_role="admin", remarks=f"Claim #{claim_id} verified by secret clue matching ({verification['score']}%)."
        )
    return jsonify({"success": True, "claim_id": claim_id, "verification": verification})

@app.route('/api/claims/<int:found_item_id>', methods=['GET'])
def get_claims_for_found_item(found_item_id):
    claims = database.get_claims_for_found_item(found_item_id)
    return jsonify({"success": True, "found_item_id": found_item_id, "claim_count": len(claims), "claims": claims})

@app.route('/api/items/<int:item_id>/handover', methods=['POST'])
def complete_handover_api(item_id):
    data = request.get_json() or {}
    staff_name = data.get('staff_name', 'Transit Depot Staff')
    recipient_name = data.get('recipient_name', 'Verified Owner')
    id_proof = data.get('id_proof_type', 'Govt Transit Pass / Aadhaar / Student ID')
    remarks = data.get('remarks', f"Property handed over to {recipient_name} upon ID check ({id_proof}).")
    
    success = database.update_item_status(item_id, 'HANDED_OVER', changed_by=staff_name, actor_role='staff', remarks=remarks)
    if not success:
        return jsonify({"success": False, "error": "Item not found"}), 404
    return jsonify({"success": True, "message": f"Item #{item_id} marked as HANDED_OVER.", "item_id": item_id})

@app.route('/api/history/<int:item_id>', methods=['GET'])
def get_item_history_api(item_id):
    history = database.get_status_history(item_id)
    return jsonify({"success": True, "item_id": item_id, "history": history})

@app.route('/api/patterns', methods=['GET'])
def get_patterns_api():
    all_items = database.get_items(privacy_mode=False)
    return jsonify({
        "success": True,
        "live_detected_patterns": analyze_incident_patterns(all_items),
        "stored_history": database.get_incident_patterns()
    })

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats_api():
    return jsonify({"success": True, "stats": database.get_dashboard_analytics()})

@app.route('/api/chatbot', methods=['POST'])
def chatbot_api():
    data = request.get_json() or {}
    return jsonify({
        "success": True,
        "response": get_chatbot_response(data.get('message', ''), data.get('lang', 'en')),
        "language": data.get('lang', 'en')
    })

@app.route('/api/demo/seed', methods=['POST'])
def seed_demo_api():
    database.init_db()
    res = database.seed_demo_data()
    return jsonify({"success": True, "result": res})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"TransitMatch Running at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)