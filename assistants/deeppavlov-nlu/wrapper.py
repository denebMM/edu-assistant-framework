# wrapper.py: Adaptador para DeepPavlov-NLU con Redis Bus
import threading
import json
import time
import sys
import os

# Agregar ruta para importar common (si es necesario en Docker)
sys.path.append('/app')

# Intentar importar Redis Bus
try:
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    print("✅ RedisBus disponible para deeppavlov")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️  RedisBus no disponible: {e}")

from fastapi import FastAPI, Request
from transformers import pipeline
import uvicorn
import re

app = FastAPI(title="Transformers QA Educativo")

try:
    print("🔄 Cargando modelo transformers educativo...")
    # Usar un modelo más robusto y multilingüe
    qa_pipeline = pipeline(
        "question-answering", 
        model="mrm8488/bert-spanish-cased-finetuned-squad",  # Modelo en español
        tokenizer="mrm8488/bert-spanish-cased-finetuned-squad"
    )
    print("✅ Modelo transformers en español cargado correctamente")
except Exception as e:
    print(f"❌ Error al cargar el modelo español: {e}")
    try:
        # Fallback a modelo inglés
        qa_pipeline = pipeline(
            "question-answering", 
            model="distilbert-base-cased-distilled-squad"
        )
        print("✅ Modelo transformers en inglés cargado correctamente")
    except Exception as e2:
        print(f"❌ Error al cargar modelo inglés: {e2}")
        print("⚠️  Usando respuestas predefinidas...")
        qa_pipeline = None

# Base de conocimiento educativo MEJORADA
CONTEXTOS = {
    "es": """
    Albert Einstein fue un físico alemán nacido en 1879. Desarrolló la teoría de la relatividad, que revolucionó la física moderna. Recibió el Premio Nobel de Física en 1921.
    
    La fotosíntesis es el proceso mediante el cual las plantas verdes y otros organismos convierten la energía luminosa en energía química. Durante la fotosíntesis, las plantas absorben dióxido de carbono (CO2) y agua (H2O) para producir glucosa y liberar oxígeno (O2).
    
    La mitosis es el proceso de división celular en el que una célula madre se divide en dos células hijas genéticamente idénticas. Es esencial para el crecimiento y la reparación de tejidos.
    # ... (el resto de tu contexto truncado, agrégalo completo aquí)
    """,
    "en": """
    Albert Einstein was a German physicist born in 1879. He developed the theory of relativity, which revolutionized modern physics. He received the Nobel Prize in Physics in 1921.
    
    Photosynthesis is the process by which green plants and other organisms convert light energy into chemical energy. During photosynthesis, plants absorb carbon dioxide (CO2) and water (H2O) to produce glucose and release oxygen (O2).
    
    Mitosis is the process of cell division where a parent cell divides into two genetically identical daughter cells. It is essential for growth and tissue repair.
    # ... (el resto de tu contexto en inglés)
    """
}

def detectar_idioma(texto: str) -> str:
    """Detecta si el texto está en español o inglés"""
    texto_normalizado = unicodedata.normalize('NFD', texto.lower())
    if re.search(r'[áéíóúñ¿¡]', texto_normalizado):
        return "es"
    return "en"

def mejorar_respuesta(pregunta: str, respuesta: str, contexto: str, idioma: str) -> str:
    """Mejora la respuesta si es necesario"""
    # Tu lógica existente para mejorar (si la tienes; si no, deja pasar)
    return respuesta

@app.post("/query")
async def handle_query(request: Request):
    """Endpoint HTTP para compatibilidad"""
    data = await request.json()
    pregunta = data.get("query", "")
    
    if not pregunta:
        return {"error": "No se proporcionó una pregunta válida."}
    
    idioma = detectar_idioma(pregunta)
    contexto = CONTEXTOS.get(idioma, CONTEXTOS["en"])
    
    print(f"🔍 Pregunta recibida: '{pregunta}'")
    print(f"🌐 Idioma detectado: {idioma}")
    
    if qa_pipeline is None:
        return {
            "response": "Lo siento, el modelo no está disponible en este momento.",
            "language": idioma,
            "model": "none"
        }
    
    try:
        resultado = qa_pipeline(
            question=pregunta,
            context=contexto,
            max_answer_len=150
        )
        
        respuesta = resultado.get("answer", "").strip()
        score = resultado.get("score", 0)
        print(f"📈 Score de confianza: {score:.4f}")
        
        if score < 0.1:
            print("⚠️  Score bajo, respuesta podría ser incorrecta")
        
        respuesta = mejorar_respuesta(pregunta, respuesta, contexto, idioma)
        
        if not respuesta or len(respuesta) < 2:
            respuesta = "No encontré información específica sobre ese tema en mi base de conocimiento." if idioma == "es" else "I didn't find specific information about that topic in my knowledge base."
        
        return {
            "response": respuesta,
            "language": idioma,
            "model": "transformers"
        }
        
    except Exception as e:
        print(f"❌ Error en handle_query: {e}")
        import traceback
        traceback.print_exc()
        return {"response": f"Error procesando la pregunta. Por favor, intenta con otra formulación.", "error": True}

@app.get("/health")
async def health():
    return {
        "status": "healthy" if qa_pipeline is not None else "degraded",
        "service": "transformers_qa"
    }

# === Integración con Redis Bus ===
def start_bus_listener():
    """Inicia el listener de Redis Bus"""
    def handle_query_request(message_data: Dict[str, Any]):
        """Manejador para solicitudes via bus"""
        try:
            query_id = message_data.get('id', str(uuid.uuid4()))
            pregunta = message_data.get('data', {}).get('query', "")  # Ajusta según tu formato de bus
            reply_to = message_data.get('reply_to')  # Canal de reply si existe
            
            print(f"📨 deeppavlov recibió mensaje del bus: {pregunta[:50]}...")
            print(f"🔍 Procesando consulta via bus: {pregunta}...")
            
            idioma = detectar_idioma(pregunta)
            contexto = CONTEXTOS.get(idioma, CONTEXTOS["en"])
            
            if qa_pipeline is None:
                respuesta = "Lo siento, el modelo no está disponible en este momento."
            else:
                resultado = qa_pipeline(
                    question=pregunta,
                    context=contexto,
                    max_answer_len=150
                )
                respuesta_cruda = resultado.get("answer", "").strip()
                respuesta = mejorar_respuesta(pregunta, respuesta_cruda, contexto, idioma)
            
            if not respuesta or len(respuesta) < 2:
                respuesta = "No encontré información específica sobre ese tema en mi base de conocimiento." if idioma == "es" else "I didn't find specific information about that topic in my knowledge base."
            
            response_data = {
                "response": respuesta,
                "language": idioma,
                "model": "transformers"
            }
            
            # Publicar respuesta via bus
            bus.publish(
                channel=reply_to if reply_to else 'assistant_responses',
                message_type='query_response',
                data={
                    'query_id': query_id,
                    'assistant': 'deeppavlov',
                    'response': response_data,
                    'status': 'success'
                },
                source='deeppavlov'
            )
            
            print(f"✅ deeppavlov respondió via bus, ID: {query_id[:8]}")
            
        except Exception as e:
            print(f"❌ Error en handle_query_request: {e}")
            if reply_to:
                bus.publish(
                    channel=reply_to,
                    message_type='query_response',
                    data={
                        'query_id': query_id,
                        'assistant': 'deeppavlov',
                        'response': f"Error: {str(e)}",
                        'status': 'error'
                    },
                    source='deeppavlov'
                )
    
    # Suscribirse al canal de solicitudes para deeppavlov
    bus.subscribe('deeppavlov_requests', handle_query_request)
    
    # También suscribirse a canal general para pruebas
    bus.subscribe('assistants.all', handle_query_request)
    
    print("✅ deeppavlov assistant escuchando en el bus de mensajes")

# Iniciar el listener en un hilo separado al arrancar
if REDIS_AVAILABLE:
    threading.Thread(target=start_bus_listener, daemon=True).start()
else:
    print("⚠️  Iniciando deeppavlov sin Redis Bus")

# Este es para mantener compatibilidad con Uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)