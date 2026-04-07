import os
import requests
import datetime
import urllib3
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv

# Vypne varování o nezabezpečeném HTTPS (protože používáme verify=False)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()

app = Flask(__name__)

# Konfigurace - na serveru musí být OPENAI_BASE_URL=https://kurim.ithope.eu/v1
api_key = os.environ.get("OPENAI_API_KEY", "tvuj_klic_nebo_placeholder")
base_url = os.environ.get("OPENAI_BASE_URL", "https://kurim.ithope.eu/v1")

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
        # Skládání URL pro endpoint kurim.ithope.eu/v1
        clean_url = base_url.rstrip('/')
        target_url = f"{clean_url}/chat/completions"
        
        # DEBUG výpis do konzole dockeru (uvidíš v logu, kam se to skutečně posílá)
        print(f"DEBUG: Volám URL: {target_url}")

        # verify=False je nutné, pokud server nemá platný SSL certifikát
        response = requests.post(
            target_url, 
            headers=headers, 
            json=payload, 
            timeout=20, 
            verify=False
        )
        
        if response.status_code == 200:
            ai_response = response.json()['choices'][0]['message']['content']
            return jsonify({"recommendation": ai_response})
        else:
            # Pokud server vrátí chybu, pošleme ji do frontendu pro diagnostiku
            return jsonify({
                "error": f"Server vrátil {response.status_code}.",
                "details": response.text
            }), response.status_code

    except Exception as e:
        return jsonify({"error": f"Spojení selhalo: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
