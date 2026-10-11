# TransitMatch — Intelligent Lost & Found Matching with Secure Ownership Verification

**CBC 2.0 • Hackathon Design Round**  
- **Team Name:** BYTEFORCE  
- **Team ID:** CBC006  
- **Domain:** Software & Web Development  
- **College:** Ballari Institute of Technology and Management  
- **Problem Statement ID:** PS-3 (Public Transport Lost-and-Found Matching)

---

## 📌 Problem Statement Breakdown (From Hackathon Paper)

| Section | Detail from Paper / Presentation | TransitMatch Implementation |
| :--- | :--- | :--- |
| **Problem** | Passengers lose items on buses, trains, and public transport. Lost and found reports are difficult to match because descriptions vary (e.g., *"blue bottle"* vs *"dark-blue metal bottle"*). | Structured attribute extraction + TF-IDF cosine similarity + color/brand synonym engine. |
| **Objective** | Create a platform that matches lost-item reports with found-item reports using available descriptive information. | Automated matching engine computing 0-100% confidence scores with explainable factor breakdowns. |
| **Workflow** | 1. Passenger reports lost item with category, color, location, and time.<br>2. Staff/passengers report found items.<br>3. System compares lost and found reports.<br>4. Potential matches are ranked for review.<br>5. User confirms/rejects match and status is updated. | End-to-end workflow implemented in UI tabs with state machine: `REPORTED` ➔ `POTENTIAL_MATCH` ➔ `CLAIM_UNDER_VERIFICATION` ➔ `VERIFIED` ➔ `HANDED_OVER`. |
| **Key Requirements** | • Lost & found reporting<br>• Matching using multiple attributes<br>• Match confidence or ranking<br>• Verification before handover<br>• Item status and audit history | Full REST APIs + SQLite audit logging + Secret Clue verification modal + Depot staff handover recording. |
| **Edge Cases** | 1. **Multiple possible matches:** Ranked candidate list sorted by score with factor breakdown.<br>2. **Incomplete or inaccurate descriptions:** TF-IDF tolerance, color synonyms, and journey proximity.<br>3. **Same item reported multiple times:** Cross-report duplicate & incident pattern detection. | Handled in `ai_engine.py` with heuristics and automated cluster detection. |
| **Scope** | **Must-Have:** Reporting, matching, ranking, verification, and status management.<br>**Stretch:** Image-assisted matching, route/journey suggestions, multilingual AI chatbot assistant, pattern detection. | All Must-Haves and Stretch goals implemented. |
| **Demo Flow** | Report a lost item, add found items, demonstrate ranked matches, and complete a verified handover. | One-click **"Load Demo Data"** button loads the exact presentation scenario for a live judge presentation. |

---

## 🛠️ Architecture & Tech Stack

- **Frontend:** HTML5 (`templates/index.html`), CSS3 (`static/css/style.css`), JavaScript (`static/js/app.js`)
- **Backend:** Python + Flask (`app.py`)
- **AI / Algorithm Layer:** TF-IDF + Cosine Similarity + Multi-Attribute Scoring (`ai_engine.py`)
- **Database:** SQLite (`transitmatch.db`, initialized via `schema.sql` and `database.py`)

---

## 🚀 How to Run the Website

### Step 1: Open Terminal in the Project Directory
```powershell
cd "C:\Users\Sai Meghana R\.gemini\antigravity\scratch\transitmatch"
```

### Step 2: Install Dependencies (if not already installed)
```powershell
pip install -r requirements.txt
```

### Step 3: Run the Flask Application
```powershell
python app.py
```

### Step 4: Open in Web Browser
Navigate to:
👉 **`http://127.0.0.1:5000`**

---

## 🎯 Step-by-Step Hackathon Demo Walkthrough for Judges

1. **Overview & Privacy Search:**
   - Open the web application at `http://127.0.0.1:5000`.
   - Click **"Load Demo Data"** in the top navigation bar.
   - Notice the Privacy-Preserving feature: private contact numbers and secret clues are masked with `🔒 Hidden for Ownership Verification` for regular passengers.
   - Change the **Active Role** dropdown in the navbar to **"Transit Depot Staff"** to see authorized staff view.

2. **AI Match Ranking ("Blue Bottle" vs "Dark-Blue Metal Bottle"):**
   - Click the **"AI Match Ranking"** tab.
   - Select Item `#1 [LOST] Blue Bottle (Metro Purple Line)`.
   - The AI compares all candidate items in custody:
     - Found Item `#2 Dark-Blue Metal Bottle` ranks at **~88% High Probability Match**!
     - Review the **Explainable Scoring Factors Table**: Category (+25%), Color Affinity (+13.5%), Brand (+12.8%), Route & Journey (+20%), Time Proximity (+10%), TF-IDF Text Similarity (+6.8%).

3. **Secret-Clue Ownership Verification (Preventing Fraud):**
   - Click **"Verify Secret Clue on Found #2"** or switch to the **"Secret-Clue Verification"** tab.
   - Claimant Rahul Sharma enters: *"Astronaut cartoon sticker on cap ring, small scratch at bottom"*.
   - Click **"Verify Ownership with AI"**.
   - The AI evaluates semantic token overlap against the depot's confidential notes without leaking the actual clue.
   - Verification succeeds with **Ownership Verified! (82.5% AI Clue Similarity)**, advancing item status to `VERIFIED`.

4. **Staff Handover & Audit Trail:**
   - Switch to the **"Staff Handover & Audit"** tab.
   - Select Verified Item `#2`.
   - Staff officer Suresh records the handover with recipient government ID verification.
   - The **Immutable Item Lifecycle History** shows the complete timeline: `REPORTED` ➔ `POTENTIAL_MATCH` ➔ `CLAIM_UNDER_VERIFICATION` ➔ `VERIFIED` ➔ `HANDED_OVER`.

5. **Cross-Report Duplicate & Pattern Detection:**
   - Click the **"Incident Patterns"** tab.
   - Shows automated alerts:
     - **Duplicate Report Flag:** Detects that Item `#3` and Item `#6` are duplicate reports filed by two family members for the same lost wallet on Bus 204.
     - **High Loss Route Alert:** Flags frequent loss routes for transit security.

6. **Multilingual AI Chatbot Assistant:**
   - Click the floating **AI** chat bubble in the bottom-right corner.
   - Switch between **English**, **हिंदी (Hindi)**, and **ಕನ್ನಡ (Kannada)**.
   - Ask: *"How do I report a lost item?"* or *"Where are found items stored?"* to demonstrate passenger assistance.
