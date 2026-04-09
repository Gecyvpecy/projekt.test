import os
import requests
import datetime
import urllib3
import redis  # Nutné pro splnění podmínky 2 služeb (bod 1 v novém zadání)
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# --- KONFIGURACE A ZABEZPEČENÍ ---
# Vypne varování o SSL certifikátu pro školní server
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Načte .env pro lokální vývoj (bod 4 zadání)
load_dotenv()

app = Flask(__name__)

# --- NAČTENÍ PROMĚNNÝCH PROSTŘEDÍ (BOD 2 ZADÁNÍ) ---
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")
# REDIS_HOST musí odpovídat názvu služby v compose.yml
redis_host = os.environ.get("REDIS_HOST", "localhost")

# --- PŘIPOJENÍ K DATABÁZI (BOD 5 ZADÁNÍ) ---
# decode_responses=True zajistí, že z databáze dostaneme text, ne bajty
cache = redis.Redis(host=redis_host, port=6379, decode_responses=True)

@app.route('/', methods=['GET'])
def home():
    """Zobrazí hlavní stránku webu."""
    return render_template('index.html')

@app.route('/status', methods=['GET'])
def status():
    """Vrací stav aplikace, autora a aktuální čas."""
    return jsonify({
        "status": "running",
        "timestamp": datetime.datetime.now().isoformat(),
        "author": "Martin Gerstner",
        "app": "PC Budget AI Advisor"
    })

@app.route('/ai', methods=['POST'])
def ai_advisor():
    """Hlavní logika: Komunikace s AI a ukládání statistik do Redisu."""
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
        # Sestavení URL (ošetření lomítek na konci)
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        # Odeslání požadavku na AI server v Kuřimi
        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=20, 
            verify=False
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            
            # --- PRÁCE S DATABÁZÍ (REDIS) ---
            # Zvýšíme počítadlo rad v databázi o jedna
            try:
                total_count = cache.incr('counter_advices')
            except Exception:
                total_count = "N/A (DB error)"

            return jsonify({
                "recommendation": ai_response,
                "total_served": total_count  # Bonusová informace z DB
            })
        else:
            return jsonify({
                "error": f"LLM server vrátil chybu {response.status_code}",
