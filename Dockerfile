FROM python:3.12-slim

WORKDIR /app

# Kopírujeme seznam knihoven
COPY requirements.txt .

# Instalujeme knihovny (flask, requests)
RUN pip install --no-cache-dir -r requirements.txt

# Kopírujeme zbytek aplikace
COPY . .

# Spouštíme aplikaci
CMD ["python", "app.py"]
