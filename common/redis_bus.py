import redis
import json
import uuid
import threading
import time
import logging
from typing import Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)

class RedisBus:
    """Bus simple Redis Pub/Sub para comunicación entre asistentes"""
    
    def __init__(self, redis_url='redis://redis:6379'):
        try:
            self.redis = redis.Redis.from_url(
                redis_url, 
                decode_responses=True,
                socket_connect_timeout=10,  # Aumentado
                socket_timeout=30,          # Aumentado
                retry_on_timeout=True,      # NUEVO: reintentar en timeout
                health_check_interval=30    # NUEVO: chequeo de salud
            )
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=False)
            self.handlers = {}
            self._running = False
            self._thread = None
            self._reconnect_attempts = 0
            self.max_reconnect_attempts = 5
            logger.info(f"✅ RedisBus conectado a {redis_url}")
        except Exception as e:
            logger.error(f"❌ Error conectando a Redis: {e}")
            raise
    
    def publish(self, channel: str, message_type: str, data: Dict[str, Any], 
                source: str = "unknown") -> Optional[str]:
        """Publica un mensaje en un canal"""
        try:
            # Verificar conexión antes de publicar
            if not self._check_connection():
                logger.warning(f"⚠️  Redis no conectado, no se puede publicar en {channel}")
                return None
                
            message = {
                'id': str(uuid.uuid4()),
                'type': message_type,
                'source': source,
                'data': data,
                'timestamp': time.time()
            }
            result = self.redis.publish(channel, json.dumps(message))
            logger.debug(f"📤 Publicado en {channel}: {message_type} (clientes: {result})")
            return message['id']
        except redis.ConnectionError as e:
            logger.error(f"❌ Error de conexión publicando en {channel}: {e}")
            self._try_reconnect()
            return None
        except Exception as e:
            logger.error(f"❌ Error publicando en {channel}: {e}")
            return None
    
    def subscribe(self, channel: str, callback: Callable[[Dict[str, Any]], None]):
        """Suscribe una función a un canal"""
        try:
            if channel not in self.handlers:
                self.handlers[channel] = []
            self.handlers[channel].append(callback)
            self.pubsub.subscribe(channel)
            logger.info(f"📥 Suscrito a canal: {channel}")
        except Exception as e:
            logger.error(f"❌ Error suscribiéndose a {channel}: {e}")
    
    def start(self):
        """Inicia el listener en un hilo separado"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_listener, daemon=True)
        self._thread.start()
        logger.info("🚀 RedisBus listener iniciado")
    
    def stop(self):
        """Detiene el listener"""
        self._running = False
        try:
            self.pubsub.close()
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("🛑 RedisBus detenido")
        except Exception as e:
            logger.error(f"Error deteniendo RedisBus: {e}")
    
    def _check_connection(self):
        """Verifica si Redis está conectado"""
        try:
            return self.redis.ping()
        except:
            return False
    
    def _try_reconnect(self):
        """Intenta reconectar a Redis"""
        if self._reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("🚨 Máximos intentos de reconexión alcanzados")
            return False
        
        self._reconnect_attempts += 1
        logger.warning(f"🔄 Intentando reconectar a Redis (intento {self._reconnect_attempts})")
        
        try:
            self.redis = redis.Redis.from_url(
                'redis://redis:6379',
                decode_responses=True,
                socket_connect_timeout=10,
                socket_timeout=30,
                retry_on_timeout=True
            )
            self.pubsub = self.redis.pubsub(ignore_subscribe_messages=False)
            self._reconnect_attempts = 0
            logger.info("✅ Reconectado a Redis exitosamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error reconectando a Redis: {e}")
            return False
    
    def _run_listener(self):
        """Ejecuta el loop del listener con manejo robusto de errores"""
        logger.info("🎧 Iniciando loop de escucha RedisBus...")
        
        while self._running:
            try:
                # Verificar conexión antes de escuchar
                if not self._check_connection():
                    logger.warning("⚠️  Redis desconectado, intentando reconectar...")
                    if not self._try_reconnect():
                        time.sleep(5)  # Esperar antes de reintentar
                        continue
                
                # Escuchar mensajes
                for message in self.pubsub.listen():
                    if not self._running:
                        break
                    
                    if message['type'] == 'subscribe':
                        logger.debug(f"✅ Suscrito a canal: {message['channel']}")
                        continue
                    
                    if message['type'] == 'message':
                        channel = message['channel']
                        try:
                            data = json.loads(message['data'])
                            
                            # Ejecutar handlers registrados para este canal
                            if channel in self.handlers:
                                for handler in self.handlers[channel]:
                                    try:
                                        handler(data)
                                    except Exception as e:
                                        logger.error(f"❌ Error en handler para {channel}: {e}")
                        except json.JSONDecodeError as e:
                            logger.error(f"❌ Error decodificando mensaje en {channel}: {e}")
                            logger.debug(f"Mensaje crudo: {message['data'][:100]}...")
                            
            except redis.ConnectionError as e:
                logger.error(f"❌ Error de conexión en listener: {e}")
                time.sleep(2)  # Esperar antes de reintentar
                self._try_reconnect()
            except Exception as e:
                logger.error(f"❌ Error inesperado en listener: {e}")
                time.sleep(1)  # Esperar breve antes de continuar
        
        logger.info("👋 Loop de escucha RedisBus finalizado")

# Singleton global
bus = RedisBus()