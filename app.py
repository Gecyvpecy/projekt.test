import os
from flask import Flask, request, jsonify, render_template
import requests
import datetime

app = Flask(__name__)

# 2. Čtení proměnných prostředí (přesně podle zadání)
api_key = os.environ.get("")
base_url = os.environ.get("https://kurim.ithope.eu/v1")

@app.route('/', methods=['GET'])
def home():
    return render_template('index.html')

@app.route('/ping', methods=['GET'])
def ping():
    return "pong", 200

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
        # Použití base_url z proměnných prostředí
        target_url = f"{base_url}/chat/completions"
        response = requests.post(target_url, headers=headers, json=payload, timeout=15, verify=False)
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            return jsonify({"recommendation": ai_response})
        return jsonify({"error": "Chyba LLM"}), 500
    except Exception as e:
        return jsonify({"error": "Spojení s AI selhalo"}), 500

if __name__ == '__main__':
    # 3. Port - aplikace naslouchá na portu z proměnné PORT (default 5000)
  app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
