# Ollama Wrapper con Redis Bus - VERSIÓN CORREGIDA
import os
import time
import threading
import sys
from typing import Dict, Any
from fastapi import FastAPI, Request
import uvicorn

# Agregar ruta para importar common
sys.path.append('/app')

app = FastAPI()

# Configurar cliente de Ollama
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://ollama-server:11434')
MODEL = os.getenv('OLLAMA_MODEL', 'tinyllama')

print(f"🔄 Iniciando Ollama assistant...")
print(f"🌐 Conectando a: {OLLAMA_HOST}")
print(f"🤖 Modelo: {MODEL}")

# Importar después de agregar path
import ollama

# Variable global para el cliente
client = None

# Función para conectar con reintentos
def connect_to_ollama(max_retries=10, delay=5):
    """Conectar a Ollama con reintentos"""
    for attempt in range(max_retries):
        try:
            print(f"🔄 Intento {attempt + 1}/{max_retries} para conectar a Ollama...")
            new_client = ollama.Client(host=OLLAMA_HOST)
            
            # Verificar que el servidor esté respondiendo
            models = new_client.list()
            print(f"✅ Conectado a Ollama. Modelos disponibles: {[m['name'] for m in models.get('models', [])]}")
            
            # Verificar que nuestro modelo esté disponible
            model_names = [m['name'] for m in models.get('models', [])]
            if not any(MODEL in name for name in model_names):
                print(f"⚠️  Modelo {MODEL} no encontrado. Intentando descargar...")
                new_client.pull(MODEL)
                print(f"✅ Modelo {MODEL} descargado")
            
            return new_client
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Error de conexión: {e}. Reintentando en {delay} segundos...")
                time.sleep(delay)
            else:
                print(f"❌ No se pudo conectar después de {max_retries} intentos: {e}")
                return None

# Conectar al iniciar
client = connect_to_ollama()

# Intentar importar Redis Bus
try:
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    print("✅ RedisBus disponible para ollama")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️  RedisBus no disponible: {e}")

    
@app.get("/")
async def root():
    return {
        "message": "Ollama Assistant API",
        "status": "running",
        "model": MODEL,
        "ollama_server": OLLAMA_HOST
    }
    
@app.post("/query")
async def handle_query(request: Request):
    """Endpoint HTTP para compatibilidad"""
    global client  # Declarar explícitamente que usamos la variable global
    
    try:
        data = await request.json()
        query = data.get("query", "")
        
        if not query:
            return {"error": "No query provided", "success": False}
        
        # Si no hay cliente, intentar conectar
        if not client:
            client = connect_to_ollama(max_retries=3, delay=2)
            if not client:
                return {"error": "Ollama no disponible", "success": False}
        
        print(f"📝 Procesando consulta: {query[:100]}...")
        
        try:
            response = client.chat(
                model=MODEL,
                messages=[{"role": "user", "content": query}],
                options={"temperature": 0.7}
            )
            
            return {
                "response": response['message']['content'].strip(),
                "model": MODEL,
                "success": True
            }
        except Exception as e:
            print(f"⚠️  Error en llamada a Ollama: {e}. Reconectando...")
            # Intentar reconectar
            client = connect_to_ollama(max_retries=2, delay=1)
            if client:
                response = client.chat(
                    model=MODEL,
                    messages=[{"role": "user", "content": query}],
                    options={"temperature": 0.7}
                )
                return {
                    "response": response['message']['content'].strip(),
                    "model": MODEL,
                    "success": True
                }
            else:
                return {"error": f"Error persistente: {e}", "success": False}
        
    except Exception as e:
        print(f"❌ Error en handle_query: {e}")
        return {"error": str(e), "success": False}

@app.get("/health")
async def health():
    try:
        if client:
            # Verificar conexión
            client.list()
            return {
                "status": "healthy", 
                "model": MODEL,
                "ollama_server": OLLAMA_HOST
            }
        return {
            "status": "unhealthy", 
            "model": MODEL,
            "reason": "Client not initialized"
        }
    except Exception as e:
        return {
            "status": "unhealthy", 
            "model": MODEL,
            "reason": str(e)
        }

@app.get("/")
async def root():
    return {
        "message": "Ollama Assistant API",
        "status": "running",
        "model": MODEL,
        "ollama_server": OLLAMA_HOST
    }

# === Integración con Redis Bus ===
def start_bus_listener():
    """Inicia el listener de Redis Bus"""
    if not REDIS_AVAILABLE:
        print("⚠️  No se iniciará listener Redis (no disponible)")
        return
    
    def handle_query_request(message):
        """Manejador para solicitudes via bus"""
        global client  # Importante: declarar que usamos la variable global
        
        try:
            if message.get('type') != 'query_request':
                return
            
            data = message.get('data', {})
            query_id = data.get('query_id')
            query = data.get('query')
            reply_to = data.get('reply_to')
            
            if not query or not query_id or not reply_to:
                print("⚠️  Mensaje incompleto, ignorando")
                return
            
            print(f"📨 Ollama recibió mensaje del bus: {query[:50]}...")
            
            if not client:
                response_text = "Ollama no disponible"
                status = "error"
            else:
                try:
                    response = client.chat(
                        model=MODEL,
                        messages=[{"role": "user", "content": query}],
                        options={"temperature": 0.7}
                    )
                    response_text = response['message']['content'].strip()
                    status = "success"
                except Exception as e:
                    response_text = f"Error: {str(e)}"
                    status = "error"
            
            # Publicar respuesta via bus
            bus.publish(
                channel=reply_to,
                message_type='query_response',
                data={
                    'query_id': query_id,
                    'assistant': 'ollama',
                    'response': response_text,
                    'status': status
                },
                source='ollama'
            )
            
            print(f"✅ Ollama respondió via bus, ID: {query_id[:8]}")
            
        except Exception as e:
            print(f"❌ Error en handle_query_request: {e}")
    
    # Suscribirse al canal de solicitudes para ollama
    bus.subscribe('ollama_requests', handle_query_request)
    
    # También suscribirse a canal general para pruebas
    bus.subscribe('assistants.all', handle_query_request)
    
    # Iniciar el bus
    bus.start()
    print("✅ Ollama assistant escuchando en el bus de mensajes")

# Iniciar el listener en un hilo separado al arrancar
if REDIS_AVAILABLE:
    threading.Thread(target=start_bus_listener, daemon=True).start()
else:
    print("⚠️  Iniciando Ollama sin Redis Bus")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5003)