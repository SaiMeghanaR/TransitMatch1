"""
====================================================================
TransitMatch - Fullstack Application Launcher
Team: BYTEFORCE (CBC006)
Domain: Software & Web Development
College: Ballari Institute of Technology and Management
Problem Statement: PS-3 Public Transport Lost-and-Found Matching
====================================================================

Run this single command from your terminal or VS Code:
    python run.py

It connects:
  - Frontend: ./frontend (index.html, style.css, script.js)
  - Backend:  ./backend  (app.py, ai_engine.py)
  - Database: ./database (schema.sql, database.py, transitmatch.db)
"""

import sys
import os

# Add backend and database directories to Python search path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_DIR, 'backend'))
sys.path.insert(0, os.path.join(PROJECT_DIR, 'database'))

from app import app

if __name__ == '__main__':
    print("=" * 65)
    print("  TransitMatch — Intelligent Lost & Found Matching Platform")
    print("  Team: BYTEFORCE (Team ID: CBC006)")
    print("=" * 65)
    print("  [+] Database Layer : ./database (SQLite)")
    print("  [+] Backend API    : ./backend  (Flask & AI Engine)")
    print("  [+] Frontend UI    : ./frontend (HTML, CSS, JS)")
    print("=" * 65)
    print("  >> OPEN YOUR WEB BROWSER AT: http://127.0.0.1:5000 <<")
    print("=" * 65)
    app.run(host='0.0.0.0', port=5000, debug=True)
