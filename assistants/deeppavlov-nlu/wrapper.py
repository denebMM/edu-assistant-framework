# DeepPavlov-NLU (Transformers QA) - VERSIÓN CON MODELO ALTERNATIVO
import threading
import sys
import os
import unicodedata
import re
from typing import Dict, Any

sys.path.append('/app')

# Redis Bus
try:
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    print("✅ RedisBus disponible para deeppavlov")
except Exception as e:
    REDIS_AVAILABLE = False
    print(f"⚠️ RedisBus no disponible: {e}")

from fastapi import FastAPI, Request
from transformers import pipeline
import uvicorn

app = FastAPI(title="DeepPavlov-NLU Transformers QA Educativo")

# ============================================
# MODELO ALTERNATIVO - USAR UNO QUE SÍ FUNCIONE
# ============================================
qa_pipeline = None
try:
    print("🔄 Cargando modelo transformers en español...")
    
    # INTENTAR DIFERENTES MODELOS (por orden de preferencia)
    modelos_alternativos = [
        "mrm8488/distill-bert-base-spanish-wwm-cased-finetuned-spa-squad2",  # Modelo español más pequeño
        "bert-large-multilingual-cased-squad2",  # Modelo multilingüe grande
        "distilbert-base-multilingual-cased",    # Modelo multilingüe pequeño
        "bert-base-multilingual-cased"           # Modelo base multilingüe
    ]
    
    modelo_cargado = False
    for modelo in modelos_alternativos:
        try:
            print(f"  Intentando modelo: {modelo}")
            qa_pipeline = pipeline(
                "question-answering",
                model=modelo,
                tokenizer=modelo,
                device=-1  # Usar CPU
            )
            print(f"✅ Modelo cargado: {modelo}")
            MODELO_USADO = modelo
            modelo_cargado = True
            break
        except Exception as e_modelo:
            print(f"  ❌ Falló {modelo}: {str(e_modelo)[:80]}...")
            continue
    
    if not modelo_cargado:
        print("⚠️ Todos los modelos fallaron. Usando modo contexto estático.")
        qa_pipeline = None
        MODELO_USADO = "none"
        
except Exception as e:
    print(f"❌ Error crítico cargando modelos: {e}")
    qa_pipeline = None
    MODELO_USADO = "error"

# ============================================
# CONTEXTO EDUCATIVO MEJORADO
# ============================================
CONTEXTO_EDUCATIVO = """
MATEMÁTICAS:
- La suma es la operación de adición: juntar dos o más números para obtener un total. Ejemplo: 45 + 100 = 145.
- La resta es la operación de sustracción: quitar una cantidad de otra. Ejemplo: 100 - 45 = 55.
- La multiplicación es la suma repetida. Ejemplo: 5 × 5 = 25.
- La división es el reparto en partes iguales. Ejemplo: 10 ÷ 2 = 5.
- 7 + 9 = 16.
- 9 + 8 = 17.
- Una ecuación cuadrática tiene forma ax² + bx + c = 0 y se resuelve con x = [-b ± √(b²-4ac)] / 2a.

CIENCIAS:
- La fotosíntesis es el proceso mediante el cual las plantas verdes convierten luz solar, agua y dióxido de carbono en glucosa y oxígeno.
- La mitosis es el proceso de división celular donde una célula madre se divide en dos células hijas genéticamente idénticas.
- La relatividad es una teoría física desarrollada por Albert Einstein que describe la relación entre espacio, tiempo, gravedad y energía.

HISTORIA:
- Albert Einstein fue un físico alemán nacido en 1879. Desarrolló la teoría de la relatividad y ganó el Premio Nobel de Física en 1921.
- Isaac Newton fue un físico, matemático y astrónomo inglés nacido en 1643. Formuló las leyes del movimiento y la ley de gravitación universal.

GEOGRAFÍA:
- La capital de Francia es París.
- La capital de España es Madrid.
- La capital de Italia es Roma.
- La capital de Alemania es Berlín.
"""

def buscar_en_contexto(consulta: str) -> str:
    """Busca respuestas simples en el contexto estático"""
    consulta_lower = consulta.lower()
    
    # Búsqueda de palabras clave
    if "45 + 100" in consulta or "45+100" in consulta:
        return "45 + 100 = 145"
    elif "7 + 9" in consulta or "7+9" in consulta:
        return "7 + 9 = 16"
    elif "9 + 8" in consulta or "9+8" in consulta:
        return "9 + 8 = 17"
    elif "fotosíntesis" in consulta_lower:
        return "La fotosíntesis es el proceso mediante el cual las plantas convierten luz solar, agua y CO2 en glucosa y oxígeno."
    elif "mitosis" in consulta_lower:
        return "La mitosis es el proceso de división celular que produce dos células hijas idénticas."
    elif "capital de francia" in consulta_lower:
        return "La capital de Francia es París."
    elif "capital de españa" in consulta_lower:
        return "La capital de España es Madrid."
    elif "einstein" in consulta_lower:
        return "Albert Einstein fue un físico alemán que desarrolló la teoría de la relatividad (1879-1955)."
    elif "relatividad" in consulta_lower:
        return "La relatividad es una teoría física de Einstein que describe la relación entre espacio, tiempo y gravedad."
    
    return ""

@app.post("/query")
async def handle_query(request: Request):
    """Endpoint HTTP"""
    try:
        data = await request.json()
        consulta = data.get("query", "").strip()

        if not consulta:
            return {
                "response": "No recibí ninguna pregunta.",
                "success": False,
                "source": "deeppavlov"
            }

        print(f"🔍 [HTTP] Consulta: '{consulta}'")

        # Primero intentar búsqueda en contexto estático
        respuesta_estatica = buscar_en_contexto(consulta)
        if respuesta_estatica:
            print(f"✅ Encontrada en contexto estático")
            return {
                "response": respuesta_estatica,
                "success": True,
                "source": "deeppavlov",
                "model": "contexto_estatico"
            }

        # Si hay pipeline, usarlo
        if qa_pipeline is not None:
            try:
                resultado = qa_pipeline(
                    question=consulta,
                    context=CONTEXTO_EDUCATIVO,
                    max_answer_len=100
                )
                
                respuesta = resultado.get("answer", "").strip()
                score = resultado.get("score", 0.0)
                
                print(f"📊 Score: {score:.4f} | Respuesta: '{respuesta}'")
                
                if score > 0.3 and len(respuesta) > 5:
                    return {
                        "response": respuesta,
                        "success": True,
                        "source": "deeppavlov",
                        "model": MODELO_USADO,
                        "confidence": round(score, 3)
                    }
            except Exception as e:
                print(f"⚠️ Error en pipeline: {e}")

        # Si llegamos aquí, no se pudo responder
        respuesta_final = "No encuentro información precisa sobre eso en mi base de conocimiento actual. Mi especialidad son matemáticas básicas, ciencias, historia y geografía."
        
        return {
            "response": respuesta_final,
            "success": False,
            "source": "deeppavlov",
            "model": MODELO_USADO if qa_pipeline else "none"
        }

    except Exception as e:
        print(f"❌ Error crítico en handle_query: {e}")
        return {
            "response": "Error interno en DeepPavlov.",
            "success": False,
            "error": str(e)
        }

@app.get("/health")
async def health():
    estado = "healthy" if qa_pipeline is not None else "degraded"
    return {
        "status": estado,
        "model_loaded": qa_pipeline is not None,
        "model": MODELO_USADO if 'MODELO_USADO' in globals() else "none",
        "service": "deeppavlov-nlu"
    }

# ============================================
# REDIS BUS SIMPLIFICADO
# ============================================
def start_bus_listener():
    if not REDIS_AVAILABLE:
        return

    def handle_query_request(message: Dict[Any, Any]):
        try:
            if message.get('type') != 'message':
                return
            
            data = json.loads(message['data'])
            if data.get('type') != 'query_request':
                return
            
            query_data = data.get('data', {})
            query_id = query_data.get('query_id')
            consulta = query_data.get('query', '').strip()
            reply_to = query_data.get('reply_to')

            if not all([query_id, consulta, reply_to]):
                return

            print(f"📨 [BUS] DeepPavlov recibió: '{consulta[:50]}...'")

            # Buscar respuesta
            respuesta_estatica = buscar_en_contexto(consulta)
            if respuesta_estatica:
                respuesta = respuesta_estatica
                status = "success"
            elif qa_pipeline is not None:
                try:
                    resultado = qa_pipeline(
                        question=consulta,
                        context=CONTEXTO_EDUCATIVO,
                        max_answer_len=100
                    )
                    respuesta_cruda = resultado.get("answer", "").strip()
                    score = resultado.get("score", 0.0)
                    
                    if score > 0.3 and len(respuesta_cruda) > 5:
                        respuesta = respuesta_cruda
                        status = "success"
                    else:
                        respuesta = "No tengo suficiente información sobre eso."
                        status = "error"
                except:
                    respuesta = "Error procesando con el modelo."
                    status = "error"
            else:
                respuesta = "Modelo no disponible. Intenta con preguntas básicas de matemáticas o ciencia."
                status = "error"

            # Responder
            bus.publish(
                channel=reply_to,
                message_type='query_response',
                data={
                    'query_id': query_id,
                    'assistant': 'deeppavlov',
                    'response': respuesta,
                    'status': status
                },
                source='deeppavlov'
            )
            
            print(f"📤 [BUS] Respondido → {status}")

        except Exception as e:
            print(f"❌ Error en bus handler: {e}")

    # Suscribirse
    bus.subscribe('deeppavlov_requests', handle_query_request)
    bus.start()
    print("✅ DeepPavlov escuchando en Redis Bus")

# Iniciar
if REDIS_AVAILABLE:
    threading.Thread(target=start_bus_listener, daemon=True).start()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5002)