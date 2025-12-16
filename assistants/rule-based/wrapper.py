# wrapper.py: Adaptador para el AV basado en reglas con Redis Bus
import threading
import json
import time
import sys
import os

# Agregar ruta para importar common
sys.path.append('/app')

# Intentar importar Redis Bus
try:
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    print("✅ RedisBus disponible para rule_based")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️  RedisBus no disponible: {e}")

from fastapi import FastAPI, Request  # Framework para API REST
app = FastAPI()  # Inicializa la app

from Code import chatbot  

@app.get("/")
async def root():
    return {"message": "Rule-based AV funcionando", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rule_based_av"}

@app.get("/bus-status")
async def bus_status():
    """Endpoint para verificar estado del bus"""
    return {
        "redis_available": REDIS_AVAILABLE,
        "listeners": ["rule_based_requests", "assistants.all"] if REDIS_AVAILABLE else [],
        "status": "connected" if REDIS_AVAILABLE else "disconnected"
    }

@app.post("/query")
async def handle_query(request: Request):
    """
    Maneja una query educativa:
    - Recibe JSON: {"query": "string", "context": {"topic": "string"}} (estandarizado)
    - Llama al AV original (regla-based).
    - Devuelve JSON: {"task": "string", "output_data": {"response": "string", "status": "string", "metadata": "object"}}
    - Para hacerlo educativo: Agrega reglas en chatbot.py, e.g., if "suma" in user_input: return "Explicación de suma...".
      Por ahora, usa las reglas originales.
    """
    data = await request.json()  # Parsea input JSON
    query = data.get("query")  # Query principal
    context = data.get("context", {})  # Contexto opcional (e.g., tema educativo)
    
    if not query:
        return {"error": "No se proporcionó una query válida."}
    
    # Llama al AV original (regla-based)
    response_text = chatbot(query)  # Llama a la función chatbot del archivo original
    
    # Si Redis está disponible, emitir evento de actividad
    if REDIS_AVAILABLE:
        try:
            bus.publish(
                channel='assistant_activity',
                message_type='http_query_processed',
                data={
                    'assistant': 'rule_based',
                    'query': query[:100],  # Solo primeros 100 caracteres
                    'response_length': len(response_text),
                    'timestamp': time.time()
                },
                source='rule_based'
            )
        except Exception as e:
            print(f"⚠️  No se pudo emitir evento al bus: {e}")
    
    # Estandariza la salida JSON (universal para todos los AVs)
    return {
        "task": "explain_basic",  # Tipo de tarea (expande: "quiz", "adapt", etc.)
        "output_data": {
            "response": response_text,  # Respuesta del AV
            "status": "success",  # Estado
            "metadata": {"topic": context.get("topic", "general")}  # Metadata educativa
        }
    }

def start_bus_listener():
    """Inicia el listener del bus para rule_based"""
    if not REDIS_AVAILABLE:
        print("⚠️  No se iniciará listener Redis (no disponible)")
        return
    
    def handle_query_request(message):
        """Maneja mensajes de tipo 'query_request' del bus"""
        try:
            print(f"📨 rule_based recibió mensaje del bus: {message.get('type')}")
            
            if message.get('type') != 'query_request':
                return
            
            data = message.get('data', {})
            query_id = data.get('query_id')
            query = data.get('query')
            reply_to = data.get('reply_to')
            
            if not query or not query_id or not reply_to:
                print("⚠️  Mensaje incompleto, ignorando")
                return
            
            print(f"🔍 Procesando consulta via bus: {query[:50]}...")
            
            # Procesar la consulta con el chatbot existente
            response_text = chatbot(query)
            
            # Preparar respuesta en formato estandarizado
            response_data = {
                "task": "explain_basic",
                "output_data": {
                    "response": response_text,
                    "status": "success",
                    "metadata": {"topic": "general", "source": "rule_based"}
                }
            }
            
            # Publicar la respuesta en el canal de respuestas
            bus.publish(
                channel=reply_to,
                message_type='query_response',
                data={
                    'query_id': query_id,
                    'assistant': 'rule_based',
                    'response': response_data,
                    'status': 'success'
                },
                source='rule_based'
            )
            
            print(f"✅ rule_based respondió via bus, ID: {query_id[:8]}")
            
        except Exception as e:
            print(f"❌ Error en handle_query_request: {e}")
            if REDIS_AVAILABLE and 'reply_to' in locals() and reply_to:
                bus.publish(
                    channel=reply_to,
                    message_type='query_response',
                    data={
                        'query_id': query_id,
                        'assistant': 'rule_based',
                        'response': f"Error: {str(e)}",
                        'status': 'error'
                    },
                    source='rule_based'
                )
    
    # Suscribirse al canal de solicitudes para rule_based
    bus.subscribe('rule_based_requests', handle_query_request)
    
    # También suscribirse a canal general para pruebas
    bus.subscribe('assistants.all', handle_query_request)
    
    # Iniciar el bus
    bus.start()
    print("✅ rule_based assistant escuchando en el bus de mensajes")

# Iniciar el listener en un hilo separado al arrancar
if REDIS_AVAILABLE:
    threading.Thread(target=start_bus_listener, daemon=True).start()
else:
    print("⚠️  Iniciando rule_based sin Redis Bus")

# Este es para mantener compatibilidad con Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5001)