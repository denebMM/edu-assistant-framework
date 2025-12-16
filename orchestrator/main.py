# orchestrator/main.py - Versión con Redis Bus
import time
import uuid
import json
import requests
import ollama
import unicodedata
import logging
import threading
from typing import Dict, Any, Tuple, Optional
from db_utils import get_or_create_user, log_metric

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar Redis Bus
try:
    import sys
    sys.path.append('/app')
    from common.redis_bus import bus
    REDIS_AVAILABLE = True
    logger.info("✅ RedisBus disponible en orquestador")
except Exception as e:
    REDIS_AVAILABLE = False
    logger.warning(f"⚠️  RedisBus no disponible: {e}")

class Orchestrator:
    def __init__(self):
        self.services = {
            "rule_based": "http://rule-based:5001",
            "deeppavlov": "http://deeppavlov-nlu:5002",
        }
        # Modelo de Ollama - usa 'phi' o 'tinyllama' según lo que tengas disponible
        self.llm_model = "tinyllama" 
        
        # Variables para comunicación por bus
        self.pending_responses = {}
        self.response_events = {}
        
        # Iniciar listener de bus si está disponible
        if REDIS_AVAILABLE:
            self._setup_bus_listeners()
            bus.start()
            logger.info("✅ Orquestador configurado con bus de mensajes")
        else:
            logger.info("⚠️  Orquestador usando comunicación HTTP tradicional")
        
        logger.info(f"✅ Orquestador inicializado con modelo Ollama: {self.llm_model}")

    def _setup_bus_listeners(self):
        """Configura los listeners del bus"""
        def handle_assistant_response(message):
            """Maneja respuestas de asistentes por bus"""
            try:
                data = message.get('data', {})
                query_id = data.get('query_id')
                assistant = data.get('assistant')
                response = data.get('response')
                status = data.get('status', 'unknown')
                
                if query_id and query_id in self.response_events:
                    logger.info(f"📥 Respuesta recibida via bus de {assistant} para query {query_id[:8]}")
                    
                    # Guardar respuesta
                    self.pending_responses[query_id] = {
                        'assistant': assistant,
                        'response': response,
                        'status': status,
                        'received_at': time.time()
                    }
                    
                    # Notificar que llegó la respuesta
                    event = self.response_events.get(query_id)
                    if event:
                        event.set()
                        
            except Exception as e:
                logger.error(f"❌ Error manejando respuesta del bus: {e}")
        
        # Suscribirse a canal general de respuestas
        bus.subscribe('assistant_responses', handle_assistant_response)

    @staticmethod
    def normalize_text(text: str) -> str:
        """Normalizar texto: quitar tildes, minúsculas"""
        if not text:
            return ""
        return ''.join(
            c for c in unicodedata.normalize('NFD', text.lower())
            if unicodedata.category(c) != 'Mn'
        )

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Decide qué asistente usar basado en keywords"""
        norm_query = self.normalize_text(query)
        
        rule_keywords = ["hola", "hello", "hi", "chiste", "joke", "suma", "resta", "cuanto es", "fotosintesis", "revolucion francesa"]
        dp_keywords = ["que es", "explica", "defin", "quien es", "quien fue", "cuando", "donde", "por que", "que significa"]
        llm_keywords = ["como se hace", "como hago", "paso a paso", "dame un ejemplo", "escribe", "redacta", "opina", "crees que", "ayudame a"]

        if any(k in norm_query for k in rule_keywords):
            return {"assistant": "rule_based", "confidence": 0.9}
        elif any(k in norm_query for k in dp_keywords):
            return {"assistant": "deeppavlov", "confidence": 0.8}
        elif any(k in norm_query for k in llm_keywords):
            return {"assistant": "ollama", "confidence": 0.7}
        else:
            return {"assistant": "ollama", "confidence": 0.5}  # Ollama es el más versátil

    def call_assistant(self, assistant: str, query: str) -> Tuple[str, float, float]:
        """Llama al asistente - intenta bus primero, fallback a HTTP"""
        start = time.time()
        
        # Para rule_based y deeppavlov, intentar primero por bus
        if REDIS_AVAILABLE and assistant in ['rule_based', 'deeppavlov']:
            try:
                logger.info(f"🔄 Intentando llamar a {assistant} via bus...")
                result = self.call_assistant_via_bus(assistant, query)
                if result["success"]:
                    latency = time.time() - start
                    logger.info(f"✅ {assistant} respondió via bus en {latency:.2f}s")
                    
                    # Emitir evento de actividad
                    bus.publish(
                        channel='assistant_activity',
                        message_type='assistant_used_via_bus',
                        data={
                            'assistant': assistant,
                            'latency': latency,
                            'query_length': len(query)
                        },
                        source='orchestrator'
                    )
                    
                    return result["response"], latency, 0.0
                else:
                    logger.warning(f"⚠️  Bus falló para {assistant}: {result.get('error')}, intentando HTTP...")
            except Exception as e:
                logger.warning(f"⚠️  Error en bus para {assistant}: {e}, usando HTTP")
        
        # Fallback a HTTP tradicional
        logger.info(f"🔄 Llamando a {assistant} via HTTP...")
        try:
            if assistant == "rule_based":
                result = self.call_rule_based(query)
            elif assistant == "deeppavlov":
                result = self.call_deeppavlov(query)
            elif assistant == "ollama":
                result = self.call_ollama(query)
            else:
                result = {"success": False, "error": "Asistente desconocido"}
        except Exception as e:
            result = {"success": False, "error": str(e)}
        
        latency = time.time() - start
        error_rate = 0.0 if result["success"] else 1.0
        response = result.get("response", f"Error: {result.get('error', 'Desconocido')}")
        
        return response, latency, error_rate

    def call_assistant_via_bus(self, assistant: str, query: str, timeout: int = 10) -> Dict:
        """Llama a un asistente usando el bus Redis"""
        if not REDIS_AVAILABLE:
            return {"success": False, "error": "Redis no disponible"}
        
        query_id = str(uuid.uuid4())
        reply_channel = f"reply_{query_id}"
        
        # Crear evento para esperar respuesta
        response_event = threading.Event()
        self.response_events[query_id] = response_event
        self.pending_responses[query_id] = None
        
        # Suscribirse temporalmente al canal de respuesta
        def temp_handler(message):
            data = message.get('data', {})
            if data.get('query_id') == query_id:
                self.pending_responses[query_id] = {
                    'assistant': data.get('assistant'),
                    'response': data.get('response'),
                    'status': data.get('status', 'unknown')
                }
                response_event.set()
        
        bus.subscribe(reply_channel, temp_handler)
        
        # Publicar solicitud
        message_id = bus.publish(
            channel=f'{assistant}_requests',
            message_type='query_request',
            data={
                'query_id': query_id,
                'query': query,
                'reply_to': reply_channel,
                'timestamp': time.time()
            },
            source='orchestrator'
        )
        
        if not message_id:
            logger.error(f"❌ No se pudo publicar mensaje en el bus para {assistant}")
            return {"success": False, "error": "Error publicando en el bus"}
        
        logger.info(f"📤 Enviado via bus a {assistant}, ID: {query_id[:8]}")
        
        # Esperar respuesta con timeout
        response_received = response_event.wait(timeout=timeout)
        
        # Limpiar
        del self.response_events[query_id]
        
        if not response_received:
            logger.warning(f"⏰ Timeout esperando respuesta de {assistant} via bus")
            return {"success": False, "error": "Timeout esperando respuesta"}
        
        # Obtener resultado
        result = self.pending_responses.pop(query_id, None)
        
        if result and result.get('status') == 'success':
            # Extraer respuesta según el formato del asistente
            response_data = result.get('response')
            if isinstance(response_data, dict):
                if 'response' in response_data:
                    output = response_data['response']
                elif 'output_data' in response_data and 'response' in response_data['output_data']:
                    output = response_data['output_data']['response']
                else:
                    output = str(response_data)
            else:
                output = str(response_data)
            
            return {"success": True, "response": output}
        else:
            error_msg = result.get('response', 'Error desconocido') if result else 'Sin respuesta'
            return {"success": False, "error": error_msg}

    def call_rule_based(self, query: str) -> Dict:
        """Llamar rule-based con manejo de formatos"""
        try:
            # Asegurarnos de enviar el formato correcto
            payload = {"query": query}
            r = requests.post(f"{self.services['rule_based']}/query", json=payload, timeout=10)
            r.raise_for_status()
            data = r.json()
            
            logger.info(f"📥 Respuesta cruda de rule_based: {data}")
            
            if "output_data" in data:
                response = data["output_data"].get("response", "Sin respuesta")
            elif "response" in data:
                response = data.get("response", "Sin respuesta")
            else:
                response = str(data)  # Como fallback
            
            logger.info(f"✅ Respuesta extraída de rule_based: {response[:100]}...")
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"❌ Error en call_rule_based: {e}")
            return {"success": False, "error": str(e)}

    def call_deeppavlov(self, query: str) -> Dict:
        """Llamar DeepPavlov"""
        try:
            payload = {"query": query}
            r = requests.post(f"{self.services['deeppavlov']}/query", json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            
            response = data.get("response", "No respuesta de DeepPavlov")
            logger.info(f"✅ Respuesta de DeepPavlov: {response[:100]}...")
            return {"success": True, "response": response}
        except Exception as e:
            logger.error(f"❌ Error en call_deeppavlov: {e}")
            return {"success": False, "error": str(e)}

    def call_ollama(self, query: str) -> Dict:
        """Llamar Ollama con prompt educativo y manejo de errores mejorado"""
        try:
            prompt = f"""Eres un tutor educativo paciente y claro.
Responde en el mismo idioma de la pregunta.
Sé conciso pero informativo.

Pregunta del estudiante: {query}

Respuesta:"""
            
            logger.info(f"🔍 Llamando a Ollama con modelo: {self.llm_model}")
            logger.info(f"📝 Prompt: {prompt[:100]}...")
            
            # Verificar conexión y modelo primero
            try:
                models = ollama.list()
                logger.info(f"📋 Modelos disponibles en Ollama: {[m['name'] for m in models.get('models', [])]}")
                
                model_available = False
                for model in models.get('models', []):
                    if self.llm_model in model['name']:
                        model_available = True
                        break
                
                if not model_available:
                    logger.error(f"❌ Modelo {self.llm_model} no encontrado en Ollama")
                    return {"success": False, "error": f"Modelo {self.llm_model} no disponible"}
            except Exception as e:
                logger.error(f"❌ Error al listar modelos de Ollama: {e}")
                return {"success": False, "error": f"Error de conexión con Ollama: {str(e)}"}
            
            # Función para llamar a Ollama de manera asíncrona con timeout
            def call_ollama_async():
                try:
                    resp = ollama.chat(
                        model=self.llm_model,
                        messages=[{"role": "user", "content": prompt}],
                        options={"temperature": 0.7}
                    )
                    return resp
                except Exception as e:
                    return {"error": str(e)}
            
            # Ejecutar con timeout
            result = None
            thread = threading.Thread(target=lambda: globals().update({'result': call_ollama_async()}))
            thread.start()
            thread.join(timeout=30)  # 30 segundos timeout
            
            if thread.is_alive():
                logger.error("❌ Timeout en llamada a Ollama")
                return {"success": False, "error": "Timeout - Ollama tardó demasiado en responder"}
            
            if result and 'error' in result:
                logger.error(f"❌ Error en Ollama: {result['error']}")
                return {"success": False, "error": result['error']}
            
            if result and 'message' in result and 'content' in result['message']:
                response_text = result['message']['content'].strip()
                logger.info(f"✅ Ollama respondió: {response_text[:200]}...")
                return {"success": True, "response": response_text}
            else:
                logger.error(f"❌ Formato de respuesta inesperado de Ollama: {result}")
                return {"success": False, "error": "Formato de respuesta inesperado"}
                
        except Exception as e:
            logger.error(f"❌ Error en call_ollama: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

# Instancia global
orchestrator = Orchestrator()

def orchestrate(task: str, username: str = "anonymous") -> str:
    """Función principal que usa el orquestador"""
    if not task.strip():
        return "Por favor, escribe una pregunta."
    
    user_id = get_or_create_user(username)
    
    # 1. Analizar qué asistente usar
    analysis = orchestrator.analyze_query(task)
    primary_assistant = analysis["assistant"]
    
    logger.info(f"Consulta: '{task}' → Asistente primario: {primary_assistant}")
    
    # 2. Intentar con el primario
    response, latency, error_rate = orchestrator.call_assistant(primary_assistant, task)
    
    # 3. Fallback inteligente si falla
    fallback_used = False
    final_assistant = primary_assistant.capitalize()
    
    if error_rate > 0:
        logger.warning(f"⚠️ {primary_assistant} falló → intentando fallback")
        
        # Orden de fallback: rule_based -> deeppavlov -> respuesta genérica
        fallback_order = ["rule_based", "deeppavlov"]
        
        for fallback in fallback_order:
            if fallback != primary_assistant:
                logger.info(f"🔄 Probando fallback: {fallback}")
                response, latency, error_rate = orchestrator.call_assistant(fallback, task)
                final_assistant = f"{fallback.capitalize()} (fallback)"
                fallback_used = True
                
                if error_rate == 0:
                    logger.info(f"✅ Fallback exitoso con {fallback}")
                    break
                else:
                    logger.warning(f"❌ Fallback {fallback} también falló")
        
        # Si todos los fallbacks fallaron
        if error_rate > 0:
            logger.error("🚨 Todos los fallbacks fallaron")
            response = """Lo siento, los servicios de asistencia no están disponibles en este momento. 

Sugerencias:
1. Intenta con una pregunta más simple
2. Verifica tu conexión a internet
3. Vuelve a intentar más tarde

Ejemplos de preguntas que podrían funcionar:
- "Hola, ¿cómo estás?"
- "¿Qué es la fotosíntesis?"
- "Cuéntame un chiste"
"""
            final_assistant = "sistema (emergencia)"
            error_rate = 0.0  # No contar como error del usuario
            latency = 0.1
    
    # 4. Loguear métrica
    log_metric(final_assistant, latency, error_rate, user_id)
    
    # 5. Respuesta final
    return f"{response}\n\n(Asistente usado: {final_assistant} • Tiempo: {latency:.1f}s)"

# Para pruebas locales
if __name__ == "__main__":
    print("=== Pruebas del orquestador ===")
    test_queries = [
        ("Hola", "test_user"),
        ("¿Qué es la fotosíntesis?", "test_user"),
        ("Explica paso a paso cómo resolver una ecuación cuadrática", "test_user"),
        ("¿Quién fue Albert Einstein?", "test_user"),
        ("¿Cómo se resuelve una ecuación cuadrática?", "test_user"),
    ]
    
    for query, user in test_queries:
        print(f"\n{'='*50}")
        print(f"📝 Consulta: '{query}'")
        print(f"👤 Usuario: {user}")
        print("-"*50)
        result = orchestrate(query, user)
        print(f"📤 Resultado: {result}")
        print(f"{'='*50}")