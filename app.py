from flask import Flask, request, jsonify, render_template
import requests
import datetime

app = Flask(__name__)

# Adresa pro Ollama běžící na tvém fyzickém PC (mimo kontejner)
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

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
        "author": "Tvuj Jmeno", # <--- DOPLŇ SVÉ JMÉNO
        "app": "PC Budget AI Advisor"
    })

@app.route('/ai', methods=['POST'])
def ai_advisor():
    data = request.json
    budget = data.get("budget", "0")
    
    prompt = f"Uživatel má budget {budget} Kč na jednu PC komponentu. Doporuč mu stručně jednu konkrétní aktuální komponentu. Odpověz pouze jednou krátkou větou v češtině."

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "gemma3:27b", 
            "prompt": prompt,
            "stream": False
        }, timeout=15)
        
        if response.status_code == 200:
            ai_response = response.json().get("response", "AI neodpovídá.")
            return jsonify({"recommendation": ai_response})
        return jsonify({"error": "Chyba LLM"}), 500
    except Exception as e:
        return jsonify({"error": "Spojení s AI selhalo"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)