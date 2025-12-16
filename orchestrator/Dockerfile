FROM python:3.10-slim

WORKDIR /app

# Copiar common desde el contexto raíz
COPY common /app/common

# Copiar requirements específico del servicio
COPY orchestrator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del servicio
COPY orchestrator/ .

EXPOSE 8000

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]