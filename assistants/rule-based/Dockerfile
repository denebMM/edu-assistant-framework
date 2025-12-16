FROM python:3.10-slim

WORKDIR /app

# Copiar common desde el contexto raíz
COPY common /app/common

# Copiar requirements específico del servicio
COPY assistants/rule-based/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del servicio
COPY assistants/rule-based/wrapper.py .
COPY assistants/rule-based/Code.py .

EXPOSE 5001

CMD ["uvicorn", "wrapper:app", "--host", "0.0.0.0", "--port", "5001"]