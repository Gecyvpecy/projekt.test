import os
import redis
import datetime
import requests
import urllib3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# --- KONFIGURACE A ZABEZPEČENÍ ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv() # Načtení .env pro lokální vývoj

app = Flask(__name__)
app.secret_key = "super_tajny_klic_pro_session" # Nutné pro login

# --- PROMĚNNÉ PROSTŘEDÍ (BOD 2 ZADÁNÍ) ---
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
# V compose.yml použij název služby 'cache' (bez podtržítek!)
redis_host = os.environ.get("REDIS_HOST", "cache")

# --- PŘIPOJENÍ K DATABÁZI (BOD 5 ZADÁNÍ) ---
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

# --- ROUTY PRO PŘIHLÁŠENÍ A REGISTRACI ---

@app.route('/')
def index():
    # Pokud je uživatel v session, pustíme ho k AI, jinak na login
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
        return "Chybí údaje", 400

    # BEZPEČNOST: Heslo v DB neuvidíš, ukládáme jen hash
    hashed_password = generate_password_hash(password)
    
    if r.exists(f"user:{username}"):
        return "Uživatel už existuje", 400
        
    r.set(f"user:{username}", hashed_password)
    r.lpush('log_pristupu', f"Registrace: {username} ({datetime.datetime.now().strftime('%H:%M')})")
    
    # PO REGISTRACI HNED NA LOGIN
    return redirect(url_for('login_page'))

@app.route('/login_user', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    stored_hash = r.get(f"user:{username}")
    
    if stored_hash and check_password_hash(stored_hash, password):
        session['user'] = username
        r.lpush('log_pristupu', f"Login: {username}")
        return redirect(url_for('index'))
    return "Špatné jméno nebo heslo", 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

# --- AI PORADCE (GEMMA 3:27B) ---

@app.route('/ai', methods=['POST'])
def ai_advisor():
    if 'user' not in session:
        return jsonify({"error": "Nepřihlášen"}), 403

    data = request.json
    budget = data.get("budget", "0")
    
    prompt = f"Uživatel má budget {budget} Kč na PC komponentu. Doporuč jednu konkrétní aktuální komponentu jednou větou česky."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gemma3:27b", 
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        # Ošetření URL, aby nevznikla chyba 404 kvůli lomítkům
        target_url = f"{base_url.rstrip('/')}/chat/completions"
        
        response = requests.post(target_url, headers=headers, json=payload, timeout=20, verify=False)
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            r.lpush('log_pristupu', f"AI Dotaz: {session['user']} (Budget: {budget})")
            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({"error": f"Chyba LLM: {response.status_code}"}), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

# --- STATUS A ADMIN (BOD 5) ---

@app.route('/status')
def status():
    # Výpis logů z databáze Redis
    logs = r.lrange('log_pristupu', 0, -1)
    return jsonify({
        "app": "PC Builder AI",
        "author": "Martin Gerstner",
        "logs_from_db": logs
    })

if __name__ == '__main__':
    # Poslech na portu z proměnné PORT (BOD 3 ZADÁNÍ)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
