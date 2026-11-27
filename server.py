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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_queues (
            queue_key TEXT PRIMARY KEY,
            items_json TEXT,
            is_approved1 INTEGER DEFAULT 0,
            is_approved2 INTEGER DEFAULT 0,
            comment1_text TEXT DEFAULT '',
            comment2_text TEXT DEFAULT ''
        )
    ''')
    conn.commit()
    conn.close()

# Gunicorn በ Render ላይ ሲያስነሳው ዳታቤዙ እና ሠንጠረዦቹ መኖራቸውን ያረጋግጣል
init_db()

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

@app.route('/api/queue', methods=['GET', 'POST'])
def handle_pending_queue():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'GET':
        company = request.args.get('company', '')
        transport = request.args.get('transportType', '')
        key = f"{company}__{transport}"
        cursor.execute("SELECT * FROM pending_queues WHERE queue_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return jsonify({
                "items": [],
                "isApproved1": False,
                "isApproved2": False,
                "comment1Text": "",
                "comment2Text": ""
            })

        try:
            items = json.loads(row['items_json'] or '[]')
        except Exception:
            items = []

        return jsonify({
            "items": items,
            "isApproved1": bool(row['is_approved1']),
            "isApproved2": bool(row['is_approved2']),
            "comment1Text": row['comment1_text'] or "",
            "comment2Text": row['comment2_text'] or ""
        })

    payload = request.get_json(silent=True) or {}
    company = payload.get('company', '')
    transport = payload.get('transportType', '')
    key = f"{company}__{transport}"
    items_json = json.dumps(payload.get('items', []), ensure_ascii=False)
    is_app1 = 1 if payload.get('isApproved1') else 0
    is_app2 = 1 if payload.get('isApproved2') else 0
    c1 = payload.get('comment1Text', '')
    c2 = payload.get('comment2Text', '')

    cursor.execute('''
        INSERT INTO pending_queues (queue_key, items_json, is_approved1, is_approved2, comment1_text, comment2_text)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(queue_key) DO UPDATE SET
            items_json = excluded.items_json,
            is_approved1 = excluded.is_approved1,
            is_approved2 = excluded.is_approved2,
            comment1_text = excluded.comment1_text,
            comment2_text = excluded.comment2_text
    ''', (key, items_json, is_app1, is_app2, c1, c2))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

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

@app.route('/api/delete_record/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM dispatch WHERE id = ?", (record_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
