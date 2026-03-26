# Použijeme lehké Python prostředí
FROM python:3.9-slim

# Nastavíme pracovní adresář uvnitř kontejneru
WORKDIR /app

# Zkopírujeme seznam závislostí a nainstalujeme je
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Zkopírujeme zbytek tvého kódu (app.py)
COPY . .

# Aplikace poběží na portu 8081 [cite: 16]
EXPOSE 8081

# Příkaz pro spuštění aplikace
CMD ["python", "app.py"]