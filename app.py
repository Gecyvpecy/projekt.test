import os
from flask import Flask, request, jsonify, render_template
import requests
import datetime
from dotenv import load_dotenv

# Načte .env pouze pokud existuje (lokálně), na serveru se ignoruje
load_dotenv()

app = Flask(__name__)

# Načtení konfigurace
api_key = os.environ.get("OPENAI_API_KEY")
base_url = os.environ.get("OPENAI_BASE_URL")

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "running",
        "timestamp": datetime.datetime.now().isoformat(),
        "author": "Martin Gerstner",
        "app": "PC Budget AI Advisor"
    })

@app.route('/ai', methods=['POST'])
def ai_advisor():
    # Kontrola, zda jsou nastaveny API klíče a URL
    if not api_key or not base_url:
        return jsonify({"error": "Chybí konfigurace API na serveru (ENV proměnné)."}), 500

    data = request.json
    budget = data.get("budget", "0")
    
    prompt = f"Uživatel má budget {budget} Kč na jednu PC komponentu. Doporuč mu stručně jednu konkrétní aktuální komponentu. Odpověz pouze jednou krátkou větou v češtině."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "gpt-4o-mini",  # Změněno na standardní model (uprav dle potřeby)
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }

    try:
        # Sestavení URL
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        response = requests.post(target_url, headers=headers, json=payload, timeout=15)
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({
                "error": f"Server vrátil {response.status_code}.",
                "details": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    # Port se bere z ENV, defaultně 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
