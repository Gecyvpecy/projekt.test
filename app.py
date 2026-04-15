import os
import sqlite3
import datetime
import requests
import urllib3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "tajny-klic-123")

# CESTA K DATABÁZI (Podle tvého obrázku)
DB_PATH = "/data/myapp.db"

def get_db_connection():
    # Pokud složka /data neexistuje (třeba při testování u tebe v PC), 
    # vytvoříme ji, aby aplikace nespadla.
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# VYTVOŘENÍ TABULEK (pokud neexistují)
def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (username TEXT PRIMARY KEY, password TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS logs 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, dt TEXT)''')
    conn.commit()
    conn.close()

init_db()

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

    hashed_pw = generate_password_hash(password)
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_pw))
        conn.execute("INSERT INTO logs (message, dt) VALUES (?, ?)", 
                     (f"Registrace: {username}", datetime.datetime.now().strftime("%H:%M:%S")))
        conn.commit()
        flash('Registrace úspěšná!', 'success')
    except sqlite3.IntegrityError:
        flash('Uživatel již existuje!', 'error')
    finally:
        conn.close()
    return redirect(url_for('login_page'))

@app.route('/login_user', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    
    if user and check_password_hash(user['password'], password):
        session['user'] = username
        conn.execute("INSERT INTO logs (message, dt) VALUES (?, ?)", 
                     (f"Login: {username}", datetime.datetime.now().strftime("%H:%M:%S")))
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
    if 'user' not in session or session['user'] != 'admin':
        return "<h1>Přístup odepřen</h1>", 403

    conn = get_db_connection()
    users = conn.execute("SELECT username FROM users").fetchall()
    logs = conn.execute("SELECT * FROM logs ORDER BY id DESC").fetchall()
    conn.close()
    
    return render_template('admin.html', 
                           uzivatele=[u['username'] for u in users], 
                           logy=[f"{l['dt']} - {l['message']}" for l in logs])

@app.route('/ai', methods=['POST'])
def ai_advisor():
    if 'user' not in session: return jsonify({"error": "Nepřihlášen"}), 403
    
    data = request.json
    budget = data.get("budget", "0")
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

    payload = {"model": "gemma3:27b", "messages": [{"role": "user", "content": f"PC komponenta za {budget} Kč. Jedna věta."}], "stream": False}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        res = requests.post(url, headers=headers, json=payload, timeout=20, verify=False)
        if res.status_code == 200:
            msg = res.json()['choices'][0]['message']['content']
            conn = get_db_connection()
            conn.execute("INSERT INTO logs (message, dt) VALUES (?, ?)", 
                         (f"AI Dotaz: {session['user']} (Budget: {budget})", datetime.datetime.now().strftime("%H:%M:%S")))
            conn.commit()
            conn.close()
            return jsonify({"recommendation": msg})
        return jsonify({"error": "Chyba AI"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
