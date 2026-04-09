import os
import redis
import datetime
import requests
import urllib3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# --- KONFIGURACE ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "tajny-klic-123")

# --- PROMĚNNÉ PROSTŘEDÍ ---
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
redis_host = os.environ.get("REDIS_HOST", "cache")

# --- PŘIPOJENÍ K DB ---
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

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
    if r.exists(f"user:{username}"):
        flash('Uživatel již existuje!', 'error')
        return redirect(url_for('login_page'))
    
    hashed_pw = generate_password_hash(password)
    r.set(f"user:{username}", hashed_pw)
    r.lpush('log_pristupu', f"Registrace: {username} ({datetime.datetime.now().strftime('%H:%M:%S')})")
    flash('Registrace úspěšná! Nyní se přihlaste.', 'success')
    return redirect(url_for('login_page'))

@app.route('/login_user', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    stored_hash = r.get(f"user:{username}")
    
    if stored_hash and check_password_hash(stored_hash, password):
        session['user'] = username
        r.lpush('log_pristupu', f"Login: {username} ({datetime.datetime.now().strftime('%H:%M:%S')})")
        return redirect(url_for('index'))
    else:
        flash('Špatné jméno nebo heslo!', 'error')
        return redirect(url_for('login_page'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

# --- ZABEZPEČENÝ ADMIN PANEL ---
@app.route('/status')
def status():
    if 'user' not in session:
        flash('Pro vstup do administrace se musíte přihlásit.', 'error')
        return redirect(url_for('login_page'))

    if session['user'] != 'admin':
        r.lpush('log_pristupu', f"NEPOVOLENÝ POKUS: {session['user']} chtěl do admina!")
        return "<h1>Přístup odepřen</h1><p>Tato sekce je pouze pro administrátora.</p>", 403

    user_keys = r.keys("user:*")
    seznam_uzivatelu = [k.replace("user:", "") for k in user_keys]
    logs = r.lrange('log_pristupu', 0, -1)
    return render_template('admin.html', uzivatele=seznam_uzivatelu, logy=logs)

# --- AI LOGIKA ---
@app.route('/ai', methods=['POST'])
def ai_advisor():
    if 'user' not in session:
        return jsonify({"error": "Nepřihlášen"}), 403
    data = request.json
    budget = data.get("budget", "0")
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": "gemma3:27b", "messages": [{"role": "user", "content": f"PC komponenta za {budget} Kč. Jedna věta."}], "stream": False}

    try:
        # Oprava URL (odstranění koncového lomítka a přidání správného endpointu)
        clean_url = f"{base_url.rstrip('/')}/chat/completions"
        res = requests.post(clean_url, headers=headers, json=payload, timeout=20, verify=False)
        if res.status_code == 200:
            msg = res.json()['choices'][0]['message']['content']
            r.lpush('log_pristupu', f"AI Dotaz: {session['user']} (Budget: {budget})")
            return jsonify({"recommendation": msg})
        return jsonify({"error": f"Chyba LLM: {res.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
