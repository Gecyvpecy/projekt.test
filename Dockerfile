FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exponujeme nestandardní port [cite: 16]
EXPOSE 8081

CMD ["python", "app.py"]