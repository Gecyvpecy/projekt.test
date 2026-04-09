import os
import redis
import datetime
import requests
import urllib3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# --- KONFIGURACE ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

app = Flask(__name__)
app.secret_key = "tajny_klic_pro_session" # Nutné pro fungování session/přihlášení

# --- NAČTENÍ PROMĚNNÝCH PROSTŘEDÍ (BOD 2) ---
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
redis_host = os.environ.get("REDIS_HOST", "localhost")

# --- PŘIPOJENÍ K DATABÁZI (BOD 5) ---
# Používáme Redis pro ukládání uživatelů a historie logů
r = redis.Redis(host=redis_host, port=6379, decode_responses=True)

# --- ROUTY PRO PŘIHLÁŠENÍ ---

@app.route('/')
def index():
    # Pokud je uživatel přihlášen, uvidí AI poradce, jinak jde na login
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
        return "Chybí jméno nebo heslo", 400

    # HESLO V DATABÁZI NEBUDE VIDĚT (převede se na hash)
    hashed_password = generate_password_hash(password)
    
    if r.exists(f"user:{username}"):
        return "Uživatel již existuje", 400
        
    # Uložíme do Redisu (klíč je user:jméno, hodnota je hash hesla)
    r.set(f"user:{username}", hashed_password)
    r.lpush('log_pristupu', f"Registrace: {username} ({datetime.datetime.now().strftime('%H:%M:%S')})")
    return "Registrace úspěšná! Nyní se můžete přihlásit na stránce /login."

@app.route('/login_user', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    
    stored_hash = r.get(f"user:{username}")
    
    # Ověření hesla proti uloženému hagi
    if stored_hash and check_password_hash(stored_hash, password):
        session['user'] = username
        r.lpush('log_pristupu', f"Přihlášení: {username} ({datetime.datetime.now().strftime('%H:%M:%S')})")
        return redirect(url_for('index'))
    return "Chybné jméno nebo heslo", 401

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login_page'))

# --- AI PORADCE (TVÁ PŮVODNÍ LOGIKA) ---

@app.route('/ai', methods=['POST'])
def ai_advisor():
    # Kontrola, zda je uživatel přihlášen
    if 'user' not in session:
        return jsonify({"error": "Přístup odepřen. Přihlaste se."}), 403

    data = request.json
    budget = data.get("budget", "0")
    
    prompt = f"Uživatel má budget {budget} Kč na jednu PC komponentu. Doporuč mu stručně jednu konkrétní aktuální komponentu. Odpověz pouze jednou krátkou větou v češtině."

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
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        response = requests.post(target_url, headers=headers, json=payload, timeout=20, verify=False)
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            # Uložíme dotaz do historie v DB
            r.lpush('log_pristupu', f"Dotaz AI: {session['user']} (Budget: {budget})")
            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({"error": f"Chyba LLM: {response.status_code}"}), 500

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

# --- ADMIN PŘEHLED (PRO KONTROLU DATABÁZE) ---

@app.route('/status', methods=['GET'])
def status():
    # Zde uvidíš logy přihlášení a jména uživatelů (ale ne hesla!)
    logs = r.lrange('log_pristupu', 0, -1)
    return jsonify({
        "status": "running",
        "author": "Martin Gerstner",
        "prihlaseni_uzivatele": logs
    })

if __name__ == '__main__':
    # Bod 3 - Port z proměnné prostředí
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
