FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY wrapper.py .

EXPOSE 5002

CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "5002"]