FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para cache
COPY assistants/ollama/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código
COPY assistants/ollama/wrapper.py .
COPY common/ /app/common/

# Puerto expuesto
EXPOSE 5003

# Comando para ejecutar
CMD ["python", "wrapper.py"]