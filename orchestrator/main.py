# orchestrator/main.py - VERSIÓN CORREGIDA CON SINGLETON Y REDIS BUS FUNCIONAL
import time
import uuid
import json
import logging
import threading
import os
from typing import Dict, Any, Tuple, Optional

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
    logger.warning(f"⚠️ RedisBus no disponible: {e}")
    raise RuntimeError(f"Redis Bus es requerido: {e}")

# Variables globales para singleton
_ORCHESTRATOR_INSTANCE = None
_ORCHESTRATOR_LOCK = threading.Lock()

class Orchestrator:
    """Orquestador principal usando Redis Bus"""
    
    def __init__(self):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis Bus es requerido para el orquestador")
        
        logger.info("🔄 Inicializando Orchestrator...")
        
        # Variables para comunicación por bus
        self.pending_responses = {}
        self.response_events = {}
        self.timeout = 8  # Timeout de 8 segundos (equilibrio entre rapidez y paciencia)
        
        # Iniciar listener de bus
        self._setup_bus_listeners()
        
        # Iniciar el bus de Redis
        bus.start()
        
        logger.info("✅ Orchestrator inicializado (Redis Bus activo, timeout: 8s)")

    def _setup_bus_listeners(self):
        """Configura listener para respuestas de asistentes"""
        def handle_assistant_response(message: Dict[str, Any]):
            try:
                logger.debug(f"📨 Mensaje RAW recibido: {message}")
                
                if message.get('type') != 'message':
                    return
                
                # Parsear el mensaje JSON
                try:
                    data = json.loads(message['data'])
                except json.JSONDecodeError as e:
                    logger.error(f"❌ Error decodificando JSON: {e}")
                    return
                
                if data.get('type') != 'query_response':
                    return
                
                response_data = data.get('data', {})
                query_id = response_data.get('query_id')
                
                if not query_id:
                    logger.warning("⚠️ Mensaje sin query_id")
                    return
                
                if query_id in self.response_events:
                    logger.info(f"📥 Respuesta recibida de {response_data.get('assistant', 'unknown')} para {query_id[:8]}")
                    
                    # Guardar respuesta
                    self.pending_responses[query_id] = {
                        'assistant': response_data.get('assistant'),
                        'response': response_data.get('response'),
                        'status': response_data.get('status', 'unknown')
                    }
                    
                    # Notificar que llegó la respuesta
                    event = self.response_events.get(query_id)
                    if event:
                        event.set()
                else:
                    logger.warning(f"⚠️ Query ID no encontrado en eventos: {query_id[:8]}")
                    
            except Exception as e:
                logger.error(f"❌ Error manejando respuesta del bus: {e}")
                import traceback
                logger.error(traceback.format_exc())

        # Suscribirse a canal general de respuestas
        bus.subscribe('orchestrator_responses', handle_assistant_response)
        logger.info("🎧 Orchestrator escuchando en 'orchestrator_responses'")

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Decide qué asistente usar basado en el contenido de la consulta"""
        query_lower = query.lower().strip()
        
        # 1. Detección de matemáticas simples
        math_patterns = [
            r'cu[áa]nto es\s+\d+\s*[+\-*/]\s*\d+',
            r'^\d+\s*[+\-*/]\s*\d+$',
            r'suma\s+\d+\s+y\s+\d+',
            r'resta\s+\d+\s+y\s+\d+',
            r'multiplica\s+\d+\s+y\s+\d+',
            r'divide\s+\d+\s+y\s+\d+',
            r'\d+\s*\+\s*\d+',  # Ej: "45+100", "45 + 100"
            r'\d+\s*\-\s*\d+',
            r'\d+\s*x\s*\d+',
            r'\d+\s*/\s*\d+'
        ]
        
        import re
        for pattern in math_patterns:
            if re.search(pattern, query_lower):
                return {"assistant": "rule_based", "reason": "matemáticas_simples"}
        
        # 2. Saludos, chistes, despedidas
        saludos = ["hola", "hello", "hi", "buenos días", "buenas tardes", "buenas noches"]
        chistes = ["chiste", "joke", "hazme reir", "cuéntame un chiste", "dime un chiste"]
        despedidas = ["adiós", "bye", "hasta luego", "nos vemos", "chao", "gracias"]
        
        if any(word in query_lower for word in saludos + chistes + despedidas):
            return {"assistant": "rule_based", "reason": "conversación_básica"}
        
        # 3. Preguntas factuales -> deeppavlov
        factual_keywords = [
            "qué es", "quién es", "quien es", "explica", "definición",
            "capital de", "qué significa", "cómo funciona", "qué son",
            "dónde está", "cuándo", "por qué"
        ]
        
        # Temas que DeepPavlov maneja bien
        deeppavlov_topics = [
            "fotosíntesis", "mitosis", "célula", "relatividad", "einstein",
            "newton", "gravedad", "física", "ciencia", "historia", "geografía"
        ]
        
        if (any(keyword in query_lower for keyword in factual_keywords) or
            any(topic in query_lower for topic in deeppavlov_topics)):
            return {"assistant": "deeppavlov", "reason": "pregunta_factual"}
        
        # 4. Todo lo demás -> ollama (asistente más capaz)
        return {"assistant": "ollama", "reason": "consulta_compleja"}

    def call_assistant_via_bus(self, assistant: str, query: str) -> Tuple[str, bool]:
        """Llama a un asistente vía Redis Bus y devuelve (respuesta, éxito)"""
        query_id = str(uuid.uuid4())
        reply_channel = "orchestrator_responses"
        
        # Crear evento para esperar respuesta
        event = threading.Event()
        self.response_events[query_id] = event
        
        try:
            # Publicar solicitud al canal específico del asistente
            logger.info(f"📤 Enviando a {assistant}: '{query[:50]}...' (ID: {query_id[:8]})")
            
            # Preparar el mensaje
            message_data = {
                'query_id': query_id,
                'query': query,
                'reply_to': reply_channel
            }
            
            # Publicar en Redis
            success = bus.publish(
                channel=f'{assistant}_requests',
                message_type='query_request',
                data=message_data,
                source='orchestrator'
            )
            
            if not success:
                logger.error(f"❌ No se pudo publicar en canal {assistant}_requests")
                return f"Error: No se pudo contactar a {assistant}", False
            
            logger.debug(f"✅ Mensaje publicado en Redis a {assistant}_requests")
            
            # Esperar respuesta con timeout
            if event.wait(timeout=self.timeout):
                # Obtener respuesta
                result = self.pending_responses.pop(query_id, {})
                status = result.get('status', 'error')
                response = result.get('response', 'Sin respuesta')
                
                if status == 'success':
                    logger.info(f"✅ {assistant} respondió exitosamente")
                    return response, True
                else:
                    logger.warning(f"⚠️ {assistant} respondió con error: {response[:100]}")
                    return response, False
            else:
                logger.warning(f"⏰ Timeout esperando respuesta de {assistant} ({self.timeout}s)")
                return f"Timeout: {assistant} no respondió en {self.timeout} segundos", False
                
        except Exception as e:
            logger.error(f"❌ Error llamando a {assistant}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return f"Error interno: {str(e)[:100]}", False
        finally:
            # Limpiar eventos pendientes
            if query_id in self.response_events:
                del self.response_events[query_id]
            if query_id in self.pending_responses:
                del self.pending_responses[query_id]

    def orchestrate_query(self, query: str, username: str = "estudiante") -> str:
        """Orquestación principal con fallback inteligente"""
        if not query or not query.strip():
            return "Por favor, escribe una pregunta."
        
        logger.info(f"👤 {username} pregunta: '{query}'")
        
        # 1. Análisis de la consulta
        analysis = self.analyze_query(query)
        primary = analysis["assistant"]
        reason = analysis["reason"]
        
        logger.info(f"🔍 Análisis: {primary} ({reason})")
        
        # 2. Intentar asistente primario
        response, success = self.call_assistant_via_bus(primary, query)
        
        if success:
            # Log para métricas
            logger.info(f"🎯 {primary} respondió exitosamente")
            return f"{response}\n\n[Respondido por: {primary.capitalize()}]"
        
        # 3. Fallback inteligente
        logger.warning(f"⚠️ {primary} falló → activando fallback")
        
        # Orden de fallback basado en el asistente que falló
        fallback_order = {
            "rule_based": ["deeppavlov", "ollama"],
            "deeppavlov": ["rule_based", "ollama"],
            "ollama": ["rule_based", "deeppavlov"]
        }
        
        # Intentar asistentes de fallback
        for fallback in fallback_order.get(primary, []):
            logger.info(f"🔄 Probando fallback: {fallback}")
            response, success = self.call_assistant_via_bus(fallback, query)
            
            if success:
                logger.info(f"✅ Fallback exitoso con {fallback}")
                return f"{response}\n\n[Respondido por: {fallback.capitalize()} (fallback)]"
        
        # 4. Si todo falla, intentar HTTP como último recurso
        logger.warning("🚨 Todos los asistentes fallaron por Redis → intentando HTTP directo")
        
        # Intentar llamada HTTP directa a rule_based (el más simple)
        try:
            import requests
            rule_based_url = os.getenv('RULE_BASED_URL', 'http://rule-based:5001')
            response = requests.post(
                f"{rule_based_url}/query",
                json={"query": query},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success", False):
                    return f"{data.get('response', 'Sin respuesta')}\n\n[Respondido por: Rule-based (HTTP directo)]"
        except Exception as e:
            logger.error(f"❌ Fallback HTTP también falló: {e}")
        
        # 5. Respuesta de error final
        error_message = """Lo siento, ninguno de los asistentes pudo responder tu pregunta en este momento.

Sugerencias:
• Intenta reformular la pregunta
• Prueba con algo más simple como "Hola", "45+100" o "¿Qué es la fotosíntesis?"
• Verifica que la pregunta esté clara y completa

¡Estamos mejorando continuamente! 😊"""
        
        logger.error("🚨 Todos los asistentes fallaron (incluyendo HTTP fallback)")
        return error_message

# ============================================
# PATRÓN SINGLETON PARA EL ORQUESTADOR
# ============================================
def get_orchestrator() -> Orchestrator:
    """Obtiene la instancia singleton del orquestador"""
    global _ORCHESTRATOR_INSTANCE
    
    with _ORCHESTRATOR_LOCK:
        if _ORCHESTRATOR_INSTANCE is None:
            try:
                logger.info("🔄 Creando nueva instancia del Orchestrator...")
                _ORCHESTRATOR_INSTANCE = Orchestrator()
                logger.info("✅ Orchestrator singleton creado exitosamente")
            except Exception as e:
                logger.error(f"❌ Error fatal creando Orchestrator: {e}")
                raise RuntimeError(f"No se pudo crear el orquestador: {e}")
        
        return _ORCHESTRATOR_INSTANCE

def orchestrate(query: str, username: str = "estudiante") -> str:
    """Función principal para orquestar consultas (API pública)"""
    try:
        orchestrator = get_orchestrator()
        return orchestrator.orchestrate_query(query, username)
    except Exception as e:
        logger.error(f"❌ Error en orquestación: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error del sistema del orquestador: {str(e)[:200]}"

# ============================================
# Funciones para compatibilidad con API existente
# ============================================
def get_or_create_user(username: str) -> str:
    """Función dummy para compatibilidad con db_utils"""
    return username

def log_metric(assistant: str, latency: float, error_rate: float, user_id: str) -> None:
    """Función dummy para compatibilidad con db_utils"""
    logger.info(f"📊 Métrica: {assistant} | Latencia: {latency:.2f}s | Error: {error_rate} | Usuario: {user_id}")

# ============================================
# Inicialización al importar
# ============================================
try:
    # Intentar crear el orquestador al importar (pero no bloquear si falla)
    if REDIS_AVAILABLE:
        # Solo intentar crear si Redis está disponible
        _orchestrator = get_orchestrator()
except Exception as e:
    logger.warning(f"⚠️ No se pudo inicializar el orquestador al importar: {e}")
    # No levantamos excepción para permitir que el módulo se importe

# ============================================
# Pruebas locales (solo si se ejecuta directamente)
# ============================================
if __name__ == "__main__":
    print("=== PRUEBAS DEL ORQUESTADOR (SINGLETON) ===")
    print("=" * 60)
    
    # Verificar Redis
    if not REDIS_AVAILABLE:
        print("❌ Redis no disponible. Ejecuta esto dentro del contenedor Docker.")
        exit(1)
    
    # Crear orquestador
    try:
        orchestrator = get_orchestrator()
        print("✅ Orchestrator singleton obtenido correctamente")
        
        # Verificar que es la misma instancia
        orchestrator2 = get_orchestrator()
        if orchestrator is orchestrator2:
            print("✅ Singleton funcionando: misma instancia")
        else:
            print("❌ ERROR: Singleton falló, instancias diferentes")
            
    except Exception as e:
        print(f"❌ Error obteniendo orquestador: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    
    # Pruebas
    test_queries = [
        ("hola", "Saludo básico"),
        ("45 + 100", "Matemáticas simple"),
        ("qué es la fotosíntesis", "Pregunta factual"),
        ("explícame la teoría de la relatividad", "Consulta compleja"),
        ("cuéntame un chiste", "Chiste"),
        ("capital de francia", "Geografía"),
    ]
    
    for query, descripcion in test_queries:
        print(f"\n{'='*60}")
        print(f"📝 Prueba: {descripcion}")
        print(f"❓ Pregunta: {query}")
        
        start_time = time.time()
        respuesta = orchestrator.orchestrate_query(query, "usuario_prueba")
        elapsed = time.time() - start_time
        
        print(f"⏱️  Tiempo: {elapsed:.2f}s")
        print(f"🤖 Respuesta: {respuesta[:200]}...")
        
        time.sleep(1)  # Pausa entre pruebas
    
    print("\n" + "="*60)
    print("✅ Pruebas completadas")