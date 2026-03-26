import os
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Dynamické načtení IP adresy. Pokud v dockeru není nastavená, použije se localhost.
OLLAMA_HOST = os.environ.get('OLLAMA_HOST', 'http://host.docker.internal:11434')

@app.route('/ping', methods=['GET'])
def ping():
    return "pong"

@app.route('/status', methods=['GET'])
def status():
    # Tady si kámoš může upravit svoje jméno a statistiky
    data = {
        "autor": "martt a kamos",
        "hra": "Counter-Strike 2",
        "K/D_ratio": 1.2,
        "win_rate": "55%"
    }
    return jsonify(data)

@app.route('/ai', methods=['POST'])
def ai_coach():
    # Tady se ptáme AI
    prompt = "Jsi herní kouč. Napiš jednu krátkou větu česky, jak se zlepšit ve hře, když má hráč špatné K/D ratio."
    
    try:
        # Použijeme dynamickou proměnnou OLLAMA_HOST
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": "llama3.2:1b",
                "prompt": prompt,
                "stream": False
            },
            timeout=15
        )
        
        if response.status_code == 200:
            result = response.json()
            advice = result.get('response', 'Chyba: AI nic nevrátila.')
            return jsonify({"ai_coach_advice": advice})
        else:
            return jsonify({"error": f"Chyba Ollamy: {response.status_code}"}), 500
            
    except Exception as e:
        return jsonify({"error": f"Nepodařilo se spojit s Ollamou: {str(e)}"}), 500

if __name__ == '__main__':
    # host='0.0.0.0' je klíč k úspěchu – naslouchá na všech IP adresách!
    app.run(host='0.0.0.0', port=8081)