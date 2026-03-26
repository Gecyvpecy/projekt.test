from flask import Flask, jsonify, request
import requests
import datetime

app = Flask(__name__)

# Fiktivní herní statistiky (protože budeme offline)
PLAYER_STATS = {
    "nickname": "ProGamer_CZ",
    "game": "Counter-Strike 2",
    "kills": 5,
    "deaths": 15,
    "accuracy": "32%",
    "rank": "Silver IV"
}

# 1. Endpoint: GET /ping (Požadavek ze zadání)
@app.route('/ping', methods=['GET'])
def ping():
    return "pong", 200

# 2. Endpoint: GET /status (Vrací JSON s časem, autorem a statistikami)
@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "status": "online",
        "autor": "Tvoje Jmeno",  # Tady si doplň své jméno
        "aktualni_cas": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data": PLAYER_STATS
    })

# 3. Endpoint: POST /ai (Komunikace s Ollama LLM)
@app.route('/ai', methods=['POST'])
def ai_coach():
    # Prompt pro AI využívající naše herní statistiky
    prompt_text = f"Hráč má {PLAYER_STATS['kills']} killů a {PLAYER_STATS['deaths']} smrtí. Poruď mu jednou krátkou větou, co má zlepšit."
    
    try:
        # Volání lokální Ollamy běžící na hostitelském stroji
        # V Dockeru použijeme 'host.docker.internal' místo 'localhost'
        response = requests.post(
            'http://host.docker.internal:11434/api/generate',
            json={
                "model": "llama3.2:1b",
                "prompt": prompt_text,
                "stream": False
            },
            timeout=10 # Aby aplikace nevisela, když AI neodpovídá
        )
        
        result = response.json()
        # Vracíme jen jednu krátkou větu podle zadání [cite: 30, 74]
        return jsonify({"ai_coach_advice": result.get("response", "AI je momentálně mimo provoz.")})
    
    except Exception as e:
        return jsonify({"error": "Nelze se spojit s AI modelem (Ollama).", "details": str(e)}), 500

if __name__ == '__main__':
    # Spuštění na nestandardním portu 8081 [cite: 16, 24]
    app.run(host='0.0.0.0', port=8081)