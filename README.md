# PC Builder AI Assistant
Projekt pro školní síťovou službu v Dockeru.

## Parametry sítě
- [cite_start]**Doména:** jmenoprijmeni.skola.test [cite: 21]
- [cite_start]**Port:** 8081 (TCP) [cite: 16]
- [cite_start]**DHCP Scope:** 10.10.10.100-200/24 (příklad) [cite: 12]

## Endpointy
- `GET /ping`: Vrátí "pong"
- `GET /status`: Vrátí JSON se stavem aplikace
- `POST /ai`: Přijme JSON `{"budget": "5000"}` a vrátí doporučení komponenty

## Spuštění
1. [cite_start]Nainstaluj a spusť Ollama s modelem: `ollama run llama3.2:1b` [cite: 28]
2. Vlož soubory na GitHub.
3. Spusť příkazem: `docker-compose up -d`

## Testování (curl)
```bash
curl -X POST http://localhost:8081/ai -H "Content-Type: application/json" -d '{"budget": "8000"}'