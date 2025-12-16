FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar common primero
COPY common /app/common

# Copiar requirements e instalar
COPY assistants/deeppavlov-nlu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el wrapper
COPY assistants/deeppavlov-nlu/wrapper.py .

# Exponer puerto
EXPOSE 5002

# Comando para ejecutar
CMD ["python", "wrapper.py"]