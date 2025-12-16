FROM python:3.10-slim

WORKDIR /app

# Copiar requirements específico del servicio
COPY ui/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del servicio
COPY ui/ .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]