import os
import sqlite3
import datetime
import requests
import urllib3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# --- KONFIGURACE ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# --- CESTA K DATABÁZI (Perzistentní složka) ---
DB_PATH = "/data/users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db_connection()
    # Tabulka pro uživatele
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (username TEXT PRIMARY KEY, password TEXT)''')
    # Tabulka pro logy
    conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, timestamp DATETIME)''')
    conn.commit()
    conn.close()

init_db()

# --- PROMĚNNÉ PROSTŘEDÍ ---
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

@app.route('/')
def index():
    if 'user' in session:
        return render_template('index.html')
    return redirect(url_for('login_page'))

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register_user', methods=['POST'])
def register():
    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        flash('Vyplňte všechna pole!', 'error')
        return redirect(url_for('login_page'))
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user:
        conn.close()
        flash('Uživatel již existuje!', 'error')
        return redirect(url_for('login_page'))
    
    hashed_pw = generate_password_hash(password)
    conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
    conn.execute("INSERT INTO logs (message, timestamp) VALUES (?, ?)", 
                 (f"Registrace: {username}", datetime.datetime.now()))
    conn.commit()
    conn.close()
    
    flash('Registrace úspěšná! Nyní se přihlaste.', 'success')
    return redirect(url_for('login_page'))

@app.route('/login_user', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        session['user'] = username
        conn.execute("INSERT INTO logs (message, timestamp) VALUES (?, ?)", 
                     (f"Login: {username}", datetime.datetime.now()))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        conn.close()
        flash('Špatné jméno nebo heslo!', 'error')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

@app.route('/status')
def status():
    if 'user' not in session:
        flash('Pro vstup do administrace se musíte přihlásit.', 'error')
        return redirect(url_for('login_page'))

    conn = get_db_connection()
    if session['user'] != 'admin':
        conn.execute("INSERT INTO logs (message, timestamp) VALUES (?, ?)", 
                     (f"NEPOVOLENÝ POKUS: {session['user']}", datetime.datetime.now()))
        conn.commit()
        conn.close()
        return "<h1>Přístup odepřen</h1>", 403

    uzivatele = conn.execute("SELECT username FROM users").fetchall()
    logy_db = conn.execute("SELECT message, timestamp FROM logs ORDER BY timestamp DESC").fetchall()
    conn.close()

    # Formátování logů pro šablonu (vytvoření textového řetězce jako to dělal Redis lpush)
    seznam_uzivatelu = [u['username'] for u in uzivatele]
    logs = [f"{l['message']} ({l['timestamp']})" for l in logy_db]
    
    return render_template('admin.html', uzivatele=seznam_uzivatelu, logy=logs)

@app.route('/ai', methods=['POST'])
def ai_advisor():
    if 'user' not in session:
        return jsonify({"error": "Nepřihlášen"}), 403
    data = request.json
    budget = data.get("budget", "0")
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gemma3:27b", "messages": [{"role": "user", "content": f"PC komponenta za {budget} Kč. Jedna věta."}], "stream": False}

    try:
        clean_url = f"{base_url.rstrip('/')}/chat/completions"
        res = requests.post(clean_url, headers=headers, json=payload, timeout=20, verify=False)
        if res.status_code == 200:
            msg = res.json()['choices'][0]['message']['content']
            conn = get_db_connection()
            conn.execute("INSERT INTO logs (message, timestamp) VALUES (?, ?)", 
                         (f"AI Dotaz: {session['user']} (Budget: {budget})", datetime.datetime.now()))
            conn.commit()
            conn.close()
            return jsonify({"recommendation": msg})
        return jsonify({"error": f"Chyba LLM"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
