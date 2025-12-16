FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y gcc g++ && rm -rf /var/lib/apt/lists/*

# Copiar common desde el contexto raíz
COPY common /app/common

# Copiar requirements específico del servicio
COPY assistants/deeppavlov-nlu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del servicio
COPY assistants/deeppavlov-nlu/wrapper.py .

EXPOSE 5002

CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "5002"]