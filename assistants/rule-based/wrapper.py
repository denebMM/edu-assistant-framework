# wrapper.py: Rule-based Assistant Wrapper - Versión FINAL corregida e integrada
import threading
import time
import sys
import os
from typing import Dict, Any

# Agregar ruta para common
sys.path.append('/app')

# Redis Bus
try:
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    print("✅ RedisBus disponible para rule_based")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️ RedisBus no disponible: {e}")

from fastapi import FastAPI, Request
import uvicorn

# Importar el chatbot original
from Code import chatbot

app = FastAPI(title="Rule-based Assistant")

# Frases comunes que indican que el rule-based no entendió o no tiene respuesta específica
UNKNOWN_PHRASES = [
    "no entiendo", "no sé", "no se", "lo siento", "disculpa",
    "no comprendo", "no tengo", "no puedo", "¿puedes repetir",
    "no match", "default", "unknown", "desconocido"
]

def es_respuesta_valida(response_text: str) -> bool:
    """Determina si la respuesta del rule-based es útil o solo un fallback genérico"""
    if not response_text:
        return False
    text_lower = response_text.strip().lower()
    if len(text_lower) < 10:  # Muy corta
        return False
    if any(phrase in text_lower for phrase in UNKNOWN_PHRASES):
        return False
    return True

@app.get("/")
async def root():
    return {"message": "Rule-based Assistant corriendo", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "rule_based"}

@app.post("/query")
async def handle_query(request: Request):
    """Endpoint HTTP - ahora con success flag para orquestador"""
    try:
        data = await request.json()
        query = data.get("query", "").strip()

        if not query:
            return {"response": "No recibí ninguna pregunta.", "success": False}

        print(f"🔍 [HTTP] Rule-based procesando: '{query}'")

        response_text = chatbot(query).strip()

        if es_respuesta_valida(response_text):
            success = True
            final_response = response_text
        else:
            final_response = (
                "Lo siento, no tengo una respuesta específica para eso con mis reglas básicas. "
                "¡Prueba con un saludo, un chiste o una operación matemática simple!"
            )
            success = False
            print("⚠️ Rule-based no reconoció la consulta → marcando como error")

        return {
            "response": final_response,
            "success": success,
            "source": "rule_based",
            "original_length": len(response_text)
        }

    except Exception as e:
        print(f"❌ Error crítico en handle_query HTTP: {e}")
        return {
            "response": "Error interno en el asistente basado en reglas.",
            "success": False,
            "error": str(e)
        }

# === Redis Bus Integration ===
# En el wrapper de rule-based, AÑADIR esto en la función start_bus_listener:
# En la función start_bus_listener del rule-based, REEMPLAZAR con:
def start_bus_listener():
    if not REDIS_AVAILABLE:
        print("⚠️ Redis no disponible → solo HTTP")
        return

    def handle_query_request(message):
        try:
            print(f"📨 [BUS] Rule-based recibió mensaje RAW: {message}")
            
            # El mensaje de Redis llega como diccionario
            if message.get('type') == 'message':
                # Parsear el JSON que viene en 'data'
                import json
                payload = json.loads(message['data'])
                
                if payload.get('type') == 'query_request':
                    data = payload.get('data', {})
                    query_id = data.get('query_id')
                    query = data.get('query', '').strip()
                    reply_to = data.get('reply_to')
                    
                    if not all([query_id, query, reply_to]):
                        print("⚠️ Mensaje incompleto vía bus")
                        return
                    
                    print(f"✅ [BUS] Rule-based procesando: '{query}'")
                    
                    # Procesar con el chatbot
                    raw_response = chatbot(query).strip()
                    
                    # Determinar si es respuesta válida
                    if es_respuesta_valida(raw_response):
                        response_text = raw_response
                        status = "success"
                        print(f"✅ Rule-based sabe responder: {response_text[:50]}")
                    else:
                        response_text = "No tengo una respuesta específica para eso."
                        status = "error"
                        print(f"⚠️ Rule-based no sabe → status=error")
                    
                    # Publicar respuesta
                    bus.publish(
                        channel=reply_to,
                        message_type='query_response',
                        data={
                            'query_id': query_id,
                            'assistant': 'rule_based',
                            'response': response_text,
                            'status': status
                        },
                        source='rule_based'
                    )
                    print(f"📤 [BUS] Rule-based respondió a {reply_to}")
                    
        except Exception as e:
            print(f"❌ Error en handler Redis: {e}")
            import traceback
            traceback.print_exc()

    # Suscribirse CORRECTAMENTE
    bus.subscribe('rule_based_requests', handle_query_request)
    bus.subscribe('assistants.all', handle_query_request)  # Para debugging
    
    # IMPORTANTE: Iniciar el bus (esto estaba faltando)
    bus.start()
    print("✅ Rule-based ESCUCHANDO en Redis Bus")
    
# Iniciar listener en background
if REDIS_AVAILABLE:
    threading.Thread(target=start_bus_listener, daemon=True).start()
else:
    print("⚠️ Iniciando rule-based solo con HTTP")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)