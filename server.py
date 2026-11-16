import os
import sqlite3
import json
from flask import Flask, send_from_directory, request, jsonify

app = Flask(__name__, static_folder='.')
DB_FILE = "habesha_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dispatch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            transportType TEXT,
            fdc TEXT UNIQUE,
            date TEXT,
            plate TEXT,
            destin TEXT,
            orig TEXT,
            dealer TEXT,
            product TEXT,
            litter REAL,
            rate REAL,
            transAmt REAL
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return send_from_directory('.', 'borkena.html')

@app.route('/api/records', methods=['GET'])
def get_records():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM dispatch ORDER BY id ASC")
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/check_fdc/<fdc_val>', methods=['GET'])
def check_fdc(fdc_val):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM dispatch WHERE fdc = ?", (fdc_val,))
    exists = cursor.fetchone() is not None
    conn.close()
    return jsonify({"exists": exists})

@app.route('/api/save_batch', methods=['POST'])
def save_batch():
    try:
        entries = request.get_json()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        for entry in entries:
            fdc_val = entry.get('fdc')
            cursor.execute("SELECT id FROM dispatch WHERE fdc = ?", (fdc_val,))
            if cursor.fetchone():
                continue
            
            cursor.execute('''
                INSERT INTO dispatch (company, transportType, fdc, date, plate, destin, orig, dealer, product, litter, rate, transAmt)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                entry.get('company'), entry.get('transportType'), fdc_val,
                entry.get('date'), entry.get('plate'), entry.get('destin'),
                entry.get('orig'), entry.get('dealer'), entry.get('product'),
                entry.get('litter'), entry.get('rate'), entry.get('transAmt')
            ))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)