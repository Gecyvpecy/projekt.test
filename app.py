from flask import Flask, request, jsonify, render_template
import requests
import datetime

app = Flask(__name__)

# Konfigurace - pokud učitelův systém pouští tvou app a Ollama běží někde jinde, 
# případně to upravíš podle jeho instrukcí. Zatím necháváme localhost/host.
OLLAMA_URL = "http://host.docker.internal:11434/api/generate"

# NOVÉ: Endpoint pro zobrazení webové stránky
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
    # Defaultní hodnota 0, pokud by náhodou nepřišlo nic
    budget = data.get("budget", "0") 
    
    # Prompt pro lokální model
    prompt = f"Uživatel má budget {budget} Kč na jednu PC komponentu. Doporuč mu stručně jednu konkrétní aktuální komponentu. Odpověz pouze jednou krátkou větou."

    try:
        response = requests.post(OLLAMA_URL, json={
            "model": "llama3.2:1b",
            "prompt": prompt,
            "stream": False
        }, timeout=15)
        
        # Ošetření, pokud se LLM spojí, ale vrátí nesmysl
        if response.status_code == 200:
            ai_response = response.json().get("response", "AI momentálně neodpovídá.")
            return jsonify({"recommendation": ai_response})
        else:
            return jsonify({"error": f"LLM vrátilo chybu: {response.status_code}"}), 500

    except Exception as e:
        return jsonify({"error": "Nepodařilo se spojit s lokálním LLM", "details": str(e)}), 500

if __name__ == '__main__':
    # 0.0.0.0 je nutnost, aby aplikace byla dostupná zvenčí
    app.run(host='0.0.0.0', port=8081)